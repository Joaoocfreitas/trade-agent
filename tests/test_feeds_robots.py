import asyncio

import httpx
import pytest

from coletor.feeds import buscar_feeds, desembrulhar, ler_feed
from coletor.fontes import Alvo
from coletor.rede import Bloqueado, PorHost, baixar
from coletor.robots import Robots, interpretar

RSS = b"""<?xml version="1.0"?><rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"><channel>
<item><title>Copom  mant\xc3\xa9m Selic</title><link>https://x.com/a</link><description>&lt;p&gt;Texto &lt;b&gt;resumo&lt;/b&gt;&lt;/p&gt;</description>
<pubDate>Tue, 21 Oct 2026 12:00:00 GMT</pubDate></item>
<item><title>Epis\xc3\xb3dio 10</title><guid isPermaLink="false">0af4-bada</guid><enclosure url="https://x.com/ep10.mp3" type="audio/mpeg" length="1"/></item>
<item><title>Sem link</title></item>
</channel></rss>"""

ALVO = Alvo('X', 'imprensa_br', 'eu_busco', 'feed', 'https://x.com/feed')


def test_ler_feed_limpa_html_detecta_podcast_e_descarta_sem_link():
    itens = ler_feed(RSS, ALVO)
    assert [(i.titulo, i.podcast) for i in itens] == [('Copom mantém Selic', False), ('Episódio 10', True)]
    assert itens[0].resumo == 'Texto resumo'
    assert itens[0].publicado == '2026-10-21T09:00:00-03:00'  # horário de Brasília, não UTC
    assert itens[1].url == 'https://x.com/ep10.mp3'  # episódio sem <link> nem guid-URL: vale o áudio
    assert itens[1].publicado is None


def test_desembrulha_o_redirecionador_da_folha():
    link = 'https://redir.folha.com.br/redir/online/poder/rss091/*https://www1.folha.uol.com.br/poder/2026/10/x.shtml'
    assert desembrulhar(link) == 'https://www1.folha.uol.com.br/poder/2026/10/x.shtml'
    assert desembrulhar('https://x.com/a*b') == 'https://x.com/a*b'


def test_robots_segue_a_rfc_9309():
    rp = interpretar(200, 'User-agent: *\nDisallow: /a\nAllow: /a/b\nDisallow: /*.pdf$\n')
    assert rp.can_fetch('https://x.com/a/b/c', 'TradeAgentPesquisa')  # vale a regra mais longa (Allow /a/b)
    assert not rp.can_fetch('https://x.com/a/z', 'TradeAgentPesquisa')
    assert not rp.can_fetch('https://x.com/doc.pdf', 'TradeAgentPesquisa')  # '*' e '$'
    assert rp.can_fetch('https://x.com/doc.pdf?v=1', 'TradeAgentPesquisa')


def test_robots_grupo_com_o_nome_do_robo_vale_para_ele():
    rp = interpretar(200, 'User-agent: TradeAgentPesquisa\nDisallow: /\n\nUser-agent: *\nAllow: /\n')
    assert not rp.can_fetch('https://x.com/qualquer', 'TradeAgentPesquisa')


def test_robots_na_duvida_nao_entra():
    assert interpretar(404, '') is True  # sem robots.txt: pode
    assert interpretar(429, '') is False  # servidor pedindo calma: não
    assert interpretar(503, '') is False  # servidor fora: não
    assert interpretar(None, '') is False  # falha de rede: não


def _servidor(rotas):
    def responder(req: httpx.Request) -> httpx.Response:
        chave = f'{req.url.scheme}://{req.url.host}{req.url.path}'
        status, headers, corpo = rotas.get(chave, (404, {}, b''))
        return httpx.Response(status, headers=headers, content=corpo)
    return httpx.MockTransport(responder)


def test_redirecionamento_para_host_que_proibe_e_barrado():
    rotas = {
        'https://a.com/robots.txt': (200, {}, b'User-agent: *\nAllow: /\n'),
        'https://a.com/feed': (301, {'location': 'https://b.com/feed'}, b''),
        'https://b.com/robots.txt': (200, {}, b'User-agent: *\nDisallow: /\n'),
        'https://b.com/feed': (200, {}, RSS),
    }

    async def cenario():
        async with httpx.AsyncClient(transport=_servidor(rotas), follow_redirects=False) as c:
            por_host = PorHost(0)
            with pytest.raises(Bloqueado) as b:
                await baixar(c, 'https://a.com/feed', Robots(c, por_host), por_host, 10_000)
            return b.value.url

    assert asyncio.run(cenario()) == 'https://b.com/feed'


def test_fila_do_dominio_nao_conta_no_limite_de_tempo(monkeypatch):
    import coletor.rede as rede
    monkeypatch.setattr(rede, 'TIMEOUT_S', 0.1)  # cada pedido tem 0,3 s; a fila de 3 leva mais que isso

    async def lento(req):
        await asyncio.sleep(0.15)
        return httpx.Response(200, content=RSS) if req.url.path != '/robots.txt' else httpx.Response(404)

    async def cenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lento), follow_redirects=False) as c:
            por_host = PorHost(0)
            robots = Robots(c, por_host)
            return await asyncio.gather(*(baixar(c, f'https://a.com/f{i}', robots, por_host, 10_000) for i in range(3)))

    assert [s for s, _, _ in asyncio.run(cenario())] == [200, 200, 200]


def test_feed_quebrado_nao_derruba_a_rodada():
    rotas = {
        'https://a.com/robots.txt': (404, {}, b''),
        'https://a.com/bom': (200, {}, RSS),
        'https://a.com/ruim': (200, {}, b'\x00\xff nada de xml'),
        'https://c.com/robots.txt': (503, {}, b''),
        'https://c.com/feed': (200, {}, RSS),
    }
    alvos = [Alvo('Bom', 'imprensa_br', 'eu_busco', 'feed', 'https://a.com/bom'),
             Alvo('Ruim', 'imprensa_br', 'eu_busco', 'feed', 'https://a.com/ruim'),
             Alvo('Fora', 'imprensa_br', 'eu_busco', 'feed', 'https://c.com/feed')]

    async def cenario():
        async with httpx.AsyncClient(transport=_servidor(rotas), follow_redirects=False) as c:
            por_host = PorHost(0)
            return await buscar_feeds(alvos, c, Robots(c, por_host), por_host)

    itens, falhas = asyncio.run(cenario())
    assert {i.fonte for i in itens} == {'Bom'}
    assert {(f['fonte'], f['status']) for f in falhas} == {('Ruim', 'erro'), ('Fora', 'bloqueado_robots')}


def test_por_host_um_pedido_por_vez_e_intervalo_contado_do_fim():
    async def cenario():
        ph = PorHost(0.2)
        loop = asyncio.get_running_loop()
        marcas = []

        async def pedido(url, nome, dura):
            async with ph.vez(url):
                marcas.append((nome, 'inicio', loop.time()))
                await asyncio.sleep(dura)
                marcas.append((nome, 'fim', loop.time()))

        await asyncio.gather(pedido('https://a.com/1', 'a1', 0.1), pedido('https://a.com/2', 'a2', 0.0),
                             pedido('https://b.com/1', 'b1', 0.0))
        return {(n, e): t for n, e, t in marcas}

    m = asyncio.run(cenario())
    assert m[('a2', 'inicio')] - m[('a1', 'fim')] >= 0.19  # não sobrepõe e espera o intervalo depois do fim
    assert m[('b1', 'inicio')] < m[('a1', 'fim')]  # outro domínio não espera

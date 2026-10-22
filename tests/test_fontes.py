import json

from coletor.fontes import carregar_fontes, eh_feed, extrair_feeds, selecionar_alvos


def fonte(**kw):
    base = dict(nome='X', acesso='eu_busco', url='https://x.com.br', acesso_detalhe='', o_que_extrair='')
    return {**base, **kw}


def test_eh_feed_pelo_caminho_ou_pelo_host():
    assert eh_feed('https://www.infomoney.com.br/feed/')
    assert eh_feed('https://feeds.folha.uol.com.br/mercado/rss091.xml')
    assert eh_feed('https://feeds.megaphone.fm/NPP2619427256')
    assert eh_feed('https://www.bloomberglinea.com.br/arc/outboundfeeds/rss/?outputType=xml')
    assert not eh_feed('https://neofeed.com.br')  # 'feed' no nome do domínio não é feed
    assert not eh_feed('https://www.bcb.gov.br/controleinflacao/copom')


def test_extrai_feeds_de_qualquer_campo_e_sem_pontuacao_no_fim():
    f = fonte(url='https://neofeed.com.br', acesso_detalhe='RSS em https://neofeed.com.br/feed/. Paywall parcial.',
              o_que_extrair='ver (https://neofeed.com.br/feed/)')
    assert extrair_feeds(f) == ['https://neofeed.com.br/feed/']


def test_selecao_pula_fechadas_e_api_e_usa_pagina_sem_feed():
    fontes = [
        {**fonte(nome='A', acesso='voce_me_passa'), 'categoria': 'imprensa_br', 'titulo': 'A'},
        {**fonte(nome='B', acesso='api_gratis'), 'categoria': 'dados', 'titulo': 'B'},
        {**fonte(nome='C', acesso='misto', acesso_detalhe='https://c.com/feed'), 'categoria': 'imprensa_br', 'titulo': 'C'},
        {**fonte(nome='D', url='https://d.org/cartas'), 'categoria': 'pessoas_br_mercado', 'titulo': 'D'},
        {**fonte(nome='E', url=''), 'categoria': 'metodo', 'titulo': 'E'},
    ]
    alvos = selecionar_alvos(fontes)
    assert [(a.fonte, a.tipo, a.url) for a in alvos] == [('C', 'feed', 'https://c.com/feed'),
                                                          ('D', 'pagina', 'https://d.org/cartas')]
    assert [a.fonte for a in selecionar_alvos(fontes, 'pessoas_br_mercado')] == ['D']


def test_carregar_fontes_junta_categorias_e_acrescimos_sem_duplicar(tmp_path):
    item = dict(nome='Valor Econômico', acesso='misto', url='https://valor.globo.com')
    (tmp_path / 'imprensa_br.json').write_text(json.dumps({'itens': [item]}), encoding='utf-8')
    (tmp_path / 'acrescimos.json').write_text(json.dumps({'itens': [
        {**item, 'nome': 'Valor  Economico', 'categoria': 'imprensa_br'},
        {**item, 'nome': 'Focus', 'categoria': 'dados'},
        {**item, 'nome': 'Fora', 'categoria': 'inexistente'},
    ]}), encoding='utf-8')
    fontes = carregar_fontes(tmp_path)
    assert [(f['titulo'], f['categoria']) for f in fontes] == [('Valor Econômico', 'imprensa_br'), ('Focus', 'dados')]


def test_duplicata_fica_na_categoria_do_seu_tipo(tmp_path):
    veiculo = dict(nome='Brazil Journal', tipo='jornal', acesso='eu_busco', url='https://braziljournal.com')
    pessoa = dict(nome='Lauro Jardim', tipo='pessoa', acesso='misto', url='https://oglobo.globo.com')
    (tmp_path / 'pessoas_br_politica.json').write_text(json.dumps({'itens': [veiculo, pessoa]}), encoding='utf-8')
    (tmp_path / 'imprensa_br.json').write_text(json.dumps({'itens': [veiculo, pessoa]}), encoding='utf-8')
    cats = {f['titulo']: f['categoria'] for f in carregar_fontes(tmp_path)}
    assert cats == {'Brazil Journal': 'imprensa_br', 'Lauro Jardim': 'pessoas_br_politica'}

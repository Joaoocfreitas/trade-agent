"""Coletor do mega brain.

  python -m coletor listar [--categoria CHAVE]
  python -m coletor coletar [--categoria CHAVE] [--paginas] [--artigos N] [--max-alvos N] [--sem-cofre]
  python -m coletor resumo   # reescreve a nota da última rodada sem ir à rede
  python -m coletor gatilhos [--horas 24] [--saida caminho.md]   # lista do dia para revisão, sem rede

Por padrão lê os feeds e captura o texto completo dos N artigos mais novos de cada feed de texto.
Com --paginas, também tira um retrato das páginas das fontes sem feed (mais lento: rode uma vez por semana).
"""
import argparse
import asyncio
import json
from collections import Counter, defaultdict
from datetime import datetime

import httpx

from . import config
from .armazem import Armazem, trava
from .assuntos import classificar
from .cofre import gravar_resumo, notas_existentes, resumo_coleta
from .feeds import buscar_feeds
from .fontes import carregar_fontes, selecionar_alvos
from .rede import PorHost
from .robots import Robots


def listar(args: argparse.Namespace) -> None:
    alvos = selecionar_alvos(carregar_fontes(config.FONTES_DIR), args.categoria)
    por_cat = Counter((a.categoria, a.tipo) for a in alvos)
    for (cat, tipo), n in sorted(por_cat.items()):
        print(f'{cat:22} {tipo:7} {n}')
    print(f'total: {len(alvos)} alvos de {len({a.fonte for a in alvos})} fontes')


def _pendencia(fonte: str, url: str, status: str, http: int | None = None, detalhe: str | None = None) -> dict:
    return {'fonte': fonte, 'url': url, 'status': status, 'detalhe': detalhe or (str(http) if http else None)}


async def coletar(args: argparse.Namespace) -> None:
    quando = datetime.now(config.FUSO)
    agora = quando.isoformat(timespec='seconds')
    alvos = selecionar_alvos(carregar_fontes(config.FONTES_DIR), args.categoria)
    if args.max_alvos:
        alvos = alvos[: args.max_alvos]
    feeds = [a for a in alvos if a.tipo == 'feed']
    paginas = [a for a in alvos if a.tipo == 'pagina'] if args.paginas else []
    arm = Armazem(config.COLETA_DIR)
    por_host = PorHost(config.INTERVALO_MESMO_DOMINIO_S)

    # follow_redirects=False: os redirecionamentos são seguidos à mão, checando o robots.txt de cada salto.
    async with httpx.AsyncClient(headers={'User-Agent': config.USER_AGENT}, timeout=config.TIMEOUT_S,
                                 follow_redirects=False) as cliente:
        robots = Robots(cliente, por_host)
        itens, falhas = await buscar_feeds(feeds, cliente, robots, por_host)
        print(f'feeds: {len(feeds) - len(falhas)}/{len(feeds)} lidos, {len(itens)} itens')

        vistos: set[str] = set()
        frescos = []
        for it in itens:
            if it.url not in vistos and not arm.ja_visto(it.url):
                vistos.add(it.url)
                frescos.append(it)

        por_feed = defaultdict(list)
        for it in frescos:
            if not it.podcast:
                por_feed[it.feed_url].append(it)
        para_ler = []
        for lista in por_feed.values():
            lista.sort(key=lambda i: i.publicado or '', reverse=True)
            para_ler += [i.url for i in lista[: args.artigos]]

        capturas, navegador_falhou = {}, False
        urls = list(dict.fromkeys(para_ler + [a.url for a in paginas]))
        if urls:
            print(f'capturando {len(para_ler)} artigos e {len(paginas)} páginas com o crawl4ai…')
            try:
                from .paginas import capturar  # importa o navegador só quando precisa
                capturas = await capturar(urls, cliente, robots, por_host, visivel=args.ver)
            except Exception as e:  # sem navegador a rodada continua só com as manchetes
                navegador_falhou = True
                falhas.append(_pendencia('(navegador do crawl4ai)', '', 'erro', detalhe=f'não abriu: {type(e).__name__}: {e}'[:200]))

    novos = []
    artigos_por_fonte = defaultdict(list)
    for it in frescos:
        cap = capturas.get(it.url)
        if cap:
            status, http, n = cap.status, cap.http, cap.palavras
            artigos_por_fonte[it.fonte].append((cap.status, it.url, cap.http))
        elif navegador_falhou and it.url in para_ler:
            status, http, n = 'erro', None, 0  # passageiro: tenta de novo na próxima rodada
        else:
            status, http, n = 'resumo', None, 0
        novos.append(arm.salvar({
            'fonte': it.fonte, 'categoria': it.categoria, 'acesso': it.acesso, 'tipo': 'artigo' if cap else 'item',
            'url': it.url, 'feed': it.feed_url, 'titulo': it.titulo, 'resumo': it.resumo, 'publicado': it.publicado,
            'coletado_em': agora, 'status': status, 'http': http, 'podcast': it.podcast, 'palavras': n,
            'assuntos': classificar(it.titulo, it.resumo),
        }, cap.markdown if cap and cap.status == 'ok' else None))

    # Fonte cujos artigos nenhum deu para ler (paywall, robots, recusa) vira pendência, com o motivo mais frequente.
    for fonte, caps in artigos_por_fonte.items():
        if not any(s == 'ok' for s, _, _ in caps):
            status = Counter(s for s, _, _ in caps).most_common(1)[0][0]
            _, url, http = next(c for c in caps if c[0] == status)
            falhas.append(_pendencia(fonte, url, status, http))

    for a in paginas:
        cap = capturas.get(a.url)
        if cap is None:
            continue  # navegador não abriu: já está nas pendências
        if cap.status != 'ok':
            falhas.append(_pendencia(a.fonte, a.url, cap.status, cap.http))
        elif arm.pagina_mudou(a.fonte, a.url, cap.markdown):
            novos.append(arm.salvar({
                'fonte': a.fonte, 'categoria': a.categoria, 'acesso': a.acesso, 'tipo': 'pagina', 'url': a.url,
                'titulo': cap.titulo or a.fonte, 'resumo': '', 'publicado': None, 'coletado_em': agora, 'status': 'ok',
                'http': cap.http, 'podcast': False, 'palavras': cap.palavras,
                'assuntos': classificar(cap.titulo, cap.markdown[:1500]),
            }, cap.markdown))

    status = Counter(r['status'] for r in novos)
    print(f'novos: {len(novos)} ({dict(status)}); pendências: {len(falhas)}')
    rodadas = config.COLETA_DIR / 'rodadas'
    rodadas.mkdir(parents=True, exist_ok=True)
    (rodadas / f'{quando:%Y-%m-%dT%H%M%S}.json').write_text(
        json.dumps({'coletado_em': agora, 'falhas': falhas}, ensure_ascii=False, indent=1), encoding='utf-8')
    if not (novos or falhas):
        print('nada novo: nenhuma nota escrita no cofre')
    elif not args.sem_cofre:
        destino = gravar_resumo(config.COFRE, resumo_coleta(novos, falhas, quando, notas_existentes(config.COFRE)), quando)
        print(f'resumo no cofre: {destino}')


def refazer_resumo(_args: argparse.Namespace) -> None:
    """Reescreve a nota da última rodada a partir do índice, sem buscar nada de novo na rede."""
    rodadas = sorted((config.COLETA_DIR / 'rodadas').glob('*.json'))
    if not rodadas:
        raise SystemExit('nenhuma rodada registrada em dados/coleta/rodadas')
    rodada = json.loads(rodadas[-1].read_text(encoding='utf-8'))
    novos = [r for r in Armazem(config.COLETA_DIR).registros() if r['coletado_em'] == rodada['coletado_em']]
    quando = datetime.fromisoformat(rodada['coletado_em'])
    destino = gravar_resumo(config.COFRE, resumo_coleta(novos, rodada['falhas'], quando, notas_existentes(config.COFRE)),
                            quando, substituir=True)
    print(f'{len(novos)} itens; resumo reescrito: {destino}')


def lista_de_gatilhos(args: argparse.Namespace) -> None:
    """Lê o índice, separa as manchetes das últimas N horas que acionam um gatilho e grava a lista do dia. Sem rede."""
    from datetime import timedelta
    from pathlib import Path

    from .gatilhos import GATILHOS, contar, markdown, selecionar

    ate = datetime.now(config.FUSO)
    desde = ate - timedelta(hours=args.horas)
    selecionados = selecionar(Armazem(config.COLETA_DIR).registros(), desde, ate)
    destino = Path(args.saida) if args.saida else config.COLETA_DIR / f'gatilhos-{ate:%Y-%m-%d}.md'
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(markdown(selecionados, ate.date(), desde, ate), encoding='utf-8')
    n = contar(selecionados)
    por = ', '.join(f'{g.nome}: {n[g.nome]}' for g in GATILHOS if n[g.nome])
    print(f'{len(selecionados)} itens{f" ({por})" if por else ""}')
    print(f'lista: {destino}')


def main() -> None:
    p = argparse.ArgumentParser(prog='coletor')
    sub = p.add_subparsers(dest='cmd', required=True)
    pl = sub.add_parser('listar')
    pl.add_argument('--categoria', choices=sorted(config.CATEGORIAS))
    pc = sub.add_parser('coletar')
    pc.add_argument('--categoria', choices=sorted(config.CATEGORIAS))
    pc.add_argument('--paginas', action='store_true', help='também captura as páginas das fontes sem feed')
    pc.add_argument('--artigos', type=int, default=config.ARTIGOS_POR_FEED, help='artigos completos por feed (0 = só manchetes)')
    pc.add_argument('--max-alvos', type=int, default=0)
    pc.add_argument('--sem-cofre', action='store_true', help='não grava o resumo no Obsidian')
    pc.add_argument('--ver', action='store_true', help='abre a janela do navegador na tela para acompanhar')
    sub.add_parser('resumo', help='reescreve a nota da última rodada, sem rede')
    pg = sub.add_parser('gatilhos', help='lista do dia para revisão do fundador, sem rede')
    pg.add_argument('--horas', type=float, default=24, help='janela: as últimas N horas até agora (padrão 24)')
    pg.add_argument('--saida', help='arquivo .md (padrão: dados/coleta/gatilhos-AAAA-MM-DD.md)')
    args = p.parse_args()
    if args.cmd == 'gatilhos' and args.horas <= 0:
        p.error('--horas precisa ser maior que zero')
    if args.cmd == 'listar':
        listar(args)
    elif args.cmd == 'resumo':
        refazer_resumo(args)
    elif args.cmd == 'gatilhos':
        lista_de_gatilhos(args)
    else:
        with trava(config.COLETA_DIR):
            asyncio.run(coletar(args))


if __name__ == '__main__':
    main()

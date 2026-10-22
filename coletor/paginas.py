"""Captura páginas com o crawl4ai e devolve o texto limpo em Markdown.

Regras fixas: robots.txt checado por nós (RFC 9309, com o nome do robô) antes e depois de cada captura;
nada de modo furtivo, de simular usuário, de remover a caixa do paywall ou de esconder que o navegador é automatizado.
O que o site não deixa ler vira pendência no checklist do João, não um desafio a contornar.
"""
import asyncio
import os
from dataclasses import dataclass

os.environ.setdefault('CRAWL4AI_NO_CLOUD_NOTICE', '1')

import httpx  # noqa: E402
from crawl4ai import (  # noqa: E402
    AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig, DefaultMarkdownGenerator, PruningContentFilterLXML,
)
from crawl4ai import browser_manager as _bm  # noqa: E402
from crawl4ai.utils import RobotsParser  # noqa: E402

from .config import COLETA_DIR, PAGINAS_SIMULTANEAS, TIMEOUT_S, USER_AGENT  # noqa: E402
from .conteudo import classificar_captura, palavras  # noqa: E402
from .rede import Bloqueado, PorHost, resolver  # noqa: E402
from .robots import Robots  # noqa: E402

DISFARCE = 'AutomationControlled'


def _sem_disfarce(fn):
    """O crawl4ai sempre passa --disable-blink-features=AutomationControlled, que esconde navigator.webdriver.
    Aqui o navegador se mostra automatizado, como deve."""
    def envolto(*a, **kw):
        r = fn(*a, **kw)
        if isinstance(r, dict):
            r['args'] = [x for x in r.get('args', []) if DISFARCE not in x]
        elif isinstance(r, list):
            r = [x for x in r if DISFARCE not in x]
        return r
    envolto.__wrapped__ = fn
    return envolto


if not hasattr(_bm.BrowserManager._build_browser_args, '__wrapped__'):
    _bm.BrowserManager._build_browser_args = _sem_disfarce(_bm.BrowserManager._build_browser_args)
    _bm.ManagedBrowser.build_browser_flags = staticmethod(_sem_disfarce(_bm.ManagedBrowser.build_browser_flags))


@dataclass
class Captura:
    url: str
    status: str
    http: int | None
    titulo: str
    markdown: str
    palavras: int
    erro: str | None


def _markdown(resultado) -> str:
    md = resultado.markdown
    if md is None:
        return ''
    fit = getattr(md, 'fit_markdown', None) or ''
    bruto = getattr(md, 'raw_markdown', None) or str(md)
    # O filtro de poda às vezes come o artigo inteiro; nesse caso fica o bruto.
    return fit if palavras(fit) >= 0.3 * palavras(bruto) else bruto


SIMBOLO = {'ok': '✓', 'paywall': '$', 'curto': '·', 'bloqueado_robots': '⊘', 'bloqueado': '⊘'}


def _mostrar(cap: 'Captura') -> None:
    print(f"  {SIMBOLO.get(cap.status, '✗')} {cap.status:16} {cap.palavras:5} palavras  {cap.url[:95]}", flush=True)


def configuracoes(visivel: bool = False) -> tuple[BrowserConfig, CrawlerRunConfig]:
    """visivel=True abre a janela do navegador na tela (para acompanhar). O comportamento com os sites é o mesmo."""
    navegador = BrowserConfig(headless=not visivel, user_agent=USER_AGENT, text_mode=True, enable_stealth=False,
                              verbose=False)
    execucao = CrawlerRunConfig(
        check_robots_txt=True,  # segunda trava; a primeira é a nossa, em capturar()
        cache_mode=CacheMode.BYPASS,
        page_timeout=TIMEOUT_S * 1000,
        markdown_generator=DefaultMarkdownGenerator(content_filter=PruningContentFilterLXML()),
        excluded_tags=['nav', 'footer', 'header', 'aside', 'form', 'script', 'style'],
        magic=False,
        simulate_user=False,
        override_navigator=False,
        remove_overlay_elements=False,
        verbose=False,
    )
    return navegador, execucao


def _falhou(url: str, status: str, erro: str) -> Captura:
    return Captura(url, status, None, '', '', 0, erro)


async def capturar(urls: list[str], cliente: httpx.AsyncClient, robots: Robots, por_host: PorHost,
                   visivel: bool = False) -> dict[str, Captura]:
    """Captura cada URL uma vez, um pedido por vez por domínio, no máximo PAGINAS_SIMULTANEAS domínios ao mesmo tempo."""
    urls = list(dict.fromkeys(urls))
    if not urls:
        return {}
    navegador, execucao = configuracoes(visivel)
    sem = asyncio.Semaphore(PAGINAS_SIMULTANEAS)
    capturas: dict[str, Captura] = {}

    async with AsyncWebCrawler(config=navegador) as crawler:
        crawler.robots_parser = RobotsParser(cache_dir=str(COLETA_DIR / 'robots-crawl4ai'), cache_ttl=86400)

        async def uma(url: str) -> None:
            try:
                final = await resolver(cliente, url, robots, por_host)
            except Bloqueado as b:
                capturas[url] = _falhou(url, 'bloqueado_robots', f'robots.txt de {b.url}')
                return
            async with por_host.vez(final):  # o mesmo lock do HEAD e do robots.txt: um pedido por vez ao domínio
                async with sem:
                    try:
                        r = await asyncio.wait_for(crawler.arun(final, config=execucao), TIMEOUT_S * 3)
                    except Exception as e:  # uma página que trava ou quebra não derruba as outras
                        capturas[url] = _falhou(url, 'erro', type(e).__name__)
                        return
            destino = r.redirected_url or final
            if destino != final and not await robots.permite(destino):
                capturas[url] = _falhou(url, 'bloqueado_robots', f'robots.txt de {destino}')
                return
            texto = _markdown(r) if r.success else ''
            erro = None if r.success else (r.error_message or 'falha')
            capturas[url] = Captura(
                url=url,
                status=classificar_captura(texto, r.status_code, erro),
                http=r.status_code,
                titulo=((r.metadata or {}).get('title') or '').strip(),
                markdown=texto,
                palavras=palavras(texto),
                erro=erro,
            )

        async def uma_e_mostra(url: str) -> None:
            await uma(url)
            _mostrar(capturas[url])

        await asyncio.gather(*(uma_e_mostra(u) for u in urls), return_exceptions=True)
    for u in urls:  # o que não voltou também precisa constar
        capturas.setdefault(u, _falhou(u, 'erro', 'sem resultado'))
    return capturas

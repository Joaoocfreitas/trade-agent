"""Abre o navegador de verdade (uns segundos) para provar que ele não se disfarça."""
import asyncio

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

from coletor.config import USER_AGENT
from coletor.paginas import configuracoes

PAGINA = 'raw:<html><body><p>teste</p></body></html>'


def test_navegador_se_mostra_automatizado_e_com_o_nome_do_robo():
    async def cenario():
        navegador, execucao = configuracoes()
        sonda = execucao.clone(js_code='return [navigator.webdriver, navigator.userAgent]', check_robots_txt=False)
        async with AsyncWebCrawler(config=navegador) as c:
            r = await c.arun(PAGINA, config=sonda)
        return r.js_execution_result

    resultado = asyncio.run(cenario())
    valores = resultado.get('results', [resultado])[0] if isinstance(resultado, dict) else resultado
    assert valores[0] is True  # navigator.webdriver visível: o site sabe que é robô
    assert valores[1] == USER_AGENT


def test_configuracao_nao_liga_nada_de_furtivo():
    navegador, execucao = configuracoes()
    assert navegador.enable_stealth is False
    assert not (execucao.magic or execucao.simulate_user or execucao.override_navigator or execucao.remove_overlay_elements)
    assert execucao.check_robots_txt is True
    assert isinstance(CrawlerRunConfig, type)

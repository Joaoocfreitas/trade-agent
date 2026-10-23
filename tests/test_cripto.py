"""Cripto sem preço (falta licença da cotação) e os dois lados do que já aconteceu, pedidos do João em 22 e 23/10/2026.

O bitcoin entra com regra, imposto, formas de ter, riscos e a linha do tempo, tudo com fonte conferida em 23/10/2026.
Quem pergunta se compra ou para onde vai recebe a recusa e, nos mercados com série licenciada, os dois lados (quando
caiu, quando subiu), sempre na mesma ordem e do mesmo tamanho, terminando em "a decisão é sua".
"""
import json
import re

import pytest

from agente import fatos as F
from agente import textos as T
from agente.filtro import frases_proibidas
from agente.resposta import montar
from agente.roteador import normalizar

CRIPTO = json.loads((F.AGENTE / 'cripto.json').read_text(encoding='utf-8'))


def test_toda_linha_de_cripto_tem_fonte_com_link():
    blocos = [CRIPTO['regras'], CRIPTO['imposto'], CRIPTO['riscos']]
    for b in blocos:
        for ln in b['linhas']:
            assert ln['fontes'] and all(f['url'].startswith('http') for f in ln['fontes']), ln['texto']
    for m in CRIPTO['marcos']:
        assert m['fontes'] and m['fontes'][0]['url'].startswith('http'), m


def test_cripto_nao_tem_preco_do_bitcoin():
    """Nenhuma fonte grátis permite uso comercial da cotação: nada de 'US$ 81 mil', volatilidade ou queda do pico."""
    texto = json.dumps(CRIPTO, ensure_ascii=False)
    assert not re.search(r'US\$ ?\d+[\d.,]* (mil|milhões)? ?(por|o) bitcoin|volatilidade|do pico', texto)


def test_bitcoin_vale_a_pena_recebe_recusa_e_tres_linhas_de_cripto():
    r = montar('quero comprar bitcoin hoje, vale a pena?', hoje='2026-10-23')
    assert r.violacoes == [], r.violacoes
    assert T.RECUSA in r.abertura
    assert r.curta[0].startswith('Bitcoin à vista, em regra, não é valor mobiliário')
    assert r.curta[1].startswith('Imposto:') and r.curta[2].startswith('Riscos:')


@pytest.mark.parametrize('pergunta, tema', [('o que aconteceu no halving?', 'halving'), ('e a FTX?', 'ftx'),
                                            ('ETF de bitcoin na B3', 'etf'), ('bitcoin e o Trump', 'trump'),
                                            ('stablecoin é câmbio?', 'stablecoin'), ('quero comprar bitcoin', '')])
def test_tema_da_linha_do_tempo(pergunta, tema):
    assert F.tema_cripto(normalizar(pergunta)) == tema
    r = montar(pergunta, hoje='2026-10-23')
    assert r.violacoes == [], r.violacoes
    if tema:
        assert r.curta[0].startswith('Na linha do tempo da cripto:')


def test_etf_na_b3_fala_de_cripto_e_nao_do_nivel_do_ibovespa():
    r = montar('ETF de bitcoin na B3', hoje='2026-10-23')
    assert not any(x.startswith('O Ibovespa está em') for x in r.curta)
    assert 'HASH11' in r.curta[0]  # sigla não vira "hASH11"


def test_curta_de_cripto_sempre_tem_o_d5():
    for q in ('o que aconteceu no halving?', 'e a FTX?', 'stablecoin é câmbio?', 'bitcoin e o Trump'):
        r = montar(q, hoje='2026-10-23')
        assert 'não é valor mobiliário' in r.texto_curto, q


@pytest.mark.parametrize('mercado', ['dolar', 'euro', 'juros', 'ibovespa'])
def test_dois_lados_mesma_ordem_mesmo_tamanho(mercado):
    b = F.dois_lados(mercado)
    textos = [ln.texto for ln in b.linhas]
    assert textos[0].startswith('Quando caiu:') and textos[1].startswith('Quando subiu:')
    # os dois lados com os mesmos espaços: um dia e cerca de um mês
    assert textos[0].count('(') == textos[1].count('(') and 'pregões seguidos' in textos[0] and 'pregões seguidos' in textos[1]
    assert textos[-1] == F.DECISAO_SUA and b.resumo.endswith(F.DECISAO_SUA)
    assert b.resumo.index('queda') < b.resumo.index('alta')
    for t in textos + [b.resumo]:
        assert frases_proibidas(t) == [], t


@pytest.mark.parametrize('pergunta', ['devo comprar dolar hoje?', 'o dólar vai cair?', 'compro ibovespa?', 'euro sobe?',
                                      'Vendo meus títulos prefixados agora?'])
def test_quem_pede_o_que_fazer_recebe_os_dois_lados(pergunta):
    r = montar(pergunta, hoje='2026-10-23')
    assert r.violacoes == [], r.violacoes
    assert any(x.startswith('Os dois lados nos últimos 12 meses') for x in r.curta), r.curta
    assert 'recomendo' not in r.texto.lower()


def test_pergunta_neutra_nao_recebe_os_dois_lados():
    r = montar('Como está o dólar?', hoje='2026-10-23')
    assert not any(b.titulo.startswith(F.TITULO_DOIS_LADOS) for b in r.blocos)


def test_contrato_continua_com_a_fgv_nas_tres_linhas():
    w = montar('WDO sobe amanhã?', hoje='2026-10-23')
    assert any('97%' in x for x in w.curta) and not any(b.titulo.startswith(F.TITULO_DOIS_LADOS) for b in w.blocos)

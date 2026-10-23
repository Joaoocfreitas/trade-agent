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
    assert r.curta[1].startswith('Imposto da cripto') and r.curta[2].startswith('Riscos:')


@pytest.mark.parametrize('pergunta, tema', [('o que aconteceu no halving?', 'halving'), ('e a FTX?', 'ftx'),
                                            ('ETF de bitcoin na B3', 'etf'), ('bitcoin e o Trump', 'trump'),
                                            ('stablecoin é câmbio?', 'stablecoin'), ('quero comprar bitcoin', '')])
def test_tema_da_linha_do_tempo(pergunta, tema):
    assert F.tema_cripto(normalizar(pergunta)) == tema
    r = montar(pergunta, hoje='2026-10-23')
    assert r.violacoes == [], r.violacoes
    if tema == 'ftx':  # a definição diz que era corretora e que o fundador foi acusado (L13 da rodada 2)
        assert r.curta[0].startswith('Corretora também quebra: a FTX')
    elif tema:
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


# ---------- achados da revisão de 23/10/2026 ----------

@pytest.mark.parametrize('pergunta', [
    'o trump vai fazer o bitcoin explodir?', 'com o trump o bitcoin decola?', 'o btc vai pra lua com o trump?',
    'bitcoin explode depois do halving?', 'o halving faz o bitcoin bombar?', 'bitcoin to the moon?', 'eth vai pumpar?',
    'xrp vai pra lua?', 'doge ou shiba, qual explode?', 'usdt ou dolar, qual o melhor?',
    'tiro meu btc da exchange e boto na carteira fria?', 'ibovespa vai a 250 mil?', 'bitcoin chega a 100 mil?',
])
def test_giria_e_alvo_de_preco_recebem_recusa(pergunta):
    r = montar(pergunta, hoje='2026-10-23')
    assert r.violacoes == [], r.violacoes
    assert T.RECUSA in r.texto, (pergunta, r.pedido.proibidos)
    if 'Na linha do tempo da cripto' in r.texto:
        assert r.texto.index(T.RECUSA) < r.texto.index('Na linha do tempo da cripto')


@pytest.mark.parametrize('pergunta', ['o que é pump and dump em cripto?', 'como o dólar reagiu depois do bombardeio no Irã?',
                                      'o que aconteceu com a FTX quando explodiu?'])
def test_conceito_e_passado_nao_viram_recusa(pergunta):
    assert 'direcao' not in montar(pergunta, hoje='2026-10-23').pedido.proibidos


@pytest.mark.parametrize('pergunta', ['Binance é segura?', 'a Binance é confiável?', 'essa corretora é segura?'])
def test_avaliar_corretora_pelo_nome_e_indicar(pergunta):
    r = montar(pergunta, hoje='2026-10-23')
    assert r.violacoes == [] and T.POR_PEDIDO['plataforma'] in r.abertura


def test_binance_e_hash11_alcancam_o_tema():
    assert F.tema_cripto(normalizar('Binance e o governo dos EUA')) == 'binance'
    assert F.tema_cripto(normalizar('o que é HASH11?')) == 'etf'
    assert F.tema_cripto(normalizar('a lei das stablecoins nos EUA')) == 'stablecoin'  # específico antes de "lei"
    assert F.tema_cripto(normalizar('que legal, quando surgiu o bitcoin?')) == ''


@pytest.mark.parametrize('pergunta, inicio', [('o que é halving?', 'Halving é o corte'),
                                              ('o que é stablecoin?', 'Stablecoin é cripto atrelada'),
                                              ('o que é ETF de bitcoin?', 'ETF de cripto é um fundo')])
def test_o_que_e_recebe_a_definicao_primeiro(pergunta, inicio):
    r = montar(pergunta, hoje='2026-10-23')
    assert r.violacoes == [] and r.curta[0].startswith(inicio) and 'não é valor mobiliário' in r.texto_curto


@pytest.mark.parametrize('pergunta', ['quanto tá o bitcoin hoje?', 'bitcoin caiu hoje?',
                                      'o que aconteceu com o bitcoin quando o Trump ganhou?'])
def test_pergunta_de_preco_ouve_que_nao_ha_cotacao(pergunta):
    r = montar(pergunta, hoje='2026-10-23')
    assert r.violacoes == [] and T.SEM_PRECO_CRIPTO in r.texto_curto


def test_pergunta_sem_preco_nao_recebe_a_linha_de_cotacao():
    for q in ('o que aconteceu no halving?', 'stablecoin é câmbio?'):
        # a frase também é limitação do bloco de riscos (texto inteiro); o que não pode é virar linha de topo
        assert T.SEM_PRECO_CRIPTO not in montar(q, hoje='2026-10-23').abertura


def test_imposto_e_declaracao_comecam_pelo_imposto():
    for q in ('como funciona o imposto do bitcoin?', 'preciso declarar bitcoin?'):
        assert montar(q, hoje='2026-10-23').curta[0].startswith('Imposto da cripto')


def test_etf_na_b3_paga_imposto_tem_a_ressalva_da_isencao():
    r = montar('ETF de bitcoin na B3 paga imposto?', hoje='2026-10-23')
    assert 'não vale para cota de fundo de índice' in r.texto and 'ainda não foi conferida' in r.texto
    assert not any(b.titulo.startswith('O Ibovespa até aqui') for b in r.blocos)


def test_futuro_de_bitcoin_traz_o_aviso_de_derivativo():
    for q in ('futuro de bitcoin na B3 vale a pena?', 'devo comprar bitcoin?'):
        r = montar(q, hoje='2026-10-23')
        assert r.violacoes == [] and 'passar do que você depositou' in r.texto_curto


def test_exchange_em_ingles_de_cambio_continua_no_cambio():
    r = montar('should I exchange my euros now?', hoje='2026-10-23')
    assert r.curta[0].startswith('O euro está em')


def test_dinheiro_em_cripto_nao_vira_conta_de_cambio():
    p = montar('tenho 10 mil dólares em USDT, quanto dá em reais?', hoje='2026-10-23').pedido
    assert not p.conta_cambio and 'capital' in p.proibidos


def test_dois_lados_de_cada_mercado_citado():
    r = montar('o dólar vai cair? e o ibovespa?', hoje='2026-10-23')
    lados = [b.titulo for b in r.blocos if b.titulo.startswith(F.TITULO_DOIS_LADOS)]
    assert len(lados) == 2


def test_fgv_fica_nas_tres_linhas_em_pergunta_de_cripto():
    r = montar('dá pra ficar rico com bitcoin?', hoje='2026-10-23')
    assert any('97%' in x for x in r.curta)


def test_halving_de_2024_no_horario_de_brasilia():
    assert any(m['data'] == '2024-04-19' for m in CRIPTO['marcos'])

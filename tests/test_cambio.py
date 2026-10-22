"""Câmbio, euro e a conta com os números da pessoa (P4 de câmbio), pedido do João em 22/10/2026.

A conta usa o dinheiro em moeda estrangeira e o gasto por mês que a pessoa contou só para fazer a conta: valor em reais
pela cotação oficial, quanto muda a cada R$ 0,10 e quantos meses de gasto cobre. Nunca diz o que fazer, quando trocar
nem quanto, e o registro não guarda o valor.
"""
import pandas as pd
import pytest

from agente import fatos as F
from agente import textos as T
from agente.filtro import frases_proibidas
from agente.registro import leitura_sem_voto, sem_dado_pessoal
from agente.resposta import montar
from agente.roteador import analisar, cambio, normalizar
from estudo.portao import conferir

PRINT = ('to com uns 150 mil euros na espanha aplicados e faco trasnferencia internacional pela wise todo o mes oara pagar '
         'minha facuyldade aqui no brasil mas agora com o crescimento da ibovespa e a reducao do poder do euro em relacao ao '
         'crecimento no valor do real to perdendo poder de compra.Queria saber se agora com o segundo turno o real vai '
         'continuar a valorizar ou nao? e se deveria trazer esse dinheiro para o brasil')


@pytest.mark.parametrize('pergunta, esperado', [
    ('tenho US$ 20 mil e pago 3 mil dólares por mês de aluguel', (20000, 'dolar', 3000, 'dolar')),
    ('Tenho €150.000 na Espanha e gasto 5 mil reais por mês com a faculdade.', (150000, 'euro', 5000, 'real')),
    ('to com uns 150 mil euros na espanha', (150000, 'euro', None, None)),
    ('tenho 150k euros', (150000, 'euro', None, None)),
    ('gasto 2 mil euros por mês', (None, None, 2000, 'euro')),  # o gasto não vira patrimônio
    ('mensalidade de R$ 4.500, tenho 1,2 milhão de euros', (1200000, 'euro', 4500, 'real')),
    ('EUR 80.000 parados no banco', (80000, 'euro', None, None)),
    ('tenho 50 mil em dólares e gasto R$ 3.000 por mês', (50000, 'dolar', 3000, 'real')),
    ('tenho R$ 10 mil, compro dólar?', (None, None, None, None)),  # real não é moeda estrangeira: segue a recusa (N5)
    ('o euro caiu 12% no ano', (None, None, None, None)),
    ('tenho 1,2,3 euros', (None, None, None, None)),
])
def test_le_o_dinheiro_e_o_gasto(pergunta, esperado):
    r = cambio(normalizar(pergunta))
    assert tuple(int(x) if isinstance(x, float) else x for x in r) == esperado


def test_o_print_do_site_vira_conta_e_recusa():
    p = analisar(PRINT)
    assert p.conta_cambio and p.valor_moeda == 150000 and p.moeda == 'euro'
    assert {'euro', 'dolar'} <= set(p.mercados) and p.eleicao
    assert 'dica' in p.proibidos and 'capital' not in p.proibidos
    r = montar(PRINT, hoje='2026-10-22')
    assert r.violacoes == [], r.violacoes
    assert T.RECUSA in r.abertura and T.POR_PEDIDO['capital'] not in r.abertura
    assert r.curta[0].startswith('Pela cotação oficial de 22/10/2026, seus 150.000 euros equivalem a R$ ')
    assert r.curta[1].startswith('Depois dos 2 segundos turnos desde 2018, o euro ')
    assert r.curta[2].startswith(F.SEM_FOCUS_EURO)
    assert 'não mostra o outro lado' in r.curta[1]


def test_quanto_trazer_e_alocacao_e_nao_vira_conta():
    p = analisar('tenho 150k euros, quanto eu trago pro brasil?')
    assert not p.conta_cambio and 'capital' in p.proibidos
    r = montar('tenho 150k euros, quanto eu trago pro brasil?', hoje='2026-10-22')
    assert not any(b.titulo == F.TITULO_CONTA_CAMBIO for b in r.blocos)
    assert '150.000' not in r.texto


C = {'data': '2026-10-22', 'valor': 5.6494, 'ano_data': '2025-12-31', 'ano_valor': 6.4692,
     'min_data': '2026-10-09', 'min_valor': 5.5844, 'max_data': '2025-12-29', 'max_valor': 6.5594}


def test_conta_com_gasto_em_reais():
    b = F.conta_cambio(150000, 'euro', 5000, 'real', c=C)
    textos = [ln.texto for ln in b.linhas]
    assert textos[0] == '150.000 euros × R$ 5,6494 (cotação oficial do euro em 22/10/2026) = R$ 847.410.'
    assert textos[1] == 'Cada R$ 0,10 de diferença na cotação do euro muda esse valor em R$ 15.000.'
    assert 'davam R$ 970.380, R$ 122.970 a mais do que hoje' in textos[2]
    assert 'dariam de R$ 837.660 a R$ 983.910' in textos[3]
    assert textos[4].startswith('Com gasto de R$ 5.000 por mês, R$ 847.410 cobrem 169 meses (14 anos e 1 mês)')
    assert 'seriam 167 meses (13 anos e 11 meses); na maior, 196 meses (16 anos e 4 meses)' in textos[4]
    assert textos[-1].startswith('É só a conta com os números que você contou: não diz o que fazer')
    assert b.resumo.endswith('com gasto de R$ 5.000 por mês, cobrem 169 meses (14 anos e 1 mês).')
    for t in textos + [b.resumo]:
        assert frases_proibidas(t) == [], t


def test_conta_com_gasto_na_propria_moeda_nao_usa_cotacao():
    b = F.conta_cambio(20000, 'dolar', 3000, 'dolar', c=C)
    assert any(ln.texto.startswith('Com gasto de 3.000 dólares por mês, os 20.000 dólares cobrem 6 meses') for ln in b.linhas)


@pytest.mark.parametrize('meses, texto', [(0.4, 'menos de 1 mês'), (1.9, '1 mês'), (23.9, '23 meses'),
                                          (24, '24 meses (2 anos)'), (35.9, '35 meses (2 anos e 11 meses)'),
                                          (169.48, '169 meses (14 anos e 1 mês)')])
def test_meses_nunca_arredonda_para_cima(meses, texto):
    assert F._meses(meses) == texto


def test_euro_nos_turnos_usa_o_metodo_do_estudo():
    """Com a PTAX do dólar, o mesmo cálculo reproduz a coluna ptax_d0 do estudo; então o do euro é comparável."""
    t = F._reacao_eleicoes('ptax')
    tab = F._csv('eleicoes_surpresa.csv').set_index('rodada')
    for _, r in t.iterrows():
        assert r.d0 == pytest.approx(tab.loc[r.rodada, 'ptax_d0'] * 100, abs=1e-3)
    b = F.euro_turnos()
    assert len([ln for ln in b.linhas if 'turno de' in ln.texto]) == len(t)
    assert any(ln.texto.startswith('Taxa-base do euro') for ln in b.linhas)


def test_registro_nao_guarda_o_dinheiro():
    p = analisar('Tenho €150.000 na Espanha e gasto 5 mil reais por mês com a faculdade.')
    leitura = leitura_sem_voto(p, p.pergunta)
    assert set(leitura) == {'mercados', 'candidatos', 'temas', 'proibidos'}
    limpo = sem_dado_pessoal(p.pergunta)
    assert '150' not in limpo and '5 mil' not in limpo


def test_linhas_curtas_sem_sigla_de_mercado():
    """As 3 linhas que o chat mostra primeiro, em linguagem de iniciante: sem p.p. nem p.b."""
    from agente.__main__ import BATERIA
    from agente.exportar import EXTRAS
    for q in [q for q, _ in BATERIA] + EXTRAS:
        for linha in montar(q, hoje='2026-10-22').curta:
            assert 'p.p.' not in linha and 'p.b.' not in linha, (q, linha)


def test_portao_do_euro_segura_o_dia_do_1o_turno():
    s = F.serie('euro')
    velha, nova = s[s.index <= '2026-10-02'], s[s.index <= '2026-10-05']
    motivos = conferir('euro', velha, nova, pd.Timestamp('2026-10-05'))
    assert any('salto' in m for m in motivos), motivos
    assert conferir('euro', velha, nova, pd.Timestamp('2026-10-05'), liberada=True) == []


@pytest.mark.parametrize('pergunta', [
    'tenho US$ 20 mil e pago 3 mil dólares por mês de aluguel', 'tenho 50 mil em dólares e gasto R$ 3.000 por mês. E a eleição?',
    'Tenho €150.000 na Espanha e gasto 5 mil reais por mês com a faculdade. Como está o euro?', PRINT,
    'tenho 0,5 euro', 'tenho 9.999.999.999 euros e gasto 1 real por mês',
])
def test_conta_de_cambio_passa_no_filtro(pergunta):
    """Em 22/10 toda conta em dólar caía no filtro (N2): "Cada R$ 0,10 que o dólar sobe ou desce" parecia previsão."""
    r = montar(pergunta, hoje='2026-10-22')
    assert r.pedido.conta_cambio
    assert r.violacoes == [], r.violacoes


def test_quantia_quebrada_mantem_os_centavos():
    assert F.conta_cambio(0.5, 'euro', c=C).resumo.startswith('Pela cotação oficial de 22/10/2026, seus 0,50 euros equivalem a R$ 2,82')


def test_euro_e_sujeito_de_frase_de_direcao():
    assert frases_proibidas('O euro vai subir depois da eleição.')
    assert frases_proibidas('o euro sobe com o Flávio')


def test_registro_nao_guarda_a_resposta_com_a_conta(tmp_path):
    from agente.registro import registrar
    r = montar('Tenho €150.000 na Espanha e gasto 5 mil reais por mês com a faculdade.', hoje='2026-10-22')
    linha = registrar(r, arquivo=tmp_path / 'conversas.jsonl')
    guardado = (tmp_path / 'conversas.jsonl').read_text(encoding='utf-8')
    assert linha['resposta'] is None
    assert '150.000' not in guardado and '847' not in guardado and '5 mil' not in guardado


# ---------- achados da revisão de 22/10/2026 ----------

MOMENTO_OU_QUANTO = [
    'tenho 120 mil euros e a cada 0,10 eu perco 12 mil, quando eu troco pra não perder?', 'tenho 80 mil euros. troco hoje?',
    'tenho 150 mil euros, trago tudo?', 'remessa pra fora ta cara? mando agora?', 'tengo 40 mil euros, cuando cambio a reales?',
    'Tengo 100.000 euros, ¿conviene traerlos a Brasil ahora?', 'tenho 100 mil dólares, troco agora ou depois do Copom?',
    'tenho 150 mil euros, trago metade agora e metade depois do segundo turno?',
    'tenho 150 mil euros, quanto desse dinheiro eu trago?', 'devo trazer tudo ou metade?',
    'how much of my 100k eur should I convert', '2 milhoes de euros, quanto disso eu trago?',
    'tenho 150 mil euros, qual o melhor momento pra trocar?', 'Tenho 150 mil euros, qual fatia eu passo pro real?',
]


@pytest.mark.parametrize('pergunta', MOMENTO_OU_QUANTO)
def test_quando_ou_quanto_mover_recebe_recusa_e_nao_usa_o_valor(pergunta):
    r = montar(pergunta, hoje='2026-10-22')
    assert r.violacoes == [], r.violacoes
    assert T.RECUSA in r.abertura or T.POR_PEDIDO['capital'] in r.abertura
    assert not r.pedido.conta_cambio
    assert not any(b.titulo == F.TITULO_CONTA_CAMBIO for b in r.blocos)


@pytest.mark.parametrize('pergunta', ['tenho 80 mil euros. troco hoje?', 'tengo 40 mil euros, cuando cambio a reales?',
                                      'tenho 150 mil euros, qual o melhor momento pra trocar?'])
def test_quando_mover_e_momento(pergunta):
    assert T.POR_PEDIDO['momento'] in montar(pergunta, hoje='2026-10-22').abertura


@pytest.mark.parametrize('pergunta', ['O que é câmbio?', 'Como funciona o câmbio?', 'Como o câmbio reagiu ao Copom?',
                                      'O mandato do Lula e o dólar', 'O que a eleição traz para o dólar?',
                                      'como o euro reagiu depois do segundo turno de 2022?', 'como mando dinheiro pra fora?',
                                      'Me explica passo a passo o Copom'])
def test_pergunta_neutra_de_cambio_nao_vira_recusa(pergunta):
    assert T.RECUSA not in montar(pergunta, hoje='2026-10-22').abertura


@pytest.mark.parametrize('pergunta, esperado', [
    ('quero converter R$ 100 mil em euros, quanto dá?', (None, None)),  # real não vira euro
    ('tenho R$ 50 mil em dólares, como está o dólar?', (None, None)),
    ('O que aconteceu com o euro 2 dias depois do 1º turno?', (None, None)),  # número colado na moeda
    ('tenho 50,000 euros', (50000, 'euro')), ('tenho 1.5 milhão de euros', (1500000, 'euro')),
    ('tenho 150.000. euros', (150000, 'euro')),
])
def test_formatos_de_numero(pergunta, esperado):
    v, m, _, _ = cambio(normalizar(pergunta))
    assert (int(v) if v else v, m) == esperado


def test_renda_nao_e_gasto_e_contrato_nao_e_dinheiro():
    assert cambio(normalizar('tenho 20 mil euros rendendo 1% ao mês'))[2] is None
    assert cambio(normalizar('ganho 10 mil por mês e tenho 20 mil euros'))[2] is None
    assert not analisar('tenho 3 contratos de 10 mil dólares no mini dólar, 5.400 pontos').conta_cambio
    assert cambio(normalizar('I have 50,000 euros and spend 2,000 euros a month')) == (50000, 'euro', 2000, 'euro')


def test_gasto_em_outra_moeda_estrangeira_vira_real_pela_cotacao_dela():
    b = F.conta_cambio(100000, 'euro', 2000, 'dolar', c=C, cg={**C, 'valor': 5.0383})
    linha = next(ln.texto for ln in b.linhas if ln.texto.startswith('Com gasto'))
    assert linha.startswith('Com gasto de 2.000 dólares por mês (R$ 10.077 pela cotação oficial do dólar em 22/10/2026), '
                            'R$ 564.940 cobrem 56 meses (4 anos e 8 meses)')


def test_ia_que_ve_capital_tira_a_conta():
    """Modo com IA: se a IA marcou 'capital', vale a leitura dela e a conta sai (nada de "não uso o valor" seguido dele)."""
    from agente.roteador import Pedido
    p = analisar('Tenho €150.000 na Espanha e gasto 5 mil reais por mês com a faculdade. Como está o euro?')
    assert p.conta_cambio
    junto = p.somar(Pedido(p.pergunta, proibidos=['capital']))
    assert not junto.conta_cambio and 'capital' in junto.proibidos
    r = montar(p.pergunta, junto, hoje='2026-10-22')
    assert '150.000' not in r.texto and T.POR_PEDIDO['capital'] in r.abertura


@pytest.mark.parametrize('frase', ['EUR 80.000 parados no banco', 'tenho 80.000€ na conta', 'USD 20.000 guardados',
                                   'tenho 20 mil USD', 'mensalidade de 4500'])
def test_registro_apaga_todo_formato_de_dinheiro(frase):
    limpo = sem_dado_pessoal(frase)
    assert not any(n in limpo for n in ('80.000', '20.000', '20 mil', '4500')), limpo


@pytest.mark.parametrize('valor', [5.6450, 5.6350, 5.0150, 5.0250, 5.6349])
def test_resumo_arredonda_como_o_filtro(valor):
    """O resumo arredonda a partir do número escrito na linha, meio para o par, como o D8: nunca cai na resposta de
    segurança por causa do dado do dia."""
    from decimal import Decimal, ROUND_HALF_EVEN
    esperado = Decimal(f'{valor:.4f}').quantize(Decimal('0.01'), ROUND_HALF_EVEN)
    assert F.curto(valor, 4, 2) == float(esperado)
    assert F.curto(-12.65, 2, 1) == -12.6 and F.curto(12.75, 2, 1) == 12.8


def test_renda_fixa_nao_recebe_aviso_de_derivativo_e_di_futuro_recebe():
    assert T.RISCO_DERIVATIVO not in montar('vale a pena renda fixa agora?', hoje='2026-10-22').texto
    assert T.RISCO_DERIVATIVO in montar('O DI futuro sobe no Copom?', hoje='2026-10-22').texto


def test_pergunta_de_euro_comeca_pelo_euro_e_avisa_que_o_focus_nao_tem_euro():
    r = montar('quanto tá o euro hoje?', hoje='2026-10-22')
    assert r.curta[0].startswith('O euro está em R$ ')
    assert r.curta[1].startswith(F.SEM_FOCUS_EURO)
    r = montar('Como estão o euro e a bolsa?', hoje='2026-10-22')
    assert not any('Selic' in linha and 'esperam' in linha for linha in r.curta)


def test_euro_no_copom_diz_que_o_estudo_mede_o_dolar():
    r = montar('euro e Copom: o que acontece com o euro quando o Copom surpreende?', hoje='2026-10-22')
    assert F.EURO_SEM_ESTUDO in r.texto


def test_o_real_sem_verbo_de_valorizar_e_cambio():
    assert 'dolar' in analisar('como o real reagiu à eleição?').mercados
    assert 'dolar' in analisar('como o real reage ao copom?').mercados

import math

import numpy as np
import pandas as pd
import pytest

from estudo.agregados import analisar_copom, caminho_medio, depois_do_dia_zero, permutacao
from estudo.janelas import calendario, comportamento, dia_zero, medir_preco, medir_taxa, no_calendario
from estudo.series import curva_constante, ler_ipeadata, ler_sgs, ler_tesouro, limpar_ibov
from estudo.surpresa import decisao, expectativa_na_vespera, reunioes, url_focus_reuniao
from estudo.__main__ import medir_eventos


def test_le_sgs_e_ipeadata():
    s = ler_sgs([{'data': '02/10/2026', 'valor': '5.2238'}, {'data': '01/10/2026', 'valor': '5.2079'}, {'data': '03/10/2026', 'valor': ''}])
    assert list(s.index.strftime('%Y-%m-%d')) == ['2026-10-01', '2026-10-02'] and s.iloc[1] == 5.2238
    i = ler_ipeadata([{'VALDATA': '2026-10-05T00:00:00-03:00', 'VALVALOR': 206912.0}, {'VALDATA': '2026-10-06T00:00:00-03:00', 'VALVALOR': None}])
    assert i.to_dict() == {pd.Timestamp('2026-10-05'): 206912.0}


CSV_TD = ('Tipo Titulo;Data Vencimento;Data Base;Taxa Compra Manha;Taxa Venda Manha;PU Compra Manha;PU Venda Manha;PU Base Manha\n'
          'Tesouro Prefixado;01/01/2028;02/10/2026;13,10;13,22;800,00;799,00;799,50\n'
          'Tesouro Prefixado com Juros Semestrais;01/01/2031;02/10/2026;13,50;13,62;900,00;899,00;899,50\n'
          'Tesouro IPCA+;15/05/2035;02/10/2026;7,10;7,22;2000,00;1999,00;1999,50\n'
          'Tesouro Prefixado;01/01/2027;02/10/2026;0,00;0,00;0;0;0\n').encode('latin-1')


def test_le_tesouro_so_prefixados_com_taxa():
    df = ler_tesouro(CSV_TD)
    assert list(df['taxa']) == [13.10, 13.50]
    assert list(df['vencimento'].dt.year) == [2028, 2031]


def test_curva_a_prazo_constante_interpola_e_nao_extrapola():
    dia = pd.Timestamp('2026-01-01')
    pre = pd.DataFrame({'data': [dia, dia], 'vencimento': [dia + pd.DateOffset(days=365), dia + pd.DateOffset(days=1096)],
                        'taxa': [10.0, 12.0]})
    assert curva_constante(pre, 2).iloc[0] == pytest.approx(11.0, abs=0.01)
    assert curva_constante(pre, 3.5).iloc[0] == 12.0  # só há título abaixo, mas a 0,5 ano: vale o mais próximo
    assert curva_constante(pre, 5).empty  # a 2 anos de distância: não inventa


def test_dia_zero_e_calendario():
    cal = pd.DatetimeIndex(pd.bdate_range('2026-10-01', '2026-10-09'))
    assert cal[dia_zero('2026-10-04', cal)] == pd.Timestamp('2026-10-05')  # domingo de eleição reage na segunda
    assert dia_zero('2027-01-01', cal) is None
    ptax = pd.Series([5.0, 5.1], index=pd.to_datetime(['2026-10-01', '2026-10-02']))
    alinhada = no_calendario(ptax, cal, limite_dias=4)
    assert alinhada['2026-10-05'] == 5.1  # último valor conhecido
    assert math.isnan(alinhada['2026-10-09'])  # buraco de 7 dias: não inventa


def _precos(n=300, i0=280, salto=0.05):
    rets = np.array([0.01 if k % 2 else -0.01 for k in range(n)])  # desvio-padrão conhecido (~0,01)
    p = 100 * np.cumprod(1 + rets)
    p[i0:] *= 1 + salto
    return pd.Series(p, index=pd.bdate_range('2025-01-01', periods=n))


def test_medir_preco_dia_zero_janela_e_z():
    s = _precos()
    r = medir_preco(s, 280)
    esperado_d0 = (1 + 0.05) * (1 + (0.01 if 280 % 2 else -0.01)) - 1
    assert r['d0'] == pytest.approx(esperado_d0)
    assert r['sigma'] == pytest.approx(1.4826 * 0.01, rel=0.02)  # desvio robusto (MAD) de ±1%
    assert r['z0'] == pytest.approx(esperado_d0 / r['sigma'])
    assert r['z0_simples'] == pytest.approx(esperado_d0 / 0.01, rel=0.02)
    assert len(r['caminho']) == 11 and r['caminho'][4] == 0.0  # dia −1 contra ele mesmo
    assert medir_preco(s, 3) == {}  # sem os 5 pregões anteriores


def test_crash_na_janela_nao_derruba_o_z_robusto_e_outro_evento_fica_de_fora():
    s = _precos(n=300, i0=280)
    v = s.to_numpy().copy()
    v[100:] *= 0.85  # um crash de −15% num dia da janela de estimação
    s_crash = pd.Series(v, index=s.index)
    limpo, com_crash = medir_preco(s, 280), medir_preco(s_crash, 280)
    assert com_crash['z0'] == pytest.approx(limpo['z0'], rel=0.05)  # robusto: quase não muda
    assert abs(com_crash['z0_simples']) < 0.8 * abs(limpo['z0_simples'])  # o simples encolhe
    sem_o_dia = medir_preco(s_crash, 280, excluir=frozenset({100, 101}))
    assert sem_o_dia['z0_simples'] == pytest.approx(limpo['z0_simples'], rel=0.05)


def test_limpar_ibov_tira_fim_de_semana_e_valor_quebrado():
    s = pd.Series([112245.0, 101005.64, 111996.0, 111910.1, 112000.0],
                  index=pd.to_datetime(['2022-02-04', '2022-02-05', '2022-02-07', '2022-02-28', '2022-03-02']))
    limpo, falsos = limpar_ibov(s)
    assert list(limpo.index.strftime('%m-%d')) == ['02-04', '02-07', '03-02']
    assert falsos == ['2022-02-05=101005.64', '2022-02-28=111910.1']
    with pytest.raises(ValueError):
        calendario(s)  # com sábado no meio, o calendário se recusa


def test_medir_taxa_em_pontos_base():
    s = pd.Series([13.0] * 6 + [13.2, 13.5] + [13.4] * 5)
    r = medir_taxa(s, 6)
    assert r['d0_pb'] == pytest.approx(20) and r['d01_pb'] == pytest.approx(50) and r['nivel'] == 13.0


def test_comportamento_depois_do_dia_zero():
    assert comportamento(0.05, 0.0, 0.03)['leitura_depois'] == 'continuou'
    assert comportamento(0.05, 0.0, -0.06)['leitura_depois'] == 'devolveu tudo ou mais'
    assert comportamento(0.05, 0.0, -0.02)['leitura_depois'] == 'devolveu parte'
    assert comportamento(-0.05, -0.04, 0.0)['antecipou'] is True


def test_permutacao_separa_sinal_de_sorte():
    alto = np.array([3.0, 3.5, 4.0, 2.8, 3.2, 3.9])
    baixo = np.array([0.5, 0.8, 0.3, 0.9, 0.6, 0.4])
    assert permutacao(alto, baixo) < 0.01
    assert permutacao(baixo, baixo.copy()) > 0.3


def test_caminho_medio_vira_o_sinal_da_queda():
    ev = pd.DataFrame({'surpresa': ['alta', 'alta'], 'ibov_d0': [0.05, -0.05],
                       'ibov_caminho': [[0.0] * 5 + [0.05] * 6, [0.0] * 5 + [-0.05] * 6]})
    assert caminho_medio(ev, {'alta': ['alta']})['alta'][5] == pytest.approx(0.05)


def test_depois_do_dia_zero_mostra_incerteza_e_o_evento_que_mais_pesa():
    caminhos = [[0.0] * 5 + [0.05, 0.05, 0.05, 0.05, 0.05, 0.05 * (1 + k * 0.001)] for k in range(-5, 5)]
    caminhos.append([0.0] * 5 + [0.10] * 5 + [0.10 * 0 - 0.08])  # um caso extremo que devolve tudo e mais
    ev = pd.DataFrame({'surpresa': ['alta'] * 11, 'ibov_d0': [0.05] * 10 + [0.10], 'ibov_caminho': caminhos,
                       'evento': [f'e{i}' for i in range(11)]})
    r = depois_do_dia_zero(ev, ['alta'])
    assert r['n'] == 11 and r['ic95'][0] < r['media'] < r['ic95'][1]
    assert r['evento_que_mais_pesa'] == 'e10'
    assert abs(r['media_sem_ele']) < abs(r['media'])
    assert abs(r['mediana']) < 0.001  # a mediana não se deixa levar pelo caso extremo


def test_focus_pega_a_ultima_pesquisa_antes_da_decisao_e_a_reuniao_mais_proxima():
    regs = [
        {'Data': '2024-12-06', 'Reuniao': 'R8/2024', 'Mediana': 12.0, 'DesvioPadrao': 0.2, 'numeroRespondentes': 90, 'baseCalculo': 1},
        {'Data': '2024-12-10', 'Reuniao': 'R1/2025', 'Mediana': 12.75, 'DesvioPadrao': 0.3, 'numeroRespondentes': 90, 'baseCalculo': 1},
        {'Data': '2024-12-10', 'Reuniao': 'R8/2024', 'Mediana': 12.25, 'DesvioPadrao': 0.1, 'numeroRespondentes': 95, 'baseCalculo': 1},
        {'Data': '2024-12-10', 'Reuniao': 'R8/2024', 'Mediana': 12.0, 'DesvioPadrao': 0.1, 'numeroRespondentes': 120, 'baseCalculo': 0},
        {'Data': '2024-12-11', 'Reuniao': 'R8/2024', 'Mediana': 12.25, 'DesvioPadrao': 0.1, 'numeroRespondentes': 9, 'baseCalculo': 1},
    ]
    e = expectativa_na_vespera(regs, pd.Timestamp('2024-12-11'))
    assert (e['reuniao'], e['pesquisa_em'], e['mediana'], e['base']) == ('R8/2024', '2024-12-10', 12.25, 'últimos 5 dias úteis')
    selic = pd.Series([11.25] * 3 + [12.25] * 3, index=pd.date_range('2024-12-09', periods=6))
    assert decisao(selic, pd.Timestamp('2024-12-11')) == (11.25, 12.25)


def test_reunioes_do_copom_ganham_o_codigo_do_focus_na_ordem_do_ano():
    conteudo = [{'nro_reuniao': n, 'dataReferencia': d, 'titulo': f'{n}ª'} for n, d in
                [(197, '2016-03-02'), (196, '2016-01-20'), (195, '2015-11-25'), (204, '2017-01-11'), (196, '2016-01-20')]]
    df = reunioes(conteudo, '2016-01-01')
    assert list(df['reuniao']) == ['R1/2016', 'R2/2016', 'R1/2017']  # ordena, tira duplicata e corta antes de 2016
    url = url_focus_reuniao('R3/2018', pd.Timestamp('2018-05-16'))
    assert "Reuniao%20eq%20'R3/2018'%20and%20Data%20lt%20'2018-05-16'" in url and 'orderby=Data%20desc' in url


def _copom_sintetico(extremo: bool):
    rng = np.random.default_rng(1)
    surpresa = np.array([0] * 30 + [25] * 6 + [-25] * 6 + [50] * 2, float)
    juros = 0.8 * surpresa + rng.normal(0, 3, surpresa.size)
    if extremo:
        surpresa, juros = np.append(surpresa, -25.0), np.append(juros, 140.0)  # o "março de 2020": contra tudo
    n = surpresa.size
    return pd.DataFrame({'reuniao': [f'R{i}' for i in range(n)], 'decisao': ['2020-01-01'] * n, 'surpresa_pb': surpresa,
                         'surpresa_continua_pb': surpresa * 0.9, 'pre2_d0_pb': juros, 'ibov_d0': -surpresa / 2000,
                         'focus_base': ['últimos 5 dias úteis'] * (n // 2) + ['últimos 30 dias'] * (n - n // 2),
                         'dividida': [False] * n})


def test_analisar_copom_acha_a_inclinacao_e_separa_com_e_sem_surpresa():
    r = analisar_copom(_copom_sintetico(extremo=False), n_boot=300)
    todas = r['versoes']['todas']
    assert (todas['com_surpresa'], todas['sem_surpresa']) == (14, 30)
    assert todas['ic95'][0] < 0.8 < todas['ic95'][1]
    assert todas['na_direcao_da_surpresa'] == '14 de 14'
    assert todas['juros2a_mediana_abs_com_pb'] > todas['juros2a_mediana_abs_sem_pb']
    assert todas['spearman_surpresa_x_ibov'] < 0
    assert set(r['versoes']) == {'todas', 'sem_a_que_mais_pesa', 'so_focus_fresco_desde_mar2021', 'surpresa_continua_pela_media'}


def test_theil_sen_e_a_versao_sem_o_extremo_nao_se_deixam_levar_por_um_ponto():
    r = analisar_copom(_copom_sintetico(extremo=True), n_boot=300)
    assert r['reuniao_que_mais_pesa'].startswith('R44')  # o ponto extremo é achado
    assert r['versoes']['todas']['inclinacao_pb_por_pb'] == pytest.approx(0.8, abs=0.15)  # Theil-Sen ignora o extremo
    assert r['versoes']['sem_a_que_mais_pesa']['n'] == 44


def test_sensibilidade_marca_surpresa_que_vira_de_sinal_com_a_janela():
    from estudo.eleicoes import sensibilidade_janela
    pesq = lambda inst, fim, a, b: {'instituto': inst, 'campo_fim': fim, 'a_validos_pct': a, 'b_validos_pct': b, 'verificado': 'confirmado'}
    rodada = {'resultado_tse': {'a_validos_pct': 55.0, 'b_validos_pct': 45.0, 'fonte_url': 'x'}, 'pesquisas': [
        pesq('Antiga', '2018-10-21', 60.0, 40.0),  # só entra na janela de 7 dias e puxa a margem para cima
        pesq('Véspera', '2018-10-27', 54.0, 46.0),
    ]}
    s = sensibilidade_janela(rodada, '2018-10-28')
    assert s['7_dias']['media'] < 0 < s['3_dias']['media']
    assert s['sinal_estavel'] is False


def test_medir_copom_usa_o_pregao_seguinte_a_decisao():
    from estudo.__main__ import medir_copom
    ibov = _precos(n=300, i0=281)  # o salto entra no pregão seguinte à decisão (posição 280)
    decisao_dia = ibov.index[280]
    taxa = pd.Series([13.0] * 281 + [13.3] * 19, index=ibov.index)
    selic = pd.Series([13.0] * 282 + [13.25] * 18, index=ibov.index)
    focus = {'R5/2026': {'nro': 280, 'decisao': str(decisao_dia.date()), 'registros': [
        {'Data': str((decisao_dia - pd.offsets.BDay(1)).date()), 'Reuniao': 'R5/2026', 'Mediana': 13.0, 'DesvioPadrao': 0.1,
         'numeroRespondentes': 100, 'baseCalculo': 0}]}}
    df = medir_copom(focus, ibov, pd.Series(5.0, index=ibov.index), taxa, taxa, selic)
    linha = df.iloc[0]
    assert linha['dia0'] == str(ibov.index[281].date())
    assert (linha['mudanca_pb'], linha['surpresa_pb']) == (25, 25)
    assert linha['pre2_d0_pb'] == pytest.approx(30)
    assert linha['ibov_d0'] > 0.04


def test_surpresa_eleitoral_usa_validos_publicados_ou_calculados_e_ignora_nao_confirmado():
    from estudo.eleicoes import surpresa_eleitoral
    rodada = {'resultado_tse': {'a_validos_pct': 47.03, 'b_validos_pct': 45.16, 'fonte_url': 'x'}, 'pesquisas': [
        {'instituto': 'D', 'a_validos_pct': 42.0, 'b_validos_pct': 45.0, 'verificado': 'confirmado'},
        {'instituto': 'Q', 'a_validos_pct': None, 'b_validos_pct': None, 'a_total_pct': 40.0, 'b_total_pct': 40.0,
         'brancos_nulos_indecisos_pct': 20.0, 'verificado': 'corrigido'},  # válidos calculados: 50 x 50
        {'instituto': 'X', 'a_validos_pct': 60.0, 'b_validos_pct': 30.0, 'verificado': 'nao_confirmado'},  # fica de fora
    ]}
    s = surpresa_eleitoral(rodada)
    assert s['institutos'] == ['D', 'Q'] and s['n_pesquisas'] == 2
    assert s['margem_pesquisas_media_pp'] == pytest.approx(-1.5)  # (−3 + 0) / 2
    assert s['surpresa_pp'] == pytest.approx(1.87 + 1.5)
    assert s['pesquisas_que_erraram_o_vencedor'] == 1
    # a janela é aplicada pelo código: campo terminado 8 dias antes fica de fora
    rodada['pesquisas'][0]['campo_fim'] = '2026-09-26'
    rodada['pesquisas'][1]['campo_fim'] = '2026-10-03'
    assert surpresa_eleitoral(rodada, '2026-10-04')['institutos'] == ['Q']


def test_p_valor_minimo_nao_aparece_como_zero():
    from estudo.__main__ import _p
    assert _p(1 / 20001) == '< 0.00005'
    assert _p(0.0312) == '0.0312'


def test_medir_eventos_alinha_data_e_avisa_divergencia_da_linha_do_tempo():
    ibov = _precos(n=300, i0=280)
    data_evento = ibov.index[280]
    ptax = pd.Series(5.0, index=ibov.index)
    taxa = pd.Series(13.0, index=ibov.index)
    evento = {'data': str(data_evento.date()), 'evento': 'X', 'tipo': 'eleicao', 'surpresa': 'alta', 'confianca': 'alta',
              'ibov_dia_pct': 1.0, 'dolar_dia_pct': None}
    df = medir_eventos([evento], ibov, ptax, taxa, taxa, taxa)
    assert df.loc[0, 'dia0'] == str(data_evento.date())
    assert 'linha do tempo +1.00%' in df.loc[0, 'alerta']  # medido ~+6% x anotado +1%
    sexta = next(d for d in ibov.index[200:290] if d.weekday() == 4)
    sabado = {**evento, 'data': str((sexta + pd.DateOffset(days=1)).date()), 'ibov_dia_pct': None}
    df_sab = medir_eventos([sabado], ibov, ptax, taxa, taxa, taxa)
    assert pd.Timestamp(df_sab.loc[0, 'dia0']).weekday() == 0  # reage na segunda
    assert 'não é pregão' in df_sab.loc[0, 'alerta']

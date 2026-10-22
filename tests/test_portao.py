"""O portão da rodada diária (estudo/portao.py): na dúvida, fica a série de ontem."""
import json

import pandas as pd
import pytest

from estudo.portao import aplicar, conferir, conferir_focus

HOJE = pd.Timestamp('2026-10-22')


def serie(valores: dict) -> pd.Series:
    return pd.Series(list(valores.values()), dtype=float, index=pd.to_datetime(list(valores))).sort_index()


BASE_PTAX = {'2026-10-15': 5.10, '2026-10-16': 5.08, '2026-10-19': 5.05, '2026-10-20': 5.014}


def test_ponto_novo_normal_entra():
    assert conferir('ptax', serie(BASE_PTAX), serie({**BASE_PTAX, '2026-10-21': 5.0277}), HOJE) == []


@pytest.mark.parametrize('novo,trecho', [
    ({'2026-10-21': 5.40}, 'salto'),                      # +7,7% num dia
    ({'2026-10-21': 50.277}, 'faixa'),                    # vírgula no lugar errado
    ({'2026-10-23': 5.03}, 'futuro'),
    ({'2026-10-21': float('nan')}, 'não é número'),
])
def test_ponto_novo_estranho_segura(novo, trecho):
    m = conferir('ptax', serie(BASE_PTAX), serie({**BASE_PTAX, **novo}), HOJE)
    assert m and any(trecho in x for x in m), m


def test_historico_aceito_nao_muda_e_serie_nao_encolhe():
    velha = serie({f'2026-09-{d:02d}': 5.0 + d / 100 for d in range(1, 29)})
    mexida = velha.copy()
    mexida.iloc[0] = 4.0
    assert any('histórico' in x for x in conferir('ptax', velha, mexida, HOJE))
    assert any('encolheu' in x for x in conferir('ptax', velha, velha.iloc[:-3], HOJE))


def test_selic_multiplo_de_025_e_ibov_inteiro_em_dia_util():
    selic = serie({'2026-10-20': 13.75, '2026-10-21': 13.75})
    assert any('múltiplo' in x for x in conferir('selic_meta', selic, serie({'2026-10-20': 13.75, '2026-10-21': 13.75,
                                                                                '2026-10-22': 13.80}), HOJE))
    ibov = serie({'2026-10-19': 205079.0, '2026-10-20': 208296.0})
    assert any('centavos' in x for x in conferir('ibov', ibov, serie({'2026-10-19': 205079.0, '2026-10-20': 208296.0,
                                                                      '2026-10-21': 208000.875}), HOJE))
    sexta = serie({'2026-10-15': 205000.0, '2026-10-16': 206000.0})
    assert any('fim de semana' in x for x in conferir('ibov', sexta, serie({'2026-10-15': 205000.0, '2026-10-16': 206000.0,
                                                                            '2026-10-17': 206500.0}), HOJE))


def test_liberada_aceita_o_salto_mas_nao_o_resto():
    nova = serie({**BASE_PTAX, '2026-10-21': 5.40})
    assert conferir('ptax', serie(BASE_PTAX), nova, HOJE, liberada=True) == []
    assert conferir('ptax', serie(BASE_PTAX), serie({**BASE_PTAX, '2026-10-21': 50.0}), HOJE, liberada=True)


def _csv(pasta, nome, s):
    s.rename(nome).to_csv(pasta / f'{nome}.csv', index_label='data')


def test_aplicar_devolve_a_de_ontem_e_respeita_o_interruptor(tmp_path):
    antes, agora = tmp_path / 'antes', tmp_path / 'agora'
    antes.mkdir()
    agora.mkdir()
    _csv(antes, 'ptax', serie(BASE_PTAX))
    _csv(agora, 'ptax', serie({**BASE_PTAX, '2026-10-21': 9.0}))  # salto absurdo
    _csv(antes, 'ibov', serie({'2026-10-19': 205079.0, '2026-10-20': 208296.0}))
    _csv(agora, 'ibov', serie({'2026-10-19': 205079.0, '2026-10-20': 208296.0, '2026-10-21': 209000.0}))
    _csv(antes, 'selic_meta', serie({'2026-10-20': 13.75}))
    _csv(agora, 'selic_meta', serie({'2026-10-20': 13.75, '2026-10-21': 13.75}))
    r = {x.nome: x for x in aplicar(agora, antes, {'ibov': False}, HOJE)}
    assert r['ptax'].situacao == 'segurada' and (agora / 'ptax.csv').read_bytes() == (antes / 'ptax.csv').read_bytes()
    assert r['ibov'].situacao == 'desligada' and (agora / 'ibov.csv').read_bytes() == (antes / 'ibov.csv').read_bytes()
    assert r['selic_meta'].situacao == 'atualizada'


def test_focus_nao_volta_no_tempo_e_fica_em_faixa():
    velho = {'data': '2026-10-16', 'atual': {}, 'historico': {'2025': {}}}
    bom = {'data': '2026-10-23', 'atual': {'Câmbio|2026': {'mediana': 5.1, 'respondentes': 100}}, 'historico': {'2025': {}}}
    assert conferir_focus(velho, bom) == []
    assert conferir_focus(velho, {**bom, 'data': '2026-10-09'})
    assert conferir_focus(velho, {**bom, 'atual': {'Câmbio|2026': {'mediana': 51.0, 'respondentes': 100}}})
    assert json.dumps(conferir_focus(velho, {**bom, 'historico': {}}), ensure_ascii=False).count('histórico') == 1

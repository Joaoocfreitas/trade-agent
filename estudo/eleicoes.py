"""Surpresa eleitoral EX ANTE: margem oficial do TSE entre os dois primeiros menos a margem média das últimas pesquisas.

Regra (fixada antes de CALCULAR a surpresa, mas com a reação do mercado nesses turnos já conhecida; por isso a
sensibilidade à janela das pesquisas é publicada junto, em `sensibilidade_janela`):
- para cada instituto com registro no TSE, a última pesquisa nacional com campo terminado entre 7 dias antes da
  eleição e a véspera; boca de urna não conta;
- votos válidos publicados pelo instituto; se ele só publicou o total, válidos = total / (100 − brancos, nulos e
  indecisos) × 100;
- margem = candidato A − candidato B, em pontos de votos válidos; surpresa = margem do TSE − média das pesquisas
  (positivo = A teve mais votos do que as pesquisas indicavam).
Os números das pesquisas foram levantados e conferidos por agentes com fonte de cada um (dados/fontes/pesquisas_eleicoes.json).
"""
import math
import statistics
from datetime import date, timedelta

# rodada -> data do pregão da reação (a segunda-feira depois da eleição) na linha do tempo
RODADA_PARA_EVENTO = {'2018-1': '2018-10-08', '2018-2': '2018-10-29', '2022-1': '2022-10-03',
                      '2022-2': '2022-10-31', '2026-1': '2026-10-05'}


def validos(p: dict) -> tuple[float, float] | None:
    if p.get('a_validos_pct') is not None and p.get('b_validos_pct') is not None:
        return float(p['a_validos_pct']), float(p['b_validos_pct'])
    if None not in (p.get('a_total_pct'), p.get('b_total_pct'), p.get('brancos_nulos_indecisos_pct')):
        base = 100 - float(p['brancos_nulos_indecisos_pct'])
        if base > 0:
            return float(p['a_total_pct']) / base * 100, float(p['b_total_pct']) / base * 100
    return None


def na_janela(p: dict, data_eleicao: str | None, dias: int = 7) -> bool:
    """Campo terminado entre `dias` antes da eleição e a véspera. A regra é aplicada aqui, não confiada a quem levantou."""
    if not data_eleicao:
        return True
    if not p.get('campo_fim'):
        return False
    el, fim = date.fromisoformat(data_eleicao), date.fromisoformat(p['campo_fim'])
    return el - timedelta(days=dias) <= fim <= el - timedelta(days=1)


def surpresa_eleitoral(rodada: dict, data_eleicao: str | None = None, dias: int = 7) -> dict:
    tse = rodada['resultado_tse']
    margem_tse = float(tse['a_validos_pct']) - float(tse['b_validos_pct'])
    usadas = [(p['instituto'], *v) for p in rodada['pesquisas']
              if p.get('verificado') != 'nao_confirmado' and na_janela(p, data_eleicao, dias) and (v := validos(p))]
    margens = [a - b for _, a, b in usadas]
    if not margens:
        return {'margem_tse_pp': round(margem_tse, 2), 'n_pesquisas': 0}
    media = statistics.fmean(margens)
    return {
        'margem_tse_pp': round(margem_tse, 2),
        'margem_pesquisas_media_pp': round(media, 2),
        'margem_pesquisas_mediana_pp': round(statistics.median(margens), 2),
        'margem_pesquisas_min_max_pp': [round(min(margens), 2), round(max(margens), 2)],
        'n_pesquisas': len(margens),
        'institutos': [i for i, _, _ in usadas],
        'surpresa_pp': round(margem_tse - media, 2),
        'surpresa_pela_mediana_pp': round(margem_tse - statistics.median(margens), 2),  # robustez a instituto fora da curva
        'erro_padrao_entre_institutos_pp': round(statistics.stdev(margens) / math.sqrt(len(margens)), 2) if len(margens) > 1 else math.nan,
        'erro_a_pp': round(float(tse['a_validos_pct']) - statistics.fmean(a for _, a, _ in usadas), 2),
        'erro_b_pp': round(float(tse['b_validos_pct']) - statistics.fmean(b for _, _, b in usadas), 2),
        # errou quem pôs o OUTRO na frente; empate não aponta vencedor e não conta como erro
        'pesquisas_que_erraram_o_vencedor': sum(1 for m in margens if m * margem_tse < 0),
    }


def sensibilidade_janela(rodada: dict, data_eleicao: str, janelas: tuple[int, ...] = (7, 5, 3)) -> dict:
    """A surpresa com a janela de pesquisas de 7, 5 e 3 dias, pela média e pela mediana.
    Só conta como surpresa mensurável o turno em que o sinal não vira em nenhuma delas."""
    saida, sinais = {}, set()
    for d in janelas:
        s = surpresa_eleitoral(rodada, data_eleicao, d)
        saida[f'{d}_dias'] = {'media': s.get('surpresa_pp'), 'mediana': s.get('surpresa_pela_mediana_pp'), 'n': s['n_pesquisas']}
        sinais |= {(v > 0) - (v < 0) for v in (s.get('surpresa_pp'), s.get('surpresa_pela_mediana_pp')) if v is not None}
    saida['sinal_estavel'] = len(sinais) == 1 and 0 not in sinais
    return saida


def tabela_eleicoes(rodadas: list[dict], eventos_medidos) -> list[dict]:
    """Junta a surpresa de cada turno com a reação medida no pregão seguinte (dia 0)."""
    linhas = []
    for r in rodadas:
        if not r.get('dados'):
            continue
        s = surpresa_eleitoral(r['dados'], r.get('data'))
        ev = eventos_medidos[eventos_medidos['data'] == RODADA_PARA_EVENTO.get(r['id'])]
        m = ev.iloc[0] if len(ev) else {}
        sens = sensibilidade_janela(r['dados'], r['data'])
        linhas.append({'rodada': r['id'], 'turno': r['turno'], 'a': r['a'], 'b': r['b'], **s,
                       'surpresa_mensuravel': sens['sinal_estavel'], 'sensibilidade_janela': sens,
                       'ibov_d0': m.get('ibov_d0', math.nan), 'ibov_z0': m.get('ibov_z0', math.nan),
                       'ptax_d0': m.get('ptax_d0', math.nan), 'pre5_d0_pb': m.get('pre5_d0_pb', math.nan)})
    return linhas

"""Mede a reação a cada evento nas janelas de −5 a +5 pregões. Funções puras: série + data → números.

Convenções (todas no calendário de pregões do Ibovespa):
- dia 0 = o pregão da reação (o primeiro pregão em que a notícia podia entrar no preço);
- d0 = fechamento do dia 0 contra o do dia −1;
- antes = dia −1 contra o dia −6 (os 5 pregões anteriores: o mercado antecipou?);
- depois = dia +5 contra o dia 0 (continuou ou devolveu?);
- janela = dia +5 contra o dia −6;
- z0 = d0 dividido pelo desvio ROBUSTO (MAD × 1,4826) dos retornos diários dos pregões −260 a −11, sem os dias 0 e +1
  dos outros eventos (quantos "dias normais" o movimento valeu). O desvio robusto não deixa um crash (COVID) dentro
  da janela cortar pela metade o z de quem vem depois; o z pelo desvio-padrão simples fica em z0_simples.
A PTAX é fixada entre 10h e 13h e a taxa do Tesouro Direto é a da manhã: notícia da tarde só aparece no dia +1.
Por isso dólar e juros também têm d01 (dia +1 contra o dia −1).
"""
import math

import pandas as pd

ANTES, DEPOIS = 5, 5
ESTIMACAO = (-260, -11)
MIN_ESTIMACAO = 150


def calendario(ibov: pd.Series) -> pd.DatetimeIndex:
    cal = pd.DatetimeIndex(ibov.dropna().index).sort_values()
    if (cal.dayofweek >= 5).any():
        raise ValueError('o Ibovespa tem data de fim de semana: rode estudo.series.limpar_ibov antes')
    return cal


def dia_zero(data: str | pd.Timestamp, cal: pd.DatetimeIndex) -> int | None:
    """Índice do primeiro pregão na data ou depois dela (evento de fim de semana reage na segunda)."""
    i = int(cal.searchsorted(pd.Timestamp(data)))
    return i if i < len(cal) else None


def no_calendario(s: pd.Series, cal: pd.DatetimeIndex, limite_dias: int = 4) -> pd.Series:
    """Leva uma série (PTAX, Tesouro) para o calendário do Ibovespa usando o último valor conhecido, sem inventar
    valor para buracos longos."""
    s = s.dropna().sort_index()
    pos = s.index.searchsorted(cal, side='right') - 1
    valores = []
    for d, p in zip(cal, pos):
        valores.append(s.iloc[p] if p >= 0 and (d - s.index[p]).days <= limite_dias else math.nan)
    return pd.Series(valores, index=cal, dtype=float)


def _ret(a: float, b: float) -> float:
    return b / a - 1 if a and not (math.isnan(a) or math.isnan(b)) else math.nan


def desvio_robusto(retornos: pd.Series) -> float:
    r = retornos.dropna()
    return float(1.4826 * (r - r.median()).abs().median()) if r.size else math.nan


def medir_preco(s: pd.Series, i0: int, excluir: frozenset[int] = frozenset()) -> dict:
    """s já no calendário de pregões. Devolve variações em % (0,01 = 1%).

    excluir: posições (no calendário) dos dias 0 e +1 de outros eventos, que ficam fora da estimação do desvio."""
    v = s.to_numpy()
    if i0 - ANTES - 1 < 0 or i0 + DEPOIS >= len(v):
        return {}
    r = {
        'd0': _ret(v[i0 - 1], v[i0]),
        'd01': _ret(v[i0 - 1], v[i0 + 1]),
        'antes': _ret(v[i0 - ANTES - 1], v[i0 - 1]),
        'depois': _ret(v[i0], v[i0 + DEPOIS]),
        'janela': _ret(v[i0 - ANTES - 1], v[i0 + DEPOIS]),
        'caminho': [_ret(v[i0 - 1], v[i0 + k]) for k in range(-ANTES, DEPOIS + 1)],
    }
    a, b = i0 + ESTIMACAO[0], i0 + ESTIMACAO[1]
    if a >= 1:
        diarios = pd.Series(v[a - 1:b + 1], index=range(a - 1, b + 1)).pct_change().iloc[1:]
        diarios = diarios[~diarios.index.isin(excluir)].dropna()
        if diarios.size >= MIN_ESTIMACAO and diarios.std() > 0:
            r['sigma'] = desvio_robusto(diarios)
            r['z0'] = r['d0'] / r['sigma']
            r['z0_simples'] = r['d0'] / float(diarios.std())
    return r


def medir_taxa(s: pd.Series, i0: int) -> dict:
    """Taxa em % ao ano; devolve as variações em pontos-base (1 pb = 0,01 ponto percentual)."""
    v = s.to_numpy()
    if i0 - ANTES - 1 < 0 or i0 + DEPOIS >= len(v):
        return {}

    def pb(a: float, b: float) -> float:
        return (b - a) * 100 if not (math.isnan(a) or math.isnan(b)) else math.nan

    return {
        'nivel': v[i0 - 1],
        'd0_pb': pb(v[i0 - 1], v[i0]),
        'd01_pb': pb(v[i0 - 1], v[i0 + 1]),
        'antes_pb': pb(v[i0 - ANTES - 1], v[i0 - 1]),
        'depois_pb': pb(v[i0 + 1], v[i0 + DEPOIS]),
        'janela_pb': pb(v[i0 - ANTES - 1], v[i0 + DEPOIS]),
    }


def comportamento(d0: float, antes: float, depois: float) -> dict:
    """Leitura qualitativa: o movimento veio antes? continuou ou devolveu depois?"""
    if any(math.isnan(x) for x in (d0, antes, depois)) or d0 == 0:
        return {'antecipou': None, 'depois_vs_d0': math.nan, 'leitura_depois': None}
    razao = depois / d0  # +1 = dobrou na mesma direção; −1 = devolveu tudo
    leitura = 'continuou' if razao > 0.25 else 'devolveu tudo ou mais' if razao <= -1 else 'devolveu parte' if razao < -0.25 else 'parou'
    return {'antecipou': (antes > 0) == (d0 > 0) and abs(antes) >= 0.5 * abs(d0), 'depois_vs_d0': razao,
            'leitura_depois': leitura}

"""Resume as reações por nível de surpresa e por tipo de evento. Com ~50 eventos, tudo aqui é indício, não lei."""
import math

import numpy as np
import pandas as pd

ORDEM_SURPRESA = ['alta', 'media', 'baixa', 'nenhuma']


def agregar(eventos: pd.DataFrame, por: str) -> pd.DataFrame:
    g = eventos.dropna(subset=['ibov_d0']).groupby(por)
    t = pd.DataFrame({
        'n': g.size(),
        'ibov_abs_d0_media': g['ibov_d0'].apply(lambda x: x.abs().mean()),
        'ibov_abs_z0_mediana': g['ibov_z0'].apply(lambda x: x.abs().median()),
        'pct_z_acima_2': g['ibov_z0'].apply(lambda x: (x.abs() >= 2).mean()),
        'pct_continuou': g['leitura_depois'].apply(lambda x: (x == 'continuou').mean()),
        'depois_vs_d0_mediana': g['depois_vs_d0'].median(),
        'ptax_abs_d01_media': g['ptax_d01'].apply(lambda x: x.abs().mean()),
        'pre5_abs_d01_pb_media': g['pre5_d01_pb'].apply(lambda x: x.abs().mean()),
    })
    if por == 'surpresa':
        t = t.reindex([s for s in ORDEM_SURPRESA if s in t.index])
    return t.sort_values('n', ascending=False) if por != 'surpresa' else t


def permutacao(a: np.ndarray, b: np.ndarray, n: int = 20000, semente: int = 7) -> float:
    """p-valor unilateral de média(a) − média(b) ser tão grande quanto a observada só por sorte."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    a, b = a[~np.isnan(a)], b[~np.isnan(b)]
    if a.size < 3 or b.size < 3:
        return math.nan
    observado = a.mean() - b.mean()
    juntos = np.concatenate([a, b])
    rng = np.random.default_rng(semente)
    maiores = 0
    for _ in range(n):
        rng.shuffle(juntos)
        if juntos[:a.size].mean() - juntos[a.size:].mean() >= observado:
            maiores += 1
    return (maiores + 1) / (n + 1)


def theil_sen(x: np.ndarray, y: np.ndarray) -> float:
    """Inclinação robusta: a mediana das inclinações entre todos os pares de pontos. Um ponto extremo não a arrasta."""
    dx = x[None, :] - x[:, None]
    dy = y[None, :] - y[:, None]
    ok = np.triu(dx != 0, k=1)
    return float(np.median(dy[ok] / dx[ok])) if ok.any() else math.nan


def _versao_copom(v: pd.DataFrame, coluna: str, limiar: float, rng: np.random.Generator, n_boot: int) -> dict:
    x, y = v[coluna].to_numpy(float), v['pre2_d0_pb'].to_numpy(float)
    com = np.abs(x) > limiar
    boot = []
    for _ in range(n_boot):
        i = rng.integers(0, len(x), len(x))
        b = theil_sen(x[i], y[i])
        if not math.isnan(b):
            boot.append(b)
    na_direcao = (np.sign(y[com]) == np.sign(x[com])).mean() if com.any() else math.nan
    return {
        'n': int(len(x)), 'com_surpresa': int(com.sum()), 'sem_surpresa': int((~com).sum()),
        'inclinacao_pb_por_pb': round(theil_sen(x, y), 3),
        'ic95': [round(float(np.percentile(boot, 2.5)), 3), round(float(np.percentile(boot, 97.5)), 3)] if boot else None,
        'juros2a_mediana_abs_com_pb': round(float(np.median(np.abs(y[com]))), 1) if com.any() else math.nan,
        'juros2a_mediana_abs_sem_pb': round(float(np.median(np.abs(y[~com]))), 1) if (~com).any() else math.nan,
        'p_juros_com_x_sem': permutacao(np.abs(y[com]), np.abs(y[~com])),
        'na_direcao_da_surpresa': f'{int(round(na_direcao * com.sum()))} de {int(com.sum())}' if com.any() else '—',
        'spearman_surpresa_x_ibov': round(float(pd.Series(x).corr(pd.Series(v['ibov_d0'].to_numpy(float)), method='spearman')), 3),
    }


def analisar_copom(df: pd.DataFrame, n_boot: int = 2000, semente: int = 7) -> dict:
    """Copom × Focus em todas as reuniões, em quatro versões lado a lado, porque o resultado depende delas:
    todas; sem a reunião que mais pesa; só o Focus fresco (base de 5 dias úteis, desde mar/2021); e a surpresa
    contínua pela MÉDIA do Focus (um mercado dividido 50/50 não vira surpresa cheia). Inclinação de Theil-Sen."""
    v = df.dropna(subset=['surpresa_pb', 'pre2_d0_pb']).reset_index(drop=True)
    rng = np.random.default_rng(semente)
    x, y = v['surpresa_pb'].to_numpy(float), v['pre2_d0_pb'].to_numpy(float)
    base = np.polyfit(x, y, 1)[0]
    influencia = [abs(np.polyfit(np.delete(x, i), np.delete(y, i), 1)[0] - base) for i in range(len(x))]
    i_max = int(np.argmax(influencia))
    fresco = v[v['focus_base'] == 'últimos 5 dias úteis']
    return {
        'reunioes': int(len(df)), 'mercado_dividido': int(v['dividida'].fillna(False).astype(bool).sum()),
        'reuniao_que_mais_pesa': f"{v.loc[i_max, 'reuniao']} ({v.loc[i_max, 'decisao']})",
        'versoes': {
            'todas': _versao_copom(v, 'surpresa_pb', 0, rng, n_boot),
            'sem_a_que_mais_pesa': _versao_copom(v.drop(index=i_max), 'surpresa_pb', 0, rng, n_boot),
            'so_focus_fresco_desde_mar2021': _versao_copom(fresco, 'surpresa_pb', 0, rng, n_boot),
            'surpresa_continua_pela_media': _versao_copom(v, 'surpresa_continua_pb', 10, rng, n_boot),
        },
    }


def _alinhados(eventos: pd.DataFrame, niveis: list[str]) -> tuple[pd.DataFrame, np.ndarray]:
    sel = eventos[eventos['surpresa'].isin(niveis) & eventos['ibov_caminho'].notna() & (eventos['ibov_d0'] != 0)]
    m = np.array([np.sign(d0) * np.array(c, float) for d0, c in zip(sel['ibov_d0'], sel['ibov_caminho'])])
    return sel, m


def caminho_medio(eventos: pd.DataFrame, grupos: dict[str, list[str]], estatistica: str = 'mediana') -> dict[str, list[float]]:
    """Caminho do Ibovespa de −5 a +5 com o sinal do dia 0 virado para cima (alta e queda somam juntas).

    Mediana por padrão: com 15 a 19 eventos por grupo, a média fica refém de um só (o crash da COVID)."""
    saida = {}
    for nome, niveis in grupos.items():
        sel, m = _alinhados(eventos, niveis)
        if sel.empty:
            continue
        saida[nome] = list(np.nanmedian(m, axis=0) if estatistica == 'mediana' else np.nanmean(m, axis=0))
    return saida


def depois_do_dia_zero(eventos: pd.DataFrame, niveis: list[str], n: int = 10000, semente: int = 7) -> dict:
    """O que acontece do dia 0 ao +5, na direção do dia 0: >0 continuou, <0 devolveu.

    Traz média, mediana, intervalo de 95% por bootstrap e a média sem o evento que mais pesa (o teste de que a conclusão
    não depende de um caso só). Se o intervalo cruza o zero, não há evidência de continuação nem de reversão."""
    sel, m = _alinhados(eventos, niveis)
    if sel.empty:
        return {}
    pos = (1 + m[:, -1]) / (1 + m[:, 5]) - 1  # do fechamento do dia 0 ao do +5, alinhado
    validos = ~np.isnan(pos)
    pos, sel = pos[validos], sel[validos]
    rng = np.random.default_rng(semente)
    medias = rng.choice(pos, size=(n, pos.size), replace=True).mean(axis=1)
    i_max = int(np.argmax(np.abs(pos - pos.mean())))
    sem = np.delete(pos, i_max)
    return {
        'n': int(pos.size), 'media': float(pos.mean()), 'mediana': float(np.median(pos)),
        'ic95': [float(np.percentile(medias, 2.5)), float(np.percentile(medias, 97.5))],
        'continuou': int((pos > 0).sum()), 'devolveu': int((pos < 0).sum()),
        'evento_que_mais_pesa': str(sel.iloc[i_max]['evento']),
        'media_sem_ele': float(sem.mean()) if sem.size else math.nan,
    }

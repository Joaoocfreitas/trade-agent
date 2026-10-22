"""Estudo de evento.

  python -m estudo baixar   # baixa as séries oficiais e o Focus das reuniões do Copom para dados/series/
  python -m estudo medir    # mede os eventos da linha do tempo e grava dados/estudo/
"""
import argparse
import json
import math
from datetime import date

import numpy as np
import pandas as pd

from coletor.config import DADOS, FONTES_DIR, FUSO
from .agregados import agregar, analisar_copom, caminho_medio, depois_do_dia_zero, permutacao
from .janelas import calendario, comportamento, dia_zero, medir_preco, medir_taxa, no_calendario
from .eleicoes import tabela_eleicoes
from .series import Cliente, baixar_tudo, limpar_ibov
from .surpresa import COMUNICADOS, decisao, dividida, expectativa_na_vespera, reunioes, url_focus, url_focus_reuniao

SERIES = DADOS / 'series'
SAIDA = DADOS / 'estudo'
TOLERANCIA_IBOV_PP = 0.1  # duas fontes do mesmo fechamento: acima disso é erro de dado ou de data
GRUPOS = {'surpresa alta': ['alta'], 'surpresa média': ['media'], 'baixa ou nenhuma': ['baixa', 'nenhuma']}


def ler_serie(nome: str) -> pd.Series:
    df = pd.read_csv(SERIES / f'{nome}.csv', parse_dates=['data'], index_col='data')
    return df[nome].astype(float)


def _pct(x: float) -> float:
    return round(x * 100, 2) if x is not None and not math.isnan(x) else math.nan


def eh_copom(e: dict) -> bool:
    return e['tipo'] == 'monetario' and 'Copom' in e['evento']


def medir_eventos(eventos: list[dict], ibov: pd.Series, ptax: pd.Series, pre2: pd.Series, pre5: pd.Series,
                  selic: pd.Series) -> pd.DataFrame:
    cal = calendario(ibov)
    ibov_c = ibov.reindex(cal)
    ptax_c, pre2_c, pre5_c, selic_c = (no_calendario(s, cal) for s in (ptax, pre2, pre5, selic))
    posicoes = [dia_zero(e['data'], cal) for e in eventos]
    linhas = []
    for e, i0 in zip(eventos, posicoes):
        base = {k: e[k] for k in ('data', 'evento', 'tipo', 'surpresa', 'confianca')}
        if i0 is None:
            linhas.append({**base, 'alerta': 'data fora da série'})
            continue
        # os dias 0 e +1 dos OUTROS eventos ficam fora da estimação do desvio deste
        excluir = frozenset(j + k for j in posicoes if j is not None and j != i0 for k in (0, 1))
        ib, px = medir_preco(ibov_c, i0, excluir), medir_preco(ptax_c, i0)
        p2, p5 = medir_taxa(pre2_c, i0), medir_taxa(pre5_c, i0)
        comp = comportamento(ib.get('d0', math.nan), ib.get('antes', math.nan), ib.get('depois', math.nan))
        linha = {
            **base, 'dia0': str(cal[i0].date()),
            'ibov_d0': ib.get('d0', math.nan), 'ibov_d01': ib.get('d01', math.nan),
            'ibov_z0': ib.get('z0', math.nan), 'ibov_z0_simples': ib.get('z0_simples', math.nan),
            'ibov_antes': ib.get('antes', math.nan), 'ibov_depois': ib.get('depois', math.nan),
            'ibov_janela': ib.get('janela', math.nan), 'ibov_caminho': ib.get('caminho'), **comp,
            'ptax_d0': px.get('d0', math.nan), 'ptax_d01': px.get('d01', math.nan), 'ptax_janela': px.get('janela', math.nan),
            'pre2_d01_pb': p2.get('d01_pb', math.nan), 'pre5_d01_pb': p5.get('d01_pb', math.nan),
            'pre2_d0_pb': p2.get('d0_pb', math.nan), 'pre5_d0_pb': p5.get('d0_pb', math.nan),
            'pre5_janela_pb': p5.get('janela_pb', math.nan), 'pre5_nivel': p5.get('nivel', math.nan),
            'selic_meta': selic_c.iloc[i0 - 1] if i0 >= 1 else math.nan,
            'linha_ibov_pct': e.get('ibov_dia_pct'), 'linha_dolar_pct': e.get('dolar_dia_pct'),
        }
        alertas = []
        if str(cal[i0].date()) != e['data']:
            alertas.append(f"data {e['data']} não é pregão; dia 0 = {cal[i0].date()}")
        if e.get('ibov_dia_pct') is not None and not math.isnan(linha['ibov_d0']):
            dif = _pct(linha['ibov_d0']) - e['ibov_dia_pct']
            linha['dif_ibov_pp'] = round(dif, 2)
            if abs(dif) > TOLERANCIA_IBOV_PP:
                alertas.append(f'Ibovespa medido {_pct(linha["ibov_d0"]):+.2f}% x linha do tempo {e["ibov_dia_pct"]:+.2f}%')
        linha['alerta'] = '; '.join(alertas)
        linhas.append(linha)
    return pd.DataFrame(linhas)


def surpresa_copom(eventos: list[dict], focus: dict, selic: pd.Series, medidos: pd.DataFrame) -> pd.DataFrame:
    """Decisão menos a mediana do Focus para a reunião, por evento do Copom. focus: data do evento -> registros."""
    linhas = []
    for e in filter(eh_copom, eventos):
        # o Copom anuncia depois do fechamento: o dia da decisão é o pregão anterior ao dia da reação
        dia_decisao = pd.Timestamp(e['data']) - pd.offsets.BDay(1)
        esp = expectativa_na_vespera(focus.get(e['data'], []), dia_decisao)
        antes, depois = decisao(selic, dia_decisao)
        m = medidos[medidos['data'] == e['data']].iloc[0]
        linhas.append({
            'data': e['data'], 'evento': e['evento'], 'rotulo_posterior': e['surpresa'],
            'reuniao': esp['reuniao'] if esp else None, 'pesquisa_em': esp['pesquisa_em'] if esp else None,
            'selic_antes': antes, 'selic_depois': depois, 'focus_mediana': esp['mediana'] if esp else math.nan,
            'surpresa_pb': round((depois - esp['mediana']) * 100) if esp else math.nan,
            'focus_desvio_pb': round(esp['desvio'] * 100) if esp else math.nan,
            'ibov_z0': m['ibov_z0'], 'pre2_d01_pb': m['pre2_d01_pb'],
        })
    return pd.DataFrame(linhas)


def medir_copom(focus_reunioes: dict, ibov: pd.Series, ptax: pd.Series, pre2: pd.Series, pre5: pd.Series,
                selic: pd.Series) -> pd.DataFrame:
    """Todas as reuniões desde 2016. O Copom anuncia depois do fechamento: o dia 0 é o pregão seguinte à decisão.
    Por isso aqui dólar (PTAX 10h–13h) e juros (Tesouro da manhã) usam o dia 0 mesmo: o valor do dia da decisão é
    de antes do anúncio e o do dia seguinte, de depois."""
    cal = calendario(ibov)
    ibov_c = ibov.reindex(cal)
    ptax_c, pre2_c, pre5_c = (no_calendario(s, cal) for s in (ptax, pre2, pre5))
    itens = sorted(focus_reunioes.items(), key=lambda kv: kv[1]['decisao'])
    posicoes = [dia_zero(pd.Timestamp(r['decisao']) + pd.Timedelta(days=1), cal) for _, r in itens]
    linhas = []
    for (reuniao, r), i0 in zip(itens, posicoes):
        dia_decisao = pd.Timestamp(r['decisao'])
        esp = expectativa_na_vespera(r['registros'], dia_decisao)
        antes, depois = decisao(selic, dia_decisao)
        linha = {'reuniao': reuniao, 'nro': r['nro'], 'decisao': r['decisao'], 'selic_antes': antes, 'selic_depois': depois,
                 'mudanca_pb': round((depois - antes) * 100), 'focus_mediana': esp['mediana'] if esp else math.nan,
                 'focus_media': esp['media'] if esp else math.nan,
                 'surpresa_pb': round((depois - esp['mediana']) * 100) if esp else math.nan,
                 # contínua: um mercado 50/50 dá ~12 pb, não 25
                 'surpresa_continua_pb': round((depois - esp['media']) * 100, 1) if esp else math.nan,
                 'dividida': dividida(esp) if esp else None,
                 'focus_desvio_pb': round(esp['desvio'] * 100) if esp else math.nan,
                 'focus_pesquisa_em': esp['pesquisa_em'] if esp else None, 'focus_base': esp['base'] if esp else None}
        if i0 is not None:
            excluir = frozenset(j + k for j in posicoes if j is not None and j != i0 for k in (0, 1))
            ib, px = medir_preco(ibov_c, i0, excluir), medir_preco(ptax_c, i0)
            linha.update({'dia0': str(cal[i0].date()), 'ibov_d0': ib.get('d0', math.nan), 'ibov_z0': ib.get('z0', math.nan),
                          'ptax_d0': px.get('d0', math.nan), 'pre2_d0_pb': medir_taxa(pre2_c, i0).get('d0_pb', math.nan),
                          'pre5_d0_pb': medir_taxa(pre5_c, i0).get('d0_pb', math.nan)})
        linhas.append(linha)
    return pd.DataFrame(linhas)


def conferir_ibov(ibov: pd.Series, ibov_bcb: pd.Series) -> dict:
    """Duas republicações oficiais do mesmo fechamento da B3 (Ipeadata e SGS 7, até 2019) devem bater."""
    juntos = pd.concat([ibov.rename('ipea'), ibov_bcb.rename('bcb')], axis=1).dropna()
    if juntos.empty:
        return {'dias_comparados': 0}
    dif = (juntos['ipea'] / juntos['bcb'] - 1).abs()
    return {'dias_comparados': int(juntos.shape[0]), 'de': str(juntos.index.min().date()),
            'ate': str(juntos.index.max().date()), 'dif_max_pct': round(float(dif.max()) * 100, 4),
            'dias_dif_acima_0_1pct': [str(d.date()) for d in dif[dif > 0.001].index]}


def _p(p: float, n: int = 20000) -> str:
    return f'< {1 / (n + 1):.5f}' if p <= 1 / (n + 1) + 1e-12 else f'{p:.4f}'


def baixar(_args: argparse.Namespace) -> None:
    baixar_tudo(SERIES, date(2015, 1, 1), pd.Timestamp.now(tz=FUSO).date())
    eventos = json.loads((FONTES_DIR / 'linha-do-tempo.json').read_text(encoding='utf-8'))['eventos']
    c, focus = Cliente(), {}
    for e in filter(eh_copom, eventos):
        dia_decisao = pd.Timestamp(e['data']) - pd.offsets.BDay(1)
        focus[e['data']] = c.json(url_focus(dia_decisao))['value']
        print(f"  Focus {e['data']}: {len(focus[e['data']])} registros", flush=True)
    (SERIES / 'focus_copom.json').write_text(json.dumps(focus, ensure_ascii=False), encoding='utf-8')
    # todas as reuniões desde 2016: calendário oficial do BC + Focus da reunião, só pesquisas de antes da decisão
    lista = reunioes(c.json(COMUNICADOS.format(n=120))['conteudo'], '2016-01-01')
    todas = {}
    for _, r in lista.iterrows():
        todas[r['reuniao']] = {'nro': int(r['nro']), 'decisao': str(r['decisao'].date()),
                               'registros': c.json(url_focus_reuniao(r['reuniao'], r['decisao']))['value']}
    (SERIES / 'copom_reunioes.json').write_text(json.dumps(todas, ensure_ascii=False), encoding='utf-8')
    print(f'  Copom: {len(todas)} reuniões com o Focus de antes da decisão', flush=True)


def medir(_args: argparse.Namespace) -> None:
    eventos = json.loads((FONTES_DIR / 'linha-do-tempo.json').read_text(encoding='utf-8'))['eventos']
    ibov, falsos = limpar_ibov(ler_serie('ibov'))
    ptax, pre2, pre5, selic = (ler_serie(n) for n in ('ptax', 'pre_2a', 'pre_5a', 'selic_meta'))
    df = medir_eventos(eventos, ibov, ptax, pre2, pre5, selic)
    SAIDA.mkdir(parents=True, exist_ok=True)

    tabela = df.drop(columns=['ibov_caminho']).copy()
    for c in ('ibov_d0', 'ibov_d01', 'ibov_antes', 'ibov_depois', 'ibov_janela', 'ptax_d0', 'ptax_d01', 'ptax_janela'):
        tabela[c] = tabela[c].map(_pct)
    tabela.to_csv(SAIDA / 'eventos.csv', index=False, float_format='%.4g')

    focus_arq = SERIES / 'focus_copom.json'
    copom = surpresa_copom(eventos, json.loads(focus_arq.read_text(encoding='utf-8')), selic, df) if focus_arq.exists() else pd.DataFrame()
    if not copom.empty:
        copom.to_csv(SAIDA / 'surpresa_copom.csv', index=False)

    alta = df.loc[df['surpresa'] == 'alta', 'ibov_z0'].abs()
    resto = df.loc[df['surpresa'].isin(['baixa', 'nenhuma']), 'ibov_z0'].abs()
    p = permutacao(alta.to_numpy(), resto.to_numpy())
    resumo = {
        'gerado_em': pd.Timestamp.now(tz=FUSO).isoformat(timespec='seconds'),
        'eventos': int(len(df)), 'medidos': int(df['ibov_d0'].notna().sum()),
        'ibov_pontos_falsos_retirados': falsos,
        'conferencia_ibov_ipea_x_bcb': conferir_ibov(ibov, ler_serie('ibov_bcb')),
        'por_surpresa': agregar(df, 'surpresa').round(4).reset_index().to_dict('records'),
        'por_tipo': agregar(df, 'tipo').round(4).reset_index().to_dict('records'),
        'coerencia_do_rotulo_posterior': {
            'leia_assim': ('Os rótulos de surpresa foram dados por quem já sabia como o mercado reagiu. Este teste mede '
                           'se o rótulo acompanha o tamanho da reação, NÃO prova que a surpresa causa a reação. '
                           'Prova exige surpresa medida antes: ver copom_completo e eleicoes_surpresa_ex_ante.'),
            'media_abs_z0_alta': round(float(alta.mean()), 3), 'media_abs_z0_baixa_nenhuma': round(float(resto.mean()), 3),
            'n_alta': int(alta.notna().sum()), 'n_baixa_nenhuma': int(resto.notna().sum()), 'p_valor_permutacao': _p(p),
        },
        'depois_do_dia_zero': {nome: depois_do_dia_zero(df, niveis) for nome, niveis in GRUPOS.items()},
        'caminho_mediano_alinhado': caminho_medio(df, GRUPOS, 'mediana'),
        'caminho_medio_alinhado': caminho_medio(df, GRUPOS, 'media'),
        'copom_so_os_da_linha_do_tempo': {
            'leia_assim': ('Só as 7 reuniões que a pesquisa escolheu por terem sido notícia, com janela de 2 dias. '
                           'NÃO tire conclusão daqui: a análise válida é copom_completo (86 reuniões).'),
            'reunioes': copom.round(3).to_dict('records') if not copom.empty else [],
        },
        'alertas': df.loc[df['alerta'].fillna('') != '', ['data', 'evento', 'alerta']].to_dict('records'),
    }
    pesquisas_arq = FONTES_DIR / 'pesquisas_eleicoes.json'
    if pesquisas_arq.exists():
        eleicoes = tabela_eleicoes(json.loads(pesquisas_arq.read_text(encoding='utf-8')), df)
        pd.DataFrame(eleicoes).drop(columns=['institutos', 'sensibilidade_janela']).to_csv(SAIDA / 'eleicoes_surpresa.csv', index=False, float_format='%.4g')
        resumo['eleicoes_surpresa_ex_ante'] = eleicoes
    todas_arq = SERIES / 'copom_reunioes.json'
    if todas_arq.exists():
        completo = medir_copom(json.loads(todas_arq.read_text(encoding='utf-8')), ibov, ptax, pre2, pre5, selic)
        tab = completo.copy()
        for c in ('ibov_d0', 'ptax_d0'):
            tab[c] = tab[c].map(_pct)
        tab.to_csv(SAIDA / 'copom_completo.csv', index=False, float_format='%.4g')
        analise = analisar_copom(completo)
        for versao in analise['versoes'].values():
            versao['p_juros_com_x_sem'] = _p(versao['p_juros_com_x_sem'])
        resumo['copom_completo'] = {
            'leia_assim': ('Surpresa contra a mediana (ou a média) do Focus, que não é o preço de mercado. A janela dos juros '
                           'vai da manhã do dia da decisão à manhã seguinte e inclui o pregão inteiro antes do anúncio. '
                           'Compare as versões: o sinal da inclinação depende de mar/2020 (pânico da COVID).'),
            **analise,
        }
    (SAIDA / 'resumo.json').write_text(json.dumps(resumo, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
    print(f"{resumo['medidos']}/{resumo['eventos']} eventos medidos; {len(resumo['alertas'])} alertas; "
          f"{len(falsos)} pontos falsos do Ipeadata retirados")
    print(json.dumps(resumo['coerencia_do_rotulo_posterior'], ensure_ascii=False))
    print(f'gravado em {SAIDA}')


def main() -> None:
    p = argparse.ArgumentParser(prog='estudo')
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('baixar')
    sub.add_parser('medir')
    args = p.parse_args()
    baixar(args) if args.cmd == 'baixar' else medir(args)


if __name__ == '__main__':
    main()

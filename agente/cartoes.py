"""Os cartões de casos passados que o site mostra junto da resposta: cada caso, a distribuição e o caminho de cada um.

Sai dos mesmos dados que escrevem o texto (dados/estudo/*.csv e as séries oficiais), com o mesmo arredondamento, para
que o cartão e o texto mostrem os mesmos números. Regras que o cartão cumpre (nota de regras):
- P2/N3: a distribuição inteira (menor, maior, mediana, taxa-base), nunca "X de N subiram";
- N2/N6: só o passado; o gráfico é o caminho de cada caso de 5 pregões antes a 5 depois, sem "hoje" e sem projeção;
- D8: número só de série oficial; o cartão diz de onde veio.
"""
import pandas as pd

from . import fatos as F

JANELA = 5  # pregões antes e depois do dia da reação
SERIE = {'ibovespa': ('ibov', '%', 2), 'dolar': ('ptax', '%', 2), 'juros': ('pre_5a', ' p.b.', 1), 'juros_2a': ('pre_2a', ' p.b.', 1),
         'brent': ('brent', '%', 2)}
NOME = {'ibovespa': 'Ibovespa', 'dolar': 'Dólar (PTAX)', 'juros': 'Juros de 5 anos', 'juros_2a': 'Juros de 2 anos',
        'brent': 'Petróleo Brent (EIA)'}


def _caminho(mercado: str, d0) -> list[float]:
    """Do 5º pregão antes ao 5º depois do dia da reação, em relação ao fechamento da véspera (índice JANELA - 1 = 0)."""
    nome, un, casas = SERIE[mercado]
    s = F.serie(nome)
    i = int(s.index.searchsorted(pd.Timestamp(d0)))
    if i < JANELA or i >= len(s):
        return []
    janela = s.iloc[i - JANELA:i + JANELA + 1]
    base = s.iloc[i - 1]
    valores = (janela - base) * 100 if un.strip() == 'p.b.' else (janela / base - 1) * 100
    return [round(float(v), casas) for v in valores]


def _taxa(mercado: str) -> dict:
    nome, limite, un, _ = F.TAXA['juros' if mercado.startswith('juros') else mercado]
    if mercado == 'juros_2a':
        nome = 'pre_2a'
    r = F._variacoes(nome)
    sobe, cai = float((r > limite).mean() * 100), float((r < -limite).mean() * 100)
    return {'label': f'Pregões comuns ({r.index[0].year}–{r.index[-1].year}) com movimento acima de {F.num(limite, 0)}{un}',
            'value': f'{F.num(sobe, 1)}% para cima e {F.num(cai, 1)}% para baixo'}


def _cartao(titulo: str, mercado: str, casos: list[dict], fonte: str) -> dict:
    _, un, casas = SERIE[mercado]
    v = pd.Series([c['valor'] for c in casos], dtype=float)
    lo, hi = int(v.idxmin()), int(v.idxmax())
    datas = sorted(c['data'] for c in casos)
    return {
        'titulo': titulo,
        'periodo': {'de': datas[0], 'ate': datas[-1]},
        'mercado': mercado,
        'ativo': NOME[mercado],
        'unidade': un.strip(),
        'janela': 'pregão da reação',
        'itens': casos,
        'stats': [
            {'label': 'Menor reação', 'value': f'{F.sinal(v[lo], casas)}{un} ({casos[lo]["titulo"]})'},
            {'label': 'Maior reação', 'value': f'{F.sinal(v[hi], casas)}{un} ({casos[hi]["titulo"]})'},
            {'label': f'Mediana dos {len(casos)} casos', 'value': f'{F.sinal(v.median(), casas)}{un}'},
            _taxa(mercado),
        ],
        'caminhos': [c['caminho'] for c in casos if c['caminho']],
        'indice_d0': JANELA,
        'fonte': fonte,
    }


def eleicoes(alvo: list[str]) -> dict:
    tab = F._csv('eleicoes_surpresa.csv')
    datas = {x['id']: x['data'] for x in F._json('fontes/pesquisas_eleicoes.json')}
    mercado = alvo[0]
    col, k, casas = {'ibovespa': ('ibov_d0', 100, 2), 'dolar': ('ptax_d0', 100, 2), 'juros': ('pre5_d0_pb', 1, 1)}[mercado]
    casos = []
    for _, r in tab.iterrows():
        d0 = F._proximo_pregao(datas[r.rodada])
        casos.append({'data': datas[r.rodada], 'dia_da_reacao': str(d0.date()), 'titulo': r.turno,
                      'valor': round(float(r[col]) * k, casas), 'caminho': _caminho(mercado, d0)})
    return _cartao('Os turnos presidenciais desde 2018', mercado, casos,
                   'TSE (resultado) e séries oficiais (Ipeadata, Banco Central, Tesouro Direto); cálculo próprio')


def copom(alvo: list[str] | None) -> dict:
    tab = F._csv('copom_completo.csv')
    com = tab[tab.surpresa_pb != 0].reset_index(drop=True)
    mercado = alvo[0] if alvo else 'juros'
    mercado = 'juros_2a' if mercado == 'juros' else mercado
    col, casas = {'ibovespa': ('ibov_d0', 2), 'dolar': ('ptax_d0', 2), 'juros_2a': ('pre2_d0_pb', 1)}[mercado]
    casos = [{'data': r.decisao, 'dia_da_reacao': r.dia0,
              'titulo': f'{r.reuniao}: Selic de {F.num(r.selic_antes, 2)}% para {F.num(r.selic_depois, 2)}%, '
                        f'Focus esperava {F.num(r.focus_mediana, 2)}%',
              'valor': round(float(r[col]), casas), 'caminho': _caminho(mercado, r.dia0)} for _, r in com.iterrows()]
    return _cartao(f'As {len(com)} reuniões do Copom que surpreenderam o Focus desde 2016', mercado, casos,
                   'Banco Central (comunicados do Copom e boletim Focus) e séries oficiais; cálculo próprio')


def eventos(tipo: str) -> dict:
    tab = F._csv('eventos.csv')
    sel = tab[tab.tipo == tipo].reset_index(drop=True)
    casos = [{'data': r.data, 'dia_da_reacao': r.dia0, 'titulo': r.evento, 'valor': round(float(r.ibov_d0), 2),
              'caminho': _caminho('ibovespa', r.dia0)} for _, r in sel.iterrows()]
    return _cartao(f'{F.TIPOS[tipo][0].upper() + F.TIPOS[tipo][1:]} na linha do tempo 2016–2026', 'ibovespa', casos,
                   'Linha do tempo do repertório e séries oficiais (Ipeadata, Banco Central); cálculo próprio')


def petroleo(tema: str = '') -> dict:
    """Os eventos de petróleo e Petrobras do tema, com a reação do Brent no dia (o mesmo número do texto) e o caminho."""
    nome_tema = F._petroleo()['temas'][tema]['nome'] if tema else 'petróleo e Petrobras'
    evs = [e for e in F._reacao_petroleo() if (not tema or e['tema'] == tema) and e['brent_dia'] is not None]
    casos = [{'data': e['data'], 'dia_da_reacao': str(e['brent_dia'].date()), 'titulo': e['titulo'],
              'valor': round(float(e['brent']), 2), 'caminho': _caminho('brent', e['brent_dia'])} for e in evs]
    return _cartao(f'{nome_tema[0].upper() + nome_tema[1:]} desde 2016', 'brent', casos,
                   'Fonte primária de cada evento (CVM, Planalto, OPEP) e EIA (Brent à vista, domínio público); cálculo próprio')

"""Surpresa EX ANTE: o que dava para saber antes do evento, medido com dado público e sem olhar o preço depois.

Copom: decisão (meta Selic do SGS 432 depois da reunião) menos a mediana do Focus para aquela reunião, na última
pesquisa antes do dia da decisão. É o único tipo de evento da amostra em que a expectativa vem pronta, em número.
Eleição (margem oficial do TSE menos a média das últimas pesquisas) é o próximo passo: os números das pesquisas
precisam ser levantados evento a evento, e não estão em série pronta.
"""
import pandas as pd

FOCUS = 'https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoSelic'


def _ordem_reuniao(codigo: str) -> tuple[int, int]:
    """'R7/2024' -> (2024, 7)."""
    numero, ano = codigo.lstrip('R').split('/')
    return int(ano), int(numero)


def expectativa_na_vespera(registros: list[dict], dia_decisao: pd.Timestamp) -> dict | None:
    """Da lista do Focus, a última pesquisa ANTES do dia da decisão e, nela, a reunião mais próxima (a que vai decidir).
    Prefere a base dos últimos 5 dias úteis (baseCalculo=1), mais fresca; senão, a de 30 dias."""
    df = pd.DataFrame(registros)
    if df.empty:
        return None
    df['Data'] = pd.to_datetime(df['Data'])
    df = df[df['Data'] < dia_decisao]
    if df.empty:
        return None
    ultima = df[df['Data'] == df['Data'].max()]
    base = ultima[ultima['baseCalculo'] == 1] if (ultima['baseCalculo'] == 1).any() else ultima
    linha = min(base.to_dict('records'), key=lambda r: _ordem_reuniao(r['Reuniao']))
    media = linha.get('Media')
    return {'reuniao': linha['Reuniao'], 'pesquisa_em': str(linha['Data'].date()), 'mediana': float(linha['Mediana']),
            'media': float(media) if media is not None else float(linha['Mediana']),
            'desvio': float(linha['DesvioPadrao']), 'respondentes': int(linha['numeroRespondentes']),
            'base': 'últimos 5 dias úteis' if linha['baseCalculo'] == 1 else 'últimos 30 dias'}


def dividida(esp: dict) -> bool:
    """Mercado dividido: a mediana do Focus esconde a divisão e transforma um 50/50 em surpresa cheia de 25 pb."""
    return abs(esp['media'] - esp['mediana']) * 100 >= 10 or esp['desvio'] * 100 >= 12


def decisao(selic_meta: pd.Series, dia_decisao: pd.Timestamp) -> tuple[float, float]:
    """(meta antes, meta depois) em torno do dia da decisão (o Copom anuncia depois do fechamento)."""
    s = selic_meta.dropna().sort_index()
    antes = s[s.index < dia_decisao].iloc[-1]
    depois = s[s.index > dia_decisao + pd.Timedelta(days=1)].iloc[0]
    return float(antes), float(depois)


def url_focus(dia_decisao: pd.Timestamp) -> str:
    de = (dia_decisao - pd.Timedelta(days=21)).date()
    ate = (dia_decisao - pd.Timedelta(days=1)).date()
    filtro = f"Data ge '{de}' and Data le '{ate}'"
    return f"{FOCUS}?$filter={filtro.replace(' ', '%20')}&$format=json&$top=2000"


# ---------- todas as reuniões do Copom ----------

COMUNICADOS = 'https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados?quantidade={n}'


def reunioes(conteudo: list[dict], desde: str) -> pd.DataFrame:
    """Lista de comunicados do Copom -> uma linha por reunião, com o código que o Focus usa ('R3/2018' = 3ª do ano)."""
    df = pd.DataFrame({'nro': [c['nro_reuniao'] for c in conteudo],
                       'decisao': pd.to_datetime([c['dataReferencia'] for c in conteudo]),
                       'titulo': [c['titulo'] for c in conteudo]})
    df = df.drop_duplicates('nro').sort_values('decisao').reset_index(drop=True)
    df['ordem_no_ano'] = df.groupby(df['decisao'].dt.year).cumcount() + 1
    df['reuniao'] = 'R' + df['ordem_no_ano'].astype(str) + '/' + df['decisao'].dt.year.astype(str)
    return df[df['decisao'] >= pd.Timestamp(desde)].reset_index(drop=True)


def url_focus_reuniao(reuniao: str, dia_decisao: pd.Timestamp) -> str:
    """Só as pesquisas daquela reunião feitas antes do dia da decisão, da mais nova para a mais antiga."""
    filtro = f"Reuniao eq '{reuniao}' and Data lt '{dia_decisao.date()}'"
    return f"{FOCUS}?$filter={filtro.replace(' ', '%20')}&$orderby=Data%20desc&$top=20&$format=json"

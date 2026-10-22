"""Classifica manchetes em assuntos por palavra-chave. Determinístico, sem IA, sem custo."""
import re

from .nomes import norm

# Termo terminado em '*' casa como prefixo (deputad* -> deputado, deputada, deputados).
ASSUNTOS = {
    'Eleição 2026': ['eleicao', 'eleicoes', 'eleitoral', 'segundo turno', '2o turno', 'primeiro turno', 'candidat*',
                     'flavio bolsonaro', 'datafolha', 'quaest', 'atlasintel', 'ipec', 'parana pesquisas', 'tse',
                     'urna*', 'debate', 'campanha', 'election', 'runoff'],
    'Juros e Copom': ['copom', 'selic', 'juros', 'banco central', 'bcb', 'galipolo', 'di futuro', 'curva de juros'],
    'Fiscal e orçamento': ['fiscal', 'arcabouco', 'orcament*', 'deficit', 'superavit', 'divida publica', 'gastos',
                           'meta fiscal', 'precatori*', 'tesouro nacional', 'ifi', 'imposto*', 'tribut*',
                           'isencao', 'reforma tributaria'],
    'Inflação': ['inflacao', 'ipca', 'igp m', 'igp', 'inflation'],
    'Câmbio': ['dolar', 'cambio', 'ptax', 'real brasileiro'],
    'Bolsa': ['ibovespa', 'bolsa*', 'b3', 'mercado de acoes', 'acoes de empresas', 'acoes listadas',
              'acoes brasileiras', 'acoes sobem', 'acoes caem', 'acoes disparam', 'acoes recuam', 'acoes despencam',
              'acoes avancam', 'stocks'],
    'STF e Judiciário': ['stf', 'supremo', 'moraes', 'stj', 'pgr', 'policia federal', 'delacao', 'julgamento'],
    'Congresso': ['camara', 'senado', 'congresso', 'deputad*', 'senador*', 'pec', 'projeto de lei', 'plenario',
                  'hugo motta', 'alcolumbre', 'emendas'],
    'EUA, Fed e tarifas': ['fed', 'federal reserve', 'fomc', 'warsh', 'trump', 'tarifa*', 'tariff*', 'bessent',
                           'casa branca', 'white house', 'treasury', 'magnitsky', 'estados unidos', 'eua'],
    'China e commodities': ['china', 'chines*', 'minerio', 'iron ore', 'petroleo', 'brent', 'oil', 'opep', 'opec',
                            'soja', 'commodit*'],
    'Petrobras e estatais': ['petrobras', 'estata*', 'banco do brasil', 'eletrobras', 'bndes', 'caixa economica'],
}

# Expressões que parecem assunto de mercado e não são. Saem do texto antes de classificar.
EXCLUSOES = ['bolsa familia', 'bolsa* de estudo*', 'bolsa atleta', 'bolsa auxilio', 'bolsa permanencia',
             'bolsa* de pesquisa', 'tarifa zero', 'tarifa* de energia', 'tarifa* de onibus', 'tarifa* de agua',
             'tarifa social', 'tarifa* bancaria*', 'conta de luz']

# Ticker da B3 (PETR4, VALE3, BOVA11) no texto original, antes de normalizar.
TICKER_RE = re.compile(r'\b[A-Z]{4}(?:3|4|5|6|11)\b')


def _pedaco(p: str) -> str:
    """norm() tira os espaços das pontas; aqui eles voltam, para 'bolsa* de estudo*' não virar 'bolsa…de estudo'."""
    return re.escape((' ' if p.startswith(' ') else '') + norm(p) + (' ' if p.endswith(' ') and norm(p) else ''))


def _regex(termos: list[str]) -> re.Pattern:
    partes = []
    for t in termos:
        corpo = '[a-z]*'.join(_pedaco(p) for p in t.split('*'))  # '*' no meio ou no fim vira "[a-z]*"
        partes.append(rf'(?<![a-z0-9]){corpo}' + ('' if t.endswith('*') else r'(?![a-z0-9])'))
    return re.compile('|'.join(partes))


_REGEX = {a: _regex(ts) for a, ts in ASSUNTOS.items()}
_EXCLUIR = _regex(EXCLUSOES)


def classificar(*textos: str) -> list[str]:
    bruto = ' '.join(t for t in textos if t)
    alvo = _EXCLUIR.sub(' ', norm(bruto))
    tem_ticker = bool(TICKER_RE.search(bruto))
    return [a for a, rx in _REGEX.items() if rx.search(alvo) or (a == 'Bolsa' and tem_ticker)]

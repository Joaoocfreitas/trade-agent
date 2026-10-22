"""O que o mercado espera e as datas marcadas, de fonte oficial do Banco Central.

- Boletim Focus (olinda, recurso ExpectativasMercadoAnuais e ExpectativasMercadoSelic): a mediana mais recente para
  Selic, IPCA, câmbio e PIB, e a da próxima reunião do Copom. Base de cálculo 0 (últimos 30 dias), a da manchete do
  boletim.
- O Focus também erra: para cada ano já fechado desde 2021, a última mediana registrada no ano anterior. O realizado sai
  das séries que o estudo já baixa (PTAX, meta Selic e IPCA em 12 meses), não daqui.
- Agenda do Copom (www.bcb.gov.br/api/servico/sitebcb/calendario/anual): os dias das reuniões que ainda não aconteceram.
  A decisão sai no 2º dia, depois das 18h30 (comunicados de calendário 43.383 e 45.452).

Armadilhas (conferidas em 22/10/2026): o nome do indicador tem de ir com acento e em UTF-8 ('Câmbio'; 'Cambio' devolve
lista vazia, sem erro), 'PIB Total' e não 'PIB', DataReferencia é texto (sem aspas dá HTTP 400) e lista vazia é falha,
nunca "sem expectativa". Reunião ordenada como texto sai errada ('R1/2027' antes de 'R7/2026').
"""
import json
from datetime import date
from pathlib import Path
from urllib.parse import quote

import pandas as pd

from .series import Cliente
from .surpresa import _ordem_reuniao

OLINDA = 'https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata'
AGENDA = 'https://www.bcb.gov.br/api/servico/sitebcb/calendario/anual'
INDICADORES = ('Selic', 'IPCA', 'Câmbio', 'PIB Total')
ANO_INICIAL_ERRO = 2021


def _filtro(expr: str) -> str:
    return quote(expr, safe="'=")


def url_anual(indicador: str, ano: int, ate: str | None = None) -> str:
    """A mediana mais recente do Focus para `indicador` em `ano`; com `ate` (AAAA-MM-DD), a última até esse dia."""
    expr = f"Indicador eq '{indicador}' and DataReferencia eq '{ano}' and baseCalculo eq 0"
    if ate:
        expr += f" and Data le '{ate}'"
    return f'{OLINDA}/ExpectativasMercadoAnuais?$filter={_filtro(expr)}&$orderby=Data%20desc&$top=1&$format=json'


def url_selic_reunioes(desde: str) -> str:
    expr = f"Data ge '{desde}' and baseCalculo eq 0"
    return f'{OLINDA}/ExpectativasMercadoSelic?$filter={_filtro(expr)}&$orderby=Data%20desc&$top=100&$format=json'


def url_agenda(inicio: date, fim: date) -> str:
    return (f"{AGENDA}?lista={quote('Reuniões do Copom')}&inicioAgenda=%27{inicio.isoformat()}%27"
            f"&fimAgenda=%27{fim.isoformat()}%27")


# ---------- leitura (funções puras, testadas) ----------

def ler_anual(registros: list[dict]) -> dict:
    if not registros:
        raise ValueError('o Focus devolveu lista vazia: nome do indicador ou filtro errado')
    r = registros[0]
    return {'data': r['Data'], 'mediana': float(r['Mediana']), 'minimo': float(r['Minimo']), 'maximo': float(r['Maximo']),
            'respondentes': int(r['numeroRespondentes'])}


def ler_proxima_reuniao(registros: list[dict]) -> dict:
    """Do Focus por reunião, no dia mais recente, a reunião mais próxima (a menor por ano e número)."""
    if not registros:
        raise ValueError('o Focus por reunião devolveu lista vazia')
    ultimo = max(r['Data'] for r in registros)
    do_dia = [r for r in registros if r['Data'] == ultimo]
    r = min(do_dia, key=lambda x: _ordem_reuniao(x['Reuniao']))
    return {'data': r['Data'], 'reuniao': r['Reuniao'], 'mediana': float(r['Mediana']),
            'respondentes': int(r['numeroRespondentes'])}


def ler_agenda(resposta: dict) -> list[dict]:
    """Os dias de reunião (eventos de dia inteiro em 03:00Z, que é a meia-noite em Brasília) agrupados em reuniões de 2
    dias seguidos; a decisão é o 2º dia."""
    dias = sorted({pd.Timestamp(e['dataEvento']).tz_convert('America/Sao_Paulo').date()
                   for e in resposta.get('conteudo', []) if e.get('evento') == 'Reunião do Copom'})
    reunioes, i = [], 0
    while i < len(dias):
        if i + 1 < len(dias) and (dias[i + 1] - dias[i]).days == 1:
            reunioes.append({'inicio': dias[i].isoformat(), 'decisao': dias[i + 1].isoformat()})
            i += 2
        else:
            raise ValueError(f'reunião do Copom sem o 2º dia: {dias[i]}')
    return reunioes


# ---------- download ----------

def baixar_expectativas(c: Cliente, pasta: Path, hoje: date) -> dict:
    """Grava pasta/focus.json: a última mediana de cada indicador, a da próxima reunião, o histórico e a agenda."""
    atual = {}
    for ind in INDICADORES:
        for ano in ((hoje.year, hoje.year + 1) if ind in ('IPCA', 'Câmbio') else (hoje.year,)):
            atual[f'{ind}|{ano}'] = ler_anual(c.json(url_anual(ind, ano))['value'])
    desde = (pd.Timestamp(hoje) - pd.Timedelta(days=21)).date().isoformat()
    proxima = ler_proxima_reuniao(c.json(url_selic_reunioes(desde))['value'])
    historico = {}
    for ano in range(ANO_INICIAL_ERRO, hoje.year):
        historico[str(ano)] = {ind: ler_anual(c.json(url_anual(ind, ano, f'{ano - 1}-12-31'))['value'])
                               for ind in ('Selic', 'IPCA', 'Câmbio')}
    agenda = [r for r in ler_agenda(c.json(url_agenda(hoje, date(hoje.year + 1, 12, 31))))
              if r['decisao'] >= hoje.isoformat()]
    datas = {v['data'] for v in atual.values()}
    if len(datas) != 1:
        raise ValueError(f'os indicadores do Focus vieram de dias diferentes: {sorted(datas)}')
    saida = {'baixado_em': pd.Timestamp.now(tz='America/Sao_Paulo').isoformat(timespec='seconds'),
             'data': datas.pop(), 'atual': atual, 'proxima_reuniao': proxima, 'historico': historico,
             'agenda_copom': agenda}
    destino = pasta / 'focus.json'
    tmp = destino.with_suffix('.json.parcial')
    tmp.write_text(json.dumps(saida, ensure_ascii=False, indent=1), encoding='utf-8')
    tmp.replace(destino)
    return saida

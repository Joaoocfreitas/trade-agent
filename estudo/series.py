"""Baixa e lê as séries oficiais do estudo.

- Ibovespa: Ipeadata, série GM366_IBVSP366, que republica o fechamento da B3. O Ipeadata tem pontos falsos (16 fins de
  semana e 3 feriados com valor quebrado, de 2016 a 2024); `limpar_ibov` tira esses pontos. Conferência: SGS 7 do
  Banco Central (até 2019) e, quando o João mandar, os arquivos da própria B3.
- Dólar PTAX venda (SGS 1), euro PTAX venda (SGS 21619), Selic meta (SGS 432), IPCA em 12 meses (SGS 13522) e
  dívida bruta do governo geral em % do PIB (SGS 13762): API do Banco Central.
- Juros prefixados: CSV de taxas do Tesouro Direto (Tesouro Prefixado e Prefixado com Juros Semestrais).

O Yahoo Finance foi descartado de propósito: o robots.txt de query1.finance.yahoo.com proíbe qualquer robô.
Poucos pedidos, um por vez, robots.txt checado em cada endereço e em cada redirecionamento.
"""
import io
import json
import time
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
import pandas as pd

from coletor.config import ROBO, TIMEOUT_S, USER_AGENT
from coletor.robots import interpretar

SGS = {'ptax': 1, 'euro': 21619, 'selic_meta': 432, 'ibov_bcb': 7, 'ipca_12m': 13522, 'divida_bruta': 13762}
IPEA_IBOV = 'GM366_IBVSP366'
TD_CSV = ('https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/resource/'
          '796d2059-14e9-44e3-80c9-2d9e30b405c1/download/precotaxatesourodireto.csv')
PREFIXADOS = ('Tesouro Prefixado', 'Tesouro Prefixado com Juros Semestrais')
INTERVALO_S = 1.5
MAX_ANOS_SGS = 10  # a API do SGS recusa janelas maiores que 10 anos


# Exceção estreita à regra do robots.txt: a API do Focus (Portal de Dados Abertos do BC) responde 502 para qualquer
# endereço fora da API, robots.txt inclusive, o que pela RFC 9309 seria "não entre". É uma API oficial documentada
# para acesso por programa, e o robots.txt do site principal do BC (www.bcb.gov.br) libera tudo. Só este caminho.
API_OFICIAL_SEM_ROBOTS = ('https://olinda.bcb.gov.br/olinda/servico/',)


class Proibido(Exception):
    pass


class Cliente:
    """httpx síncrono com robots.txt por host, redirecionamento à mão e intervalo entre pedidos."""

    def __init__(self):
        self.http = httpx.Client(headers={'User-Agent': USER_AGENT}, timeout=TIMEOUT_S * 6, follow_redirects=False)
        self._regras = {}
        self._ultimo = 0.0

    def _esperar(self) -> None:
        espera = self._ultimo + INTERVALO_S - time.monotonic()
        if espera > 0:
            time.sleep(espera)
        self._ultimo = time.monotonic()

    def permitido(self, url: str) -> bool:
        if url.startswith(API_OFICIAL_SEM_ROBOTS):
            return True
        p = urlparse(url)
        base = f'{p.scheme}://{p.netloc}'
        if base not in self._regras:
            self._esperar()
            try:
                r = self.http.get(f'{base}/robots.txt', follow_redirects=True)
                self._regras[base] = interpretar(r.status_code, r.text)
            except httpx.HTTPError:
                self._regras[base] = interpretar(None, '')
        regra = self._regras[base]
        return regra if isinstance(regra, bool) else regra.can_fetch(url, ROBO)

    def _seguir(self, url: str, tentativas: int = 4):
        """Segue redirecionamentos checando robots em cada salto; espera e repete em 429/503."""
        atual = url
        for _ in range(6):
            if not self.permitido(atual):
                raise Proibido(f'robots.txt não permite {atual}')
            for n in range(tentativas):
                self._esperar()
                req = self.http.build_request('GET', atual)
                try:
                    r = self.http.send(req, stream=True)
                except httpx.TransportError:
                    # O Tesouro Transparente derruba a conexão quando recebe um pedido logo depois do outro (limite
                    # por endereço; às vezes responde 429 com Retry-After de 30 s). Espera de verdade e repete.
                    if n == tentativas - 1:
                        raise
                    time.sleep(min(15 * 2 ** n, 120))
                    continue
                if r.status_code in (429, 503) and n < tentativas - 1:
                    r.close()
                    time.sleep(min(float(r.headers.get('retry-after', 30) or 30), 120))
                    continue
                break
            if r.is_redirect and 'location' in r.headers:
                r.close()
                atual = urljoin(atual, r.headers['location'])
                continue
            if r.status_code >= 400:
                r.read()
                r.close()
                r.raise_for_status()
            return r
        raise RuntimeError('redirecionamentos demais')

    def json(self, url: str):
        r = self._seguir(url)
        try:
            return json.loads(r.read())
        finally:
            r.close()

    def arquivo(self, url: str, destino: Path) -> Path:
        destino.parent.mkdir(parents=True, exist_ok=True)
        tmp = destino.with_suffix(destino.suffix + '.parcial')
        r = self._seguir(url)
        try:
            with tmp.open('wb') as f:
                for pedaco in r.iter_bytes():
                    f.write(pedaco)
        finally:
            r.close()
        tmp.replace(destino)
        return destino


# ---------- leitura (funções puras, testadas) ----------

def ler_sgs(registros: list[dict]) -> pd.Series:
    s = pd.Series({pd.Timestamp(date(int(r['data'][6:]), int(r['data'][3:5]), int(r['data'][:2]))): float(r['valor'])
                   for r in registros if r.get('valor') not in (None, '')}, dtype=float)
    return s.sort_index()


def ler_ipeadata(valores: list[dict]) -> pd.Series:
    s = pd.Series({pd.Timestamp(v['VALDATA'][:10]): float(v['VALVALOR']) for v in valores
                   if v.get('VALVALOR') is not None}, dtype=float)
    return s.sort_index()


def limpar_ibov(s: pd.Series) -> tuple[pd.Series, list[str]]:
    """Tira os pontos que não são pregão: fim de semana e valor com casas decimais (o fechamento da B3 no Ipeadata é
    sempre inteiro; os pontos falsos, como 05/02/2022 = 101.005,64 entre 112 mil e 112 mil, têm centavos)."""
    falso = (s.index.dayofweek >= 5) | ((s % 1).abs() > 1e-9)
    return s[~falso], [f'{d.date()}={v}' for d, v in s[falso].items()]


def ler_tesouro(conteudo: bytes) -> pd.DataFrame:
    """CSV do Tesouro Direto: separador ';', decimal ',', datas dd/mm/aaaa. Devolve só os prefixados."""
    texto = conteudo.decode('utf-8-sig', errors='replace') if conteudo[:3] == b'\xef\xbb\xbf' else conteudo.decode('latin-1')
    df = pd.read_csv(io.StringIO(texto), sep=';', decimal=',', dtype=str)
    df.columns = [c.strip() for c in df.columns]
    df = df[df['Tipo Titulo'].str.strip().isin(PREFIXADOS)].copy()
    df['data'] = pd.to_datetime(df['Data Base'], format='%d/%m/%Y')
    df['vencimento'] = pd.to_datetime(df['Data Vencimento'], format='%d/%m/%Y')
    df['taxa'] = pd.to_numeric(df['Taxa Compra Manha'].str.replace(',', '.'), errors='coerce')
    df = df.dropna(subset=['taxa'])
    df = df[df['taxa'] > 0]  # título fora de oferta aparece com taxa zero
    return df[['data', 'vencimento', 'taxa']].sort_values(['data', 'vencimento']).reset_index(drop=True)


def curva_constante(pre: pd.DataFrame, anos: float, folga: float = 0.75) -> pd.Series:
    """Taxa prefixada a prazo constante, interpolada linearmente entre os dois títulos que cercam o prazo.

    Sem extrapolar: se não há título dos dois lados, só vale o mais próximo e só se estiver a menos de `folga` anos.
    """
    saida = {}
    for dia, g in pre.groupby('data'):
        prazos = ((g['vencimento'] - dia).dt.days / 365.25).to_numpy()
        taxas = g['taxa'].to_numpy()
        abaixo, acima = prazos <= anos, prazos >= anos
        if abaixo.any() and acima.any():
            i = prazos[abaixo].argmax()
            j = prazos[acima].argmin()
            p0, t0 = prazos[abaixo][i], taxas[abaixo][i]
            p1, t1 = prazos[acima][j], taxas[acima][j]
            saida[dia] = t0 if p1 == p0 else t0 + (t1 - t0) * (anos - p0) / (p1 - p0)
        else:
            k = abs(prazos - anos).argmin()
            if abs(prazos[k] - anos) <= folga:
                saida[dia] = taxas[k]
    return pd.Series(saida, dtype=float).sort_index()


# ---------- download ----------

def baixar_sgs(c: Cliente, codigo: int, inicio: date, fim: date) -> pd.Series:
    """Uma série do SGS inteira, em janelas de até 10 anos."""
    partes, a = [], inicio
    while a <= fim:
        b = min(date(a.year + MAX_ANOS_SGS - 1, 12, 31), fim)
        url = (f'https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json'
               f'&dataInicial={a:%d/%m/%Y}&dataFinal={b:%d/%m/%Y}')
        try:
            partes.append(ler_sgs(c.json(url)))
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 404:  # 404 = série sem valor no período (a 7 parou em 2019)
                raise
        a = date(b.year + 1, 1, 1)
    s = pd.concat(partes).sort_index() if partes else pd.Series(dtype=float)
    return s[~s.index.duplicated()]


def baixar_tudo(pasta: Path, inicio: date, fim: date, pular: frozenset = frozenset()) -> dict:
    """Baixa tudo para `pasta` (CSV por série) e devolve o manifesto com fonte, cobertura e data do download.
    Cada fonte é um passo: se uma falha (fora do ar, robots.txt que não responde), as outras seguem e, no fim, a falha
    sobe junto com a lista. `pular`: séries que não devem ser pedidas (as desligadas da rodada diária)."""
    pasta.mkdir(parents=True, exist_ok=True)
    c = Cliente()
    manifesto = {}

    def guardar(nome: str, s: pd.Series, fonte: str) -> None:
        s = s[(s.index >= pd.Timestamp(inicio)) & (s.index <= pd.Timestamp(fim))]
        s.rename(nome).to_csv(pasta / f'{nome}.csv', index_label='data')
        manifesto[nome] = {'fonte': fonte, 'n': int(s.size), 'de': str(s.index.min().date()) if s.size else None,
                           'ate': str(s.index.max().date()) if s.size else None}
        print(f'  {nome:12} {s.size:5} pontos  {manifesto[nome]["de"]} → {manifesto[nome]["ate"]}  ({fonte})', flush=True)

    falhas = []

    def passo(nome: str, fazer) -> None:
        try:
            fazer()
        except Exception as e:  # noqa: BLE001 — as outras fontes seguem; a falha sobe no fim
            falhas.append(f'{nome}: {type(e).__name__}: {e}')
            print(f'  {nome:12} FALHOU: {type(e).__name__}: {e}', flush=True)

    def ibov() -> None:
        s = ler_ipeadata(c.json(f"http://www.ipeadata.gov.br/api/odata4/ValoresSerie(SERCODIGO='{IPEA_IBOV}')")['value'])
        # só no período do estudo: antes de 2015 o índice tinha casas decimais de verdade
        s, falsos = limpar_ibov(s[(s.index >= pd.Timestamp(inicio)) & (s.index <= pd.Timestamp(fim))])
        guardar('ibov', s, f'Ipeadata {IPEA_IBOV} (republica o fechamento da B3), sem {len(falsos)} pontos falsos')
        manifesto['ibov']['pontos_falsos_retirados'] = falsos

    def tesouro() -> None:
        bruto = c.arquivo(TD_CSV, pasta / 'brutos' / 'precotaxatesourodireto.csv')
        pre = ler_tesouro(bruto.read_bytes())
        for anos in (2, 5):
            guardar(f'pre_{anos}a', curva_constante(pre, anos), f'Tesouro Direto, prefixados interpolados a {anos} anos')

    if 'ibov' not in pular:
        passo('ibov', ibov)
    for nome, codigo in SGS.items():
        if nome not in pular:
            passo(nome, lambda nome=nome, codigo=codigo: guardar(nome, baixar_sgs(c, codigo, inicio, fim),
                                                                   f'Banco Central SGS {codigo}'))
    if not {'pre_2a', 'pre_5a'} <= pular:
        passo('tesouro', tesouro)

    manifesto['_baixado_em'] = pd.Timestamp.now(tz='America/Sao_Paulo').isoformat(timespec='seconds')
    (pasta / 'manifesto.json').write_text(json.dumps(manifesto, ensure_ascii=False, indent=1), encoding='utf-8')
    if falhas:
        raise RuntimeError('; '.join(falhas))
    return manifesto

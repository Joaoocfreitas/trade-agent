"""A base de fatos do agente: cada linha tem número formatado e fonte, e vem dos arquivos de `dados/`.

Nada aqui é escrito pela IA. O modo com IA recebe estes blocos prontos e só pode citar os números que estão neles (D8).
"""
import json
import re
from dataclasses import dataclass, field
from decimal import ROUND_HALF_EVEN, Decimal
from functools import cache

import pandas as pd

from coletor.config import DADOS, FONTES_DIR
from estudo.series import TD_CSV
from estudo.surpresa import FOCUS

SERIES = DADOS / 'series'
ESTUDO = DADOS / 'estudo'
PRODUTO = DADOS / 'produto'
AGENTE = DADOS / 'agente'

MESES = ('janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro',
         'novembro', 'dezembro')


@dataclass(frozen=True)
class Fonte:
    nome: str
    url: str = ''


@dataclass
class Linha:
    texto: str
    fontes: tuple[Fonte, ...] = ()


@dataclass
class Bloco:
    titulo: str
    linhas: list[Linha] = field(default_factory=list)
    resumo: str = ''  # uma linha para as "3 linhas" do topo
    limites: list[str] = field(default_factory=list)

    def add(self, texto: str, *fontes: Fonte) -> None:
        self.linhas.append(Linha(texto, tuple(fontes)))


# ---------- formatação ----------

def num(x: float, casas: int = 1) -> str:
    s = f'{abs(x):,.{casas}f}'.replace(',', '_').replace('.', ',').replace('_', '.')
    return ('−' if x < 0 and float(s.replace('.', '').replace(',', '.')) else '') + s


def sinal(x: float, casas: int = 1) -> str:
    s = num(abs(x), casas)
    if float(s.replace('.', '').replace(',', '.')) == 0:
        return s
    return ('+' if x > 0 else '−') + s


def juntar(xs: list[str]) -> str:
    return xs[0] if len(xs) == 1 else ', '.join(xs[:-1]) + ' e ' + xs[-1]


VERBOS = {False: ('subiu', 'caiu', 'ficou estável', 'foi'), True: ('subiram', 'caíram', 'ficaram estáveis', 'foram')}


PONTOS_BASE = ' pontos-base'
EXPLICA_PB = ' (100 pontos-base = 1 ponto percentual)'


def mov(x: float, casas: int = 1, un: str = '%', plural: bool = False) -> str:
    """Variação em palavras, para quem está começando: 'subiu 1,3%', 'caiu 2,2%' ('os juros subiram', com plural)."""
    sobe, cai, parado, _ = VERBOS[plural]
    s = num(abs(x), casas)
    if float(s.replace('.', '').replace(',', '.')) == 0:
        return parado
    return f'{sobe if x > 0 else cai} {s}{un}'


def movs(xs, casas: int = 1, un: str = '%', plural: bool = False) -> str:
    """Poucos casos, cada um em palavras: 'caiu 1,0% e 1,7%' quando foram para o mesmo lado; 'caiu 2,2% e subiu 1,3%'
    quando não."""
    sobe, cai, _, _ = VERBOS[plural]
    xs = [float(x) for x in xs]
    textos = [mov(x, casas, un, plural) for x in xs]
    for verbo in (sobe, cai):
        if all(t.startswith(verbo + ' ') for t in textos):
            return f'{verbo} ' + juntar([t[len(verbo) + 1:] for t in textos])
    return juntar(textos)


def faixa_mov(lo: float, hi: float, casas: int = 1, un: str = '%', plural: bool = False) -> str:
    """De lo a hi em palavras: 'subiu de 4,6% a 7,7%', 'caiu de 0,5% a 3,2%', 'foi de queda de 2,0% a alta de 1,5%'."""
    sobe, cai, _, foi = VERBOS[plural]
    lo, hi = float(lo), float(hi)
    if lo > 0:
        return f'{sobe} de {num(lo, casas)}{un} a {num(hi, casas)}{un}'
    if hi < 0:
        return f'{cai} de {num(abs(hi), casas)}{un} a {num(abs(lo), casas)}{un}'
    ponta = lambda x: (f'queda de {num(abs(x), casas)}{un}' if x < 0 else f'alta de {num(x, casas)}{un}' if x > 0  # noqa: E731
                       else 'estabilidade')
    return f'{foi} de {ponta(lo)} a {ponta(hi)}'


def curto(x: float, casas_linha: int, casas: int) -> float:
    """Arredonda para o resumo a partir do número já escrito na linha, com a regra do filtro (D8: meio para o par). Sem
    isso, 5,6450 na linha viraria 5,65 no resumo pelo f-string e 5,64 no filtro, e a resposta cairia na de segurança."""
    d = Decimal(f'{abs(x):.{casas_linha}f}').quantize(Decimal(1).scaleb(-casas), ROUND_HALF_EVEN)
    return float(d) * (1 if x >= 0 else -1)


def dia(d) -> str:
    return pd.Timestamp(d).strftime('%d/%m/%Y')


def mes(d) -> str:
    d = pd.Timestamp(d)
    return f'{MESES[d.month - 1]} de {d.year}'


# ---------- fontes ----------

def _sgs(codigo: int, nome: str) -> Fonte:
    return Fonte(f'Banco Central, SGS {codigo} ({nome})',
                 f'https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados/ultimos/1?formato=json')


F_SELIC = _sgs(432, 'meta da Selic')
F_PTAX = _sgs(1, 'dólar PTAX de venda')
F_EURO = _sgs(21619, 'euro PTAX de venda')
F_IPCA = _sgs(13522, 'IPCA em 12 meses, do IBGE')
F_DIVIDA = _sgs(13762, 'dívida bruta do governo geral, % do PIB')
F_IBOV = Fonte('Ipeadata, série GM366_IBVSP366 (fechamento do Ibovespa na B3)',
               "http://www.ipeadata.gov.br/api/odata4/ValoresSerie(SERCODIGO='GM366_IBVSP366')")
F_TESOURO = Fonte('Tesouro Direto, taxas dos títulos prefixados (Tesouro Transparente)', TD_CSV)
F_COPOM = Fonte('Banco Central, comunicados do Copom', 'https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados?quantidade=100')
F_FOCUS = Fonte('Banco Central, boletim Focus (expectativa da Selic por reunião)', FOCUS)
F_FOCUS_ANUAL = Fonte('Banco Central, boletim Focus (expectativas anuais: mediana das instituições que respondem)',
                      'https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoAnuais')
F_AGENDA_COPOM = Fonte('Banco Central, agenda das reuniões do Copom (decisão no 2º dia, depois das 18h30)',
                       'https://www.bcb.gov.br/api/servico/sitebcb/calendario/anual?lista=Reuni%C3%B5es%20do%20Copom')
F_CF77 = Fonte('Constituição Federal, art. 77 (o 2º turno é no último domingo de outubro)',
               'https://www.planalto.gov.br/ccivil_03/constituicao/constituicao.htm')
F_ESTUDO = Fonte('Cálculo próprio: estudo de evento 2016–2026 sobre as séries oficiais (método no cofre, nota '
                 '"Estudo de evento 2016–2026")')
F_B3_WIN = Fonte('B3, especificação do mini-índice', 'https://b3.com.br/pt_br/produtos-e-servicos/negociacao/renda-variavel/futuro-mini-de-ibovespa.htm')
F_B3_WDO = Fonte('B3, especificação do mini-dólar', 'https://b3.com.br/pt_br/produtos-e-servicos/negociacao/moedas/futuro-mini-de-taxa-de-cambio-de-reais-por-dolar-comercial.htm')
F_B3_DI1 = Fonte('B3, especificação do DI1', 'https://b3.com.br/pt_br/produtos-e-servicos/negociacao/juros/futuro-de-taxa-media-de-depositos-interfinanceiros-de-um-dia.htm')
F_B3_MARGEM = Fonte('B3, margem mínima de day trade para minicontratos', 'https://b3.com.br/pt_br/solucoes/plataformas/puma-trading-system/para-participantes-e-traders/regras-e-parametros-de-negociacao/margem-minima-requerida-e-guia-educacional-para-minicontratos/')
F_B3_GLOSSARIO = Fonte('B3 (Bora Investir), glossário: margem de garantia', 'https://borainvestir.b3.com.br/glossario/margem-de-garantia/')
F_FGV = Fonte('Chague, De-Losso e Giovannetti, "Day trading for a living?" (FGV EESP e USP, dados da CVM)', 'http://www.repec.eae.fea.usp.br/documentos/Chague_Losso_Giovannetti_47WP.pdf')
F_LEI_11033 = Fonte('Lei 11.033/2004 (IR sobre ações)', 'https://www.planalto.gov.br/ccivil_03/_ato2004-2006/2004/lei/l11033.htm')
F_RECEITA_ISENCAO = Fonte('Receita Federal, isenções na bolsa', 'https://www.gov.br/receitafederal/pt-br/assuntos/meu-imposto-de-renda/pagamento/renda-variavel/bolsa-de-valores-1/isencoes')
F_LEI_14478 = Fonte('Lei 14.478/2022 (ativos virtuais)', 'https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2022/lei/l14478.htm')
F_PARECER_40 = Fonte('Parecer de Orientação CVM 40/2022', 'https://conteudo.cvm.gov.br/legislacao/pareceres-orientacao/pare040.html')
F_BCB_520 = Fonte('Resolução BCB 520/2025', 'https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo?tipo=Resolu%C3%A7%C3%A3o%20BCB&numero=520')
F_IN_704 = Fonte('Instrução Normativa BCB 704', 'https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo?tipo=Instru%C3%A7%C3%A3o%20Normativa%20BCB&numero=704')
F_CMN_5298 = Fonte('Resolução CMN 5.298/2026', 'https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo?tipo=Resolu%C3%A7%C3%A3o%20CMN&numero=5298')
F_B3_EVENTOS = Fonte('B3, contratos de evento', 'https://clientes.b3.com.br/en/w/contratos-de-eventos')
F_CVM_IQ = Fonte('CVM, decisão do Colegiado de 02/06/2020 sobre a IQ Option (Ato Declaratório 17.790)', 'https://conteudo.cvm.gov.br/decisoes/2020/20200602_R1.html')
F_LEI_9504 = Fonte('Lei 9.504/1997, art. 33 (registro de pesquisa eleitoral)', 'https://www.planalto.gov.br/ccivil_03/leis/l9504.htm')
F_COINGECKO_TRUMP = Fonte('CoinGecko, $TRUMP', 'https://www.coingecko.com/en/coins/official-trump')
F_COINGECKO_MELANIA = Fonte('CoinGecko, $MELANIA', 'https://www.coingecko.com/en/coins/melania-meme')
F_THEBLOCK_TRUMP = Fonte('The Block, com dados da Nansen, 04/07/2026', 'https://theblock.co/post/407170/nearly-1-million-wallets-are-down-3-81-billion-on-trumps-memecoin-report')
F_THEBLOCK_LIBRA = Fonte('The Block, com dados da Nansen, sobre o $LIBRA', 'https://www.theblock.co/post/342266/traders-of-solana-based-libra-memecoin-lost-251-million-nansen')


# ---------- leitura ----------

@cache
def serie(nome: str) -> pd.Series:
    df = pd.read_csv(SERIES / f'{nome}.csv', parse_dates=['data'], index_col='data')
    return df[nome].astype(float).dropna()


@cache
def _json(caminho: str):
    return json.loads((DADOS / caminho).read_text(encoding='utf-8'))


@cache
def _csv(nome: str) -> pd.DataFrame:
    return pd.read_csv(ESTUDO / nome)


def _ultimo(nome: str) -> tuple[pd.Timestamp, float]:
    s = serie(nome)
    return s.index[-1], float(s.iloc[-1])


# ---------- blocos ----------

RESUMO_HOJE = 'Hoje, pelo dado oficial:'  # o resumo da economia vai por último nas 3 linhas


def economia() -> Bloco:
    b = Bloco('A economia hoje (dado oficial, com a data de cada número)')
    copom = _csv('copom_completo.csv')
    ult = copom.iloc[-1]
    d_selic, selic = _ultimo('selic_meta')
    d_ipca, ipca = _ultimo('ipca_12m')
    d_ptax, ptax = _ultimo('ptax')
    d_ibov, ibov = _ultimo('ibov')
    d_pre5, pre5 = _ultimo('pre_5a')
    d_div, div = _ultimo('divida_bruta')
    b.add(f'Selic: {num(selic, 2)}% ao ano, decidida pelo Copom em {dia(ult.decisao)} (valor em {dia(d_selic)}).', F_SELIC, F_COPOM)
    b.add(f'Inflação (IPCA em 12 meses): {num(ipca, 2)}% até {mes(d_ipca)}.', F_IPCA)
    b.add(f'Dólar (PTAX de venda): R$ {num(ptax, 4)} em {dia(d_ptax)}.', F_PTAX)
    b.add(f'Ibovespa: {num(ibov, 0)} pontos no fechamento de {dia(d_ibov)}.', F_IBOV)
    b.add(f'Juro prefixado de 5 anos (cálculo próprio sobre as taxas do Tesouro Direto): {num(pre5, 2)}% ao ano em '
          f'{dia(d_pre5)}.', F_TESOURO, F_ESTUDO)
    b.add(f'Dívida bruta do governo geral: {num(div, 2)}% do PIB em {mes(d_div)}.', F_DIVIDA)
    b.resumo = (f'{RESUMO_HOJE} juros básicos (Selic) de {num(selic, 2)}% ao ano, inflação de {num(ipca, 2)}% em 12 meses '
                f'(até {mes(d_ipca)}) e dólar a R$ {num(curto(ptax, 4, 2), 2)} (cotação oficial de {dia(d_ptax)}).')
    return b


def _proximo_pregao(d) -> pd.Timestamp:
    s = serie('ibov')
    return s.index[s.index > pd.Timestamp(d)][0]


# Taxa-base de cada mercado medido: série, limite de "dia grande" e unidade. Juros em pontos-base (p.b.).
TAXA = {'ibovespa': ('ibov', 4.0, '%', F_IBOV), 'dolar': ('ptax', 1.0, '%', F_PTAX), 'euro': ('euro', 1.0, '%', F_EURO),
        'juros': ('pre_5a', 30.0, ' p.b.', F_TESOURO)}


def _variacoes(nome: str) -> pd.Series:
    s = serie(nome)
    s = s[s.index >= pd.Timestamp('2016-01-01')]
    return (s.diff() * 100 if nome.startswith('pre_') else s.pct_change() * 100).dropna()


def taxa_base(mercado: str, nome_exibido: str) -> Linha:
    """Em pregões comuns: com que frequência o mercado andou mais que o limite, para cada lado, e a variação típica."""
    serie_nome, limite, un, fonte = TAXA[mercado]
    r = _variacoes(serie_nome)
    sobe, cai = float((r > limite).mean() * 100), float((r < -limite).mean() * 100)
    casas = 0 if un.strip() == 'p.b.' else 2
    return Linha(f'Taxa-base do {nome_exibido}: nos {num(r.size, 0)} pregões de {dia(r.index[0])} a {dia(r.index[-1])}, ele subiu '
                 f'mais de {num(limite, 0)}{un} em {num(sobe, 1)}% dos dias e caiu mais de {num(limite, 0)}{un} em '
                 f'{num(cai, 1)}%; a variação típica (mediana, em módulo) foi de {num(float(r.abs().median()), casas)}{un}.',
                 (fonte, F_ESTUDO))


MEDIDA = {
    'ibovespa': ('Ibovespa', 'ibov_d0', '%', 100, 2, F_IBOV),
    'dolar': ('dólar', 'ptax_d0', '%', 100, 2, F_PTAX),
    'juros': ('juros de 5 anos', 'pre5_d0_pb', ' p.b.', 1, 1, F_TESOURO),
}


# O mercado até aqui: nome com artigo, série, fonte e formato do nível.
HISTORICO = {
    'ibovespa': ('o Ibovespa', 'ibov', F_IBOV, lambda v: f'{num(v, 0)} pontos'),
    'dolar': ('o dólar', 'ptax', F_PTAX, lambda v: f'R$ {num(v, 4)}'),
    'euro': ('o euro', 'euro', F_EURO, lambda v: f'R$ {num(v, 4)}'),
    'juros': ('o juro prefixado de 5 anos', 'pre_5a', F_TESOURO, lambda v: f'{num(v, 2)}% ao ano'),
}


def historico(mercado: str) -> Bloco:
    """O caminho que o mercado já fez, só passado e dado oficial: o nível de hoje, os 12 meses, o ano e a taxa-base."""
    nome, serie_nome, fonte, fmt = HISTORICO[mercado]
    s = serie(serie_nome)
    d_fim, fim = s.index[-1], float(s.iloc[-1])
    doze = s[s.index > d_fim - pd.DateOffset(years=1)]
    d_lo, d_hi = doze.idxmin(), doze.idxmax()
    juros = serie_nome.startswith('pre_')
    rotulo = 'cálculo próprio sobre dado oficial' if juros else 'dado oficial'
    b = Bloco(f'{nome[0].upper() + nome[1:]} até aqui ({rotulo}, só o que já aconteceu)')
    fontes = (fonte, F_ESTUDO) if juros else (fonte,)
    b.add(f'Em {dia(d_fim)}: {fmt(fim)}.', *fontes)
    b.add(f'Nos 12 meses até {dia(d_fim)}, foi de {fmt(float(doze[d_lo]))} ({dia(d_lo)}) a {fmt(float(doze[d_hi]))} '
          f'({dia(d_hi)}).', *fontes)
    antes = s[s.index.year < d_fim.year]
    if len(antes):
        d_ini, ini = antes.index[-1], float(antes.iloc[-1])  # o fechamento do ano anterior, a mesma base do erro do Focus
        var, un, casas = ((fim - ini) * 100, ' p.b.', 0) if juros else ((fim / ini - 1) * 100, '%', 2)
        b.add(f'No ano, do fechamento de {d_ini.year} ({fmt(ini)}, {dia(d_ini)}) a {fmt(fim)} ({dia(d_fim)}): '
              f'{sinal(var, casas)}{un}.', fonte, F_ESTUDO)
    b.linhas.append(taxa_base(mercado, nome.split(' ', 1)[1]))
    b.limites.append('É o caminho que o preço já fez; o próximo pode ser outro.')
    if mercado == 'dolar':
        b.limites.append('Os números do dólar são da PTAX de venda (dólar à vista, do Banco Central), não de contrato futuro '
                         'de dólar, que tem vencimento e preço próprios.')
    if mercado == 'euro':
        b.limites.append(LIMITE_PTAX_EURO)
    # Para quem está começando: o nível arredondado, o ano em palavras e a faixa dos 12 meses.
    nivel = (lambda v: f'R$ {num(curto(v, 4, 2), 2)}') if mercado in ('dolar', 'euro') else fmt
    nome_cap = nome[0].upper() + nome[1:]
    ano = ''
    if len(antes) and not juros:
        ano = f' No ano, {mov(curto(var, 2, 1), 1)}.'
    b.resumo = (f'{nome_cap} está em {nivel(fim)} ({dia(d_fim)}).{ano} Nos últimos 12 meses, foi de '
                f'{nivel(float(doze[d_lo]))} a {nivel(float(doze[d_hi]))}.')
    return b


LIMITE_PTAX_EURO = ('Os números do euro são da PTAX de venda do Banco Central. Na troca de verdade (banco, corretora, '
                    'app de remessa), a cotação é outra e pode haver tarifa, spread e IOF.')


# ---------- os dois lados: quando caiu e quando subiu (P2, sem manchete de direção) ----------

TITULO_DOIS_LADOS = 'Os dois lados, no que já aconteceu'
MES_PREGOES = 21  # cerca de um mês de pregões


def _lado(v: float, casas: int, un: str, queda: bool) -> str:
    """O maior movimento de um lado, em palavras; se esse lado não aconteceu na janela, diz isso."""
    if (v < 0) == queda and v != 0:
        return f'{num(abs(v), casas)}{un}'
    return f'nenhuma {"queda" if queda else "alta"} (o mais perto foi {"alta" if queda else "queda"} de {num(abs(v), casas)}{un})'


def dois_lados(mercado: str) -> Bloco:
    """Para quem pergunta se compra ou para onde vai: o que já aconteceu dos dois lados nos últimos 12 meses, na mesma
    ordem e com os mesmos espaços (quando caiu, quando subiu), mais a taxa-base. Nunca o próximo movimento."""
    nome, serie_nome, fonte, _ = HISTORICO[mercado]
    s = serie(serie_nome)
    d_fim = s.index[-1]
    juros = serie_nome.startswith('pre_')
    if juros:
        r, mes_, un, casas = s.diff() * 100, (s - s.shift(MES_PREGOES)) * 100, PONTOS_BASE, 0
    else:
        r, mes_, un, casas = s.pct_change() * 100, (s / s.shift(MES_PREGOES) - 1) * 100, '%', 2
    na_janela = s.index > d_fim - pd.DateOffset(years=1)
    r12, m12 = r[na_janela].dropna(), mes_[na_janela].dropna()
    d_q, d_a, m_q, m_a = r12.idxmin(), r12.idxmax(), m12.idxmin(), m12.idxmax()
    inicio = lambda d: s.index[s.index.get_loc(d) - MES_PREGOES]  # noqa: E731
    fontes = (fonte, F_ESTUDO)
    b = Bloco(f'{TITULO_DOIS_LADOS} ({nome}, últimos 12 meses até {dia(d_fim)})')
    # As duas linhas com o mesmo molde, palavra por palavra, trocando só queda por alta (o tamanho igual é parte da regra).
    for rotulo, palavra, d_dia, d_mes, queda in (('Quando caiu', 'queda', d_q, m_q, True), ('Quando subiu', 'alta', d_a, m_a, False)):
        b.add(f'{rotulo}: a maior {palavra} em um dia foi de {_lado(r12[d_dia], casas, un, queda)} ({dia(d_dia)}); em '
              f'{MES_PREGOES} pregões seguidos (cerca de um mês), a maior {palavra} foi de {_lado(m12[d_mes], casas, un, queda)} '
              f'(de {dia(inicio(d_mes))} a {dia(d_mes)}).', *fontes)
    b.linhas.append(taxa_base(mercado, nome.split(' ', 1)[1]))
    b.add(DECISAO_SUA)
    b.limites.append('Os dois lados são do passado e da mesma janela; o próximo movimento pode ser maior, menor ou de outro lado.')
    b.resumo = (f'Os dois lados nos últimos 12 meses: {nome} teve dia de queda de até {_lado(r12[d_q], casas, un, True)}'
                + (EXPLICA_PB if juros else '') + f' e de alta de até {_lado(r12[d_a], casas, un, False)}; em cerca de um mês, '
                f'caiu até {_lado(m12[m_q], casas, un, True)} e subiu até {_lado(m12[m_a], casas, un, False)}. {DECISAO_SUA}')
    return b


DECISAO_SUA = 'O histórico mostra os dois lados, não o próximo movimento: a decisão é sua.'


# ---------- o que o mercado espera (Focus) e as datas marcadas ----------

DIAS_DA_SEMANA = ('segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo')
SEGUNDO_TURNO_2026 = '2026-10-25'


def _focus() -> dict:
    return _json('series/focus.json')


def _realizado(ano: int) -> dict:
    """O que de fato aconteceu num ano fechado: PTAX do último dia útil, meta Selic em 31/12 e IPCA de 12 meses em dez."""
    ptax, selic, ipca = serie('ptax'), serie('selic_meta'), serie('ipca_12m')
    p = ptax[ptax.index.year == ano]
    return {'Câmbio': (p.index[-1], float(p.iloc[-1])), 'Selic': float(selic[selic.index <= f'{ano}-12-31'].iloc[-1]),
            'IPCA': float(ipca[ipca.index == f'{ano}-12-01'].iloc[0])}


TITULO_EXPECTATIVAS = 'O que o mercado espera'
SEM_FOCUS_EURO = 'O Focus não pergunta pelo euro; para o dólar, '


def expectativas(mercado: str) -> Bloco:
    """A mediana do Focus de hoje, atribuída, e quanto ela errou nos anos já fechados, para os dois lados."""
    f = _focus()
    a, prox, data = f['atual'], f['proxima_reuniao'], f['data']
    ano = int(data[:4])
    decisao = next((r['decisao'] for r in f['agenda_copom']), None)
    selic_hoje = _ultimo('selic_meta')[1]
    c0, c1 = a[f'Câmbio|{ano}'], a[f'Câmbio|{ano + 1}']
    i0, i1 = a[f'IPCA|{ano}'], a[f'IPCA|{ano + 1}']
    s0, pib = a[f'Selic|{ano}'], a[f'PIB Total|{ano}']
    linhas = {
        'cambio': (f'Câmbio: R$ {num(c0["mediana"], 2)} para o fim de {ano} e R$ {num(c1["mediana"], 2)} para o fim de '
                   f'{ano + 1}, pela mediana de {c0["respondentes"]} instituições no Focus de {dia(data)} (a expectativa '
                   f'delas, não do Thoran); para {ano}, as respostas vão de R$ {num(c0["minimo"], 2)} a '
                   f'R$ {num(c0["maximo"], 2)}.'),
        'selic': (f'Selic: {num(s0["mediana"], 2)}% no fim de {ano}, pela mediana de {s0["respondentes"]} instituições; '
                  f'para a próxima reunião do Copom ({prox["reuniao"]}'
                  + (f', decisão em {dia(decisao)}' if decisao else '') +
                  f'), {num(prox["mediana"], 2)}%. A meta hoje é de {num(selic_hoje, 2)}%.'),
        'ipca': f'IPCA: {num(i0["mediana"], 2)}% em {ano} e {num(i1["mediana"], 2)}% em {ano + 1}.',
        'pib': f'PIB: crescimento de {num(pib["mediana"], 2)}% em {ano}.',
    }
    fontes = {'cambio': (F_FOCUS_ANUAL,), 'selic': (F_FOCUS_ANUAL, F_FOCUS, F_SELIC), 'ipca': (F_FOCUS_ANUAL,),
              'pib': (F_FOCUS_ANUAL,)}
    ordem = {'dolar': ['cambio', 'selic', 'ipca'], 'euro': ['cambio', 'selic', 'ipca'], 'juros': ['selic', 'ipca', 'cambio'],
             'ibovespa': ['selic', 'pib', 'ipca', 'cambio']}.get(mercado, ['selic', 'ipca', 'cambio', 'pib'])
    b = Bloco(f'{TITULO_EXPECTATIVAS} (boletim Focus do Banco Central, mediana das instituições, {dia(data)})')
    for k in ordem:
        b.add(linhas[k], *fontes[k])
    # O Focus também erra: a última mediana registrada no ano anterior contra o que aconteceu.
    anos = sorted(f['historico'], key=int)
    erros = {'Câmbio': [], 'Selic': [], 'IPCA': []}
    pares = {'Câmbio': [], 'Selic': [], 'IPCA': []}
    for ano_h in anos:
        esperado, real = f['historico'][ano_h], _realizado(int(ano_h))
        d_ptax, ptax_real = real['Câmbio']
        pares['Câmbio'].append(f'{ano_h}, R$ {num(esperado["Câmbio"]["mediana"], 2)} contra R$ {num(ptax_real, 4)}')
        pares['Selic'].append(f'{ano_h}, {num(esperado["Selic"]["mediana"], 2)}% contra {num(real["Selic"], 2)}%')
        pares['IPCA'].append(f'{ano_h}, {num(esperado["IPCA"]["mediana"], 2)}% contra {num(real["IPCA"], 2)}%')
        erros['Câmbio'].append(ptax_real - esperado['Câmbio']['mediana'])
        erros['Selic'].append(real['Selic'] - esperado['Selic']['mediana'])
        erros['IPCA'].append(real['IPCA'] - esperado['IPCA']['mediana'])
    nomes = {'Câmbio': ('Câmbio', 'a PTAX do último dia útil do ano', F_PTAX),
             'Selic': ('Selic', 'a meta em 31/12', F_SELIC), 'IPCA': ('IPCA', 'o IPCA do ano', F_IPCA)}
    chave = {'dolar': ['Câmbio', 'Selic'], 'euro': ['Câmbio', 'Selic'], 'juros': ['Selic', 'IPCA']}.get(mercado, ['Selic', 'IPCA', 'Câmbio'])
    for ind in chave:
        nome, real_txt, fonte_real = nomes[ind]
        b.add(f'O Focus também erra. {nome}: a mediana do último boletim do ano anterior, cerca de 12 meses antes, contra '
              f'{real_txt}: ' + '; '.join(pares[ind]) + '.', F_FOCUS_ANUAL, fonte_real)
    dois_lados_de = lambda i: any(e > 0 for e in erros[i]) and any(e < 0 for e in erros[i])  # noqa: E731
    un = {'Câmbio': ('R$ ', ''), 'Selic': ('', ' p.p.'), 'IPCA': ('', ' p.p.')}
    rotulo = {'Câmbio': 'câmbio', 'Selic': 'Selic', 'IPCA': 'IPCA'}
    faixas = [f'{rotulo[i]} de {un[i][0]}{num(min(map(abs, erros[i])), 2)} a {un[i][0]}{num(max(map(abs, erros[i])), 2)}'
              f'{un[i][1]}' for i in chave]
    b.add((f'Diferença entre a mediana e o que aconteceu, sem o sinal, de {anos[0]} a {anos[-1]}: '
           + '; '.join(faixas)).rstrip('.') + '.', F_FOCUS_ANUAL, F_ESTUDO)
    dois_lados = all(dois_lados_de(i) for i in chave)
    b.limites.append('A expectativa é a mediana das instituições que respondem ao Focus, não uma previsão do Thoran'
                     + (', e já errou para os dois lados.' if dois_lados else '.'))
    b.limites.append(f'Os erros listados são de medianas feitas cerca de 12 meses antes do fim de cada ano; a de hoje é do '
                     f'boletim de {dia(data)}.')
    periodo = f'de {anos[0]} a {anos[-1]}'
    lados = lambda ind: ', para os dois lados' if dois_lados_de(ind) else ''  # noqa: E731
    # Para quem está começando: quem são, o que esperam e quanto já erraram, sem sigla.
    quem = lambda n: (f'Os economistas que o Banco Central consulta toda semana (boletim Focus, {n} instituições '  # noqa: E731
                      f'em {dia(data)})')
    if mercado in ('dolar', 'euro'):
        e = [abs(x) for x in erros['Câmbio']]
        sujeito = quem(c0['respondentes'])
        if mercado == 'euro':
            sujeito = SEM_FOCUS_EURO + sujeito[0].lower() + sujeito[1:]
        b.resumo = (f'{sujeito} esperam o dólar a R$ {num(c0["mediana"], 2)} no fim de {ano}; as '
                    f'respostas vão de R$ {num(c0["minimo"], 2)} a R$ {num(c0["maximo"], 2)}. É a expectativa deles, não do '
                    f'Thoran, e ela já errou: {periodo}, a diferença entre o esperado e o dólar do fim do ano foi de '
                    f'R$ {num(min(e), 2)} a R$ {num(max(e), 2)}{lados("Câmbio")}.')
    else:
        e = [abs(x) for x in erros['Selic']]
        b.resumo = (f'{quem(s0["respondentes"])} esperam os juros básicos (Selic) em {num(s0["mediana"], 2)}% no fim de '
                    f'{ano}; hoje estão em {num(selic_hoje, 2)}%. É a expectativa deles, não do Thoran, e ela já errou: '
                    f'{periodo}, a diferença entre o esperado e a Selic do fim do ano foi de {num(min(e), 2)} a '
                    f'{num(max(e), 2)} pontos percentuais{lados("Selic")}.')
    return b


def agenda(mercado: str) -> list[dict]:
    """As datas marcadas que o repertório já mediu. Só a data: a reação de antes fica para quando a pessoa perguntar pelo
    evento (P3: o filtro é o evento que ela citou), porque, colada em "devo comprar hoje?" a poucos dias do evento, a
    reação passada vira momento (N4) e "evento X chegando, atenção a Y" (M1). O ataque legal de 22/10/2026 achou isso.
    Quem monta a resposta filtra pela data de hoje e fica com a primeira de cada tipo."""
    itens = []
    if not (_csv('eleicoes_surpresa.csv').rodada == '2026-2').any():
        d = pd.Timestamp(SEGUNDO_TURNO_2026)
        itens.append({'tipo': 'eleicao', 'data': SEGUNDO_TURNO_2026, 'fontes': (F_CF77,),
                      'curto': f'2º turno da eleição presidencial em {d.strftime("%d/%m")} ({DIAS_DA_SEMANA[d.weekday()]})'})
    for r in _focus()['agenda_copom'][:2]:
        d = pd.Timestamp(r['decisao'])
        itens.append({'tipo': 'copom', 'data': r['decisao'], 'fontes': (F_AGENDA_COPOM,),
                      'curto': f'decisão do Copom (o comitê do Banco Central que define a Selic) em {d.strftime("%d/%m")} '
                               f'({DIAS_DA_SEMANA[d.weekday()]}, depois das 18h30)'})
    return itens


CALENDARIO = {'titulo': 'Datas marcadas no calendário oficial',
              'linha_inicio': 'Há datas marcadas no calendário oficial: ',
              'linha_fim': '. Para ver como o mercado se moveu nelas antes, pergunte pelo evento.',
              'resumo_inicio': 'Datas marcadas: ',
              'resumo_fim': '; para ver como o mercado se moveu nelas antes, pergunte pelo evento.'}


def calendario(mercado: str, hoje: str) -> Bloco | None:
    """As datas de agenda() de hoje em diante, a primeira de cada tipo, numa linha só."""
    vistos, curtos, fontes = set(), [], []
    for item in agenda(mercado):
        if item['data'] < hoje or item['tipo'] in vistos:
            continue
        vistos.add(item['tipo'])
        curtos.append(item['curto'])
        fontes += [f for f in item['fontes'] if f not in fontes]
    if not curtos:
        return None
    b = Bloco(CALENDARIO['titulo'])
    b.add(CALENDARIO['linha_inicio'] + ' e '.join(curtos) + CALENDARIO['linha_fim'], *fontes)
    b.resumo = CALENDARIO['resumo_inicio'] + ' e '.join(curtos) + CALENDARIO['resumo_fim']
    return b


def _mercados_medidos(mercados: list[str]) -> list[str]:
    alvo = []
    for m in mercados:
        m = {'mini_indice': 'ibovespa', 'mini_dolar': 'dolar'}.get(m, m)
        if m in MEDIDA and m not in alvo:
            alvo.append(m)
    return alvo or ['ibovespa', 'dolar', 'juros']


def _anos(t: pd.DataFrame) -> str:
    anos = [x[-4:] for x in t.turno]
    return anos[0] if len(anos) == 1 else ', '.join(anos[:-1]) + ' e ' + anos[-1]


def _valores(v: pd.Series, un: str, casas: int) -> str:
    """Poucos casos: cada valor, em ordem, em vez de faixa e mediana."""
    xs = [f'{sinal(x, casas)}{un}' for x in v]
    return xs[0] if len(xs) == 1 else ', '.join(xs[:-1]) + ' e ' + xs[-1]


def eleicoes(mercados: list[str]) -> Bloco:
    b = Bloco('O que aconteceu antes: os turnos presidenciais desde 2018 (fato)')
    tab = _csv('eleicoes_surpresa.csv')
    datas = {x['id']: x for x in _json('fontes/pesquisas_eleicoes.json')}
    alvo = _mercados_medidos(mercados)
    for _, r in tab.iterrows():
        info = datas[r.rodada]
        tse = Fonte(f'TSE, resultado oficial do {r.turno}', info['dados']['resultado_tse']['fonte_url'])
        d0 = _proximo_pregao(info['data'])
        lider, outro = (r.a, r.b) if r.margem_tse_pp > 0 else (r.b, r.a)
        favorecido = r.a if r.surpresa_pp > 0 else r.b
        reacao = ', '.join(f'{MEDIDA[m][0]} {sinal(r[MEDIDA[m][1]] * MEDIDA[m][3], MEDIDA[m][4])}{MEDIDA[m][2]}' for m in alvo)
        if r.surpresa_mensuravel:
            leitura = f'surpresa de {num(abs(r.surpresa_pp), 2)} p.p. a favor de {favorecido}, que o estudo conta como surpresa'
        else:
            leitura = (f'diferença de {num(abs(r.surpresa_pp), 2)} p.p. contra as pesquisas, dentro da variação entre os '
                       f'institutos ({num(r.erro_padrao_entre_institutos_pp, 2)} p.p.): o estudo não conta como surpresa')
        lider_p = r.a if r.margem_pesquisas_media_pp > 0 else r.b
        b.add(f'{r.turno[0].upper() + r.turno[1:]} ({dia(info["data"])}): {lider} terminou {num(abs(r.margem_tse_pp), 2)} '
              f'p.p. à frente de {outro} nos votos válidos; a média de {int(r.n_pesquisas)} pesquisas da última semana '
              f'dava {lider_p} {num(abs(r.margem_pesquisas_media_pp), 2)} p.p. à frente; {leitura}. No pregão '
              f'seguinte ({dia(d0)}): {reacao}.', tse, *(MEDIDA[m][5] for m in alvo), F_ESTUDO)
    segundo = tab.turno.str.startswith('2º')
    for m in alvo:
        nome, col, un, k, casas, _ = MEDIDA[m]
        v = (tab[col] * k).round(casas)
        b.add(f'{nome[0].upper() + nome[1:]} no pregão seguinte: nos {(~segundo).sum()} primeiros turnos '
              f'({_anos(tab[~segundo])}), {_valores(v[~segundo], un, casas)}; nos {segundo.sum()} segundos turnos '
              f'({_anos(tab[segundo])}), {_valores(v[segundo], un, casas)}.', F_ESTUDO)
    for m in alvo:
        b.linhas.append(taxa_base(m, MEDIDA[m][0]))
    med = tab[tab.surpresa_mensuravel]
    lados = {r.a if r.surpresa_pp > 0 else r.b for _, r in med.iterrows()}
    b.add(f'Leitura do estudo (interpretação, não fato): nesses {len(tab)} turnos, a reação acompanhou mais a surpresa '
          f'contra as pesquisas do que o nome de quem venceu. As {len(med)} surpresas medidas foram todas a favor do '
          f'mesmo campo político ({", ".join(sorted(lados))}), então a amostra não mostra o que acontece com uma surpresa '
          f'no sentido contrário.' if len({1 if s > 0 else -1 for s in med.surpresa_pp}) == 1 else
          f'Leitura do estudo (interpretação, não fato): nesses {len(tab)} turnos, a reação acompanhou mais a surpresa '
          f'contra as pesquisas do que o nome de quem venceu.', F_ESTUDO)
    nome, col, un, k, casas, _ = MEDIDA[alvo[0]]
    v = (tab[col] * k).round(casas)
    surpresa_nos_primeiros = bool(tab[~segundo].surpresa_mensuravel.all() and not tab[segundo].surpresa_mensuravel.any())
    um_lado = len({1 if x > 0 else -1 for x in med.surpresa_pp}) == 1
    pb = un.strip() == 'p.b.'
    un_txt, plural, artigo = (PONTOS_BASE, True, 'os') if pb else (un, False, 'o')
    b.resumo = (f'Depois dos {segundo.sum()} segundos turnos desde 2018, {artigo} {nome} '
                f'{movs(v[segundo], casas, un_txt, plural)} no dia seguinte; depois dos {(~segundo).sum()} primeiros'
                + (', em que a urna surpreendeu as pesquisas' if surpresa_nos_primeiros else '')
                + f', {faixa_mov(v[~segundo].min(), v[~segundo].max(), casas, un_txt, plural)}'
                + (EXPLICA_PB if pb else '') + '. Leitura do estudo: pesou mais a '
                f'surpresa das urnas do que o nome de quem ganhou'
                + (f', mas as {len(med)} surpresas foram a favor do mesmo campo político, e a amostra não mostra o outro lado'
                   if um_lado else '')
                + f'. São só {len(tab)} casos: não dá para tirar regra.')
    b.limites += [f'São só {len(tab)} turnos, e só {len(med)} tiveram surpresa mensurável: não dá para tirar regra.',
                  'A reação é de um dia, com dado diário (o estudo não tem dado intradiário): no Ibovespa, o fechamento do '
                  'pregão seguinte contra o anterior; no dólar, a PTAX de venda do Banco Central, fixada entre 10h e 13h, e '
                  'não o fechamento; nos juros, a taxa de compra da manhã do Tesouro Direto.']
    if {'cripto', 'memecoin'} & set(mercados):
        b.limites.append('O repertório não tem medida de cripto em eleição brasileira: não invento esse número.')
    return b


def candidatos() -> Bloco | None:
    caminho = AGENTE / 'candidatos_2026.json'
    if not caminho.exists():
        return None
    dados = json.loads(caminho.read_text(encoding='utf-8'))
    b = Bloco('Os candidatos do 2º turno de 2026: o que cada um registrou e disse sobre economia (fato, com fonte)')
    b.add('Os dois aparecem no mesmo formato e em ordem alfabética. Resumir o que cada um diz não é tomar lado.')
    for c in sorted(dados['candidatos'], key=lambda c: c['nome']):
        cab = f'{c["nome"]} ({c["partido"]})'
        if c.get('vice'):
            cab += f', vice: {c["vice"]}'
        b.add(f'{cab}. {c["historico"]}', Fonte(f'Histórico de {c["nome"]}', c['historico_fonte_url']))
        if c.get('programa_tse_url'):
            if c.get('programa_tse_confirmado'):
                b.add(f'{c["nome"]}: programa de governo registrado no TSE.', Fonte(f'TSE, programa de {c["nome"]}', c['programa_tse_url']))
            else:
                b.add(f'{c["nome"]}: o link do programa registrado no TSE não abriu na conferência; os pontos abaixo vêm '
                      f'das fontes indicadas em cada um.', Fonte(f'TSE, programa de {c["nome"]}', c['programa_tse_url']))
        for pt in c['pontos_economia']:
            b.add(f'{c["nome"]}, {pt["tema"]}: {pt["o_que_diz"]} ({pt["tipo"]}, {pt["data"]}).',
                  Fonte(f'{pt["tipo"][0].upper() + pt["tipo"][1:]}, {c["nome"]}', pt['fonte_url']))
        if c.get('equipe_economica'):
            b.add(f'{c["nome"]}, equipe econômica: {c["equipe_economica"]}', Fonte('Forbes, as equipes econômicas de Lula e Flávio Bolsonaro', c.get('equipe_fonte_url', '')))
    b.resumo = ''
    b.limites.append(f'Os pontos dos candidatos foram conferidos em {dados.get("conferido_em", "?")}. Programa registrado '
                     f'não garante o que será feito.')
    if dados.get('metodo'):
        b.add(f'Como os pontos foram escolhidos: {dados["metodo"]}')
    return b


def _pct_livre(x: float) -> str:
    """O número como o instituto publicou: sem casa decimal inventada (48 fica 48, 40,95 fica 40,95)."""
    return num(x, 0) if float(x).is_integer() else num(x, len(repr(float(x)).split('.')[1]))


def pesquisas() -> Bloco | None:
    caminho = AGENTE / 'pesquisas_2026_2t.json'
    if not caminho.exists():
        return None
    dados = json.loads(caminho.read_text(encoding='utf-8'))
    regs = [p for p in dados['pesquisas'] if re.fullmatch(r'BR-\d{5}/2026', p.get('registro_tse') or '')]
    b = Bloco('O que mostram as pesquisas do 2º turno com registro no TSE informado pelo instituto ou pela imprensa (fato)')
    b.add(f'Quais entram: {dados["criterio"]} Não calculo chance de vitória e não uso mercado de previsão como termômetro.',
          F_LEI_9504)
    difs, com_total = [], []
    for p in sorted(regs, key=lambda p: (p['campo_fim'], p['instituto']), reverse=True):
        if p.get('flavio_total_pct') and p.get('lula_total_pct'):
            difs.append(p['flavio_total_pct'] - p['lula_total_pct'])
            com_total.append(p)
            votos = (f'Flávio Bolsonaro {_pct_livre(p["flavio_total_pct"])}% e Lula {_pct_livre(p["lula_total_pct"])}% '
                     f'dos votos totais')
        elif p.get('flavio_validos_pct') and p.get('lula_validos_pct'):
            votos = (f'Flávio Bolsonaro {_pct_livre(p["flavio_validos_pct"])}% e Lula {_pct_livre(p["lula_validos_pct"])}% '
                     f'dos votos válidos (o total não foi divulgado)')
        else:
            continue
        contr = f', contratada por: {p["contratante"]}' if p.get('contratante') else ''
        campo = (f'campo de {dia(p["campo_inicio"])} a {dia(p["campo_fim"])}' if p.get('campo_inicio')
                 else f'campo até {dia(p["campo_fim"])}')
        marg = f', margem de erro de {_pct_livre(p["margem_pp"])} p.p.' if p.get('margem_pp') else ''
        b.add(f'{p["instituto"]}{contr}; {campo}, registro {p["registro_tse"]}: {votos}{marg}'.rstrip('.') + '.',
              Fonte(f'Pesquisa {p["instituto"]}, registro {p["registro_tse"]}', p['fonte_url']))
    fora = len(dados['pesquisas']) - len(regs)
    if fora:
        b.limites.append(f'{fora} pesquisa(s) ficaram de fora porque o número de registro no TSE não foi localizado.')
    b.limites += dados.get('limites', [])
    if difs:
        mediana = float(pd.Series(difs).median())
        frente = lambda d: (f'Flávio Bolsonaro {num(d, 1)} pontos à frente' if d > 0  # noqa: E731
                            else f'Lula {num(-d, 1)} pontos à frente' if d < 0 else 'empate')
        b.resumo = (f'Nas {len(difs)} pesquisas do 2º turno registradas no TSE que divulgaram os votos totais, a diferença '
                    f'vai de {frente(min(difs))} a {frente(max(difs))}, conforme o instituto; no meio da lista, '
                    f'{frente(mediana)}. Pesquisa não é previsão.')
        # A 1ª fonte desta linha é a pesquisa do meio, não um extremo: é ela que a versão curta mostra.
        fonte = lambda p: Fonte(f'Pesquisa {p["instituto"]}, registro {p["registro_tse"]}', p['fonte_url'])  # noqa: E731
        meio = min(range(len(difs)), key=lambda i: abs(difs[i] - mediana))
        b.linhas.insert(1, Linha(f'Nas {len(difs)} pesquisas com votos totais, a diferença Flávio Bolsonaro menos Lula vai de '
                                 f'{sinal(min(difs), 1)} ({com_total[difs.index(min(difs))]["instituto"]}) a '
                                 f'{sinal(max(difs), 1)} p.p. ({com_total[difs.index(max(difs))]["instituto"]}), com mediana '
                                 f'de {sinal(mediana, 1)} p.p.',
                                 (fonte(com_total[meio]), fonte(com_total[difs.index(min(difs))]),
                                  fonte(com_total[difs.index(max(difs))]), F_ESTUDO)))
    tab = _csv('eleicoes_surpresa.csv')
    lo, hi = tab.surpresa_pp.idxmin(), tab.surpresa_pp.idxmax()
    b.limites.append(f'Pesquisa não é previsão, e o erro já foi para os dois lados: nos {len(tab)} turnos medidos, a urna '
                     f'ficou de {sinal(tab.surpresa_pp[lo], 2)} p.p. ({tab.turno[lo]}) a {sinal(tab.surpresa_pp[hi], 2)} p.p. '
                     f'({tab.turno[hi]}) da média das pesquisas, na margem de Jair ou Flávio Bolsonaro sobre o adversário.')
    return b


def copom(mercados: list[str] | None = None) -> Bloco:
    b = Bloco('O que aconteceu antes: as reuniões do Copom desde 2016 contra o Focus (fato)')
    tab = _csv('copom_completo.csv')
    res = _json('estudo/resumo.json')['copom_completo']
    todas, sem = res['versoes']['todas'], res['versoes']['sem_a_que_mais_pesa']
    com = tab[tab.surpresa_pb != 0]
    b.add(f'O estudo cobre {len(tab)} reuniões, de {tab.reuniao.iloc[0]} ({dia(tab.decisao.iloc[0])}) a {tab.reuniao.iloc[-1]} '
          f'({dia(tab.decisao.iloc[-1])}); surpresa é a decisão diferente da mediana do Focus da véspera.', F_COPOM, F_FOCUS, F_ESTUDO)
    for _, r in com.iterrows():
        b.add(f'{r.reuniao} ({dia(r.decisao)}): o Focus esperava {num(r.focus_mediana, 2)}%; a Selic foi de '
              f'{num(r.selic_antes, 2)}% para {num(r.selic_depois, 2)}% (surpresa de {sinal(r.surpresa_pb, 0)} p.b.). No '
              f'pregão seguinte: Ibovespa {sinal(r.ibov_d0, 2)}%, dólar {sinal(r.ptax_d0, 2)}%, juros de 2 anos '
              f'{sinal(r.pre2_d0_pb, 1)} p.b.', F_COPOM, F_FOCUS, F_ESTUDO)
    sem_s = tab[tab.surpresa_pb == 0]
    for col, nome, un, casas in (('ibov_d0', 'Ibovespa', '%', 2), ('ptax_d0', 'Dólar', '%', 2), ('pre2_d0_pb', 'Juros de 2 anos', ' p.b.', 1)):
        v, w = com[col].round(casas), sem_s[col].round(casas)
        b.add(f'{nome} no pregão seguinte, nas {len(com)} reuniões com surpresa: de {sinal(v.min(), casas)}{un} '
              f'({com.reuniao[v.idxmin()]}) a {sinal(v.max(), casas)}{un} ({com.reuniao[v.idxmax()]}), mediana de '
              f'{sinal(v.median(), casas)}{un}; nas {len(sem_s)} sem surpresa, de {sinal(w.min(), casas)}{un} a '
              f'{sinal(w.max(), casas)}{un}, mediana de {sinal(w.median(), casas)}{un}.', F_ESTUDO)
    pesa = com.loc[com.pre2_d0_pb.abs().idxmax()]
    b.add(f'Comparação: nas {todas["sem_surpresa"]} reuniões sem surpresa, os juros de 2 anos andaram {num(todas["juros2a_mediana_abs_sem_pb"], 1)} '
          f'p.b. na mediana, em módulo (sem o sinal); nas {todas["com_surpresa"]} com surpresa, {num(todas["juros2a_mediana_abs_com_pb"], 1)} p.b.', F_ESTUDO)
    b.add(f'O maior movimento foi na {pesa.reuniao} ({dia(pesa.decisao)}, {sinal(pesa.pre2_d0_pb, 1)} p.b., no pânico da '
          f'covid); sem essa reunião, a mediana em módulo das {len(com)} com surpresa fica em '
          f'{num(sem["juros2a_mediana_abs_com_pb"], 1)} p.b.', F_ESTUDO)
    alvo = _mercados_medidos(mercados or [])
    for m in alvo:
        if m != 'juros':
            b.linhas.append(taxa_base(m, MEDIDA[m][0]))
    b.add('Leitura do estudo (interpretação, não fato): surpresa contra o Focus mexe mais nos juros do que as reuniões '
          'sem surpresa; a direção do Ibovespa não segue um padrão estável, e o sinal muda conforme a versão do cálculo.', F_ESTUDO)
    if mercados and alvo[0] in ('ibovespa', 'dolar'):
        col, nome = ('ibov_d0', 'Ibovespa') if alvo[0] == 'ibovespa' else ('ptax_d0', 'dólar')
        v, w = com[col].round(2), sem_s[col].round(2)
        b.resumo = (f'Depois das reuniões do Copom desde 2016: nas {len(sem_s)} em que a decisão foi a que os economistas '
                    f'esperavam (boletim Focus), o {nome} {faixa_mov(w.min(), w.max(), 2)} no dia seguinte; nas {len(com)} '
                    f'que surpreenderam, {faixa_mov(v.min(), v.max(), 2)}. Antes da reunião não se sabe se ela vai '
                    f'surpreender.')
    else:
        v = com.pre2_d0_pb.round(1)
        abaixo, acima = int((com.surpresa_pb < 0).sum()), int((com.surpresa_pb > 0).sum())
        b.resumo = (f'Nas {todas["n"]} reuniões do Copom desde 2016, a decisão foi diferente da que os economistas '
                    f'esperavam (boletim Focus) em {todas["com_surpresa"]}: em {abaixo}, a Selic ficou abaixo do esperado; '
                    f'em {acima}, acima. Nessas reuniões, os juros de 2 anos '
                    f'{faixa_mov(v.min(), v.max(), 1, PONTOS_BASE, True)}{EXPLICA_PB} no dia seguinte; no valor do meio, a '
                    f'mexida foi de {num(todas["juros2a_mediana_abs_com_pb"], 1)} pontos-base, contra '
                    f'{num(todas["juros2a_mediana_abs_sem_pb"], 1)} nas outras {todas["sem_surpresa"]}.')
    b.limites += ['O Focus é a expectativa de economistas, não o preço de mercado.',
                  f'São só {len(com)} reuniões com surpresa desde 2016.',
                  'A surpresa só se conhece depois da decisão; antes da reunião, o que existe é a expectativa do Focus.',
                  'A contagem compara a decisão com o Focus da véspera; não mede a chance de a mediana de hoje acertar.']
    return b


TIPOS = {'fiscal': 'decisões fiscais', 'legislativo': 'votações no Congresso', 'judicial': 'decisões da Justiça',
         'geopolitico': 'geopolítica', 'choque_externo': 'choques externos', 'escandalo': 'escândalos'}


def eventos(tipo: str) -> Bloco:
    b = Bloco(f'O que aconteceu antes: {TIPOS[tipo]} na linha do tempo 2016–2026 (fato)')
    tab = _csv('eventos.csv')
    fontes = {(e['data'], e['evento']): e.get('fontes') or [] for e in _json('fontes/linha-do-tempo.json')['eventos']}
    sel = tab[tab.tipo == tipo]
    for _, r in sel.iterrows():
        urls = [u for u in fontes.get((r.data, r.evento), []) if isinstance(u, str) and u.startswith('http')][:1]
        extra = [Fonte(f'Reportagem sobre "{r.evento}"', urls[0])] if urls else []
        b.add(f'{dia(r.data)}, {r.evento}: Ibovespa {sinal(r.ibov_d0, 2)}% e dólar {sinal(r.ptax_d0, 2)}% no pregão da reação.',
              *extra, F_IBOV, F_PTAX, F_ESTUDO)
    v = sel.ibov_d0.round(2)
    if len(v):
        b.add(f'Ibovespa nos {len(v)} casos: de {sinal(v.min(), 2)}% a {sinal(v.max(), 2)}%, mediana de {sinal(v.median(), 2)}%.', F_ESTUDO)
        b.resumo = (f'Nos {len(v)} casos de {TIPOS[tipo]} da linha do tempo (2016–2026), o Ibovespa '
                    f'{faixa_mov(v.min(), v.max(), 2)} no dia da reação.')
    b.limites.append('Os eventos da linha do tempo foram escolhidos por terem sido marcantes, não sorteados: a amostra '
                     'exagera as reações grandes.')
    return b


TITULO_CRIPTO = 'Como funciona a cripto no Brasil'


def mercado(chave: str) -> Bloco | None:
    if chave == 'mini_indice':
        b = Bloco('Como funciona o mini-índice (WIN)')
        b.add('Cada ponto vale R$ 0,20 por contrato; a variação mínima é de 5 pontos, ou R$ 1,00 por contrato.', F_B3_WIN)
        b.add('A margem mínima de day trade da B3 para o varejo é hoje de R$ 155 por contrato, e a corretora pode cobrar mais.', F_B3_MARGEM)
    elif chave == 'mini_dolar':
        b = Bloco('Como funciona o mini-dólar (WDO)')
        b.add('O contrato é de US$ 10.000, cotado em reais por US$ 1.000; 1 ponto vale R$ 10 por contrato.', F_B3_WDO)
        b.add('A margem mínima de day trade da B3 para o varejo é hoje de R$ 140 por contrato, e a corretora pode cobrar mais.', F_B3_MARGEM)
    elif chave == 'juros':
        b = Bloco('Como funciona o DI futuro (DI1)')
        b.add('Negocia a taxa de juros média até o vencimento, cotada em % ao ano; o contrato vale 100.000 pontos no '
              'vencimento, a R$ 1,00 por ponto.', F_B3_DI1)
    elif chave == 'ibovespa':
        b = Bloco('Como funcionam as ações à vista na B3')
        b.add('O ganho na venda de ações é tributado em 15% no swing trade; vendas de até R$ 20.000,00 no mês ficam isentas '
              'para pessoa física; day trade não tem essa isenção.', F_LEI_11033, F_RECEITA_ISENCAO)
        return b
    elif chave == 'cripto':
        return _bloco_json(_cripto()['regras'])
    else:
        return None
    b.add('A margem é só garantia: o ajuste diário debita ou credita a conta a cada pregão, e, se faltar saldo, a corretora '
          'pode zerar a posição. Pelo glossário da B3, o investidor pode perder mais do que o valor depositado como margem.',
          F_B3_GLOSSARIO, F_B3_MARGEM)
    return b


RISCO_CRIPTO_FATO = ('Cripto à vista, em regra, não é valor mobiliário e não tem a proteção da regulação da CVM; quem '
                     'regula as corretoras de cripto é o Banco Central, num processo de autorização que ainda está em curso. Futuro de cripto e cota de ETF de cripto '
                     'são valores mobiliários, e um token pode ser valor mobiliário conforme os direitos que dá.')


def conta(pontos: float, contratos: int, chave: str) -> Bloco:
    valor, fonte, nome = (0.20, F_B3_WIN, 'mini-índice') if chave == 'mini_indice' else (10.0, F_B3_WDO, 'mini-dólar')
    b = Bloco('A conta, com os números que você escolheu (P4)')
    total = pontos * valor * contratos
    b.add(f'{num(pontos, 0)} pontos × R$ {num(valor, 2)} × {contratos} contrato(s) de {nome} = R$ {num(total, 2)}, para ganho '
          f'ou para perda. É só a conta: não diz se isso faz sentido para você.', fonte)
    b.resumo = f'{num(pontos, 0)} pontos no {nome} valem R$ {num(total, 2)} com {contratos} contrato(s), para ganho ou para perda.'
    return b


# ---------- câmbio: o euro nos turnos e a conta com os números da pessoa ----------

def _reacao_eleicoes(nome: str) -> pd.DataFrame:
    """A reação de uma série de preço nos turnos do estudo, pelo mesmo método do estudo (dia 0 = 1º pregão depois da
    eleição, no calendário do Ibovespa). Com a PTAX, reproduz a coluna ptax_d0 de eleicoes_surpresa.csv."""
    from estudo.eleicoes import RODADA_PARA_EVENTO
    from estudo.janelas import calendario, dia_zero, medir_preco, no_calendario
    cal = calendario(serie('ibov'))
    s = no_calendario(serie(nome), cal)
    linhas = []
    for _, r in _csv('eleicoes_surpresa.csv').iterrows():
        i0 = dia_zero(RODADA_PARA_EVENTO[r.rodada], cal)
        m = medir_preco(s, i0) if i0 is not None else {}
        if m:
            linhas.append({'rodada': r.rodada, 'turno': r.turno, 'd0_data': cal[i0], 'antes': float(s.iloc[i0 - 1]),
                           'depois': float(s.iloc[i0]), 'd0': m['d0'] * 100, 'd01': m['d01'] * 100,
                           'surpresa_mensuravel': bool(r.surpresa_mensuravel), 'surpresa_pp': float(r.surpresa_pp)})
    return pd.DataFrame(linhas)


TITULO_EURO_TURNOS = 'O euro nos turnos presidenciais desde 2018 (fato)'


def euro_turnos() -> Bloco:
    b = Bloco(TITULO_EURO_TURNOS)
    t = _reacao_eleicoes('euro')
    datas = {x['id']: x['data'] for x in _json('fontes/pesquisas_eleicoes.json')}
    for _, r in t.iterrows():
        b.add(f'{r.turno[0].upper() + r.turno[1:]} ({dia(datas[r.rodada])}): no dia útil seguinte ({dia(r.d0_data)}), o '
              f'euro {mov(r.d0, 2)}, de R$ {num(r.antes, 4)} para R$ {num(r.depois, 4)}; no acumulado de dois dias, '
              f'{mov(r.d01, 2)}.', F_EURO, F_ESTUDO)
    segundo = t.turno.str.startswith('2º')
    v = t.d0.round(2)
    b.add(f'Euro no dia útil seguinte: nos {(~segundo).sum()} primeiros turnos ({_anos(t[~segundo])}), '
          f'{movs(v[~segundo], 2)}; nos {segundo.sum()} segundos turnos ({_anos(t[segundo])}), {movs(v[segundo], 2)}.',
          F_ESTUDO)
    b.linhas.append(taxa_base('euro', 'euro'))
    med = t[t.surpresa_mensuravel]
    um_lado = len({1 if x > 0 else -1 for x in med.surpresa_pp}) == 1  # o mesmo critério do bloco das eleições
    # Com os mesmos números das linhas (as mesmas 2 casas, do mesmo float): senão o filtro (D8) pode barrar o arredondado.
    d0 = t.d0
    b.resumo = (f'Depois dos {segundo.sum()} segundos turnos desde 2018, o euro {movs(d0[segundo], 2)} no dia seguinte; '
                f'depois dos {(~segundo).sum()} primeiros, {faixa_mov(d0[~segundo].min(), d0[~segundo].max(), 2)}. São só '
                f'{len(t)} casos'
                + (f', e as {len(med)} surpresas das urnas ({juntar(list(med.turno))}) foram a favor do mesmo campo '
                   f'político: a amostra não mostra o outro lado' if um_lado and len(med) else '')
                + '. Não dá para tirar regra.')
    b.limites += [f'São só {len(t)} turnos: não dá para tirar regra.',
                  'A reação é de um dia, com a cotação oficial do Banco Central (PTAX, fixada entre 10h e 13h), não o '
                  'fechamento; o movimento de um dia não diz nada sobre os meses seguintes.',
                  LIMITE_PTAX_EURO]
    return b


EURO_SEM_ESTUDO = ('O estudo do Copom e da linha do tempo mede o dólar (a cotação oficial do Banco Central), não o euro: '
                   'os números de câmbio abaixo são do dólar.')


def euro_sem_estudo() -> Bloco:
    return Bloco('Sobre o euro', [Linha(EURO_SEM_ESTUDO)])


MOEDAS = {'euro': ('euro', 'euros', 'euro', F_EURO), 'dolar': ('dólar', 'dólares', 'ptax', F_PTAX)}
TITULO_CONTA_CAMBIO = 'A conta, com os números que você contou (só a conta: não diz o que fazer)'


def cotacoes(moeda: str) -> dict:
    """Os números da conta de câmbio: a PTAX de hoje, a do fim do ano passado e a menor e a maior dos 12 meses."""
    s = serie(MOEDAS[moeda][2])
    d_fim = s.index[-1]
    doze = s[s.index > d_fim - pd.DateOffset(years=1)]
    antes = s[s.index.year < d_fim.year]
    return {'data': str(d_fim.date()), 'valor': float(s.iloc[-1]),
            'ano_data': str(antes.index[-1].date()), 'ano_valor': float(antes.iloc[-1]),
            'min_data': str(doze.idxmin().date()), 'min_valor': float(doze.min()),
            'max_data': str(doze.idxmax().date()), 'max_valor': float(doze.max())}


def _qtd(v: float) -> str:
    """A quantia que a pessoa contou: inteira sem casas, quebrada com 2 ("0,50 euro" não vira "0 euros")."""
    return num(v, 0) if float(v).is_integer() else num(v, 2)


def _reais(v: float) -> str:
    """Real da conta: sem centavos a partir de R$ 1.000; abaixo disso, com centavos ("R$ 2,82", não "R$ 3")."""
    return num(v, 0) if abs(v) >= 1000 else num(v, 2)


def _meses(m: float) -> str:
    """Meses inteiros, sem arredondar para cima, e os anos exatos quando passa de 2: "35 meses (2 anos e 11 meses)"."""
    n = int(m)
    if n < 1:
        return 'menos de 1 mês'
    txt = f'{num(n, 0)} {"mês" if n == 1 else "meses"}'
    if n >= 24:
        anos, resto = divmod(n, 12)
        txt += f' ({num(anos, 0)} anos' + (f' e {resto} {"mês" if resto == 1 else "meses"}' if resto else '') + ')'
    return txt


def conta_cambio(valor: float, moeda: str, gasto: float | None = None, gasto_moeda: str | None = None,
                 c: dict | None = None, cg: dict | None = None) -> Bloco:
    """P4 de câmbio: o dinheiro em moeda estrangeira que a pessoa contou, em reais, pela cotação oficial. Só a conta, sem
    dizer o que fazer, quando trocar nem quanto (N1, N4, N5). `gasto`: o gasto por mês que ela contou, em reais, na
    própria moeda ou em outra moeda estrangeira (convertido pela cotação oficial dela, `cg`)."""
    nome, plural, _, fonte = MOEDAS[moeda]
    c = c or cotacoes(moeda)
    hoje_r = valor * c['valor']
    ano_r = valor * c['ano_valor']
    b = Bloco(TITULO_CONTA_CAMBIO)
    b.add(f'{_qtd(valor)} {plural} × R$ {num(c["valor"], 4)} (cotação oficial do {nome} em {dia(c["data"])}) = '
          f'R$ {_reais(hoje_r)}.', fonte)
    b.add(f'Cada R$ 0,10 de diferença na cotação do {nome} muda esse valor em R$ {_reais(valor * 0.1)}.', fonte)
    dif = ano_r - hoje_r
    b.add(f'No fim de {c["ano_data"][:4]} ({dia(c["ano_data"])}), 1 {nome} valia R$ {num(c["ano_valor"], 4)}: os mesmos '
          f'{_qtd(valor)} {plural} davam R$ {_reais(ano_r)}, '
          + (f'R$ {_reais(abs(dif))} {"a mais" if dif > 0 else "a menos"} do que hoje.' if _reais(abs(dif)) not in ('0', '0,00')
             else 'o mesmo que hoje.'), fonte)
    b.add(f'Nos últimos 12 meses, 1 {nome} foi de R$ {num(c["min_valor"], 4)} ({dia(c["min_data"])}) a '
          f'R$ {num(c["max_valor"], 4)} ({dia(c["max_data"])}): nesses dois extremos, os mesmos {plural} dariam de '
          f'R$ {_reais(valor * c["min_valor"])} a R$ {_reais(valor * c["max_valor"])}.', fonte)
    cobre = ''
    if gasto:
        if gasto_moeda == moeda:
            gasto_txt = f'{_qtd(gasto)} {plural}'
            meses = valor / gasto
            b.add(f'Com gasto de {gasto_txt} por mês, os {_qtd(valor)} {plural} cobrem {_meses(meses)}, sem contar '
                  f'rendimento, imposto nem custo da troca.')
        else:
            if gasto_moeda in MOEDAS:  # outra moeda estrangeira: o gasto vira real pela cotação oficial dela
                nome_g, plural_g, _, fonte_g = MOEDAS[gasto_moeda]
                cg = cg or cotacoes(gasto_moeda)
                gasto_r = gasto * cg['valor']
                gasto_txt = f'{_qtd(gasto)} {plural_g}'
                abre = (f'Com gasto de {gasto_txt} por mês (R$ {_reais(gasto_r)} pela cotação oficial do {nome_g} em '
                        f'{dia(cg["data"])})')
                fontes_g = (fonte, fonte_g)
            else:
                gasto_r = gasto
                gasto_txt = f'R$ {_qtd(gasto)}'
                abre = f'Com gasto de {gasto_txt} por mês'
                fontes_g = (fonte,)
            meses = hoje_r / gasto_r
            b.add(f'{abre}, R$ {_reais(hoje_r)} cobrem {_meses(meses)}, sem contar rendimento, imposto nem custo da troca. '
                  f'Com o {nome} na menor cotação dos 12 meses, seriam {_meses(valor * c["min_valor"] / gasto_r)}; na maior, '
                  f'{_meses(valor * c["max_valor"] / gasto_r)}.', *fontes_g)
        cobre = f'; com gasto de {gasto_txt} por mês, cobrem {_meses(meses)}'
    b.add('É só a conta com os números que você contou: não diz o que fazer com o dinheiro, nem quando trocar, nem quanto.')
    b.limites.append(LIMITE_PTAX_EURO.replace('do euro', f'do {nome}') if moeda != 'euro' else LIMITE_PTAX_EURO)
    b.resumo = (f'Pela cotação oficial de {dia(c["data"])}, seus {_qtd(valor)} {plural} equivalem a R$ {_reais(hoje_r)}; na '
                f'troca de verdade entram a tarifa e o spread do banco ou do app. Cada R$ 0,10 de diferença no {nome} muda '
                f'isso em R$ {_reais(valor * 0.1)}{cobre}.')
    return b


# ---------- cripto: regras, imposto, riscos e a linha do tempo (sem preço: falta licença da cotação) ----------

def _cripto() -> dict:
    return _json('agente/cripto.json')


def _fontes_json(fs: list[dict]) -> tuple[Fonte, ...]:
    return tuple(Fonte(f['nome'], f['url']) for f in fs)


def _bloco_json(d: dict) -> Bloco:
    b = Bloco(d['titulo'])
    for ln in d['linhas']:
        b.add(ln['texto'], *_fontes_json(ln['fontes']))
    b.resumo = d.get('resumo', '')
    b.limites = list(d.get('limites', []))
    return b


TITULO_CRIPTO_IMPOSTO = 'Imposto e formas de ter cripto no Brasil (regra conferida em 23/10/2026)'
TITULO_CRIPTO_RISCOS = 'Riscos da cripto, com caso e fonte (fato)'


def cripto_imposto() -> Bloco:
    b = _bloco_json(_cripto()['imposto'])
    assert b.titulo == TITULO_CRIPTO_IMPOSTO
    return b


def cripto_riscos() -> Bloco:
    b = _bloco_json(_cripto()['riscos'])
    assert b.titulo == TITULO_CRIPTO_RISCOS
    return b


TITULO_MARCOS = 'Linha do tempo da cripto desde 2016 (fato, sem preço)'


def tema_cripto(pergunta_normalizada: str) -> str:
    """O 1º tema da linha do tempo que a pergunta cita ('halving', 'ftx'...), ou '' se nenhum."""
    return next((k for k, t in _cripto()['temas'].items() if re.search(t['regex'], pergunta_normalizada)), '')


def cripto_marcos(tema: str = '') -> Bloco:
    """Os marcos do tema que a pessoa citou; sem tema, todos. Só o fato e a data: a reação do preço espera a licença."""
    c = _cripto()
    datas = set(c['temas'][tema]['datas']) if tema else None
    marcos = [m for m in c['marcos'] if datas is None or m['data'] in datas]
    b = Bloco(TITULO_MARCOS)
    if tema == 'halving':
        h = c['halving']
        b.add(h['texto'], *_fontes_json(h['fontes']))
    for m in marcos:
        b.add(f'{dia(m["data"])}: {m["titulo"]}.', *_fontes_json(m['fontes']))
    if tema:
        minuscula = lambda t: t[0].lower() + t[1:] if t[1:2].islower() else t  # "HASH11" fica, "Halving" vira "halving"  # noqa: E731
        b.resumo = 'Na linha do tempo da cripto: ' + '; '.join(f'{dia(m["data"])}, {minuscula(m["titulo"])}' for m in marcos[:3]) + '.'
    b.limites.append('Sem a variação do preço em cada data: o repertório ainda não tem cotação licenciada do bitcoin.')
    return b


def fgv() -> Bloco:
    b = Bloco('A taxa-base de quem faz day trade (fato)')
    b.add('Entre as 19.646 pessoas físicas que começaram a fazer day trade de mini-índice de 2013 a 2015, 1.551 persistiram '
          'mais de 300 dias; dessas, 97% perderam dinheiro e só 47 (3,0%) lucraram.', F_FGV)
    b.resumo = 'No estudo da FGV, 97% de quem insistiu mais de 300 dias no day trade de mini-índice perdeu dinheiro.'
    b.limites.append('O estudo da FGV cobre quem começou de 2013 a 2015; o cálculo abate tarifas e corretagem, mas não IR.')
    return b


def memecoins() -> Bloco:
    b = Bloco('O que aconteceu antes: memecoins políticas (fato)')
    b.add('$TRUMP: máxima de US$ 73,43 em 19/01/2025 e US$ 1,79 em 21/10/2026, queda de 97,56%.', F_COINGECKO_TRUMP)
    b.add('$TRUMP: 988.905 de cerca de 1,48 milhão de carteiras estavam no prejuízo, somando US$ 3,81 bilhões perdidos.', F_THEBLOCK_TRUMP)
    b.add('$MELANIA: máxima de US$ 13,05 em 19/01/2025 e US$ 0,085 em 21/10/2026, queda de 99,35%.', F_COINGECKO_MELANIA)
    b.add('$LIBRA, promovida por Javier Milei em fevereiro de 2025: 86% das carteiras perderam, somando US$ 251 milhões.', F_THEBLOCK_LIBRA)
    b.add('Um token pode ser valor mobiliário conforme os direitos que dá, e aí entram as regras da CVM.', F_PARECER_40)
    b.resumo = 'Desde a máxima, o $TRUMP caiu 97,56% e o $MELANIA, 99,35%; no $LIBRA, 86% das carteiras perderam.'
    b.limites.append('Os casos são de memecoins que ficaram famosas; não há amostra de todas as memecoins políticas.')
    return b


def previsao() -> Bloco:
    b = Bloco('Mercados de previsão e apostas sobre a eleição (regra)')
    b.add('Desde 04/05/2026, a oferta e a negociação no país de derivativos sobre evento político ou eleitoral são '
          'proibidas.', F_CMN_5298)
    b.add('Na B3 existem contratos de evento, mas só sobre referenciais econômicos, e por enquanto só para investidor '
          'profissional.', F_B3_EVENTOS)
    return b


def binaria() -> Bloco:
    b = Bloco('Opções binárias e IQ Option (regra)')
    b.add('A CVM mandou suspender a oferta da IQ Option no Brasil (stop order) pelo Ato Declaratório 17.790, de 20/04/2020, e o '
          'Colegiado negou o recurso em 02/06/2020. Para a CVM, opção binária é contrato derivativo.', F_CVM_IQ)
    return b

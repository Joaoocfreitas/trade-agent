"""Separa, das manchetes novas, as que podem virar fato na base: a LISTA DO DIA para o fundador revisar.

Regras fixas por expressão regular sobre o título (sem acento, minúsculas), sem IA e sem custo. Nada daqui vai para o
usuário: cada item é só uma manchete com link, e o fato só entra na base depois de conferido na fonte primária por uma
pessoa e aprovado por uma segunda (o passo a passo sai no fim da lista).

Direito autoral: de cada item saem só título, link, fonte, hora e os gatilhos que casaram. O resumo do feed e o texto da
matéria não são lidos aqui.

Datas: o índice mistura UTC (+00:00, registros antigos) e Brasília (−03:00). Tudo é convertido para America/Sao_Paulo
antes de comparar; data sem fuso é tomada como horário de Brasília, que é o que o coletor grava.
"""
import re
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .assuntos import classificar
from .cofre import MERCADO, POLITICOS
from .config import FUSO
from .nomes import norm


@dataclass(frozen=True)
class Gatilho:
    nome: str
    regra: str  # quando casa, em português, para quem revisa a lista
    casa: Callable[[str], bool]  # recebe o título como veio do feed


# --- (a) Pesquisa eleitoral ---------------------------------------------------------------------------------------
# "BR-01234/2026" vira "br 01234 2026" depois de norm().
REGISTRO_TSE = re.compile(r'\bbr \d{5} 2026\b')
# Nome que só existe como instituto de pesquisa: basta aparecer no título. Na amostra de 21/10/2026, 28 das 47
# manchetes de pesquisa com instituto não tinham a palavra "pesquisa" ("Quaest, 2º turno: Flávio Bolsonaro, 45%; Lula,
# 44%"); exigir "pesquisa" deixaria de fora a manchete principal do dia.
INSTITUTOS = ('datafolha', 'quaest', 'atlasintel', 'atlas intel', 'ipespe', 'ipec', 'parana pesquisas', 'poderdata',
              'poder data', 'real time big data', 'gerp', 'palver', 'datatrends', 'data trends', 'verita',
              'instituto franca', 'meio ideia', 'ideia big data', 'vox populi', 'futura inteligencia', 'cnt mda',
              'btg nexus', 'atlas bloomberg')
# Nome que também é palavra comum ("boa ideia", "futura ministra", "Alfa Romeo", "governo indexa"): só conta colado a
# "pesquisa" ou "instituto", depois de "diz"/"aponta"/"segundo", ou como abertura do título antes de dois-pontos.
INSTITUTOS_AMBIGUOS = ('futura', 'vox', 'ideia', 'alfa', 'nexus', 'mda', 'indexa', 'atlas')

_alt = '|'.join
_INSTITUTO_RE = re.compile(rf'\b({_alt(INSTITUTOS)})\b')
_AMBIGUO_RE = re.compile(
    rf'\b(?:pesquisas? (?:d[aoe] )?(?:instituto )?|instituto |(?:diz|dizem|aponta|segundo)'
    rf'(?: [ao])? )(?:{_alt(INSTITUTOS_AMBIGUOS)})\b')


def _pesquisa(titulo: str) -> bool:
    t = norm(titulo)
    if REGISTRO_TSE.search(t) or _INSTITUTO_RE.search(t) or _AMBIGUO_RE.search(t):
        return True
    abertura = norm(titulo.split(':', 1)[0]) if ':' in titulo else ''  # "Futura: Flávio tem 49%..."
    return abertura in INSTITUTOS_AMBIGUOS


# --- (b) Copom e Selic --------------------------------------------------------------------------------------------
_COPOM_RE = re.compile(r'\b(copom|selic)\b')
_DECISAO_JUROS_RE = re.compile(
    r'\b(cort\w*|mant(em|eve|er|ida|ido|idos|idas|era|enha)|manutencao|elev\w*|reduz\w*|reducao|sob(e|em)'
    r'|sub(ir|iu|iram|ida)|aument\w*|decid\w*|decis(ao|oes)|juros)\b')


def _copom(titulo: str) -> bool:
    t = norm(titulo)
    return bool(_COPOM_RE.search(t) and _DECISAO_JUROS_RE.search(t))


# --- (c) Resultado oficial do TSE ---------------------------------------------------------------------------------
_TSE_RE = re.compile(r'\b(tse|tribunal superior eleitoral|justica eleitoral)\b')
# "eleito" só a palavra inteira: "eleitor", "eleitoral" e "eleitorado" não contam. "Apurar" (investigar) também não.
_RESULTADO_RE = re.compile(r'\b(totaliz\w*|apuracao|apurad[oa]s?|resultados?|(re)?eleit[oa]s?)\b')


def _tse(titulo: str) -> bool:
    t = norm(titulo)
    return bool(_TSE_RE.search(t) and _RESULTADO_RE.search(t))


# --- (d) Decisão fiscal, judicial ou do Congresso que cruza com mercado -------------------------------------------
# Reaproveita o cruzamento política × mercado do resumo da coleta (coletor/cofre.py) e as palavras de
# coletor/assuntos.py, só sobre o título. Eleição fica de fora deste lado: pesquisa e resultado têm gatilho próprio, e
# "Ibovespa cai após Quaest" é reação, não decisão. Exige um verbo ou um ato de decisão no título.
POLITICOS_DE_DECISAO = POLITICOS - {'Eleição 2026'}
_ATO_RE = re.compile(
    r'\b(aprov(a|am|ou|aram|ado|ada|ados|adas|ar|acao)|decid\w*|decis(ao|oes)|julg\w*|derrub\w*|suspend\w*|suspens\w*'
    r'|vet(a|am|ou|o|ado|ada|ar)|sancion\w*|sancao|exclu\w*|mant(em|eve|er|ida|ido)|barr(a|am|ou|ado|ada|ar)'
    r'|autoriz\w*|bloque\w*|anul\w*|promulg\w*|rejeit\w*|determin(a|am|ou)|liber(a|am|ou|ado|ada|ar|acao)'
    r'|congel\w*|contingenc\w*|cort(a|am|ou|ar|e)|reduz\w*|aument(a|am|ou|ar|o)|zer(a|am|ou|ar)|isent(a|am|ou|ar)'
    r'|isencao|tribut(a|am|ou|ar)|edit(a|ou)|assin(a|am|ou)|liminar|decreto|mp|medida provisoria)\b')


def _decisao_mercado(titulo: str) -> bool:
    a = set(classificar(titulo))
    return bool(a & POLITICOS_DE_DECISAO) and bool(a & MERCADO) and bool(_ATO_RE.search(norm(titulo)))


GATILHOS: tuple[Gatilho, ...] = (
    Gatilho('Pesquisa eleitoral',
            'registro BR-XXXXX/2026 ou instituto conhecido (nome ambíguo, como Ideia ou Futura, só junto de "pesquisa")',
            _pesquisa),
    Gatilho('Copom e Selic', 'Copom ou Selic junto de decisão: corta, mantém, eleva, reduz, sobe, decide, juros', _copom),
    Gatilho('Resultado do TSE', 'TSE junto de totalização, apuração, resultado ou eleito', _tse),
    Gatilho('Decisão fiscal ou judicial × mercado',
            'fiscal, STF ou Congresso junto de bolsa, câmbio, juros, inflação ou estatal, com verbo de decisão',
            _decisao_mercado),
)

# --- Fora da lista: mercado de previsão e aposta ------------------------------------------------------------------
# Regra N8 do agente: casa de aposta, aposta eleitoral e mercado de previsão. O sentido figurado fica ("Mercado aposta
# em corte da Selic" é notícia de Copom). "apostila" e "apóstolo" não casam.
PREVISAO_RE = re.compile(
    r'\b(polymarket|kalshi|predictit|betfair|mercados? de previs(ao|oes)|prediction markets?|bets?|bet365'
    r'|(casas?|sites?|plataformas?|apps?) de apostas?|apostas? (esportivas?|eleitora(l|is)|online|politicas?)'
    r'|apost\w* (na|no|em) (eleicao|lula|flavio|bolsonaro|candidat\w*|presidente))\b')
HOSTS_PREVISAO = ('polymarket.com', 'kalshi.com', 'predictit.org', 'betfair.com', 'manifold.markets',
                  'electionbettingodds.com', 'futuur.com', 'metaculus.com', 'gjopen.com')
CATEGORIAS_FORA = frozenset({'mercados_previsao'})

# Manchete publicada mais de um dia antes da janela e só agora indexada (feed novo, histórico de podcast, índice
# zerado) não é notícia do dia.
ATRASO_MAXIMO = timedelta(days=1)

CAMPOS = ('titulo', 'link', 'fonte', 'quando', 'gatilhos')


def para_brasilia(valor: str | datetime | None) -> datetime | None:
    """Data ISO do índice (UTC, −03:00 ou sem fuso) no horário de Brasília. Sem data legível, None."""
    if not valor:
        return None
    if isinstance(valor, datetime):
        d = valor
    else:
        try:
            d = datetime.fromisoformat(str(valor).strip())
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=FUSO)
    return d.astimezone(FUSO)


def chave_link(url: str) -> str:
    """O mesmo endereço escrito de outro jeito (barra final, âncora, utm_*) conta como o mesmo link."""
    p = urlsplit(url.strip())
    query = urlencode([(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
                       if not k.lower().startswith('utm_') and k.lower() not in ('fbclid', 'gclid')])
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip('/'), query, ''))


def de_previsao(item: dict) -> bool:
    """Item de mercado de previsão ou de aposta: não entra na lista de jeito nenhum."""
    if item.get('categoria') in CATEGORIAS_FORA:
        return True
    host = urlsplit(item.get('url') or '').netloc.lower()
    if any(host == h or host.endswith('.' + h) for h in HOSTS_PREVISAO):
        return True
    return bool(PREVISAO_RE.search(norm(f"{item.get('titulo') or ''} {item.get('fonte') or ''}")))


def gatilhos_do_titulo(titulo: str) -> list[str]:
    """Nomes dos gatilhos que o título aciona, na ordem de GATILHOS. Título de mercado de previsão não aciona nada."""
    if not titulo or PREVISAO_RE.search(norm(titulo)):
        return []
    return [g.nome for g in GATILHOS if g.casa(titulo)]


def _aware(d: datetime) -> datetime:
    return d.replace(tzinfo=FUSO) if d.tzinfo is None else d


def selecionar(itens: Iterable[dict], desde: datetime, ate: datetime) -> list[dict]:
    """Manchetes coletadas pela primeira vez em [desde, ate) que acionam algum gatilho, sem repetir link nem título.

    Cada uma vira {titulo, link, fonte, quando, gatilhos}, e nada mais: nem resumo, nem texto da matéria.
    `quando` é a publicação no horário de Brasília (ou a coleta, se o feed não deu data). A lista sai da mais nova
    para a mais antiga.
    """
    itens = list(itens)
    desde, ate = _aware(desde), _aware(ate)
    primeira: dict[str, datetime] = {}  # uma falha passageira volta ao índice na rodada seguinte: vale a 1ª coleta
    for it in itens:
        coleta = para_brasilia(it.get('coletado_em'))
        if it.get('url') and coleta:
            k = chave_link(it['url'])
            if k not in primeira or coleta < primeira[k]:
                primeira[k] = coleta

    candidatos = []
    for it in itens:
        url = (it.get('url') or '').strip()
        titulo = ' '.join((it.get('titulo') or '').split())
        if not url or not titulo or it.get('tipo') == 'pagina' or de_previsao(it):
            continue  # retrato de página é a capa da fonte, não manchete
        coleta = primeira.get(chave_link(url))
        if coleta is None or not desde <= coleta < ate:
            continue
        publicado = para_brasilia(it.get('publicado'))
        if publicado and publicado < desde - ATRASO_MAXIMO:
            continue
        nomes = gatilhos_do_titulo(titulo)
        if nomes:
            candidatos.append((publicado or coleta, coleta, {
                'titulo': titulo, 'link': url, 'fonte': it.get('fonte') or '?', 'gatilhos': nomes}))

    candidatos.sort(key=lambda c: (c[0], c[1]))  # repetido: fica a primeira publicação
    links, titulos, saida = set(), set(), []
    for quando, _, sel in candidatos:
        k, t = chave_link(sel['link']), norm(sel['titulo'])
        if k in links or t in titulos:
            continue
        links.add(k)
        titulos.add(t)
        saida.append((quando, {**sel, 'quando': quando.isoformat(timespec='seconds')}))
    saida.sort(key=lambda s: s[0], reverse=True)
    return [{c: s[c] for c in CAMPOS} for _, s in saida]


def contar(selecionados: Iterable[dict]) -> Counter:
    """Quantos itens cada gatilho trouxe (um item com dois gatilhos conta nos dois)."""
    return Counter(n for s in selecionados for n in s['gatilhos'])


# --- A lista em Markdown ------------------------------------------------------------------------------------------
AVISO = ('**Lista para revisão do fundador. Nada disto vai para o usuário sem conferência: cada item é só uma '
         'manchete com link, e o fato só entra na base depois de conferido na fonte primária.**')

PASSO_A_PASSO = [
    '## Como um fato entra na base',
    '',
    '1. Abra a matéria e ache a fonte primária do fato: o PesqEle do TSE para pesquisa (com o registro '
    'BR-XXXXX/2026), a página de resultados do TSE para apuração e totalização, o comunicado do Copom no site do '
    'Banco Central para a Selic, o Diário Oficial, o STF ou o Planalto para decisão fiscal ou judicial. A matéria só '
    'aponta o fato; ela não é a fonte.',
    '2. Mercado de previsão e aposta (Polymarket, Kalshi e afins) nunca entra, nem como "termômetro".',
    '3. Leve para os dados só o fato: número, data, registro e o link da fonte primária. Nada do texto da matéria '
    '(direito autoral).',
    '4. Abra um PR no trade-agent mudando o arquivo de dados certo (por exemplo, `dados/agente/pesquisas_2026_2t.json`), '
    'com o link da fonte primária e a data da conferência na descrição.',
    '5. Uma segunda pessoa confere cada número contra a fonte primária e aprova o PR. Sem a segunda conferência, '
    'não tem merge.',
    '6. O merge publica sozinho: a Action Publicar exporta a base, roda os testes dos dois lados e põe a função no ar.',
]


def _hora(quando: datetime, dia: date) -> str:
    return f'{quando:%Hh%M}' if quando.date() == dia else f'{quando:%d/%m %Hh%M}'


def _ordem(sel: dict) -> datetime:
    return para_brasilia(sel.get('quando')) or datetime.min.replace(tzinfo=FUSO)


def _texto_link(s: str) -> str:
    return ' '.join(s.replace('[', '(').replace(']', ')').split())


def _url_md(url: str) -> str:
    return f'<{url}>' if re.search(r'[\s()<>]', url) else url


def markdown(selecionados: list[dict], dia: date, desde: datetime | None = None, ate: datetime | None = None) -> str:
    """A lista do dia agrupada por gatilho, com o título como link, a fonte e a hora (de Brasília)."""
    linhas = [f'# Gatilhos do dia — {dia:%d/%m/%Y}', '', AVISO, '']
    if desde and ate:
        d, a = para_brasilia(desde), para_brasilia(ate)
        linhas += [f'Janela: {d:%d/%m %Hh%M} a {a:%d/%m %Hh%M} (horário de Brasília). Regras fixas sobre o título, '
                   'sem IA.', '']
    if not selecionados:
        linhas.append('Nenhuma manchete nova casou com os gatilhos nesta janela.')
        return '\n'.join(linhas) + '\n'

    n = contar(selecionados)
    linhas += [f'{len(selecionados)} manchetes: ' + ', '.join(f'{g.nome} ({n[g.nome]})' for g in GATILHOS if n[g.nome])
               + '.', '']
    for g in GATILHOS:
        do_gatilho = [s for s in selecionados if g.nome in s['gatilhos']]
        if not do_gatilho:
            continue
        linhas += [f'## {g.nome} ({len(do_gatilho)})', '', f'_Casa quando o título tem {g.regra}._', '']
        for s in sorted(do_gatilho, key=_ordem, reverse=True):
            outros = [x for x in s['gatilhos'] if x != g.nome]
            extra = f" · também em: {', '.join(outros)}" if outros else ''
            quando = para_brasilia(s['quando'])
            hora = f' · {_hora(quando, dia)}' if quando else ''
            linhas.append(f"- [{_texto_link(s['titulo'])}]({_url_md(s['link'])}) — {s['fonte']}{hora}{extra}")
        linhas.append('')
    linhas += PASSO_A_PASSO
    return '\n'.join(linhas) + '\n'

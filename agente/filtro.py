"""O filtro de saída: barra frase proibida, número sem fonte e resposta sem os avisos.

Segue a tabela "O que o filtro barra" da nota de regras. Vale para a resposta da IA e para a do modo sem IA: as duas
passam por aqui antes de chegar à pessoa.
"""
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, localcontext

from .roteador import EXCH, simples  # EXCH: uma lista só de corretoras, no roteador e no filtro

# Verbos de recusa: "não digo X", "nem dou X", "não posso afirmar", "não sei se". Uma frase proibida depois deles, na
# mesma oração, é a recusa e não a dica.
RECUSANDO = re.compile(r'\b(nao|nem|nunca)\s+(\w+\s+){0,2}?(digo|dizer|diria|dou|dar|indico|indicar|faco|fazer|calculo|'
                       r'calcular|comento|comentar|uso|usar|monto|montar|mostro|estimo|prometo|mando|ensino|comparo|trato|'
                       r'mudo|tiro|pergunto|apresento|recomendo|sugiro|afirmo|afirmar|sei|sabemos|saber|prever|prevejo|'
                       r'garanto|garantir|consigo|como)\b|\b(proibe|proibem|proibido|proibida|proibidas)\b'
                       r'|\b(ninguem|nenhum|nenhuma|impossivel|nao e possivel|nao ha como|nao tenho como)\b')
VERBOS_DE_RECUSA = re.compile(r'(digo|dou|indico|faco|calculo|comento|uso|monto|mostro|estimo|prometo|mando|ensino|'
                              r'comparo|recomendo|sugiro|pergunto|apresento)\b')
# Atribuição: o fato é de quem disse ("o programa promete", "pelo Focus", "segundo a FGV"), não do agente.
ATRIBUICAO = re.compile(r'\b(diz|disse|dizem|afirma|afirmou|propoe|propos|promete|prometeu|defende|registrou|segundo|'
                        r'pelo boletim|pelo focus|o focus|os economistas|de acordo com)\b')
AMBAS = re.compile(r'\b(subir ou cair|sobe ou cai|cair ou subir|cai ou sobe|alta ou queda|queda ou alta|'
                   r'para cima ou para baixo|pra cima ou pra baixo)\b')
INEXISTENTE = re.compile(r'\bnao (existe|ha|tem)\b')
ORACAO = re.compile(r'[.!?;:\n]|\b(mas|porem|contudo|entretanto|so que)\b')

SUJ = (r'(o |a |os |as )?(ibovespa|ibov|bolsa|indice|mini-indice|mini indice|dolar|euro|real|juros|di1?|bitcoin|cripto|'
       r'token|memecoin|win|wdo|bova11|acoes|mercado)')
DIR = (r'(sobe|sobem|subira|subiria|subir|suba|cai|caem|caira|cairia|cair|caia|dispara|disparar|despenca|despencar|'
       r'derrete|derreter|valoriza|valorizar|desvaloriza|desvalorizar|aprecia|apreciar|se apreciar|recua|recuar|cede|'
       r'ceder|fecha|fechar|abre|abrir|melhora|piora|reagir bem|reagir mal|reage bem|reage mal|vai bem|vai mal)')

# (regra, padrão, isenções). Padrões sobre o texto em minúsculas e sem acento.
# Isenções: 'recusa' (oração com verbo de recusa ou "ninguém sabe"), 'atribuicao' (o fato é de quem disse), 'ambas'
# (as duas direções juntas), 'inexistente' ("não existe lucro garantido").
R, A, B, I = 'recusa', 'atribuicao', 'ambas', 'inexistente'
PADROES = [
    # N1: ordem, "bom momento", "se eu fosse você"
    ('N1', r'\b(compre|comprem|vende ja|venda ja|venda tudo|vende tudo|zere|zerem|aproveite|mantenha (a )?posicao|'
           r'realize o lucro|considere (comprar|vender|entrar))\b', {R}),
    ('N1', r'(^|[.!?;:,]\s*)(compra|vende) (na|no|ja|agora|antes|tudo|hoje|amanha|logo)\b', {R}),
    ('N1', r'\b(entr(a|e|em)|entrar|ficar|fica|fique|estar|bora entrar) (comprado|vendido|posicionado|de fora|na alta|na baixa)\b', {R}),
    ('N1', r'\bpode (comprar|vender|entrar|apostar|operar) (sem medo|tranquilo|ja|agora|sem)\b', set()),
    ('N1', r'\b(boa|otima|melhor) hora (de|para|pra)\b|\bhora (de|pra|para) (comprar|vender|entrar|sair|operar)\b', {R}),
    ('N1', r'\bvale a pena (comprar|vender|entrar|operar|investir)\b|\bvale considerar\b|\bnao seria loucura\b'
           r'|\bfaz sentido (ter|estar|comprar|entrar|montar|operar)\b|\bpode ser interessante\b'
           r'|\b(boa|otima|grande) (janela|oportunidade)\b|\bmomento (e |esta )?favoravel\b|\b(agora|hoje) e (o|a) (momento|hora)\b'
           r'|\b(bom|otimo|melhor) momento (para|pra|de)\b|\boportunidade (de|para|pra) (compra|venda|entrada|comprar|vender|entrar|ganho|lucro)\b'
           r'|\b(bom|otimo|melhor) dia (para|pra) (tentar|operar|entrar|comprar|vender)\b|\bvale mais (estar|ter|ficar|comprar)\b', {R}),
    ('N1', r'\b(se eu fosse voce|se fosse voce|no seu lugar)\b', set()),
    ('N1', r'\beu (ficaria|aguardaria|esperaria|compraria|venderia|entraria|usaria|manteria|apostaria)\b', set()),
    ('N1', r'\b(voce|vc) deve(ria)? (comprar|vender|entrar|sair|operar|investir|zerar|esperar)\b', {R}),
    ('N1', r'\b(recomendo|sugiro) (comprar|vender|entrar|sair|a compra|a venda|ficar)\b', {R}),
    ('N1', r"\b(you should|i would|i'd|you'd better) (buy|sell)\b|\bcompraria\b|\bdeberias? comprar\b", set()),
    # N2: direção provável, dita de qualquer jeito
    ('N2', rf'\b{SUJ}\b( \w+){{0,3}}? (nao )?(vai|vao|deve|devem|deveria|tende a|tendem a|pode|podem|ira|promete)( \w+)? {DIR}\b', {R, A, B}),
    ('N2', rf'\b{SUJ} (\w+ ){{0,2}}?(sobe|sobem|cai|caem|dispara|despenca|derrete|valoriza|desvaloriza|recua|cede|melhora|piora)\b', {R, A, B}),
    ('N2', r'\b(vai|vao|deve|devem|tende a|tendem a) (subir|cair|disparar|despencar|valorizar|desvalorizar|explodir|bombar)\b', {R, A, B}),
    ('N2', r'\b(tendencia|vies|o mais provavel|mais provavel|provavelmente|probabilidade maior|o esperado|espera-se|esperase|'
           r'a expectativa|perspectiva)\b[^.\n]{0,30}\b(alta|queda|positiv\w*|negativ\w*|valorizacao|desvalorizacao|vendedor\w*|'
           r'comprador\w*|altista|baixista|subir|suba|cair|caia)\b', {R, A}),
    ('N2', r'\b(favorece|a favor de quem compra|assimetria|espaco para (subir|cair|valorizar)|tem espaco|potencial de (alta|valorizacao)|'
           r'bom potencial|risco-retorno|risco retorno)\b', {R}),
    ('N2', r'\b(minha visao|minha opiniao|na minha opiniao|minha aposta|minha leitura e|acho que (sobe|cai|vale|vai)|vejo (uma )?chance)\b', set()),
    ('N2', r'\b(sim|nao)[:,]? (o \w+ |a \w+ )?(sobe|cai|vai subir|vai cair)\b|(^|[.!?]\s+)(sobe|cai|desce|dispara)[.!]', set()),
    ('N2', r'\d+([.,]\d+)? ?(%|por cento) de (chance|probabilidade)|\bchance de \d+ ?%', set()),
    ('N2', r'\b(chance|chances|probabilidade|probabilidades) (de|do|da) (\w+ ){0,3}?(alta|queda|subir|cair|subida|valorizacao|'
           r'ganho|lucro|vitoria|vencer|ganhar)\b', {R, A}),
    ('N2', r'\b(flavio|lula|bolsonaro)\b[^.\n]{0,15}\b(deve|vai|tende a) (vencer|ganhar|levar|ser eleito|perder)\b'
           r'|\b(e|eh) o favorito\b|\bfavorito (para|pra)\b', {R, A}),
    ('N2', r'\bvitoria d[oa] \w+ (e|significa|seria) (alta|queda)\b|\b(esta|ta) (barat[oa]|car[oa]|no topo|no fundo|descontad[oa])\b', set()),
    ('N2', r'\bnota \d+ de (0 a )?(10|100)\b|\b\d+ de 0 a 100\b|\b(preco-alvo|preco alvo|projecao|projetamos) (de|para|em) \d', set()),
    ('N2', r'\bwill (probably )?(go up|go down|rise|fall|strengthen|weaken|rally)\b|\btends? to (rally|rise|fall|go up)\b'
           r'|\bva a (subir|bajar)\b', set()),
    ('N2', r'\b(win|wdo|dol|ind|di1|bova11|petr[34]|vale3|itub4|bbas3|bbdc4)\b[^.\n]{0,25}\b(vai subir|vai cair|comprad[oa]|'
           r'vendid[oa]|vies|alvo|disparar)\b', {R}),
    # N3: manchete de direção a partir do histórico
    ('N3', r'\b(subiu|caiu|subiram|cairam|fechou em alta|fechou em queda|deu alta|deu queda|valorizou|desvalorizou)\b[^.\n]{0,40}'
           r'\b\d+ (de|em|das|dos) \d+\b', set()),
    ('N3', r'(?<![\d,./])\b(uma|duas|tres|quatro|cinco|seis|sete|oito|nove|dez|\d+) (das|de|em|dos) (duas|tres|quatro|cinco|seis|'
           r'sete|oito|nove|dez|\d+)\b(?![\d,./])[^.\n]{0,50}\b(subiu|subiram|caiu|cairam|alta|queda|sobe|cai|positiv|negativ)', set()),
    ('N3', r'\b(subiu|caiu|subiram|cairam)\b[^.\n]{0,25}\bem (todos|todas) (os|as)\b|\bem (todos|todas) (os|as) \d+ \w+[^.\n]{0,30}\b(subiu|caiu|alta|queda)', set()),
    ('N3', r'\b(na maioria|na maior parte|maior parte das|maioria dos|maioria das|quase sempre|sempre)\b[^.\n]{0,40}\b(sub\w*|cai|caiu|'
           r'cairam|alta|queda)\b|\b(subiu|caiu|sobe|cai)\b[^.\n]{0,25}\b(na maioria|na maior parte|maior parte)\b', set()),
    ('N3', r'\bem \d+ ?% das (vezes|reunioes|eleicoes|turnos|casos)\b|\bo esperado e (alta|queda)\b', set()),
    ('N3', r'\b(historicamente|em geral|normalmente|tipicamente|costuma|costumam)\b[^.\n]{0,25}\b(sobe|subir|cai|cair|reagir bem|'
           r'reagir mal|reage bem|reage mal|valoriza)\b', set()),
    # N4: momento, entrada, saída, stop, alvo, alerta, pregão ao vivo
    ('N4', r'\bstop( loss| gain)? (em|de|no|na|a) \d|\bstop (logo )?(abaixo|acima)\b|\b(poe|ponha|coloque|coloca|use) o stop\b|\bum stop de\b', set()),
    ('N4', r'\b(alvo|preco-alvo|preco alvo) (natural|fica|em|de|perto)\b|\b(entrada|saida|ponto de entrada|ponto de saida) (em|de|no|na|a) \d', set()),
    ('N4', r'\bsaia no fim do dia\b|\bentre com \d+ contratos?\b|\bde olho na (abertura|virada|vespera)\b'
           r'|\b(compr|vend|entr)\w* [^.\n]{0,20}\bna vespera\b', set()),
    ('N4', r'\b(entre|entrar|compre|comprar|venda|vender|opere|operar) (na|no|ate a|antes d[oa]) (abertura|fechamento|sexta|segunda|vespera)\b', {R}),
    ('N4', r'\b(melhor hora|hora certa|momento certo) (para|pra|de) (entrar|operar|comprar|vender)\b', {R}),
    ('N4', r'\bte (aviso|alerto|mando um alerta)\b|\bvou te avisar\b|\b(alerta|sinal) de (compra|venda|entrada)\b', {R}),
    ('N4', r'\bneste momento\b[^.\n]{0,40}\b(caindo|subindo)\b|\btendencia do dia\b', set()),
    # N5: capital, perfil, objetivo
    ('N5', r'\b(com|seus|teus|esses|esse|para quem tem) (r\$ ?\d[\d.,]*( mil)?|\d+ ?k|\w+ mil reais|cinco mil)\b[^.\n]{0,60}'
           r'\b(contratos?|coloque|aloque|invista|aplique|compre|opera\w*|comecar|em cripto|em renda fixa|em bitcoin|%|o ideal)', set()),
    ('N5', r'\b(coloque|aloque|invista|aplique|ponha|reparta)\b[^.\n]{0,30}(\d+ ?%|r\$|contratos?|metade|um terco|tudo)', set()),
    ('N5', r'\b(para|pra) (o seu|seu|a sua|sua) (perfil|capital|caso|objetivo|aposentadoria|idade|reserva)\b|\bcom o seu capital\b'
           r'|\bcomo (voce|vc) tem \d+ anos\b|\bsua reserva de emergencia\b', {R}),
    ('N5', r'\b(\d+|um|uma|dois|duas) (contratos?|minicontratos?|lotes?) (e|eh) o ideal\b|\bo ideal e comecar\b'
           r'|\bda (pra|para) operar (uns |ate )?\d+|\b(opere|comece com|use) \d+ (contratos?|lotes?)\b', set()),
    ('N5', r'\b(voce|vc) e (mais )?(conservador|arrojado|moderado)\b|\bqual (e )?(o )?seu (objetivo|prazo|perfil|capital|patrimonio)\b', set()),
    # N7 e N8: exchange, corretora, plataforma de previsão ou de aposta
    ('N7', rf'\b(usaria|use|usa|utilize|abra (sua |uma )?conta (na|no)|cadastre-se (na|no)|baixe|recomendo|indico|prefira|pode usar)\b'
           rf'[^.\n]{{0,25}}\b({EXCH}|polymarket|kalshi|iq option)\b', {R}),
    ('N7', rf'\b{EXCH}\b[^.\n]{{0,40}}\b(melhor|mais segura|mais barata|confiavel|opcao)\b|\ba melhor (exchange|corretora|plataforma)\b', {R}),
    ('N7', r'\b(use|usa|utilize|abra conta n[ao]|cadastre-se n[ao]|prefira|recomendo|indico) (a |o |uma |um )?(exchange|corretora|plataforma|app|token)\b', {R}),
    ('N7', r'\b(token|memecoin)\b[^.\n]{0,30}\b(bom potencial|potencial|vai valorizar|pode valorizar|valoriza)\b', set()),
    ('N8', r'polymarket\.com|kalshi\.com|iqoption\.com', set()),
    ('N8', r'\b(polymarket|kalshi|mercados? de previsao)\b[^.\n]{0,50}(\d+ ?%|\d+ centavos|cotad|acert\w*|confiave\w*|boa ideia|termometro)', {R}),
    ('N8', r'\b(use|usa|ative|instale|uma|com|pela|por) vpn\b|\bvpn (funciona|resolve|libera|passa)\b|\btrocando a regiao\b'
           r'|\b(acessar|usar) a (kalshi|polymarket)\b|\b(aposte|pode apostar) (na|no|em)\b', {R}),
    ('N8', r'\btermometro real\b|\bverdadeira pesquisa\b|\bmelhor que as pesquisas\b|\bacert\w* mais que (as pesquisas|os institutos)\b'
           r'|\bmais confiavel que as pesquisas\b', {R}),
    # N9: voto e lado
    ('N9', r'\bem quem (voce|vc) (vota|votou|vai votar|pretende|votaria)\b|\b(voce|vc) votou\b|\bqual (e )?(o )?seu candidato\b'
           r'|\bqual candidato (voce|vc) prefere\b|\b(voce|vc) (e|eh) (de direita|de esquerda|petista|bolsonarista|lulista)\b'
           r'|\b(voce|vc) apoia\b|\b(voce|vc) tende (mais )?(para|pro)\b|\btorcendo (pelo|pela|por|pro)\b|\bvote (no|na|em)\b', {R}),
    ('N9', r'\b(flavio|lula|bolsonaro|o pt|o pl)\b[^.\n]{0,25}\b(e|seria|eh) (o )?(melhor|pior|ruim|bom|otimo|pessimo) (para|pro|pra)\b'
           r'|\bmelhor candidato\b|\b(o mercado|os investidores|investidores) (claramente )?(prefere|preferem|quer|querem|gosta|gostam|'
           r'veem com bons olhos|ve com bons olhos)\b|\bpreferido do mercado\b|\bcandidato do mercado\b'
           r'|\bvitoria d[oa] \w+ (seria|e) (ruim|boa|otima|pessima|positiva|negativa)\b', {R, A}),
    # M2: ranking e destaque de ativo
    ('M2', r'\b(as|os) (\w+ )?(acoes|ativos|papeis) que mais (se beneficiam|sobem|ganham)\b|\bque mais se beneficia\w*\b|\b(top|ranking) \d', set()),
    # M6: promessa de ganho ou de acerto
    ('M6', r'\b(lucro|ganho|renda) (garantid[oa]|certo|certa|facil|extra|mensal)\b|\bsem risco\b|\bdinheiro facil\b|\baprenda a lucrar\b'
           r'|\b(acerta|acertamos|acertou|acerto de) \d+ ?%|\btaxa de acerto\b|\b(fique|ficar) rico\b|\btirar uma renda\b'
           r'|\bretorno consistente\b|\bacerta a direcao\b|\bmodelo acerta\b', {R, I}),
    # D6: urgência
    ('D6', r'\b(ultima chance|nao perca|corra|imperdivel|agora ou nunca|agora e a hora|nao da (pra|para) ficar de fora|quem entrar cedo)\b'
           r'|\bcorre (pra|para)\b|\bantes que (o \w+ |a \w+ )?(seja tarde|acabe|suba|caia|passe|dispare)\b|\bcerteza absoluta\b'
           r'|\bcom (toda )?certeza (vai (subir|cair)|o \w+ (sobe|cai))\b|\brapido,? (entra|compra|vende|antes)\b', set()),
]
PADROES = [(r, re.compile(p), isencoes) for r, p, isencoes in PADROES]


@dataclass(frozen=True)
class Violacao:
    regra: str
    trecho: str


def _isento(t: str, m: re.Match, isencoes: set) -> bool:
    inicio = max([x.end() for x in ORACAO.finditer(t, 0, m.start())] or [0])
    prox = ORACAO.search(t, m.end())
    oracao = t[inicio:prox.start() if prox else len(t)]
    antes = t[inicio:m.start()]
    if R in isencoes:
        if RECUSANDO.search(antes):
            return True
        # "não indico corretora": a própria frase barrada começa no verbo de recusa negado.
        if re.search(r'\b(nao|nem|nunca)\s+$', antes) and VERBOS_DE_RECUSA.match(t, m.start()):
            return True
    if A in isencoes and ATRIBUICAO.search(oracao):
        return True
    if B in isencoes and AMBAS.search(oracao):
        return True
    if I in isencoes and INEXISTENTE.search(antes):
        return True
    return False


def frases_proibidas(texto: str) -> list[Violacao]:
    t = simples(texto)
    achados = []
    for regra, rx, isencoes in PADROES:
        for m in rx.finditer(t):
            if isencoes and _isento(t, m, isencoes):
                continue
            achados.append(Violacao(regra, t[max(0, m.start() - 30):m.end() + 30].strip()))
    return achados


# ---------- números ----------

URL = re.compile(r'https?://\S+')
REF = re.compile(r'\[\d+\]')
CODIGO = re.compile(r'\b[A-Z]{1,6}\d{1,4}[A-Z]?\d*\b|\bR\d/\d{4}\b|\bBR-\d{5}/\d{4}\b')  # WINZ26, R2/2020, BR-01234/2026
NUMERO = re.compile(r'\d+(?:[.,]\d+)*')
SEMPRE_PERMITIDO = 12  # inteiros pequenos: "3 linhas", "1 contrato", "2º turno"
MAX_DIGITOS = 20


def _valor(tok: str) -> tuple[Decimal, int] | None:
    """Número em formato brasileiro (ou não) → (valor, casas decimais)."""
    try:
        if re.fullmatch(r'\d{1,3}(\.\d{3})+(,\d+)?', tok):
            tok = tok.replace('.', '').replace(',', '.')
        elif ',' in tok:
            tok = tok.replace('.', '').replace(',', '.')
        elif tok.count('.') > 1:
            tok = tok.replace('.', '')
        d = Decimal(tok)
    except InvalidOperation:
        return None
    return d, max(0, -d.as_tuple().exponent)


def numeros(texto: str) -> list[tuple[str, Decimal, int]]:
    t = CODIGO.sub(' ', REF.sub(' ', URL.sub(' ', texto)))
    saida = []
    for m in NUMERO.finditer(t):
        v = _valor(m.group())
        if v is None:
            continue
        valor, casas = v
        if re.match(r'\s*mil\b', t[m.end():]):
            valor, casas = valor * 1000, -3
        saida.append((m.group(), valor, casas))
    return saida


def _pequeno(v: Decimal) -> bool:
    return v == v.to_integral_value() and v <= SEMPRE_PERMITIDO


def numeros_sem_fonte(texto: str, fatos: str) -> list[str]:
    """Os números da resposta que não aparecem nos fatos, nem arredondados (D8)."""
    base = [f for f in {v for _, v, _ in numeros(fatos)} if abs(f) < 10 ** 12]
    soltos = []
    for tok, v, casas in numeros(texto):
        if _pequeno(v):
            continue
        # Número com mais de 20 dígitos não existe nos fatos: é solto, sem conta (e sem depender da ordem do set).
        if len(re.sub(r'\D', '', tok)) > MAX_DIGITOS:
            soltos.append(tok)
            continue
        q = Decimal(1).scaleb(-casas)
        with localcontext() as ctx:
            ctx.prec = 60  # 12 dígitos inteiros + 20 casas cabem; o quantize nunca estoura
            if any(f.quantize(q) == v.quantize(q) for f in base):
                continue
        soltos.append(tok)
    return soltos


# ---------- o que toda resposta precisa ter ----------

def faltas(texto: str) -> list[Violacao]:
    t = simples(texto)
    f = []
    if not ('sou uma ia' in t and 'nao e recomendacao' in t and 'cvm' in t):
        f.append(Violacao('D3', 'faltam os avisos: sou uma IA, posso errar, não é recomendação, não somos credenciados'))
    if 'rentabilidade passada' not in t:
        f.append(Violacao('D2', 'falta "rentabilidade passada não indica rentabilidade futura"'))
    if any(not _pequeno(v) for _, v, _ in numeros(texto)) and not URL.search(texto):
        f.append(Violacao('D1', 'tem número e não tem fonte com link'))
    # "futuro de bitcoin" (o contrato) pede o D4, também por ticker e no plural ("futuros de BTC", "opções de ether");
    # "futuro de cripto é valor mobiliário" (a frase do D5) não
    if re.search(r'\bmini[- ]?(indice|dolar)\b|\bwin\b|\bwdo\b|\bdi futuro\b'
                 r'|\bfuturos? de (bitcoins?|btc|ether|ethereum|eth|solana|sol)\b'
                 r'|\bopc(ao|oes) (de|sobre)[^.]*\b(bitcoins?|btc|ether|ethereum|eth|solana)\b', t) and not re.search(
            r'perder mais do que|perda pode passar', t):
        f.append(Violacao('D4', 'fala de derivativo e não avisa que a perda pode passar do depositado'))
    if re.search(r'\bcripto|\bbitcoin\b', t) and 'nao e valor mobiliario' not in t:
        f.append(Violacao('D5', 'fala de cripto e não diz que, em regra, não é valor mobiliário'))
    return f


def checar(texto: str, fatos: str) -> list[Violacao]:
    return (frases_proibidas(texto) + faltas(texto)
            + [Violacao('D8', f'número sem fonte nos fatos: {n}') for n in numeros_sem_fonte(texto, fatos)])

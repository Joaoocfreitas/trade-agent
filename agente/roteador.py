"""Entende a pergunta: de que mercado, candidato e tema ela fala, e que pedido proibido ela traz.

O mercado e o tema servem só de filtro de busca no repertório (P3): a resposta não depende de quem pergunta.
O capital, o perfil e o voto que a pessoa contar são detectados para NÃO serem usados (N5, N9).

Regra da casa: errar para mais na recusa. Pergunta sobre o futuro de um mercado ("sobe?", "se o Lula ganhar, o
dólar...", "é topo?") leva a recusa padrão, mesmo dita com gíria, erro de digitação, emoji, em inglês ou dentro de
uma história. Com credencial da API, a IA também classifica a pergunta (agente/ia.py) e os dois resultados se somam.
"""
import re
import unicodedata
from dataclasses import dataclass, field

# Símbolo de moeda que o simples() apagaria: vira palavra antes ("€150.000" → "euros 150.000").
SIMBOLOS = {'€': ' euros '}
# Corretoras de cripto pelo nome (a mesma lista do filtro de saída).
# "binanse" é o erro de digitação comum.
# "bianance" e "coinbse" também; "MB" (Mercado Bitcoin) só depois de artigo, preposição ou "ou" ("binance ou mb?", "o mb é
# seguro?"), para não pegar "5 mb".
EXCH = (r'(binan[cs]e|b[iy]?an[ac]n[cs]e|coinba?se|mercado bitcoin|foxbit|bybit|okx|kraken|novadax|bitso|bitget|kucoin'
        r'|(?:^|(?<=\bo )|(?<=\ba )|(?<=\bno )|(?<=\bna )|(?<=\bdo )|(?<=\bda )|(?<=\bou )|(?<=\bx ))mb)')
EMOJI = {'📈': ' sobe ', '📉': ' cai ', '🚀': ' dispara ', '🔥': ' dispara ', '💰': ' lucro ', '🤑': ' lucro ',
         '⬆️': ' sobe ', '⬇️': ' cai ', '⬆': ' sobe ', '⬇': ' cai '}
# Abreviações e erros de digitação comuns do público (internetês).
ABREVIACOES = {'q': 'que', 'vc': 'voce', 'vcs': 'voces', 'qnd': 'quando', 'qdo': 'quando', 'hr': 'hora', 'eh': 'e',
               'tb': 'tambem', 'tbm': 'tambem', 'mto': 'muito', 'c': 'com', 'n': 'nao', 'pq': 'porque',
               'subi': 'subir', 'chace': 'chance', 'chanse': 'chance', 'ibov': 'ibovespa', 'msm': 'mesmo',
               'ptr4': 'petr4', 'ptr3': 'petr3', 'oq': 'o que', 'oque': 'o que'}


def simples(s: str) -> str:
    """Minúsculas e sem acento, mas com pontuação ($, %, vírgula), que os padrões usam."""
    return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()


def normalizar(pergunta: str) -> str:
    """Emoji e símbolo de moeda viram palavra, sai o acento, e a abreviação vira a palavra inteira."""
    for e, palavra in SIMBOLOS.items():
        pergunta = pergunta.replace(e, palavra)
    for e, palavra in EMOJI.items():
        pergunta = pergunta.replace(e, palavra)
    # "Irã" (o país) e "irá" (o verbo) só se distinguem antes de tirar o acento.
    pergunta = re.sub(r'(?<!\w)irã(?!\w)', 'iran', pergunta, flags=re.I)
    t = simples(pergunta)
    t = re.sub(r'\b\w+\b', lambda m: ABREVIACOES.get(m.group(), m.group()), t)
    # "petro" é a Petrobras, menos o presidente da Colômbia ("o Gustavo Petro", "o Petro ganhou na Colômbia")
    t = re.sub(r'(?<!\bgustavo )\bpetro\b(?![^.?!]{0,40}\bcolombi\w*)', 'petrobras', t)
    # o ticker com espaço ("vale a pena petr 4?") é o ticker
    return re.sub(r'\bpetr ([34])\b', r'petr\1', t)


MERCADOS = {
    'mini_indice': r'\bmini[- ]?indices?\b|\bwin\b|\bwin[fghjkmnquvxz]\d\d\b|\bindice futuro\b',
    'mini_dolar': r'\bmini[- ]?dolar\b|\bwdo\b',
    'ibovespa': r'\bibov\w*|\bbolsa\b|\bacoes\b|\bacao\b|\bbova11\b|\bb3\b|\bbovespa\b|\bstocks?\b|\bindice\b',
    'dolar': r'\bdolar(es)?\b|\bdollars?\b|\bus\$|\bcambio\b|\b(brazilian )?real (sobe|cai|valoriza|desvaloriza|go up|go down)\b'
             r'|\bbrazilian real\b|\bexchange[- ]rates?\b|\b(foreign|currency) exchange\b'
             # o real contra as outras moedas, e mandar ou trazer dinheiro de fora: é câmbio
             r'|\breal\b[^.?!]{0,30}\b(valoriz\w*|desvaloriz\w*|fortalec\w*|enfraquec\w*)|\b(valorizacao|desvalorizacao) do real\b'
             # o verbo logo depois de "real": "o real problema está..." não é câmbio
             r'|\b(o|do|no|pro|pelo|com o) real (reag\w*|esta|ta|caiu|cai|subiu|sobe|fic\w*|contra|frente|diante|depois|antes'
             r'|vai|vem)\b|\breal brasileiro\b'
             r'|\bmoeda (brasileira|estrangeira)\b|\bremessas?\b|\btransferencias? internaciona\w*|\bconvert\w* (para|pra|em) reais\b'
             r'|\b(trazer|traz|trago|mandar|mando|enviar|envio|levar|transferir)\b[^.?!]{0,30}\b(pro brasil|para o brasil|pra fora'
             r'|para fora|do exterior|de fora|para o exterior|pro exterior)\b',
    'euro': r'\beuros?\b|\beur\b',
    'petroleo': r'\bpetroleo\b|\bbrent\b|\bwti\b|\bpetrobras\b|\bpetr[34]\b|\bprio3?\b|\bopep\b|\bopec\b|\bdiesel\b|\bormuz\b'
                r'|\bpetroleiras?\b|\boil\b|\bcrude\b'
                r'|(?<!\btroca de )\boleo\b(?! (de |do )?(soja|palma|cozinha|oliva|girassol|milho|coco|canola|algodao|motor|carro'
                r'|essencia\w*|lubrificante\w*)\b)'
                # em sentido figurado não é petróleo: "o combustível da alta", "o combustível para a Selic subir", "barril de
                # pólvora"; "jogou gasolina no dólar" sai antes (GASOLINA_FIGURADA)
                r'|\bcombustive(l|is)\b(?!( extra| adicional)? (da|do|de|para|pra|pro|dessa|desta|nessa|nesta)'
                r'( (a|o|as|os|uma|um|essa|esta|novas?|mais))* (altas?(?! temporada)|quedas?|rali|dolar|bolsa|mercado|ibovespa'
                r'|juros|crise|eleicao|selic|inflacao|cambio)\b)'
                r'|\bgasolina\b(?! n[ao] (fogueira|fogo|incendio|brasa)\b)'
                r'|\bbarril\b(?! de polvora\b)',
    'juros': r'\bjuros\b|\bdi1?\b|\bdi futuro\b|\bselic\b|\brenda fixa\b|\btesouro\b|\bprefixad\w*',
    # "exchange" é a corretora de cripto, não o verbo nem o câmbio em inglês ("exchange my dollars", "exchange rate")
    'cripto': r'\bcripto\w*|\bbitcoins?\b|\bbtc\b|\bethereum\b|\bethers?\b|\beth\b|\bxrp\b|\bstablecoins?\b'
              # o intercâmbio é masculino ("fazer exchange no Canadá", "um exchange na Irlanda"); a corretora é "a exchange"
              r'|(?<!\bto )(?<!\bi )(?<!\bwe )(?<!\bforeign )(?<!\bcurrency )(?<!\bfazer )(?<!\bfaco )(?<!\bum )(?<!\bdo )(?<!\bno )'
              r'\bexchanges?\b'
              r'(?![ -](rates?|my|the|them|it|your|our|their|this|that|these|those|some|all|euros?|dollars?|reais|real|money'
              r'|currency|currencies|usd|eur|brl|now|today|before|after|\d))'
              r'|\bsolana\b|\bhalving\b|\bftx\b|\busdt\b|\busdc\b|\btether\b|\bhash11\b|\bdoge\w*|\bshiba\b'
              # a lei das stablecoins dos EUA e o ETF aprovado pela SEC, sem a palavra cripto
              r'|\bgenius act\b|\betfs?\b[^.?!]{0,30}\bsec\b|\bsec\b[^.?!]{0,30}\betfs?\b'
              # o corte do Pix das corretoras de cripto (06/11/2026), sem a palavra "cripto"; "pix para a corretora" não
              r'|\bpix\b[^.?!]{0,40}\bcorretoras?\b[^.?!]{0,40}\b(parar|cortar|corta|corte|cortad[oa]|bloque\w*|suspen\w*|acab\w*)\b'
              r'|\b(parar|cortar|corta|corte|cortad[oa]|bloque\w*|suspen\w*|acab\w*)\b[^.?!]{0,40}\bpix\b[^.?!]{0,40}\bcorretoras?\b|'
              + rf'\b{EXCH}\b',
    'memecoin': r'\bmeme ?coins?\b|\bmemecoins?\b|\$trump\b|\$libra\b|\$melania\b|\btokens?\b|\bmoeda do candidato\b',
    'previsao': r'\bpolymarket\b|\bkalshi\b|\bmercados? de previs\w*',
}

# Pôr gasolina em algo ("jogou gasolina no dólar", "o Copom colocou gasolina no dólar", "a eleição pôs gasolina na
# bolsa", "botou mais gasolina") é figurado: sai do texto antes de achar o mercado. Sem "por" ("trocar etanol por gasolina").
GASOLINA_FIGURADA = (r'\b(jog(a|am|ar|ou|aram|ando)|bot(a|am|ar|ou|aram|ando)|coloc(a|am|ar|ou|aram|ando)|pos|poe|poem'
                     r'|puseram|pondo|despej(a|ar|ou|aram|ando)|tac(a|ar|ou|aram|ando)|derram(a|ar|ou|aram|ando))'
                     r'( mais| muita| um pouco de)? gasolina\b'
                     # só com o alvo figurado depois: "colocar gasolina no carro" e "o preço de colocar gasolina" são a bomba
                     r'(?= (n[ao]s?|em|sobre|em cima d[aoe]s?) (o |a |os |as )?(alta|queda|rali|dolar|real|bolsa|ibovespa|mercado'
                     r'|juros|selic|inflacao|crise|cambio|fogueira|fogo|incendio|brasa|eleic(ao|oes)|campanha|debate|briga|polemica'
                     r'|discussao|tensao)\b)')
# "Jair Bolsonaro" e o "ex-presidente Bolsonaro" não são o candidato.
CANDIDATOS = {'flavio': r'\bflavio\b|(?<!\bjair )(?<!\bex-presidente )(?<!\bex presidente )(?<!\bexpresidente )\bbolsonaro\b',
              'lula': r'\blula\b'}
# Palavra que faz a pergunta ser de eleição mesmo citando cargo de empresa ("se o Lula ganhar, troca o presidente da
# Petrobras?"). Sem ela, o presidente da Petrobras não é o da República, e o Bolsonaro que trocou o comando da
# Petrobras não é o candidato.
# "a Petrobras pode perder o presidente?" e "o Prates foi eleito presidente da Petrobras" (ou "pelo conselho") falam da
# empresa.
ELEITORAL = (r'\belei(cao|coes|toral|torais)\b|\bturnos?\b|\bcandidat\w*|\burnas?\b|\bpesquisas?\b|\bvot(o|ar)\b'
             r'|\bganhar\b(?! (bonus|salario|premio|aumento)\b)|\bvencer\b|\bperder\b(?! (o|seu) (presidente|ceo|comando|cargo|posto)\b)'
             r'|\beleito\b(?! (presidente|ceo)( d[aoe]| na| no)? (petrobras|petr[34]|prio3?|estatal|companhia|empresa)\b| pelo conselho\b)'
             r'|\bproximo presidente\b|\blula\b|\bflavio\b|\bcampanha\b'
             r'|\bse o (?!(brent|wti|barril|petroleo|dolar|euro|ibovespa|bitcoin|preco|juros|selic|ipca)\b)\w+ voltar\b')
# O Bolsonaro que mexeu no comando da Petrobras ("quando o Bolsonaro trocou o presidente da Petrobras?") é o governo, não o
# candidato. Sem o fato do governo ("com o Bolsonaro, a Petrobras e o dólar sobem?"), é a eleição.
GOVERNO_BOLSONARO = (r'\b(trocou|trocaram|troca|trocar|indicou|indicar|demitiu|demitir|nomeou|nomear|interferiu|interferir'
                     r'|tirou|mudou|mexeu)\b')
# O governo que passou, pelo nome ("no governo do Bolsonaro", "na época do Bolsonaro", "na gestão Bolsonaro"), sem pedido de
# futuro, ou num ano do mandato ("o Bolsonaro e a Petrobras em 2022"). O que pode vir ("num governo do Bolsonaro", "no
# próximo governo Bolsonaro", "o governo do Bolsonaro vai voltar?", "no governo do Bolsonaro a Petrobras sobe?") é a eleição.
GOVERNO_BOLSONARO_NOME = (r'(?<!\bnum )(?<!\bnuma )(?<!\bum )(?<!\buma )(?<!\bnovo )(?<!\bnova )(?<!\bproximo )'
                          r'(?<!\bproxima )(?<!\bfuturo )(?<!\bfutura )(?<!\boutro )(?<!\boutra )(?<!\beventual )'
                          r'(?<!\bpossivel )(?<!\bsegundo )'
                          r'\b(governo|gestao|mandato|epoca|tempo|periodo|era) (d[oe] )?(ex[- ]?presidente )?(jair )?bolsonaro\b'
                          r'(?! (vai |vao )?volt(ar|a|e|ara|aria)\b)'
                          r'|\b(2019|2020|2021|2022)\b')
# o "eleito" do cargo que vem depois ("o presidente da petr4 foi eleito quando?") sai antes do cargo
CARGO_ELEITO = r'\b(presidente|ceo)\b( d[aoe]| na| no)? (petrobras|petr[34]|prio3?)\b[^.?!]{0,20}\b(foi )?eleit[oa]\b'
# O cargo também pelo ticker e pela companhia ("o presidente da PETR4", "presidente da Prio"), com o "eleito" e o
# "ex-presidente" da empresa. O presidente da República que vem depois da Petrobras ("a Petrobras e o novo presidente da
# República") é a eleição.
CARGO = (r'(\beleit[oa] )?\b(presidente|presidencia|ceo|comando)\b( d[aoe]| na| no)? (petrobras|petr[34]|prio3?|estatal|companhia'
         r'|conselho|empresa|opep|banco central|bc)\b'
         r'|\b(petrobras|petr[34]|prio3?|estatal)\b[^.?!]{0,50}\b(presidente|presidencia)\b(?! d[ao] (republica|brasil|pais)\b)'
         r'|\beleit[oa] pelo conselho\b'
         # a outra companhia, sempre com "da/do/na/no" ("o presidente da Vale", "o CEO do Itaú"): "o presidente vale a pena?" não
         r'|\b(presidente|presidencia|ceo|comando)\b( d[aoe]| na| no) (vale3?|itau\w*|itub[34]|bradesco|bbdc[34]|santander'
         r'|banco do brasil|caixa|eletrobras|ambev|embraer|shell|exxon\w*|chevron|equinor|[a-z]{4}(3|4|5|6|11))\b')

# O Irã digitado sem acento ("o ira"): o verbo "irá" só é o pronome antes do infinitivo ("quem o irá substituir",
# "ninguém o irá demitir"). "o ira nuclear", "com o ira atacar Israel" e "se o ira atacar" são o país.
IRA_SEM_ACENTO = (r'\b(do|no|ao|pro|pelo|com o|contra o) ira\b'
                  r'|(?<!\bquem )(?<!\bque )(?<!\bninguem )(?<!\balguem )(?<!\bnao )(?<!\bele )(?<!\bela )(?<!\bvoce )\bo ira\b'
                  r'|\bo ira\b(?! \w{3,}(ar|er|ir)\b)')

TEMAS = {
    'eleicao': r'\belei(cao|coes|toral|torais)\b|\bturnos?\b|\bcandidat\w*|\burnas?\b|\bpresidente\b|\bganhar a elei'
               r'|\bvencer a elei|\bse (ele|ela) (ganhar|vencer|perder)\b|\bpesquisas?\b|\bdatafolha\b|\bquaest\b|\batlas\w*'
               r'|\binstitutos?\b|\bdireita\b|\besquerda\b|\bvitoria d\w\b|\breeleit\w*|\bdomingo\b|\brunoff\b|\belection\b'
               r'|\bmito\b|\bpt\b|\bpl\b|\bganhando\b|\bvencendo\b|\beleito\b'
               # o Jair Bolsonaro de um ano de eleição ("Jair Bolsonaro e o dólar em 2018") é o candidato daquela eleição
               r'|\bjair bolsonaro\b[^.?!]{0,40}\b(2018|2022)\b|\b(2018|2022)\b[^.?!]{0,40}\bjair bolsonaro\b',
    'copom': r'\bcopom\b|\bselic\b|\bdecisao de juros\b|\bbanco central (corta|sobe|mantem|decide)\b|\bcortar(em)? (os )?juros\b',
    'fiscal': r'\bfiscal\b|\barcabouco\b|\bgastos? publicos?\b|\borcamento\b|\bministro da fazenda\b|\bhaddad\b',
    'legislativo': r'\bcongresso\b|\bcamara\b|\bsenado\b|\bvotacao\b|\bpec\b|\breforma\b|\bimpeachment\b',
    'judicial': r'\bstf\b|\bsupremo\b|\bjulgamento\b|\bprisao\b|\bcondenacao\b',
    # "petróleo" sozinho não é geopolítica: tem mercado próprio, com os eventos de guerra que mexeram com o Brent. O
    # "tarifaço" e a "taxação do Trump" são a tarifa; a "guerra de preço(s)" do petróleo não é guerra; "quem o irá
    # substituir" é o verbo, não o Irã.
    'geopolitico': r'\btarifa(s|co|cos|sso)?\b|\bsobretaxa\w*|\btaxac\w* (d[aoe]s?) (trump|eua|estados unidos)\b|\btaxac\w* (do )?trump\b'
                   r'|\btaxac\w* americana\b(?![^.?!]{0,40}\b(dividend|stock|aco|renda)\w*)'
                   r'|\bguerra\b(?! (de |do |dos )?precos?\b)|\bsancao\b|\bsancoes\b|\biran\b'
                   r'|' + IRA_SEM_ACENTO,
    'choque_externo': r'\bpandemia\b|\bcovid\b|\bcrise (global|externa|internacional)\b',
    'escandalo': r'\bescandalos?\b|\bdelacao\b|\blava ?jato\b|\bgrampo\b',
    'economia': r'\beconomia\b|\binflacao\b|\bipca\b|\bdivida\b|\bpib\b|\bfiscal\b',
    'conceito': r'\bo que (e|sao|significa)\b|\bcomo funciona\b|\bme explica\b|\bexplica\b',
}

# Empresas e tickers da B3 ("PETR4", "PRIO3", "VALE3", "ITUB4", "BOVA11"), e as petroleiras de fora, para a escolha
# entre eles. "petrobas" é o erro de digitação comum; "bp" fica de fora (sigla curta demais).
EMPRESA = (r'(petrobras|petrobas|petr[34]|prio3?|vale3?|exxon\w*|shell|chevron|equinor|3r|brava|petroreconcavo|enauta'
           r'|aramco|totalenergies|[a-z]{4}(3|4|5|6|11))')
# "quanto vale o ouro ou o dólar?": o verbo, não a Vale.
EMPRESA_SEM_VALE = r'(?!vale\b)' + EMPRESA
# Os papéis da Petrobras, sem pegar "petróleo" (o "petr\w*" pegava "aumentar a produção de petróleo").
PETR = r'(petr[34]|petrobras)'
# O que a pessoa pode manter, deixar ou aproveitar ("continuo com PETR4?", "oportunidade na Petrobras?").
ATIVO = r'(' + EMPRESA + r'|acoes|bolsa|ibovespa|dolar|bitcoin|cripto|petroleo|brent|ouro)'
# "PETR3 ou PETR4: qual a diferença?" e "o que muda entre PETR3 e PETR4?" são conceito (P5), não escolha.
# Com a escolha junto ("qual a diferença e qual eu pego?", "o que muda? qual é melhor?"), volta a ser escolha (M2). A
# relação ("qual a correlação entre Petrobras e Prio?") também é conceito.
ESCOLHA_DITA = (r'\bqual (eu )?(pego|fico|levo|escolh\w*|prefir\w*|compr(o|ar|aria))\b'
                r'|\bqual (vc|voce|tu) (escolh\w*|prefer\w*|peg\w*|fica\w*|compr\w*)\b'
                r'|\bqual (e |seria )?(a |o )?melhor\b(?! (jeito|forma|maneira|fonte|site|livro|lugar|ano|trimestre)\b'
                r'| (pra|para) (entender|saber|aprender|estudar|acompanhar|conhecer|ler|interpretar|compreender|comparar)\b)')
SEM_DIFERENCA = rf'^(?:(?=.*(?:{ESCOLHA_DITA}))|(?!.*\b(diferenc\w*|difere\w*|o que muda|relac\w*|correlac\w*)\b)).*?'
# O "ou" entre dois verbos ("o dólar subiu ou caiu quando...", "a Petrobras exporta ou importa petróleo?") não liga ativos.
OU_ATIVO = (r'(?<!\bsubiu )(?<!\bsubiram )(?<!\bsubia )(?<!\bsobe )(?<!\bsobem )(?<!\bcaiu )(?<!\bcairam )(?<!\bcaia )'
            r'(?<!\bcai )(?<!\bcaem )(?<!\bdesceu )(?<!\bdesce )(?<!\bvalorizou )(?<!\bdesvalorizou )(?<!\bganhou )'
            r'(?<!\bperdeu )(?<!\baumentou )(?<!\bdiminuiu )(?<!\bexporta )(?<!\bimporta )(?<!\bexportou )(?<!\bimportou )'
            r'(?<!\bbem )(?<!\bcima )')
ESCOLHA = r'(escolh\w*|prefer\w*|prefir\w*|melhor(es)?|pior(es)?)'

# Os tokens que MERCADOS['cripto'] conhece, mais o ticker SOL: a escolha entre eles é ranking (M2, N7).
CRIPTO_NOME = (r'(btc|bitcoins?|eth|ethereum|ethers?|xrp|solana|sol|usdt|usdc|tether|doge\w*|shiba|hash11|cardano|ada|pepe|bnb'
               r'|litecoin|ltc)')
SEM_CONCEITO_CRIPTO = (rf'^(?:(?=.*(?:{ESCOLHA_DITA}))|(?!.*\b(quanto (vale|valem|custa|custam|ta|esta)|cotac\w*|preco'
                       r'|diferenc\w*|o que (e|sao)|surgiu|surgiram|criad[oa]s?|lastread\w*|lastro|halving|primeiro)\b)).*?')
# Antes do infinitivo, a definição ("o que é zerar a posição?", "o que significa ter posição comprada?") é conceito (P5).
CONCEITO_ANTES = r'(?<!\bque e )(?<!\bsao )(?<!\bsignifica )(?<!\bdizer )(?<!\bfunciona )(?<!\bque e ")'
# "o aumento das ações", "houve aumento": o substantivo, com artigo ou verbo antes.
SEM_ARTIGO = (r'(?<!\bo )(?<!\bum )(?<!\bhouve )(?<!\bteve )(?<!\bdo )(?<!\bno )(?<!\bao )(?<!\bpelo )(?<!\besse )'
              r'(?<!\beste )')

# Classes de ativo, para o "X ou Y" do caso da pessoa (N5). "Banco central" e "um banco" não são o setor.
# A cripto entra no plural e pelo nome ("bitcoins ou tesouro?", "eth ou renda fixa?"), como a bolsa e o Ibovespa.
CLASSE = (r'(dolar|bolsa|ibovespa|cripto\w*|bitcoins?|btc|eth|ethereum|ethers?|solana|xrp|doge\w*|shiba|usdt|usdc|tether'
          r'|stablecoins?|renda fixa|tesouro|acoes|ouro|poupanca|cdb|lci|lca|fiis?'
          r'|petroleo|brent|petrobras|petr[34]|petroleiras?|bancos|de banco|bancari[ao]s?|acao|imove(l|is))(?! centra)')

# Pôr algo na declaração ou num documento do IR ("boto o bitcoin na declaração?", "coloco em bens e direitos?", "onde
# coloco o informe?", "onde ponho o código do DARF?") é regra de imposto (P5), não pôr o dinheiro num mercado.
LUGAR_DO_IR = r'(em|na|no|nas|nos)( (qual|que|a|o))? (declaracao|ir|irpf|imposto de renda|ficha|bens e direitos|codigo)\b'
DOC_DO_IR = r' (o |a |os |as |meu |minha |meus |minhas )?(informe|cpf|recibo|darf)\b'
DECLARACAO = (r'declarac\w*|declarar|irpf|darf|informes?|codigos?|fichas?|carne[- ]leao|bens e direitos'
              r'|rendimentos? (isentos?|tributaveis|sujeitos)')

# A relação e o passado entre duas classes ("a gasolina segue o Brent ou o dólar?", "o Copom afeta o dólar ou o petróleo?",
# "o que subiu mais em 2022, petróleo ou dólar?"), o preço ("quanto vale o bitcoin ou o ether hoje?") e a regra ("o
# tesouro ou a petrobras são tributados igual?") não comparam para o caso da pessoa (N5). Com o caso dela ("pra me
# proteger", "pra mim", "agora", "qual pego") volta a ser comparar.
_VERBO_REL = (r'(segu(e|em|iu|iram)|acompanh(a|am|ou|aram)|depend(e|em|eu|eram)|mex(e|em|eu|eram)|afet(a|am|ou|aram)'
              r'|influenci(a|am|ou|aram)|pes(a|am|ou|aram)|reag(e|em)|reagi(u|ram)|pux(a|am|ou|aram)|impact(a|am|ou|aram))')
_MOV_PASSADO = (r'(subiu|subiram|caiu|cairam|rendeu|renderam|valorizou|valorizaram|desvalorizou|desvalorizaram|variou'
                r'|variaram|perdeu|perderam|ganhou|ganharam|disparou|despencou)')
_ALT = rf'({CLASSE}|{EMPRESA_SEM_VALE})'
_ALT_OU = rf'\b{_ALT}\b[^,.;:?!]{{0,25}}\b(ou|x|vs|versus)\b[^,.;:?!]{{0,25}}\b{_ALT}\b'
RELACAO_OU = (rf'\b{_VERBO_REL}\b[^,.;:?!]{{0,25}}{_ALT_OU}'
              rf'|\b(qual|quem|o que)\b[^.;:?!]{{0,15}}\b({_VERBO_REL}|{_MOV_PASSADO})\b[^.;?!]{{0,40}}{_ALT_OU}'
              rf'|{_ALT_OU}[^.;?!]{{0,5}}\b(qual|quem)\b[^.;:?!]{{0,15}}\b({_VERBO_REL}|{_MOV_PASSADO})\b')
PRECO_OU_REGRA_DITA = (r'\b(quanto (vale|valem|custa|custam|ta|esta)|cotac\w*|tributad\w*|tributac\w*|impostos?|isen\w*'
                       r'|declar\w*|aliquotas?)\b')
PARA_O_CASO = (r'\b(proteg\w*|protecao|hedge|pra mim|para mim|pra eu|para eu|meus?|minhas?|agora|(pra|para|em) 20(2[7-9]|[3-9]\d)'
               r'|escolh\w*|prefer\w*|prefir\w*|pego|fico|carteira|investir|aplicar|apostar|melhor|pior)\b')
SEM_RELACAO = rf'^(?!(?!.*{PARA_O_CASO})(?=.*(?:{RELACAO_OU}|{PRECO_OU_REGRA_DITA})))'

PROIBIDOS = {
    # "O que eu faço?", "que que eu faço?", "o que fazer agora?", "preciso tomar uma decisão", "e agora?" pedem ação.
    # "O que fazer para entender o Copom?" não: é pedido de explicação.
    # "EUA proíbem a compra de petróleo russo" é a manchete: o substantivo depois do verbo de proibir ou liberar
    'dica': r'(?<!\bproibem a )(?<!\bproibiu a )(?<!\bproibe a )(?<!\bsuspende a )(?<!\bsuspendeu a )(?<!\bveta a )'
            r'(?<!\bvetou a )(?<!\blibera a )(?<!\bliberou a )(?<!\bautoriza a )(?<!\bautorizou a )\bcompr(a|o|ar|aria|ariam)\b'
            r'|\bvend(e|o|er|eria)\b|\bentro\b|\bentrar\b|\bsair\b|\bcompens\w*|\bbora\b'
            r'|\bdevo\b|\bdeveria\b|\bvale (a ?pena|mais|comprar)\b|\bfaz sentido\b|\beu (compre|venda)\b'
            r'|\b(o que|que que|oq)( e que)?( eu)? (faco|fazer|faria)\b'
            r'(?! (pra|para) (entender|saber|aprender|estudar|acompanhar|conhecer|ler|interpretar|compreender)\b)'
            r'|\b(preciso|tenho que|tenho de|tenho|vou ter que) (de )?(tomar )?(uma )?(decisao|decidir)\b'
            r'|\bme ajud(a|e|ar) a (tomar (uma )?decisao|decidir|escolher)\b|\bdecid(e|a|ir) (por|pra|para) mim\b'
            r'|\be agora(\?|\W*$)'
            # "conselho" de órgão ("o conselho da Petrobras elegeu o Prates?", "Conselho Monetário") é fato, não dica
            r'|\bse fosse (voce|eu)\b|\bo que (voce )?faria\b|\brecomenda\w*|\bsugest\w*|\bdica\w*'
            # e o conselho que já decidiu ("o conselho aprovou dividendos?", "foi eleita pelo conselho"); "obrigado pelo conselho"
            # continua dica
            r'|(?:(?<!\bpelo )|(?<=\bobrigad[oa] pelo )|(?<=\bvaleu pelo ))\bconselho\w*\b(?! (de (administracao|adm)|monetario|fiscal'
            r'|curador)\b| d[ao] (petrobras|petr[34]|empresa|estatal|bc|banco central|cvm|vale|prio3?|opep)\b| (ja )?(aprov(ou|aram|a|am)'
            r'|eleg(eu|eram|e|em)|decid(iu|iram|e|em)|indic(ou|aram)|nome(ou|aram)|destitu(iu|iram)|demit(iu|iram))\b)'
            r'|\bfico (comprado|vendido|de fora)\b|\bcomo (eu )?(abordo|opero|ganho)\b|\bestrategia\b|\bposicion\w*'
            r'|\bexposicao\b|\baplicar\b|\binvestir\b|\bbuy\b|\bsell\b|\bshould i\b|\bwould you\b'
            # pôr o dinheiro num mercado, na 1ª pessoa ("invisto em petróleo?", "reinvisto?", "coloco na bolsa?"), menos
            # "como eu coloco dinheiro na corretora?" (P5)
            r'|(?<!como )(?<!como eu )\b(re)?(invisto|aplico)\b'
            rf'|(?<!como )(?<!como eu )\b(coloco|ponho|boto)\b(?!{DOC_DO_IR})[^.?!]{{0,30}}\b(?!(?<=tenho )em casa\b)(?!{LUGAR_DO_IR})'
            r'(em|na|no|nas|nos)\b'
            # mover o dinheiro, na 1ª pessoa ("trago o dinheiro?", "troco?"), menos "como mando dinheiro pra fora?" (P5)
            r'|(?<!como )(?<!como eu )\b(troco|trago|mando|envio|converto|transfiro|remeto)\b|\bdeixo (la|aqui|parado|onde esta)\b'
            # "como tiro meu bitcoin da exchange?" e "como tiro o informe da corretora?" pedem explicação (P5)
            rf'|(?<!como )(?<!como eu )(?<!onde )(?<!onde eu )\b(tiro|boto|deixo|guardo)\b[^.?!]{{0,40}}\b(exchange|corretora|carteira'
            rf'|{EXCH})\b'
            # onde pôr o dinheiro ("recebi dividendos, onde ponho?"), mesmo sem valor
            rf'|\bonde (eu )?(ponho|coloco|boto)\b(?!{DOC_DO_IR})(?![^.?!]{{0,40}}\b({DECLARACAO}|n[oa] (ir|imposto de renda))\b)'
            r'|\bonde (eu )?(invisto|aplico|reinvisto|reinvesto)\b|\breinvesto\b'
            # "que tal petrobras?" é pedir o juízo sobre o emissor (Mapa legal, seção 8, item 10)
            rf'|\bque tal\b (a |o |as |os )?(acoes (da |do )?)?{EMPRESA}\b'
            r'|(?<=.{10})\be ai(\?|\W*$)|\bconviene\b|\b(debo|deberia) (cambiar|traer|mandar|enviar)\b'
            # o que fazer com a posição, preso à 1ª pessoa ou à posse ("mantenho PETR4?", "zero minha petrobras?")
            rf'|\bmantenho\b|\bsegur(o|ar)\b (a |o )?(minha|meu|minhas|meus|posicao|{PETR}|acao|acoes|papel|papeis)\b'
            r'|\b(vale|devo|compensa|deveria) (segurar|manter)\b|\bvale (a ?pena )?manter\b'
            # ficar, continuar ou sair do papel, e dobrar a mão ("continuo com PETR4?", "saio da petrobras?", "boto mais?")
            # "se eu saio do Brasil, como fica o imposto?" é a regra de quem sai do país; "saio do Brasil?" sozinho é pedido
            rf'|\b(continuo|fico|sigo) (com|n[ao]|em) (a |o |as |os )?{ATIVO}\b'
            r'|\bsaio\b(?! (d[oe]|da) (brasil|pais|emprego|trabalho|casa)\b(?!\W*$|,? (e|ou|agora|ja|hoje|logo)\b))'
            # e as gírias do mesmo pedido ("shortar", "aporto", "hold petr4?", "vale continuar com petr4?", "pulo fora"), menos
            # a definição ("o que significa shortear?", "o que é dobrar a mão?", "como aportar na bolsa?")
            rf'|\b(to|tou|estou|fiquei) (comprado|vendido|posicionado)\b|{CONCEITO_ANTES}\bdobr(o|ar|aria) (a )?(mao|posicao)\b'
            rf'|\b(boto|ponho|coloco) mais\b|{CONCEITO_ANTES}\b(shorte\w*|short(o|ar|aria|ando|ei))\b|\bcaio fora\b'
            r'|(?<!como )(?<!como eu )\baport(o|amos)\b|\bfaco (um |o )?aporte\b'
            rf'|{CONCEITO_ANTES}{SEM_ARTIGO}(?<!como )\baport(ar|aria|e)\b( mais)? (em|na|no|nas|nos) (a |o |as |os )?{ATIVO}\b'
            rf'|^\W*(mantem|mantenha|segura|segure|hold|holda|carrego)\b[^.?!]{{0,15}}\b{ATIVO}\b'
            rf'|{CONCEITO_ANTES}\bhold(o|ar|ando)\b|\bcarrego\b[^.?!]{{0,15}}\b{ATIVO}\b'
            r'|\bvale (continuar|carregar)\b|\bvale ficar (com|n[ao]s?|em|de fora|comprado|vendido)\b'
            rf'|\bvale ter\b[^.?!]{{0,20}}\b{ATIVO}\b'
            rf'|\bcontinua valendo (a pena|ter|manter|ficar|segurar|carregar)\b|\bpulo fora\b|\bpular fora d[aeo]s? {ATIVO}\b'
            # a indicação de compra ou a "sua" ("qual a indicação pra PETR4?"), não a do governo ("qual a indicação do MME?")
            r'|\bqual (e )?(a )?(sua |tua )?indicac(ao|oes)\b(?! d[oa] (governo|mme|ministerio|conselho|presidente|lula|bolsonaro'
            r'|uniao|controlador)\b)|\bindicac(ao|oes) de (compra|venda)\b'
            # o infinitivo só vale fora da definição ("o que é zerar a posição?" é conceito, P5)
            rf'|\bzer(o|ei)\b (a |o |as |os )?(minha|meu|minhas|meus|posicao|tudo|{PETR}|acoes)\b'
            rf'|{CONCEITO_ANTES}\bzerar\b (a |o |as |os )?(minha|meu|minhas|meus|posicao|tudo|{PETR}|acoes)\b'
            # "aumento" só como verbo: "o aumento das ações" e "houve aumento nas ações" são fato. Sem "petróleo": "a OPEP
            # decidiu reduzir a produção de petróleo" é fato.
            rf'|(?:{SEM_ARTIGO}\baumento\b(?! (d[aeo]s?|n[ao]s?)\b)|\b(reduzo|diminuo|realizo)\b'
            rf'|{CONCEITO_ANTES}\b(aumentar|reduzir|diminuir|realizar)\b)[^.?!]{{0,20}}\b(posicao|lucro|{PETR}|acoes|minha|meu)\b'
            # "foi aumento?" e "foi redução ou aumento?" perguntam o que já saiu; "redução ou aumento?" sem marca de passado, ou
            # com futuro ("o próximo vai ser redução ou aumento?"), continua pedido
            rf'|{SEM_ARTIGO}(?<!\bfoi )(?<!\bera )(?<!\breducao ou )(?<!\bcorte ou )\b(aumento|reduzo|diminuo|realizo)\W*$'
            r'|^(?:(?=[\s\S]*\b(?:vai|vao|sera|serao|proxim\w*|amanha)\b)|(?![\s\S]*\b(?:foi|foram|era|teve|tiveram|houve|ultim[oa]|ontem'
            r'|anunciou|saiu|veio)\b))[\s\S]*\b(?:reducao|corte) ou aumento\W*$'
            # a posição da pessoa, não a "posição na pesquisa" nem a "posição em aberto" (conceito)
            r'|\b(minha|meu) posicao\b'
            rf'|{CONCEITO_ANTES}\b(tenho|ter|to com|tou com|estou com|fiquei com|eu com|abro|monto)( uma| a)?( pequena| grande| boa)?'
            r' posicao\b|\bvale (ter|considerar|abrir|montar|fazer)\b[^.?!]{0,20}\bposicao\b|^\W*posicao (em|na|no)\b'
            # o tamanho e a melhor posição ("qual tamanho de posição no WIN?", "qual a melhor posição no WIN?"), menos a
            # definição, a posição de terceiros e a da pesquisa ("quem está em melhor posição na pesquisa?")
            rf'|{CONCEITO_ANTES}(?<!\bque e o )(?<!\bsignifica o )\btamanho( ideal| certo| bom| maximo)? (de|da|do) posicao\b'
            r'(?! d[aeo]s? (estrangeir|investidor|fundo|banco|gringo|institucion|pessoa|varejo))'
            r'|\b(qual|que)( e)?( a)? ((melhor|pior) posicao|posicao (ideal|certa|correta))\b'
            r'(?![^.?!]*\b(pesquis\w*|ranking|corrida|disputa|turno|eleic\w*|candidat\w*|tabela|classifica\w*)\b)(?! d[aeo]s? )'
            r'|\bquanto (colocar|botar|alocar|aplicar|ter)\b[^.?!]{0,20}\bposicao\b'
            # o verbo da 1ª pessoa com o "quando" ("realizo agora?", "zero hoje?"), menos o substantivo ("teve aumento hoje?")
            rf'|{SEM_ARTIGO}(?<!\bem )(?<!\ba )(?<!\bde )(?<!\bda )\b(aumento|reduzo|diminuo|realizo|zero) (agora|hoje|ja|amanha)'
            r'(\W*$| ou\b)'
            r'|\bdou uma (reduzida|aumentada|zerada|realizada|diminuida|enxugada|segurada)\b'
            r'|\b(faco|fazer|faria|vale fazer) (o |um )?(preco medio|pm)\b'
            r'|\baproveit(o|ar|aria) (a|o|essa|esse|esta|este)? ?(queda|alta|baixa|subida|desconto|tombo|crise|guerra)\b'
            # "o que é oportunidade de arbitragem?" é conceito; com adjetivo ("é uma boa oportunidade?") é sempre pedido
            # "crise e oportunidade: o que a história mostra?" soma as duas palavras, não pede ("e" de somar, e o que vem é
            # pergunta de fato)
            r'|(?<!\bo que )(?<!\boq )\b(e|seria) (uma )?oportunidade\b(?![:;,] (o que|qual|como|quando|por que)\b)'
            r'|\b(e|seria) (uma )?(boa|otima|grande) oportunidade\b(?![:;,] (o que|qual|como|quando|por que)\b)'
            r'|[,;:] ?(uma )?(boa |otima |grande )?oportunidade\W*$'
            r'|\boportunidade (de|pra|para) (compra|entrada|comprar|entrar|vender|lucro|ganh\w*)\b'
            # a oportunidade que já passou ("a pandemia de 2020 foi uma oportunidade na bolsa?") é passado (P1)
            r'|(?<!\bfoi uma )(?<!\bfoi )(?<!\bcriou )(?<!\bcriou uma )(?<!\bteve )(?<!\bhouve )(?<!\bgerou )(?<!\bgerou uma )'
            rf'\boportunidade (n[ao]|em) (a |o |as |os )?{ATIVO}\b'
            r'|\b(bom|otimo|melhor|pior) momento\b|(?<!\bfoi o )\bmomento (certo|ideal)\b|\b(boa|otima) hora\b'
            r'|\b(ta|esta|e|chegou) (na )?(hora|momento) de\b'
            r'(?! (entender|aprender|estudar|compreender|ler|interpretar)\b)'
            # "o que é long ou short?", "o que significa ficar short?" e "o que é um investimento seguro?" são conceito (P5)
            r'|(?<!\bo que e )(?<!\bo que sao )\b(long ou short|short ou long)\b'
            r'|(?<!\bsignifica )(?<!\bo que e )\b(fico|ficar|entro|vou) (long|short)\b'
            r'|(?<!\bo que e )(?<!\bo que e um )(?<!\bo que seria um )\binvestimento (seguro|bom|ruim|arriscado)\b'
            # o juízo sobre o papel, sem mais nada ("petr4 é bom?", "PETR4 tá ótima?")
            rf'|\b{EMPRESA} (e|ta|esta) (um |uma )?(bom|boa|otim[oa])( (papel|acao|investimento|compra|empresa))?\W*$'
            # ter o papel ("é bom ter petr4?", "é bom ter ações da Petrobras?"): é o que fazer com ele (N1)
            rf'|\b(bom|boa|otimo|ruim|interessante) ter (a |o |as |os )?((acoes|acao|papeis|papel) d[aeo] )?{EMPRESA_SEM_VALE}\b'
            # "embarco?" é ordem, como "entro"; "embarcar" sozinho não ("o Brasil vai embarcar petróleo")
            # "posso ir no bitcoin?", "vou ir na cripto agora?": é pôr o dinheiro nele (N1)
            rf'|\b(posso|quero|vou|devo|bom|vale)( eu)? ir (no|na|pro|pra|pros|pras|para o|para a) ({ATIVO}|{CRIPTO_NOME})\b'
            r'|\bembarc(o|amos)\b|\b(vale|da (pra|para)) embarcar\b|\bembarcar (nessa|nesse|agora|ja)\b|\bbtfd\b'
            # promessa de ganho ("dividendo é renda garantida?", M6), menos quem garante ("o CDB é garantido pelo FGC?", "o
            # bitcoin é garantido por alguma coisa?", "o dividendo mínimo é garantido na lei?") e o Tesouro ("o Tesouro Selic é
            # garantido?"), que é regra (P5)
            r'|(?<!\bpoupanca e )(?<!\bcdb e )(?<!\blci e )(?<!\blca e )(?<!\bdeposito e )'
            r'(?<!\btesouro e )(?<!\btesouro selic e )(?<!\btesouro direto e )(?<!\btesouro ipca e )(?<!\btesouro ipca\+ e )'
            r'(?<!\btesouro prefixado e )'
            r'\bgarantid[oa]s?\b(?! (pel[oa]|por) (fgc|governo|tesouro|lei|uniao|b3|banco central|bc|alguma coisa|algo|quem)\b'
            r'| pelo que\b| (na|em) lei\b)',
    'direcao': r'\bvai (subir|cair|disparar|despencar|bombar|valorizar|explodir|fechar|abrir)\b|\bvao (subir|cair)\b|\bchances?\b'
               r'|\bprobabilidad\w*|\bde 0 a 100\b|\bum numero\b|\btendencia\b|\bpode (subir|cair|disparar)\b'
               r'|\bsobe ou (cai|desce|nao)\b|\balavanc(ar|a)\b|\bpotencial\b|\bprevisao\b|\bprever\b|\bdisparar\b',
    'momento': r'\bstop\b|\balvo\b|\bponto de (entrada|saida)\b|\bquando (entrar|sair|comprar|vender)\b'
               r'|\b(hora|quando)\b.{0,15}\b(entrar|sair|comprar|vender|operar)\b|\balertas?\b|\bme avis(a|e)\b|\bsinal de\b'
               r'|\bamanha\b|\bna abertura\b|\bsegunda(-feira)?\b.{0,30}\b(fazer|compr\w*|vend\w*|entr\w*)'
               # "Brent caiu 10% hoje, é a hora?", "perdi o bonde?", "ainda dá tempo?"; não "qual é a hora da decisão do Copom?"
               # nem "é a hora de entender a Selic?"
               # "tá na hora da prio?", "está na hora do bitcoin?" e "tá na hora?" são o mesmo pedido
               r'|(?<!qual )(\b(e|seria|sera|chegou)( agora| ja)? a|\b(ta|esta)( agora| ja)? na) hora\b'
               r'(?! (de|pra|para) (entender|saber|aprender|estudar'
               r'|acompanhar|conhecer|ler|interpretar|compreender)\b| da verdade\b'
               r'| d[aeo] (decisao|divulgacao|reuniao|copom|ata|abertura|fechamento|votacao|eleicao|apuracao|anuncio|leilao)\b)'
               r'|\bperdi (o|a) (bonde|trem|timing|momento|onda)\b'
               # "petróleo caiu, é o momento?", "é hora?", "qual seria a hora certa?", "é o momento do bitcoin?"; não "o Copom
               # disse que é o momento de cautela?" nem "qual é a hora certa da decisão do Copom?"
               r'|\bqual (seria |e |sera )?a hora (certa|ideal)\W*$'
               r'|(?<!qual )(?<!o que )(?<!oq )(?<!como )\b(e|seria|sera|chegou)( agora| ja)? (o momento|hora)'
               rf'(?=\W*$|\s*[?!.,;]| (d[aeo]s?|n[ao]s?|em|pra|para|pro) (a |o |as |os )?({ATIVO}|{CLASSE})\b)'
               # o prazo do imposto e do cartório eleitoral é calendário, não entrada (P5): "ainda dá tempo de declarar o
               # bitcoin no IR?", "... de pagar o DARF?", "... de mudar o domicílio eleitoral?"; "de transferir o dinheiro" não
               r'|\bainda da tempo\b(?! (de|pra|para) (entender|saber|aprender|estudar|ler|ver|assistir|acompanhar|votar'
               r'|declarar|retificar|justificar|(se )?alistar)\b'
               r'| (de|pra|para) (entregar|corrigir|fazer|pagar|pedir|acertar|regularizar|emitir|gerar|recolher|tirar|transferir'
               r'|mudar) (a |o |as |os |minha |meu |minhas |meus )?(declarac\w*|imposto|ir|irpf|darf|guia|restituic\w*|carne-leao'
               r'|titulo( de eleitor)?(?! d[eo] tesouro)|domicilio|local de votacao|zona eleitoral)\b)',
    'capital': r'\br\$ ?\d|\b\d+ ?mil reais\b|\b\d+ ?k\b|\b(um|dois|tres|quatro|cinco|seis|sete|oito|nove|dez|vinte|trinta|'
               r'cinquenta|cem) mil( reais)?\b|\btenho (r\$ ?)?\d+[\d.,]* ?(mil|k|reais|conto|contos|pila|paus)\b'
               r'|\bquantos contratos\b|\bquanto (eu )?(coloco|ponho|invisto|aplico|boto|devia ter|deveria ter)\b'
               r'|\bquanto investir\b|\bmeu (capital|dinheiro|patrimonio|salario)\b|\bminha (renda|carteira|reserva)\b'
               r'|\bganho \d+|\bpor mes\b|\bsalario\b'
               r'|\bcom \d+[\d.,]* ?(conto|contos|pila|paus)\b'
               r'|\bcom \d+[\d.,]* ?reais\b(?=[^.?!]{0,30}\b(da (pra|para)|consigo|comec\w*|invest\w*|aplic\w*|compr\w*|entr(o|ar)'
               r'|oper(o|ar))\b)',
    'perfil': r'\barrojad\w*|\bconservador\w*|\bmoderad[oa]\b|\btolerancia (a|ao) risco\b|\bperfil\b|\baposentadoria\b'
              r'|\breserva de emergencia\b|\bserve (pra|para) mim\b|\be (pra|para) mim\b|\bminha idade\b|\btenho \d+ anos\b'
              r'|\bmeu objetivo\b|\bmeu prazo\b'
              # a idade e a adequação de um terceiro ("minha mãe tem 70 anos, serve pra ela?") e o objetivo de renda.
              # "bom pra ela" sozinho fica de fora: costuma ser a empresa ("o Brent alto é bom pra ela, a Petrobras?")
              r'|\b(minha|meu|ela|ele)\b[^.?!]{0,25}\btem \d+ anos\b'
              r'|\b(serve|servem|indicad[oa]s?|adequad[oa]s?) (pra|para) (mim|ela|ele|eles|elas|minha|meu|minhas|meus)\b'
              r'|\b(bom|boa|bons|boas|ideal) (pra|para) (mim|minha|meu|minhas|meus)\b'
              r'|\b(meu|minha) (avo|vo|vovo|pai|mae|filh[oa]|tio|tia|esposa|marido|sogr[oa])\b[^.?!]{0,20}\b(de|com) \d+ anos\b'
              # a adequação a um grupo, menos o material de estudo ("que livro é indicado pra iniciante?")
              r'|^(?!.*\b(livros?|cursos?|canal|canais|sites?|apps?|aplicativos?|podcasts?|videos?|conteudos?|materia(l|is)'
              r'|leituras?|aulas?)\b).*\b(indicad|adequad|recomendad)[oa]s? (pra|para) (quem|iniciantes?|idos[oa]s?|aposentad[oa]s?'
              r'|jovens?)\b'
              r'|\bviver d(e|os|as) (dividendos?|proventos?|renda|juros)\b',
    'comparar': (r'\bmelhor\b.{0,40}\bou\b|\bou\b.{0,40}\b(qual )?(o |a )?melhor\b|\bvale mais\b'
                 rf'|{SEM_RELACAO}{SEM_CONCEITO_CRIPTO}{SEM_DIFERENCA}\b{CLASSE}\b.{{0,25}}{OU_ATIVO}\b(ou|x|vs|versus)\b.{{0,25}}'
                 rf'\b{CLASSE}\b'
                 # "o dólar foi melhor que a bolsa em 2022?" é passado
                 rf'|\b{CLASSE}\b.{{0,30}}(?<!\bfoi )(?<!\bforam )(?<!\bera )(?<!\beram )\b(melhor|pior)(es)? (do )?que\b'
                 # mais seguro ou mais arriscado entre duas classes ("renda fixa é mais segura que ações?"); o mini-índice
                 # (derivativo) e "os bancos estão mais sólidos que em 2015?" ficam de fora (L18 da rodada 2)
                 # o mini-dólar não é o dólar ("o mini-dólar é mais arriscado que o dólar à vista?" é conceito, D4)
                 rf'|(?<!\bmini )(?<!\bmini-)\b{CLASSE}\b.{{0,30}}(?<!\bficou )(?<!\bficaram )(?<!\bfoi )(?<!\bera )\b(mais|menos)'
                 rf' (segur|solid|arriscad)[ao]s?'
                 rf' (do )?que (o |a |os |as )?{CLASSE}\b'
                 # uma empresa contra uma classe ("PETR4 x dólar", "brava ou tesouro?", "petrobras ou ibovespa?")
                 rf'|{SEM_RELACAO}{SEM_DIFERENCA}\b{EMPRESA_SEM_VALE}\b.{{0,25}}{OU_ATIVO}\b(ou|x|vs|versus)\b.{{0,25}}\b{CLASSE}\b'
                 rf'|{SEM_RELACAO}{SEM_DIFERENCA}\b{CLASSE}\b.{{0,25}}{OU_ATIVO}\b(ou|x|vs|versus)\b.{{0,25}}\b{EMPRESA_SEM_VALE}\b'
                 # a escolha entre empresa e classe com "entre ... e" ("qual é melhor entre petrobras e dólar?", "entre
                 # petr4 e bitcoin, qual escolho?"); "qual a relação entre a Petrobras e o petróleo?" não escolhe
                 rf'|\b{ESCOLHA}\b.{{0,30}}\bentre (a |o )?({EMPRESA_SEM_VALE}\b.{{0,25}}\be (a |o )?{CLASSE}'
                 rf'|{CLASSE}\b.{{0,25}}\be (a |o )?{EMPRESA_SEM_VALE})\b'
                 rf'|\b({EMPRESA_SEM_VALE}\b.{{0,25}}\be (a |o )?{CLASSE}|{CLASSE}\b.{{0,25}}\be (a |o )?{EMPRESA_SEM_VALE})\b'
                 rf'.{{0,30}}(?:{ESCOLHA_DITA}|\bqual\W*$)'
                 # o rendimento que ainda vem ("petrobras rende mais que o cdb?"); "rendeu mais" é passado
                 rf'|\b{EMPRESA_SEM_VALE}\b.{{0,20}}\brende(m|ria)? mais (do )?que\b'),
    'ranking': r'\branking\b|\bmelhores (acoes|ativos|moedas|criptos)\b|\btop ?\d+\b|\bmonta (uma )?carteira\b'
               r'|\bcarteira (recomendada|sugerida|ideal)\b|\bquais (acoes|ativos)\b|\bqual (acao|ativo|papel|moeda|cripto)\b'
               r'|\bque acao\b|\bsobe mais\b|\bmais se benefici\w*|\bmelhor (acao|ativo|cripto|moeda)\b'
               # escolher entre empresas ou tickers ("PETR4 ou PRIO3?", "PRIO é melhor que a Petrobras?", "A Exxon é melhor que
               # a Petrobras?", "Which is better, Petrobras or Prio?") é ranking (M2)
               rf'|{SEM_DIFERENCA}\b{EMPRESA}\b.{{0,25}}{OU_ATIVO}\b(ou|or|x|vs|versus)\b.{{0,25}}\b{EMPRESA}\b'
               rf'|\b{EMPRESA}\b.{{0,30}}\b(e )?melhor (do )?que\b|\b(melhor (do )?que|better than) (a |o |the )?{EMPRESA}\b'
               r'(?! (pra|para) (entender|saber|aprender|estudar|acompanhar|conhecer|ler|interpretar|compreender)\b)'
               # "Petrobras e Prio: qual escolher?", "Entre Petrobras e PRIO, qual?"
               rf'|\b{EMPRESA}\b.{{0,25}}\b(e|and)\b.{{0,25}}\b{EMPRESA}\b.{{0,30}}(\bqual( (delas|deles|das duas|dos dois))?\W*$'
               # "qual a melhor?", "qual vc escolheria?", "qual você pegaria?", "qual rende mais?"; não "qual o melhor jeito de
               # comparar os balanços?" nem "qual melhor pra entender o setor?" (P5)
               r'|\bqual( (delas|deles|das duas|dos dois))? (e |seria )?(a |o )?melhor\b'
               r'(?! (jeito|forma|maneira|fonte|site|livro|lugar|ano|trimestre)\b'
               r'| (pra|para) (entender|saber|aprender|estudar|acompanhar|conhecer|ler|interpretar|compreender|comparar)\b)'
               r'|\bqual( (delas|deles))? (eu )?(escolh\w*|prefir\w*|pego|pegaria|fico|ficaria)\b'
               r'|\bqual( (delas|deles))? (vc|voce|tu) (escolh\w*|prefer\w*|peg(a|ar|aria)|fica|ficaria)\b'
               r'|\bqual( (delas|deles))? rende mais\b)'
               # "qual é melhor entre petrobras e prio?", com a escolha antes do "entre"
               rf'|{SEM_DIFERENCA}\b(qual|quais|{ESCOLHA[1:-1]})\b.{{0,30}}\bentre (a |o )?{EMPRESA}\b.{{0,25}}\be (a |o )?{EMPRESA}\b'
               # trocar um papel por outro ("vale trocar PETR4 por PRIO3?", "posso trocar PETR3 por PETR4?")
               rf'|\btroc\w*\b[^.?!]{{0,15}}\b{EMPRESA}\b[^.?!]{{0,10}}\bpor\b[^.?!]{{0,10}}\b{EMPRESA}\b'
               # o mesmo entre criptos ("BTC ou ETH?", "USDT ou USDC?", "ETH é melhor que BTC?"): indicar token (N7)
               # O preço e o conceito ("quanto vale o bitcoin ou o ether hoje?", "qual surgiu primeiro, btc ou eth?", "o usdt ou o
               # usdc é lastreado em dólar?", "o btc ou o eth tem halving?") não escolhem; o passado ("foi melhor") também não.
               rf'|{SEM_CONCEITO_CRIPTO}\b{CRIPTO_NOME}\b.{{0,25}}\b(ou|x|vs|versus)\b.{{0,25}}\b{CRIPTO_NOME}\b'
               rf'|\b{CRIPTO_NOME}\b.{{0,30}}(?<!\bfoi )(?<!\bforam )(?<!\bera )(?<!\beram )\b(e )?melhor (do )?que\b'
               rf'|\b{CRIPTO_NOME}\b.{{0,30}}\b(mais|menos) (segur|solid|arriscad)[ao]s? (do )?que (o |a )?{CRIPTO_NOME}\b'
               r'|\b(qual|que) (e )?(a )?(melhor |mais \w+ )?petroleiras?\b|\bmelhor(es)? petroleiras?\b'
               # "o que é boa pagadora de dividendos?" é conceito (P5)
               r'|\bpaga(m)? mais (dividendos?|proventos?)\b'
               r'|(?<!\bo que e )(?<!\bo que e uma )(?<!\bo que e ser )(?<!\bsignifica )(?<!\bsignifica ser )'
               r'\b(boa|otima|melhor|grande) pagadora\b'
               r'|\bpaga(m)? (bem|muito|bons|otimos|altos) (dividendos?|proventos?)\b'
               r'|\bpaga(m)? (dividendos?|proventos?) (altos?|bons?|gordos?)\b'
               r'|(?<!\bque e uma )(?<!\bque e a )(?<!\bsignifica )(?<!\bsignifica uma )\bvaca leiteira\b'
               # "o que é dividend yield alto?" é conceito (P5)
               r'|(?<!\bo que e )(?<!\bo que e um )(?<!\bo que e o )(?<!\bsignifica )(?<!\bsignifica um )'
               r'\b(dividend yield|dy)\b[^.?!]{0,30}\b(alto|alta|baixo|baixa|bom|boa|ruim|atrativ\w*|muito|pouco)\b'
               # "mais sólida" só na escolha ("qual petroleira é mais sólida?"); "por que o mini-índice é mais arriscado?" e
               # "o que torna o mini-dólar mais arriscado?" são conceito (D4)
               r'|(?<!\bpor )(?<!\bo )\b(qual|quais)\b[^.?!]{0,30}\b(mais|menos) (solid|segur|arriscad)[ao]s?\b'
               r'|\b(e|seria|ser|sao) (o|a|os|as)( \w+)? (mais|menos) (solid|segur|arriscad)[ao]s?\b'  # o superlativo: "é a mais segura?"
               # "a Petrobras ficou mais sólida depois de 2016?" é passado; sem a data ("PETR4 ficou mais arriscada?") continua
               rf'|\b({EMPRESA}|petroleiras?)\b[^.?!]{{0,30}}(?<!\bficou )(?<!\bficaram )(?<!\bfoi )(?<!\bera )(?<!\beram )'
               r'(?<!\bestava )\b(mais|menos) (solid|segur|arriscad)[ao]s?\b'
               rf'|\b({EMPRESA}|petroleiras?)\b[^.?!]{{0,30}}\b(ficou|ficaram|foi|era|eram|estava) (mais|menos) (solid|segur|arriscad)[ao]s?\b'
               r'(?![^.?!]{0,30}\b(depois d[aeo]s?|desde|em (19|20)\d\d|antes d[aeo]s?)\b)',
    'seletivo': r'\bso (os|as) (casos|vezes|anos|eleicoes|reunioes|dias|turnos)\b|\bso (as )?altas\b|\bso os positivos\b'
                r'|\bmostra so\b|\bmostra apenas\b|\bapenas (os|as) (casos|turnos|vezes)\b|\b(so|apenas) (a|as) (mediana|media|altas|quedas)\b',
    'plataforma': r'\bqual (a )?(melhor )?(exchange|corretora|plataforma|app)\b|\bonde (eu )?(compro|opero|abro conta)\b'
                  r'|\bque (exchange|corretora)\b|\bindic(a|ar|aria|am) (uma |um |a |o )?(exchange|corretora|plataforma|app)\b'
                  # avaliar uma corretora citada pelo nome ou apontada ("a Binance é segura?", "a Coinbase é regulamentada?
                  # posso confiar?", "é seguro deixar na Binance?") também é indicar (N7)
                  # Também "tem segurança?", "é de confiança?", "é furada?", "presta?", "vale a pena?", "é boa?" e a ordem inversa
                  # ("é confiável a coinbase?"). "Segurou os saques", "confirmou o acordo" e "boa parte das exchanges" são fato.
                  rf'|\b{EXCH}\b.{{0,80}}\b(segur[ao]s?|seguranca|confiave(l|is)|confianca|confi(o|ar)|golpe|furada|presta|vale a pena)\b'
                  rf'|\b{EXCH}\b[^.?!]{{0,30}}\b(e|ta|esta) (uma )?((exchange|corretora) )?(boa|bom|ruim|melhor|pior|top|seria|serio'
                  r'|idone[ao]|arriscad[ao]|piramide|de boa)\b(?! parte\b)'
                  rf'|\b(segur[ao]s?|seguranca|confiave(l|is)|confiar|confio|confianca|golpe|furada)\b[^.?!]{{0,40}}\b{EXCH}\b'
                  r'|\b(essa|esta|nessa|nesta) (corretora|exchange|plataforma|app)\b[^.?!]{0,20}\b(segur[ao]|confiavel|golpe|boa|ruim'
                  r'|furada|presta)\b'
                  r'|\bconfi(o|ar) (nessa|nesta) (corretora|exchange|plataforma|app)\b'
                  # escolher entre corretoras ("Binance ou Mercado Bitcoin?"), usar, abrir conta ou deixar o dinheiro numa delas
                  rf'|\b{EXCH}\b[^.?!]{{0,30}}\b(ou|x|vs|versus)\b[^.?!]{{0,30}}\b({EXCH}|outra|corretora|exchange)\b'
                  rf'|\b(corretora|exchange)\b[^.?!]{{0,30}}\b(ou|x|vs|versus)\b[^.?!]{{0,30}}\b{EXCH}\b'
                  rf'|\b(abr(o|ir|iria) (uma )?conta|(crio|criar|criaria|faco|fazer|faria) (uma )?conta|cadastr\w*|deix(o|ar)|guard(o|ar)'
                  rf'|confi(o|ar)|recomenda\w*)\b[^.?!]{{0,30}}\b{EXCH}\b'
                  # "Uso a Binance ou a Foxbit?", com a corretora no fim; não "Uso a Binance, como declaro o imposto?"
                  rf'|\b(uso|usar)\b[^.?!]{{0,15}}\b{EXCH}\W*$',
    'aposta': r'\bapost\w*|\baposto\b|\bbets?\b|\bpolymarket\b|\bkalshi\b|\bvpn\b',
    'voto': r'\bem quem\b|\bquem e (o )?melhor\b|\bmelhor candidato\b|\bdevo votar\b|\bquem (voce|vc) (apoia|prefere)\b'
            r'|\bmelhor (pra|para) (a |o )?(economia|bolsa|mercado|pais|brasil|investidor)\b|\bmercado prefere\b'
            r'|\b(pior|ruim|bom|boa) (pra|para) (a |o )?(bolsa|economia|mercado)\b|\bquem o mercado (quer|prefere)\b'
            r'|\bquebra o pais\b|\bvoce (vota|votaria|apoia|prefere)\b',
    # Trocar de papel ou tirar o aviso. "Só entre nós" não é troca de papel: a pergunta que vem depois é que pede recusa.
    'papel': r'\bfinj\w*|\bfinge\b|\bfaz de conta\b|\bimagin(e|a) que (voce|vc)\b|\b(voce|vc) e (um )?(analista|consultor|trader)\b'
             r'|\bcomo (um )?analista\b|\bignor(e|a|ar) (as |os |o )?(regras|instrucoes|avisos?)\b|\bsem (o |os )?avisos?\b'
             r'|\besquec\w* (as |os |o |das |dos |do )?(regras|instrucoes|avisos?)\b|\btir(a|e|ar) (o |os |esse |esses )?avisos?\b'
             r'|\bcomo se (voce )?fosse (um|uma|meu|minha) (amig[oa]|analista|consultor\w*|trader|assessor\w*|gerente|especialista)\b'
             r'|\bcomo (um|uma|meu|minha) amig[oa]\b'
             r'|\bsem rodeio\w*|\bmodo (desenvolvedor|dev|livre|dan|sem filtro)\b|\bjailbreak\b|\bvoce (agora )?e (o|a) [a-z]+'
             r'|\bsem filtros?\b|\bpode pular\b|\bassumo (toda |total |a )?responsabilidade\b|\bpara um (livro|roteiro|trabalho|filme|conto)\b'
             r'|\bhipotetic\w*|\bhypothetical\b|\bimagina um cenario\b|\bnum cenario\b|\bnum mundo\b|\bpersonagem\b|\bpretend\b'
             r'|\bja li (todos )?os avisos\b|\b(ja )?sei (os|dos) riscos\b|\bpela ultima vez\b|\bja perguntei\b',
    'binaria': r'\biq ?option\b|\bopc(ao|oes) binarias?\b|\bbinarias\b',
    'chance_candidato': r'\bquem (vai )?(ganha|ganhar|vence|vencer)\b'
                        r'|\bchances? (de|do|da|de o|de a) (ele|ela|o candidato|candidato|flavio|lula|bolsonaro) (ganhar|vencer|levar)\b'
                        r'|\bfavorit\w*|\bchances? de vitoria\b|\bquais (as|sao as) chances\b|\breeleit\w*|\beurasia\b'
                        r'|\b(vence|vencer|ganha|ganhar|leva|levar)\b.{0,20}\b(domingo|eleicao|segundo turno|2o turno)\b'
                        r'|\bprobabilidade d[oea] (lula|flavio|bolsonaro|ele|ela)\b|\bquem (ta|esta) na frente\b'
                        r'|\b(lula|flavio|bolsonaro) (vence|ganha|leva)\b',
    'chance_dinheiro': r'\bchances? de (eu )?(ganhar|lucrar)\b|\bganhar dinheiro\b|\bvou lucrar\b|\bda (pra|para) lucrar\b'
                       r'|\bquanto (eu )?ganho\b|\bquais (as|sao as) chances\b|\bganhar ou (nao|perder)\b|\bganha(r)? (uma )?grana\b'
                       r'|\blucr\w*|\brenda (mensal|extra)\b|\bficar rico\b'
                       # os sinônimos ("dá pra enriquecer com bitcoin?", "ficar milionário", "fazer fortuna", "viver de bitcoin")
                       r'|\benriquec\w*|\bficar milionari\w*|\bfazer (uma )?fortuna\b|\bviver de (bitcoin|btc|cripto\w*|trade|day ?trade)\b'
                       r'|\bdeixa\w* (alguem|a gente|eu) ric[oa]\b',
}

# O prazo que ainda vem ("até dezembro", "no Natal", "daqui a 6 meses", "by Christmas"). "Até dezembro de 2025", "no
# Natal de 2020" e "o fim do ano passado" são passado.
MESES = r'(janeiro|fevereiro|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)'
PRAZO = (r'(\bate (o )?(' + MESES[1:-1] + r'|natal|carnaval|fim|final)\b'
         r'|\b(no|pro|para o|pelo) (natal|fim do ano|final do ano|fim do mes|final do mes)\b)'
         r'(?! (de |do ano de )?(20)?\d\d\b| passado\b)'
         r'|\b(ano|mes|semestre) que vem\b|\bproximo (ano|mes|semestre)\b|\bdaqui (a\b|\d|uns?\b|umas?\b)'
         r'|\bby (christmas|year[- ]end|the end of|end of)\b|\bnext (year|month|week)\b')
# Um nível de preço (ou o preço) seguido de um prazo que ainda vem.
# O ano que já passou depois de "em/de" ("quanto o Ibovespa caiu em 2008 até o fim do ano?") não é nível; com moeda, ou
# depois de "a/to/at" ("eth a 2000 até o fim do ano?"), é. A elipse com "nos/aos/na casa dos" ("brent nos 200 até o fim
# do ano?") também é nível.
NIVEL_PRAZO = (r'(\b(a|to|at|nos|aos|(na )?casa d[oa]s)( us\$| r\$| \$|\$)? ?\d|\b(em|de)(( us\$| r\$| \$|\$) ?| (?!(19|20)\d\d\b))\d'
               r'|\b(brent|wti|barril|petroleo|oil|dolar|euro|ibovespa|bitcoin|btc|gasolina|diesel) (us\$ ?|\$)?\d'
               r'|\b\d[\d.,]* ?(dolares|dolar|reais|mil|k)\b|\b(preco|cotacao|valor|price)\b)'
               r'[^.?!]{0,40}(' + PRAZO + r')')
# Nível de preço no futuro ("vai a 150?", "chega nos 200?", "volta pros 70?", "rompe 120?", "bate na casa dos 150?", "vai
# a R$ 50?"): termina no 1º dígito, para valer com "150k" e "250 mil". Fica de fora o passado ("passou de", "chegou a",
# "atingiu"), o prazo ("chega em 2 dias"), o ano ("chega em 2027"), o ordinal ("rumo ao 2º turno"), a regra ("vendas que
# chegam a 35 mil") e o "conseguiu voltar a 100 mil em 2020" (passado).
# O infinitivo "ir a/pra" ("pode ir a 200?", "o ibovespa pode ir pra 200 mil?") também, menos o passado ("chegou a ir a
# 140"). O "rumo a" do ano ("o plano rumo a 2030") não é nível; "rumo aos 2000" é.
NIVEL_VERBO = (r'(?:\bva[io] (?:a|ao|aos|as|pra|pro|pros|pras|para|para o|para os|para as)'
               r'|(?<!\bchegou a )(?<!\bchegaram a )(?<!\bconseguiu )(?<!\bconseguiram )'
               r'\bir (?:a|ao|aos|as|pra|pro|pros|pras|para|para o|para os|para as)'
               r'|\brumo(?: (?:aos|as|os|pros|pras|para os|para as)|(?: (?:a|ao|pra|pro|para|para o))?(?! (?:19|20)\d\d\b))'
               r'|(?<!\bque )(?<!\bconseguiu )(?<!\bconseguiram )\b(?:chega|chegam|chegar|chegaria|volta|voltam|voltar|bate|batem|bater'
               r'|atinge|atingem|atingir|alcanca|alcancam|alcancar|ultrapassa|ultrapassam|ultrapassar|supera|superam|superar|rompe'
               r'|rompem|romper|retorna|retornam|retornar)'
               r'(?: (?:a|ao|aos|as|os|na|no|nas|nos|pra|pro|pras|pros|para|para o|para os|para as|em(?! (?:19|20)\d\d\b)))?)'
               r'(?: (?:a )?casa d[oa]s)?(?: (?:r\$|us\$|u\$))? ?')
NIVEL = (r'|' + NIVEL_VERBO + r'\d(?!\d*[oa]\b)(?![\d.,]*\s?(?:h|hs|horas?|minutos?|dias?|semanas?|mes|meses|anos?|pregoes|uteis)\b)'
         # "passa de R$ 6?" só com preço unitário: "se eu passar de R$ 35 mil" é a regra do imposto
         r'|\bpassa(?:m|r)? (?:de|dos|das|da)(?: (?:a )?casa d[oa]s)?(?: us\$| r\$(?! ?(?:[\d.,]* ?(?:mil|mi|milh\w*|k)\b|\d{4}'
         r'|\d{1,3}\.\d{3})))? ?\d'
         # com o mercado de sujeito e verbo de futuro, qualquer R$ ("o bitcoin vai passar de R$ 500 mil?")
         r'|(?<!\bde )(?<!\bem )\b(?:dolar|euro|ibovespa|bitcoin|btc|brent|wti|barril|petroleo|gasolina|diesel|etanol|ouro|petr[34]'
         r'|petrobras)(?: \w+)? (?:vai|vao|pode|podem|poderia|deve|devem|deveria|consegue|conseguem) passar (?:de|dos|das)'
         r'(?: (?:a )?casa d[oa]s)? r\$ ?\d'
         # "PETR4 sai de 30 pra 40?"
         r'|\b(?:sai|vai|passa) de(?: r\$| us\$)? ?\d[\d.,]*(?: mil| k)? (?:pra|para|a|ate)(?: r\$| us\$)? ?\d')
# O número do alvo ("o dólar vai a R$ 7?", "btc rumo aos 100k?", "o ouro vai a 3000 dólares?") não é o dinheiro da pessoa:
# sai do texto antes do capital e da conta de câmbio.
# Também o alvo com "sobe/cai pra", "passa de" e o nível com prazo ("bitcoin a 200k ano que vem?").
_ALVO_VERBO = (r'(?:\b(?:sobe|sobem|subir|cai|caem|cair|desce|descem|descer|recua|recuam|recuar|despenca|despencam|despencar)'
               r' (?:a|ao|aos|as|pra|pro|pros|pras|para|para o|para os|para as|ate)'
               r'|(?<!\beu )\bpassa(?:m|r)? (?:de|dos|das)(?: (?:a )?casa d[oa]s)?)(?: (?:r\$|us\$|u\$))? ?')
_ALVO_QUANTIA = (r'\d(?!\d*[oa]\b)[\d.,]*(?: ?(?:mil|k|milhao|milhoes|mi)\b)?'
                 r'(?: ?(?:de )?(?:reais|dolares|dolar|dollars?|usd|euros?|eur|pontos?)\b)?')
ALVO_NUM = ('(?:' + NIVEL_VERBO + '|' + _ALVO_VERBO + ')' + _ALVO_QUANTIA
            # o nível com prazo, sem verbo ("bitcoin a 200k ano que vem?", "bitcoin nos 200k até o Natal?"); sem o "de", que
            # é o dinheiro dela ("uma reserva de 10 mil dólares até o fim do ano")
            + r'|\b(?:a|aos?|nos?|em|to|at) (?:r\$ ?|us\$ ?|\$ ?)?' + _ALVO_QUANTIA + r'(?=[^.?!]{0,40}(?:' + PRAZO + r'))')
# Pergunta sobre o futuro de um preço: direção, magnitude, nível ou "o que acontece se". Leva a recusa (N2).
FUTURO = (r'\b(sobe|sobem|subir|suba|subira|subiria|desce|descer|cai|caem|cair|caia|caira|cairia|despenc\w*|dispar\w*|derret\w*'
          r'|valoriz\w*|desvaloriz\w*|aprecia\w*|recua\w*|fecha|fechar|abre|abrir|pra cima|para cima|pra baixo|para baixo|topo'
          # "fundo de índice" e "fundo de investimento" são o produto, não o fundo do preço; "fundo do bitcoin" é o fundo do
          # preço, "fundo de bitcoin" é o produto
          r'|fundo(?! (de|do|da|dos|das) (indices?|investimentos?|pensao|previdencia|renda|garantia|emergencia)\b'
          r'| de (acoes|cripto\w*|bitcoins?)\b| imobiliarios?\b)'
          r'|barat[oa]s?|car[oa]s?|vies|palpite|visao|acha|acham|opiniao|tendencia|provavel|esperado|retorno|potencial'
          # o preço de uma ação contra o "justo" (valuation) também é opinião sobre para onde ela vai
          r'|descontad[oa]s?|esticad[oa]s?|subvalorizad[oa]s?|sobrevalorizad[oa]s?|supervalorizad[oa]s?|upside|valuation'
          r'|preco justo|valor justo|carissim[oa]s?|baratissim[oa]s?|precificad[oa]s?'
          # "o imposto está no preço da gasolina?" é a composição da bomba, e "o brent tá no preço de 2022?" é o passado; o
          # "já está no preço do petróleo/da PETR4" é opinião e continua recusa
          r'|(ta|esta|estao|tao|negocia|negociam|sendo negociad[oa]s?) (com desconto|em promocao|num preco (bom|otimo)'
          r'|num (bom|otimo) preco|com (um )?(bom|otimo) preco|com preco (bom|otimo)'
          r'|(abaixo|acima) do (seu )?valor( patrimonial| real| intrinseco)?\b(?! d[aeo]s? | de | em )'
          r'|no preco\b(?! d[aeo]s? (gasolina|diesel|etanol|combustive(l|is)|bomba)\b| de (ontem|antes|19\d\d|20\d\d)\b'
          r'| d[oa] (ano|mes|semana|dia) passad[oa]\b))'
          r'|pechinch\w*|promocao|de graca|baratinh\w*|undervalued|overvalued|cheap|expensive|price target|subavaliad\w*'
          r'|preco de banana|vale o preco'
          r'|target price'
          r'|vai bem|vai mal|reage bem|reage mal|pra onde|para onde|go up|go down|rise|fall|rally'
          # juízo sobre a ação ("isso é bom pra ação?", "é bom pra PETR4?"): é opinião sobre para onde ela vai
          r'|(bom|boa|ruim|otimo|otima|pessimo|pessima) (pra|para|pro|pros|pras) (a |o |as |os )?(acao|acoes|papel|papeis'
          r'|cotacao|petr[34]|petrobras|prio3?)'
          # "conseguiu voltar a 100 mil em 2020?" é passado
          r'|bajar|probabilidad\w*|chances?|(?<!conseguiu )(?<!conseguiram )voltar (pra|para|a)'
          # "segue subindo?", "continua caindo?"; o passado ("seguiu", "continuou") fica de fora
          r'|(continua|continuam|continuar|segue|seguem|seguir) (subindo|caindo|em alta|em queda)'
          # gíria de cripto, em formas fechadas: "bombardeio" e "pump and dump" (conceito) não entram, nem o passado
          # ("o dólar explodiu na pandemia?", "o Ibovespa decolou em 2018?", "bombou em 2019?")
          r'|explod(?!iu\b|iram\b|ido\b)\w*|decol(?!ou\b|aram\b|ado\b)\w*|bombar|bombando|pumpa\w*|pumpar|pra lua|para a lua'
          # "o que significa moon?" é conceito
          rf'|to the moon|{CONCEITO_ANTES}(?<!\bque e )moon|voa|voam|voar|voara|voaria|voando|pro espaco|para o espaco|vai (mais )?longe'
          r'|pras? (alturas|nuvens)|afund(a|am|ar|ara|aria|ando)'
          # "estourar o limite do cartão" é a dívida, não o preço
          # "estourar a (minha) margem", "a garantia estoura" e "a conta estourar" são a chamada de margem (P5, D4), que o
          # bloco do WIN explica; "vai estourar" continua pedido
          r'|(?<!margem )(?<!garantia )(?<!conta )estour(a|am|ar|ara|aria|ando)'
          r'(?! (o |a |do |da )?((meu|minha|seu|sua) )?(cartao|orcamento|cheque|limite|margem|garantia|conta)))\b'
          r'|\b(vai|vao) estourar\b'
          # "o bitcoin explodiu, vai continuar?": o que vem depois do movimento
          r'|\b(vai|vao|deve|devem) continuar\b'
          # o movimento trazido por alguém ("o petróleo pode trazer 10 dólares de alta?", "a OPEP vai dar uma alta?")
          r'|\b(pode|podem|poderia|vai|vao|deve|devem|deveria) (trazer|levar|dar)( \w+){0,3} (altas?|quedas?|subidas?|baixas?)\b'
          # "o bitcoin bombou, continua?", "o dólar subiu, segue?": o verbo sozinho na oração (depois de vírgula, ponto, "e"
          # ou "mas"); com sujeito ("a isenção continua?", "a guerra continua?") não
          r'|(?:^|[,.;:!?]|\b(?:e|mas)\b)\W*(?:sera (?:que )?)?(?:ainda |isso )?(?:(?:vai|vao|deve|devem) (?:continuar|seguir)'
          r'|continua|continuam|segue|seguem|continuara|continuarao|seguira|seguirao)'
          r'(?: assim| subindo| caindo| desse jeito| em alta| em queda)?\W*$'
          r'|(?<!\bna )(?<!\bda )(?<!\ba )(?<!\bpra )(?<!\bpara )(?<!\bpela )(?<!\bnas )(?<!\bdas )\bbomba (mais|de novo)\b'
          + NIVEL +
          # "quanto vai estar o barril no natal?", "¿cuánto va a valer el barril?"
          r'|\b(vai|vao|va a|van a) (estar|valer|custar|ficar|ta|llegar|costar)\b'
          r'|\b(vai|vao) (pra|para) quanto\b|\b(pra|para) quanto (vai|vao)\b'
          # "já subiu demais?" é o "esticado"; o pretérito com data fechada ("por que a bolsa caiu demais em março de 2020?",
          # "caiu demais na pandemia?", "caiu demais ontem") é passado (P1). "desde 2020" chega até hoje e continua recusa.
          r'|\b(sobe|cai|subindo|caindo) demais\b|\bja (subiu|caiu|subiram|cairam) demais\b'
          r'|(?:^|[.?!;])(?!(?![^.?!;]*\bdesde\b)[^.?!;]*\b((19|20)\d\d|pandemia|covid|ontem|anteontem|passad[oa]s?)\b)'
          r'[^.?!;]*\b(subiu|caiu|subiram|cairam) demais\b'
          # "o petróleo termina o ano acima de 100?", como o "fecha" ("terminou o ano" é passado)
          r'|\b(termina|terminar|terminam|encerra|encerrar|encerram) (o ano|o mes|a semana|o semestre|20\d\d)\b'
          # em inglês ("Will oil hit $100?", "Is oil going to crash?"), sem "crash" nem "hit" soltos ("o crash de 2020")
          # O futuro da pessoa ("I'm going to Brazil", "we are going to Lisbon", "I am going to study oil") não é o do preço,
          # a não ser que fale do dinheiro ou do nível ("I'm going to lose money?", "we're going to see the dollar at 6?"); a
          # agenda ("what is going to happen at the OPEC meeting?") também não.
          r"|(?<!\bi'm )(?<!\bim )(?<!\bi am )(?<!\bwe're )(?<!\bwere )(?<!\bwe are )(?<!\bthey're )(?<!\btheyre )"
          r"(?<!\bthey are )\b(going to|gonna)\b(?! happen (at|in|on|during)\b)"
          r'|\b(going to|gonna) ((make|lose) (money|a profit|profit)|profit|get rich'
          r'|see( \w+){0,2} (at (\$|us\$|r\$)? ?\d|hit|reach|go|drop|fall|rise|crash))\b'
          # "how much will I get in reais for 1000 dollars?" é a conversão de hoje; com prazo ("... in December?") é futuro
          r'|\bwill (?!(?<=how much will )(i|we|you) get\b(?![^.?!]*\b(next|tomorrow|later|when|after|before|until|by|end of'
          r'|in (january|february|march|april|may|june|july|august|september|october|november|december|20\d\d))\b))'
          r'(\w+ ){0,2}(hit|reach|crash|drop|climb|go|be|get|rise|fall)\b'
          r'|\bwhere (is|are|will)( \w+){1,3} (headed|heading|going)\b'
          r'|^\W*(\w+ ){1,2}to \$?\d'  # manchete: "Oil to 150 by Christmas?", "BTC to 100k?"
          r'|\bllega(r|ra)? a( us\$)? ?\d|\b(ja )?(foi|era) (o|a) pico\W*$'
          # máxima e "flip" de cripto, no futuro e no presente ("bitcoin vai renovar máxima?", "eth vai flipar?"); o passado
          # ("renovou", "flipou") e o conceito ("o que é ATH?", "flippening") ficam de fora
          r'|\brenova(r|ra|ria|rao)?( a| uma)?( nova)? (maximas?|ath)\b'
          r'|\b(vai|vao|chega|chegar|volta|voltar) (pra|para|na|a)( uma)?( nova)? maximas?\b'
          r'|\b(bate|bater|batera|bateria|faz|fazer|fara|faria|atinge|atingir|atingira|atingiria|ter|tera|teria|marca|marcar'
          r'|marcara)( uma| um)?( nova| novo)? (maximas?|ath)\b'
          r'|\b(vai|vao|pode|podem|deve|devem) (bater|fazer|atingir|ter|marcar)( a| uma| o| um)?( nova| novo)? (maximas?|ath)\b'
          r'|\bflipp?(a|ar|am|ara|aria|e|em|ando|s)\b'
          rf'|\b(vai|vao|pode|podem|deve|devem|consegue) (passar|ultrapassar|superar)( o| a)? {CRIPTO_NOME}\b'
          rf'|\b(ultrapassa|ultrapassam|ultrapassara|ultrapassaria|supera|superam|superara|superaria)( o| a)? {CRIPTO_NOME}\b'
          # "PETR4 tá muito alta?": o juízo sobre o nível do papel ("a Selic está muito alta?" fica de fora)
          rf'|(?<!\bda )(?<!\bdo )\b{EMPRESA}\b[^.?!]{{0,15}}\b(ta|esta) (muito|bem) (alt|baix)[oa]s?\b'
          # o nível com prazo, sem verbo ("Brent a 100 até dezembro?", "Qual o preço do brent daqui a 6 meses?")
          r'|' + NIVEL_PRAZO)
# O que não é preço sai do texto só para o FUTURO (o resto do roteador lê a pergunta inteira):
# - "cara" vocativo ("cara, como tá o dólar?", "ô cara", "o dólar, cara,") e substantivo ("a cara do Ibovespa", "com cara
#   de quê", "o cara do BC"). "Tá cara?", "cara demais" e qualquer "cara de X" (de alta, de subida, de oportunidade)
#   continuam valuation e direção (N2); só "a cara do/da" e "cara de quê" saem.
CARA_NAO_PRECO = (r'^((o|oh|ai|ei|e ai|fala|opa|oi|po|poxa|putz|nossa|mano|meu|velho|vei|serio|olha|ah|tipo|bom|caramba|eita)'
                  r'\W+)?cara\b(?! demais\b)|,\s*cara\b(?! demais\b)'
                  r'|\b(a|qual a|qual e a|qual seria a) cara d[ao]s?\b|\bcara de que\b'
                  r'|\b(o|um|esse|este|aquele|do|no|pro|pelo|ao|num|dum|desse|nesse|daquele) cara\b')
# - "descontado" de imposto ou de provento ("o IR é descontado na fonte?", "o dividendo é descontado do preço?"): é regra
#   (P5), não "a ação tá descontada". Com empresa citada, só o "na fonte" sai.
DESCONTO_NA_FONTE = r'\bdescontad[oa]s? (na|no) (fonte|holerite|contracheque|salario)\b'
DESCONTO_NAO_PRECO = (r'\b(imposto|ir|irrf|iof|tributos?|taxas?|tarifas?|custodia|corretagem|emolumentos?|come cotas'
                      r'|dividendos?|jcp|proventos?|juros sobre capital|cupom|cupons)'
                      r'( (de|do|da|dos|das|sobre|no|na|em) (\w+ ){0,3}\w+)? (e|sao|foi|foram|vem|sera|serao|fica|ficam|seria)'
                      r' descontad[oa]s?\b')
# Depois de um conector de adjunto ("o bitcoin com as taxas é descontado?", "o ibovespa pagando dividendos é descontado?"),
# o imposto ou o provento não é o sujeito: o "descontado" é do ativo, e continua valuation (N2).
ADJUNTO_ANTES = r'\b(com|sem|pagando|incluindo|considerando|contando)( (o|a|os|as))? $'
# - a definição inteira e genérica ("o que é valuation?", "como se calcula o preço justo de uma ação?") é conceito (P5).
#   Com artigo, mercado ou empresa ("o que é o upside do Ibovespa?") continua recusa.
_GENERICO = r'( (de|em|numa|num) (uma |um )?(acao|acoes|empresa|empresas|ativo|ativos|papel|papeis))?\W*$'
DEFINICAO_VALUATION = (r'^((o que|oq) (e|sao|significa|quer dizer)|como (funciona|se calcula|se faz|e calculado))( o| um| uma)?'
                       r'( (acao|acoes|papel|ativo))? (valuation|upside|preco justo|valor justo|descontad[oa]s?|esticad[oa]s?'
                       r'|subvalorizad[oa]s?|sobrevalorizad[oa]s?|precificad[oa]s?|undervalued|overvalued|price target|target price'
                       r'|pechinchas?|vaca leiteira)' + _GENERICO)
# - o "caro" da bomba numa pergunta que pede a explicação ("por que a gasolina está cara?", "quanto do preço da gasolina
#   cara é imposto?") é o que o bloco do barril à bomba responde, não valuation. "A gasolina tá cara?" e "a gasolina vai
#   ficar mais cara?" continuam recusa (N2).
BOMBA_EXPLICA = r'\b(por que|porque|pq|por causa d\w*|culpa d\w*|o que (deixa|faz|torna)|quanto d[oa]|imposto\w*|do mundo)\b'
BOMBA_CARA = r'\b(gasolina|diesel|etanol|combustive(?:l|is))\b([^.?!]{0,30}?)\b(car|barat)[oa]s?\b'
# A bomba junto com a ação ("por que a gasolina e a petr4 estão caras?") é valuation do papel (N2; Mapa legal, seção 8,
# item 10): o "caro" não sai.
_COMBUSTIVEL = r'(gasolina|diesel|etanol|combustive(?:l|is))'
BOMBA_E_EMPRESA = (rf'\b{_COMBUSTIVEL},? (e|ou) (a |o |as |os )?((acao|acoes|papel|papeis) d[aeo]s? )?{EMPRESA_SEM_VALE}\b'
                   rf'|\b{EMPRESA_SEM_VALE},? (e|ou) (a |o |as |os )?{_COMBUSTIVEL}\b')
# - a regra do circuit breaker ("quando a queda passa de 10%?") não é nível de preço no futuro.
REGRA_DE_QUEDA = (r'\bquando\b[^?!.]{0,40}\b(queda|baixa)\b[^?!.]{0,20}\bpassa(r)? de \d+([.,]\d+)? ?%'
                  r'|\bquando\b[^?!.]{0,40}\bpassa(r)? de \d+([.,]\d+)? ?% de (queda|baixa)\b')
PASSA_DE_PCT = r'\bpassa(r)? de (?=\d+([.,]\d+)? ?%)'
# "quando o ibovespa cai mais de 10% tem circuit breaker?" é a regra do circuit breaker, não previsão
REGRA_CIRCUIT = r'\bquando\b[^?!.]{0,60}\bcircuit[ -]?breakers?\b|\bcircuit[ -]?breakers?\b[^?!.]{0,60}\bquando\b'
# - a regra com o imposto como sujeito ("a isenção do bitcoin de 35 mil vai continuar?", "quanto vai ficar o IOF do cartão?",
#   "o IR do bitcoin sai de 15 para 17,5?", "qual o valor da isenção no ano que vem?", "o valor mínimo do Tesouro muda?") é
#   regra (P5). O imposto que acompanha um preço ("o dólar com IOF vai ficar quanto?") não sai, e a frase com "e", "ou",
#   "também" ou "se" ("quanto vai ficar o IOF e o dólar?") continua recusa.
REGRA_SUJEITO = (r'(?<!\bcom )(?<!\bsem )(?<!\bmais )(?<!\bmenos )(?<!\bcom o )(?<!\bcom a )(?<!\bsem o )(?<!\bsem a )'
                 r'\b(iof|impostos?|ir(?! (pra|para|pro|pros|a|ao|aos|bem|mal|longe|ate|alem)\b)|irpf|aliquotas?|isenc\w*'
                 r'|taxas? de (custodia|corretagem|administracao)|custodia|corretagem|emolumentos?|declarac\w*|come-?cotas|tributac\w*)\b')
_COMPLEMENTO = r'( (?!(o|a|os|as|um|uma|e|ou|mas|que|se|com|sem)\b)\w+)'
REGRA_FUTURA = (rf'\b(vai|vao|deve|devem) (ficar|custar|continuar|valer|estar|mudar)( (o|a|os|as))? {REGRA_SUJEITO}'
                rf'|{REGRA_SUJEITO}{_COMPLEMENTO}{{0,6}} (vai|vao|deve|devem) (ficar|custar|continuar|valer|estar)\b'
                rf'|{REGRA_SUJEITO}{_COMPLEMENTO}{{0,4}} (sai|vai|passa) de [\d.,]+ ?%? (pra|para|a) [\d.,]+'
                rf'|\b(valor|preco)( d[aoe]s?)? {REGRA_SUJEITO}'
                r'|\bvalor minimo\b(?=( (d[aoe]s?|pra|para|de|no|na|em))? (o |a )?(tesouro|investimento|investir|aplicac\w*|aplicar'
                r'|aporte|aportar|cdb|lci|lca|fiis?|fundos?|cotas?|resgate|deposito|depositar|saque|sacar|conta)\b)')
COORDENA = (r'\b(ou|nem|tambem|se)\b|(?<!\bqual )(?<!\bquanto )(?<!\bcomo )(?<!\bque )(?<!\bonde )(?<!\bquando )(?<!\bisso )'
            r'(?<!\bnao )\be\b(?! que\b)')
CAI_MAIS_PCT = r'\b(cai|caem|cair|recua|recuam|recuar|despenca|despencam) mais de (?=\d+([.,]\d+)? ?%)'
# - o intervalo que começa num mês ou ano ("de janeiro até outubro", "desde 2020 até") não é o prazo de uma previsão.
INTERVALO = rf'\b(de|desde) (o |a )?({MESES[1:-1]}|inicio do ano|comeco do ano|20\d\d) ate\b'
CONDICIONAL = (r'\bse (o |a )?(\w+ ){0,2}(ganhar|vencer|perder|for eleito|for reeleito|cortar|cortarem|subir|aumentar|baixar|'
               r'reduzir|mantiver|wins?)\b|\b(ganhando|vencendo|perdendo)\b|\bcom (o |a )?\w+ eleit[oa]\b|\bif \w+ wins?\b')
# Pergunta sobre o que já aconteceu: não pede direção.
# "o Brent teve retorno negativo no ano?" também pergunta o que já aconteceu
# O "antes" de um evento que ainda vem ("o dólar sobe antes da eleição?", "antes do halving?") não é passado; com o ano
# ("antes da eleição de 2018") é.
PASSADO = (r'\b(reagiu|reagiram|aconteceu|aconteceram|foi|foram|ficou|ficaram|teve|tiveram|historico|historicamente|ja houve'
           r'|antes(?! d[aeo]s? (eleic(ao|oes)|turno|\d+o turno|(primeiro|segundo) turno|copom|halving|reuniao|posse'
           r'|votacao|decisao|proxim\w*|fim|final)\b(?! de (19|20)\d\d))|passad[ao]s?|levou|levaram|demorou|demoraram)\b')
FUTURO_EXPLICITO = (r'\b(vai|vao|agora|amanha|semana que vem|depois d[oa]|proxim\w*|pra onde|para onde)\b'
                    # "Brent em 138 foi o topo?" e "o bitcoin já teve o topo?": se o topo já passou é pergunta sobre o que vem;
                    # com o ano que já passou ("o bitcoin a 69 mil em 2021 foi o topo?") é passado
                    r'|\bdaqui a\b|\bja (foi|era|teve|tiveram) (o|a|seu) (topo|fundo|pico)\W*$'
                    r'|^(?!.*\b(19\d\d|20[01]\d|202[0-5])\b).*\b(foi|era|teve|tiveram) (o|a|seu) (topo|fundo|pico)\W*$'
                    # "o fundo já foi?", "o topo já passou?": com o "já", pergunta se o que vem é mais baixo ou mais alto
                    r'|\b(topo|fundo|pico) ja (foi|passou)\W*$')
# Oração: "o dólar ficou abaixo de 5, cai mais?" pede o próximo movimento na 2ª oração; o "ficou" da 1ª não apaga o
# pedido. Vírgula e ponto de número ("5,04", "1.000") não separam.
ORACAO = r'[;:?!]|[,.](?!\d)|\b(?:e|mas)\b'
# "teve" e o passado da oração relativa ("o petróleo que teve alta tende a cair?", "o dólar que ficou alto cai?",
# "o dólar já teve alta suficiente pra cair?") não apagam o verbo no futuro da mesma oração. Sem verbo no futuro ("o
# Brent teve retorno negativo no ano?", "a ação que teve retorno negativo em 2020?"), continuam marca de passado.
PASSADO_FRACO = (r'\b(teve|tiveram)\b'
                 r'|(?<!\bo )(?<!\bpor )(?<!\bpra )(?<!\bpara )\bque (ja )?(teve|tiveram|ficou|ficaram|foi|foram)\b')
FUTURO_VERBO = (r'(?<!\bvoltou a )(?<!\bvoltaram a )(?<!\bteve que )(?<!\bteve de )(?<!\bcomecou a )(?<!\bpassou a )'
                r'\b(sobe|sobem|subir|suba|subam|subira|subirao|subiria|desce|descem|descer|cai|caem|cair|caia|caiam|caira'
                r'|cairao|cairia|despenca|despencam|despencar|dispara|disparam|disparar|derrete|derretem|derreter|valoriza'
                r'|valorizam|valorizar|desvaloriza|desvalorizam|desvalorizar|recua|recuam|recuar|tende|tendem|tera|terao)\b'
                r'|\b(volta|voltam|voltar) (a|pra|para)\b')


def _passado_da_oracao(o: str) -> bool:
    if re.search(FUTURO_VERBO, o):
        o = re.sub(PASSADO_FRACO, ' ', o)
    return bool(re.search(PASSADO, o))


# O advérbio vale para a frase inteira: "historicamente, a bolsa sobe depois de eleição?" pergunta o que já aconteceu (P1).
PASSADO_DA_FRASE = r'\b(historicamente|no passado)\b'
# O trecho entre pontuação: o advérbio só vale para a frase toda quando no máximo um trecho pede ou se move ("historicamente
# o dólar sobe em eleição, sobe esse ano?" pede no 2º trecho).
TRECHO = r'[;:?!]|[,.](?!\d)'
# O verbo de pedido no presente depois do "ficou/foi" na mesma oração ("o dolar ficou abaixo de 5 cai mais?", "o bitcoin que
# ficou barato explode?") é o pedido; numa subordinada ("como o dólar reagiu quando o Copom sobe?") não.
VERBO_PEDIDO = (r'\b(sobe|sobem|desce|descem|cai|caem|despenca|despencam|dispara|disparam|derrete|derretem|valoriza'
                r'|valorizam|desvaloriza|desvalorizam|aprecia|recua|recuam|explode|explodem|decola|decolam|voa|voam)\b')
PASSADO_VERBAL = r'\b(reagiu|reagiram|aconteceu|aconteceram|foi|foram|ficou|ficaram|teve|tiveram)\b'
SUBORDINADA = r'\b(quando|sempre que|toda vez que|enquanto|porque|por que)\b.*'
# O ano que já passou marca a oração sem verbo ("o euro ficou caro em 2022 e barato em 2023?"). Teto fixo (o analisar não
# recebe a data): quando envelhecer, erra para mais recusa.
ANO_PASSADO = r'\b(em|de|no ano de) (19\d\d|20[01]\d|202[0-5])\b'
# A oração sem verbo que repete o "ficou caro/barato" da anterior ("em 2020 a bolsa ficou barata, e o dólar caro?") herda o
# passado dela. "tá barato?", "continua caro?", "barato em 2027?" e a empresa ("a PETR4 ficou barata e a PRIO cara?")
# continuam pedido.
ELIPTICA = r'^\W*(?:(?:o|a|os|as) \w+ )?(?:barat|car)[oa]s?(?: em ((?:19|20)\d\d))?\W*$'
# Na oração, o movimento no pretérito também é marca de passado ("como o dólar reagiu e se valorizou na pandemia?"): o
# FUTURO pega "valoriz", "dispar" e "despenc" em qualquer tempo.
MOVIMENTO_PASSADO = (r'\b(subiu|subiram|caiu|cairam|valorizou|valorizaram|desvalorizou|desvalorizaram|despencou|despencaram'
                     r'|disparou|dispararam|derreteu|derreteram|recuou|recuaram|apreciou|apreciaram|explodiu|explodiram|decolou'
                     r'|decolaram|bombou|fechou|fecharam|abriu|abriram)\b')
# A oração que pergunta o que foi: "qual foi a decisão?", "como foi?"
QUAL_FOI = r'^\W*(qual|que|como|quando|o que) (foi|foram|era)\b'
VERBO_DECISAO = ('corta|cortam|mantem|segura|eleva|elevam|aumenta|aumentam|baixa|baixam|reduz|reduzem|sobe|sobem'
                 '|reajusta|reajustam')
# O melhor ou o pior momento que já passou ("qual foi o pior momento do Ibovespa na pandemia?") é fato (P1). O momento
# "pra comprar" continua pedido, mesmo no passado ("qual foi o melhor momento pra comprar dólar em 2020?").
MOMENTO_DICA = r'\b(bom|otimo|melhor|pior) momento\b'
MOMENTO_PASSADO = (r'\b(qual|quando) (foi|foram) o (melhor|pior) momento\b|\b(teve|tiveram|viveu) (o|seu) (melhor|pior) momento\b'
                   r'|\b(melhor|pior) momento\b[^.?!,;]{0,40}\b(foi|foram|aconteceu|ocorreu) (em|no|na|nos|nas|durante|quando|entre)\b')
MOMENTO_PRA = r'\b(bom|otimo|melhor|pior) momento\b[^.?!,;]{0,25}\b(pra|para|de) \w+(ar|er|ir)\b'
# A viagem de quem fala, com destino ("vou voar pra Lisboa com 2 mil euros", "embarco semana que vem pros EUA"), não é a
# gíria do preço ("o bitcoin vai voar", "vou voar com o bitcoin?") nem a entrada ("embarco no brent?", "embarco hoje?",
# "embarco pro bitcoin?", "embarco pra lucrar?"): sai do texto que o FUTURO e a dica leem.
VIAGEM = (r'(\b(vou|vamos|a gente vai|eu|estou|to|tou) (voar|voando)\b|\bembarc(o|amos)\b)'
          r'( (hoje|amanha|(na |nesta |essa |nessa |esta )?(semana|mes) que vem|dia \d+|em \d+ dias|daqui a \d+ dias'
          r'|(na |nesta |essa |nessa |esta )?(segunda|terca|quarta|quinta|sexta)(-feira)?|(no |neste |nesse |este |esse )?(sabado|domingo)'
          rf'|em {MESES}))?'
          r' (pra|para|pro|pros|pras|rumo a|rumo ao|a caminho d[aeo])\b'
          rf'(?! (o |a |os |as |um |uma )?(({ATIVO}|{CRIPTO_NOME}|euros?|lua|cima|baixo|espaco|alto|ceu|marte|dentro'
          r'|\w+(ar|er|ir))\b|\d|r\$|us\$))')
# O prazo curto de uma decisão que ainda vai sair.
PRAZO_DECISAO = r'(proxim\w*|amanha|semana que vem|mes que vem|(essa|esta|nessa|nesta) semana|(este|esse|neste|nesse) mes)'
SEM_IMPOSTO = r'(?! d[aoe]s? (impostos?|iof|ir|irpf|tributos?|aliquotas?)\b)'
# Decisão de juros que ainda vai sair: "vai cortar os juros?", "o BC vai reduzir a Selic?", "vai ter corte?", "o Copom
# cortará?", "corta na próxima reunião?". É futuro pela forma do verbo: não passa pelo filtro do PASSADO.
DECISAO = (r'\b(vai|vao|ira|irao|deve|devem|pode|podem)( \w+){0,2} (cortar|baixar|reduzir|manter|segurar|elevar|aumentar'
           r'|subir|mexer|parar|pausar|interromper|reajustar)\b'
           # pagar dividendo que ainda vai sair é previsão; pagar imposto, IOF, cupom ou o juro semestral do título é regra
           # (P5). "O tesouro vai pagar mais juros?" e "o CDB vai pagar juros altos?" continuam previsão. Com empresa citada,
           # o PAGAR_EMPRESA decide.
           r'|\b(vai|vao|ira|irao|deve|devem|pode|podem)( \w+){0,2} pagar\b(?!( \w+){0,2} (impostos?|ir|irpf|iof|darf|tributos?'
           r'|taxas?(?! de (dividendos?|retorno|distribuicao|pagamento))|tarifas?|cupom|cupons|come-?cotas|ajustes?)\b'
           r'| (mais|menos) (que|do que) (a |o )?(selic|cdi|poupanca)'
           r'| juros? (semestra\w*|mensa\w*|(todo|a cada|por) (mes|semestre))\b| juros?\W*$)'
           r'|\b(cort|baix|segur|elev|aument)a(ra|rao|ria|riam)\b|\breduzi(ra|rao|ria|riam)\b|\bmante(ra|rao|ria|riam)\b'
           r'|\b(vai ter|vai haver|vao ter|tera|havera|teremos|vai sair|vai vir|vai rolar|vao rolar)( \w+){0,2} (corte|cortes|alta|altas'
           r'|aumento|reducao'
           r'|elevacao|manutencao|pausa|queda|reajuste|reajustes|dividendos?|proventos?)\b'
           # o dividendo que volta ("a petrobras volta a pagar dividendo?"); "voltou a pagar" é passado, e o imposto é regra
           r'|\bvolta(m|ra|rao)? a (pagar|distribuir)\b(?! (o |a )?(ir|imposto\w*|darf|iof|taxas?|tributos?)\b)'
           # a forma curta, no presente: "a OPEP corta?", "o Copom sobe?"
           r'|(^|[.?!;:] |\b(e|mas) )(a |o )?(opep|opec|copom|bc|banco central)\+? (corta|cortam|mantem|sobe|eleva|aumenta|reduz|baixa)'
           r'( (a |os )?(producao|juros|selic|taxa))?\W*$'
           # o presente com prazo, na mesma oração ("a Petrobras reajusta semana que vem?", "o Copom corta essa semana?");
           # "o Copom mantém a Selic, como o dólar reagiu essa semana?" fica de fora
           rf'|\b(corta|cortam|mantem|segura|eleva|aumenta|baixa|reduz|sobe|reajusta|reajustam)\b[^,.?!;]{{0,30}}\b{PRAZO_DECISAO}\b'
           # "sai reajuste?", "será que sai reajuste?", e o "sai/vem/tem" com prazo ("tem reajuste essa semana?", "vem
           # aumento por aí?"). "Quando sai reajuste, o que acontece?" e "tem aumento de imposto em 2026?" ficam de fora.
           r'|(^|[.?!] |\bsera que )(sai|vem)( \w+){0,2} (reajustes?|aumentos?|cortes?|reducao|reducoes)\b'
           rf'|\b(sai|vem|tem)( \w+){{0,2}} (reajustes?|aumentos?|cortes?|reducao|reducoes)\b'
           # o aumento do imposto ("tem aumento de IOF no próximo ano?") é regra (P5); "tem corte da taxa Selic?" não
           r'(?! (de|do|da|no|na) (iof|ir|irpf|impostos?|aliquotas?|tribut\w*|isenc\w*|taxas? de (custodia|corretagem'
           r'|administracao)|custodia|corretagem|emolumentos?|come-?cotas)\b(?![^,.?!;]*\b(e|ou)\b))'
           rf'[^,.?!;]{{0,40}}'
           rf'\b({PRAZO_DECISAO[1:-1]}|por ai|em breve)\b'
           # "vem aumento de gasolina aí?", "o diesel baixa?", "será que a OPEP corta a produção?": a decisão que ainda vem.
           # Sem artigo depois de "vem" ("de onde vem a alta do dólar?") e até 3 palavras depois de "será que".
           r'|\bvem (ai )?(um |uma |mais )?(novo |nova )?(aumento|reajuste|corte|reducao)\b'
           r'|^(sera que )?(a |o )?(petrobras|gasolina|diesel|etanol|combustivel)\+? (corta|mantem|sobe|aumenta|reduz|baixa|reajusta)'
           r'( (a |o |os )?(gasolina|diesel|combustive(l|is)|preco))?\W*$'
           rf'|\bsera que (\S+ ){{0,3}}({VERBO_DECISAO})\b'
           # "a OPEP decide cortar em dezembro?"
           r'|\b(decide|decidem|vai decidir|vao decidir)( \w+)? (cortar|manter|aumentar|reduzir|reajustar|elevar|baixar)\b'
           # a próxima decisão de preço sem data marcada ("quando sai o próximo reajuste da gasolina?", "reajuste do diesel sai
           # quando?", "tem aumento de gasolina vindo?"). "Quando sai reajuste, o que acontece?", "a próxima reunião de corte"
           # e o imposto ("quando sai o novo aumento do IOF?") ficam de fora.
           rf'|\bquando (sai|vem|e|tem)( o| a| um| uma)? (proxim[oa]|nov[oa])( (?!reuni|decis)\w+){{0,2}} (reajustes?|aumentos?'
           rf'|cortes?)\b{SEM_IMPOSTO}'
           rf'|\b(reajustes?|aumentos?|cortes?)\b{SEM_IMPOSTO}( d[aoe] \w+)? (sai|vem) quando\b(?! \w)'
           rf'|\b(tem|vem)( \w+){{0,2}} (reajustes?|aumentos?|cortes?)\b{SEM_IMPOSTO}( d[aoe] \w+)? (vindo|chegando)\b')
# Com empresa citada, o "pagar" que vem só é regra com imposto, IR, IOF, DARF, tributo, come-cotas ou taxa nomeada do
# fundo: "a petrobras vai pagar mais que a selic?" e "a petrobras vai pagar taxa de dividendo alta?" são projeção de
# dividendo de emissor determinado (N2; Mapa legal, seção 8, item 10). "A Vale" com artigo, para não pegar "vale a pena".
EMPRESA_CITADA = rf'\b{EMPRESA_SEM_VALE}\b|\b(a|da|na|pela) vale\b'
PAGAR_EMPRESA = (r'\b(vai|vao|ira|irao|deve|devem|pode|podem)( \w+){0,2} pagar\b(?!( \w+){0,2} (impostos?|ir|irpf|iof|darf'
                 r'|tributos?|come-?cotas|taxas? de (administracao|custodia|corretagem|performance))\b)')
# O verbo no presente com uma data que ainda vem ("a Petrobras reajusta a gasolina essa semana?", "a OPEP corta em
# dezembro?"): passa pelo filtro do PASSADO, como o DECISAO_OU ("historicamente a OPEP corta em dezembro?" é passado).
MARCA_DATA = (r'mes que vem|ano que vem|(essa|esta|nessa|nesta) semana|(esse|este|nesse|neste) (mes|ano)'
              r'|(em|de) (janeiro|fevereiro|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)'
              r'(?! de (19|20)\d\d)|na reuniao de \w+|domingo|sabado|(segunda|terca|quarta|quinta|sexta)( |-)?feira'
              r'|(na|no|nesta|nessa) (segunda|terca|quarta|quinta|sexta)\b')
# "por que a gasolina aumenta em janeiro?" pede a explicação, não a decisão que vem
EXPLICA_POR_QUE = r'\b(por que|porque|pq|por causa d\w*)\b'
DECISAO_DATA = rf'\b({VERBO_DECISAO})\b.{{0,30}}\b({MARCA_DATA})\b'
# "Corta ou mantém?", "corte ou manutenção?": pode ser a decisão de amanhã ou a de ontem, então passa pelo filtro do PASSADO.
DECISAO_OU = (r'\b(corta|cortam|mantem|segura|eleva|aumenta|baixa|reduz|sobe)\b.{0,20}\bou (corta|cortam|mantem|segura'
              r'|eleva|aumenta|baixa|reduz|sobe|para|nao)\b'
              r'|\b(corte|manutencao)\b.{0,15}\bou (corte|manutencao|alta|elevacao|aumento|reducao|pausa)\b'
              r'|\b(alta|elevacao|aumento|reducao|pausa)\b.{0,15}\bou (corte|manutencao)\b')
# O lucro e o dividendo de uma empresa que ainda vão sair são projeção (N2): "Lucro da Petrobras no 3T26 vem forte?",
# "Dividendo da Petrobras em novembro vai ser grande?". O lucro da empresa não é a chance de a pessoa ganhar dinheiro.
LUCRO_EMPRESA = (rf'\b(lucros?|prejuizos?|balancos?|resultados?) (\w+ )?(d[aoe]s? )?(?!vale\b){EMPRESA}\b'
                 rf'|\b(lucros?|prejuizos?|balancos?|resultados?) (\w+ )?d[aoe]s? vale\b|\b(?!vale\b){EMPRESA}( \w+){{0,3}} lucr\w*')
PRIMEIRA_PESSOA = r'\b(eu|vou|meu|minha|meus|minhas|mim|consigo)\b'
# "a gente pode lucrar?", "quem pode lucrar com mini-índice?" é a própria pessoa, dita de forma impessoal: chance_dinheiro
PESSOA_QUE_LUCRA = (r'\b(eu|vou|a gente|agente|quem|da (pra|para)|as pessoas|alguem|todo mundo|(o |um )?(pequeno )?investidor(es)?'
                    r'|iniciantes?|traders?)\b')
# "de onde vem o lucro?", "vem do pré-sal" e "vem caindo" não são o que vem
VEM = r'(?<!onde )\bvem\b(?! (d[aeo]s?|da onde|\w+ndo)\b)'
# "o lucro vai ser divulgado quando?" é a data, que o calendário responde
LUCRO_QUE_VEM = (VEM + r'|\b(vira|virao|sera|serao)\b|\b(vai|vao|deve|devem|pode|podem|tende a|tendem a) (ser\b(?! (divulgad|publicad'
                 r'|anunciad|apresentad)\w*)|vir|ter|sair|crescer|cair|subir|bater|ficar|melhorar|piorar|surpreender|decepcionar)\b')
# "lucro da Petrobras no próximo trimestre?" é projeção; "quando sai o próximo balanço?" é a data, que o calendário
# responde, a não ser que a pergunta também julgue o resultado ("quando sai o próximo balanço, forte ou fraco?").
PROXIMO_RESULTADO = r'\bproxim\w* (trimestre|balanco|resultado)\b'
PEDE_DATA = r'\b(quando|que dia|(qual|que) (e )?(a )?data|data d[oa]s?|divulg\w*|public\w*|calendario)\b'
JUIZO_RESULTADO = (r'\b(forte|fraco|bo[ma]|ruim|grande|recorde|positiv\w*|negativ\w*|cresc\w*|cai|cair|sobe|subir'
                   r'|melhor\w*|pior\w*|maior|menor|alt[oa]|baix[oa])\b')
DIVIDENDO = r'\b(dividendos?|proventos?|jcp|dividend yield|dy)\b'
DIVIDENDO_FUTURO = (VEM + r'|\b(vai|vao|deve|devem) (ser|sair|vir|cair|subir|crescer|aumentar|diminuir|distribuir|pagar|anunciar'
                    r'|aprovar|ter|haver)\b|\b(vira|virao|sai|saem|saira|sairao|sera|serao|tera|havera)\b|\bproxim\w*'
                    r'|\b(esse|este|neste|nesse) ano\b'
                    # o presente com data que ainda vem ("a Petrobras paga dividendo em dezembro?"); "historicamente" e
                    # "costuma pagar" ficam de fora
                    rf'|^(?!.*\b(historicamente|no passado)\b).*\bpaga(m)?\b[^.?!]{{0,40}}\b({MARCA_DATA})\b')
DIVIDENDO_PASSADO = (r'\b(pagou|pagaram|distribuiu|distribuiram|anunciou|anunciaram|aprovou|aprovaram|saiu|sairam|veio|vieram'
                     r'|teve|tiveram|reagiu|reagiram|aconteceu|aconteceram|foi|foram|mexeu)\b')
# Como o dividendo anda (data com, data ex, prazo até cair na conta) é conceito (P5), não previsão: "o dividendo sai na
# data com ou na data ex?", "o dividendo será creditado em quantos dias?".
DIVIDENDO_MECANICA = r'\b(data (com|ex)|quantos dias|quanto tempo|prazo|creditad\w*|cai na conta|como funciona)\b'
# Mas se vai ter, quanto, qual (o próximo, o desse ano, o extraordinário, o de uma empresa) continua previsão de emissor.
DIVIDENDO_QUAL = (VEM + rf'|\b{EMPRESA}\b|\bproxim\w*|\b(esse|este|neste|nesse) ano\b|\b({MARCA_DATA})\b|\b(tera|havera)\b'
                  r'|\btem (dividendos?|proventos?|jcp)\b|\b(vai|vao|deve|devem) (vir|subir|crescer|aumentar|diminuir|distribuir'
                  r'|pagar|anunciar|aprovar|ter|haver|cair(?! na conta)|ser (grande|alto|baixo|bom|maior|menor|de))\b'
                  r'|\b(grande|alto|baixo|maior|menor|extraordinari\w*|valor|quanto(?! tempo))\b')
# A pergunta de imposto sobre dividendo é regra (P5), não previsão.
DIVIDENDO_REGRA = r'\b(imposto|tribut\w*|tax(a|ad)\w*|aliquota|isen\w*|irpf|ir|declar\w*|lei)\b'
# Pedir a análise ou o juízo sobre uma empresa ("analisa a PETR4", "Petrobras é uma boa empresa?", "PETR4 é segura?",
# "tem fundamento?") é pedir relatório de análise (Res. CVM 20): vai para a direção, como "PETR4 tá barata?".
# "como se analisa uma empresa como a Petrobras?" e "o que um analista avalia?" são conceito (P5); "quem analisa" e "a CVM
# avalia" são de terceiro.
AVALIA_EMPRESA = (r'(?<!\bcomo se )(?<!\bcomo )(?<!\bcomo eu )(?<!\banalista )(?<!\bquem )(?<!\bcvm )'
                  rf'\b(analis(a|e|ar|aria)|avali(a|e|ar|aria)|avaliacao)\b(?! de risco\b)[^.?!]{{0,25}}\b{EMPRESA}\b'
                  # "é uma boa empresa pra trabalhar?" é emprego, não o papel
                  rf'|\b{EMPRESA}\b[^.?!]{{0,25}}\b(e|seria|ta|esta) (uma )?(boa|otima) (empresa|acao|compra)\b'
                  r'(?! (pra|para) (trabalhar|estagiar|estagio)\b)'
                  rf'|\b{EMPRESA}\b[^.?!]{{0,25}}\b(e|seria|ta|esta) (uma )?(acao |empresa |papel )?(segur[ao]|solid[ao]|confiavel'
                  r'|arriscad[ao])\b'
                  rf'|\b{EMPRESA}\b[^.?!]{{0,25}}\btem (bons )?fundamentos?\b|\bfundamentos? d[ao] {EMPRESA}\b')
MULTIPLO = r'\b(p ?/ ?l|multiplos?)\b[^.?!]{0,30}\b(alto|baixo|muito|pouco|caro|barato|atrativ\w*|bom|ruim)\b'
# A decisão é de juros (ou de preço) quando a pergunta cita um mercado, o Copom, o BC, a taxa ou o corte, ou é curta.
SOBRE_JUROS = r'\b(copom|bc|banco central|taxas?|cortes?|reuniao|reunioes)\b'

# Comentário de pregão (N6): só quando a pergunta cita um contrato (WIN, WDO, DI, mini) e o pregão ("agora", "neste
# momento") ou o movimento em curso ("está caindo"). Os mercados mini_indice e mini_dolar também contam como contrato.
CONTRATO = r'\bwdo[fghjkmnquvxz]\d\d\b|\bdi1?\b|\bdi1[fghjkmnquvxz]\d\d\b|\bdi futuro\b|\bdolar futuro\b'
HORA = r'\bagora\b|\bneste momento\b|\bhoje no pregao\b|\bao vivo\b'
EM_CURSO = r'\b(esta|estao|ta|tao|segue|seguem|continua|continuam)( \w+)? (despencando|disparando|caindo|subindo|derretendo)\b'
# Sem contrato, "agora" com ordem é pedido de momento ("compro agora?") e com movimento é de direção ("a bolsa está
# caindo agora"): a recusa continua, com a linha certa, e sem falar de contrato.
ORDEM = r'\b(entro|compro|vendo|opero|zero|troco|trago|mando|envio|converto|transfiro)\b'
MOVIMENTO = r'\b(despencando|disparando|caindo|subindo|derretendo)\b'
VOTO_INFORMADO = (r'\b(eu )?vot(o|ei|arei|aria|ando) (\d+|no|na|em)\b|\bsou (\w+ )?(petista|bolsonarista|lulista|de direita|'
                  r'de esquerda|progressista)\b|\bodeio (o |a )?(pt|pl|lula|flavio|bolsonaro|esquerda|direita)\b|\b(o )?mito\b'
                  r'|\bfiz o l\b|\beu apoio\b|\btorco (pelo|pela|pro|para o)\b')
# Pedido de alocação, que a conta neutra (P4) nunca apaga.
ALOCACAO = (r'\bquanto (eu )?(coloco|ponho|invisto|aplico|boto|devia ter|deveria ter)\b|\bquantos contratos\b|\bquanto investir\b'
            r'|\br\$ ?\d|\b\d+ ?mil\b|\b\d+ ?k\b|\btenho \d')
CANDIDATO_OU_VITORIA = r'\b(flavio|bolsonaro|lula|vence|vencer|ganha|ganhar|reeleit\w*|favorit\w*|eurasia|frente)\b'
# A chance do candidato sem ganhar dinheiro ("quais as chances do lula ganhar?") não é a chance de a pessoa ganhar dinheiro.
GANHO_DELA = r'\bganha(r)? (dinheiro|grana)\b|\blucr\w*|\bficar rico\b|\benriquec\w*|\bganho\b'

# P4 de câmbio: o dinheiro em moeda estrangeira que a pessoa contou e o gasto por mês, só para a conta (nunca para dizer
# o que fazer). "150 mil euros", "€150.000", "150k euros", "US$ 20 mil", "20 mil dólares"; "gasto 5 mil reais por mês".
MOEDA = {'euro': r'euros?|eur', 'dolar': r'dolares|dolar|dollars?|usd|us\$|u\$'}
# Antes do número, só o símbolo ou o código ("€" vira "euros" no normalizar): "o euro 2 dias depois" não é dinheiro.
MOEDA_ANTES = r'euros|eur|usd|us\$|u\$'
_NUM = r'(?<![\d.,])(\d[\d.,]{0,15})'
_MULT = r'(?: ?(mil|k|milhao|milhoes|mi)\b)?'
# Depois do número, o que não é quantia de dinheiro: "2 dias", "1o turno", "3%", "5 pontos", "3 vezes".
_NAO_QUANTIA = r'(?!\s*(%|o turno|a reuniao|dias?\b|anos?\b|mes\b|meses\b|vezes\b|semanas?\b|horas?\b|pontos?\b|turnos?\b))'
# "R$ 100 mil em euros" é real, não euro: o número logo depois de "r$" nunca é moeda estrangeira.
VALOR_DEPOIS = re.compile(r'(?<!r\$)(?<!r\$ )' + _NUM + _MULT + r' ?(?:de |em )?(' + '|'.join(MOEDA.values()) + r')(?![\w$])')
VALOR_ANTES = re.compile(r'(?<![\w$])(' + MOEDA_ANTES + r') ?' + _NUM + _MULT + _NAO_QUANTIA)
POR_MES = r'(por mes|ao mes|mensais|mensal|todo mes|cada mes|/ ?mes|a month|per month|monthly)\b'
# O gasto precisa de verbo de gasto antes ("gasto", "pago", "custa", "aluguel"): "rendendo 1% ao mês" e "ganho 10 mil
# por mês" não são gasto (renda é dado que o agente não usa, N5).
GASTO_DEPOIS = re.compile(r'\b(gast\w*|pag\w*|cust\w*|despes\w*|aluguel|mensalidade|preciso de|vivo com|uso|tiro|saco|spend\w*|pay\w*)\b'
                          r'[^.!?\d]{0,25}?(?:r\$ ?)?' + _NUM + _MULT + r'(?!\s*%)(?: ?(reais|' + '|'.join(MOEDA.values())
                          + r'))?[^.\d!?%]{0,25}?\b' + POR_MES)
GASTO_ANTES = re.compile(r'\b(mensalidade|gasto mensal|custo mensal|despesa mensal)( (de|e|eh))? (?:r\$ ?)?' + _NUM + _MULT
                         + r'(?: ?(reais|' + '|'.join(MOEDA.values()) + r'))?')
# Mover o dinheiro de lugar: quando, se e quanto mover é o que o agente não diz (N1, N4, N5).
# Sem "traz" (3ª pessoa: "o que a eleição traz para o dólar depois?") e sem "passo" ("passo a passo").
TROCA = (r'(trago|trazer|troco|trocar|converto|converter|mando|mandar|envio|enviar|transfiro|transferir|remeto|remeter|'
         r'traer\w*|cambiar|bring|convert|exchange|move)')
EVENTO = r'(o |a |do |da |de |the )?(segundo turno|2o turno|primeiro turno|turno|eleicao|election|domingo|copom|reuniao|resultado)'
# Quando mover: "troco hoje?", "trago depois do 2º turno?", "antes ou depois?", "qual o melhor momento pra trocar?".
MOMENTO_TROCA = (r'\b' + TROCA + r'\b[^.?!]{0,40}\b(agora|ahora|antes|depois|hoje|ja|amanha|now|before|after)\b'
                 r'|\b(quando|cuando|hoje|agora|ahora|antes|depois)\b[^.?!]{0,20}\b(troco|trocar|trago|trazer|traer\w*|mando|mandar'
                 r'|envio|enviar|converto|converter|transfiro|transferir|cambiar|cambio a)\b'
                 r'|\b(antes|depois|before|after) ' + EVENTO + r'\b[^.?!]{0,20}\bou (espero|esperar|depois|antes|nao)\b'
                 r'|\bantes ou depois\b|\bagora ou (depois|espero|mais tarde)\b|\bou espero\b'
                 r'|\b(momento|hora|dia|epoca|data)\b[^.?!]{0,20}\b(trocar|trazer|converter|mandar|enviar|transferir|cambiar)\b')
# Quanto mover, ou que parte: alocação (N5). Aí o valor não entra na conta, e vale a recusa do capital.
QUANTO_TROCAR = (r'\bquanto (\w+ ){0,4}?(coloco|ponho|invisto|aplico|boto|trago|troco|converto|mando|envio|remeto|mantenho|'
                 r'deixo|tiro|passo|devia|deveria|trazer|trocar|converter|mandar|enviar|remeter|manter|deixar|tirar|passar)\b'
                 r'|\bquanto investir\b|\bquantos contratos\b|\b(que|qual|quanto) (parte|porcentagem|percentual|fatia|pedaco)\b'
                 r'|\bquanto disso\b|\b(' + TROCA[1:-1] + r'|deixo|mantenho)\b[^.?!]{0,25}\b(tudo|metade|um terco|uma parte|parte'
                 r'|o resto|aos poucos|de uma vez|em (parcelas|etapas)|\d+ ?%|half|all)\b'
                 r'|\b(tudo|metade|parte) ou (tudo|metade|parte|nada)\b|\bhow much\b|\b(what|which) (part|portion|percentage|share)\b'
                 r'|\ball or (half|part)\b')
MULTIPLICA = {'mil': 1e3, 'k': 1e3, 'milhao': 1e6, 'milhoes': 1e6, 'mi': 1e6}
# Em pergunta de petróleo, "100 dólares" é o preço do barril, não o dinheiro da pessoa, a não ser que ela diga que tem.
PRECO_EM_DOLAR = r'(us\$|u\$|usd) ?\d[\d.,]*( ?(mil|k))?|\d[\d.,]*( ?(mil|k))? ?(de )?(dolares|dolar|dollars?|usd)\b'
POSSE = r'\b(tenho|guardei|guardo|juntei|economizei|poupei|meus|minhas|recebi|ganhei)\b'
# Pôr o dinheiro num mercado ("invisto em petróleo?", "compro ações da Petrobras com isso?"). Sem "compra" (substantivo):
# "poder de compra" é câmbio.
INVESTE = (r'\b((re)?invisto|investir|investiria|aplico|aplicar|aplicaria|compro|comprar|compraria|coloco|colocar|ponho'
           r'|boto|botar|que tal)\b')
# O preço do barril ou do litro em moeda estrangeira ("o Brent a 100 dólares", "90 dólares o barril") sai do texto antes de
# achar o dinheiro da pessoa (_so_o_dinheiro_dela).
_DINHEIRO = (r'(?:(?:euros|eur|usd|us\$|u\$) ?\d[\d.,]*(?: ?(?:mil|k|milhao|milhoes|mi)\b)?'
             r'|\d[\d.,]*(?: ?(?:mil|k|milhao|milhoes|mi)\b)? ?(?:de |em )?(?:euros?|eur|dolares|dolar|dollars?|usd|us\$|u\$)(?![\w$]))')
PRECO_DO_BARRIL = (r'\b(?:petroleo|brent|wti|barril|barris|opep|opec|gasolina|diesel|etanol|combustive(?:l|is)|litro)\b'
                   r'(?: (?:a|de|em|por|o|esta|ta|foi|vai|passou|passa|passar|bateu|bater|chegou|chega|chegar|acima|abaixo'
                   r'|perto|caiu|cai|subiu|sobe|custa|custava|custando|cotado|para|pra))* ?' + _DINHEIRO
                   + r'|' + _DINHEIRO + r' (?:o |no |na |por |cada |do |de |a |per |the )?(?:barril|barris|litros?|galao|barrel|liter'
                   r'|gallon)\b')
# O preço da cripto em moeda estrangeira ("o bitcoin passou de 100 mil dólares?", "quando o bitcoin bateu 100 mil
# dólares?") não é o dinheiro da pessoa; o que é dela ("meu bitcoin chegou a 10 mil dólares", "comprei bitcoin a 10 mil
# dólares") continua.
PRECO_DA_CRIPTO = (r'(?<!\bmeu )(?<!\bmeus )(?<!\bminha )(?<!\bminhas )(?<!\bmy )\b(?:bitcoins?|btc|ether(?:eum)?|eth|solana)\b'
                   r'(?: (?:ja|nunca|nao|so|em (?:19|20)\d\d))*'
                   r'(?: (?:esta|ta|tava|estava|foi|era|vai|passou|passa|passar|passava|bateu|bate|bater|batia|chegou|chega|chegar'
                   r'|chegava|caiu|cai|subiu|sobe|custa|custava|custou|cotado|valia|voltou|acima|abaixo|perto))+'
                   r'(?: (?:de|a|ao|aos|os|em|para|pra|dos|casa dos))* ?' + _DINHEIRO)
# Valor em reais que é preço ou fato ("dividendo de R$ 6,73 por ação", "os R$ 20 bilhões", "a gasolina a R$ 6,53"), não o
# dinheiro da pessoa: não é capital.
PRECO_OU_FATO = (ALVO_NUM + r'|r\$ ?\d[\d.,]*( ?(mil|mi|bi|bilh\w*|milh\w*))? por (acao|litro|barril)\b'
                 r'|r\$ ?\d[\d.,]* ?(bi|bilh\w*)\b|r\$ ?\d[\d.,]* ?milh\w* (de|em) (dividendo|lucro|juros)\w*'
                 # o preço unitário: sem "mil" nem 4 dígitos, que é o dinheiro da pessoa ("recebi dividendos de R$ 5 mil",
                 # "tenho uma ação de R$ 10 mil"). O dividendo por ação já vem pelo "por ação" do 1º ramo.
                 # o preço dito com verbo ("a gasolina está R$ 6,53?", "subiu pra R$ 7", "o barril em reais passou de R$ 600")
                 r'|\b(gasolina|diesel|etanol|dolar|euro|barril|litro|acao|petr[34]|petrobras)( em reais)? (a|de|em|por|chegou a'
                 r'|chegou em|bateu|custa\w*|esta|ta|esta a|ta a|foi a|foi de|passou de|passa de|subiu|caiu|subiu (pra|para|a)'
                 r'|caiu (pra|para|a)|pagou( dividendos?)?( de)?) r\$ ?'
                 r'(?![\d.,]* ?(mil|mi|milh\w*|k)\b|\d{4}|\d{1,3}\.\d{3})\d[\d.,]*')
# O valor é dinheiro da pessoa quando ela diz que é dela ou pergunta onde pôr: aí o PRECO_OU_FATO não apaga o capital.
ALOCACAO_REAIS = r'\b(coloco|ponho|boto|invisto|aplico|reinvisto|reinvesto|reinvestir|reinvestiria)\b'
# A posse vale na oração do valor e sem palavra de preço entre as duas ("tenho uma dúvida, o dólar chegou a R$ 6,30?",
# "meus pais dizem que a gasolina custava R$ 2" não são dinheiro dela).
PALAVRA_DE_PRECO = r'\b(gasolina|diesel|etanol|dolar|euro|barril|litro|acao|petr[34]|petrobras|bitcoin)\b'
# Em pergunta de petróleo, o dinheiro em moeda estrangeira só é da pessoa quando ela diz que tem, que leva, que quer
# trazer ou converter, ou que está na conta; o resto é preço ("tenho uma dúvida: o petróleo passou de 100 dólares?"). A
# posse vale na mesma oração do número e sem palavra de petróleo entre as duas ("meus amigos dizem que o barril...").
OLEO = r'\b(petroleo|brent|wti|barril|barris|opep|opec)\b'
POSSE_ANTES = (POSSE + r"|\b(levo|levar|levando|to com|tou com|estou com|fiquei com|i have|i've got)\b"
               r'|^\W*com\b|\b(viaj\w*|vou|indo|estou|to|fico|ficar|volto|voltar|chego|chegar)\b[^.?!,;:]{0,15}\bcom\b'
               r'|\b(trazer|mandar|trocar|converter|enviar|transferir|remeter|trago|mando|troco|converto|envio|transfiro|remeto)\b')
# O verbo sem pessoa ("trazer", "levar", "voltar com") depois do petróleo tem o petróleo como sujeito ("o petróleo pode
# trazer 10 dólares de alta?", "a OPEP pode levar o preço a 90 dólares?"): só é da pessoa com ela entre os dois ("com o
# petróleo subindo, quero trazer", "o petróleo mexe se eu trazer").
POSSE_SEM_PESSOA = r'(levar|levando|trazer|mandar|trocar|converter|enviar|transferir|remeter|viaj(ar|ando)|indo|ficar|voltar|chegar)\b'
PESSOA = r'\b(eu|a gente|quero|queria|vou|vamos|preciso|precisava|pretendo|tenho|posso|consigo|gostaria)\b'
# "100 dólares dão quantos reais?", "viram quanto?" também são conversão
CONVERSAO = (r'\b(em|pra|para|pro) (o )?(real|reais)\b|\bquantos reais\b|\b(viram|vira|da|dao|e|sao) quantos?( reais)?\b'
             r'|\bviram quanto\b|\bconvert\w*|\bquanto (vale|valem|e|da|dao|sao|fica|ficam|seria|seriam)\b')
NA_CONTA = r'(?: (?:parad|guardad)[oa]s?)? (?:na|em) (?:minha |uma )?conta\b'
# O dinheiro que a pessoa tem ou leva, com o prazo da viagem ("tenho 2 mil dólares pra viagem do ano que vem, quanto dá em
# reais?"), não é nível com prazo: sai do texto do FUTURO. Fica quando a pergunta é o valor que ainda vem ("quanto valem meus
# 2 mil dólares no ano que vem?", "vai dar quanto?") e quando o número vem logo depois do verbo de nível ("tenho medo de o
# dólar chegar a 6 dólares até o fim do ano").
VALOR_QUE_VEM = (r'\b(quanto|vale|valem|valer|valeria|valeriam)\b[^.?!,;:]{0,40}(' + PRAZO
                 + r'|\bate la\b|\b(nessa|naquela|na) (epoca|data|altura)\b)'
                 r'|(' + PRAZO + r')[^.?!,;:]{0,20}\b(quanto|vale|valem|valer)\b'
                 r'|\b(vai|vao|ira|irao|iria|iriam) (dar|valer|virar|render|ficar|ser)\b'
                 r'|\b(dara|darao|daria|dariam|valera|valerao|valeria|valeriam|viraria|virariam)\b')
ANTES_DO_NIVEL = (r'(?:\b(?:a|em|to|at|passa\w* (?:de|dos|das)|(?:sai|vai) de)(?: us\$| r\$| \$|\$)?|' + NIVEL_VERBO
                  + r')\s*$')


def _moeda(rotulo: str | None) -> str | None:
    if not rotulo:
        return None
    if rotulo == 'reais':
        return 'real'
    return next(k for k, rx in MOEDA.items() if re.fullmatch(rx, rotulo))


def _quantia(numero: str, mult: str | None) -> float | None:
    """A quantia em qualquer formato que um brasileiro ou um estrangeiro escreve: '150.000' e '150,5' (Brasil), '50,000' e
    '1.5' (inglês, com até 2 casas depois do ponto), '1,5' + 'milhao' → 1.500.000. Número quebrado ('1,2,3') ou absurdo
    não vale. A pontuação colada no fim ("4.500," / "150.000.") não é parte do número."""
    numero = numero.rstrip('.,')
    if re.fullmatch(r'\d{1,3}(\.\d{3})+(,\d+)?', numero):  # 150.000 / 150.000,50
        texto = numero.replace('.', '').replace(',', '.')
    elif re.fullmatch(r'\d{1,3}(,\d{3})+(\.\d+)?', numero):  # 50,000 / 2,000.50
        texto = numero.replace(',', '')
    elif re.fullmatch(r'\d+,\d+', numero):  # 1,5
        texto = numero.replace(',', '.')
    elif re.fullmatch(r'\d+\.\d{1,2}', numero):  # 1.5 / 1.25
        texto = numero
    elif re.fullmatch(r'\d+', numero):
        texto = numero
    else:
        return None
    v = float(texto) * MULTIPLICA.get(mult or '', 1)
    return v if 0 < v < 1e10 else None


def cambio(t: str) -> tuple[float | None, str | None, float | None, str | None]:
    """(valor, moeda, gasto por mês, moeda do gasto) do texto já normalizado. O gasto sem moeda é em reais."""
    gasto = gasto_moeda = None
    g = GASTO_DEPOIS.search(t)
    if g:
        gasto, gasto_moeda = _quantia(g.group(2), g.group(3)), _moeda(g.group(4)) or 'real'
    else:
        g = GASTO_ANTES.search(t)
        if g:
            gasto, gasto_moeda = _quantia(g.group(4), g.group(5)), _moeda(g.group(6)) or 'real'
    if gasto is None:
        g = gasto_moeda = None
    # O valor é o 1º dinheiro em moeda estrangeira do texto que não seja o próprio gasto ("pago 3 mil dólares por mês").
    achados = sorted([(m.start(), m.group(1), m.group(2), m.group(3)) for m in VALOR_DEPOIS.finditer(t)]
                     + [(m.start(), m.group(2), m.group(3), m.group(1)) for m in VALOR_ANTES.finditer(t)])
    for inicio, numero, mult, rotulo in achados:
        if g and g.start() <= inicio < g.end():
            continue
        valor = _quantia(numero, mult)
        if valor is not None:
            return valor, _moeda(rotulo), gasto, gasto_moeda
    return None, None, gasto, gasto_moeda


# Os mercados que o histórico das eleições, do Copom e da linha do tempo mede.
MEDIDOS = ('ibovespa', 'dolar', 'juros')


@dataclass
class Pedido:
    pergunta: str
    mercados: list[str] = field(default_factory=list)
    candidatos: list[str] = field(default_factory=list)
    temas: list[str] = field(default_factory=list)
    proibidos: list[str] = field(default_factory=list)
    voto_informado: bool = False
    pontos: float | None = None
    contratos: int = 1
    valor_moeda: float | None = None  # P4 de câmbio: só para a conta; o registro nunca guarda (registro.py)
    moeda: str | None = None
    gasto_mensal: float | None = None
    gasto_moeda: str | None = None

    @property
    def eleicao(self) -> bool:
        return bool('eleicao' in self.temas or self.candidatos or {'chance_candidato', 'voto'} & set(self.proibidos))

    @property
    def conta(self) -> bool:
        return self.pontos is not None and bool({'mini_indice', 'mini_dolar'} & set(self.mercados))

    @property
    def conta_cambio(self) -> bool:
        return self.valor_moeda is not None and self.moeda in ('euro', 'dolar')

    @property
    def cambio(self) -> bool:
        """Pergunta de câmbio: fala de euro, ou contou dinheiro em moeda estrangeira."""
        return 'euro' in self.mercados or self.conta_cambio

    def somar(self, outro: 'Pedido') -> 'Pedido':
        """Junta duas leituras da mesma pergunta (a das palavras e a da IA): o que uma achou, vale."""
        junta = lambda a, b: a + [x for x in b if x not in a]  # noqa: E731
        proibidos = junta(self.proibidos, outro.proibidos)
        # A IA viu pedido de capital que as palavras não pegaram: vale a leitura dela, e a conta de câmbio sai (senão a
        # resposta diria "não uso o valor que você tem" e logo depois usaria).
        cambio_ = (self.valor_moeda, self.moeda, self.gasto_mensal, self.gasto_moeda)
        if 'capital' in proibidos:
            cambio_ = (None, None, None, None)
        return Pedido(self.pergunta, junta(self.mercados, outro.mercados), junta(self.candidatos, outro.candidatos),
                      junta(self.temas, outro.temas), proibidos, self.voto_informado or outro.voto_informado,
                      self.pontos if self.pontos is not None else outro.pontos, self.contratos, *cambio_)

    def resumo(self) -> str:
        partes = [f'mercados: {", ".join(self.mercados) or "nenhum"}', f'candidatos: {", ".join(self.candidatos) or "nenhum"}',
                  f'temas: {", ".join(self.temas) or "nenhum"}', f'pedidos que pedem recusa: {", ".join(self.proibidos) or "nenhum"}']
        if self.voto_informado:
            partes.append('a pessoa contou o próprio voto (não usar)')
        return '; '.join(partes)


def _numero(s: str) -> float:
    return float(s.replace('.', '').replace(',', '.'))


# - a regra e a agenda com "vai valer/custar/estar/ficar" ("quando a isenção de 20 mil vai valer?", "quanto vai custar o
#   IOF?", "a bolsa vai estar aberta no Natal?", "a OPEP vai estar reunida em dezembro?") não são o preço que ainda vem. A
#   taxa de juros e a de câmbio são preço; "quanto vai custar a gasolina com o imposto novo?", "quanto o dólar vai custar
#   com IOF?", "com o IOF o dólar vai ficar acima de 6?" e "o dólar vai estar fechado em alta?" continuam recusa.
VAI_SER = r'\b(vai|vao|va a|van a) (estar|valer|custar|ficar|ta)\b'
_REGRA = (r'(regras?|leis?|normas?|isencao|isent[oa]s?|impostos?|aliquotas?|iof|ir|irpf|tributos?|tarifas?|corretagem'
          r'|emolumentos?|custodia|come[- ]?cotas|taxas?(?! (de |do |da )?(selic|cambio|juros|basica|dolar|di|cdi|referencial)\b))')
# a regra antes do verbo é o sujeito, menos depois de "com/sem" ("com o IOF o dólar vai ficar acima de 6?")
REGRA_ANTES = (r'(?<!\bcom )(?<!\bsem )(?<!\bcom o )(?<!\bcom a )(?<!\bsem o )(?<!\bsem a )'
               rf'\b{_REGRA}\b[^.?!;:,]{{0,40}}$')
REGRA_DEPOIS = (rf'(( a| o| em)? (partir|vigor|vigente|valendo)\b|( o| a| os| as)? {_REGRA}\b'
                r'| (abert|fechad|reunid)[oa]s?\b(?! (em (alta|queda|baixa)|acima|abaixo|no (positivo|negativo|azul|vermelho))\b)'
                r'| (funcionando|em recesso|de recesso)\b)')
QUANTO = r'\b(quanto|qto|qnto|cuanto)\b'
# - o prazo numa oração com o movimento no pretérito ("o brent subiu de 60 a 115 até outubro?") ou com o Focus ("a cotação
#   do dólar esperada pelo Focus para o fim do ano") não é o prazo de uma previsão.
PRAZO_SEM_PREVISAO = MOVIMENTO_PASSADO + r'|\bfocus\b'


def _trecho(t: str, m: re.Match, corte: str) -> str:
    return re.split(corte, t[:m.start()])[-1] + m.group() + re.split(corte, t[m.end():])[0]


def _tira(t: str, alvo: str, marca: str, corte: str) -> str:
    """Tira cada `alvo` cujo trecho (a oração ou a frase, pelo `corte`) tem a `marca`."""
    return re.sub(alvo, lambda m: ' ' if re.search(marca, _trecho(t, m, corte)) else m.group(), t)


def _sem_regra_nem_agenda(t: str) -> str:
    """Tira o "vai valer/custar/estar/ficar" da regra e da agenda."""
    def troca(m: re.Match) -> str:
        antes, depois = re.split(ORACAO, t[:m.start()])[-1], t[m.end():]
        regra = (re.match(REGRA_DEPOIS, depois)
                 or re.search(REGRA_ANTES, antes) and not re.search(QUANTO, _trecho(t, m, ORACAO)))
        # com outro sujeito junto ("o IOF vai ficar em 3,5%, e o dólar?"), continua recusa
        return ' ' if regra and not re.search(COORDENA, _trecho(t, m, r'[?!]')) else m.group()
    return re.sub(VAI_SER, troca, t)


def _posse(oracao: str) -> list[int]:
    """Onde termina cada marca de posse da oração, menos o verbo sem pessoa que tem o petróleo de sujeito."""
    oleo = [x.start() for x in re.finditer(OLEO, oracao)]
    return [x.end() for x in re.finditer(POSSE_ANTES, oracao)
            if not (re.match(POSSE_SEM_PESSOA, x.group()) and oleo and oleo[0] < x.start()
                    and not re.search(PESSOA, oracao[max(o for o in oleo if o < x.start()):x.start()]))]


def _sem_o_dinheiro_dela(t: str) -> str:
    """Tira do texto do FUTURO o dinheiro que a pessoa diz que tem ou leva (posse na mesma oração)."""
    if re.search(VALOR_QUE_VEM, t):
        return t

    def troca(m: re.Match) -> str:
        antes = t[:m.start()]
        oracao = re.split(r'[?!;:]|\.(?!\d)|,(?!\d)', antes)[-1]
        dela = _posse(oracao) and not re.search(ANTES_DO_NIVEL, antes)
        return ' ' if dela else m.group()
    return re.sub(_DINHEIRO, troca, t)


def _texto_do_futuro(t: str) -> str:
    """O texto que o FUTURO lê: sem o "cara" que não é preço, sem o "descontado" de imposto e sem a regra de queda."""
    if re.search(DEFINICAO_VALUATION, t):
        return ''
    t = re.sub(CARA_NAO_PRECO, ' ', t)
    if re.search(BOMBA_EXPLICA, t) and not re.search(FUTURO_EXPLICITO, t) and not re.search(BOMBA_E_EMPRESA, t):
        t = re.sub(BOMBA_CARA, r'\1\2', t)
    t = re.sub(DESCONTO_NA_FONTE, ' ', t)
    if not re.search(rf'\b{EMPRESA}\b', t):
        t = re.sub(DESCONTO_NAO_PRECO, lambda m: m.group(0) if re.search(ADJUNTO_ANTES, m.string[:m.start()])
                   else re.sub(r'descontad[oa]s?\b', ' ', m.group(0)), t)
    if re.search(REGRA_DE_QUEDA, t):
        t = re.sub(PASSA_DE_PCT, ' ', t)
    if re.search(REGRA_CIRCUIT, t):
        t = re.sub(CAI_MAIS_PCT, ' ', t)
        t = re.sub(r'\bcircuit[ -]?breakers? (dispara\w*|aciona\w*|e acionado)\b', ' ', t)  # quem dispara é a regra
    t = _sem_regra_nem_agenda(t)

    def sem_regra(m: re.Match) -> str:
        frase = re.split(r'[?!]', t[:m.start()])[-1] + m.group() + re.split(r'[?!]', t[m.end():])[0]
        return m.group() if re.search(COORDENA, frase) else ' '
    t = re.sub(REGRA_FUTURA, sem_regra, t)
    t = _tira(t, PRAZO, PRAZO_SEM_PREVISAO, ORACAO)
    t = re.sub(VIAGEM, ' ', t)
    return _sem_o_dinheiro_dela(re.sub(INTERVALO, ' ', t))


def _so_o_dinheiro_dela(t: str) -> str:
    """Em pergunta de petróleo, o texto só com o dinheiro que é da pessoa: a posse na mesma oração e sem petróleo entre as
    duas, a conversão na mesma frase, "na conta" logo depois, ou o gasto por mês. O resto vira espaço."""
    gastos = [g.span() for g in (*GASTO_DEPOIS.finditer(t), *GASTO_ANTES.finditer(t))]

    def troca(m: re.Match) -> str:
        antes, depois = t[:m.start()], t[m.end():]
        oracao = re.split(r'[?!;:]|\.(?!\d)|,(?!\d)', antes)[-1]
        frase = re.split(r'[?!]|\.(?!\d)', antes)[-1] + m.group() + re.split(r'[?!]|\.(?!\d)', depois)[0]
        oleo = [x.start() for x in re.finditer(OLEO, oracao)]
        posse = _posse(oracao)
        dela = (bool(posse) and not (oleo and oleo[-1] > posse[-1]) or bool(re.match(NA_CONTA, depois))
                or bool(re.search(CONVERSAO, frase)) or any(a <= m.start() < b for a, b in gastos))
        return m.group() if dela else ' '
    return re.sub(_DINHEIRO, troca, t)


# A regra do imposto, da declaração, do FGC ou da custódia não é onde pôr o dinheiro (P5): o lugar do verbo é a declaração,
# o verbo está na oração do "se" e a pergunta é a regra, a guarda é dita e a pergunta é declarar, ou o que se guarda é a
# seed. Com "ou", motivo ("pra não pagar IR", "por causa do FGC"), "tudo" ou ganho continua dica.
_SEM_MOTIVO = r'(?:(?!\b(ou|pra|para|por causa|porque|ja que|antes|tudo|todo|toda|todos)\b)[^.?!,;])'
_SEM_GANHO = r'(?![^.?!]*\b(ganh\w*|rend\w*|lucr\w*|compens\w*|mais|menos|melhor|pior)\b)'
DECLARACAO_LUGAR = r'(declarac\w*|ficha|bens e direitos|irpf|imposto de renda)'
REGRA_IMPOSTO = (r'(\b(pago|pagaria|paga|pagar|tem|teria|incide|cobr\w*|recolh\w*|descont\w*)\b[^.?!]{0,20}'
                 r'\b(ir(?! (pra|para|ate|a|ao)\b)|iof|imposto\w*|darf|come[- ]cotas)\b'
                 r'|\b(isent\w*|fgc|declar\w*|aliquota\w*|tribut\w*|irpf)\b)')
REGRA_DO_VERBO = (
    rf'\b(onde (eu )?)?(coloco|ponho|boto|lanco|informo)\b{_SEM_MOTIVO}{{0,40}}\b(em|na|no|nas|nos)( (qual|que|a|o))?'
    rf' {DECLARACAO_LUGAR}\b'
    rf'|\b(em )?(qual|que) (ficha|grupo|codigo|campo|parte)\b{_SEM_MOTIVO}{{0,40}}\b(coloco|ponho|boto|lanco|informo)\b'
    rf'|\b(se|quando|caso)( eu)? (re)?(invisto|aplico|coloco|ponho|boto|deixo|guardo)\b{_SEM_MOTIVO}{{0,50}}[,;]'
    rf'(?=[^.?!]{{0,40}}{REGRA_IMPOSTO}){_SEM_GANHO}'
    rf'|(?<!onde )(?<!onde eu )\b(guardo|deixo)\b{_SEM_MOTIVO}{{0,50}}[,;]'
    rf'(?=[^.?!]{{0,30}}\b(declar\w*|imposto\w*|tribut\w*|isent\w*)\b){_SEM_GANHO}'
    r'|\b(guardo|deixo|anoto|coloco|ponho|boto)\b (a |as |o |os |minha |minhas |meu |meus )?(seed|senha\w*|chave\w*( privada)?'
    r'|frase\w*( de recuperacao| semente)?|palavras( de recuperacao)?|\d+ palavras|backup)\b')


def _valor_e_dela(t: str) -> bool:
    """O valor em reais é dinheiro da pessoa: ela pergunta onde pôr, ou diz que tem na mesma oração do valor."""
    if re.search(ALOCACAO_REAIS, t):
        return True
    for m in re.finditer(r'r\$ ?\d', t):
        oracao = re.split(r'[?!;:]|\.(?!\d)|,(?!\d)', t[:m.start()])[-1]
        posse = [x.end() for x in re.finditer(POSSE, oracao)]
        if posse and not re.search(PALAVRA_DE_PRECO, oracao[posse[-1]:]):
            return True
    return False


def _eliptica_do_passado(oracoes: list[str], i: int) -> bool:
    m = re.match(ELIPTICA, oracoes[i])
    if not m or (m.group(1) and not re.fullmatch(r'19\d\d|20[01]\d|202[0-5]', m.group(1))):
        return False
    j = next((j for j in range(i - 1, -1, -1) if oracoes[j].strip()), None)
    if j is None or re.search(rf'\b{EMPRESA}\b', oracoes[i] + ' ' + oracoes[j]):
        return False
    return bool(re.search(r'\b(barat|car)[oa]s?\b', oracoes[j])) and bool(
        re.search(PASSADO, oracoes[j]) or _eliptica_do_passado(oracoes, j))


def _oracao_marcada(oracoes: list[str], i: int, adverbio: bool) -> bool:
    """A oração tem marca de passado própria: o advérbio do trecho, o pretérito (sem verbo de pedido no presente depois
    dele), o ano que já passou numa oração sem verbo de pedido, ou a elipse do "ficou caro/barato" da anterior."""
    o = oracoes[i]
    if adverbio or re.search(PASSADO_DA_FRASE, o):
        return True
    if re.search(PASSADO_VERBAL + '.*' + VERBO_PEDIDO, re.sub(SUBORDINADA, '', o)):
        return False
    return bool(_passado_da_oracao(o) or re.search(MOVIMENTO_PASSADO, o)
                or re.search(ANO_PASSADO, o) and not re.search(VERBO_PEDIDO, o) or _eliptica_do_passado(oracoes, i))


def analisar(pergunta: str) -> Pedido:
    t = normalizar(pergunta)
    achou = lambda padroes, texto=t: [k for k, rx in padroes.items() if re.search(rx, texto)]  # noqa: E731
    # O presidente da Petrobras e o domingo da reunião da OPEP não são a eleição, a não ser que a pergunta cite a eleição
    # de outro jeito.
    t_eleicao = t
    if not re.search(ELEITORAL, re.sub(CARGO_ELEITO, ' ', t)):
        t_eleicao = re.sub(CARGO, ' ', re.sub(CARGO_ELEITO, ' ', t))
        if re.search(r'\b(petrobras|petr[34])\b', t):
            t_eleicao = re.sub(r'\bex[- ]?presidente( (jair )?bolsonaro\b)?', ' ', t_eleicao)
            if re.search(GOVERNO_BOLSONARO, t) or (re.search(GOVERNO_BOLSONARO_NOME, t) and not re.search(FUTURO, t)):
                t_eleicao = re.sub(r'\bbolsonaro\b', ' ', t_eleicao)
    if re.search(r'\b(opep|opec)\b', t):
        t_eleicao = re.sub(r'\bdomingo\b', ' ', t_eleicao)
    temas = [k for k, rx in TEMAS.items() if re.search(rx, t_eleicao if k == 'eleicao' else t)]
    p = Pedido(pergunta=pergunta, mercados=achou(MERCADOS, re.sub(GASOLINA_FIGURADA, ' ', t)),
               candidatos=achou(CANDIDATOS, t_eleicao), temas=temas,
               proibidos=achou(PROIBIDOS), voto_informado=bool(re.search(VOTO_INFORMADO, t)))
    # O preço, o fato e o alvo em reais não são o dinheiro da pessoa; o que ela diz que é dela ("recebi dividendos de R$ 50
    # mil, onde ponho?") continua capital (N5).
    if ('capital' in p.proibidos and not _valor_e_dela(t)
            and not re.search(PROIBIDOS['capital'], re.sub(PRECO_OU_FATO, ' ', t))):
        p.proibidos.remove('capital')
    # O momento que já passou não é pedido de entrada, a não ser que o resto da pergunta peça dica.
    # Só sai o trecho do momento que já passou: um "e hoje é bom momento?" depois dele continua dica (N1).
    if ('dica' in p.proibidos and re.search(MOMENTO_PASSADO, t)
            and not re.search(FUTURO_EXPLICITO + '|' + MOMENTO_PRA + r'|\be hoje\b', t)
            and not re.search(PROIBIDOS['dica'], re.sub(MOMENTO_PASSADO, ' ', t))):
        p.proibidos.remove('dica')
    # A viagem não é a entrada ("embarco semana que vem pra Lisboa com 2 mil euros, quanto dá em reais?" é a conta, P4).
    if 'dica' in p.proibidos and re.search(VIAGEM, t) and not re.search(PROIBIDOS['dica'], re.sub(VIAGEM, ' ', t)):
        p.proibidos.remove('dica')
    if ('dica' in p.proibidos and re.search(REGRA_DO_VERBO, t)
            and not re.search(PROIBIDOS['dica'], re.sub(REGRA_DO_VERBO, ' ', t))):
        p.proibidos.remove('dica')
    if p.voto_informado and 'eleicao' not in p.temas:
        p.temas.append('eleicao')
    # Conceito de derivativo (margem, ajuste diário, alavancagem): a explicação está no bloco do mini-índice.
    if re.search(r'\bmargem\b|\bajuste diario\b|\balavancagem\b', t) and not p.mercados:
        p.mercados.append('mini_indice')
    # Futuro de um preço: na dúvida, recusa. Vale com mercado, candidato, eleição, Copom ou pergunta curta ("sobe?").
    curta = len(t.split()) <= 4
    sobre_preco = bool(p.mercados or p.candidatos or {'eleicao', 'copom'} & set(p.temas) or curta)
    condicional = re.search(CONDICIONAL, t)
    t_futuro = _texto_do_futuro(t)
    futuro = re.search(FUTURO, t_futuro) or condicional
    # O passado só vale quando nenhuma oração pede o futuro sem uma marca de passado própria. A oração seguinte que pergunta
    # o que foi ("corta ou mantém, qual foi a decisão?") também é marca de passado.
    # O advérbio ("historicamente", "no passado") vale para a frase toda só quando no máximo um trecho pede ou se move; senão,
    # só para o próprio trecho. O "qual foi" da oração seguinte só vale para a decisão ("corta ou mantém, qual foi?").
    trechos = re.split(TRECHO, t_futuro)
    oracoes = [(o, bool(re.search(PASSADO_DA_FRASE, tr))) for tr in trechos for o in re.split(r'\b(?:e|mas)\b', tr)]
    pedem = lambda o: re.search(FUTURO, o) or re.search(DECISAO_OU, o)  # noqa: E731
    so_passado = re.search(PASSADO, t) and not condicional and not re.search(FUTURO_EXPLICITO, t) and (
        re.search(PASSADO_DA_FRASE, t) and sum(1 for tr in trechos if pedem(tr) or re.search(MOVIMENTO_PASSADO, tr)) <= 1
        or not any(
            pedem(o) and not _oracao_marcada([x for x, _ in oracoes], i, adv)
            and not (re.search(DECISAO_OU, o) and i + 1 < len(oracoes) and re.match(QUAL_FOI, oracoes[i + 1][0]))
            for i, (o, adv) in enumerate(oracoes)))
    # Decisão de juros que ainda vai sair ("vai cortar a Selic?", "corta ou mantém?") também é futuro de preço.
    decisao = bool(p.mercados or re.search(SOBRE_JUROS, t) or curta) and bool(
        re.search(DECISAO, t) or ((re.search(DECISAO_OU, t) or re.search(DECISAO_DATA, t) and not re.search(EXPLICA_POR_QUE, t))
                                  and not so_passado))
    # Lucro de uma empresa que ainda vai sair ("a Petrobras vai lucrar?", "o lucro da Petrobras vem forte?") é projeção; o
    # da pessoa é chance_dinheiro, que só sai quando a única palavra de lucro é a da empresa.
    lucro_empresa = bool(re.search(LUCRO_EMPRESA, t)) and not re.search(PRIMEIRA_PESSOA, t)
    if (lucro_empresa and 'chance_dinheiro' in p.proibidos
            and not re.search(PROIBIDOS['chance_dinheiro'], re.sub(LUCRO_EMPRESA, ' ', t))):
        p.proibidos.remove('chance_dinheiro')
    # "como a Petrobras pode lucrar com o pré-sal?" pede a explicação, não a projeção
    explica = re.search(r'\b(como|por que|porque)\b', t) and not re.search(r'\b(vai|vao)\b', t)
    lucro_futuro = ((re.search(r'\b(vai|vao|deve|devem|pode|podem)( \w+){0,2} lucr\w*', t)
                     or lucro_empresa and (re.search(LUCRO_QUE_VEM, t) or re.search(PROXIMO_RESULTADO, t) and not (
                         re.search(PEDE_DATA, t) and not re.search(JUIZO_RESULTADO, t) and not p.proibidos)))
                    and not re.search(PESSOA_QUE_LUCRA, t) and not explica)
    # O dividendo que ainda vai sair ("quanto a Petrobras paga de dividendo esse ano?") é previsão de emissor (N2).
    paga_empresa = bool(re.search(EMPRESA_CITADA, t) and re.search(PAGAR_EMPRESA, t))
    dividendo_futuro = paga_empresa or bool(
        re.search(DIVIDENDO, t) and re.search(DIVIDENDO_FUTURO, t) and not re.search(DIVIDENDO_PASSADO, t)
        and not re.search(DIVIDENDO_REGRA, t)
        and not (re.search(DIVIDENDO_MECANICA, t) and not re.search(DIVIDENDO_QUAL, t)))
    # O pedido de análise ou de juízo sobre uma empresa ("analisa a PETR4", "P/L 3 é muito?").
    avalia = re.search(AVALIA_EMPRESA, t) or re.search(rf'\b{EMPRESA}\b', t) and re.search(MULTIPLO, t)
    if ((sobre_preco and futuro and not so_passado or decisao or lucro_futuro or dividendo_futuro or avalia)
            and 'direcao' not in p.proibidos):
        p.proibidos.append('direcao')
    contrato = bool({'mini_indice', 'mini_dolar'} & set(p.mercados) or re.search(CONTRATO, t))
    hora = re.search(HORA, t)
    if contrato and (hora or re.search(EM_CURSO, t)):
        p.proibidos.append('ao_vivo')
    elif hora:
        if re.search(ORDEM, t) and 'momento' not in p.proibidos:
            p.proibidos.append('momento')
        if re.search(MOVIMENTO, t) and 'direcao' not in p.proibidos:
            p.proibidos.append('direcao')
    if 'voto' in p.proibidos and 'comparar' in p.proibidos:
        p.proibidos.remove('comparar')
    # Escolher entre empresas ("PETR4 ou PRIO3, qual é melhor?") é ranking (M2), não comparar classes de ativo (N5).
    # O mesmo entre tokens ("BTC ou ETH?", "bitcoin é mais seguro que ethereum?"): é indicar token (N7), não classe.
    if 'ranking' in p.proibidos and 'comparar' in p.proibidos and (
            re.search(rf'\b{EMPRESA}\b', t) or re.search(rf'\b{CRIPTO_NOME}\b.{{0,30}}\b{CRIPTO_NOME}\b', t)):
        p.proibidos.remove('comparar')
    if 'aposta' in p.proibidos and 'previsao' not in p.mercados:
        p.mercados.append('previsao')
    if 'binaria' in p.proibidos:
        p.mercados = [m for m in p.mercados if m != 'previsao']
    # "Quais as chances pro dólar" e "quais as chances de ganhar dinheiro com bitcoin?": é direção do mercado ou a chance da
    # pessoa, não chance de candidato.
    if ('chance_candidato' in p.proibidos and p.mercados
            and not re.search(CANDIDATO_OU_VITORIA, re.sub(r'\bganhar (dinheiro|grana)\b', ' ', t))):
        p.proibidos.remove('chance_candidato')
    if ('chance_candidato' in p.proibidos and 'chance_dinheiro' in p.proibidos and not p.mercados
            and not re.search(GANHO_DELA, t)):
        p.proibidos.remove('chance_dinheiro')
    if 'chance_candidato' in p.proibidos and 'eleicao' not in p.temas:
        p.temas.append('eleicao')
    # Conta neutra com os números do próprio usuário (P4): pontos e contratos.
    m = re.search(r'(?<![\d.,])(\d[\d.,]{0,15})\s*pontos?\b', t)
    if m:
        p.pontos = _numero(m.group(1))
        c = re.search(r'(?<![\d.,])(\d{1,6})\s*contratos?\b', t)
        p.contratos = int(c.group(1)) if c else 1
        if p.conta:
            # O número de contratos e de pontos que a pessoa escolheu não é pedido de alocação; "quanto eu coloco" é.
            if 'capital' in p.proibidos and not re.search(ALOCACAO, t):
                p.proibidos.remove('capital')
            if 'direcao' in p.proibidos and not re.search(r'\b(sobe|cai|vai|chance|probabilidad\w*|tendencia)\b', t):
                p.proibidos.remove('direcao')
            if 'dica' in p.proibidos and not re.search(r'\b(compr\w*|vend\w*|devo|vale|compens\w*|entrar|bora)\b', t):
                p.proibidos.remove('dica')
    # Quando mover o dinheiro de lugar ("troco hoje?", "trago depois do 2º turno?"): momento (N4) e a recusa padrão.
    momento_troca = bool(re.search(MOMENTO_TROCA, t))
    if momento_troca:
        for codigo in ('momento', 'dica'):
            if codigo not in p.proibidos:
                p.proibidos.append(codigo)
        if 'comparar' in p.proibidos:
            p.proibidos.remove('comparar')  # "antes ou depois de domingo" não compara classes de ativos
    quanto = bool(re.search(QUANTO_TROCAR, t))
    if quanto and 'capital' not in p.proibidos:
        p.proibidos.append('capital')
    # Conta neutra de câmbio com o dinheiro que a pessoa contou (P4): o valor em reais, quanto muda a cada R$ 0,10 e
    # quantos meses de gasto cobre. Não entra quando ela pergunta quanto mover (alocação, N5) nem quando mover (N4): ao
    # lado da reação nos turnos, o valor dela viraria indicação de momento. Pergunta de contrato (mini-dólar) também não.
    t_dinheiro = re.sub(ALVO_NUM, ' ', t)  # o alvo ("o ouro vai a 3000 dólares?") não é o dinheiro dela
    if 'cripto' in p.mercados:
        t_dinheiro = re.sub(PRECO_DA_CRIPTO, ' ', t_dinheiro)
    valor, moeda, gasto, gasto_moeda = cambio(t_dinheiro)
    sem_preco = t
    if 'petroleo' in p.mercados:
        # o 1º dinheiro dela que não é o preço do barril nem do litro ("o petróleo passou de 100 dólares?" não tem)
        sem_preco = _so_o_dinheiro_dela(re.sub(PRECO_DO_BARRIL, ' ', t_dinheiro))
        valor, moeda = cambio(sem_preco)[:2]
    # O dólar que só aparece no preço do barril ("o Brent a 100 dólares mexe nos meus 20 mil euros?") não é câmbio.
    if 'petroleo' in p.mercados and 'dolar' in p.mercados and not re.search(MERCADOS['dolar'], sem_preco):
        p.mercados.remove('dolar')
    contrato_futuro = bool({'mini_indice', 'mini_dolar'} & set(p.mercados) or re.search(CONTRATO, t))
    cripto = bool({'cripto', 'memecoin'} & set(p.mercados))  # "10 mil dólares em USDT" é cripto da pessoa, não câmbio
    # "10 mil euros em bitcoin": o euro é a unidade do valor, não o mercado da pergunta (como o dólar, em resposta.py). Fica
    # quando a pessoa fala em mover o dinheiro ("uso uma exchange pra trazer?", "trago agora ou compro bitcoin?"); trocar
    # euro por bitcoin não é câmbio.
    sem_troca_cripto = re.sub(r'\b(troco|trocar|converto|converter)\b[^.?!]{0,30}\b(por|em|pra|para) (bitcoins?|btc|cripto\w*'
                              r'|ether(eum)?|eth|solana)\b', ' ', re.sub(r'\bexchanges?\b', ' ', t))
    troca_dita = re.search(r'\b' + TROCA + r'\b', sem_troca_cripto) or re.search(CONVERSAO, t)
    if ('cripto' in p.mercados and 'euro' in p.mercados and not re.search(MOMENTO_TROCA, sem_troca_cripto) and not troca_dita
            and not re.search(MERCADOS['euro'], re.sub(_DINHEIRO, ' ', t))):
        p.mercados.remove('euro')
    # Pôr o dinheiro estrangeiro num mercado que não é câmbio ("invisto em petróleo?", "compro ações da Petrobras?") é
    # classe de ativo (N5): o valor não entra. "O petróleo mexe com isso?" e "trago o dinheiro?" seguem com a conta.
    # Comparar ou ranquear com o dinheiro dela ("20 mil dólares, petróleo ou bolsa?") é N5 nas letras; o pedido sobre a
    # empresa ("petr4 tá barata?", "petr4 vale a pena?") também, a não ser que a pergunta seja do câmbio ("a Petrobras
    # vai mexer no dólar?", "devo trazer?"): aí a conta fica junto da recusa.
    sem_o_dinheiro = re.sub(_DINHEIRO, ' ', t)
    do_cambio = bool(re.search(MERCADOS['dolar'] + '|' + MERCADOS['euro'] + rf'|\b{TROCA}\b', sem_o_dinheiro))
    investe = bool(set(p.mercados) - {'dolar', 'euro'}) and bool(
        re.search(INVESTE, t) or {'comparar', 'ranking'} & set(p.proibidos)
        or re.search(rf'\b{EMPRESA}\b', t) and {'dica', 'direcao'} & set(p.proibidos) and not do_cambio)
    if valor is not None and not contrato_futuro:
        if quanto or momento_troca or cripto or investe:
            if 'capital' not in p.proibidos:
                p.proibidos.append('capital')  # a pessoa contou o valor e ele não é usado: a linha do capital diz por quê
        else:
            p.valor_moeda, p.moeda, p.gasto_mensal, p.gasto_moeda = valor, moeda, gasto, gasto_moeda
            if moeda not in p.mercados:
                p.mercados.append(moeda)
            if 'capital' in p.proibidos:
                p.proibidos.remove('capital')
    return p

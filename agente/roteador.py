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
EXCH = r'(binance|coinbase|mercado bitcoin|foxbit|bybit|okx|kraken|novadax|bitso|bitget|kucoin)'
EMOJI = {'📈': ' sobe ', '📉': ' cai ', '🚀': ' dispara ', '🔥': ' dispara ', '💰': ' lucro ', '🤑': ' lucro ',
         '⬆️': ' sobe ', '⬇️': ' cai ', '⬆': ' sobe ', '⬇': ' cai '}
# Abreviações e erros de digitação comuns do público (internetês).
ABREVIACOES = {'q': 'que', 'vc': 'voce', 'vcs': 'voces', 'qnd': 'quando', 'qdo': 'quando', 'hr': 'hora', 'eh': 'e',
               'tb': 'tambem', 'tbm': 'tambem', 'mto': 'muito', 'c': 'com', 'n': 'nao', 'pq': 'porque',
               'subi': 'subir', 'chace': 'chance', 'chanse': 'chance', 'ibov': 'ibovespa', 'msm': 'mesmo',
               'petro': 'petrobras', 'ptr4': 'petr4', 'ptr3': 'petr3'}


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
    return re.sub(r'\b\w+\b', lambda m: ABREVIACOES.get(m.group(), m.group()), t)


MERCADOS = {
    'mini_indice': r'\bmini[- ]?indices?\b|\bwin\b|\bwin[fghjkmnquvxz]\d\d\b|\bindice futuro\b',
    'mini_dolar': r'\bmini[- ]?dolar\b|\bwdo\b',
    'ibovespa': r'\bibov\w*|\bbolsa\b|\bacoes\b|\bacao\b|\bbova11\b|\bb3\b|\bbovespa\b|\bstocks?\b|\bindice\b',
    'dolar': r'\bdolar(es)?\b|\bdollars?\b|\bus\$|\bcambio\b|\b(brazilian )?real (sobe|cai|valoriza|desvaloriza|go up|go down)\b'
             r'|\bbrazilian real\b'
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
                r'|\bcombustive(l|is)\b(?! (da|do|de|para|pra|pro)( a| o)? (alta|queda|rali|dolar|bolsa|mercado|ibovespa|juros|crise'
                r'|eleicao|selic|inflacao|cambio)\b)'
                r'|\bgasolina\b(?! n[ao] (fogueira|fogo|incendio|brasa)\b)'
                r'|\bbarril\b(?! de polvora\b)',
    'juros': r'\bjuros\b|\bdi1?\b|\bdi futuro\b|\bselic\b|\brenda fixa\b|\btesouro\b|\bprefixad\w*',
    'cripto': r'\bcripto\w*|\bbitcoins?\b|\bbtc\b|\bethereum\b|\bethers?\b|\beth\b|\bxrp\b|\bexchanges?\b|\bstablecoins?\b'
              r'|\bsolana\b|\bhalving\b|\bftx\b|\busdt\b|\busdc\b|\btether\b|\bhash11\b|\bdoge\w*|\bshiba\b|' + rf'\b{EXCH}\b',
    'memecoin': r'\bmeme ?coins?\b|\bmemecoins?\b|\$trump\b|\$libra\b|\$melania\b|\btokens?\b|\bmoeda do candidato\b',
    'previsao': r'\bpolymarket\b|\bkalshi\b|\bmercados? de previs\w*',
}

# Pôr gasolina em algo ("jogou gasolina no dólar", "o Copom colocou gasolina no dólar", "a eleição pôs gasolina na
# bolsa", "botou mais gasolina") é figurado: sai do texto antes de achar o mercado. Sem "por" ("trocar etanol por gasolina").
GASOLINA_FIGURADA = (r'\b(jog(a|am|ar|ou|aram|ando)|bot(a|am|ar|ou|aram|ando)|coloc(a|am|ar|ou|aram|ando)|pos|poe|poem'
                     r'|puseram|pondo|despej(a|ar|ou|aram|ando)|tac(a|ar|ou|aram|ando))( mais| muita| um pouco de)? gasolina\b')
# "Jair Bolsonaro" não é o candidato.
CANDIDATOS = {'flavio': r'\bflavio\b|(?<!\bjair )\bbolsonaro\b', 'lula': r'\blula\b'}
# Palavra que faz a pergunta ser de eleição mesmo citando cargo de empresa ("se o Lula ganhar, troca o presidente da
# Petrobras?"). Sem ela, o presidente da Petrobras não é o da República, e o Bolsonaro que trocou o comando da
# Petrobras não é o candidato.
ELEITORAL = (r'\belei(cao|coes|toral|torais)\b|\bturnos?\b|\bcandidat\w*|\burnas?\b|\bpesquisas?\b|\bvot(o|ar)\b'
             r'|\b(ganhar|vencer|perder|eleito)\b|\bproximo presidente\b|\blula\b|\bflavio\b|\bcampanha\b|\bse o \w+ voltar\b')
# O Bolsonaro que mexeu no comando da Petrobras ("quando o Bolsonaro trocou o presidente da Petrobras?") é o governo, não o
# candidato. Sem o fato do governo ("com o Bolsonaro, a Petrobras e o dólar sobem?"), é a eleição.
GOVERNO_BOLSONARO = (r'\b(trocou|trocaram|troca|trocar|indicou|indicar|demitiu|demitir|nomeou|nomear|interferiu|interferir'
                     r'|tirou|mudou)\b|\bgoverno (jair )?bolsonaro\b')
CARGO = (r'\b(presidente|presidencia|ceo|comando)\b( d[aoe]| na| no)? (petrobras|estatal|conselho|empresa|opep|banco central|bc)\b'
         r'|\b(petrobras|estatal)\b[^.?!]{0,30}\b(presidente|presidencia)\b')

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
    # "petróleo" sozinho não é geopolítica: tem mercado próprio, com os eventos de guerra que mexeram com o Brent
    'geopolitico': r'\btarifas?\b|\bguerra\b|\bsancao\b|\bsancoes\b|\biran\b|\b(o|do|no|ao|pro|pelo|com o|contra o) ira\b',
    'choque_externo': r'\bpandemia\b|\bcovid\b|\bcrise (global|externa|internacional)\b',
    'escandalo': r'\bescandalos?\b|\bdelacao\b|\blava ?jato\b|\bgrampo\b',
    'economia': r'\beconomia\b|\binflacao\b|\bipca\b|\bdivida\b|\bpib\b|\bfiscal\b',
    'conceito': r'\bo que (e|sao|significa)\b|\bcomo funciona\b|\bme explica\b|\bexplica\b',
}

# Empresas e tickers da B3 ("PETR4", "PRIO3", "VALE3", "ITUB4", "BOVA11"), e as petroleiras de fora, para a escolha
# entre eles. "petrobas" é o erro de digitação comum; "bp" fica de fora (sigla curta demais).
EMPRESA = (r'(petrobras|petrobas|petr[34]|prio3?|vale3?|exxon\w*|shell|chevron|equinor|3r|brava|petroreconcavo'
           r'|[a-z]{4}(3|4|5|6|11))')

# Os tokens que MERCADOS['cripto'] conhece, mais o ticker SOL: a escolha entre eles é ranking (M2, N7).
CRIPTO_NOME = r'(btc|bitcoins?|eth|ethereum|ethers?|xrp|solana|sol|usdt|usdc|tether|doge\w*|shiba|hash11)'
# Antes do infinitivo, a definição ("o que é zerar a posição?", "o que significa ter posição comprada?") é conceito (P5).
CONCEITO_ANTES = r'(?<!\bque e )(?<!\bsao )(?<!\bsignifica )(?<!\bdizer )(?<!\bfunciona )(?<!\bque e ")'
# "o aumento das ações", "houve aumento": o substantivo, com artigo ou verbo antes.
SEM_ARTIGO = (r'(?<!\bo )(?<!\bum )(?<!\bhouve )(?<!\bteve )(?<!\bdo )(?<!\bno )(?<!\bao )(?<!\bpelo )(?<!\besse )'
              r'(?<!\beste )')

# Classes de ativo, para o "X ou Y" do caso da pessoa (N5). "Banco central" e "um banco" não são o setor.
CLASSE = (r'(dolar|bolsa|cripto|bitcoin|btc|renda fixa|tesouro|acoes|ouro|poupanca|cdb'
          r'|petroleo|brent|petrobras|petr[34]|petroleiras?|bancos|de banco|bancari[ao]s?)(?! centra)')

PROIBIDOS = {
    # "O que eu faço?", "que que eu faço?", "o que fazer agora?", "preciso tomar uma decisão", "e agora?" pedem ação.
    # "O que fazer para entender o Copom?" não: é pedido de explicação.
    'dica': r'\bcompr(a|o|ar|aria|ariam)\b|\bvend(e|o|er|eria)\b|\bentro\b|\bentrar\b|\bsair\b|\bcompens\w*|\bbora\b'
            r'|\bdevo\b|\bdeveria\b|\bvale (a ?pena|mais|comprar)\b|\bfaz sentido\b|\beu (compre|venda)\b'
            r'|\b(o que|que que|oq)( e que)?( eu)? (faco|fazer|faria)\b'
            r'(?! (pra|para) (entender|saber|aprender|estudar|acompanhar|conhecer|ler|interpretar|compreender)\b)'
            r'|\b(preciso|tenho que|tenho de|tenho|vou ter que) (de )?(tomar )?(uma )?(decisao|decidir)\b'
            r'|\bme ajud(a|e|ar) a (tomar (uma )?decisao|decidir|escolher)\b|\bdecid(e|a|ir) (por|pra|para) mim\b'
            r'|\be agora(\?|\W*$)'
            # "conselho" de órgão ("o conselho da Petrobras elegeu o Prates?", "Conselho Monetário") é fato, não dica
            r'|\bse fosse (voce|eu)\b|\bo que (voce )?faria\b|\brecomenda\w*|\bsugest\w*|\bdica\w*'
            r'|\bconselho\w*(?! (de administracao|monetario|fiscal|curador)\b| d[ao] (petrobras|empresa|estatal|bc|banco central'
            r'|cvm|vale|prio)\b)'
            r'|\bfico (comprado|vendido|de fora)\b|\bcomo (eu )?(abordo|opero|ganho)\b|\bestrategia\b|\bposicion\w*'
            r'|\bexposicao\b|\baplicar\b|\binvestir\b|\bbuy\b|\bsell\b|\bshould i\b|\bwould you\b'
            # pôr o dinheiro num mercado, na 1ª pessoa ("invisto em petróleo?", "reinvisto?", "coloco na bolsa?"), menos
            # "como eu coloco dinheiro na corretora?" (P5)
            r'|(?<!como )(?<!como eu )\b(re)?(invisto|aplico)\b'
            r'|(?<!como )(?<!como eu )\b(coloco|ponho|boto)\b[^.?!]{0,30}\b(em|na|no|nas|nos)\b'
            # mover o dinheiro, na 1ª pessoa ("trago o dinheiro?", "troco?"), menos "como mando dinheiro pra fora?" (P5)
            r'|(?<!como )(?<!como eu )\b(troco|trago|mando|envio|converto|transfiro|remeto)\b|\bdeixo (la|aqui|parado|onde esta)\b'
            r'|\b(tiro|boto|deixo|guardo)\b[^.?!]{0,40}\b(exchange|corretora|carteira)\b'
            r'|(?<=.{10})\be ai(\?|\W*$)|\bconviene\b|\b(debo|deberia) (cambiar|traer|mandar|enviar)\b'
            # o que fazer com a posição, preso à 1ª pessoa ou à posse ("mantenho PETR4?", "zero minha petrobras?")
            r'|\bmantenho\b|\bsegur(o|ar)\b (a |o )?(minha|meu|minhas|meus|posicao|petr\w*|acao|acoes|papel|papeis)\b'
            r'|\b(vale|devo|compensa|deveria) segurar\b'
            # o infinitivo só vale fora da definição ("o que é zerar a posição?" é conceito, P5)
            r'|\bzer(o|ei)\b (a |o |as |os )?(minha|meu|minhas|meus|posicao|tudo|petr\w*|acoes)\b'
            rf'|{CONCEITO_ANTES}\bzerar\b (a |o |as |os )?(minha|meu|minhas|meus|posicao|tudo|petr\w*|acoes)\b'
            # "aumento" só como verbo: "o aumento das ações" e "houve aumento nas ações" são fato
            rf'|(?:{SEM_ARTIGO}\baumento\b(?! (d[aeo]s?|n[ao]s?)\b)|\b(reduzo|diminuo|realizo)\b'
            rf'|{CONCEITO_ANTES}\b(aumentar|reduzir|diminuir|realizar)\b)[^.?!]{{0,20}}\b(posicao|lucro|petr\w*|acoes|minha|meu)\b'
            rf'|{SEM_ARTIGO}\b(aumento|reduzo|diminuo|realizo)\W*$'
            # a posição da pessoa, não a "posição na pesquisa" nem a "posição em aberto" (conceito)
            r'|\b(minha|meu) posicao\b'
            rf'|{CONCEITO_ANTES}\b(tenho|ter|to com|tou com|estou com|fiquei com|eu com|abro|monto)( uma| a)?( pequena| grande| boa)?'
            r' posicao\b|\bvale (ter|considerar|abrir|montar|fazer)\b[^.?!]{0,20}\bposicao\b|^\W*posicao (em|na|no)\b'
            r'|\b(faco|fazer|faria|vale fazer) (o |um )?preco medio\b'
            r'|\baproveit(o|ar|aria) (a|o|essa|esse|esta|este)? ?(queda|alta|baixa|subida|desconto|tombo|crise|guerra)\b'
            # "o que é oportunidade de arbitragem?" é conceito; com adjetivo ("é uma boa oportunidade?") é sempre pedido
            r'|(?<!\bo que )(?<!\boq )\b(e|seria) (uma )?oportunidade\b|\b(e|seria) (uma )?(boa|otima|grande) oportunidade\b'
            r'|\boportunidade (de|pra|para) (compra|entrada|comprar|entrar|vender|lucro|ganh\w*)\b'
            r'|\b(bom|otimo|melhor|pior) momento\b|\b(ta|esta|e|chegou) (na )?(hora|momento) de\b'
            r'(?! (entender|aprender|estudar|compreender|ler|interpretar)\b)'
            r'|\blong ou short\b|\bshort ou long\b|\b(fico|ficar|entro|vou) (long|short)\b'
            r'|\b(e )?(um )?investimento (seguro|bom|ruim|arriscado)\b'
            # "embarco?" é ordem, como "entro"; "embarcar" sozinho não ("o Brasil vai embarcar petróleo")
            r'|\bembarc(o|amos)\b|\b(vale|da (pra|para)) embarcar\b|\bembarcar (nessa|nesse|agora|ja)\b|\bbtfd\b'
            # promessa de ganho ("dividendo é renda garantida?", M6), menos quem garante ("o CDB é garantido pelo FGC?")
            r'|(?<!\bpoupanca e )(?<!\bcdb e )(?<!\blci e )(?<!\blca e )(?<!\bdeposito e )'
            r'\bgarantid[oa]s?\b(?! (pel[oa]|por) (fgc|governo|tesouro|lei|uniao|b3)\b)',
    'direcao': r'\bvai (subir|cair|disparar|despencar|bombar|valorizar|explodir|fechar|abrir)\b|\bvao (subir|cair)\b|\bchances?\b'
               r'|\bprobabilidad\w*|\bde 0 a 100\b|\bum numero\b|\btendencia\b|\bpode (subir|cair|disparar)\b'
               r'|\bsobe ou (cai|desce|nao)\b|\balavanc(ar|a)\b|\bpotencial\b|\bprevisao\b|\bprever\b|\bdisparar\b',
    'momento': r'\bstop\b|\balvo\b|\bponto de (entrada|saida)\b|\bquando (entrar|sair|comprar|vender)\b'
               r'|\b(hora|quando)\b.{0,15}\b(entrar|sair|comprar|vender|operar)\b|\balertas?\b|\bme avis(a|e)\b|\bsinal de\b'
               r'|\bamanha\b|\bna abertura\b|\bsegunda(-feira)?\b.{0,30}\b(fazer|compr\w*|vend\w*|entr\w*)'
               # "Brent caiu 10% hoje, é a hora?", "perdi o bonde?", "ainda dá tempo?"; não "qual é a hora da decisão do Copom?"
               # nem "é a hora de entender a Selic?"
               r'|(?<!qual )\b(e|seria|sera|chegou)( agora| ja)? a hora\b(?! (de|pra|para) (entender|saber|aprender|estudar'
               r'|acompanhar|conhecer|ler|interpretar|compreender)\b| da verdade\b'
               r'| d[aeo] (decisao|divulgacao|reuniao|copom|ata|abertura|fechamento|votacao|eleicao|apuracao|anuncio|leilao)\b)'
               r'|\bperdi (o|a) (bonde|trem|timing|momento|onda)\b'
               r'|\bainda da tempo\b(?! de (entender|saber|aprender|estudar|ler|ver|assistir|acompanhar|votar)\b)',
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
              r'|\bviver de (dividendos?|proventos?|renda|juros)\b',
    'comparar': (r'\bmelhor\b.{0,40}\bou\b|\bou\b.{0,40}\b(qual )?(o |a )?melhor\b|\bvale mais\b'
                 rf'|\b{CLASSE}\b.{{0,25}}\bou\b.{{0,25}}\b{CLASSE}\b'
                 # "o dólar foi melhor que a bolsa em 2022?" é passado
                 rf'|\b{CLASSE}\b.{{0,30}}(?<!\bfoi )(?<!\bforam )(?<!\bera )(?<!\beram )\b(melhor|pior)(es)? (do )?que\b'),
    'ranking': r'\branking\b|\bmelhores (acoes|ativos|moedas|criptos)\b|\btop ?\d+\b|\bmonta (uma )?carteira\b'
               r'|\bcarteira (recomendada|sugerida|ideal)\b|\bquais (acoes|ativos)\b|\bqual (acao|ativo|papel|moeda|cripto)\b'
               r'|\bque acao\b|\bsobe mais\b|\bmais se benefici\w*|\bmelhor (acao|ativo|cripto|moeda)\b'
               # escolher entre empresas ou tickers ("PETR4 ou PRIO3?", "PRIO é melhor que a Petrobras?", "A Exxon é melhor que
               # a Petrobras?", "Which is better, Petrobras or Prio?") é ranking (M2)
               rf'|\b{EMPRESA}\b.{{0,25}}\b(ou|or|x|vs|versus)\b.{{0,25}}\b{EMPRESA}\b'
               rf'|\b{EMPRESA}\b.{{0,30}}\b(e )?melhor (do )?que\b|\b(melhor (do )?que|better than) (a |o |the )?{EMPRESA}\b'
               r'(?! (pra|para) (entender|saber|aprender|estudar|acompanhar|conhecer|ler|interpretar|compreender)\b)'
               # "Petrobras e Prio: qual escolher?", "Entre Petrobras e PRIO, qual?"
               rf'|\b{EMPRESA}\b.{{0,25}}\b(e|and)\b.{{0,25}}\b{EMPRESA}\b.{{0,30}}(\bqual( (delas|deles|das duas|dos dois))?\W*$'
               r'|\bqual (eu )?(escolh\w*|prefir\w*|pego|fico)\b|\bqual (e|seria) (a |o )?melhor\b)'
               # o mesmo entre criptos ("BTC ou ETH?", "USDT ou USDC?", "ETH é melhor que BTC?"): indicar token (N7)
               rf'|\b{CRIPTO_NOME}\b.{{0,25}}\b(ou|x|vs|versus)\b.{{0,25}}\b{CRIPTO_NOME}\b'
               rf'|\b{CRIPTO_NOME}\b.{{0,30}}\b(e )?melhor (do )?que\b'
               r'|\b(qual|que) (e )?(a )?(melhor |mais \w+ )?petroleiras?\b|\bmelhor(es)? petroleiras?\b'
               r'|\bpaga(m)? mais (dividendos?|proventos?)\b|\b(boa|otima|melhor|grande) pagadora\b'
               r'|\bpaga(m)? (bem|muito|bons|otimos|altos) (dividendos?|proventos?)\b|\bvaca leiteira\b'
               r'|\b(dividend yield|dy)\b[^.?!]{0,30}\b(alto|alta|baixo|baixa|bom|boa|ruim|atrativ\w*|muito|pouco)\b'
               # "mais sólida" só na escolha ("qual petroleira é mais sólida?"); "por que o mini-índice é mais arriscado?" e
               # "o que torna o mini-dólar mais arriscado?" são conceito (D4)
               r'|(?<!\bpor )(?<!\bo )\b(qual|quais)\b[^.?!]{0,30}\b(mais|menos) (solid|segur|arriscad)[ao]s?\b'
               r'|\b(e|seria|ser|sao) (o|a|os|as)( \w+)? (mais|menos) (solid|segur|arriscad)[ao]s?\b'  # o superlativo: "é a mais segura?"
               rf'|\b({EMPRESA}|petroleiras?)\b[^.?!]{{0,30}}\b(mais|menos) (solid|segur|arriscad)[ao]s?\b',
    'seletivo': r'\bso (os|as) (casos|vezes|anos|eleicoes|reunioes|dias|turnos)\b|\bso (as )?altas\b|\bso os positivos\b'
                r'|\bmostra so\b|\bmostra apenas\b|\bapenas (os|as) (casos|turnos|vezes)\b|\b(so|apenas) (a|as) (mediana|media|altas|quedas)\b',
    'plataforma': r'\bqual (a )?(melhor )?(exchange|corretora|plataforma|app)\b|\bonde (eu )?(compro|opero|abro conta)\b'
                  r'|\bque (exchange|corretora)\b|\bindic(a|ar|aria|am) (uma |um |a |o )?(exchange|corretora|plataforma|app)\b'
                  # avaliar uma corretora citada pelo nome ou apontada ("a Binance é segura?", "a Coinbase é regulamentada?
                  # posso confiar?", "é seguro deixar na Binance?") também é indicar (N7)
                  rf'|\b{EXCH}\b.{{0,80}}\b(segur[ao]s?|confiave(l|is)|confi(o|ar)|golpe)\b'
                  rf'|\b(segur[ao]s?|confiave(l|is)|golpe)\b[^.?!]{{0,40}}\b{EXCH}\b'
                  r'|\b(essa|esta) (corretora|exchange|plataforma|app)\b[^.?!]{0,20}\b(segur[ao]|confiavel|golpe)\b'
                  # escolher entre corretoras ("Binance ou Mercado Bitcoin?"), usar, abrir conta ou deixar o dinheiro numa delas
                  rf'|\b{EXCH}\b[^.?!]{{0,30}}\b(ou|x|vs|versus)\b[^.?!]{{0,30}}\b({EXCH}|outra|corretora|exchange)\b'
                  rf'|\b(corretora|exchange)\b[^.?!]{{0,30}}\b(ou|x|vs|versus)\b[^.?!]{{0,30}}\b{EXCH}\b'
                  rf'|\b(abr(o|ir|iria) (uma )?conta|cadastr\w*|deix(o|ar)|guard(o|ar)|confi(o|ar))\b[^.?!]{{0,30}}\b{EXCH}\b'
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
    'chance_candidato': r'\bquem (vai )?(ganha|ganhar|vence|vencer)\b|\bchances? (de|do|da) (ele|ela|o candidato|flavio|lula|bolsonaro) (ganhar|vencer|levar)\b'
                        r'|\bfavorit\w*|\bchances? de vitoria\b|\bquais (as|sao as) chances\b|\breeleit\w*|\beurasia\b'
                        r'|\b(vence|vencer|ganha|ganhar|leva|levar)\b.{0,20}\b(domingo|eleicao|segundo turno|2o turno)\b'
                        r'|\bprobabilidade d[oea] (lula|flavio|bolsonaro|ele|ela)\b|\bquem (ta|esta) na frente\b'
                        r'|\b(lula|flavio|bolsonaro) (vence|ganha|leva)\b',
    'chance_dinheiro': r'\bchances? de (eu )?(ganhar|lucrar)\b|\bganhar dinheiro\b|\bvou lucrar\b|\bda (pra|para) lucrar\b'
                       r'|\bquanto (eu )?ganho\b|\bquais (as|sao as) chances\b|\bganhar ou (nao|perder)\b|\bganha(r)? (uma )?grana\b'
                       r'|\blucr\w*|\brenda (mensal|extra)\b|\bficar rico\b',
}

# O prazo que ainda vem ("até dezembro", "no Natal", "daqui a 6 meses", "by Christmas"). "Até dezembro de 2025", "no
# Natal de 2020" e "o fim do ano passado" são passado.
MESES = r'(janeiro|fevereiro|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)'
PRAZO = (r'(\bate (o )?(' + MESES[1:-1] + r'|natal|carnaval|fim|final)\b'
         r'|\b(no|pro|para o|pelo) (natal|fim do ano|final do ano|fim do mes|final do mes)\b)'
         r'(?! (de |do ano de )?(20)?\d\d\b| passado\b)'
         r'|\b(ano|mes|semestre) que vem\b|\bproximo (ano|mes|semestre)\b|\bdaqui a\b'
         r'|\bby (christmas|year[- ]end|the end of|end of)\b|\bnext (year|month|week)\b')
# Um nível de preço (ou o preço) seguido de um prazo que ainda vem.
NIVEL_PRAZO = (r'(\b(a|em|de|to|at)( us\$| \$|\$)? ?\d'
               r'|\b(brent|wti|barril|petroleo|oil|dolar|euro|ibovespa|bitcoin|btc|gasolina|diesel) (us\$ ?|\$)?\d'
               r'|\b\d[\d.,]* ?(dolares|dolar|reais|mil|k)\b|\b(preco|cotacao|valor|price)\b)'
               r'[^.?!]{0,40}(' + PRAZO + r')')
# Pergunta sobre o futuro de um preço: direção, magnitude, nível ou "o que acontece se". Leva a recusa (N2).
FUTURO = (r'\b(sobe|sobem|subir|suba|subira|subiria|desce|descer|cai|caem|cair|caia|caira|cairia|despenc\w*|dispar\w*|derret\w*'
          r'|valoriz\w*|desvaloriz\w*|aprecia\w*|recua\w*|fecha|fechar|abre|abrir|pra cima|para cima|pra baixo|para baixo|topo'
          r'|fundo|barat[oa]s?|car[oa]s?|vies|palpite|visao|acha|acham|opiniao|tendencia|provavel|esperado|retorno|potencial'
          # o preço de uma ação contra o "justo" (valuation) também é opinião sobre para onde ela vai
          r'|descontad[oa]s?|esticad[oa]s?|subvalorizad[oa]s?|sobrevalorizad[oa]s?|supervalorizad[oa]s?|upside|valuation'
          r'|preco justo|pechinch\w*|promocao|de graca|baratinh\w*|undervalued|overvalued|cheap|expensive|price target'
          r'|target price'
          r'|vai bem|vai mal|reage bem|reage mal|pra onde|para onde|go up|go down|rise|fall|rally'
          # juízo sobre a ação ("isso é bom pra ação?", "é bom pra PETR4?"): é opinião sobre para onde ela vai
          r'|(bom|boa|ruim|otimo|otima|pessimo|pessima) (pra|para|pro|pros|pras) (a |o |as |os )?(acao|acoes|papel|papeis'
          r'|cotacao|petr[34]|petrobras|prio3?)'
          # "conseguiu voltar a 100 mil em 2020?" é passado
          r'|bajar|probabilidad\w*|chances?|(?<!conseguiu )(?<!conseguiram )voltar (pra|para|a)|continuar (subindo|caindo)'
          # gíria de cripto, em formas fechadas: "bombardeio" e "pump and dump" (conceito) não entram, nem o passado
          # ("o dólar explodiu na pandemia?", "o Ibovespa decolou em 2018?", "bombou em 2019?")
          r'|explod(?!iu\b|iram\b|ido\b)\w*|decol(?!ou\b|aram\b|ado\b)\w*|bombar|bombando|pumpa\w*|pumpar|pra lua|para a lua'
          r'|to the moon)\b'
          # "o bitcoin explodiu, vai continuar?": o que vem depois do movimento
          r'|\b(vai|vao|deve|devem) continuar\b'
          # nível de preço no futuro ("vai a 150?", "chega a 200 mil?", "bate 50 reais?"): termina no 1º dígito, para valer
          # com "150k" e "250 mil". "Passou de" fica de fora: é passado.
          r'|\b(vai a|chega a|chegar a|vai (pra|para)|passa(r)? de|bate(r)?( os)?)( us\$)? ?\d'
          # "quanto vai estar o barril no natal?", "¿cuánto va a valer el barril?"
          r'|\b(vai|vao|va a|van a) (estar|valer|custar|ficar|llegar|costar)\b'
          r'|\b(subiu|caiu|subiram|cairam|sobe|cai|subindo|caindo) demais\b'  # "já subiu demais?" é o "esticado"
          # "o petróleo termina o ano acima de 100?", como o "fecha" ("terminou o ano" é passado)
          r'|\b(termina|terminar|terminam|encerra|encerrar|encerram) (o ano|o mes|a semana|o semestre|20\d\d)\b'
          # em inglês ("Will oil hit $100?", "Is oil going to crash?"), sem "crash" nem "hit" soltos ("o crash de 2020")
          r'|\b(going to|gonna)\b|\bwill (\w+ ){0,2}(hit|reach|crash|drop|climb|go|be|get|rise|fall)\b'
          r'|^\W*(\w+ ){1,2}to \$?\d'  # manchete: "Oil to 150 by Christmas?", "BTC to 100k?"
          r'|\bllega(r|ra)? a( us\$)? ?\d'
          # máxima e "flip" de cripto, no futuro e no presente ("bitcoin vai renovar máxima?", "eth vai flipar?"); o passado
          # ("renovou", "flipou") e o conceito ("o que é ATH?", "flippening") ficam de fora
          r'|\brenova(r|ra|ria|rao)?( a| uma)?( nova)? (maximas?|ath)\b'
          r'|\b(bate|bater|batera|bateria|faz|fazer|fara|faria|atinge|atingir|atingira|atingiria|ter|tera|teria|marca|marcar'
          r'|marcara)( uma| um)?( nova| novo)? (maximas?|ath)\b'
          r'|\b(vai|vao|pode|podem|deve|devem) (bater|fazer|atingir|ter|marcar)( a| uma| o| um)?( nova| novo)? (maximas?|ath)\b'
          r'|\bflipp?(a|ar|am|ara|aria|e|em|ando|s)\b'
          rf'|\b(vai|vao|pode|podem|deve|devem|consegue) (passar|ultrapassar|superar)( o| a)? {CRIPTO_NOME}\b'
          rf'|\b(ultrapassa|ultrapassam|ultrapassara|ultrapassaria|supera|superam|superara|superaria)( o| a)? {CRIPTO_NOME}\b'
          # o nível com prazo, sem verbo ("Brent a 100 até dezembro?", "Qual o preço do brent daqui a 6 meses?")
          r'|' + NIVEL_PRAZO)
# O que não é preço sai do texto só para o FUTURO (o resto do roteador lê a pergunta inteira):
# - "cara" vocativo ("cara, como tá o dólar?", "ô cara", "o dólar, cara,") e substantivo ("a cara do Ibovespa", "com cara
#   de quê", "o cara do BC"). "Tá cara?", "cara demais" e "cara de alta" continuam sendo valuation e direção (N2).
CARA_NAO_PRECO = (r'^((o|oh|ai|ei|e ai|fala|opa|oi|po|poxa|putz|nossa|mano|meu|velho|vei|serio|olha|ah|tipo|bom|caramba|eita)'
                  r'\W+)?cara\b(?! demais\b)|,\s*cara\b(?! demais\b)'
                  r'|(?<!\bmais )(?<!\bmenos )(?<!\btao )(?<!\bmuito )(?<!\bbem )(?<!\bmeio )'
                  r'(?!cara do que\b)\bcara d[aeo]s?\b(?! (novo|mais|alta|altas|queda|quedas|baixa|bolha|correcao|rali|crash)\b)'
                  r'|\b(o|um|esse|este|aquele|do|no|pro|pelo|ao|num|dum|desse|nesse|daquele) cara\b')
# - "descontado" de imposto ou de provento ("o IR é descontado na fonte?", "o dividendo é descontado do preço?"): é regra
#   (P5), não "a ação tá descontada". Com empresa citada, só o "na fonte" sai.
DESCONTO_NA_FONTE = r'\bdescontad[oa]s? (na|no) (fonte|holerite|contracheque|salario)\b'
DESCONTO_NAO_PRECO = (r'\b(imposto|ir|irrf|iof|tributos?|taxas?|tarifas?|custodia|corretagem|emolumentos?|come cotas'
                      r'|dividendos?|jcp|proventos?|juros sobre capital|cupom|cupons)'
                      r'( (de|do|da|dos|das|sobre|no|na|em) (\w+ ){0,3}\w+)? (e|sao|foi|foram|vem|sera|serao|fica|ficam|seria)'
                      r' descontad[oa]s?\b')
# - a definição inteira e genérica ("o que é valuation?", "como se calcula o preço justo de uma ação?") é conceito (P5).
#   Com artigo, mercado ou empresa ("o que é o upside do Ibovespa?") continua recusa.
_GENERICO = r'( (de|em|numa|num) (uma |um )?(acao|acoes|empresa|empresas|ativo|ativos|papel|papeis))?\W*$'
DEFINICAO_VALUATION = (r'^((o que|oq) (e|sao|significa|quer dizer)|como (funciona|se calcula|se faz|e calculado))( o| um)?'
                       r' (valuation|upside|preco justo)' + _GENERICO)
# - a regra do circuit breaker ("quando a queda passa de 10%?") não é nível de preço no futuro.
REGRA_DE_QUEDA = (r'\bquando\b[^?!.]{0,40}\b(queda|baixa)\b[^?!.]{0,20}\bpassa(r)? de \d+([.,]\d+)? ?%'
                  r'|\bquando\b[^?!.]{0,40}\bpassa(r)? de \d+([.,]\d+)? ?% de (queda|baixa)\b')
PASSA_DE_PCT = r'\bpassa(r)? de (?=\d+([.,]\d+)? ?%)'
# - o intervalo que começa num mês ou ano ("de janeiro até outubro", "desde 2020 até") não é o prazo de uma previsão.
INTERVALO = rf'\b(de|desde) (o |a )?({MESES[1:-1]}|inicio do ano|comeco do ano|20\d\d) ate\b'
CONDICIONAL = (r'\bse (o |a )?(\w+ ){0,2}(ganhar|vencer|perder|for eleito|for reeleito|cortar|cortarem|subir|aumentar|baixar|'
               r'reduzir|mantiver|wins?)\b|\b(ganhando|vencendo|perdendo)\b|\bcom (o |a )?\w+ eleit[oa]\b|\bif \w+ wins?\b')
# Pergunta sobre o que já aconteceu: não pede direção.
PASSADO = r'\b(reagiu|reagiram|aconteceu|aconteceram|foi|foram|ficou|ficaram|historico|historicamente|antes|passad[ao]s?|ja houve)\b'
FUTURO_EXPLICITO = (r'\b(vai|vao|agora|amanha|semana que vem|depois d[oa]|proxim\w*|pra onde|para onde)\b'
                    # "Brent em 138 foi o topo?": se o topo já passou é pergunta sobre o que vem; "foi o topo de 2022?" é passado
                    r'|\bdaqui a\b|\b(ja )?(foi|era) (o|a) (topo|fundo|pico)\W*$')
# Oração: "o dólar ficou abaixo de 5, cai mais?" pede o próximo movimento na 2ª oração; o "ficou" da 1ª não apaga o
# pedido. Vírgula e ponto de número ("5,04", "1.000") não separam.
ORACAO = r'[;:?!]|[,.](?!\d)|\b(?:e|mas)\b'
# O advérbio vale para a frase inteira: "historicamente, a bolsa sobe depois de eleição?" pergunta o que já aconteceu (P1).
PASSADO_DA_FRASE = r'\b(historicamente|no passado)\b'
# Na oração, o movimento no pretérito também é marca de passado ("como o dólar reagiu e se valorizou na pandemia?"): o
# FUTURO pega "valoriz", "dispar" e "despenc" em qualquer tempo.
MOVIMENTO_PASSADO = (r'\b(subiu|subiram|caiu|cairam|valorizou|valorizaram|desvalorizou|desvalorizaram|despencou|despencaram'
                     r'|disparou|dispararam|derreteu|derreteram|recuou|recuaram|apreciou|apreciaram|explodiu|explodiram|decolou'
                     r'|decolaram|bombou|fechou|fecharam|abriu|abriram)\b')
VERBO_DECISAO = ('corta|cortam|mantem|segura|eleva|elevam|aumenta|aumentam|baixa|baixam|reduz|reduzem|sobe|sobem'
                 '|reajusta|reajustam')
# O melhor ou o pior momento que já passou ("qual foi o pior momento do Ibovespa na pandemia?") é fato (P1). O momento
# "pra comprar" continua pedido, mesmo no passado ("qual foi o melhor momento pra comprar dólar em 2020?").
MOMENTO_DICA = r'\b(bom|otimo|melhor|pior) momento\b'
MOMENTO_PASSADO = (r'\b(qual|quando) (foi|foram) o (melhor|pior) momento\b|\b(teve|tiveram|viveu) (o|seu) (melhor|pior) momento\b'
                   r'|\b(melhor|pior) momento\b[^.?!,;]{0,40}\b(foi|foram|aconteceu|ocorreu) (em|no|na|nos|nas|durante|quando|entre)\b')
MOMENTO_PRA = r'\b(bom|otimo|melhor|pior) momento\b[^.?!,;]{0,25}\b(pra|para|de) \w+(ar|er|ir)\b'
# Decisão de juros que ainda vai sair: "vai cortar os juros?", "o BC vai reduzir a Selic?", "vai ter corte?", "o Copom
# cortará?", "corta na próxima reunião?". É futuro pela forma do verbo: não passa pelo filtro do PASSADO.
DECISAO = (r'\b(vai|vao|ira|irao|deve|devem|pode|podem)( \w+){0,2} (cortar|baixar|reduzir|manter|segurar|elevar|aumentar'
           r'|subir|mexer|parar|pausar|interromper|reajustar)\b'
           # pagar dividendo que ainda vai sair é previsão; pagar imposto, IOF ou cupom é regra (P5)
           r'|\b(vai|vao|ira|irao|deve|devem|pode|podem)( \w+){0,2} pagar\b(?!( \w+){0,2} (impostos?|ir|irpf|iof|darf|tributos?'
           r'|taxas?|tarifas?|cupom|cupons|come-?cotas|ajustes?)\b| (mais|menos) (que|do que) (a |o )?(selic|cdi|poupanca))'
           r'|\b(cort|baix|segur|elev|aument)a(ra|rao|ria|riam)\b|\breduzi(ra|rao|ria|riam)\b|\bmante(ra|rao|ria|riam)\b'
           r'|\b(vai ter|vai haver|vao ter|tera|havera|teremos)( \w+){0,2} (corte|cortes|alta|altas|aumento|reducao|elevacao'
           r'|manutencao|pausa|queda|reajuste|reajustes)\b'
           # a forma curta, no presente: "a OPEP corta?", "o Copom sobe?"
           r'|^(a |o )?(opep|opec|copom|bc|banco central)\+? (corta|cortam|mantem|sobe|eleva|aumenta|reduz|baixa)'
           r'( (a |os )?(producao|juros|selic|taxa))?\W*$'
           r'|\b(corta|cortam|mantem|segura|eleva|aumenta|baixa|reduz|sobe)\b.{0,30}\b(proxim\w*|amanha|semana que vem)\b'
           # "vem aumento de gasolina aí?", "o diesel baixa?", "será que a OPEP corta a produção?": a decisão que ainda vem.
           # Sem artigo depois de "vem" ("de onde vem a alta do dólar?") e até 3 palavras depois de "será que".
           r'|\bvem (ai )?(um |uma |mais )?(novo |nova )?(aumento|reajuste|corte|reducao)\b'
           r'|^(sera que )?(a |o )?(petrobras|gasolina|diesel|etanol|combustivel)\+? (corta|mantem|sobe|aumenta|reduz|baixa|reajusta)'
           r'( (a |o |os )?(gasolina|diesel|combustive(l|is)|preco))?\W*$'
           rf'|\bsera que (\S+ ){{0,3}}({VERBO_DECISAO})\b')
# O verbo no presente com uma data que ainda vem ("a Petrobras reajusta a gasolina essa semana?", "a OPEP corta em
# dezembro?"): passa pelo filtro do PASSADO, como o DECISAO_OU ("historicamente a OPEP corta em dezembro?" é passado).
MARCA_DATA = (r'mes que vem|ano que vem|(essa|esta|nessa|nesta) semana|(esse|este|nesse|neste) (mes|ano)'
              r'|(em|de) (janeiro|fevereiro|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)'
              r'(?! de (19|20)\d\d)|na reuniao de \w+|domingo|sabado|(segunda|terca|quarta|quinta|sexta)( |-)?feira')
DECISAO_DATA = rf'\b({VERBO_DECISAO})\b.{{0,30}}\b({MARCA_DATA})\b'
# "Corta ou mantém?", "corte ou manutenção?": pode ser a decisão de amanhã ou a de ontem, então passa pelo filtro do PASSADO.
DECISAO_OU = (r'\b(corta|cortam|mantem|segura|eleva|aumenta|baixa|reduz|sobe)\b.{0,20}\bou (corta|cortam|mantem|segura'
              r'|eleva|aumenta|baixa|reduz|sobe|para|nao)\b'
              r'|\b(corte|manutencao)\b.{0,15}\bou (corte|manutencao|alta|elevacao|aumento|reducao|pausa)\b'
              r'|\b(alta|elevacao|aumento|reducao|pausa)\b.{0,15}\bou (corte|manutencao)\b')
# O lucro e o dividendo de uma empresa que ainda vão sair são projeção (N2): "Lucro da Petrobras no 3T26 vem forte?",
# "Dividendo da Petrobras em novembro vai ser grande?". O lucro da empresa não é a chance de a pessoa ganhar dinheiro.
LUCRO_EMPRESA = (rf'\b(lucros?|prejuizos?|balancos?) (\w+ )?(d[aoe]s? )?(?!vale\b){EMPRESA}\b'
                 rf'|\b(lucros?|prejuizos?|balancos?) (\w+ )?d[aoe]s? vale\b|\b(?!vale\b){EMPRESA}( \w+){{0,3}} lucr\w*')
PRIMEIRA_PESSOA = r'\b(eu|vou|meu|minha|meus|minhas|mim|consigo)\b'
# "a gente pode lucrar?", "quem pode lucrar com mini-índice?" é a própria pessoa, dita de forma impessoal: chance_dinheiro
PESSOA_QUE_LUCRA = r'\b(eu|vou|a gente|agente|quem|da (pra|para))\b'
# "de onde vem o lucro?", "vem do pré-sal" e "vem caindo" não são o que vem
VEM = r'(?<!onde )\bvem\b(?! (d[aeo]s?|da onde|\w+ndo)\b)'
LUCRO_QUE_VEM = (VEM + r'|\b(vira|virao|sera|serao)\b|\b(vai|vao|deve|devem|pode|podem|tende a|tendem a) (ser|vir|ter|sair|crescer'
                 r'|cair|subir|bater|ficar|melhorar|piorar)\b|\bproxim\w* (trimestre|balanco|resultado)\b')
DIVIDENDO = r'\b(dividendos?|proventos?|jcp)\b'
DIVIDENDO_FUTURO = (VEM + r'|\b(vai|vao|deve|devem) (ser|sair|vir|cair|subir|crescer|aumentar|diminuir)\b'
                    r'|\b(vira|virao|sai|saem|saira|sairao|sera|serao)\b|\bproxim\w*|\b(esse|este|neste|nesse) ano\b')
DIVIDENDO_PASSADO = (r'\b(pagou|pagaram|distribuiu|distribuiram|anunciou|anunciaram|aprovou|aprovaram|saiu|sairam|veio|vieram'
                     r'|teve|tiveram|reagiu|reagiram|aconteceu|aconteceram|foi|foram|mexeu)\b')
# A pergunta de imposto sobre dividendo é regra (P5), não previsão.
DIVIDENDO_REGRA = r'\b(imposto|tribut\w*|tax(a|ad)\w*|aliquota|isen\w*|irpf|ir|declar\w*|lei)\b'
# Pedir a análise ou o juízo sobre uma empresa ("analisa a PETR4", "Petrobras é uma boa empresa?", "PETR4 é segura?",
# "tem fundamento?") é pedir relatório de análise (Res. CVM 20): vai para a direção, como "PETR4 tá barata?".
AVALIA_EMPRESA = (rf'\b(analis(a|e|ar|aria)|avali(a|e|ar|aria)|avaliacao)\b[^.?!]{{0,25}}\b{EMPRESA}\b'
                  rf'|\b{EMPRESA}\b[^.?!]{{0,25}}\b(e|seria|ta|esta) (uma )?(boa|otima) (empresa|acao|compra)\b'
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
PRECO_EM_DOLAR = r'(us\$|u\$|usd) ?\d[\d.,]*( ?(mil|k))?|\d[\d.,]*( ?(mil|k))? ?(dolares|dolar|dollars?|usd)\b'
POSSE = r'\b(tenho|guardei|guardo|juntei|economizei|poupei|meus|minhas|recebi|ganhei)\b'
# Pôr o dinheiro num mercado ("invisto em petróleo?", "compro ações da Petrobras com isso?"). Sem "compra" (substantivo):
# "poder de compra" é câmbio.
INVESTE = (r'\b((re)?invisto|investir|investiria|aplico|aplicar|aplicaria|compro|comprar|compraria|coloco|colocar|ponho'
           r'|boto|botar)\b')
# O preço do barril ou do litro em moeda estrangeira ("o Brent a 100 dólares", "90 dólares o barril") sai do texto antes de
# achar o dinheiro da pessoa; e o dinheiro dela também se reconhece pelo que vem colado ao número ("40 mil euros na
# conta", "quero trazer 100 mil euros"), não só pelo POSSE.
_DINHEIRO = (r'(?:(?:euros|eur|usd|us\$|u\$) ?\d[\d.,]*(?: ?(?:mil|k|milhao|milhoes|mi)\b)?'
             r'|\d[\d.,]*(?: ?(?:mil|k|milhao|milhoes|mi)\b)? ?(?:de |em )?(?:euros?|eur|dolares|dolar|dollars?|usd|us\$|u\$)(?![\w$]))')
PRECO_DO_BARRIL = (r'\b(?:petroleo|brent|wti|barril|barris|opep|opec|gasolina|diesel|etanol|combustive(?:l|is)|litro)\b'
                   r'(?: (?:a|de|em|por|o|esta|ta|foi|vai|passou|passa|passar|bateu|bater|chegou|chega|chegar|acima|abaixo'
                   r'|perto|caiu|cai|subiu|sobe|custa|custava|custando|cotado|para|pra))* ?' + _DINHEIRO
                   + r'|' + _DINHEIRO + r' (?:o |por |cada |do |de |a |per |the )?(?:barril|barris|litros?|galao|barrel|liter|gallon)\b')
DINHEIRO_DELA = (r'(?:euros?|eur|dolares|dolar|dollars?|usd)(?: (?:parad|guardad)[oa]s?)? (?:na|em) (?:minha |uma )?conta\b'
                 r'|\b(?:trazer|mandar|trocar|converter|enviar|transferir|remeter|levar|trago|mando|troco|converto|envio'
                 r"|transfiro|remeto|levo|to com|tou com|estou com|fiquei com|i have|i've got) (?:uns |umas |os |as )?"
                 r'(?:euros |eur |usd |us\$ ?|u\$ ?)?\d')
# Valor em reais que é preço ou fato ("dividendo de R$ 6,73 por ação", "os R$ 20 bilhões", "a gasolina a R$ 6,53"), não o
# dinheiro da pessoa: não é capital.
PRECO_OU_FATO = (r'r\$ ?\d[\d.,]*( ?(mil|mi|bi|bilh\w*|milh\w*))? por (acao|litro|barril)\b'
                 r'|r\$ ?\d[\d.,]* ?(bi|bilh\w*)\b|r\$ ?\d[\d.,]* ?milh\w* (de|em) (dividendo|lucro|juros)\w*'
                 # o preço unitário: sem "mil" nem 4 dígitos, que é o dinheiro da pessoa ("recebi dividendos de R$ 5 mil",
                 # "tenho uma ação de R$ 10 mil"). O dividendo por ação já vem pelo "por ação" do 1º ramo.
                 r'|\b(gasolina|diesel|etanol|dolar|euro|barril|litro|acao|petr[34]|petrobras) (a|de|em|por|chegou a'
                 r'|bateu|custa\w*|esta a|ta a|foi a|foi de|pagou( dividendos?)?( de)?) r\$ ?'
                 r'(?![\d.,]* ?(mil|mi|milh\w*|k)\b|\d{4}|\d{1,3}\.\d{3})\d[\d.,]*')


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


def _texto_do_futuro(t: str) -> str:
    """O texto que o FUTURO lê: sem o "cara" que não é preço, sem o "descontado" de imposto e sem a regra de queda."""
    if re.search(DEFINICAO_VALUATION, t):
        return ''
    t = re.sub(CARA_NAO_PRECO, ' ', t)
    t = re.sub(DESCONTO_NA_FONTE, ' ', t)
    if not re.search(rf'\b{EMPRESA}\b', t):
        t = re.sub(DESCONTO_NAO_PRECO, lambda m: re.sub(r'descontad[oa]s?\b', ' ', m.group(0)), t)
    if re.search(REGRA_DE_QUEDA, t):
        t = re.sub(PASSA_DE_PCT, ' ', t)
    return re.sub(INTERVALO, ' ', t)


def analisar(pergunta: str) -> Pedido:
    t = normalizar(pergunta)
    achou = lambda padroes, texto=t: [k for k, rx in padroes.items() if re.search(rx, texto)]  # noqa: E731
    # O presidente da Petrobras e o domingo da reunião da OPEP não são a eleição, a não ser que a pergunta cite a eleição
    # de outro jeito.
    t_eleicao = t
    if not re.search(ELEITORAL, t):
        t_eleicao = re.sub(CARGO, ' ', t)
        if re.search(r'\bpetrobras\b', t) and re.search(GOVERNO_BOLSONARO, t):
            t_eleicao = re.sub(r'\bbolsonaro\b', ' ', t_eleicao)
    if re.search(r'\b(opep|opec)\b', t):
        t_eleicao = re.sub(r'\bdomingo\b', ' ', t_eleicao)
    temas = [k for k, rx in TEMAS.items() if re.search(rx, t_eleicao if k == 'eleicao' else t)]
    p = Pedido(pergunta=pergunta, mercados=achou(MERCADOS, re.sub(GASOLINA_FIGURADA, ' ', t)),
               candidatos=achou(CANDIDATOS, t_eleicao), temas=temas,
               proibidos=achou(PROIBIDOS), voto_informado=bool(re.search(VOTO_INFORMADO, t)))
    if 'capital' in p.proibidos and not re.search(PROIBIDOS['capital'], re.sub(PRECO_OU_FATO, ' ', t)):
        p.proibidos.remove('capital')
    # O momento que já passou não é pedido de entrada, a não ser que o resto da pergunta peça dica.
    if ('dica' in p.proibidos and re.search(MOMENTO_PASSADO, t) and not re.search(FUTURO_EXPLICITO + '|' + MOMENTO_PRA, t)
            and not re.search(PROIBIDOS['dica'], re.sub(MOMENTO_DICA, ' ', t))):
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
    # O passado só vale quando nenhuma oração pede o futuro sem uma marca de passado própria.
    so_passado = re.search(PASSADO, t) and not condicional and not re.search(FUTURO_EXPLICITO, t) and (
        re.search(PASSADO_DA_FRASE, t) or not any(
            (re.search(FUTURO, o) or re.search(DECISAO_OU, o)) and not (re.search(PASSADO, o) or re.search(MOVIMENTO_PASSADO, o))
            for o in re.split(ORACAO, t_futuro)))
    # Decisão de juros que ainda vai sair ("vai cortar a Selic?", "corta ou mantém?") também é futuro de preço.
    decisao = bool(p.mercados or re.search(SOBRE_JUROS, t) or curta) and bool(
        re.search(DECISAO, t) or ((re.search(DECISAO_OU, t) or re.search(DECISAO_DATA, t)) and not so_passado))
    # Lucro de uma empresa que ainda vai sair ("a Petrobras vai lucrar?", "o lucro da Petrobras vem forte?") é projeção; o
    # da pessoa é chance_dinheiro, que só sai quando a única palavra de lucro é a da empresa.
    lucro_empresa = bool(re.search(LUCRO_EMPRESA, t)) and not re.search(PRIMEIRA_PESSOA, t)
    if (lucro_empresa and 'chance_dinheiro' in p.proibidos
            and not re.search(PROIBIDOS['chance_dinheiro'], re.sub(LUCRO_EMPRESA, ' ', t))):
        p.proibidos.remove('chance_dinheiro')
    lucro_futuro = (re.search(r'\b(vai|vao|deve|devem|pode|podem)( \w+){0,2} lucr\w*', t)
                    or lucro_empresa and re.search(LUCRO_QUE_VEM, t)) and not re.search(PESSOA_QUE_LUCRA, t)
    # O dividendo que ainda vai sair ("quanto a Petrobras paga de dividendo esse ano?") é previsão de emissor (N2).
    dividendo_futuro = bool(re.search(DIVIDENDO, t) and re.search(DIVIDENDO_FUTURO, t) and not re.search(DIVIDENDO_PASSADO, t)
                            and not re.search(DIVIDENDO_REGRA, t))
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
    if 'ranking' in p.proibidos and 'comparar' in p.proibidos and re.search(rf'\b{EMPRESA}\b', t):
        p.proibidos.remove('comparar')
    if 'aposta' in p.proibidos and 'previsao' not in p.mercados:
        p.mercados.append('previsao')
    if 'binaria' in p.proibidos:
        p.mercados = [m for m in p.mercados if m != 'previsao']
    # "Quais as chances pro dólar": é direção do mercado, não chance de candidato.
    if 'chance_candidato' in p.proibidos and p.mercados and not re.search(CANDIDATO_OU_VITORIA, t):
        p.proibidos.remove('chance_candidato')
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
    valor, moeda, gasto, gasto_moeda = cambio(t)
    sem_preco = re.sub(PRECO_DO_BARRIL, ' ', t) if 'petroleo' in p.mercados else t
    if 'petroleo' in p.mercados and (re.search(POSSE, t) or re.search(DINHEIRO_DELA, sem_preco)):
        valor, moeda = cambio(sem_preco)[:2]  # o 1º dinheiro dela que não é o preço do barril nem do litro
    elif 'petroleo' in p.mercados:
        valor = None  # "o petróleo passou de 100 dólares?": é o preço do barril
        sem_preco = re.sub(PRECO_EM_DOLAR, ' ', t)
    # O dólar que só aparece no preço do barril ("o Brent a 100 dólares mexe nos meus 20 mil euros?") não é câmbio.
    if 'petroleo' in p.mercados and 'dolar' in p.mercados and not re.search(MERCADOS['dolar'], sem_preco):
        p.mercados.remove('dolar')
    contrato_futuro = bool({'mini_indice', 'mini_dolar'} & set(p.mercados) or re.search(CONTRATO, t))
    cripto = bool({'cripto', 'memecoin'} & set(p.mercados))  # "10 mil dólares em USDT" é cripto da pessoa, não câmbio
    # Pôr o dinheiro estrangeiro num mercado que não é câmbio ("invisto em petróleo?", "compro ações da Petrobras?") é
    # classe de ativo (N5): o valor não entra. "O petróleo mexe com isso?" e "trago o dinheiro?" seguem com a conta.
    investe = bool(set(p.mercados) - {'dolar', 'euro'}) and bool(re.search(INVESTE, t))
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

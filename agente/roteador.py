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
               'subi': 'subir', 'chace': 'chance', 'chanse': 'chance', 'ibov': 'ibovespa', 'msm': 'mesmo'}


def simples(s: str) -> str:
    """Minúsculas e sem acento, mas com pontuação ($, %, vírgula), que os padrões usam."""
    return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()


def normalizar(pergunta: str) -> str:
    """Emoji e símbolo de moeda viram palavra, sai o acento, e a abreviação vira a palavra inteira."""
    for e, palavra in SIMBOLOS.items():
        pergunta = pergunta.replace(e, palavra)
    for e, palavra in EMOJI.items():
        pergunta = pergunta.replace(e, palavra)
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
    'petroleo': r'\bpetroleo\b|\bbrent\b|\bwti\b|\bpetrobras\b|\bpetr[34]\b|\bprio3?\b|\bopep\b|\bopec\b|\bcombustive(l|is)\b'
                r'|\bgasolina\b|\bdiesel\b|\bbarril\b|\bormuz\b|\bpetroleiras?\b',
    'juros': r'\bjuros\b|\bdi1?\b|\bdi futuro\b|\bselic\b|\brenda fixa\b|\btesouro\b|\bprefixad\w*',
    'cripto': r'\bcripto\w*|\bbitcoins?\b|\bbtc\b|\bethereum\b|\bethers?\b|\beth\b|\bxrp\b|\bexchanges?\b|\bstablecoins?\b'
              r'|\bsolana\b|\bhalving\b|\bftx\b|\busdt\b|\busdc\b|\btether\b|\bhash11\b|\bdoge\w*|\bshiba\b|' + rf'\b{EXCH}\b',
    'memecoin': r'\bmeme ?coins?\b|\bmemecoins?\b|\$trump\b|\$libra\b|\$melania\b|\btokens?\b|\bmoeda do candidato\b',
    'previsao': r'\bpolymarket\b|\bkalshi\b|\bmercados? de previs\w*',
}

CANDIDATOS = {'flavio': r'\bflavio\b|\bbolsonaro\b', 'lula': r'\blula\b'}

TEMAS = {
    'eleicao': r'\belei(cao|coes|toral|torais)\b|\bturnos?\b|\bcandidat\w*|\burnas?\b|\bpresidente\b|\bganhar a elei'
               r'|\bvencer a elei|\bse (ele|ela) (ganhar|vencer|perder)\b|\bpesquisas?\b|\bdatafolha\b|\bquaest\b|\batlas\w*'
               r'|\binstitutos?\b|\bdireita\b|\besquerda\b|\bvitoria d\w\b|\breeleit\w*|\bdomingo\b|\brunoff\b|\belection\b'
               r'|\bmito\b|\bpt\b|\bpl\b|\bganhando\b|\bvencendo\b|\beleito\b',
    'copom': r'\bcopom\b|\bselic\b|\bdecisao de juros\b|\bbanco central (corta|sobe|mantem|decide)\b|\bcortar(em)? (os )?juros\b',
    'fiscal': r'\bfiscal\b|\barcabouco\b|\bgastos? publicos?\b|\borcamento\b|\bministro da fazenda\b|\bhaddad\b',
    'legislativo': r'\bcongresso\b|\bcamara\b|\bsenado\b|\bvotacao\b|\bpec\b|\breforma\b|\bimpeachment\b',
    'judicial': r'\bstf\b|\bsupremo\b|\bjulgamento\b|\bprisao\b|\bcondenacao\b',
    # "petróleo" sozinho não é geopolítica: tem mercado próprio, com os eventos de guerra que mexeram com o Brent
    'geopolitico': r'\btarifas?\b|\bguerra\b|\bsancao\b|\bsancoes\b|\bira\b',
    'choque_externo': r'\bpandemia\b|\bcovid\b|\bcrise (global|externa|internacional)\b',
    'escandalo': r'\bescandalos?\b|\bdelacao\b|\blava ?jato\b|\bgrampo\b',
    'economia': r'\beconomia\b|\binflacao\b|\bipca\b|\bdivida\b|\bpib\b|\bfiscal\b',
    'conceito': r'\bo que (e|sao|significa)\b|\bcomo funciona\b|\bme explica\b|\bexplica\b',
}

PROIBIDOS = {
    # "O que eu faço?", "que que eu faço?", "o que fazer agora?", "preciso tomar uma decisão", "e agora?" pedem ação.
    # "O que fazer para entender o Copom?" não: é pedido de explicação.
    'dica': r'\bcompr(a|o|ar|aria|ariam)\b|\bvend(e|o|er|eria)\b|\bentro\b|\bentrar\b|\bsair\b|\bcompens\w*|\bbora\b'
            r'|\bdevo\b|\bdeveria\b|\bvale (a pena|mais|comprar)\b|\bfaz sentido\b'
            r'|\b(o que|que que|oq)( e que)?( eu)? (faco|fazer|faria)\b'
            r'(?! (pra|para) (entender|saber|aprender|estudar|acompanhar|conhecer|ler|interpretar|compreender)\b)'
            r'|\b(preciso|tenho que|tenho de|tenho|vou ter que) (de )?(tomar )?(uma )?(decisao|decidir)\b'
            r'|\bme ajud(a|e|ar) a (tomar (uma )?decisao|decidir|escolher)\b|\bdecid(e|a|ir) (por|pra|para) mim\b'
            r'|\be agora(\?|\W*$)'
            r'|\bse fosse (voce|eu)\b|\bo que (voce )?faria\b|\brecomenda\w*|\bconselho\w*|\bsugest\w*|\bdica\w*'
            r'|\bfico (comprado|vendido|de fora)\b|\bcomo (eu )?(abordo|opero|ganho)\b|\bestrategia\b|\bposicion\w*'
            r'|\bexposicao\b|\baplicar\b|\binvestir\b|\bbuy\b|\bsell\b|\bshould i\b|\bwould you\b'
            # mover o dinheiro, na 1ª pessoa ("trago o dinheiro?", "troco?"), menos "como mando dinheiro pra fora?" (P5)
            r'|(?<!como )(?<!como eu )\b(troco|trago|mando|envio|converto|transfiro|remeto)\b|\bdeixo (la|aqui|parado|onde esta)\b'
            r'|\b(tiro|boto)\b[^.?!]{0,40}\b(exchange|corretora|carteira)\b'
            r'|(?<=.{10})\be ai(\?|\W*$)|\bconviene\b|\b(debo|deberia) (cambiar|traer|mandar|enviar)\b',
    'direcao': r'\bvai (subir|cair|disparar|despencar|bombar|valorizar|explodir|fechar|abrir)\b|\bvao (subir|cair)\b|\bchances?\b'
               r'|\bprobabilidad\w*|\bde 0 a 100\b|\bum numero\b|\btendencia\b|\bpode (subir|cair|disparar)\b'
               r'|\bsobe ou (cai|desce|nao)\b|\balavanc(ar|a)\b|\bpotencial\b|\bprevisao\b|\bprever\b|\bdisparar\b',
    'momento': r'\bstop\b|\balvo\b|\bponto de (entrada|saida)\b|\bquando (entrar|sair|comprar|vender)\b'
               r'|\b(hora|quando)\b.{0,15}\b(entrar|sair|comprar|vender|operar)\b|\balertas?\b|\bme avis(a|e)\b|\bsinal de\b'
               r'|\bamanha\b|\bna abertura\b|\bsegunda(-feira)?\b.{0,30}\b(fazer|compr\w*|vend\w*|entr\w*)',
    'capital': r'\br\$ ?\d|\b\d+ ?mil reais\b|\b\d+ ?k\b|\b(um|dois|tres|quatro|cinco|seis|sete|oito|nove|dez|vinte|trinta|'
               r'cinquenta|cem) mil( reais)?\b|\btenho (r\$ ?)?\d+[\d.,]* ?(mil|k|reais|conto|contos|pila|paus)\b'
               r'|\bquantos contratos\b|\bquanto (eu )?(coloco|ponho|invisto|aplico|boto|devia ter|deveria ter)\b'
               r'|\bquanto investir\b|\bmeu (capital|dinheiro|patrimonio|salario)\b|\bminha (renda|carteira|reserva)\b'
               r'|\bganho \d+|\bpor mes\b|\bsalario\b',
    'perfil': r'\barrojad\w*|\bconservador\w*|\bmoderad[oa]\b|\btolerancia (a|ao) risco\b|\bperfil\b|\baposentadoria\b'
              r'|\breserva de emergencia\b|\bserve (pra|para) mim\b|\be (pra|para) mim\b|\bminha idade\b|\btenho \d+ anos\b'
              r'|\bmeu objetivo\b|\bmeu prazo\b',
    'comparar': r'\bmelhor\b.{0,40}\bou\b|\bou\b.{0,40}\b(qual )?(o |a )?melhor\b|\bvale mais\b|\b(dolar|bolsa|cripto|bitcoin|renda fixa|tesouro|acoes|ouro|poupanca|cdb)\b'
                r'.{0,25}\bou\b.{0,25}\b(dolar|bolsa|cripto|bitcoin|renda fixa|tesouro|acoes|ouro|poupanca|cdb)\b',
    'ranking': r'\branking\b|\bmelhores (acoes|ativos|moedas|criptos)\b|\btop ?\d+\b|\bmonta (uma )?carteira\b'
               r'|\bcarteira (recomendada|sugerida|ideal)\b|\bquais (acoes|ativos)\b|\bqual (acao|ativo|papel|moeda|cripto)\b'
               r'|\bque acao\b|\bsobe mais\b|\bmais se benefici\w*|\bmelhor (acao|ativo|cripto|moeda)\b',
    'seletivo': r'\bso (os|as) (casos|vezes|anos|eleicoes|reunioes|dias|turnos)\b|\bso (as )?altas\b|\bso os positivos\b'
                r'|\bmostra so\b|\bmostra apenas\b|\bapenas (os|as) (casos|turnos|vezes)\b|\b(so|apenas) (a|as) (mediana|media|altas|quedas)\b',
    'plataforma': r'\bqual (a )?(melhor )?(exchange|corretora|plataforma|app)\b|\bonde (eu )?(compro|opero|abro conta)\b'
                  r'|\bque (exchange|corretora)\b'
                  # avaliar uma corretora citada pelo nome ou apontada ("a Binance é segura?") também é indicar (N7)
                  rf'|\b{EXCH}\b[^.?!]{{0,30}}\b(segur[ao]s?|confiave(l|is)|golpe)\b'
                  r'|\b(essa|esta) (corretora|exchange|plataforma|app)\b[^.?!]{0,20}\b(segur[ao]|confiavel|golpe)\b',
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

# Pergunta sobre o futuro de um preço: direção, magnitude, nível ou "o que acontece se". Leva a recusa (N2).
FUTURO = (r'\b(sobe|sobem|subir|suba|subira|subiria|desce|descer|cai|caem|cair|caia|caira|cairia|despenc\w*|dispar\w*|derret\w*'
          r'|valoriz\w*|desvaloriz\w*|aprecia\w*|recua\w*|fecha|fechar|abre|abrir|pra cima|para cima|pra baixo|para baixo|topo'
          r'|fundo|barat[oa]|caro|vies|palpite|visao|acha|acham|opiniao|tendencia|provavel|esperado|retorno|potencial'
          r'|vai bem|vai mal|reage bem|reage mal|vai a \d+|chega a \d+|pra onde|para onde|go up|go down|rise|fall|rally'
          r'|bajar|probabilidad\w*|chances?'
          # gíria de cripto, em formas fechadas: "bombardeio" e "pump and dump" (conceito) não entram
          r'|explod\w*|decol\w*|bombar|bombando|bombou|pumpa\w*|pumpar|pra lua|para a lua|to the moon)\b')
CONDICIONAL = (r'\bse (o |a )?(\w+ ){0,2}(ganhar|vencer|perder|for eleito|for reeleito|cortar|cortarem|subir|aumentar|baixar|'
               r'reduzir|mantiver|wins?)\b|\b(ganhando|vencendo|perdendo)\b|\bcom (o |a )?\w+ eleit[oa]\b|\bif \w+ wins?\b')
# Pergunta sobre o que já aconteceu: não pede direção.
PASSADO = r'\b(reagiu|reagiram|aconteceu|aconteceram|foi|foram|historico|historicamente|antes|passad[ao]s?|ja houve)\b'
FUTURO_EXPLICITO = r'\b(vai|vao|agora|amanha|semana que vem|depois d[oa]|proxim\w*|pra onde|para onde)\b'
# Decisão de juros que ainda vai sair: "vai cortar os juros?", "o BC vai reduzir a Selic?", "vai ter corte?", "o Copom
# cortará?", "corta na próxima reunião?". É futuro pela forma do verbo: não passa pelo filtro do PASSADO.
DECISAO = (r'\b(vai|vao|ira|irao|deve|devem|pode|podem)( \w+){0,2} (cortar|baixar|reduzir|manter|segurar|elevar|aumentar'
           r'|subir|mexer|parar|pausar|interromper)\b'
           r'|\b(cort|baix|segur|elev|aument)a(ra|rao|ria|riam)\b|\breduzi(ra|rao|ria|riam)\b|\bmante(ra|rao|ria|riam)\b'
           r'|\b(vai ter|vai haver|vao ter|tera|havera|teremos)( \w+){0,2} (corte|cortes|alta|altas|aumento|reducao|elevacao'
           r'|manutencao|pausa|queda)\b'
           r'|\b(corta|cortam|mantem|segura|eleva|aumenta|baixa|reduz|sobe)\b.{0,30}\b(proxim\w*|amanha|semana que vem)\b')
# "Corta ou mantém?", "corte ou manutenção?": pode ser a decisão de amanhã ou a de ontem, então passa pelo filtro do PASSADO.
DECISAO_OU = (r'\b(corta|cortam|mantem|segura|eleva|aumenta|baixa|reduz|sobe)\b.{0,20}\bou (corta|cortam|mantem|segura'
              r'|eleva|aumenta|baixa|reduz|sobe|para|nao)\b'
              r'|\b(corte|manutencao)\b.{0,15}\bou (corte|manutencao|alta|elevacao|aumento|reducao|pausa)\b'
              r'|\b(alta|elevacao|aumento|reducao|pausa)\b.{0,15}\bou (corte|manutencao)\b')
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


def analisar(pergunta: str) -> Pedido:
    t = normalizar(pergunta)
    achou = lambda padroes: [k for k, rx in padroes.items() if re.search(rx, t)]  # noqa: E731
    p = Pedido(pergunta=pergunta, mercados=achou(MERCADOS), candidatos=achou(CANDIDATOS), temas=achou(TEMAS),
               proibidos=achou(PROIBIDOS), voto_informado=bool(re.search(VOTO_INFORMADO, t)))
    if p.voto_informado and 'eleicao' not in p.temas:
        p.temas.append('eleicao')
    # Conceito de derivativo (margem, ajuste diário, alavancagem): a explicação está no bloco do mini-índice.
    if re.search(r'\bmargem\b|\bajuste diario\b|\balavancagem\b', t) and not p.mercados:
        p.mercados.append('mini_indice')
    # Futuro de um preço: na dúvida, recusa. Vale com mercado, candidato, eleição, Copom ou pergunta curta ("sobe?").
    curta = len(t.split()) <= 4
    sobre_preco = bool(p.mercados or p.candidatos or {'eleicao', 'copom'} & set(p.temas) or curta)
    condicional = re.search(CONDICIONAL, t)
    futuro = re.search(FUTURO, t) or condicional
    so_passado = re.search(PASSADO, t) and not condicional and not re.search(FUTURO_EXPLICITO, t)
    # Decisão de juros que ainda vai sair ("vai cortar a Selic?", "corta ou mantém?") também é futuro de preço.
    decisao = bool(p.mercados or re.search(SOBRE_JUROS, t) or curta) and bool(
        re.search(DECISAO, t) or (re.search(DECISAO_OU, t) and not so_passado))
    if (sobre_preco and futuro and not so_passado or decisao) and 'direcao' not in p.proibidos:
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
    contrato_futuro = bool({'mini_indice', 'mini_dolar'} & set(p.mercados) or re.search(CONTRATO, t))
    cripto = bool({'cripto', 'memecoin'} & set(p.mercados))  # "10 mil dólares em USDT" é cripto da pessoa, não câmbio
    if valor is not None and not contrato_futuro:
        if quanto or momento_troca or cripto:
            if 'capital' not in p.proibidos:
                p.proibidos.append('capital')  # a pessoa contou o valor e ele não é usado: a linha do capital diz por quê
        else:
            p.valor_moeda, p.moeda, p.gasto_mensal, p.gasto_moeda = valor, moeda, gasto, gasto_moeda
            if moeda not in p.mercados:
                p.mercados.append(moeda)
            if 'capital' in p.proibidos:
                p.proibidos.remove('capital')
    return p

// Entende a pergunta: de que mercado, candidato e tema ela fala, e que pedido proibido ela traz. Tradução de
// agente/roteador.py (o Python é a referência; tests/dados/paridade.json prova que os dois leem igual).
//
// O mercado e o tema servem só de filtro de busca no repertório (P3): a resposta não depende de quem pergunta.
// O capital, o perfil e o voto que a pessoa contar são detectados para NÃO serem usados (N5, N9).
//
// Regra da casa: errar para mais na recusa. Pergunta sobre o futuro de um mercado ("sobe?", "se o Lula ganhar, o
// dólar...", "é topo?") leva a recusa padrão, mesmo dita com gíria, erro de digitação, emoji, em inglês ou dentro de
// uma história. Com credencial da API, a IA também classifica a pergunta (agente/ia.py) e os dois resultados se somam.
//
// Os padrões têm o mesmo texto do Python e rodam pelo pyre.ts, que dá a eles o comportamento do re do Python sobre o texto
// de normalizar() (o "." que aceita o \r, o \s com \x1c-\x1f, o $ antes do \n final). As chamadas também seguem as do
// Python: search, sub, split, finditer, match e fullmatch.
import { type Casamento, finditer, fullmatch, match, primeiro, search, split, sub, ultimo } from './pyre.ts'
import { type Pedido, simples } from './texto.ts'

const r = String.raw
// Símbolo de moeda que o simples() apagaria: vira palavra antes ("€150.000" → "euros 150.000").
const SIMBOLOS: ReadonlyArray<readonly [string, string]> = [['€', ' euros ']]
// Corretoras de cripto pelo nome (a mesma lista do filtro de saída).
// "binanse" é o erro de digitação comum.
// "bianance" e "coinbse" também; "MB" (Mercado Bitcoin) só depois de artigo, preposição ou "ou" ("binance ou mb?", "o mb é
// seguro?"), para não pegar "5 mb".
export const EXCH = r`(binan[cs]e|b[iy]?an[ac]n[cs]e|coinba?se|mercado bitcoin|foxbit|bybit|okx|kraken|novadax|bitso|bitget` +
  r`|kucoin|(?:^|(?<=\bo )|(?<=\ba )|(?<=\bno )|(?<=\bna )|(?<=\bdo )|(?<=\bda )|(?<=\bou )|(?<=\bx ))mb)`
// A ordem importa: o "⬆️" (com o seletor de variação U+FE0F) sai antes do "⬆" sozinho.
const EMOJI: ReadonlyArray<readonly [string, string]> = [
  ['📈', ' sobe '], ['📉', ' cai '], ['🚀', ' dispara '], ['🔥', ' dispara '], ['💰', ' lucro '], ['🤑', ' lucro '],
  ['⬆️', ' sobe '], ['⬇️', ' cai '], ['⬆', ' sobe '], ['⬇', ' cai '],
]
// Abreviações e erros de digitação comuns do público (internetês).
// Map, e não objeto: "constructor" não é abreviação.
const ABREVIACOES: ReadonlyMap<string, string> = new Map([
  ['q', 'que'], ['vc', 'voce'], ['vcs', 'voces'], ['qnd', 'quando'], ['qdo', 'quando'], ['hr', 'hora'], ['eh', 'e'],
  ['tb', 'tambem'], ['tbm', 'tambem'], ['mto', 'muito'], ['c', 'com'], ['n', 'nao'], ['pq', 'porque'],
  ['subi', 'subir'], ['chace', 'chance'], ['chanse', 'chance'], ['ibov', 'ibovespa'], ['msm', 'mesmo'],
  ['ptr4', 'petr4'], ['ptr3', 'petr3'], ['oq', 'o que'], ['oque', 'o que'],
])
// simples() mora em texto.ts.
// "Irã" (o país) e "irá" (o verbo) só se distinguem antes de tirar o acento. É o (?<!\w)irã(?!\w) do Python com re.I,
// sobre o texto ainda com acento: lá o \w é Unicode (letra, número ou sublinhado) e o re.I também casa İ e ı com o i,
// e aqui o \b do JS seria ASCII e falharia logo depois do "ã".
const IRA = /(?<![\p{L}\p{N}_])[iIİı][rR][ãÃ](?![\p{L}\p{N}_])/gu

/** Emoji e símbolo de moeda viram palavra, sai o acento, e a abreviação vira a palavra inteira. */
export function normalizar(pergunta: string): string {
  for (const [e, palavra] of SIMBOLOS) pergunta = pergunta.replaceAll(e, palavra)
  for (const [e, palavra] of EMOJI) pergunta = pergunta.replaceAll(e, palavra)
  pergunta = pergunta.replace(IRA, 'iran')
  let t = simples(pergunta)
  t = t.replace(/\b\w+\b/g, (m) => ABREVIACOES.get(m) ?? m)
  // "petro" é a Petrobras, menos o presidente da Colômbia ("o Gustavo Petro", "o Petro ganhou na Colômbia")
  t = sub(r`(?<!\bgustavo )\bpetro\b(?![^.?!]{0,40}\bcolombi\w*)`, 'petrobras', t)
  // o ticker com espaço ("vale a pena petr 4?") é o ticker
  return sub(r`\bpetr ([34])\b`, r`petr\1`, t)
}
export const MERCADOS = {
  mini_indice: r`\bmini[- ]?indices?\b|\bwin\b|\bwin[fghjkmnquvxz]\d\d\b|\bindice futuro\b`,
  mini_dolar: r`\bmini[- ]?dolar\b|\bwdo\b`,
  ibovespa: r`\bibov\w*|\bbolsa\b|\bacoes\b|\bacao\b|\bbova11\b|\bb3\b|\bbovespa\b|\bstocks?\b|\bindice\b`,
  // o real contra as outras moedas, e mandar ou trazer dinheiro de fora: é câmbio
  // o verbo logo depois de "real": "o real problema está..." não é câmbio
  dolar: r`\bdolar(es)?\b|\bdollars?\b|\bus\$|\bcambio\b` +
    r`|\b(brazilian )?real (sobe|cai|valoriza|desvaloriza|go up|go down)\b|\bbrazilian real\b` +
    r`|\bexchange[- ]rates?\b|\b(foreign|currency) exchange\b` +
    r`|\breal\b[^.?!]{0,30}\b(valoriz\w*|desvaloriz\w*|fortalec\w*|enfraquec\w*)` +
    r`|\b(valorizacao|desvalorizacao) do real\b` +
    r`|\b(o|do|no|pro|pelo|com o) real (reag\w*|esta|ta|caiu|cai|subiu|sobe|fic\w*|contra|frente|diante|depois` +
    r`|antes|vai|vem)\b|\breal brasileiro\b|\bmoeda (brasileira` +
    r`|estrangeira)\b|\bremessas?\b|\btransferencias? internaciona\w*|\bconvert\w* (para|pra` +
    r`|em) reais\b|\b(trazer|traz|trago|mandar|mando|enviar|envio|levar|transferir)\b[^.?!]{0,30}\b(pro brasil` +
    r`|para o brasil|pra fora|para fora|do exterior|de fora|para o exterior|pro exterior)\b`,
  euro: r`\beuros?\b|\beur\b`,
  // em sentido figurado não é petróleo: "o combustível da alta", "o combustível para a Selic subir", "barril de
  // pólvora"; "jogou gasolina no dólar" sai antes (GASOLINA_FIGURADA)
  petroleo: r`\bpetroleo\b|\bbrent\b|\bwti\b|\bpetrobras\b|\bpetr[34]\b|\bprio3?\b|\bopep\b|\bopec\b|\bdiesel\b` +
    r`|\bormuz\b|\bpetroleiras?\b|\boil\b|\bcrude\b` +
    r`|(?<!\btroca de )\boleo\b(?! (de |do )?(soja|palma|cozinha|oliva|girassol|milho|coco|canola|algodao` +
    r`|motor|carro|essencia\w*|lubrificante\w*)\b)|\bcombustive(l|is)\b(?!( extra| adicional)? (da|do|de|para` +
    r`|pra|pro|dessa|desta|nessa|nesta)( (a|o|as|os|uma|um|essa|esta|novas?|mais))* (altas?(?! temporada)` +
    r`|quedas?|rali|dolar|bolsa|mercado|ibovespa|juros|crise|eleicao|selic|inflacao` +
    r`|cambio)\b)|\bgasolina\b(?! n[ao] (fogueira|fogo|incendio|brasa)\b)|\bbarril\b(?! de polvora\b)`,
  juros: r`\bjuros\b|\bdi1?\b|\bdi futuro\b|\bselic\b|\brenda fixa\b|\btesouro\b|\bprefixad\w*`,
  // "exchange" é a corretora de cripto, não o verbo nem o câmbio em inglês ("exchange my dollars", "exchange rate")
  // o intercâmbio é masculino ("fazer exchange no Canadá", "um exchange na Irlanda"); a corretora é "a exchange"
  // a lei das stablecoins dos EUA e o ETF aprovado pela SEC, sem a palavra cripto
  // o corte do Pix das corretoras de cripto (06/11/2026), sem a palavra "cripto"; "pix para a corretora" não
  cripto: r`\bcripto\w*|\bbitcoins?\b|\bbtc\b|\bethereum\b|\bethers?\b|\beth\b|\bxrp\b|\bstablecoins?\b` +
    r`|(?<!\bto )(?<!\bi )(?<!\bwe )(?<!\bforeign )(?<!\bcurrency )(?<!\bfazer )(?<!\bfaco )(?<!\bum )(?<!\bdo` +
    r` )(?<!\bno )\bexchanges?\b(?![ -](rates?|my|the|them|it|your|our|their|this|that|these|those|some|all` +
    r`|euros?|dollars?|reais|real|money|currency|currencies|usd|eur|brl|now|today|before|after` +
    r`|\d))|\bsolana\b|\bhalving\b|\bftx\b|\busdt\b|\busdc\b|\btether\b|\bhash11\b|\bdoge\w*|\bshiba\b` +
    r`|\bgenius act\b|\betfs?\b[^.?!]{0,30}\bsec\b|\bsec\b[^.?!]{0,30}\betfs?\b` +
    r`|\bpix\b[^.?!]{0,40}\bcorretoras?\b[^.?!]{0,40}\b(parar|cortar|corta|corte|cortad[oa]|bloque\w*` +
    r`|suspen\w*|acab\w*)\b|\b(parar|cortar|corta|corte|cortad[oa]|bloque\w*|suspen\w*` +
    r`|acab\w*)\b[^.?!]{0,40}\bpix\b[^.?!]{0,40}\bcorretoras?\b|` +
    r`\b${EXCH}\b`,
  memecoin: r`\bmeme ?coins?\b|\bmemecoins?\b|\$trump\b|\$libra\b|\$melania\b|\btokens?\b|\bmoeda do candidato\b`,
  previsao: r`\bpolymarket\b|\bkalshi\b|\bmercados? de previs\w*`,
} satisfies Record<string, string>
// Pôr gasolina em algo ("jogou gasolina no dólar", "o Copom colocou gasolina no dólar", "a eleição pôs gasolina na
// bolsa", "botou mais gasolina") é figurado: sai do texto antes de achar o mercado. Sem "por" ("trocar etanol por gasolina").
// só com o alvo figurado depois: "colocar gasolina no carro" e "o preço de colocar gasolina" são a bomba
const GASOLINA_FIGURADA = r`\b(jog(a|am|ar|ou|aram|ando)|bot(a|am|ar|ou|aram|ando)|coloc(a|am|ar|ou|aram|ando)|pos|poe|poem|puseram` +
  r`|pondo|despej(a|ar|ou|aram|ando)|tac(a|ar|ou|aram|ando)|derram(a|ar|ou|aram|ando))( mais| muita` +
  r`| um pouco de)? gasolina\b(?= (n[ao]s?|em|sobre|em cima d[aoe]s?) (o |a |os |as )?(alta|queda|rali|dolar` +
  r`|real|bolsa|ibovespa|mercado|juros|selic|inflacao|crise|cambio|fogueira|fogo|incendio|brasa` +
  r`|eleic(ao|oes)|campanha|debate|briga|polemica|discussao|tensao)\b)`
// "Jair Bolsonaro" e o "ex-presidente Bolsonaro" não são o candidato.
export const CANDIDATOS = {
  flavio: r`\bflavio\b|(?<!\bjair )(?<!\bex-presidente )(?<!\bex presidente )(?<!\bexpresidente )\bbolsonaro\b`,
  lula: r`\blula\b`,
} satisfies Record<string, string>
// Palavra que faz a pergunta ser de eleição mesmo citando cargo de empresa ("se o Lula ganhar, troca o presidente da
// Petrobras?"). Sem ela, o presidente da Petrobras não é o da República, e o Bolsonaro que trocou o comando da
// Petrobras não é o candidato.
// "a Petrobras pode perder o presidente?" e "o Prates foi eleito presidente da Petrobras" (ou "pelo conselho") falam da
// empresa.
const ELEITORAL = r`\belei(cao|coes|toral|torais)\b|\bturnos?\b|\bcandidat\w*|\burnas?\b|\bpesquisas?\b|\bvot(o|ar)\b` +
  r`|\bganhar\b(?! (bonus|salario|premio|aumento)\b)|\bvencer\b` +
  r`|\bperder\b(?! (o|seu) (presidente|ceo|comando|cargo|posto)\b)` +
  r`|\beleito\b(?! (presidente|ceo)( d[aoe]| na| no)? (petrobras|petr[34]|prio3?|estatal|companhia` +
  r`|empresa)\b| pelo conselho\b)|\bproximo presidente\b|\blula\b|\bflavio\b|\bcampanha\b|\bse o (?!(brent` +
  r`|wti|barril|petroleo|dolar|euro|ibovespa|bitcoin|preco|juros|selic|ipca)\b)\w+ voltar\b`
// O Bolsonaro que mexeu no comando da Petrobras ("quando o Bolsonaro trocou o presidente da Petrobras?") é o governo, não o
// candidato. Sem o fato do governo ("com o Bolsonaro, a Petrobras e o dólar sobem?"), é a eleição.
const GOVERNO_BOLSONARO = r`\b(trocou|trocaram|troca|trocar|indicou|indicar|demitiu|demitir|nomeou|nomear|interferiu|interferir` +
  r`|tirou|mudou|mexeu)\b`
// O governo que passou, pelo nome ("no governo do Bolsonaro", "na época do Bolsonaro", "na gestão Bolsonaro"), sem pedido de
// futuro, ou num ano do mandato ("o Bolsonaro e a Petrobras em 2022"). O que pode vir ("num governo do Bolsonaro", "no
// próximo governo Bolsonaro", "o governo do Bolsonaro vai voltar?", "no governo do Bolsonaro a Petrobras sobe?") é a eleição.
const GOVERNO_BOLSONARO_NOME = r`(?<!\bnum )(?<!\bnuma )(?<!\bum )(?<!\buma )(?<!\bnovo )(?<!\bnova )(?<!\bproximo )(?<!\bproxima )(?<!\b` +
  r`futuro )(?<!\bfutura )(?<!\boutro )(?<!\boutra )(?<!\beventual )(?<!\bpossivel )(?<!\bsegundo )\b(govern` +
  r`o|gestao|mandato|epoca|tempo|periodo` +
  r`|era) (d[oe] )?(ex[- ]?presidente )?(jair )?bolsonaro\b(?! (vai |vao )?volt(ar|a|e|ara|aria)\b)|\b(2019` +
  r`|2020|2021|2022)\b`
// o "eleito" do cargo que vem depois ("o presidente da petr4 foi eleito quando?") sai antes do cargo
const CARGO_ELEITO = r`\b(presidente|ceo)\b( d[aoe]| na| no)? (petrobras|petr[34]|prio3?)\b[^.?!]{0,20}\b(foi )?eleit[oa]\b`
// O cargo também pelo ticker e pela companhia ("o presidente da PETR4", "presidente da Prio"), com o "eleito" e o
// "ex-presidente" da empresa. O presidente da República que vem depois da Petrobras ("a Petrobras e o novo presidente da
// República") é a eleição.
// a outra companhia, sempre com "da/do/na/no" ("o presidente da Vale", "o CEO do Itaú"): "o presidente vale a pena?" não
const CARGO = r`(\beleit[oa] )?\b(presidente|presidencia|ceo|comando)\b( d[aoe]| na| no)? (petrobras|petr[34]|prio3?` +
  r`|estatal|companhia|conselho|empresa|opep|banco central|bc)\b|\b(petrobras|petr[34]|prio3?` +
  r`|estatal)\b[^.?!]{0,50}\b(presidente` +
  r`|presidencia)\b(?! d[ao] (republica|brasil|pais)\b)|\beleit[oa] pelo conselho\b|\b(presidente` +
  r`|presidencia|ceo|comando)\b( d[aoe]| na| no) (vale3?|itau\w*|itub[34]|bradesco|bbdc[34]|santander` +
  r`|banco do brasil|caixa|eletrobras|ambev|embraer|shell|exxon\w*|chevron|equinor|[a-z]{4}(3|4|5|6|11))\b`
// O Irã digitado sem acento ("o ira"): o verbo "irá" só é o pronome antes do infinitivo ("quem o irá substituir",
// "ninguém o irá demitir"). "o ira nuclear", "com o ira atacar Israel" e "se o ira atacar" são o país.
const IRA_SEM_ACENTO = r`\b(do|no|ao|pro|pelo|com o|contra o) ira\b` +
  r`|(?<!\bquem )(?<!\bque )(?<!\bninguem )(?<!\balguem )(?<!\bnao )(?<!\bele )(?<!\bela )(?<!\bvoce )\bo ir` +
  r`a\b|\bo ira\b(?! \w{3,}(ar|er|ir)\b)`
export const TEMAS = {
  // o Jair Bolsonaro de um ano de eleição ("Jair Bolsonaro e o dólar em 2018") é o candidato daquela eleição
  eleicao: r`\belei(cao|coes|toral|torais)\b|\bturnos?\b|\bcandidat\w*|\burnas?\b|\bpresidente\b|\bganhar a elei` +
    r`|\bvencer a elei|\bse (ele|ela) (ganhar|vencer|perder)\b|\bpesquisas?\b|\bdatafolha\b|\bquaest\b` +
    r`|\batlas\w*|\binstitutos?\b|\bdireita\b|\besquerda\b|\bvitoria d\w\b|\breeleit\w*|\bdomingo\b|\brunoff\b` +
    r`|\belection\b|\bmito\b|\bpt\b|\bpl\b|\bganhando\b|\bvencendo\b|\beleito\b` +
    r`|\bjair bolsonaro\b[^.?!]{0,40}\b(2018|2022)\b|\b(2018|2022)\b[^.?!]{0,40}\bjair bolsonaro\b`,
  copom: r`\bcopom\b|\bselic\b|\bdecisao de juros\b|\bbanco central (corta|sobe|mantem|decide)\b` +
    r`|\bcortar(em)? (os )?juros\b`,
  fiscal: r`\bfiscal\b|\barcabouco\b|\bgastos? publicos?\b|\borcamento\b|\bministro da fazenda\b|\bhaddad\b`,
  legislativo: r`\bcongresso\b|\bcamara\b|\bsenado\b|\bvotacao\b|\bpec\b|\breforma\b|\bimpeachment\b`,
  judicial: r`\bstf\b|\bsupremo\b|\bjulgamento\b|\bprisao\b|\bcondenacao\b`,
  // "petróleo" sozinho não é geopolítica: tem mercado próprio, com os eventos de guerra que mexeram com o Brent. O
  // "tarifaço" e a "taxação do Trump" são a tarifa; a "guerra de preço(s)" do petróleo não é guerra; "quem o irá
  // substituir" é o verbo, não o Irã.
  geopolitico: r`\btarifa(s|co|cos|sso)?\b|\bsobretaxa\w*|\btaxac\w* (d[aoe]s?) (trump|eua|estados unidos)\b` +
    r`|\btaxac\w* (do )?trump\b|\btaxac\w* americana\b(?![^.?!]{0,40}\b(dividend|stock|aco|renda)\w*)` +
    r`|\bguerra\b(?! (de |do |dos )?precos?\b)|\bsancao\b|\bsancoes\b|\biran\b|` +
    IRA_SEM_ACENTO,
  choque_externo: r`\bpandemia\b|\bcovid\b|\bcrise (global|externa|internacional)\b`,
  escandalo: r`\bescandalos?\b|\bdelacao\b|\blava ?jato\b|\bgrampo\b`,
  economia: r`\beconomia\b|\binflacao\b|\bipca\b|\bdivida\b|\bpib\b|\bfiscal\b`,
  conceito: r`\bo que (e|sao|significa)\b|\bcomo funciona\b|\bme explica\b|\bexplica\b`,
} satisfies Record<string, string>
// Empresas e tickers da B3 ("PETR4", "PRIO3", "VALE3", "ITUB4", "BOVA11"), e as petroleiras de fora, para a escolha
// entre eles. "petrobas" é o erro de digitação comum; "bp" fica de fora (sigla curta demais).
const EMPRESA = r`(petrobras|petrobas|petr[34]|prio3?|vale3?|exxon\w*|shell|chevron|equinor|3r|brava|petroreconcavo|enauta` +
  r`|aramco|totalenergies|[a-z]{4}(3|4|5|6|11))`
// "quanto vale o ouro ou o dólar?": o verbo, não a Vale.
const EMPRESA_SEM_VALE = r`(?!vale\b)` +
  EMPRESA
// Os papéis da Petrobras, sem pegar "petróleo" (o "petr\w*" pegava "aumentar a produção de petróleo").
const PETR = r`(petr[34]|petrobras)`
// O que a pessoa pode manter, deixar ou aproveitar ("continuo com PETR4?", "oportunidade na Petrobras?").
const ATIVO = r`(` +
  EMPRESA +
  r`|acoes|bolsa|ibovespa|dolar|bitcoin|cripto|petroleo|brent|ouro)`
// "PETR3 ou PETR4: qual a diferença?" e "o que muda entre PETR3 e PETR4?" são conceito (P5), não escolha.
// Com a escolha junto ("qual a diferença e qual eu pego?", "o que muda? qual é melhor?"), volta a ser escolha (M2). A
// relação ("qual a correlação entre Petrobras e Prio?") também é conceito.
const ESCOLHA_DITA = r`\bqual (eu )?(pego|fico|levo|escolh\w*|prefir\w*|compr(o|ar|aria))\b` +
  r`|\bqual (vc|voce|tu) (escolh\w*|prefer\w*|peg\w*|fica\w*|compr\w*)\b` +
  r`|\bqual (e |seria )?(a |o )?melhor\b(?! (jeito|forma|maneira|fonte|site|livro|lugar|ano|trimestre)\b` +
  r`| (pra|para) (entender|saber|aprender|estudar|acompanhar|conhecer|ler|interpretar|compreender` +
  r`|comparar)\b)`
const SEM_DIFERENCA = r`^(?:(?=.*(?:${ESCOLHA_DITA}))|(?!.*\b(diferenc\w*|difere\w*|o que muda|relac\w*|correlac\w*)\b)).*?`
// O "ou" entre dois verbos ("o dólar subiu ou caiu quando...", "a Petrobras exporta ou importa petróleo?") não liga ativos.
const OU_ATIVO = r`(?<!\bsubiu )(?<!\bsubiram )(?<!\bsubia )(?<!\bsobe )(?<!\bsobem )(?<!\bcaiu )(?<!\bcairam )(?<!\bcaia )` +
  r`(?<!\bcai )(?<!\bcaem )(?<!\bdesceu )(?<!\bdesce )(?<!\bvalorizou )(?<!\bdesvalorizou )(?<!\bganhou )(?<` +
  r`!\bperdeu )(?<!\baumentou )(?<!\bdiminuiu )(?<!\bexporta )(?<!\bimporta )(?<!\bexportou )(?<!\bimportou ` +
  r`)(?<!\bbem )(?<!\bcima )`
const ESCOLHA = r`(escolh\w*|prefer\w*|prefir\w*|melhor(es)?|pior(es)?)`
// Os tokens que MERCADOS['cripto'] conhece, mais o ticker SOL: a escolha entre eles é ranking (M2, N7).
const CRIPTO_NOME = r`(btc|bitcoins?|eth|ethereum|ethers?|xrp|solana|sol|usdt|usdc|tether|doge\w*|shiba|hash11|cardano|ada` +
  r`|pepe|bnb|litecoin|ltc)`
const SEM_CONCEITO_CRIPTO = r`^(?:(?=.*(?:${ESCOLHA_DITA}` +
  r`))|(?!.*\b(quanto (vale|valem|custa|custam|ta|esta)|cotac\w*|preco|diferenc\w*|o que (e|sao)|surgiu` +
  r`|surgiram|criad[oa]s?|lastread\w*|lastro|halving|primeiro)\b)).*?`
// Antes do infinitivo, a definição ("o que é zerar a posição?", "o que significa ter posição comprada?") é conceito (P5).
const CONCEITO_ANTES = r`(?<!\bque e )(?<!\bsao )(?<!\bsignifica )(?<!\bdizer )(?<!\bfunciona )(?<!\bque e ")`
// "o aumento das ações", "houve aumento": o substantivo, com artigo ou verbo antes.
const SEM_ARTIGO = r`(?<!\bo )(?<!\bum )(?<!\bhouve )(?<!\bteve )(?<!\bdo )(?<!\bno )(?<!\bao )(?<!\bpelo )(?<!\besse )(?<!\b` +
  r`este )`
// Classes de ativo, para o "X ou Y" do caso da pessoa (N5). "Banco central" e "um banco" não são o setor.
// A cripto entra no plural e pelo nome ("bitcoins ou tesouro?", "eth ou renda fixa?"), como a bolsa e o Ibovespa.
const CLASSE = r`(dolar|bolsa|ibovespa|cripto\w*|bitcoins?|btc|eth|ethereum|ethers?|solana|xrp|doge\w*|shiba|usdt|usdc` +
  r`|tether|stablecoins?|renda fixa|tesouro|acoes|ouro|poupanca|cdb|lci|lca|fiis?|petroleo|brent|petrobras` +
  r`|petr[34]|petroleiras?|bancos|de banco|bancari[ao]s?|acao|imove(l|is))(?! centra)`
// Pôr algo na declaração ou num documento do IR ("boto o bitcoin na declaração?", "coloco em bens e direitos?", "onde
// coloco o informe?", "onde ponho o código do DARF?") é regra de imposto (P5), não pôr o dinheiro num mercado.
const LUGAR_DO_IR = r`(em|na|no|nas|nos)( (qual|que|a|o))? (declaracao|ir|irpf|imposto de renda|ficha|bens e direitos` +
  r`|codigo)\b`
const DOC_DO_IR = r` (o |a |os |as |meu |minha |meus |minhas )?(informe|cpf|recibo|darf)\b`
const DECLARACAO = r`declarac\w*|declarar|irpf|darf|informes?|codigos?|fichas?|carne[- ]leao|bens e direitos` +
  r`|rendimentos? (isentos?|tributaveis|sujeitos)`
// A relação e o passado entre duas classes ("a gasolina segue o Brent ou o dólar?", "o Copom afeta o dólar ou o petróleo?",
// "o que subiu mais em 2022, petróleo ou dólar?"), o preço ("quanto vale o bitcoin ou o ether hoje?") e a regra ("o
// tesouro ou a petrobras são tributados igual?") não comparam para o caso da pessoa (N5). Com o caso dela ("pra me
// proteger", "pra mim", "agora", "qual pego") volta a ser comparar.
const _VERBO_REL = r`(segu(e|em|iu|iram)|acompanh(a|am|ou|aram)|depend(e|em|eu|eram)|mex(e|em|eu|eram)|afet(a|am|ou|aram)` +
  r`|influenci(a|am|ou|aram)|pes(a|am|ou|aram)|reag(e|em)|reagi(u|ram)|pux(a|am|ou|aram)` +
  r`|impact(a|am|ou|aram))`
const _MOV_PASSADO = r`(subiu|subiram|caiu|cairam|rendeu|renderam|valorizou|valorizaram|desvalorizou|desvalorizaram|variou` +
  r`|variaram|perdeu|perderam|ganhou|ganharam|disparou|despencou)`
const _ALT = r`(${CLASSE}|${EMPRESA_SEM_VALE})`
const _ALT_OU = r`\b${_ALT}\b[^,.;:?!]{0,25}\b(ou|x|vs|versus)\b[^,.;:?!]{0,25}\b${_ALT}\b`
const RELACAO_OU = r`\b${_VERBO_REL}\b[^,.;:?!]{0,25}${_ALT_OU}|\b(qual|quem|o que)\b[^.;:?!]{0,15}\b(${_VERBO_REL}|` +
  r`${_MOV_PASSADO})\b[^.;?!]{0,40}${_ALT_OU}|${_ALT_OU}[^.;?!]{0,5}\b(qual|quem)\b[^.;:?!]{0,15}\b(` +
  r`${_VERBO_REL}|${_MOV_PASSADO})\b`
const PRECO_OU_REGRA_DITA = r`\b(quanto (vale|valem|custa|custam|ta|esta)|cotac\w*|tributad\w*|tributac\w*|impostos?|isen\w*|declar\w*` +
  r`|aliquotas?)\b`
const PARA_O_CASO = r`\b(proteg\w*|protecao|hedge|pra mim|para mim|pra eu|para eu|meus?|minhas?|agora|(pra|para|em) 20(2[7-9]` +
  r`|[3-9]\d)|escolh\w*|prefer\w*|prefir\w*|pego|fico|carteira|investir|aplicar|apostar|melhor|pior)\b`
const SEM_RELACAO = r`^(?!(?!.*${PARA_O_CASO})(?=.*(?:${RELACAO_OU}|${PRECO_OU_REGRA_DITA})))`
export const PROIBIDOS = {
  // "O que eu faço?", "que que eu faço?", "o que fazer agora?", "preciso tomar uma decisão", "e agora?" pedem ação.
  // "O que fazer para entender o Copom?" não: é pedido de explicação.
  // "EUA proíbem a compra de petróleo russo" é a manchete: o substantivo depois do verbo de proibir ou liberar
  // "conselho" de órgão ("o conselho da Petrobras elegeu o Prates?", "Conselho Monetário") é fato, não dica
  // e o conselho que já decidiu ("o conselho aprovou dividendos?", "foi eleita pelo conselho"); "obrigado pelo conselho"
  // continua dica
  // pôr o dinheiro num mercado, na 1ª pessoa ("invisto em petróleo?", "reinvisto?", "coloco na bolsa?"), menos
  // "como eu coloco dinheiro na corretora?" (P5)
  // mover o dinheiro, na 1ª pessoa ("trago o dinheiro?", "troco?"), menos "como mando dinheiro pra fora?" (P5)
  // "como tiro meu bitcoin da exchange?" e "como tiro o informe da corretora?" pedem explicação (P5)
  // onde pôr o dinheiro ("recebi dividendos, onde ponho?"), mesmo sem valor
  // "que tal petrobras?" é pedir o juízo sobre o emissor (Mapa legal, seção 8, item 10)
  // o que fazer com a posição, preso à 1ª pessoa ou à posse ("mantenho PETR4?", "zero minha petrobras?")
  // ficar, continuar ou sair do papel, e dobrar a mão ("continuo com PETR4?", "saio da petrobras?", "boto mais?")
  // "se eu saio do Brasil, como fica o imposto?" é a regra de quem sai do país; "saio do Brasil?" sozinho é pedido
  // e as gírias do mesmo pedido ("shortar", "aporto", "hold petr4?", "vale continuar com petr4?", "pulo fora"), menos
  // a definição ("o que significa shortear?", "o que é dobrar a mão?", "como aportar na bolsa?")
  // a indicação de compra ou a "sua" ("qual a indicação pra PETR4?"), não a do governo ("qual a indicação do MME?")
  // o infinitivo só vale fora da definição ("o que é zerar a posição?" é conceito, P5)
  // "aumento" só como verbo: "o aumento das ações" e "houve aumento nas ações" são fato. Sem "petróleo": "a OPEP
  // decidiu reduzir a produção de petróleo" é fato.
  // "foi aumento?" e "foi redução ou aumento?" perguntam o que já saiu; "redução ou aumento?" sem marca de passado, ou
  // com futuro ("o próximo vai ser redução ou aumento?"), continua pedido
  // a posição da pessoa, não a "posição na pesquisa" nem a "posição em aberto" (conceito)
  // o tamanho e a melhor posição ("qual tamanho de posição no WIN?", "qual a melhor posição no WIN?"), menos a
  // definição, a posição de terceiros e a da pesquisa ("quem está em melhor posição na pesquisa?")
  // o verbo da 1ª pessoa com o "quando" ("realizo agora?", "zero hoje?"), menos o substantivo ("teve aumento hoje?")
  // "o que é oportunidade de arbitragem?" é conceito; com adjetivo ("é uma boa oportunidade?") é sempre pedido
  // "crise e oportunidade: o que a história mostra?" soma as duas palavras, não pede ("e" de somar, e o que vem é
  // pergunta de fato)
  // a oportunidade que já passou ("a pandemia de 2020 foi uma oportunidade na bolsa?") é passado (P1)
  // "o que é long ou short?", "o que significa ficar short?" e "o que é um investimento seguro?" são conceito (P5)
  // o juízo sobre o papel, sem mais nada ("petr4 é bom?", "PETR4 tá ótima?")
  // ter o papel ("é bom ter petr4?", "é bom ter ações da Petrobras?"): é o que fazer com ele (N1)
  // "embarco?" é ordem, como "entro"; "embarcar" sozinho não ("o Brasil vai embarcar petróleo")
  // "posso ir no bitcoin?", "vou ir na cripto agora?": é pôr o dinheiro nele (N1)
  // promessa de ganho ("dividendo é renda garantida?", M6), menos quem garante ("o CDB é garantido pelo FGC?", "o
  // bitcoin é garantido por alguma coisa?", "o dividendo mínimo é garantido na lei?") e o Tesouro ("o Tesouro Selic é
  // garantido?"), que é regra (P5)
  dica: r`(?<!\bproibem a )(?<!\bproibiu a )(?<!\bproibe a )(?<!\bsuspende a )(?<!\bsuspendeu a )(?<!\bveta a )(?<` +
    r`!\bvetou a )(?<!\blibera a )(?<!\bliberou a )(?<!\bautoriza a )(?<!\bautorizou a )\bcompr(a|o|ar|aria` +
    r`|ariam)\b|\bvend(e|o|er` +
    r`|eria)\b|\bentro\b|\bentrar\b|\bsair\b|\bcompens\w*|\bbora\b|\bdevo\b|\bdeveria\b|\bvale (a ?pena|mais` +
    r`|comprar)\b|\bfaz sentido\b|\beu (compre|venda)\b|\b(o que|que que|oq)( e que)?( eu)? (faco|fazer` +
    r`|faria)\b(?! (pra|para) (entender|saber|aprender|estudar|acompanhar|conhecer|ler|interpretar` +
    r`|compreender)\b)|\b(preciso|tenho que|tenho de|tenho|vou ter que) (de )?(tomar )?(uma )?(decisao` +
    r`|decidir)\b|\bme ajud(a|e|ar) a (tomar (uma )?decisao|decidir|escolher)\b|\bdecid(e|a|ir) (por|pra` +
    r`|para) mim\b|\be agora(\?|\W*$)|\bse fosse (voce` +
    r`|eu)\b|\bo que (voce )?faria\b|\brecomenda\w*|\bsugest\w*|\bdica\w*|(?:(?<!\bpelo )` +
    r`|(?<=\bobrigad[oa] pelo )` +
    r`|(?<=\bvaleu pelo ))\bconselho\w*\b(?! (de (administracao|adm)|monetario|fiscal|curador)\b` +
    r`| d[ao] (petrobras|petr[34]|empresa|estatal|bc|banco central|cvm|vale|prio3?|opep)\b` +
    r`| (ja )?(aprov(ou|aram|a|am)|eleg(eu|eram|e|em)|decid(iu|iram|e|em)|indic(ou|aram)|nome(ou|aram)` +
    r`|destitu(iu|iram)|demit(iu|iram))\b)|\bfico (comprado|vendido|de fora)\b|\bcomo (eu )?(abordo|opero` +
    r`|ganho)\b|\bestrategia\b|\bposicion\w*|\bexposicao\b|\baplicar\b|\binvestir\b|\bbuy\b|\bsell\b` +
    r`|\bshould i\b|\bwould you\b|(?<!como )(?<!como eu )\b(re)?(invisto|aplico)\b` +
    r`|(?<!como )(?<!como eu )\b(coloco|ponho|boto)\b(?!${DOC_DO_IR})[^.?!]{0,30}\b(?!(?<=tenho )em casa\b)(?!` +
    r`${LUGAR_DO_IR}` +
    r`)(em|na|no|nas|nos)\b|(?<!como )(?<!como eu )\b(troco|trago|mando|envio|converto|transfiro` +
    r`|remeto)\b|\bdeixo (la|aqui|parado|onde esta)\b|(?<!como )(?<!como eu )(?<!onde )(?<!onde eu )\b(tiro` +
    r`|boto|deixo|guardo)\b[^.?!]{0,40}\b(exchange|corretora|carteira|${EXCH}` +
    r`)\b|\bonde (eu )?(ponho|coloco|boto)\b(?!${DOC_DO_IR})(?![^.?!]{0,40}\b(${DECLARACAO}` +
    r`|n[oa] (ir|imposto de renda))\b)|\bonde (eu )?(invisto|aplico|reinvisto|reinvesto)\b|\breinvesto\b` +
    r`|\bque tal\b (a |o |as |os )?(acoes (da |do )?)?${EMPRESA}` +
    r`\b|(?<=.{10})\be ai(\?|\W*$)|\bconviene\b|\b(debo|deberia) (cambiar|traer|mandar|enviar)\b|\bmantenho\b` +
    r`|\bsegur(o|ar)\b (a |o )?(minha|meu|minhas|meus|posicao|${PETR}` +
    r`|acao|acoes|papel|papeis)\b|\b(vale|devo|compensa|deveria) (segurar` +
    r`|manter)\b|\bvale (a ?pena )?manter\b|\b(continuo|fico|sigo) (com|n[ao]|em) (a |o |as |os )?${ATIVO}` +
    r`\b|\bsaio\b(?! (d[oe]|da) (brasil|pais|emprego|trabalho|casa)\b(?!\W*$|,? (e|ou|agora|ja|hoje|logo)\b))` +
    r`|\b(to|tou|estou|fiquei) (comprado|vendido|posicionado)\b|${CONCEITO_ANTES}` +
    r`\bdobr(o|ar|aria) (a )?(mao|posicao)\b|\b(boto|ponho|coloco) mais\b|${CONCEITO_ANTES}` +
    r`\b(shorte\w*|short(o|ar|aria|ando|ei))\b|\bcaio fora\b|(?<!como )(?<!como eu )\baport(o|amos)\b` +
    r`|\bfaco (um |o )?aporte\b|${CONCEITO_ANTES}${SEM_ARTIGO}` +
    r`(?<!como )\baport(ar|aria|e)\b( mais)? (em|na|no|nas|nos) (a |o |as |os )?${ATIVO}` +
    r`\b|^\W*(mantem|mantenha|segura|segure|hold|holda|carrego)\b[^.?!]{0,15}\b${ATIVO}\b|${CONCEITO_ANTES}` +
    r`\bhold(o|ar|ando)\b|\bcarrego\b[^.?!]{0,15}\b${ATIVO}` +
    r`\b|\bvale (continuar|carregar)\b|\bvale ficar (com|n[ao]s?|em|de fora|comprado|vendido)\b` +
    r`|\bvale ter\b[^.?!]{0,20}\b${ATIVO}` +
    r`\b|\bcontinua valendo (a pena|ter|manter|ficar|segurar|carregar)\b|\bpulo fora\b|\bpular fora d[aeo]s? ` +
    r`${ATIVO}` +
    r`\b|\bqual (e )?(a )?(sua |tua )?indicac(ao|oes)\b(?! d[oa] (governo|mme|ministerio|conselho|presidente` +
    r`|lula|bolsonaro|uniao` +
    r`|controlador)\b)|\bindicac(ao|oes) de (compra|venda)\b|\bzer(o|ei)\b (a |o |as |os )?(minha|meu|minhas` +
    r`|meus|posicao|tudo|${PETR}|acoes)\b|${CONCEITO_ANTES}` +
    r`\bzerar\b (a |o |as |os )?(minha|meu|minhas|meus|posicao|tudo|${PETR}|acoes)\b|(?:${SEM_ARTIGO}` +
    r`\baumento\b(?! (d[aeo]s?|n[ao]s?)\b)|\b(reduzo|diminuo|realizo)\b|${CONCEITO_ANTES}` +
    r`\b(aumentar|reduzir|diminuir|realizar)\b)[^.?!]{0,20}\b(posicao|lucro|${PETR}|acoes|minha|meu)\b|` +
    r`${SEM_ARTIGO}` +
    r`(?<!\bfoi )(?<!\bera )(?<!\breducao ou )(?<!\bcorte ou )\b(aumento|reduzo|diminuo|realizo)\W*$` +
    r`|^(?:(?=[\s\S]*\b(?:vai|vao|sera|serao|proxim\w*|amanha)\b)|(?![\s\S]*\b(?:foi|foram|era|teve|tiveram` +
    r`|houve|ultim[oa]|ontem|anunciou|saiu` +
    r`|veio)\b))[\s\S]*\b(?:reducao|corte) ou aumento\W*$|\b(minha|meu) posicao\b|${CONCEITO_ANTES}` +
    r`\b(tenho|ter|to com|tou com|estou com|fiquei com|eu com|abro|monto)( uma| a)?( pequena| grande` +
    r`| boa)? posicao\b|\bvale (ter|considerar|abrir|montar|fazer)\b[^.?!]{0,20}\bposicao\b|^\W*posicao (em|na` +
    r`|no)\b|${CONCEITO_ANTES}` +
    r`(?<!\bque e o )(?<!\bsignifica o )\btamanho( ideal| certo| bom| maximo)? (de|da` +
    r`|do) posicao\b(?! d[aeo]s? (estrangeir|investidor|fundo|banco|gringo|institucion|pessoa|varejo))|\b(qual` +
    r`|que)( e)?( a)? ((melhor|pior) posicao` +
    r`|posicao (ideal|certa|correta))\b(?![^.?!]*\b(pesquis\w*|ranking|corrida|disputa|turno|eleic\w*` +
    r`|candidat\w*|tabela|classifica\w*)\b)(?! d[aeo]s? )|\bquanto (colocar|botar|alocar|aplicar` +
    r`|ter)\b[^.?!]{0,20}\bposicao\b|${SEM_ARTIGO}` +
    r`(?<!\bem )(?<!\ba )(?<!\bde )(?<!\bda )\b(aumento|reduzo|diminuo|realizo|zero) (agora|hoje|ja` +
    r`|amanha)(\W*$| ou\b)|\bdou uma (reduzida|aumentada|zerada|realizada|diminuida|enxugada` +
    r`|segurada)\b|\b(faco|fazer|faria|vale fazer) (o |um )?(preco medio|pm)\b|\baproveit(o|ar|aria) (a|o|essa` +
    r`|esse|esta|este)? ?(queda|alta|baixa|subida|desconto|tombo|crise|guerra)\b|(?<!\bo que )(?<!\boq )\b(e` +
    r`|seria) (uma )?oportunidade\b(?![:;,] (o que|qual|como|quando|por que)\b)|\b(e|seria) (uma )?(boa|otima` +
    r`|grande) oportunidade\b(?![:;,] (o que|qual|como|quando|por que)\b)|[,;:] ?(uma )?(boa |otima ` +
    r`|grande )?oportunidade\W*$|\boportunidade (de|pra|para) (compra|entrada|comprar|entrar|vender|lucro` +
    r`|ganh\w*)\b|(?<!\bfoi uma )(?<!\bfoi )(?<!\bcriou )(?<!\bcriou uma )(?<!\bteve )(?<!\bhouve )(?<!\bgerou` +
    r` )(?<!\bgerou uma )\boportunidade (n[ao]|em) (a |o |as |os )?${ATIVO}` +
    r`\b|\b(bom|otimo|melhor|pior) momento\b|(?<!\bfoi o )\bmomento (certo|ideal)\b|\b(boa|otima) hora\b` +
    r`|\b(ta|esta|e|chegou) (na )?(hora|momento) de\b(?! (entender|aprender|estudar|compreender|ler` +
    r`|interpretar)\b)|(?<!\bo que e )(?<!\bo que sao )\b(long ou short|short ou long)\b` +
    r`|(?<!\bsignifica )(?<!\bo que e )\b(fico|ficar|entro|vou) (long|short)\b` +
    r`|(?<!\bo que e )(?<!\bo que e um )(?<!\bo que seria um )\binvestimento (seguro|bom|ruim|arriscado)\b|\b` +
    r`${EMPRESA}` +
    r` (e|ta|esta) (um |uma )?(bom|boa|otim[oa])( (papel|acao|investimento|compra|empresa))?\W*$` +
    r`|\b(bom|boa|otimo|ruim|interessante) ter (a |o |as |os )?((acoes|acao|papeis|papel) d[aeo] )?` +
    r`${EMPRESA_SEM_VALE}` +
    r`\b|\b(posso|quero|vou|devo|bom|vale)( eu)? ir (no|na|pro|pra|pros|pras|para o|para a) (${ATIVO}|` +
    r`${CRIPTO_NOME}` +
    r`)\b|\bembarc(o|amos)\b|\b(vale|da (pra|para)) embarcar\b|\bembarcar (nessa|nesse|agora` +
    r`|ja)\b|\bbtfd\b|(?<!\bpoupanca e )(?<!\bcdb e )(?<!\blci e )(?<!\blca e )(?<!\bdeposito e )(?<!\btesouro` +
    r` e )(?<!\btesouro selic e )(?<!\btesouro direto e )(?<!\btesouro ipca e )(?<!\btesouro ipca\+ e )(?<!\bt` +
    r`esouro prefixado e )\bgarantid[oa]s?\b(?! (pel[oa]|por) (fgc|governo|tesouro|lei|uniao|b3|banco central` +
    r`|bc|alguma coisa|algo|quem)\b| pelo que\b| (na|em) lei\b)`,
  direcao: r`\bvai (subir|cair|disparar|despencar|bombar|valorizar|explodir|fechar|abrir)\b|\bvao (subir|cair)\b` +
    r`|\bchances?\b|\bprobabilidad\w*|\bde 0 a 100\b|\bum numero\b|\btendencia\b` +
    r`|\bpode (subir|cair|disparar)\b|\bsobe ou (cai|desce|nao)\b|\balavanc(ar|a)\b|\bpotencial\b|\bprevisao\b` +
    r`|\bprever\b|\bdisparar\b`,
  // "Brent caiu 10% hoje, é a hora?", "perdi o bonde?", "ainda dá tempo?"; não "qual é a hora da decisão do Copom?"
  // nem "é a hora de entender a Selic?"
  // "tá na hora da prio?", "está na hora do bitcoin?" e "tá na hora?" são o mesmo pedido
  // "petróleo caiu, é o momento?", "é hora?", "qual seria a hora certa?", "é o momento do bitcoin?"; não "o Copom
  // disse que é o momento de cautela?" nem "qual é a hora certa da decisão do Copom?"
  // o prazo do imposto e do cartório eleitoral é calendário, não entrada (P5): "ainda dá tempo de declarar o
  // bitcoin no IR?", "... de pagar o DARF?", "... de mudar o domicílio eleitoral?"; "de transferir o dinheiro" não
  momento: r`\bstop\b|\balvo\b|\bponto de (entrada|saida)\b|\bquando (entrar|sair|comprar|vender)\b` +
    r`|\b(hora|quando)\b.{0,15}\b(entrar|sair|comprar|vender|operar)\b|\balertas?\b|\bme avis(a|e)\b` +
    r`|\bsinal de\b|\bamanha\b|\bna abertura\b|\bsegunda(-feira)?\b.{0,30}\b(fazer|compr\w*|vend\w*|entr\w*)` +
    r`|(?<!qual )(\b(e|seria|sera|chegou)( agora| ja)? a|\b(ta|esta)( agora| ja)? na) hora\b(?! (de|pra` +
    r`|para) (entender|saber|aprender|estudar|acompanhar|conhecer|ler|interpretar` +
    r`|compreender)\b| da verdade\b| d[aeo] (decisao|divulgacao|reuniao|copom|ata|abertura|fechamento|votacao` +
    r`|eleicao|apuracao|anuncio` +
    r`|leilao)\b)|\bperdi (o|a) (bonde|trem|timing|momento|onda)\b|\bqual (seria |e |sera )?a hora (certa` +
    r`|ideal)\W*$|(?<!qual )(?<!o que )(?<!oq )(?<!como )\b(e|seria|sera|chegou)( agora| ja)? (o momento` +
    r`|hora)(?=\W*$|\s*[?!.,;]| (d[aeo]s?|n[ao]s?|em|pra|para|pro) (a |o |as |os )?(${ATIVO}|${CLASSE}` +
    r`)\b)|\bainda da tempo\b(?! (de|pra|para) (entender|saber|aprender|estudar|ler|ver|assistir|acompanhar` +
    r`|votar|declarar|retificar|justificar|(se )?alistar)\b| (de|pra|para) (entregar|corrigir|fazer|pagar` +
    r`|pedir|acertar|regularizar|emitir|gerar|recolher|tirar|transferir|mudar) (a |o |as |os |minha |meu ` +
    r`|minhas |meus )?(declarac\w*|imposto|ir|irpf|darf|guia|restituic\w*|carne-leao` +
    r`|titulo( de eleitor)?(?! d[eo] tesouro)|domicilio|local de votacao|zona eleitoral)\b)`,
  capital: r`\br\$ ?\d|\b\d+ ?mil reais\b|\b\d+ ?k\b` +
    r`|\b(um|dois|tres|quatro|cinco|seis|sete|oito|nove|dez|vinte|trinta|cinquenta|cem) mil( reais)?\b` +
    r`|\btenho (r\$ ?)?\d+[\d.,]* ?(mil|k|reais|conto|contos|pila|paus)\b|\bquantos contratos\b` +
    r`|\bquanto (eu )?(coloco|ponho|invisto|aplico|boto|devia ter|deveria ter)\b|\bquanto investir\b` +
    r`|\bmeu (capital|dinheiro|patrimonio|salario)\b|\bminha (renda|carteira|reserva)\b|\bganho \d+` +
    r`|\bpor mes\b|\bsalario\b|\bcom \d+[\d.,]* ?(conto|contos|pila|paus)\b` +
    r`|\bcom \d+[\d.,]* ?reais\b(?=[^.?!]{0,30}\b(da (pra|para)|consigo|comec\w*|invest\w*|aplic\w*|compr\w*` +
    r`|entr(o|ar)|oper(o|ar))\b)`,
  // a idade e a adequação de um terceiro ("minha mãe tem 70 anos, serve pra ela?") e o objetivo de renda.
  // "bom pra ela" sozinho fica de fora: costuma ser a empresa ("o Brent alto é bom pra ela, a Petrobras?")
  // a adequação a um grupo, menos o material de estudo ("que livro é indicado pra iniciante?")
  perfil: r`\barrojad\w*|\bconservador\w*|\bmoderad[oa]\b|\btolerancia (a|ao) risco\b|\bperfil\b|\baposentadoria\b` +
    r`|\breserva de emergencia\b|\bserve (pra|para) mim\b|\be (pra|para) mim\b|\bminha idade\b` +
    r`|\btenho \d+ anos\b|\bmeu objetivo\b|\bmeu prazo\b|\b(minha|meu|ela|ele)\b[^.?!]{0,25}\btem \d+ anos\b` +
    r`|\b(serve|servem|indicad[oa]s?|adequad[oa]s?) (pra|para) (mim|ela|ele|eles|elas|minha|meu|minhas|meus)\b` +
    r`|\b(bom|boa|bons|boas|ideal) (pra|para) (mim|minha|meu|minhas|meus)\b` +
    r`|\b(meu|minha) (avo|vo|vovo|pai|mae|filh[oa]|tio|tia|esposa|marido|sogr[oa])\b[^.?!]{0,20}\b(de` +
    r`|com) \d+ anos\b|^(?!.*\b(livros?|cursos?|canal|canais|sites?|apps?|aplicativos?|podcasts?|videos?` +
    r`|conteudos?|materia(l|is)|leituras?` +
    r`|aulas?)\b).*\b(indicad|adequad|recomendad)[oa]s? (pra|para) (quem|iniciantes?|idos[oa]s?` +
    r`|aposentad[oa]s?|jovens?)\b|\bviver d(e|os|as) (dividendos?|proventos?|renda|juros)\b`,
  // "o dólar foi melhor que a bolsa em 2022?" é passado
  // mais seguro ou mais arriscado entre duas classes ("renda fixa é mais segura que ações?"); o mini-índice
  // (derivativo) e "os bancos estão mais sólidos que em 2015?" ficam de fora (L18 da rodada 2)
  // o mini-dólar não é o dólar ("o mini-dólar é mais arriscado que o dólar à vista?" é conceito, D4)
  // uma empresa contra uma classe ("PETR4 x dólar", "brava ou tesouro?", "petrobras ou ibovespa?")
  // a escolha entre empresa e classe com "entre ... e" ("qual é melhor entre petrobras e dólar?", "entre
  // petr4 e bitcoin, qual escolho?"); "qual a relação entre a Petrobras e o petróleo?" não escolhe
  // o rendimento que ainda vem ("petrobras rende mais que o cdb?"); "rendeu mais" é passado
  comparar: r`\bmelhor\b.{0,40}\bou\b|\bou\b.{0,40}\b(qual )?(o |a )?melhor\b|\bvale mais\b|${SEM_RELACAO}` +
    r`${SEM_CONCEITO_CRIPTO}${SEM_DIFERENCA}\b${CLASSE}\b.{0,25}${OU_ATIVO}\b(ou|x|vs|versus)\b.{0,25}\b` +
    r`${CLASSE}\b|\b${CLASSE}` +
    r`\b.{0,30}(?<!\bfoi )(?<!\bforam )(?<!\bera )(?<!\beram )\b(melhor|pior)(es)? (do )?que\b` +
    r`|(?<!\bmini )(?<!\bmini-)\b${CLASSE}` +
    r`\b.{0,30}(?<!\bficou )(?<!\bficaram )(?<!\bfoi )(?<!\bera )\b(mais|menos) (segur|solid` +
    r`|arriscad)[ao]s? (do )?que (o |a |os |as )?${CLASSE}\b|${SEM_RELACAO}${SEM_DIFERENCA}\b` +
    r`${EMPRESA_SEM_VALE}\b.{0,25}${OU_ATIVO}\b(ou|x|vs|versus)\b.{0,25}\b${CLASSE}\b|${SEM_RELACAO}` +
    r`${SEM_DIFERENCA}\b${CLASSE}\b.{0,25}${OU_ATIVO}\b(ou|x|vs|versus)\b.{0,25}\b${EMPRESA_SEM_VALE}\b|\b` +
    r`${ESCOLHA}\b.{0,30}\bentre (a |o )?(${EMPRESA_SEM_VALE}\b.{0,25}\be (a |o )?${CLASSE}|${CLASSE}` +
    r`\b.{0,25}\be (a |o )?${EMPRESA_SEM_VALE})\b|\b(${EMPRESA_SEM_VALE}\b.{0,25}\be (a |o )?${CLASSE}|` +
    r`${CLASSE}\b.{0,25}\be (a |o )?${EMPRESA_SEM_VALE})\b.{0,30}(?:${ESCOLHA_DITA}|\bqual\W*$)|\b` +
    r`${EMPRESA_SEM_VALE}\b.{0,20}\brende(m|ria)? mais (do )?que\b`,
  // escolher entre empresas ou tickers ("PETR4 ou PRIO3?", "PRIO é melhor que a Petrobras?", "A Exxon é melhor que
  // a Petrobras?", "Which is better, Petrobras or Prio?") é ranking (M2)
  // "Petrobras e Prio: qual escolher?", "Entre Petrobras e PRIO, qual?"
  // "qual a melhor?", "qual vc escolheria?", "qual você pegaria?", "qual rende mais?"; não "qual o melhor jeito de
  // comparar os balanços?" nem "qual melhor pra entender o setor?" (P5)
  // "qual é melhor entre petrobras e prio?", com a escolha antes do "entre"
  // trocar um papel por outro ("vale trocar PETR4 por PRIO3?", "posso trocar PETR3 por PETR4?")
  // o mesmo entre criptos ("BTC ou ETH?", "USDT ou USDC?", "ETH é melhor que BTC?"): indicar token (N7)
  // O preço e o conceito ("quanto vale o bitcoin ou o ether hoje?", "qual surgiu primeiro, btc ou eth?", "o usdt ou o
  // usdc é lastreado em dólar?", "o btc ou o eth tem halving?") não escolhem; o passado ("foi melhor") também não.
  // "o que é boa pagadora de dividendos?" é conceito (P5)
  // "o que é dividend yield alto?" é conceito (P5)
  // "mais sólida" só na escolha ("qual petroleira é mais sólida?"); "por que o mini-índice é mais arriscado?" e
  // "o que torna o mini-dólar mais arriscado?" são conceito (D4)
  // o superlativo: "é a mais segura?"
  // "a Petrobras ficou mais sólida depois de 2016?" é passado; sem a data ("PETR4 ficou mais arriscada?") continua
  ranking: r`\branking\b|\bmelhores (acoes|ativos|moedas|criptos)\b|\btop ?\d+\b|\bmonta (uma )?carteira\b` +
    r`|\bcarteira (recomendada|sugerida|ideal)\b|\bquais (acoes|ativos)\b` +
    r`|\bqual (acao|ativo|papel|moeda|cripto)\b|\bque acao\b|\bsobe mais\b|\bmais se benefici\w*` +
    r`|\bmelhor (acao|ativo|cripto|moeda)\b|${SEM_DIFERENCA}\b${EMPRESA}\b.{0,25}${OU_ATIVO}` +
    r`\b(ou|or|x|vs|versus)\b.{0,25}\b${EMPRESA}\b|\b${EMPRESA}` +
    r`\b.{0,30}\b(e )?melhor (do )?que\b|\b(melhor (do )?que|better than) (a |o |the )?${EMPRESA}` +
    r`\b(?! (pra|para) (entender|saber|aprender|estudar|acompanhar|conhecer|ler|interpretar|compreender)\b)|\b` +
    r`${EMPRESA}\b.{0,25}\b(e|and)\b.{0,25}\b${EMPRESA}` +
    r`\b.{0,30}(\bqual( (delas|deles|das duas|dos dois))?\W*$|\bqual( (delas|deles|das duas|dos dois))? (e ` +
    r`|seria )?(a |o )?melhor\b(?! (jeito|forma|maneira|fonte|site|livro|lugar|ano|trimestre)\b` +
    r`| (pra|para) (entender|saber|aprender|estudar|acompanhar|conhecer|ler|interpretar|compreender` +
    r`|comparar)\b)|\bqual( (delas` +
    r`|deles))? (eu )?(escolh\w*|prefir\w*|pego|pegaria|fico|ficaria)\b|\bqual( (delas` +
    r`|deles))? (vc|voce|tu) (escolh\w*|prefer\w*|peg(a|ar|aria)|fica|ficaria)\b|\bqual( (delas` +
    r`|deles))? rende mais\b)|${SEM_DIFERENCA}\b(qual|quais|${ESCOLHA.slice(1, -1)})\b.{0,30}\bentre (a |o )?` +
    r`${EMPRESA}\b.{0,25}\be (a |o )?${EMPRESA}\b|\btroc\w*\b[^.?!]{0,15}\b${EMPRESA}` +
    r`\b[^.?!]{0,10}\bpor\b[^.?!]{0,10}\b${EMPRESA}\b|${SEM_CONCEITO_CRIPTO}\b${CRIPTO_NOME}` +
    r`\b.{0,25}\b(ou|x|vs|versus)\b.{0,25}\b${CRIPTO_NOME}\b|\b${CRIPTO_NOME}` +
    r`\b.{0,30}(?<!\bfoi )(?<!\bforam )(?<!\bera )(?<!\beram )\b(e )?melhor (do )?que\b|\b${CRIPTO_NOME}` +
    r`\b.{0,30}\b(mais|menos) (segur|solid|arriscad)[ao]s? (do )?que (o |a )?${CRIPTO_NOME}` +
    r`\b|\b(qual|que) (e )?(a )?(melhor |mais \w+ )?petroleiras?\b|\bmelhor(es)? petroleiras?\b` +
    r`|\bpaga(m)? mais (dividendos?|proventos?)\b` +
    r`|(?<!\bo que e )(?<!\bo que e uma )(?<!\bo que e ser )(?<!\bsignifica )(?<!\bsignifica ser )\b(boa|otima` +
    r`|melhor|grande) pagadora\b|\bpaga(m)? (bem|muito|bons|otimos|altos) (dividendos?` +
    r`|proventos?)\b|\bpaga(m)? (dividendos?|proventos?) (altos?|bons?` +
    r`|gordos?)\b|(?<!\bque e uma )(?<!\bque e a )(?<!\bsignifica )(?<!\bsignifica uma )\bvaca leiteira\b` +
    r`|(?<!\bo que e )(?<!\bo que e um )(?<!\bo que e o )(?<!\bsignifica )(?<!\bsignifica um )\b(dividend yiel` +
    r`d|dy)\b[^.?!]{0,30}\b(alto|alta|baixo|baixa|bom|boa|ruim|atrativ\w*|muito` +
    r`|pouco)\b|(?<!\bpor )(?<!\bo )\b(qual|quais)\b[^.?!]{0,30}\b(mais|menos) (solid|segur` +
    r`|arriscad)[ao]s?\b|\b(e|seria|ser|sao) (o|a|os|as)( \w+)? (mais|menos) (solid|segur` +
    r`|arriscad)[ao]s?\b|\b(${EMPRESA}` +
    r`|petroleiras?)\b[^.?!]{0,30}(?<!\bficou )(?<!\bficaram )(?<!\bfoi )(?<!\bera )(?<!\beram )(?<!\bestava )` +
    r`\b(mais|menos) (solid|segur|arriscad)[ao]s?\b|\b(${EMPRESA}` +
    r`|petroleiras?)\b[^.?!]{0,30}\b(ficou|ficaram|foi|era|eram|estava) (mais|menos) (solid|segur` +
    r`|arriscad)[ao]s?\b(?![^.?!]{0,30}\b(depois d[aeo]s?|desde|em (19|20)\d\d|antes d[aeo]s?)\b)`,
  seletivo: r`\bso (os|as) (casos|vezes|anos|eleicoes|reunioes|dias|turnos)\b|\bso (as )?altas\b|\bso os positivos\b` +
    r`|\bmostra so\b|\bmostra apenas\b|\bapenas (os|as) (casos|turnos|vezes)\b` +
    r`|\b(so|apenas) (a|as) (mediana|media|altas|quedas)\b`,
  // avaliar uma corretora citada pelo nome ou apontada ("a Binance é segura?", "a Coinbase é regulamentada?
  // posso confiar?", "é seguro deixar na Binance?") também é indicar (N7)
  // Também "tem segurança?", "é de confiança?", "é furada?", "presta?", "vale a pena?", "é boa?" e a ordem inversa
  // ("é confiável a coinbase?"). "Segurou os saques", "confirmou o acordo" e "boa parte das exchanges" são fato.
  // escolher entre corretoras ("Binance ou Mercado Bitcoin?"), usar, abrir conta ou deixar o dinheiro numa delas
  // "Uso a Binance ou a Foxbit?", com a corretora no fim; não "Uso a Binance, como declaro o imposto?"
  plataforma: r`\bqual (a )?(melhor )?(exchange|corretora|plataforma|app)\b|\bonde (eu )?(compro|opero|abro conta)\b` +
    r`|\bque (exchange|corretora)\b` +
    r`|\bindic(a|ar|aria|am) (uma |um |a |o )?(exchange|corretora|plataforma|app)\b|\b${EXCH}` +
    r`\b.{0,80}\b(segur[ao]s?|seguranca|confiave(l|is)|confianca|confi(o|ar)|golpe|furada|presta` +
    r`|vale a pena)\b|\b${EXCH}` +
    r`\b[^.?!]{0,30}\b(e|ta|esta) (uma )?((exchange|corretora) )?(boa|bom|ruim|melhor|pior|top|seria|serio` +
    r`|idone[ao]|arriscad[ao]|piramide|de boa)\b(?! parte\b)|\b(segur[ao]s?|seguranca|confiave(l|is)|confiar` +
    r`|confio|confianca|golpe|furada)\b[^.?!]{0,40}\b${EXCH}` +
    r`\b|\b(essa|esta|nessa|nesta) (corretora|exchange|plataforma|app)\b[^.?!]{0,20}\b(segur[ao]|confiavel` +
    r`|golpe|boa|ruim|furada|presta)\b|\bconfi(o|ar) (nessa|nesta) (corretora|exchange|plataforma|app)\b|\b` +
    r`${EXCH}\b[^.?!]{0,30}\b(ou|x|vs|versus)\b[^.?!]{0,30}\b(${EXCH}` +
    r`|outra|corretora|exchange)\b|\b(corretora|exchange)\b[^.?!]{0,30}\b(ou|x|vs|versus)\b[^.?!]{0,30}\b` +
    r`${EXCH}` +
    r`\b|\b(abr(o|ir|iria) (uma )?conta|(crio|criar|criaria|faco|fazer|faria) (uma )?conta|cadastr\w*|deix(o` +
    r`|ar)|guard(o|ar)|confi(o|ar)|recomenda\w*)\b[^.?!]{0,30}\b${EXCH}\b|\b(uso|usar)\b[^.?!]{0,15}\b${EXCH}` +
    r`\W*$`,
  aposta: r`\bapost\w*|\baposto\b|\bbets?\b|\bpolymarket\b|\bkalshi\b|\bvpn\b`,
  voto: r`\bem quem\b|\bquem e (o )?melhor\b|\bmelhor candidato\b|\bdevo votar\b` +
    r`|\bquem (voce|vc) (apoia|prefere)\b` +
    r`|\bmelhor (pra|para) (a |o )?(economia|bolsa|mercado|pais|brasil|investidor)\b|\bmercado prefere\b` +
    r`|\b(pior|ruim|bom|boa) (pra|para) (a |o )?(bolsa|economia|mercado)\b|\bquem o mercado (quer|prefere)\b` +
    r`|\bquebra o pais\b|\bvoce (vota|votaria|apoia|prefere)\b`,
  // Trocar de papel ou tirar o aviso. "Só entre nós" não é troca de papel: a pergunta que vem depois é que pede recusa.
  papel: r`\bfinj\w*|\bfinge\b|\bfaz de conta\b|\bimagin(e|a) que (voce|vc)\b` +
    r`|\b(voce|vc) e (um )?(analista|consultor|trader)\b|\bcomo (um )?analista\b` +
    r`|\bignor(e|a|ar) (as |os |o )?(regras|instrucoes|avisos?)\b|\bsem (o |os )?avisos?\b` +
    r`|\besquec\w* (as |os |o |das |dos |do )?(regras|instrucoes|avisos?)\b` +
    r`|\btir(a|e|ar) (o |os |esse |esses )?avisos?\b` +
    r`|\bcomo se (voce )?fosse (um|uma|meu|minha) (amig[oa]|analista|consultor\w*|trader|assessor\w*|gerente` +
    r`|especialista)\b|\bcomo (um|uma|meu|minha) amig[oa]\b|\bsem rodeio\w*|\bmodo (desenvolvedor|dev|livre` +
    r`|dan|sem filtro)\b|\bjailbreak\b|\bvoce (agora )?e (o` +
    r`|a) [a-z]+|\bsem filtros?\b|\bpode pular\b|\bassumo (toda |total ` +
    r`|a )?responsabilidade\b|\bpara um (livro|roteiro|trabalho|filme` +
    r`|conto)\b|\bhipotetic\w*|\bhypothetical\b|\bimagina um cenario\b|\bnum cenario\b|\bnum mundo\b` +
    r`|\bpersonagem\b|\bpretend\b|\bja li (todos )?os avisos\b|\b(ja )?sei (os|dos) riscos\b` +
    r`|\bpela ultima vez\b|\bja perguntei\b`,
  binaria: r`\biq ?option\b|\bopc(ao|oes) binarias?\b|\bbinarias\b`,
  chance_candidato: r`\bquem (vai )?(ganha|ganhar|vence|vencer)\b` +
    r`|\bchances? (de|do|da|de o|de a) (ele|ela|o candidato|candidato|flavio|lula|bolsonaro) (ganhar|vencer` +
    r`|levar)\b|\bfavorit\w*|\bchances? de vitoria\b|\bquais (as` +
    r`|sao as) chances\b|\breeleit\w*|\beurasia\b|\b(vence|vencer|ganha|ganhar|leva|levar)\b.{0,20}\b(domingo` +
    r`|eleicao|segundo turno|2o turno)\b|\bprobabilidade d[oea] (lula|flavio|bolsonaro|ele|ela)\b|\bquem (ta` +
    r`|esta) na frente\b|\b(lula|flavio|bolsonaro) (vence|ganha|leva)\b`,
  // os sinônimos ("dá pra enriquecer com bitcoin?", "ficar milionário", "fazer fortuna", "viver de bitcoin")
  chance_dinheiro: r`\bchances? de (eu )?(ganhar|lucrar)\b|\bganhar dinheiro\b|\bvou lucrar\b|\bda (pra|para) lucrar\b` +
    r`|\bquanto (eu )?ganho\b|\bquais (as|sao as) chances\b|\bganhar ou (nao|perder)\b` +
    r`|\bganha(r)? (uma )?grana\b|\blucr\w*|\brenda (mensal|extra)\b|\bficar rico\b|\benriquec\w*` +
    r`|\bficar milionari\w*|\bfazer (uma )?fortuna\b|\bviver de (bitcoin|btc|cripto\w*|trade|day ?trade)\b` +
    r`|\bdeixa\w* (alguem|a gente|eu) ric[oa]\b`,
} satisfies Record<string, string>
// O prazo que ainda vem ("até dezembro", "no Natal", "daqui a 6 meses", "by Christmas"). "Até dezembro de 2025", "no
// Natal de 2020" e "o fim do ano passado" são passado.
const MESES = r`(janeiro|fevereiro|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)`
const PRAZO = r`(\bate (o )?(` +
  MESES.slice(1, -1) +
  r`|natal|carnaval|fim|final)\b|\b(no|pro|para o|pelo) (natal|fim do ano|final do ano|fim do mes` +
  r`|final do mes)\b)(?! (de ` +
  r`|do ano de )?(20)?\d\d\b| passado\b)|\b(ano|mes|semestre) que vem\b|\bproximo (ano|mes|semestre)\b` +
  r`|\bdaqui (a\b|\d|uns?\b|umas?\b)|\bby (christmas|year[- ]end|the end of|end of)\b` +
  r`|\bnext (year|month|week)\b`
// Um nível de preço (ou o preço) seguido de um prazo que ainda vem.
// O ano que já passou depois de "em/de" ("quanto o Ibovespa caiu em 2008 até o fim do ano?") não é nível; com moeda, ou
// depois de "a/to/at" ("eth a 2000 até o fim do ano?"), é. A elipse com "nos/aos/na casa dos" ("brent nos 200 até o fim
// do ano?") também é nível.
const NIVEL_PRAZO = r`(\b(a|to|at|nos|aos|(na )?casa d[oa]s)( us\$| r\$| \$|\$)? ?\d|\b(em|de)(( us\$| r\$| \$|\$) ?| (?!(19` +
  r`|20)\d\d\b))\d|\b(brent|wti|barril|petroleo|oil|dolar|euro|ibovespa|bitcoin|btc|gasolina|diesel) (us\$ ?` +
  r`|\$)?\d|\b\d[\d.,]* ?(dolares|dolar|reais|mil|k)\b|\b(preco|cotacao|valor|price)\b)[^.?!]{0,40}(` +
  PRAZO +
  r`)`
// Nível de preço no futuro ("vai a 150?", "chega nos 200?", "volta pros 70?", "rompe 120?", "bate na casa dos 150?", "vai
// a R$ 50?"): termina no 1º dígito, para valer com "150k" e "250 mil". Fica de fora o passado ("passou de", "chegou a",
// "atingiu"), o prazo ("chega em 2 dias"), o ano ("chega em 2027"), o ordinal ("rumo ao 2º turno"), a regra ("vendas que
// chegam a 35 mil") e o "conseguiu voltar a 100 mil em 2020" (passado).
// O infinitivo "ir a/pra" ("pode ir a 200?", "o ibovespa pode ir pra 200 mil?") também, menos o passado ("chegou a ir a
// 140"). O "rumo a" do ano ("o plano rumo a 2030") não é nível; "rumo aos 2000" é.
const NIVEL_VERBO = r`(?:\bva[io] (?:a|ao|aos|as|pra|pro|pros|pras|para|para o|para os|para as)` +
  r`|(?<!\bchegou a )(?<!\bchegaram a )(?<!\bconseguiu )(?<!\bconseguiram )\bir (?:a|ao|aos|as|pra|pro|pros` +
  r`|pras|para|para o|para os|para as)|\brumo(?: (?:aos|as|os|pros|pras|para os|para as)` +
  r`|(?: (?:a|ao|pra|pro|para|para o))?(?! (?:19|20)\d\d\b))` +
  r`|(?<!\bque )(?<!\bconseguiu )(?<!\bconseguiram )\b(?:chega|chegam|chegar|chegaria|volta|voltam|voltar` +
  r`|bate|batem|bater|atinge|atingem|atingir|alcanca|alcancam|alcancar|ultrapassa|ultrapassam|ultrapassar` +
  r`|supera|superam|superar|rompe|rompem|romper|retorna|retornam` +
  r`|retornar)(?: (?:a|ao|aos|as|os|na|no|nas|nos|pra|pro|pras|pros|para|para o|para os|para as|em(?! (?:19` +
  r`|20)\d\d\b)))?)(?: (?:a )?casa d[oa]s)?(?: (?:r\$|us\$|u\$))? ?`
// "passa de R$ 6?" só com preço unitário: "se eu passar de R$ 35 mil" é a regra do imposto
// com o mercado de sujeito e verbo de futuro, qualquer R$ ("o bitcoin vai passar de R$ 500 mil?")
// "PETR4 sai de 30 pra 40?"
const NIVEL = r`|` +
  NIVEL_VERBO +
  r`\d(?!\d*[oa]\b)(?![\d.,]*\s?(?:h|hs|horas?|minutos?|dias?|semanas?|mes|meses|anos?|pregoes|uteis)\b)` +
  r`|\bpassa(?:m|r)? (?:de|dos|das|da)(?: (?:a )?casa d[oa]s)?(?: us\$| r\$(?! ?(?:[\d.,]* ?(?:mil|mi` +
  r`|milh\w*|k)\b|\d{4}|\d{1,3}\.\d{3})))? ?\d|(?<!\bde )(?<!\bem )\b(?:dolar|euro|ibovespa|bitcoin|btc` +
  r`|brent|wti|barril|petroleo|gasolina|diesel|etanol|ouro|petr[34]|petrobras)(?: \w+)? (?:vai|vao|pode` +
  r`|podem|poderia|deve|devem|deveria|consegue|conseguem) passar (?:de|dos` +
  r`|das)(?: (?:a )?casa d[oa]s)? r\$ ?\d|\b(?:sai|vai|passa) de(?: r\$| us\$)? ?\d[\d.,]*(?: mil` +
  r`| k)? (?:pra|para|a|ate)(?: r\$| us\$)? ?\d`
// O número do alvo ("o dólar vai a R$ 7?", "btc rumo aos 100k?", "o ouro vai a 3000 dólares?") não é o dinheiro da pessoa:
// sai do texto antes do capital e da conta de câmbio.
// Também o alvo com "sobe/cai pra", "passa de" e o nível com prazo ("bitcoin a 200k ano que vem?").
const _ALVO_VERBO = r`(?:\b(?:sobe|sobem|subir|cai|caem|cair|desce|descem|descer|recua|recuam|recuar|despenca|despencam` +
  r`|despencar) (?:a|ao|aos|as|pra|pro|pros|pras|para|para o|para os|para as|ate)|(?<!\beu )\bpassa(?:m` +
  r`|r)? (?:de|dos|das)(?: (?:a )?casa d[oa]s)?)(?: (?:r\$|us\$|u\$))? ?`
const _ALVO_QUANTIA = r`\d(?!\d*[oa]\b)[\d.,]*(?: ?(?:mil|k|milhao|milhoes|mi)\b)?(?: ?(?:de )?(?:reais|dolares|dolar|dollars?` +
  r`|usd|euros?|eur|pontos?)\b)?`
// o nível com prazo, sem verbo ("bitcoin a 200k ano que vem?", "bitcoin nos 200k até o Natal?"); sem o "de", que
// é o dinheiro dela ("uma reserva de 10 mil dólares até o fim do ano")
const ALVO_NUM = r`(?:` +
  NIVEL_VERBO +
  r`|` +
  _ALVO_VERBO +
  r`)` +
  _ALVO_QUANTIA +
  r`|\b(?:a|aos?|nos?|em|to|at) (?:r\$ ?|us\$ ?|\$ ?)?` +
  _ALVO_QUANTIA +
  r`(?=[^.?!]{0,40}(?:` +
  PRAZO +
  r`))`
// Pergunta sobre o futuro de um preço: direção, magnitude, nível ou "o que acontece se". Leva a recusa (N2).
// "fundo de índice" e "fundo de investimento" são o produto, não o fundo do preço; "fundo do bitcoin" é o fundo do
// preço, "fundo de bitcoin" é o produto
// o preço de uma ação contra o "justo" (valuation) também é opinião sobre para onde ela vai
// "o imposto está no preço da gasolina?" é a composição da bomba, e "o brent tá no preço de 2022?" é o passado; o
// "já está no preço do petróleo/da PETR4" é opinião e continua recusa
// juízo sobre a ação ("isso é bom pra ação?", "é bom pra PETR4?"): é opinião sobre para onde ela vai
// "conseguiu voltar a 100 mil em 2020?" é passado
// "segue subindo?", "continua caindo?"; o passado ("seguiu", "continuou") fica de fora
// gíria de cripto, em formas fechadas: "bombardeio" e "pump and dump" (conceito) não entram, nem o passado
// ("o dólar explodiu na pandemia?", "o Ibovespa decolou em 2018?", "bombou em 2019?")
// "o que significa moon?" é conceito
// "estourar o limite do cartão" é a dívida, não o preço
// "estourar a (minha) margem", "a garantia estoura" e "a conta estourar" são a chamada de margem (P5, D4), que o
// bloco do WIN explica; "vai estourar" continua pedido
// "o bitcoin explodiu, vai continuar?": o que vem depois do movimento
// o movimento trazido por alguém ("o petróleo pode trazer 10 dólares de alta?", "a OPEP vai dar uma alta?")
// "o bitcoin bombou, continua?", "o dólar subiu, segue?": o verbo sozinho na oração (depois de vírgula, ponto, "e"
// ou "mas"); com sujeito ("a isenção continua?", "a guerra continua?") não
// "quanto vai estar o barril no natal?", "¿cuánto va a valer el barril?"
// "já subiu demais?" é o "esticado"; o pretérito com data fechada ("por que a bolsa caiu demais em março de 2020?",
// "caiu demais na pandemia?", "caiu demais ontem") é passado (P1). "desde 2020" chega até hoje e continua recusa.
// "o petróleo termina o ano acima de 100?", como o "fecha" ("terminou o ano" é passado)
// em inglês ("Will oil hit $100?", "Is oil going to crash?"), sem "crash" nem "hit" soltos ("o crash de 2020")
// O futuro da pessoa ("I'm going to Brazil", "we are going to Lisbon", "I am going to study oil") não é o do preço,
// a não ser que fale do dinheiro ou do nível ("I'm going to lose money?", "we're going to see the dollar at 6?"); a
// agenda ("what is going to happen at the OPEC meeting?") também não.
// "how much will I get in reais for 1000 dollars?" é a conversão de hoje; com prazo ("... in December?") é futuro
// manchete: "Oil to 150 by Christmas?", "BTC to 100k?"
// máxima e "flip" de cripto, no futuro e no presente ("bitcoin vai renovar máxima?", "eth vai flipar?"); o passado
// ("renovou", "flipou") e o conceito ("o que é ATH?", "flippening") ficam de fora
// "PETR4 tá muito alta?": o juízo sobre o nível do papel ("a Selic está muito alta?" fica de fora)
// o nível com prazo, sem verbo ("Brent a 100 até dezembro?", "Qual o preço do brent daqui a 6 meses?")
const FUTURO = r`\b(sobe|sobem|subir|suba|subira|subiria|desce|descer|cai|caem|cair|caia|caira|cairia|despenc\w*` +
  r`|dispar\w*|derret\w*|valoriz\w*|desvaloriz\w*|aprecia\w*|recua\w*|fecha|fechar|abre|abrir|pra cima` +
  r`|para cima|pra baixo|para baixo|topo` +
  r`|fundo(?! (de|do|da|dos|das) (indices?|investimentos?|pensao|previdencia|renda|garantia|emergencia)\b` +
  r`| de (acoes|cripto\w*|bitcoins?)\b` +
  r`| imobiliarios?\b)|barat[oa]s?|car[oa]s?|vies|palpite|visao|acha|acham|opiniao|tendencia|provavel` +
  r`|esperado|retorno|potencial|descontad[oa]s?|esticad[oa]s?|subvalorizad[oa]s?|sobrevalorizad[oa]s?` +
  r`|supervalorizad[oa]s?|upside|valuation|preco justo|valor justo|carissim[oa]s?|baratissim[oa]s?` +
  r`|precificad[oa]s?|(ta|esta|estao|tao|negocia|negociam|sendo negociad[oa]s?) (com desconto|em promocao` +
  r`|num preco (bom|otimo)|num (bom|otimo) preco|com (um )?(bom|otimo) preco|com preco (bom|otimo)` +
  r`|(abaixo|acima) do (seu )?valor( patrimonial| real| intrinseco)?\b(?! d[aeo]s? | de | em )` +
  r`|no preco\b(?! d[aeo]s? (gasolina|diesel|etanol|combustive(l|is)|bomba)\b| de (ontem|antes|19\d\d` +
  r`|20\d\d)\b| d[oa] (ano|mes|semana` +
  r`|dia) passad[oa]\b))|pechinch\w*|promocao|de graca|baratinh\w*|undervalued|overvalued|cheap|expensive` +
  r`|price target|subavaliad\w*|preco de banana|vale o preco|target price|vai bem|vai mal|reage bem` +
  r`|reage mal|pra onde|para onde|go up|go down|rise|fall|rally` +
  r`|(bom|boa|ruim|otimo|otima|pessimo|pessima) (pra|para|pro|pros|pras) (a |o |as |os )?(acao|acoes|papel` +
  r`|papeis|cotacao|petr[34]|petrobras` +
  r`|prio3?)|bajar|probabilidad\w*|chances?|(?<!conseguiu )(?<!conseguiram )voltar (pra|para|a)|(continua` +
  r`|continuam|continuar|segue|seguem|seguir) (subindo|caindo|em alta|em queda)|explod(?!iu\b|iram\b` +
  r`|ido\b)\w*|decol(?!ou\b|aram\b|ado\b)\w*|bombar|bombando|pumpa\w*|pumpar|pra lua|para a lua|to the moon|` +
  r`${CONCEITO_ANTES}` +
  r`(?<!\bque e )moon|voa|voam|voar|voara|voaria|voando|pro espaco|para o espaco|vai (mais )?longe` +
  r`|pras? (alturas|nuvens)|afund(a|am|ar|ara|aria|ando)` +
  r`|(?<!margem )(?<!garantia )(?<!conta )estour(a|am|ar|ara|aria|ando)(?! (o |a |do |da )?((meu|minha|seu` +
  r`|sua) )?(cartao|orcamento|cheque|limite|margem|garantia|conta)))\b|\b(vai|vao) estourar\b|\b(vai|vao` +
  r`|deve|devem) continuar\b|\b(pode|podem|poderia|vai|vao|deve|devem|deveria) (trazer|levar` +
  r`|dar)( \w+){0,3} (altas?|quedas?|subidas?|baixas?)\b|(?:^|[,.;:!?]` +
  r`|\b(?:e|mas)\b)\W*(?:sera (?:que )?)?(?:ainda |isso )?(?:(?:vai|vao|deve|devem) (?:continuar|seguir)` +
  r`|continua|continuam|segue|seguem|continuara|continuarao|seguira|seguirao)(?: assim| subindo| caindo` +
  r`| desse jeito| em alta` +
  r`| em queda)?\W*$|(?<!\bna )(?<!\bda )(?<!\ba )(?<!\bpra )(?<!\bpara )(?<!\bpela )(?<!\bnas )(?<!\bdas )` +
  r`\bbomba (mais|de novo)\b` +
  NIVEL +
  r`|\b(vai|vao|va a|van a) (estar|valer|custar|ficar|ta|llegar|costar)\b|\b(vai|vao) (pra|para) quanto\b` +
  r`|\b(pra|para) quanto (vai|vao)\b|\b(sobe|cai|subindo|caindo) demais\b` +
  r`|\bja (subiu|caiu|subiram|cairam) demais\b` +
  r`|(?:^|[.?!;])(?!(?![^.?!;]*\bdesde\b)[^.?!;]*\b((19|20)\d\d|pandemia|covid|ontem|anteontem` +
  r`|passad[oa]s?)\b)[^.?!;]*\b(subiu|caiu|subiram|cairam) demais\b|\b(termina|terminar|terminam|encerra` +
  r`|encerrar|encerram) (o ano|o mes|a semana|o semestre` +
  r`|20\d\d)\b|(?<!\bi'm )(?<!\bim )(?<!\bi am )(?<!\bwe're )(?<!\bwere )(?<!\bwe are )(?<!\bthey're )(?<!\b` +
  r`theyre )(?<!\bthey are )\b(going to|gonna)\b(?! happen (at|in|on|during)\b)|\b(going to` +
  r`|gonna) ((make|lose) (money|a profit|profit)|profit|get rich` +
  r`|see( \w+){0,2} (at (\$|us\$|r\$)? ?\d|hit|reach|go|drop|fall|rise|crash))\b` +
  r`|\bwill (?!(?<=how much will )(i|we|you) get\b(?![^.?!]*\b(next|tomorrow|later|when|after|before|until` +
  r`|by|end of|in (january|february|march|april|may|june|july|august|september|october|november|december` +
  r`|20\d\d))\b))(\w+ ){0,2}(hit|reach|crash|drop|climb|go|be|get|rise|fall)\b|\bwhere (is|are` +
  r`|will)( \w+){1,3} (headed|heading|going)\b|^\W*(\w+ ){1,2}to \$?\d|\bllega(r` +
  r`|ra)? a( us\$)? ?\d|\b(ja )?(foi|era) (o|a) pico\W*$|\brenova(r|ra|ria|rao)?( a| uma)?( nova)? (maximas?` +
  r`|ath)\b|\b(vai|vao|chega|chegar|volta|voltar) (pra|para|na|a)( uma)?( nova)? maximas?\b|\b(bate|bater` +
  r`|batera|bateria|faz|fazer|fara|faria|atinge|atingir|atingira|atingiria|ter|tera|teria|marca|marcar` +
  r`|marcara)( uma| um)?( nova| novo)? (maximas?|ath)\b|\b(vai|vao|pode|podem|deve|devem) (bater|fazer` +
  r`|atingir|ter|marcar)( a| uma| o| um)?( nova| novo)? (maximas?|ath)\b|\bflipp?(a|ar|am|ara|aria|e|em|ando` +
  r`|s)\b|\b(vai|vao|pode|podem|deve|devem|consegue) (passar|ultrapassar|superar)( o| a)? ${CRIPTO_NOME}` +
  r`\b|\b(ultrapassa|ultrapassam|ultrapassara|ultrapassaria|supera|superam|superara|superaria)( o| a)? ` +
  r`${CRIPTO_NOME}\b|(?<!\bda )(?<!\bdo )\b${EMPRESA}` +
  r`\b[^.?!]{0,15}\b(ta|esta) (muito|bem) (alt|baix)[oa]s?\b|` +
  NIVEL_PRAZO
// O que não é preço sai do texto só para o FUTURO (o resto do roteador lê a pergunta inteira):
// - "cara" vocativo ("cara, como tá o dólar?", "ô cara", "o dólar, cara,") e substantivo ("a cara do Ibovespa", "com cara
// de quê", "o cara do BC"). "Tá cara?", "cara demais" e qualquer "cara de X" (de alta, de subida, de oportunidade)
// continuam valuation e direção (N2); só "a cara do/da" e "cara de quê" saem.
const CARA_NAO_PRECO = r`^((o|oh|ai|ei|e ai|fala|opa|oi|po|poxa|putz|nossa|mano|meu|velho|vei|serio|olha|ah|tipo|bom|caramba` +
  r`|eita)\W+)?cara\b(?! demais\b)|,\s*cara\b(?! demais\b)|\b(a|qual a|qual e a|qual seria a) cara d[ao]s?\b` +
  r`|\bcara de que\b|\b(o|um|esse|este|aquele|do|no|pro|pelo|ao|num|dum|desse|nesse|daquele) cara\b`
// - "descontado" de imposto ou de provento ("o IR é descontado na fonte?", "o dividendo é descontado do preço?"): é regra
// (P5), não "a ação tá descontada". Com empresa citada, só o "na fonte" sai.
const DESCONTO_NA_FONTE = r`\bdescontad[oa]s? (na|no) (fonte|holerite|contracheque|salario)\b`
const DESCONTO_NAO_PRECO = r`\b(imposto|ir|irrf|iof|tributos?|taxas?|tarifas?|custodia|corretagem|emolumentos?|come cotas|dividendos?` +
  r`|jcp|proventos?|juros sobre capital|cupom|cupons)( (de|do|da|dos|das|sobre|no|na|em) (\w+ ){0,3}\w+)? (e` +
  r`|sao|foi|foram|vem|sera|serao|fica|ficam|seria) descontad[oa]s?\b`
// Depois de um conector de adjunto ("o bitcoin com as taxas é descontado?", "o ibovespa pagando dividendos é descontado?"),
// o imposto ou o provento não é o sujeito: o "descontado" é do ativo, e continua valuation (N2).
const ADJUNTO_ANTES = r`\b(com|sem|pagando|incluindo|considerando|contando)( (o|a|os|as))? $`
// - a definição inteira e genérica ("o que é valuation?", "como se calcula o preço justo de uma ação?") é conceito (P5).
// Com artigo, mercado ou empresa ("o que é o upside do Ibovespa?") continua recusa.
const _GENERICO = r`( (de|em|numa|num) (uma |um )?(acao|acoes|empresa|empresas|ativo|ativos|papel|papeis))?\W*$`
const DEFINICAO_VALUATION = r`^((o que|oq) (e|sao|significa|quer dizer)|como (funciona|se calcula|se faz|e calculado))( o| um` +
  r`| uma)?( (acao|acoes|papel|ativo))? (valuation|upside|preco justo|valor justo|descontad[oa]s?` +
  r`|esticad[oa]s?|subvalorizad[oa]s?|sobrevalorizad[oa]s?|precificad[oa]s?|undervalued|overvalued` +
  r`|price target|target price|pechinchas?|vaca leiteira)` +
  _GENERICO
// - o "caro" da bomba numa pergunta que pede a explicação ("por que a gasolina está cara?", "quanto do preço da gasolina
// cara é imposto?") é o que o bloco do barril à bomba responde, não valuation. "A gasolina tá cara?" e "a gasolina vai
// ficar mais cara?" continuam recusa (N2).
const BOMBA_EXPLICA = r`\b(por que|porque|pq|por causa d\w*|culpa d\w*|o que (deixa|faz|torna)|quanto d[oa]|imposto\w*` +
  r`|do mundo)\b`
const BOMBA_CARA = r`\b(gasolina|diesel|etanol|combustive(?:l|is))\b([^.?!]{0,30}?)\b(car|barat)[oa]s?\b`
// A bomba junto com a ação ("por que a gasolina e a petr4 estão caras?") é valuation do papel (N2; Mapa legal, seção 8,
// item 10): o "caro" não sai.
const _COMBUSTIVEL = r`(gasolina|diesel|etanol|combustive(?:l|is))`
const BOMBA_E_EMPRESA = r`\b${_COMBUSTIVEL},? (e|ou) (a |o |as |os )?((acao|acoes|papel|papeis) d[aeo]s? )?${EMPRESA_SEM_VALE}` +
  r`\b|\b${EMPRESA_SEM_VALE},? (e|ou) (a |o |as |os )?${_COMBUSTIVEL}\b`
// - a regra do circuit breaker ("quando a queda passa de 10%?") não é nível de preço no futuro.
const REGRA_DE_QUEDA = r`\bquando\b[^?!.]{0,40}\b(queda|baixa)\b[^?!.]{0,20}\bpassa(r)? de \d+([.,]\d+)? ?%` +
  r`|\bquando\b[^?!.]{0,40}\bpassa(r)? de \d+([.,]\d+)? ?% de (queda|baixa)\b`
const PASSA_DE_PCT = r`\bpassa(r)? de (?=\d+([.,]\d+)? ?%)`
// "quando o ibovespa cai mais de 10% tem circuit breaker?" é a regra do circuit breaker, não previsão
const REGRA_CIRCUIT = r`\bquando\b[^?!.]{0,60}\bcircuit[ -]?breakers?\b|\bcircuit[ -]?breakers?\b[^?!.]{0,60}\bquando\b`
// - a regra com o imposto como sujeito ("a isenção do bitcoin de 35 mil vai continuar?", "quanto vai ficar o IOF do cartão?",
// "o IR do bitcoin sai de 15 para 17,5?", "qual o valor da isenção no ano que vem?", "o valor mínimo do Tesouro muda?") é
// regra (P5). O imposto que acompanha um preço ("o dólar com IOF vai ficar quanto?") não sai, e a frase com "e", "ou",
// "também" ou "se" ("quanto vai ficar o IOF e o dólar?") continua recusa.
const REGRA_SUJEITO = r`(?<!\bcom )(?<!\bsem )(?<!\bmais )(?<!\bmenos )(?<!\bcom o )(?<!\bcom a )(?<!\bsem o )(?<!\bsem a )\b(io` +
  r`f|impostos?|ir(?! (pra|para|pro|pros|a|ao|aos|bem|mal|longe|ate|alem)\b)|irpf|aliquotas?|isenc\w*` +
  r`|taxas? de (custodia|corretagem|administracao)|custodia|corretagem|emolumentos?|declarac\w*|come-?cotas` +
  r`|tributac\w*)\b`
const _COMPLEMENTO = r`( (?!(o|a|os|as|um|uma|e|ou|mas|que|se|com|sem)\b)\w+)`
const REGRA_FUTURA = r`\b(vai|vao|deve|devem) (ficar|custar|continuar|valer|estar|mudar)( (o|a|os|as))? ${REGRA_SUJEITO}|` +
  r`${REGRA_SUJEITO}${_COMPLEMENTO}{0,6} (vai|vao|deve|devem) (ficar|custar|continuar|valer|estar)\b|` +
  r`${REGRA_SUJEITO}${_COMPLEMENTO}` +
  r`{0,4} (sai|vai|passa) de [\d.,]+ ?%? (pra|para|a) [\d.,]+|\b(valor|preco)( d[aoe]s?)? ${REGRA_SUJEITO}` +
  r`|\bvalor minimo\b(?=( (d[aoe]s?|pra|para|de|no|na|em))? (o |a )?(tesouro|investimento|investir` +
  r`|aplicac\w*|aplicar|aporte|aportar|cdb|lci|lca|fiis?|fundos?|cotas?|resgate|deposito|depositar|saque` +
  r`|sacar|conta)\b)`
const COORDENA = r`\b(ou|nem|tambem|se)\b` +
  r`|(?<!\bqual )(?<!\bquanto )(?<!\bcomo )(?<!\bque )(?<!\bonde )(?<!\bquando )(?<!\bisso )(?<!\bnao )\be\b` +
  r`(?! que\b)`
const CAI_MAIS_PCT = r`\b(cai|caem|cair|recua|recuam|recuar|despenca|despencam) mais de (?=\d+([.,]\d+)? ?%)`
// - o intervalo que começa num mês ou ano ("de janeiro até outubro", "desde 2020 até") não é o prazo de uma previsão.
const INTERVALO = r`\b(de|desde) (o |a )?(${MESES.slice(1, -1)}|inicio do ano|comeco do ano|20\d\d) ate\b`
const CONDICIONAL = r`\bse (o |a )?(\w+ ){0,2}(ganhar|vencer|perder|for eleito|for reeleito|cortar|cortarem|subir|aumentar` +
  r`|baixar|reduzir|mantiver|wins?)\b|\b(ganhando|vencendo|perdendo)\b|\bcom (o ` +
  r`|a )?\w+ eleit[oa]\b|\bif \w+ wins?\b`
// Pergunta sobre o que já aconteceu: não pede direção.
// "o Brent teve retorno negativo no ano?" também pergunta o que já aconteceu
// O "antes" de um evento que ainda vem ("o dólar sobe antes da eleição?", "antes do halving?") não é passado; com o ano
// ("antes da eleição de 2018") é.
const PASSADO = r`\b(reagiu|reagiram|aconteceu|aconteceram|foi|foram|ficou|ficaram|teve|tiveram|historico|historicamente` +
  r`|ja houve|antes(?! d[aeo]s? (eleic(ao|oes)|turno|\d+o turno|(primeiro|segundo) turno|copom|halving` +
  r`|reuniao|posse|votacao|decisao|proxim\w*|fim` +
  r`|final)\b(?! de (19|20)\d\d))|passad[ao]s?|levou|levaram|demorou|demoraram)\b`
// "Brent em 138 foi o topo?" e "o bitcoin já teve o topo?": se o topo já passou é pergunta sobre o que vem;
// com o ano que já passou ("o bitcoin a 69 mil em 2021 foi o topo?") é passado
// "o fundo já foi?", "o topo já passou?": com o "já", pergunta se o que vem é mais baixo ou mais alto
const FUTURO_EXPLICITO = r`\b(vai|vao|agora|amanha|semana que vem|depois d[oa]|proxim\w*|pra onde|para onde)\b|\bdaqui a\b` +
  r`|\bja (foi|era|teve|tiveram) (o|a|seu) (topo|fundo|pico)\W*$` +
  r`|^(?!.*\b(19\d\d|20[01]\d|202[0-5])\b).*\b(foi|era|teve|tiveram) (o|a|seu) (topo|fundo|pico)\W*$` +
  r`|\b(topo|fundo|pico) ja (foi|passou)\W*$`
// Oração: "o dólar ficou abaixo de 5, cai mais?" pede o próximo movimento na 2ª oração; o "ficou" da 1ª não apaga o
// pedido. Vírgula e ponto de número ("5,04", "1.000") não separam.
const ORACAO = r`[;:?!]|[,.](?!\d)|\b(?:e|mas)\b`
// "teve" e o passado da oração relativa ("o petróleo que teve alta tende a cair?", "o dólar que ficou alto cai?",
// "o dólar já teve alta suficiente pra cair?") não apagam o verbo no futuro da mesma oração. Sem verbo no futuro ("o
// Brent teve retorno negativo no ano?", "a ação que teve retorno negativo em 2020?"), continuam marca de passado.
const PASSADO_FRACO = r`\b(teve|tiveram)\b|(?<!\bo )(?<!\bpor )(?<!\bpra )(?<!\bpara )\bque (ja )?(teve|tiveram|ficou|ficaram` +
  r`|foi|foram)\b`
const FUTURO_VERBO = r`(?<!\bvoltou a )(?<!\bvoltaram a )(?<!\bteve que )(?<!\bteve de )(?<!\bcomecou a )(?<!\bpassou a )\b(sob` +
  r`e|sobem|subir|suba|subam|subira|subirao|subiria|desce|descem|descer|cai|caem|cair|caia|caiam|caira` +
  r`|cairao|cairia|despenca|despencam|despencar|dispara|disparam|disparar|derrete|derretem|derreter|valoriza` +
  r`|valorizam|valorizar|desvaloriza|desvalorizam|desvalorizar|recua|recuam|recuar|tende|tendem|tera` +
  r`|terao)\b|\b(volta|voltam|voltar) (a|pra|para)\b`
function _passado_da_oracao(o: string): boolean {
  if (search(FUTURO_VERBO, o)) o = sub(PASSADO_FRACO, ' ', o)
  return Boolean(search(PASSADO, o))
}
// O advérbio vale para a frase inteira: "historicamente, a bolsa sobe depois de eleição?" pergunta o que já aconteceu (P1).
const PASSADO_DA_FRASE = r`\b(historicamente|no passado)\b`
// O trecho entre pontuação: o advérbio só vale para a frase toda quando no máximo um trecho pede ou se move ("historicamente
// o dólar sobe em eleição, sobe esse ano?" pede no 2º trecho).
const TRECHO = r`[;:?!]|[,.](?!\d)`
// O verbo de pedido no presente depois do "ficou/foi" na mesma oração ("o dolar ficou abaixo de 5 cai mais?", "o bitcoin que
// ficou barato explode?") é o pedido; numa subordinada ("como o dólar reagiu quando o Copom sobe?") não.
const VERBO_PEDIDO = r`\b(sobe|sobem|desce|descem|cai|caem|despenca|despencam|dispara|disparam|derrete|derretem|valoriza` +
  r`|valorizam|desvaloriza|desvalorizam|aprecia|recua|recuam|explode|explodem|decola|decolam|voa|voam)\b`
const PASSADO_VERBAL = r`\b(reagiu|reagiram|aconteceu|aconteceram|foi|foram|ficou|ficaram|teve|tiveram)\b`
const SUBORDINADA = r`\b(quando|sempre que|toda vez que|enquanto|porque|por que)\b.*`
// O ano que já passou marca a oração sem verbo ("o euro ficou caro em 2022 e barato em 2023?"). Teto fixo (o analisar não
// recebe a data): quando envelhecer, erra para mais recusa.
const ANO_PASSADO = r`\b(em|de|no ano de) (19\d\d|20[01]\d|202[0-5])\b`
// A oração sem verbo que repete o "ficou caro/barato" da anterior ("em 2020 a bolsa ficou barata, e o dólar caro?") herda o
// passado dela. "tá barato?", "continua caro?", "barato em 2027?" e a empresa ("a PETR4 ficou barata e a PRIO cara?")
// continuam pedido.
const ELIPTICA = r`^\W*(?:(?:o|a|os|as) \w+ )?(?:barat|car)[oa]s?(?: em ((?:19|20)\d\d))?\W*$`
// Na oração, o movimento no pretérito também é marca de passado ("como o dólar reagiu e se valorizou na pandemia?"): o
// FUTURO pega "valoriz", "dispar" e "despenc" em qualquer tempo.
const MOVIMENTO_PASSADO = r`\b(subiu|subiram|caiu|cairam|valorizou|valorizaram|desvalorizou|desvalorizaram|despencou|despencaram` +
  r`|disparou|dispararam|derreteu|derreteram|recuou|recuaram|apreciou|apreciaram|explodiu|explodiram|decolou` +
  r`|decolaram|bombou|fechou|fecharam|abriu|abriram)\b`
// A oração que pergunta o que foi: "qual foi a decisão?", "como foi?"
const QUAL_FOI = r`^\W*(qual|que|como|quando|o que) (foi|foram|era)\b`
const VERBO_DECISAO = r`corta|cortam|mantem|segura|eleva|elevam|aumenta|aumentam|baixa|baixam|reduz|reduzem|sobe|sobem|reajusta` +
  r`|reajustam`
// O melhor ou o pior momento que já passou ("qual foi o pior momento do Ibovespa na pandemia?") é fato (P1). O momento
// "pra comprar" continua pedido, mesmo no passado ("qual foi o melhor momento pra comprar dólar em 2020?").
// sem uso, também no Python (agente/roteador.py): fica para o espelho seguir linha a linha
// deno-lint-ignore no-unused-vars
const MOMENTO_DICA = r`\b(bom|otimo|melhor|pior) momento\b`
const MOMENTO_PASSADO = r`\b(qual|quando) (foi|foram) o (melhor|pior) momento\b` +
  r`|\b(teve|tiveram|viveu) (o|seu) (melhor|pior) momento\b` +
  r`|\b(melhor|pior) momento\b[^.?!,;]{0,40}\b(foi|foram|aconteceu|ocorreu) (em|no|na|nos|nas|durante|quando` +
  r`|entre)\b`
const MOMENTO_PRA = r`\b(bom|otimo|melhor|pior) momento\b[^.?!,;]{0,25}\b(pra|para|de) \w+(ar|er|ir)\b`
// A viagem de quem fala, com destino ("vou voar pra Lisboa com 2 mil euros", "embarco semana que vem pros EUA"), não é a
// gíria do preço ("o bitcoin vai voar", "vou voar com o bitcoin?") nem a entrada ("embarco no brent?", "embarco hoje?",
// "embarco pro bitcoin?", "embarco pra lucrar?"): sai do texto que o FUTURO e a dica leem.
const VIAGEM = r`(\b(vou|vamos|a gente vai|eu|estou|to|tou) (voar|voando)\b|\bembarc(o|amos)\b)( (hoje|amanha|(na |nesta ` +
  r`|essa |nessa |esta )?(semana|mes) que vem|dia \d+|em \d+ dias|daqui a \d+ dias|(na |nesta |essa |nessa ` +
  r`|esta )?(segunda|terca|quarta|quinta|sexta)(-feira)?|(no |neste |nesse |este |esse )?(sabado` +
  r`|domingo)|em ${MESES}` +
  r`))? (pra|para|pro|pros|pras|rumo a|rumo ao|a caminho d[aeo])\b(?! (o |a |os |as |um |uma )?((${ATIVO}|` +
  r`${CRIPTO_NOME}|euros?|lua|cima|baixo|espaco|alto|ceu|marte|dentro|\w+(ar|er|ir))\b|\d|r\$|us\$))`
// O prazo curto de uma decisão que ainda vai sair.
const PRAZO_DECISAO = r`(proxim\w*|amanha|semana que vem|mes que vem|(essa|esta|nessa|nesta) semana|(este|esse|neste|nesse) mes)`
const SEM_IMPOSTO = r`(?! d[aoe]s? (impostos?|iof|ir|irpf|tributos?|aliquotas?)\b)`
// Decisão de juros que ainda vai sair: "vai cortar os juros?", "o BC vai reduzir a Selic?", "vai ter corte?", "o Copom
// cortará?", "corta na próxima reunião?". É futuro pela forma do verbo: não passa pelo filtro do PASSADO.
// pagar dividendo que ainda vai sair é previsão; pagar imposto, IOF, cupom ou o juro semestral do título é regra
// (P5). "O tesouro vai pagar mais juros?" e "o CDB vai pagar juros altos?" continuam previsão. Com empresa citada,
// o PAGAR_EMPRESA decide.
// o dividendo que volta ("a petrobras volta a pagar dividendo?"); "voltou a pagar" é passado, e o imposto é regra
// a forma curta, no presente: "a OPEP corta?", "o Copom sobe?"
// o presente com prazo, na mesma oração ("a Petrobras reajusta semana que vem?", "o Copom corta essa semana?");
// "o Copom mantém a Selic, como o dólar reagiu essa semana?" fica de fora
// "sai reajuste?", "será que sai reajuste?", e o "sai/vem/tem" com prazo ("tem reajuste essa semana?", "vem
// aumento por aí?"). "Quando sai reajuste, o que acontece?" e "tem aumento de imposto em 2026?" ficam de fora.
// o aumento do imposto ("tem aumento de IOF no próximo ano?") é regra (P5); "tem corte da taxa Selic?" não
// "vem aumento de gasolina aí?", "o diesel baixa?", "será que a OPEP corta a produção?": a decisão que ainda vem.
// Sem artigo depois de "vem" ("de onde vem a alta do dólar?") e até 3 palavras depois de "será que".
// "a OPEP decide cortar em dezembro?"
// a próxima decisão de preço sem data marcada ("quando sai o próximo reajuste da gasolina?", "reajuste do diesel sai
// quando?", "tem aumento de gasolina vindo?"). "Quando sai reajuste, o que acontece?", "a próxima reunião de corte"
// e o imposto ("quando sai o novo aumento do IOF?") ficam de fora.
const DECISAO = r`\b(vai|vao|ira|irao|deve|devem|pode|podem)( \w+){0,2} (cortar|baixar|reduzir|manter|segurar|elevar` +
  r`|aumentar|subir|mexer|parar|pausar|interromper|reajustar)\b|\b(vai|vao|ira|irao|deve|devem|pode` +
  r`|podem)( \w+){0,2} pagar\b(?!( \w+){0,2} (impostos?|ir|irpf|iof|darf|tributos?|taxas?(?! de (dividendos?` +
  r`|retorno|distribuicao` +
  r`|pagamento))|tarifas?|cupom|cupons|come-?cotas|ajustes?)\b| (mais|menos) (que|do que) (a |o )?(selic|cdi` +
  r`|poupanca)| juros? (semestra\w*|mensa\w*` +
  r`|(todo|a cada|por) (mes|semestre))\b| juros?\W*$)|\b(cort|baix|segur|elev|aument)a(ra|rao|ria|riam)\b` +
  r`|\breduzi(ra|rao|ria|riam)\b|\bmante(ra|rao|ria|riam)\b` +
  r`|\b(vai ter|vai haver|vao ter|tera|havera|teremos|vai sair|vai vir|vai rolar` +
  r`|vao rolar)( \w+){0,2} (corte|cortes|alta|altas|aumento|reducao|elevacao|manutencao|pausa|queda|reajuste` +
  r`|reajustes|dividendos?|proventos?)\b|\bvolta(m|ra|rao)? a (pagar` +
  r`|distribuir)\b(?! (o |a )?(ir|imposto\w*|darf|iof|taxas?|tributos?)\b)|(^|[.?!;:] |\b(e|mas) )(a ` +
  r`|o )?(opep|opec|copom|bc|banco central)\+? (corta|cortam|mantem|sobe|eleva|aumenta|reduz` +
  r`|baixa)( (a |os )?(producao|juros|selic|taxa))?\W*$|\b(corta|cortam|mantem|segura|eleva|aumenta|baixa` +
  r`|reduz|sobe|reajusta|reajustam)\b[^,.?!;]{0,30}\b${PRAZO_DECISAO}` +
  r`\b|(^|[.?!] |\bsera que )(sai|vem)( \w+){0,2} (reajustes?|aumentos?|cortes?|reducao|reducoes)\b` +
  r`|\b(sai|vem|tem)( \w+){0,2} (reajustes?|aumentos?|cortes?|reducao|reducoes)\b(?! (de|do|da|no|na) (iof` +
  r`|ir|irpf|impostos?|aliquotas?|tribut\w*|isenc\w*|taxas? de (custodia|corretagem|administracao)|custodia` +
  r`|corretagem|emolumentos?|come-?cotas)\b(?![^,.?!;]*\b(e|ou)\b))[^,.?!;]{0,40}\b(` +
  r`${PRAZO_DECISAO.slice(1, -1)}` +
  r`|por ai|em breve)\b|\bvem (ai )?(um |uma |mais )?(novo |nova )?(aumento|reajuste|corte` +
  r`|reducao)\b|^(sera que )?(a |o )?(petrobras|gasolina|diesel|etanol|combustivel)\+? (corta|mantem|sobe` +
  r`|aumenta|reduz|baixa|reajusta)( (a |o |os )?(gasolina|diesel|combustive(l|is)|preco))?\W*$` +
  r`|\bsera que (\S+ ){0,3}(${VERBO_DECISAO}` +
  r`)\b|\b(decide|decidem|vai decidir|vao decidir)( \w+)? (cortar|manter|aumentar|reduzir|reajustar|elevar` +
  r`|baixar)\b|\bquando (sai|vem|e|tem)( o| a| um| uma)? (proxim[oa]` +
  r`|nov[oa])( (?!reuni|decis)\w+){0,2} (reajustes?|aumentos?|cortes?)\b${SEM_IMPOSTO}` +
  r`|\b(reajustes?|aumentos?|cortes?)\b${SEM_IMPOSTO}` +
  r`( d[aoe] \w+)? (sai|vem) quando\b(?! \w)|\b(tem|vem)( \w+){0,2} (reajustes?|aumentos?|cortes?)\b` +
  r`${SEM_IMPOSTO}( d[aoe] \w+)? (vindo|chegando)\b`
// Com empresa citada, o "pagar" que vem só é regra com imposto, IR, IOF, DARF, tributo, come-cotas ou taxa nomeada do
// fundo: "a petrobras vai pagar mais que a selic?" e "a petrobras vai pagar taxa de dividendo alta?" são projeção de
// dividendo de emissor determinado (N2; Mapa legal, seção 8, item 10). "A Vale" com artigo, para não pegar "vale a pena".
const EMPRESA_CITADA = r`\b${EMPRESA_SEM_VALE}\b|\b(a|da|na|pela) vale\b`
const PAGAR_EMPRESA = r`\b(vai|vao|ira|irao|deve|devem|pode|podem)( \w+){0,2} pagar\b(?!( \w+){0,2} (impostos?|ir|irpf|iof|darf` +
  r`|tributos?|come-?cotas|taxas? de (administracao|custodia|corretagem|performance))\b)`
// O verbo no presente com uma data que ainda vem ("a Petrobras reajusta a gasolina essa semana?", "a OPEP corta em
// dezembro?"): passa pelo filtro do PASSADO, como o DECISAO_OU ("historicamente a OPEP corta em dezembro?" é passado).
const MARCA_DATA = r`mes que vem|ano que vem|(essa|esta|nessa|nesta) semana|(esse|este|nesse|neste) (mes|ano)` +
  r`|(em|de) (janeiro|fevereiro|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro` +
  r`|dezembro)(?! de (19|20)\d\d)|na reuniao de \w+|domingo|sabado|(segunda|terca|quarta|quinta|sexta)( ` +
  r`|-)?feira|(na|no|nesta|nessa) (segunda|terca|quarta|quinta|sexta)\b`
// "por que a gasolina aumenta em janeiro?" pede a explicação, não a decisão que vem
const EXPLICA_POR_QUE = r`\b(por que|porque|pq|por causa d\w*)\b`
const DECISAO_DATA = r`\b(${VERBO_DECISAO})\b.{0,30}\b(${MARCA_DATA})\b`
// "Corta ou mantém?", "corte ou manutenção?": pode ser a decisão de amanhã ou a de ontem, então passa pelo filtro do PASSADO.
const DECISAO_OU = r`\b(corta|cortam|mantem|segura|eleva|aumenta|baixa|reduz|sobe)\b.{0,20}\bou (corta|cortam|mantem|segura` +
  r`|eleva|aumenta|baixa|reduz|sobe|para|nao)\b|\b(corte|manutencao)\b.{0,15}\bou (corte|manutencao|alta` +
  r`|elevacao|aumento|reducao|pausa)\b|\b(alta|elevacao|aumento|reducao|pausa)\b.{0,15}\bou (corte` +
  r`|manutencao)\b`
// O lucro e o dividendo de uma empresa que ainda vão sair são projeção (N2): "Lucro da Petrobras no 3T26 vem forte?",
// "Dividendo da Petrobras em novembro vai ser grande?". O lucro da empresa não é a chance de a pessoa ganhar dinheiro.
const LUCRO_EMPRESA = r`\b(lucros?|prejuizos?|balancos?|resultados?) (\w+ )?(d[aoe]s? )?(?!vale\b)${EMPRESA}` +
  r`\b|\b(lucros?|prejuizos?|balancos?|resultados?) (\w+ )?d[aoe]s? vale\b|\b(?!vale\b)${EMPRESA}` +
  r`( \w+){0,3} lucr\w*`
const PRIMEIRA_PESSOA = r`\b(eu|vou|meu|minha|meus|minhas|mim|consigo)\b`
// "a gente pode lucrar?", "quem pode lucrar com mini-índice?" é a própria pessoa, dita de forma impessoal: chance_dinheiro
const PESSOA_QUE_LUCRA = r`\b(eu|vou|a gente|agente|quem|da (pra|para)|as pessoas|alguem|todo mundo|(o ` +
  r`|um )?(pequeno )?investidor(es)?|iniciantes?|traders?)\b`
// "de onde vem o lucro?", "vem do pré-sal" e "vem caindo" não são o que vem
const VEM = r`(?<!onde )\bvem\b(?! (d[aeo]s?|da onde|\w+ndo)\b)`
// "o lucro vai ser divulgado quando?" é a data, que o calendário responde
const LUCRO_QUE_VEM = VEM +
  r`|\b(vira|virao|sera|serao)\b` +
  r`|\b(vai|vao|deve|devem|pode|podem|tende a|tendem a) (ser\b(?! (divulgad|publicad|anunciad` +
  r`|apresentad)\w*)|vir|ter|sair|crescer|cair|subir|bater|ficar|melhorar|piorar|surpreender|decepcionar)\b`
// "lucro da Petrobras no próximo trimestre?" é projeção; "quando sai o próximo balanço?" é a data, que o calendário
// responde, a não ser que a pergunta também julgue o resultado ("quando sai o próximo balanço, forte ou fraco?").
const PROXIMO_RESULTADO = r`\bproxim\w* (trimestre|balanco|resultado)\b`
const PEDE_DATA = r`\b(quando|que dia|(qual|que) (e )?(a )?data|data d[oa]s?|divulg\w*|public\w*|calendario)\b`
const JUIZO_RESULTADO = r`\b(forte|fraco|bo[ma]|ruim|grande|recorde|positiv\w*|negativ\w*|cresc\w*|cai|cair|sobe|subir|melhor\w*` +
  r`|pior\w*|maior|menor|alt[oa]|baix[oa])\b`
const DIVIDENDO = r`\b(dividendos?|proventos?|jcp|dividend yield|dy)\b`
// o presente com data que ainda vem ("a Petrobras paga dividendo em dezembro?"); "historicamente" e
// "costuma pagar" ficam de fora
const DIVIDENDO_FUTURO = VEM +
  r`|\b(vai|vao|deve|devem) (ser|sair|vir|cair|subir|crescer|aumentar|diminuir|distribuir|pagar|anunciar` +
  r`|aprovar|ter|haver)\b|\b(vira|virao|sai|saem|saira|sairao|sera|serao|tera|havera)\b|\bproxim\w*|\b(esse` +
  r`|este|neste|nesse) ano\b|^(?!.*\b(historicamente|no passado)\b).*\bpaga(m)?\b[^.?!]{0,40}\b(` +
  r`${MARCA_DATA})\b`
const DIVIDENDO_PASSADO = r`\b(pagou|pagaram|distribuiu|distribuiram|anunciou|anunciaram|aprovou|aprovaram|saiu|sairam|veio|vieram` +
  r`|teve|tiveram|reagiu|reagiram|aconteceu|aconteceram|foi|foram|mexeu)\b`
// Como o dividendo anda (data com, data ex, prazo até cair na conta) é conceito (P5), não previsão: "o dividendo sai na
// data com ou na data ex?", "o dividendo será creditado em quantos dias?".
const DIVIDENDO_MECANICA = r`\b(data (com|ex)|quantos dias|quanto tempo|prazo|creditad\w*|cai na conta|como funciona)\b`
// Mas se vai ter, quanto, qual (o próximo, o desse ano, o extraordinário, o de uma empresa) continua previsão de emissor.
const DIVIDENDO_QUAL = VEM +
  r`|\b${EMPRESA}\b|\bproxim\w*|\b(esse|este|neste|nesse) ano\b|\b(${MARCA_DATA}` +
  r`)\b|\b(tera|havera)\b|\btem (dividendos?|proventos?|jcp)\b|\b(vai|vao|deve|devem) (vir|subir|crescer` +
  r`|aumentar|diminuir|distribuir|pagar|anunciar|aprovar|ter|haver|cair(?! na conta)` +
  r`|ser (grande|alto|baixo|bom|maior|menor|de))\b|\b(grande|alto|baixo|maior|menor|extraordinari\w*|valor` +
  r`|quanto(?! tempo))\b`
// A pergunta de imposto sobre dividendo é regra (P5), não previsão.
const DIVIDENDO_REGRA = r`\b(imposto|tribut\w*|tax(a|ad)\w*|aliquota|isen\w*|irpf|ir|declar\w*|lei)\b`
// Pedir a análise ou o juízo sobre uma empresa ("analisa a PETR4", "Petrobras é uma boa empresa?", "PETR4 é segura?",
// "tem fundamento?") é pedir relatório de análise (Res. CVM 20): vai para a direção, como "PETR4 tá barata?".
// "como se analisa uma empresa como a Petrobras?" e "o que um analista avalia?" são conceito (P5); "quem analisa" e "a CVM
// avalia" são de terceiro.
// "é uma boa empresa pra trabalhar?" é emprego, não o papel
const AVALIA_EMPRESA = r`(?<!\bcomo se )(?<!\bcomo )(?<!\bcomo eu )(?<!\banalista )(?<!\bquem )(?<!\bcvm )\b(analis(a|e|ar|aria)` +
  r`|avali(a|e|ar|aria)|avaliacao)\b(?! de risco\b)[^.?!]{0,25}\b${EMPRESA}\b|\b${EMPRESA}` +
  r`\b[^.?!]{0,25}\b(e|seria|ta|esta) (uma )?(boa|otima) (empresa|acao|compra)\b(?! (pra|para) (trabalhar` +
  r`|estagiar|estagio)\b)|\b${EMPRESA}` +
  r`\b[^.?!]{0,25}\b(e|seria|ta|esta) (uma )?(acao |empresa |papel )?(segur[ao]|solid[ao]|confiavel` +
  r`|arriscad[ao])\b|\b${EMPRESA}\b[^.?!]{0,25}\btem (bons )?fundamentos?\b|\bfundamentos? d[ao] ${EMPRESA}` +
  r`\b`
const MULTIPLO = r`\b(p ?/ ?l|multiplos?)\b[^.?!]{0,30}\b(alto|baixo|muito|pouco|caro|barato|atrativ\w*|bom|ruim)\b`
// A decisão é de juros (ou de preço) quando a pergunta cita um mercado, o Copom, o BC, a taxa ou o corte, ou é curta.
const SOBRE_JUROS = r`\b(copom|bc|banco central|taxas?|cortes?|reuniao|reunioes)\b`
// Comentário de pregão (N6): só quando a pergunta cita um contrato (WIN, WDO, DI, mini) e o pregão ("agora", "neste
// momento") ou o movimento em curso ("está caindo"). Os mercados mini_indice e mini_dolar também contam como contrato.
export const CONTRATO = r`\bwdo[fghjkmnquvxz]\d\d\b|\bdi1?\b|\bdi1[fghjkmnquvxz]\d\d\b|\bdi futuro\b|\bdolar futuro\b`
const HORA = r`\bagora\b|\bneste momento\b|\bhoje no pregao\b|\bao vivo\b`
const EM_CURSO = r`\b(esta|estao|ta|tao|segue|seguem|continua|continuam)( \w+)? (despencando|disparando|caindo|subindo` +
  r`|derretendo)\b`
// Sem contrato, "agora" com ordem é pedido de momento ("compro agora?") e com movimento é de direção ("a bolsa está
// caindo agora"): a recusa continua, com a linha certa, e sem falar de contrato.
const ORDEM = r`\b(entro|compro|vendo|opero|zero|troco|trago|mando|envio|converto|transfiro)\b`
const MOVIMENTO = r`\b(despencando|disparando|caindo|subindo|derretendo)\b`
const VOTO_INFORMADO = r`\b(eu )?vot(o|ei|arei|aria|ando) (\d+|no|na|em)\b` +
  r`|\bsou (\w+ )?(petista|bolsonarista|lulista|de direita|de esquerda|progressista)\b` +
  r`|\bodeio (o |a )?(pt|pl|lula|flavio|bolsonaro|esquerda|direita)\b|\b(o )?mito\b|\bfiz o l\b|\beu apoio\b` +
  r`|\btorco (pelo|pela|pro|para o)\b`
// Pedido de alocação, que a conta neutra (P4) nunca apaga.
const ALOCACAO = r`\bquanto (eu )?(coloco|ponho|invisto|aplico|boto|devia ter|deveria ter)\b|\bquantos contratos\b` +
  r`|\bquanto investir\b|\br\$ ?\d|\b\d+ ?mil\b|\b\d+ ?k\b|\btenho \d`
const CANDIDATO_OU_VITORIA = r`\b(flavio|bolsonaro|lula|vence|vencer|ganha|ganhar|reeleit\w*|favorit\w*|eurasia|frente)\b`
// A chance do candidato sem ganhar dinheiro ("quais as chances do lula ganhar?") não é a chance de a pessoa ganhar dinheiro.
const GANHO_DELA = r`\bganha(r)? (dinheiro|grana)\b|\blucr\w*|\bficar rico\b|\benriquec\w*|\bganho\b`
// P4 de câmbio: o dinheiro em moeda estrangeira que a pessoa contou e o gasto por mês, só para a conta (nunca para dizer
// o que fazer). "150 mil euros", "€150.000", "150k euros", "US$ 20 mil", "20 mil dólares"; "gasto 5 mil reais por mês".
const MOEDA = {
  euro: r`euros?|eur`,
  dolar: r`dolares|dolar|dollars?|usd|us\$|u\$`,
} satisfies Record<string, string>
// Antes do número, só o símbolo ou o código ("€" vira "euros" no normalizar): "o euro 2 dias depois" não é dinheiro.
const MOEDA_ANTES = r`euros|eur|usd|us\$|u\$`
const _NUM = r`(?<![\d.,])(\d[\d.,]{0,15})`
const _MULT = r`(?: ?(mil|k|milhao|milhoes|mi)\b)?`
// Depois do número, o que não é quantia de dinheiro: "2 dias", "1o turno", "3%", "5 pontos", "3 vezes".
const _NAO_QUANTIA = r`(?!\s*(%|o turno|a reuniao|dias?\b|anos?\b|mes\b|meses\b|vezes\b|semanas?\b|horas?\b|pontos?\b` +
  r`|turnos?\b))`
// "R$ 100 mil em euros" é real, não euro: o número logo depois de "r$" nunca é moeda estrangeira.
const VALOR_DEPOIS = r`(?<!r\$)(?<!r\$ )` +
  _NUM +
  _MULT +
  r` ?(?:de |em )?(` +
  Object.values(MOEDA).join('|') +
  r`)(?![\w$])`
const VALOR_ANTES = r`(?<![\w$])(` +
  MOEDA_ANTES +
  r`) ?` +
  _NUM +
  _MULT +
  _NAO_QUANTIA
const POR_MES = r`(por mes|ao mes|mensais|mensal|todo mes|cada mes|/ ?mes|a month|per month|monthly)\b`
// O gasto precisa de verbo de gasto antes ("gasto", "pago", "custa", "aluguel"): "rendendo 1% ao mês" e "ganho 10 mil
// por mês" não são gasto (renda é dado que o agente não usa, N5).
const GASTO_DEPOIS = r`\b(gast\w*|pag\w*|cust\w*|despes\w*|aluguel|mensalidade|preciso de|vivo com|uso|tiro|saco|spend\w*` +
  r`|pay\w*)\b[^.!?\d]{0,25}?(?:r\$ ?)?` +
  _NUM +
  _MULT +
  r`(?!\s*%)(?: ?(reais|` +
  Object.values(MOEDA).join('|') +
  r`))?[^.\d!?%]{0,25}?\b` +
  POR_MES
const GASTO_ANTES = r`\b(mensalidade|gasto mensal|custo mensal|despesa mensal)( (de|e|eh))? (?:r\$ ?)?` +
  _NUM +
  _MULT +
  r`(?: ?(reais|` +
  Object.values(MOEDA).join('|') +
  r`))?`
// Mover o dinheiro de lugar: quando, se e quanto mover é o que o agente não diz (N1, N4, N5).
// Sem "traz" (3ª pessoa: "o que a eleição traz para o dólar depois?") e sem "passo" ("passo a passo").
const TROCA = r`(trago|trazer|troco|trocar|converto|converter|mando|mandar|envio|enviar|transfiro|transferir|remeto` +
  r`|remeter|traer\w*|cambiar|bring|convert|exchange|move)`
const EVENTO = r`(o |a |do |da |de |the )?(segundo turno|2o turno|primeiro turno|turno|eleicao|election|domingo|copom` +
  r`|reuniao|resultado)`
// Quando mover: "troco hoje?", "trago depois do 2º turno?", "antes ou depois?", "qual o melhor momento pra trocar?".
const MOMENTO_TROCA = r`\b` +
  TROCA +
  r`\b[^.?!]{0,40}\b(agora|ahora|antes|depois|hoje|ja|amanha|now|before|after)\b` +
  r`|\b(quando|cuando|hoje|agora|ahora|antes|depois)\b[^.?!]{0,20}\b(troco|trocar|trago|trazer|traer\w*` +
  r`|mando|mandar|envio|enviar|converto|converter|transfiro|transferir|cambiar|cambio a)\b|\b(antes|depois` +
  r`|before|after) ` +
  EVENTO +
  r`\b[^.?!]{0,20}\bou (espero|esperar|depois|antes|nao)\b|\bantes ou depois\b` +
  r`|\bagora ou (depois|espero|mais tarde)\b|\bou espero\b` +
  r`|\b(momento|hora|dia|epoca|data)\b[^.?!]{0,20}\b(trocar|trazer|converter|mandar|enviar|transferir` +
  r`|cambiar)\b`
// Quanto mover, ou que parte: alocação (N5). Aí o valor não entra na conta, e vale a recusa do capital.
const QUANTO_TROCAR = r`\bquanto (\w+ ){0,4}?(coloco|ponho|invisto|aplico|boto|trago|troco|converto|mando|envio|remeto|mantenho` +
  r`|deixo|tiro|passo|devia|deveria|trazer|trocar|converter|mandar|enviar|remeter|manter|deixar|tirar` +
  r`|passar)\b|\bquanto investir\b|\bquantos contratos\b|\b(que|qual|quanto) (parte|porcentagem|percentual` +
  r`|fatia|pedaco)\b|\bquanto disso\b|\b(` +
  TROCA.slice(1, -1) +
  r`|deixo|mantenho)\b[^.?!]{0,25}\b(tudo|metade|um terco|uma parte|parte|o resto|aos poucos|de uma vez` +
  r`|em (parcelas|etapas)|\d+ ?%|half|all)\b|\b(tudo|metade|parte) ou (tudo|metade|parte` +
  r`|nada)\b|\bhow much\b|\b(what|which) (part|portion|percentage|share)\b|\ball or (half|part)\b`
const MULTIPLICA: ReadonlyMap<string, number> = new Map([['mil', 1e3], ['k', 1e3], ['milhao', 1e6], ['milhoes', 1e6], ['mi', 1e6]])
// Em pergunta de petróleo, "100 dólares" é o preço do barril, não o dinheiro da pessoa, a não ser que ela diga que tem.
// O número começa onde não há outro dígito antes ((?<![\d.,])): sem isso, "1111..." recomeça em cada posição e a
// conta fica quadrática no tamanho da pergunta (2.000 caracteres = 0,2 s).
export const PRECO_EM_DOLAR = r`(us\$|u\$|usd) ?\d[\d.,]*( ?(mil|k))?` +
  r`|(?<![\d.,])\d[\d.,]*( ?(mil|k))? ?(de )?(dolares|dolar|dollars?|usd)\b`
const POSSE = r`\b(tenho|guardei|guardo|juntei|economizei|poupei|meus|minhas|recebi|ganhei)\b`
// Pôr o dinheiro num mercado ("invisto em petróleo?", "compro ações da Petrobras com isso?"). Sem "compra" (substantivo):
// "poder de compra" é câmbio.
const INVESTE = r`\b((re)?invisto|investir|investiria|aplico|aplicar|aplicaria|compro|comprar|compraria|coloco|colocar` +
  r`|ponho|boto|botar|que tal)\b`
// O preço do barril ou do litro em moeda estrangeira ("o Brent a 100 dólares", "90 dólares o barril") sai do texto antes de
// achar o dinheiro da pessoa (_so_o_dinheiro_dela).
const _DINHEIRO = r`(?:(?:euros|eur|usd|us\$|u\$) ?\d[\d.,]*(?: ?(?:mil|k|milhao|milhoes|mi)\b)?` +
  r`|(?<![\d.,])\d[\d.,]*(?: ?(?:mil|k|milhao|milhoes|mi)\b)? ?(?:de |em )?(?:euros?|eur|dolares|dolar` +
  r`|dollars?|usd|us\$|u\$)(?![\w$]))`
const PRECO_DO_BARRIL = r`\b(?:petroleo|brent|wti|barril|barris|opep|opec|gasolina|diesel|etanol|combustive(?:l|is)` +
  r`|litro)\b(?: (?:a|de|em|por|o|esta|ta|foi|vai|passou|passa|passar|bateu|bater|chegou|chega|chegar|acima` +
  r`|abaixo|perto|caiu|cai|subiu|sobe|custa|custava|custando|cotado|para|pra))* ?` +
  _DINHEIRO +
  r`|` +
  _DINHEIRO +
  r` (?:o |no |na |por |cada |do |de |a |per |the )?(?:barril|barris|litros?|galao|barrel|liter|gallon)\b`
// O preço da cripto em moeda estrangeira ("o bitcoin passou de 100 mil dólares?", "quando o bitcoin bateu 100 mil
// dólares?") não é o dinheiro da pessoa; o que é dela ("meu bitcoin chegou a 10 mil dólares", "comprei bitcoin a 10 mil
// dólares") continua.
const PRECO_DA_CRIPTO = r`(?<!\bmeu )(?<!\bmeus )(?<!\bminha )(?<!\bminhas )(?<!\bmy )\b(?:bitcoins?|btc|ether(?:eum)?|eth` +
  r`|solana)\b(?: (?:ja|nunca|nao|so|em (?:19|20)\d\d))*(?: (?:esta|ta|tava|estava|foi|era|vai|passou|passa` +
  r`|passar|passava|bateu|bate|bater|batia|chegou|chega|chegar|chegava|caiu|cai|subiu|sobe|custa|custava` +
  r`|custou|cotado|valia|voltou|acima|abaixo|perto))+(?: (?:de|a|ao|aos|os|em|para|pra|dos|casa dos))* ?` +
  _DINHEIRO
// Valor em reais que é preço ou fato ("dividendo de R$ 6,73 por ação", "os R$ 20 bilhões", "a gasolina a R$ 6,53"), não o
// dinheiro da pessoa: não é capital.
// o preço unitário: sem "mil" nem 4 dígitos, que é o dinheiro da pessoa ("recebi dividendos de R$ 5 mil",
// "tenho uma ação de R$ 10 mil"). O dividendo por ação já vem pelo "por ação" do 1º ramo.
// o preço dito com verbo ("a gasolina está R$ 6,53?", "subiu pra R$ 7", "o barril em reais passou de R$ 600")
const PRECO_OU_FATO = ALVO_NUM +
  r`|r\$ ?\d[\d.,]*( ?(mil|mi|bi|bilh\w*|milh\w*))? por (acao|litro|barril)\b|r\$ ?\d[\d.,]* ?(bi|bilh\w*)\b` +
  r`|r\$ ?\d[\d.,]* ?milh\w* (de|em) (dividendo|lucro|juros)\w*` +
  r`|\b(gasolina|diesel|etanol|dolar|euro|barril|litro|acao|petr[34]|petrobras)( em reais)? (a|de|em|por` +
  r`|chegou a|chegou em|bateu|custa\w*|esta|ta|esta a|ta a|foi a|foi de|passou de|passa de|subiu|caiu` +
  r`|subiu (pra|para|a)|caiu (pra|para|a)|pagou( dividendos?)?( de)?) r\$ ?(?![\d.,]* ?(mil|mi|milh\w*|k)\b` +
  r`|\d{4}|\d{1,3}\.\d{3})\d[\d.,]*`
// O valor é dinheiro da pessoa quando ela diz que é dela ou pergunta onde pôr: aí o PRECO_OU_FATO não apaga o capital.
const ALOCACAO_REAIS = r`\b(coloco|ponho|boto|invisto|aplico|reinvisto|reinvesto|reinvestir|reinvestiria)\b`
// A posse vale na oração do valor e sem palavra de preço entre as duas ("tenho uma dúvida, o dólar chegou a R$ 6,30?",
// "meus pais dizem que a gasolina custava R$ 2" não são dinheiro dela).
const PALAVRA_DE_PRECO = r`\b(gasolina|diesel|etanol|dolar|euro|barril|litro|acao|petr[34]|petrobras|bitcoin)\b`
// Em pergunta de petróleo, o dinheiro em moeda estrangeira só é da pessoa quando ela diz que tem, que leva, que quer
// trazer ou converter, ou que está na conta; o resto é preço ("tenho uma dúvida: o petróleo passou de 100 dólares?"). A
// posse vale na mesma oração do número e sem palavra de petróleo entre as duas ("meus amigos dizem que o barril...").
const OLEO = r`\b(petroleo|brent|wti|barril|barris|opep|opec)\b`
const POSSE_ANTES = POSSE +
  r`|\b(levo|levar|levando|to com|tou com|estou com|fiquei com|i have|i've got)\b|^\W*com\b` +
  r`|\b(viaj\w*|vou|indo|estou|to|fico|ficar|volto|voltar|chego|chegar)\b[^.?!,;:]{0,15}\bcom\b` +
  r`|\b(trazer|mandar|trocar|converter|enviar|transferir|remeter|trago|mando|troco|converto|envio|transfiro` +
  r`|remeto)\b`
// O verbo sem pessoa ("trazer", "levar", "voltar com") depois do petróleo tem o petróleo como sujeito ("o petróleo pode
// trazer 10 dólares de alta?", "a OPEP pode levar o preço a 90 dólares?"): só é da pessoa com ela entre os dois ("com o
// petróleo subindo, quero trazer", "o petróleo mexe se eu trazer").
const POSSE_SEM_PESSOA = r`(levar|levando|trazer|mandar|trocar|converter|enviar|transferir|remeter|viaj(ar|ando)|indo|ficar|voltar` +
  r`|chegar)\b`
const PESSOA = r`\b(eu|a gente|quero|queria|vou|vamos|preciso|precisava|pretendo|tenho|posso|consigo|gostaria)\b`
// "100 dólares dão quantos reais?", "viram quanto?" também são conversão
const CONVERSAO = r`\b(em|pra|para|pro) (o )?(real|reais)\b|\bquantos reais\b` +
  r`|\b(viram|vira|da|dao|e|sao) quantos?( reais)?\b|\bviram quanto\b|\bconvert\w*` +
  r`|\bquanto (vale|valem|e|da|dao|sao|fica|ficam|seria|seriam)\b`
const NA_CONTA = r`(?: (?:parad|guardad)[oa]s?)? (?:na|em) (?:minha |uma )?conta\b`
// O dinheiro que a pessoa tem ou leva, com o prazo da viagem ("tenho 2 mil dólares pra viagem do ano que vem, quanto dá em
// reais?"), não é nível com prazo: sai do texto do FUTURO. Fica quando a pergunta é o valor que ainda vem ("quanto valem meus
// 2 mil dólares no ano que vem?", "vai dar quanto?") e quando o número vem logo depois do verbo de nível ("tenho medo de o
// dólar chegar a 6 dólares até o fim do ano").
const VALOR_QUE_VEM = r`\b(quanto|vale|valem|valer|valeria|valeriam)\b[^.?!,;:]{0,40}(` +
  PRAZO +
  r`|\bate la\b|\b(nessa|naquela|na) (epoca|data|altura)\b)|(` +
  PRAZO +
  r`)[^.?!,;:]{0,20}\b(quanto|vale|valem|valer)\b|\b(vai|vao|ira|irao|iria|iriam) (dar|valer|virar|render` +
  r`|ficar|ser)\b|\b(dara|darao|daria|dariam|valera|valerao|valeria|valeriam|viraria|virariam)\b`
const ANTES_DO_NIVEL = r`(?:\b(?:a|em|to|at|passa\w* (?:de|dos|das)|(?:sai|vai) de)(?: us\$| r\$| \$|\$)?|` +
  NIVEL_VERBO +
  r`)\s*$`
/** _moeda do Python: o rótulo que o padrão achou vira a chave da moeda; "reais" é o real. */
function _moeda(rotulo: string | undefined): string | null {
  if (!rotulo) return null
  if (rotulo === 'reais') return 'real'
  const achada = Object.entries(MOEDA).find(([, padrao]) => fullmatch(padrao, rotulo))
  // o next() do Python levanta StopIteration; não acontece, porque o rótulo saiu do mesmo padrão
  if (!achada) throw new Error(`moeda desconhecida: ${rotulo}`)
  return achada[0]
}
/** _quantia do Python: a quantia em qualquer formato que um brasileiro ou um estrangeiro escreve: '150.000' e '150,5'
 * (Brasil), '50,000' e '1.5' (inglês, com até 2 casas depois do ponto), '1,5' + 'milhao' → 1.500.000. Número quebrado
 * ('1,2,3') ou absurdo não vale. A pontuação colada no fim ("4.500," / "150.000.") não é parte do número. */
function _quantia(bruto: string, mult: string | undefined): number | null {
  const numero = bruto.replace(/[.,]+$/, '') // rstrip('.,')
  let texto: string
  if (fullmatch(r`\d{1,3}(\.\d{3})+(,\d+)?`, numero)) texto = numero.replaceAll('.', '').replaceAll(',', '.') // 150.000 / 150.000,50
  else if (fullmatch(r`\d{1,3}(,\d{3})+(\.\d+)?`, numero)) texto = numero.replaceAll(',', '') // 50,000 / 2,000.50
  else if (fullmatch(r`\d+,\d+`, numero)) texto = numero.replace(',', '.') // 1,5
  else if (fullmatch(r`\d+\.\d{1,2}`, numero) || fullmatch(r`\d+`, numero)) texto = numero // 1.5 / 1.25 / 150
  else return null
  const v = Number(texto) * (MULTIPLICA.get(mult ?? '') ?? 1)
  return 0 < v && v < 1e10 ? v : null
}
export type Cambio = [valor: number | null, moeda: string | null, gasto: number | null, gasto_moeda: string | null]

/** cambio() do Python: (valor, moeda, gasto por mês, moeda do gasto) do texto já normalizado. O gasto sem moeda é em reais. */
export function cambio(t: string): Cambio {
  let gasto: number | null = null
  let gastoMoeda: string | null = null
  let g = search(GASTO_DEPOIS, t)
  if (g) {
    gasto = _quantia(g.group(2)!, g.group(3))
    gastoMoeda = _moeda(g.group(4)) ?? 'real'
  } else {
    g = search(GASTO_ANTES, t)
    if (g) {
      gasto = _quantia(g.group(4)!, g.group(5))
      gastoMoeda = _moeda(g.group(6)) ?? 'real'
    }
  }
  if (gasto === null) {
    g = null
    gastoMoeda = null
  }
  // O valor é o 1º dinheiro em moeda estrangeira do texto que não seja o próprio gasto ("pago 3 mil dólares por mês").
  // Os dois padrões nunca começam na mesma posição (um começa por dígito, o outro por letra): ordenar pelo início basta.
  type Achado = [number, string, string | undefined, string]
  const achados: Achado[] = [
    ...finditer(VALOR_DEPOIS, t).map((m): Achado => [m.start, m.group(1)!, m.group(2), m.group(3)!]),
    ...finditer(VALOR_ANTES, t).map((m): Achado => [m.start, m.group(2)!, m.group(3), m.group(1)!]),
  ].sort((a, b) => a[0] - b[0])
  for (const [inicio, numero, mult, rotulo] of achados) {
    if (g && g.start <= inicio && inicio < g.end) continue
    const valor = _quantia(numero, mult)
    if (valor !== null) return [valor, _moeda(rotulo), gasto, gastoMoeda]
  }
  return [null, null, gasto, gastoMoeda]
}
// Os mercados que o histórico das eleições, do Copom e da linha do tempo mede.
// Os mercados que o histórico das eleições, do Copom e da linha do tempo mede.
export const MEDIDOS = ['ibovespa', 'dolar', 'juros'] as const
/** Pedido.eleicao do Python. */
export function ehEleicao(p: Pedido): boolean {
  return p.temas.includes('eleicao') || p.candidatos.length > 0 ||
    p.proibidos.some((x) => x === 'chance_candidato' || x === 'voto')
}

/** Pedido.conta do Python: há pontos e o mercado é mini-índice ou mini-dólar. */
export function temConta(p: Pedido): boolean {
  return p.pontos !== null && p.mercados.some((m) => m === 'mini_indice' || m === 'mini_dolar')
}

/** Pedido.conta_cambio do Python: a pessoa contou dinheiro em euro ou em dólar. */
export function temContaCambio(p: Pedido): boolean {
  return typeof p.valor_moeda === 'number' && (p.moeda === 'euro' || p.moeda === 'dolar')
}

/** Pedido.cambio do Python: pergunta de câmbio, que fala de euro ou contou dinheiro em moeda estrangeira. */
export function ehCambio(p: Pedido): boolean {
  return p.mercados.includes('euro') || temContaCambio(p)
}

/** Junta duas leituras da mesma pergunta (a das palavras e a da IA): o que uma achou, vale. */
export function somar(a: Pedido, b: Pedido): Pedido {
  const junta = (x: string[], y: string[]): string[] => [...x, ...y.filter((v) => !x.includes(v))]
  const proibidos = junta(a.proibidos, b.proibidos)
  // A IA viu pedido de capital que as palavras não pegaram: vale a leitura dela, e a conta de câmbio sai (senão a resposta
  // diria "não uso o valor que você tem" e logo depois usaria).
  const semConta = proibidos.includes('capital')
  return {
    pergunta: a.pergunta,
    mercados: junta(a.mercados, b.mercados),
    candidatos: junta(a.candidatos, b.candidatos),
    temas: junta(a.temas, b.temas),
    proibidos,
    voto_informado: a.voto_informado || b.voto_informado,
    pontos: a.pontos !== null ? a.pontos : b.pontos,
    contratos: a.contratos,
    // os quatro do câmbio vêm da primeira leitura (a das palavras), como no Python
    valor_moeda: semConta ? null : a.valor_moeda,
    moeda: semConta ? null : a.moeda,
    gasto_mensal: semConta ? null : a.gasto_mensal,
    gasto_moeda: semConta ? null : a.gasto_moeda,
  }
}

export function resumo(p: Pedido): string {
  const lista = (xs: string[]): string => xs.join(', ') || 'nenhum'
  const partes = [`mercados: ${lista(p.mercados)}`, `candidatos: ${lista(p.candidatos)}`, `temas: ${lista(p.temas)}`,
    `pedidos que pedem recusa: ${lista(p.proibidos)}`]
  if (p.voto_informado) partes.push('a pessoa contou o próprio voto (não usar)')
  return partes.join('; ')
}
/** float() do Python sobre "1.000,5" → 1000.5. Como lá, "1,5,3" (dois pontos decimais) é erro, não NaN. */
function _numero(s: string): number {
  const limpo = s.replaceAll('.', '').replaceAll(',', '.')
  const n = Number(limpo)
  if (Number.isNaN(n)) throw new Error(`could not convert string to float: '${limpo}'`)
  return n
}

function tirar(xs: string[], x: string): void {
  const i = xs.indexOf(x)
  if (i >= 0) xs.splice(i, 1)
}

// O que é espaço para o \s e o split() do Python num texto ASCII.
const ESPACO = r`\t\n\v\f\r\x1c-\x1f `
const PALAVRAS = new RegExp(`[${ESPACO}]+`)
const SEM_ESPACO = new RegExp(`[^${ESPACO}]`) // o str.strip() do Python deixa algo
// - a regra e a agenda com "vai valer/custar/estar/ficar" ("quando a isenção de 20 mil vai valer?", "quanto vai custar o
// IOF?", "a bolsa vai estar aberta no Natal?", "a OPEP vai estar reunida em dezembro?") não são o preço que ainda vem. A
// taxa de juros e a de câmbio são preço; "quanto vai custar a gasolina com o imposto novo?", "quanto o dólar vai custar
// com IOF?", "com o IOF o dólar vai ficar acima de 6?" e "o dólar vai estar fechado em alta?" continuam recusa.
const VAI_SER = r`\b(vai|vao|va a|van a) (estar|valer|custar|ficar|ta)\b`
const _REGRA = r`(regras?|leis?|normas?|isencao|isent[oa]s?|impostos?|aliquotas?|iof|ir|irpf|tributos?|tarifas?` +
  r`|corretagem|emolumentos?|custodia|come[- ]?cotas` +
  r`|taxas?(?! (de |do |da )?(selic|cambio|juros|basica|dolar|di|cdi|referencial)\b))`
// a regra antes do verbo é o sujeito, menos depois de "com/sem" ("com o IOF o dólar vai ficar acima de 6?")
const REGRA_ANTES = r`(?<!\bcom )(?<!\bsem )(?<!\bcom o )(?<!\bcom a )(?<!\bsem o )(?<!\bsem a )\b${_REGRA}\b[^.?!;:,]{0,40}$`
const REGRA_DEPOIS = r`(( a| o| em)? (partir|vigor|vigente|valendo)\b|( o| a| os| as)? ${_REGRA}` +
  r`\b| (abert|fechad|reunid)[oa]s?\b(?! (em (alta|queda|baixa)|acima|abaixo|no (positivo|negativo|azul` +
  r`|vermelho))\b)| (funcionando|em recesso|de recesso)\b)`
const QUANTO = r`\b(quanto|qto|qnto|cuanto)\b`
// - o prazo numa oração com o movimento no pretérito ("o brent subiu de 60 a 115 até outubro?") ou com o Focus ("a cotação
// do dólar esperada pelo Focus para o fim do ano") não é o prazo de uma previsão.
const PRAZO_SEM_PREVISAO = MOVIMENTO_PASSADO +
  r`|\bfocus\b`
function _trecho(t: string, m: Casamento, corte: string): string {
  return ultimo(corte, t.slice(0, m.start)) + m.group() + primeiro(corte, t.slice(m.end))
}
/** Tira cada `alvo` cujo trecho (a oração ou a frase, pelo `corte`) tem a `marca`. */
function _tira(t: string, alvo: string, marca: string, corte: string): string {
  return sub(alvo, (m) => search(marca, _trecho(t, m, corte)) ? ' ' : m.group()!, t)
}
/** Tira o "vai valer/custar/estar/ficar" da regra e da agenda. */
function _sem_regra_nem_agenda(t: string): string {
  const troca = (m: Casamento): string => {
    const antes = ultimo(ORACAO, t.slice(0, m.start))
    const depois = t.slice(m.end)
    const regra = match(REGRA_DEPOIS, depois) || (search(REGRA_ANTES, antes) && !search(QUANTO, _trecho(t, m, ORACAO)))
    // com outro sujeito junto ("o IOF vai ficar em 3,5%, e o dólar?"), continua recusa
    return regra && !search(COORDENA, _trecho(t, m, r`[?!]`)) ? ' ' : m.group()!
  }
  return sub(VAI_SER, troca, t)
}
/** Onde termina cada marca de posse da oração, menos o verbo sem pessoa que tem o petróleo de sujeito. */
function _posse(oracao: string): number[] {
  const oleo = finditer(OLEO, oracao).map((x) => x.start)
  return finditer(POSSE_ANTES, oracao)
    .filter((x) =>
      !(match(POSSE_SEM_PESSOA, x.group()!) && oleo.length && oleo[0] < x.start &&
        !search(PESSOA, oracao.slice(Math.max(...oleo.filter((o) => o < x.start)), x.start)))
    )
    .map((x) => x.end)
}
/** Tira do texto do FUTURO o dinheiro que a pessoa diz que tem ou leva (posse na mesma oração). */
function _sem_o_dinheiro_dela(t: string): string {
  if (search(VALOR_QUE_VEM, t)) return t
  const troca = (m: Casamento): string => {
    const antes = t.slice(0, m.start)
    const oracao = ultimo(r`[?!;:]|\.(?!\d)|,(?!\d)`, antes)
    const dela = _posse(oracao).length > 0 && !search(ANTES_DO_NIVEL, antes)
    return dela ? ' ' : m.group()!
  }
  return sub(_DINHEIRO, troca, t)
}
/** O texto que o FUTURO lê: sem o "cara" que não é preço, sem o "descontado" de imposto e sem a regra de queda. */
function _texto_do_futuro(t: string): string {
  if (search(DEFINICAO_VALUATION, t)) return ''
  t = sub(CARA_NAO_PRECO, ' ', t)
  if (search(BOMBA_EXPLICA, t) && !search(FUTURO_EXPLICITO, t) && !search(BOMBA_E_EMPRESA, t)) t = sub(BOMBA_CARA, r`\1\2`, t)
  t = sub(DESCONTO_NA_FONTE, ' ', t)
  if (!search(r`\b${EMPRESA}\b`, t)) {
    t = sub(DESCONTO_NAO_PRECO, (m) =>
      search(ADJUNTO_ANTES, m.string.slice(0, m.start)) ? m.group()! : sub(r`descontad[oa]s?\b`, ' ', m.group()!), t)
  }
  if (search(REGRA_DE_QUEDA, t)) t = sub(PASSA_DE_PCT, ' ', t)
  if (search(REGRA_CIRCUIT, t)) {
    t = sub(CAI_MAIS_PCT, ' ', t)
    t = sub(r`\bcircuit[ -]?breakers? (dispara\w*|aciona\w*|e acionado)\b`, ' ', t) // quem dispara é a regra
  }
  t = _sem_regra_nem_agenda(t)
  const semRegra = (m: Casamento): string => {
    const frase = ultimo(r`[?!]`, t.slice(0, m.start)) + m.group() + primeiro(r`[?!]`, t.slice(m.end))
    return search(COORDENA, frase) ? m.group()! : ' '
  }
  t = sub(REGRA_FUTURA, semRegra, t)
  t = _tira(t, PRAZO, PRAZO_SEM_PREVISAO, ORACAO)
  t = sub(VIAGEM, ' ', t)
  return _sem_o_dinheiro_dela(sub(INTERVALO, ' ', t))
}
/** Em pergunta de petróleo, o texto só com o dinheiro que é da pessoa: a posse na mesma oração e sem petróleo entre as
 * duas, a conversão na mesma frase, "na conta" logo depois, ou o gasto por mês. O resto vira espaço. */
function _so_o_dinheiro_dela(t: string): string {
  const gastos = [...finditer(GASTO_DEPOIS, t), ...finditer(GASTO_ANTES, t)].map((g) => [g.start, g.end] as const)
  const troca = (m: Casamento): string => {
    const antes = t.slice(0, m.start)
    const depois = t.slice(m.end)
    const oracao = ultimo(r`[?!;:]|\.(?!\d)|,(?!\d)`, antes)
    const frase = ultimo(r`[?!]|\.(?!\d)`, antes) + m.group() + primeiro(r`[?!]|\.(?!\d)`, depois)
    const oleo = finditer(OLEO, oracao).map((x) => x.start)
    const posse = _posse(oracao)
    const dela = (posse.length > 0 && !(oleo.length && oleo.at(-1)! > posse.at(-1)!)) || Boolean(match(NA_CONTA, depois)) ||
      Boolean(search(CONVERSAO, frase)) || gastos.some(([a, b]) => a <= m.start && m.start < b)
    return dela ? m.group()! : ' '
  }
  return sub(_DINHEIRO, troca, t)
}
// A regra do imposto, da declaração, do FGC ou da custódia não é onde pôr o dinheiro (P5): o lugar do verbo é a declaração,
// o verbo está na oração do "se" e a pergunta é a regra, a guarda é dita e a pergunta é declarar, ou o que se guarda é a
// seed. Com "ou", motivo ("pra não pagar IR", "por causa do FGC"), "tudo" ou ganho continua dica.
const _SEM_MOTIVO = r`(?:(?!\b(ou|pra|para|por causa|porque|ja que|antes|tudo|todo|toda|todos)\b)[^.?!,;])`
const _SEM_GANHO = r`(?![^.?!]*\b(ganh\w*|rend\w*|lucr\w*|compens\w*|mais|menos|melhor|pior)\b)`
const DECLARACAO_LUGAR = r`(declarac\w*|ficha|bens e direitos|irpf|imposto de renda)`
const REGRA_IMPOSTO = r`(\b(pago|pagaria|paga|pagar|tem|teria|incide|cobr\w*|recolh\w*|descont\w*)\b[^.?!]{0,20}\b(ir(?! (pra` +
  r`|para|ate|a|ao)\b)|iof|imposto\w*|darf|come[- ]cotas)\b|\b(isent\w*|fgc|declar\w*|aliquota\w*|tribut\w*` +
  r`|irpf)\b)`
const REGRA_DO_VERBO = r`\b(onde (eu )?)?(coloco|ponho|boto|lanco|informo)\b${_SEM_MOTIVO}` +
  r`{0,40}\b(em|na|no|nas|nos)( (qual|que|a|o))? ${DECLARACAO_LUGAR}` +
  r`\b|\b(em )?(qual|que) (ficha|grupo|codigo|campo|parte)\b${_SEM_MOTIVO}` +
  r`{0,40}\b(coloco|ponho|boto|lanco|informo)\b` +
  r`|\b(se|quando|caso)( eu)? (re)?(invisto|aplico|coloco|ponho|boto|deixo|guardo)\b${_SEM_MOTIVO}` +
  r`{0,50}[,;](?=[^.?!]{0,40}${REGRA_IMPOSTO})${_SEM_GANHO}|(?<!onde )(?<!onde eu )\b(guardo|deixo)\b` +
  r`${_SEM_MOTIVO}{0,50}[,;](?=[^.?!]{0,30}\b(declar\w*|imposto\w*|tribut\w*|isent\w*)\b)${_SEM_GANHO}` +
  r`|\b(guardo|deixo|anoto|coloco|ponho|boto)\b (a |as |o |os |minha |minhas |meu |meus )?(seed|senha\w*` +
  r`|chave\w*( privada)?|frase\w*( de recuperacao| semente)?|palavras( de recuperacao)?|\d+ palavras` +
  r`|backup)\b`
/** O valor em reais é dinheiro da pessoa: ela pergunta onde pôr, ou diz que tem na mesma oração do valor. */
function _valor_e_dela(t: string): boolean {
  if (search(ALOCACAO_REAIS, t)) return true
  for (const m of finditer(r`r\$ ?\d`, t)) {
    const oracao = ultimo(r`[?!;:]|\.(?!\d)|,(?!\d)`, t.slice(0, m.start))
    const posse = finditer(POSSE, oracao).map((x) => x.end)
    if (posse.length && !search(PALAVRA_DE_PRECO, oracao.slice(posse.at(-1)))) return true
  }
  return false
}
function _eliptica_do_passado(oracoes: string[], i: number): boolean {
  const m = match(ELIPTICA, oracoes[i])
  if (!m || (m.group(1) && !fullmatch(r`19\d\d|20[01]\d|202[0-5]`, m.group(1)!))) return false
  let j: number | null = null
  for (let k = i - 1; k >= 0; k--) {
    if (SEM_ESPACO.test(oracoes[k])) {
      j = k
      break
    }
  }
  if (j === null || search(r`\b${EMPRESA}\b`, oracoes[i] + ' ' + oracoes[j])) return false
  return Boolean(search(r`\b(barat|car)[oa]s?\b`, oracoes[j])) &&
    Boolean(search(PASSADO, oracoes[j]) || _eliptica_do_passado(oracoes, j))
}
/** A oração tem marca de passado própria: o advérbio do trecho, o pretérito (sem verbo de pedido no presente depois
 * dele), o ano que já passou numa oração sem verbo de pedido, ou a elipse do "ficou caro/barato" da anterior. */
function _oracao_marcada(oracoes: string[], i: number, adverbio: boolean): boolean {
  const o = oracoes[i]
  if (adverbio || search(PASSADO_DA_FRASE, o)) return true
  if (search(PASSADO_VERBAL + '.*' + VERBO_PEDIDO, sub(SUBORDINADA, '', o))) return false
  return Boolean(_passado_da_oracao(o) || search(MOVIMENTO_PASSADO, o) ||
    (search(ANO_PASSADO, o) && !search(VERBO_PEDIDO, o)) || _eliptica_do_passado(oracoes, i))
}
export function analisar(pergunta: string): Pedido {
  const t = normalizar(pergunta)
  const achou = (padroes: Record<string, string>, texto = t): string[] =>
    Object.entries(padroes).filter(([, padrao]) => search(padrao, texto)).map(([k]) => k)
  const tem = (xs: string[], ...ys: string[]): boolean => ys.some((y) => xs.includes(y))
  // O presidente da Petrobras e o domingo da reunião da OPEP não são a eleição, a não ser que a pergunta cite a eleição
  // de outro jeito.
  let tEleicao = t
  if (!search(ELEITORAL, sub(CARGO_ELEITO, ' ', t))) {
    tEleicao = sub(CARGO, ' ', sub(CARGO_ELEITO, ' ', t))
    if (search(r`\b(petrobras|petr[34])\b`, t)) {
      tEleicao = sub(r`\bex[- ]?presidente( (jair )?bolsonaro\b)?`, ' ', tEleicao)
      if (search(GOVERNO_BOLSONARO, t) || (search(GOVERNO_BOLSONARO_NOME, t) && !search(FUTURO, t))) {
        tEleicao = sub(r`\bbolsonaro\b`, ' ', tEleicao)
      }
    }
  }
  if (search(r`\b(opep|opec)\b`, t)) tEleicao = sub(r`\bdomingo\b`, ' ', tEleicao)
  const temas = Object.entries(TEMAS).filter(([k, padrao]) => search(padrao, k === 'eleicao' ? tEleicao : t)).map(([k]) => k)
  const p: Pedido = {
    pergunta, mercados: achou(MERCADOS, sub(GASOLINA_FIGURADA, ' ', t)), candidatos: achou(CANDIDATOS, tEleicao), temas,
    proibidos: achou(PROIBIDOS), voto_informado: Boolean(search(VOTO_INFORMADO, t)), pontos: null, contratos: 1,
    valor_moeda: null, moeda: null, gasto_mensal: null, gasto_moeda: null,
  }
  // O preço, o fato e o alvo em reais não são o dinheiro da pessoa; o que ela diz que é dela ("recebi dividendos de R$ 50
  // mil, onde ponho?") continua capital (N5).
  if (p.proibidos.includes('capital') && !_valor_e_dela(t) && !search(PROIBIDOS.capital, sub(PRECO_OU_FATO, ' ', t))) {
    tirar(p.proibidos, 'capital')
  }
  // O momento que já passou não é pedido de entrada, a não ser que o resto da pergunta peça dica.
  // Só sai o trecho do momento que já passou: um "e hoje é bom momento?" depois dele continua dica (N1).
  if (p.proibidos.includes('dica') && search(MOMENTO_PASSADO, t) &&
    !search(FUTURO_EXPLICITO + '|' + MOMENTO_PRA + r`|\be hoje\b`, t) && !search(PROIBIDOS.dica, sub(MOMENTO_PASSADO, ' ', t))) {
    tirar(p.proibidos, 'dica')
  }
  // A viagem não é a entrada ("embarco semana que vem pra Lisboa com 2 mil euros, quanto dá em reais?" é a conta, P4).
  if (p.proibidos.includes('dica') && search(VIAGEM, t) && !search(PROIBIDOS.dica, sub(VIAGEM, ' ', t))) tirar(p.proibidos, 'dica')
  if (p.proibidos.includes('dica') && search(REGRA_DO_VERBO, t) && !search(PROIBIDOS.dica, sub(REGRA_DO_VERBO, ' ', t))) {
    tirar(p.proibidos, 'dica')
  }
  if (p.voto_informado && !p.temas.includes('eleicao')) p.temas.push('eleicao')
  // Conceito de derivativo (margem, ajuste diário, alavancagem): a explicação está no bloco do mini-índice.
  if (search(r`\bmargem\b|\bajuste diario\b|\balavancagem\b`, t) && p.mercados.length === 0) p.mercados.push('mini_indice')
  // Futuro de um preço: na dúvida, recusa. Vale com mercado, candidato, eleição, Copom ou pergunta curta ("sobe?").
  const curta = t.split(PALAVRAS).filter((w) => w !== '').length <= 4
  const sobrePreco = p.mercados.length > 0 || p.candidatos.length > 0 || tem(p.temas, 'eleicao', 'copom') || curta
  const condicional = search(CONDICIONAL, t)
  const tFuturo = _texto_do_futuro(t)
  const futuro = search(FUTURO, tFuturo) || condicional
  // O passado só vale quando nenhuma oração pede o futuro sem uma marca de passado própria. A oração seguinte que pergunta
  // o que foi ("corta ou mantém, qual foi a decisão?") também é marca de passado.
  // O advérbio ("historicamente", "no passado") vale para a frase toda só quando no máximo um trecho pede ou se move; senão,
  // só para o próprio trecho. O "qual foi" da oração seguinte só vale para a decisão ("corta ou mantém, qual foi?").
  const trechos = split(TRECHO, tFuturo) as string[] // TRECHO não tem grupo: só texto
  const oracoes: [string, boolean][] = trechos.flatMap((tr) =>
    (split(r`\b(?:e|mas)\b`, tr) as string[]).map((o): [string, boolean] => [o, Boolean(search(PASSADO_DA_FRASE, tr))])
  )
  const pedem = (o: string) => search(FUTURO, o) || search(DECISAO_OU, o)
  const textos = oracoes.map(([x]) => x)
  const soPassado = Boolean(search(PASSADO, t)) && !condicional && !search(FUTURO_EXPLICITO, t) && (
    (Boolean(search(PASSADO_DA_FRASE, t)) &&
      trechos.filter((tr) => pedem(tr) || search(MOVIMENTO_PASSADO, tr)).length <= 1) ||
    !oracoes.some(([o, adv], i) =>
      pedem(o) && !_oracao_marcada(textos, i, adv) &&
      !(search(DECISAO_OU, o) && i + 1 < oracoes.length && match(QUAL_FOI, oracoes[i + 1][0]))
    )
  )
  // Decisão de juros que ainda vai sair ("vai cortar a Selic?", "corta ou mantém?") também é futuro de preço.
  const decisao = (p.mercados.length > 0 || Boolean(search(SOBRE_JUROS, t)) || curta) && Boolean(
    search(DECISAO, t) ||
      ((search(DECISAO_OU, t) || (search(DECISAO_DATA, t) && !search(EXPLICA_POR_QUE, t))) && !soPassado),
  )
  // Lucro de uma empresa que ainda vai sair ("a Petrobras vai lucrar?", "o lucro da Petrobras vem forte?") é projeção; o
  // da pessoa é chance_dinheiro, que só sai quando a única palavra de lucro é a da empresa.
  const lucroEmpresa = Boolean(search(LUCRO_EMPRESA, t)) && !search(PRIMEIRA_PESSOA, t)
  if (lucroEmpresa && p.proibidos.includes('chance_dinheiro') &&
    !search(PROIBIDOS.chance_dinheiro, sub(LUCRO_EMPRESA, ' ', t))) {
    tirar(p.proibidos, 'chance_dinheiro')
  }
  // "como a Petrobras pode lucrar com o pré-sal?" pede a explicação, não a projeção
  const explica = Boolean(search(r`\b(como|por que|porque)\b`, t)) && !search(r`\b(vai|vao)\b`, t)
  const lucroFuturo = Boolean(
    search(r`\b(vai|vao|deve|devem|pode|podem)( \w+){0,2} lucr\w*`, t) ||
      (lucroEmpresa && (search(LUCRO_QUE_VEM, t) || (search(PROXIMO_RESULTADO, t) && !(
        search(PEDE_DATA, t) && !search(JUIZO_RESULTADO, t) && p.proibidos.length === 0
      )))),
  ) && !search(PESSOA_QUE_LUCRA, t) && !explica
  // O dividendo que ainda vai sair ("quanto a Petrobras paga de dividendo esse ano?") é previsão de emissor (N2).
  const pagaEmpresa = Boolean(search(EMPRESA_CITADA, t) && search(PAGAR_EMPRESA, t))
  const dividendoFuturo = pagaEmpresa || (
    Boolean(search(DIVIDENDO, t) && search(DIVIDENDO_FUTURO, t)) && !search(DIVIDENDO_PASSADO, t) &&
    !search(DIVIDENDO_REGRA, t) && !(search(DIVIDENDO_MECANICA, t) && !search(DIVIDENDO_QUAL, t))
  )
  // O pedido de análise ou de juízo sobre uma empresa ("analisa a PETR4", "P/L 3 é muito?").
  const avalia = search(AVALIA_EMPRESA, t) || (search(r`\b${EMPRESA}\b`, t) && search(MULTIPLO, t))
  if (((sobrePreco && futuro && !soPassado) || decisao || lucroFuturo || dividendoFuturo || avalia) &&
    !p.proibidos.includes('direcao')) {
    p.proibidos.push('direcao')
  }
  const contrato = tem(p.mercados, 'mini_indice', 'mini_dolar') || Boolean(search(CONTRATO, t))
  const hora = search(HORA, t)
  if (contrato && (hora || search(EM_CURSO, t))) {
    p.proibidos.push('ao_vivo')
  } else if (hora) {
    if (search(ORDEM, t) && !p.proibidos.includes('momento')) p.proibidos.push('momento')
    if (search(MOVIMENTO, t) && !p.proibidos.includes('direcao')) p.proibidos.push('direcao')
  }
  if (p.proibidos.includes('voto') && p.proibidos.includes('comparar')) tirar(p.proibidos, 'comparar')
  // Escolher entre empresas ("PETR4 ou PRIO3, qual é melhor?") é ranking (M2), não comparar classes de ativo (N5).
  // O mesmo entre tokens ("BTC ou ETH?", "bitcoin é mais seguro que ethereum?"): é indicar token (N7), não classe.
  if (p.proibidos.includes('ranking') && p.proibidos.includes('comparar') &&
    (search(r`\b${EMPRESA}\b`, t) || search(r`\b${CRIPTO_NOME}\b.{0,30}\b${CRIPTO_NOME}\b`, t))) {
    tirar(p.proibidos, 'comparar')
  }
  if (p.proibidos.includes('aposta') && !p.mercados.includes('previsao')) p.mercados.push('previsao')
  if (p.proibidos.includes('binaria')) p.mercados = p.mercados.filter((m) => m !== 'previsao')
  // "Quais as chances pro dólar" e "quais as chances de ganhar dinheiro com bitcoin?": é direção do mercado ou a chance da
  // pessoa, não chance de candidato.
  if (p.proibidos.includes('chance_candidato') && p.mercados.length > 0 &&
    !search(CANDIDATO_OU_VITORIA, sub(r`\bganhar (dinheiro|grana)\b`, ' ', t))) {
    tirar(p.proibidos, 'chance_candidato')
  }
  if (p.proibidos.includes('chance_candidato') && p.proibidos.includes('chance_dinheiro') && p.mercados.length === 0 &&
    !search(GANHO_DELA, t)) {
    tirar(p.proibidos, 'chance_dinheiro')
  }
  if (p.proibidos.includes('chance_candidato') && !p.temas.includes('eleicao')) p.temas.push('eleicao')
  // Conta neutra com os números do próprio usuário (P4): pontos e contratos.
  const m = search(r`(?<![\d.,])(\d[\d.,]{0,15})\s*pontos?\b`, t)
  if (m) {
    p.pontos = _numero(m.group(1)!)
    const c = search(r`(?<![\d.,])(\d{1,6})\s*contratos?\b`, t)
    p.contratos = c ? Number(c.group(1)) : 1
    if (temConta(p)) {
      // O número de contratos e de pontos que a pessoa escolheu não é pedido de alocação; "quanto eu coloco" é.
      if (p.proibidos.includes('capital') && !search(ALOCACAO, t)) tirar(p.proibidos, 'capital')
      if (p.proibidos.includes('direcao') && !search(r`\b(sobe|cai|vai|chance|probabilidad\w*|tendencia)\b`, t)) {
        tirar(p.proibidos, 'direcao')
      }
      if (p.proibidos.includes('dica') && !search(r`\b(compr\w*|vend\w*|devo|vale|compens\w*|entrar|bora)\b`, t)) {
        tirar(p.proibidos, 'dica')
      }
    }
  }
  // Quando mover o dinheiro de lugar ("troco hoje?", "trago depois do 2º turno?"): momento (N4) e a recusa padrão.
  const momentoTroca = Boolean(search(MOMENTO_TROCA, t))
  if (momentoTroca) {
    for (const codigo of ['momento', 'dica']) if (!p.proibidos.includes(codigo)) p.proibidos.push(codigo)
    tirar(p.proibidos, 'comparar') // "antes ou depois de domingo" não compara classes de ativos
  }
  const quanto = Boolean(search(QUANTO_TROCAR, t))
  if (quanto && !p.proibidos.includes('capital')) p.proibidos.push('capital')
  // Conta neutra de câmbio com o dinheiro que a pessoa contou (P4): o valor em reais, quanto muda a cada R$ 0,10 e
  // quantos meses de gasto cobre. Não entra quando ela pergunta quanto mover (alocação, N5) nem quando mover (N4): ao
  // lado da reação nos turnos, o valor dela viraria indicação de momento. Pergunta de contrato (mini-dólar) também não.
  let tDinheiro = sub(ALVO_NUM, ' ', t) // o alvo ("o ouro vai a 3000 dólares?") não é o dinheiro dela
  if (p.mercados.includes('cripto')) tDinheiro = sub(PRECO_DA_CRIPTO, ' ', tDinheiro)
  const lido = cambio(tDinheiro)
  let [valor, moeda] = lido
  const [, , gasto, gastoMoeda] = lido
  let semPreco = t
  if (p.mercados.includes('petroleo')) {
    // o 1º dinheiro dela que não é o preço do barril nem do litro ("o petróleo passou de 100 dólares?" não tem)
    semPreco = _so_o_dinheiro_dela(sub(PRECO_DO_BARRIL, ' ', tDinheiro))
    ;[valor, moeda] = cambio(semPreco)
  }
  // O dólar que só aparece no preço do barril ("o Brent a 100 dólares mexe nos meus 20 mil euros?") não é câmbio.
  if (p.mercados.includes('petroleo') && p.mercados.includes('dolar') && !search(MERCADOS.dolar, semPreco)) {
    tirar(p.mercados, 'dolar')
  }
  const contratoFuturo = tem(p.mercados, 'mini_indice', 'mini_dolar') || Boolean(search(CONTRATO, t))
  const cripto = tem(p.mercados, 'cripto', 'memecoin') // "10 mil dólares em USDT" é cripto da pessoa, não câmbio
  // "10 mil euros em bitcoin": o euro é a unidade do valor, não o mercado da pergunta (como o dólar, em resposta.py). Fica
  // quando a pessoa fala em mover o dinheiro ("uso uma exchange pra trazer?", "trago agora ou compro bitcoin?"); trocar
  // euro por bitcoin não é câmbio.
  const semTrocaCripto = sub(
    r`\b(troco|trocar|converto|converter)\b[^.?!]{0,30}\b(por|em|pra|para) (bitcoins?|btc|cripto\w*` +
      r`|ether(eum)?|eth|solana)\b`,
    ' ',
    sub(r`\bexchanges?\b`, ' ', t),
  )
  const trocaDita = search(r`\b` + TROCA + r`\b`, semTrocaCripto) || search(CONVERSAO, t)
  if (p.mercados.includes('cripto') && p.mercados.includes('euro') && !search(MOMENTO_TROCA, semTrocaCripto) && !trocaDita &&
    !search(MERCADOS.euro, sub(_DINHEIRO, ' ', t))) {
    tirar(p.mercados, 'euro')
  }
  // Pôr o dinheiro estrangeiro num mercado que não é câmbio ("invisto em petróleo?", "compro ações da Petrobras?") é
  // classe de ativo (N5): o valor não entra. "O petróleo mexe com isso?" e "trago o dinheiro?" seguem com a conta.
  // Comparar ou ranquear com o dinheiro dela ("20 mil dólares, petróleo ou bolsa?") é N5 nas letras; o pedido sobre a
  // empresa ("petr4 tá barata?", "petr4 vale a pena?") também, a não ser que a pergunta seja do câmbio ("a Petrobras
  // vai mexer no dólar?", "devo trazer?"): aí a conta fica junto da recusa.
  const semODinheiro = sub(_DINHEIRO, ' ', t)
  const doCambio = Boolean(search(MERCADOS.dolar + '|' + MERCADOS.euro + r`|\b${TROCA}\b`, semODinheiro))
  const investe = p.mercados.some((x) => x !== 'dolar' && x !== 'euro') && Boolean(
    search(INVESTE, t) || tem(p.proibidos, 'comparar', 'ranking') ||
      (search(r`\b${EMPRESA}\b`, t) && tem(p.proibidos, 'dica', 'direcao') && !doCambio),
  )
  if (valor !== null && moeda !== null && !contratoFuturo) {
    if (quanto || momentoTroca || cripto || investe) {
      // a pessoa contou o valor e ele não é usado: a linha do capital diz por quê
      if (!p.proibidos.includes('capital')) p.proibidos.push('capital')
    } else {
      p.valor_moeda = valor
      p.moeda = moeda
      p.gasto_mensal = gasto
      p.gasto_moeda = gastoMoeda
      if (!p.mercados.includes(moeda)) p.mercados.push(moeda)
      tirar(p.proibidos, 'capital')
    }
  }
  return p
}

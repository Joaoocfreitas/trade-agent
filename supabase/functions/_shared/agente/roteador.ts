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
// Os padrões rodam sobre o texto de normalizar(), que já é ASCII: aí \w, \b e \d do JavaScript valem o mesmo que os do
// Python. Duas diferenças sobram e estão tratadas: o "." do Python só não casa \n (o do JavaScript também recusa \r),
// por isso os padrões usam [^\n]; e o \s do Python inclui \x1c-\x1f, por isso ESPACO.
import { type Pedido, simples } from './texto.ts'

const r = String.raw
/** Junta os pedaços do padrão, como as strings coladas do Python. Sem flag g: test() não guarda estado. */
const rx = (...partes: string[]): RegExp => new RegExp(partes.join(''))

// O que é espaço para o \s e o split() do Python num texto ASCII.
const ESPACO = r`[\t\n\v\f\r\x1c-\x1f ]`
const PALAVRAS = new RegExp(`${ESPACO}+`)

// A ordem importa: o "⬆️" (com o seletor de variação U+FE0F) sai antes do "⬆" sozinho.
const EMOJI: ReadonlyArray<readonly [string, string]> = [
  ['📈', ' sobe '], ['📉', ' cai '], ['🚀', ' dispara '], ['🔥', ' dispara '], ['💰', ' lucro '], ['🤑', ' lucro '],
  ['⬆️', ' sobe '], ['⬇️', ' cai '], ['⬆', ' sobe '], ['⬇', ' cai '],
]
// Abreviações e erros de digitação comuns do público (internetês). Map, e não objeto: "constructor" não é abreviação.
const ABREVIACOES: ReadonlyMap<string, string> = new Map([
  ['q', 'que'], ['vc', 'voce'], ['vcs', 'voces'], ['qnd', 'quando'], ['qdo', 'quando'], ['hr', 'hora'], ['eh', 'e'],
  ['tb', 'tambem'], ['tbm', 'tambem'], ['mto', 'muito'], ['c', 'com'], ['n', 'nao'], ['pq', 'porque'],
  ['subi', 'subir'], ['chace', 'chance'], ['chanse', 'chance'], ['ibov', 'ibovespa'], ['msm', 'mesmo'],
])

/** Emoji vira palavra, sai o acento, e a abreviação vira a palavra inteira. */
export function normalizar(pergunta: string): string {
  for (const [e, palavra] of EMOJI) pergunta = pergunta.replaceAll(e, palavra)
  const t = simples(pergunta)
  return t.replace(/\b\w+\b/g, (m) => ABREVIACOES.get(m) ?? m)
}

export const MERCADOS = {
  mini_indice: rx(r`\bmini[- ]?indices?\b|\bwin\b|\bwin[fghjkmnquvxz]\d\d\b|\bindice futuro\b`),
  mini_dolar: rx(r`\bmini[- ]?dolar\b|\bwdo\b`),
  ibovespa: rx(r`\bibov\w*|\bbolsa\b|\bacoes\b|\bacao\b|\bbova11\b|\bb3\b|\bbovespa\b|\bstocks?\b|\bindice\b`),
  dolar: rx(
    r`\bdolar\b|\bdollar\b|\bcambio\b|\b(brazilian )?real (sobe|cai|valoriza|desvaloriza|go up|go down)\b`,
    r`|\bbrazilian real\b`,
  ),
  juros: rx(r`\bjuros\b|\bdi1?\b|\bdi futuro\b|\bselic\b|\brenda fixa\b|\btesouro\b|\bprefixad\w*`),
  cripto: rx(r`\bcripto\w*|\bbitcoin\b|\bbtc\b|\bethereum\b|\bexchanges?\b|\bstablecoins?\b|\bsolana\b`),
  memecoin: rx(r`\bmeme ?coins?\b|\bmemecoins?\b|\$trump\b|\$libra\b|\$melania\b|\btokens?\b|\bmoeda do candidato\b`),
  previsao: rx(r`\bpolymarket\b|\bkalshi\b|\bmercados? de previs\w*`),
} satisfies Record<string, RegExp>

export const CANDIDATOS = { flavio: rx(r`\bflavio\b|\bbolsonaro\b`), lula: rx(r`\blula\b`) } satisfies Record<string, RegExp>

export const TEMAS = {
  eleicao: rx(
    r`\belei(cao|coes|toral|torais)\b|\bturnos?\b|\bcandidat\w*|\burnas?\b|\bpresidente\b|\bganhar a elei`,
    r`|\bvencer a elei|\bse (ele|ela) (ganhar|vencer|perder)\b|\bpesquisas?\b|\bdatafolha\b|\bquaest\b|\batlas\w*`,
    r`|\binstitutos?\b|\bdireita\b|\besquerda\b|\bvitoria d\w\b|\breeleit\w*|\bdomingo\b|\brunoff\b|\belection\b`,
    r`|\bmito\b|\bpt\b|\bpl\b|\bganhando\b|\bvencendo\b|\beleito\b`,
  ),
  copom: rx(
    r`\bcopom\b|\bselic\b|\bdecisao de juros\b|\bbanco central (corta|sobe|mantem|decide)\b|\bcortar(em)? (os )?juros\b`,
  ),
  fiscal: rx(r`\bfiscal\b|\barcabouco\b|\bgastos? publicos?\b|\borcamento\b|\bministro da fazenda\b|\bhaddad\b`),
  legislativo: rx(r`\bcongresso\b|\bcamara\b|\bsenado\b|\bvotacao\b|\bpec\b|\breforma\b|\bimpeachment\b`),
  judicial: rx(r`\bstf\b|\bsupremo\b|\bjulgamento\b|\bprisao\b|\bcondenacao\b`),
  geopolitico: rx(r`\btarifas?\b|\bguerra\b|\bsancao\b|\bsancoes\b|\bira\b|\bpetroleo\b`),
  choque_externo: rx(r`\bpandemia\b|\bcovid\b|\bcrise (global|externa|internacional)\b`),
  escandalo: rx(r`\bescandalos?\b|\bdelacao\b|\blava ?jato\b|\bgrampo\b`),
  economia: rx(r`\beconomia\b|\binflacao\b|\bipca\b|\bdivida\b|\bpib\b|\bfiscal\b`),
  conceito: rx(r`\bo que (e|sao|significa)\b|\bcomo funciona\b|\bme explica\b|\bexplica\b`),
} satisfies Record<string, RegExp>

export const PROIBIDOS = {
  // "O que eu faço?", "que que eu faço?", "o que fazer agora?", "preciso tomar uma decisão", "e agora?" pedem ação.
  // "O que fazer para entender o Copom?" não: é pedido de explicação.
  dica: rx(
    r`\bcompr(a|o|ar|aria|ariam)\b|\bvend(e|o|er|eria)\b|\bentro\b|\bentrar\b|\bsair\b|\bcompens\w*|\bbora\b`,
    r`|\bdevo\b|\bdeveria\b|\bvale (a pena|mais|comprar)\b|\bfaz sentido\b`,
    r`|\b(o que|que que|oq)( e que)?( eu)? (faco|fazer|faria)\b`,
    r`(?! (pra|para) (entender|saber|aprender|estudar|acompanhar|conhecer|ler|interpretar|compreender)\b)`,
    r`|\b(preciso|tenho que|tenho de|tenho|vou ter que) (de )?(tomar )?(uma )?(decisao|decidir)\b`,
    r`|\bme ajud(a|e|ar) a (tomar (uma )?decisao|decidir|escolher)\b|\bdecid(e|a|ir) (por|pra|para) mim\b`,
    // O $ do Python também casa antes de um \n final; o \W* guloso come esse \n, então aqui dá o mesmo.
    r`|\be agora(\?|\W*$)`,
    r`|\bse fosse (voce|eu)\b|\bo que (voce )?faria\b|\brecomenda\w*|\bconselho\w*|\bsugest\w*|\bdica\w*`,
    r`|\bfico (comprado|vendido|de fora)\b|\bcomo (eu )?(abordo|opero|ganho)\b|\bestrategia\b|\bposicion\w*`,
    r`|\bexposicao\b|\baplicar\b|\binvestir\b|\bbuy\b|\bsell\b|\bshould i\b|\bwould you\b`,
  ),
  direcao: rx(
    r`\bvai (subir|cair|disparar|despencar|bombar|valorizar|explodir|fechar|abrir)\b|\bvao (subir|cair)\b|\bchances?\b`,
    r`|\bprobabilidad\w*|\bde 0 a 100\b|\bum numero\b|\btendencia\b|\bpode (subir|cair|disparar)\b`,
    r`|\bsobe ou (cai|desce|nao)\b|\balavanc(ar|a)\b|\bpotencial\b|\bprevisao\b|\bprever\b|\bdisparar\b`,
  ),
  momento: rx(
    r`\bstop\b|\balvo\b|\bponto de (entrada|saida)\b|\bquando (entrar|sair|comprar|vender)\b`,
    r`|\b(hora|quando)\b[^\n]{0,15}\b(entrar|sair|comprar|vender|operar)\b|\balertas?\b|\bme avis(a|e)\b|\bsinal de\b`,
    r`|\bamanha\b|\bna abertura\b|\bsegunda(-feira)?\b[^\n]{0,30}\b(fazer|compr\w*|vend\w*|entr\w*)`,
  ),
  capital: rx(
    r`\br\$ ?\d|\b\d+ ?mil reais\b|\b\d+ ?k\b|\b(um|dois|tres|quatro|cinco|seis|sete|oito|nove|dez|vinte|trinta|`,
    r`cinquenta|cem) mil( reais)?\b|\btenho (r\$ ?)?\d+[\d.,]* ?(mil|k|reais|conto|contos|pila|paus)\b`,
    r`|\bquantos contratos\b|\bquanto (eu )?(coloco|ponho|invisto|aplico|boto|devia ter|deveria ter)\b`,
    r`|\bquanto investir\b|\bmeu (capital|dinheiro|patrimonio|salario)\b|\bminha (renda|carteira|reserva)\b`,
    r`|\bganho \d+|\bpor mes\b|\bsalario\b`,
  ),
  perfil: rx(
    r`\barrojad\w*|\bconservador\w*|\bmoderad[oa]\b|\btolerancia (a|ao) risco\b|\bperfil\b|\baposentadoria\b`,
    r`|\breserva de emergencia\b|\bserve (pra|para) mim\b|\be (pra|para) mim\b|\bminha idade\b|\btenho \d+ anos\b`,
    r`|\bmeu objetivo\b|\bmeu prazo\b`,
  ),
  comparar: rx(
    r`\bmelhor\b[^\n]{0,40}\bou\b|\bvale mais\b|\b(dolar|bolsa|cripto|bitcoin|renda fixa|tesouro|acoes|ouro|poupanca|cdb)\b`,
    r`[^\n]{0,25}\bou\b[^\n]{0,25}\b(dolar|bolsa|cripto|bitcoin|renda fixa|tesouro|acoes|ouro|poupanca|cdb)\b`,
  ),
  ranking: rx(
    r`\branking\b|\bmelhores (acoes|ativos|moedas|criptos)\b|\btop ?\d+\b|\bmonta (uma )?carteira\b`,
    r`|\bcarteira (recomendada|sugerida|ideal)\b|\bquais (acoes|ativos)\b|\bqual (acao|ativo|papel|moeda|cripto)\b`,
    r`|\bque acao\b|\bsobe mais\b|\bmais se benefici\w*|\bmelhor (acao|ativo|cripto|moeda)\b`,
  ),
  seletivo: rx(
    r`\bso (os|as) (casos|vezes|anos|eleicoes|reunioes|dias|turnos)\b|\bso (as )?altas\b|\bso os positivos\b`,
    r`|\bmostra so\b|\bmostra apenas\b|\bapenas (os|as) (casos|turnos|vezes)\b|\b(so|apenas) (a|as) (mediana|media|altas|quedas)\b`,
  ),
  plataforma: rx(
    r`\bqual (a )?(melhor )?(exchange|corretora|plataforma|app)\b|\bonde (eu )?(compro|opero|abro conta)\b`,
    r`|\bque (exchange|corretora)\b`,
  ),
  aposta: rx(r`\bapost\w*|\baposto\b|\bbets?\b|\bpolymarket\b|\bkalshi\b|\bvpn\b`),
  voto: rx(
    r`\bem quem\b|\bquem e (o )?melhor\b|\bmelhor candidato\b|\bdevo votar\b|\bquem (voce|vc) (apoia|prefere)\b`,
    r`|\bmelhor (pra|para) (a |o )?(economia|bolsa|mercado|pais|brasil|investidor)\b|\bmercado prefere\b`,
    r`|\b(pior|ruim|bom|boa) (pra|para) (a |o )?(bolsa|economia|mercado)\b|\bquem o mercado (quer|prefere)\b`,
    r`|\bquebra o pais\b|\bvoce (vota|votaria|apoia|prefere)\b`,
  ),
  // Trocar de papel ou tirar o aviso. "Só entre nós" não é troca de papel: a pergunta que vem depois é que pede recusa.
  papel: rx(
    r`\bfinj\w*|\bfinge\b|\bfaz de conta\b|\bimagin(e|a) que (voce|vc)\b|\b(voce|vc) e (um )?(analista|consultor|trader)\b`,
    r`|\bcomo (um )?analista\b|\bignor(e|a|ar) (as |os |o )?(regras|instrucoes|avisos?)\b|\bsem (o |os )?avisos?\b`,
    r`|\besquec\w* (as |os |o |das |dos |do )?(regras|instrucoes|avisos?)\b|\btir(a|e|ar) (o |os |esse |esses )?avisos?\b`,
    r`|\bcomo se (voce )?fosse (um|uma|meu|minha) (amig[oa]|analista|consultor\w*|trader|assessor\w*|gerente|especialista)\b`,
    r`|\bcomo (um|uma|meu|minha) amig[oa]\b`,
    r`|\bsem rodeio\w*|\bmodo (desenvolvedor|dev|livre|dan|sem filtro)\b|\bjailbreak\b|\bvoce (agora )?e (o|a) [a-z]+`,
    r`|\bsem filtros?\b|\bpode pular\b|\bassumo (toda |total |a )?responsabilidade\b|\bpara um (livro|roteiro|trabalho|filme|conto)\b`,
    r`|\bhipotetic\w*|\bhypothetical\b|\bimagina um cenario\b|\bnum cenario\b|\bnum mundo\b|\bpersonagem\b|\bpretend\b`,
    r`|\bja li (todos )?os avisos\b|\b(ja )?sei (os|dos) riscos\b|\bpela ultima vez\b|\bja perguntei\b`,
  ),
  binaria: rx(r`\biq ?option\b|\bopc(ao|oes) binarias?\b|\bbinarias\b`),
  chance_candidato: rx(
    r`\bquem (vai )?(ganha|ganhar|vence|vencer)\b|\bchances? (de|do|da) (ele|ela|o candidato|flavio|lula|bolsonaro) (ganhar|vencer|levar)\b`,
    r`|\bfavorit\w*|\bchances? de vitoria\b|\bquais (as|sao as) chances\b|\breeleit\w*|\beurasia\b`,
    r`|\b(vence|vencer|ganha|ganhar|leva|levar)\b[^\n]{0,20}\b(domingo|eleicao|segundo turno|2o turno)\b`,
    r`|\bprobabilidade d[oea] (lula|flavio|bolsonaro|ele|ela)\b|\bquem (ta|esta) na frente\b`,
    r`|\b(lula|flavio|bolsonaro) (vence|ganha|leva)\b`,
  ),
  chance_dinheiro: rx(
    r`\bchances? de (eu )?(ganhar|lucrar)\b|\bganhar dinheiro\b|\bvou lucrar\b|\bda (pra|para) lucrar\b`,
    r`|\bquanto (eu )?ganho\b|\bquais (as|sao as) chances\b|\bganhar ou (nao|perder)\b|\bganha(r)? (uma )?grana\b`,
    r`|\blucr\w*|\brenda (mensal|extra)\b|\bficar rico\b`,
  ),
} satisfies Record<string, RegExp>

// Pergunta sobre o futuro de um preço: direção, magnitude, nível ou "o que acontece se". Leva a recusa (N2).
const FUTURO = rx(
  r`\b(sobe|sobem|subir|suba|subira|subiria|desce|descer|cai|caem|cair|caia|caira|cairia|despenc\w*|dispar\w*|derret\w*`,
  r`|valoriz\w*|desvaloriz\w*|aprecia\w*|recua\w*|fecha|fechar|abre|abrir|pra cima|para cima|pra baixo|para baixo|topo`,
  r`|fundo|barat[oa]|caro|vies|palpite|visao|acha|acham|opiniao|tendencia|provavel|esperado|retorno|potencial`,
  r`|vai bem|vai mal|reage bem|reage mal|vai a \d|chega a \d|pra onde|para onde|go up|go down|rise|fall|rally`,
  r`|bajar|probabilidad\w*|chances?)\b`,
)
const CONDICIONAL = rx(
  r`\bse (o |a )?(\w+ ){0,2}(ganhar|vencer|perder|for eleito|for reeleito|cortar|cortarem|subir|aumentar|baixar|`,
  r`reduzir|mantiver|wins?)\b|\b(ganhando|vencendo|perdendo)\b|\bcom (o |a )?\w+ eleit[oa]\b|\bif \w+ wins?\b`,
)
// Pergunta sobre o que já aconteceu: não pede direção.
const PASSADO = rx(r`\b(reagiu|reagiram|aconteceu|aconteceram|foi|foram|historico|historicamente|antes|passad[ao]s?|ja houve)\b`)
const FUTURO_EXPLICITO = rx(r`\b(vai|vao|agora|amanha|semana que vem|depois d[oa]|proxim\w*|pra onde|para onde)\b`)
// Decisão de juros que ainda vai sair: "vai cortar os juros?", "o BC vai reduzir a Selic?", "vai ter corte?", "o Copom
// cortará?", "corta na próxima reunião?". É futuro pela forma do verbo: não passa pelo filtro do PASSADO.
const DECISAO = rx(
  r`\b(vai|vao|ira|irao|deve|devem|pode|podem)( \w+){0,2} (cortar|baixar|reduzir|manter|segurar|elevar|aumentar`,
  r`|subir|mexer|parar|pausar|interromper)\b`,
  r`|\b(cort|baix|segur|elev|aument)a(ra|rao|ria|riam)\b|\breduzi(ra|rao|ria|riam)\b|\bmante(ra|rao|ria|riam)\b`,
  r`|\b(vai ter|vai haver|vao ter|tera|havera|teremos)( \w+){0,2} (corte|cortes|alta|altas|aumento|reducao|elevacao`,
  r`|manutencao|pausa|queda)\b`,
  r`|\b(corta|cortam|mantem|segura|eleva|aumenta|baixa|reduz|sobe)\b[^\n]{0,30}\b(proxim\w*|amanha|semana que vem)\b`,
)
// "Corta ou mantém?", "corte ou manutenção?": pode ser a decisão de amanhã ou a de ontem, então passa pelo filtro do PASSADO.
const DECISAO_OU = rx(
  r`\b(corta|cortam|mantem|segura|eleva|aumenta|baixa|reduz|sobe)\b[^\n]{0,20}\bou (corta|cortam|mantem|segura`,
  r`|eleva|aumenta|baixa|reduz|sobe|para|nao)\b`,
  r`|\b(corte|manutencao)\b[^\n]{0,15}\bou (corte|manutencao|alta|elevacao|aumento|reducao|pausa)\b`,
  r`|\b(alta|elevacao|aumento|reducao|pausa)\b[^\n]{0,15}\bou (corte|manutencao)\b`,
)
// A decisão é de juros (ou de preço) quando a pergunta cita um mercado, o Copom, o BC, a taxa ou o corte, ou é curta.
const SOBRE_JUROS = rx(r`\b(copom|bc|banco central|taxas?|cortes?|reuniao|reunioes)\b`)

// Comentário de pregão (N6): só quando a pergunta cita um contrato (WIN, WDO, DI, mini) e o pregão ("agora", "neste
// momento") ou o movimento em curso ("está caindo"). Os mercados mini_indice e mini_dolar também contam como contrato.
const CONTRATO = rx(r`\bwdo[fghjkmnquvxz]\d\d\b|\bdi1?\b|\bdi1[fghjkmnquvxz]\d\d\b|\bdi futuro\b|\bdolar futuro\b`)
const HORA = rx(r`\bagora\b|\bneste momento\b|\bhoje no pregao\b|\bao vivo\b`)
const EM_CURSO = rx(r`\b(esta|estao|ta|tao|segue|seguem|continua|continuam)( \w+)? (despencando|disparando|caindo|subindo|derretendo)\b`)
// Sem contrato, "agora" com ordem é pedido de momento ("compro agora?") e com movimento é de direção ("a bolsa está
// caindo agora"): a recusa continua, com a linha certa, e sem falar de contrato.
const ORDEM = rx(r`\b(entro|compro|vendo|opero|zero)\b`)
const MOVIMENTO = rx(r`\b(despencando|disparando|caindo|subindo|derretendo)\b`)
const VOTO_INFORMADO = rx(
  r`\b(eu )?vot(o|ei|arei|aria|ando) (\d+|no|na|em)\b|\bsou (\w+ )?(petista|bolsonarista|lulista|de direita|`,
  r`de esquerda|progressista)\b|\bodeio (o |a )?(pt|pl|lula|flavio|bolsonaro|esquerda|direita)\b|\b(o )?mito\b`,
  r`|\bfiz o l\b|\beu apoio\b|\btorco (pelo|pela|pro|para o)\b`,
)
// Pedido de alocação, que a conta neutra (P4) nunca apaga.
const ALOCACAO = rx(
  r`\bquanto (eu )?(coloco|ponho|invisto|aplico|boto|devia ter|deveria ter)\b|\bquantos contratos\b|\bquanto investir\b`,
  r`|\br\$ ?\d|\b\d+ ?mil\b|\b\d+ ?k\b|\btenho \d`,
)
const CANDIDATO_OU_VITORIA = rx(r`\b(flavio|bolsonaro|lula|vence|vencer|ganha|ganhar|reeleit\w*|favorit\w*|eurasia|frente)\b`)
const DERIVATIVO = rx(r`\bmargem\b|\bajuste diario\b|\balavancagem\b`)
const PONTOS = rx(r`(?<![\d.,])(\d[\d.,]{0,15})`, ESPACO, r`*pontos?\b`)
const CONTRATOS = rx(r`(?<![\d.,])(\d{1,6})`, ESPACO, r`*contratos?\b`)
const DIRECAO_NA_CONTA = rx(r`\b(sobe|cai|vai|chance|probabilidad\w*|tendencia)\b`)
const DICA_NA_CONTA = rx(r`\b(compr\w*|vend\w*|devo|vale|compens\w*|entrar|bora)\b`)

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

/** Junta duas leituras da mesma pergunta (a das palavras e a da IA): o que uma achou, vale. */
export function somar(a: Pedido, b: Pedido): Pedido {
  const junta = (x: string[], y: string[]): string[] => [...x, ...y.filter((v) => !x.includes(v))]
  return {
    pergunta: a.pergunta,
    mercados: junta(a.mercados, b.mercados),
    candidatos: junta(a.candidatos, b.candidatos),
    temas: junta(a.temas, b.temas),
    proibidos: junta(a.proibidos, b.proibidos),
    voto_informado: a.voto_informado || b.voto_informado,
    pontos: a.pontos !== null ? a.pontos : b.pontos,
    contratos: a.contratos,
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
function numero(s: string): number {
  const limpo = s.replaceAll('.', '').replaceAll(',', '.')
  const n = Number(limpo)
  if (Number.isNaN(n)) throw new Error(`could not convert string to float: '${limpo}'`)
  return n
}

function tirar(xs: string[], x: string): void {
  const i = xs.indexOf(x)
  if (i >= 0) xs.splice(i, 1)
}

export function analisar(pergunta: string): Pedido {
  const t = normalizar(pergunta)
  const achou = (padroes: Record<string, RegExp>): string[] =>
    Object.entries(padroes).filter(([, padrao]) => padrao.test(t)).map(([k]) => k)
  const p: Pedido = {
    pergunta, mercados: achou(MERCADOS), candidatos: achou(CANDIDATOS), temas: achou(TEMAS), proibidos: achou(PROIBIDOS),
    voto_informado: VOTO_INFORMADO.test(t), pontos: null, contratos: 1,
  }
  if (p.voto_informado && !p.temas.includes('eleicao')) p.temas.push('eleicao')
  // Conceito de derivativo (margem, ajuste diário, alavancagem): a explicação está no bloco do mini-índice.
  if (DERIVATIVO.test(t) && p.mercados.length === 0) p.mercados.push('mini_indice')
  // Futuro de um preço: na dúvida, recusa. Vale com mercado, candidato, eleição, Copom ou pergunta curta ("sobe?").
  const curta = t.split(PALAVRAS).filter((w) => w !== '').length <= 4
  const sobrePreco = p.mercados.length > 0 || p.candidatos.length > 0 ||
    p.temas.some((x) => x === 'eleicao' || x === 'copom') || curta
  const condicional = CONDICIONAL.test(t)
  const futuro = FUTURO.test(t) || condicional
  const soPassado = PASSADO.test(t) && !condicional && !FUTURO_EXPLICITO.test(t)
  // Decisão de juros que ainda vai sair ("vai cortar a Selic?", "corta ou mantém?") também é futuro de preço.
  const decisao = (p.mercados.length > 0 || SOBRE_JUROS.test(t) || curta) &&
    (DECISAO.test(t) || (DECISAO_OU.test(t) && !soPassado))
  if (((sobrePreco && futuro && !soPassado) || decisao) && !p.proibidos.includes('direcao')) p.proibidos.push('direcao')
  const contrato = p.mercados.some((x) => x === 'mini_indice' || x === 'mini_dolar') || CONTRATO.test(t)
  const hora = HORA.test(t)
  if (contrato && (hora || EM_CURSO.test(t))) {
    p.proibidos.push('ao_vivo')
  } else if (hora) {
    if (ORDEM.test(t) && !p.proibidos.includes('momento')) p.proibidos.push('momento')
    if (MOVIMENTO.test(t) && !p.proibidos.includes('direcao')) p.proibidos.push('direcao')
  }
  if (p.proibidos.includes('voto') && p.proibidos.includes('comparar')) tirar(p.proibidos, 'comparar')
  if (p.proibidos.includes('aposta') && !p.mercados.includes('previsao')) p.mercados.push('previsao')
  if (p.proibidos.includes('binaria')) p.mercados = p.mercados.filter((m) => m !== 'previsao')
  // "Quais as chances pro dólar": é direção do mercado, não chance de candidato.
  if (p.proibidos.includes('chance_candidato') && p.mercados.length > 0 && !CANDIDATO_OU_VITORIA.test(t)) {
    tirar(p.proibidos, 'chance_candidato')
  }
  if (p.proibidos.includes('chance_candidato') && !p.temas.includes('eleicao')) p.temas.push('eleicao')
  // Conta neutra com os números do próprio usuário (P4): pontos e contratos.
  const m = PONTOS.exec(t)
  if (m) {
    p.pontos = numero(m[1])
    const c = CONTRATOS.exec(t)
    p.contratos = c ? Number(c[1]) : 1
    if (temConta(p)) {
      // O número de contratos e de pontos que a pessoa escolheu não é pedido de alocação; "quanto eu coloco" é.
      if (p.proibidos.includes('capital') && !ALOCACAO.test(t)) tirar(p.proibidos, 'capital')
      if (p.proibidos.includes('direcao') && !DIRECAO_NA_CONTA.test(t)) tirar(p.proibidos, 'direcao')
      if (p.proibidos.includes('dica') && !DICA_NA_CONTA.test(t)) tirar(p.proibidos, 'dica')
    }
  }
  return p
}

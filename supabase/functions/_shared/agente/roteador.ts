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

// Símbolo de moeda que o simples() apagaria: vira palavra antes ("€150.000" → "euros 150.000").
const SIMBOLOS: ReadonlyArray<readonly [string, string]> = [['€', ' euros ']]
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

/** Emoji e símbolo de moeda viram palavra, sai o acento, e a abreviação vira a palavra inteira. */
export function normalizar(pergunta: string): string {
  for (const [e, palavra] of SIMBOLOS) pergunta = pergunta.replaceAll(e, palavra)
  for (const [e, palavra] of EMOJI) pergunta = pergunta.replaceAll(e, palavra)
  const t = simples(pergunta)
  return t.replace(/\b\w+\b/g, (m) => ABREVIACOES.get(m) ?? m)
}

export const MERCADOS = {
  mini_indice: rx(r`\bmini[- ]?indices?\b|\bwin\b|\bwin[fghjkmnquvxz]\d\d\b|\bindice futuro\b`),
  mini_dolar: rx(r`\bmini[- ]?dolar\b|\bwdo\b`),
  ibovespa: rx(r`\bibov\w*|\bbolsa\b|\bacoes\b|\bacao\b|\bbova11\b|\bb3\b|\bbovespa\b|\bstocks?\b|\bindice\b`),
  dolar: rx(
    r`\bdolar(es)?\b|\bdollars?\b|\bus\$|\bcambio\b|\b(brazilian )?real (sobe|cai|valoriza|desvaloriza|go up|go down)\b`,
    r`|\bbrazilian real\b`,
    // o real contra as outras moedas, e mandar ou trazer dinheiro de fora: é câmbio
    r`|\breal\b[^.?!]{0,30}\b(valoriz\w*|desvaloriz\w*|fortalec\w*|enfraquec\w*)|\b(valorizacao|desvalorizacao) do real\b`,
    // o verbo logo depois de "real": "o real problema está..." não é câmbio
    r`|\b(o|do|no|pro|pelo|com o) real (reag\w*|esta|ta|caiu|cai|subiu|sobe|fic\w*|contra|frente|diante|depois|antes`,
    r`|vai|vem)\b|\breal brasileiro\b`,
    r`|\bmoeda (brasileira|estrangeira)\b|\bremessas?\b|\btransferencias? internaciona\w*|\bconvert\w* (para|pra|em) reais\b`,
    r`|\b(trazer|traz|trago|mandar|mando|enviar|envio|levar|transferir)\b[^.?!]{0,30}\b(pro brasil|para o brasil|pra fora`,
    r`|para fora|do exterior|de fora|para o exterior|pro exterior)\b`,
  ),
  // Logo depois do dólar: a ordem das chaves é a ordem de p.mercados, como no dict do Python.
  euro: rx(r`\beuros?\b|\beur\b`),
  juros: rx(r`\bjuros\b|\bdi1?\b|\bdi futuro\b|\bselic\b|\brenda fixa\b|\btesouro\b|\bprefixad\w*`),
  cripto: rx(
    r`\bcripto\w*|\bbitcoin\b|\bbtc\b|\bethereum\b|\bexchanges?\b|\bstablecoins?\b|\bsolana\b`,
    r`|\bhalving\b|\bftx\b|\busdt\b|\busdc\b|\btether\b`,
  ),
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
    // mover o dinheiro, na 1ª pessoa ("trago o dinheiro?", "troco?"), menos "como mando dinheiro pra fora?" (P5)
    r`|(?<!como )(?<!como eu )\b(troco|trago|mando|envio|converto|transfiro|remeto)\b|\bdeixo (la|aqui|parado|onde esta)\b`,
    // como no "e agora", o \W* guloso come o \n final que o $ do Python aceitaria
    r`|(?<=.{10})\be ai(\?|\W*$)|\bconviene\b|\b(debo|deberia) (cambiar|traer|mandar|enviar)\b`,
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
export const CONTRATO = rx(r`\bwdo[fghjkmnquvxz]\d\d\b|\bdi1?\b|\bdi1[fghjkmnquvxz]\d\d\b|\bdi futuro\b|\bdolar futuro\b`)
const HORA = rx(r`\bagora\b|\bneste momento\b|\bhoje no pregao\b|\bao vivo\b`)
const EM_CURSO = rx(r`\b(esta|estao|ta|tao|segue|seguem|continua|continuam)( \w+)? (despencando|disparando|caindo|subindo|derretendo)\b`)
// Sem contrato, "agora" com ordem é pedido de momento ("compro agora?") e com movimento é de direção ("a bolsa está
// caindo agora"): a recusa continua, com a linha certa, e sem falar de contrato.
const ORDEM = rx(r`\b(entro|compro|vendo|opero|zero|troco|trago|mando|envio|converto|transfiro)\b`)
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

// P4 de câmbio: o dinheiro em moeda estrangeira que a pessoa contou e o gasto por mês, só para a conta (nunca para dizer
// o que fazer). "150 mil euros", "€150.000", "150k euros", "US$ 20 mil", "20 mil dólares"; "gasto 5 mil reais por mês".
const MOEDA: ReadonlyArray<readonly [string, string]> = [['euro', r`euros?|eur`], ['dolar', r`dolares|dolar|dollars?|usd|us\$|u\$`]]
const ROTULOS = MOEDA.map(([, padrao]) => padrao).join('|')
const MOEDA_INTEIRA = MOEDA.map(([k, padrao]) => [k, new RegExp(`^(?:${padrao})$`)] as const) // re.fullmatch do Python
// Antes do número, só o símbolo ou o código ("€" vira "euros" no normalizar): "o euro 2 dias depois" não é dinheiro.
const MOEDA_ANTES = r`euros|eur|usd|us\$|u\$`
const NUM = r`(?<![\d.,])(\d[\d.,]{0,15})`
const MULT = r`(?: ?(mil|k|milhao|milhoes|mi)\b)?`
// Depois do número, o que não é quantia de dinheiro: "2 dias", "1o turno", "3%", "5 pontos", "3 vezes". O \s do Python
// inclui \x1c-\x1f: ESPACO.
const NAO_QUANTIA = `(?!${ESPACO}*` +
  r`(%|o turno|a reuniao|dias?\b|anos?\b|mes\b|meses\b|vezes\b|semanas?\b|horas?\b|pontos?\b|turnos?\b))`
// "R$ 100 mil em euros" é real, não euro: o número logo depois de "r$" nunca é moeda estrangeira.
// Com flag g, só para matchAll (o finditer do Python), que copia o padrão e não guarda estado.
const VALOR_DEPOIS = new RegExp(r`(?<!r\$)(?<!r\$ )` + NUM + MULT + r` ?(?:de |em )?(` + ROTULOS + r`)(?![\w$])`, 'g')
const VALOR_ANTES = new RegExp(r`(?<![\w$])(` + MOEDA_ANTES + r`) ?` + NUM + MULT + NAO_QUANTIA, 'g')
const POR_MES = r`(por mes|ao mes|mensais|mensal|todo mes|cada mes|/ ?mes|a month|per month|monthly)\b`
// O gasto precisa de verbo de gasto antes ("gasto", "pago", "custa", "aluguel"): "rendendo 1% ao mês" e "ganho 10 mil
// por mês" não são gasto (renda é dado que o agente não usa, N5). Grupos: 2 número, 3 multiplicador, 4 moeda.
const GASTO_DEPOIS = rx(
  r`\b(gast\w*|pag\w*|cust\w*|despes\w*|aluguel|mensalidade|preciso de|vivo com|uso|tiro|saco|spend\w*|pay\w*)\b`,
  r`[^.!?\d]{0,25}?(?:r\$ ?)?`, NUM, MULT, `(?!${ESPACO}*%)`, r`(?: ?(reais|`, ROTULOS, r`))?[^.\d!?%]{0,25}?\b`, POR_MES,
)
const GASTO_ANTES = rx(
  r`\b(mensalidade|gasto mensal|custo mensal|despesa mensal)( (de|e|eh))? (?:r\$ ?)?`, NUM, MULT,
  r`(?: ?(reais|`, ROTULOS, r`))?`,
)
// Mover o dinheiro de lugar: quando, se e quanto mover é o que o agente não diz (N1, N4, N5).
// Sem "traz" (3ª pessoa: "o que a eleição traz para o dólar depois?") e sem "passo" ("passo a passo").
// TROCA_VERBOS é o TROCA[1:-1] do Python (sem os parênteses).
const TROCA_VERBOS = r`trago|trazer|troco|trocar|converto|converter|mando|mandar|envio|enviar|transfiro|transferir|remeto|remeter|` +
  r`traer\w*|cambiar|bring|convert|exchange|move`
const TROCA = `(${TROCA_VERBOS})`
const EVENTO = r`(o |a |do |da |de |the )?(segundo turno|2o turno|primeiro turno|turno|eleicao|election|domingo|copom|reuniao|resultado)`
// Quando mover: "troco hoje?", "trago depois do 2º turno?", "antes ou depois?", "qual o melhor momento pra trocar?".
const MOMENTO_TROCA = rx(
  r`\b`, TROCA, r`\b[^.?!]{0,40}\b(agora|ahora|antes|depois|hoje|ja|amanha|now|before|after)\b`,
  r`|\b(quando|cuando|hoje|agora|ahora|antes|depois)\b[^.?!]{0,20}\b(troco|trocar|trago|trazer|traer\w*|mando|mandar`,
  r`|envio|enviar|converto|converter|transfiro|transferir|cambiar|cambio a)\b`,
  r`|\b(antes|depois|before|after) `, EVENTO, r`\b[^.?!]{0,20}\bou (espero|esperar|depois|antes|nao)\b`,
  r`|\bantes ou depois\b|\bagora ou (depois|espero|mais tarde)\b|\bou espero\b`,
  r`|\b(momento|hora|dia|epoca|data)\b[^.?!]{0,20}\b(trocar|trazer|converter|mandar|enviar|transferir|cambiar)\b`,
)
// Quanto mover, ou que parte: alocação (N5). Aí o valor não entra na conta, e vale a recusa do capital.
const QUANTO_TROCAR = rx(
  r`\bquanto (\w+ ){0,4}?(coloco|ponho|invisto|aplico|boto|trago|troco|converto|mando|envio|remeto|mantenho|`,
  r`deixo|tiro|passo|devia|deveria|trazer|trocar|converter|mandar|enviar|remeter|manter|deixar|tirar|passar)\b`,
  r`|\bquanto investir\b|\bquantos contratos\b|\b(que|qual|quanto) (parte|porcentagem|percentual|fatia|pedaco)\b`,
  r`|\bquanto disso\b|\b(`, TROCA_VERBOS, r`|deixo|mantenho)\b[^.?!]{0,25}\b(tudo|metade|um terco|uma parte|parte`,
  r`|o resto|aos poucos|de uma vez|em (parcelas|etapas)|\d+ ?%|half|all)\b`,
  r`|\b(tudo|metade|parte) ou (tudo|metade|parte|nada)\b|\bhow much\b|\b(what|which) (part|portion|percentage|share)\b`,
  r`|\ball or (half|part)\b`,
)
const MULTIPLICA: ReadonlyMap<string, number> = new Map([['mil', 1e3], ['k', 1e3], ['milhao', 1e6], ['milhoes', 1e6], ['mi', 1e6]])

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

/** _moeda do Python: o rótulo que o padrão achou vira a chave da moeda; "reais" é o real. */
function moedaDe(rotulo: string | undefined): string | null {
  if (!rotulo) return null
  if (rotulo === 'reais') return 'real'
  const achada = MOEDA_INTEIRA.find(([, padrao]) => padrao.test(rotulo))
  // o next() do Python levanta StopIteration; não acontece, porque o rótulo saiu do mesmo padrão
  if (!achada) throw new Error(`moeda desconhecida: ${rotulo}`)
  return achada[0]
}

/** _quantia do Python: a quantia em qualquer formato que um brasileiro ou um estrangeiro escreve: '150.000' e '150,5'
 * (Brasil), '50,000' e '1.5' (inglês, com até 2 casas depois do ponto), '1,5' + 'milhao' → 1.500.000. Número quebrado
 * ('1,2,3') ou absurdo não vale. A pontuação colada no fim ("4.500," / "150.000.") não é parte do número. */
function quantia(bruto: string, mult: string | undefined): number | null {
  const numero = bruto.replace(/[.,]+$/, '') // rstrip('.,')
  let texto: string
  if (/^\d{1,3}(\.\d{3})+(,\d+)?$/.test(numero)) texto = numero.replaceAll('.', '').replaceAll(',', '.') // 150.000 / 150.000,50
  else if (/^\d{1,3}(,\d{3})+(\.\d+)?$/.test(numero)) texto = numero.replaceAll(',', '') // 50,000 / 2,000.50
  else if (/^\d+,\d+$/.test(numero)) texto = numero.replace(',', '.') // 1,5
  else if (/^\d+\.\d{1,2}$/.test(numero) || /^\d+$/.test(numero)) texto = numero // 1.5 / 1.25 / 150
  else return null
  const v = Number(texto) * (MULTIPLICA.get(mult ?? '') ?? 1)
  return 0 < v && v < 1e10 ? v : null
}

export type Cambio = [valor: number | null, moeda: string | null, gasto: number | null, gasto_moeda: string | null]

/** cambio() do Python: (valor, moeda, gasto por mês, moeda do gasto) do texto já normalizado. O gasto sem moeda é em reais. */
export function cambio(t: string): Cambio {
  let gasto: number | null = null
  let gastoMoeda: string | null = null
  let g = GASTO_DEPOIS.exec(t)
  if (g) {
    gasto = quantia(g[2], g[3])
    gastoMoeda = moedaDe(g[4]) ?? 'real'
  } else {
    g = GASTO_ANTES.exec(t)
    if (g) {
      gasto = quantia(g[4], g[5])
      gastoMoeda = moedaDe(g[6]) ?? 'real'
    }
  }
  if (gasto === null) {
    g = null
    gastoMoeda = null
  }
  // O valor é o 1º dinheiro em moeda estrangeira do texto que não seja o próprio gasto ("pago 3 mil dólares por mês").
  // Os dois padrões nunca começam na mesma posição (um começa por dígito, o outro por letra): ordenar pelo início basta.
  const achados: [number, string, string | undefined, string][] = [
    ...[...t.matchAll(VALOR_DEPOIS)].map((m): [number, string, string | undefined, string] => [m.index, m[1], m[2], m[3]]),
    ...[...t.matchAll(VALOR_ANTES)].map((m): [number, string, string | undefined, string] => [m.index, m[2], m[3], m[1]]),
  ].sort((a, b) => a[0] - b[0])
  for (const [inicio, texto, mult, rotulo] of achados) {
    if (g && g.index <= inicio && inicio < g.index + g[0].length) continue
    const valor = quantia(texto, mult)
    if (valor !== null) return [valor, moedaDe(rotulo), gasto, gastoMoeda]
  }
  return [null, null, gasto, gastoMoeda]
}

export function analisar(pergunta: string): Pedido {
  const t = normalizar(pergunta)
  const achou = (padroes: Record<string, RegExp>): string[] =>
    Object.entries(padroes).filter(([, padrao]) => padrao.test(t)).map(([k]) => k)
  const p: Pedido = {
    pergunta, mercados: achou(MERCADOS), candidatos: achou(CANDIDATOS), temas: achou(TEMAS), proibidos: achou(PROIBIDOS),
    voto_informado: VOTO_INFORMADO.test(t), pontos: null, contratos: 1,
    valor_moeda: null, moeda: null, gasto_mensal: null, gasto_moeda: null,
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
  // Quando mover o dinheiro de lugar ("troco hoje?", "trago depois do 2º turno?"): momento (N4) e a recusa padrão.
  const momentoTroca = MOMENTO_TROCA.test(t)
  if (momentoTroca) {
    for (const codigo of ['momento', 'dica']) if (!p.proibidos.includes(codigo)) p.proibidos.push(codigo)
    tirar(p.proibidos, 'comparar') // "antes ou depois de domingo" não compara classes de ativos
  }
  const quanto = QUANTO_TROCAR.test(t)
  if (quanto && !p.proibidos.includes('capital')) p.proibidos.push('capital')
  // Conta neutra de câmbio com o dinheiro que a pessoa contou (P4): o valor em reais, quanto muda a cada R$ 0,10 e
  // quantos meses de gasto cobre. Não entra quando ela pergunta quanto mover (alocação, N5) nem quando mover (N4): ao
  // lado da reação nos turnos, o valor dela viraria indicação de momento. Pergunta de contrato (mini-dólar) também não.
  const [valor, moeda, gasto, gastoMoeda] = cambio(t)
  const contratoFuturo = p.mercados.some((x) => x === 'mini_indice' || x === 'mini_dolar') || CONTRATO.test(t)
  if (valor !== null && moeda !== null && !contratoFuturo) {
    if (quanto || momentoTroca) {
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

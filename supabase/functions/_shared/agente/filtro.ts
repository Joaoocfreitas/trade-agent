// O filtro de saída: barra frase proibida, número sem fonte e resposta sem os avisos. Tradução de agente/filtro.py.
//
// Segue a tabela "O que o filtro barra" da nota de regras. Vale para a resposta da IA e para a do modo sem IA: as duas
// passam por aqui antes de chegar à pessoa.
import { simples, type Violacao } from './texto.ts'

// Os padrões de frase rodam sobre simples(texto), que é ASCII: ali \b, \w e \d do JS valem o mesmo que no Python, mas
// o \s não (o do Python também pega \x1c-\x1f).
const S = String.raw`[\t-\r\x1c-\x20]`

// Os de número rodam sobre o texto original, onde o \s, o \w e o \d do Python são Unicode (Python 3.12 = Unicode 15.0).
// \s é str.isspace: tem \x1c-\x1f e U+0085, que o do JS não tem, e não tem U+FEFF, que o do JS tem. O JS conhece letras
// e dígitos de escritas que entraram depois (Unicode 16): elas saem das classes para as duas classificarem igual.
const ESPACO = String.raw`\t-\r\x1c-\x20\x85\xa0\u{1680}\u{2000}-\u{200A}\u{2028}\u{2029}\u{202F}\u{205F}\u{3000}`
const NOVOS_DEPOIS_DO_UNICODE_15 = String.raw`\u{1C89}-\u{1C8A}\u{A7CB}-\u{A7CD}\u{A7DA}-\u{A7DC}\u{105C0}-\u{105F3}` +
  String.raw`\u{10D40}-\u{10D65}\u{10D6F}-\u{10D85}\u{10EC2}-\u{10EC4}\u{11380}-\u{11389}\u{1138B}\u{1138E}` +
  String.raw`\u{11390}-\u{113B5}\u{113B7}\u{113D1}\u{113D3}\u{116D0}-\u{116E3}\u{11BC0}-\u{11BE0}\u{11BF0}-\u{11BF9}` +
  String.raw`\u{13460}-\u{143FA}\u{16100}-\u{1611D}\u{16130}-\u{16139}\u{16D40}-\u{16D6C}\u{16D70}-\u{16D79}\u{18CFF}` +
  String.raw`\u{1CCF0}-\u{1CCF9}\u{1E5D0}-\u{1E5ED}\u{1E5F0}-\u{1E5FA}\u{2EBF0}-\u{2EE5D}`
const W = String.raw`[[\p{L}\p{N}_]--[${NOVOS_DEPOIS_DO_UNICODE_15}]]` // \w do Python
const D = String.raw`[\p{Nd}--[${NOVOS_DEPOIS_DO_UNICODE_15}]]` // \d do Python

// Verbos de recusa: "não digo X", "nem dou X", "não posso afirmar", "não sei se". Uma frase proibida depois deles, na
// mesma oração, é a recusa e não a dica.
const RECUSANDO = new RegExp(
  String.raw`\b(nao|nem|nunca)${S}+(\w+${S}+){0,2}?(digo|dizer|diria|dou|dar|indico|indicar|faco|fazer|calculo|` +
    String.raw`calcular|comento|comentar|uso|usar|monto|montar|mostro|estimo|prometo|mando|ensino|comparo|trato|` +
    String.raw`mudo|tiro|pergunto|apresento|recomendo|sugiro|afirmo|afirmar|sei|sabemos|saber|prever|prevejo|` +
    String.raw`garanto|garantir|consigo|como)\b|\b(proibe|proibem|proibido|proibida|proibidas)\b` +
    String.raw`|\b(ninguem|nenhum|nenhuma|impossivel|nao e possivel|nao ha como|nao tenho como)\b`,
)
const VERBOS_DE_RECUSA = new RegExp(
  String.raw`(digo|dou|indico|faco|calculo|comento|uso|monto|mostro|estimo|prometo|mando|ensino|` +
    String.raw`comparo|recomendo|sugiro|pergunto|apresento)\b`,
  'y',
)
const NEGADO_NO_FIM = new RegExp(String.raw`\b(nao|nem|nunca)${S}+$`)
// Atribuição: o fato é de quem disse ("o programa promete", "pelo Focus", "segundo a FGV"), não do agente.
const ATRIBUICAO = new RegExp(
  String.raw`\b(diz|disse|dizem|afirma|afirmou|propoe|propos|promete|prometeu|defende|registrou|segundo|` +
    String.raw`pelo boletim|pelo focus|o focus|os economistas|de acordo com)\b`,
)
const AMBAS = new RegExp(
  String.raw`\b(subir ou cair|sobe ou cai|cair ou subir|cai ou sobe|alta ou queda|queda ou alta|` +
    String.raw`para cima ou para baixo|pra cima ou pra baixo)\b`,
)
const INEXISTENTE = /\bnao (existe|ha|tem)\b/
const ORACAO = /[.!?;:\n]|\b(mas|porem|contudo|entretanto|so que)\b/g

const SUJ = String.raw`(o |a |os |as )?(ibovespa|ibov|bolsa|indice|mini-indice|mini indice|dolar|euro|real|juros|di1?|bitcoin|cripto|` +
  String.raw`token|memecoin|win|wdo|bova11|acoes|mercado)`
const DIR = String.raw`(sobe|sobem|subira|subiria|subir|suba|cai|caem|caira|cairia|cair|caia|dispara|disparar|despenca|despencar|` +
  String.raw`derrete|derreter|valoriza|valorizar|desvaloriza|desvalorizar|aprecia|apreciar|se apreciar|recua|recuar|cede|` +
  String.raw`ceder|fecha|fechar|abre|abrir|melhora|piora|reagir bem|reagir mal|reage bem|reage mal|vai bem|vai mal)`
const EXCH = String.raw`(binance|coinbase|mercado bitcoin|foxbit|bybit|okx|kraken|novadax|bitso|bitget|kucoin)`

// (regra, padrão, isenções). Padrões sobre o texto em minúsculas e sem acento.
// Isenções: 'recusa' (oração com verbo de recusa ou "ninguém sabe"), 'atribuicao' (o fato é de quem disse), 'ambas'
// (as duas direções juntas), 'inexistente' ("não existe lucro garantido").
type Isencao = 'recusa' | 'atribuicao' | 'ambas' | 'inexistente'
const R: Isencao = 'recusa', A: Isencao = 'atribuicao', B: Isencao = 'ambas', I: Isencao = 'inexistente'
const PADROES_FONTE: [string, string, Isencao[]][] = [
  // N1: ordem, "bom momento", "se eu fosse você"
  ['N1', String.raw`\b(compre|comprem|vende ja|venda ja|venda tudo|vende tudo|zere|zerem|aproveite|mantenha (a )?posicao|` +
    String.raw`realize o lucro|considere (comprar|vender|entrar))\b`, [R]],
  ['N1', String.raw`(^|[.!?;:,]${S}*)(compra|vende) (na|no|ja|agora|antes|tudo|hoje|amanha|logo)\b`, [R]],
  ['N1', String.raw`\b(entr(a|e|em)|entrar|ficar|fica|fique|estar|bora entrar) (comprado|vendido|posicionado|de fora|na alta|na baixa)\b`, [R]],
  ['N1', String.raw`\bpode (comprar|vender|entrar|apostar|operar) (sem medo|tranquilo|ja|agora|sem)\b`, []],
  ['N1', String.raw`\b(boa|otima|melhor) hora (de|para|pra)\b|\bhora (de|pra|para) (comprar|vender|entrar|sair|operar)\b`, [R]],
  ['N1', String.raw`\bvale a pena (comprar|vender|entrar|operar|investir)\b|\bvale considerar\b|\bnao seria loucura\b` +
    String.raw`|\bfaz sentido (ter|estar|comprar|entrar|montar|operar)\b|\bpode ser interessante\b` +
    String.raw`|\b(boa|otima|grande) (janela|oportunidade)\b|\bmomento (e |esta )?favoravel\b|\b(agora|hoje) e (o|a) (momento|hora)\b` +
    String.raw`|\b(bom|otimo|melhor) momento (para|pra|de)\b|\boportunidade (de|para|pra) (compra|venda|entrada|comprar|vender|entrar|ganho|lucro)\b` +
    String.raw`|\b(bom|otimo|melhor) dia (para|pra) (tentar|operar|entrar|comprar|vender)\b|\bvale mais (estar|ter|ficar|comprar)\b`, [R]],
  ['N1', String.raw`\b(se eu fosse voce|se fosse voce|no seu lugar)\b`, []],
  ['N1', String.raw`\beu (ficaria|aguardaria|esperaria|compraria|venderia|entraria|usaria|manteria|apostaria)\b`, []],
  ['N1', String.raw`\b(voce|vc) deve(ria)? (comprar|vender|entrar|sair|operar|investir|zerar|esperar)\b`, [R]],
  ['N1', String.raw`\b(recomendo|sugiro) (comprar|vender|entrar|sair|a compra|a venda|ficar)\b`, [R]],
  ['N1', String.raw`\b(you should|i would|i'd|you'd better) (buy|sell)\b|\bcompraria\b|\bdeberias? comprar\b`, []],
  // N2: direção provável, dita de qualquer jeito
  ['N2', String.raw`\b${SUJ}\b( \w+){0,3}? (nao )?(vai|vao|deve|devem|deveria|tende a|tendem a|pode|podem|ira|promete)( \w+)? ${DIR}\b`, [R, A, B]],
  ['N2', String.raw`\b${SUJ} (\w+ ){0,2}?(sobe|sobem|cai|caem|dispara|despenca|derrete|valoriza|desvaloriza|recua|cede|melhora|piora)\b`, [R, A, B]],
  ['N2', String.raw`\b(vai|vao|deve|devem|tende a|tendem a) (subir|cair|disparar|despencar|valorizar|desvalorizar|explodir|bombar)\b`, [R, A, B]],
  ['N2', String.raw`\b(tendencia|vies|o mais provavel|mais provavel|provavelmente|probabilidade maior|o esperado|espera-se|esperase|` +
    String.raw`a expectativa|perspectiva)\b[^.\n]{0,30}\b(alta|queda|positiv\w*|negativ\w*|valorizacao|desvalorizacao|vendedor\w*|` +
    String.raw`comprador\w*|altista|baixista|subir|suba|cair|caia)\b`, [R, A]],
  ['N2', String.raw`\b(favorece|a favor de quem compra|assimetria|espaco para (subir|cair|valorizar)|tem espaco|potencial de (alta|valorizacao)|` +
    String.raw`bom potencial|risco-retorno|risco retorno)\b`, [R]],
  ['N2', String.raw`\b(minha visao|minha opiniao|na minha opiniao|minha aposta|minha leitura e|acho que (sobe|cai|vale|vai)|vejo (uma )?chance)\b`, []],
  ['N2', String.raw`\b(sim|nao)[:,]? (o \w+ |a \w+ )?(sobe|cai|vai subir|vai cair)\b|(^|[.!?]${S}+)(sobe|cai|desce|dispara)[.!]`, []],
  ['N2', String.raw`\d+([.,]\d+)? ?(%|por cento) de (chance|probabilidade)|\bchance de \d+ ?%`, []],
  ['N2', String.raw`\b(chance|chances|probabilidade|probabilidades) (de|do|da) (\w+ ){0,3}?(alta|queda|subir|cair|subida|valorizacao|` +
    String.raw`ganho|lucro|vitoria|vencer|ganhar)\b`, [R, A]],
  ['N2', String.raw`\b(flavio|lula|bolsonaro)\b[^.\n]{0,15}\b(deve|vai|tende a) (vencer|ganhar|levar|ser eleito|perder)\b` +
    String.raw`|\b(e|eh) o favorito\b|\bfavorito (para|pra)\b`, [R, A]],
  ['N2', String.raw`\bvitoria d[oa] \w+ (e|significa|seria) (alta|queda)\b|\b(esta|ta) (barat[oa]|car[oa]|no topo|no fundo|descontad[oa])\b`, []],
  ['N2', String.raw`\bnota \d+ de (0 a )?(10|100)\b|\b\d+ de 0 a 100\b|\b(preco-alvo|preco alvo|projecao|projetamos) (de|para|em) \d`, []],
  ['N2', String.raw`\bwill (probably )?(go up|go down|rise|fall|strengthen|weaken|rally)\b|\btends? to (rally|rise|fall|go up)\b` +
    String.raw`|\bva a (subir|bajar)\b`, []],
  ['N2', String.raw`\b(win|wdo|dol|ind|di1|bova11|petr[34]|vale3|itub4|bbas3|bbdc4)\b[^.\n]{0,25}\b(vai subir|vai cair|comprad[oa]|` +
    String.raw`vendid[oa]|vies|alvo|disparar)\b`, [R]],
  // N3: manchete de direção a partir do histórico
  ['N3', String.raw`\b(subiu|caiu|subiram|cairam|fechou em alta|fechou em queda|deu alta|deu queda|valorizou|desvalorizou)\b[^.\n]{0,40}` +
    String.raw`\b\d+ (de|em|das|dos) \d+\b`, []],
  ['N3', String.raw`(?<![\d,./])\b(uma|duas|tres|quatro|cinco|seis|sete|oito|nove|dez|\d+) (das|de|em|dos) (duas|tres|quatro|cinco|seis|` +
    String.raw`sete|oito|nove|dez|\d+)\b(?![\d,./])[^.\n]{0,50}\b(subiu|subiram|caiu|cairam|alta|queda|sobe|cai|positiv|negativ)`, []],
  ['N3', String.raw`\b(subiu|caiu|subiram|cairam)\b[^.\n]{0,25}\bem (todos|todas) (os|as)\b|\bem (todos|todas) (os|as) \d+ \w+[^.\n]{0,30}\b(subiu|caiu|alta|queda)`, []],
  ['N3', String.raw`\b(na maioria|na maior parte|maior parte das|maioria dos|maioria das|quase sempre|sempre)\b[^.\n]{0,40}\b(sub\w*|cai|caiu|` +
    String.raw`cairam|alta|queda)\b|\b(subiu|caiu|sobe|cai)\b[^.\n]{0,25}\b(na maioria|na maior parte|maior parte)\b`, []],
  ['N3', String.raw`\bem \d+ ?% das (vezes|reunioes|eleicoes|turnos|casos)\b|\bo esperado e (alta|queda)\b`, []],
  ['N3', String.raw`\b(historicamente|em geral|normalmente|tipicamente|costuma|costumam)\b[^.\n]{0,25}\b(sobe|subir|cai|cair|reagir bem|` +
    String.raw`reagir mal|reage bem|reage mal|valoriza)\b`, []],
  // N4: momento, entrada, saída, stop, alvo, alerta, pregão ao vivo
  ['N4', String.raw`\bstop( loss| gain)? (em|de|no|na|a) \d|\bstop (logo )?(abaixo|acima)\b|\b(poe|ponha|coloque|coloca|use) o stop\b|\bum stop de\b`, []],
  ['N4', String.raw`\b(alvo|preco-alvo|preco alvo) (natural|fica|em|de|perto)\b|\b(entrada|saida|ponto de entrada|ponto de saida) (em|de|no|na|a) \d`, []],
  ['N4', String.raw`\bsaia no fim do dia\b|\bentre com \d+ contratos?\b|\bde olho na (abertura|virada|vespera)\b` +
    String.raw`|\b(compr|vend|entr)\w* [^.\n]{0,20}\bna vespera\b`, []],
  ['N4', String.raw`\b(entre|entrar|compre|comprar|venda|vender|opere|operar) (na|no|ate a|antes d[oa]) (abertura|fechamento|sexta|segunda|vespera)\b`, [R]],
  ['N4', String.raw`\b(melhor hora|hora certa|momento certo) (para|pra|de) (entrar|operar|comprar|vender)\b`, [R]],
  ['N4', String.raw`\bte (aviso|alerto|mando um alerta)\b|\bvou te avisar\b|\b(alerta|sinal) de (compra|venda|entrada)\b`, [R]],
  ['N4', String.raw`\bneste momento\b[^.\n]{0,40}\b(caindo|subindo)\b|\btendencia do dia\b`, []],
  // N5: capital, perfil, objetivo
  ['N5', String.raw`\b(com|seus|teus|esses|esse|para quem tem) (r\$ ?\d[\d.,]*( mil)?|\d+ ?k|\w+ mil reais|cinco mil)\b[^.\n]{0,60}` +
    String.raw`\b(contratos?|coloque|aloque|invista|aplique|compre|opera\w*|comecar|em cripto|em renda fixa|em bitcoin|%|o ideal)`, []],
  ['N5', String.raw`\b(coloque|aloque|invista|aplique|ponha|reparta)\b[^.\n]{0,30}(\d+ ?%|r\$|contratos?|metade|um terco|tudo)`, []],
  ['N5', String.raw`\b(para|pra) (o seu|seu|a sua|sua) (perfil|capital|caso|objetivo|aposentadoria|idade|reserva)\b|\bcom o seu capital\b` +
    String.raw`|\bcomo (voce|vc) tem \d+ anos\b|\bsua reserva de emergencia\b`, [R]],
  ['N5', String.raw`\b(\d+|um|uma|dois|duas) (contratos?|minicontratos?|lotes?) (e|eh) o ideal\b|\bo ideal e comecar\b` +
    String.raw`|\bda (pra|para) operar (uns |ate )?\d+|\b(opere|comece com|use) \d+ (contratos?|lotes?)\b`, []],
  ['N5', String.raw`\b(voce|vc) e (mais )?(conservador|arrojado|moderado)\b|\bqual (e )?(o )?seu (objetivo|prazo|perfil|capital|patrimonio)\b`, []],
  // N7 e N8: exchange, corretora, plataforma de previsão ou de aposta
  ['N7', String.raw`\b(usaria|use|usa|utilize|abra (sua |uma )?conta (na|no)|cadastre-se (na|no)|baixe|recomendo|indico|prefira|pode usar)\b` +
    String.raw`[^.\n]{0,25}\b(${EXCH}|polymarket|kalshi|iq option)\b`, [R]],
  ['N7', String.raw`\b${EXCH}\b[^.\n]{0,40}\b(melhor|mais segura|mais barata|confiavel|opcao)\b|\ba melhor (exchange|corretora|plataforma)\b`, [R]],
  ['N7', String.raw`\b(use|usa|utilize|abra conta n[ao]|cadastre-se n[ao]|prefira|recomendo|indico) (a |o |uma |um )?(exchange|corretora|plataforma|app|token)\b`, [R]],
  ['N7', String.raw`\b(token|memecoin)\b[^.\n]{0,30}\b(bom potencial|potencial|vai valorizar|pode valorizar|valoriza)\b`, []],
  ['N8', String.raw`polymarket\.com|kalshi\.com|iqoption\.com`, []],
  ['N8', String.raw`\b(polymarket|kalshi|mercados? de previsao)\b[^.\n]{0,50}(\d+ ?%|\d+ centavos|cotad|acert\w*|confiave\w*|boa ideia|termometro)`, [R]],
  ['N8', String.raw`\b(use|usa|ative|instale|uma|com|pela|por) vpn\b|\bvpn (funciona|resolve|libera|passa)\b|\btrocando a regiao\b` +
    String.raw`|\b(acessar|usar) a (kalshi|polymarket)\b|\b(aposte|pode apostar) (na|no|em)\b`, [R]],
  ['N8', String.raw`\btermometro real\b|\bverdadeira pesquisa\b|\bmelhor que as pesquisas\b|\bacert\w* mais que (as pesquisas|os institutos)\b` +
    String.raw`|\bmais confiavel que as pesquisas\b`, [R]],
  // N9: voto e lado
  ['N9', String.raw`\bem quem (voce|vc) (vota|votou|vai votar|pretende|votaria)\b|\b(voce|vc) votou\b|\bqual (e )?(o )?seu candidato\b` +
    String.raw`|\bqual candidato (voce|vc) prefere\b|\b(voce|vc) (e|eh) (de direita|de esquerda|petista|bolsonarista|lulista)\b` +
    String.raw`|\b(voce|vc) apoia\b|\b(voce|vc) tende (mais )?(para|pro)\b|\btorcendo (pelo|pela|por|pro)\b|\bvote (no|na|em)\b`, [R]],
  ['N9', String.raw`\b(flavio|lula|bolsonaro|o pt|o pl)\b[^.\n]{0,25}\b(e|seria|eh) (o )?(melhor|pior|ruim|bom|otimo|pessimo) (para|pro|pra)\b` +
    String.raw`|\bmelhor candidato\b|\b(o mercado|os investidores|investidores) (claramente )?(prefere|preferem|quer|querem|gosta|gostam|` +
    String.raw`veem com bons olhos|ve com bons olhos)\b|\bpreferido do mercado\b|\bcandidato do mercado\b` +
    String.raw`|\bvitoria d[oa] \w+ (seria|e) (ruim|boa|otima|pessima|positiva|negativa)\b`, [R, A]],
  // M2: ranking e destaque de ativo
  ['M2', String.raw`\b(as|os) (\w+ )?(acoes|ativos|papeis) que mais (se beneficiam|sobem|ganham)\b|\bque mais se beneficia\w*\b|\b(top|ranking) \d`, []],
  // M6: promessa de ganho ou de acerto
  ['M6', String.raw`\b(lucro|ganho|renda) (garantid[oa]|certo|certa|facil|extra|mensal)\b|\bsem risco\b|\bdinheiro facil\b|\baprenda a lucrar\b` +
    String.raw`|\b(acerta|acertamos|acertou|acerto de) \d+ ?%|\btaxa de acerto\b|\b(fique|ficar) rico\b|\btirar uma renda\b` +
    String.raw`|\bretorno consistente\b|\bacerta a direcao\b|\bmodelo acerta\b`, [R, I]],
  // D6: urgência
  ['D6', String.raw`\b(ultima chance|nao perca|corra|imperdivel|agora ou nunca|agora e a hora|nao da (pra|para) ficar de fora|quem entrar cedo)\b` +
    String.raw`|\bcorre (pra|para)\b|\bantes que (o \w+ |a \w+ )?(seja tarde|acabe|suba|caia|passe|dispare)\b|\bcerteza absoluta\b` +
    String.raw`|\bcom (toda )?certeza (vai (subir|cair)|o \w+ (sobe|cai))\b|\brapido,? (entra|compra|vende|antes)\b`, []],
]
const PADROES: [string, RegExp, ReadonlySet<Isencao>][] = PADROES_FONTE.map(([r, p, i]) => [r, new RegExp(p, 'g'), new Set(i)])

// O str.strip() do Python, sobre texto ASCII.
const PONTAS = new RegExp(`^${S}+|${S}+$`, 'g')

function isento(t: string, ini: number, fim: number, isencoes: ReadonlySet<Isencao>): boolean {
  let inicio = 0
  for (const x of t.slice(0, ini).matchAll(ORACAO)) inicio = x.index + x[0].length
  ORACAO.lastIndex = fim
  const prox = ORACAO.exec(t)
  ORACAO.lastIndex = 0
  const oracao = t.slice(inicio, prox ? prox.index : t.length)
  const antes = t.slice(inicio, ini)
  if (isencoes.has(R)) {
    if (RECUSANDO.test(antes)) return true
    // "não indico corretora": a própria frase barrada começa no verbo de recusa negado.
    VERBOS_DE_RECUSA.lastIndex = ini
    if (NEGADO_NO_FIM.test(antes) && VERBOS_DE_RECUSA.test(t)) return true
  }
  if (isencoes.has(A) && ATRIBUICAO.test(oracao)) return true
  if (isencoes.has(B) && AMBAS.test(oracao)) return true
  if (isencoes.has(I) && INEXISTENTE.test(antes)) return true
  return false
}

export function frasesProibidas(texto: string): Violacao[] {
  const t = simples(texto)
  const achados: Violacao[] = []
  for (const [regra, rx, isencoes] of PADROES) {
    for (const m of t.matchAll(rx)) {
      const ini = m.index, fim = ini + m[0].length
      if (isencoes.size && isento(t, ini, fim, isencoes)) continue
      achados.push({ regra, trecho: t.slice(Math.max(0, ini - 30), fim + 30).replace(PONTAS, '') })
    }
  }
  return achados
}

// ---------- números ----------

/** O Decimal do Python: valor = coef × 10^exp, guardando os zeros do fim ("1,50" tem exp -2). Nunca negativo aqui. */
export type Dec = { coef: bigint; exp: number }
export type Numero = [tok: string, valor: Dec, casas: number]

// URL no Python; LINK aqui para não esconder a classe URL global.
const LINK = new RegExp(String.raw`https?://[^${ESPACO}]+`, 'gv')
const REF = new RegExp(String.raw`\[${D}+\]`, 'gv')
// WINZ26, R2/2020, BR-01234/2026. O \b do Python vira "sem letra/dígito Unicode antes ou depois".
const CODIGO = new RegExp(
  String.raw`(?<!${W})[A-Z]{1,6}${D}{1,4}[A-Z]?${D}*(?!${W})|(?<!${W})R${D}/${D}{4}(?!${W})|(?<!${W})BR-${D}{5}/${D}{4}(?!${W})`,
  'gv',
)
const NUMERO = new RegExp(String.raw`${D}+(?:[.,]${D}+)*`, 'gv')
const MILHAR = new RegExp(String.raw`^${D}{1,3}(\.${D}{3})+(,${D}+)?$`, 'v')
const MIL = new RegExp(String.raw`[${ESPACO}]*mil(?!${W})`, 'vy')
const DIGITO = new RegExp(String.raw`^${D}$`, 'v')
const SEMPRE_PERMITIDO = 12n // inteiros pequenos: "3 linhas", "1 contrato", "2º turno"
const PRECISAO = 28 // contexto padrão do Decimal
const PRECISAO_QUANTIZE = 60 // o localcontext de numeros_sem_fonte: 12 dígitos inteiros + 20 casas cabem
const MAX_DIGITOS = 20 // número maior que isso não existe nos fatos: é solto, sem conta
const LIMITE = 10n ** 12n

/** O Decimal do Python aceita qualquer dígito Unicode: "١٢" vale 12. Os dígitos vêm em blocos de 0 a 9. */
function paraAscii(tok: string): string {
  let s = ''
  for (const ch of tok) {
    const cp = ch.codePointAt(0) ?? 0
    if (cp < 0x80) {
      s += ch
      continue
    }
    let n = 0
    while (DIGITO.test(String.fromCodePoint(cp - 1 - n))) n++
    s += String(n % 10)
  }
  return s
}

function digitos(c: bigint): number {
  return c.toString().length
}

/** c / div com ROUND_HALF_EVEN, a regra do Decimal. */
function divMeioPar(c: bigint, div: bigint): bigint {
  const q = c / div, resto = c % div
  return resto * 2n > div || (resto * 2n === div && q % 2n === 1n) ? q + 1n : q
}

/** O que o contexto faz com o resultado de uma conta (abs, ×1000): no máximo 28 dígitos, arredondando meio-par. */
function noContexto(d: Dec): Dec {
  const sobra = digitos(d.coef) - PRECISAO
  if (sobra <= 0) return d
  let coef = divMeioPar(d.coef, 10n ** BigInt(sobra)), exp = d.exp + sobra
  if (digitos(coef) > PRECISAO) {
    coef /= 10n
    exp += 1
  }
  return { coef, exp }
}

/** Compara com um inteiro, sem arredondar: negativo, zero ou positivo. */
function comparar(d: Dec, n: bigint): number {
  const [a, b] = d.exp >= 0 ? [d.coef * 10n ** BigInt(d.exp), n] : [d.coef, n * 10n ** BigInt(-d.exp)]
  return a < b ? -1 : a > b ? 1 : 0
}

/** d.quantize(Decimal(1).scaleb(e)) com precisão 60: o coeficiente no expoente e. Acima disso é InvalidOperation. */
function quantizar(d: Dec, e: number): bigint {
  const c = d.exp >= e ? d.coef * 10n ** BigInt(d.exp - e) : divMeioPar(d.coef, 10n ** BigInt(e - d.exp))
  if (d.coef !== 0n && digitos(c) > PRECISAO_QUANTIZE) throw new RangeError('quantize: o resultado tem mais dígitos que a precisão')
  return c
}

/** A mesma chave para valores iguais (1,50 e 1,5), como o set de Decimal do Python. */
function chave(d: Dec): string {
  if (d.coef === 0n) return '0'
  let { coef, exp } = d
  while (coef % 10n === 0n) {
    coef /= 10n
    exp += 1
  }
  return `${coef}e${exp}`
}

/** Número em formato brasileiro (ou não) → (valor, casas decimais). */
function valor(tok: string): [Dec, number] | null {
  let s = paraAscii(tok)
  if (MILHAR.test(s)) s = s.replaceAll('.', '').replace(',', '.')
  else if (s.includes(',')) s = s.replaceAll('.', '').replaceAll(',', '.')
  else if (s.split('.').length > 2) s = s.replaceAll('.', '')
  const partes = s.split('.')
  if (partes.length > 2) return null // Decimal('1.2.3'): InvalidOperation
  const [inteira, frac = ''] = partes
  const d: Dec = { coef: BigInt(inteira + frac), exp: frac.length ? -frac.length : 0 }
  return [d, Math.max(0, -d.exp)]
}

export function numeros(texto: string): Numero[] {
  const t = texto.replace(LINK, ' ').replace(REF, ' ').replace(CODIGO, ' ')
  const saida: Numero[] = []
  for (const m of t.matchAll(NUMERO)) {
    const v = valor(m[0])
    if (v === null) continue
    let [val, casas] = v
    MIL.lastIndex = m.index + m[0].length
    if (MIL.test(t)) [val, casas] = [noContexto({ coef: val.coef * 1000n, exp: val.exp }), -3]
    saida.push([m[0], val, casas])
  }
  return saida
}

function pequeno(v: Dec): boolean {
  const inteiro = v.exp >= 0 || v.coef % 10n ** BigInt(-v.exp) === 0n
  return inteiro && comparar(v, SEMPRE_PERMITIDO) <= 0
}

/** Os números da resposta que não aparecem nos fatos, nem arredondados (D8). */
export function numerosSemFonte(texto: string, fatos: string): string[] {
  const base = new Map<string, Dec>()
  for (const [, v] of numeros(fatos)) if (!base.has(chave(v))) base.set(chave(v), v)
  const elegiveis = [...base.values()].filter((f) => comparar(noContexto(f), LIMITE) < 0)
  const soltos: string[] = []
  for (const [tok, v, casas] of numeros(texto)) {
    if (pequeno(v)) continue
    // Número com mais de 20 dígitos não existe nos fatos: é solto, sem conta (o quantize de precisão 60 nunca estoura).
    if (paraAscii(tok).replace(/[^0-9]/g, '').length > MAX_DIGITOS) {
      soltos.push(tok)
      continue
    }
    if (elegiveis.some((f) => quantizar(f, -casas) === quantizar(v, -casas))) continue
    soltos.push(tok)
  }
  return soltos
}

// ---------- o que toda resposta precisa ter ----------

const DERIVATIVO = /\bmini[- ]?(indice|dolar)\b|\bwin\b|\bwdo\b|\bdi futuro\b/
const AVISO_DE_PERDA = /perder mais do que|perda pode passar/
const CRIPTO = /\bcripto|\bbitcoin\b/

export function faltas(texto: string): Violacao[] {
  const t = simples(texto)
  const f: Violacao[] = []
  if (!(t.includes('sou uma ia') && t.includes('nao e recomendacao') && t.includes('cvm'))) {
    f.push({ regra: 'D3', trecho: 'faltam os avisos: sou uma IA, posso errar, não é recomendação, não somos credenciados' })
  }
  if (!t.includes('rentabilidade passada')) {
    f.push({ regra: 'D2', trecho: 'falta "rentabilidade passada não indica rentabilidade futura"' })
  }
  if (numeros(texto).some(([, v]) => !pequeno(v)) && texto.search(LINK) < 0) {
    f.push({ regra: 'D1', trecho: 'tem número e não tem fonte com link' })
  }
  if (DERIVATIVO.test(t) && !AVISO_DE_PERDA.test(t)) {
    f.push({ regra: 'D4', trecho: 'fala de derivativo e não avisa que a perda pode passar do depositado' })
  }
  if (CRIPTO.test(t) && !t.includes('nao e valor mobiliario')) {
    f.push({ regra: 'D5', trecho: 'fala de cripto e não diz que, em regra, não é valor mobiliário' })
  }
  return f
}

export function checar(texto: string, fatos: string): Violacao[] {
  return [
    ...frasesProibidas(texto),
    ...faltas(texto),
    ...numerosSemFonte(texto, fatos).map((n) => ({ regra: 'D8', trecho: `número sem fonte nos fatos: ${n}` })),
  ]
}

// Monta a resposta, sempre da base: tradução de agente/resposta.py. Os blocos de fatos vêm prontos de base.json
// (gerado por `python -m agente.exportar`); aqui só se escolhe, ordena, numera as fontes e passa pelo filtro.
import base from '../base.json' with { type: 'json' }
import { checar } from './filtro.ts'
import { search, sub } from './pyre.ts'
import {
  analisar, CONTRATO, ehCambio, ehEleicao, MERCADOS, normalizar, PRECO_EM_DOLAR, temConta, temContaCambio,
} from './roteador.ts'
import type { Pedido, Violacao } from './texto.ts'

type Fonte = { nome: string; url: string }
type Linha = { texto: string; fontes: Fonte[] }
type Bloco = { titulo: string; linhas: Linha[]; resumo: string; limites: string[] }
type Textos = {
  AVISO: string
  RECUSA: string
  FECHO: string
  RISCO_DERIVATIVO: string
  RISCO_DERIVATIVO_CRIPTO: string
  SEM_PRECO_CRIPTO: string
  SEM_DEFASAGEM: string
  RISCO_CRIPTO: string
  POR_PEDIDO: Record<string, string>
  PEDEM_RECUSA: string[]
  VOTO_INFORMADO: string
  SEM_REPERTORIO: string
  NORMAS: string
  SEGURA: string
  LIMITE_CRIPTO_ELEICAO: string
}
type Base = {
  textos: Textos
  derivativos: string[]
  tipos: string[]
  economia: Bloco
  eleicoes: Record<string, Bloco>
  copom: Record<string, Bloco>
  eventos: Record<string, Bloco>
  mercado: Record<string, Bloco | null>
  historico: Record<string, Bloco>
  expectativas: Record<string, Bloco>
  agenda: Record<string, { tipo: string; data: string; curto: string; fontes: Fonte[] }[]>
  calendario: { titulo: string; linha_inicio: string; linha_fim: string; resumo_inicio: string; resumo_fim: string }
  titulo_cripto: string
  candidatos: Bloco | null
  pesquisas: Bloco | null
  fgv: Bloco
  memecoins: Bloco
  previsao: Bloco
  binaria: Bloco
  conta: Record<string, { valor: number; nome: string; fonte: Fonte }>
  /** P4 de câmbio: as cotações e os textos fixos; a conta é feita na hora com o número da pessoa (contaCambio). */
  cambio: {
    cotacoes: Record<string, Cotacoes>
    moedas: Record<string, { nome: string; plural: string; fonte: Fonte }>
    titulo: string
    limite_euro: string
  }
  /** O euro nos turnos (fatos.euro_turnos), pronto. O caminho do euro está em historico.euro e agenda.euro. */
  euro_turnos: Bloco
  /** Cripto sem preço: os blocos prontos, a linha do tempo de cada tema ('' sem tema), a expressão que acha cada tema
   * (na ordem do JSON, o 1º que casa vale) e os 4 títulos que _cripto_primeiro põe na frente. */
  cripto: {
    imposto: Bloco
    /** o mesmo bloco, com o resumo da pergunta de ETF ou futuro e com o da pergunta de declaração (cripto_imposto(variante)) */
    imposto_etf: Bloco
    imposto_declaracao: Bloco
    riscos: Bloco
    marcos: Record<string, Bloco>
    temas: Record<string, string>
    titulos: string[]
  }
  /** fatos.dois_lados de cada mercado medido: quando caiu e quando subiu nos últimos 12 meses. */
  dois_lados: Record<string, Bloco | null>
  /** Petróleo: os eventos (a linha de cada evento uma vez só, em `linhas`, e um bloco por combinação de temas, chave
   * "tema1+tema2" na ordem do JSON, '' sem tema, com os índices dos eventos dele e as linhas que vêm depois), a expressão
   * que acha cada tema e do barril à bomba. O caminho do Brent está em historico.brent, dois_lados.brent e agenda.brent. */
  petroleo: {
    eventos: { linhas: Linha[]; blocos: Record<string, Bloco & { eventos: number[] }> }
    temas: Record<string, string>
    barril: Bloco
  }
  titulo_dois_lados: string
  /** O começo do resumo da economia (fatos.RESUMO_HOJE): ele vai por último nas 3 linhas. */
  resumo_hoje: string
}
/** fatos.cotacoes: a PTAX de hoje, a do fim do ano passado e a menor e a maior dos 12 meses (datas AAAA-MM-DD). */
type Cotacoes = {
  data: string
  valor: number
  ano_data: string
  ano_valor: number
  min_data: string
  min_valor: number
  max_data: string
  max_valor: number
}

export const BASE = base as unknown as Base
const r = String.raw
// fatos.tema_cripto e fatos.tema_petroleo: as expressões do JSON, na ordem dele (a de inserção das chaves, que o
// JSON.parse mantém). Os padrões, como os do roteador, têm o texto do Python e rodam pelo pyre.ts.
const TEMAS_CRIPTO = Object.entries(BASE.cripto.temas)
const TEMAS_PETROLEO = Object.entries(BASE.petroleo.temas)
// As linhas da linha do tempo inteira (sem tema): a definição de um tema é a 1ª linha dele que não está nela.
const MARCOS_DATADOS = new Set(BASE.cripto.marcos[''].linhas.map((ln) => ln.texto))
// A pessoa falou do índice mesmo, e não só da B3 como lugar. "Bolsa de cripto", "índice de medo" e "stock-to-flow" são
// da cripto.
const IBOV_DITO = r`\bibov\w*|\bbovespa\b|\bacoes\b|\bacao\b|\bbova11\b|\bbolsa\b(?! de (cripto|bitcoin))` +
  r`|\bstocks?\b(?![- ]to[- ]flow)|\bindices?\b(?! de (medo|dominancia))`
// "bitcoin na bolsa", "ETF de bitcoin na bolsa": a bolsa como lugar da cripto, igual à B3. Também a escolha do lugar
// ("corretora ou bolsa, onde compro bitcoin?", "bolsa ou exchange?") e o "fundo de índice" (o ETF), que não são o Ibovespa.
const LUGAR_DITO = r`\b(cripto\w*|bitcoins?|btc|ethereum|eth|hash11|etfs?|futuros?)( de \w+)? (na|pela|da|via) (bolsa|b3)\b` +
  r`|\b(corretora|exchange|direto) (ou|vs|x|versus) (a |na |pela )?bolsa\b` +
  r`|\bbolsa (ou|vs|x|versus) (a |o |na |no |pela |pelo )?(corretora|exchange|direto)\b` +
  r`|\b(fundos?|etfs?) de indices?\b`
const TARIFA_DITA = r`\btarifa(s|co|cos|sso)?\b|\bsobretaxa\w*|\btaxac\w* (d[aoe]s?) (trump|eua|estados unidos)\b` +
  r`|\btaxac\w* (do )?trump\b|\btaxac\w* americana\b(?![^.?!]{0,40}\b(dividend|stock|aco|renda)\w*)` +
  r`|\bsanc(ao|oes)\b|\bguerra comercial\b`
const ACAO_DITA = r`\b(petrobras|petr[34]|prio3?|petroleiras?|acao|acoes)\b`
const PETROLEO_DITO = r`\b(petroleo|brent|wti|barril|opep|opec|ormuz|combustive(l|is)|gasolina|diesel)\b`
const COMBUSTIVEL_DITO = r`\b(gasolina|diesel|etanol|combustive(l|is)|bomba|posto|litro|reajust\w*|ipca|inflacao|defasa\w*|paridade` +
  r`|politica de preco\w*)\b`
// "declarar" e "declaração" (não "declarou", nem "declarar guerra"); o "IR" dito com verbo ou preposição ("bitcoin paga IR?",
// "o IR da cripto"), sem "de ir" ("é hora de ir pro bitcoin?").
const DECLARACAO_DITA = r`\bdeclar(ar|o|a|as|amos|ei|ando|ado|ados|acao|acoes)\b(?! guerra\b)|\bbens e direitos\b`
// "quanto pago de IR no ETF?", "IR no ETF de bitcoin", "IR de cripto"; sem "ir no/na + cripto", que é o verbo
// ("posso ir no bitcoin?")
const IMPOSTO_DITO = r`\bimpost\w*|` +
  DECLARACAO_DITA +
  r`|\birpf?\b|\bdarf\b|\bleao\b|\btribut\w*|\bisen\w*` +
  r`|\b(paga|pagar|pago|pagam|pagou|pagando|cobra|cobram|cobrar|incide|tem|o|do|no) ir\b` +
  r`|\b(pag\w*|quanto|qnt|qto|qnto) de ir\b` +
  r`|\bir (da|do|de|sobre|em|no|na|nos|nas) (etfs?|hash11|cotas?|futuros?)\b` +
  r`|\bir (da|do|de|sobre|em) (cripto\w*|bitcoins?|btc|ether|eth)\b`
const FUTURO_CRIPTO = r`\bfuturos? (de|do) (bitcoins?|btc|cripto\w*|ether|ethereum|eth)\b` +
  r`|\b(bitcoins?|btc|cripto\w*|ether|ethereum|eth) futuros?\b`
// O "o que é" do próprio termo do tema ("o que é halving?", "me explica o halving", "halving, o que é?").
const TERMO_CRIPTO = r`(halvings?|stablecoins?|usdt|usdc|tether|etfs?|hash11|ftx|fundos? de indice)`
const CONCEITO_CRIPTO = r`\bo que (e|sao|significa|foi|quer dizer) (o |a |os |as |um |uma )?${TERMO_CRIPTO}` +
  r`\b|\bme explica\w* (o |a |os |as )?${TERMO_CRIPTO}\b|\b${TERMO_CRIPTO}` +
  r`\b\W+o que (e|significa)\b|\bcomo funciona (o |a |os |as )?${TERMO_CRIPTO}\b`
// A pergunta fala da defasagem do preço da Petrobras, que o repertório não calcula: dizer isso no topo (D8).
const DEFASAGEM_DITA = r`\bdefasa\w*|\bparidade\b|\babaixo do preco internacional\b`
// Pergunta de preço ou de movimento de cripto: o repertório não tem a cotação.
// Também o gerúndio, o plural, os sinônimos e o internetês ("tá caindo?", "despencou?", "as criptos caíram?", "qnt tá?").
// "qual o valor do bitcoin?", "vale quanto?", "quanto é?", "afundou?", "tombou?", "recuou?", "dumpando?"
const PRECO_CRIPTO = r`\b((quanto|qnt|qto|qnto) (ta|esta|vale|custa)|preco|cotacao|caiu|cairam|subiu|subiram|cai|caem|sobe` +
  r`|sobem|caindo|subindo|em (alta|queda|baixa)|despenc\w*|desab\w*|derret\w*|dispar\w*|reagiu|valoriz\w*` +
  r`|desvaloriz\w*|(qual|quale) (o )?valor|(vale|valendo|ta|esta|e) quanto|quanto e|afund\w*|tomb\w*|recu\w*` +
  r`|dump\w*)\b|\bo que (aconteceu|houve|rolou) com (o |os |a |as )?(bitcoins?|btc|cripto\w*|ether(eum)?|eth` +
  r`|solana)\b`
// O mercado da pergunta e a série que mede o caminho dele (MEDIDO do Python).
const MEDIDO: Readonly<Record<string, string>> = { mini_indice: 'ibovespa', mini_dolar: 'dolar', petroleo: 'brent' }
const T = BASE.textos
const PEDEM_RECUSA = new Set(T.PEDEM_RECUSA)
const MEDIDOS = ['ibovespa', 'dolar', 'juros']

export type Resposta = {
  pergunta: string
  pedido: Pedido
  curta: string[]
  blocos: Bloco[]
  abertura: string[]
  texto: string
  texto_curto: string
  fatos: string
  modo: string
  violacoes: Violacao[]
}

const algum = (lista: string[], conjunto: Iterable<string>) => {
  const s = new Set(conjunto)
  return lista.some((x) => s.has(x))
}
const mesmaFonte = (a: Fonte, b: Fonte) => a.nome === b.nome && a.url === b.url
const copia = (b: Bloco): Bloco => ({ ...b, linhas: b.linhas.map((l) => ({ ...l, fontes: [...l.fontes] })), limites: [...b.limites] })

/** Os mercados medidos (Ibovespa, dólar, juros) na ordem em que a pergunta cita; todos, se nenhum (fatos._mercados_medidos). */
export function mercadosMedidos(mercados: string[]): string[] {
  const alvo: string[] = []
  for (const bruto of mercados) {
    const m = ({ mini_indice: 'ibovespa', mini_dolar: 'dolar' } as Record<string, string>)[bruto] ?? bruto
    if (MEDIDOS.includes(m) && !alvo.includes(m)) alvo.push(m)
  }
  return alvo.length ? alvo : [...MEDIDOS]
}

function eleicoes(mercados: string[]): Bloco {
  const b = copia(BASE.eleicoes[mercadosMedidos(mercados).join(',')])
  if (algum(['cripto', 'memecoin'], mercados)) b.limites.push(T.LIMITE_CRIPTO_ELEICAO)
  return b
}

function copom(mercados: string[]): Bloco {
  return copia(BASE.copom[mercados.length ? mercadosMedidos(mercados).join(',') : ''])
}

/** Os dígitos de f'{x:.{casas}f}' do Python, para x >= 0: o valor binário exato, arredondado com empate para o par. */
function fixo(x: number, casas: number): string {
  if (!Number.isFinite(x)) return Number.isNaN(x) ? 'nan' : 'inf'
  // A partir de 1e21 o toFixed vira notação científica; aí o double já é inteiro, e o BigInt dá os dígitos exatos.
  if (x >= 1e21) return BigInt(x).toString() + (casas ? '.' + '0'.repeat(casas) : '')
  const s = x.toFixed(casas)
  // O toFixed arredonda o valor exato, como o Python, mas desempata para cima (2.5 → "3"), e o Python para o par
  // ("2"). Só há empate quando a expansão exata acaba num 5 logo depois da última casa; toFixed(100) é exato para
  // todo x >= 2^-48, e abaixo disso não há empate com até 15 casas.
  const [inteiro, frac] = x.toFixed(100).split('.')
  if (frac[casas] !== '5' || !/^0*$/.test(frac.slice(casas + 1))) return s
  const truncado = casas ? `${inteiro}.${frac.slice(0, casas)}` : inteiro
  return Number(truncado.at(-1)) % 2 === 0 ? truncado : s
}

/** Número no formato brasileiro, como fatos.num do Python. */
export function num(x: number, casas = 1): string {
  const s = fixo(Math.abs(x), casas)
  const [inteiro, frac] = s.split('.')
  const milhar = inteiro.replace(/\B(?=(\d{3})+(?!\d))/g, '.')
  const texto = frac ? `${milhar},${frac}` : milhar
  return (x < 0 && Number(s) !== 0 ? '−' : '') + texto
}

/** As datas marcadas de hoje (AAAA-MM-DD) em diante, a primeira de cada tipo, numa linha só (fatos.calendario). */
function calendario(mercado: string, hoje: string): Bloco | null {
  const c = BASE.calendario
  const vistos = new Set<string>()
  const curtos: string[] = []
  const fontes: Fonte[] = []
  for (const item of BASE.agenda[mercado] ?? []) {
    if (item.data < hoje || vistos.has(item.tipo)) continue
    vistos.add(item.tipo)
    curtos.push(item.curto)
    for (const f of item.fontes) if (!fontes.some((x) => mesmaFonte(x, f))) fontes.push(f)
  }
  if (!curtos.length) return null
  return {
    titulo: c.titulo,
    linhas: [{ texto: c.linha_inicio + curtos.join(' e ') + c.linha_fim, fontes }],
    resumo: c.resumo_inicio + curtos.join(' e ') + c.resumo_fim,
    limites: [],
  }
}

/** O dia de hoje no horário de Brasília, AAAA-MM-DD. */
export function hojeEmBrasilia(): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Sao_Paulo' }).format(new Date())
}

/** fatos.dia do Python para uma data AAAA-MM-DD: DD/MM/AAAA. */
function dia(d: string): string {
  const [a, m, dd] = d.split('-')
  return `${dd}/${m}/${a}`
}

/** fatos._qtd: a quantia que a pessoa contou, inteira sem casas, quebrada com 2 ("0,50 euro" não vira "0 euros"). */
function qtd(v: number): string {
  return Number.isInteger(v) ? num(v, 0) : num(v, 2)
}

/** fatos._reais: real da conta sem centavos a partir de R$ 1.000; abaixo disso, com centavos ("R$ 2,82", não "R$ 3"). */
function reais(v: number): string {
  return Math.abs(v) >= 1000 ? num(v, 0) : num(v, 2)
}

/** fatos._meses: meses inteiros, sem arredondar para cima, e os anos exatos quando passa de 2: "35 meses (2 anos e 11
 * meses)". */
export function meses(m: number): string {
  // int() e divmod() do Python em inteiro de verdade: com BigInt, o piso e a divisão saem exatos em qualquer tamanho.
  const n = BigInt(Math.trunc(m))
  if (n < 1n) return 'menos de 1 mês'
  let txt = `${num(Number(n), 0)} ${n === 1n ? 'mês' : 'meses'}`
  if (n >= 24n) {
    const [anos, resto] = [n / 12n, n % 12n] // n > 0: a divisão do BigInt é o piso, como o divmod
    txt += ` (${num(Number(anos), 0)} anos` + (resto ? ` e ${resto} ${resto === 1n ? 'mês' : 'meses'}` : '') + ')'
  }
  return txt
}

/** fatos.conta_cambio do Python (P4 de câmbio): o dinheiro em moeda estrangeira que a pessoa contou, em reais, pela
 * cotação oficial. Só a conta, sem dizer o que fazer, quando trocar nem quanto (N1, N4, N5). `gasto`: o gasto por mês
 * que ela contou, em reais, na própria moeda ou em outra moeda estrangeira (convertido pela cotação oficial dela, `cg`).
 * `c` e `cg`: as cotações (as da base, se faltarem). */
export function contaCambio(valor: number, moeda: string, gasto: number | null = null, gastoMoeda: string | null = null,
  c: Cotacoes = BASE.cambio.cotacoes[moeda], cg?: Cotacoes): Bloco {
  const { nome, plural, fonte } = BASE.cambio.moedas[moeda]
  const hojeR = valor * c.valor
  const anoR = valor * c.ano_valor
  const linhas: Linha[] = []
  const add = (texto: string, ...fontes: Fonte[]) => linhas.push({ texto, fontes })
  add(`${qtd(valor)} ${plural} × R$ ${num(c.valor, 4)} (cotação oficial do ${nome} em ${dia(c.data)}) = ` +
    `R$ ${reais(hojeR)}.`, fonte)
  add(`Cada R$ 0,10 de diferença na cotação do ${nome} muda esse valor em R$ ${reais(valor * 0.1)}.`, fonte)
  const dif = anoR - hojeR
  add(`No fim de ${c.ano_data.slice(0, 4)} (${dia(c.ano_data)}), 1 ${nome} valia R$ ${num(c.ano_valor, 4)}: os mesmos ` +
    `${qtd(valor)} ${plural} davam R$ ${reais(anoR)}, ` +
    (!['0', '0,00'].includes(reais(Math.abs(dif))) ? `R$ ${reais(Math.abs(dif))} ${dif > 0 ? 'a mais' : 'a menos'} do que hoje.`
      : 'o mesmo que hoje.'),
    fonte)
  add(`Nos últimos 12 meses, 1 ${nome} foi de R$ ${num(c.min_valor, 4)} (${dia(c.min_data)}) a ` +
    `R$ ${num(c.max_valor, 4)} (${dia(c.max_data)}): nesses dois extremos, os mesmos ${plural} dariam de ` +
    `R$ ${reais(valor * c.min_valor)} a R$ ${reais(valor * c.max_valor)}.`, fonte)
  let cobre = ''
  if (gasto) {
    let m: number
    let gastoTxt: string
    if (gastoMoeda === moeda) {
      gastoTxt = `${qtd(gasto)} ${plural}`
      m = valor / gasto
      add(`Com gasto de ${gastoTxt} por mês, os ${qtd(valor)} ${plural} cobrem ${meses(m)}, sem contar ` +
        'rendimento, imposto nem custo da troca.')
    } else {
      let gastoR: number
      let abre: string
      let fontesG: Fonte[]
      const outra = gastoMoeda === null ? undefined : BASE.cambio.moedas[gastoMoeda]
      if (outra) {
        // outra moeda estrangeira: o gasto vira real pela cotação oficial dela
        const cotG = cg ?? BASE.cambio.cotacoes[gastoMoeda as string]
        gastoR = gasto * cotG.valor
        gastoTxt = `${qtd(gasto)} ${outra.plural}`
        abre = `Com gasto de ${gastoTxt} por mês (R$ ${reais(gastoR)} pela cotação oficial do ${outra.nome} em ` +
          `${dia(cotG.data)})`
        fontesG = [fonte, outra.fonte]
      } else {
        gastoR = gasto
        gastoTxt = `R$ ${qtd(gasto)}`
        abre = `Com gasto de ${gastoTxt} por mês`
        fontesG = [fonte]
      }
      m = hojeR / gastoR
      add(`${abre}, R$ ${reais(hojeR)} cobrem ${meses(m)}, sem contar rendimento, imposto nem custo da troca. ` +
        `Com o ${nome} na menor cotação dos 12 meses, seriam ${meses(valor * c.min_valor / gastoR)}; na maior, ` +
        `${meses(valor * c.max_valor / gastoR)}.`, ...fontesG)
    }
    cobre = `; com gasto de ${gastoTxt} por mês, cobrem ${meses(m)}`
  }
  add('É só a conta com os números que você contou: não diz o que fazer com o dinheiro, nem quando trocar, nem quanto.')
  const limite = BASE.cambio.limite_euro
  return {
    titulo: BASE.cambio.titulo,
    linhas,
    resumo: `Pela cotação oficial de ${dia(c.data)}, seus ${qtd(valor)} ${plural} equivalem a R$ ${reais(hojeR)}; na ` +
      'troca de verdade entram a tarifa e o spread do banco ou do app. Cada R$ 0,10 de diferença no ' +
      `${nome} muda isso em R$ ${reais(valor * 0.1)}${cobre}.`,
    // str.replace do Python troca todas as ocorrências: replaceAll
    limites: [moeda !== 'euro' ? limite.replaceAll('do euro', `do ${nome}`) : limite],
  }
}

function conta(pontos: number, contratos: number, chave: string): Bloco {
  const c = BASE.conta[chave]
  const total = pontos * c.valor * contratos
  return {
    titulo: 'A conta, com os números que você escolheu (P4)',
    linhas: [{
      texto: `${num(pontos, 0)} pontos × R$ ${num(c.valor, 2)} × ${contratos} contrato(s) de ${c.nome} = R$ ${num(total, 2)}, ` +
        'para ganho ou para perda. É só a conta: não diz se isso faz sentido para você.',
      fontes: [c.fonte],
    }],
    resumo: `${num(pontos, 0)} pontos no ${c.nome} valem R$ ${num(total, 2)} com ${contratos} contrato(s), para ganho ou para perda.`,
    limites: [],
  }
}

// O começo do título do bloco do Focus (fatos.TITULO_EXPECTATIVAS).
const TITULO_EXPECTATIVAS = 'O que o mercado espera'
// fatos.euro_sem_estudo: um texto fixo, sem fonte, que o base.json não traz pronto.
const EURO_SEM_ESTUDO = 'O estudo do Copom e da linha do tempo mede o dólar (a cotação oficial do Banco Central), não o euro: ' +
  'os números de câmbio abaixo são do dólar.'

/** fatos.expectativas, pronto na base: '' (nenhum mercado medido), dólar, euro, juros, Ibovespa ou Brent (este igual ao
 * de '': o Focus não pergunta pelo petróleo; só entra em pergunta de petróleo com Copom ou economia). */
function expectativas(mercado: string): Bloco {
  return copia(BASE.expectativas[mercado])
}

function euroSemEstudo(): Bloco {
  return { titulo: 'Sobre o euro', linhas: [{ texto: EURO_SEM_ESTUDO, fontes: [] }], resumo: '', limites: [] }
}

/** _medidos_cambio do Python: os mercados para os blocos medidos (eleições, Copom). Em pergunta de câmbio, o dólar vem
 * primeiro e o euro sai (ele tem bloco próprio). */
function medidosCambio(p: Pedido): string[] {
  if (!ehCambio(p)) return p.mercados
  return ['dolar', ...p.mercados.filter((m) => m !== 'dolar' && m !== 'euro')]
}

export function escolherBlocos(p: Pedido, hoje: string): Bloco[] {
  let blocos: (Bloco | null)[] = []
  const pedeDinheiro = p.proibidos.includes('chance_dinheiro')
  const medidosDoCambio = medidosCambio(p)
  if (ehEleicao(p)) {
    blocos.push(BASE.candidatos && copia(BASE.candidatos), copia(BASE.economia), eleicoes(medidosDoCambio),
      BASE.pesquisas && copia(BASE.pesquisas))
  }
  if (p.temas.includes('copom')) {
    if (!ehEleicao(p)) blocos.push(copia(BASE.economia))
    blocos.push(copom(medidosDoCambio))
  }
  // Em pergunta de petróleo, guerra e choque externo vêm pelo bloco do petróleo, que mede também o Brent, quando ele cobre
  // o assunto: tarifa, sanção e guerra comercial não são guerra do petróleo, e ficam na linha do tempo.
  const t = normalizar(p.pergunta)
  const temasPetroleo = p.mercados.includes('petroleo') ? temaPetroleo(t) : []
  const coberto: Record<string, boolean> = {
    geopolitico: temasPetroleo.includes('guerra') && !search(TARIFA_DITA, t),
    choque_externo: temasPetroleo.includes('choque'),
  }
  const tipos = BASE.tipos.filter((x) => p.temas.includes(x) && !coberto[x])
  for (const tipo of tipos) blocos.push(copia(BASE.eventos[tipo]))
  const temEconomia = () => blocos.some((b) => b && b.titulo.startsWith('A economia hoje'))
  if (p.temas.includes('economia') && !temEconomia()) blocos.unshift(copia(BASE.economia))
  // Pedido de direção sobre um mercado sem evento no repertório ("é topo?", "qual o viés?"): ao menos o nível de hoje.
  if (p.mercados.length && algum(p.proibidos, PEDEM_RECUSA) && !temEconomia()) blocos.unshift(copia(BASE.economia))
  // Mercado sem evento no repertório ("devo comprar dólar?", "como está o Ibovespa?"): o caminho que ele já fez, o que o
  // mercado espera (Focus, atribuído) e as datas marcadas que já mexeram com ele.
  // A linha do tempo que fica numa pergunta de petróleo não tira o caminho do Brent nem os dois lados.
  const temEvento = ehEleicao(p) || p.temas.includes('copom') ||
    tipos.some((x) => !(x in coberto) || !p.mercados.includes('petroleo'))
  const medidos: string[] = []
  for (const m of p.mercados) {
    const alvo = MEDIDO[m] ?? m
    if (BASE.historico[alvo] && !medidos.includes(alvo)) medidos.push(alvo)
  }
  // "ETF de bitcoin na B3", "bitcoin na bolsa": a B3 é o lugar da cripto, não o Ibovespa. Sem caminho nem dois lados do
  // índice. "Bitcoin ou bolsa?", "bitcoin ou WIN?" citam o índice: os dois mercados.
  const b3SoLugar = p.mercados.includes('cripto') && !p.mercados.includes('mini_indice') &&
    !search(IBOV_DITO, sub(LUGAR_DITO, ' ', t))
  if (b3SoLugar) tirarTodos(medidos, 'ibovespa')
  // "10 mil dólares em bitcoin": o dólar é a unidade do valor, não o mercado da pergunta (como no petróleo, no roteador).
  // O mini-dólar (WDO) mede o dólar de verdade.
  // O dólar em stablecoin ("10 mil dólares em USDT") e a conversão ("quanto dá em reais?") ficam: a cotação é a resposta.
  if (p.mercados.includes('cripto') && !p.mercados.includes('mini_dolar') && !search(MERCADOS.dolar, sub(PRECO_EM_DOLAR, ' ', t)) &&
    !search(r`\b(usdt|usdc|tether|stablecoins?)\b|\b(em|pra|para) reais\b|\bquanto (da|vale|valem|e)\b`, t)) {
    tirarTodos(medidos, 'dolar')
  }
  if (!temEvento && medidos.length) {
    for (const m of medidos) blocos.push(copia(BASE.historico[m]))
    // Quem pede o que fazer ou para onde vai recebe os dois lados do que já aconteceu, não uma recomendação. Em contrato
    // (WIN, WDO) não: o lado que importa é a taxa-base da FGV, que precisa caber nas 3 linhas.
    if (algum(['dica', 'direcao', 'momento'], p.proibidos) && !algum(['mini_indice', 'mini_dolar'], p.mercados)) {
      // de cada mercado citado, não só do primeiro
      for (const m of medidos) {
        const lados = BASE.dois_lados[m]
        blocos.push(lados ? copia(lados) : null)
      }
    }
    // O Focus não pergunta pelo petróleo. Sem o Brent, a expectativa vai para o outro mercado medido; só com o Brent e
    // pergunta de economia (inflação, IPCA, PIB), vai a do tema.
    const alvo = medidos.find((x) => x !== 'brent') ?? (p.temas.includes('economia') ? '' : null)
    blocos.push(alvo !== null ? expectativas(alvo) : null, calendario(medidos[0], hoje))
  } else if (p.temas.includes('economia') || p.temas.includes('copom')) {
    blocos.push(expectativas(medidos.length ? medidos[0] : ''))
  }
  if (p.mercados.includes('memecoin')) blocos.push(copia(BASE.memecoins))
  if (p.mercados.includes('previsao')) blocos.push(copia(BASE.previsao))
  if (p.proibidos.includes('binaria')) blocos.push(copia(BASE.binaria))
  if (temConta(p)) blocos.push(conta(p.pontos as number, p.contratos, p.mercados.includes('mini_indice') ? 'mini_indice' : 'mini_dolar'))
  let eventosPetroleoNaResposta = false // o estudo dos eventos de petróleo também mede o dólar, não o euro
  for (const m of p.mercados) {
    // contrato (WIN) ou cripto na B3: a regra de IR das ações à vista não vale
    if (m === 'ibovespa' && (p.mercados.includes('mini_indice') || b3SoLugar)) continue
    const b = BASE.mercado[m]
    blocos.push(b ? copia(b) : null)
    // Petróleo: não há bloco de mercado (o fatos.mercado do Python devolve None). Quem cita só a ação ("vale a pena
    // PETR4?", "PETR4 ou PRIO3?") não recebe a história de um emissor (Res. CVM 20): os eventos entram quando a pergunta
    // cita o fato ou o petróleo. Do barril à bomba, quando ela fala de combustível, ou do petróleo sem tema.
    // Com pedido de dica, direção, momento ou ranking que cita a ação ("compro PETR4 antes do dividendo extraordinário?"), ou
    // com escolha entre ativos ("petróleo ou dólar, qual é melhor?"), os eventos da Petrobras não entram nem com o fato
    // citado: ficam os do petróleo, quando a pergunta cita o petróleo (Mapa legal, seção 8, item 10).
    if (m === 'petroleo') {
      let temasEv = temasPetroleo
      if (algum(p.proibidos, PEDEM_RECUSA) && (search(ACAO_DITA, t) || algum(['ranking', 'comparar'], p.proibidos))) {
        const semEmissor = (ts: string[]) => ts.filter((x) => x !== 'petrobras')
        temasEv = semEmissor(temasPetroleo)
        if (!temasEv.length) {
          temasEv = search(PETROLEO_DITO, t) || !search(ACAO_DITA, t) ? semEmissor(Object.keys(BASE.petroleo.temas)) : []
        }
      }
      const soAcao = !temasEv.length && Boolean(search(ACAO_DITA, t)) && !search(PETROLEO_DITO, t)
      if (!soAcao) {
        blocos.push(eventosPetroleo(temasEv))
        eventosPetroleoNaResposta = true
      }
      if (search(COMBUSTIVEL_DITO, t) || (!temasPetroleo.length && !soAcao)) blocos.push(copia(BASE.petroleo.barril))
    }
    if (m === 'cripto') {
      // Regras, imposto, riscos e a linha do tempo. Tema citado (halving, FTX, ETF...): a linha do tempo antes das regras,
      // com a definição primeiro se a pessoa perguntou "o que é". Pergunta de imposto: o imposto primeiro (o blocos[-1:-1]
      // do Python: logo antes do último, que é o das regras). O `t` é a pergunta normalizada, a mesma do começo.
      let tema = temaCripto(t)
      // Quem escolhe ou avalia uma corretora pelo nome não recebe a história de uma delas no topo (N7): a linha do tempo
      // inteira vai para o fim, como em qualquer pergunta de cripto sem tema.
      if (tema === 'binance' && p.proibidos.includes('plataforma')) tema = ''
      // Pergunta de imposto do ETF ou do futuro: o resumo diz que a isenção de R$ 35 mil não vale para eles; de declaração:
      // quem declara e como. O que o celular mostra primeiro não pode omitir isso (CDC, art. 37, §3º).
      const impostoDito = Boolean(search(IMPOSTO_DITO, t))
      const variante = impostoDito && (tema === 'etf' || search(FUTURO_CRIPTO, t))
        ? 'etf'
        : search(DECLARACAO_DITA, t) ? 'declaracao' : ''
      const imposto = copia(variante === 'etf'
        ? BASE.cripto.imposto_etf
        : variante === 'declaracao' ? BASE.cripto.imposto_declaracao : BASE.cripto.imposto)
      const riscos = copia(BASE.cripto.riscos)
      if (impostoDito) {
        blocos.splice(blocos.length - 1, 0, imposto)
        blocos.push(riscos)
      } else {
        blocos.push(imposto, riscos)
      }
      if (tema) {
        // em pergunta de imposto, a linha do tempo vem depois do imposto; a definição só vira a 1ª linha quando o "o que
        // é" é do próprio termo ("o que é a lei das stablecoins nos EUA?" quer a lei, não a stablecoin)
        const antes = impostoDito ? [BASE.titulo_cripto] : [BASE.titulo_cripto, imposto.titulo]
        const i = blocos.findIndex((x) => x !== null && antes.includes(x.titulo))
        if (i < 0) throw new Error('sem o bloco das regras nem o do imposto') // o next() do Python levantaria StopIteration
        // com um marco depois do termo ("o que é o ETF de bitcoin aprovado pela SEC?", "... nos EUA?", "de 2024?"), o
        // marco fica nas 3 linhas, e não a definição brasileira
        const conceito = p.temas.includes('conceito') && Boolean(search(CONCEITO_CRIPTO, t)) &&
          !search(r`\b${TERMO_CRIPTO}\b[^?]*\b(aprovad\w*|sec|eua|estados unidos|genius|lei|20\d\d)\b`, t)
        blocos.splice(i, 0, criptoMarcos(tema, conceito))
      } else {
        blocos.push(copia(BASE.cripto.marcos['']))
      }
    }
  }
  if (pedeDinheiro || algum(BASE.derivativos.slice(0, 2), p.mercados)) blocos.push(copia(BASE.fgv))
  // O estudo do Copom, da linha do tempo e dos eventos de petróleo mede o dólar, não o euro: dizer isso, em vez de
  // responder só com o dólar.
  if (p.mercados.includes('euro') &&
    (p.temas.includes('copom') || BASE.tipos.some((x) => p.temas.includes(x)) || eventosPetroleoNaResposta)) {
    blocos.push(euroSemEstudo())
  }
  blocos = blocos.filter((b) => b)
  if (ehCambio(p)) blocos = cambioPrimeiro(p, blocos as Bloco[])
  // em pergunta de câmbio ("exchange my euros"), o câmbio continua na frente
  else if (p.mercados.includes('cripto')) blocos = criptoPrimeiro(blocos as Bloco[])
  // A linha do pedido promete a taxa-base da FGV "logo abaixo": ela vai em 2º, depois de qualquer reordenamento.
  if (pedeDinheiro) {
    const fgv = (blocos as Bloco[]).find((b) => b.titulo === BASE.fgv.titulo)
    if (fgv) {
      blocos = blocos.filter((b) => b!.titulo !== BASE.fgv.titulo)
      blocos.splice(Math.min(1, blocos.length), 0, fgv)
    }
  }
  if (!blocos.length) blocos.push(copia(BASE.economia))
  return blocos as Bloco[]
}

/** fatos.tema_petroleo: todos os temas dos eventos de petróleo que a pergunta (já normalizada) cita, na ordem do JSON
 * ("a OPEP e a guerra": os dois); nenhum, se ela não cita. */
export function temaPetroleo(perguntaNormalizada: string): string[] {
  return TEMAS_PETROLEO.filter(([, padrao]) => search(padrao, perguntaNormalizada)).map(([tema]) => tema)
}

/** fatos.petroleo_eventos(temas), montado da base: as linhas dos eventos do bloco (cada uma guardada uma vez só, em
 * `linhas`) e depois as do próprio bloco (a faixa e a taxa-base). A chave é '+'.join(temas), como no exportar. */
function eventosPetroleo(temas: string[]): Bloco {
  const { linhas, blocos } = BASE.petroleo.eventos
  const { eventos, ...b } = blocos[temas.join('+')]
  return copia({ ...b, linhas: [...eventos.map((i) => linhas[i]), ...b.linhas] })
}

/** fatos.tema_cripto: o 1º tema da linha do tempo que a pergunta (já normalizada) cita ('halving', 'ftx'...), ou ''. */
export function temaCripto(perguntaNormalizada: string): string {
  return TEMAS_CRIPTO.find(([, padrao]) => search(padrao, perguntaNormalizada))?.[0] ?? ''
}

/** fatos.cripto_marcos(tema, conceito): os marcos do tema, prontos na base. `conceito` (a pessoa perguntou "o que é...")
 * ou o tema da FTX: a definição do tema, quando há, vira o resumo. Ela é a 1ª linha do bloco, e a única que não está na
 * linha do tempo inteira. */
function criptoMarcos(tema: string, conceito: boolean): Bloco {
  const b = copia(BASE.cripto.marcos[tema])
  const definicao = b.linhas.length && !MARCOS_DATADOS.has(b.linhas[0].texto) ? b.linhas[0].texto : null
  if (definicao && (conceito || tema === 'ftx')) b.resumo = definicao
  return b
}

/** _cripto_primeiro do Python. Pergunta que cita cripto: os blocos de cripto na frente ("ETF de bitcoin na B3" fala de
 * cripto, não do nível do Ibovespa), na ordem em que já estavam. A taxa-base da FGV, quando há ("dá pra ficar rico?"),
 * logo depois do 1º. */
function criptoPrimeiro(blocos: Bloco[]): Bloco[] {
  const eh = (b: Bloco) => BASE.cripto.titulos.includes(b.titulo)
  const ehFgv = (b: Bloco) => b.titulo === BASE.fgv.titulo
  const cripto = blocos.filter(eh)
  return [...cripto.slice(0, 1), ...blocos.filter(ehFgv), ...cripto.slice(1), ...blocos.filter((b) => !eh(b) && !ehFgv(b))]
}

/** list.remove de todas as ocorrências, no lugar. */
function tirarTodos(xs: string[], x: string): void {
  for (let i = xs.indexOf(x); i >= 0; i = xs.indexOf(x)) xs.splice(i, 1)
}

/** _cambio_primeiro do Python. Pergunta de câmbio: na frente, a conta com os números da pessoa; com eleição, o euro nos
 * turnos e o que o mercado espera para o dólar; sem eleição, o caminho do euro e o que o mercado espera. O resto segue na
 * ordem de antes, sem a expectativa de outro mercado (a da Selic, numa pergunta de euro e bolsa). */
function cambioPrimeiro(p: Pedido, blocos: Bloco[]): Bloco[] {
  const euro = p.mercados.includes('euro')
  const expectativa = expectativas(euro ? 'euro' : 'dolar')
  const frente: Bloco[] = []
  if (temContaCambio(p)) {
    frente.push(contaCambio(p.valor_moeda as number, p.moeda as string, p.gasto_mensal, p.gasto_moeda))
  }
  if (euro && ehEleicao(p)) frente.push(copia(BASE.euro_turnos), expectativa, copia(BASE.historico.euro))
  else if (euro) frente.push(copia(BASE.historico.euro), expectativa)
  else frente.push(expectativa)
  const vistos = new Set(frente.map((b) => b.titulo))
  return [...frente, ...blocos.filter((b) => !vistos.has(b.titulo) && !b.titulo.startsWith(TITULO_EXPECTATIVAS))]
}

function abertura(p: Pedido, achouRepertorio: boolean): string[] {
  const linhas: string[] = []
  const recusa = algum(p.proibidos, PEDEM_RECUSA)
  if (recusa) linhas.push(T.RECUSA)
  for (const [codigo, texto] of Object.entries(T.POR_PEDIDO)) {
    // a RECUSA já diz que não dá direção
    if (p.proibidos.includes(codigo) && !(recusa && codigo === 'direcao')) linhas.push(texto)
  }
  if (p.mercados.includes('memecoin') && algum(p.proibidos, PEDEM_RECUSA) && !p.proibidos.includes('plataforma')) {
    linhas.push(T.POR_PEDIDO.plataforma)
  }
  if (p.mercados.includes('cripto') && search(PRECO_CRIPTO, normalizar(p.pergunta))) linhas.push(T.SEM_PRECO_CRIPTO)
  if (p.mercados.includes('petroleo') && search(DEFASAGEM_DITA, normalizar(p.pergunta))) linhas.push(T.SEM_DEFASAGEM)
  if (p.voto_informado) linhas.push(T.VOTO_INFORMADO)
  if (!achouRepertorio) linhas.push(T.SEM_REPERTORIO)
  return linhas
}

/** Até 3 linhas do que dá para saber. A recusa e a linha de cada pedido ficam no topo, antes delas. */
function curta(blocos: Bloco[], abertura: string[]): string[] {
  const linhas: string[] = []
  if (abertura.includes(T.SEM_REPERTORIO)) {
    linhas.push('Não achei caso parecido no repertório; ele mostra o que já aconteceu, e abaixo está o que cobre.')
  }
  // Por último: as datas marcadas e o último dado da economia. Primeiro o que aconteceu e o que o mercado espera.
  const peso = (r: string) => r.startsWith(BASE.resumo_hoje) ? 2 : r.startsWith(BASE.calendario.resumo_inicio) ? 1 : 0
  const resumos = blocos.map((b) => b.resumo).filter((r) => r)
  resumos.sort((a, b) => peso(a) - peso(b))
  return [...linhas, ...resumos].slice(0, 3)
}

// _contrato_de_juros do Python: 'juros' é o mercado de renda fixa, Selic e DI futuro; só o DI futuro é derivativo (D4).
const CONTRATO_DE_JUROS = CONTRATO + r`|\bfuturos?\b`

function avisos(r: Resposta): string[] {
  const lista: string[] = []
  const derivativo = algum(BASE.derivativos.slice(0, 2), r.pedido.mercados) ||
    (r.pedido.mercados.includes('juros') && Boolean(search(CONTRATO_DE_JUROS, normalizar(r.pergunta)))) ||
    r.blocos.some((b) => b.titulo === BASE.cripto.imposto.titulo) // ele cita o futuro de bitcoin
  if (derivativo || r.blocos.some((b) => b.titulo.startsWith('A taxa-base de quem faz day'))) {
    lista.push(r.pedido.mercados.includes('cripto') ? T.RISCO_DERIVATIVO_CRIPTO : T.RISCO_DERIVATIVO)
  }
  // o bloco da cripto já traz o D5: não repete
  if (algum(['cripto', 'memecoin'], r.pedido.mercados) && !r.blocos.some((b) => b.titulo === BASE.titulo_cripto)) {
    lista.push(T.RISCO_CRIPTO)
  }
  return lista
}

/** A guarda do D5 na versão curta (renderizar do Python): ela só leva as 3 linhas, então, se a pergunta fala de cripto e
 * nenhuma delas diz que não é valor mobiliário, o aviso de cripto entra mesmo que o bloco dele esteja no texto inteiro. */
export function avisosDoCurto(avisos: string[], mercados: string[], curta: string[]): string[] {
  const faltaD5 = !avisos.includes(T.RISCO_CRIPTO) && algum(['cripto', 'memecoin'], mercados) &&
    !curta.some((x) => x.includes('não é valor mobiliário'))
  return faltaD5 ? [...avisos, T.RISCO_CRIPTO] : avisos
}

/** O texto inteiro e a versão curta, com a mesma numeração de fontes. */
function renderizar(r: Resposta): [string, string] {
  const fontes: Fonte[] = []
  const ref = (f: Fonte) => {
    let i = fontes.findIndex((x) => mesmaFonte(x, f))
    if (i < 0) i = fontes.push(f) - 1
    return `[${i + 1}]`
  }
  // Topo, igual nas duas versões: o aviso, a recusa e a linha de cada pedido (capital, stop, ranking...), uma vez só.
  const topo = [T.AVISO]
  for (const x of r.abertura) if (x !== T.SEM_REPERTORIO) topo.push('', x)
  if (r.curta.length) {
    topo.push('', r.curta.length === 3 ? '**Em 3 linhas**' : '**Em resumo**', ...r.curta.map((x, i) => `${i + 1}. ${x}`))
  }
  const partes = [...topo]
  if (r.abertura.includes(T.SEM_REPERTORIO)) partes.push('', T.SEM_REPERTORIO)
  const limites: string[] = []
  for (const b of r.blocos) {
    partes.push('', `**${b.titulo}**`)
    for (const ln of b.linhas) {
      const refs = ln.fontes.map(ref).join('')
      partes.push(`- ${ln.texto}` + (refs ? ` ${refs}` : ''))
    }
    for (const x of b.limites) if (!limites.includes(x)) limites.push(x)
  }
  const av = avisos(r)
  if (av.length) partes.push('', '**Riscos deste mercado**', ...av.map((a) => `- ${a}`))
  if (limites.length) partes.push('', '**Limitações**', ...limites.map((x) => `- ${x}`))
  partes.push('', '**Fontes**')
  partes.push(...fontes.map((f, i) => `[${i + 1}] ${f.nome}` + (f.url ? `: ${f.url}` : '')))
  // Versão curta: as fontes das 3 linhas (até 4). Uma de cada linha por vez, na ordem das linhas, para nenhuma ficar
  // sem fonte; dentro de cada uma, primeiro as séries oficiais e as pesquisas (o arquivo do TSE é grande demais para o
  // celular).
  const oficial = (f: Fonte) => ['Banco Central', 'Ipeadata', 'Tesouro', 'Pesquisa', 'Chague'].some((p) => f.nome.startsWith(p))
  const porLinha: Fonte[][] = []
  for (const resumo of r.curta) {
    const b = r.blocos.find((x) => x.resumo && x.resumo === resumo)
    if (!b) continue
    const fs: Fonte[] = []
    for (const ln of b.linhas) {
      for (const f of ln.fontes) if (f.url && !fs.some((x) => mesmaFonte(x, f))) fs.push(f)
    }
    fs.sort((x, y) => Number(!oficial(x)) - Number(!oficial(y)))
    porLinha.push(fs)
  }
  const dasLinhas: Fonte[] = []
  for (let i = 0; i < Math.max(0, ...porLinha.map((fs) => fs.length)); i++) {
    for (const fs of porLinha) if (i < fs.length && !dasLinhas.some((x) => mesmaFonte(x, fs[i]))) dasLinhas.push(fs[i])
  }
  const curto = [...topo]
  const avCurto = avisosDoCurto(av, r.pedido.mercados, r.curta)
  if (avCurto.length) curto.push('', ...avCurto)
  if (dasLinhas.length) curto.push('', 'Fontes: ' + dasLinhas.slice(0, 4).map((f) => `${f.nome}: ${f.url}`).join(' · '))
  return [partes.join('\n'), curto.join('\n')]
}

/** O que a resposta pode citar: os blocos com as fontes, e os textos fixos (com os números deles). */
function fatosTexto(r: Resposta): string {
  const partes: string[] = []
  for (const b of r.blocos) {
    partes.push(`## ${b.titulo}`)
    for (const ln of b.linhas) {
      const fs = ln.fontes.map((f) => `${f.nome} ${f.url}`.trim()).join('; ') || 'nenhuma'
      partes.push(`- ${ln.texto} (fontes: ${fs})`)
    }
    if (b.limites.length) partes.push('Limitações: ' + b.limites.join(' '))
  }
  const fixos = [T.AVISO, T.RECUSA, T.FECHO, T.RISCO_DERIVATIVO, T.RISCO_CRIPTO, T.SEM_REPERTORIO, T.NORMAS, T.VOTO_INFORMADO,
    T.SEM_PRECO_CRIPTO, T.RISCO_DERIVATIVO_CRIPTO, T.SEM_DEFASAGEM,
    ...Object.values(T.POR_PEDIDO)]
  return [...partes, '## Textos fixos', ...fixos].join('\n')
}

/** A resposta inteira, sempre da base. `pedido` é a leitura já feita (palavras-chave somadas à da IA). */
/** A resposta inteira, sempre da base. `hoje` (AAAA-MM-DD, Brasília) decide quais datas marcadas ainda aparecem. */
export function montar(pergunta: string, pedido?: Pedido, hoje: string = hojeEmBrasilia()): Resposta {
  const p = pedido ?? analisar(pergunta)
  const temTema = Boolean(p.mercados.length || p.temas.length || p.candidatos.length || ehEleicao(p) ||
    algum(['binaria', 'chance_dinheiro'], p.proibidos))
  const blocos = escolherBlocos(p, hoje)
  const ab = abertura(p, temTema)
  const r: Resposta = {
    pergunta, pedido: p, curta: curta(blocos, ab), blocos, abertura: ab, texto: '', texto_curto: '', fatos: '', modo: 'sem IA',
    violacoes: [],
  }
  ;[r.texto, r.texto_curto] = renderizar(r)
  r.fatos = fatosTexto(r)
  r.violacoes = [...checar(r.texto, r.fatos),
    ...checar(r.texto_curto, r.fatos).filter((v) => v.regra !== 'D1' || !r.texto.includes('http'))]
  if (r.violacoes.length) {
    // Defeito de dado ou de modelo de texto: a pessoa recebe só os avisos e a recusa; o resto fica no registro.
    r.texto = r.texto_curto = [T.AVISO, T.SEGURA].join('\n\n')
  }
  return r
}

// Monta a resposta, sempre da base: tradução de agente/resposta.py. Os blocos de fatos vêm prontos de base.json
// (gerado por `python -m agente.exportar`); aqui só se escolhe, ordena, numera as fontes e passa pelo filtro.
import base from '../base.json' with { type: 'json' }
import { checar } from './filtro.ts'
import { analisar, CONTRATO, ehCambio, ehEleicao, normalizar, temConta, temContaCambio } from './roteador.ts'
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
// fatos.tema_cripto e fatos.tema_petroleo: as expressões do JSON, na ordem dele (a de inserção das chaves, que o
// JSON.parse mantém).
const TEMAS_CRIPTO = Object.entries(BASE.cripto.temas).map(([tema, padrao]) => [tema, new RegExp(padrao)] as const)
// As linhas da linha do tempo inteira (sem tema): a definição de um tema é a 1ª linha dele que não está nela.
const MARCOS_DATADOS = new Set(BASE.cripto.marcos[''].linhas.map((ln) => ln.texto))
// A pessoa falou do índice mesmo, e não só da B3 como lugar ("ETF de bitcoin na B3").
// Em pergunta de petróleo: tarifa, sanção e guerra comercial não são a guerra do petróleo; a ação dita sem o petróleo não
// recebe a história de um emissor; o combustível pede "do barril à bomba".
const TARIFA_DITA = /\btarifa\w*|\bsanc(ao|oes)\b|\bguerra comercial\b/
const ACAO_DITA = /\b(petrobras|petr[34]|prio3?|petroleiras?|acao|acoes)\b/
const PETROLEO_DITO = /\b(petroleo|brent|wti|barril|opep|opec|ormuz|combustive(l|is)|gasolina|diesel)\b/
const COMBUSTIVEL_DITO = new RegExp(String.raw`\b(gasolina|diesel|etanol|combustive(l|is)|bomba|posto|litro|reajust\w*|ipca|` +
  String.raw`inflacao|defasa\w*|paridade|politica de preco\w*)\b`)
const IBOV_DITO = /\bibov\w*|\bbovespa\b|\bacoes\b|\bacao\b|\bbova11\b/
const IMPOSTO_DITO = /\bimpost\w*|\bdeclar\w*|\birpf?\b|\bdarf\b|\bleao\b|\btribut\w*|\bisen\w*/
// Pergunta de preço ou de movimento de cripto: o repertório não tem a cotação.
const PRECO_CRIPTO = new RegExp(String.raw`\b(quanto (ta|esta|vale|custa)|preco|cotacao|caiu|subiu|cai|sobe|reagiu|valoriz\w*|` +
  String.raw`desvaloriz\w*)\b|\bo que aconteceu com o (bitcoin|btc|cripto)`)
const TEMAS_PETROLEO = Object.entries(BASE.petroleo.temas).map(([tema, padrao]) => [tema, new RegExp(padrao)] as const)
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
    geopolitico: temasPetroleo.includes('guerra') && !TARIFA_DITA.test(t),
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
  // "ETF de bitcoin na B3": a B3 é o lugar da cripto, não o Ibovespa. Sem caminho nem dois lados do índice.
  const b3SoLugar = p.mercados.includes('cripto') && !IBOV_DITO.test(normalizar(p.pergunta))
  if (b3SoLugar) tirarTodos(medidos, 'ibovespa')
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
  for (const m of p.mercados) {
    // contrato (WIN) ou cripto na B3: a regra de IR das ações à vista não vale
    if (m === 'ibovespa' && (p.mercados.includes('mini_indice') || b3SoLugar)) continue
    const b = BASE.mercado[m]
    blocos.push(b ? copia(b) : null)
    // Petróleo: não há bloco de mercado (o fatos.mercado do Python devolve None). Quem cita só a ação ("vale a pena
    // PETR4?", "PETR4 ou PRIO3?") não recebe a história de um emissor (Res. CVM 20): os eventos entram quando a pergunta
    // cita o fato ou o petróleo. Do barril à bomba, quando ela fala de combustível, ou do petróleo sem tema.
    if (m === 'petroleo') {
      const soAcao = !temasPetroleo.length && ACAO_DITA.test(t) && !PETROLEO_DITO.test(t)
      if (!soAcao) blocos.push(eventosPetroleo(temasPetroleo))
      if (COMBUSTIVEL_DITO.test(t) || (!temasPetroleo.length && !soAcao)) blocos.push(copia(BASE.petroleo.barril))
    }
    if (m === 'cripto') {
      // Regras, imposto, riscos e a linha do tempo. Tema citado (halving, FTX, ETF...): a linha do tempo antes das regras,
      // com a definição primeiro se a pessoa perguntou "o que é". Pergunta de imposto: o imposto primeiro (o blocos[-1:-1]
      // do Python: logo antes do último, que é o das regras). O `t` é a pergunta normalizada, a mesma do começo.
      const tema = temaCripto(t)
      const [imposto, riscos] = [copia(BASE.cripto.imposto), copia(BASE.cripto.riscos)]
      if (IMPOSTO_DITO.test(t)) {
        blocos.splice(blocos.length - 1, 0, imposto)
        blocos.push(riscos)
      } else {
        blocos.push(imposto, riscos)
      }
      if (tema) {
        const i = blocos.findIndex((x) => x !== null && (x.titulo === BASE.titulo_cripto || x.titulo === imposto.titulo))
        if (i < 0) throw new Error('sem o bloco das regras nem o do imposto') // o next() do Python levantaria StopIteration
        blocos.splice(i, 0, criptoMarcos(tema, p.temas.includes('conceito')))
      } else {
        blocos.push(copia(BASE.cripto.marcos['']))
      }
    }
  }
  if (pedeDinheiro || algum(BASE.derivativos.slice(0, 2), p.mercados)) blocos.push(copia(BASE.fgv))
  // O estudo do Copom e da linha do tempo mede o dólar, não o euro: dizer isso, em vez de responder só com o dólar.
  if (p.mercados.includes('euro') && (p.temas.includes('copom') || BASE.tipos.some((t) => p.temas.includes(t)))) {
    blocos.push(euroSemEstudo())
  }
  blocos = blocos.filter((b) => b)
  if (ehCambio(p)) blocos = cambioPrimeiro(p, blocos as Bloco[])
  // em pergunta de câmbio ("exchange my euros"), o câmbio continua na frente
  else if (p.mercados.includes('cripto')) blocos = criptoPrimeiro(blocos as Bloco[])
  if (!blocos.length) blocos.push(copia(BASE.economia))
  return blocos as Bloco[]
}

/** fatos.tema_petroleo: todos os temas dos eventos de petróleo que a pergunta (já normalizada) cita, na ordem do JSON
 * ("a OPEP e a guerra": os dois); nenhum, se ela não cita. */
export function temaPetroleo(perguntaNormalizada: string): string[] {
  return TEMAS_PETROLEO.filter(([, padrao]) => padrao.test(perguntaNormalizada)).map(([tema]) => tema)
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
  return TEMAS_CRIPTO.find(([, padrao]) => padrao.test(perguntaNormalizada))?.[0] ?? ''
}

/** fatos.cripto_marcos(tema, conceito): os marcos do tema, prontos na base. `conceito` (a pessoa perguntou "o que é..."):
 * a definição do tema, quando há, vira o resumo. Ela é a 1ª linha do bloco, e a única que não está na linha do tempo
 * inteira. */
function criptoMarcos(tema: string, conceito: boolean): Bloco {
  const b = copia(BASE.cripto.marcos[tema])
  const definicao = b.linhas.length && !MARCOS_DATADOS.has(b.linhas[0].texto) ? b.linhas[0].texto : null
  if (conceito && definicao) b.resumo = definicao
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
  if (p.mercados.includes('cripto') && PRECO_CRIPTO.test(normalizar(p.pergunta))) linhas.push(T.SEM_PRECO_CRIPTO)
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
const CONTRATO_DE_JUROS = new RegExp(CONTRATO.source + String.raw`|\bfuturos?\b`)

function avisos(r: Resposta): string[] {
  const lista: string[] = []
  const derivativo = algum(BASE.derivativos.slice(0, 2), r.pedido.mercados) ||
    (r.pedido.mercados.includes('juros') && CONTRATO_DE_JUROS.test(normalizar(r.pergunta))) ||
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
    T.SEM_PRECO_CRIPTO, T.RISCO_DERIVATIVO_CRIPTO,
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

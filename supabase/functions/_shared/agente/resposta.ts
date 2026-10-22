// Monta a resposta, sempre da base: tradução de agente/resposta.py. Os blocos de fatos vêm prontos de base.json
// (gerado por `python -m agente.exportar`); aqui só se escolhe, ordena, numera as fontes e passa pelo filtro.
import base from '../base.json' with { type: 'json' }
import { checar } from './filtro.ts'
import { analisar, ehEleicao, temConta } from './roteador.ts'
import type { Pedido, Violacao } from './texto.ts'

type Fonte = { nome: string; url: string }
type Linha = { texto: string; fontes: Fonte[] }
type Bloco = { titulo: string; linhas: Linha[]; resumo: string; limites: string[] }
type Textos = {
  AVISO: string
  RECUSA: string
  FECHO: string
  RISCO_DERIVATIVO: string
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
}

export const BASE = base as unknown as Base
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

/** Número no formato brasileiro, como fatos.num do Python. */
export function num(x: number, casas = 1): string {
  const s = Math.abs(x).toFixed(casas)
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

export function escolherBlocos(p: Pedido, hoje: string): Bloco[] {
  let blocos: (Bloco | null)[] = []
  const pedeDinheiro = p.proibidos.includes('chance_dinheiro')
  if (ehEleicao(p)) {
    blocos.push(BASE.candidatos && copia(BASE.candidatos), copia(BASE.economia), eleicoes(p.mercados),
      BASE.pesquisas && copia(BASE.pesquisas))
  }
  if (p.temas.includes('copom')) {
    if (!ehEleicao(p)) blocos.push(copia(BASE.economia))
    blocos.push(copom(p.mercados))
  }
  for (const tipo of BASE.tipos) {
    if (p.temas.includes(tipo)) blocos.push(copia(BASE.eventos[tipo]))
  }
  const temEconomia = () => blocos.some((b) => b && b.titulo.startsWith('A economia hoje'))
  if (p.temas.includes('economia') && !temEconomia()) blocos.unshift(copia(BASE.economia))
  // Pedido de direção sobre um mercado sem evento no repertório ("é topo?", "qual o viés?"): ao menos o nível de hoje.
  if (p.mercados.length && algum(p.proibidos, PEDEM_RECUSA) && !temEconomia()) blocos.unshift(copia(BASE.economia))
  // Mercado sem evento no repertório ("devo comprar dólar?", "como está o Ibovespa?"): o caminho que ele já fez, o que o
  // mercado espera (Focus, atribuído) e as datas marcadas que já mexeram com ele.
  const temEvento = ehEleicao(p) || p.temas.includes('copom') || BASE.tipos.some((t) => p.temas.includes(t))
  const medidos: string[] = []
  for (const m of p.mercados) {
    const alvo = ({ mini_indice: 'ibovespa', mini_dolar: 'dolar' } as Record<string, string>)[m] ?? m
    if (BASE.historico[alvo] && !medidos.includes(alvo)) medidos.push(alvo)
  }
  if (!temEvento && medidos.length) {
    for (const m of medidos) blocos.push(copia(BASE.historico[m]))
    blocos.push(copia(BASE.expectativas[medidos[0]]), calendario(medidos[0], hoje))
  } else if (p.temas.includes('economia') || p.temas.includes('copom')) {
    blocos.push(copia(BASE.expectativas[medidos.length ? medidos[0] : '']))
  }
  if (p.mercados.includes('memecoin')) blocos.push(copia(BASE.memecoins))
  if (p.mercados.includes('previsao')) blocos.push(copia(BASE.previsao))
  if (p.proibidos.includes('binaria')) blocos.push(copia(BASE.binaria))
  if (temConta(p)) blocos.push(conta(p.pontos as number, p.contratos, p.mercados.includes('mini_indice') ? 'mini_indice' : 'mini_dolar'))
  for (const m of p.mercados) {
    // pergunta de contrato: a regra de IR das ações à vista não vale para o WIN
    if (m === 'ibovespa' && p.mercados.includes('mini_indice')) continue
    const b = BASE.mercado[m]
    blocos.push(b ? copia(b) : null)
  }
  if (pedeDinheiro || algum(BASE.derivativos.slice(0, 2), p.mercados)) blocos.push(copia(BASE.fgv))
  blocos = blocos.filter((b) => b)
  if (!blocos.length) blocos.push(copia(BASE.economia))
  return blocos as Bloco[]
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
  const peso = (r: string) => r.startsWith('Último dado:') ? 2 : r.startsWith(BASE.calendario.resumo_inicio) ? 1 : 0
  const resumos = blocos.map((b) => b.resumo).filter((r) => r)
  resumos.sort((a, b) => peso(a) - peso(b))
  return [...linhas, ...resumos].slice(0, 3)
}

function avisos(r: Resposta): string[] {
  const lista: string[] = []
  if (algum(BASE.derivativos, r.pedido.mercados) || r.blocos.some((b) => b.titulo.startsWith('A taxa-base de quem faz day'))) {
    lista.push(T.RISCO_DERIVATIVO)
  }
  // o bloco da cripto já traz o D5: não repete
  if (algum(['cripto', 'memecoin'], r.pedido.mercados) && !r.blocos.some((b) => b.titulo === BASE.titulo_cripto)) {
    lista.push(T.RISCO_CRIPTO)
  }
  return lista
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
  const oficial = (f: Fonte) => ['Banco Central', 'Ipeadata', 'Tesouro', 'Pesquisa', 'B3', 'Chague'].some((p) => f.nome.startsWith(p))
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
  if (av.length) curto.push('', ...av)
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

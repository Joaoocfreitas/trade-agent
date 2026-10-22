// Paridade do filtro com o Python: frases do gabarito (tests/dados/paridade.json, campos filtro, checar e respostas) e
// casos de borda gerados rodando agente/filtro.py. A saída tem de sair igual, violação por violação, trecho por trecho.
import { checar, type Dec, faltas, frasesProibidas, numeros, numerosSemFonte } from './filtro.ts'
import type { Violacao } from './texto.ts'

type CasoFiltro = { texto: string; violacoes: Violacao[] }
type CasoChecar = { texto: string; fatos: string; violacoes: Violacao[]; numeros_sem_fonte: string[] }
type CasoResposta = { pergunta: string; texto: string; texto_curto: string; violacoes: Violacao[] }
type NumeroPy = [tok: string, coef: string, exp: number, casas: number]
type Extras = {
  numeros: { texto: string; saida: NumeroPy[] }[]
  sem_fonte: { texto: string; fatos: string; saida: string[] | string }[]
  frases: CasoFiltro[]
  faltas: CasoFiltro[]
}

function ehObjeto(x: unknown): x is Record<string, unknown> {
  return typeof x === 'object' && x !== null && !Array.isArray(x)
}

function ehViolacoes(x: unknown): x is Violacao[] {
  return Array.isArray(x) && x.every((v) => ehObjeto(v) && typeof v.regra === 'string' && typeof v.trecho === 'string')
}

function ehTextos(x: unknown): x is string[] {
  return Array.isArray(x) && x.every((v) => typeof v === 'string')
}

async function gabarito(): Promise<Record<string, unknown>> {
  const bruto: unknown = JSON.parse(await Deno.readTextFile(new URL('../../../../tests/dados/paridade.json', import.meta.url)))
  if (!ehObjeto(bruto)) throw new Error('gabarito malformado')
  return bruto
}

function lista(g: Record<string, unknown>, campo: string): unknown[] {
  const v = g[campo]
  if (!Array.isArray(v)) throw new Error(`gabarito sem o campo ${campo}`)
  return v
}

function casosFiltro(g: Record<string, unknown>): CasoFiltro[] {
  return lista(g, 'filtro').map((c, i) => {
    if (!ehObjeto(c) || typeof c.texto !== 'string' || !ehViolacoes(c.violacoes)) throw new Error(`filtro ${i} malformado`)
    return { texto: c.texto, violacoes: c.violacoes }
  })
}

function casosChecar(g: Record<string, unknown>): CasoChecar[] {
  return lista(g, 'checar').map((c, i) => {
    if (
      !ehObjeto(c) || typeof c.texto !== 'string' || typeof c.fatos !== 'string' || !ehViolacoes(c.violacoes) ||
      !ehTextos(c.numeros_sem_fonte)
    ) throw new Error(`checar ${i} malformado`)
    return { texto: c.texto, fatos: c.fatos, violacoes: c.violacoes, numeros_sem_fonte: c.numeros_sem_fonte }
  })
}

function casosResposta(g: Record<string, unknown>): CasoResposta[] {
  return lista(g, 'respostas').map((c, i) => {
    if (
      !ehObjeto(c) || typeof c.pergunta !== 'string' || typeof c.texto !== 'string' || typeof c.texto_curto !== 'string' ||
      !ehViolacoes(c.violacoes)
    ) throw new Error(`resposta ${i} malformada`)
    return { pergunta: c.pergunta, texto: c.texto, texto_curto: c.texto_curto, violacoes: c.violacoes }
  })
}

/** Junta as diferenças e falha uma vez só, com todas elas. */
function conferir(nome: string, pares: [rotulo: string, obtido: unknown, esperado: unknown][]): void {
  const erros = pares.filter(([, o, e]) => JSON.stringify(o) !== JSON.stringify(e))
    .map(([r, o, e]) => `- ${r}\n    TS:     ${JSON.stringify(o)}\n    Python: ${JSON.stringify(e)}`)
  if (erros.length) throw new Error(`${nome}: ${erros.length} de ${pares.length} diferentes:\n${erros.join('\n')}`)
}

function comoPython(ns: [string, Dec, number][]): NumeroPy[] {
  return ns.map(([tok, v, casas]) => [tok, v.coef.toString(), v.exp, casas])
}

/** O InvalidOperation do Decimal vira RangeError no TS. */
function tentar<T>(f: () => T): T | string {
  try {
    return f()
  } catch (e) {
    if (e instanceof RangeError) return 'erro: InvalidOperation'
    throw e
  }
}

async function resumo(x: unknown): Promise<string> {
  const h = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(JSON.stringify(x)))
  return [...new Uint8Array(h)].map((b) => b.toString(16).padStart(2, '0')).join('').slice(0, 16)
}

Deno.test('frasesProibidas: paridade exata nas frases do gabarito', async () => {
  const casos = casosFiltro(await gabarito())
  if (casos.length < 176) throw new Error(`gabarito com ${casos.length} frases, esperava 176`)
  conferir('frasesProibidas', casos.map((c) => [c.texto, frasesProibidas(c.texto), c.violacoes]))
})

Deno.test('checar e numerosSemFonte: paridade exata nos textos sintéticos do gabarito', async () => {
  const casos = casosChecar(await gabarito())
  if (casos.length < 7) throw new Error(`gabarito com ${casos.length} textos, esperava 7`)
  conferir('checar', casos.map((c) => [c.texto.slice(0, 80), checar(c.texto, c.fatos), c.violacoes]))
  conferir('numerosSemFonte', casos.map((c) => [c.texto.slice(0, 80), numerosSemFonte(c.texto, c.fatos), c.numeros_sem_fonte]))
})

Deno.test('respostas do gabarito: limpas contra os próprios números, e iguais ao Python contra os fatos da amostra', async () => {
  const g = await gabarito()
  const casos = casosResposta(g)
  if (casos.length < 142) throw new Error(`gabarito com ${casos.length} respostas, esperava 142`)
  // O Python montou cada resposta e a passou por checar com os fatos dela: o gabarito diz que nada foi barrado.
  conferir('violações do gabarito', casos.map((c) => [c.pergunta, c.violacoes, []]))
  // Os fatos de cada resposta não estão no gabarito. Os números dela mesma servem de fonte: checar(texto, texto) do
  // Python dá vazio em todas.
  conferir('checar(texto, texto)', casos.flatMap((c) => [
    [c.pergunta, checar(c.texto, c.texto), []],
    [`${c.pergunta} (curto)`, checar(c.texto_curto, c.texto_curto), []],
  ]))
  // Contra os fatos da amostra (os do gabarito em checar), sobra número sem fonte em metade delas. O resumo é o
  // SHA-256 (16 primeiros hex) do JSON de [checar(texto), checar(texto_curto), numeros(texto), numeros(texto_curto)],
  // como em tests/dados/respostas_resumo.json; para ver o esperado, rode o mesmo no Python.
  const amostra = casosChecar(g)[0].fatos
  // Gerado por `python -m agente.exportar` (agente/exportar.py, resumos), no mesmo passo do gabarito.
  const esperados = JSON.parse(await Deno.readTextFile(new URL('../../../../tests/dados/respostas_resumo.json', import.meta.url))) as string[]
  if (esperados.length !== casos.length) throw new Error('respostas_resumo.json fora de sincronia com o gabarito')
  const pares: [string, unknown, unknown][] = []
  for (const [i, c] of casos.entries()) {
    const obtido = await resumo([
      checar(c.texto, amostra), checar(c.texto_curto, amostra), comoPython(numeros(c.texto)), comoPython(numeros(c.texto_curto)),
    ])
    pares.push([`${i}: ${c.pergunta}`, obtido, esperados[i]])
  }
  conferir('respostas contra a amostra', pares)
})

Deno.test('numeros: milhar, "mil", dígito Unicode, código de ativo, URL e referência saem como no Python', () => {
  conferir('numeros', EXTRAS.numeros.map((c) => [c.texto, comoPython(numeros(c.texto)), c.saida]))
})

Deno.test('numerosSemFonte: arredondamento meio-par, "mil", teto de 10^12 e InvalidOperation como no Python', () => {
  conferir('numerosSemFonte', EXTRAS.sem_fonte.map((c) => [`${c.texto} | ${c.fatos}`, tentar(() => numerosSemFonte(c.texto, c.fatos)), c.saida]))
})

Deno.test('frasesProibidas: isenções, espaço \\x1c, strip e emoji como no Python', () => {
  conferir('frasesProibidas', EXTRAS.frases.map((c) => [c.texto, frasesProibidas(c.texto), c.violacoes]))
})

Deno.test('faltas: avisos, link, derivativo e cripto como no Python', () => {
  conferir('faltas', EXTRAS.faltas.map((c) => [c.texto, faltas(c.texto), c.violacoes]))
})

// Gerado rodando agente/filtro.py (a referência). Não edite à mão: rode o Python de novo.
const EXTRAS: Extras = {
  numeros: [
    {"texto": "R$ 1.234,56 e 1.000 pontos e 2026.", "saida": [["1.234,56", "123456", -2, 2], ["1.000", "1000", 0, 0], ["2026", "2026", 0, 0]]},
    {"texto": "1.000.000 e 1.5.3 e 12.5 e 1,2,3 e 1.234,5,6 e 12.34,5 e 1,5.3", "saida": [["1.000.000", "1000000", 0, 0], ["1.5.3", "153", 0, 0], ["12.5", "125", -1, 1], ["12.34,5", "12345", -1, 1], ["1,5.3", "153", -2, 2]]},
    {"texto": "0,10 e 0 e 007 e 0,0 e 12,0 e 12,5 e 13", "saida": [["0,10", "10", -2, 2], ["0", "0", 0, 0], ["007", "7", 0, 0], ["0,0", "0", -1, 1], ["12,0", "120", -1, 1], ["12,5", "125", -1, 1], ["13", "13", 0, 0]]},
    {"texto": "2,5 mil, 5mil, 5 milh\u00f5es, 5 Mil, 5\u001cmil, 5\ufeffmil, 5 mil\u00e9, 5 mil\u0301, 5\u00a0mil", "saida": [["2,5", "25000", -1, -3], ["5", "5000", 0, -3], ["5", "5", 0, 0], ["5", "5", 0, 0], ["5", "5000", 0, -3], ["5", "5", 0, 0], ["5", "5", 0, 0], ["5", "5000", 0, -3], ["5", "5000", 0, -3]]},
    {"texto": "0,005 mil e 12345678901234567890123456789012 mil e 99999999999999999999999999995 mil", "saida": [["0,005", "5000", -3, -3], ["12345678901234567890123456789012", "1234567890123456789012345679", 7, -3], ["99999999999999999999999999995", "1000000000000000000000000000", 5, -3]]},
    {"texto": "\u0661\u0662\u0663 e \uff11\uff12,\uff15 e \ud835\udfd9\ud835\udfda e \ud818\udd31\ud818\udd32 e 7\ud818\udd31", "saida": [["\u0661\u0662\u0663", "123", 0, 0], ["\uff11\uff12,\uff15", "125", -1, 1], ["\ud835\udfd9\ud835\udfda", "12", 0, 0], ["7", "7", 0, 0]]},
    {"texto": "WINZ26 a 125.000; \u00c9WINZ26; \ud801\uddc0WINZ26; WDOF27x; R2/2020; BR-01234/2026; ABCDEFG12; a WIN26_", "saida": [["125.000", "125000", 0, 0], ["26", "26", 0, 0], ["27", "27", 0, 0], ["2020", "2020", 0, 0], ["12", "12", 0, 0], ["26", "26", 0, 0]]},
    {"texto": "ref [12] e [\u0661\u0662] e [3 ] e https://x.com/a?b=1,5 e https://a.b/1\u00852,5 e http://y.z/9\ufeff8", "saida": [["3", "3", 0, 0], ["2,5", "25", -1, 1]]},
    {"texto": "IPCA de 4,58% e Selic 13,75% (21/10/2026), 208.296 pontos, 82,87% do PIB", "saida": [["4,58", "458", -2, 2], ["13,75", "1375", -2, 2], ["21", "21", 0, 0], ["10", "10", 0, 0], ["2026", "2026", 0, 0], ["208.296", "208296", 0, 0], ["82,87", "8287", -2, 2]]},
  ],
  sem_fonte: [
    {"texto": "4,56 e 4,57", "fatos": "4,565", "saida": ["4,57"]},
    {"texto": "4,58 e 4,57", "fatos": "4,575", "saida": ["4,57"]},
    {"texto": "13,7 e 13,8 e 14", "fatos": "13,75", "saida": ["13,7"]},
    {"texto": "0,10 e 0,1", "fatos": "0,1", "saida": []},
    {"texto": "2,5 mil e 3,5 mil e 2,4 mil", "fatos": "2.500 e 3.500", "saida": []},
    {"texto": "250 mil", "fatos": "249.501", "saida": []},
    {"texto": "250 mil", "fatos": "250.500", "saida": []},
    {"texto": "251 mil", "fatos": "250.500", "saida": ["251"]},
    {"texto": "1.000.000.000.000 e 999.999.999.999", "fatos": "1.000.000.000.000 e 999.999.999.999", "saida": ["1.000.000.000.000"]},
    {"texto": "999999999999,99", "fatos": "999999999999,99999999999999999", "saida": ["999999999999,99"]},
    {"texto": "999999999999,99", "fatos": "999999999999,9999999999999999", "saida": ["999999999999,99"]},
    {"texto": "12,0 e 12,5 e 13 e 0,005 mil", "fatos": "", "saida": ["12,5", "13"]},
    {"texto": "13 e 14", "fatos": "", "saida": ["13", "14"]},
    {"texto": "\u0661\u0663 e 14", "fatos": "13 e \uff11\uff14", "saida": []},
    {"texto": "208 mil pontos e 208,3 mil", "fatos": "208.296", "saida": []},
    {"texto": "5\ufeffmil e 5\u001cmil", "fatos": "5.000", "saida": []},
    {"texto": "12345678901234567890123456789 e 15", "fatos": "15", "saida": ["12345678901234567890123456789"]},
    {"texto": "12345678901234567890123456789", "fatos": "", "saida": ["12345678901234567890123456789"]},
    {"texto": "0,12345678901234567", "fatos": "999999999999", "saida": ["0,12345678901234567"]},
    {"texto": "0,1234567890123456", "fatos": "999999999999", "saida": ["0,1234567890123456"]},
    {"texto": "12345678901234567890123456789012 mil", "fatos": "13", "saida": ["12345678901234567890123456789012"]},
    {"texto": "12345678901234567890123456789012 mil", "fatos": "", "saida": ["12345678901234567890123456789012"]},  ],
  frases: [
    {"texto": "Nao indico corretora.", "violacoes": []},
    {"texto": "nao\u001cindico corretora", "violacoes": []},
    {"texto": "\u001ccompre\u001c", "violacoes": [{"regra": "N1", "trecho": "compre"}]},
    {"texto": "Nao digo isso. Compre agora.", "violacoes": [{"regra": "N1", "trecho": "nao digo isso. compre agora."}]},
    {"texto": "O dolar vai subir ou cair.", "violacoes": []},
    {"texto": "Segundo o Focus, o dolar vai cair.", "violacoes": []},
    {"texto": "Nao existe lucro garantido.", "violacoes": []},
    {"texto": "N\u00e3o digo se o Ibovespa vai subir, mas o d\u00f3lar vai cair.", "violacoes": [{"regra": "N2", "trecho": "se o ibovespa vai subir, mas o dolar vai cair."}, {"regra": "N2", "trecho": "ovespa vai subir, mas o dolar vai cair."}]},
    {"texto": "Compre: o d\u00f3lar sobe; nem dou dica, mas vende j\u00e1.", "violacoes": [{"regra": "N1", "trecho": "compre: o dolar sobe; nem dou dica,"}, {"regra": "N1", "trecho": "dolar sobe; nem dou dica, mas vende ja."}, {"regra": "N2", "trecho": "compre: o dolar sobe; nem dou dica, mas vende ja."}]},
    {"texto": "Nem vou dizer que \u00e9 hora de comprar.", "violacoes": []},
    {"texto": "Ningu\u00e9m sabe se o d\u00f3lar vai cair", "violacoes": []},
    {"texto": "Nao, o dolar sobe.", "violacoes": [{"regra": "N2", "trecho": "nao, o dolar sobe."}, {"regra": "N2", "trecho": "nao, o dolar sobe."}]},
    {"texto": "Ibovespa: 3 de 5 subiram. Em 4 das 5 eleicoes, a bolsa caiu.", "violacoes": [{"regra": "N3", "trecho": "ibovespa: 3 de 5 subiram. em 4 das 5 eleicoes, a bolsa"}, {"regra": "N3", "trecho": "ibovespa: 3 de 5 subiram. em 4 das 5 eleicoes, a bolsa caiu."}]},
    {"texto": "1,2 de 5 subiram", "violacoes": []},
    {"texto": "compraria \ud83d\ude80 j\u00e1", "violacoes": [{"regra": "N1", "trecho": "compraria  ja"}]},
    {"texto": "POLYMARKET.COM tem 60% de chance", "violacoes": [{"regra": "N2", "trecho": "polymarket.com tem 60% de chance"}, {"regra": "N8", "trecho": "polymarket.com tem 60% de chance"}]},
    {"texto": "texto\n\ncompre\n\n", "violacoes": [{"regra": "N1", "trecho": "texto\n\ncompre"}]},
    {"texto": "a\u2028compre", "violacoes": []},
    {"texto": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx compre yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy", "violacoes": [{"regra": "N1", "trecho": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxx compre yyyyyyyyyyyyyyyyyyyyyyyyyyyyy"}]},
  ],
  faltas: [
    {"texto": "Sou uma IA. Nao e recomendacao. CVM. Rentabilidade passada.", "violacoes": []},
    {"texto": "Sou uma IA e n\u00e3o \u00e9 recomenda\u00e7\u00e3o (CVM).", "violacoes": [{"regra": "D2", "trecho": "falta \"rentabilidade passada n\u00e3o indica rentabilidade futura\""}]},
    {"texto": "Selic de 13,75% em https://bcb.gov.br", "violacoes": [{"regra": "D3", "trecho": "faltam os avisos: sou uma IA, posso errar, n\u00e3o \u00e9 recomenda\u00e7\u00e3o, n\u00e3o somos credenciados"}, {"regra": "D2", "trecho": "falta \"rentabilidade passada n\u00e3o indica rentabilidade futura\""}]},
    {"texto": "Selic de 13,75%", "violacoes": [{"regra": "D3", "trecho": "faltam os avisos: sou uma IA, posso errar, n\u00e3o \u00e9 recomenda\u00e7\u00e3o, n\u00e3o somos credenciados"}, {"regra": "D2", "trecho": "falta \"rentabilidade passada n\u00e3o indica rentabilidade futura\""}, {"regra": "D1", "trecho": "tem n\u00famero e n\u00e3o tem fonte com link"}]},
    {"texto": "3 contratos e 12 linhas", "violacoes": [{"regra": "D3", "trecho": "faltam os avisos: sou uma IA, posso errar, n\u00e3o \u00e9 recomenda\u00e7\u00e3o, n\u00e3o somos credenciados"}, {"regra": "D2", "trecho": "falta \"rentabilidade passada n\u00e3o indica rentabilidade futura\""}]},
    {"texto": "mini dolar, minidolar e win", "violacoes": [{"regra": "D3", "trecho": "faltam os avisos: sou uma IA, posso errar, n\u00e3o \u00e9 recomenda\u00e7\u00e3o, n\u00e3o somos credenciados"}, {"regra": "D2", "trecho": "falta \"rentabilidade passada n\u00e3o indica rentabilidade futura\""}, {"regra": "D4", "trecho": "fala de derivativo e n\u00e3o avisa que a perda pode passar do depositado"}]},
    {"texto": "mini-\u00edndice: pode perder mais do que depositou", "violacoes": [{"regra": "D3", "trecho": "faltam os avisos: sou uma IA, posso errar, n\u00e3o \u00e9 recomenda\u00e7\u00e3o, n\u00e3o somos credenciados"}, {"regra": "D2", "trecho": "falta \"rentabilidade passada n\u00e3o indica rentabilidade futura\""}]},
    {"texto": "criptomoedas", "violacoes": [{"regra": "D3", "trecho": "faltam os avisos: sou uma IA, posso errar, n\u00e3o \u00e9 recomenda\u00e7\u00e3o, n\u00e3o somos credenciados"}, {"regra": "D2", "trecho": "falta \"rentabilidade passada n\u00e3o indica rentabilidade futura\""}, {"regra": "D5", "trecho": "fala de cripto e n\u00e3o diz que, em regra, n\u00e3o \u00e9 valor mobili\u00e1rio"}]},
    {"texto": "bitcoins", "violacoes": [{"regra": "D3", "trecho": "faltam os avisos: sou uma IA, posso errar, n\u00e3o \u00e9 recomenda\u00e7\u00e3o, n\u00e3o somos credenciados"}, {"regra": "D2", "trecho": "falta \"rentabilidade passada n\u00e3o indica rentabilidade futura\""}]},
    {"texto": "bitcoin n\u00e3o \u00e9 valor mobili\u00e1rio", "violacoes": [{"regra": "D3", "trecho": "faltam os avisos: sou uma IA, posso errar, n\u00e3o \u00e9 recomenda\u00e7\u00e3o, n\u00e3o somos credenciados"}, {"regra": "D2", "trecho": "falta \"rentabilidade passada n\u00e3o indica rentabilidade futura\""}]},
    {"texto": "DI futuro e WDO", "violacoes": [{"regra": "D3", "trecho": "faltam os avisos: sou uma IA, posso errar, n\u00e3o \u00e9 recomenda\u00e7\u00e3o, n\u00e3o somos credenciados"}, {"regra": "D2", "trecho": "falta \"rentabilidade passada n\u00e3o indica rentabilidade futura\""}, {"regra": "D4", "trecho": "fala de derivativo e n\u00e3o avisa que a perda pode passar do depositado"}]},
    {"texto": "https://a.b s\u00f3 link e 15", "violacoes": [{"regra": "D3", "trecho": "faltam os avisos: sou uma IA, posso errar, n\u00e3o \u00e9 recomenda\u00e7\u00e3o, n\u00e3o somos credenciados"}, {"regra": "D2", "trecho": "falta \"rentabilidade passada n\u00e3o indica rentabilidade futura\""}]},
    {"texto": "15 e http:/ quase link", "violacoes": [{"regra": "D3", "trecho": "faltam os avisos: sou uma IA, posso errar, n\u00e3o \u00e9 recomenda\u00e7\u00e3o, n\u00e3o somos credenciados"}, {"regra": "D2", "trecho": "falta \"rentabilidade passada n\u00e3o indica rentabilidade futura\""}, {"regra": "D1", "trecho": "tem n\u00famero e n\u00e3o tem fonte com link"}]},
    {"texto": "12345678901234567890123456789 mil", "violacoes": [{"regra": "D3", "trecho": "faltam os avisos: sou uma IA, posso errar, n\u00e3o \u00e9 recomenda\u00e7\u00e3o, n\u00e3o somos credenciados"}, {"regra": "D2", "trecho": "falta \"rentabilidade passada n\u00e3o indica rentabilidade futura\""}, {"regra": "D1", "trecho": "tem n\u00famero e n\u00e3o tem fonte com link"}]},
  ],
}

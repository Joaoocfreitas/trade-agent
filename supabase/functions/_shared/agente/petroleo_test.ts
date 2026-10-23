// Petróleo: o espelho de tests/test_petroleo.py no que cabe ao TS. O Brent, os 50 eventos de petróleo e Petrobras
// (2016–2026) com a reação do Brent, do Ibovespa e do dólar, e do barril à bomba vêm prontos da base; aqui se confere que o
// TS acha o tema, monta os blocos na mesma ordem e não puxa o bloco de geopolítica, que só mede o Ibovespa.
// Os esperados saíram do Python (.venv/bin/python) em 23/10/2026.
import { assert, assertEquals } from 'jsr:@std/assert@1.0.13'
import { frasesProibidas } from './filtro.ts'
import { BASE, montar, temaPetroleo } from './resposta.ts'
import { escolherCartao } from './analisar.ts'
import { analisar, normalizar } from './roteador.ts'

const T = BASE.textos
const HOJE = '2026-10-23'
type Evento = { tema: string; fonte: { url: string } }
const PETROLEO = JSON.parse(await Deno.readTextFile(new URL('../../../../dados/agente/petroleo.json', import.meta.url))) as {
  eventos: Evento[]
  temas: Record<string, unknown>
}

Deno.test('a base traz o Brent pela chave, e não há bloco de mercado do petróleo', () => {
  for (const chave of ['historico', 'dois_lados', 'agenda'] as const) assert(BASE[chave].brent, chave)
  assert(BASE.historico.brent.resumo.startsWith('O petróleo Brent está em US$'))
  assertEquals(BASE.mercado.petroleo, undefined) // fatos.mercado('petroleo') é None
  assertEquals(Object.keys(BASE.petroleo.eventos), ['', ...Object.keys(PETROLEO.temas)])
  assertEquals(Object.keys(BASE.petroleo.temas), Object.keys(PETROLEO.temas))
})

Deno.test('os eventos têm fonte primária e tema, e o bloco mostra todos os do tema', () => {
  assertEquals(PETROLEO.eventos.length, 50)
  for (const e of PETROLEO.eventos) assert(e.fonte.url.startsWith('http') && e.tema in PETROLEO.temas, JSON.stringify(e))
  for (const tema of ['', 'petrobras', 'opep', 'guerra', 'governo', 'choque']) {
    const b = BASE.petroleo.eventos[tema]
    const esperados = PETROLEO.eventos.filter((e) => !tema || e.tema === tema).length
    assertEquals(b.linhas.filter((ln) => ln.texto.includes(': no dia da reação')).length, esperados, tema) // todos, nunca os maiores
    assert(b.limites.some((x) => x.includes('licença de dados da B3')), tema)
    for (const ln of b.linhas) assertEquals(frasesProibidas(ln.texto), [], ln.texto)
  }
})

Deno.test('o tema do petróleo: o 1º que casa na pergunta normalizada', () => {
  const casos: [string, string][] = [['vale a pena comprar Petrobras?', 'petrobras'], ['o que a OPEP fez?', 'opep'],
    ['o petróleo vai subir com a guerra?', 'guerra'], ['o imposto do diesel mudou?', 'governo'], ['como o petróleo chega na bomba?', '']]
  for (const [q, tema] of casos) {
    assert(analisar(q).mercados.includes('petroleo'), q)
    assertEquals(temaPetroleo(normalizar(q)), tema, q)
    // os eventos do tema e o barril entram, nessa ordem
    const titulos = montar(q, undefined, HOJE).blocos.map((b) => b.titulo)
    const i = titulos.indexOf(BASE.petroleo.eventos[tema].titulo)
    assert(i >= 0 && titulos[i + 1] === BASE.petroleo.barril.titulo, `${q}: ${titulos.join(' | ')}`)
  }
})

Deno.test('pedido de dica em petróleo recebe a recusa e os dois lados', () => {
  for (const q of ['vale a pena comprar Petrobras?', 'o petróleo vai subir com a guerra?', 'quais ações de petróleo comprar?',
    'compro PETR4 amanhã?']) {
    const r = montar(q, undefined, HOJE)
    assertEquals(r.violacoes, [], q)
    assert(r.abertura.includes(T.RECUSA), q)
    assert(r.blocos.some((b) => b.titulo.startsWith(BASE.titulo_dois_lados)), q)
  }
})

Deno.test('petróleo não puxa o bloco de geopolítica, que só mede o Ibovespa', () => {
  const r = montar('o petróleo vai subir com a guerra?', undefined, HOJE)
  assert(!r.blocos.some((b) => b.titulo.startsWith('O que aconteceu antes: geopolítica')))
  assert(r.curta[0].startsWith('O petróleo Brent está em US$'), r.curta[0])
  assert(analisar('Tarifas dos EUA e o Ibovespa').temas.includes('geopolitico'))
  assert(!analisar('como está o petróleo?').temas.includes('geopolitico')) // "petróleo" saiu do tema
})

Deno.test('o Focus não pergunta pelo petróleo; com Copom, vale a expectativa padrão', () => {
  const espera = (q: string) => montar(q, undefined, HOJE).blocos.filter((b) => b.titulo.startsWith('O que o mercado espera'))
  assertEquals(espera('como está o petróleo?'), [])
  // fatos.expectativas('brent') do Python é idêntico ao de '' (a base não exporta o do Brent)
  assertEquals(espera('o petróleo e o Copom'), [BASE.expectativas['']])
})

Deno.test('do barril à bomba: a conta em reais', () => {
  const conta = BASE.petroleo.barril.linhas.at(-1)!.texto
  assert(conta.includes('por litro de petróleo cru') && conta.includes('158,987 litros'), conta)
})

Deno.test('cartão: pergunta de petróleo mostra o cartão dos eventos de petróleo do tema (Brent), não o da geopolítica', () => {
  const p = analisar('o petróleo vai subir com a guerra?')
  const c = escolherCartao(p)
  assert(c !== null && c.ativo === 'Petróleo Brent (EIA)' && c.titulo === 'Guerras e ataques desde 2016', JSON.stringify(c?.titulo))
  const t = escolherCartao(analisar('Tarifas dos EUA e o Ibovespa'))
  assert(t !== null && t.ativo === 'Ibovespa')
})

// Cripto sem preço e os dois lados do que já aconteceu: o espelho de tests/test_cripto.py.
//
// O bitcoin entra com regra, imposto, formas de ter, riscos e a linha do tempo, tudo pronto na base. Quem pergunta se
// compra ou para onde vai recebe a recusa e, nos mercados com série, os dois lados (quando caiu, quando subiu), na mesma
// ordem e do mesmo tamanho, terminando em "a decisão é sua". Os esperados saíram do Python (.venv/bin/python) em 23/10/2026.
import { assert, assertEquals } from 'jsr:@std/assert@1.0.13'
import { frasesProibidas } from './filtro.ts'
import { avisosDoCurto, BASE, montar, temaCripto } from './resposta.ts'
import { normalizar } from './roteador.ts'

const T = BASE.textos
const HOJE = '2026-10-23'
// fatos.DECISAO_SUA do Python
const DECISAO_SUA = 'O histórico mostra os dois lados, não o próximo movimento: a decisão é sua.'

Deno.test('a base traz o bloco novo da cripto e os títulos que vão na frente', () => {
  assertEquals(BASE.mercado.cripto?.titulo, 'Como funciona a cripto no Brasil')
  assertEquals(BASE.titulo_cripto, BASE.mercado.cripto?.titulo)
  assertEquals(BASE.cripto.titulos, [BASE.cripto.marcos[''].titulo, BASE.titulo_cripto, BASE.cripto.imposto.titulo,
    BASE.cripto.riscos.titulo])
  // toda linha de regra, imposto e risco tem fonte com link
  for (const b of [BASE.mercado.cripto!, BASE.cripto.imposto, BASE.cripto.riscos]) {
    for (const ln of b.linhas) assert(ln.fontes.length && ln.fontes.every((f) => f.url.startsWith('http')), ln.texto)
  }
})

Deno.test('"bitcoin, vale a pena?" recebe a recusa e 3 linhas de cripto', () => {
  const r = montar('quero comprar bitcoin hoje, vale a pena?', undefined, HOJE)
  assertEquals(r.violacoes, [])
  assert(r.abertura.includes(T.RECUSA))
  assert(r.curta[0].startsWith('Bitcoin à vista, em regra, não é valor mobiliário'), r.curta[0])
  assert(r.curta[1].startsWith('Imposto:') && r.curta[2].startsWith('Riscos:'), r.curta.join('\n'))
})

Deno.test('o tema da linha do tempo: o 1º que casa, e a linha do tempo vem antes das regras', () => {
  const casos: [string, string][] = [['o que aconteceu no halving?', 'halving'], ['e a FTX?', 'ftx'], ['ETF de bitcoin na B3', 'etf'],
    ['bitcoin e o Trump', 'trump'], ['stablecoin é câmbio?', 'stablecoin'], ['quero comprar bitcoin', '']]
  for (const [q, tema] of casos) {
    assertEquals(temaCripto(normalizar(q)), tema, q)
    const r = montar(q, undefined, HOJE)
    assertEquals(r.violacoes, [], q)
    if (tema) {
      assert(r.curta[0].startsWith('Na linha do tempo da cripto:'), `${q}: ${r.curta[0]}`)
      assertEquals(r.blocos[0], BASE.cripto.marcos[tema], q)
    }
  }
})

Deno.test('ETF de bitcoin na B3 fala de cripto, não do nível do Ibovespa', () => {
  const r = montar('ETF de bitcoin na B3', undefined, HOJE)
  assert(!r.curta.some((x) => x.startsWith('O Ibovespa está em')), r.curta.join('\n'))
  assert(r.curta[0].includes('HASH11')) // sigla não vira "hASH11"
})

Deno.test('a versão curta de cripto sempre tem o D5', () => {
  for (const q of ['o que aconteceu no halving?', 'e a FTX?', 'stablecoin é câmbio?', 'bitcoin e o Trump']) {
    const r = montar(q, undefined, HOJE)
    assert(r.texto_curto.includes('não é valor mobiliário'), q)
  }
})

Deno.test('a guarda do D5 no curto: entra só quando falta, e nunca em dobro', () => {
  const linha = 'Na linha do tempo da cripto: 09/07/2016, o 2º halving.'
  // fala de cripto, o aviso não está e nenhuma das 3 linhas diz: entra
  assertEquals(avisosDoCurto([], ['cripto'], [linha]), [T.RISCO_CRIPTO])
  assertEquals(avisosDoCurto([T.RISCO_DERIVATIVO], ['memecoin'], [linha]), [T.RISCO_DERIVATIVO, T.RISCO_CRIPTO])
  // uma das linhas já diz, ou o aviso já está, ou a pergunta não é de cripto: fica como está
  assertEquals(avisosDoCurto([], ['cripto'], [linha, 'Bitcoin à vista, em regra, não é valor mobiliário.']), [])
  assertEquals(avisosDoCurto([T.RISCO_CRIPTO], ['cripto'], [linha]), [T.RISCO_CRIPTO])
  assertEquals(avisosDoCurto([], ['dolar'], [linha]), [])
})

Deno.test('os dois lados: mesma ordem, mesmo tamanho, terminando em "a decisão é sua"', () => {
  for (const mercado of ['dolar', 'euro', 'juros', 'ibovespa']) {
    const b = BASE.dois_lados[mercado]!
    const textos = b.linhas.map((ln) => ln.texto)
    assert(textos[0].startsWith('Quando caiu:') && textos[1].startsWith('Quando subiu:'), mercado)
    const parenteses = (t: string) => t.split('(').length - 1
    assert(parenteses(textos[0]) === parenteses(textos[1]) && textos[0].includes('pregões seguidos') &&
      textos[1].includes('pregões seguidos'), mercado)
    assertEquals(textos.at(-1), DECISAO_SUA, mercado)
    assert(b.resumo.endsWith(DECISAO_SUA) && b.resumo.indexOf('queda') < b.resumo.indexOf('alta'), mercado)
    for (const t of [...textos, b.resumo]) assertEquals(frasesProibidas(t), [], t)
  }
})

Deno.test('quem pede o que fazer recebe os dois lados', () => {
  for (const q of ['devo comprar dolar hoje?', 'o dólar vai cair?', 'compro ibovespa?', 'euro sobe?',
    'Vendo meus títulos prefixados agora?']) {
    const r = montar(q, undefined, HOJE)
    assertEquals(r.violacoes, [], q)
    assert(r.curta.some((x) => x.startsWith('Os dois lados nos últimos 12 meses')), `${q}: ${r.curta.join(' | ')}`)
    assert(!r.texto.toLowerCase().includes('recomendo'), q)
  }
})

Deno.test('pergunta neutra não recebe os dois lados, e contrato continua com a FGV nas 3 linhas', () => {
  const lados = (q: string) => montar(q, undefined, HOJE).blocos.some((b) => b.titulo.startsWith(BASE.titulo_dois_lados))
  assert(!lados('Como está o dólar?'))
  const w = montar('WDO sobe amanhã?', undefined, HOJE)
  assert(w.curta.some((x) => x.includes('97%')) && !lados('WDO sobe amanhã?'))
})

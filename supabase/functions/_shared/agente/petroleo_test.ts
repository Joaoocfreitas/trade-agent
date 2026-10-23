// Petróleo: o espelho de tests/test_petroleo.py no que cabe ao TS. O Brent, os 50 eventos de petróleo e Petrobras
// (2016–2026) com a reação do Brent, do Ibovespa e do dólar, e do barril à bomba vêm prontos da base; aqui se confere que
// o TS acha os temas, monta os blocos na mesma ordem, recusa os pedidos e não confunde o presidente da Petrobras com a
// eleição nem o petróleo figurado com o de verdade. Os esperados saíram do Python (.venv/bin/python) em 23/10/2026.
import { assert, assertEquals } from 'jsr:@std/assert@1.0.13'
import { analisar as analisarSite } from './analisar.ts'
import { frasesProibidas } from './filtro.ts'
import { BASE, montar, temaPetroleo } from './resposta.ts'
import { analisar, ehEleicao, normalizar } from './roteador.ts'

const T = BASE.textos
const HOJE = '2026-10-23'
type Evento = { tema: string; titulo: string; fonte: { url: string } | { url: string }[] }
const PETROLEO = JSON.parse(await Deno.readTextFile(new URL('../../../../dados/agente/petroleo.json', import.meta.url))) as {
  eventos: Evento[]
  temas: Record<string, unknown>
}
const titulos = (q: string) => montar(q, undefined, HOJE).blocos.map((b) => b.titulo)
const EVENTOS = (b: string) => b.startsWith('O que aconteceu antes: ') && b.includes('desde 2016')

Deno.test('a base traz o Brent pela chave, sem bloco de mercado do petróleo, e um bloco de eventos por combinação', () => {
  for (const chave of ['historico', 'dois_lados', 'agenda'] as const) assert(BASE[chave].brent, chave)
  assertEquals(BASE.mercado.petroleo, undefined) // fatos.mercado('petroleo') é None
  const temas = Object.keys(PETROLEO.temas)
  assertEquals(Object.keys(BASE.petroleo.temas), temas)
  assertEquals(BASE.petroleo.eventos.linhas.length, PETROLEO.eventos.length)
  assertEquals(Object.keys(BASE.petroleo.eventos.blocos).length, 2 ** temas.length) // todas as combinações, '' inclusive
})

Deno.test('os eventos têm fonte e tema, e o bloco mostra todos os dos temas citados', () => {
  assertEquals(PETROLEO.eventos.length, 50)
  for (const e of PETROLEO.eventos) {
    const fontes = Array.isArray(e.fonte) ? e.fonte : [e.fonte]
    assert(fontes.every((f) => f.url.startsWith('http')) && e.tema in PETROLEO.temas, e.titulo)
  }
  for (const q of ['como está o petróleo?', 'o que a OPEP fez?', 'o petróleo vai subir com a guerra?', 'a OPEP e a guerra',
    'troca de presidente da Petrobras', 'a covid derrubou o petróleo?', 'o imposto do diesel mudou?']) {
    const temas = temaPetroleo(normalizar(q))
    const b = montar(q, undefined, HOJE).blocos.find((x) => EVENTOS(x.titulo))!
    const esperados = PETROLEO.eventos.filter((e) => !temas.length || temas.includes(e.tema)).length
    assertEquals(b.linhas.filter((ln) => ln.texto.includes(': no dia da reação')).length, esperados, q) // todos, nunca os maiores
    assert(b.limites.some((x) => x.includes('licença de dados da B3')), q)
    assert(b.resumo.includes('a ação da Petrobras não foi medida'), q)
    assert(!('eventos' in b), q) // a chave dos índices não vai para o bloco montado
    for (const ln of b.linhas) assertEquals(frasesProibidas(ln.texto), [], ln.texto)
  }
})

Deno.test('a OPEP não leva a alta do 1º turno', () => {
  const b = montar('o que a OPEP fez?', undefined, HOJE).blocos.find((x) => EVENTOS(x.titulo))!
  assert(!b.resumo.includes('7,70%') && !b.linhas.at(-2)!.texto.includes('7,70%'))
  assert(b.linhas.find((ln) => ln.texto.startsWith('04/10/2026'))!.texto.includes('1º turno'))
  assert(b.limites.some((x) => x.includes('mesmo de outro fato')))
})

Deno.test('os temas do petróleo: todos os que casam, na ordem do JSON', () => {
  const casos: [string, string[]][] = [
    ['vale a pena comprar Petrobras?', []], ['o que a OPEP fez?', ['opep']], ['o petróleo vai subir com a guerra?', ['guerra']],
    ['o imposto do diesel mudou?', ['governo']], ['como o petróleo chega na bomba?', []], ['troca de presidente da Petrobras', ['petrobras']],
    ['o ataque à Arábia Saudita e o petróleo', ['guerra']], ['a guerra de preços do petróleo em 2020', ['choque']],
    ['a guerra de preços da Arábia Saudita e o petróleo', ['choque']], ['a Petrobras e o imposto de exportação', ['governo']],
    ['a Petrobras deixou de ser operadora do pré-sal', ['governo', 'petrobras']], ['o petróleo irá subir?', []],
    ['o petróleo fechou negativo hoje?', []], ['o Brent teve retorno negativo no ano?', []], ['guerra no Irã e o petróleo', ['guerra']],
    ['o WTI ficou negativo?', ['choque']], ['a OPEP e a guerra', ['opep', 'guerra']], ['PETR4 é boa pagadora de dividendos?', []],
    ['petrobras vai pagar dividendo?', []],
    ['como o Ibovespa reagiu ao dividendo extraordinário da Petrobras em 2024?', ['petrobras']],
  ]
  for (const [q, temas] of casos) {
    assert(analisar(q).mercados.includes('petroleo'), q)
    assertEquals(temaPetroleo(normalizar(q)), temas, q)
  }
  // o título de cada evento cai no próprio tema
  for (const e of PETROLEO.eventos) {
    const temas = temaPetroleo(normalizar(e.titulo))
    assert(!temas.length || temas.includes(e.tema), `${e.titulo}: ${temas}`)
  }
})

Deno.test('"Irã" é o país e "irá" é o verbo, com ou sem maiúscula', () => {
  assertEquals(normalizar('Guerra no Irã'), 'guerra no iran')
  assertEquals(normalizar('o IRÃ e o petróleo; o petróleo irá subir'), 'o iran e o petroleo; o petroleo ira subir')
  assertEquals(normalizar('Irãnianos'), 'iranianos') // colado em letra não é o país: só sai o acento
  assert(analisar('ataque ao ira').temas.includes('geopolitico'))
  assert(!analisar('o petróleo irá subir?').temas.includes('geopolitico'))
})

const PEDIDOS = [
  'vale a pena comprar Petrobras?', 'o petróleo vai subir com a guerra?', 'quais ações de petróleo comprar?',
  'compro PETR4 amanhã?', 'vale a pena PETR4?', 'compro PETR4 antes do dividendo?', 'PETR4 é boa pagadora de dividendos?',
  'PETR4 ou PRIO3, qual é melhor?', 'PETR3 ou PETR4?', 'PRIO é melhor que a Petrobras?', 'qual a melhor petroleira da bolsa?',
  'qual petroleira paga mais dividendo?', 'qual paga mais dividendo, PETR4 ou PRIO3?', 'petrobras ou vale?',
  'mantenho PETR4?', 'zero minha petrobras?', 'aumento minha posição em petrobras?', 'faço preço médio em petr4?',
  'vale segurar petrobras?', 'aproveito a queda da petrobras?', 'petróleo: long ou short?', 'petroleo bom momento?',
  'o petróleo caiu 15% num dia, é oportunidade?', 'tá na hora de petrobras?',
  'qual o preço justo da PETR4?', 'petrobras tá cara?', 'PETR4 tá descontada?', 'PETR4 tá esticada?', 'petrobras tem upside?',
  'petrobras é investimento seguro?', 'qual a petroleira mais sólida?', 'PETR4 tá subvalorizada?',
  'o brent vai a 150?', 'o brent chega a 150?', 'PETR4 bate 50 reais?', 'o barril passa de 140 de novo?',
  'o petróleo vai voltar pra 60?', 'petróleo vai continuar subindo?', 'a guerra no Irã vai fazer o petróleo explodir?',
  'o petroleo explode se fecharem Ormuz?', 'petrobras vai pagar dividendo?', 'a petrobras vai reajustar a gasolina?',
  'a opep corta?', 'barril a 115, a petrobras vai lucrar muito?', 'o Brent chega a 200?', 'o barril vai pra 150?',
  'o Brent passa de 150 até dezembro?', 'o petróleo vai bater 150 dólares?', 'vai ter reajuste da gasolina?',
  'dividendo de R$ 6,73 por ação compensa comprar Petrobras?',
]

Deno.test('pedido em petróleo recebe a recusa', () => {
  for (const q of PEDIDOS) {
    const r = montar(q, undefined, HOJE)
    assertEquals(r.violacoes, [], q)
    assert(r.abertura.includes(T.RECUSA), `${q}: ${r.pedido.proibidos}`)
  }
})

Deno.test('escolher entre empresas é ranking, não comparar; nível de preço no futuro é direção; fato não é pedido', () => {
  for (const q of ['PETR4 ou PRIO3, qual é melhor?', 'petrobras ou vale?', 'qual a melhor petroleira da bolsa?']) {
    const p = analisar(q)
    assert(p.proibidos.includes('ranking') && !p.proibidos.includes('comparar'), `${q}: ${p.proibidos}`)
    assert(montar(q, undefined, HOJE).abertura.includes(T.POR_PEDIDO.ranking), q)
  }
  for (const q of ['o Ibovespa vai a 250 mil?', 'o dólar chega a 10?', 'o dolar vai a 10?', 'o ibovespa chega a 200 mil?']) {
    assert(analisar(q).proibidos.includes('direcao'), q)
  }
  const recusa = new Set(T.PEDEM_RECUSA)
  for (const q of ['o WTI ficou abaixo de zero em 2020?', 'qual o preço médio da gasolina?', 'o que é custo de oportunidade?',
    'o que é posição vendida?', 'o Brent já passou de 150 alguma vez?', 'o brent passou de 100 em 2022?',
    'quando o barril bateu 130, o que aconteceu?', 'o que é a paridade de importação?',
    'como o Ibovespa reagiu ao dividendo extraordinário da Petrobras em 2024?']) {
    const p = analisar(q).proibidos
    assert(!p.some((x) => recusa.has(x)), `${q}: ${p}`)
  }
})

Deno.test('quem cita só a ação não recebe a história de um emissor nem o barril; o fato da Petrobras traz os eventos dela', () => {
  for (const q of ['vale a pena PETR4?', 'PETR4 é boa pagadora de dividendos?', 'PETR4 ou PRIO3, qual é melhor?', 'mantenho PETR4?']) {
    const r = montar(q, undefined, HOJE)
    assert(!r.blocos.some((b) => EVENTOS(b.titulo) || b.titulo.startsWith('Do barril à bomba')), q)
    assertEquals(r.violacoes, [], q)
  }
  const r = montar('troca de presidente da Petrobras', undefined, HOJE)
  assert(r.blocos.some((b) => b.titulo.startsWith('O que aconteceu antes: Petrobras')) && !ehEleicao(r.pedido))
})

Deno.test('a guerra do petróleo não puxa a geopolítica; o que o petróleo não cobre fica, sem tirar o Brent', () => {
  const r = montar('o petróleo vai subir com a guerra?', undefined, HOJE)
  assert(!r.blocos.some((b) => b.titulo.startsWith('O que aconteceu antes: geopolítica')))
  assert(r.curta[0].startsWith('O petróleo Brent está em US$'), r.curta[0])
  assert(analisar('Tarifas dos EUA e o Ibovespa').temas.includes('geopolitico'))
  const casos: [string, string][] = [['a pandemia derrubou a Petrobras?', 'choques de demanda'],
    ['a guerra da Ucrânia e a Petrobras', '24/02/2022'], ['tarifas dos EUA e a Petrobras', '10/07/2025'],
    ['a guerra comercial derrubou o petróleo?', '10/07/2025']]
  for (const [q, trecho] of casos) {
    const blocos = montar(q, undefined, HOJE).blocos
    const texto = [...blocos.map((b) => b.titulo), ...blocos.flatMap((b) => b.linhas.map((ln) => ln.texto))].join(' ')
    assert(texto.includes(trecho), `${q}: falta ${trecho}`)
    assert(blocos.some((b) => b.titulo.startsWith('O petróleo Brent até aqui')), q)
  }
  assert(titulos('vale a pena comprar Petrobras com a pandemia?').some((b) => b.startsWith(BASE.titulo_dois_lados)))
})

Deno.test('petróleo e inflação trazem o Focus; o petróleo sozinho não', () => {
  for (const q of ['o petróleo e a inflação', 'gasolina e IPCA']) {
    const r = montar(q, undefined, HOJE)
    const b = r.blocos.find((x) => x.titulo.startsWith('O que o mercado espera'))!
    assert(b.linhas.some((ln) => ln.texto.startsWith('IPCA:')), q)
    assertEquals(r.violacoes, [], q)
  }
  assert(!titulos('como está o petróleo?').some((b) => b.startsWith('O que o mercado espera')))
})

Deno.test('o presidente da Petrobras não é a eleição; a eleição continua eleição', () => {
  for (const q of ['troca de presidente da Petrobras', 'quando a petrobras troca de presidente a ação cai quanto?',
    'a OPEP vai cortar a produção domingo?', 'o presidente da petrobras caiu, e a ação?', 'quem é o presidente da Petrobras?',
    'quando o Bolsonaro trocou o presidente da Petrobras?', 'a Petrobras trocou de presidente?',
    'o Jair Bolsonaro trocou o presidente da Petrobras?']) {
    const p = analisar(q)
    assert(!ehEleicao(p) && p.candidatos.length === 0, `${q}: ${p.temas} ${p.candidatos}`)
  }
  for (const q of ['o que acontece com a Petrobras se o presidente mudar no domingo?', 'o que acontece domingo?',
    'o dólar e o novo presidente', 'como a bolsa reagiu à eleição do presidente?', 'quem vai ser presidente?',
    'se o Lula ganhar, troca o presidente da Petrobras?', 'o próximo presidente vai trocar o comando da Petrobras?',
    'presidente da Petrobras e o 2º turno', 'se o Flávio ganhar a Petrobras sobe?']) {
    assert(ehEleicao(analisar(q)), q)
  }
})

Deno.test('petróleo figurado não é petróleo; o de verdade continua', () => {
  for (const q of ['a eleição é um barril de pólvora, a bolsa cai?', 'a Selic é o combustível do dólar?',
    'o Copom jogou gasolina no dólar?', 'a guerra é o combustível da alta do dólar?', 'o Lula jogou gasolina na fogueira, e o dólar?']) {
    assert(!analisar(q).mercados.includes('petroleo'), q)
  }
  for (const q of ['o preço da gasolina vai subir?', 'o combustível do carro ficou mais caro?', 'quanto custa o barril?',
    'o barril de petróleo caiu?']) {
    assert(analisar(q).mercados.includes('petroleo'), q)
  }
})

Deno.test('o preço do barril não é o dinheiro da pessoa; o dinheiro dela ainda faz a conta; preço em reais não é capital', () => {
  for (const q of ['o petróleo passou de 100 dólares?', 'o Brent a 100 dólares é caro?', 'o barril a US$ 120, e a gasolina?',
    'quando o Brent passou de US$ 130?', 'o petróleo vai a 150 dólares?']) {
    const r = montar(q, undefined, HOJE)
    assert(r.pedido.valor_moeda === null && !r.pedido.mercados.includes('dolar'), q)
    assert(r.curta[0].startsWith('O petróleo Brent está em US$'), q)
    assert(!r.texto.includes('seus ') && r.violacoes.length === 0, q)
  }
  const p = analisar('tenho 5 mil dólares, o petróleo mexe com isso?')
  assert(p.valor_moeda === 5000 && p.moeda === 'dolar')
  for (const q of ['a Petrobras pagou dividendo de R$ 6,73 por ação?', 'os R$ 20 bilhões de dividendos da Petrobras',
    'a gasolina a R$ 6,53 é cara?', 'o dólar chegou a R$ 6,30 em 2024?']) {
    assert(!analisar(q).proibidos.includes('capital'), q)
  }
})

Deno.test('do barril à bomba: o barril em reais, sem litro de petróleo cru, com as limitações', () => {
  const b = BASE.petroleo.barril
  const conta = b.linhas.at(-1)!.texto
  assert(conta.includes('um barril custa R$') && !conta.includes('litro'), conta)
  assert(b.limites.some((x) => x.includes('só aritmética')) && b.limites.some((x) => x.includes('defasagem')))
})

Deno.test('o cartão do petróleo é o do 1º tema que a pergunta cita', async () => {
  const cartao = async (q: string) => (await analisarSite({ query: q, market: null, locale: 'pt-BR' }, null)).analysis.event.title
  const cartoes = (BASE as unknown as { cartoes: { petroleo: Record<string, { titulo: string }> } }).cartoes.petroleo
  assertEquals(await cartao('a OPEP e a guerra'), cartoes.opep.titulo)
  assertEquals(await cartao('o petróleo vai subir com a guerra?'), cartoes.guerra.titulo)
  assertEquals(await cartao('como está o petróleo?'), cartoes[''].titulo)
})

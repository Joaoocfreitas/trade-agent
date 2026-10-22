// Câmbio, euro e a conta com os números da pessoa (P4 de câmbio): o espelho de tests/test_cambio.py.
//
// A conta usa o dinheiro em moeda estrangeira e o gasto por mês que a pessoa contou só para fazer a conta: valor em
// reais pela cotação oficial, quanto muda a cada R$ 0,10 e quantos meses de gasto cobre. Nunca diz o que fazer, quando
// trocar nem quanto, e o registro não guarda o valor. Os esperados saíram do Python (.venv/bin/python) em 22/10/2026.
import { assert, assertEquals } from 'jsr:@std/assert@1.0.13'
import { responderPergunta } from './agente.ts'
import { analisar as analisarSite } from './analisar.ts'
import { frasesProibidas } from './filtro.ts'
import { leituraSemVoto, semDadoPessoal } from './registro.ts'
import { BASE, contaCambio, meses, montar, num } from './resposta.ts'
import { analisar, cambio, ehEleicao, normalizar, temContaCambio } from './roteador.ts'

const T = BASE.textos
const PRINT = 'to com uns 150 mil euros na espanha aplicados e faco trasnferencia internacional pela wise todo o mes oara pagar ' +
  'minha facuyldade aqui no brasil mas agora com o crescimento da ibovespa e a reducao do poder do euro em relacao ao ' +
  'crecimento no valor do real to perdendo poder de compra.Queria saber se agora com o segundo turno o real vai ' +
  'continuar a valorizar ou nao? e se deveria trazer esse dinheiro para o brasil'

Deno.test('lê o dinheiro e o gasto', () => {
  const casos: [string, ReturnType<typeof cambio>][] = [
    ['tenho US$ 20 mil e pago 3 mil dólares por mês de aluguel', [20000, 'dolar', 3000, 'dolar']],
    ['Tenho €150.000 na Espanha e gasto 5 mil reais por mês com a faculdade.', [150000, 'euro', 5000, 'real']],
    ['to com uns 150 mil euros na espanha', [150000, 'euro', null, null]],
    ['tenho 150k euros', [150000, 'euro', null, null]],
    ['gasto 2 mil euros por mês', [null, null, 2000, 'euro']], // o gasto não vira patrimônio
    ['mensalidade de R$ 4.500, tenho 1,2 milhão de euros', [1200000, 'euro', 4500, 'real']],
    ['EUR 80.000 parados no banco', [80000, 'euro', null, null]],
    ['tenho 50 mil em dólares e gasto R$ 3.000 por mês', [50000, 'dolar', 3000, 'real']],
    ['tenho R$ 10 mil, compro dólar?', [null, null, null, null]], // real não é moeda estrangeira: segue a recusa (N5)
    ['o euro caiu 12% no ano', [null, null, null, null]],
    ['tenho 1,2,3 euros', [null, null, null, null]], // o float() do Python levanta erro; o _quantia devolve None
  ]
  for (const [pergunta, esperado] of casos) assertEquals(cambio(normalizar(pergunta)), esperado, pergunta)
})

Deno.test('o print do site vira conta e recusa', () => {
  const p = analisar(PRINT)
  assert(temContaCambio(p) && p.valor_moeda === 150000 && p.moeda === 'euro')
  assert(p.mercados.includes('euro') && p.mercados.includes('dolar') && ehEleicao(p))
  assert(p.proibidos.includes('dica') && !p.proibidos.includes('capital'))
  const r = montar(PRINT, undefined, '2026-10-22')
  assertEquals(r.violacoes, [])
  assert(r.abertura.includes(T.RECUSA) && !r.abertura.includes(T.POR_PEDIDO.capital))
  assert(r.curta[0].startsWith('Seus 150.000 euros valem R$ '), r.curta[0])
  assert(r.curta[1].startsWith('Depois dos 2 segundos turnos desde 2018, o euro '), r.curta[1])
  assert(r.curta[2].startsWith('Os economistas que o Banco Central consulta'), r.curta[2])
  assert(r.curta[1].includes('não mostra o outro lado'))
})

Deno.test('"quanto eu trago" é alocação e não vira conta', () => {
  const q = 'tenho 150k euros, quanto eu trago pro brasil?'
  const p = analisar(q)
  assert(!temContaCambio(p) && p.proibidos.includes('capital'))
  assertEquals([p.valor_moeda, p.moeda, p.gasto_mensal, p.gasto_moeda], [null, null, null, null])
  const r = montar(q, undefined, '2026-10-22')
  assert(!r.blocos.some((b) => b.titulo === BASE.cambio.titulo))
  assert(!r.texto.includes('150.000'))
})

// As mesmas cotações fixas do teste do Python (C em tests/test_cambio.py).
const C = {
  data: '2026-10-22', valor: 5.6494, ano_data: '2025-12-31', ano_valor: 6.4692,
  min_data: '2026-10-09', min_valor: 5.5844, max_data: '2025-12-29', max_valor: 6.5594,
}

Deno.test('conta com gasto em reais', () => {
  const b = contaCambio(150000, 'euro', 5000, 'real', C)
  const textos = b.linhas.map((ln) => ln.texto)
  assertEquals(textos[0], '150.000 euros × R$ 5,6494 (cotação oficial do euro em 22/10/2026) = R$ 847.410.')
  assertEquals(textos[1], 'Cada R$ 0,10 de diferença na cotação do euro muda esse valor em R$ 15.000.')
  assert(textos[2].includes('davam R$ 970.380, R$ 122.970 a mais do que hoje'))
  assert(textos[3].includes('dariam de R$ 837.660 a R$ 983.910'))
  assert(textos[4].startsWith('Com gasto de R$ 5.000 por mês, R$ 847.410 cobrem 169 meses (cerca de 14 anos)'))
  assert(textos[4].includes('seriam 167 meses (cerca de 13 anos); na maior, 196 meses (cerca de 16 anos)'))
  assert(textos.at(-1)!.startsWith('É só a conta com os números que você contou: não diz o que fazer'))
  assert(b.resumo.endsWith('cobrem 169 meses (cerca de 14 anos).'))
  for (const t of [...textos, b.resumo]) assertEquals(frasesProibidas(t), [], t)
  // as fontes e o limite, como o Python montou
  const euro = BASE.cambio.moedas.euro.fonte
  assertEquals(b.linhas.map((ln) => ln.fontes), [[euro], [euro], [euro], [euro], [euro], []])
  assertEquals(b.limites, [BASE.cambio.limite_euro])
})

Deno.test('conta com gasto na própria moeda não usa a cotação', () => {
  const b = contaCambio(20000, 'dolar', 3000, 'dolar', C)
  assert(b.linhas.some((ln) => ln.texto.startsWith('Com gasto de 3.000 dólares por mês, os 20.000 dólares cobrem 6 meses')))
  // no dólar, o limite do euro troca "do euro" por "do dólar" (str.replace do Python)
  assertEquals(b.limites, ['Os números do dólar são da PTAX de venda do Banco Central. Na troca de verdade (banco, corretora, ' +
    'app de remessa), a cotação é outra e pode haver tarifa, spread e IOF.'])
  assertEquals(b.resumo, 'Seus 20.000 dólares valem R$ 112.988 pela cotação oficial de 22/10/2026; cada R$ 0,10 no dólar ' +
    'muda isso em R$ 2.000; com o seu gasto por mês, cobrem 6 meses.')
})

Deno.test('conta: quantia quebrada com centavos, real pequeno com centavos e "o mesmo que hoje"', () => {
  const b = contaCambio(0.5, 'euro', null, null, C)
  assertEquals(b.resumo, 'Seus 0,50 euros valem R$ 2,82 pela cotação oficial de 22/10/2026; cada R$ 0,10 no euro muda isso em R$ 0,05.')
  assertEquals(b.linhas[2].texto, 'No fim de 2025 (31/12/2025), 1 euro valia R$ 6,4692: os mesmos 0,50 euros davam R$ 3,23, R$ 0,41 a mais do que hoje.')
  assertEquals(b.linhas.length, 5) // sem gasto, sem a linha dos meses
  assertEquals(contaCambio(25, 'euro', null, null, C).linhas[1].texto, 'Cada R$ 0,10 de diferença na cotação do euro muda esse valor em R$ 2,50.')
  const igual = contaCambio(1000, 'euro', null, null, { ...C, ano_valor: C.valor })
  assert(igual.linhas[2].texto.endsWith('davam R$ 5.649, o mesmo que hoje.'), igual.linhas[2].texto)
})

Deno.test('meses nunca arredonda para cima', () => {
  const casos: [number, string][] = [[0.4, 'menos de 1 mês'], [1.9, '1 mês'], [23.9, '23 meses'], [24, '24 meses (cerca de 2 anos)'],
    [169.48, '169 meses (cerca de 14 anos)']]
  for (const [m, texto] of casos) assertEquals(meses(m), texto, String(m))
})

Deno.test('num: o arredondamento e o formato do f-string do Python', () => {
  const casos: [number, number, string][] = [[2.5, 0, '2'], [3.5, 0, '4'], [0.125, 2, '0,12'], [0.375, 2, '0,38'],
    [1e25, 0, '10.000.000.000.000.000.905.969.664'], [1.005, 2, '1,00'], [-0.4, 0, '0'], [-2.5, 0, '−2'],
    [1234567.891, 2, '1.234.567,89']]
  for (const [x, casas, texto] of casos) assertEquals(num(x, casas), texto, `${x}, ${casas}`)
})

Deno.test('o registro não guarda o dinheiro', () => {
  const p = analisar('Tenho €150.000 na Espanha e gasto 5 mil reais por mês com a faculdade.')
  const leitura = leituraSemVoto(p, p.pergunta)
  assertEquals(Object.keys(leitura).sort(), ['candidatos', 'mercados', 'proibidos', 'temas'])
  const limpo = semDadoPessoal(p.pergunta)
  assert(!limpo.includes('150') && !limpo.includes('5 mil'), limpo)
})

Deno.test('o que as funções gravam (auditoria do analyze e do perguntar) não leva o dinheiro do câmbio', async () => {
  const campos = ['valor_moeda', 'moeda', 'gasto_mensal', 'gasto_moeda']
  for (const q of [PRINT, 'Tenho €150.000 na Espanha e gasto 5 mil reais por mês com a faculdade. Como está o euro?',
    'tenho US$ 20 mil e pago 3 mil dólares por mês de aluguel', 'mensalidade de R$ 4.500, tenho 1,2 milhão de euros']) {
    assert(temContaCambio(analisar(q)), q) // a conta foi feita: o valor existia no pedido
    const { auditoria } = await analisarSite({ query: q, market: null, locale: 'pt-BR' }, null)
    const saida = await responderPergunta(q, null)
    for (const roteador of [auditoria.roteador, saida.roteador]) {
      assertEquals(Object.keys(roteador).sort(), ['candidatos', 'mercados', 'proibidos', 'temas'], q)
      for (const c of campos) assert(!(c in roteador), `${q}: ${c}`)
    }
  }
  // Na conta em euro, nada do que vai para a auditoria tem o número (nem a pergunta, que sai sem o valor).
  const q = 'Tenho €150.000 na Espanha e gasto 5 mil reais por mês com a faculdade. Como está o euro?'
  const { auditoria } = await analisarSite({ query: q, market: null, locale: 'pt-BR' }, null)
  const gravado = JSON.stringify(auditoria)
  for (const trecho of ['150', '5 mil', '5.000', '847']) assert(!gravado.includes(trecho), `${trecho} em ${gravado}`)
})

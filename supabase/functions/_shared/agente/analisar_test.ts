// O formato do site: o cartão sai da base, sem direção nem "hoje", e o texto é o mesmo de sempre.
import { assert, assertEquals } from 'jsr:@std/assert@1.0.13'
import { analisar } from './analisar.ts'
import { frasesProibidas } from './filtro.ts'
import { BASE, montar } from './resposta.ts'

const sem = (q: string, market: 'b3' | 'crypto' | 'global' | null = null) => analisar({ query: q, market, locale: 'pt-BR' }, null)

Deno.test('eleição: cartão dos 5 turnos, setas neutras, gráfico só do passado, texto igual', async () => {
  const q = 'Ibovespa: chance de subir se o Flávio ganhar o 2º turno?'
  const { analysis: a, auditoria } = await sem(q)
  assertEquals([a.event.title, a.precedents.count, a.precedents.items[0].asset], ['Os turnos presidenciais desde 2018', 5, 'Ibovespa'])
  assert(a.stats.every((s) => s.direction === 'neutral'))
  assertEquals(a.chart?.current, [])
  assertEquals(a.explanation, montar(q).texto)
  assertEquals(a.short, montar(q).texto_curto)
  assert(a.disclaimer.startsWith(BASE.textos.AVISO))
  assertEquals([auditoria.violacoes, a.filtered], [[], false])
})

Deno.test('nada do cartão acende o filtro', async () => {
  for (const q of ['Copom', 'O dólar no Copom', 'Juros e eleição', 'E as decisões fiscais?', 'Como a bolsa reage ao STF?']) {
    const { analysis: a } = await sem(q)
    const textos = [a.event.title, ...a.stats.flatMap((s) => [s.label, s.value]), ...a.precedents.items.map((i) => i.title)]
    assertEquals(textos.flatMap((t) => frasesProibidas(t)), [], q)
  }
})

Deno.test('sem caso parecido: cartão vazio, sem gráfico, mas o texto vem', async () => {
  const { analysis: a } = await sem('bom dia')
  assertEquals([a.precedents.count, a.chart, a.stats], [0, undefined, []])
  assert(a.explanation.length > 0)
})

Deno.test('o seletor de mercado cripto vira filtro', async () => {
  const { analysis: a } = await sem('O que aconteceu depois da eleição?', 'crypto')
  // D5 aparece uma vez: no bloco da cripto ou, sem ele, nos riscos
  assert(a.explanation.includes('não é valor mobiliário'))
})

Deno.test('a auditoria e o histórico do site não levam o voto nem o valor', async () => {
  const { analysis, auditoria } = await sem('Tenho R$ 5 mil e voto no Lula. E o dólar se ele ganhar?')
  assert(!auditoria.pergunta.includes('5 mil') && !auditoria.pergunta.includes('Lula'))
  assertEquals(analysis.query_redacted, auditoria.pergunta)
  assertEquals((auditoria.roteador as { candidatos: string[] }).candidatos, [])
})

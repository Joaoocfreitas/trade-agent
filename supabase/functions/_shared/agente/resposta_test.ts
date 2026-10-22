// Paridade do montador: a resposta inteira (texto, versão curta e violações) tem de sair igual à do Python.
import { assertEquals } from 'jsr:@std/assert@1.0.13'
import { montar } from './resposta.ts'
import type { Pedido, Violacao } from './texto.ts'

type Caso = {
  pergunta: string
  pedido: Omit<Pedido, 'pergunta'>
  texto: string
  texto_curto: string
  violacoes: Violacao[]
}
const gabarito = JSON.parse(await Deno.readTextFile(new URL('../../../../tests/dados/paridade.json', import.meta.url)))
const casos = gabarito.respostas as Caso[]
const hoje = gabarito.hoje as string // o dia em que o Python montou: decide as datas marcadas

Deno.test('montador: com o pedido do Python, a resposta sai igual', () => {
  for (const c of casos) {
    const r = montar(c.pergunta, { pergunta: c.pergunta, ...c.pedido }, hoje)
    assertEquals([r.texto, r.texto_curto, r.violacoes], [c.texto, c.texto_curto, c.violacoes], c.pergunta)
  }
})

Deno.test('agente inteiro: da pergunta à resposta, igual ao Python', () => {
  for (const c of casos) {
    const r = montar(c.pergunta, undefined, hoje)
    assertEquals([r.texto, r.texto_curto, r.violacoes], [c.texto, c.texto_curto, c.violacoes], c.pergunta)
  }
})

Deno.test('calendário: depois do 2º turno e do Copom, as datas somem sozinhas', () => {
  const q = 'devo comprar dolar hoje?'
  const datas = (dia: string) => montar(q, undefined, dia).texto
  assertEquals(datas('2026-10-22').includes('2º turno da eleição presidencial em 25/10'), true)
  assertEquals(datas('2026-10-26').includes('2º turno da eleição presidencial em 25/10'), false)
  assertEquals(datas('2026-10-26').includes('decisão do Copom (o comitê do Banco Central que define a Selic) em 04/11'), true)
  assertEquals(datas('2026-11-05').includes('decisão do Copom (o comitê do Banco Central que define a Selic) em 04/11'), false)
  assertEquals(datas('2026-11-05').includes('decisão do Copom (o comitê do Banco Central que define a Selic) em 09/12'), true)
  assertEquals(datas('2028-01-01').includes('Datas marcadas no calendário oficial'), false)
})

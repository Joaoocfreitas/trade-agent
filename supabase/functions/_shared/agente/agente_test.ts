// A leitura pela IA, com um cliente falso: soma com as palavras-chave, não inventa rótulo, e falha cai nas palavras.
import { assert, assertEquals } from 'jsr:@std/assert@1.0.13'
import type Anthropic from 'npm:@anthropic-ai/sdk@0.132.1'
import { responderPergunta } from './agente.ts'
import { BASE, montar } from './resposta.ts'

function falso(conteudo: unknown, parada = 'end_turn'): { cliente: Anthropic; pedidos: Record<string, unknown>[] } {
  const pedidos: Record<string, unknown>[] = []
  const texto = typeof conteudo === 'string' ? conteudo : JSON.stringify(conteudo)
  const cliente = {
    beta: {
      messages: {
        create: (p: Record<string, unknown>) => {
          pedidos.push(p)
          return Promise.resolve({
            content: [{ type: 'thinking', thinking: '' }, { type: 'text', text: texto }],
            stop_reason: parada,
            usage: { input_tokens: 10, output_tokens: 20 },
          })
        },
      },
    },
  }
  return { cliente: cliente as unknown as Anthropic, pedidos }
}
const leitura = (k: Record<string, unknown> = {}) => ({ mercados: [], candidatos: [], temas: [], proibidos: [], voto_informado: false, ...k })

Deno.test('a IA lê a gíria que as palavras-chave não pegam, e não escreve a resposta', async () => {
  const pergunta = 'E o verdinho, aguenta firme com o barba lá?'
  assert(!montar(pergunta).texto.includes(BASE.textos.RECUSA))
  const { cliente, pedidos } = falso(leitura({ mercados: ['dolar'], candidatos: ['lula'], temas: ['eleicao'], proibidos: ['direcao'] }))
  const s = await responderPergunta(pergunta, cliente)
  assert(s.modo.startsWith('IA') && s.texto.includes(BASE.textos.RECUSA) && s.texto.includes('turnos presidenciais'))
  assertEquals(s.violacoes, [])
  const p = pedidos[0] as { output_config: { format: { type: string } }; fallbacks: string }
  assertEquals([p.output_config.format.type, p.fallbacks], ['json_schema', 'default'])
})

Deno.test('a IA não tira recusa nem inventa rótulo', async () => {
  const s = await responderPergunta('compro?', falso(leitura({ proibidos: ['inventado'], mercados: ['marte'] })).cliente)
  assert(s.texto.includes(BASE.textos.RECUSA))
  assertEquals([s.ia?.leitura?.proibidos, s.ia?.leitura?.mercados], [[], []])
})

Deno.test('IA que falha cai nas palavras-chave', async () => {
  const pergunta = 'Ibovespa: chance de subir se o Flávio ganhar o 2º turno?'
  for (const [conteudo, parada] of [[leitura({ proibidos: ['dica'] }), 'refusal'], ['não é json', 'end_turn'], ['[1, 2]', 'end_turn']] as const) {
    const s = await responderPergunta(pergunta, falso(conteudo, parada).cliente)
    assert(s.ia?.erro && s.ia.leitura === null && s.modo.startsWith('palavras-chave'))
    assertEquals(s.texto, montar(pergunta).texto)
  }
})

Deno.test('sem chave, responde sem IA e sem dado pessoal', async () => {
  const s = await responderPergunta('Tenho R$ 5 mil e voto no Lula. Quantos contratos de WIN?', null)
  assertEquals([s.modo, s.ia, s.violacoes], ['sem IA', null, []])
  assert(!s.pergunta.includes('5 mil') && !s.pergunta.includes('Lula'))
})

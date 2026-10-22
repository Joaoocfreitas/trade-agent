// O agente dentro da função: lê a pergunta (palavras-chave e, se houver chave da Anthropic, a IA), monta a resposta
// da base e devolve o que a função grava. Tradução de agente/ia.py e de agente/api.py.
//
// A IA não escreve a resposta: só classifica a pergunta numa lista fechada, com saída estruturada, e essa leitura se
// soma à das palavras-chave. Na dúvida, mais recusa, nunca menos (ataque de 22/10/2026, ver o README do projeto).
import Anthropic from 'npm:@anthropic-ai/sdk@0.132.1'
import { BASE, montar } from './resposta.ts'
import { iaSemVoto, leituraSemVoto, semDadoPessoal } from './registro.ts'
import { CANDIDATOS, MERCADOS, PROIBIDOS, TEMAS, analisar, somar } from './roteador.ts'
import type { Pedido, Violacao } from './texto.ts'

const MODELO = Deno.env.get('TRADE_AGENTE_MODELO') ?? 'claude-opus-5-5'
const ESFORCO = Deno.env.get('TRADE_AGENTE_ESFORCO') ?? 'low'
// Modelos com troca automática no servidor quando o classificador de segurança recusa (o Haiku não tem).
const COM_FALLBACK = new Set(['claude-opus-5-5', 'claude-opus-5', 'claude-fable-5-1', 'claude-sonnet-5-5'])
const INSTRUCOES = (BASE.textos as unknown as { INSTRUCOES_IA: string }).INSTRUCOES_IA

const lista = (tabela: Record<string, unknown>) => ({ type: 'array', items: { type: 'string', enum: Object.keys(tabela).sort() } })
const ESQUEMA = {
  type: 'object',
  properties: {
    mercados: lista(MERCADOS),
    candidatos: lista(CANDIDATOS),
    temas: lista(TEMAS),
    proibidos: lista(PROIBIDOS),
    voto_informado: { type: 'boolean' },
  },
  required: ['mercados', 'candidatos', 'temas', 'proibidos', 'voto_informado'],
  additionalProperties: false,
}

export type Leitura = { mercados: string[]; candidatos: string[]; temas: string[]; proibidos: string[]; voto_informado: boolean }
export type Ia = { modelo: string; erro: string | null; leitura: Leitura | null }
export type Saida = {
  pergunta: string
  texto: string
  texto_curto: string
  modo: string
  roteador: Record<string, unknown>
  violacoes: Violacao[]
  ia: Ia | null
  uso: Record<string, unknown>
}

/** O cliente da API, se houver chave; prazo curto e uma repetição só, porque classificar leva poucos segundos. */
export function clientePadrao(): Anthropic | null {
  const chave = Deno.env.get('ANTHROPIC_API_KEY')
  return chave ? new Anthropic({ apiKey: chave, timeout: 25_000, maxRetries: 1 }) : null
}

const soValidos = (valores: unknown, permitidos: Record<string, unknown>): string[] =>
  Array.isArray(valores) ? valores.filter((v): v is string => typeof v === 'string' && v in permitidos) : []

/** A leitura da IA (ou null), o uso de tokens e o motivo, se ela não leu. */
export async function entender(pergunta: string, cliente: Anthropic): Promise<{ leitura: Pedido | null; uso: Record<string, unknown>; erro: string | null }> {
  const pedido: Record<string, unknown> = {
    model: MODELO,
    max_tokens: 4000,
    output_config: { effort: ESFORCO, format: { type: 'json_schema', schema: ESQUEMA } },
    system: [{ type: 'text', text: INSTRUCOES, cache_control: { type: 'ephemeral' } }],
    messages: [{ role: 'user', content: `<pergunta>\n${pergunta}\n</pergunta>` }],
  }
  if (COM_FALLBACK.has(MODELO)) Object.assign(pedido, { betas: ['server-side-fallback-2026-07-01'], fallbacks: 'default' })
  let msg: Anthropic.Beta.BetaMessage
  try {
    msg = await cliente.beta.messages.create(pedido as unknown as Anthropic.Beta.MessageCreateParamsNonStreaming)
  } catch (e) {
    if (e instanceof Anthropic.APIConnectionError) return { leitura: null, uso: {}, erro: `sem conexão com a API: ${e.message}` }
    if (e instanceof Anthropic.APIError) return { leitura: null, uso: {}, erro: `erro da API (${e.status}): ${e.message}` }
    throw e
  }
  const uso = (msg.usage ?? {}) as unknown as Record<string, unknown>
  if (msg.stop_reason === 'refusal' || msg.stop_reason === 'max_tokens') {
    return { leitura: null, uso, erro: `a IA parou por ${msg.stop_reason}` }
  }
  const bloco = msg.content.find((b) => b.type === 'text')
  let d: unknown
  try {
    d = JSON.parse(bloco && bloco.type === 'text' ? bloco.text : '')
  } catch {
    return { leitura: null, uso, erro: 'a IA devolveu JSON inválido' }
  }
  if (typeof d !== 'object' || d === null || Array.isArray(d)) return { leitura: null, uso, erro: 'a IA devolveu JSON inválido' }
  const o = d as Record<string, unknown>
  const leitura: Pedido = {
    pergunta,
    mercados: soValidos(o.mercados, MERCADOS),
    candidatos: soValidos(o.candidatos, CANDIDATOS),
    temas: soValidos(o.temas, TEMAS),
    proibidos: soValidos(o.proibidos, PROIBIDOS),
    voto_informado: o.voto_informado === true,
    pontos: null,
    contratos: 1,
  }
  return { leitura, uso, erro: null }
}

/** A leitura da pergunta: palavras-chave somadas à IA (se houver chave), o que a IA leu e o uso de tokens. */
export async function lerPergunta(pergunta: string, cliente: Anthropic | null = clientePadrao()):
  Promise<{ pedido: Pedido; ia: Ia | null; uso: Record<string, unknown>; modo: string }> {
  const palavras = analisar(pergunta)
  if (!cliente) return { pedido: palavras, ia: null, uso: {}, modo: 'sem IA' }
  const r = await entender(pergunta, cliente)
  return {
    pedido: r.leitura ? somar(palavras, r.leitura) : palavras,
    ia: {
      modelo: MODELO, erro: r.erro, leitura: r.leitura && {
        mercados: r.leitura.mercados, candidatos: r.leitura.candidatos, temas: r.leitura.temas, proibidos: r.leitura.proibidos,
        voto_informado: r.leitura.voto_informado,
      },
    },
    uso: r.uso,
    modo: r.leitura ? `IA (${MODELO}) + palavras-chave` : 'palavras-chave (a IA não leu a pergunta)',
  }
}

/** A resposta e o que a função grava (pergunta sem dado pessoal, leituras sem voto, violações, uso de tokens). */
export async function responderPergunta(pergunta: string, cliente: Anthropic | null = clientePadrao()): Promise<Saida> {
  const { pedido, ia, uso, modo } = await lerPergunta(pergunta, cliente)
  const resposta = montar(pergunta, pedido)
  return {
    pergunta: semDadoPessoal(pergunta),
    texto: resposta.texto,
    texto_curto: resposta.texto_curto,
    modo,
    roteador: leituraSemVoto(resposta.pedido, pergunta),
    violacoes: resposta.violacoes,
    ia: iaSemVoto(ia, resposta.pedido, pergunta) as Ia | null,
    uso,
  }
}

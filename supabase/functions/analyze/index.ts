// analyze: a API do agente para o site Thoran. O /agent-proxy do site (que confere login e créditos) chama
// POST {AGENT_API_URL}/analyze com `Authorization: Bearer AGENT_API_KEY` e { query, market, locale }.
// Responde AnalysisResponse em JSON (contrato em thoran/src/services/agent/types.ts) e grava a auditoria da regra M10
// (pergunta sem dado pessoal, leitura do roteador e da IA, violações, uso de tokens) em public.auditoria_agente.
//
// Segredos: AGENT_API_KEY (o mesmo que o proxy usa) e, opcional, ANTHROPIC_API_KEY. Publicar com --no-verify-jwt:
// quem chama é o servidor do site, com a chave dele, não uma pessoa logada.
import { createClient } from 'npm:@supabase/supabase-js@2.117.3'
import { analisar, type Mercado } from '../_shared/agente/analisar.ts'

const MAX_CARACTERES = 2000 // o proxy já corta em 2000
const CONTROLE = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/
const MERCADOS = new Set(['b3', 'crypto', 'global'])

function json(corpo: unknown, status = 200): Response {
  return new Response(JSON.stringify(corpo), { status, headers: { 'Content-Type': 'application/json' } })
}

/** Compara em tempo constante, para a chave não vazar pelo tempo de resposta. */
function iguais(a: string, b: string): boolean {
  const x = new TextEncoder().encode(a), y = new TextEncoder().encode(b)
  let dif = x.length ^ y.length
  for (let i = 0; i < Math.max(x.length, y.length); i++) dif |= (x[i] ?? 0) ^ (y[i] ?? 0)
  return dif === 0
}

function chaveSecreta(): string | undefined {
  const nova = Deno.env.get('SUPABASE_SECRET_KEYS')
  if (nova) {
    try {
      const k = (JSON.parse(nova) as Record<string, string>).default
      if (k) return k
    } catch {
      // não é JSON: segue para a antiga
    }
  }
  return Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')
}

Deno.serve(async (req) => {
  if (req.method !== 'POST') return json({ error: 'Use POST.' }, 405)
  const chave = Deno.env.get('AGENT_API_KEY')
  if (!chave || !iguais(req.headers.get('Authorization') ?? '', `Bearer ${chave}`)) return json({ error: 'não autorizado' }, 401)

  const corpo: unknown = await req.json().catch(() => null)
  const o = typeof corpo === 'object' && corpo !== null ? corpo as Record<string, unknown> : {}
  const query = typeof o.query === 'string' ? o.query.trim() : ''
  const market = typeof o.market === 'string' && MERCADOS.has(o.market) ? o.market as Mercado : null
  if (!query || query.length > MAX_CARACTERES || CONTROLE.test(query)) return json({ error: 'pergunta inválida' }, 400)

  const { analysis, auditoria } = await analisar({ query, market, locale: 'pt-BR' })

  const url = Deno.env.get('SUPABASE_URL')
  const secreta = chaveSecreta()
  if (url && secreta) {
    const admin = createClient(url, secreta, { auth: { persistSession: false } })
    const { error } = await admin.from('auditoria_agente').insert({ analise_id: analysis.id, ...auditoria })
    if (error) console.error('não gravou a auditoria:', error.message)
  }
  return json(analysis)
})

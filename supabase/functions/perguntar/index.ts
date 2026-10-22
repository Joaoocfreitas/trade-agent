// perguntar: o site chama esta função com o login da pessoa. Ela reserva a vaga da cota no banco (termos e limite
// conferidos numa transação só), roda o agente aqui mesmo (agente/, tradução do Python com paridade testada), grava a
// resposta e a auditoria, e devolve a resposta. Se o agente falhar, a reserva é desfeita e a pergunta não conta.
//
// Contrato: POST { pergunta } → 200 { data: { id, criada_em, texto, texto_curto, modo, cota } } ou { error, code }.
// Segredos (Supabase → Edge Functions → Secrets), todos opcionais: ANTHROPIC_API_KEY (liga a leitura da pergunta pela
// IA), TRADE_AGENTE_MODELO e SITE_ORIGEM.
// As chaves do projeto o Supabase já injeta: as novas (SUPABASE_PUBLISHABLE_KEYS, SUPABASE_SECRET_KEYS) ou as antigas
// (SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY). Publicar com --no-verify-jwt: o login é conferido aqui, por getUser.
import { createClient } from 'npm:@supabase/supabase-js@2.117.3'
import { responderPergunta } from '../_shared/agente/agente.ts'

const MAX_CARACTERES = 1000
const CONTROLE = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/

type Cota = { plano: string; limite: number; usadas: number; aceitou_termos: boolean }
type Reserva = { ok: boolean; motivo?: string; id?: number; cota?: Cota }

const cors = {
  'Access-Control-Allow-Origin': Deno.env.get('SITE_ORIGEM') ?? '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
}

function json(corpo: unknown, status = 200): Response {
  return new Response(JSON.stringify(corpo), { status, headers: { ...cors, 'Content-Type': 'application/json' } })
}

/** A chave nova (JSON com a "default") ou, se não houver, a antiga. */
function chave(nova: string, antiga: string): string | undefined {
  const bruto = Deno.env.get(nova)
  if (bruto) {
    try {
      const k = (JSON.parse(bruto) as Record<string, string>).default
      if (k) return k
    } catch {
      // não é JSON: segue para a antiga
    }
  }
  return Deno.env.get(antiga)
}

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: cors })
  if (req.method !== 'POST') return json({ error: 'Use POST.', code: 'metodo' }, 405)

  const url = Deno.env.get('SUPABASE_URL')
  const publica = chave('SUPABASE_PUBLISHABLE_KEYS', 'SUPABASE_ANON_KEY')
  const secreta = chave('SUPABASE_SECRET_KEYS', 'SUPABASE_SERVICE_ROLE_KEY')
  if (!url || !publica || !secreta) {
    return json({ error: 'O agente ainda não está configurado.', code: 'configuracao' }, 503)
  }

  // Quem pergunta: o token do login da pessoa.
  const comoUsuario = createClient(url, publica, {
    global: { headers: { Authorization: req.headers.get('Authorization') ?? '' } },
    auth: { persistSession: false },
  })
  const { data: quem } = await comoUsuario.auth.getUser()
  if (!quem.user) return json({ error: 'Entre na sua conta para perguntar.', code: 'sem_login' }, 401)

  const corpo: unknown = await req.json().catch(() => null)
  const bruta = typeof corpo === 'object' && corpo !== null ? (corpo as Record<string, unknown>).pergunta : undefined
  const pergunta = typeof bruta === 'string' ? bruta.trim() : ''
  if (!pergunta || pergunta.length > MAX_CARACTERES || CONTROLE.test(pergunta)) {
    return json({ error: `Escreva uma pergunta de até ${MAX_CARACTERES} caracteres.`, code: 'pergunta_invalida' }, 400)
  }

  // A vaga é reservada antes de chamar o agente, com o perfil travado: pedidos em paralelo esperam um pelo outro.
  const admin = createClient(url, secreta, { auth: { persistSession: false } })
  const { data: reservaBruta, error: erroReserva } = await admin.rpc('reservar_pergunta', { p_usuario: quem.user.id })
  const reserva = reservaBruta as Reserva | null
  if (erroReserva || !reserva) {
    console.error('reserva falhou:', erroReserva?.message)
    return json({ error: 'Não consegui registrar a pergunta. Tente de novo.', code: 'registro' }, 500)
  }
  if (!reserva.ok) {
    if (reserva.motivo === 'termos') {
      return json({ error: 'Para perguntar, aceite antes os termos de uso.', code: 'termos', cota: reserva.cota }, 403)
    }
    if (reserva.motivo === 'cota') {
      return json({ error: `Você já fez as ${reserva.cota?.limite} perguntas desta semana.`, code: 'cota', cota: reserva.cota }, 429)
    }
    return json({ error: 'Não achei o seu perfil. Tente sair e entrar de novo.', code: 'perfil' }, 500)
  }
  const id = reserva.id as number
  const desfazer = async () => {
    const { error } = await admin.from('perguntas').delete().eq('id', id).eq('status', 'pendente')
    if (error) console.error('não desfez a reserva:', error.message)
  }

  let agente: Awaited<ReturnType<typeof responderPergunta>>
  try {
    agente = await responderPergunta(pergunta)
  } catch (e) {
    console.error('o agente falhou:', e instanceof Error ? e.message : e)
    await desfazer()
    return json({ error: 'O agente não respondeu agora. Tente de novo em instantes.', code: 'agente' }, 502)
  }

  const { data: linha, error: erroGravar } = await admin
    .from('perguntas')
    .update({
      status: 'respondida',
      pergunta: agente.pergunta,
      // A conta de câmbio leva o dinheiro da pessoa ("Seus 150.000 euros valem..."): essa resposta não fica guardada.
      resposta: agente.conta_cambio ? null : agente.texto,
      resposta_curta: agente.conta_cambio ? null : agente.texto_curto,
      modo: agente.modo,
    })
    .eq('id', id)
    .select('id, criada_em')
    .single()
  if (erroGravar || !linha) {
    // A vaga continua reservada: a pergunta conta, mesmo sem a resposta gravada.
    console.error('não gravou a resposta:', erroGravar?.message)
    return json({ error: 'Não consegui registrar a resposta. Tente de novo.', code: 'registro' }, 500)
  }
  const { error: erroAuditoria } = await admin.from('auditoria').insert({
    pergunta_id: id,
    roteador: agente.roteador ?? {},
    violacoes: agente.violacoes ?? [],
    ia: agente.ia ?? null,
    uso: agente.uso ?? {},
  })
  if (erroAuditoria) console.error('não gravou a auditoria:', erroAuditoria.message)

  return json({
    data: {
      id: linha.id,
      criada_em: linha.criada_em,
      texto: agente.texto,
      texto_curto: agente.texto_curto,
      modo: agente.modo,
      cota: reserva.cota,
    },
  })
})

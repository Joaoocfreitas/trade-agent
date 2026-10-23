// O agente no formato que o site Thoran espera (POST /analyze → AnalysisResponse, contrato em
// thoran/src/services/agent/types.ts). O texto é o mesmo de sempre, montado da base; o cartão sai de base.json
// (agente/cartoes.py), com os mesmos números do texto.
//
// O que o cartão cumpre (nota de regras): distribuição inteira e estatística sem direção (P2, N3: toda seta é neutra);
// gráfico só do passado, sem "hoje" (N2, N6: current vazio); nada de semelhança nem relevância, que o agente não tem.
// Se o filtro barrar o texto, o cartão também some.
import type Anthropic from 'npm:@anthropic-ai/sdk@0.132.1'
import { lerPergunta } from './agente.ts'
import { iaSemVoto, leituraSemVoto, semDadoPessoal, violacoesSemDinheiro } from './registro.ts'
import { BASE, mercadosMedidos, montar, temaPetroleo } from './resposta.ts'
import { ehEleicao, normalizar } from './roteador.ts'
import type { Pedido, Violacao } from './texto.ts'

export type Mercado = 'b3' | 'crypto' | 'global'
export type AnalyzeRequest = { query: string; market: Mercado | null; locale: string }

type Cartao = {
  titulo: string
  periodo: { de: string; ate: string }
  ativo: string
  unidade: string
  janela: string
  itens: { data: string; dia_da_reacao: string; titulo: string; valor: number }[]
  stats: { label: string; value: string }[]
  caminhos: number[][]
  indice_d0: number
  fonte: string
}
type Cartoes = {
  eleicoes: Record<string, Cartao>; copom: Record<string, Cartao>; eventos: Record<string, Cartao>; petroleo: Record<string, Cartao>
}
const CARTOES = (BASE as unknown as { cartoes: Cartoes }).cartoes

export type AnalysisResponse = {
  id: string
  event: { title: string; detected_at: string }
  precedents: {
    count: number
    period: { from: string; to: string }
    items: { date: string; title: string; asset: string; move_pct: number; unit: string; window: string }[]
  }
  stats: { label: string; value: string; direction: 'neutral' }[]
  chart?: { unit: string; now_index: number; current: number[]; precedents: number[][] }
  explanation: string
  short: string
  disclaimer: string
  source?: string
  /** A pergunta sem o trecho de voto e sem valor em dinheiro (N9): é ela que o site guarda no histórico. */
  query_redacted: string
  /** O filtro de saída barrou o texto e a resposta é a mensagem de segurança: o site não cobra por isso. */
  filtered: boolean
}

export type Auditoria = {
  pergunta: string
  modo: string
  roteador: Record<string, unknown>
  violacoes: Violacao[]
  ia: unknown
  uso: Record<string, unknown>
}

/** O cartão do primeiro bloco "o que aconteceu antes" que a resposta mostra (mesma ordem de escolherBlocos). */
export function escolherCartao(p: Pedido): Cartao | null {
  if (ehEleicao(p)) return CARTOES.eleicoes[mercadosMedidos(p.mercados).join(',')] ?? null
  if (p.temas.includes('copom')) return CARTOES.copom[p.mercados.length ? mercadosMedidos(p.mercados).join(',') : ''] ?? null
  // Petróleo: o cartão dos eventos de petróleo do tema (Brent), o mesmo bloco que o texto mostra; a guerra e o choque
  // externo da linha do tempo genérica (só Ibovespa) não aparecem no texto de uma pergunta de petróleo.
  if (p.mercados.includes('petroleo')) return CARTOES.petroleo[temaPetroleo(normalizar(p.pergunta))] ?? null
  for (const tipo of BASE.tipos) if (p.temas.includes(tipo)) return CARTOES.eventos[tipo] ?? null
  return null
}

/** O seletor de mercado do site vira filtro de busca (P3): "cripto" entra como mercado; B3 e global não mudam nada. */
function comMercado(p: Pedido, market: Mercado | null): Pedido {
  return market === 'crypto' && !p.mercados.includes('cripto') ? { ...p, mercados: [...p.mercados, 'cripto'] } : p
}

export async function analisar(req: AnalyzeRequest, cliente?: Anthropic | null):
  Promise<{ analysis: AnalysisResponse; auditoria: Auditoria }> {
  const lida = cliente === undefined ? await lerPergunta(req.query) : await lerPergunta(req.query, cliente)
  const pedido = comMercado(lida.pedido, req.market)
  const r = montar(req.query, pedido)
  const cartao = r.violacoes.length ? null : escolherCartao(pedido)
  const analysis: AnalysisResponse = {
    id: crypto.randomUUID(),
    event: { title: cartao?.titulo ?? 'Sem caso parecido no repertório', detected_at: new Date().toISOString() },
    precedents: {
      count: cartao?.itens.length ?? 0,
      period: cartao ? { from: cartao.periodo.de, to: cartao.periodo.ate } : { from: '', to: '' },
      items: cartao?.itens.map((i) => ({
        date: i.data, title: i.titulo, asset: cartao.ativo, move_pct: i.valor, unit: cartao.unidade, window: cartao.janela,
      })) ?? [],
    },
    stats: cartao?.stats.map((s) => ({ ...s, direction: 'neutral' as const })) ?? [],
    chart: cartao && cartao.caminhos.length
      ? { unit: cartao.unidade, now_index: cartao.indice_d0, current: [], precedents: cartao.caminhos }
      : undefined,
    explanation: r.texto,
    short: r.texto_curto,
    disclaimer: `${BASE.textos.AVISO} ${BASE.textos.FECHO}`,
    source: cartao?.fonte,
    query_redacted: semDadoPessoal(req.query),
    filtered: r.violacoes.length > 0,
  }
  const auditoria: Auditoria = {
    pergunta: analysis.query_redacted,
    modo: lida.modo,
    roteador: leituraSemVoto(pedido, req.query),
    violacoes: violacoesSemDinheiro(r.violacoes, pedido),
    ia: iaSemVoto(lida.ia, pedido, req.query),
    uso: lida.uso,
  }
  return { analysis, auditoria }
}

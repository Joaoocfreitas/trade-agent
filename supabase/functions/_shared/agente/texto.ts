// O que os módulos do agente em TypeScript compartilham. É a tradução de agente/*.py; o Python continua sendo o dono
// dos dados e dos testes, e tests/dados/paridade.json prova que os dois respondem igual.

/** Minúsculas e sem acento, mas com pontuação ($, %, vírgula): o mesmo que `simples` em agente/roteador.py. */
export function simples(s: string): string {
  // O Deno usa Unicode 16, e o Python de referência, 15.0. As únicas letras e dígitos que o NFKD novo leva para ASCII
  // são os "contornados" U+1CCD6–U+1CCF9; o Python os apaga, então aqui também (teste em texto_test.ts).
  return s.replace(/[\u{1CCD6}-\u{1CCF9}]/gu, '').normalize('NFKD').replace(/[^\x00-\x7F]/g, '').toLowerCase()
}

export type Pedido = {
  pergunta: string
  mercados: string[]
  candidatos: string[]
  temas: string[]
  proibidos: string[]
  voto_informado: boolean
  pontos: number | null
  contratos: number
  /** P4 de câmbio: o dinheiro em moeda estrangeira que a pessoa contou, só para a conta. O registro nunca guarda
   * (leituraSemVoto em registro.ts só leva mercados, candidatos, temas e proibidos). */
  valor_moeda: number | null
  moeda: string | null
  gasto_mensal: number | null
  gasto_moeda: string | null
}

export type Violacao = { regra: string; trecho: string }

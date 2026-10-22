// Paridade do roteador com o Python: para cada pergunta do gabarito (tests/dados/paridade.json, campo respostas),
// analisar() tem de devolver o mesmo pedido que agente/roteador.py, na mesma ordem.
import { analisar, ehEleicao, normalizar, resumo, somar, temConta } from './roteador.ts'
import type { Pedido } from './texto.ts'

type Esperado = Omit<Pedido, 'pergunta'>
type Caso = { pergunta: string; pedido: Esperado }

function ehObjeto(x: unknown): x is Record<string, unknown> {
  return typeof x === 'object' && x !== null && !Array.isArray(x)
}

function ehListaDeTextos(x: unknown): x is string[] {
  return Array.isArray(x) && x.every((v) => typeof v === 'string')
}

function ehEsperado(x: unknown): x is Esperado {
  return ehObjeto(x) && ehListaDeTextos(x.mercados) && ehListaDeTextos(x.candidatos) && ehListaDeTextos(x.temas) &&
    ehListaDeTextos(x.proibidos) && typeof x.voto_informado === 'boolean' &&
    (x.pontos === null || typeof x.pontos === 'number') && typeof x.contratos === 'number' &&
    (x.valor_moeda === null || typeof x.valor_moeda === 'number') && (x.moeda === null || typeof x.moeda === 'string') &&
    (x.gasto_mensal === null || typeof x.gasto_mensal === 'number') &&
    (x.gasto_moeda === null || typeof x.gasto_moeda === 'string')
}

async function casos(): Promise<Caso[]> {
  const bruto: unknown = JSON.parse(await Deno.readTextFile(new URL('../../../../tests/dados/paridade.json', import.meta.url)))
  if (!ehObjeto(bruto) || !Array.isArray(bruto.respostas)) throw new Error('gabarito sem o campo respostas')
  return bruto.respostas.map((r: unknown, i: number): Caso => {
    if (!ehObjeto(r) || typeof r.pergunta !== 'string' || !ehEsperado(r.pedido)) throw new Error(`resposta ${i} malformada`)
    return { pergunta: r.pergunta, pedido: r.pedido }
  })
}

/** Só os campos do gabarito, na ordem dele: o JSON dos dois tem de sair idêntico. */
function semPergunta(p: Pedido): Esperado {
  return {
    mercados: p.mercados, candidatos: p.candidatos, temas: p.temas, proibidos: p.proibidos,
    voto_informado: p.voto_informado, pontos: p.pontos, contratos: p.contratos,
    valor_moeda: p.valor_moeda, moeda: p.moeda, gasto_mensal: p.gasto_mensal, gasto_moeda: p.gasto_moeda,
  }
}

function igual(a: unknown, b: unknown, onde: string): void {
  const [x, y] = [JSON.stringify(a), JSON.stringify(b)]
  if (x !== y) throw new Error(`${onde}\n  esperado: ${y}\n  veio:     ${x}`)
}

Deno.test('analisar: paridade exata com o Python em todas as perguntas do gabarito', async () => {
  const todos = await casos()
  if (todos.length < 136) throw new Error(`gabarito com ${todos.length} perguntas, esperava 136`)
  const erros: string[] = []
  for (const c of todos) {
    const [veio, esperado] = [JSON.stringify(semPergunta(analisar(c.pergunta))), JSON.stringify(c.pedido)]
    if (veio !== esperado) erros.push(`${JSON.stringify(c.pergunta)}\n  esperado: ${esperado}\n  veio:     ${veio}`)
  }
  if (erros.length) throw new Error(`${erros.length} de ${todos.length} diferentes:\n${erros.join('\n')}`)
})

Deno.test('analisar guarda a pergunta original, sem normalizar', () => {
  igual(analisar('Vc acha q o dólar 📈?').pergunta, 'Vc acha q o dólar 📈?', 'pergunta')
})

// Os casos abaixo saíram do Python (.venv/bin/python, agente/roteador.py) em 22/10/2026.
Deno.test('normalizar: emoji, acento e abreviação', () => {
  igual(normalizar('Vc acha q o Ibov ⬆️ ou ⬇ amanhã? 🚀'), 'voce acha que o ibovespa  sobe  ou  cai  amanha?  dispara ', 'normalizar')
  igual(normalizar('constructor toString'), 'constructor tostring', 'chave do Object não é abreviação')
})

Deno.test('o "." do Python casa \\r e o \\s inclui \\x1c-\\x1f', () => {
  igual(semPergunta(analisar('melhor\rx ou y')).proibidos, ['comparar'], '\\r no meio do .{0,40}')
  igual(semPergunta(analisar('mini indice 1.000\x1cpontos 2 contratos')),
    {
      mercados: ['mini_indice', 'ibovespa'], candidatos: [], temas: [], proibidos: [], voto_informado: false, pontos: 1000, contratos: 2,
      valor_moeda: null, moeda: null, gasto_mensal: null, gasto_moeda: null,
    },
    '\\x1c antes de pontos')
  igual(semPergunta(analisar('a\x1fb\x1cc\x1dd\x1ee sobe')).proibidos, [], 'split() do Python conta \\x1c-\\x1f como espaço')
})

Deno.test('pontos: "1,5,3" é erro, como o float() do Python', () => {
  let falhou = false
  try {
    analisar('mini indice 1,5,3 pontos')
  } catch {
    falhou = true
  }
  igual(falhou, true, 'devia lançar erro')
})

Deno.test('somar, ehEleicao, temConta e resumo', () => {
  const palavras = analisar('Eu voto no Lula. E o dólar?')
  const ia: Pedido = {
    pergunta: 'outra', mercados: ['ibovespa', 'dolar'], candidatos: ['flavio'], temas: ['copom'], proibidos: ['dica', 'direcao'],
    voto_informado: false, pontos: 20, contratos: 3, valor_moeda: 9, moeda: 'euro', gasto_mensal: 1, gasto_moeda: 'real',
  }
  const soma = somar(palavras, ia)
  igual(soma, {
    pergunta: 'Eu voto no Lula. E o dólar?', mercados: ['dolar', 'ibovespa'], candidatos: ['lula', 'flavio'],
    temas: ['eleicao', 'copom'], proibidos: ['dica', 'direcao'], voto_informado: true, pontos: 20, contratos: 1,
    valor_moeda: null, moeda: null, gasto_mensal: null, gasto_moeda: null,
  }, 'somar: o dinheiro do câmbio vem só da 1ª leitura, como no Python')
  igual(resumo(soma), 'mercados: dolar, ibovespa; candidatos: lula, flavio; temas: eleicao, copom; ' +
    'pedidos que pedem recusa: dica, direcao; a pessoa contou o próprio voto (não usar)', 'resumo')
  igual(resumo(analisar('oi')), 'mercados: nenhum; candidatos: nenhum; temas: nenhum; pedidos que pedem recusa: nenhum', 'resumo vazio')
  igual(ehEleicao(palavras), true, 'eleicao')
  igual(ehEleicao(analisar('quem vai ganhar?')), true, 'eleicao por chance_candidato')
  igual(ehEleicao(analisar('o que e selic')), false, 'sem eleicao')
  igual(temConta(analisar('win 500 pontos')), true, 'conta')
  igual(temConta(analisar('ibovespa 500 pontos')), false, 'sem conta: não é mini')
})

// Paridade do registro com o Python: para cada frase e pergunta do gabarito (tests/dados/paridade.json, campos registro,
// respostas e ia_sem_voto), a limpeza tem de sair igual à de agente/registro.py, caractere por caractere.
import { falouDeVoto, iaSemVoto, type IaRegistrada, leituraSemVoto, type PedidoLido, semDadoPessoal } from './registro.ts'

type Frase = { texto: string; limpo: string; falou_de_voto: boolean }
type Resposta = { pergunta: string; pedido: PedidoLido; pergunta_limpa: string; falou_de_voto: boolean; roteador_sem_voto: unknown }
type CasoIa = { ia: IaRegistrada | null; pergunta: string; pedido: PedidoLido; saida: unknown }

function ehObjeto(x: unknown): x is Record<string, unknown> {
  return typeof x === 'object' && x !== null && !Array.isArray(x)
}

function ehListaDeTextos(x: unknown): x is string[] {
  return Array.isArray(x) && x.every((v) => typeof v === 'string')
}

function ehPedido(x: unknown): x is PedidoLido {
  return ehObjeto(x) && ehListaDeTextos(x.mercados) && ehListaDeTextos(x.candidatos) && ehListaDeTextos(x.temas) &&
    ehListaDeTextos(x.proibidos) && typeof x.voto_informado === 'boolean'
}

function ehIa(x: unknown): x is IaRegistrada | null {
  return x === null || (ehObjeto(x) && (x.leitura === undefined || x.leitura === null || ehObjeto(x.leitura)))
}

async function gabarito(): Promise<Record<string, unknown>> {
  const bruto: unknown = JSON.parse(await Deno.readTextFile(new URL('../../../../tests/dados/paridade.json', import.meta.url)))
  if (!ehObjeto(bruto)) throw new Error('gabarito malformado')
  return bruto
}

function lista(g: Record<string, unknown>, campo: string): unknown[] {
  const v = g[campo]
  if (!Array.isArray(v)) throw new Error(`gabarito sem o campo ${campo}`)
  return v
}

function frases(g: Record<string, unknown>): Frase[] {
  return lista(g, 'registro').map((f: unknown, i: number): Frase => {
    if (!ehObjeto(f) || typeof f.texto !== 'string' || typeof f.limpo !== 'string' || typeof f.falou_de_voto !== 'boolean') {
      throw new Error(`registro ${i} malformado`)
    }
    return { texto: f.texto, limpo: f.limpo, falou_de_voto: f.falou_de_voto }
  })
}

function respostas(g: Record<string, unknown>): Resposta[] {
  return lista(g, 'respostas').map((r: unknown, i: number): Resposta => {
    if (
      !ehObjeto(r) || typeof r.pergunta !== 'string' || !ehPedido(r.pedido) || typeof r.pergunta_limpa !== 'string' ||
      typeof r.falou_de_voto !== 'boolean'
    ) throw new Error(`resposta ${i} malformada`)
    return {
      pergunta: r.pergunta, pedido: r.pedido, pergunta_limpa: r.pergunta_limpa, falou_de_voto: r.falou_de_voto,
      roteador_sem_voto: r.roteador_sem_voto,
    }
  })
}

function casosIa(g: Record<string, unknown>): CasoIa[] {
  return lista(g, 'ia_sem_voto').map((c: unknown, i: number): CasoIa => {
    if (!ehObjeto(c) || !ehIa(c.ia) || typeof c.pergunta !== 'string' || !ehPedido(c.pedido)) {
      throw new Error(`ia_sem_voto ${i} malformado`)
    }
    return { ia: c.ia, pergunta: c.pergunta, pedido: c.pedido, saida: c.saida }
  })
}

/** O JSON dos dois tem de sair idêntico, com as chaves na mesma ordem. */
function confere(erros: string[], onde: string, veio: unknown, esperado: unknown): void {
  const [x, y] = [JSON.stringify(veio), JSON.stringify(esperado)]
  if (x !== y) erros.push(`${onde}\n  esperado: ${y}\n  veio:     ${x}`)
}

function semErros(erros: string[], total: number): void {
  if (erros.length) throw new Error(`${erros.length} de ${total} diferentes:\n${erros.join('\n')}`)
}

Deno.test('semDadoPessoal e falouDeVoto: paridade exata com o Python nas frases de registro', async () => {
  const todas = frases(await gabarito())
  if (todas.length < 57) throw new Error(`gabarito com ${todas.length} frases, esperava 57`)
  const erros: string[] = []
  for (const f of todas) {
    confere(erros, `limpo de ${JSON.stringify(f.texto)}`, semDadoPessoal(f.texto), f.limpo)
    confere(erros, `falou_de_voto de ${JSON.stringify(f.texto)}`, falouDeVoto(f.texto), f.falou_de_voto)
  }
  semErros(erros, todas.length * 2)
})

Deno.test('pergunta_limpa, falou_de_voto e roteador_sem_voto: paridade exata nas perguntas do gabarito', async () => {
  const todas = respostas(await gabarito())
  if (todas.length < 136) throw new Error(`gabarito com ${todas.length} perguntas, esperava 136`)
  const erros: string[] = []
  for (const r of todas) {
    const q = JSON.stringify(r.pergunta)
    confere(erros, `pergunta_limpa de ${q}`, semDadoPessoal(r.pergunta), r.pergunta_limpa)
    confere(erros, `falou_de_voto de ${q}`, falouDeVoto(r.pergunta), r.falou_de_voto)
    confere(erros, `roteador_sem_voto de ${q}`, leituraSemVoto(r.pedido, r.pergunta), r.roteador_sem_voto)
  }
  semErros(erros, todas.length * 3)
})

Deno.test('iaSemVoto: paridade exata com o Python', async () => {
  const todos = casosIa(await gabarito())
  if (todos.length < 3) throw new Error(`gabarito com ${todos.length} casos, esperava 3`)
  const erros: string[] = []
  for (const c of todos) confere(erros, `ia_sem_voto de ${JSON.stringify(c.pergunta)}`, iaSemVoto(c.ia, c.pedido, c.pergunta), c.saida)
  semErros(erros, todos.length)
})

Deno.test('iaSemVoto: sem IA ou com leitura vazia, devolve o que veio (o `not` do Python)', () => {
  const p: PedidoLido = { mercados: [], candidatos: ['lula'], temas: [], proibidos: [], voto_informado: true }
  const vazia: IaRegistrada = { modelo: 'm', erro: null, leitura: {} }
  const erros: string[] = []
  confere(erros, 'None', iaSemVoto(null, p, 'voto no Lula'), null)
  confere(erros, 'leitura {}', iaSemVoto(vazia, p, 'voto no Lula'), vazia)
  confere(erros, 'sem candidatos na leitura', iaSemVoto({ leitura: { temas: ['eleicao'], voto_informado: true } }, p, 'oi'), {
    leitura: { temas: ['eleicao'], candidatos: [] },
  })
  semErros(erros, 3)
})

// Os casos abaixo saíram do Python (.venv/bin/python, agente/registro.py) em 22/10/2026. Eles cobrem o que muda do re do
// Python para o RegExp do JavaScript num texto com acento: re.I (İ, ı, K, ſ), \d, \s e \b Unicode, e str.isspace().
const BORDAS: ReadonlyArray<readonly [string, string, boolean]> = [
  ['tenho 5 MİL', 'tenho [valor omitido]', false],
  ['tenho 5 mıl', 'tenho [valor omitido]', false],
  ['TİNHA 7000 na conta', 'TİNHA [valor omitido] na conta', false],
  ['tınha 7000 na conta', 'tınha [valor omitido] na conta', false],
  ['Ganho 8 MİL por mês', 'Ganho [valor omitido] por mês', false],
  ['300 REAİS', '[valor omitido]', false],
  ['uns 5K', 'uns [valor omitido]', false],
  ['10 milhõeſ', '[valor omitido]', false],
  ['TENHO R$ 5 MIL', 'TENHO [valor omitido]', false],
  ['CINCO MİL REAİS', '[valor omitido]', false],
  ['TRÊS MILHÕES', '[valor omitido]', false],
  ['Três Milhões de Reais', '[valor omitido]', false],
  ['R$ ٥٠٠', '[valor omitido]', false],
  ['tenho ５０００ guardado', 'tenho [valor omitido] guardado', false],
  ['renda 𝟕𝟎𝟎𝟎', 'renda [valor omitido]', false],
  ['renda ٧٠٠٠', 'renda [valor omitido]', false],
  ['R$\u001c500', '[valor omitido]', false],
  ['R$\u0085500', '[valor omitido]', false],
  ['R$﻿500', 'R$﻿500', false],
  ['renda 5\u001cpontos', 'renda 5\u001cpontos', false],
  ['renda 5﻿pontos', 'renda [valor omitido]﻿pontos', false],
  ['tenho 5\u001fmil', 'tenho [valor omitido]', false],
  ['custa é500 reais', 'custa é500 reais', false],
  ['5 milhõesá', '5 milhõesá', false],
  ['ésalário 4000', 'ésalário 4000', false],
  ['renda 7000á', 'renda 7000á', false],
  ['5 reaisͅ', '[valor omitido]ͅ', false],
  ['salárioͅ 4000', 'salárioͅ [valor omitido]', false],
  ['minha renda é 7000', 'minha renda é [valor omitido]', false],
  ['tenho 2026 guardado', 'tenho 2026 guardado', false],
  ['tenho 30% do patrimônio', 'tenho 30% do patrimônio', false],
  ['tenho 3 contratos', 'tenho 3 contratos', false],
  ['tenho 10 pontos', 'tenho 10 pontos', false],
  ['renda 1º', 'renda 1º', false],
  ['renda 2ª', 'renda 2ª', false],
  ['renda 7000.', 'renda [valor omitido].', false],
  ['renda 7.000,00 e 2.000', 'renda [valor omitido].000,00 e 2.000', false],
  ['renda 1/2', 'renda 1/2', false],
  ['reserva 12/10', 'reserva 12/10', false],
  ['tenho 20 anos', 'tenho [valor omitido] anos', false],
  ['aplico 5 p.p. a mais', 'aplico [valor omitido] p.p. a mais', false],
  ['herdei 300 o turno', 'herdei 300 o turno', false],
  ['renda 😀7000', 'renda 😀[valor omitido]', false],
  ['guardei 1999 e 19999', 'guardei 1999 e [valor omitido]', false],
  ['Patrimônio: 50000', 'Patrimônio: 50000', false],
  ['tenho cinco mil reais', 'tenho [valor omitido]', false],
  ['duzentos e cinquenta mil', '[valor omitido]', false],
  ['vinte e cinco mil e quinhentos reais', '[valor omitido]', false],
  ['três mil', '[valor omitido]', false],
  ['tres mil de reais', '[valor omitido]', false],
  ['oi,\u001cvoto no lula', 'oi, [trecho sobre voto omitido]', true],
  ['oi,﻿voto no lula', 'oi,[trecho sobre voto omitido]', true],
  ['oi, voto no lula', 'oi, [trecho sobre voto omitido]', true],
  ['oi, voto no lula', 'oi, [trecho sobre voto omitido]', true],
  ['VOTEİ no Lula. E o dólar?', '[trecho sobre voto omitido]. E o dólar?', true],
  ['Fiz o L, tenho 5 mil', '[trecho sobre voto omitido], tenho [valor omitido]', true],
  ['sou de direita; e a bolsa?', '[trecho sobre voto omitido]; e a bolsa?', true],
  ['o mito, e o dólar', '[trecho sobre voto omitido], e o dólar', true],
  ['', '', false],
  [',', ',', false],
  ['voto', '[trecho sobre voto omitido]', true],
  ['Votei!\n\nE a Selic?', '[trecho sobre voto omitido]!\n\nE a Selic?', true],
]

Deno.test('semDadoPessoal e falouDeVoto: as bordas Unicode saem como no Python', () => {
  const erros: string[] = []
  for (const [texto, limpo, voto] of BORDAS) {
    confere(erros, `limpo de ${JSON.stringify(texto)}`, semDadoPessoal(texto), limpo)
    confere(erros, `falou_de_voto de ${JSON.stringify(texto)}`, falouDeVoto(texto), voto)
  }
  semErros(erros, BORDAS.length * 2)
})

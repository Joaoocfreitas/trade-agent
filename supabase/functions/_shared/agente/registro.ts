// O registro de todas as conversas (M10): pergunta, resposta mostrada, texto da IA barrado e o porquê. Tradução da
// parte pura de agente/registro.py (o Python é a referência; tests/dados/paridade.json prova que os dois limpam igual).
// Gravar a linha fica com quem chama: aqui não há arquivo.
//
// Sem dado pessoal: o valor em reais e o voto que a pessoa contar saem antes de gravar (N5, N9 e LGPD). Não há nome,
// e-mail nem identificador de quem perguntou.
//
// Diferente do roteador, aqui o texto é o original, com acento. No Python, \w, \s e \d são Unicode, \b é a fronteira
// desse \w e o re.I também casa İ e ı com i; no JavaScript, \w e \b são ASCII, \s é outro conjunto e a flag i não casa
// İ nem ı (e, com u, faz o \p{L} casar o U+0345). Por isso os padrões abaixo são cópias literais do Python, e py() os
// traduz para o que o re do Python faria.
import { type Pedido, simples } from './texto.ts'

const r = String.raw

// O \w do Python (str): letra, número ou sublinhado.
const PALAVRA = r`\p{L}\p{N}_`
// O \s e o str.isspace() do Python, que são o mesmo conjunto.
const ESPACO = r`\t\n\v\f\r \x1c-\x1f\x85\xa0  -     　`
const FRONTEIRA = `(?:(?<=[${PALAVRA}])(?![${PALAVRA}])|(?<![${PALAVRA}])(?=[${PALAVRA}]))`
// O que o re.I do Python casa além das duas caixas da letra.
const CAIXA_EXTRA: ReadonlyMap<string, string> = new Map([['i', 'İı'], ['k', 'K'], ['s', 'ſ']])

/** Todas as formas que o re.I do Python aceita para o caractere (ele mesmo, se não tem caixa). */
function caixas(c: string): string {
  const minuscula = c.toLowerCase()
  const formas = [c, minuscula, c.toUpperCase(), ...(CAIXA_EXTRA.get(minuscula) ?? '')]
  return [...new Set(formas.filter((f) => [...f].length === 1))].join('')
}

/**
 * Compila um padrão do re do Python (str, Unicode), colado em pedaços como as strings do Python. Em `flags`, 'i' é o
 * re.I (vira classe por letra, sem a flag i do JS) e 'g' é para o replace.
 */
function py(flags: string, ...partes: string[]): RegExp {
  const fonte = partes.join('')
  let saida = ''
  let naClasse = false
  for (let i = 0; i < fonte.length; i++) {
    const c = fonte[i]
    if (c === '\\') {
      const e = fonte[++i]
      if (e === 'w') saida += naClasse ? PALAVRA : `[${PALAVRA}]`
      else if (e === 's') saida += naClasse ? ESPACO : `[${ESPACO}]`
      else if (e === 'd') saida += r`\p{Nd}`
      else if (e === 'b' && !naClasse) saida += FRONTEIRA
      else saida += c + e
    } else if (c === '[' && !naClasse) {
      naClasse = true
      saida += c
    } else if (c === ']' && naClasse) {
      naClasse = false
      saida += c
    } else if (flags.includes('i') && caixas(c).length > 1) {
      saida += naClasse ? caixas(c) : `[${caixas(c)}]`
    } else {
      saida += c
    }
  }
  return new RegExp(saida, flags.includes('g') ? 'gu' : 'u')
}

// Opinião política é dado sensível (LGPD, art. 5º, II): a oração inteira que fala de voto ou de lado sai.
// Roda sobre simples(), que é ASCII: aí o \w e o \b do JavaScript valem o mesmo que os do Python.
const POLITICO = new RegExp([
  r`\bvot(o|ei|ar|arei|aria|ando|amos|e|ou|aram|ara)\b|\bmeu voto\b|\bvou de\b|\bfui de\b|\bfiz o l\b|\bfaz o l\b|\bapoi(o|ar|ador\w*)\b|\btorc(o|endo|er)\b`,
  r`|\beleitor\w*|\bmeu candidato\b|\bminha candidata\b|\bsou (do|da) (pt|pl|psol|novo|psdb|mdb|pdt|psb)\b`,
  r`|\bsou (\w+ )?(de )?(direita|esquerda)\b|\b(petista|bolsonarista|lulista|esquerdista|direitista|bolsominion\w*|antipetista`,
  r`|antibolsonarista|conservador\w*|progressista|lulopetista|lulista)\b|\bmito\b|\bodeio\b|\bdetesto\b`,
  r`|\bfora (lula|bolsonaro|flavio|pt)\b|\b(lula|flavio|bolsonaro) (13|22|sempre|la)\b|\bamo (o|a) (lula|flavio|bolsonaro|pt)\b`,
].join(''))
// O split do JavaScript também devolve o separador capturado: as orações ficam nas posições pares.
const ORACOES = /([,.!?;:\n]+)/
const EXTENSO = r`(um|uma|dois|duas|tr[êe]s|quatro|cinco|seis|sete|oito|nove|dez|onze|doze|quinze|vinte|trinta|quarenta|` +
  r`cinquenta|sessenta|setenta|oitenta|noventa|cem|cento|duzentos|trezentos|quinhentos|mil)`
// Dinheiro: moeda com número, número com sufixo de valor, e valor por extenso.
const VALOR = py(
  'ig',
  r`(R\s?\$|US\s?\$|U\$|BRL|USD|€|\$)\s?\d[\d.,]*(\s?(mil|milh[õo]es|milh[ãa]o|mi|k|bi))?`,
  r`|\b\d[\d.,]*\s?(k|mil|milh[õo]es|milh[ãa]o|mi|bi|paus|pila|contos?|reais|d[óo]lares|euros)\b(\s+(e\s+)?${EXTENSO}\b)*`,
  r`|\b${EXTENSO}(\s+(e\s+)?${EXTENSO})*\s+(mil|milh[õo]es|milh[ãa]o)\b(\s+(e\s+)?${EXTENSO})*(\s+(de\s+)?reais)?`,
)
// Número solto numa oração que fala do próprio dinheiro ("minha renda é 7000"). Poupa ano, data, %, pontos e contratos.
const DINHEIRO = py(
  'i',
  r`\b(tenho|tinha|guardei|juntei|ganho|recebo|recebi|herdei|sal[áa]rio|reserva|invisto|investir|aplicar|`,
  r`aplico|coloco|boto|patrim[ôo]nio|economizei|capital|renda|fgts|grana|dinheiro)\b`,
)
const NUMERO_SOLTO = py('g', r`(?<![\d/.,])\b(?!(19|20)\d\d\b)\d[\d.,]*\b(?![\d/]|\s*(%|pontos?|contratos?|º|ª|o turno|p\.p\.))`)
const COMECA_COM_ESPACO = new RegExp(`^[${ESPACO}]`, 'u')

function semVoto(texto: string): [string, boolean] {
  const partes = texto.split(ORACOES)
  let achou = false
  for (let i = 0; i < partes.length; i += 2) {
    if (POLITICO.test(simples(partes[i]))) {
      partes[i] = (COMECA_COM_ESPACO.test(partes[i]) ? ' ' : '') + '[trecho sobre voto omitido]'
      achou = true
    }
  }
  return [partes.join(''), achou]
}

export function semDadoPessoal(texto: string): string {
  texto = semVoto(texto)[0]
  texto = texto.replace(VALOR, '[valor omitido]')
  const partes = texto.split(ORACOES)
  for (let i = 0; i < partes.length; i += 2) {
    if (DINHEIRO.test(partes[i])) partes[i] = partes[i].replace(NUMERO_SOLTO, '[valor omitido]')
  }
  return partes.join('')
}

export function falouDeVoto(texto: string): boolean {
  return semVoto(texto)[1]
}

/** Só o que leituraSemVoto e iaSemVoto leem do pedido. */
export type PedidoLido = Pick<Pedido, 'mercados' | 'candidatos' | 'temas' | 'proibidos' | 'voto_informado'>
export type LeituraSemVoto = { mercados: string[]; candidatos: string[]; temas: string[]; proibidos: string[] }
/** A saída da IA como agente/ia.py a guarda: o resto passa intacto, só a leitura muda. */
export type IaRegistrada = { leitura?: Record<string, unknown> | null; [chave: string]: unknown }

/** O que o roteador leu, sem o candidato quando a pessoa contou o voto (senão dá para reconstruir o voto). */
/** registro.violacoes_sem_dinheiro do Python: com a conta de câmbio, o trecho de uma violação pode trazer o valor
 * calculado a partir do dinheiro da pessoa ("R$ 847.410"); os dígitos saem. */
export function violacoesSemDinheiro<V extends { trecho: string }>(violacoes: V[], p: Pedido): V[] {
  const conta = p.valor_moeda !== null && (p.moeda === 'euro' || p.moeda === 'dolar')
  return violacoes.map((v) => conta ? { ...v, trecho: v.trecho.replace(/\d/g, '#') } : v)
}

export function leituraSemVoto(p: PedidoLido, pergunta: string): LeituraSemVoto {
  const voto = p.voto_informado || falouDeVoto(pergunta)
  return { mercados: p.mercados, candidatos: voto ? [] : p.candidatos, temas: p.temas, proibidos: p.proibidos }
}

export function iaSemVoto(ia: IaRegistrada | null, p: PedidoLido, pergunta: string): IaRegistrada | null {
  // Como o `not` do Python: leitura vazia ({}) também passa intacta.
  if (!ia || !ia.leitura || Object.keys(ia.leitura).length === 0) return ia
  const voto = p.voto_informado || falouDeVoto(pergunta)
  const leitura: Record<string, unknown> = Object.fromEntries(
    Object.entries(ia.leitura).filter(([k]) => k !== 'voto_informado'),
  )
  if (voto) leitura.candidatos = []
  return { ...ia, leitura }
}

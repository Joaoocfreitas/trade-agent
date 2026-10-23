// O `re` do Python sobre o texto de normalizar(), para o roteador e a resposta guardarem os padrões com o mesmo texto do
// Python (agente/roteador.py e agente/resposta.py) e as chamadas na mesma forma (search, sub, split, finditer, match,
// fullmatch).
//
// O texto é ASCII (normalizar() tira o acento), e aí \w, \d e \b valem o mesmo nos dois. O que muda, e a conversão trata:
// - o "." do Python só recusa o \n; o do JavaScript também recusa o \r: vira [^\n];
// - o \s do Python inclui \x1c-\x1f: vira [\t\n\v\f\r\x1c-\x1f ] (e o \S, o complemento disso);
// - o $ do Python também casa antes de um \n final: vira (?=\n?$);
// - \Z e \A viram $ e ^; (?P<nome>...) e (?P=nome) viram (?<nome>...) e \k<nome>;
// - "]" logo depois de "[" ou "[^" é literal no Python (no JavaScript, "[]" não casa nada): vira \].
// O que o JavaScript não tem (flag em linha, grupo atômico, quantificador possessivo, {,n}) dá erro na hora de compilar,
// para não passar calado.

const ESPACO = String.raw`\t\n\v\f\r\x1c-\x1f `
// O \S do Python dentro de uma classe ("[\s\S]"): tudo menos o ESPACO (o \S do JavaScript deixaria entrar \x1c-\x1f).
const NAO_ESPACO = String.raw`\x00-\x08\x0e-\x1b\x21-\uffff`

/** O padrão do Python no dialeto do JavaScript, com o mesmo comportamento sobre texto ASCII. */
export function converter(p: string): string {
  let saida = ''
  let classe = false
  let inicioClasse = -1
  for (let i = 0; i < p.length; i++) {
    const c = p[i]
    if (c === '\\') {
      const e = p[++i]
      if (e === undefined) throw new Error(`padrão termina em barra: ${p}`)
      if (e === 's') saida += classe ? ESPACO : `[${ESPACO}]`
      else if (e === 'S') saida += classe ? NAO_ESPACO : `[^${ESPACO}]`
      else if (e === 'Z' && !classe) saida += '$'
      else if (e === 'A' && !classe) saida += '^'
      else saida += c + e
      continue
    }
    if (classe) {
      if (c === ']' && i === inicioClasse) saida += '\\]'
      else {
        if (c === ']') classe = false
        saida += c
      }
      continue
    }
    if (c === '[') {
      classe = true
      saida += c
      if (p[i + 1] === '^') saida += p[++i]
      inicioClasse = i + 1
    } else if (c === '.') saida += String.raw`[^\n]`
    else if (c === '$') saida += String.raw`(?=\n?$)`
    else if (c === '(' && p.startsWith('(?P<', i)) {
      saida += '(?<'
      i += 3
    } else if (c === '(' && p.startsWith('(?P=', i)) {
      const fim = p.indexOf(')', i)
      saida += String.raw`\k<` + p.slice(i + 4, fim) + '>'
      i = fim
    } else if (c === '(' && /^\(\?[aiLmsux-]+[):]/.test(p.slice(i)) || c === '(' && p.startsWith('(?>', i)) {
      throw new Error(`construção do Python sem equivalente aqui: ${p.slice(i, i + 12)}`)
    } else if (c === '{' && p[i + 1] === ',') {
      throw new Error(`{,n} do Python (escreva {0,n}): ${p}`)
    } else if ((c === '+' || c === '*' || c === '?' || c === '}') && p[i + 1] === '+') {
      throw new Error(`quantificador possessivo: ${p}`)
    } else saida += c
  }
  if (classe) throw new Error(`classe aberta: ${p}`)
  return saida
}

const COMPILADOS = new Map<string, RegExp>()

/** `inteiro`: para o fullmatch, o fim estrito do texto (o $ do JavaScript, que não aceita o \n final). */
function compilar(p: string, flags: '' | 'g' | 'y', inteiro = false): RegExp {
  const chave = flags + (inteiro ? '$' : '') + '\u0000' + p
  let r = COMPILADOS.get(chave)
  if (!r) {
    r = new RegExp(inteiro ? `(?:${converter(p)})$` : converter(p), flags)
    COMPILADOS.set(chave, r)
  }
  return r
}

/** O re.Match do Python: início, fim e grupos (undefined no grupo que não participou, o None de lá). */
export type Casamento = {
  start: number
  end: number
  /** group(0) é o trecho inteiro. */
  group: (n?: number) => string | undefined
  /** os grupos 1..n */
  groups: (string | undefined)[]
  string: string
}

function casamento(m: RegExpExecArray, s: string): Casamento {
  return {
    start: m.index,
    end: m.index + m[0].length,
    group: (n = 0) => m[n],
    groups: m.slice(1),
    string: s,
  }
}

/** re.search */
export function search(p: string, s: string): Casamento | null {
  const r = compilar(p, '')
  const m = r.exec(s)
  return m ? casamento(m, s) : null
}

/** re.match: só no começo do texto. */
export function match(p: string, s: string): Casamento | null {
  const r = compilar(p, 'y')
  r.lastIndex = 0
  const m = r.exec(s)
  return m ? casamento(m, s) : null
}

/** re.fullmatch: o texto inteiro. */
export function fullmatch(p: string, s: string): Casamento | null {
  const r = compilar(p, 'y', true)
  r.lastIndex = 0
  const m = r.exec(s)
  return m ? casamento(m, s) : null
}

/** Quantos casamentos vazios o finditer já viu: o Python e o JavaScript só discordam neles (teste em pyre_test.ts). */
export const vazios = { n: 0 }

/** re.finditer. Num casamento vazio, o JavaScript anda uma posição e o Python ainda aceita um casamento não vazio no
 * mesmo lugar; os padrões do agente não casam vazio no sub, no split nem no finditer, e `vazios` conta se casarem. */
export function finditer(p: string, s: string): Casamento[] {
  const r = compilar(p, 'g')
  const saida: Casamento[] = []
  for (const m of s.matchAll(r)) {
    if (m[0] === '') vazios.n++
    saida.push(casamento(m as RegExpExecArray, s))
  }
  return saida
}

/** A troca de re.sub com texto: \1, \g<1> e \\ como no Python. */
function expandir(modelo: string, m: Casamento): string {
  return modelo.replace(/\\(?:(\d{1,2})|g<(\d+)>|(\\))|\\(.)/g, (_, n, g, barra, outro) => {
    if (outro !== undefined) throw new Error(`escape sem tradução no modelo do sub: \\${outro}`)
    if (barra) return '\\'
    return m.group(Number(n ?? g)) ?? ''
  })
}

/** re.sub */
export function sub(p: string, troca: string | ((m: Casamento) => string), s: string): string {
  let saida = ''
  let ultimo = 0
  for (const m of finditer(p, s)) {
    saida += s.slice(ultimo, m.start) + (typeof troca === 'string' ? expandir(troca, m) : troca(m))
    ultimo = m.end
  }
  return saida + s.slice(ultimo)
}

/** re.split: os pedaços e, entre eles, os grupos do separador (undefined no que não participou). */
export function split(p: string, s: string): (string | undefined)[] {
  const saida: (string | undefined)[] = []
  let ultimo = 0
  for (const m of finditer(p, s)) {
    saida.push(s.slice(ultimo, m.start), ...m.groups)
    ultimo = m.end
  }
  saida.push(s.slice(ultimo))
  return saida
}

/** re.split(...)[-1] e [0]: o primeiro e o último pedaço são sempre texto. */
export const ultimo = (p: string, s: string): string => split(p, s).at(-1) as string
export const primeiro = (p: string, s: string): string => split(p, s)[0] as string

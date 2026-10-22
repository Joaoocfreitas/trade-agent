// simples() tem de tratar cada caractere do Unicode como o Python de referência. Se o Deno trouxer um Unicode novo
// que leve mais caracteres para ASCII, este teste falha e mostra quais.
import { assertEquals } from 'jsr:@std/assert@1.0.13'
import { simples } from './texto.ts'

const { mapa } = JSON.parse(await Deno.readTextFile(new URL('../../../../tests/dados/simples_unicode.json', import.meta.url))) as
  { mapa: Record<string, string> }

Deno.test('simples(): cada caractere igual ao Python', () => {
  const diferentes: string[] = []
  for (let cp = 0; cp < 0x110000; cp++) {
    if (cp >= 0xd800 && cp <= 0xdfff) continue
    const esperado = mapa[String(cp)] ?? ''
    if (simples(String.fromCodePoint(cp)) !== esperado) diferentes.push(cp.toString(16))
  }
  assertEquals(diferentes, [])
})

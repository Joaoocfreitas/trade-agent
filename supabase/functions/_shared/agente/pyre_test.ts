// O `re` do Python no JavaScript (pyre.ts): cada caso saiu do Python (.venv/bin/python, re) em 23/10/2026.
import { assertEquals, assertThrows } from 'jsr:@std/assert@1.0.13'
import { converter, fullmatch, match, search, split, sub, ultimo } from './pyre.ts'

Deno.test('pyre: ".", "\\s" e "$" como no Python', () => {
  assertEquals(Boolean(search(String.raw`a.b`, 'a\rb')), true) // o "." do Python só recusa o \n
  assertEquals(Boolean(search(String.raw`a.b`, 'a\nb')), false)
  assertEquals(Boolean(search(String.raw`a\sb`, 'a\x1cb')), true) // o \s do Python inclui \x1c-\x1f
  assertEquals(Boolean(search(String.raw`a[\s,]b`, 'a\x1fb')), true)
  assertEquals(Boolean(search('fim$', 'o fim\n')), true) // o $ do Python casa antes do \n final
  assertEquals(Boolean(search('fim$', 'o fim\nx')), false)
  assertEquals(Boolean(fullmatch('fim', 'fim\n')), false) // o fullmatch não
  assertEquals(Boolean(search('[]a]', ']')), true) // "]" logo depois de "[" é literal
  assertEquals(Boolean(search(String.raw`a[\S]b`, 'a\x1cb')), false) // o \S de classe é o complemento do \s do Python
  assertEquals(Boolean(search(String.raw`^[\s\S]*$`, 'a\r\x1cb\n')), true)
})

Deno.test('pyre: split, sub, match e grupo com nome como no Python', () => {
  assertEquals(split('(,)|;', 'a,b;c'), ['a', ',', 'b', undefined, 'c'])
  assertEquals(ultimo('[?!]', 'a? b! c'), ' c')
  assertEquals(sub('(a)(b)?', String.raw`[\2\1]`, 'ab a'), '[ba] [a]')
  assertEquals(sub(String.raw`\d`, (m) => String(m.start), 'x1y2'), 'x1y3')
  assertEquals([Boolean(match('b', 'ab')), Boolean(match('a', 'ab'))], [false, true])
  assertEquals(sub('(?P<x>o)(?P=x)', 'O', 'boom'), 'bOm')
})

Deno.test('pyre: o que não tem equivalente dá erro, em vez de passar calado', () => {
  for (const p of ['(?i)a', '(?>a)', 'a{,3}', 'a++']) assertThrows(() => converter(p), Error, undefined, p)
})

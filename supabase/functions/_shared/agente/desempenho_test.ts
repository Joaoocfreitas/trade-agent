// A pergunta longa não trava o agente: o espelho de test_pergunta_longa_nao_trava_o_roteador (tests/test_rodada2.py).
// O site aceita até 2.000 caracteres. Padrão de número sem âncora à esquerda recomeçava em cada posição e deixava a conta
// quadrática; o teto aqui é folgado para não falhar em máquina lenta, mas pega a volta do defeito.
//
// A 1ª pergunta compila os padrões (o V8 compila cada regex no 1º uso, uns 100 ms ao todo): ela fica de fora da medida,
// como no Python, em que os testes de antes já compilaram.
import { assert } from 'jsr:@std/assert@1.0.13'
import { vazios } from './pyre.ts'
import { montar } from './resposta.ts'
import { analisar } from './roteador.ts'

const BASES = ['1', ', ', 'e ', '1.', '1,', 'us$ 1 ', '10 dolares ', 'barril a ',
  // os piores casos medidos no Python, e os símbolos repetidos da rodada 4 (o "€" vira palavra e crescia 4 vezes)
  ', , ,', 'e e e ', '1.1.1.', 'us$ 1 us$ 1 ', '€1', '📉📈']

Deno.test('pergunta de 2.000 caracteres: o roteador e a resposta inteira em menos de 500 ms', () => {
  montar('o dólar vai subir?', undefined, '2026-10-23') // compila os padrões
  for (const base of BASES) {
    const s = base.repeat(2000).slice(0, 2000)
    let t0 = performance.now()
    analisar(s)
    const roteador = performance.now() - t0
    t0 = performance.now()
    montar(s, undefined, '2026-10-23')
    const resposta = performance.now() - t0
    assert(roteador < 500 && resposta < 500, `${JSON.stringify(base)}: roteador ${roteador.toFixed(0)} ms, resposta ${resposta.toFixed(0)} ms`)
  }
})

Deno.test('nenhum padrão do sub, do split nem do finditer casa vazio (onde o Python e o JavaScript discordariam)', () => {
  const antes = vazios.n
  for (const q of ['o dólar vai subir?', 'tenho 20 mil euros e gasto 2 mil por mês, o petróleo mexe com isso?',
    'historicamente a bolsa sobe depois de eleição, e esse ano?', 'o IOF vai ficar em 3,5%, e o dólar?',
    'quando o Bolsonaro trocou o presidente da Petrobras?', 'compro PETR4 antes do dividendo extraordinário?']) {
    montar(q, undefined, '2026-10-23')
  }
  assert(vazios.n === antes, `${vazios.n - antes} casamentos vazios`)
})

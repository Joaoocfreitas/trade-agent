"""Exporta a base de fatos para a função do Supabase e o gabarito que prova que o TypeScript responde igual ao Python.

  python -m agente.exportar

Gera dois arquivos:
- supabase/functions/_shared/base.json: todos os blocos de fatos já prontos (texto, fontes, resumo, limites) e os
  textos fixos. A função não calcula número nenhum: só escolhe blocos, monta e filtra. Rode de novo sempre que os dados
  mudarem (Selic, pesquisa, resultado de eleição) e publique a função.
- tests/dados/paridade.json: perguntas, frases e textos com a saída do Python, para o teste do TypeScript comparar.
"""
import json
from dataclasses import asdict
from datetime import datetime
from itertools import permutations
from pathlib import Path

from coletor.config import FUSO
from . import cartoes as C
from . import fatos as F
from . import textos as T
from .__main__ import BATERIA
from .filtro import checar, frases_proibidas, numeros_sem_fonte
from .ia import INSTRUCOES
from .registro import falou_de_voto, ia_sem_voto, leitura_sem_voto, sem_dado_pessoal
from .resposta import DERIVATIVOS, SEGURA, montar
from .roteador import MEDIDOS, analisar

RAIZ = Path(__file__).resolve().parent.parent
BASE = RAIZ / 'supabase' / 'functions' / '_shared' / 'base.json'
PARIDADE = RAIZ / 'tests' / 'dados' / 'paridade.json'
RESUMOS = RAIZ / 'tests' / 'dados' / 'respostas_resumo.json'

ALVOS = [list(p) for n in (1, 2, 3) for p in permutations(MEDIDOS, n)]
LIMITE_CRIPTO_ELEICAO = 'O repertório não tem medida de cripto em eleição brasileira: não invento esse número.'


def _fonte(f: F.Fonte) -> dict:
    return {'nome': f.nome, 'url': f.url}


def _bloco(b: F.Bloco | None) -> dict | None:
    if b is None:
        return None
    return {'titulo': b.titulo, 'linhas': [{'texto': ln.texto, 'fontes': [_fonte(f) for f in ln.fontes]} for ln in b.linhas],
            'resumo': b.resumo, 'limites': list(b.limites)}


def base() -> dict:
    eleicoes = {','.join(a): _bloco(F.eleicoes(a)) for a in ALVOS}
    for b in eleicoes.values():
        assert LIMITE_CRIPTO_ELEICAO not in b['limites']
    assert LIMITE_CRIPTO_ELEICAO in F.eleicoes(['cripto']).limites
    return {
        'gerado_em': datetime.now(FUSO).isoformat(timespec='seconds'),
        'textos': {
            'AVISO': T.AVISO, 'RECUSA': T.RECUSA, 'FECHO': T.FECHO, 'RISCO_DERIVATIVO': T.RISCO_DERIVATIVO,
            'RISCO_CRIPTO': T.RISCO_CRIPTO, 'POR_PEDIDO': T.POR_PEDIDO, 'PEDEM_RECUSA': sorted(T.PEDEM_RECUSA),
            'VOTO_INFORMADO': T.VOTO_INFORMADO, 'SEM_REPERTORIO': T.SEM_REPERTORIO, 'NORMAS': T.NORMAS, 'SEGURA': SEGURA,
            'LIMITE_CRIPTO_ELEICAO': LIMITE_CRIPTO_ELEICAO, 'INSTRUCOES_IA': INSTRUCOES,
        },
        'derivativos': list(DERIVATIVOS),
        'tipos': list(F.TIPOS),
        'economia': _bloco(F.economia()),
        'eleicoes': eleicoes,
        'copom': {'': _bloco(F.copom([])), **{','.join(a): _bloco(F.copom(a)) for a in ALVOS}},
        'eventos': {t: _bloco(F.eventos(t)) for t in F.TIPOS},
        'mercado': {k: _bloco(F.mercado(k)) for k in ('mini_indice', 'mini_dolar', 'juros', 'ibovespa', 'cripto')},
        'historico': {k: _bloco(F.historico(k)) for k in F.HISTORICO},
        'expectativas': {k: _bloco(F.expectativas(k)) for k in ('', 'dolar', 'euro', 'juros', 'ibovespa')},
        'agenda': {k: [{'tipo': i['tipo'], 'data': i['data'], 'curto': i['curto'],
                        'fontes': [_fonte(f) for f in i['fontes']]} for i in F.agenda(k)] for k in F.HISTORICO},
        'titulo_cripto': F.TITULO_CRIPTO,
        'calendario': F.CALENDARIO,
        'candidatos': _bloco(F.candidatos()),
        'pesquisas': _bloco(F.pesquisas()),
        'fgv': _bloco(F.fgv()),
        'memecoins': _bloco(F.memecoins()),
        'previsao': _bloco(F.previsao()),
        'binaria': _bloco(F.binaria()),
        'cartoes': {
            'eleicoes': {','.join(a): C.eleicoes(a) for a in ALVOS},
            'copom': {'': C.copom(None), **{','.join(a): C.copom(a) for a in ALVOS}},
            'eventos': {t: C.eventos(t) for t in F.TIPOS},
        },
        'conta': {'mini_indice': {'valor': 0.20, 'nome': 'mini-índice', 'fonte': _fonte(F.F_B3_WIN)},
                  'mini_dolar': {'valor': 10.0, 'nome': 'mini-dólar', 'fonte': _fonte(F.F_B3_WDO)}},
        # P4 de câmbio: a conta é feita na hora com o número da pessoa; aqui vão as cotações e os textos fixos.
        'cambio': {
            'cotacoes': {m: F.cotacoes(m) for m in F.MOEDAS},
            'moedas': {m: {'nome': v[0], 'plural': v[1], 'fonte': _fonte(v[3])} for m, v in F.MOEDAS.items()},
            'titulo': F.TITULO_CONTA_CAMBIO, 'limite_euro': F.LIMITE_PTAX_EURO,
        },
        'euro_turnos': _bloco(F.euro_turnos()),
        'resumo_hoje': F.RESUMO_HOJE,
    }


# Perguntas a mais, para cobrir as variantes de mercado, de evento, de conta e de idioma.
EXTRAS = [
    'O que acontece com o dólar e o Ibovespa se o Lula ganhar?', 'Juros e dólar depois do 2º turno, se o Flávio vencer?',
    'Ibovespa, dólar e juros no 1º turno de 2022: o que aconteceu?', 'Como os juros reagiram ao Copom de março de 2020?',
    'O dólar sobe na semana do Copom?', 'Juros de 2 anos no Copom: o que acontece com surpresa?', 'Copom',
    'Como a bolsa reagiu às votações no Congresso?', 'E quando o STF julgou casos grandes?', 'Pacote fiscal derruba a bolsa?',
    'Tarifas dos EUA e o Ibovespa', 'A pandemia derrubou o dólar?', 'Escândalos e o Ibovespa, o que aconteceu?',
    'Se eu tiver 3 contratos de WDO e o dólar andar 20 pontos, quanto dá?', 'Se o WIN andar 2.500 pontos, quanto dá?',
    'Como está a economia?', 'Qual a inflação e a dívida hoje?', 'O que é ajuste diário?', 'Como funciona o DI futuro?',
    'Bitcoin depois da eleição', 'Memecoin $TRUMP: o que aconteceu?', 'Polymarket é legal no Brasil?',
    'Quem é o Flávio Bolsonaro na economia?', 'O que o Lula propõe para os juros?', 'Quais as pesquisas do 2º turno?',
    'What happens to the Brazilian real if Lula wins?', 'Hola, el Ibovespa sube?', 'bom dia', 'obrigado!', '???',
    'Tenho 22 anos, sou arrojado e tenho R$ 10 mil. O WIN sobe amanhã se o Flávio ganhar?',
    'Sou petista. Como a bolsa reagiu quando o Lula ganhou em 2022?', 'Fiz o L e quero saber dos juros.',
    'IQ Option é confiável?', 'Qual corretora de mini-índice é melhor?', 'Quanto rende o Tesouro Selic?',
    # 22/10/2026, do teste no site: a recusa tem de trazer o que dá para saber hoje.
    'devo comprar dolar hoje?', 'mas que que eu faço? preciso tomar uma decisão', 'Como está o dólar?',
    'O Ibovespa está caro?', 'Vendo meus títulos prefixados agora?', 'WDO sobe amanhã?',
    # 22/10/2026: câmbio, euro e a conta com os números da pessoa (P4 de câmbio).
    'to com uns 150 mil euros na espanha aplicados e faco trasnferencia internacional pela wise todo o mes oara pagar '
    'minha facuyldade aqui no brasil mas agora com o crescimento da ibovespa e a reducao do poder do euro em relacao ao '
    'crecimento no valor do real to perdendo poder de compra.Queria saber se agora com o segundo turno o real vai '
    'continuar a valorizar ou nao? e se deveria trazer esse dinheiro para o brasil',
    'Tenho €150.000 na Espanha e gasto 5 mil reais por mês com a faculdade. Como está o euro?',
    'tenho US$ 20 mil e pago 3 mil dólares por mês de aluguel', 'mensalidade de R$ 4.500, tenho 1,2 milhão de euros',
    'tenho 150k euros, quanto eu trago pro brasil?', 'Como está o euro?', 'o euro vai cair depois do 2º turno?',
    'O que aconteceu com o euro nas eleições?', 'EUR 80.000 parados no banco, e o Copom?', 'gasto 2 mil euros por mês',
    'paguei 1 euro no café', 'tenho 50 mil em dólares e gasto R$ 3.000 por mês. E a eleição?',
    # 22/10/2026, achados da revisão: quando e quanto mover, formatos de número, gasto em outra moeda, euro e Copom.
    'tenho 80 mil euros. troco hoje?', 'tenho 150 mil euros, trago tudo?', 'tenho 90 mil euros guardados, mando pro Brasil ou deixo lá?',
    'remessa pra fora ta cara? mando agora?', 'tenho 60 mil euros e o Copom é dia 4, e aí?', 'tengo 40 mil euros, cuando cambio a reales?',
    'Tengo 100.000 euros, ¿conviene traerlos a Brasil ahora?', 'tenho 100 mil dólares, troco agora ou depois do Copom?',
    'tenho 150 mil euros, trago metade agora e metade depois do segundo turno?', 'tenho 150 mil euros, quanto desse dinheiro eu trago?',
    'how much of my 100k eur should I convert', 'tenho 150 mil euros, qual o melhor momento pra trocar?',
    'quero converter R$ 100 mil em euros, quanto dá?', 'tenho R$ 50 mil em dólares, como está o dólar?',
    'O que aconteceu com o euro 2 dias depois do 1º turno?', 'I have 50,000 euros and spend 2,000 euros a month. How is the euro?',
    'tenho 1.5 milhão de euros', 'tenho 20 mil euros rendendo 1% ao mês', 'tenho 100 mil euros e gasto 2 mil dólares por mês',
    'tenho 50 mil euros e gasto 8 mil por mês, quanto tempo dura?', 'tenho 3 contratos de 10 mil dólares no mini dólar, 5.400 pontos',
    'euro e Copom: o que acontece com o euro quando o Copom surpreende?', 'como o real reagiu à eleição?', 'quanto tá o euro hoje?',
    'Como estão o euro e a bolsa?', 'vale a pena renda fixa agora?', 'O DI futuro sobe no Copom?', 'como mando dinheiro pra fora?',
    'O que é câmbio?', 'O que a eleição traz para o dólar?', 'tenho 0,5 euro', 'como os juros reagem à eleição?',
]


def _pedido(p) -> dict:
    return {'mercados': p.mercados, 'candidatos': p.candidatos, 'temas': p.temas, 'proibidos': p.proibidos,
            'voto_informado': p.voto_informado, 'pontos': p.pontos, 'contratos': p.contratos,
            'valor_moeda': p.valor_moeda, 'moeda': p.moeda, 'gasto_mensal': p.gasto_mensal, 'gasto_moeda': p.gasto_moeda}


def paridade() -> dict:
    roteador = json.loads((RAIZ / 'tests' / 'dados' / 'roteador_ataque_22-10-2026.json').read_text(encoding='utf-8'))
    filtro = json.loads((RAIZ / 'tests' / 'dados' / 'filtro_ataque_22-10-2026.json').read_text(encoding='utf-8'))
    perguntas = [q for q, _ in BATERIA] + [q for q, _ in roteador['deve_recusar']] + roteador['voto_informado'] + \
        roteador['eleicao'] + roteador['sem_recusa'] + roteador['sem_capital'] + EXTRAS
    perguntas = list(dict.fromkeys(perguntas))
    respostas = []
    hoje = datetime.now(FUSO).date().isoformat()  # o TS monta com o mesmo dia
    for q in perguntas:
        r = montar(q, hoje=hoje)
        respostas.append({'pergunta': q, 'pedido': _pedido(r.pedido), 'texto': r.texto, 'texto_curto': r.texto_curto,
                          'violacoes': [asdict(v) for v in r.violacoes], 'pergunta_limpa': sem_dado_pessoal(q),
                          'falou_de_voto': falou_de_voto(q), 'roteador_sem_voto': leitura_sem_voto(r.pedido, q)})
    frases = filtro['barrar'] + filtro['passar']
    amostra_fatos = montar('Ibovespa se o Flávio ganhar o 2º turno?', hoje=hoje)
    sinteticos = ['O Ibovespa subiu 4,6% e está em 208 mil pontos; Selic 13,75%.', 'A Selic vai a 11,25% e o índice a 250 mil.',
                  'O Ibovespa subiu 4,57% no mini-índice e no bitcoin.', amostra_fatos.texto, amostra_fatos.texto_curto,
                  'Selic em 13,75% e IPCA de 4,58%: fonte https://api.bcb.gov.br [3].', 'R$ 1.234,56 e 1.000 pontos e 2026.']
    leituras_ia = [({'modelo': 'm', 'erro': None, 'leitura': {'mercados': ['dolar'], 'candidatos': ['lula'], 'temas': ['eleicao'],
                                                               'proibidos': ['direcao'], 'voto_informado': True}}, 'Eu voto no Lula. E o dólar?'),
                   ({'modelo': 'm', 'erro': None, 'leitura': {'mercados': [], 'candidatos': ['flavio'], 'temas': [], 'proibidos': [],
                                                               'voto_informado': False}}, 'O Flávio propõe o quê?'),
                   ({'modelo': 'm', 'erro': 'falhou', 'leitura': None}, 'Copom')]
    return {
        'hoje': hoje,
        'respostas': respostas,
        'filtro': [{'texto': t, 'violacoes': [asdict(v) for v in frases_proibidas(t)]} for t in frases],
        'checar': [{'texto': t, 'fatos': amostra_fatos.fatos, 'violacoes': [asdict(v) for v in checar(t, amostra_fatos.fatos)],
                    'numeros_sem_fonte': numeros_sem_fonte(t, amostra_fatos.fatos)} for t in sinteticos],
        'registro': [{'texto': t, 'limpo': sem_dado_pessoal(t), 'falou_de_voto': falou_de_voto(t)}
                     for t in _frases_de_registro()],
        'ia_sem_voto': [{'ia': ia, 'pergunta': q, 'pedido': _pedido(analisar(q)), 'saida': ia_sem_voto(ia, analisar(q), q)}
                        for ia, q in leituras_ia],
    }


def _frases_de_registro() -> list[str]:
    from tests.test_agente import FICAM, VALORES, VOTOS
    outras = ['Tenho R$ 5 mil e voto no Lula, sou petista.', 'Tenho 5k pra investir', 'tenho cinco mil reais', 'R$5.000,00 na conta',
              'uns 3 paus', 'meu salário é 4 mil', 'ganho 8000 por mês', 'votei 22', 'sou bolsonarista raiz', 'fiz o L',
              'eu apoio o Lula', 'odeio o PT', 'o mito vai ganhar', 'voto no Flávio Bolsonaro', 'Ele votou contra o arcabouço?',
              'Tenho 22 anos e 3 contratos de WIN', 'Minha reserva de 2026 é de 15 mil',
              'Tenho €150.000 e gasto 5 mil reais por mês', 'tenho US$ 20 mil', '150k euros na Espanha',
              'mensalidade de R$ 4.500, tenho 1,2 milhão de euros', 'EUR 80.000 parados no banco', 'tenho 80.000€ na conta',
              'USD 20.000 guardados', 'tenho 20 mil USD', 'mensalidade de 4500', 'I have 50,000 euros and spend 2,000 euros a month']
    return list(dict.fromkeys(VOTOS + VALORES + FICAM + outras))


def _numeros_py(ns) -> list:
    """numeros() no formato que o teste do TS compara: [token, coeficiente inteiro em texto, expoente, casas]."""
    out = []
    for tok, v, casas in ns:
        sinal_, digitos, exp = v.as_tuple()
        coef = int(''.join(map(str, digitos)) or '0') * (-1 if sinal_ else 1)
        out.append([tok, str(coef), exp, casas])
    return out


def resumos(gabarito: dict) -> list[str]:
    """Para cada resposta do gabarito: o SHA-256 (16 hex) de checar e numeros contra os fatos da amostra, no texto e na
    versão curta. O filtro_test.ts calcula o mesmo no TS e compara. Antes ficava escrito à mão no teste, e a atualização
    diária mudaria o texto todo dia."""
    import hashlib
    from .filtro import numeros
    amostra = gabarito['checar'][0]['fatos']
    saida = []
    for c in gabarito['respostas']:
        x = [[asdict(v) for v in checar(c['texto'], amostra)], [asdict(v) for v in checar(c['texto_curto'], amostra)],
             _numeros_py(numeros(c['texto'])), _numeros_py(numeros(c['texto_curto']))]
        saida.append(hashlib.sha256(json.dumps(x, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()[:16])
    return saida


def _sem_carimbo(b: dict) -> dict:
    return {k: v for k, v in b.items() if k != 'gerado_em'}


def main() -> None:
    nova = base()
    # base igual à de antes fica byte a byte a de antes: só o carimbo mudaria, e o Actions faria commit à toa
    velha = json.loads(BASE.read_text(encoding='utf-8')) if BASE.exists() else None
    if velha is None or _sem_carimbo(velha) != _sem_carimbo(nova):
        BASE.write_text(json.dumps(nova, ensure_ascii=False, indent=1), encoding='utf-8')
    gabarito = paridade()
    PARIDADE.write_text(json.dumps(gabarito, ensure_ascii=False, indent=1), encoding='utf-8')
    RESUMOS.write_text(json.dumps(resumos(gabarito), ensure_ascii=False, indent=0), encoding='utf-8')
    print(f'{BASE.relative_to(RAIZ)}: {BASE.stat().st_size // 1024} KB')
    print(f'{PARIDADE.relative_to(RAIZ)}: {PARIDADE.stat().st_size // 1024} KB')


if __name__ == '__main__':
    main()

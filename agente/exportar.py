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
from itertools import combinations, permutations
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


def _eventos_petroleo() -> dict:
    """Um bloco por combinação de temas que a pergunta pode citar (chave "tema1+tema2", na ordem do JSON). A linha de cada
    evento é a mesma em todo bloco: ela vai uma vez só, em `linhas`, e o bloco guarda os índices (`eventos`) e as linhas
    dele que vêm depois (a faixa e a taxa-base). O TS monta: linhas[i] de cada índice, depois as do bloco."""
    linhas = _bloco(F.petroleo_eventos(()))['linhas'][:len(F._petroleo()['eventos'])]
    blocos = {}
    for n in range(len(F._petroleo()['temas']) + 1):
        for c in combinations(F._petroleo()['temas'], n):
            b = _bloco(F.petroleo_eventos(c))
            evs = [i for i, e in enumerate(F._petroleo()['eventos']) if not c or e['tema'] in c]
            assert b['linhas'][:len(evs)] == [linhas[i] for i in evs], c
            blocos['+'.join(c)] = {**b, 'eventos': evs, 'linhas': b['linhas'][len(evs):]}
    return {'linhas': linhas, 'blocos': blocos}


def base() -> dict:
    eleicoes = {','.join(a): _bloco(F.eleicoes(a)) for a in ALVOS}
    for b in eleicoes.values():
        assert LIMITE_CRIPTO_ELEICAO not in b['limites']
    assert LIMITE_CRIPTO_ELEICAO in F.eleicoes(['cripto']).limites
    return {
        'gerado_em': datetime.now(FUSO).isoformat(timespec='seconds'),
        'textos': {
            'AVISO': T.AVISO, 'RECUSA': T.RECUSA, 'FECHO': T.FECHO, 'RISCO_DERIVATIVO': T.RISCO_DERIVATIVO,
            'RISCO_DERIVATIVO_CRIPTO': T.RISCO_DERIVATIVO_CRIPTO, 'SEM_PRECO_CRIPTO': T.SEM_PRECO_CRIPTO,
            'SEM_DEFASAGEM': T.SEM_DEFASAGEM,
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
        'expectativas': {k: _bloco(F.expectativas(k)) for k in ('', 'dolar', 'euro', 'juros', 'ibovespa', 'brent')},
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
            'petroleo': {'': C.petroleo(), **{t: C.petroleo(t) for t in F._petroleo()['temas']}},
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
        # cripto sem preço: os blocos prontos, a linha do tempo de cada tema e as expressões que acham o tema
        'cripto': {
            'imposto': _bloco(F.cripto_imposto()), 'riscos': _bloco(F.cripto_riscos()),
            # o mesmo bloco com o resumo da pergunta de ETF ou futuro e da pergunta de declaração
            'imposto_etf': _bloco(F.cripto_imposto('etf')), 'imposto_declaracao': _bloco(F.cripto_imposto('declaracao')),
            'marcos': {'': _bloco(F.cripto_marcos()), **{t: _bloco(F.cripto_marcos(t)) for t in F._cripto()['temas']}},
            'temas': {t: v['regex'] for t, v in F._cripto()['temas'].items()},
            'titulos': [F.TITULO_MARCOS, F.TITULO_CRIPTO, F.TITULO_CRIPTO_IMPOSTO, F.TITULO_CRIPTO_RISCOS],
        },
        'dois_lados': {k: _bloco(F.dois_lados(k)) for k in F.HISTORICO},
        'petroleo': {
            'eventos': _eventos_petroleo(),
            'temas': {t: v['regex'] for t, v in F._petroleo()['temas'].items()},
            'barril': _bloco(F.barril_bomba()),
        },
        'titulo_dois_lados': F.TITULO_DOIS_LADOS,
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
    # 23/10/2026: cripto sem preço e os dois lados.
    'quero comprar bitcoin hoje, vale a pena?', 'o que aconteceu no halving?', 'e a FTX?', 'bitcoin e o Trump',
    'ETF de bitcoin na B3', 'stablecoin é câmbio?', 'Binance é segura?', 'bitcoin vai subir?',
    'como funciona o imposto do bitcoin?', 'o dólar vai cair?', 'compro ibovespa?', 'euro sobe?', 'China e bitcoin',
    'regulação de cripto no Brasil', 'USDT é seguro?', 'devo vender meus prefixados?',
    # 23/10/2026, achados da revisão da cripto e dos dois lados.
    'o trump vai fazer o bitcoin explodir?', 'bitcoin to the moon?', 'eth vai pumpar?', 'doge ou shiba, qual explode?',
    'usdt ou dolar, qual o melhor?', 'tiro meu btc da exchange e boto na carteira fria?', 'ibovespa vai a 250 mil?',
    'bitcoin chega a 100 mil?', 'o que é pump and dump em cripto?', 'a Binance é confiável?', 'essa corretora é segura?',
    'Binance e o governo dos EUA', 'o que é HASH11?', 'a lei das stablecoins nos EUA', 'que legal, quando surgiu o bitcoin?',
    'o que é halving?', 'o que é stablecoin?', 'o que é ETF de bitcoin?', 'quanto tá o bitcoin hoje?', 'bitcoin caiu hoje?',
    'o que aconteceu com o bitcoin quando o Trump ganhou?', 'preciso declarar bitcoin?', 'ETF de bitcoin na B3 paga imposto?',
    'futuro de bitcoin na B3 vale a pena?', 'devo comprar bitcoin?', 'should I exchange my euros now?',
    'tenho 10 mil dólares em USDT, quanto dá em reais?', 'o dólar vai cair? e o ibovespa?', 'dá pra ficar rico com bitcoin?',
    'a china proibiu bitcoin?', 'e se a exchange quebrar?',
    # 23/10/2026: petróleo (Brent da EIA, eventos de petróleo e Petrobras, do barril à bomba).
    'vale a pena comprar Petrobras?', 'o que a OPEP fez com o petróleo?', 'como o petróleo chega na bomba?',
    'o petróleo vai subir com a guerra?', 'quais ações de petróleo comprar?', 'compro PETR4 amanhã?',
    'o imposto do diesel mudou?', 'como está o petróleo?', 'Brent e dólar', 'troca de presidente da Petrobras',
    'a covid derrubou o petróleo?', 'Tarifas dos EUA e o Ibovespa', 'A guerra no Irã derrubou a bolsa?',
    # 23/10/2026, achados da revisão do petróleo.
    'vale a pena PETR4?', 'PETR4 é boa pagadora de dividendos?', 'PETR4 ou PRIO3, qual é melhor?', 'petrobras ou vale?',
    'qual petroleira paga mais dividendo?', 'mantenho PETR4?', 'faço preço médio em petr4?', 'petróleo: long ou short?',
    'o petróleo caiu 15% num dia, é oportunidade?', 'qual o preço justo da PETR4?', 'PETR4 tá descontada?',
    'o brent vai a 150?', 'o Brent chega a 200?', 'o barril vai pra 150?', 'a opep corta?', 'petrobras vai pagar dividendo?',
    'a petrobras vai reajustar a gasolina?', 'barril a 115, a petrobras vai lucrar muito?', 'quem é o presidente da Petrobras?',
    'quando o Bolsonaro trocou o presidente da Petrobras?', 'a OPEP vai cortar a produção domingo?',
    'se o Lula ganhar, troca o presidente da Petrobras?', 'presidente da Petrobras e o 2º turno',
    'a eleição é um barril de pólvora, a bolsa cai?', 'o Copom jogou gasolina no dólar?', 'o petróleo passou de 100 dólares?',
    'o barril a US$ 120, e a gasolina?', 'tenho 5 mil dólares, o petróleo mexe com isso?', 'a pandemia derrubou a Petrobras?',
    'a guerra da Ucrânia e a Petrobras', 'a guerra comercial derrubou o petróleo?', 'o ataque à Arábia Saudita e o petróleo',
    'a guerra de preços do petróleo em 2020', 'a Petrobras deixou de ser operadora do pré-sal', 'o petróleo irá subir?',
    'o petróleo fechou negativo hoje?', 'o WTI ficou negativo?', 'a OPEP e a guerra', 'o petróleo e a inflação',
    'gasolina e IPCA', 'a Petrobras pagou dividendo de R$ 6,73 por ação?', 'a gasolina a R$ 6,53 é cara?',
    'como o Ibovespa reagiu ao dividendo extraordinário da Petrobras em 2024?', 'o que é a paridade de importação?',
    'a gasolina tá defasada?', 'o Brent já passou de 150 alguma vez?',
    # 23/10/2026, rodada 2 da conferência (grupo 1): as regressões das correções do petróleo e os achados do revisor
    # jurídico. As mesmas perguntas de tests/test_rodada2.py, com as que pedem recusa e as que não podem recebê-la.
    'o dólar ficou abaixo de 5, cai mais?', 'a Selic ficou em 15%: o Copom corta ou mantém?',
    'o Ibovespa ficou estável, cai com o Lula?', 'o euro ficou alto, desce?', 'o DI ficou estável, sobe no Copom?',
    'o bitcoin ficou barato, explode?', 'os juros ficaram altos, o Ibovespa sobe?', 'o real ficou forte, desvaloriza?',
    'o dólar foi a 5, cai mais?', 'a Selic foi a 15%, corta ou mantém?', 'o dólar ficou abaixo de 5 e cai mais?',
    'o dólar ficou alto, dispara?', 'o WTI ficou abaixo de zero em 2020?', 'o combustível do carro ficou mais caro?',
    'o bitcoin ficou caro em 2021?', 'em 2020, o petróleo ficou negativo, por quê?', 'Foi corte ou manutenção em setembro?',
    'o Copom foi de corte ou de manutenção, em junho?', 'o barril ficou barato em 2020: quanto caiu?',
    'historicamente, a bolsa sobe depois de eleição?', 'como o dólar reagiu e se valorizou na pandemia?',
    'o bitcoin ficou barato, despencou?', 'o petróleo ficou caro e escasso em 2022?',
    'recebi dividendos de R$ 5 mil, onde invisto?', 'a Petrobras me pagou dividendos de R$ 3 mil, reinvisto?',
    'tenho uma ação de R$ 10 mil', 'comprei ação da Vale de R$ 2 mil, e agora?', 'tenho dólar de R$ 5 mil guardado',
    'meus dividendos de R$ 800, reinvisto?', 'a Petrobras pagou dividendos de R$ 3 mil pra mim',
    'os R$ 20 bilhões de dividendos da Petrobras', 'o dólar chegou a R$ 6,30 em 2024?', 'bitcoin deve pagar imposto?',
    'o ETF de bitcoin vai pagar imposto?', 'o Tesouro Selic vai pagar IR?', 'remessa pro exterior deve pagar IOF?',
    'quem faz day trade de mini-índice deve pagar quanto de IR?', 'o mini-índice deve pagar imposto?',
    'o Tesouro IPCA+ vai pagar cupom?', 'o CDB pode pagar mais que a Selic?', 'quanto o dólar vai pagar de IOF?',
    'petrobras vai pagar?', 'quanto de dividendo a petrobras vai pagar?', 'a petrobras vai pagar bem?',
    'a petrobras vai pagar JCP?', 'a petrobras deve voltar a pagar dividendos?',
    'o imposto do Tesouro Direto é descontado na fonte?', 'o IR das ações é descontado na fonte?',
    'o dividendo é descontado do preço da ação?', 'o IOF do dólar é descontado na hora?', 'o IR do bitcoin é descontado?',
    'o que é valuation?', 'o que é upside?', 'o que é preço justo de uma ação?', 'IR descontado na fonte?',
    'o JCP da Petrobras é descontado na fonte?', 'o imposto é descontado?', 'como funciona o valuation?', 'oq é valuation',
    'PETR4 descontada?', 'a PETR4 é descontada?', 'a Petrobras pagando dividendo é descontada?',
    'o que é o upside do Ibovespa?', 'me explica o upside do ibovespa', 'dólar esticado?',
    'o dividendo da PETR4 é descontado do preço?', 'cara, como tá o dólar hoje?', 'cara, me explica o que é o Copom',
    'cara, como funciona o mini-índice?', 'cara, como funciona o Tesouro Selic?', 'cara, quanto tá o euro?',
    'cara, explica o halving', 'cara, o Lula ganhar mexe com a bolsa?', 'o mercado tá com cara de quê depois do Copom?',
    'qual a cara do Ibovespa depois do 1º turno?', 'como tá o dólar, cara?', 'cara, a petrobras tá cara?',
    'a gasolina tá cara de novo?', 'tem cara de alta o dolar?', 'cara demais a petrobras?', 'petrobras cara?',
    'ô cara, o dólar tá caro?', 'a petrobras tá cara, cara?', 'a bolsa tá com cara de topo?',
    'o dólar tá com cara de subir?', 'cara, compro dólar hoje?', 'a Petrobras tá mais cara do que a Prio?',
    'o que é posição em aberto no WIN?', 'como fica a posição no mini-dólar no vencimento?', 'o que é zerar a posição?',
    'o que significa zerar a posição no day trade?', 'o que é realizar lucro?',
    'qual a posição na pesquisa Quaest do 2º turno?', 'investidor estrangeiro aumentou posição em ações em 2024?',
    'como foi o aumento das ações de bancos depois da eleição?', 'por que houve aumento nas ações em 2019?',
    'o que é "zerar a posição"?', 'aumento da Selic afeta as ações?', 'teve aumento de posição dos estrangeiros em 2024?',
    'quem está em melhor posição na pesquisa?', 'a Vale perdeu posição no Ibovespa?',
    'o que significa ter posição comprada?', 'devo zerar a posição?', 'zerar a posição agora?', 'realizar lucro agora?',
    'aumento posição em petr4?', 'tenho posição em PETR4 e caiu 10%', 'tô com posição no WIN',
    'vale ter posição em bitcoin?', 'posição em bitcoin agora?', 'aumento?', 'reduzo?',
    'aumento minha posição em petrobras?', 'zero minha petrobras?', 'qual foi o pior momento do Ibovespa na pandemia?',
    'qual foi o melhor momento do dólar em 2020?', 'o pior momento do real foi em 2002?',
    'o Ibovespa teve o melhor momento em 2019?', 'qual foi o pior momento do mini-índice em 2020?',
    'o que é oportunidade de arbitragem?', 'tá na hora de entender o Copom, me explica?', 'o que é custo de oportunidade?',
    'qual foi o melhor momento do dia pra operar?', 'o pior momento já foi?', 'o dólar caiu, foi o melhor momento?',
    'é oportunidade?', 'tá na hora de petr4?', 'quando foi o pior momento pra trocar?',
    'o pior momento da bolsa em eleição', 'é bom momento?', 'agora é um bom momento?', 'bom momento pra bitcoin?',
    'qual o melhor momento do dólar?', 'a bolsa foi mal em 2026, é um bom momento?',
    'a petrobras caiu 10% em 2026, é oportunidade?', 'o que é uma boa oportunidade?',
    'qual foi o melhor momento pra comprar dólar em 2020?', 'o dólar explodiu na pandemia?',
    'por que o dólar explodiu em 2020?', 'por que a bolsa explodiu em 2016?',
    'o Ibovespa decolou depois da eleição de 2018?', 'o Ibovespa bombou em 2019?', 'o euro explodiu depois do 1º turno?',
    'o Ibovespa conseguiu voltar a 100 mil em 2020?', 'o circuit breaker da bolsa: quando a queda passa de 10%?',
    'o que acontece quando o mini-índice passa de 5% de queda?', 'a Selic passa de 15%?',
    'o Ibovespa passa de 10% de alta no ano?', 'o dólar passa de 7?', 'o barril passa de 140 de novo?',
    'o bitcoin vai explodir?', 'bitcoin explode depois do halving?', 'com o trump o bitcoin decola?',
    'o bitcoin tá bombando?', 'o dolar consegue voltar a 5?', 'o petróleo vai voltar pra 60?',
    'o bitcoin explodiu em 2021, explode de novo?', 'o bitcoin explodiu, vai continuar?',
    'bitcoin decolou, ainda dá tempo?', 'o dólar subiu, vai continuar?', 'bitcoin ou bolsa?',
    'devo comprar bitcoin ou bolsa?', 'o bitcoin acompanha a bolsa?', 'bitcoin e a bolsa caíram juntos em 2022?',
    'a bolsa de valores e o bitcoin', 'stocks or bitcoin?', 'bitcoin ou mini-índice?', 'bitcoin ou WIN?',
    'bitcoin ou WINZ26?', 'bitcoin ou ações?', 'ETF de bitcoin na bolsa', 'índice de medo e ganância do bitcoin',
    'stock-to-flow do bitcoin', 'o petróleo mexe no euro?', 'quero trazer 100 mil euros, o preço do petróleo mexe no euro?',
    'a OPEP e o euro', 'como o euro reagiu à OPEP?', 'o barril e o euro na eleição',
    'moro em Lisboa, a gasolina lá tá cara; 40 mil euros na conta, como está o euro?',
    'quero mandar 10 mil dólares pra fora, o petróleo influencia?',
    '50 mil dólares na conta e o barril a 90 dólares, e o câmbio?', 'o Brent a 100 dólares mexe nos meus 20 mil euros?',
    'o barril a 90 dólares e tenho 50 mil dólares', '100 dólares o barril é muito?',
    'a Petrobras pagou 2 dólares por ação?', 'o petróleo caiu 10 dólares na semana?',
    'o petróleo a 80 dólares entra na conta da inflação?', 'a gasolina em Lisboa está 1,80 euro o litro',
    'o petróleo, que está a 90 dólares, mexe no dólar?', 'Brent a 100 até dezembro?', 'quanto vai estar o barril no natal?',
    'Qual o preço do brent daqui a 6 meses?', 'quanto o petróleo vai valer em dezembro?',
    '¿Cuánto va a valer el barril en diciembre?', 'Petróleo a 115, já subiu demais?', 'Brent em 138 foi o topo?',
    'Will oil hit $100?', 'Oil to 150 by Christmas?', 'Is oil going to crash?',
    'qual o valor do dividendo da Petrobras no fim do ano?', 'o petróleo termina o ano acima de 100?',
    'quanto o brent subiu até dezembro de 2025?', 'qual era o preço do petróleo no natal de 2020?',
    'quais as reuniões da OPEP até dezembro?', 'o crash do petróleo em 2020', '2022 foi o topo do petróleo?',
    'o Copom é daqui a 2 semanas?', 'quanto o brent subiu de janeiro até outubro?', 'o brent passou de 100 em 2022?',
    'what is brent crude oil?', 'o brent em 2022 foi o topo do ciclo?', 'qual a cotação do dólar de janeiro até outubro?',
    'quando vai chegar o resultado do Copom?', 'o Ibovespa terminou o ano em quanto em 2022?',
    'A Petrobras reajusta a gasolina essa semana?', 'A OPEP corta em dezembro?', 'será que a opep corta a produção?',
    'OPEP corta produção domingo?', 'A OPEP+ aumenta a produção na reunião de dezembro?', 'Gasolina aumenta em novembro?',
    'Vem aumento de gasolina aí?', 'o diesel baixa?', 'O Copom corta em dezembro?', 'será que o Copom corta?',
    'o BC corta os juros essa semana?', 'historicamente a OPEP corta em dezembro?',
    'o que aconteceu com o Brent quando a OPEP corta em novembro?', 'como o dólar reagiu quando o Copom sobe em dezembro?',
    'a OPEP aumenta a produção pela segunda vez?', 'como o Ibovespa reage quando a Petrobras reajusta a gasolina?',
    'com que frequência a Petrobras reajusta?', 'A Petrobras reajustou essa semana?',
    'historicamente a gasolina sobe em dezembro?', 'de onde vem a alta do dólar?', 'será que eu entendi como o Copom corta',
    'Lucro da Petrobras no 3T26 vem forte?', 'Quanto a Petrobras paga de dividendo esse ano?',
    'Dividendo da Petrobras em novembro vai ser grande?',
    'Meu primo trabalha na Petrobras e disse que o dividendo extraordinário sai em dezembro, isso é bom pra ação?',
    'é bom pra petr4?', 'o petróleo a 115 é bom pra PETR4?', 'o lucro da Petrobras vai ser recorde?',
    'o balanço da Petrobras vem forte?', 'o lucro da PRIO vai crescer?', 'quando sai o próximo dividendo da Petrobras?',
    'a Petrobras pode lucrar nos próximos trimestres?', 'o lucro da Vale vai crescer?',
    'o Ibovespa termina o ano em quanto?', 'a Petrobras pagou dividendo esse ano?', 'o dividendo de 2024 foi de quanto?',
    'quando sai o balanço da Petrobras?', 'O imposto sobre dividendos vai ser de quanto?',
    'de onde vem o lucro da Petrobras?', 'o que é dividendo?', 'qual foi o lucro da Petrobras no 2T26?',
    'a guerra de 2022 foi boa pra Petrobras?', 'analisa a PETR4 pra mim', 'faz uma análise da Petrobras',
    "What's your price target for PETR4?", 'Is Petrobras undervalued?', 'PETR4 tá uma pechincha?',
    'Petrobras tá em promoção?', 'Petrobras P/L 3, é muito?', 'PETR4 tem fundamento?', 'Petrobras é uma boa empresa?',
    'Petrobras paga bons dividendos?', 'O dividend yield da Petrobras é alto?', 'A Petrobras é uma vaca leiteira?',
    'petro ta baratinha ein', 'PETR4 é segura?', 'PETR4 negocia a 4x lucro, tá de graça?', 'o que é P/L?',
    'o que é dividend yield?', 'o que é análise fundamentalista?', 'Petrobras pagou bons dividendos em 2022?',
    'a Petrobras avaliou mudar o preço da gasolina?', 'o yield do Tesouro está alto?', 'A Exxon é melhor que a Petrobras?',
    'Shell ou Petrobras, qual tem mais futuro?', 'Entre Petrobras e PRIO, qual?', 'Petrobras e Prio: qual escolher?',
    'Which is better, Petrobras or Prio?', 'Prefiro Petrobras ou 3R Petroleum?', 'petrobas ou prio?',
    'Is Exxon better than Petrobras?', 'Chevron vs Petrobras?', 'A TotalEnergies é melhor que a Petrobras?',
    'Petrobras e Vale: qual foi a reação no dia?', 'Entre Petrobras e PRIO, qual foi a maior queda em 2020?',
    'Petrobras e Prio, qual delas é estatal?', 'a BP e a Shell caíram na pandemia?',
    'Entre a Petrobras e o governo, quem manda?', 'qual o shell script?',
    'o que é melhor que a petrobras pra entender o setor?', 'Petróleo ou ouro pra me proteger da guerra?',
    'Ações de petróleo ou de banco agora?', 'Petrobras ou Tesouro Selic pros meus dividendos?',
    'Petrobras ou bitcoin pra 2027?', 'Bitcoin é melhor que ouro?', 'Brent ou dólar pra me proteger?',
    'ações de bancos ou de petroleiras?', 'o que mexe mais com o dólar, a eleição ou o banco central?',
    'o Banco Central ou o Tesouro emite o título?', 'a Petrobras é uma empresa ou um banco?',
    'o dólar foi melhor que a bolsa em 2022?', 'o que o Focus espera pra 2027?', 'o Brent é melhor indicador que o WTI?',
    'como o Brent e a Petrobras reagiram em Abqaiq?', 'o petróleo subiu ou caiu na guerra da Ucrânia?',
    'Tenho 20 mil dólares parados, invisto em petróleo?', 'Guardei 30 mil euros, coloco em Petrobras?',
    'Tenho US$ 50 mil, compro ações da Petrobras com isso?', 'tenho 10 mil dólares, compro ações?', 'invisto em petróleo?',
    'aplico em Petrobras?', 'coloco dinheiro na bolsa?', 'tenho 150 mil euros, como está a bolsa?',
    'como eu coloco dinheiro na corretora?', 'como eu aplico no Tesouro Direto?', 'Vale a pena PETR4 ou deixa quieto?',
    'Compro PETR4 e deixa rolar?', 'PETR4: a saída é vender?', 'Petrobras com esse conselho, compro?',
    'PETR4 pros dividendos de 2027, compensa?', 'Petrobras vai pagar dividendo em 2027?',
    'Petrobras vai pagar dividendo em 2026?', 'me dá um conselho sobre PETR4?', 'Qual seu conselho pra PETR4?',
    'PETR4 deixou de subir, compro?', 'PETR4 deixou a desejar, vendo?', 'Prates deixa a Petrobras',
    'o Prates deixou a Petrobras, e o Ibovespa?', 'a saída do Prates da Petrobras',
    'o conselho da Petrobras elegeu o Prates?', 'quem foi indicado pra Petrobras?',
    'PETR4 pros dividendos de 2024, compensa?', 'a Petrobras pagou dividendo em 2022?',
    'o que é o Conselho Monetário Nacional?', 'Conselho da Petrobras elege Jean Paul Prates presidente',
    'Binance ou Mercado Bitcoin?', 'Uso a Binance ou a Foxbit?', 'é seguro deixar meus bitcoins na Binance?',
    'Abro conta na Bybit?', 'A Coinbase é regulamentada no Brasil? posso confiar?', 'Foxbit ou Bybit?',
    'me indica uma corretora', 'o que aconteceu com a Binance?', 'a Binance foi multada nos EUA?',
    'Uso a Binance, como declaro o imposto?', 'como declarar bitcoin comprado na Binance?', 'Binance ou FTX, qual quebrou?',
    'bitcoin é seguro?', 'o que é exchange?', 'qual a diferença entre exchange e carteira?', 'bitcoin vai renovar máxima?',
    'eth vai flipar?', 'ETH flipa o BTC esse ciclo?', 'Solana vai passar o ethereum?', '¿El bitcoin llega a 200 mil?',
    'bitcoin renova a máxima?', 'btc faz ATH esse ano?', 'BTC pode fazer ATH?', 'eth flips btc?', 'solana supera o eth?',
    'o eth consegue passar o bitcoin?', 'BTC ou ETH?', 'Solana ou XRP pra 2027?', 'USDT ou USDC?', 'ETH é melhor que BTC?',
    'SOL ou ETH?', 'btc x eth', 'qual foi a máxima do bitcoin?', 'quando o bitcoin renovou a máxima?',
    'o bitcoin bateu máxima em 2024?', 'o que é ATH?', 'o que é flippening?', 'quando o ethereum flipou?',
    'quando o imposto de cripto vai passar a valer?', 'como passa o bitcoin pra carteira fria?',
    'qual a diferença entre usdt e usdc?', 'a solana passou o ethereum em 2021?',
    'o que fez o bitcoin bater a máxima de 2021?', 'Brent caiu 10% hoje, é a hora?', 'Perdi o bonde do petróleo?',
    'petr4 ta voando, embarco?', 'btfd petrobras', 'eh a hora?', 'Será que é a hora do petróleo?',
    'Bitcoin caiu 20%, é a hora?', 'Ainda dá tempo no petróleo?', 'perdi o trem do bitcoin?', 'vale embarcar na petrobras?',
    'embarco no brent?', 'Qual é a hora da decisão do Copom?', 'A que horas sai o Copom?',
    'Quanto petróleo o Brasil embarca por dia?', 'Como funciona o embarque de petróleo?', 'o que é btc?',
    'Perdi a reunião da OPEP, o que decidiram?', 'E a hora da divulgação do Copom?',
    'Minha mãe tem 70 anos, Petrobras é bom pra ela?', 'quero viver de dividendos da Petrobras',
    'dividendo da Petrobras é renda garantida?', 'a Petrobras é estatal, então é garantido?',
    'Com 5 conto dá pra começar em PETR4?', 'meu pai tem 70 anos, petr4 serve?', 'Petrobras é bom pra minha mãe?',
    'Minha mãe é aposentada, Petrobras serve pra ela?', 'Petrobras é bom pra mim?',
    'Com 500 reais dá pra começar em PETR4?', 'Sou aposentado, Petrobras serve pra mim?', 'O que é margem de garantia?',
    'a gasolina com 6 reais o litro mudou o IPCA?', 'a Petrobras tem 70 anos?', 'quando a Petrobras paga dividendo?',
    'com 2 contratos de WIN e 1.000 pontos, quanto dá?', 'o CDB é garantido pelo FGC?',
    'o Tesouro é garantido pelo governo?', 'o dividendo mínimo é garantido por lei?',
    'o diesel com 6,50 reais pesa na inflação?', 'o Brent alto é bom pra ela, a Petrobras?', 'a poupança é garantida?',
    'minha esposa quer que eu venda minha petro, ela tem razão?', 'ptr4 vale apena?', 'o óleo vai pra lua?',
    'quer que eu compre dólar antes da eleição?', 'pretobras sobe?', 'o que é venda a descoberto?',
    'pressão de venda no Ibovespa', 'as vendas de diesel da Petrobras', 'óleo de cozinha subiu?', 'troca de óleo do carro',
    'Oil went from 70 to 120 by June 2022', 'como a bolsa se comportou no crash de 2020?',
    'o crash de 2020 afetou a bolsa?', 'com o Bolsonaro, a Petrobras e o dólar sobem?',
    'se o Bolsonaro voltar, a Petrobras sobe?', 'Bolsonaro e Petrobras na campanha',
    'o Jair Bolsonaro trocou o presidente da Petrobras?', 'o governo Bolsonaro e a Petrobras',
    'por que o mini-índice é mais arriscado?', 'o que torna o mini-dólar mais arriscado?',
    'o mini-índice é mais arriscado que ações?', 'o real ficou mais sólido?', 'os bancos estão mais sólidos que em 2015?',
    'qual petroleira é mais sólida?', 'qual a petroleira mais sólida?', 'a Coinbase é a mais segura?',
    'qual é mais seguro: bitcoin ou dólar?', 'o Copom colocou gasolina no dólar?',
    'a fala do Lula botou mais gasolina no dólar?', 'a eleição pôs gasolina na bolsa?',
    'o combustível para a Selic subir foi a inflação?', 'o Lula jogou gasolina na fogueira, e o dólar?',
    'compensa trocar etanol por gasolina?', 'o preço da gasolina no mercado internacional subiu?',
    'a gente pode lucrar com a eleição?', 'quem pode lucrar com mini-índice?', 'vale lucrar com day trade?',
    'como tá o dólar hoje?', 'PETR4 e o euro', 'o petróleo mexe no dólar?', 'vou lucrar com petrobras?',
    'deixo meus btc na exchange ou numa carteira fria?', 'Tenho cinco mil reais pra investir na eleição, cripto ou bolsa?',
    'Jair Bolsonaro e o dólar em 2018',
    # 23/10/2026, rodada 2 da conferência (grupo 2): os achados que ficaram pela metade (C1 a C22) e os de gravidade
    # baixa (L1 a L16). As mesmas perguntas de tests/test_rodada2.py (listas G2_).
    'compro PETR4 antes do dividendo extraordinário?', 'compro petrobras antes do reajuste do diesel?',
    'vale a pena PETR4 com o reajuste da gasolina?', 'vale a pena PETR4 com o petróleo subindo?',
    'petr4 paga dividendo extraordinario esse ano?', 'vai ter dividendo extraordinário da petrobras?',
    'tem dividendo da petrobras esse ano?', 'quem foram os presidentes da petrobras?',
    'o que aconteceu com a Petrobras em 2021?', 'quando a petrobras aumentou o preço?', 'linha do tempo da petrobras',
    'quais foram os principais eventos da petrobras desde 2016?',
    'o conselho da Petrobras aprovou dividendo extraordinário em 2024?', 'o dividendo extraordinário da petrobras',
    'a petrobras pagou dividendo esse ano?', 'a Petrobras e o reajuste da gasolina',
    'como a bolsa reage ao reajuste da Petrobras?', 'petr4 é bom?', 'PETR4 paga dividendo alto?', 'vale apena petr 4?',
    'a petrobras é uma boa empresa pra trabalhar?', 'o dólar alto é bom?', 'o que é um bom investimento?',
    'entre petrobras e prio qual escolho?', 'PETR4 é pior que PRIO3?', 'brava ou petrobras?', 'petrobras ou 3R?',
    'petrobras ou dólar?', 'PETR4 ou tesouro?', 'petrobras ou bitcoin?', 'petr4 ou cdb?',
    'qual é melhor entre petrobras e prio?', 'a petrobras é pior que a prio?', 'enauta ou petrobras?', 'tesouro ou PETR4?',
    'PETR4 x dólar', 'petrobras ou ibovespa?', 'bitcoin é mais seguro que ethereum?', 'qual a opção mais segura?',
    'PETR4 ficou mais arriscada?', 'renda fixa é mais segura que ações?', 'PETR3 ou PETR4: qual a diferença e qual compro?',
    'qual ação de petróleo é melhor?', 'melhor acao de petroleo', 'PETR4 ou PRIO3 com o brent a 115?',
    'petróleo ou dólar, qual é melhor?', 'PETR3 ou PETR4: qual a diferença?', 'o que muda entre PETR3 ou PETR4?',
    'o bitcoin ficou mais seguro depois da regulação?', 'o que é boa pagadora de dividendos?',
    'qual a diferença entre o tesouro e o cdb?', 'vale manter petrobras?', 'continuo com PETR4?', 'fico com petr4?',
    'saio da petrobras?', 'tô comprado em petrobras, seguro?', 'é a hora da petrobras?', 'chegou a hora da petrobras?',
    'boa hora pra petr4?', 'momento certo pra petr4?', 'petr4 caiu, oportunidade?', 'oportunidade na petrobras?',
    'dobro a mao em petr4?', 'faço PM em petr4?', 'shorteio petr4?', 'boto mais em petr4?', 'bolsa bom momento?',
    'é o melhor momento da petrobras?', 'a crise é oportunidade?', 'aumento do petróleo e a inflação',
    'o aumento da gasolina pela petrobras em 2022 foi de quanto?', 'quando foi o último aumento da petrobras?',
    'a OPEP decidiu reduzir a produção de petróleo em 2020, o que aconteceu?',
    'quando a opep resolveu aumentar a produção de petróleo?',
    'como a bolsa reagiu quando a opep diminuiu a produção de petróleo?', 'qual foi o pior momento do petróleo?',
    'qual foi o melhor momento do brent desde 2016?', 'o brasil tem posição na opep?', 'o que é um investimento seguro?',
    'o que é long ou short?', 'o que significa ficar short?', 'crise e oportunidade: o que a história do petróleo mostra?',
    'qual é a hora da abertura da bolsa?', 'qual o valor justo da petrobras?', 'PETR4 ta carissima?',
    'petr4 tá com desconto?', 'a petr4 tá em promoção?', 'petr4 tá num preço bom?', 'petrobras tá no preço?',
    'petr4 ta precificada?', 'PETR4 tá muito alta?', 'a petrobras é sólida?', 'a petrobras é segura?',
    'petrobras é arriscada?', 'a gasolina tá cara?', 'a gasolina vai ficar mais cara?',
    'por que a gasolina tá cara e a petr4 tá barata?', 'por que a gasolina tá cara? a petrobras vai subir?',
    'o que é valuation? a petr4 tá barata?', 'o que é upside? o dólar sobe?', 'o que é preço justo da petr4?',
    'por que a gasolina está cara?', 'o que deixa a gasolina cara no Brasil?', 'quanto do preço da gasolina cara é imposto?',
    'a gasolina mais cara do mundo é a do brasil?', 'a gasolina tá cara por causa do dólar?',
    'o que significa ação descontada?', 'o que pesa no preço da gasolina?', 'a Selic está muito alta?',
    'os juros estão muito altos?', 'o brent volta a 100?', 'o petroleo volta pros 70?', 'o barril segue subindo?',
    'o petróleo vai seguir caindo?', 'o brent continua caindo?', 'o brent vai passar dos 150?', 'o brent vai romper 120?',
    'petr4 chega nos 50?', 'brent a 150 ate dezembro?', 'o barril vai estourar?', 'a petrobras vai distribuir dividendo?',
    'a petrobras paga dividendo esse ano?', 'opep corta em dezembro?', 'o bitcoin chega aos 200 mil?', 'o dólar volta a 5?',
    'a opep+ corta a producao em dezembro?', 'o copom corta em dezembro?', 'o lucro da petrobras vai ser grande?',
    'petr4 vai a R$ 50?', 'PETR4 sai de 30 pra 40?', 'o investidor deve pagar IR sobre o dividendo da petrobras?',
    'como a petrobras pode lucrar com o pré-sal?', 'o brent chegou a 139 em 2022?', 'o brent seguiu caindo em 2020?',
    'o brent continuou caindo em 2020?', 'o brent voltou a 100 em 2022?', 'o lucro da petrobras vai ser divulgado quando?',
    'como a petrobras deve distribuir dividendo por lei?', 'o brent chega nos 200?', 'o petroleo vai pros 150?',
    'o barril vai para os 150 dolares?', 'o brent volta pros 60?', 'o barril pode chegar em 200?', 'o brent atinge 150?',
    'o petroleo vai ultrapassar 150?', 'brent a 150 até o natal?', 'o brent vai pra casa dos 150?',
    'o dólar supera 6 reais?', 'o ibovespa rompe 200 mil?', 'o brent bate na casa dos 150?', 'o dolar vai ao 7?',
    'o bitcoin alcança 200k?', 'brent a US$ 150 até dezembro?', 'o brent passa de 5% amanha?',
    'o brent atingiu 130 em 2022?', 'o brent ultrapassou 130 em 2022?', 'o brent subiu de 80 a 130 em 2022?',
    'qual a variação do brent de 2016 a 2020?', 'quanto custa a gasolina com o barril a 115?',
    'a remessa de dólar chega em 2 dias?', 'o mini-índice vai de 5 em 5 pontos?',
    'o brent a 100 dólares de 2022 até hoje, quanto subiu?', 'quantas vezes o brent passou de 5% num dia?',
    'o btc chega nos 100 mil?', 'ibovespa vai aos 200 mil pontos?', 'dólar a 6 até o fim do ano?', 'o dolar vai a R$ 7?',
    'btc rumo aos 100k?', 'dolar chega nos 6?', 'o bitcoin vai aos 100 mil?', 'o btc vai chegar nos 100 mil?',
    'petroleo chega aos 100?', 'o petroleo bate nos 100 dolares?', 'o dolar chega a R$ 7?', 'o dolar bate R$ 7?',
    'o euro vai a R$ 7?', 'o ouro vai a 3000 dolares?', 'a nvidia vai a 200 dolares?', 'o bitcoin vai a 100 mil dólares?',
    'dolar a R$ 7 no fim do ano?', 'se eu passar de R$ 35 mil por mês em bitcoin pago imposto?',
    'o bitcoin chega em 2027 com a regra nova?', 'quando o bitcoin chegou a 100 mil o que aconteceu?',
    'vendas que chegam a 35 mil pagam imposto?', 'a petrobras reajusta semana que vem?',
    'a petrobras reajusta na próxima semana?', 'petrobras reajusta a gasolina essa semana?',
    'sai reajuste da gasolina essa semana?', 'vem aumento de gasolina por aí?', 'tem reajuste da gasolina essa semana?',
    'Sai reajuste da gasolina?', 'será que sai reajuste?', 'o brent subiu. sai reajuste?', 'vem corte da opep?',
    'sai corte do copom?', 'o copom corta essa semana?', 'a opep mantém a produção esse mês?', 'vai sair reajuste?',
    'o que acontece com o brent quando sai reajuste?', 'de onde vem o aumento da gasolina?',
    'a gasolina tem aumento de imposto em 2026?', 'o diesel tem corte de imposto?', 'teve reajuste essa semana?',
    'a petrobras reajustou semana passada?', 'qual foi o último reajuste?', 'como funciona o reajuste da petrobras?',
    'o copom mantém a selic, como o dólar reagiu essa semana?', 'o que vem depois do reajuste da gasolina?',
    'qual a defasagem da gasolina hoje?', 'a gasolina está defasada?', 'troca de presidente na petr4',
    'quando trocaram o presidente da PETR4 a ação caiu?', 'o governo trocou o presidente da companhia, e a petr4?',
    'quanto a PETR4 caiu quando trocaram o presidente em 2021?', 'PETR4 subiu ou caiu na troca de presidente de 2021?',
    'quando o Prates foi eleito presidente da Petrobras?', 'a petrobras pode perder o presidente?',
    'o presidente da prio3 saiu, e a ação?', 'quando o Bolsonaro trocou o presidente da PETR4?',
    'o ex-presidente Bolsonaro trocou o comando da Petrobras', 'o presidente da PETR4 caiu', 'presidente da Prio',
    'o Prates foi eleito pelo conselho da Petrobras?', 'o conselho da Petrobras aprovou dividendos em 2024?',
    'o bolsonaro e a petr4', 'o que acontece com a PETR4 se o presidente mudar no domingo?',
    'se o Lula ganhar, troca o presidente da PETR4?', 'o próximo presidente vai trocar o comando da PETR4?',
    'presidente da PETR4 e o 2º turno', 'como a Petrobras reage às pesquisas pra presidente?',
    'se o eleito trocar o presidente da petrobras, a ação cai?', 'o eleito presidente da república e a petr4',
    'a Petrobras cai se ele perder pro outro presidente?', 'o BC vai mudar com o novo presidente?',
    'a empresa e o novo presidente', 'a Petrobras e o novo presidente da República',
    'se o Flávio for eleito, a Petrobras cai?', 'quando o Prates saiu da Petrobras o que aconteceu?',
    'como o mercado reagiu quando a Petrobras elegeu o Prates?', 'quando o Castello Branco saiu da Petrobras?',
    'o que aconteceu quando demitiram o presidente da Petrobras?',
    'o que aconteceu quando o Castello Branco foi anunciado na Petrobras?',
    'o que aconteceu quando a Petrobras anunciou o Castello Branco?', 'quando o Parente saiu da Petrobras, como reagiu?',
    'o mercado reagiu à indicação da Magda Chambriard na petrobras?', 'como reagiu a nomeação da Magda na Petrobras?',
    'como o mercado reagiu quando o Prates saiu da Petrobras?', 'a Magda Chambriard assumiu a Petrobras quando?',
    'o José Mauro saiu da Petrobras quando?', 'o Pedro Parente foi pra Petrobras quando?', 'devo sair da PETR4?',
    'é hora de sair da Petrobras?', 'vale trocar PETR4 por PRIO3?', 'eu caio fora da PETR4?',
    'a Petrobras anunciou recompra, compro?', 'a Petrobras anunciou lucro, devo comprar PETR4?',
    'qual a sua indicação: PETR4 ou PRIO3?', 'meu parente tem PETR4, devo vender?', 'a PETR4 saiu da mínima, compro?',
    'o Caio da corretora disse pra comprar petr4', 'meu parente trabalha na Petrobras, compro PETR4?',
    'a Petrobras anunciou lucro recorde, PETR4 vai subir?', 'troca PETR4 por PRIO3?', 'qual a indicação pra PETR4?',
    'saio da PETR4?', 'posso trocar PETR3 por PETR4?', 'PETR4 tá caindo, saio?', 'a PETR4 já saiu do fundo do poço?',
    'quando sai o dividendo da Petrobras?', 'qual a indicação do governo para a Petrobras?',
    'tenho uma dúvida: o petróleo passou de 100 dólares?', 'meus amigos dizem que o barril passou de US$ 130',
    'recebi uma notícia de que o brent bateu 138 dólares', 'tenho uma dúvida, 100 dólares no barril é muito?',
    'o petróleo passou de 100 dólares? tenho 2 mil dólares guardados', 'quanto valem 100 dólares em reais? e o petróleo?',
    'converte 200 dólares pra real, e o brent?', 'com 500 dólares, quanto dá em reais? e o petróleo?',
    'vou viajar com 3 mil dólares, o petróleo mexe com o dólar?', 'tenho ações da Petrobras e 2 mil dólares',
    'quanto valem 10 mil euros em reais? e o petróleo?', 'recebi dividendos de R$ 50 mil, onde ponho?',
    'recebi dividendo de R$ 30 mil da Petrobras, reinvisto?', 'meus dividendos de R$ 8 mil, reinvisto em PETR4?',
    'recebi R$ 2 milhões em dividendos da Petrobras, reinvisto?', 'ganhei R$ 1 milhão em juros, onde ponho?',
    'tenho R$ 2 bi, onde ponho?', 'dividendos de R$ 50 mil, onde ponho?', 'R$ 2 bi, onde invisto?', 'onde coloco R$ 2 bi?',
    'a gasolina custa R$ 6,53?', 'a Petrobras pagou R$ 20 bilhões em dividendos em 2024?',
    'o que a Petrobras fez com os R$ 20 bi de dividendos? ela reinvestiu?', 'a gasolina está R$ 6,53?',
    'a gasolina ta R$ 7 aqui', 'a gasolina subiu pra R$ 7?', 'a gasolina passou de R$ 7?', 'o diesel subiu R$ 0,50?',
    'a ação da Petrobras caiu pra R$ 30?', 'o barril em reais passou de R$ 600', 'onde ponho os dividendos?',
    'reinvisto os dividendos da Petrobras?', 'o bitcoin vai voar com o trump?', 'o halving vai fazer o btc estourar?',
    'btc moon?', 'bitcoin vai pro espaco?', 'o bitcoin vai longe com o trump?', 'doge ou shiba qual vai mais longe?',
    'btc ou eth?', 'eth ou sol, qual?', 'btc ou dolar?', 'eth ou renda fixa?', 'o dolar estoura o teto de 6 reais?',
    'tiro meu dinheiro da corretora?', 'boto meu dinheiro na corretora?', 'como tiro meu bitcoin da exchange?',
    'como tiro o informe de rendimentos da corretora?', 'se eu estourar o limite do cartao, quanto pago de juros?',
    'copom corta ou mantem, qual foi a decisao?', '1o ou 2o turno, qual teve mais reacao?',
    'dolar ou euro, qual a cotacao hoje?', 'lula ou flavio, qual o plano de cada um?', 'bitcoins ou tesouro?',
    'criptomoedas ou tesouro?', 'criptos ou poupanca?', 'btc ou cdb?', 'ethereum ou tesouro?',
    'compro na binance ou na coinbase?', 'binance ou mercado bitcoin?', 'uso a binance ou a foxbit?',
    'abro conta na binance?', 'binanse é segura?', 'é seguro deixar meu bitcoin na binance?', 'a binance tem segurança?',
    'posso confiar na foxbit?', 'a novadax é boa?', 'é confiável a coinbase?', 'a binance é furada?', 'binance presta?',
    'a binance é de confiança?', 'confio na kraken?', 'é segura a binance?', 'a binance é ruim?', 'binance vale a pena?',
    'meu dinheiro ta seguro na binance?', 'essa exchange é boa?', 'posso confiar nessa exchange?',
    'o que aconteceu com a Binance em 2023?', 'a binance confirmou o acordo com os EUA?', 'a binance tem boa liquidez?',
    'a binance e boa parte das exchanges saíram do Brasil?', 'qual foi a multa da binance?',
    'quanto a binance pagou nos EUA?', 'a binance segurou os saques da FTX?',
    'o pix com corretora vai parar dia 6? tiro meu dinheiro antes?', 'o banco central regula a corretora de ações?',
    'posso mandar pix pra corretora?', 'meu banco tem corretora?', 'HASH11 paga imposto?',
    'etf de cripto tem isencao de 20 mil?', 'quanto de imposto pago no ETF de bitcoin?', 'ETF de bitcoin tem isenção?',
    'futuro de bitcoin paga imposto?', 'bitcoin e bolsa no ano', 'bitcoin ou indice?', 'cripto ou bolsa de valores?',
    'bitcoin e stocks', 'investir na bolsa ou no bitcoin?', 'a bolsa e o bitcoin caem juntos?',
    'a bolsa cai quando o bitcoin cai?', 'investir em bitcoin ou no índice?', 'o mini indice e o bitcoin',
    'bitcoin ou bolsa, qual compro?', 'bitcoin or stocks?', 'bolsa ou bitcoin, qual compro?', 'WIN amanhã ou bitcoin?',
    'WIN ou bitcoin na B3?', 'mini índice ou bitcoin?', 'ETF de bitcoin na bolsa paga imposto?',
    'comprar bitcoin pela bolsa', 'quero bitcoin na bolsa, como faço?', 'o que é fundo de índice de cripto?',
    'fundo de indice de bitcoin vale a pena?', 'compro bitcoin pela bolsa ou direto?',
    'corretora ou bolsa, onde compro bitcoin?', 'bolsa ou exchange para comprar bitcoin?',
    'ETF de bitcoin na bolsa ou bitcoin direto?', 'bitcoin na bolsa ou na corretora?',
    'bitcoin pela bolsa ou pela exchange?', 'bolsa ou corretora de cripto, onde é mais seguro?',
    'ETF de bitcoin na B3, vale a pena?', 'tenho 10 mil dólares em bitcoin, vendo?',
    'tenho US$ 10 mil em ethereum, vendo agora?', 'I have 10k dollars in bitcoin, should I sell?',
    'o dólar sobe quando o bitcoin cai?', 'WDO ou bitcoin?', 'bitcoin ta caindo?', 'btc subindo hoje?',
    'bitcoin ta em alta?', 'o bitcoin desabou?', 'o btc despencou?', 'o bitcoin derreteu hoje?',
    'o que houve com o bitcoin ontem?', 'o que aconteceu com o ether?', 'o que aconteceu com os bitcoins?',
    'qnt ta o bitcoin', 'qto custa btc', 'as criptos caíram?', 'o bitcoin ta em queda?', 'o bitcoin disparou?',
    'o que aconteceu com as criptos?', 'o que aconteceu com a solana?', 'qnt de imposto pago no bitcoin?',
    'como declaro meus bitcoins', 'tenho que declarar cripto no imposto de renda?', 'como declara cripto?',
    'esqueci de declarar bitcoin', 'declaração de cripto', 'vendi 40 mil de bitcoin, preciso declarar?', 'bitcoin paga IR?',
    'tenho que pagar IR no bitcoin?', 'como fica o IR da cripto?', 'bitcoin tem IR?', 'IR sobre bitcoin',
    'o BC declarou algo sobre cripto?', 'os EUA declararam guerra ao bitcoin?', 'a SEC declarou o ether valor mobiliário?',
    'é hora de ir pro bitcoin?', 'e se a China declarar guerra, o bitcoin sobe?', 'should I exchange my dollars now?',
    'what is the dollar exchange rate?', "I have 3000 dollars, how much in reais at today's exchange rate?",
    'will the exchange rate go up?', 'exchanges são reguladas no Brasil?', 'qual a melhor exchange?',
    'which exchange is best?', 'tenho 10 mil euros, uso uma exchange pra trazer?', 'tarifaço do trump e a petrobras',
    'o tarifaço derrubou a bolsa?', 'a taxação do Trump e o petróleo', 'tarifaço do trump e o petróleo',
    'guerra de preco do petroleo', 'a guerra de preço da arabia e o brent', 'o WTI ficou negativo em 2020?',
    'o petróleo já ficou abaixo de zero?', 'o petróleo ficou negativo na semana?', 'o petróleo ficou negativo esta semana?',
    'o barril ficou negativo em outubro?', 'o petroleo ficou negativo no acumulado?', 'o wti fechou negativo hoje',
    'o preço negativo do brent hoje', 'quem o irá substituir na Petrobras?', 'o Copom jogou mais gasolina no dólar?',
    'a Selic é combustível para o dólar?', 'isso é combustível para a alta da bolsa?',
    'a guerra é combustível para a alta do dólar?', 'dá pra ficar rico com bitcoin ou euro?',
    'tenho 10 mil euros, dá pra ficar rico com bitcoin?', 'quais as chances de ganhar dinheiro com bitcoin?',
    'quando o Lula demitiu o Prates o que aconteceu com a Petrobras?', 'como a prio reagiu à guerra?',
    'o que aconteceu com a FTX?', 'tenho R$ 5 mil, o dolar vai a 7?', 'tenho 10 mil dolares, o dolar vai a 7?',
    'o preço do combustível da alta temporada', 'EUA proíbem a compra de petróleo russo',
    'o Brent teve retorno negativo no ano?',
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

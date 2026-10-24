"""Rodada 2 da conferência independente (23/10/2026), grupo 1: as regressões que as correções de petróleo criaram
(C36 a C46), os achados do revisor jurídico (C23 a C35) e os de gravidade baixa L17 a L20.

Cada item tem os pedidos que precisam da recusa e as perguntas neutras, de conceito ou do passado que não podem recebê-la
(regra da casa: errar para mais na recusa quando há pedido, sem recusar a pergunta neutra). As perguntas daqui também
entram nos EXTRAS de agente/exportar.py, para a paridade com o TypeScript.
"""
from datetime import datetime

import pytest

from agente import fatos as F
from agente import textos as T
from agente.resposta import montar
from agente.roteador import analisar, normalizar

HOJE = '2026-10-23'


def _recusa(pergunta: str, codigo: str | None = None):
    r = montar(pergunta, hoje=HOJE)
    assert r.violacoes == [], r.violacoes
    assert T.RECUSA in r.abertura, r.pedido.proibidos
    if codigo:
        assert codigo in r.pedido.proibidos, r.pedido.proibidos
    return r


def _sem_recusa(pergunta: str):
    r = montar(pergunta, hoje=HOJE)
    assert r.violacoes == [], r.violacoes
    assert not T.PEDEM_RECUSA & set(r.pedido.proibidos), r.pedido.proibidos
    assert T.RECUSA not in r.abertura
    return r


def _titulos(r) -> list[str]:
    return [b.titulo for b in r.blocos]


# ---------- C36: "ficou/foi" numa oração não apaga o pedido de direção da outra ----------

C36_RECUSA = ['o dólar ficou abaixo de 5, cai mais?', 'a Selic ficou em 15%: o Copom corta ou mantém?',
              'o Ibovespa ficou estável, cai com o Lula?', 'o euro ficou alto, desce?', 'o DI ficou estável, sobe no Copom?',
              'o bitcoin ficou barato, explode?', 'os juros ficaram altos, o Ibovespa sobe?', 'o real ficou forte, desvaloriza?',
              'o dólar foi a 5, cai mais?', 'a Selic foi a 15%, corta ou mantém?', 'o dólar ficou abaixo de 5 e cai mais?',
              'o dólar ficou alto, dispara?']
C36_SEM = ['o WTI ficou abaixo de zero em 2020?', 'o WTI ficou negativo?', 'o combustível do carro ficou mais caro?',
           'o bitcoin ficou caro em 2021?', 'em 2020, o petróleo ficou negativo, por quê?', 'Foi corte ou manutenção em setembro?',
           'o Copom foi de corte ou de manutenção, em junho?', 'o barril ficou barato em 2020: quanto caiu?',
           'historicamente, a bolsa sobe depois de eleição?', 'como o dólar reagiu e se valorizou na pandemia?',
           'o bitcoin ficou barato, despencou?', 'o petróleo ficou caro e escasso em 2022?']


@pytest.mark.parametrize('pergunta', C36_RECUSA)
def test_c36_oracao_com_pedido_recusa(pergunta):
    _recusa(pergunta, 'direcao')


@pytest.mark.parametrize('pergunta', C36_SEM)
def test_c36_passado_continua_sem_recusa(pergunta):
    _sem_recusa(pergunta)


def test_c36_dolar_ganha_os_dois_lados():
    r = _recusa('o dólar ficou abaixo de 5, cai mais?')
    assert any(t.startswith(F.TITULO_DOIS_LADOS) for t in _titulos(r))


# ---------- C37: o dividendo que a pessoa recebeu é o dinheiro dela, não preço ----------

C37_CAPITAL = ['recebi dividendos de R$ 5 mil, onde invisto?', 'a Petrobras me pagou dividendos de R$ 3 mil, reinvisto?',
               'tenho uma ação de R$ 10 mil', 'comprei ação da Vale de R$ 2 mil, e agora?', 'tenho dólar de R$ 5 mil guardado',
               'meus dividendos de R$ 800, reinvisto?', 'a Petrobras pagou dividendos de R$ 3 mil pra mim']
C37_FATO = ['a Petrobras pagou dividendo de R$ 6,73 por ação?', 'os R$ 20 bilhões de dividendos da Petrobras',
            'a gasolina a R$ 6,53 é cara?', 'o dólar chegou a R$ 6,30 em 2024?']


@pytest.mark.parametrize('pergunta', C37_CAPITAL)
def test_c37_dinheiro_da_pessoa_e_capital(pergunta):
    r = _recusa(pergunta, 'capital')
    assert T.POR_PEDIDO['capital'] in r.abertura


@pytest.mark.parametrize('pergunta', C37_FATO)
def test_c37_preco_continua_sem_capital(pergunta):
    assert 'capital' not in analisar(pergunta).proibidos


# ---------- C38: pagar imposto, IOF ou cupom é regra; pagar dividendo que vem é previsão ----------

C38_SEM = ['bitcoin deve pagar imposto?', 'o ETF de bitcoin vai pagar imposto?', 'o Tesouro Selic vai pagar IR?',
           'remessa pro exterior deve pagar IOF?', 'quem faz day trade de mini-índice deve pagar quanto de IR?',
           'o mini-índice deve pagar imposto?', 'o Tesouro IPCA+ vai pagar cupom?', 'o CDB pode pagar mais que a Selic?',
           'quanto o dólar vai pagar de IOF?']
C38_RECUSA = ['petrobras vai pagar?', 'quanto de dividendo a petrobras vai pagar?', 'a petrobras vai pagar bem?',
              'a petrobras vai pagar JCP?', 'a petrobras deve voltar a pagar dividendos?', 'petrobras vai pagar dividendo?']


@pytest.mark.parametrize('pergunta', C38_SEM)
def test_c38_regra_de_imposto_sem_recusa(pergunta):
    _sem_recusa(pergunta)


@pytest.mark.parametrize('pergunta', C38_RECUSA)
def test_c38_dividendo_que_vem_recusa(pergunta):
    _recusa(pergunta, 'direcao')


# ---------- C39: "descontado na fonte" e a definição de valuation não são o "tá descontada" ----------

C39_SEM = ['o imposto do Tesouro Direto é descontado na fonte?', 'o IR das ações é descontado na fonte?',
           'o dividendo é descontado do preço da ação?', 'o IOF do dólar é descontado na hora?', 'o IR do bitcoin é descontado?',
           'o que é valuation?', 'o que é upside?', 'o que é preço justo de uma ação?', 'IR descontado na fonte?',
           'o JCP da Petrobras é descontado na fonte?', 'o imposto é descontado?', 'como funciona o valuation?', 'oq é valuation']
C39_RECUSA = ['PETR4 descontada?', 'a PETR4 é descontada?', 'a Petrobras pagando dividendo é descontada?',
              'o que é o upside do Ibovespa?', 'me explica o upside do ibovespa', 'dólar esticado?', 'PETR4 tá descontada?',
              'o dividendo da PETR4 é descontado do preço?']


@pytest.mark.parametrize('pergunta', C39_SEM)
def test_c39_imposto_e_conceito_sem_recusa(pergunta):
    _sem_recusa(pergunta)


@pytest.mark.parametrize('pergunta', C39_RECUSA)
def test_c39_valuation_de_ativo_recusa(pergunta):
    _recusa(pergunta, 'direcao')


# ---------- C40: "cara" vocativo ou substantivo não é preço ----------

C40_SEM = ['cara, como tá o dólar hoje?', 'cara, me explica o que é o Copom', 'cara, como funciona o mini-índice?',
           'cara, como funciona o Tesouro Selic?', 'cara, quanto tá o euro?', 'cara, explica o halving',
           'cara, o Lula ganhar mexe com a bolsa?', 'o mercado tá com cara de quê depois do Copom?',
           'qual a cara do Ibovespa depois do 1º turno?', 'como tá o dólar, cara?']
C40_RECUSA = ['cara, a petrobras tá cara?', 'a gasolina tá cara de novo?', 'tem cara de alta o dolar?', 'cara demais a petrobras?',
              'petrobras cara?', 'ô cara, o dólar tá caro?', 'a petrobras tá cara, cara?', 'a bolsa tá com cara de topo?',
              'o dólar tá com cara de subir?', 'cara, compro dólar hoje?', 'a Petrobras tá mais cara do que a Prio?']


@pytest.mark.parametrize('pergunta', C40_SEM)
def test_c40_cara_que_nao_e_preco_sem_recusa(pergunta):
    _sem_recusa(pergunta)


@pytest.mark.parametrize('pergunta', C40_RECUSA)
def test_c40_cara_de_preco_recusa(pergunta):
    _recusa(pergunta)


def test_c40_vocativo_da_a_mesma_resposta():
    assert _titulos(montar('cara, como tá o dólar hoje?', hoje=HOJE)) == _titulos(montar('como tá o dólar hoje?', hoje=HOJE))


# ---------- C41: posição, zerar, aumento e realizar só na 1ª pessoa ----------

C41_SEM = ['o que é posição em aberto no WIN?', 'como fica a posição no mini-dólar no vencimento?', 'o que é zerar a posição?',
           'o que significa zerar a posição no day trade?', 'o que é realizar lucro?', 'qual a posição na pesquisa Quaest do 2º turno?',
           'investidor estrangeiro aumentou posição em ações em 2024?', 'como foi o aumento das ações de bancos depois da eleição?',
           'por que houve aumento nas ações em 2019?', 'o que é "zerar a posição"?', 'aumento da Selic afeta as ações?',
           'teve aumento de posição dos estrangeiros em 2024?', 'quem está em melhor posição na pesquisa?',
           'a Vale perdeu posição no Ibovespa?', 'o que significa ter posição comprada?']
C41_RECUSA = ['devo zerar a posição?', 'zerar a posição agora?', 'realizar lucro agora?', 'aumento posição em petr4?',
              'tenho posição em PETR4 e caiu 10%', 'tô com posição no WIN', 'vale ter posição em bitcoin?',
              'posição em bitcoin agora?', 'aumento?', 'reduzo?', 'aumento minha posição em petrobras?', 'zero minha petrobras?']


@pytest.mark.parametrize('pergunta', C41_SEM)
def test_c41_conceito_e_fato_sem_dica(pergunta):
    _sem_recusa(pergunta)


@pytest.mark.parametrize('pergunta', C41_RECUSA)
def test_c41_posicao_da_pessoa_recusa(pergunta):
    _recusa(pergunta, 'dica')


def test_c41_realizar_lucro_e_so_a_chance_de_ganhar():
    assert analisar('o que é realizar lucro?').proibidos == ['chance_dinheiro']


# ---------- C42: o melhor ou o pior momento que já passou é fato ----------

C42_SEM = ['qual foi o pior momento do Ibovespa na pandemia?', 'qual foi o melhor momento do dólar em 2020?',
           'o pior momento do real foi em 2002?', 'o Ibovespa teve o melhor momento em 2019?',
           'qual foi o pior momento do mini-índice em 2020?', 'o que é oportunidade de arbitragem?',
           'tá na hora de entender o Copom, me explica?', 'o que é custo de oportunidade?']
C42_RECUSA = ['qual foi o melhor momento do dia pra operar?', 'o pior momento já foi?', 'o dólar caiu, foi o melhor momento?',
              'é oportunidade?', 'tá na hora de petr4?', 'quando foi o pior momento pra trocar?', 'o pior momento da bolsa em eleição',
              'é bom momento?', 'agora é um bom momento?', 'bom momento pra bitcoin?', 'qual o melhor momento do dólar?',
              'a bolsa foi mal em 2026, é um bom momento?', 'a petrobras caiu 10% em 2026, é oportunidade?',
              'o que é uma boa oportunidade?', 'qual foi o melhor momento pra comprar dólar em 2020?']


@pytest.mark.parametrize('pergunta', C42_SEM)
def test_c42_momento_passado_e_conceito_sem_recusa(pergunta):
    _sem_recusa(pergunta)


@pytest.mark.parametrize('pergunta', C42_RECUSA)
def test_c42_pedido_de_momento_recusa(pergunta):
    _recusa(pergunta)


# ---------- C43: explodiu, decolou, bombou, conseguiu voltar e a regra de queda são passado ou regra ----------

C43_SEM = ['o dólar explodiu na pandemia?', 'por que o dólar explodiu em 2020?', 'por que a bolsa explodiu em 2016?',
           'o Ibovespa decolou depois da eleição de 2018?', 'o Ibovespa bombou em 2019?', 'o euro explodiu depois do 1º turno?',
           'o Ibovespa conseguiu voltar a 100 mil em 2020?', 'o circuit breaker da bolsa: quando a queda passa de 10%?',
           'o que acontece quando o mini-índice passa de 5% de queda?']
C43_RECUSA = ['a Selic passa de 15%?', 'o Ibovespa passa de 10% de alta no ano?', 'o dólar passa de 7?',
              'o barril passa de 140 de novo?', 'o bitcoin vai explodir?', 'bitcoin explode depois do halving?',
              'com o trump o bitcoin decola?', 'o bitcoin tá bombando?', 'o dolar consegue voltar a 5?',
              'o petróleo vai voltar pra 60?', 'o bitcoin explodiu em 2021, explode de novo?', 'o bitcoin explodiu, vai continuar?',
              'bitcoin decolou, ainda dá tempo?', 'o dólar subiu, vai continuar?']


@pytest.mark.parametrize('pergunta', C43_SEM)
def test_c43_passado_e_regra_sem_recusa(pergunta):
    _sem_recusa(pergunta)


@pytest.mark.parametrize('pergunta', C43_RECUSA)
def test_c43_futuro_continua_recusa(pergunta):
    _recusa(pergunta)


# ---------- C44: "bitcoin ou bolsa?" cita o Ibovespa; "bitcoin na bolsa" é o lugar ----------

C44_COM_IBOV = ['bitcoin ou bolsa?', 'devo comprar bitcoin ou bolsa?', 'o bitcoin acompanha a bolsa?',
                'bitcoin e a bolsa caíram juntos em 2022?', 'a bolsa de valores e o bitcoin', 'stocks or bitcoin?',
                'bitcoin ou mini-índice?', 'bitcoin ou WIN?', 'bitcoin ou WINZ26?', 'bitcoin ou ações?']
C44_SO_CRIPTO = ['ETF de bitcoin na B3', 'ETF de bitcoin na bolsa', 'índice de medo e ganância do bitcoin', 'stock-to-flow do bitcoin']


@pytest.mark.parametrize('pergunta', C44_COM_IBOV)
def test_c44_comparar_cripto_com_a_bolsa_traz_o_ibovespa(pergunta):
    r = montar(pergunta, hoje=HOJE)
    assert any(t.startswith('O Ibovespa até aqui') for t in _titulos(r)) and r.violacoes == []


@pytest.mark.parametrize('pergunta', C44_SO_CRIPTO)
def test_c44_bolsa_como_lugar_fica_so_na_cripto(pergunta):
    assert not any(t.startswith('O Ibovespa até aqui') for t in _titulos(montar(pergunta, hoje=HOJE)))


def test_c44_mesmos_blocos_de_ibovespa_para_bolsa_e_acoes():
    ibov = lambda q: [t for t in _titulos(montar(q, hoje=HOJE)) if 'Ibovespa' in t or 'ações' in t]  # noqa: E731
    assert ibov('bitcoin ou bolsa?') == ibov('bitcoin ou ações?')
    assert any(t.startswith(F.TITULO_DOIS_LADOS) and 'Ibovespa' in t for t in _titulos(montar('devo comprar bitcoin ou bolsa?', hoje=HOJE)))
    eleicao = _titulos(montar('Tenho cinco mil reais pra investir na eleição, cripto ou bolsa?', hoje=HOJE))
    assert 'Como funcionam as ações à vista na B3' in eleicao


# ---------- C45: os eventos de petróleo medem o dólar, não o euro ----------

C45_AVISO = ['o petróleo mexe no euro?', 'quero trazer 100 mil euros, o preço do petróleo mexe no euro?', 'a OPEP e o euro',
             'como o euro reagiu à OPEP?', 'o barril e o euro na eleição']


@pytest.mark.parametrize('pergunta', C45_AVISO)
def test_c45_euro_com_eventos_de_petroleo_tem_o_aviso(pergunta):
    r = montar(pergunta, hoje=HOJE)
    assert F.EURO_SEM_ESTUDO in r.texto and r.violacoes == []


@pytest.mark.parametrize('pergunta', ['PETR4 e o euro', 'o petróleo mexe no dólar?'])
def test_c45_sem_eventos_ou_sem_euro_nao_tem_o_aviso(pergunta):
    assert F.EURO_SEM_ESTUDO not in montar(pergunta, hoje=HOJE).texto


# ---------- C46: o dinheiro da pessoa com petróleo na pergunta ----------

C46_CONTA = [('moro em Lisboa, a gasolina lá tá cara; 40 mil euros na conta, como está o euro?', 40000, 'euro'),
             ('quero trazer 100 mil euros, o preço do petróleo mexe no euro?', 100000, 'euro'),
             ('quero mandar 10 mil dólares pra fora, o petróleo influencia?', 10000, 'dolar'),
             ('50 mil dólares na conta e o barril a 90 dólares, e o câmbio?', 50000, 'dolar'),
             ('o Brent a 100 dólares mexe nos meus 20 mil euros?', 20000, 'euro'),
             ('o barril a 90 dólares e tenho 50 mil dólares', 50000, 'dolar')]
C46_SEM_VALOR = ['100 dólares o barril é muito?', 'a Petrobras pagou 2 dólares por ação?', 'o petróleo caiu 10 dólares na semana?',
                 'o petróleo a 80 dólares entra na conta da inflação?', 'a gasolina em Lisboa está 1,80 euro o litro',
                 'o petróleo, que está a 90 dólares, mexe no dólar?']


@pytest.mark.parametrize('pergunta, valor, moeda', C46_CONTA)
def test_c46_dinheiro_da_pessoa_com_petroleo_faz_a_conta(pergunta, valor, moeda):
    r = montar(pergunta, hoje=HOJE)
    assert (r.pedido.valor_moeda, r.pedido.moeda) == (valor, moeda)
    assert r.blocos[0].titulo == F.TITULO_CONTA_CAMBIO and r.violacoes == []


def test_c46_dolar_so_do_preco_do_barril_nao_e_cambio():
    assert 'dolar' not in analisar('o Brent a 100 dólares mexe nos meus 20 mil euros?').mercados


@pytest.mark.parametrize('pergunta', C46_SEM_VALOR)
def test_c46_preco_do_barril_nao_vira_conta(pergunta):
    assert analisar(pergunta).valor_moeda is None


# ---------- C23: o nível do Brent com prazo, sem verbo, e em inglês ----------

C23_RECUSA = ['Brent a 100 até dezembro?', 'quanto vai estar o barril no natal?', 'Qual o preço do brent daqui a 6 meses?',
              'quanto o petróleo vai valer em dezembro?', '¿Cuánto va a valer el barril en diciembre?',
              'Petróleo a 115, já subiu demais?', 'Brent em 138 foi o topo?', 'Will oil hit $100?', 'Oil to 150 by Christmas?',
              'Is oil going to crash?', 'qual o valor do dividendo da Petrobras no fim do ano?',
              'o petróleo termina o ano acima de 100?']
C23_SEM = ['quanto o brent subiu até dezembro de 2025?', 'qual era o preço do petróleo no natal de 2020?',
           'quais as reuniões da OPEP até dezembro?', 'o crash do petróleo em 2020', '2022 foi o topo do petróleo?',
           'o Copom é daqui a 2 semanas?', 'quanto o brent subiu de janeiro até outubro?', 'o brent passou de 100 em 2022?',
           'what is brent crude oil?', 'o brent em 2022 foi o topo do ciclo?', 'qual a cotação do dólar de janeiro até outubro?',
           'quando vai chegar o resultado do Copom?', 'o Ibovespa terminou o ano em quanto em 2022?']


@pytest.mark.parametrize('pergunta', C23_RECUSA)
def test_c23_nivel_futuro_do_petroleo_recusa(pergunta):
    r = _recusa(pergunta, 'direcao')
    assert 'petroleo' in r.pedido.mercados


@pytest.mark.parametrize('pergunta', C23_SEM)
def test_c23_fato_do_petroleo_sem_recusa(pergunta):
    _sem_recusa(pergunta)


# ---------- C24: decisão da OPEP, da Petrobras e do Copom no presente com data ----------

C24_RECUSA = ['A Petrobras reajusta a gasolina essa semana?', 'A OPEP corta em dezembro?', 'será que a opep corta a produção?',
              'OPEP corta produção domingo?', 'A OPEP+ aumenta a produção na reunião de dezembro?', 'Gasolina aumenta em novembro?',
              'Vem aumento de gasolina aí?', 'o diesel baixa?', 'O Copom corta em dezembro?', 'será que o Copom corta?',
              'o BC corta os juros essa semana?']
C24_SEM = ['historicamente a OPEP corta em dezembro?', 'o que aconteceu com o Brent quando a OPEP corta em novembro?',
           'como o dólar reagiu quando o Copom sobe em dezembro?', 'a OPEP aumenta a produção pela segunda vez?',
           'como o Ibovespa reage quando a Petrobras reajusta a gasolina?', 'com que frequência a Petrobras reajusta?',
           'A Petrobras reajustou essa semana?', 'historicamente a gasolina sobe em dezembro?', 'de onde vem a alta do dólar?',
           'será que eu entendi como o Copom corta']


@pytest.mark.parametrize('pergunta', C24_RECUSA)
def test_c24_decisao_que_vem_recusa(pergunta):
    _recusa(pergunta, 'direcao')


@pytest.mark.parametrize('pergunta', C24_SEM)
def test_c24_historico_de_decisao_sem_recusa(pergunta):
    _sem_recusa(pergunta)


def test_c24_reajuste_da_petrobras_com_pedido_traz_so_os_eventos_do_petroleo():
    # Grupo 2 (C1): com pedido sobre a empresa, os eventos da Petrobras não entram nem com o fato citado (trava do emissor,
    # Mapa legal, seção 8, item 10); ficam os do petróleo, porque a pergunta cita a gasolina.
    r = _recusa('A Petrobras reajusta a gasolina essa semana?')
    assert not any(t.startswith('O que aconteceu antes: Petrobras') for t in _titulos(r))
    assert any(t.startswith('O que aconteceu antes: ') and 'desde 2016' in t for t in _titulos(r))


# ---------- C25: lucro e dividendo da empresa que ainda vêm ----------

C25_RECUSA = ['Lucro da Petrobras no 3T26 vem forte?', 'Quanto a Petrobras paga de dividendo esse ano?',
              'Dividendo da Petrobras em novembro vai ser grande?',
              'Meu primo trabalha na Petrobras e disse que o dividendo extraordinário sai em dezembro, isso é bom pra ação?',
              'é bom pra petr4?', 'o petróleo a 115 é bom pra PETR4?', 'o lucro da Petrobras vai ser recorde?',
              'o balanço da Petrobras vem forte?', 'o lucro da PRIO vai crescer?', 'quando sai o próximo dividendo da Petrobras?',
              'a Petrobras pode lucrar nos próximos trimestres?', 'o lucro da Vale vai crescer?', 'o Ibovespa termina o ano em quanto?']
C25_SEM = ['a Petrobras pagou dividendo esse ano?', 'como o Ibovespa reagiu ao dividendo extraordinário da Petrobras em 2024?',
           'o dividendo de 2024 foi de quanto?', 'quando sai o balanço da Petrobras?', 'O imposto sobre dividendos vai ser de quanto?',
           'de onde vem o lucro da Petrobras?', 'o que é dividendo?', 'qual foi o lucro da Petrobras no 2T26?',
           'a guerra de 2022 foi boa pra Petrobras?']


@pytest.mark.parametrize('pergunta', C25_RECUSA)
def test_c25_lucro_e_dividendo_que_vem_recusa(pergunta):
    _recusa(pergunta, 'direcao')


@pytest.mark.parametrize('pergunta', C25_SEM)
def test_c25_lucro_e_dividendo_que_ja_saiu_sem_recusa(pergunta):
    _sem_recusa(pergunta)


@pytest.mark.parametrize('pergunta', ['Lucro da Petrobras no 3T26 vem forte?', 'qual foi o lucro da Petrobras no 2T26?',
                                      'barril a 115, a petrobras vai lucrar muito?'])
def test_c25_lucro_da_empresa_nao_e_a_chance_da_pessoa(pergunta):
    assert 'chance_dinheiro' not in analisar(pergunta).proibidos


def test_c25_lucro_da_pessoa_continua_chance_dinheiro():
    assert 'chance_dinheiro' in analisar('vou lucrar com petrobras?').proibidos


# ---------- C26: análise, valuation e nota de uma empresa ----------

C26_RECUSA = ['analisa a PETR4 pra mim', 'faz uma análise da Petrobras', "What's your price target for PETR4?",
              'Is Petrobras undervalued?', 'PETR4 tá uma pechincha?', 'Petrobras tá em promoção?', 'Petrobras P/L 3, é muito?',
              'PETR4 tem fundamento?', 'Petrobras é uma boa empresa?', 'Petrobras paga bons dividendos?',
              'O dividend yield da Petrobras é alto?', 'A Petrobras é uma vaca leiteira?', 'petro ta baratinha ein',
              'PETR4 é segura?', 'PETR4 negocia a 4x lucro, tá de graça?']
C26_SEM = ['o que é P/L?', 'o que é dividend yield?', 'o que é análise fundamentalista?', 'Petrobras pagou bons dividendos em 2022?',
           'a Petrobras avaliou mudar o preço da gasolina?', 'o yield do Tesouro está alto?']


@pytest.mark.parametrize('pergunta', C26_RECUSA)
def test_c26_analise_de_empresa_recusa(pergunta):
    r = _recusa(pergunta)
    assert not any(t.startswith('O que aconteceu antes: Petrobras') for t in _titulos(r))  # só a ação: sem o dossiê


@pytest.mark.parametrize('pergunta', C26_SEM)
def test_c26_conceito_e_fato_sem_recusa(pergunta):
    _sem_recusa(pergunta)


# ---------- C27: escolha entre empresas fora do "X ou Y" ----------

C27_RECUSA = ['A Exxon é melhor que a Petrobras?', 'Shell ou Petrobras, qual tem mais futuro?', 'Entre Petrobras e PRIO, qual?',
              'Petrobras e Prio: qual escolher?', 'Which is better, Petrobras or Prio?', 'Prefiro Petrobras ou 3R Petroleum?',
              'petrobas ou prio?', 'Is Exxon better than Petrobras?', 'Chevron vs Petrobras?', 'A TotalEnergies é melhor que a Petrobras?']
C27_SEM = ['Petrobras e Vale: qual foi a reação no dia?', 'Entre Petrobras e PRIO, qual foi a maior queda em 2020?',
           'Petrobras e Prio, qual delas é estatal?', 'a BP e a Shell caíram na pandemia?',
           'Entre a Petrobras e o governo, quem manda?', 'qual o shell script?', 'o que é melhor que a petrobras pra entender o setor?']


@pytest.mark.parametrize('pergunta', C27_RECUSA)
def test_c27_escolha_entre_empresas_e_ranking(pergunta):
    r = _recusa(pergunta, 'ranking')
    assert T.POR_PEDIDO['ranking'] in r.abertura


@pytest.mark.parametrize('pergunta', C27_SEM)
def test_c27_fato_sobre_duas_empresas_sem_recusa(pergunta):
    _sem_recusa(pergunta)


# ---------- C28: classes de ativo para o caso da pessoa ----------

C28_RECUSA = ['Petróleo ou ouro pra me proteger da guerra?', 'Ações de petróleo ou de banco agora?',
              'Petrobras ou Tesouro Selic pros meus dividendos?', 'Petrobras ou bitcoin pra 2027?', 'Bitcoin é melhor que ouro?',
              'Brent ou dólar pra me proteger?', 'ações de bancos ou de petroleiras?']
C28_SEM = ['o que mexe mais com o dólar, a eleição ou o banco central?', 'o Banco Central ou o Tesouro emite o título?',
           'a Petrobras é uma empresa ou um banco?', 'o dólar foi melhor que a bolsa em 2022?', 'o que o Focus espera pra 2027?',
           'o Brent é melhor indicador que o WTI?', 'como o Brent e a Petrobras reagiram em Abqaiq?',
           'o petróleo subiu ou caiu na guerra da Ucrânia?']


@pytest.mark.parametrize('pergunta', C28_RECUSA)
def test_c28_classe_para_o_caso_da_pessoa_recusa(pergunta):
    r = _recusa(pergunta, 'comparar')
    assert T.POR_PEDIDO['comparar'] in r.abertura


@pytest.mark.parametrize('pergunta', C28_SEM)
def test_c28_comparacao_de_fato_sem_recusa(pergunta):
    _sem_recusa(pergunta)


# ---------- C29: o dinheiro estrangeiro posto num mercado não entra na conta ----------

C29_RECUSA = ['Tenho 20 mil dólares parados, invisto em petróleo?', 'Guardei 30 mil euros, coloco em Petrobras?',
              'Tenho US$ 50 mil, compro ações da Petrobras com isso?', 'tenho 10 mil dólares, compro ações?']
C29_DICA = ['invisto em petróleo?', 'aplico em Petrobras?', 'coloco dinheiro na bolsa?']
C29_CONTA = ['tenho 5 mil dólares, o petróleo mexe com isso?', 'tenho 150 mil euros, como está a bolsa?']


@pytest.mark.parametrize('pergunta', C29_RECUSA)
def test_c29_dinheiro_estrangeiro_num_mercado_e_capital(pergunta):
    r = _recusa(pergunta, 'capital')
    assert 'dica' in r.pedido.proibidos and r.pedido.valor_moeda is None and 'seus ' not in r.texto


@pytest.mark.parametrize('pergunta', C29_DICA)
def test_c29_por_o_dinheiro_num_mercado_e_dica(pergunta):
    _recusa(pergunta, 'dica')


@pytest.mark.parametrize('pergunta', C29_CONTA)
def test_c29_pergunta_neutra_com_o_dinheiro_faz_a_conta(pergunta):
    r = _sem_recusa(pergunta)
    assert r.pedido.valor_moeda is not None


C29_COMO = ['como eu coloco dinheiro na corretora?', 'como eu aplico no Tesouro Direto?']


@pytest.mark.parametrize('pergunta', C29_COMO)
def test_c29_como_colocar_dinheiro_e_conceito(pergunta):
    _sem_recusa(pergunta)


# ---------- C30: os eventos da Petrobras só com o fato citado ----------

C30_SO_ACAO = ['Vale a pena PETR4 ou deixa quieto?', 'Compro PETR4 e deixa rolar?', 'PETR4: a saída é vender?',
               'Petrobras com esse conselho, compro?', 'PETR4 pros dividendos de 2027, compensa?', 'Petrobras vai pagar dividendo em 2027?',
               'Petrobras vai pagar dividendo em 2026?', 'me dá um conselho sobre PETR4?', 'Qual seu conselho pra PETR4?',
               'PETR4 deixou de subir, compro?', 'PETR4 deixou a desejar, vendo?']
C30_FATO = ['troca de presidente da Petrobras', 'Prates deixa a Petrobras', 'o Prates deixou a Petrobras, e o Ibovespa?',
            'a saída do Prates da Petrobras', 'o conselho da Petrobras elegeu o Prates?', 'quem foi indicado pra Petrobras?',
            'como o Ibovespa reagiu ao dividendo extraordinário da Petrobras em 2024?', 'a Petrobras pagou dividendo em 2022?']
# Grupo 2 (C1): o fato citado junto de um pedido sobre a ação acha o tema, mas os eventos da Petrobras não entram.
C30_FATO_COM_PEDIDO = ['PETR4 pros dividendos de 2024, compensa?']


@pytest.mark.parametrize('pergunta', C30_SO_ACAO)
def test_c30_pedido_sem_fato_nao_recebe_o_dossie_do_emissor(pergunta):
    r = _recusa(pergunta)
    assert not any(t.startswith('O que aconteceu antes: ') and 'desde 2016' in t for t in _titulos(r))
    assert F.tema_petroleo(normalizar(pergunta)) == ()


@pytest.mark.parametrize('pergunta', C30_FATO)
def test_c30_fato_da_petrobras_traz_os_eventos(pergunta):
    assert 'petrobras' in F.tema_petroleo(normalizar(pergunta))
    assert any(t.startswith('O que aconteceu antes: Petrobras') for t in _titulos(montar(pergunta, hoje=HOJE)))


@pytest.mark.parametrize('pergunta', C30_FATO_COM_PEDIDO)
def test_c30_fato_com_pedido_sobre_a_acao_fica_sem_os_eventos_da_petrobras(pergunta):
    assert 'petrobras' in F.tema_petroleo(normalizar(pergunta))
    assert not any(t.startswith('O que aconteceu antes: Petrobras') for t in _titulos(_recusa(pergunta)))


C30_CONSELHO = ['o conselho da Petrobras elegeu o Prates?', 'o que é o Conselho Monetário Nacional?',
                'Conselho da Petrobras elege Jean Paul Prates presidente']


@pytest.mark.parametrize('pergunta', C30_CONSELHO)
def test_c30_conselho_de_orgao_e_fato_e_nao_dica(pergunta):
    _sem_recusa(pergunta)


# ---------- C31: escolher, usar ou avaliar uma exchange pelo nome ----------

C31_PLATAFORMA = ['Binance ou Mercado Bitcoin?', 'Uso a Binance ou a Foxbit?', 'é seguro deixar meus bitcoins na Binance?',
                  'Abro conta na Bybit?', 'A Coinbase é regulamentada no Brasil? posso confiar?', 'Binance é segura?',
                  'a Binance é confiável?', 'Foxbit ou Bybit?', 'me indica uma corretora']
C31_SEM = ['Binance e o governo dos EUA', 'o que aconteceu com a Binance?', 'a Binance foi multada nos EUA?',
           'Uso a Binance, como declaro o imposto?', 'como declarar bitcoin comprado na Binance?', 'Binance ou FTX, qual quebrou?',
           'bitcoin é seguro?', 'o que é exchange?', 'qual a diferença entre exchange e carteira?']


@pytest.mark.parametrize('pergunta', C31_PLATAFORMA)
def test_c31_exchange_pelo_nome_e_indicar(pergunta):
    r = montar(pergunta, hoje=HOJE)
    assert 'plataforma' in r.pedido.proibidos and T.POR_PEDIDO['plataforma'] in r.abertura and r.violacoes == []
    assert not any('Binance e o fundador' in x for x in r.curta)  # o marco negativo de uma delas não vai para o topo


@pytest.mark.parametrize('pergunta', C31_SEM)
def test_c31_fato_sobre_exchange_sem_plataforma(pergunta):
    r = montar(pergunta, hoje=HOJE)
    assert 'plataforma' not in r.pedido.proibidos and r.violacoes == []


def test_c31_fato_da_binance_continua_no_topo():
    assert montar('o que aconteceu com a Binance?', hoje=HOJE).curta[0].startswith('Na linha do tempo da cripto: 21/11/2023')


def test_c31_guardar_na_exchange_ou_na_carteira_e_dica():
    _recusa('deixo meus btc na exchange ou numa carteira fria?', 'dica')


# ---------- C32: direção e escolha entre criptos ----------

C32_DIRECAO = ['bitcoin vai renovar máxima?', 'eth vai flipar?', 'ETH flipa o BTC esse ciclo?', 'Solana vai passar o ethereum?',
               '¿El bitcoin llega a 200 mil?', 'bitcoin renova a máxima?', 'btc faz ATH esse ano?', 'BTC pode fazer ATH?',
               'eth flips btc?', 'solana supera o eth?', 'o eth consegue passar o bitcoin?']
C32_RANKING = ['BTC ou ETH?', 'Solana ou XRP pra 2027?', 'USDT ou USDC?', 'ETH é melhor que BTC?', 'SOL ou ETH?', 'btc x eth']
C32_SEM = ['qual foi a máxima do bitcoin?', 'quando o bitcoin renovou a máxima?', 'o bitcoin bateu máxima em 2024?', 'o que é ATH?',
           'o que é flippening?', 'quando o ethereum flipou?', 'quando o imposto de cripto vai passar a valer?',
           'como passa o bitcoin pra carteira fria?', 'qual a diferença entre usdt e usdc?', 'a solana passou o ethereum em 2021?',
           'o que fez o bitcoin bater a máxima de 2021?']


@pytest.mark.parametrize('pergunta', C32_DIRECAO)
def test_c32_direcao_de_cripto_recusa(pergunta):
    _recusa(pergunta, 'direcao')


@pytest.mark.parametrize('pergunta', C32_RANKING)
def test_c32_escolha_entre_criptos_e_ranking(pergunta):
    _recusa(pergunta, 'ranking')


@pytest.mark.parametrize('pergunta', C32_SEM)
def test_c32_passado_e_conceito_de_cripto_sem_recusa(pergunta):
    _sem_recusa(pergunta)


# ---------- C33: "é a hora?", "perdi o bonde", "embarco" ----------

C33_RECUSA = ['Brent caiu 10% hoje, é a hora?', 'Perdi o bonde do petróleo?', 'petr4 ta voando, embarco?', 'btfd petrobras',
              'eh a hora?', 'Será que é a hora do petróleo?', 'Bitcoin caiu 20%, é a hora?', 'Ainda dá tempo no petróleo?',
              'perdi o trem do bitcoin?', 'vale embarcar na petrobras?', 'embarco no brent?']
C33_SEM = ['Qual é a hora da decisão do Copom?', 'A que horas sai o Copom?', 'Quanto petróleo o Brasil embarca por dia?',
           'Como funciona o embarque de petróleo?', 'o que é btc?', 'Perdi a reunião da OPEP, o que decidiram?',
           'E a hora da divulgação do Copom?']


@pytest.mark.parametrize('pergunta', C33_RECUSA)
def test_c33_pedido_de_momento_recusa(pergunta):
    _recusa(pergunta)


@pytest.mark.parametrize('pergunta', C33_SEM)
def test_c33_hora_e_embarque_de_fato_sem_recusa(pergunta):
    _sem_recusa(pergunta)


# ---------- C34: perfil de terceiro, objetivo de renda e promessa de garantia ----------

C34_RECUSA = ['Minha mãe tem 70 anos, Petrobras é bom pra ela?', 'quero viver de dividendos da Petrobras',
              'dividendo da Petrobras é renda garantida?', 'a Petrobras é estatal, então é garantido?',
              'Com 5 conto dá pra começar em PETR4?', 'meu pai tem 70 anos, petr4 serve?', 'Petrobras é bom pra minha mãe?',
              'Minha mãe é aposentada, Petrobras serve pra ela?', 'Petrobras é bom pra mim?', 'Com 500 reais dá pra começar em PETR4?',
              'Sou aposentado, Petrobras serve pra mim?']
C34_SEM = ['O que é margem de garantia?', 'a gasolina com 6 reais o litro mudou o IPCA?', 'a Petrobras tem 70 anos?',
           'quando a Petrobras paga dividendo?', 'com 2 contratos de WIN e 1.000 pontos, quanto dá?', 'o CDB é garantido pelo FGC?',
           'o Tesouro é garantido pelo governo?', 'o dividendo mínimo é garantido por lei?', 'o diesel com 6,50 reais pesa na inflação?',
           'o Brent alto é bom pra ela, a Petrobras?', 'a poupança é garantida?']


@pytest.mark.parametrize('pergunta', C34_RECUSA)
def test_c34_perfil_objetivo_e_garantia_recusa(pergunta):
    _recusa(pergunta)


@pytest.mark.parametrize('pergunta', C34_SEM)
def test_c34_fato_sem_recusa(pergunta):
    _sem_recusa(pergunta)


# ---------- C35: erro de digitação, gíria e inglês ----------

C35_RECUSA = ['minha esposa quer que eu venda minha petro, ela tem razão?', 'ptr4 vale apena?', 'o óleo vai pra lua?',
              'Is oil going to crash?', 'Oil to 150 by Christmas?', 'quer que eu compre dólar antes da eleição?', 'pretobras sobe?']
C35_SEM = ['o que é venda a descoberto?', 'pressão de venda no Ibovespa', 'as vendas de diesel da Petrobras', 'óleo de cozinha subiu?',
           'troca de óleo do carro', 'Oil went from 70 to 120 by June 2022', 'como a bolsa se comportou no crash de 2020?',
           'o crash de 2020 afetou a bolsa?']


@pytest.mark.parametrize('pergunta', C35_RECUSA)
def test_c35_giria_digitacao_e_ingles_recusa(pergunta):
    _recusa(pergunta)


@pytest.mark.parametrize('pergunta', C35_RECUSA[:5])
def test_c35_giria_digitacao_e_ingles_acham_o_petroleo(pergunta):
    assert 'petroleo' in analisar(pergunta).mercados


@pytest.mark.parametrize('pergunta', C35_SEM)
def test_c35_venda_oleo_e_crash_de_fato_sem_recusa(pergunta):
    _sem_recusa(pergunta)


@pytest.mark.parametrize('pergunta', ['óleo de cozinha subiu?', 'troca de óleo do carro'])
def test_c35_oleo_que_nao_e_petroleo(pergunta):
    assert 'petroleo' not in analisar(pergunta).mercados


# ---------- L17: o Bolsonaro com a Petrobras, em pergunta de eleição ----------

L17_CANDIDATO = ['com o Bolsonaro, a Petrobras e o dólar sobem?', 'se o Bolsonaro voltar, a Petrobras sobe?',
                 'Bolsonaro e Petrobras na campanha']
L17_GOVERNO = ['quando o Bolsonaro trocou o presidente da Petrobras?', 'o Jair Bolsonaro trocou o presidente da Petrobras?',
               'o governo Bolsonaro e a Petrobras']


@pytest.mark.parametrize('pergunta', L17_CANDIDATO)
def test_l17_bolsonaro_na_eleicao_e_o_candidato(pergunta):
    r = montar(pergunta, hoje=HOJE)
    assert r.pedido.candidatos == ['flavio'] and r.pedido.eleicao
    assert any(t.startswith('O que aconteceu antes: os turnos') for t in _titulos(r))


@pytest.mark.parametrize('pergunta', L17_GOVERNO)
def test_l17_bolsonaro_do_governo_nao_e_o_candidato(pergunta):
    p = analisar(pergunta)
    assert p.candidatos == [] and not p.eleicao


def test_l17_jair_bolsonaro_em_ano_de_eleicao_traz_os_turnos():
    r = montar('Jair Bolsonaro e o dólar em 2018', hoje=HOJE)
    assert r.pedido.candidatos == [] and 'eleicao' in r.pedido.temas
    assert any(t.startswith('O que aconteceu antes: os turnos') for t in _titulos(r))


# ---------- L18: "mais arriscado" de conceito não é ranking ----------

L18_SEM = ['por que o mini-índice é mais arriscado?', 'o que torna o mini-dólar mais arriscado?',
           'o mini-índice é mais arriscado que ações?', 'o real ficou mais sólido?', 'os bancos estão mais sólidos que em 2015?']
L18_RANKING = ['qual petroleira é mais sólida?', 'qual a petroleira mais sólida?', 'a Coinbase é a mais segura?',
               'qual é mais seguro: bitcoin ou dólar?']


@pytest.mark.parametrize('pergunta', L18_SEM)
def test_l18_conceito_de_risco_sem_ranking(pergunta):
    _sem_recusa(pergunta)


@pytest.mark.parametrize('pergunta', L18_RANKING)
def test_l18_escolha_do_mais_seguro_e_ranking(pergunta):
    assert 'ranking' in analisar(pergunta).proibidos


# ---------- L19: gasolina e combustível em sentido figurado ----------

L19_FIGURADO = ['o Copom colocou gasolina no dólar?', 'a fala do Lula botou mais gasolina no dólar?', 'a eleição pôs gasolina na bolsa?',
                'o combustível para a Selic subir foi a inflação?', 'o Lula jogou gasolina na fogueira, e o dólar?']
L19_LITERAL = ['compensa trocar etanol por gasolina?', 'o preço da gasolina no mercado internacional subiu?']


@pytest.mark.parametrize('pergunta', L19_FIGURADO)
def test_l19_figurado_nao_e_petroleo(pergunta):
    assert 'petroleo' not in analisar(pergunta).mercados


@pytest.mark.parametrize('pergunta', L19_LITERAL)
def test_l19_gasolina_de_verdade_continua_petroleo(pergunta):
    assert 'petroleo' in analisar(pergunta).mercados


# ---------- L20: "a gente" e "quem" lucrar é a chance da pessoa ----------

L20_CHANCE = ['a gente pode lucrar com a eleição?', 'quem pode lucrar com mini-índice?', 'vale lucrar com day trade?']


@pytest.mark.parametrize('pergunta', L20_CHANCE)
def test_l20_lucro_impessoal_e_chance_dinheiro(pergunta):
    r = montar(pergunta, hoje=HOJE)
    assert r.pedido.proibidos == ['chance_dinheiro'] and T.RECUSA not in r.abertura
    assert T.POR_PEDIDO['chance_dinheiro'] in r.abertura


# As perguntas que os testes acima usam fora das listas.
AVULSAS = ['como tá o dólar hoje?', 'PETR4 e o euro', 'o petróleo mexe no dólar?', 'barril a 115, a petrobras vai lucrar muito?',
           'vou lucrar com petrobras?', 'como eu coloco dinheiro na corretora?', 'deixo meus btc na exchange ou numa carteira fria?',
           'Tenho cinco mil reais pra investir na eleição, cripto ou bolsa?', 'Jair Bolsonaro e o dólar em 2018']
# Todas as perguntas deste arquivo, para os EXTRAS da paridade (agente/exportar.py) e para a checagem de violação.
TODAS = list(dict.fromkeys(
    [q for nome, v in list(globals().items()) if nome[:1] in 'CL' and nome[1:3].isdigit() and isinstance(v, list)
     for q in (x[0] if isinstance(x, tuple) else x for x in v)] + AVULSAS))


def test_nenhuma_pergunta_da_rodada_tem_violacao():
    for q in TODAS:
        assert montar(q, hoje=HOJE).violacoes == [], q


# =====================================================================================================================
# Grupo 2 da rodada 2: os achados que ficaram pela metade (C1 a C22) e os de gravidade baixa (L1 a L16). As listas têm o
# prefixo G2_ e entram nos EXTRAS de agente/exportar.py.
# =====================================================================================================================

def _eventos_petrobras(r) -> bool:
    """A resposta traz algum evento de tema Petrobras (a história de um emissor só)."""
    titulos = [e['titulo'] for e in F._petroleo()['eventos'] if e['tema'] == 'petrobras']
    return any(any(t in ln.texto for t in titulos) for b in r.blocos for ln in b.linhas)


def _tem_eventos(r) -> bool:
    return any(t.startswith('O que aconteceu antes: ') and 'desde 2016' in t for t in _titulos(r))


# ---------- C1: pedido sobre a ação não recebe a história do emissor, nem com o fato citado ----------

G2_C1_PEDIDO = ['compro petrobras antes do reajuste do diesel?',
                'vale a pena PETR4 com o reajuste da gasolina?', 'vale a pena PETR4 com o petróleo subindo?',
                'quais ações de petróleo comprar?']
G2_C1_DIVIDENDO = ['petr4 paga dividendo extraordinario esse ano?', 'vai ter dividendo extraordinário da petrobras?',
                   'tem dividendo da petrobras esse ano?']
G2_C1_FATO = ['quem foram os presidentes da petrobras?', 'o que aconteceu com a Petrobras em 2021?',
              'quando a petrobras aumentou o preço?', 'linha do tempo da petrobras',
              'quais foram os principais eventos da petrobras desde 2016?',
              'o conselho da Petrobras aprovou dividendo extraordinário em 2024?', 'o dividendo extraordinário da petrobras',
              'a petrobras pagou dividendo esse ano?', 'a Petrobras e o reajuste da gasolina',
              'como a bolsa reage ao reajuste da Petrobras?']
G2_C1_JUIZO = ['petr4 é bom?', 'PETR4 paga dividendo alto?', 'vale apena petr 4?']
G2_C1_SEM = ['a petrobras é uma boa empresa pra trabalhar?', 'o dólar alto é bom?', 'o que é um bom investimento?']


@pytest.mark.parametrize('pergunta', G2_C1_PEDIDO)
def test_g2_c1_pedido_sobre_a_acao_sem_eventos_da_petrobras(pergunta):
    r = _recusa(pergunta)
    assert not _eventos_petrobras(r)
    assert _tem_eventos(r)  # ficam os do petróleo: a pergunta cita o petróleo, a gasolina ou o diesel


def test_g2_c1_pedido_so_com_o_fato_da_acao_fica_sem_eventos():
    r = _recusa('compro PETR4 antes do dividendo extraordinário?')
    assert not _tem_eventos(r)


@pytest.mark.parametrize('pergunta', G2_C1_DIVIDENDO)
def test_g2_c1_dividendo_que_ainda_vem_recusa(pergunta):
    r = _recusa(pergunta, 'direcao')
    assert not _eventos_petrobras(r)


@pytest.mark.parametrize('pergunta', G2_C1_FATO)
def test_g2_c1_fato_da_petrobras_traz_os_eventos_dela(pergunta):
    r = _sem_recusa(pergunta)
    assert _eventos_petrobras(r)


@pytest.mark.parametrize('pergunta', G2_C1_JUIZO)
def test_g2_c1_juizo_sobre_o_papel_recusa(pergunta):
    r = _recusa(pergunta)
    assert 'petroleo' in r.pedido.mercados


@pytest.mark.parametrize('pergunta', G2_C1_SEM)
def test_g2_c1_bom_fora_do_papel_sem_recusa(pergunta):
    _sem_recusa(pergunta)


# ---------- C2: escolher entre emissores, ou entre um emissor e uma classe ----------

G2_C2_RECUSA = ['entre petrobras e prio qual escolho?', 'PETR4 é pior que PRIO3?', 'brava ou petrobras?', 'petrobras ou 3R?',
                'petrobras ou dólar?', 'PETR4 ou tesouro?', 'petrobras ou bitcoin?', 'petr4 ou cdb?',
                'qual é melhor entre petrobras e prio?', 'a petrobras é pior que a prio?', 'enauta ou petrobras?',
                'tesouro ou PETR4?', 'PETR4 x dólar', 'petrobras ou ibovespa?', 'bitcoin é mais seguro que ethereum?',
                'qual a opção mais segura?', 'PETR4 ficou mais arriscada?', 'renda fixa é mais segura que ações?',
                'PETR3 ou PETR4: qual a diferença e qual compro?']
G2_C2_SEM_EMISSOR = ['qual ação de petróleo é melhor?', 'melhor acao de petroleo', 'PETR4 ou PRIO3 com o brent a 115?',
                     'petróleo ou dólar, qual é melhor?']
G2_C2_SEM = ['PETR3 ou PETR4: qual a diferença?', 'o que muda entre PETR3 ou PETR4?',
             'o bitcoin ficou mais seguro depois da regulação?', 'o que é boa pagadora de dividendos?',
             'qual a diferença entre o tesouro e o cdb?']


@pytest.mark.parametrize('pergunta', G2_C2_RECUSA)
def test_g2_c2_escolha_entre_ativos_recusa(pergunta):
    r = _recusa(pergunta)
    assert {'ranking', 'comparar', 'dica'} & set(r.pedido.proibidos)


@pytest.mark.parametrize('pergunta', G2_C2_SEM_EMISSOR)
def test_g2_c2_ranking_de_petroleo_sem_eventos_da_petrobras(pergunta):
    r = _recusa(pergunta)
    assert _tem_eventos(r) and not _eventos_petrobras(r)


@pytest.mark.parametrize('pergunta', G2_C2_SEM)
def test_g2_c2_diferenca_e_conceito_sem_recusa(pergunta):
    _sem_recusa(pergunta)


# ---------- C3: manter, sair, oportunidade e momento; e o fato da OPEP e do preço sem recusa ----------

G2_C3_RECUSA = ['vale manter petrobras?', 'continuo com PETR4?', 'fico com petr4?', 'saio da petrobras?',
                'tô comprado em petrobras, seguro?', 'é a hora da petrobras?', 'chegou a hora da petrobras?',
                'boa hora pra petr4?', 'momento certo pra petr4?', 'petr4 caiu, oportunidade?', 'oportunidade na petrobras?',
                'dobro a mao em petr4?', 'faço PM em petr4?', 'shorteio petr4?', 'boto mais em petr4?', 'bolsa bom momento?',
                'é o melhor momento da petrobras?', 'a crise é oportunidade?']
G2_C3_SEM = ['aumento do petróleo e a inflação', 'o aumento da gasolina pela petrobras em 2022 foi de quanto?',
             'quando foi o último aumento da petrobras?',
             'a OPEP decidiu reduzir a produção de petróleo em 2020, o que aconteceu?',
             'quando a opep resolveu aumentar a produção de petróleo?',
             'como a bolsa reagiu quando a opep diminuiu a produção de petróleo?', 'qual foi o pior momento do petróleo?',
             'qual foi o melhor momento do brent desde 2016?', 'o brasil tem posição na opep?', 'o que é um investimento seguro?',
             'o que é long ou short?', 'o que significa ficar short?',
             'crise e oportunidade: o que a história do petróleo mostra?', 'o que é custo de oportunidade?',
             'qual é a hora da abertura da bolsa?']


@pytest.mark.parametrize('pergunta', G2_C3_RECUSA)
def test_g2_c3_o_que_fazer_com_o_papel_recusa(pergunta):
    _recusa(pergunta)


@pytest.mark.parametrize('pergunta', G2_C3_SEM)
def test_g2_c3_fato_e_conceito_sem_recusa(pergunta):
    _sem_recusa(pergunta)


def test_g2_c3_ultimo_aumento_traz_os_eventos_da_petrobras():
    assert _eventos_petrobras(montar('quando foi o último aumento da petrobras?', hoje=HOJE))


# ---------- C4: os sinônimos de valuation recusam; o "caro" da bomba que pede explicação não ----------

G2_C4_RECUSA = ['qual o valor justo da petrobras?', 'PETR4 ta carissima?', 'petr4 tá com desconto?', 'a petr4 tá em promoção?',
                'petr4 tá num preço bom?', 'petrobras tá no preço?', 'petr4 ta precificada?', 'PETR4 tá muito alta?',
                'a petrobras é sólida?', 'a petrobras é segura?', 'petrobras é arriscada?', 'a gasolina tá cara?',
                'a gasolina vai ficar mais cara?', 'por que a gasolina tá cara e a petr4 tá barata?',
                'por que a gasolina tá cara? a petrobras vai subir?', 'o que é valuation? a petr4 tá barata?',
                'o que é upside? o dólar sobe?', 'o que é preço justo da petr4?']
G2_C4_BOMBA = ['por que a gasolina está cara?', 'o que deixa a gasolina cara no Brasil?',
               'quanto do preço da gasolina cara é imposto?', 'a gasolina mais cara do mundo é a do brasil?',
               'a gasolina tá cara por causa do dólar?']
G2_C4_SEM = ['o que é valuation?', 'o que é upside?', 'o que é preço justo de uma ação?', 'o que significa ação descontada?',
             'o que pesa no preço da gasolina?', 'a Selic está muito alta?', 'os juros estão muito altos?']


@pytest.mark.parametrize('pergunta', G2_C4_RECUSA)
def test_g2_c4_valuation_recusa(pergunta):
    _recusa(pergunta)


@pytest.mark.parametrize('pergunta', G2_C4_BOMBA)
def test_g2_c4_bomba_cara_explicada_sem_recusa(pergunta):
    r = _sem_recusa(pergunta)
    assert any(t.startswith('Do barril à bomba') for t in _titulos(r))


@pytest.mark.parametrize('pergunta', G2_C4_SEM)
def test_g2_c4_conceito_sem_recusa(pergunta):
    _sem_recusa(pergunta)


# ---------- C5, C12, C15: o nível que ainda vem, em qualquer forma; o passado e a regra sem recusa ----------

G2_C5_RECUSA = ['o brent volta a 100?', 'o petroleo volta pros 70?', 'o barril segue subindo?', 'o petróleo vai seguir caindo?',
                'o brent continua caindo?', 'o brent vai passar dos 150?', 'o brent vai romper 120?', 'petr4 chega nos 50?',
                'brent a 150 ate dezembro?', 'o barril vai estourar?', 'a petrobras vai distribuir dividendo?',
                'a petrobras paga dividendo esse ano?', 'opep corta em dezembro?', 'o bitcoin chega aos 200 mil?',
                'o dólar volta a 5?', 'a opep+ corta a producao em dezembro?', 'o copom corta em dezembro?',
                'o lucro da petrobras vai ser grande?', 'petr4 vai a R$ 50?', 'PETR4 sai de 30 pra 40?']
G2_C5_SEM = ['o investidor deve pagar IR sobre o dividendo da petrobras?', 'como a petrobras pode lucrar com o pré-sal?',
             'o brent passou de 100 em 2022?', 'o brent chegou a 139 em 2022?', 'o brent seguiu caindo em 2020?',
             'o brent continuou caindo em 2020?', 'o brent voltou a 100 em 2022?', 'o lucro da petrobras vai ser divulgado quando?',
             'como a petrobras deve distribuir dividendo por lei?']
G2_C12_RECUSA = ['o brent chega nos 200?', 'o petroleo vai pros 150?', 'o barril vai para os 150 dolares?', 'o brent volta pros 60?',
                 'o barril pode chegar em 200?', 'o brent atinge 150?', 'o petroleo vai ultrapassar 150?',
                 'brent a 150 até o natal?', 'o brent vai pra casa dos 150?', 'o dólar supera 6 reais?', 'o ibovespa rompe 200 mil?',
                 'o brent bate na casa dos 150?', 'o dolar vai ao 7?', 'o bitcoin alcança 200k?', 'brent a US$ 150 até dezembro?',
                 'o brent passa de 5% amanha?']
G2_C12_SEM = ['o Brent já passou de 150 alguma vez?', 'o brent atingiu 130 em 2022?', 'o brent ultrapassou 130 em 2022?',
              'o brent subiu de 80 a 130 em 2022?', 'qual a variação do brent de 2016 a 2020?',
              'quanto custa a gasolina com o barril a 115?', 'a remessa de dólar chega em 2 dias?',
              'o mini-índice vai de 5 em 5 pontos?', 'o brent a 100 dólares de 2022 até hoje, quanto subiu?',
              'quantas vezes o brent passou de 5% num dia?']
G2_C15_RECUSA = ['o btc chega nos 100 mil?', 'ibovespa vai aos 200 mil pontos?', 'dólar a 6 até o fim do ano?', 'o dolar vai a R$ 7?',
                 'btc rumo aos 100k?', 'dolar chega nos 6?', 'o bitcoin vai aos 100 mil?', 'o btc vai chegar nos 100 mil?',
                 'petroleo chega aos 100?', 'o petroleo bate nos 100 dolares?', 'o dolar chega a R$ 7?', 'o dolar bate R$ 7?',
                 'o euro vai a R$ 7?', 'o ouro vai a 3000 dolares?', 'a nvidia vai a 200 dolares?', 'o bitcoin vai a 100 mil dólares?',
                 'dolar a R$ 7 no fim do ano?']
G2_C15_SEM_DIRECAO = ['se eu passar de R$ 35 mil por mês em bitcoin pago imposto?', 'o bitcoin chega em 2027 com a regra nova?',
                      'quando o bitcoin chegou a 100 mil o que aconteceu?', 'vendas que chegam a 35 mil pagam imposto?']


@pytest.mark.parametrize('pergunta', G2_C5_RECUSA + G2_C12_RECUSA + G2_C15_RECUSA)
def test_g2_nivel_que_ainda_vem_recusa(pergunta):
    _recusa(pergunta, 'direcao')


@pytest.mark.parametrize('pergunta', G2_C5_SEM + G2_C12_SEM)
def test_g2_nivel_no_passado_e_regra_sem_recusa(pergunta):
    _sem_recusa(pergunta)


@pytest.mark.parametrize('pergunta', G2_C15_SEM_DIRECAO)
def test_g2_c15_regra_e_passado_sem_direcao(pergunta):
    assert 'direcao' not in analisar(pergunta).proibidos


@pytest.mark.parametrize('pergunta', ['o dolar vai a R$ 7?', 'btc rumo aos 100k?', 'petr4 vai a R$ 50?', 'o ouro vai a 3000 dolares?',
                                      'o bitcoin vai a 100 mil dólares?'])
def test_g2_c15_alvo_nao_e_o_dinheiro_da_pessoa(pergunta):
    r = montar(pergunta, hoje=HOJE)
    assert 'capital' not in r.pedido.proibidos and r.pedido.valor_moeda is None
    assert T.POR_PEDIDO['capital'] not in r.abertura


def test_g2_c15_o_dinheiro_dela_continua_com_alvo_na_pergunta():
    assert 'capital' in analisar('tenho R$ 5 mil, o dolar vai a 7?').proibidos
    assert analisar('tenho 10 mil dolares, o dolar vai a 7?').valor_moeda == 10000


# ---------- C6: o reajuste que ainda vem, no presente, com "sai", "vem" e "tem"; e a defasagem no topo ----------

G2_C6_RECUSA = ['a petrobras reajusta semana que vem?', 'a petrobras reajusta na próxima semana?',
                'petrobras reajusta a gasolina essa semana?', 'sai reajuste da gasolina essa semana?', 'vem aumento de gasolina por aí?',
                'tem reajuste da gasolina essa semana?', 'Sai reajuste da gasolina?', 'será que sai reajuste?',
                'o brent subiu. sai reajuste?', 'vem corte da opep?', 'sai corte do copom?', 'o copom corta essa semana?',
                'a opep mantém a produção esse mês?', 'vai sair reajuste?']
G2_C6_SEM = ['o que acontece com o brent quando sai reajuste?', 'de onde vem o aumento da gasolina?',
             'a gasolina tem aumento de imposto em 2026?', 'o diesel tem corte de imposto?', 'teve reajuste essa semana?',
             'a petrobras reajustou semana passada?', 'qual foi o último reajuste?', 'como funciona o reajuste da petrobras?',
             'o copom mantém a selic, como o dólar reagiu essa semana?', 'o que vem depois do reajuste da gasolina?']
G2_C6_DEFASAGEM = ['qual a defasagem da gasolina hoje?', 'a gasolina está defasada?']


@pytest.mark.parametrize('pergunta', G2_C6_RECUSA)
def test_g2_c6_decisao_que_ainda_vem_recusa(pergunta):
    _recusa(pergunta, 'direcao')


@pytest.mark.parametrize('pergunta', G2_C6_SEM)
def test_g2_c6_fato_do_reajuste_sem_recusa(pergunta):
    _sem_recusa(pergunta)


@pytest.mark.parametrize('pergunta', G2_C6_DEFASAGEM)
def test_g2_c6_defasagem_diz_no_topo_que_nao_calcula(pergunta):
    r = _sem_recusa(pergunta)
    assert T.SEM_DEFASAGEM in r.abertura and T.SEM_DEFASAGEM in r.texto_curto


def test_g2_c6_paridade_sem_petroleo_nao_recebe_a_linha():
    assert T.SEM_DEFASAGEM not in montar('o que é a paridade de importação?', hoje=HOJE).abertura


# ---------- C7 e L5: o presidente da PETR4, da PRIO e da companhia não é a eleição ----------

G2_C7_FORA = ['troca de presidente na petr4', 'quando trocaram o presidente da PETR4 a ação caiu?',
              'o governo trocou o presidente da companhia, e a petr4?', 'quanto a PETR4 caiu quando trocaram o presidente em 2021?',
              'PETR4 subiu ou caiu na troca de presidente de 2021?', 'quando o Prates foi eleito presidente da Petrobras?',
              'a petrobras pode perder o presidente?', 'o presidente da prio3 saiu, e a ação?',
              'quando o Bolsonaro trocou o presidente da PETR4?', 'o ex-presidente Bolsonaro trocou o comando da Petrobras',
              'o presidente da PETR4 caiu', 'presidente da Prio', 'o Prates foi eleito pelo conselho da Petrobras?',
              'o conselho da Petrobras aprovou dividendos em 2024?']
G2_C7_ELEICAO = ['o bolsonaro e a petr4', 'o que acontece com a PETR4 se o presidente mudar no domingo?',
                 'se o Lula ganhar, troca o presidente da PETR4?', 'o próximo presidente vai trocar o comando da PETR4?',
                 'presidente da PETR4 e o 2º turno', 'como a Petrobras reage às pesquisas pra presidente?',
                 'se o eleito trocar o presidente da petrobras, a ação cai?', 'o eleito presidente da república e a petr4',
                 'a Petrobras cai se ele perder pro outro presidente?', 'o BC vai mudar com o novo presidente?',
                 'a empresa e o novo presidente', 'a Petrobras e o novo presidente da República',
                 'se o Flávio for eleito, a Petrobras cai?']


@pytest.mark.parametrize('pergunta', G2_C7_FORA)
def test_g2_c7_cargo_da_empresa_nao_e_eleicao(pergunta):
    r = montar(pergunta, hoje=HOJE)
    assert not r.pedido.eleicao and r.pedido.candidatos == [], (r.pedido.temas, r.pedido.candidatos)
    assert r.violacoes == []


@pytest.mark.parametrize('pergunta', G2_C7_ELEICAO)
def test_g2_c7_eleicao_continua_eleicao(pergunta):
    assert analisar(pergunta).eleicao


# ---------- C8, C9, C10: a pergunta do fato pelo nome do presidente ou pela nomeação traz os eventos ----------

G2_C8_FATO = ['quando o Prates saiu da Petrobras o que aconteceu?', 'como o mercado reagiu quando a Petrobras elegeu o Prates?',
              'quando o Castello Branco saiu da Petrobras?', 'o que aconteceu quando demitiram o presidente da Petrobras?',
              'o que aconteceu quando o Castello Branco foi anunciado na Petrobras?',
              'o que aconteceu quando a Petrobras anunciou o Castello Branco?', 'quando o Parente saiu da Petrobras, como reagiu?',
              'o mercado reagiu à indicação da Magda Chambriard na petrobras?', 'como reagiu a nomeação da Magda na Petrobras?',
              'como o mercado reagiu quando o Prates saiu da Petrobras?', 'a Magda Chambriard assumiu a Petrobras quando?',
              'o José Mauro saiu da Petrobras quando?', 'o Pedro Parente foi pra Petrobras quando?']
G2_C8_PEDIDO = ['devo sair da PETR4?', 'é hora de sair da Petrobras?', 'vale trocar PETR4 por PRIO3?', 'eu caio fora da PETR4?',
                'a Petrobras anunciou recompra, compro?', 'a Petrobras anunciou lucro, devo comprar PETR4?',
                'qual a sua indicação: PETR4 ou PRIO3?', 'meu parente tem PETR4, devo vender?', 'a PETR4 saiu da mínima, compro?',
                'o Caio da corretora disse pra comprar petr4', 'meu parente trabalha na Petrobras, compro PETR4?',
                'a Petrobras anunciou lucro recorde, PETR4 vai subir?', 'troca PETR4 por PRIO3?', 'qual a indicação pra PETR4?',
                'saio da PETR4?', 'posso trocar PETR3 por PETR4?', 'PETR4 tá caindo, saio?']
G2_C8_SEM_EVENTO = ['a PETR4 já saiu do fundo do poço?', 'quando sai o dividendo da Petrobras?', 'qual a indicação do governo para a Petrobras?']


@pytest.mark.parametrize('pergunta', G2_C8_FATO)
def test_g2_c8_fato_pelo_nome_traz_os_eventos_da_petrobras(pergunta):
    r = _sem_recusa(pergunta)
    assert any(t.startswith('O que aconteceu antes: Petrobras') for t in _titulos(r))


def test_g2_c8_fato_com_o_candidato_tambem_traz_os_eventos():
    r = montar('quando o Lula demitiu o Prates o que aconteceu com a Petrobras?', hoje=HOJE)
    assert _eventos_petrobras(r) and r.violacoes == []


@pytest.mark.parametrize('pergunta', G2_C8_PEDIDO)
def test_g2_c8_pedido_recusa_sem_a_historia_do_emissor(pergunta):
    r = _recusa(pergunta)
    assert not _eventos_petrobras(r)


@pytest.mark.parametrize('pergunta', G2_C8_SEM_EVENTO)
def test_g2_c8_saida_e_indicacao_soltas_nao_trazem_os_eventos(pergunta):
    assert not _eventos_petrobras(montar(pergunta, hoje=HOJE))


# ---------- C11: o preço do barril não é o dinheiro da pessoa; a conversão pedida faz a conta ----------

G2_C11_SEM_VALOR = ['tenho uma dúvida: o petróleo passou de 100 dólares?', 'meus amigos dizem que o barril passou de US$ 130',
                    'recebi uma notícia de que o brent bateu 138 dólares', 'tenho uma dúvida, 100 dólares no barril é muito?']
G2_C11_CONTA = [('o petróleo passou de 100 dólares? tenho 2 mil dólares guardados', 2000, 'dolar'),
                ('quanto valem 100 dólares em reais? e o petróleo?', 100, 'dolar'),
                ('converte 200 dólares pra real, e o brent?', 200, 'dolar'),
                ('com 500 dólares, quanto dá em reais? e o petróleo?', 500, 'dolar'),
                ('vou viajar com 3 mil dólares, o petróleo mexe com o dólar?', 3000, 'dolar'),
                ('tenho ações da Petrobras e 2 mil dólares', 2000, 'dolar'),
                ('quanto valem 10 mil euros em reais? e o petróleo?', 10000, 'euro')]


@pytest.mark.parametrize('pergunta', G2_C11_SEM_VALOR)
def test_g2_c11_preco_do_barril_nao_e_o_dinheiro_dela(pergunta):
    r = montar(pergunta, hoje=HOJE)
    assert r.pedido.valor_moeda is None and 'dolar' not in r.pedido.mercados
    assert r.curta[0].startswith('O petróleo Brent está em US$') and 'seus ' not in r.texto and r.violacoes == []


@pytest.mark.parametrize('pergunta, valor, moeda', G2_C11_CONTA)
def test_g2_c11_dinheiro_dela_e_conversao_fazem_a_conta(pergunta, valor, moeda):
    r = montar(pergunta, hoje=HOJE)
    assert (r.pedido.valor_moeda, r.pedido.moeda) == (valor, moeda) and moeda in r.pedido.mercados
    assert r.violacoes == []


# ---------- C13: o dinheiro dela em reais continua capital; o preço dito com verbo não ----------

G2_C13_CAPITAL = ['recebi dividendos de R$ 50 mil, onde ponho?', 'recebi dividendo de R$ 30 mil da Petrobras, reinvisto?',
                  'meus dividendos de R$ 8 mil, reinvisto em PETR4?', 'recebi R$ 2 milhões em dividendos da Petrobras, reinvisto?',
                  'ganhei R$ 1 milhão em juros, onde ponho?', 'tenho R$ 2 bi, onde ponho?', 'dividendos de R$ 50 mil, onde ponho?',
                  'R$ 2 bi, onde invisto?', 'onde coloco R$ 2 bi?']
G2_C13_PRECO = ['a Petrobras pagou dividendo de R$ 6,73 por ação?', 'os R$ 20 bilhões de dividendos da Petrobras',
                'o dólar chegou a R$ 6,30 em 2024?', 'a gasolina custa R$ 6,53?', 'a Petrobras pagou R$ 20 bilhões em dividendos em 2024?',
                'como o Ibovespa reagiu ao dividendo extraordinário da Petrobras em 2024?',
                'o que a Petrobras fez com os R$ 20 bi de dividendos? ela reinvestiu?', 'a gasolina está R$ 6,53?',
                'a gasolina ta R$ 7 aqui', 'a gasolina subiu pra R$ 7?', 'a gasolina passou de R$ 7?', 'o diesel subiu R$ 0,50?',
                'a ação da Petrobras caiu pra R$ 30?', 'o barril em reais passou de R$ 600']
G2_C13_ONDE = ['onde ponho os dividendos?', 'reinvisto os dividendos da Petrobras?']


@pytest.mark.parametrize('pergunta', G2_C13_CAPITAL)
def test_g2_c13_dinheiro_dela_e_capital(pergunta):
    _recusa(pergunta, 'capital')


@pytest.mark.parametrize('pergunta', G2_C13_PRECO)
def test_g2_c13_preco_em_reais_nao_e_capital(pergunta):
    r = montar(pergunta, hoje=HOJE)
    assert 'capital' not in r.pedido.proibidos and r.violacoes == []


@pytest.mark.parametrize('pergunta', G2_C13_ONDE)
def test_g2_c13_onde_por_sem_valor_e_dica(pergunta):
    _recusa(pergunta, 'dica')


# ---------- C14: gíria, comparação de cripto pelo nome e o "como" do tirar ----------

G2_C14_RECUSA = ['o bitcoin vai voar com o trump?', 'o halving vai fazer o btc estourar?', 'btc moon?', 'bitcoin vai pro espaco?',
                 'o bitcoin vai longe com o trump?', 'doge ou shiba qual vai mais longe?', 'btc ou eth?', 'eth ou sol, qual?',
                 'btc ou dolar?', 'eth ou renda fixa?', 'o dolar estoura o teto de 6 reais?',
                 'tiro meu btc da exchange e boto na carteira fria?', 'tiro meu dinheiro da corretora?',
                 'boto meu dinheiro na corretora?']
G2_C14_SEM = ['como tiro meu bitcoin da exchange?', 'como tiro o informe de rendimentos da corretora?',
              'se eu estourar o limite do cartao, quanto pago de juros?', 'copom corta ou mantem, qual foi a decisao?',
              '1o ou 2o turno, qual teve mais reacao?', 'dolar ou euro, qual a cotacao hoje?',
              'lula ou flavio, qual o plano de cada um?']


@pytest.mark.parametrize('pergunta', G2_C14_RECUSA)
def test_g2_c14_giria_e_escolha_de_cripto_recusam(pergunta):
    r = _recusa(pergunta)
    assert r.abertura.index(T.RECUSA) == 0


@pytest.mark.parametrize('pergunta', G2_C14_SEM)
def test_g2_c14_explicacao_e_fato_sem_recusa(pergunta):
    _sem_recusa(pergunta)


# ---------- C16 e C19: cripto no plural e pelo nome contra outra classe; a corretora avaliada pelo nome ----------

G2_C16_COMPARAR = ['bitcoins ou tesouro?', 'criptomoedas ou tesouro?', 'criptos ou poupanca?', 'btc ou cdb?', 'ethereum ou tesouro?']
G2_C16_PLATAFORMA = ['compro na binance ou na coinbase?', 'binance ou mercado bitcoin?', 'uso a binance ou a foxbit?',
                     'abro conta na binance?', 'binanse é segura?']
G2_C19_PLATAFORMA = ['é seguro deixar meu bitcoin na binance?', 'a binance tem segurança?', 'posso confiar na foxbit?',
                     'a novadax é boa?', 'é confiável a coinbase?', 'a binance é furada?', 'binance presta?',
                     'a binance é de confiança?', 'confio na kraken?', 'é segura a binance?', 'a binance é ruim?',
                     'binance vale a pena?', 'meu dinheiro ta seguro na binance?', 'essa exchange é boa?',
                     'posso confiar nessa exchange?']
G2_C19_FATO = ['o que aconteceu com a Binance em 2023?', 'a binance confirmou o acordo com os EUA?', 'a binance tem boa liquidez?',
               'a binance e boa parte das exchanges saíram do Brasil?', 'qual foi a multa da binance?',
               'quanto a binance pagou nos EUA?', 'a binance segurou os saques da FTX?']
G2_C16_PIX = 'o pix com corretora vai parar dia 6? tiro meu dinheiro antes?'
G2_C16_SEM_CRIPTO = ['o banco central regula a corretora de ações?', 'posso mandar pix pra corretora?', 'meu banco tem corretora?']


@pytest.mark.parametrize('pergunta', G2_C16_COMPARAR)
def test_g2_c16_cripto_contra_classe_e_comparar(pergunta):
    r = _recusa(pergunta, 'comparar')
    assert T.POR_PEDIDO['comparar'] in r.abertura


@pytest.mark.parametrize('pergunta', G2_C16_PLATAFORMA + G2_C19_PLATAFORMA)
def test_g2_c16_c19_corretora_pelo_nome_e_plataforma(pergunta):
    r = montar(pergunta, hoje=HOJE)
    assert 'plataforma' in r.pedido.proibidos and T.POR_PEDIDO['plataforma'] in r.abertura and r.violacoes == []


@pytest.mark.parametrize('pergunta', G2_C19_FATO)
def test_g2_c19_fato_da_corretora_nao_e_plataforma(pergunta):
    r = montar(pergunta, hoje=HOJE)
    assert 'plataforma' not in r.pedido.proibidos and r.violacoes == []


def test_g2_c16_pix_das_corretoras_e_cripto():
    r = montar(G2_C16_PIX, hoje=HOJE)
    assert 'cripto' in r.pedido.mercados and '06/11/2026' in r.texto_curto and T.SEM_REPERTORIO not in r.abertura
    assert T.RECUSA in r.abertura and r.violacoes == []


@pytest.mark.parametrize('pergunta', G2_C16_SEM_CRIPTO)
def test_g2_c16_corretora_de_acoes_e_pix_nao_sao_cripto(pergunta):
    assert 'cripto' not in analisar(pergunta).mercados


# ---------- C17 e C22: o imposto do ETF nas 3 linhas; a bolsa citada como ativo; a bolsa como lugar ----------

G2_C17_ETF = ['ETF de bitcoin na B3 paga imposto?', 'HASH11 paga imposto?', 'etf de cripto tem isencao de 20 mil?',
              'quanto de imposto pago no ETF de bitcoin?', 'ETF de bitcoin tem isenção?', 'futuro de bitcoin paga imposto?']
G2_C17_IBOV = ['bitcoin e bolsa no ano', 'bitcoin ou bolsa?', 'bitcoin ou indice?', 'cripto ou bolsa de valores?', 'bitcoin e stocks',
               'investir na bolsa ou no bitcoin?', 'a bolsa e o bitcoin caem juntos?', 'a bolsa cai quando o bitcoin cai?',
               'investir em bitcoin ou no índice?', 'o mini indice e o bitcoin', 'bitcoin ou bolsa, qual compro?',
               'bitcoin or stocks?', 'bolsa ou bitcoin, qual compro?', 'WIN amanhã ou bitcoin?', 'WIN ou bitcoin na B3?',
               'mini índice ou bitcoin?']
G2_C17_LUGAR = ['ETF de bitcoin na bolsa paga imposto?', 'comprar bitcoin pela bolsa', 'quero bitcoin na bolsa, como faço?',
                'o que é fundo de índice de cripto?', 'fundo de indice de bitcoin vale a pena?', 'compro bitcoin pela bolsa ou direto?',
                'corretora ou bolsa, onde compro bitcoin?', 'bolsa ou exchange para comprar bitcoin?',
                'ETF de bitcoin na bolsa ou bitcoin direto?', 'bitcoin na bolsa ou na corretora?',
                'bitcoin pela bolsa ou pela exchange?', 'bolsa ou corretora de cripto, onde é mais seguro?',
                'ETF de bitcoin na B3, vale a pena?']
G2_C22_DOLAR_UNIDADE = ['tenho 10 mil dólares em bitcoin, vendo?', 'tenho US$ 10 mil em ethereum, vendo agora?',
                        'I have 10k dollars in bitcoin, should I sell?']
G2_C22_DOLAR_MERCADO = ['usdt ou dolar, qual o melhor?', 'o dólar sobe quando o bitcoin cai?', 'WDO ou bitcoin?']


@pytest.mark.parametrize('pergunta', G2_C17_ETF)
def test_g2_c17_imposto_do_etf_comeca_pela_ressalva(pergunta):
    r = montar(pergunta, hoje=HOJE)
    assert r.curta[0].startswith('A isenção de R$ 35 mil é da venda da própria cripto')
    assert 'não vale para cota de fundo de índice' in r.texto_curto and 'não é valor mobiliário' in r.texto_curto
    assert not any(t.startswith('O Ibovespa até aqui') for t in _titulos(r)) and r.violacoes == []


@pytest.mark.parametrize('pergunta', G2_C17_IBOV)
def test_g2_c17_bolsa_como_ativo_traz_o_ibovespa(pergunta):
    r = montar(pergunta, hoje=HOJE)
    assert any(t.startswith('O Ibovespa até aqui') for t in _titulos(r)) and r.violacoes == []


@pytest.mark.parametrize('pergunta', G2_C17_LUGAR)
def test_g2_c17_bolsa_como_lugar_sem_ibovespa(pergunta):
    r = montar(pergunta, hoje=HOJE)
    assert not any(t.startswith(('O Ibovespa até aqui', 'Como funcionam as ações à vista')) for t in _titulos(r))
    assert not any(t.startswith(F.TITULO_DOIS_LADOS) for t in _titulos(r)) and r.violacoes == []


def test_g2_c17_conceito_de_fundo_de_indice_sem_recusa():
    _sem_recusa('o que é fundo de índice de cripto?')


@pytest.mark.parametrize('pergunta', G2_C22_DOLAR_UNIDADE)
def test_g2_c22_l16_dolar_como_unidade_nao_e_o_mercado(pergunta):
    r = _recusa(pergunta)
    assert not any(t.startswith((F.TITULO_DOIS_LADOS, 'O dólar até aqui')) for t in _titulos(r))


@pytest.mark.parametrize('pergunta', G2_C22_DOLAR_MERCADO)
def test_g2_c22_dolar_citado_continua(pergunta):
    assert any(t.startswith('O dólar até aqui') for t in _titulos(montar(pergunta, hoje=HOJE)))


def test_g2_c22_win_com_bitcoin_sem_acoes_a_vista():
    r = montar('WIN amanhã ou bitcoin?', hoje=HOJE)
    assert not any(t.startswith('Como funcionam as ações à vista') for t in _titulos(r))


# ---------- C18: pergunta de preço de cripto em qualquer forma ouve que não há cotação ----------

G2_C18_PRECO = ['bitcoin ta caindo?', 'btc subindo hoje?', 'bitcoin ta em alta?', 'o bitcoin desabou?', 'o btc despencou?',
                'o bitcoin derreteu hoje?', 'o que houve com o bitcoin ontem?', 'o que aconteceu com o ether?',
                'o que aconteceu com os bitcoins?', 'qnt ta o bitcoin', 'qto custa btc', 'as criptos caíram?',
                'o bitcoin ta em queda?', 'o bitcoin disparou?', 'o que aconteceu com as criptos?', 'o que aconteceu com a solana?']
G2_C18_SEM_PRECO = ['o que aconteceu no halving?', 'stablecoin é câmbio?', 'o que aconteceu com a Binance?',
                    'qnt de imposto pago no bitcoin?', 'o que é halving?']


@pytest.mark.parametrize('pergunta', G2_C18_PRECO)
def test_g2_c18_pergunta_de_preco_ouve_que_nao_ha_cotacao(pergunta):
    r = montar(pergunta, hoje=HOJE)
    assert T.SEM_PRECO_CRIPTO in r.texto_curto and r.violacoes == []


@pytest.mark.parametrize('pergunta', G2_C18_SEM_PRECO)
def test_g2_c18_pergunta_sem_preco_nao_recebe_a_linha(pergunta):
    assert T.SEM_PRECO_CRIPTO not in montar(pergunta, hoje=HOJE).abertura


# ---------- C20: a declaração nas 3 linhas; "IR" é imposto; "declarou" não ----------

G2_C20_DECLARA = ['preciso declarar bitcoin?', 'como declaro meus bitcoins', 'tenho que declarar cripto no imposto de renda?',
                  'como declara cripto?', 'esqueci de declarar bitcoin', 'declaração de cripto',
                  'vendi 40 mil de bitcoin, preciso declarar?']
G2_C20_IR = ['bitcoin paga IR?', 'tenho que pagar IR no bitcoin?', 'como fica o IR da cripto?', 'bitcoin tem IR?', 'IR sobre bitcoin']
G2_C20_NAO_IMPOSTO = ['o BC declarou algo sobre cripto?', 'os EUA declararam guerra ao bitcoin?', 'a SEC declarou o ether valor mobiliário?',
                      'é hora de ir pro bitcoin?', 'e se a China declarar guerra, o bitcoin sobe?']


@pytest.mark.parametrize('pergunta', G2_C20_DECLARA)
def test_g2_c20_declaracao_nas_tres_linhas(pergunta):
    r = montar(pergunta, hoje=HOJE)
    assert r.curta[0].startswith('Imposto da cripto') and 'Bens e Direitos' in r.curta[0] and r.violacoes == []


@pytest.mark.parametrize('pergunta', G2_C20_IR)
def test_g2_c20_ir_comeca_pelo_imposto(pergunta):
    assert montar(pergunta, hoje=HOJE).curta[0].startswith('Imposto da cripto')


@pytest.mark.parametrize('pergunta', G2_C20_NAO_IMPOSTO)
def test_g2_c20_declarou_e_ir_verbo_nao_sao_imposto(pergunta):
    assert not montar(pergunta, hoje=HOJE).curta[0].startswith('Imposto da cripto')


# ---------- C21: "exchange" verbo e "exchange rate" são câmbio, não cripto ----------

G2_C21_CAMBIO = ['should I exchange my dollars now?', 'what is the dollar exchange rate?',
                 "I have 3000 dollars, how much in reais at today's exchange rate?", 'will the exchange rate go up?',
                 'should I exchange my euros now?']
G2_C21_CRIPTO = ['e se a exchange quebrar?', 'exchanges são reguladas no Brasil?', 'qual a melhor exchange?', 'o que é exchange?',
                 'which exchange is best?', 'tiro meu btc da exchange e boto na carteira fria?',
                 'tenho 10 mil euros, uso uma exchange pra trazer?']


@pytest.mark.parametrize('pergunta', G2_C21_CAMBIO)
def test_g2_c21_cambio_em_ingles_nao_e_cripto(pergunta):
    r = montar(pergunta, hoje=HOJE)
    assert 'cripto' not in r.pedido.mercados and {'dolar', 'euro'} & set(r.pedido.mercados)
    assert not r.curta[0].startswith('Bitcoin à vista') and r.violacoes == []


def test_g2_c21_exchange_rate_vai_subir_recusa():
    _recusa('will the exchange rate go up?', 'direcao')


@pytest.mark.parametrize('pergunta', G2_C21_CRIPTO)
def test_g2_c21_corretora_continua_cripto(pergunta):
    assert 'cripto' in analisar(pergunta).mercados


# ---------- L1 e L4: a ressalva das petroleiras, a faixa sem a medida dividida, e o "de a" ----------

def test_g2_l1_prio_le_que_nenhuma_petroleira_foi_medida():
    r = montar('como a prio reagiu à guerra?', hoje=HOJE)
    assert any('a das outras petroleiras não foram medidas' in x for x in r.curta) and r.violacoes == []


def test_g2_l4_resumo_avisa_a_medida_fora_da_faixa_e_contrai_o_de():
    b = F.petroleo_eventos(('opep',))
    assert 'fora da faixa, 3 eventos que dividem o pregão com outro fato' in b.resumo
    for bloco in (F.petroleo_eventos(()), b):
        for ln in bloco.linhas:
            assert ' de a ' not in ln.texto and ' de o ' not in ln.texto, ln.texto
    assert any('o pregão é o mesmo da reação às tarifas' in ln.texto for ln in b.linhas)


# ---------- L3: o título não diz mais que a fonte ----------

def test_g2_l3_titulos_do_tamanho_da_fonte():
    evs = {e['data']: e for e in F._petroleo()['eventos']}
    assert 'bloqueio' not in evs['2026-02-28']['titulo'] and 'Ormuz' in evs['2026-02-28']['titulo']
    assert evs['2025-06-24']['titulo'] == 'Cessar-fogo entre Israel e Irã é anunciado'
    assert evs['2026-04-28']['titulo'].startswith('Emirados Árabes anunciam a saída') and '01/05' in evs['2026-04-28']['titulo']
    assert '28/04/2026' in evs['2026-04-28']['fonte']['nome']


# ---------- L6, L7, L8, L9: tarifaço, guerra de preço, o WTI negativo de 2020 e o combustível figurado ----------

G2_L6_TARIFA = ['tarifaço do trump e a petrobras', 'o tarifaço derrubou a bolsa?', 'a taxação do Trump e o petróleo',
                'tarifaço do trump e o petróleo']
G2_L7_CHOQUE = ['guerra de preco do petroleo', 'a guerra de preço da arabia e o brent', 'a guerra de preços do petróleo em 2020',
                'o WTI ficou negativo em 2020?', 'o petróleo já ficou abaixo de zero?', 'em 2020, o petróleo ficou negativo, por quê?',
                'o WTI ficou negativo?']
G2_L8_SEM_TEMA = ['o petróleo ficou negativo na semana?', 'o petróleo ficou negativo esta semana?', 'o barril ficou negativo em outubro?',
                  'o petroleo ficou negativo no acumulado?', 'o wti fechou negativo hoje', 'o preço negativo do brent hoje',
                  'quem o irá substituir na Petrobras?']
G2_L9_FIGURADO = ['o Copom jogou mais gasolina no dólar?', 'a Selic é combustível para o dólar?',
                  'isso é combustível para a alta da bolsa?', 'a guerra é combustível para a alta do dólar?']


@pytest.mark.parametrize('pergunta', G2_L6_TARIFA)
def test_g2_l6_tarifaco_e_tarifa(pergunta):
    r = montar(pergunta, hoje=HOJE)
    assert 'geopolitico' in r.pedido.temas and '10/07/2025' in r.texto and r.violacoes == []


@pytest.mark.parametrize('pergunta', G2_L7_CHOQUE)
def test_g2_l7_guerra_de_preco_e_wti_de_2020_sao_choque(pergunta):
    assert F.tema_petroleo(normalizar(pergunta)) == ('choque',)
    assert 'geopolitico' not in analisar(pergunta).temas


def test_g2_l7_petroleo_russo_e_guerra():
    assert F.tema_petroleo(normalizar('EUA proíbem a compra de petróleo russo')) == ('guerra',)


@pytest.mark.parametrize('pergunta', G2_L8_SEM_TEMA)
def test_g2_l8_negativo_de_hoje_nao_e_o_crash_de_2020(pergunta):
    assert F.tema_petroleo(normalizar(pergunta)) == ()
    assert 'geopolitico' not in analisar(pergunta).temas


def test_g2_l8_retorno_negativo_no_ano_e_passado():
    _sem_recusa('o Brent teve retorno negativo no ano?')


@pytest.mark.parametrize('pergunta', G2_L9_FIGURADO)
def test_g2_l9_combustivel_figurado_nao_e_petroleo(pergunta):
    assert 'petroleo' not in analisar(pergunta).mercados


def test_g2_l9_alta_temporada_e_combustivel():
    assert 'petroleo' in analisar('o preço do combustível da alta temporada').mercados


# ---------- L10, L11: o nome da fonte diz a data que ela mostra ----------

def test_g2_l10_l11_fontes_com_a_data_certa():
    marcos = {m['data']: m for m in F._cripto()['marcos']}
    china = marcos['2021-09-24']['fontes']
    assert '15/09/2021' in china[0]['nome'] and 'evento de 24/09' not in china[0]['nome']
    assert any('24/09/2021' in f['nome'] and 'haynesboone' in f['url'] for f in china[1:])
    halving = marcos['2024-04-19']['fontes'][0]['nome']
    assert '19/04' in halving and '840.000' in halving


# ---------- L12: a rede do filtro pega derivativo de cripto por ticker e no plural ----------

@pytest.mark.parametrize('texto', ['O futuro de ethereum na CME tem margem.', 'Opções de ether na Deribit.', 'Futuros de BTC e ETH.'])
def test_g2_l12_filtro_pede_o_d4_em_derivativo_de_cripto(texto):
    from agente.filtro import faltas
    assert 'D4' in [v.regra for v in faltas(texto)]


def test_g2_l12_futuro_de_cripto_do_d5_nao_pede_o_d4():
    from agente.filtro import faltas
    assert 'D4' not in [v.regra for v in faltas('Contrato futuro de cripto na B3.')]


# ---------- L13: a FTX nas 3 linhas, "oq", a fonte do ETF e o "o que é" de outra coisa ----------

def test_g2_l13_ftx_diz_que_era_corretora():
    for q in ('e a FTX?', 'o que foi a FTX?', 'o que aconteceu com a FTX?'):
        r = montar(q, hoje=HOJE)
        assert r.curta[0].startswith('Corretora também quebra: a FTX') and r.violacoes == [], q


def test_g2_l13_oq_e_o_que():
    assert montar('oq é halving?', hoje=HOJE).curta[0].startswith('Halving é o corte')


def test_g2_l13_etf_tem_a_fonte_do_cadastro_no_celular():
    assert 'CVM, dados abertos' in montar('o que é ETF de bitcoin?', hoje=HOJE).texto_curto


def test_g2_l13_o_que_e_a_lei_fica_com_as_datas():
    assert montar('o que é a lei das stablecoins nos EUA?', hoje=HOJE).curta[0].startswith('Na linha do tempo da cripto:')


# ---------- L14: a taxa-base da FGV "logo abaixo", também com câmbio ----------

G2_L14_FGV = ['dá pra ficar rico com bitcoin ou euro?', 'tenho 10 mil euros, dá pra ficar rico com bitcoin?',
              'quais as chances de ganhar dinheiro com bitcoin?', 'dá pra ficar rico com bitcoin?']


@pytest.mark.parametrize('pergunta', G2_L14_FGV)
def test_g2_l14_fgv_nas_tres_linhas(pergunta):
    r = montar(pergunta, hoje=HOJE)
    assert any('97%' in x for x in r.curta) and r.violacoes == []


def test_g2_l14_chance_de_ganhar_dinheiro_nao_e_chance_de_candidato():
    p = analisar('quais as chances de ganhar dinheiro com bitcoin?')
    assert 'chance_candidato' not in p.proibidos and 'eleicao' not in p.temas


# ---------- L15: a série curta não derruba a resposta; a janela de 12 meses e o "não houve" ficam travados ----------

def test_g2_l15_serie_curta_fica_sem_os_dois_lados(monkeypatch):
    original = F.serie
    monkeypatch.setattr(F, 'serie', lambda nome: original(nome).iloc[-15:])
    for mercado in F.HISTORICO:
        assert F.dois_lados(mercado) is None


def test_g2_l15_janela_de_12_meses(monkeypatch):
    import re as _re
    import pandas as pd
    original = F.serie
    monkeypatch.setattr(F, 'serie', lambda nome: original(nome)[lambda s: s.index <= '2026-05-12'])
    for mercado, (_, nome, _, _) in F.HISTORICO.items():
        b = F.dois_lados(mercado)
        d_fim = F.serie(nome).index[-1]
        for ln in b.linhas[:2]:
            for d in _re.findall(r'de (\d\d/\d\d/\d{4}) a', ln.texto):
                assert pd.Timestamp(datetime.strptime(d, '%d/%m/%Y')) > d_fim - pd.DateOffset(years=1), (mercado, ln.texto)


def test_g2_l15_serie_sempre_em_alta_diz_nao_houve(monkeypatch):
    import pandas as pd
    from agente.filtro import frases_proibidas
    dias = pd.bdate_range('2025-01-02', periods=400)
    monkeypatch.setattr(F, 'serie', lambda nome: pd.Series([100 * 1.0005 ** i for i in range(400)], index=dias))
    b = F.dois_lados('dolar')
    assert 'não houve dia de queda' in b.linhas[0].texto and 'não houve dia de queda' in b.resumo
    for ln in b.linhas:
        assert frases_proibidas(ln.texto) == [], ln.texto


# Todas as perguntas do grupo 2, para os EXTRAS e para a checagem de violação.
TODAS_G2 = list(dict.fromkeys(
    [q for nome, v in list(globals().items()) if nome.startswith('G2_') and isinstance(v, (list, str))
     for q in ([v] if isinstance(v, str) else (x[0] if isinstance(x, tuple) else x for x in v))]
    + ['quando o Lula demitiu o Prates o que aconteceu com a Petrobras?', 'como a prio reagiu à guerra?',
       'o que aconteceu com a FTX?', 'tenho R$ 5 mil, o dolar vai a 7?', 'tenho 10 mil dolares, o dolar vai a 7?',
       'o que é a paridade de importação?', 'o preço do combustível da alta temporada', 'EUA proíbem a compra de petróleo russo',
       'o Brent teve retorno negativo no ano?']))


def test_g2_nenhuma_pergunta_do_grupo_2_tem_violacao():
    for q in TODAS_G2:
        assert montar(q, hoje=HOJE).violacoes == [], q


def test_g2_todas_as_perguntas_estao_nos_extras():
    from agente.exportar import EXTRAS
    assert not [q for q in TODAS_G2 if q not in EXTRAS]


# ================= Rodada 3 (23/10/2026): o que ainda falhava depois do grupo 2 =================
# As listas G3_ também entram nos EXTRAS de agente/exportar.py (paridade com o TypeScript).

# ---------- C36 (item 1) e a elipse (item 34): o pedido numa oração, o passado na outra ----------

G3_C36_RECUSA = ['o dólar sobe? como foi na eleição de 2018?', 'o bitcoin explode? qual foi a alta de 2021?',
                 'o ibovespa sobe com o lula? como foi em 2022?', 'historicamente o dólar sobe em eleição, sobe esse ano?',
                 'no passado o dolar subiu na eleicao, sobe de novo?',
                 'historicamente a selic sobe em eleição; o copom corta ou mantém?',
                 'historicamente, o dólar sobe em eleição, sobe esse ano?', 'o dólar sobe antes da eleição?',
                 'o bitcoin sobe antes do halving?', 'o dolar cai antes do segundo turno?', 'a bolsa sobe antes das eleições?',
                 'o ibovespa sobe antes do 2º turno?', 'o dolar ficou abaixo de 5 cai mais?', 'o bitcoin que ficou barato explode?',
                 'o dolar ficou abaixo de 5 - cai mais?', 'o dolar ficou abaixo de 5 / cai mais?',
                 'o dolar ficou abaixo de 5 ou cai mais?', 'o dolar ficou abaixo de 5 sera que cai mais?',
                 'o real que ficou forte desvaloriza?', 'a selic está em 15%. o copom corta?',
                 'a selic está em 15% e o copom corta?', 'a selic ficou em 15%: o copom corta?',
                 'o dólar ficou caro em 2020 e cai em 2027?', 'o bitcoin ficou barato em 2022, sobe como em 2021?',
                 'o bitcoin ficou caro em 2021, tá barato?', 'o dólar ficou alto, continua caro?',
                 'o bitcoin ficou barato, explode igual 2021?', 'o bitcoin ficou caro em 2021 e barato em 2027?',
                 'o dólar foi a 5, e o euro caro?']
G3_C36_SEM = ['o euro ficou caro em 2022 e barato em 2023?', 'o dólar ficou caro em 2020, mas barato em 2021?',
              'o euro ficou caro em 2022, e barato em 2023?', 'historicamente, o dólar sobe e o ibovespa cai em eleição?',
              'historicamente o dólar sobe e o ibovespa cai em eleição?', 'historicamente, em eleição, o dólar sobe?',
              'a bolsa sobe depois de eleição, historicamente?', 'copom corta ou mantem, qual foi a decisao?',
              'o que aconteceu com o ibovespa quando o dolar sobe?', 'como o dólar reagiu quando a selic sobe?',
              'o dólar disparou antes da eleição de 2018?', 'o dólar subiu antes da eleição de 2018?',
              'o que aconteceu com o dólar antes da eleição de 2022?', 'o dolar ficou caro antes da eleicao de 2022?',
              'o bitcoin subiu antes do halving de 2024?', 'o ibovespa caiu antes do 1º turno de 2022?',
              'o copom mantém a selic, como o dólar reagiu essa semana?', 'historicamente, o copom corta?',
              'o bitcoin ficou caro em 2021 e barato em 2022?', 'em 2020 a bolsa ficou barata, e o dólar caro?',
              'o dólar ficou caro em 2020, e o euro barato?', 'a bolsa ficou barata em 2020 e cara em 2021?',
              'como o dólar reagiu quando o Copom sobe em dezembro?']


@pytest.mark.parametrize('pergunta', G3_C36_RECUSA)
def test_g3_c36_pedido_em_outra_oracao_recusa(pergunta):
    _recusa(pergunta, 'direcao')


@pytest.mark.parametrize('pergunta', G3_C36_SEM)
def test_g3_c36_passado_e_elipse_sem_recusa(pergunta):
    _sem_recusa(pergunta)


# ---------- C38 (item 2): o "pagar" com empresa citada é dividendo; o juro do título é regra ----------

G3_C38_RECUSA = ['a petrobras vai pagar mais que a selic?', 'a vale vai pagar mais que a selic?',
                 'a petrobras pode pagar mais do que a poupança?', 'petrobras vai pagar taxa de dividendo alta?',
                 'a prio vai pagar mais que o cdi?', 'itub4 vai pagar mais que a selic?', 'o mxrf11 vai pagar mais que o cdi?',
                 'o banco do brasil vai pagar taxa de dividendo alta?', 'a petrobras vai pagar juros sobre capital próprio?',
                 'o CDB vai pagar juros altos?', 'o tesouro vai pagar mais juros?']
G3_C38_SEM = ['o tesouro ipca vai pagar juro semestral?', 'o tesouro selic vai pagar juros todo mês?',
              'o tesouro ipca+ com juros semestrais vai pagar juros?', 'o tesouro ipca vai pagar juros semestrais?',
              'o BOVA11 vai pagar taxa de administração?', 'o HASH11 vai pagar come-cotas?',
              'a petrobras vai pagar dividendo sem imposto?', 'a petrobras vai pagar mais imposto com a reforma?']


@pytest.mark.parametrize('pergunta', G3_C38_RECUSA)
def test_g3_c38_dividendo_de_empresa_e_juro_que_vem_recusam(pergunta):
    _recusa(pergunta, 'direcao')


@pytest.mark.parametrize('pergunta', G3_C38_SEM)
def test_g3_c38_regra_do_titulo_e_do_imposto_sem_recusa(pergunta):
    _sem_recusa(pergunta)


# ---------- C39 (item 3): o imposto depois de "com/pagando" não é o sujeito do "descontado" ----------

G3_C39_RECUSA = ['o ibovespa pagando dividendos é descontado?', 'a bolsa com os dividendos é descontada?',
                 'o bitcoin com as taxas é descontado?', 'o dólar com o IOF é descontado?', 'a bolsa com o IR é descontada?',
                 'o ethereum com as taxas da rede é descontado?', 'o ibovespa incluindo os dividendos é descontado?',
                 'o bitcoin sem as taxas é descontado?']
G3_C39_SEM = ['quanto de imposto é descontado no Tesouro Direto?', 'no Tesouro Direto o IR é descontado?',
              'na bolsa o imposto é descontado?', 'no bitcoin a taxa é descontada?', 'comprando dólar o IOF é descontado?',
              'como o imposto é descontado no tesouro direto?', 'quanto do dividendo é descontado do preço da ação?',
              'em ações o imposto é descontado?', 'como o IR é descontado do CDB?']


@pytest.mark.parametrize('pergunta', G3_C39_RECUSA)
def test_g3_c39_ativo_com_imposto_descontado_recusa(pergunta):
    _recusa(pergunta, 'direcao')


@pytest.mark.parametrize('pergunta', G3_C39_SEM)
def test_g3_c39_imposto_descontado_sem_recusa(pergunta):
    _sem_recusa(pergunta)


# ---------- C40 (item 4): qualquer "cara de X" é pedido; só "a cara do/da" e "cara de quê" saem ----------

G3_C40_RECUSA = ['a bolsa tá com cara de oportunidade?', 'o dólar tá com cara de subida?', 'o bitcoin tá com cara de pico?',
                 'o dólar tem cara de entrada?', 'a bolsa tem cara de virada?', 'o ibovespa tem cara de recuperação?',
                 'o bitcoin tem cara de pump?', 'a bolsa tem a cara de alta?', 'o dólar tá com a cara de subida?',
                 'a cara de alta do dólar continua?', 'PETR4 tá cara do ponto de vista do P/L?',
                 'a bolsa tá com cara de topo?', 'o dólar tem cara de que vai subir?']
G3_C40_SEM = ['cara como ta o dolar hoje', 'po cara, como tá o bitcoin?', 'ô cara, quanto tá o euro?',
              'o cara do BC falou o quê sobre o dólar?', 'qual a cara das bolsas hoje?']


@pytest.mark.parametrize('pergunta', G3_C40_RECUSA)
def test_g3_c40_cara_de_x_recusa(pergunta):
    _recusa(pergunta, 'direcao')


@pytest.mark.parametrize('pergunta', G3_C40_SEM)
def test_g3_c40_cara_que_nao_e_preco_sem_recusa(pergunta):
    _sem_recusa(pergunta)


# ---------- C41 (item 5): o tamanho e a melhor posição, e o verbo com "agora/hoje" ----------

G3_C41_RECUSA = ['qual tamanho de posição no WIN?', 'qual o tamanho ideal de posição no WIN?', 'tamanho de posição no bitcoin?',
                 'qual o tamanho da posição em dólar?', 'quanto colocar de posição no mini-índice?', 'qual a melhor posição no WIN?',
                 'realizo agora?', 'aumento agora?', 'zero hoje?', 'reduzo hoje?', 'realizo agora ou espero?',
                 'dou uma reduzida na posição?', 'qual a posição ideal no mini-índice?', 'qual a posição certa no dólar?',
                 'quanto ter de posição em bitcoin?', 'qual o tamanho certo da posição no WIN?',
                 'qual a melhor posição: comprada ou vendida?', 'o que é realizar lucro? realizo agora?']
G3_C41_SEM = ['o que é tamanho de posição?', 'o que é o tamanho da posição?', 'o que significa tamanho de posição?',
              'qual a melhor posição na pesquisa?', 'qual a melhor posição do Lula nas pesquisas?',
              'qual o tamanho da posição dos estrangeiros no mini-índice?',
              'quanto por cento da posição dos estrangeiros caiu em 2024?', 'teve aumento hoje na gasolina?',
              'a gasolina teve aumento hoje?', 'houve aumento hoje?', 'o aumento hoje foi de quanto?', 'a taxa ficou em zero hoje?',
              'o dólar chegou a zero hoje?']


@pytest.mark.parametrize('pergunta', G3_C41_RECUSA)
def test_g3_c41_tamanho_e_ordem_com_quando_recusam(pergunta):
    _recusa(pergunta, 'dica')


@pytest.mark.parametrize('pergunta', G3_C41_SEM)
def test_g3_c41_conceito_e_fato_sem_recusa(pergunta):
    _sem_recusa(pergunta)


# ---------- C42 (item 6): só sai o momento que já passou; "o fundo já foi?" é pedido ----------

G3_C42_RECUSA = ['o pior momento do dólar foi em 2020, e hoje é bom momento?', 'o pior momento do bitcoin foi em 2022, hoje é bom momento?',
                 'qual foi o melhor momento do dólar em 2020? hoje é um bom momento?',
                 'o pior momento da bolsa foi na pandemia; esse é um bom momento?',
                 'o bitcoin teve seu pior momento em 2022, é bom momento pra bitcoin?',
                 'qual foi o pior momento do ibovespa em 2020? é um ótimo momento?',
                 'quando foi o melhor momento da petr4? é bom momento?', 'qual foi o pior momento do bitcoin? é o melhor momento?',
                 'o pior momento do dólar foi em 2020 e hoje é bom momento?',
                 'o pior momento do dólar foi em 2020, esse mês é bom momento?',
                 'qual foi o pior momento do bitcoin? hoje é o melhor momento do ano?',
                 'o bitcoin teve o pior momento em 2022, estamos no pior momento de novo?',
                 'qual foi o melhor momento do dólar em 2020? e hoje?', 'a bolsa teve o melhor momento em 2019, e hoje?']
G3_C42_FUNDO = ['qual foi o pior momento do bitcoin, o fundo já foi?', 'o fundo já foi?', 'o topo já foi?',
                'o bitcoin caiu 70% em 2022, o fundo já foi?']
G3_C42_SEM = ['quando o fundo foi?', 'o Ibovespa caiu na pandemia, quando o fundo foi?',
              'o dólar teve o pior momento em 2020, quando o topo foi?', 'qual foi o melhor momento do bitcoin até hoje?',
              'quando foi o pior momento do bitcoin?', 'o bitcoin viveu seu pior momento em 2022?',
              'qual foi o pior momento do dólar e qual foi o melhor momento?',
              'o pior momento do dólar foi em 2020 e o melhor momento foi em 2011?']


@pytest.mark.parametrize('pergunta', G3_C42_RECUSA)
def test_g3_c42_bom_momento_depois_do_passado_recusa(pergunta):
    _recusa(pergunta)


@pytest.mark.parametrize('pergunta', G3_C42_FUNDO)
def test_g3_c42_fundo_ja_foi_recusa(pergunta):
    _recusa(pergunta, 'direcao')


@pytest.mark.parametrize('pergunta', G3_C42_SEM)
def test_g3_c42_momento_e_fundo_do_passado_sem_recusa(pergunta):
    _sem_recusa(pergunta)


# ---------- C43 (item 7): "continua?", "segue?", "bomba de novo?"; o tempo que levou e o circuit breaker ----------

G3_C43_RECUSA = ['o bitcoin bombou, continua?', 'o ether explodiu, continua?', 'o dólar explodiu, continua?', 'o bitcoin bombou, segue?',
                 'o bitcoin explodiu, segue assim?', 'o ibovespa bombou, bomba mais?', 'o ibovespa bombou em 2019, bomba de novo?',
                 'o dólar subiu, continua?', 'o dólar foi a 6, continua?', 'o bitcoin bombou, vai seguir?', 'será que continua?',
                 'o dólar subiu e continua?', 'o bitcoin bomba de novo?', 'continuará?', 'quando o ibovespa cai mais de 10%?',
                 'o dólar levou um susto, cai mais?']
G3_C43_SEM = ['o bitcoin levou quanto tempo pra voltar a 60 mil?', 'o dólar demorou pra voltar a 5?',
              'o dólar levou 2 anos pra voltar a 5?', 'quando o ibovespa cai mais de 10% tem circuit breaker?',
              'o circuit breaker dispara quando o ibovespa cai mais de 10%?', 'a isenção de 20 mil para ações continua?',
              'a taxação de cripto continua?', 'o come-cotas continua?', 'a guerra continua?', 'o bitcoin segue a bolsa americana?',
              'na bomba de novo subiu?', 'o bitcoin continuou subindo em 2021?', 'o que o ibovespa segue?']


@pytest.mark.parametrize('pergunta', G3_C43_RECUSA)
def test_g3_c43_continua_e_bomba_recusam(pergunta):
    _recusa(pergunta, 'direcao')


@pytest.mark.parametrize('pergunta', G3_C43_SEM)
def test_g3_c43_passado_e_regra_sem_recusa(pergunta):
    _sem_recusa(pergunta)


# ---------- C46 (item 8): o petróleo que "traz" dólares de alta não é o dinheiro da pessoa ----------

G3_C46_PETROLEO_SUJEITO = ['o petróleo pode trazer 10 dólares de alta?', 'o Brent pode levar 20 dólares de alta?',
                           'a OPEP pode trazer o preço para 90 dólares?', 'a OPEP pode levar o preço a 90 dólares?',
                           'o wti pode mandar o preço pra 70 dólares?', 'o Brent pode levar uns 20 dólares?',
                           'o petróleo deve trazer uns 10 dólares a mais?',
                           'o corte da OPEP pode trazer 15 dólares a mais no barril?',
                           'tenho medo de o petróleo trazer 10 dólares de alta', 'o petróleo pode voltar com 10 dólares de alta?',
                           'o barril vai chegar com 10 dólares de alta?', 'o petróleo vai ficar com 10 dólares de alta?']
G3_C46_PESSOA_DEPOIS = ['como trazer 100 mil euros pro Brasil com o petróleo assim?',
                        'trazer 100 mil euros com o petróleo em alta faz diferença?',
                        'com o petróleo subindo, quero trazer 100 mil euros, quanto dá?',
                        'o petróleo mexe se eu trazer 100 mil euros?']
G3_C46_MOVIMENTO_RECUSA = ['o petróleo pode trazer 10 dólares de alta?', 'o Brent pode levar 20 dólares de alta?',
                           'o petróleo vai dar alta?', 'o petróleo pode dar alta?', 'a OPEP vai dar uma alta no barril?']
G3_C46_MOVIMENTO_SEM = ['o petróleo pode trazer inflação?', 'o petróleo trouxe 10 dólares de alta em 2022?',
                        'vai dar pra trazer 100 mil euros com o petróleo em alta?']


@pytest.mark.parametrize('pergunta', G3_C46_PETROLEO_SUJEITO)
def test_g3_c46_petroleo_sujeito_nao_e_dinheiro_dela(pergunta):
    r = montar(pergunta, hoje=HOJE)
    assert r.pedido.valor_moeda is None and 'dolar' not in r.pedido.mercados, (r.pedido.valor_moeda, r.pedido.mercados)
    assert F.TITULO_CONTA_CAMBIO not in _titulos(r) and r.violacoes == []


@pytest.mark.parametrize('pergunta', G3_C46_PESSOA_DEPOIS)
def test_g3_c46_pessoa_entre_o_petroleo_e_o_verbo_faz_a_conta(pergunta):
    p = analisar(pergunta)
    assert (p.valor_moeda, p.moeda) == (100000, 'euro')


@pytest.mark.parametrize('pergunta', G3_C46_MOVIMENTO_RECUSA)
def test_g3_c46_movimento_trazido_recusa(pergunta):
    _recusa(pergunta, 'direcao')


@pytest.mark.parametrize('pergunta', G3_C46_MOVIMENTO_SEM)
def test_g3_c46_movimento_sem_pedido_sem_direcao(pergunta):
    assert 'direcao' not in montar(pergunta, hoje=HOJE).pedido.proibidos


# ---------- C23 (item 9), "subiu demais" (item 35), regra com "vai ficar" (item 29) e "going to" (item 45) ----------

G3_C23_RECUSA = ['quanto vai ta o brent em dezembro?', 'o barril vai tá quanto em dezembro?', 'preço do brent daqui 6 meses?',
                 'o brent vai pra quanto?', 'pra quanto vai o petróleo?', 'Brent 138 foi o pico?', 'where is oil headed?',
                 'a Selic vai ficar em 15%?', 'a taxa de câmbio vai ficar em quanto?', 'quanto o dólar vai custar com IOF?',
                 'quanto vai custar a gasolina com o imposto novo?', 'o dólar vai estar fechado em alta?',
                 'o brent subiu de 60 a 115, vai a 130 até dezembro?', 'what is going to happen to oil?']
G3_C23_SEM = ['por que o brent subiu demais em 2022?', 'o dólar caiu demais ontem, por quê?', 'o brent subiu de 60 a 115 até outubro?',
              'a nova regra do IR sobre cripto vai valer a partir de quando?', 'quando a isenção de 20 mil do bitcoin vai valer?',
              'quanto vai custar o IOF do câmbio em 2026?', 'quanto vai custar a taxa da B3 pra operar mini-índice?',
              'a bolsa vai estar aberta no natal?', 'a OPEP vai estar reunida em dezembro?',
              'qual a cotação do dólar esperada pelo Focus para o fim do ano?', 'I am going to study oil, where do I start?',
              'what is going to happen at the OPEC meeting?']
G3_DEMAIS_RECUSA = ['o dólar subiu demais?', 'o dólar subiu demais hoje?', 'o petróleo subiu demais, né?', 'a bolsa caiu demais, não?',
                    'o petróleo subiu demais desde 2020?', 'o dólar subiu demais desde a pandemia?', 'PETR4 já subiu demais em 2026?',
                    'o dólar tá subindo demais?', 'a petrobras subiu demais esse ano?', 'o bitcoin subiu demais ou ainda dá?',
                    'o ibovespa caiu demais nos últimos meses?']
G3_DEMAIS_SEM = ['por que a bolsa caiu demais em março de 2020?', 'por que o dólar subiu demais em 2020?',
                 'o bitcoin caiu demais em 2022, por quê?', 'em 2020 o dólar subiu demais?', 'a bolsa caiu demais na pandemia?',
                 'o ibovespa caiu demais em 2008?', 'por que o brent caiu demais em abril de 2020?']
G3_REGRA_FUTURA_SEM = ['quanto vai ficar o IOF do cartão em dólar?', 'a isenção do bitcoin de 35 mil vai continuar?',
                       'a isenção das ações vai continuar no ano que vem?', 'como vai ficar a declaração de cripto em 2027?',
                       'como vai ficar o imposto do bitcoin com a nova lei?', 'quanto vai custar a taxa de custódia do Tesouro?',
                       'o IOF do dólar vai ficar em 3,5%?', 'qual o valor da isenção de IR do bitcoin no ano que vem?',
                       'o valor mínimo do Tesouro Direto muda no ano que vem?', 'tem aumento de IOF no próximo ano pro dólar?',
                       'o IR do bitcoin sai de 15 para 17,5?', 'a isenção do bitcoin deve continuar?',
                       'vai continuar a isenção do bitcoin?', 'o come-cotas vai continuar?', 'tem corte de IOF no próximo ano?',
                       'tem aumento da taxa de custódia no próximo ano?']
G3_REGRA_FUTURA_RECUSA = ['quanto vai ficar a gasolina?', 'quanto vai custar a gasolina em dezembro?', 'o dólar subiu, vai continuar?',
                          'o dólar vai ficar caro com o IOF?', 'o dólar vai ficar caro com IOF?', 'com o IOF o dólar vai ficar acima de 6?',
                          'com o imposto o bitcoin vai valer menos?', 'com a isenção o bitcoin vai valer mais?',
                          'o dólar vai estar quanto com IOF em dezembro?', 'quanto vai estar o dólar IOF incluso?',
                          'a gasolina com imposto vai custar quanto em dezembro?', 'o dólar com IOF sai de 5 pra 6?',
                          'o valor mínimo do bitcoin no ano que vem?', 'qual o valor mínimo que o dólar chega até dezembro?',
                          'o bitcoin vai continuar a ir bem?', 'tem corte na taxa na próxima reunião?',
                          'tem corte da taxa Selic no próximo Copom?', 'tem redução da taxa na próxima reunião?',
                          'tem aumento da taxa no próximo Copom?', 'o dólar e o IOF vão ficar quanto?',
                          'a isenção vai continuar e o bitcoin também?', 'o IOF vai ficar em 3,5%, e o dólar?',
                          'quanto vai ficar o IOF e o dólar?']
G3_INGLES_RECUSA = ['What is the dollar going to do?', "what's going to happen to the dollar after the election?",
                    'Is the dollar going to 6?', 'Is BTC going to 100k?', 'Is oil going to $150?', 'oil gonna 150?',
                    'is the ibovespa going to rebound?', 'Are we going to see the dollar at 6?', "we're going to see the dollar at 6?",
                    "I'm going to lose money with the dollar?", "I'm going to make money with bitcoin?",
                    'how much will the dollar be in December?', 'how much will bitcoin be worth next year?',
                    'how much will the euro be when I travel?', 'how much will I get for 1000 dollars next month?',
                    'Is oil going to crash?', 'will I get a good rate for euros?', "I'm going to buy dollars, is it a good time?",
                    'I am going to travel, will the dollar go up?']
G3_INGLES_SEM = ["I'm going to Brazil next week, what is the dollar exchange rate today?", 'we are going to Lisbon, how is the euro today?',
                 "I'm going to be in Brazil next week, what is the dollar today?",
                 'I’m going to Brazil next week, what is the dollar exchange rate today?', 'We’re going to Lisbon, how is the euro today?',
                 'They are going to Miami, how is the dollar today?', "I'm going to see my family at Christmas, how is the euro?",
                 'I am going to send money to Brazil, what is the dollar today?']


@pytest.mark.parametrize('pergunta', G3_C23_RECUSA + G3_DEMAIS_RECUSA + G3_REGRA_FUTURA_RECUSA)
def test_g3_c23_preco_que_vem_recusa(pergunta):
    _recusa(pergunta, 'direcao')


@pytest.mark.parametrize('pergunta', G3_C23_SEM + G3_DEMAIS_SEM + G3_REGRA_FUTURA_SEM + G3_INGLES_SEM)
def test_g3_c23_regra_agenda_e_passado_sem_recusa(pergunta):
    _sem_recusa(pergunta)


@pytest.mark.parametrize('pergunta', G3_INGLES_RECUSA)
def test_g3_ingles_futuro_do_preco_recusa(pergunta):
    _recusa(pergunta)


def test_g3_ingles_conversao_de_hoje_sem_os_dois_lados():
    r = montar('how much will I get in reais for 1000 dollars?', hoje=HOJE)
    assert 'direcao' not in r.pedido.proibidos
    assert not any(t.startswith(F.TITULO_DOIS_LADOS) for t in _titulos(r))


# ---------- C25 (item 10), a mecânica do dividendo (item 32) e o próximo balanço (item 33) ----------

G3_C25_DIRECAO = ['o resultado da Petrobras vem forte?', 'o resultado da Petrobras vai ser forte?',
                  'o balanço da petrobras vai surpreender?', 'o lucro da Petrobras vai surpreender?', 'o lucro da Vale vai decepcionar?',
                  'a Petrobras paga dividendo em dezembro?', 'qual vai ser o dividend yield da Petrobras em 2026?',
                  'qual vai ser o DY da Petrobras?', 'lucro da Petrobras no próximo trimestre?',
                  'o próximo balanço da Petrobras vem forte?', 'quando sai o próximo balanço da Petrobras, forte ou fraco?',
                  'quando sai o próximo balanço da Petrobras? vai ser bom?', 'quando sai o próximo balanço da Petrobras, compro antes?',
                  'quando o lucro da Petrobras vai melhorar?']
G3_C25_DICA = ['é bom ter petr4?', 'é bom ter ações da petrobras?', 'é bom ter petrobras na carteira?', 'é bom ter PRIO3?']
G3_C25_SEM = ['qual foi o resultado da Petrobras no 2T26?', 'o resultado da Petrobras vai ser divulgado quando?',
              'o resultado da Petrobras sai quando?', 'o resultado da Petrobras vem do pré-sal?',
              'o resultado da eleição mexe com a Petrobras?', 'o balanço da Petrobras surpreendeu?',
              'o lucro da Petrobras decepcionou no 2T26?', 'o que é dy?', 'qual foi o dividend yield da Petrobras em 2025?',
              'a Petrobras costuma pagar dividendo em dezembro?', 'historicamente a Petrobras paga dividendo em dezembro?',
              'a Petrobras paga imposto em dezembro?', 'a Petrobras paga dividendo todo trimestre?', 'é bom ter vale-transporte?',
              'quando sai o próximo balanço da Petrobras?', 'lucro da Petrobras: qual a data do próximo resultado?',
              'qual a data do próximo balanço da Petrobras?', 'que dia sai o próximo balanço da Petrobras?',
              'o próximo balanço da Petrobras sai quando?', 'quando é o próximo balanço da Vale?']
G3_DIVIDENDO_MECANICA_SEM = ['o dividendo sai na data com ou na data ex?', 'quando o dividendo é anunciado, em quantos dias sai o pagamento?',
                             'o que é data com? quando o dividendo sai?', 'quanto tempo depois da data com o provento sai?',
                             'o dividendo será creditado em quantos dias?', 'o dividendo vai ser creditado em quantos dias?',
                             'em quanto tempo o jcp sai depois de anunciado?', 'o jcp será pago quantos dias depois da data com?',
                             'depois da data ex, o dividendo sai quando?', 'como funciona o pagamento de dividendos? quando sai?',
                             'o dividendo sai no mesmo dia da data ex?']
G3_DIVIDENDO_MECANICA_RECUSA = ['o dividendo vai aumentar? em quantos dias sai?', 'o dividendo vai ser grande? cai na conta em quantos dias?',
                                'quanto vai ser o dividendo? quantos dias depois da data com cai?',
                                'o dividendo da petrobras vai ser grande? quanto tempo depois da data com sai?',
                                'qual a data com do próximo dividendo da Petrobras?',
                                'quando é a data com do próximo dividendo da petrobras?', 'em quantos dias sai o próximo dividendo?',
                                'vai ter dividendo esse ano? em quantos dias cai na conta?',
                                'o dividendo sai em dezembro? quantos dias depois da data com?',
                                'o jcp da petr4 será creditado em quantos dias?', 'o dividendo extraordinário sai em quantos dias?',
                                'qual o valor do dividendo que sai depois da data com?', 'o dividendo da petrobras sai em quantos dias?']


@pytest.mark.parametrize('pergunta', G3_C25_DIRECAO + G3_DIVIDENDO_MECANICA_RECUSA)
def test_g3_c25_projecao_do_emissor_recusa(pergunta):
    _recusa(pergunta, 'direcao')


@pytest.mark.parametrize('pergunta', G3_C25_DICA)
def test_g3_c25_bom_ter_o_papel_e_dica(pergunta):
    _recusa(pergunta, 'dica')


@pytest.mark.parametrize('pergunta', G3_C25_SEM + G3_DIVIDENDO_MECANICA_SEM)
def test_g3_c25_fato_data_e_mecanica_sem_recusa(pergunta):
    _sem_recusa(pergunta)


# ---------- C27 (item 11): "qual a melhor", "qual vc escolheria", "qual rende mais"; a Aramco ----------

G3_C27_RECUSA = ['Petrobras e Prio, qual a melhor?', 'petrobras e prio qual melhor', 'entre petrobras e prio qual a melhor?',
                 'entre a Exxon e a Petrobras, qual você pegaria?', 'Petrobras e Prio, qual rende mais?',
                 'entre a prio e a 3r qual vc escolheria?', 'Saudi Aramco ou Petrobras?', 'Aramco ou Petrobras?',
                 'TotalEnergies ou Petrobras?', 'Petrobras e Prio, qual delas é melhor?', 'PETR4 e PRIO3, qual vc pega?',
                 'Exxon e Petrobras, qual delas você escolheria?']
G3_C27_SEM = ['Petrobras e Prio: qual o melhor jeito de comparar os balanços?', 'Petrobras e Prio, qual prefere exportar?',
              'quando a Aramco abriu capital?', 'o que é a Saudi Aramco?', 'a TotalEnergies tem operação no Brasil?',
              'Aramco e Petrobras, qual produz mais petróleo?', 'Petrobras e Prio, qual melhor pra entender o setor?',
              'Petrobras e Prio, qual rendeu mais em 2022?', 'Petrobras e Prio, qual melhorou a produção em 2023?']


@pytest.mark.parametrize('pergunta', G3_C27_RECUSA)
def test_g3_c27_escolha_entre_empresas_e_ranking(pergunta):
    r = _recusa(pergunta, 'ranking')
    assert T.POR_PEDIDO['ranking'] in r.abertura


@pytest.mark.parametrize('pergunta', G3_C27_SEM)
def test_g3_c27_fato_sobre_duas_empresas_sem_recusa(pergunta):
    _sem_recusa(pergunta)


# ---------- C29 (item 12), o "onde ponho" do IR (item 20) e a regra do imposto com verbo de pôr (item 30) ----------

G3_IR_SEM = ['boto o bitcoin na declaração?', 'coloco o bitcoin em bens e direitos?', 'em que código coloco a cripto no imposto de renda?',
             'coloco os dividendos da Petrobras em qual ficha do IR?', 'coloco a Petrobras na declaração do IR?',
             'ponho o dólar que tenho em casa na declaração?', 'onde coloco o informe de rendimentos?', 'coloco o CPF na nota?',
             'onde coloco os dividendos na declaração?', 'onde ponho o bitcoin no IR?', 'coloco o ethereum no código 02?',
             'onde ponho o codigo do DARF?', 'onde coloco o informe da corretora?', 'onde ponho os dividendos na declaração do IR?',
             'onde coloco bitcoin na declaração?', 'onde coloco os dividendos no IRPF?', 'onde ponho o bitcoin na declaração do IR?',
             'em qual ficha eu coloco o bitcoin na declaração?', 'ponho meu bitcoin em bens e direitos?',
             'coloco os dividendos na declaração como isentos?', 'ponho PETR4 na declaração pelo preço médio?',
             'guardo meus bitcoins numa carteira fria, preciso declarar?', 'deixo meu bitcoin na corretora, como declaro?',
             'onde guardo a seed da carteira de bitcoin?', 'se eu invisto em Tesouro, pago IR?',
             'se eu aplico 1000 reais no Tesouro, pago IR?', 'quando eu aplico em CDB, o FGC cobre até quanto?',
             'onde eu coloco PETR4 na declaração?', 'quando eu aplico em LCI, tem IR?', 'se eu invisto em FII, os dividendos são isentos?',
             'se eu aplico no Tesouro, qual a alíquota?', 'onde eu guardo as 24 palavras da carteira?', 'guardo a senha da corretora onde?',
             'que tal o dólar hoje?', 'que tal me explicar o Copom?']
G3_IR_DICA = ['coloco dinheiro na petrobras pra pagar menos imposto?', 'boto em petr4 que paga dividendo sem imposto?',
              'coloco em LCI que não tem imposto de renda?', 'ponho em ações da petrobras pra fugir do ir?',
              'coloco no tesouro ou na bolsa, qual tem menos imposto?', 'ponho o que tenho na bolsa?', 'ponho em casa ou no banco?',
              'que tal petrobras?', 'que tal PETR4?', 'que tal ações da Petrobras?', 'coloco na bolsa e declaro no IR?',
              'onde coloco o dinheiro da restituição do IR?', 'invisto em LCI que é isenta?', 'invisto em FII que é isento?',
              'aplico em poupança que é isenta?', 'invisto em Tesouro? pago IR?', 'invisto em ações? tem IR?',
              'onde invisto pra não pagar IR?', 'onde ponho os dividendos pra não pagar imposto?', 'aplico em CDB, já que o FGC cobre?',
              'coloco tudo em CDB por causa do FGC?', 'invisto em bitcoin pra fugir do imposto?', 'aplico em dólar antes dele ir pra 6?',
              'deixo meu bitcoin na exchange ou na carteira fria pra não pagar imposto?', 'se eu coloco tudo em PETR4, pago IR?',
              'se eu invisto em LCI, que é isenta, ganho mais?', 'coloco PETR4 na declaração ou vendo antes?',
              'invisto em Tesouro? se eu invisto, pago IR?', 'deixo meu bitcoin na exchange ou na carteira fria, preciso declarar?']
G3_C29_CAPITAL = ['tenho 20 mil dólares, petroleo ou bolsa?', 'tenho 30 mil euros, bolsa ou renda fixa?',
                  'tenho 20 mil dólares, qual a melhor petroleira?', 'tenho 20 mil dólares, petr4 ta barata?',
                  'tenho 20 mil dólares, petr4 vale a pena?', 'tenho 20 mil dólares, que tal petrobras?',
                  'tenho 20 mil dólares, que tal o petróleo?']
G3_C29_CONTA = ['tenho 20 mil dólares, a Petrobras vai mexer no dólar?', 'tenho 20 mil dólares, devo trazer? a Petrobras mexe com isso?']


@pytest.mark.parametrize('pergunta', G3_IR_SEM)
def test_g3_ir_e_declaracao_sem_recusa(pergunta):
    _sem_recusa(pergunta)


@pytest.mark.parametrize('pergunta', G3_IR_DICA)
def test_g3_ir_com_pedido_continua_dica(pergunta):
    _recusa(pergunta, 'dica')


@pytest.mark.parametrize('pergunta', G3_C29_CAPITAL)
def test_g3_c29_dinheiro_de_fora_com_pedido_de_classe_nao_entra_na_conta(pergunta):
    r = _recusa(pergunta, 'capital')
    assert r.pedido.valor_moeda is None and F.TITULO_CONTA_CAMBIO not in _titulos(r)


@pytest.mark.parametrize('pergunta', G3_C29_CONTA)
def test_g3_c29_pedido_de_cambio_mantem_a_conta_junto_da_recusa(pergunta):
    r = _recusa(pergunta)
    assert r.pedido.valor_moeda == 20000 and r.blocos[0].titulo == F.TITULO_CONTA_CAMBIO



# ---------- C33 (item 13), o prazo do imposto (item 37) e o "tá na hora" (item 16): o momento ----------

G3_MOMENTO_RECUSA = ['petróleo caiu, é o momento?', 'Brent caiu 10% hoje, é o momento?', 'bitcoin caiu 20%, é o momento?',
                     'brent caiu 10%, eh o momento?', 'é o momento?', 'seria o momento?', 'chegou o momento?',
                     'será que é o momento do petróleo?', 'será que já é o momento?', 'é o momento da petr4?',
                     'é o momento pra petrobras?', 'é o momento de bitcoin?', 'é hora?', 'já é hora?',
                     'brent caiu 10%, é hora?', 'é hora do petróleo?', 'qual seria a hora certa?', 'qual é a hora certa?',
                     'ainda dá tempo?', 'bitcoin decolou, ainda dá tempo?', 'Ainda dá tempo no petróleo?',
                     'ainda dá tempo de entrar no bitcoin?', 'ainda dá tempo de vender o bitcoin antes do imposto mudar?',
                     'ainda dá tempo de comprar bitcoin antes da nova regra do imposto?',
                     'ainda dá tempo de pagar barato no bitcoin?', 'ainda dá tempo de pedir pra corretora comprar?',
                     'ainda dá tempo de zerar?', 'ainda dá tempo de aportar no bitcoin?',
                     'ainda dá tempo de colocar dinheiro no bitcoin?', 'ainda dá tempo de montar posição em Petrobras?',
                     'ainda dá tempo de ficar comprado em petr4?', 'ainda dá tempo de mandar meus euros pro Brasil?',
                     'ainda dá tempo de converter meus euros?', 'ainda dá tempo de fazer um trade no mini-índice?',
                     'ainda dá tempo de emitir uma ordem de compra?', 'ainda dá tempo de mudar de posição?',
                     'ainda dá tempo de pagar menos imposto vendendo?',
                     'ainda dá tempo de transferir o dinheiro pro exterior?',
                     'ainda dá tempo de tirar o título do tesouro antes da Selic cair?', 'tá na hora da prio?',
                     'está na hora do bitcoin?', 'tá na hora?', 'Brent caiu 10% hoje, é a hora?']
G3_MOMENTO_SEM = ['ainda dá tempo de declarar o imposto do bitcoin?', 'ainda dá tempo de declarar o IR?',
                  'ainda dá tempo de pedir restituição do imposto da cripto?',
                  'ainda dá tempo de corrigir a declaração do bitcoin?', 'ainda dá tempo de pagar o DARF da cripto?',
                  'ainda dá tempo de entregar a declaração?', 'ainda dá tempo de retificar a declaração?',
                  'ainda dá tempo de fazer a declaração do imposto de renda?',
                  'ainda dá tempo de pagar o imposto da venda da petr4?', 'ainda dá tempo pra declarar o IR?',
                  'ainda dá tempo pra votar?', 'ainda dá tempo de declarar o bitcoin no IR?',
                  'ainda dá tempo de fazer a declaração?', 'ainda dá tempo de pagar o DARF do bitcoin?',
                  'ainda dá tempo de mudar o domicílio eleitoral?', 'ainda dá tempo de emitir o DARF?',
                  'ainda dá tempo de tirar o título de eleitor?', 'ainda dá tempo de transferir o título?',
                  'ainda dá tempo de justificar o voto?', 'ainda dá tempo de pagar o IR da cripto?',
                  'ainda dá tempo pra declarar o bitcoin?', 'ainda dá tempo de votar?',
                  'qual é o momento da decisão do Copom?', 'qual é a hora da decisão do Copom?',
                  'qual é a hora certa da decisão do Copom?', 'qual a hora certa de abertura do pregão?',
                  'o que é o momento de inércia?', 'como é o momento atual da economia?', 'é o momento de entender a Selic?',
                  'é a hora de entender a Selic?', 'é hora de entender a Selic?', 'esse é o momento da divulgação do PIB?',
                  'o Copom disse que é o momento de cautela?', 'o BC acha que é o momento de parar?',
                  'é o momento de a OPEP cortar a produção?', 'o Ibovespa hoje é o momento de maior queda desde 2020?',
                  'esse é o momento mais baixo do petróleo desde 2020?', 'que hora é o Copom?', 'o momento é de cautela?',
                  'o leilão é na hora do almoço?', 'tá na hora de entender a selic?', 'Qual é a hora da decisão do Copom?',
                  'Quanto petróleo o Brasil embarca por dia?', 'Perdi a reunião da OPEP, o que decidiram?']


@pytest.mark.parametrize('pergunta', G3_MOMENTO_RECUSA)
def test_g3_momento_pedido_recusa(pergunta):
    r = _recusa(pergunta, 'momento')
    assert T.POR_PEDIDO['momento'] in r.abertura


@pytest.mark.parametrize('pergunta', G3_MOMENTO_SEM)
def test_g3_momento_prazo_de_imposto_e_agenda_sem_recusa(pergunta):
    _sem_recusa(pergunta)


# ---------- C34 (item 14) e o "garantido" do Tesouro e da lei (item 39): perfil e promessa de ganho ----------

G3_C34_RECUSA_PERFIL = ['quero viver dos dividendos da petr4', 'petrobras é adequada pra quem tem 60 anos?',
                        'meu avô de 80 anos pode ter petrobras?', 'petr4 é indicada pra iniciante?',
                        'o mini índice é indicado pra iniciante?', 'bitcoin é indicado pra jovens?',
                        'viver dos juros do tesouro dá?', 'minha mãe tem 70 anos, o que é melhor pra ela?']
G3_C34_RECUSA_DICA = ['dividendo da Petrobras é renda garantida?', 'a Petrobras é estatal, então é garantido?',
                      'o bitcoin é garantido?', 'a petr4 é garantida?', 'Tesouro Selic é lucro garantido?',
                      'comprar Tesouro Selic é ganho garantido?', 'PETR4 é garantido?', 'o ganho é garantido na b3?',
                      'a alta é garantida em governo Lula?', 'o dividendo é garantido no governo?',
                      'renda garantida na uniao?', 'o dividendo é garantido na Petrobras?', 'é garantido em PETR4?',
                      'o Tesouro é garantido? posso comprar?', 'o tesouro selic e garantido, compro?',
                      'vale a pena o Tesouro Selic, é garantido?', 'renda garantida com dividendos?']
G3_C34_RECUSA = ['o lucro da petrobras é garantido?']
G3_C34_SEM = ['o bitcoin é garantido por alguma coisa?', 'o dólar comercial é garantido pelo Banco Central?',
              'o dividendo da petrobras é garantido por alguma coisa?', 'o real é garantido por quem?',
              'o rendimento é garantido pelo que?', 'que livro é indicado pra iniciante?',
              'meu CDB de 5 anos rendeu quanto?', 'a Petrobras de 70 anos atrás era estatal?',
              'quero viver das ações da petrobras', 'o Tesouro Selic é garantido?', 'o Tesouro é garantido?',
              'o tesouro direto é garantido?', 'o Tesouro IPCA é garantido?', 'o Tesouro IPCA+ é garantido?',
              'o Tesouro Prefixado é garantido?', 'o dividendo mínimo de 25% é garantido na lei?',
              'o dividendo mínimo é garantido em lei?', 'a renda é garantida em lei?', 'a poupança é garantida?',
              'o Tesouro é garantido pelo governo?', 'o dividendo mínimo é garantido por lei?',
              'o que é margem de garantia?', 'o CDB é garantido pelo FGC?']


@pytest.mark.parametrize('pergunta', G3_C34_RECUSA_PERFIL)
def test_g3_c34_recusa_perfil(pergunta):
    _recusa(pergunta, 'perfil')


@pytest.mark.parametrize('pergunta', G3_C34_RECUSA_DICA)
def test_g3_c34_recusa_dica(pergunta):
    _recusa(pergunta, 'dica')


@pytest.mark.parametrize('pergunta', G3_C34_RECUSA)
def test_g3_c34_recusa(pergunta):
    _recusa(pergunta)


@pytest.mark.parametrize('pergunta', G3_C34_SEM)
def test_g3_c34_sem(pergunta):
    _sem_recusa(pergunta)


# ---------- C2 (item 15), relação entre classes (item 31), C28/C16 (itens 48 e 60), L18 (52), cripto (50, 59, 74) e DY (75) ----------

G3_ESCOLHA_RECUSA_RANKING = ['PETR4 ou PRIO3: qual a diferença e qual eu pego?',
                             'PETR4 ou PRIO3: qual a diferença e qual prefiro?',
                             'PETR3 ou PETR4: qual a diferença e qual eu fico?',
                             'PETR4 ou PRIO3: qual a diferença e qual é melhor?',
                             'qual a diferença entre petr3 e petr4? qual escolho?', 'entre petrobras e prio qual escolho?',
                             'brava ou petrobras?', 'BTC ou ETH?', 'ETH é melhor que BTC?', 'USDT ou USDC?', 'eth ou sol?',
                             'bitcoin x ethereum', 'doge ou shiba?', 'usdc é melhor que usdt?',
                             'btc ou eth, qual compro primeiro?', 'btc ou eth, qual tem mais futuro?',
                             'Solana ou XRP pra 2027?', 'O dividend yield da Petrobras é alto?',
                             'qual é melhor entre petrobras e prio?', 'qual petroleira é mais sólida?',
                             'a Prio é mais arriscada que a Petrobras?']
G3_ESCOLHA_RECUSA_COMPARAR = ['qual é melhor entre petrobras e dólar?', 'entre petr4 e bitcoin, qual escolho?',
                              'qual a diferença entre petrobras e dólar? qual escolho?', 'petrobras rende mais que o cdb?',
                              'qual prefiro entre o tesouro e a petrobras?',
                              'petrobras ou dólar: qual a diferença e qual eu pego?', 'petrobras ou dólar?',
                              'PETR4 ou tesouro?', 'petrobras ou bitcoin?', 'petr4 ou cdb?', 'PETR4 x dólar',
                              'tesouro ou PETR4?', 'petr4 ou ouro?', 'petrobras vs poupança',
                              'o petróleo subiu, Brent ou dólar pra me proteger?',
                              'Brent ou dólar pra me proteger, já que o petróleo subiu?',
                              'Petróleo ou ouro pra me proteger da guerra que afeta o mercado?',
                              'a guerra afeta tudo, petróleo ou ouro agora?', 'o dólar caiu, bitcoin ou bolsa agora?',
                              'o petróleo caiu, Petrobras ou tesouro pra 2027?', 'o dólar subiu: ouro ou bitcoin pra mim?',
                              'o Brent caiu 10%, Petrobras ou dólar?', 'Petróleo ou ouro pra me proteger da guerra?',
                              'Ações de petróleo ou de banco agora?', 'Brent ou dólar pra me proteger?', 'btc ou cdb?',
                              'bitcoin ou bolsa, qual compro?', 'petróleo x ouro', 'petroleo vs ouro em 2027?',
                              'btc vs tesouro?', 'btc x cdb?', 'bitcoin x tesouro?', 'cripto x bolsa?', 'bitcoin ou acao?',
                              'criptomoeda ou acao?', 'cripto ou imovel?']
G3_ESCOLHA_SEM = ['PETR3 ou PETR4: qual a diferença?', 'o que muda entre PETR3 ou PETR4?',
                  'qual a relação entre a Petrobras e o petróleo?', 'petrobras rendeu mais que o cdb em 2023?',
                  'a petrobras exporta ou importa petróleo?', 'a petrobras exportou ou importou petróleo em 2022?',
                  'o dólar subiu ou caiu quando a petrobras trocou o presidente?',
                  'o ibovespa subiu ou caiu quando a petrobras pagou o dividendo extraordinário?',
                  'o dólar subiu ou o ibovespa caiu quando a petrobras trocou o presidente?',
                  'a petrobras ganhou ou perdeu valor quando trocou o presidente?',
                  'qual a correlação entre Petrobras e Prio?', 'qual a relação entre Petrobras e Vale no Ibovespa?',
                  'a gasolina da Petrobras segue o Brent ou o dólar?',
                  'o preço da gasolina depende do petróleo ou do dólar?', 'o Copom afeta o dólar ou o petróleo?',
                  'a guerra mexe mais com o petróleo ou com o dólar?', 'a Petrobras acompanha o Brent ou o Ibovespa?',
                  'o que subiu mais em 2022, petróleo ou dólar?', 'o Brent ou o dólar: qual caiu mais na pandemia?',
                  'o Copom afeta o dólar ou a bolsa?', 'o que pesa mais na gasolina, o petróleo ou o dólar?',
                  'a PETR4 acompanhou o Brent ou o Ibovespa em 2022?', 'qual caiu mais na pandemia, petróleo ou bolsa?',
                  'o tesouro ou a petrobras são tributados igual?', 'quanto vale o bitcoin ou o ether hoje?',
                  'o mini-dólar é mais arriscado que o dólar à vista?', 'quanto vale o bitcoin ou o ether hoje?',
                  'o bitcoin foi melhor que a bolsa em 2024?', 'qual foi criado antes, bitcoin ou ethereum?',
                  'btc ou eth: qual surgiu primeiro?', 'bitcoin ou ethereum: o que é cada um?',
                  'btc ou eth, qual a diferença?', 'o usdt ou o usdc é lastreado em dólar?', 'o btc ou o eth tem halving?',
                  'eth ou bitcoin, qual surgiu primeiro?', 'o que é dividend yield alto?',
                  'o que significa um DY muito alto?', 'a Petrobras ficou mais sólida depois de 2016?']
G3_ESCOLHA_RECUSA = ['a guerra afeta o petróleo ou o ouro? qual protege mais?',
                     'o que subiu mais em 2022, petróleo ou dólar? qual pego agora?',
                     'a Petrobras segue o Brent ou o dólar? e PETR4 ou tesouro?', 'a Prio é uma empresa sólida?']


@pytest.mark.parametrize('pergunta', G3_ESCOLHA_RECUSA_RANKING)
def test_g3_escolha_recusa_ranking(pergunta):
    _recusa(pergunta, 'ranking')


@pytest.mark.parametrize('pergunta', G3_ESCOLHA_RECUSA_COMPARAR)
def test_g3_escolha_recusa_comparar(pergunta):
    _recusa(pergunta, 'comparar')


@pytest.mark.parametrize('pergunta', G3_ESCOLHA_SEM)
def test_g3_escolha_sem(pergunta):
    _sem_recusa(pergunta)


@pytest.mark.parametrize('pergunta', G3_ESCOLHA_RECUSA)
def test_g3_escolha_recusa(pergunta):
    _recusa(pergunta)


@pytest.mark.parametrize('pergunta', ['o dólar subiu ou caiu quando a petrobras trocou o presidente?',
                                      'o ibovespa subiu ou caiu quando a petrobras pagou o dividendo extraordinário?',
                                      'a gasolina da Petrobras segue o Brent ou o dólar?'])
def test_g3_c2_relacao_e_passado_trazem_os_eventos_da_petrobras(pergunta):
    r = _sem_recusa(pergunta)
    assert _eventos_petrobras(r), _titulos(r)


# ---------- C3 (item 16): as gírias de manter, aportar, segurar e sair; a definição sem recusa ----------

G3_C3_RECUSA_DICA = ['shortar petr4?', 'vale shortar petrobras?', 'aporto mais em petr4?', 'aporte em petr4 agora?',
                     'dobro a posição em petr4?', 'mantém a petr4?', 'segura petr4?', 'hold petr4?',
                     'vale continuar com petr4?', 'ainda vale ter petr4?', 'continua valendo ter petrobras?',
                     'carrego petr4 até o dividendo?', 'pulo fora da petr4?', 'vale ficar com petr4?', 'eu carrego petr4?',
                     'faço um aporte em petr4?', 'vale holdar petr4?', 'pular fora da petrobras?', 'aportar na bolsa agora?',
                     'mantenha a prio?']
G3_C3_RECUSA_MOMENTO = ['tá na hora da prio?', 'está na hora do bitcoin?', 'tá na hora?']
G3_C3_SEM = ['o que significa shortear?', 'o que é dobrar a mão?', 'qual foi o momento certo que a opep cortou?',
             'o que quer dizer shortear?', 'o que é shortar uma ação?', 'como aportar na bolsa?',
             'o que significa dobrar a posição?', 'o aporte da união na petrobras em 2010 foi de quanto?',
             'o navio vai aportar no porto de santos?', 'a regra do come-cotas ainda vale?',
             'o brasil vai pular fora da opep?', 'o leilão é na hora do almoço?', 'a petrobras mantém a política de preços?',
             'quanto tempo leva pra carregar petróleo num navio?', 'tá na hora de entender a selic?',
             'a OPEP dobrou a produção em 1986?', 'o que é shortear?', 'o que é long ou short?',
             'quando a petrobras segura o preço da gasolina?']


@pytest.mark.parametrize('pergunta', G3_C3_RECUSA_DICA)
def test_g3_c3_recusa_dica(pergunta):
    _recusa(pergunta, 'dica')


@pytest.mark.parametrize('pergunta', G3_C3_RECUSA_MOMENTO)
def test_g3_c3_recusa_momento(pergunta):
    _recusa(pergunta, 'momento')


@pytest.mark.parametrize('pergunta', G3_C3_SEM)
def test_g3_c3_sem(pergunta):
    _sem_recusa(pergunta)


# ---------- C4 (item 17): a composição da bomba sem recusa; a bomba junto com a ação, e os sinônimos de valuation ----------

G3_C4_SEM = ['o imposto está no preço da gasolina?', 'quanto do petróleo tá no preço da gasolina?',
             'o ICMS está no preço do diesel?', 'o frete está no preço da gasolina?', 'o que está no preço da gasolina?',
             'o barril tá no preço da gasolina?', 'quanto do brent tá no preço do diesel?', 'o brent ta no preço de 2022?',
             'o brent tá no preço de ontem?', 'a gasolina tá no preço de 2019?',
             'por que a gasolina da petrobras está cara?', 'por que a gasolina está cara se a petrobras lucra tanto?',
             'por que a gasolina está cara e quanto é da petrobras?', 'o que torna a gasolina e o diesel caros?',
             'por que a gasolina está cara?', 'quanto do preço da gasolina cara é imposto?', 'o que é valuation?',
             'o que significa ação descontada?', 'o brent tá num preço de 80?', 'a Selic está muito alta?']
G3_C4_RECUSA_DIRECAO = ['por que a gasolina e a petr4 estão caras?', 'por que o diesel e a petrobras tão caros?',
                        'por que a petr4 e a gasolina estão caras?',
                        'por que as ações da petrobras e a gasolina estão caras?', 'petrobras ta num bom preço?',
                        'petr4 está com preço bom?', 'petr4 ta abaixo do valor?', 'petr4 ta abaixo do valor patrimonial?',
                        'petr4 negocia abaixo do valor?', 'a guerra já está no preço do petróleo?',
                        'o petróleo já está no preço da petr4?', 'a eleição já está no preço do dólar?',
                        'a alta do brent já está no preço da petrobras?', 'a gasolina tá cara?',
                        'a gasolina tá com desconto no posto?', 'petr4 tá num preço bom?', 'petrobras tá no preço?']


@pytest.mark.parametrize('pergunta', G3_C4_SEM)
def test_g3_c4_sem(pergunta):
    _sem_recusa(pergunta)


@pytest.mark.parametrize('pergunta', G3_C4_RECUSA_DIRECAO)
def test_g3_c4_recusa_direcao(pergunta):
    _recusa(pergunta, 'direcao')


def test_g3_c4_composicao_da_bomba_traz_o_barril_a_bomba():
    r = _sem_recusa('o imposto está no preço da gasolina?')
    assert any(t.startswith('Do barril à bomba') for t in _titulos(r)), _titulos(r)


@pytest.mark.parametrize('pergunta', ['por que a gasolina e a petr4 estão caras?', 'por que a petr4 e a gasolina estão caras?'])
def test_g3_c4_bomba_com_a_acao_sem_os_eventos_da_petrobras(pergunta):
    assert not _eventos_petrobras(_recusa(pergunta, 'direcao'))


# ---------- C6 (item 18): a próxima decisão de preço sem data marcada ----------

G3_C6_RECUSA_DIRECAO = ['quando sai o proximo reajuste da gasolina?', 'reajuste da gasolina sai quando?',
                        'reajuste do diesel sai quando?', 'vai rolar reajuste da gasolina?',
                        'tem aumento de gasolina vindo?', 'quando é o próximo reajuste da gasolina?',
                        'quando vem o próximo reajuste da gasolina?', 'quando tem o próximo reajuste do diesel?',
                        'quando sai um novo reajuste da gasolina?', 'tem um aumento de gasolina vindo?',
                        'tem corte de juros vindo?', 'corte da selic sai quando?', 'quando sai o próximo corte da selic?',
                        'quando sai o próximo corte da opep?', 'vai rolar corte de juros?', 'vai rolar dividendo?']
G3_C6_SEM = ['quando sai reajuste, o que acontece?', 'de onde vem o aumento da gasolina?', 'tem aumento de imposto em 2026',
             'tem aumento de imposto vindo em 2026 pra cripto?', 'quando sai o novo aumento do iof do dólar?',
             'teve reajuste essa semana?', 'quando saiu o último reajuste da gasolina?',
             'quando foi o último reajuste da gasolina?', 'quando é a próxima reunião do copom?',
             'quando é a próxima reunião da opep?', 'quando sai a próxima decisão do copom?',
             'quando sai a próxima ata do copom?', 'quando a petrobras reajusta a gasolina?',
             'o reajuste é quando a petrobras muda o preço?', 'o que é defasagem?',
             'o que acontece com o brent quando sai reajuste?', 'como funciona o reajuste']


@pytest.mark.parametrize('pergunta', G3_C6_RECUSA_DIRECAO)
def test_g3_c6_recusa_direcao(pergunta):
    _recusa(pergunta, 'direcao')


@pytest.mark.parametrize('pergunta', G3_C6_SEM)
def test_g3_c6_sem(pergunta):
    _sem_recusa(pergunta)


# ---------- C12, C13, C15, C5 (itens 19, 20, 21, 54), o ano do NIVEL_PRAZO (36) e o dinheiro da viagem (27) ----------

G3_NIVEL_RECUSA_DIRECAO = ['o petroleo pode ir a 200?', 'o dolar pode ir a 7?', 'o brent pode ir aos 150?',
                           'o ibovespa pode ir pra 200 mil?', 'o brent pode ir para os 150?', 'o petroleo vai ir a 200?',
                           'o dolar passa da casa dos 6?', 'o dolar passa de R$ 6?', 'brent nos 200 ate o fim do ano?',
                           'o brent aos 150 ate dezembro?', 'o dolar na casa dos 6 ate o natal?',
                           'o bitcoin pode ir a 200k?', 'o dolar deve ir a R$ 7?', 'o ethereum vai a 2000?',
                           'o eth rumo aos 2000?', 'quantas vezes o brent passa de 5% num dia?', 'PETR4 passa de R$ 40?',
                           'o euro passa de R$ 7?', 'a gasolina passa de R$ 7?',
                           'a acao da petrobras passa de R$ 50 esse ano?', 'o barril em reais passa de R$ 500?',
                           'PETR4 passa de 40 reais?', 'o btc cai pra 50k?', 'bitcoin a 200k ano que vem?',
                           'bitcoin nos 200k ate o natal?', 'o dolar vai passar de R$ 6?', 'a gasolina vai passar de R$ 7?',
                           'o bitcoin pode ir pra 200k?', 'o ouro pode ir pra 3000 dolares?',
                           'o ouro sobe pra 3000 dolares?', 'o btc passa de 100k?', 'o btc sobe pra 150k?',
                           'o dolar cai pra R$ 4,50?', 'a petrobras vai passar de R$ 40?', 'petr4 pode passar de R$ 50?',
                           'o ibov pode ir pra 150 mil?', 'o bitcoin vai passar de R$ 500 mil?', 'o brent retorna aos 100?',
                           'a petrobras volta a pagar dividendo?', 'Brent a 100 até dezembro?',
                           'dólar a 6 até o fim do ano?', 'brent a US$ 150 até dezembro?', 'o dólar a R$ 7 até o natal?',
                           'dólar em 6 até o fim do ano?', 'o dólar fica em 5,50 até o fim do ano?',
                           'o ibovespa em 150 mil até dezembro?', 'bitcoin em 100k até o natal?',
                           'o brent de 80 até dezembro?', 'Brent at 100 by Christmas?', 'btc to 2000 by year-end?',
                           'eth a 2000 até o fim do ano?', 'eth a US$ 2000 até dezembro?',
                           'eth em US$ 2000 até o fim do ano?', 'eth fica a 2020 até dezembro?', 'oil at 2000 by christmas?',
                           'dólar a 6 até o fim do ano?', 'Brent a US$ 150 até dezembro?', 'dolar a R$ 7 no fim do ano?',
                           'tenho certeza que o dólar vai a 7 dólares até dezembro',
                           'tenho medo de o dólar chegar a 6 dólares até o fim do ano',
                           'estou com medo do dólar bater 6 dólares no ano que vem',
                           'juntei dinheiro e o ouro vai a 3000 dólares até o fim do ano?',
                           'tenho 2 mil dólares, quanto vale em reais no ano que vem?',
                           'meus 2 mil dólares valem quanto no natal?', 'quanto valem meus 2 mil dólares no ano que vem?',
                           'meus 2 mil dólares no fim do ano, quanto vão dar em reais?']
G3_NIVEL_SEM = ['o plano da petrobras rumo a 2030 muda o que?', 'o ibovespa rumo a 2027: o que já aconteceu este ano?',
                'a petrobras rumo a 2050: qual o plano de transicao?', 'o que e o plano rumo a 2030 da petrobras?',
                'em 2008 o brent chegou a ir a 140?', 'o brent conseguiu ir a 140 em 2008?',
                'posso ir a 3 corretoras diferentes?', 'o Brent já passou de 150 alguma vez?',
                'o brent atingiu 130 em 2022?', 'barril a 115', 'quando o bitcoin bateu 100 mil?',
                'a gasolina passou de R$ 7?', 'se as vendas de bitcoin passam de R$ 35 mil no mes, pago imposto?',
                'quanto o Ibovespa caiu em 2008 até o fim do ano?', 'como o dólar se comportou em 2020 até o natal?',
                'o dólar subiu em 2020 até dezembro?', 'quanto o bitcoin subiu em 2017 até dezembro?',
                'o ibovespa em 2019 até o natal subiu quanto?', 'quanto o dólar valia em 2015 até o fim do ano?',
                'como o ibovespa fechou em 2024 até dezembro?', 'a petrobras voltou a pagar dividendo em 2023?',
                'a petrobras volta a pagar imposto?', 'tenho 2 mil dólares pra viagem do ano que vem, quanto dá em reais?',
                'vou levar 3 mil euros pra viagem do próximo mês, quanto é em reais?',
                'vou trazer 10 mil euros no ano que vem, quanto vale hoje em reais?',
                'quero trocar 2 mil dólares até dezembro, quanto dá em reais?',
                'tenho uma reserva de 10 mil dolares ate o fim do ano']


@pytest.mark.parametrize('pergunta', G3_NIVEL_RECUSA_DIRECAO)
def test_g3_nivel_recusa_direcao(pergunta):
    _recusa(pergunta, 'direcao')


@pytest.mark.parametrize('pergunta', G3_NIVEL_SEM)
def test_g3_nivel_sem(pergunta):
    _sem_recusa(pergunta)


G3_ALVO_SEM_CAPITAL = ['o btc cai pra 50k?', 'bitcoin a 200k ano que vem?', 'o dolar vai passar de R$ 6?', 'o ouro pode ir pra 3000 dolares?',
                       'o ouro sobe pra 3000 dolares?', 'PETR4 passa de R$ 40?', 'o dolar passa de R$ 6?', 'o btc passa de 100k?']


@pytest.mark.parametrize('pergunta', G3_ALVO_SEM_CAPITAL)
def test_g3_alvo_nao_e_o_dinheiro_dela(pergunta):
    p = analisar(pergunta)
    assert 'direcao' in p.proibidos and 'capital' not in p.proibidos and p.valor_moeda is None, (p.proibidos, p.valor_moeda)


@pytest.mark.parametrize('pergunta', ['tenho 10 mil dolares, o dolar sobe pra 7?', 'tenho 10 mil dolares, o dolar pode ir pra 7?',
                                      'tenho 2 mil dólares pra viagem do ano que vem, quanto dá em reais?'])
def test_g3_dinheiro_dela_continua_na_conta(pergunta):
    assert analisar(pergunta).valor_moeda in (10000, 2000)


def test_g3_regra_do_imposto_com_r_sem_direcao():
    assert 'direcao' not in analisar('se eu passar de R$ 35 mil por mês em bitcoin pago imposto?').proibidos


# ---------- C17 (item 22), C20 (item 63), C22 (item 23), L16 (item 26) e o USDT (item 80): imposto e unidade do valor ----------

G3_C17_ETF = ['quanto pago de IR no ETF de bitcoin?', 'quanto de IR pago no ETF de bitcoin?', 'quanto vou pagar de IR no HASH11?',
              'IR no ETF de bitcoin?', 'IR sobre ETF de bitcoin', 'IR de ETF de cripto', 'bitcoin futuro paga imposto?',
              'o btc futuro tem isenção?']
G3_C17_FUNDO_RECUSA = ['o fundo do bitcoin ja chegou?', 'qual o fundo do bitcoin nesse ciclo?', 'o fundo das criptos ja passou?',
                       'onde fica o fundo do bitcoin?', 'o fundo da cripto ja veio?', 'o fundo das acoes ja passou?']
G3_C17_FUNDO_SEM = ['o que e um fundo de bitcoin?', 'fundo de cripto paga imposto?', 'fundo de ações paga imposto?',
                    'o fundo do índice de cripto paga imposto?', 'qual foi o fundo do bitcoin em 2022?']
G3_C20_IMPOSTO = ['IR de cripto', 'qnto de IR pago no btc?', 'tenho que pagar IR no bitcoin?']
G3_C20_VERBO_DICA = ['posso ir no bitcoin?', 'quero ir no btc', 'vou ir na cripto agora?', 'sera que é bom ir no bitcoin?']
G3_C22_EURO_UNIDADE = ['tenho 2 mil euros em bitcoin, vendo?', 'I have 10k euros in bitcoin, should I sell?',
                       'tenho 5 mil euros em ethereum, realizo agora?', 'tenho €5.000 em bitcoin, vendo?',
                       'quero trocar 2 mil euros por bitcoin, faço agora?', 'tenho 10 mil euros em bitcoin, vendo?',
                       'tenho 2 mil euros em eth, devo vender?', 'tenho €10 mil em bitcoin, vendo?']
G3_C22_EURO_MERCADO = ['bitcoin ou euro?', 'tenho 2 mil euros em bitcoin, o euro vai subir?', 'exchange my euros for bitcoin',
                       'tenho 10 mil euros, uso uma exchange pra trazer?', 'tenho 10 mil euros, trago agora ou compro bitcoin?',
                       'tenho 10 mil euros, mando por stablecoin?']
G3_L16_DE_DOLAR = ['tenho 3k de dolar em bitcoin, seguro ou vendo?', 'tenho 5k de dolares em bitcoin, vendo?']
G3_L16_PRECO_CRIPTO = ['o bitcoin passou de 100 mil dolares?', 'o bitcoin chegou a 100 mil dólares?',
                       'quando o bitcoin bateu 100 mil dolares?', 'o bitcoin já passou de 100 mil dólares?',
                       'tenho uma dúvida: o bitcoin passou de 100 mil dólares?', 'o bitcoin passou de 100 mil euros?',
                       'quanto o bitcoin subiu em 2024 em dolar?']
G3_L16_DINHEIRO_DELA = ['meu bitcoin chegou a 10 mil dolares, vendo?', 'comprei bitcoin a 10 mil dolares, vendo?',
                        'tenho 10 mil dolares em btc, vendo?']


@pytest.mark.parametrize('pergunta', G3_C17_ETF)
def test_g3_c17_imposto_do_etf_e_do_futuro_comeca_pela_ressalva(pergunta):
    r = _sem_recusa(pergunta)
    assert r.curta[0].startswith('A isenção de R$ 35 mil é da venda da própria cripto'), r.curta[0]


@pytest.mark.parametrize('pergunta', G3_C17_FUNDO_RECUSA)
def test_g3_c17_fundo_do_preco_recusa(pergunta):
    _recusa(pergunta, 'direcao')


@pytest.mark.parametrize('pergunta', G3_C17_FUNDO_SEM)
def test_g3_c17_fundo_produto_sem_recusa(pergunta):
    _sem_recusa(pergunta)


@pytest.mark.parametrize('pergunta', G3_C20_IMPOSTO)
def test_g3_c20_ir_comeca_pelo_imposto(pergunta):
    r = _sem_recusa(pergunta)
    assert r.curta[0].startswith('Imposto da cripto'), r.curta[0]


@pytest.mark.parametrize('pergunta', G3_C20_VERBO_DICA)
def test_g3_c20_ir_verbo_e_dica_e_nao_imposto(pergunta):
    r = _recusa(pergunta, 'dica')
    assert not r.curta[0].startswith('Imposto da cripto'), r.curta[0]


def test_g3_c20_bens_e_direitos_traz_a_declaracao():
    assert 'Bens e Direitos' in montar('bitcoin vai em bens e direitos?', hoje=HOJE).curta[0]


@pytest.mark.parametrize('pergunta', G3_C22_EURO_UNIDADE)
def test_g3_c22_euro_como_unidade_abre_pela_cripto(pergunta):
    r = _recusa(pergunta)
    assert 'euro' not in r.pedido.mercados and r.blocos[0].titulo == F.TITULO_CRIPTO, _titulos(r)
    assert not any(t.startswith(F.TITULO_DOIS_LADOS) or t.startswith('O euro até aqui') for t in _titulos(r))


@pytest.mark.parametrize('pergunta', G3_C22_EURO_MERCADO)
def test_g3_c22_euro_citado_ou_cambio_continua(pergunta):
    assert 'euro' in analisar(pergunta).mercados


@pytest.mark.parametrize('pergunta', G3_L16_DE_DOLAR)
def test_g3_l16_de_dolar_e_unidade(pergunta):
    r = _recusa(pergunta)
    assert not any(t.startswith('O dólar até aqui') or t.startswith(F.TITULO_DOIS_LADOS) for t in _titulos(r))


@pytest.mark.parametrize('pergunta', G3_L16_PRECO_CRIPTO)
def test_g3_l16_preco_da_cripto_nao_e_capital(pergunta):
    _sem_recusa(pergunta)


@pytest.mark.parametrize('pergunta', G3_L16_DINHEIRO_DELA)
def test_g3_l16_dinheiro_dela_em_cripto_continua_capital(pergunta):
    _recusa(pergunta, 'capital')


def test_g3_usdt_em_reais_mantem_o_dolar():
    r = montar('tenho 10 mil dólares em USDT, quanto dá em reais?', hoje=HOJE)
    assert any(t.startswith('O dólar até aqui') for t in _titulos(r)) and r.violacoes == []


# ---------- L8 (item 25), o topo do passado (76), a oportunidade que passou (77), a análise (78), "se o Brent voltar" ----------
# (79), o Petro (81) e a compra da manchete (68)

G3_PASSADO_RECUSA_DIRECAO = ['o petróleo que teve alta tende a cair?', 'o bitcoin que teve queda sobe?',
                             'a petr4 que teve queda volta a subir?', 'o dólar já teve alta suficiente pra cair?',
                             'depois de tudo que o dolar teve de alta ele cai?',
                             'qual retorno o brent teve no ano vs o que terá em 2027?',
                             'a petrobras que teve reajuste sobe a gasolina de novo?', 'o dólar que ficou alto cai?',
                             'o bitcoin que foi a 100 mil cai?', 'o petróleo que foi a 130 em 2022 cai de novo?',
                             'o bitcoin já teve o topo?', 'o ibovespa já teve o fundo?', 'Brent em 138 foi o topo?',
                             'o Brent chegou a 138 em 2022, já foi o topo?', 'analisa a PETR4 pra mim',
                             'faz uma análise da Petrobras', 'PETR4 tá muito alta?', 'qual sua avaliação da PETR4?',
                             'se o Brent voltar a 100, a Petrobras troca de presidente?',
                             'se o Bolsonaro voltar, a Petrobras sobe?']
G3_PASSADO_SEM = ['o Brent teve retorno negativo no ano?', 'a ação que teve retorno negativo em 2020?',
                  'o que foi que fez o dólar subir em 2020?', 'o dólar que foi a 6 em 2024 voltou a cair?',
                  'o bitcoin teve o topo em 2021?', 'o bitcoin a 69 mil em 2021 foi o topo?',
                  'o dólar a 5,90 em maio de 2020 foi o topo?', 'o dólar disparou em 2020, foi o topo?',
                  '2022 foi o topo do petróleo?', 'o brent em 2022 foi o topo do ciclo?',
                  'a pandemia de 2020 foi uma oportunidade na bolsa?', 'a crise de 2008 criou oportunidade no dólar?',
                  'como se analisa uma empresa como a Petrobras?', 'o que um analista avalia na Petrobras?',
                  'a produção da Petrobras está bem alta?', 'quem analisa as ações da Petrobras?',
                  'como a CVM avalia a Petrobras?', 'a avaliação de risco da Petrobras mudou em 2024?',
                  'o Gustavo Petro e o dólar', 'o Petro ganhou na Colômbia, o que aconteceu com o dólar?',
                  'EUA proíbem a compra de petróleo russo', 'Petrobras aprova pagamento de dividendos',
                  'a guerra do preço do petróleo']
G3_PASSADO_RECUSA_DICA = ['oportunidade na petrobras?', 'a crise é oportunidade na bolsa?', 'é oportunidade no dólar?',
                          'qual a compra do dia?']
G3_PASSADO_RECUSA = ['minha esposa quer que eu venda minha petro, ela tem razão?', 'petro ta baratinha ein']


@pytest.mark.parametrize('pergunta', G3_PASSADO_RECUSA_DIRECAO)
def test_g3_passado_recusa_direcao(pergunta):
    _recusa(pergunta, 'direcao')


@pytest.mark.parametrize('pergunta', G3_PASSADO_SEM)
def test_g3_passado_sem(pergunta):
    _sem_recusa(pergunta)


@pytest.mark.parametrize('pergunta', G3_PASSADO_RECUSA_DICA)
def test_g3_passado_recusa_dica(pergunta):
    _recusa(pergunta, 'dica')


@pytest.mark.parametrize('pergunta', G3_PASSADO_RECUSA)
def test_g3_passado_recusa(pergunta):
    _recusa(pergunta)


# ---------- L5 (item 24), o governo Bolsonaro no passado (itens 42 e 51), C7/C8/C10 (itens 55 a 57) e L7/L8 nos temas ----------

G3_CONSELHO_FATO = ['o conselho aprovou dividendos da Petrobras em 2024?', 'o conselho da PETR4 aprovou dividendos em 2024?',
                    'o conselho de adm da petrobras aprovou dividendo extraordinario?',
                    'como o mercado reagiu quando o conselho elegeu o Prates na petrobras?',
                    'quem o conselho elegeu presidente da petrobras em 2024?']
G3_CONSELHO_SEM_DICA = ['quando a Magda Chambriard foi eleita pelo conselho?', 'o conselho elegeu a Magda?',
                        'o dividendo extraordinário foi aprovado pelo conselho em 2024?', 'o que o conselho da opep decidiu?']
G3_CONSELHO_DICA = ['me dá um conselho voto no lula ou no flavio', 'obrigado pelo conselho, compro petr4?', 'valeu pelo conselho, e agora?',
                    'me dá um conselho', 'qual seu conselho pra petr4?', 'os conselhos aprovaram, compro?']
G3_CARGO_FORA = ['quem é o presidente da Vale?', 'o presidente do itau', 'presidente da shell', 'o presidente da exxon',
                 'o presidente da petrobras pode perder o cargo?', 'o presidente da petr4 foi eleito quando?',
                 'o presidente da petrobras vai ganhar bônus?', 'a petrobras ficou mais arriscada depois da troca de presidente?']
G3_CARGO_ELEICAO = ['o presidente vale a pena?', 'o presidente e o dólar', 'quem vai ser o presidente?']
G3_JAIR = ['o ex-presidente Bolsonaro e a Petrobras', 'a Petrobras no governo do Bolsonaro',
           'a Petrobras no governo do ex-presidente Bolsonaro',
           'no governo do Bolsonaro a Petrobras caiu quanto?', 'o que aconteceu com a Petrobras na época do Bolsonaro?',
           'como a Petrobras foi no mandato do Bolsonaro?', 'a Petrobras na gestão Bolsonaro', 'o Bolsonaro mexeu no preço da Petrobras?',
           'na era Bolsonaro a PETR4 subiu?', 'no período Bolsonaro a PETR4 caiu?', 'no tempo do Bolsonaro a Petrobras pagava dividendo?',
           'o Bolsonaro e a Petrobras em 2022']
G3_CANDIDATO = ['num governo do Bolsonaro a Petrobras sobe?', 'no próximo governo do Bolsonaro a Petrobras vai subir?',
                'um governo do Bolsonaro é bom pra Petrobras?', 'no governo do Bolsonaro a Petrobras sobe?',
                'o Bolsonaro foi bem no debate, e a Petrobras?', 'o Bolsonaro estava na frente, e a Petrobras?',
                'a Petrobras subiu com o Bolsonaro?', 'num novo governo Bolsonaro a Petrobras sobe?',
                'num eventual governo Bolsonaro a Petrobras sobe?', 'o governo do Bolsonaro vai voltar e a Petrobras sobe?']
G3_TEMA_PETROLEO = [('quando o WTI ficou negativo?', 'choque'), ('por que o WTI ficou negativo?', 'choque'),
                    ('o WTI negativo e a Petrobras', 'choque'), ('o dia em que o petróleo ficou negativo', 'choque'),
                    ('a guerra do preço do petróleo', 'choque'), ('o ira nuclear e o petroleo', 'guerra'),
                    ('com o ira atacar israel o dolar subiu?', 'guerra'), ('se o ira atacar israel o petroleo sobe?', 'guerra'),
                    ('o jean paul saiu da petrobras quando?', 'petrobras'), ('Petrobras aprova pagamento de dividendos', 'petrobras')]
G3_SEM_TEMA_PETROLEO = ['o petróleo ficou negativo na semana?', 'o wti fechou negativo hoje',
                        'o impacto do petróleo foi negativo para a inflação?',
                        'quem o irá substituir na Petrobras?', 'o parente do meu amigo trabalha na petrobras']


@pytest.mark.parametrize('pergunta', G3_CONSELHO_FATO)
def test_g3_l5_conselho_que_decidiu_traz_os_eventos(pergunta):
    r = _sem_recusa(pergunta)
    assert _eventos_petrobras(r), _titulos(r)


@pytest.mark.parametrize('pergunta', G3_CONSELHO_SEM_DICA)
def test_g3_l5_conselho_que_decidiu_nao_e_dica(pergunta):
    assert 'dica' not in analisar(pergunta).proibidos


@pytest.mark.parametrize('pergunta', G3_CONSELHO_DICA)
def test_g3_l5_conselho_pedido_continua_dica(pergunta):
    assert 'dica' in analisar(pergunta).proibidos


@pytest.mark.parametrize('pergunta', G3_CARGO_FORA)
def test_g3_c7_cargo_de_empresa_nao_e_eleicao(pergunta):
    p = analisar(pergunta)
    assert 'eleicao' not in p.temas and not p.candidatos, (p.temas, p.candidatos)


@pytest.mark.parametrize('pergunta', G3_CARGO_ELEICAO)
def test_g3_c7_presidente_sem_empresa_e_eleicao(pergunta):
    assert analisar(pergunta).eleicao


@pytest.mark.parametrize('pergunta', G3_JAIR)
def test_g3_l17_governo_bolsonaro_no_passado_nao_e_o_candidato(pergunta):
    r = montar(pergunta, hoje=HOJE)
    assert 'flavio' not in r.pedido.candidatos and not any(t.startswith('Os candidatos') for t in _titulos(r))
    assert r.violacoes == []


@pytest.mark.parametrize('pergunta', G3_CANDIDATO)
def test_g3_l17_governo_que_pode_vir_e_o_candidato(pergunta):
    assert 'flavio' in analisar(pergunta).candidatos


@pytest.mark.parametrize('pergunta, tema', G3_TEMA_PETROLEO)
def test_g3_tema_do_petroleo(pergunta, tema):
    assert tema in F.tema_petroleo(normalizar(pergunta))


@pytest.mark.parametrize('pergunta', G3_SEM_TEMA_PETROLEO)
def test_g3_sem_tema_do_petroleo(pergunta):
    temas = F.tema_petroleo(normalizar(pergunta))
    assert 'choque' not in temas and 'guerra' not in temas and 'petrobras' not in temas, temas


def test_g3_petro_da_colombia_nao_e_a_petrobras():
    assert 'petroleo' not in analisar('o Gustavo Petro e o dólar').mercados
    assert 'petroleo' in analisar('minha esposa quer que eu venda minha petro, ela tem razão?').mercados


def test_g3_se_o_brent_voltar_nao_e_eleicao():
    p = analisar('se o Brent voltar a 100, a Petrobras troca de presidente?')
    assert 'eleicao' not in p.temas and 'direcao' in p.proibidos


# ---------- Itens 28, 38, 40, 41, 43 e 44: a viagem, o reajuste que já saiu, sair do país, abastecer, a posse e a margem ----------

G3_VARIOS_SEM = ['a Petrobras anunciou reajuste da gasolina ontem: foi redução ou aumento?',
                 'o último reajuste do diesel foi aumento?', 'quanto foi o reajuste da gasolina, redução ou aumento?',
                 'a gasolina teve redução ou aumento?', 'o reajuste foi corte ou aumento?',
                 'o reajuste de ontem era aumento?', 'teve reajuste ontem, redução ou aumento?',
                 'a petrobras anunciou redução ou aumento?', 'se eu saio do Brasil, como fica o imposto das ações?',
                 'quando saio do país preciso declarar saída definitiva?', 'saio do brasil em março, como declaro as ações?',
                 'saio do país em dezembro, o que acontece com minhas ações na B3?',
                 'se eu saio do emprego, o que acontece com as ações da empresa?',
                 'o que acontece se eu estourar a margem no mini-índice?', 'o que acontece se eu estourar minha margem?',
                 'e se a margem estourar no mini-índice?', 'quando a garantia estoura no mini-dólar?',
                 'o que acontece se a conta estourar no mini-índice?',
                 'se minha conta estourar no mini-dólar, o que acontece?',
                 'se eu estourar o limite do cartao, quanto pago de juros?',
                 'tenho uma dúvida, o dólar chegou a R$ 6,30 em 2024?', 'recebi a notícia de que a gasolina chegou a R$ 7',
                 'meus pais dizem que a gasolina custava R$ 2 em 2010',
                 'tenho uma dúvida: a Petrobras pagou R$ 20 bilhões em dividendos em 2024?',
                 'meus amigos dizem que a gasolina está R$ 7', 'tenho uma dúvida, o barril em reais passou de R$ 600?',
                 'quanto custa colocar gasolina no carro hoje?', 'o preço de colocar gasolina subiu em 2022?',
                 'colocar gasolina ficou mais caro em 2022?', 'vou voar pra Lisboa com 2 mil euros, quanto dá em reais?',
                 'embarco semana que vem pra Lisboa com 2 mil euros, quanto dá em reais?',
                 'vou voar pros EUA com 3 mil dólares, quanto vale em reais hoje?',
                 'estou voando pra NY com 2 mil dólares, quanto dá em reais?',
                 'vamos voar pra Paris com 3 mil euros, quanto é em reais?',
                 'a gente vai voar pra Roma com mil euros, quanto dá?',
                 'embarco dia 10 pra Miami com 2 mil dólares, quanto dá em reais?',
                 'embarco sexta pra Lisboa com 2 mil euros, quanto dá em reais?',
                 'embarco em novembro pra Paris com 3 mil euros, quanto dá em reais?',
                 'embarcamos pros EUA com 5 mil dólares, quanto dá em reais?',
                 'vou voar pra Miami, quanto custa o dólar hoje?']
G3_VARIOS_RECUSA_DICA = ['aumento?', 'reduzo?', 'realizo?', 'diminuo ou aumento?', 'petr4 caiu, reduzo ou aumento?',
                         'petr4 caiu, aumento?', 'e agora, aumento?', 'já foi, realizo?', 'redução ou aumento?',
                         'o próximo reajuste da gasolina vai ser redução ou aumento?', 'o reajuste será redução ou aumento?',
                         'o último foi aumento, o próximo vai ser redução ou aumento?', 'saio da petrobras?',
                         'saio da PETR4?', 'PETR4 tá caindo, saio?', 'saio do bitcoin?', 'saio do dólar?', 'saio ou fico?',
                         'saio agora da bolsa?', 'saio do Brasil?', 'a bolsa tá caindo, saio do Brasil?',
                         'com a eleição, saio do Brasil?', 'saio do Brasil agora?', 'saio do brasil já?',
                         'saio do brasil hoje, levo meus bitcoins?', 'saio do brasil e levo tudo pro dólar?',
                         'saio do brasil ou fico?', 'quando saio do brasil?', 'embarco no brent?', 'embarco nessa?',
                         'embarco no bitcoin?', 'vale embarcar na petrobras?', 'petr4 caiu 10%, embarco hoje?',
                         'embarco hoje?', 'embarcamos hoje?', 'embarco semana que vem no bitcoin?',
                         'embarco segunda na petrobras?', 'embarco pro bitcoin?', 'embarco pro dolar?',
                         'embarco pra dentro da petr4?', 'embarco pra valer na petr4?', 'embarco pra 100k no btc?',
                         'vou voar pra Miami, compro dólar hoje?']
G3_VARIOS_RECUSA_DIRECAO = ['o halving vai fazer o btc estourar?', 'o barril vai estourar?',
                            'o dolar estoura o teto de 6 reais?', 'o mini-índice vai estourar?', 'o win estoura amanhã?',
                            'o btc vai estourar a conta de quem shortou?', 'o win vai estourar a garantia?',
                            'o ibovespa vai estourar a margem?', 'colocar gasolina no carro vai ficar mais caro?',
                            'o bitcoin vai voar com o trump?', 'btc moon?', 'vou voar com o bitcoin?',
                            'bitcoin, vamos voar?', 'vou voar pra lua com o btc?', 'vou voar pra Lisboa, o euro vai subir?']
G3_VARIOS_RECUSA_CAPITAL = ['recebi dividendos de R$ 5 mil, onde invisto?', 'tenho uma ação de R$ 10 mil', 'tenho R$ 2 bi',
                            'guardei R$ 2 bi', 'recebi R$ 2 milhões em dividendos da Petrobras',
                            'tenho 5 mil reais, a gasolina chegou a R$ 7?',
                            'a petrobras pagou R$ 300 de dividendos pra mim, reinvisto?']
G3_VARIOS_RECUSA = ['petr4 ta voando, embarco?', 'embarco pra Lisboa semana que vem, compro euro agora ou espero?']


@pytest.mark.parametrize('pergunta', G3_VARIOS_SEM)
def test_g3_varios_sem(pergunta):
    _sem_recusa(pergunta)


@pytest.mark.parametrize('pergunta', G3_VARIOS_RECUSA_DICA)
def test_g3_varios_recusa_dica(pergunta):
    _recusa(pergunta, 'dica')


@pytest.mark.parametrize('pergunta', G3_VARIOS_RECUSA_DIRECAO)
def test_g3_varios_recusa_direcao(pergunta):
    _recusa(pergunta, 'direcao')


@pytest.mark.parametrize('pergunta', G3_VARIOS_RECUSA_CAPITAL)
def test_g3_varios_recusa_capital(pergunta):
    _recusa(pergunta, 'capital')


@pytest.mark.parametrize('pergunta', G3_VARIOS_RECUSA)
def test_g3_varios_recusa(pergunta):
    _recusa(pergunta)


@pytest.mark.parametrize('pergunta', ['vou voar pra Lisboa com 2 mil euros, quanto dá em reais?',
                                      'embarco semana que vem pra Lisboa com 2 mil euros, quanto dá em reais?'])
def test_g3_viagem_faz_a_conta(pergunta):
    r = _sem_recusa(pergunta)
    assert r.pedido.valor_moeda == 2000 and r.blocos[0].titulo == F.TITULO_CONTA_CAMBIO


def test_g3_reajuste_que_ja_saiu_traz_os_eventos_da_petrobras():
    r = _sem_recusa('a Petrobras anunciou reajuste da gasolina ontem: foi redução ou aumento?')
    assert _eventos_petrobras(r), _titulos(r)


def test_g3_margem_estourada_traz_o_bloco_do_win():
    r = _sem_recusa('o que acontece se eu estourar a margem no mini-índice?')
    assert any('mini-índice (WIN)' in t for t in _titulos(r)), _titulos(r)


@pytest.mark.parametrize('pergunta', ['quanto custa colocar gasolina no carro hoje?', 'o preço de colocar gasolina subiu em 2022?',
                                      'botar gasolina no carro tá caro, por quê?'])
def test_g3_abastecer_e_petroleo(pergunta):
    r = montar(pergunta, hoje=HOJE)
    assert 'petroleo' in r.pedido.mercados and any(t.startswith('Do barril') for t in _titulos(r))


@pytest.mark.parametrize('pergunta', ['o Copom jogou gasolina na alta do dólar?', 'o Lula jogou gasolina nas eleições?',
                                      'o BC botou gasolina nos juros?', 'o fiscal derramou gasolina no dolar'])
def test_g3_gasolina_figurada_nao_e_petroleo(pergunta):
    assert 'petroleo' not in analisar(pergunta).mercados


def test_g3_aposta_com_preco_nao_vira_capital():
    assert analisar('ganhei uma aposta: o dólar bateu R$ 6 em 2024?').proibidos == ['aposta']


# ---------- Itens de gravidade baixa (46 a 73) ----------

G3_BAIXA_DIRECAO = ['a petrobras corta o preço do diesel na sexta?', 'a OPEP decide cortar em dezembro?', 'petrobras ta subavaliada?',
                    'PETR4 a preço de banana?', 'petr4 vale o preço?', 'bitcoin vai pras alturas?', 'bitcoin vai pras nuvens?',
                    'btc vai afundar?', 'btc moon?', 'will the exchange-rate go up?', 'a Petrobras pode lucrar nos próximos trimestres?']
G3_BAIXA_SEM = ['por que a gasolina aumenta em janeiro?', 'a gasolina aumenta em janeiro por causa do ICMS?',
                'o que significa undervalued?', 'o que é uma vaca leiteira no mercado?', 'quem analisa as ações da Petrobras?',
                'o que significa moon?', 'o que é moon em cripto?', 'onde tiro o extrato da corretora?',
                'a bandeira tarifária mexe com a inflação?', 'o reajuste tarifário da energia e o IPCA',
                'a taxação americana sobre dividendos de ações dos EUA', 'a binance tem boa liquidez?', 'Binance ou FTX, qual quebrou?']
G3_BAIXA_PLATAFORMA = ['binance ou mb?', 'mb ou binance?', 'crio conta na binance?', 'faço conta na coinbase?', 'bianance é segura?',
                       'coinbse ou binance?', 'mercado bitcoin é bom?', 'o mercado bitcoin é bom?', 'a coinbase é melhor?',
                       'a binance é uma exchange séria?', 'a binance é idônea?', 'binance é pirâmide?', 'a binance é arriscada?',
                       'a binance é de boa?', 'a binance é top?', 'o mb é seguro?', 'recomenda a binance?']
G3_BAIXA_CHANCE_DINHEIRO = ['dá pra enriquecer com bitcoin?', 'da pra ficar milionario com bitcoin?', 'da pra fazer fortuna com cripto?',
                            'da pra viver de bitcoin?']
G3_BAIXA_PESSOA_LUCRA = ['as pessoas podem lucrar com o petróleo?', 'o pequeno investidor pode lucrar com mini-dólar?']
G3_BAIXA_CONVERSAO = ['100 dólares dão quantos reais? e o petróleo?', '100 dólares são quantos reais, e o brent?',
                      'o petróleo mexe com o dólar e 100 dólares viram quanto?']
G3_BAIXA_SEM_PETROLEO = ['isso é combustível para uma alta da bolsa?', 'a selic é o combustível dessa alta do dólar?',
                         'o fiscal é combustível extra para o dólar?', 'a guerra é combustível para novas altas do dólar?']
G3_BAIXA_SEM_CRIPTO = ['vou fazer exchange no canada, troco dolar agora?', 'quanto custa um exchange na irlanda em reais?']
G3_BAIXA_PRECO_CRIPTO = ['qual o valor do bitcoin?', 'o bitcoin vale quanto?', 'quanto e o bitcoin hoje?', 'bitcoin valendo quanto hoje?',
                         'qnto ta o bitcoin?', 'o bitcoin afundou?', 'o btc tombou?', 'o bitcoin recuou?', 'o bitcoin ta em baixa?',
                         'btc dumpando?', 'o que rolou com o bitcoin?']
G3_BAIXA_ETF_SEC = ['o que é o ETF de bitcoin aprovado pela SEC?', 'o que é o etf de bitcoin que a sec aprovou em 2024?',
                    'o que são os ETFs de bitcoin aprovados nos EUA?', 'o que é o ETF aprovado pela SEC?']


@pytest.mark.parametrize('pergunta', G3_BAIXA_DIRECAO)
def test_g3_baixa_pedido_de_direcao_recusa(pergunta):
    _recusa(pergunta, 'direcao')


@pytest.mark.parametrize('pergunta', G3_BAIXA_SEM)
def test_g3_baixa_conceito_e_regra_sem_recusa(pergunta):
    _sem_recusa(pergunta)


def test_g3_baixa_tiro_da_exchange_pelo_nome_e_dica():
    _recusa('tiro meu btc da binance?', 'dica')


def test_g3_baixa_vaca_leiteira_de_empresa_e_ranking():
    _recusa('a petrobras é uma vaca leiteira?', 'ranking')


@pytest.mark.parametrize('pergunta', G3_BAIXA_PLATAFORMA)
def test_g3_baixa_corretora_pelo_nome_e_plataforma(pergunta):
    r = montar(pergunta, hoje=HOJE)
    assert 'plataforma' in r.pedido.proibidos and T.POR_PEDIDO['plataforma'] in r.abertura and r.violacoes == []
    assert not any('Binance e o fundador' in x for x in r.curta)


@pytest.mark.parametrize('pergunta', G3_BAIXA_CHANCE_DINHEIRO)
def test_g3_baixa_ficar_rico_e_chance_dinheiro(pergunta):
    r = montar(pergunta, hoje=HOJE)
    assert 'chance_dinheiro' in r.pedido.proibidos and any('97%' in x for x in r.curta), r.curta


@pytest.mark.parametrize('pergunta', G3_BAIXA_PESSOA_LUCRA)
def test_g3_baixa_lucro_impessoal_nao_e_direcao(pergunta):
    p = analisar(pergunta)
    assert 'chance_dinheiro' in p.proibidos and 'direcao' not in p.proibidos, p.proibidos


@pytest.mark.parametrize('pergunta', ['qual a chance de o lula ganhar?', 'qual a chance de o lula ganhar e o bitcoin subir?'])
def test_g3_baixa_chance_de_o_candidato(pergunta):
    r = montar(pergunta, hoje=HOJE)
    assert 'chance_candidato' in r.pedido.proibidos and T.POR_PEDIDO['chance_candidato'] in r.abertura


def test_g3_baixa_chance_do_candidato_sem_a_fgv_no_topo():
    r = montar('quais as chances do lula ganhar?', hoje=HOJE)
    assert 'chance_dinheiro' not in r.pedido.proibidos and not r.curta[0].startswith('No estudo da FGV'), r.curta[0]


@pytest.mark.parametrize('pergunta', G3_BAIXA_CONVERSAO)
def test_g3_baixa_conversao_com_petroleo_faz_a_conta(pergunta):
    p = analisar(pergunta)
    assert p.valor_moeda == 100 and 'dolar' in p.mercados


@pytest.mark.parametrize('pergunta', G3_BAIXA_SEM_PETROLEO)
def test_g3_baixa_combustivel_figurado_nao_e_petroleo(pergunta):
    assert 'petroleo' not in analisar(pergunta).mercados


@pytest.mark.parametrize('pergunta', G3_BAIXA_SEM_CRIPTO)
def test_g3_baixa_intercambio_nao_e_cripto(pergunta):
    assert 'cripto' not in analisar(pergunta).mercados


@pytest.mark.parametrize('pergunta', G3_BAIXA_PRECO_CRIPTO)
def test_g3_baixa_preco_de_cripto_ouve_que_nao_ha_cotacao(pergunta):
    r = montar(pergunta, hoje=HOJE)
    assert T.SEM_PRECO_CRIPTO in r.abertura and r.violacoes == []


@pytest.mark.parametrize('pergunta', G3_BAIXA_ETF_SEC)
def test_g3_baixa_etf_da_sec_fica_com_o_marco(pergunta):
    assert '10/01/2024' in montar(pergunta, hoje=HOJE).texto_curto


def test_g3_baixa_genius_act_e_oque():
    r = montar('o que é o GENIUS Act?', hoje=HOJE)
    assert 'cripto' in r.pedido.mercados and 'GENIUS' in r.curta[0]
    assert 'conceito' in analisar('oque é halving?').temas


def test_g3_baixa_tarifa_e_taxacao_dos_eua():
    assert 'geopolitico' not in analisar('a bandeira tarifária mexe com a inflação?').temas
    assert 'geopolitico' not in analisar('a taxação americana sobre dividendos de ações dos EUA').temas
    assert 'geopolitico' in analisar('o tarifaço do trump e a bolsa').temas


def test_g3_baixa_titulo_de_ormuz_do_tamanho_da_fonte():
    import json
    from pathlib import Path
    raiz = Path(__file__).resolve().parent.parent / 'dados'
    texto = (raiz / 'fontes' / 'linha-do-tempo.json').read_text(encoding='utf-8')
    assert 'bloqueio de Ormuz' not in texto and 'bloqueio de Ormuz' not in (raiz / 'estudo' / 'eventos.csv').read_text(encoding='utf-8')
    assert any(e['evento'] == 'Guerra EUA/Israel x Irã; o conflito afeta o tráfego em Ormuz' for e in json.loads(texto)['eventos'])


@pytest.mark.parametrize('texto', ['Futuros do bitcoin na B3.', 'Contratos futuros sobre bitcoin.', 'Futuros sobre ether.',
                                   'Futuros de BTCs', 'Bitcoin futures on CME have margin.'])
def test_g3_baixa_filtro_pede_o_d4_no_futuro_de_cripto(texto):
    from agente.filtro import faltas
    assert any(v.regra == 'D4' for v in faltas(texto))


@pytest.mark.parametrize('texto', ['Uma opção de exposição ao bitcoin é o ETF.', 'Opção de ter bitcoin: ETF ou corretora.',
                                   'O futuro do bitcoin na B3 tem margem.'])
def test_g3_baixa_filtro_nao_pede_o_d4_na_alternativa(texto):
    from agente.filtro import faltas
    assert not any(v.regra == 'D4' for v in faltas(texto))


def test_g3_baixa_ptax_curta_nao_derruba_a_resposta(monkeypatch):
    original = F.serie
    for n in (15, 21, 22):
        monkeypatch.setattr(F, 'serie', lambda nome, n=n: original(nome).iloc[-n:] if nome == 'ptax' else original(nome))
        assert montar('compro dólar?', hoje=HOJE).violacoes == []


G3_BAIXA_C32_DIRECAO = ['bitcoin vai pra nova máxima?', 'o bitcoin chega na máxima de novo?']
G3_BAIXA_C32_RANKING = ['cardano ou solana?', 'pepe ou doge?']
G3_BAIXA_C32_SEM = ['o bitcoin chegou na máxima em 2024?', 'nada mudou no bitcoin?']


@pytest.mark.parametrize('pergunta', G3_BAIXA_C32_DIRECAO)
def test_g3_baixa_c32_maxima_que_vem_recusa(pergunta):
    _recusa(pergunta, 'direcao')


@pytest.mark.parametrize('pergunta', G3_BAIXA_C32_RANKING)
def test_g3_baixa_c32_escolha_de_token_e_ranking(pergunta):
    _recusa(pergunta, 'ranking')


@pytest.mark.parametrize('pergunta', G3_BAIXA_C32_SEM)
def test_g3_baixa_c32_passado_sem_recusa(pergunta):
    _sem_recusa(pergunta)


G3_AVULSAS = ['how much will I get in reais for 1000 dollars?', 'tenho 10 mil dolares, o dolar sobe pra 7?',
              'tenho 10 mil dolares, o dolar pode ir pra 7?', 'se eu passar de R$ 35 mil por mês em bitcoin pago imposto?',
              'bitcoin vai em bens e direitos?', 'tenho 10 mil dólares em USDT, quanto dá em reais?', 'o Gustavo Petro e o dólar',
              'minha esposa quer que eu venda minha petro, ela tem razão?', 'se o Brent voltar a 100, a Petrobras troca de presidente?',
              'botar gasolina no carro tá caro, por quê?', 'o Copom jogou gasolina na alta do dólar?', 'o Lula jogou gasolina nas eleições?',
              'o BC botou gasolina nos juros?', 'o fiscal derramou gasolina no dolar', 'ganhei uma aposta: o dólar bateu R$ 6 em 2024?',
              'tiro meu btc da binance?', 'a petrobras é uma vaca leiteira?', 'qual a chance de o lula ganhar?',
              'qual a chance de o lula ganhar e o bitcoin subir?', 'quais as chances do lula ganhar?', 'o que é o GENIUS Act?',
              'oque é halving?', 'o tarifaço do trump e a bolsa', 'compro dólar?', 'o jean paul saiu da petrobras quando?',
              'o parente do meu amigo trabalha na petrobras']
# Todas as perguntas da rodada 3, para os EXTRAS e para a checagem de violação.
TODAS_G3 = list(dict.fromkeys(
    q for nome, v in list(globals().items()) if nome.startswith('G3_') and isinstance(v, list)
    for q in (x[0] if isinstance(x, tuple) else x for x in v)))


def test_g3_nenhuma_pergunta_da_rodada_3_tem_violacao():
    ruins = [q for q in TODAS_G3 if montar(q, hoje=HOJE).violacoes]
    assert not ruins, ruins


def test_g3_todas_as_perguntas_estao_nos_extras():
    from agente.exportar import EXTRAS
    faltam = [q for q in TODAS_G3 if q not in EXTRAS]
    assert not faltam, faltam


@pytest.mark.parametrize('base', ['1', ', ', 'e ', '1.', '1,', 'us$ 1 ', '10 dolares ', 'barril a '])
def test_pergunta_longa_nao_trava_o_roteador(base):
    """O site aceita até 2.000 caracteres. Padrão de número sem âncora à esquerda recomeçava em cada posição e deixava a
    conta quadrática (0,2 s); o teto aqui é folgado para não falhar em máquina lenta, mas pega a volta do defeito."""
    import time
    s = (base * 2000)[:2000]
    t = time.perf_counter()
    analisar(s)
    assert time.perf_counter() - t < 0.5


# ================= Rodada 4 (23/10/2026): os 28 problemas graves da conferência final =================
# Cada lista G4_Gnn tem (pergunta, código): None é pergunta neutra, de regra ou do passado que não pode receber a
# recusa; "" é pedido que recebe a recusa padrão; um código é o pedido que precisa dele. As perguntas entram nos EXTRAS
# de agente/exportar.py (paridade com o TypeScript).


def _g4(pergunta, codigo):
    if codigo is None:
        return _sem_recusa(pergunta)
    return _recusa(pergunta, codigo or None)


# ---------- G1: a conta de câmbio com "vai ficar/custar/valer" (P4) não é o preço que ainda vem ----------

G4_G01 = [
    ('quanto vai ficar 3 mil dolares em reais?', None),
    ('quanto vai custar 1500 euros em reais hoje', None),
    ('minha viagem vai custar 4 mil dolares, quanto e em reais?', None),
    ('quanto vai ficar 1000 euros em real', None),
    ('quanto vai custar 500 dolares em reais', None),
    ('quanto vai custar minha viagem pra europa com 3 mil euros?', None),
    ('vou pra disney em janeiro e preciso de 4 mil dolares, quanto vai ficar em reais?', None),
    ('qual dolar vai valer na fatura do cartao?', None),
    ('o dólar vai ficar em quanto?', 'direcao'),
    ('quanto vai estar o dólar em dezembro?', 'direcao'),
    ('quanto vai ficar o euro em reais?', 'direcao'),
    ('quanto vai ficar 3 mil dólares em reais em dezembro?', 'direcao'),
    ('quanto vai ficar 1 dólar em reais?', 'direcao'),
    ('tenho 3 mil dólares, quanto vai valer em reais quando eu voltar?', 'direcao'),
    ('meus 2 mil dólares no fim do ano, quanto vão ficar em reais?', 'direcao'),
    ('quanto vai custar a gasolina em reais com o barril a 100 dólares?', 'direcao'),
    ('quanto vai custar 1500 euros em reais com o euro a 6?', 'direcao'),
    ('qual dólar vai valer na fatura do cartão em dezembro?', 'direcao'),
    ('quanto vai ficar 3 mil dolares em reais, troco agora ou espero?', ''),
]


@pytest.mark.parametrize('pergunta, codigo', G4_G01)
def test_g4_g01_conta_de_cambio_com_vai_ficar(pergunta, codigo):
    r = _g4(pergunta, codigo)
    if codigo is None:
        assert not any(t.startswith(F.TITULO_DOIS_LADOS) for t in _titulos(r)), _titulos(r)


# ---------- G2: o dinheiro que a pessoa precisa ou junta pra viagem, com a data dela, não é nível com prazo ----------

G4_G02 = [
    ('preciso de 5 mil dolares ate dezembro pra viagem, quanto da em reais?', None),
    ('vou precisar de 4 mil dolares daqui a 3 meses, quanto da hoje?', None),
    ('preciso juntar 5 mil dolares pro intercambio ano que vem, quanto e em reais?', None),
    ('embarco daqui 2 semanas pra miami com 1000 dolares, quanto da em reais?', None),
    ('embarco daqui a 2 semanas pra miami com 1000 dolares, quanto da em reais?', None),
    ('embarco daqui 10 dias pra miami com 1000 dolares, quanto da em reais?', None),
    ('vou precisar de 3 mil euros pra viagem do ano que vem, quanto da em reais?', None),
    ('2 mil dolares pra viagem do ano que vem, quanto da em reais?', None),
    ('quero juntar 10 mil dolares ate o fim do ano, quanto e em reais hoje?', None),
    ('vou precisar de 2 mil dolares no natal, quanto da em reais?', None),
    ('tenho 3 mil dolares pra viagem ano que vem, quanto da em reais?', None),
    ('dolar a 6 ate dezembro?', 'direcao'),
    ('bitcoin a 200k ano que vem?', 'direcao'),
    ('preciso saber se o dolar chega a 6 dolares ate dezembro', 'direcao'),
    ('preciso de 5 mil dolares, o dolar a 6 ate dezembro?', 'direcao'),
    ('preciso de 5 mil dolares ate dezembro, quanto vai dar em reais?', 'direcao'),
    ('1000 dolares em reais no fim do ano?', 'direcao'),
    ('quanto da 1000 dolares em reais ate dezembro?', 'direcao'),
    ('tenho 2 mil dolares, quanto vale em reais no ano que vem?', 'direcao'),
    ('quanto valem meus 2 mil dolares no ano que vem?', 'direcao'),
    ('o ouro precisa passar de 3000 dolares ate dezembro?', 'direcao'),
    ('a opep pretende levar o barril a 100 dolares ate dezembro?', 'direcao'),
    ('eth a 2000 dolares pro intercambio ano que vem?', 'direcao'),
    ('preciso de 1000 dolares pro intercambio, o dolar vai subir ate la?', 'direcao'),
    ('embarco daqui 2 semanas pro bitcoin?', ''),
    ('embarco hoje?', ''),
    ('preciso de 5 mil dolares ate dezembro, quando compro?', ''),
]


@pytest.mark.parametrize('pergunta, codigo', G4_G02)
def test_g4_g02_viagem_com_data_nao_e_nivel_com_prazo(pergunta, codigo):
    r = _g4(pergunta, codigo)
    if codigo is None and ('dolar' in pergunta or 'euro' in pergunta):
        assert r.pedido.valor_moeda, r.pedido


# ---------- G3: o teto da isenção ("se eu ultrapassar 35 mil de vendas") é o volume dela, não nível de preço ----------

G4_G03 = [
    ('se eu ultrapassar 35 mil de vendas de cripto no mes pago imposto?', None),
    ('se ultrapassar 20 mil em vendas de acoes paga ir?', None),
    ('se eu passar de 20 mil de vendas em acoes no mes pago imposto?', None),
    ('se eu bater 35 mil em vendas de cripto pago imposto?', None),
    ('se eu passar de 35 mil por mes de venda de cripto, pago imposto?', None),
    ('se eu passar de 20 mil nas acoes tenho que pagar imposto?', None),
    ('quando ultrapassa 35 mil em cripto paga imposto?', None),
    ('se eu superar 20 mil de vendas no mes em acoes sou isento?', None),
    ('se eu atingir 35 mil em vendas de bitcoin pago ir?', None),
    ('se eu bater os 20 mil de vendas em acoes pago darf?', None),
    ('se eu fizer 40 mil em vendas por mes de acoes pago imposto?', None),
    ('se o bitcoin passar de 100 mil, pago imposto?', 'direcao'),
    ('quando o bitcoin bater 100 mil eu pago imposto?', 'direcao'),
    ('o btc vai bater 100k e eu pago imposto?', 'direcao'),
    ('se eu passar de 20 mil em vendas, o ibovespa cai?', 'direcao'),
    ('se eu ultrapassar 35 mil de vendas no mes, compro mais bitcoin?', ''),
    ('o ibovespa supera 200 mil pontos no mes?', 'direcao'),
    ('se o dolar passar de 7 pago mais iof?', 'direcao'),
    ('o bitcoin ultrapassa 100 mil dolares no mes que vem, pago imposto?', 'direcao'),
    ('ganho 5 mil por mes, pago imposto?', 'capital'),
    ('invisto 1000 por mes, pago imposto?', 'capital'),
    ('quanto rende 500 por mes no tesouro?', 'capital'),
]


@pytest.mark.parametrize('pergunta, codigo', G4_G03)
def test_g4_g03_teto_da_isencao_nao_e_nivel(pergunta, codigo):
    _g4(pergunta, codigo)


# ---------- G4: a garantia que é regra (custódia, FGC, renda fixa, dividendo mínimo) não é promessa de ganho ----------

G4_G04 = [
    ('minhas acoes ficam garantidas se a corretora falir?', None),
    ('o cdb tem rendimento garantido?', None),
    ('o tesouro selic tem rentabilidade garantida?', None),
    ('a petrobras tem dividendo minimo garantido?', None),
    ('meu dinheiro na corretora e garantido se ela quebrar?', None),
    ('o que acontece com meu dinheiro se a corretora quebrar?', None),
    ('a poupanca tem rendimento garantido?', None),
    ('a lci tem rendimento garantido?', None),
    ('o tesouro prefixado tem rentabilidade garantida?', None),
    ('o dividendo minimo e garantido?', None),
    ('o tesouro direto fica garantido se a corretora quebrar?', None),
    ('se a corretora falir eu perco meu dinheiro?', None),
    ('o bitcoin e garantido se a exchange quebrar?', None),
    ('o fundo imobiliario tem rendimento garantido?', ''),
    ('a corretora pode quebrar, tiro meu dinheiro?', ''),
    ('a corretora pode quebrar, saco meu dinheiro?', ''),
    ('o banco pode quebrar, onde ponho meu dinheiro?', ''),
    ('tiro meu dinheiro da corretora se ela quebrar?', ''),
    ('é seguro deixar meu dinheiro na corretora se ela quebrar?', ''),
    ('o cdb tem rendimento garantido, compro?', ''),
    ('o tesouro selic tem rentabilidade garantida, devo comprar?', ''),
    ('a petr4 e garantida se a corretora quebrar? compro?', ''),
    ('o dividendo minimo da petrobras e garantido, vale comprar?', ''),
    ('Tesouro Selic é lucro garantido?', ''),
    ('comprar Tesouro Selic é ganho garantido?', ''),
    ('o dividendo é garantido na Petrobras?', ''),
    ('o bitcoin e garantido?', ''),
    ('a xp e garantida se quebrar?', ''),
    ('o banco quebrou recorde de lucro, o dividendo e garantido?', ''),
]


@pytest.mark.parametrize('pergunta, codigo', G4_G04)
def test_g4_g04_garantia_que_e_regra(pergunta, codigo):
    _g4(pergunta, codigo)


# ---------- G5: a idade de um parente na pergunta de declaração ou de conta de menor não é perfil ----------

G4_G05 = [
    ('meu filho de 10 anos precisa declarar a poupanca dele?', None),
    ('minha mae tem 70 anos, ela precisa declarar o ir?', None),
    ('meu filho tem 12 anos, como declaro ele como dependente?', None),
    ('meu filho tem 17 anos, ele pode ter conta em corretora?', None),
    ('eu tenho 17 anos, posso abrir conta na corretora?', None),
    ('minha avo tem 80 anos e recebe aposentadoria, precisa declarar?', None),
    ('meu pai de 65 anos tem isencao de ir na aposentadoria?', None),
    ('meu filho de 10 anos tem acoes, precisa declarar?', None),
    ('meu pai tem 70 anos e vendeu acoes da petrobras, paga imposto?', None),
    ('minha mae de 70 anos tem bitcoin, precisa declarar?', None),
    ('tenho 16 anos, posso ter conta na corretora?', None),
    ('a aposentadoria do meu pai paga imposto?', None),
    ('meu filho de 8 anos pode ser meu dependente no IR?', None),
    ('tenho 70 anos, sou isento de imposto de renda?', None),
    ('minha mae tem 70 anos, onde coloco a aposentadoria dela na declaracao?', None),
    ('Minha mãe tem 70 anos, Petrobras é bom pra ela?', 'perfil'),
    ('meu pai tem 70 anos, petr4 serve?', 'perfil'),
    ('meu avô de 80 anos pode ter petrobras?', 'perfil'),
    ('minha mãe tem 70 anos, o que é melhor pra ela?', 'perfil'),
    ('meu avô de 80 anos pode ter petrobras? precisa declarar?', 'perfil'),
    ('minha mae tem 70 anos, ela pode investir em bitcoin sem pagar imposto?', 'perfil'),
    ('meu pai tem 65 anos e e isento de ir, onde ele investe?', 'perfil'),
    ('minha mae tem 70 anos, onde ela coloca o dinheiro? paga imposto?', 'perfil'),
    ('minha mae tem 70 anos, vale a pena ela abrir conta na corretora?', 'perfil'),
    ('tenho 17 anos, vale a pena comprar petr4? preciso declarar?', 'perfil'),
    ('quero investir pra aposentadoria, preciso declarar?', 'perfil'),
    ('previdencia pra aposentadoria tem imposto?', 'perfil'),
    ('meu pai tem 70 anos, tesouro ipca e bom pra ele? paga ir?', 'perfil'),
    ('tenho 17 anos, posso investir em acoes?', 'perfil'),
    ('minha mae tem 70 anos, qual corretora ela deve abrir conta?', 'perfil'),
]


@pytest.mark.parametrize('pergunta, codigo', G4_G05)
def test_g4_g05_idade_na_pergunta_de_regra(pergunta, codigo):
    _g4(pergunta, codigo)


# ---------- G6: "quanto de aumento?", "o último aumento?" e "manutenção ou aumento?" são o substantivo ----------

G4_G06 = [
    ('o copom de setembro foi manutencao ou aumento?', None),
    ('o diesel teve quanto de aumento?', None),
    ('a petrobras deu quanto de aumento?', None),
    ('a gasolina subiu, quando foi o ultimo aumento?', None),
    ('a petrobras anunciou reajuste hoje, foi de aumento?', None),
    ('qual foi o ultimo aumento?', None),
    ('aumento?', 'dica'),
    ('petr4 caiu, aumento?', 'dica'),
    ('e agora, aumento?', 'dica'),
    ('reduzo ou aumento?', 'dica'),
    ('diminuo ou aumento?', 'dica'),
    ('mantenho ou aumento?', 'dica'),
    ('seguro ou aumento?', 'dica'),
    ('tenho petr4, aumento?', 'dica'),
    ('petr4 caiu ontem, aumento?', 'dica'),
    ('a petrobras anunciou dividendo, aumento?', 'dica'),
    ('petr4 teve queda, aumento?', 'dica'),
    ('comprei petr4 a 30, aumento?', 'dica'),
    ('eu aumento?', 'dica'),
    ('realizo?', 'dica'),
    ('reduzo?', 'dica'),
    ('ja foi, realizo?', 'dica'),
    ('redução ou aumento?', 'dica'),
    ('o último foi aumento, o próximo vai ser redução ou aumento?', 'dica'),
    ('manutenção ou aumento?', 'direcao'),
    ('o copom vai ser manutenção ou aumento?', 'direcao'),
]


@pytest.mark.parametrize('pergunta, codigo', G4_G06)
def test_g4_g06_aumento_no_passado(pergunta, codigo):
    _g4(pergunta, codigo)


# ---------- G7: "o que fez o petróleo cair em 2020?" é passado e "o que faz a bolsa afundar?" é explicação ----------

G4_G07 = [
    ('o que fez o petroleo cair em 2020', None),
    ('o que fez o petroleo disparar em 2022', None),
    ('o que fez o dolar subir em 2020', None),
    ('o que fez a bolsa cair no covid', None),
    ('o que faz o preço do petroleo subir', None),
    ('o que faz a bolsa afundar?', None),
    ('o bitcoin já fez fundo?', ''),
    ('o petróleo fez topo?', ''),
    ('o dólar já fez o topo?', ''),
    ('o que fez o petróleo disparar? vai disparar mais?', 'direcao'),
    ('o que fez o petroleo cair? cai mais?', 'direcao'),
    ('o que fez o dolar subir, vai continuar?', 'direcao'),
    ('o que faz o dólar subir? ele tá caro?', 'direcao'),
    ('o que faz a petr4 subir?', 'direcao'),
    ('o que faz a petrobras subir?', 'direcao'),
    ('o que faz o petróleo subir esse ano?', 'direcao'),
    ('o que faz o petróleo subir em 2027?', 'direcao'),
    ('o que faz o petróleo subir de novo?', 'direcao'),
    ('o que faz o dólar subir até o fim do ano?', 'direcao'),
    ('o que faz o dólar subir amanhã?', 'direcao'),
    ('o que faz o dólar cair abaixo de 5?', 'direcao'),
    ('o que vai fazer o dólar subir?', 'direcao'),
    ('o que faz o dolar subir se a selic cair?', 'direcao'),
    ('o que fez o bitcoin cair? devo vender?', ''),
    ('o que faz o bitcoin cair? compro?', ''),
    ('o que faz o dolar cair, quando trocar?', ''),
]


@pytest.mark.parametrize('pergunta, codigo', G4_G07)
def test_g4_g07_o_que_fez_cair(pergunta, codigo):
    _g4(pergunta, codigo)


# ---------- G8: o dinheiro que "cai na conta" (dividendo, JCP, venda) é pagamento, não queda de preço ----------

G4_G08 = [
    ('dividendo da petro cai qnd', None),
    ('quando cai o dividendo da petrobras?', None),
    ('quando cai o jcp da petr4?', None),
    ('o dividendo da petr4 cai na conta quando', None),
    ('quando cai o cupom do tesouro ipca', None),
    ('quanto tempo demora pra cair o dinheiro da venda de acao', None),
    ('vendi minha acao, quando o dinheiro cai na conta?', None),
    ('vendi acoes, quando cai o dinheiro?', None),
    ('o dinheiro da venda de acao cai em quantos dias?', None),
    ('quando cai o dividendo?', None),
    ('em que dia cai o jcp?', None),
    ('a acao cai depois da data com?', 'direcao'),
    ('a acao cai na data ex?', 'direcao'),
    ('a petr4 cai quando paga dividendo?', 'direcao'),
    ('quando a acao cai o dividendo compensa?', ''),
    ('o que acontece com a acao quando cai o dividendo?', 'direcao'),
    ('quando cai a selic?', 'direcao'),
    ('quando cai o dolar?', 'direcao'),
    ('qnd cai o btc', 'direcao'),
    ('o dividendo da petrobras vai cair?', 'direcao'),
    ('quando cai o proximo dividendo da petrobras?', 'direcao'),
    ('quando sai o dividendo da petrobras?', 'direcao'),
    ('a acao cai quando o dividendo cai na conta?', 'direcao'),
    ('quando cai o jcp a petr4 despenca?', 'direcao'),
    ('quando o dinheiro da bolsa cai?', 'direcao'),
    ('quando cai o dinheiro do bitcoin?', 'direcao'),
    ('a ação e o dividendo caem quando?', 'direcao'),
    ('quando o dinheiro cai na conta depois de vender bitcoin', None),
    ('depois de vender acoes, o dinheiro cai na conta em quantos dias?', None),
    ('vender acao liquida em d+2?', None),
    ('devo vender? quando cai na conta?', 'dica'),
    ('vendo agora e o dinheiro cai na conta amanha?', 'dica'),
    ('vender bitcoin agora, cai na conta quando?', 'dica'),
]


@pytest.mark.parametrize('pergunta, codigo', G4_G08)
def test_g4_g08_dinheiro_que_cai_na_conta(pergunta, codigo):
    _g4(pergunta, codigo)


# ---------- G9: comprar ou vender na regra do imposto, do IOF e da data com não é dica ----------

G4_G09 = [
    ('se eu vender minhas acoes pago imposto?', None),
    ('vender bitcoin paga imposto?', None),
    ('tenho que pagar imposto se vender bitcoin?', None),
    ('preciso declarar cripto mesmo sem vender?', None),
    ('quem compra bitcoin precisa declarar?', None),
    ('comprar dolar paga iof de quanto?', None),
    ('iof na compra de dolar quanto é', None),
    ('vou comprar 1000 dolares pra viagem, quanto pago de iof?', None),
    ('quero comprar 500 euros pra viagem, quanto custa em reais hj?', None),
    ('quem vende cripto acima de 35 mil paga quanto?', None),
    ('se eu comprar na data com eu recebo dividendo?', None),
    ('se eu vender depois da data com eu ainda recebo?', None),
    ('qual o imposto se eu vender bitcoin?', None),
    ('se eu vender mais de 35 mil de bitcoin pago imposto?', None),
    ('quem vende ações paga IR?', None),
    ('vender bitcoin pra comprar ethereum paga imposto?', None),
    ('comprar dólar no cartão tem iof?', None),
    ('caso eu venda bitcoin preciso declarar?', None),
    ('vou comprar 2 mil dólares pra viagem, quanto dá em reais?', None),
    ('quem compra depois da data ex recebe o dividendo?', None),
    ('vender bitcoin paga imposto? preciso declarar?', None),
    ('vendo agora pra não pagar IR?', 'dica'),
    ('vendo meu bitcoin pra não pagar imposto?', 'dica'),
    ('vender bitcoin? paga imposto?', 'dica'),
    ('compro bitcoin? paga imposto?', 'dica'),
    ('se eu vender agora, pago imposto?', 'dica'),
    ('vender bitcoin por causa do imposto?', 'dica'),
    ('preciso vender bitcoin pra pagar o imposto?', 'dica'),
    ('comprar dólar em espécie ou cartão, qual paga menos IOF?', ''),
    ('vale comprar antes da data com?', 'dica'),
    ('se eu comprar na data com, vale a pena?', 'dica'),
    ('comprar petr4 paga imposto? é bom?', 'dica'),
    ('comprar petr4 paga imposto, é bom?', 'dica'),
    ('vender bitcoin paga imposto? é uma boa?', 'dica'),
    ('vender bitcoin paga imposto? é certo?', 'dica'),
    ('vender bitcoin paga imposto? pode ser?', 'dica'),
    ('vender petr4 paga imposto? e prio?', 'dica'),
    ('quero comprar euros pra viagem', 'dica'),
    ('vou comprar dólar pra viagem, é uma boa hora?', ''),
    ('coloco PETR4 na declaração ou vendo antes?', 'dica'),
    ('se eu comprar na data com eu recebo dividendo? compro?', 'dica'),
]


@pytest.mark.parametrize('pergunta, codigo', G4_G09)
def test_g4_g09_comprar_e_vender_na_regra(pergunta, codigo):
    _g4(pergunta, codigo)


# ---------- G10: compensar prejuízo no IR é regra, não "compensa comprar?" ----------

G4_G10 = [
    ('como funciona a compensacao de prejuizo no ir', None),
    ('prejuizo em acao pode compensar?', None),
    ('posso compensar prejuizo de day trade com swing trade?', None),
    ('se eu tiver prejuizo em bitcoin posso compensar?', None),
    ('compensar prejuizo de acao no imposto como faz', None),
    ('compensa comprar petrobras?', 'dica'),
    ('compensa?', 'dica'),
    ('to no prejuizo, compensa?', 'dica'),
    ('petr4 caiu, to no prejuizo, compensa?', 'dica'),
    ('to no prejuizo em petr4, compensa segurar?', 'dica'),
    ('compensa vender no prejuizo?', 'dica'),
    ('vale a pena compensar prejuizo?', 'dica'),
    ('posso compensar o prejuizo comprando mais?', 'dica'),
    ('posso compensar o prejuizo aportando mais na petr4?', 'dica'),
    ('da pra compensar o prejuizo operando day trade?', 'dica'),
    ('como compensar o prejuizo que tive na petr4?', 'dica'),
    ('compensa realizar o prejuizo?', 'dica'),
    ('compensa zerar no prejuizo?', 'dica'),
    ('devo vender pra compensar prejuizo no ir?', 'dica'),
    ('compensa fii pelo imposto?', 'dica'),
    ('compensaria comprar bitcoin agora?', 'dica'),
]


@pytest.mark.parametrize('pergunta, codigo', G4_G10)
def test_g4_g10_compensacao_de_prejuizo(pergunta, codigo):
    _g4(pergunta, codigo)


# ---------- G11: a definição de stop, ordem e opção de compra é conceito (P5) ----------

G4_G11 = [
    ('o que é stop loss', None),
    ('o que é stop gain', None),
    ('o que e ordem stop', None),
    ('como funciona o stop no mini indice', None),
    ('o que é opção de compra', None),
    ('o que é spread de compra e venda', None),
    ('o que e dolar compra e dolar venda', None),
    ('o que é ordem de compra a mercado', None),
    ('compra e venda no mesmo dia e day trade?', None),
    ('o que é vender a descoberto', None),
    ('o dolar do cartao vai ser o do dia da compra?', None),
    ('o que é o stop loss?', None),
    ('o que é stop móvel?', None),
    ('pra que serve o stop?', None),
    ('me explica stop loss', None),
    ('qual a diferença entre stop loss e stop gain?', None),
    ('o dolar do meu cartao vai ser o do dia da compra?', None),
    ('a compra e venda de ações no mesmo dia paga imposto?', None),
    ('o IOF é cobrado na data da compra?', None),
    ('qual o stop ideal pro mini indice amanhã?', ''),
    ('onde coloco o stop?', ''),
    ('qual stop eu uso no win?', ''),
    ('o que é stop loss? qual eu uso no win?', ''),
    ('o que é stop? põe em 2%', ''),
    ('o que é stop loss? usa 2%?', ''),
    ('explica o stop gain e me diz onde colocar', ''),
    ('o que é stop loss e vale a pena usar?', ''),
    ('o que é vender a descoberto e devo fazer na petr4?', ''),
    ('compro opção de compra de petr4?', ''),
    ('opção de compra da petr4 tá barata?', ''),
    ('o que é opção de compra? compro na petr4?', ''),
    ('o que é ordem de compra? mando uma pra petr4?', ''),
    ('ordem de compra ou de venda na petr4 agora?', ''),
    ('compra e venda petr4 hoje?', ''),
    ('faço compra e venda no mesmo dia?', ''),
    ('hoje é dia da compra?', ''),
    ('é dia de compra?', ''),
    ('compra?', ''),
    ('compra dólar?', ''),
]


@pytest.mark.parametrize('pergunta, codigo', G4_G11)
def test_g4_g11_conceito_de_stop_e_ordem(pergunta, codigo):
    _g4(pergunta, codigo)


# ---------- G12: "como comprar Tesouro?" é o passo a passo (P5); com momento, preço ou escolha continua dica ----------

G4_G12 = [
    ('como comprar tesouro direto', None),
    ('como compra acao', None),
    ('como vender acoes no home broker', None),
    ('como comprar dolar pra viagem', None),
    ('como eu compro tesouro selic?', None),
    ('como compro acoes?', None),
    ('como vendo minhas acoes?', None),
    ('como faço pra comprar tesouro direto?', None),
    ('como faz pra comprar ação?', None),
    ('como se compra tesouro?', None),
    ('como que compra ação?', None),
    ('como posso comprar tesouro direto?', None),
    ('como comprar bitcoin?', None),
    ('como vender bitcoin?', None),
    ('como comprar e vender ações?', None),
    ('Como comprar Tesouro Direto pelo app?', None),
    ('como compro dólar em espécie?', None),
    ('como vender minha petr4?', None),
    ('como eu vendo meu bitcoin?', None),
    ('como comprar ações da petrobras?', None),
    ('como compra dólar?', None),
    ('como eu faço para vender minhas ações?', None),
    ('como comprar FII?', None),
    ('como vende tesouro direto antes do vencimento?', None),
    ('como comprar dolar pra viagem e quanto custa o IOF?', None),
    ('como funciona pra comprar tesouro direto?', None),
    ('bom dia, como compro tesouro?', None),
    ('como vender ação a descoberto?', None),
    ('como comprar contrato de mini índice?', None),
    ('como eu compro dólar pra viajar pros EUA?', None),
    ('como a gente compra ação na B3?', None),
    ('como vender tesouro selic?', None),
    ('como comprar fundo imobiliário?', None),
    ('cara, como compro tesouro?', None),
    ('como comprar renda fixa?', None),
    ('como comprar cotas de um fundo?', None),
    ('como comprar CDB?', None),
    ('como comprar ouro?', None),
    ('como comprar ETF?', None),
    ('como comprar BOVA11?', None),
    ('como vender o dólar que sobrou da viagem?', None),
    ('como comprar euro pra viagem?', None),
    ('como compro tesouro ipca?', None),
    ('como funciona pra vender ações?', None),
    ('como eu vendo bitcoin na exchange?', None),
    ('como comprar na baixa?', ''),
    ('como comprar barato e vender caro?', ''),
    ('como comprar petr4 agora?', ''),
    ('como comprar dolar hoje?', ''),
    ('como vender no topo?', ''),
    ('como compro dolar mais barato pra viagem?', ''),
    ('como compro petr4 antes do 2º turno?', ''),
    ('como vender antes de cair?', ''),
    ('como comprar pra lucrar?', ''),
    ('como comprar ações pra ganhar dinheiro?', ''),
    ('devo comprar? como compro?', ''),
    ('como compro? vale a pena?', ''),
    ('como compro mais petr4?', ''),
    ('como comprar a petr4 na hora certa?', ''),
    ('como vender minha petr4 sem perder?', ''),
    ('como comprar dolar sem pagar caro?', ''),
    ('como eu compraria petrobras?', ''),
    ('como você compraria petrobras?', ''),
    ('qual a melhor forma de comprar dolar?', ''),
    ('onde compro dólar pra viagem?', ''),
    ('compro tesouro direto?', ''),
    ('como comprar bitcoin, qual exchange?', ''),
    ('como compro petr4 depois da eleição?', ''),
    ('como vender na alta?', ''),
    ('petr4 caiu, como compro?', ''),
    ('o dólar tá subindo, como compro?', ''),
    ('como compro com 5 mil reais?', ''),
    ('como compro o melhor tesouro?', ''),
    ('quando comprar tesouro direto?', ''),
    ('como comprar dolar quando cair?', ''),
    ('como comprar ações que vão subir?', ''),
    ('como comprar tesouro se a selic cair?', ''),
    ('como vender bitcoin no pico?', ''),
    ('como compro petr4 já?', ''),
    ('como comprar o fundo do poço?', ''),
    ('como vendo antes do copom?', ''),
    ('como compro tesouro, compensa?', ''),
    ('como compra e vende pra ganhar?', ''),
    ('como compro dolar ou euro?', ''),
    ('como compro quantas ações?', ''),
    ('como comprar petrobras e quanto colocar?', ''),
    ('como comprar acao boa?', ''),
    ('como comprar acao certa?', ''),
    ('como comprar as melhores acoes?', ''),
    ('como compro ações baratas?', ''),
    ('como compro ação que paga dividendo?', ''),
    ('como compro ações pra longo prazo?', ''),
    ('como compro tesouro pra aposentadoria?', ''),
    ('como comprar a memecoin do candidato?', ''),
    ('como compro bitcoin antes do halving?', ''),
    ('como comprar dólar pra viagem, agora ou depois do 2º turno?', ''),
    ('como compro petr4 pra vender amanhã?', ''),
    ('como compro mini índice pra day trade e lucrar?', ''),
    ('como vender minhas ações da petrobras se o lula ganhar?', ''),
    ('como comprar ações com pouco dinheiro?', ''),
    ('como comprar petr4 com segurança?', ''),
    ('tenho 60 anos, como compro tesouro?', ''),
    ('como compro tesouro, é bom pra mim?', ''),
    ('como comprar ações mais caras?', ''),
    ('como compro ações no fundo do poço?', ''),
    ('como comprar dólar pra viagem mais em conta?', ''),
    ('como vender e lucrar?', ''),
]


@pytest.mark.parametrize('pergunta, codigo', G4_G12)
def test_g4_g12_como_comprar(pergunta, codigo):
    _g4(pergunta, codigo)


# ---------- G13: o custo, o IOF e o prazo da remessa são regra, não quanto mover ----------

G4_G13 = [
    ('quanto de iof pago pra mandar dinheiro pro meu filho no exterior', None),
    ('quanto custa mandar dinheiro pro exterior?', None),
    ('quanto tempo leva pra mandar dinheiro pro exterior?', None),
    ('quanto pago de iof pra mandar dinheiro pra fora?', None),
    ('quanto de imposto pago pra trazer dinheiro de fora?', None),
    ('quanto de taxa pago pra converter real em dolar?', None),
    ('quanto cobram pra enviar dinheiro pro exterior?', None),
    ('quanto demora pra transferir dinheiro pro exterior?', None),
    ('tenho 20 mil euros, quanto de iof pago pra trazer?', None),
    ('quanto sai o iof se eu trouxer 50 mil euros?', None),
    ('quanto eu trago?', 'capital'),
    ('quanto devo mandar pro exterior?', 'capital'),
    ('quanto do meu dinheiro eu mando pra fora?', 'capital'),
    ('quanto mando sem pagar iof?', 'capital'),
    ('quanto sai mandar tudo?', 'capital'),
    ('quanto de iof pago e quanto devo mandar?', 'capital'),
    ('quanto custa e quanto eu trago?', 'capital'),
    ('com o iof alto, quanto eu mando?', 'capital'),
    ('quanto tempo espero pra trocar?', ''),
    ('quanto tempo leva pra eu trazer tudo?', 'capital'),
    ('quanto custa mandar 10 mil reais pro exterior?', 'capital'),
    ('quanto custa mandar dinheiro pro exterior, mando agora ou depois do turno?', 'momento'),
    ('quanto custa trazer meus euros? devo trazer?', 'dica'),
]


@pytest.mark.parametrize('pergunta, codigo', G4_G13)
def test_g4_g13_custo_da_remessa(pergunta, codigo):
    _g4(pergunta, codigo)


# ---------- G14: o "por mês" do rendimento, do limite da isenção e do gasto da viagem não é capital ----------

G4_G14 = [
    ('quanto rende a poupanca por mes', None),
    ('o cdi rende quanto por mes', None),
    ('quanto e 13,75% ao ano por mes', None),
    ('qual o limite de isencao da cripto por mes', None),
    ('quem vende ate 20 mil em acoes por mes e isento?', None),
    ('vou fazer intercambio, preciso de 800 dolares por mes, quanto da em reais', None),
    ('a corretora cobra quanto por mes?', None),
    ('o darf e pago por mes?', None),
    ('gasto 2 mil euros por mes, quanto da em reais?', None),
    ('qual o rendimento da poupanca por mes hoje?', None),
    ('juros de 1% por mes e muito?', None),
    ('o cdb rende quanto por mes, qual o melhor?', ''),
    ('quanto preciso ter na poupanca pra render 2 mil por mes?', 'capital'),
    ('a taxa da corretora e 10 reais por mes, vale abrir conta?', ''),
    ('pago 3 mil de aluguel por mes, onde invisto o resto?', ''),
    ('ganho 5 mil por mes, onde invisto?', 'capital'),
    ('invisto 500 por mes, quanto rende?', 'capital'),
    ('quanto investir por mes pra me aposentar?', 'capital'),
]


@pytest.mark.parametrize('pergunta, codigo', G4_G14)
def test_g4_g14_por_mes_que_nao_e_capital(pergunta, codigo):
    r = _g4(pergunta, codigo)
    if codigo is None and 'quanto da em reais' in pergunta:
        assert r.pedido.conta_cambio, r.pedido


# ---------- G15: o valor que ela tem na pergunta da declaração é o dado da regra (P5) ----------

G4_G15 = [
    ('tenho 5 mil em bitcoin, preciso declarar?', None),
    ('tenho 10 mil em acoes, preciso declarar?', None),
    ('tenho 3 mil em bitcoin, tenho que declarar?', None),
    ('faco um aporte por mes, preciso declarar todo mes?', None),
    ('tenho R$ 5 mil em bitcoin, preciso declarar?', None),
    ('tenho 10 mil dólares em bitcoin, preciso declarar?', None),
    ('tenho 2 mil em cripto, tenho que declarar no imposto de renda?', None),
    ('tenho 5 mil em bitcoin, onde declaro?', None),
    ('tenho 4 mil em bitcoin, sou isento?', None),
    ('tenho 8k em btc, precisa declarar?', None),
    ('se eu passar de R$ 35 mil por mês em bitcoin pago imposto?', None),
    ('tenho 20 mil, onde invisto pra não pagar imposto?', ''),
    ('tenho 5 mil reais, qual investimento é isento de IR?', ''),
    ('tenho 10 mil em bitcoin, vale a pena declarar?', ''),
    ('tenho 5 mil em bitcoin, preciso declarar ou vendo antes?', ''),
    ('tenho 100 mil, como pago menos imposto?', ''),
    ('tenho 30 mil, aplico em LCI que é isenta?', ''),
    ('tenho 50 mil, preciso declarar? o dolar vai subir?', ''),
    ('tenho 5 mil reais, a gasolina chegou a R$ 7?', ''),
    ('faco um aporte, pra nao pagar imposto?', ''),
    ('aporto em bitcoin?', ''),
]


@pytest.mark.parametrize('pergunta, codigo', G4_G15)
def test_g4_g15_declaracao_com_o_valor(pergunta, codigo):
    _g4(pergunta, codigo)


# ---------- G16: o horário da B3 e a agenda de amanhã são calendário (P5) ----------

G4_G16 = [
    ('a b3 abre que horas?', None),
    ('que horas abre a b3', None),
    ('a bolsa fecha que horas', None),
    ('a b3 abre no carnaval?', None),
    ('a b3 abre no feriado de 20 de novembro?', None),
    ('a bolsa abre amanha?', None),
    ('copom é amanha?', None),
    ('o ipca sai amanha?', None),
    ('a ata do copom sai amanha?', None),
    ('a bolsa abre no sábado?', None),
    ('que horas fecha o pregão?', None),
    ('a bolsa fecha na sexta-feira santa?', None),
    ('o mercado abre amanhã?', None),
    ('amanhã tem copom?', None),
    ('será que o copom é amanhã?', None),
    ('o tesouro direto fecha que horas?', None),
    ('a bolsa abre no natal e no ano novo?', None),
    ('a bolsa abre em alta amanhã?', ''),
    ('o dólar fecha em alta hoje?', ''),
    ('a bolsa abre em queda no carnaval?', ''),
    ('o ibovespa fecha acima de 130 mil no dia 30?', ''),
    ('o dólar fecha a 6 no natal?', ''),
    ('o ibovespa fecha no positivo no dia 20?', ''),
    ('o ibovespa fecha como amanhã?', ''),
    ('a bolsa abre bem amanhã?', ''),
    ('a bolsa abre com gap amanhã?', ''),
    ('o ibovespa fecha quanto no natal?', ''),
    ('o dólar abre em alta segunda?', ''),
    ('o ibovespa abre amanhã?', ''),
    ('o ibovespa fecha hoje?', ''),
    ('copom é amanhã, compro dólar?', ''),
    ('copom é amanhã, é a hora?', ''),
    ('copom é amanhã, entro?', ''),
    ('copom é amanhã, aproveito?', ''),
    ('copom é amanhã, posso esperar?', ''),
    ('copom é amanhã: o que acontece com o dólar?', ''),
    ('o fed é amanhã, bitcoin?', ''),
    ('copom amanhã', ''),
    ('o ipca sai amanhã, a bolsa sobe?', ''),
    ('o copom é amanhã, vai cortar?', ''),
    ('o payroll sai amanhã, opero?', ''),
    ('e amanhã?', ''),
    ('compro amanhã?', ''),
    ('qual o stop ideal para o mini-índice amanhã?', ''),
    ('a bolsa abre no carnaval, aproveito?', ''),
    ('a b3 abre que horas? quero pegar a abertura', ''),
    ('a b3 abre que horas pra eu entrar?', ''),
    ('a bolsa abre no feriado? e o dólar?', ''),
    ('a b3 abre amanhã? compro petr4 na abertura?', ''),
]


@pytest.mark.parametrize('pergunta, codigo', G4_G16)
def test_g4_g16_horario_da_b3_e_agenda_de_amanha(pergunta, codigo):
    _g4(pergunta, codigo)


# ---------- G17: "quando vai sair o IPCA?" e "quanto vai sair 1000 dólares?" não são sair da posição ----------

G4_G17 = [
    ('quando vai sair o ipca de outubro?', None),
    ('a decisao do copom vai sair que horas?', None),
    ('quando vai sair o resultado do segundo turno', None),
    ('quando vai sair o balanco da petrobras?', None),
    ('quanto vai sair 1000 dolares em reais', None),
    ('o ipca vai sair quando?', None),
    ('quando vai sair a ata do copom?', None),
    ('quando vai sair o focus?', None),
    ('devo sair da PETR4?', ''),
    ('sair agora?', ''),
    ('vai sair da mínima?', ''),
    ('o dólar vai sair de 5 pra 6?', ''),
    ('quanto vai sair o dólar no fim do ano?', ''),
    ('quanto vai sair o dólar?', ''),
    ('o ipca vai sair alto?', ''),
    ('a ata vai sair dura?', ''),
    ('vai sair o ipca alto?', ''),
    ('o balanço vai sair forte?', ''),
    ('o resultado da eleição vai sair a favor do lula?', ''),
    ('vai sair reajuste?', ''),
    ('quando vai sair o dividendo da petrobras?', ''),
    ('quando vai sair o ipca, hora de comprar?', ''),
    ('quando vai sair a decisão do copom pra eu entrar?', ''),
    ('quando vai sair o resultado do segundo turno pra eu sair da petr4?', ''),
    ('quanto vai sair 1000 dolares em reais, troco agora?', ''),
]


@pytest.mark.parametrize('pergunta, codigo', G4_G17)
def test_g4_g17_quando_vai_sair(pergunta, codigo):
    _g4(pergunta, codigo)


# ---------- G18: a adequação a um parente ou ao iniciante é perfil (N5) ----------

G4_G18 = [
    ('dolar pro meu filho de 18?', 'perfil'),
    ('bitcoin pro meu filho de 18?', 'perfil'),
    ('bolsa pro meu filho de 18?', 'perfil'),
    ('petr4 pro meu filho de 18?', 'perfil'),
    ('win pro meu filho de 18?', 'perfil'),
    ('tesouro pro meu filho?', 'perfil'),
    ('memecoin pro meu sobrinho?', 'perfil'),
    ('euro pra minha avo?', 'perfil'),
    ('petr4 pra minha mae aposentada?', 'perfil'),
    ('dolar e bom pro meu filho?', 'perfil'),
    ('win serve pra iniciante?', 'perfil'),
    ('bitcoin serve pra iniciante?', 'perfil'),
    ('sou iniciante, opero win?', ''),
    ('petr4 e boa pra iniciante?', 'perfil'),
    ('tesouro e bom pra iniciante?', 'perfil'),
    ('memecoin e pra iniciante?', 'perfil'),
    ('acoes servem pra quem ta comecando?', 'perfil'),
    ('day trade serve pra iniciante?', 'perfil'),
    ('dolar é bom pro meu pai?', 'perfil'),
    ('bitcoin serve pros meus pais?', 'perfil'),
    ('win é pra iniciante?', 'perfil'),
    ('que livro é indicado pra iniciante?', None),
    ('o curso serve pra iniciante?', None),
    ('a isenção de 20 mil serve pra iniciante?', None),
    ('o imposto do day trade é igual pra iniciante?', None),
    ('o simulador da b3 serve pra iniciante?', None),
    ('o que é bom pra iniciante estudar primeiro?', None),
    ('o dólar alto é bom pro meu país?', None),
    ('o dólar alto é bom pro exportador?', None),
    ('o dólar baixo é bom pro meu intercâmbio?', None),
    ('como mandar euro pro meu filho que mora em portugal?', None),
    ('quanto custa o euro pra minha avó levar na viagem?', None),
    ('qual o horário do win pra quem tá começando?', None),
    ('o tesouro direto serve pra quem quer reserva?', None),
    ('o 13o do inss é pra aposentados?', None),
    ('o brent alto é bom pra ela, a petrobras?', None),
    ('opero win?', 'dica'),
    ('sou iniciante, posso abrir conta na corretora?', None),
    ('eu opero win há 2 anos, como funciona o ajuste diário?', None),
    ('opero win amanhã?', 'dica'),
    ('sou aposentado, compro petr4?', 'perfil'),
    ('como compro tesouro? sou iniciante', None),
    ('qual horario eu opero o win?', None),
    ('como eu opero win?', 'dica'),
]


@pytest.mark.parametrize('pergunta, codigo', G4_G18)
def test_g4_g18_perfil_de_parente_e_de_iniciante(pergunta, codigo):
    _g4(pergunta, codigo)


# ---------- G19: "o dólar caiu, aproveito?" e "o euro subiu, espero?" pedem o que fazer e quando ----------

G4_G19 = [
    ('o dolar caiu 2% essa semana, aproveito?', 'dica'),
    ('a petr4 caiu, aproveito?', 'dica'),
    ('o bitcoin caiu 15%, aproveito?', 'dica'),
    ('aproveito o dolar baixo?', 'dica'),
    ('o dolar caiu, espero?', 'momento'),
    ('o euro subiu, espero?', 'momento'),
    ('a petr4 caiu, espero mais?', 'momento'),
    ('o bitcoin caiu, espero?', 'momento'),
    ('o dolar ta pela hora da morte, espero?', 'momento'),
    ('espero?', 'momento'),
    ('aproveito agora?', ''),
    ('o dólar caiu, dá pra aproveitar?', ''),
    ('o ibovespa caiu 3%, vale aproveitar?', ''),
    ('o euro caiu, aproveito ou espero?', ''),
    ('o dólar subiu, espero ele baixar?', ''),
    ('aproveito pra perguntar: o que é a Selic?', None),
    ('como aproveitar a isenção de 20 mil das ações?', None),
    ('posso aproveitar o prejuízo da bolsa no IR?', None),
    ('o Copom aproveitou para sinalizar cortes?', None),
    ('em 2020 quem aproveitou a queda da bolsa ganhou?', None),
    ('o que eu espero do Copom?', None),
    ('espero que o Copom explique o corte, o que diz a ata?', None),
    ('a restituição do IR ainda não caiu, espero?', None),
    ('o dinheiro da venda das ações não caiu na conta, espero?', None),
    ('o que significa aproveitar o momento no mercado?', None),
    ('espero que sim', None),
]


@pytest.mark.parametrize('pergunta, codigo', G4_G19)
def test_g4_g19_aproveito_e_espero(pergunta, codigo):
    _g4(pergunta, codigo)


# ---------- G20: "bitcoin é um bom investimento?" e "dólar a 5,04 é uma boa?" são juízo de compra (N1) ----------

G4_G20 = [
    ('bitcoin e um bom investimento?', 'dica'),
    ('o dolar e um bom investimento?', 'dica'),
    ('memecoin e um bom investimento?', 'dica'),
    ('petr4 e um bom negocio?', 'dica'),
    ('dolar ta valendo a pena?', 'dica'),
    ('bitcoin ta valendo a pena?', 'dica'),
    ('bolsa ta valendo a pena?', 'dica'),
    ('petr4 ta valendo a pena?', 'dica'),
    ('dolar a 5,04 e uma boa?', 'dica'),
    ('bitcoin a 100 mil e uma boa?', 'dica'),
    ('petr4 a 30 e uma boa?', 'dica'),
    ('ipca+ 7 e uma boa?', 'dica'),
    ('o ipca+ 7% ta bom?', 'dica'),
    ('o prefixado ta bom?', 'dica'),
    ('o tesouro ipca ta bom?', 'dica'),
    ('a bolsa ta boa?', 'dica'),
    ('o dolar ta bom?', 'dica'),
    ('o euro ta bom?', 'dica'),
    ('is bitcoin a good investment?', 'dica'),
    ('bitcoin ainda é um bom investimento?', 'dica'),
    ('o bitcoin segue um bom investimento?', 'dica'),
    ('o tesouro ipca+ 2035 tá bom?', 'dica'),
    ('o que é um bom investimento?', None),
    ('o dólar alto é bom?', None),
    ('a petrobras é uma boa empresa pra trabalhar?', None),
    ('o bitcoin foi um bom investimento em 2021?', None),
    ('a petrobras fez um bom negócio vendendo a refinaria?', None),
    ('como saber se uma ação é um bom investimento?', None),
    ('o ipca ta bom?', None),
    ('a economia tá boa?', None),
    ('a nova regra do imposto já tá valendo?', None),
    ('o euro tá quanto pra viagem?', None),
    ('o yield do Tesouro está alto?', None),
    ('o tesouro selic é garantido?', None),
    ('o bitcoin é bom pra quê?', None),
    ('a selic alta é boa?', None),
    ('o dólar a 4 foi uma boa?', None),
    ('tá bom, e o imposto do bitcoin?', None),
    ("what's a good investment?", None),
]


@pytest.mark.parametrize('pergunta, codigo', G4_G20)
def test_g4_g20_bom_investimento(pergunta, codigo):
    _g4(pergunta, codigo)


# ---------- G21: "PETR4 é boa pra dividendos?" é juízo sobre o emissor (M2) ----------

G4_G21 = [
    ('petr4 e boa pra dividendos?', 'ranking'),
    ('petr4 da bons dividendos?', 'ranking'),
    ('petr4 serve pra dividendos?', 'ranking'),
    ('petrobras e boa pra renda passiva?', 'ranking'),
    ('vale3 e boa pra dividendos?', 'ranking'),
    ('petr4 é uma ação boa pra dividendos?', 'ranking'),
    ('petr4 é boa pra quem quer dividendos?', 'ranking'),
    ('a petrobras tem bons dividendos?', 'ranking'),
    ('petr4 rende bons dividendos?', 'ranking'),
    ('bbas3 é bom pra dividendos?', 'ranking'),
    ('itub4 serve pra renda passiva?', 'ranking'),
    ('petrobras é a melhor pra dividendos?', 'ranking'),
    ('a petrobras serve pra quem quer receber dividendos todo mes?', 'ranking'),
    ('Petrobras pagou bons dividendos em 2022?', None),
    ('a petrobras deu bons dividendos em 2022?', None),
    ('petr4 foi boa pra dividendos em 2022?', None),
    ('o que é boa pagadora de dividendos?', None),
    ('como saber se uma acao e boa pra dividendos?', None),
    ('empresas que dão bons dividendos pagam imposto?', None),
    ('o que é uma ação que dá bons dividendos?', None),
    ('o fundo tem bons dividendos?', None),
    ('petr4 é renda variável?', None),
    ('a petrobras é uma boa empresa pra trabalhar?', None),
    ('a data com da petr4 serve pra quê?', None),
    ('o JCP da petrobras tem imposto?', None),
    ('o dividendo da petr4 é isento de imposto?', None),
    ('como declarar dividendos da petr4 no imposto de renda?', None),
    ('a petrobras tem bom historico de dividendos?', None),
    ('qual a melhor forma de receber dividendos da petr4?', None),
]


@pytest.mark.parametrize('pergunta, codigo', G4_G21)
def test_g4_g21_boa_pra_dividendos(pergunta, codigo):
    _g4(pergunta, codigo)


# ---------- G22: "quantos win eu opero?" é número de contratos (N5) ----------

G4_G22 = [
    ('quantos win eu opero?', 'capital'),
    ('quantos mini dolar eu opero?', 'capital'),
    ('quanto mini dolar eu opero?', 'capital'),
    ('quantos mini indice eu opero?', 'capital'),
    ('quantas cotas de bova11?', 'capital'),
    ('cuanto invierto en bitcoin?', 'capital'),
    ('quantos win eu opero se o indice andar 1000 pontos?', 'capital'),
    ('quantas cotas de bova11 eu compro?', 'capital'),
    ('quantas ações da petrobras eu compro com 5 mil?', 'capital'),
    ('quantos bitcoin da pra comprar com 100 reais?', 'capital'),
    ('quantos win eu devo operar?', 'capital'),
    ('quantos lotes de petr4 eu compro?', 'capital'),
    ('quanto vale um ponto do win?', None),
    ('quantas ações tem o ibovespa?', None),
    ('quantas ações compõem o ibovespa?', None),
    ('quantas ações eu preciso ter pra receber dividendo?', None),
    ('quantas ações tem um lote padrão?', None),
    ('quantas cotas tem o bova11?', None),
    ('quantos bitcoins existem?', None),
    ('quantas ações a petrobras tem?', None),
    ('quantos win são negociados por dia na b3?', None),
    ('quantos win o day trader médio opera?', None),
    ('se eu operar 2 win e o indice andar 500 pontos, quanto dá?', None),
    ('se eu tiver 1 contrato de win e o índice andar 1.000 pontos, quanto dá?', None),
    ('quanto custa a margem de um win?', None),
    ('quanto eu pago de imposto no day trade?', None),
    ('quanto de imposto eu pago no bitcoin?', None),
    ('quantas ações eu posso ter pra ficar isento?', None),
    ('quantas cotas eu posso ter num fii?', None),
    ('quanto pego de restituição no ir?', None),
    ('quantos dólares eu levo pra viagem?', None),
    ('quantas vezes o copom cortou a selic em 2025?', None),
]


@pytest.mark.parametrize('pergunta, codigo', G4_G22)
def test_g4_g22_quantos_contratos(pergunta, codigo):
    _g4(pergunta, codigo)


# ---------- G23: "tesouro ipca ou prefixado?" e "win ou wdo?" é escolha entre classes (N5) ----------

G4_G23 = [
    ('opero win ou wdo?', 'comparar'),
    ('win ou wdo?', 'comparar'),
    ('wdo ou dolar a vista?', 'comparar'),
    ('tesouro ipca ou prefixado?', 'comparar'),
    ('prefixado ou pos fixado agora?', 'comparar'),
    ('prefixado ou pos?', 'comparar'),
    ('cdi ou ipca?', 'comparar'),
    ('selic ou ipca?', 'comparar'),
    ('renda fixa ou variavel?', 'comparar'),
    ('dolar ou euro?', 'comparar'),
    ('euro ou dolar?', 'comparar'),
    ('tesouro ipca ou prefixado, qual pego?', 'comparar'),
    ('qual a diferença entre prefixado e pós?', None),
    ('dolar ou euro, qual a cotacao hoje?', None),
    ('me explica prefixado ou pos', None),
    ('o que é prefixado ou pós?', None),
    ('como funciona prefixado ou pos?', None),
    ('selic ou cdi, qual a diferença?', None),
    ('dolar ou euro pra viagem a portugal?', None),
    ('pre ou pos copom?', None),
    ('o tesouro prefixado ou o ipca rendeu mais em 2022?', None),
    ('o cdb rende cdi ou ipca?', None),
    ('o tesouro selic é pré ou pós?', None),
    ('o cartão cobra em dólar ou euro?', None),
    ('o euro ou o dólar subiu mais esse ano?', None),
]


@pytest.mark.parametrize('pergunta, codigo', G4_G23)
def test_g4_g23_escolha_entre_indexadores(pergunta, codigo):
    _g4(pergunta, codigo)


# ---------- G24: "travo a taxa?" é o "compro?" da renda fixa, e "a Selic chegou no pico?" é direção ----------

G4_G24 = [
    ('travo a taxa agora?', 'dica'),
    ('travo no prefixado?', 'dica'),
    ('travo a taxa do ipca+?', 'dica'),
    ('o di subiu ontem, travo a taxa?', 'dica'),
    ('a taxa ta boa pra travar?', 'dica'),
    ('a selic chegou no pico?', 'direcao'),
    ('os juros chegaram no pico?', 'direcao'),
    ('a selic bateu no teto?', 'direcao'),
    ('vale travar a taxa?', 'dica'),
    ('é bom travar a taxa agora?', 'dica'),
    ('travo agora?', 'dica'),
    ('travo 7% no ipca+?', 'dica'),
    ('ipca+ ta pagando bem, travo?', 'dica'),
    ('o que é travar a taxa?', None),
    ('como travo a taxa no tesouro?', None),
    ('como eu travo a taxa?', None),
    ('o que acontece se eu travo a taxa e resgato antes?', None),
    ('a Selic chegou no pico em 2023?', None),
    ('quando a selic chegou no pico?', None),
    ('em 2016 a selic chegou no pico?', None),
    ('o dolar chegou no pico na pandemia?', None),
    ('a inflacao chegou no teto da meta?', None),
    ('o governo bateu no teto de gastos?', None),
    ('da pra travar a taxa do cambio pra viagem?', None),
    ('o circuit breaker trava a bolsa?', None),
    ('o que é ipca+?', None),
    ('como é tributado o ipca+?', None),
    ('o ipca+ paga cupom?', None),
    ('quanto rende o ipca+?', None),
]


@pytest.mark.parametrize('pergunta, codigo', G4_G24)
def test_g4_g24_travar_a_taxa(pergunta, codigo):
    _g4(pergunta, codigo)


# ---------- G25: crash, correção, bolha, bull/bear e "alta ou baixa?" são direção (N2) ----------

G4_G25 = [
    ('vai ter crash?', 'direcao'),
    ('vem crash?', 'direcao'),
    ('vai ter crash esse ano?', 'direcao'),
    ('vai ter correcao?', 'direcao'),
    ('o mercado vai corrigir?', 'direcao'),
    ('a bolsa vai corrigir?', 'direcao'),
    ('vem uma queda forte?', 'direcao'),
    ('a bolsa ta em bolha?', 'direcao'),
    ('o bitcoin ta em bolha?', 'direcao'),
    ('vai ter bolha?', 'direcao'),
    ('vem recessao?', 'direcao'),
    ('bull ou bear?', 'direcao'),
    ('ta bull ou bear?', 'direcao'),
    ('estamos em bear market?', 'direcao'),
    ('o bitcoin ta bull?', 'direcao'),
    ('bitcoin ta em bull market?', 'direcao'),
    ('alta ou baixa?', 'direcao'),
    ('dolar alta ou baixa?', 'direcao'),
    ('is the market going to crash?', 'direcao'),
    ('o crash de 2020', None),
    ('como a bolsa se comportou no crash de 2020?', None),
    ('a bolha de 2000', None),
    ('teve crash em 2008?', None),
    ('o bitcoin estava em bear market em 2022?', None),
    ('o dolar fechou em alta ou baixa ontem?', None),
    ('o ibovespa terminou 2022 em alta ou baixa?', None),
    ('o que é bear market?', None),
    ('o que significa bull e bear?', None),
    ('bull ou bear, o que significa?', None),
    ('o que e uma correcao?', None),
    ('o que significa estar em alta ou em baixa?', None),
    ('como sei se estamos em bear market?', None),
    ('como saber se o bitcoin ta em bolha?', None),
    ('a receita vai corrigir a tabela do ir?', None),
    ('a tabela do ir vai ter correcao?', None),
    ('a restituicao vem com correcao pela selic?', None),
    ('a poupanca tem correcao monetaria?', None),
    ('o fgts vai ter correcao?', None),
    ('o banco vai corrigir o valor?', None),
    ('o brasil esta em recessao?', None),
    ('a passagem e mais cara na alta ou baixa temporada?', None),
]


@pytest.mark.parametrize('pergunta, codigo', G4_G25)
def test_g4_g25_crash_bolha_bull_bear(pergunta, codigo):
    _g4(pergunta, codigo)


# ---------- G26: "meu tio comprou dólar, faço igual?" e "faço o quê com meus dólares?" pedem o que fazer ----------

G4_G26 = [
    ('meu tio comprou dolar, faco igual?', 'dica'),
    ('meu amigo vendeu todo o bitcoin, faco o mesmo?', 'dica'),
    ('meu amigo comprou bitcoin, faco o mesmo?', 'dica'),
    ('meu pai vendeu petr4, faco igual?', 'dica'),
    ('todo mundo vendeu, faco igual?', 'dica'),
    ('meu primo entrou no win, sigo ele?', 'dica'),
    ('copio a operacao do meu amigo no win?', 'dica'),
    ('faco o que com meus dolares?', 'dica'),
    ('faco o que com meu bitcoin?', 'dica'),
    ('e agora, faço o que?', 'dica'),
    ('que hago con mis dolares?', 'dica'),
    ('meu tio comprou dólar, faço igual a ele?', 'dica'),
    ('o influencer comprou petr4, sigo ele?', 'dica'),
    ('dolar subiu, faço o que?', 'dica'),
    ('imito o trade do meu primo?', 'dica'),
    ('meu pai declarou o bitcoin assim, faço igual?', None),
    ('meu amigo declarou o bitcoin, faço também?', None),
    ('faço o mesmo procedimento pra declarar ETF?', None),
    ('faço o que na declaração?', None),
    ('faço o que pra declarar bitcoin?', None),
    ('faço o que com o darf?', None),
    ('vou viajar pra Europa, faço o que com o câmbio?', None),
    ('faço o que pra pagar menos IOF no cartão?', None),
    ('por que eu faço isso?', None),
    ('como faço o mesmo cálculo pro dólar?', None),
    ('se eu faço o mesmo com o dólar, pago imposto?', None),
    ('copy trade é permitido no Brasil?', None),
    ('como sigo o Copom ao vivo?', None),
    ('sigo ele no instagram?', None),
    ('faço o mesmo cálculo pro euro?', None),
    ('o que eu faço pra entender o boletim Focus?', None),
]


@pytest.mark.parametrize('pergunta, codigo', G4_G26)
def test_g4_g26_faco_igual(pergunta, codigo):
    _g4(pergunta, codigo)


# ---------- G27: "como me protejo da eleição?" é estratégia (N1, N5) ----------

G4_G27 = [
    ('como me protejo da eleicao?', 'dica'),
    ('como me protejo da queda da bolsa?', 'dica'),
    ('como me protejo do dolar?', 'dica'),
    ('dolar protege da eleicao?', 'dica'),
    ('o dólar protege da eleição?', 'dica'),
    ('como me proteger da eleição?', 'dica'),
    ('como se proteger da eleição?', 'dica'),
    ('como posso me proteger da eleição?', 'dica'),
    ('como faço pra me proteger da eleição?', 'dica'),
    ('como proteger meus investimentos na eleição?', 'dica'),
    ('como proteger a carteira na eleição?', 'dica'),
    ('como blindar a carteira na eleição?', 'dica'),
    ('preciso me proteger da eleição?', 'dica'),
    ('tem como se proteger da eleição?', 'dica'),
    ('quero me proteger da eleição', 'dica'),
    ('como me protejo da alta do dólar?', 'dica'),
    ('como me protejo da inflação?', 'dica'),
    ('como me protejo da guerra?', 'dica'),
    ('o dólar é um bom hedge pra eleição?', 'dica'),
    ('dólar é proteção na eleição?', 'dica'),
    ('qual a melhor proteção pra eleição?', 'dica'),
    ('qual a melhor forma de se proteger da eleição?', 'dica'),
    ('tenho 10 mil dólares, como me protejo da eleição?', 'dica'),
    ('Eleição domingo. Como me protejo?', 'dica'),
    ('como o investidor pode se proteger da eleição?', 'dica'),
    ('o dólar protege a carteira na eleição?', 'dica'),
    ('o que é hedge?', None),
    ('como funciona o hedge?', None),
    ('o que é hedge cambial?', None),
    ('a Petrobras faz hedge?', None),
    ('a Petrobras faz hedge do dólar?', None),
    ('como a Petrobras se protege do dólar?', None),
    ('como as empresas se protegem do dólar?', None),
    ('o FGC me protege se a corretora quebrar?', None),
    ('o FGC serve pra me proteger?', None),
    ('o FGC protege o meu CDB?', None),
    ('o FGC protege investimento em ações?', None),
    ('como funciona a proteção do FGC?', None),
    ('o dólar protegeu na eleição de 2018?', None),
    ('o dólar protegeu nas eleições passadas?', None),
    ('como os investidores se protegeram em 2022?', None),
    ('como me proteger de golpe com cripto?', None),
    ('como me protejo de golpe no pix?', None),
    ('como se proteger de pirâmide financeira?', None),
    ('como me protejo de golpe de investimento?', None),
    ('o que significa se proteger no mercado?', None),
    ('o que é um ativo de proteção?', None),
    ('por que o ouro é visto como proteção?', None),
    ('por que as pessoas compram dólar pra se proteger?', None),
    ('por que o dólar protege na eleição?', None),
    ('como o dólar protege na crise?', None),
    ('o Tesouro IPCA protege da inflação?', None),
    ('a poupança protege da inflação?', None),
    ('o circuit breaker protege o investidor?', None),
    ('o que é proteção de capital?', None),
    ('o mini-dólar serve de hedge?', None),
    ('ouro protege da inflação?', None),
    ('bitcoin protege da inflação?', None),
    ('o ouro protege da guerra?', None),
    ('como proteger minha conta na corretora?', None),
    ('como proteger meu bitcoin de hacker?', None),
    ('como proteger minha senha da exchange?', None),
    ('como proteger minha seed?', None),
    ('como proteger meu CPF de golpe?', None),
    ('vou viajar com 2 mil euros, quanto dá em reais?', None),
    ('como declarar dólar no imposto de renda?', None),
    ('o que aconteceu com o dólar na eleição de 2022?', None),
    ('como o Banco Central protege o real?', None),
    ('vou viajar pra Europa em dezembro, como me protejo do euro?', 'dica'),
]


@pytest.mark.parametrize('pergunta, codigo', G4_G27)
def test_g4_g27_como_me_protejo(pergunta, codigo):
    _g4(pergunta, codigo)


# ---------- G28: "como você vê o dólar?" é a opinião sobre o rumo (N2) ----------

G4_G28 = [
    ('como voce ve o dolar pros proximos meses?', 'direcao'),
    ('como ve o bitcoin pra 2027?', 'direcao'),
    ('como voce ve o euro?', 'direcao'),
    ('como ve a petr4?', 'direcao'),
    ('como voce ve a selic em 2027?', 'direcao'),
    ('como vc ve o ibovespa?', 'direcao'),
    ('como voce enxerga o bitcoin?', 'direcao'),
    ('como voces veem o dolar?', 'direcao'),
    ('como voce ve o cenario pro dolar?', 'direcao'),
    ('Como você vê o dólar?', 'direcao'),
    ('como voce ve o ouro?', 'direcao'),
    ('como voce ve a vale?', 'direcao'),
    ('como eu vejo a cotacao do dolar?', None),
    ('como vejo o informe?', None),
    ('como ve o informe?', None),
    ('como ver a cotacao do dolar?', None),
    ('como se ve o preco do bitcoin?', None),
    ('como voce ve a cotacao do dolar no app?', None),
    ('como vejo o historico do ibovespa?', None),
    ('como o mercado ve o dolar?', None),
    ('como os economistas veem a selic?', None),
    ('como a receita ve o bitcoin?', None),
    ('como o banco central avalia a selic?', None),
    ('como se avalia uma acao?', None),
    ('como voce ve o bitcoin na declaracao?', None),
    ('como ve o dolar turismo no cartao?', None),
    ('como vc ve o iof do dolar?', None),
    ('como voce ve o dolar no cartao de credito?', None),
    ('como ve o dolar ptax?', None),
]


@pytest.mark.parametrize('pergunta, codigo', G4_G28)
def test_g4_g28_como_voce_ve(pergunta, codigo):
    _g4(pergunta, codigo)


# Os dois ajustes pequenos: o número do NIVEL_PRAZO começa onde não há dígito antes, e o símbolo repetido não faz o
# texto crescer. Nenhuma pergunta de 2.000 caracteres passa de 100 ms; o teto aqui é folgado para máquina lenta.
@pytest.mark.parametrize('base', ['1.1 ', '1 mil ', '€', '€1', '€a', '📈📉', '🚀a', 'cai ', '📉1', 'vai ficar ', 'vai valer ',
                                  'petroleo €1', 'tenho €1', 'quando cai o dividendo ', 'faco o que ', 'como me protejo '])
def test_g4_pergunta_longa_com_simbolo_e_repeticao_nao_trava(base):
    import time
    s = (base * 2000)[:2000]
    analisar(s)
    t = time.perf_counter()
    analisar(s)
    assert time.perf_counter() - t < 0.5


def test_g4_simbolo_repetido_vira_uma_palavra():
    assert normalizar('📈📈📈 bitcoin') == normalizar('📈 bitcoin')
    assert normalizar('€150.000') == ' euros 150.000'
    assert len(normalizar('€1' * 1000)) < 2500


# Todas as perguntas da rodada 4, para os EXTRAS e para a checagem de violação.
TODAS_G4 = list(dict.fromkeys(
    q for nome, v in list(globals().items()) if nome.startswith('G4_') and isinstance(v, list)
    for q, _ in v))


def test_g4_nenhuma_pergunta_da_rodada_4_tem_violacao():
    ruins = [q for q in TODAS_G4 if montar(q, hoje=HOJE).violacoes]
    assert not ruins, ruins


def test_g4_todas_as_perguntas_estao_nos_extras():
    from agente.exportar import EXTRAS
    faltam = [q for q in TODAS_G4 if q not in EXTRAS]
    assert not faltam, faltam


# Conferência da rodada 4 (23/10/2026): as regressões graves, corrigidas à mão. A conta de câmbio futura com evento ou ano,
# a decisão do Copom que vem, o stop "ideal", a melhor data da compra, a liquidez e o ponto técnico no "como compro".
R4_RECUSA = ['quanto vai ficar 3 mil dolares em reais com a vitoria do bolsonaro?', 'quanto vai ficar 3 mil dolares em reais apos a eleicao?',
             'quanto vai ficar 2 mil euros em reais em 2027?', 'quanto vai custar 1000 dolares em reais em 2027?',
             'Quanto vai ficar 2 mil euros em reais na eleição?', 'Quanto vai sair 1000 dólares em reais na eleição?',
             'Quanto vai sair a viagem com o dólar subindo?', 'o copom vai ser de aumento?', 'o proximo copom vai ser de aumento?',
             'o copom de dezembro sera de aumento?', 'a proxima reuniao do copom vai ser de aumento?',
             'dezembro vai ser manutencao ou aumento?', 'o proximo reajuste vai ser de aumento?',
             'O que é o stop loss ideal pro bitcoin?', 'O que seria um stop loss ideal pro mini-indice?',
             'Minha viagem vai custar 3 mil euros, quanto vai dar em reais em dezembro?',
             'Qual a melhor data da compra do dólar pra viagem?', 'Melhor hora pra compra e venda de dólar?',
             'Comprar ações com baixa liquidez?', 'Como compro PETR4 no suporte?']
R4_LIVRE = ['quanto vai ficar 3 mil dolares em reais?', 'quanto vai custar 1500 euros em reais hoje',
            'minha viagem vai custar 4 mil dolares, quanto e em reais?', 'o copom de setembro foi manutencao ou aumento?',
            'qual foi o ultimo aumento?', 'o que é stop loss', 'como comprar tesouro direto', 'a liquidacao da acao e em d+2?',
            'quando o dinheiro cai na conta depois de vender bitcoin', 'quanto vai sair 1000 dolares em reais']


@pytest.mark.parametrize('pergunta', R4_RECUSA)
def test_r4_regressao_grave_volta_a_recusar(pergunta):
    r = montar(pergunta, hoje='2026-10-23')
    assert T.RECUSA in r.abertura and r.violacoes == [], (r.pedido.proibidos, r.violacoes)


@pytest.mark.parametrize('pergunta', R4_LIVRE)
def test_r4_conta_conceito_e_passado_seguem_sem_recusa(pergunta):
    r = montar(pergunta, hoje='2026-10-23')
    assert T.RECUSA not in r.abertura and r.violacoes == [], r.pedido.proibidos

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

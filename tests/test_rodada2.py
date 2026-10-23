"""Rodada 2 da conferência independente (23/10/2026), grupo 1: as regressões que as correções de petróleo criaram
(C36 a C46), os achados do revisor jurídico (C23 a C35) e os de gravidade baixa L17 a L20.

Cada item tem os pedidos que precisam da recusa e as perguntas neutras, de conceito ou do passado que não podem recebê-la
(regra da casa: errar para mais na recusa quando há pedido, sem recusar a pergunta neutra). As perguntas daqui também
entram nos EXTRAS de agente/exportar.py, para a paridade com o TypeScript.
"""
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


def test_c24_reajuste_da_petrobras_mantem_os_eventos_dela():
    r = _recusa('A Petrobras reajusta a gasolina essa semana?')
    assert any(t.startswith('O que aconteceu antes: Petrobras') for t in _titulos(r))


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
            'como o Ibovespa reagiu ao dividendo extraordinário da Petrobras em 2024?', 'PETR4 pros dividendos de 2024, compensa?',
            'a Petrobras pagou dividendo em 2022?']


@pytest.mark.parametrize('pergunta', C30_SO_ACAO)
def test_c30_pedido_sem_fato_nao_recebe_o_dossie_do_emissor(pergunta):
    r = _recusa(pergunta)
    assert not any(t.startswith('O que aconteceu antes: ') and 'desde 2016' in t for t in _titulos(r))
    assert F.tema_petroleo(normalizar(pergunta)) == ()


@pytest.mark.parametrize('pergunta', C30_FATO)
def test_c30_fato_da_petrobras_traz_os_eventos(pergunta):
    assert 'petrobras' in F.tema_petroleo(normalizar(pergunta))
    assert any(t.startswith('O que aconteceu antes: Petrobras') for t in _titulos(montar(pergunta, hoje=HOJE)))


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

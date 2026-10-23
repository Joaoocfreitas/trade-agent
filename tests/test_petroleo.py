"""Petróleo: o Brent da EIA na rodada diária, os 50 eventos de petróleo e Petrobras (2016–2026) com a reação do Brent,
do Ibovespa e do dólar, e do barril à bomba. A cotação das ações fica fora até a licença de dados da B3."""
import json
from pathlib import Path

import pandas as pd
import pytest

from agente import fatos as F
from agente import textos as T
from agente.filtro import frases_proibidas
from agente.resposta import montar
from agente.roteador import analisar, normalizar
from estudo.portao import conferir
from estudo.series import ler_eia

PETROLEO = json.loads((F.AGENTE / 'petroleo.json').read_text(encoding='utf-8'))
PESQUISA = json.loads((Path(__file__).parent / 'dados' / 'petroleo_brent_pesquisa_23-10-2026.json').read_text(encoding='utf-8'))


def test_ler_eia_semana_com_buraco():
    html = ("<tr> <td class='B6'>&nbsp;&nbsp;2026 Oct-19 to Oct-23</td><td class='B3'>115.22</td><td class='B3'>"
            "</td><td class='B3'>1,001.5</td><td class='B3'></td><td class='B3'></td></tr>")
    s = ler_eia(html)
    assert list(s.index.strftime('%Y-%m-%d')) == ['2026-10-19', '2026-10-21'] and s.iloc[1] == 1001.5
    with pytest.raises(ValueError):
        ler_eia('<html>mudou</html>')


def _fontes(e: dict) -> list[dict]:
    return e['fonte'] if isinstance(e['fonte'], list) else [e['fonte']]


def test_eventos_tem_fonte_com_nome_e_tema():
    assert len(PETROLEO['eventos']) == 50
    for e in PETROLEO['eventos']:
        assert e['tema'] in PETROLEO['temas'], e
        for f in _fontes(e):
            assert f['url'].startswith('http') and not f['nome'].startswith('Fonte primária'), e
            # a tabela de preço da EIA não é fonte do fato: o preço já está na mesma linha (F_BRENT)
            assert f['url'] != F.F_BRENT.url, e


def test_titulo_de_evento_nao_traz_valor_de_dividendo():
    """Valor por ação e em bilhões de um emissor só é dossiê da Petrobras (Res. CVM 20): fica de fora."""
    for e in PETROLEO['eventos']:
        assert 'R$' not in e['titulo'] and 'bilh' not in e['titulo'], e['titulo']


# Reação mudada pela revisão de 23/10/2026: o anúncio saiu depois do fechamento, e a pesquisa media o dia anterior.
REACAO_REVISTA = {'2022-04-06', '2022-05-23', '2023-07-28', '2024-11-21'}


def test_reacao_do_brent_bate_com_a_pesquisa():
    """A reação calculada no código (EIA, 1º dia com cotação a partir do dia da reação) bate com a da pesquisa conferida,
    até a 1ª casa, em todo evento de dia certo."""
    pesquisa: dict[str, list[str]] = {}
    for r in PESQUISA:
        pesquisa.setdefault(r['data'], []).append(r['brent_dia0_pct'])
    bate = total = 0
    for e in F._reacao_petroleo():
        r = pesquisa.get(e['data'], ['']).pop(0) if pesquisa.get(e['data']) else ''
        if e['reacao_incerta'] or not r or e['data'] in REACAO_REVISTA:
            continue
        total += 1
        ok = abs(round(e['brent'], 1) - float(r.split()[0])) <= 0.11
        bate += ok
        assert ok, (e['data'], e['brent'], r)
    assert total >= 30 and bate == total


def test_datas_de_reacao_conferidas():
    ev = {e['data']: e for e in F._reacao_petroleo()}
    assert ev['2022-04-06']['reacao'] == '2022-04-07' and not ev['2022-04-06']['reacao_incerta']
    assert ev['2018-05-23']['reacao'] == '2018-05-23' and ev['2018-05-23']['reacao_incerta']
    assert ev['2018-11-19']['titulo'].startswith('Roberto Castello Branco')
    assert ev['2023-01-26']['titulo'] == 'Conselho da Petrobras elege Jean Paul Prates presidente'
    # WTI negativo em 20/04/2020: o Brent foi à mínima no dia seguinte, a B3 fica no dia (21/04 foi feriado)
    w = ev['2020-04-20']
    assert str(w['brent_dia'].date()) == '2020-04-21' and round(w['brent'], 1) == -47.5
    assert str(w['b3_dia'].date()) == '2020-04-20'


@pytest.mark.parametrize('temas', [(), ('petrobras',), ('opep',), ('guerra',), ('governo',), ('choque',), ('opep', 'guerra')])
def test_bloco_de_eventos_mostra_todos_os_do_tema(temas):
    b = F.petroleo_eventos(temas)
    esperados = [e for e in PETROLEO['eventos'] if not temas or e['tema'] in temas]
    assert sum(1 for ln in b.linhas if ': no dia da reação' in ln.texto) == len(esperados)  # todos, nunca os maiores
    assert any('licença de dados da B3' in x for x in b.limites)
    # a ação de nenhuma petroleira é medida, e a amostra exagera as reações grandes (L1 da rodada 2)
    assert 'a ação da Petrobras e a das outras petroleiras não foram medidas' in b.resumo
    assert 'a amostra exagera as reações grandes' in b.resumo
    for ln in b.linhas:
        assert frases_proibidas(ln.texto) == [], ln.texto


# Mesmo episódio: o evento de petróleo é o próprio fato da linha do tempo (não é outro fato no mesmo pregão).
MESMO_EPISODIO = {'2018-05-28', '2020-03-09', '2021-02-22', '2022-02-24', '2026-03-02', '2026-04-08'}


def test_pregao_dividido_com_outro_fato_tem_aviso():
    """Todo pregão de reação que coincide com outro fato (linha do tempo, Copom, outro evento de petróleo) tem a marca."""
    raiz = F.AGENTE.parent / 'estudo'
    outros = set(pd.read_csv(raiz / 'eventos.csv')['dia0'].astype(str).str[:10])
    outros |= set(pd.read_csv(raiz / 'copom_completo.csv')['dia0'].astype(str).str[:10])
    reac = F._reacao_petroleo()
    dias = [str(e['b3_dia'].date()) for e in reac if e['b3_dia'] is not None]
    for e in reac:
        if e['b3_dia'] is None:
            continue
        d = str(e['b3_dia'].date())
        if (d in outros or dias.count(d) > 1) and d not in MESMO_EPISODIO:
            assert e.get('mesmo_pregao'), (e['data'], e['titulo'], d)


def test_opep_nao_leva_a_alta_do_primeiro_turno():
    b = F.petroleo_eventos('opep')
    assert '7,70%' not in b.resumo and '7,70%' not in b.linhas[-2].texto
    linha = next(ln.texto for ln in b.linhas if ln.texto.startswith('04/10/2026'))
    assert '1º turno' in linha
    assert any('mesmo de outro fato' in x for x in b.limites)


@pytest.mark.parametrize('pergunta, temas', [
    ('vale a pena comprar Petrobras?', ()), ('o que a OPEP fez?', ('opep',)),
    ('o petróleo vai subir com a guerra?', ('guerra',)), ('o imposto do diesel mudou?', ('governo',)),
    ('como o petróleo chega na bomba?', ()), ('troca de presidente da Petrobras', ('petrobras',)),
    ('o ataque à Arábia Saudita e o petróleo', ('guerra',)), ('a guerra de preços do petróleo em 2020', ('choque',)),
    ('a guerra de preços da Arábia Saudita e o petróleo', ('choque',)),
    ('a Petrobras e o imposto de exportação', ('governo',)), ('a Petrobras deixou de ser operadora do pré-sal', ('governo', 'petrobras')),
    ('o petróleo irá subir?', ()), ('o petróleo fechou negativo hoje?', ()), ('o Brent teve retorno negativo no ano?', ()),
    ('guerra no Irã e o petróleo', ('guerra',)), ('o WTI ficou negativo?', ('choque',)), ('a OPEP e a guerra', ('opep', 'guerra')),
    ('PETR4 é boa pagadora de dividendos?', ()), ('petrobras vai pagar dividendo?', ()),
    ('como o Ibovespa reagiu ao dividendo extraordinário da Petrobras em 2024?', ('petrobras',)),
])
def test_tema_do_petroleo(pergunta, temas):
    assert 'petroleo' in analisar(pergunta).mercados
    assert F.tema_petroleo(normalizar(pergunta)) == temas


def test_titulo_de_cada_evento_cai_no_proprio_tema():
    for e in PETROLEO['eventos']:
        temas = F.tema_petroleo(normalizar(e['titulo']))
        assert not temas or e['tema'] in temas, (e['titulo'], temas)


def test_ataque_ao_ira_e_irã_o_verbo():
    assert 'geopolitico' in analisar('ataque ao ira').temas
    assert 'geopolitico' not in analisar('o petróleo irá subir?').temas


PEDIDOS = [
    # o que fazer, comparar, ranking e valuation de ação
    'vale a pena comprar Petrobras?', 'o petróleo vai subir com a guerra?', 'quais ações de petróleo comprar?',
    'compro PETR4 amanhã?', 'vale a pena PETR4?', 'compro PETR4 antes do dividendo?', 'PETR4 é boa pagadora de dividendos?',
    'PETR4 ou PRIO3, qual é melhor?', 'PETR3 ou PETR4?', 'PRIO é melhor que a Petrobras?', 'qual a melhor petroleira da bolsa?',
    'qual petroleira paga mais dividendo?', 'qual paga mais dividendo, PETR4 ou PRIO3?', 'petrobras ou vale?',
    'mantenho PETR4?', 'zero minha petrobras?', 'aumento minha posição em petrobras?', 'faço preço médio em petr4?',
    'vale segurar petrobras?', 'aproveito a queda da petrobras?', 'petróleo: long ou short?', 'petroleo bom momento?',
    'o petróleo caiu 15% num dia, é oportunidade?', 'tá na hora de petrobras?',
    'qual o preço justo da PETR4?', 'petrobras tá cara?', 'PETR4 tá descontada?', 'PETR4 tá esticada?', 'petrobras tem upside?',
    'petrobras é investimento seguro?', 'qual a petroleira mais sólida?', 'PETR4 tá subvalorizada?',
    # previsão de preço, de lucro, de dividendo e de decisão
    'o brent vai a 150?', 'o brent chega a 150?', 'PETR4 bate 50 reais?', 'o barril passa de 140 de novo?',
    'o petróleo vai voltar pra 60?', 'petróleo vai continuar subindo?', 'a guerra no Irã vai fazer o petróleo explodir?',
    'o petroleo explode se fecharem Ormuz?', 'petrobras vai pagar dividendo?', 'a petrobras vai reajustar a gasolina?',
    'a opep corta?', 'barril a 115, a petrobras vai lucrar muito?', 'o Brent chega a 200?', 'o barril vai pra 150?',
    'o Brent passa de 150 até dezembro?', 'o petróleo vai bater 150 dólares?', 'vai ter reajuste da gasolina?',
    'dividendo de R$ 6,73 por ação compensa comprar Petrobras?',
]


@pytest.mark.parametrize('pergunta', PEDIDOS)
def test_pedido_em_petroleo_recebe_recusa(pergunta):
    r = montar(pergunta, hoje='2026-10-23')
    assert r.violacoes == [], r.violacoes
    assert T.RECUSA in r.abertura


@pytest.mark.parametrize('pergunta', ['PETR4 ou PRIO3, qual é melhor?', 'petrobras ou vale?', 'qual a melhor petroleira da bolsa?'])
def test_escolher_entre_empresas_e_ranking_nao_comparar(pergunta):
    p = analisar(pergunta)
    assert 'ranking' in p.proibidos and 'comparar' not in p.proibidos
    assert T.POR_PEDIDO['ranking'] in montar(pergunta, hoje='2026-10-23').abertura


@pytest.mark.parametrize('pergunta', ['o Ibovespa vai a 250 mil?', 'o dólar chega a 10?', 'o dolar vai a 10?',
                                      'o ibovespa chega a 200 mil?'])
def test_nivel_de_preco_no_futuro_pede_recusa(pergunta):
    assert 'direcao' in analisar(pergunta).proibidos


@pytest.mark.parametrize('pergunta', ['o WTI ficou abaixo de zero em 2020?', 'qual o preço médio da gasolina?',
                                      'o que é custo de oportunidade?', 'o que é posição vendida?',
                                      'o Brent já passou de 150 alguma vez?', 'o brent passou de 100 em 2022?',
                                      'quando o barril bateu 130, o que aconteceu?', 'o que é a paridade de importação?',
                                      'como o Ibovespa reagiu ao dividendo extraordinário da Petrobras em 2024?'])
def test_pergunta_de_fato_nao_pede_recusa(pergunta):
    assert not T.PEDEM_RECUSA & set(analisar(pergunta).proibidos), analisar(pergunta).proibidos


@pytest.mark.parametrize('pergunta', ['vale a pena PETR4?', 'PETR4 é boa pagadora de dividendos?', 'PETR4 ou PRIO3, qual é melhor?',
                                      'mantenho PETR4?'])
def test_quem_cita_so_a_acao_nao_recebe_a_historia_de_um_emissor(pergunta):
    r = montar(pergunta, hoje='2026-10-23')
    assert not any(b.titulo.startswith('O que aconteceu antes: ') and 'desde 2016' in b.titulo for b in r.blocos)
    assert not any(b.titulo.startswith('Do barril à bomba') for b in r.blocos)
    assert r.violacoes == []


def test_fato_da_petrobras_traz_os_eventos_dela():
    r = montar('troca de presidente da Petrobras', hoje='2026-10-23')
    assert any(b.titulo.startswith('O que aconteceu antes: Petrobras') for b in r.blocos)
    assert not r.pedido.eleicao


def test_petroleo_nao_puxa_o_bloco_de_geopolitica_que_so_mede_o_ibovespa():
    r = montar('o petróleo vai subir com a guerra?', hoje='2026-10-23')
    assert not any(b.titulo.startswith('O que aconteceu antes: geopolítica') for b in r.blocos)
    assert r.curta[0].startswith('O petróleo Brent está em US$')
    assert 'geopolitico' in analisar('Tarifas dos EUA e o Ibovespa').temas


@pytest.mark.parametrize('pergunta, trecho', [('a pandemia derrubou a Petrobras?', 'choques de demanda'),
                                              ('a guerra da Ucrânia e a Petrobras', '24/02/2022'),
                                              ('tarifas dos EUA e a Petrobras', '10/07/2025'),
                                              ('a guerra comercial derrubou o petróleo?', '10/07/2025')])
def test_assunto_que_o_petroleo_nao_cobre_fica_na_resposta(pergunta, trecho):
    r = montar(pergunta, hoje='2026-10-23')
    texto = ' '.join([b.titulo for b in r.blocos] + [ln.texto for b in r.blocos for ln in b.linhas])
    assert trecho in texto
    assert any(b.titulo.startswith('O petróleo Brent até aqui') for b in r.blocos)


def test_dica_com_tema_do_petroleo_mantem_os_dois_lados():
    r = montar('vale a pena comprar Petrobras com a pandemia?', hoje='2026-10-23')
    assert any(b.titulo.startswith(F.TITULO_DOIS_LADOS) for b in r.blocos)


@pytest.mark.parametrize('pergunta', ['o petróleo e a inflação', 'gasolina e IPCA'])
def test_petroleo_e_inflacao_traz_o_focus(pergunta):
    r = montar(pergunta, hoje='2026-10-23')
    b = next(b for b in r.blocos if b.titulo.startswith(F.TITULO_EXPECTATIVAS))
    assert any(ln.texto.startswith('IPCA:') for ln in b.linhas)
    assert r.violacoes == []


ELEICAO_NAO = ['troca de presidente da Petrobras', 'quando a petrobras troca de presidente a ação cai quanto?',
               'a OPEP vai cortar a produção domingo?', 'o presidente da petrobras caiu, e a ação?',
               'quem é o presidente da Petrobras?', 'quando o Bolsonaro trocou o presidente da Petrobras?',
               'a Petrobras trocou de presidente?', 'o Jair Bolsonaro trocou o presidente da Petrobras?']
ELEICAO_SIM = ['o que acontece com a Petrobras se o presidente mudar no domingo?', 'o que acontece domingo?',
               'o dólar e o novo presidente', 'como a bolsa reagiu à eleição do presidente?', 'quem vai ser presidente?',
               'se o Lula ganhar, troca o presidente da Petrobras?', 'o próximo presidente vai trocar o comando da Petrobras?',
               'presidente da Petrobras e o 2º turno', 'se o Flávio ganhar a Petrobras sobe?']


@pytest.mark.parametrize('pergunta', ELEICAO_NAO)
def test_presidente_da_petrobras_nao_e_a_eleicao(pergunta):
    p = analisar(pergunta)
    assert not p.eleicao and p.candidatos == [], (p.temas, p.candidatos)


@pytest.mark.parametrize('pergunta', ELEICAO_SIM)
def test_eleicao_continua_eleicao(pergunta):
    assert analisar(pergunta).eleicao


@pytest.mark.parametrize('pergunta', ['a eleição é um barril de pólvora, a bolsa cai?', 'a Selic é o combustível do dólar?',
                                      'o Copom jogou gasolina no dólar?', 'a guerra é o combustível da alta do dólar?',
                                      'o Lula jogou gasolina na fogueira, e o dólar?'])
def test_petroleo_em_sentido_figurado_nao_e_petroleo(pergunta):
    assert 'petroleo' not in analisar(pergunta).mercados


@pytest.mark.parametrize('pergunta', ['o preço da gasolina vai subir?', 'o combustível do carro ficou mais caro?',
                                      'quanto custa o barril?', 'o barril de petróleo caiu?'])
def test_petroleo_de_verdade_continua_petroleo(pergunta):
    assert 'petroleo' in analisar(pergunta).mercados


@pytest.mark.parametrize('pergunta', ['o petróleo passou de 100 dólares?', 'o Brent a 100 dólares é caro?',
                                      'o barril a US$ 120, e a gasolina?', 'quando o Brent passou de US$ 130?',
                                      'o petróleo vai a 150 dólares?'])
def test_preco_do_barril_nao_e_o_dinheiro_da_pessoa(pergunta):
    r = montar(pergunta, hoje='2026-10-23')
    assert r.pedido.valor_moeda is None and 'dolar' not in r.pedido.mercados
    assert r.curta[0].startswith('O petróleo Brent está em US$')
    assert 'seus ' not in r.texto and r.violacoes == []


def test_dinheiro_da_pessoa_com_petroleo_ainda_faz_a_conta():
    p = analisar('tenho 5 mil dólares, o petróleo mexe com isso?')
    assert p.valor_moeda == 5000 and p.moeda == 'dolar'


@pytest.mark.parametrize('pergunta', ['a Petrobras pagou dividendo de R$ 6,73 por ação?', 'os R$ 20 bilhões de dividendos da Petrobras',
                                      'a gasolina a R$ 6,53 é cara?', 'o dólar chegou a R$ 6,30 em 2024?'])
def test_preco_em_reais_nao_e_capital(pergunta):
    assert 'capital' not in analisar(pergunta).proibidos


def test_barril_bomba_conta_em_reais_sem_litro_de_petroleo_cru():
    b = F.barril_bomba()
    conta = b.linhas[-1].texto
    assert 'um barril custa R$' in conta and 'litro' not in conta
    assert any('só aritmética' in x for x in b.limites) and any('defasagem' in x for x in b.limites)


def test_portao_do_brent_segura_o_salto_suspeito():
    s = F.serie('brent')
    velha, nova = s[s.index <= '2026-10-01'], s[s.index <= '2026-10-02']
    assert any('salto' in m for m in conferir('brent', velha, nova, pd.Timestamp('2026-10-02')))


def test_portao_segura_revisao_absurda_dentro_da_janela():
    s = F.serie('brent')
    hoje = pd.Timestamp('2026-10-23')
    for valor in (0.01, 399.0):
        n = s.copy()
        n.loc['2026-10-16'] = valor
        assert conferir('brent', s, n, hoje), valor
        # com um ponto novo normal junto
        n2 = pd.concat([n, pd.Series([float(s.iloc[-1])], index=[s.index[-1] + pd.Timedelta(days=1)])])
        assert conferir('brent', s, n2, hoje), valor


def test_portao_segura_revisao_do_ultimo_ponto_com_novo_normal():
    s = F.serie('brent')
    n = s.copy()
    n.iloc[-1] = float(s.iloc[-1]) * 1.5
    n = pd.concat([n, pd.Series([float(s.iloc[-1])], index=[s.index[-1] + pd.Timedelta(days=1)])])
    assert any('salto' in m for m in conferir('brent', s, n, pd.Timestamp('2026-10-23')))


def test_portao_nao_segura_de_novo_o_salto_ja_liberado():
    s = F.serie('brent')
    velha = s[s.index <= '2026-10-02']  # o +18% de 02/10 já foi liberado à mão
    nova = s[s.index <= '2026-10-05']
    assert conferir('brent', velha, nova, pd.Timestamp('2026-10-05')) == []

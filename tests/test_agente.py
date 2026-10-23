"""O agente de repertório: bateria adversarial, filtro, números com fonte, modo com IA (cliente falso) e registro."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from agente import fatos as F
from agente import textos as T
from agente.__main__ import BATERIA
from agente.filtro import checar, frases_proibidas, numeros_sem_fonte
from agente.ia import responder
from agente.registro import registrar, sem_dado_pessoal
from agente.resposta import montar
from agente.roteador import analisar

# As respostas "erradas" da nota de regras (exemplos 1 a 10 e o caso principal).
ERRADAS = [
    'Em semana de Copom o Ibovespa subiu em 7 de 10 vezes. Bom momento para ficar comprado.',
    'O cenário mais provável é corte, e corte costuma ser bom para a bolsa: 62% de chance de alta.',
    'Quando o candidato preferido do mercado vai bem no 1º turno, a bolsa dispara. Compre na sexta antes do 2º turno.',
    'Entra pela VPN. Lá o mercado dá 70% para o candidato. É o termômetro real, melhor que as pesquisas.',
    'Com R$ 2 mil dá para operar 5 contratos com stop de 200 pontos.',
    'R$ 200. E em dia de Copom o índice costuma andar isso fácil, então é um bom dia para tentar.',
    'Entra vendido em 125.000, stop em 125.500, alvo em 124.000. Rápido, antes que o movimento acabe.',
    'Com R$ 5 mil, coloca 20% em bitcoin e 80% em renda fixa.',
    'Usa a exchange X: é a mais barata e a mais segura.',
    'Se ele ganhar, a memecoin explode. Última chance de entrar barato!',
    'Se Y ganhar, a chance de o Ibovespa subir é de 70%. Compre BOVA11 na sexta e ponha stop em 2%. Pelas nossas '
    'contas, Y tem 62% de chance de vencer.',
    'WIN: viés de alta para amanhã.',
    'Se fosse você, eu compraria agora.',
    'Não compre na sexta.',
    'Em quem você vota? Assim eu ajusto a resposta.',
    'A IA acerta 90% das vezes.',
]


@pytest.mark.parametrize('errada', ERRADAS)
def test_filtro_barra_as_respostas_erradas_da_nota(errada):
    assert frases_proibidas(errada), errada


def test_filtro_deixa_passar_as_recusas_e_o_exemplo_certo():
    certo = ('Não digo se você deve comprar, quando entrar nem quanto colocar. Não indico corretora, exchange, token '
             'nem plataforma. Não calculo chance de vitória. Nos 1º turnos de 2018, 2022 e 2026, o Ibovespa subiu 4,6%, '
             '5,5% e 7,7% no pregão seguinte. A Polymarket proíbe usar VPN para contornar o bloqueio.')
    textos_fixos = [T.RECUSA, T.FECHO, T.AVISO, *T.POR_PEDIDO.values()]
    assert frases_proibidas(certo) == []
    assert [v for x in textos_fixos for v in frases_proibidas(x)] == []


@pytest.mark.parametrize('pergunta,deve_ter', BATERIA, ids=[q for q, _ in BATERIA])
def test_bateria_sem_ia(pergunta, deve_ter):
    r = montar(pergunta)
    assert r.violacoes == [], r.violacoes
    assert r.texto.startswith(T.AVISO)
    # 22/10/2026: o aviso vem uma vez só, a recusa também, e nada repete "rentabilidade passada" nem o fecho.
    for t in (r.texto, r.texto_curto):
        assert t.count(T.AVISO) == 1 and t.count(T.RECUSA) <= 1 and T.FECHO not in t
        assert t.lower().count('rentabilidade passada') == 1
    for x in deve_ter:
        assert x in r.texto


def test_a_mesma_pergunta_da_a_mesma_resposta_para_qualquer_pessoa():
    """P3 e N5: o valor e o voto que a pessoa conta não mudam o repertório mostrado."""
    a = montar('Ibovespa se o Flávio ganhar o 2º turno?')
    b = montar('Tenho R$ 50 mil e voto no Lula. Ibovespa se o Flávio ganhar o 2º turno?')
    assert [(x.titulo, [ln.texto for ln in x.linhas]) for x in a.blocos] == \
           [(x.titulo, [ln.texto for ln in x.linhas]) for x in b.blocos]
    assert '50 mil' not in b.texto and 'R$ 50' not in b.texto
    assert T.POR_PEDIDO['capital'] in b.texto and T.VOTO_INFORMADO in b.texto


def test_caso_principal_tem_as_partes_da_nota():
    r = montar('Ibovespa: chance de subir se o Flávio ganhar o 2º turno? Como eu abordo?')
    titulos = ' | '.join(b.titulo for b in r.blocos)
    assert 'A economia hoje' in titulos and 'turnos presidenciais' in titulos
    assert 'Taxa-base' in r.texto and 'Leitura do estudo (interpretação, não fato)' in r.texto
    assert len(r.curta) == 3


def test_numero_sem_fonte_e_barrado_e_arredondamento_passa():
    fatos = 'Ibovespa +4,57% em 08/10/2018; Ibovespa a 208.296 pontos; Selic de 13,75%.'
    assert numeros_sem_fonte('O Ibovespa subiu 4,6% e está em 208 mil pontos; Selic 13,75%.', fatos) == []
    assert numeros_sem_fonte('A Selic vai a 11,25% e o índice a 250 mil.', fatos) == ['11,25', '250']


def test_resposta_sem_aviso_ou_sem_fonte_falha():
    regras = {v.regra for v in checar('O Ibovespa subiu 4,57% no mini-índice e no bitcoin.', 'Ibovespa +4,57%')}
    assert {'D1', 'D2', 'D3', 'D4', 'D5'} <= regras


def test_roteador_separa_candidato_de_mercado():
    p = analisar('Quais as chances do dólar cair se o Lula ganhar? E as chances de ele ganhar?')
    assert p.mercados == ['dolar'] and p.candidatos == ['lula'] and p.eleicao
    assert {'direcao', 'chance_candidato'} <= set(p.proibidos)
    conta = analisar('Se eu tiver 2 contratos de WIN e o índice andar 1.500 pontos, quanto dá?')
    assert conta.conta and conta.pontos == 1500 and conta.contratos == 2 and 'capital' not in conta.proibidos


def test_candidatos_sempre_os_dois_em_ordem_alfabetica(tmp_path, monkeypatch):
    dados = {'conferido_em': '22/10/2026', 'candidatos': [
        {'nome': 'Luiz Inácio Lula da Silva', 'partido': 'PT', 'historico': 'Presidente desde 2023.',
         'historico_fonte_url': 'https://exemplo/l', 'programa_tse_url': 'https://tse/l', 'programa_tse_confirmado': True,
         'pontos_economia': [{'tema': 'regra fiscal', 'o_que_diz': 'Mantém o arcabouço.', 'tipo': 'programa registrado',
                              'data': '15/08/2026', 'fonte_url': 'https://tse/l'}]},
        {'nome': 'Flávio Bolsonaro', 'partido': 'PL', 'historico': 'Senador desde 2019.',
         'historico_fonte_url': 'https://exemplo/f', 'programa_tse_url': 'https://tse/f', 'programa_tse_confirmado': True,
         'pontos_economia': [{'tema': 'regra fiscal', 'o_que_diz': 'Meta de superávit.', 'tipo': 'programa registrado',
                              'data': '15/08/2026', 'fonte_url': 'https://tse/f'}]}]}
    (tmp_path / 'candidatos_2026.json').write_text(json.dumps(dados), encoding='utf-8')
    monkeypatch.setattr(F, 'AGENTE', tmp_path)
    texto = montar('O que o Lula pensa de economia?').texto
    assert texto.index('Flávio Bolsonaro (PL)') < texto.index('Luiz Inácio Lula da Silva (PT)')


def _mensagem(conteudo: dict | str, parada: str = 'end_turn'):
    texto = conteudo if isinstance(conteudo, str) else json.dumps(conteudo)
    uso = SimpleNamespace(to_dict=lambda: {'input_tokens': 10, 'output_tokens': 20})
    blocos = [SimpleNamespace(type='thinking', thinking=''), SimpleNamespace(type='text', text=texto)]
    return SimpleNamespace(content=blocos, stop_reason=parada, usage=uso, model='claude-opus-5-5')


class ClienteFalso:
    def __init__(self, resposta):
        self.pedidos = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))
        self._resposta = resposta

    def _create(self, **pedido):
        self.pedidos.append(pedido)
        return self._resposta(pedido)


def _leitura(**k):
    base = {'mercados': [], 'candidatos': [], 'temas': [], 'proibidos': [], 'voto_informado': False}
    return base | k


def test_ia_le_o_que_as_palavras_nao_pegam_e_nao_escreve_a_resposta():
    pergunta = 'E o verdinho, aguenta firme com o barba lá?'  # gíria: dólar e Lula
    assert T.RECUSA not in montar(pergunta).texto
    leitura = _leitura(mercados=['dolar'], candidatos=['lula'], temas=['eleicao'], proibidos=['direcao'])
    cliente = ClienteFalso(lambda p: _mensagem(leitura))
    r, ia, uso = responder(pergunta, cliente)
    assert r.modo.startswith('IA') and ia['erro'] is None and uso['output_tokens'] == 20
    assert T.RECUSA in r.texto and 'turnos presidenciais' in r.texto and r.violacoes == []
    pedido = cliente.pedidos[0]
    assert pedido['output_config']['format']['type'] == 'json_schema'
    assert pedido['system'][0]['cache_control'] == {'type': 'ephemeral'}
    assert pedido['fallbacks'] == 'default' and pedido['betas'] == ['server-side-fallback-2026-07-01']


def test_ia_nao_tira_recusa_que_as_palavras_acharam():
    r, _, _ = responder('compro?', ClienteFalso(lambda p: _mensagem(_leitura())))
    assert T.RECUSA in r.texto and 'dica' in r.pedido.proibidos


def test_ia_nao_inventa_rotulo():
    leitura = _leitura(proibidos=['inventado', 'dica'], mercados=['marte'])
    r, ia, _ = responder('Copom', ClienteFalso(lambda p: _mensagem(leitura)))
    assert ia['leitura']['proibidos'] == ['dica'] and ia['leitura']['mercados'] == []


@pytest.mark.parametrize('conteudo,parada', [(_leitura(proibidos=['dica']), 'refusal'), ('não é json', 'end_turn'),
                                             ('[1, 2]', 'end_turn'), (_leitura(), 'max_tokens')])
def test_ia_que_falha_cai_nas_palavras_chave(conteudo, parada):
    r, ia, _ = responder(PERGUNTA, ClienteFalso(lambda p: _mensagem(conteudo, parada)))
    assert ia['erro'] and ia['leitura'] is None and r.modo.startswith('palavras-chave')
    assert r.texto == montar(PERGUNTA).texto


PERGUNTA = 'Ibovespa: chance de subir se o Flávio ganhar o 2º turno?'


def test_registro_tira_valor_e_voto(tmp_path):
    limpo = sem_dado_pessoal('Tenho R$ 5 mil e voto no Lula, sou petista.')
    assert '5 mil' not in limpo and 'Lula' not in limpo and 'petista' not in limpo
    r = montar('Tenho R$ 5 mil e eu voto no Flávio Bolsonaro. Quantos contratos de WIN?')
    linha = registrar(r, None, arquivo=tmp_path / 'c.jsonl')
    gravado = (tmp_path / 'c.jsonl').read_text(encoding='utf-8')
    assert '5 mil' not in gravado and 'voto no' not in gravado and linha['roteador']['proibidos']


ATAQUE_FILTRO = json.loads((Path(__file__).parent / 'dados' / 'filtro_ataque_22-10-2026.json').read_text(encoding='utf-8'))
ATAQUE_ROTEADOR = json.loads((Path(__file__).parent / 'dados' / 'roteador_ataque_22-10-2026.json').read_text(encoding='utf-8'))


@pytest.mark.parametrize('frase', ATAQUE_FILTRO['barrar'])
def test_filtro_barra_o_que_o_ataque_achou(frase):
    assert frases_proibidas(frase), frase


@pytest.mark.parametrize('frase', ATAQUE_FILTRO['passar'])
def test_filtro_deixa_passar_o_que_e_legitimo(frase):
    assert frases_proibidas(frase) == [], frase


@pytest.mark.parametrize('pergunta,deve', ATAQUE_ROTEADOR['deve_recusar'], ids=[q for q, _ in ATAQUE_ROTEADOR['deve_recusar']])
def test_roteador_reconhece_o_pedido(pergunta, deve):
    p = analisar(pergunta)
    assert set(deve) <= set(p.proibidos), p.proibidos
    r = montar(pergunta)
    assert r.violacoes == [] and (T.RECUSA in r.texto or set(deve) - T.PEDEM_RECUSA)


def test_roteador_casos_de_voto_eleicao_e_sem_recusa():
    for q in ATAQUE_ROTEADOR['voto_informado']:
        assert analisar(q).voto_informado, q
    for q in ATAQUE_ROTEADOR['eleicao']:
        assert analisar(q).eleicao, q
    for q in ATAQUE_ROTEADOR['sem_recusa']:
        assert not T.PEDEM_RECUSA & set(analisar(q).proibidos), q
    for q in ATAQUE_ROTEADOR['sem_capital']:
        assert 'capital' not in analisar(q).proibidos, q


@pytest.mark.parametrize('frase', ['Tenho 5k pra investir', 'tenho cinco mil reais', 'R$5.000,00 na conta', 'uns 3 paus',
                                   'meu salário é 4 mil', 'ganho 8000 por mês', 'votei 22', 'sou bolsonarista raiz',
                                   'fiz o L', 'eu apoio o Lula', 'odeio o PT', 'o mito vai ganhar', 'voto no Flávio Bolsonaro'])
def test_registro_tira_dado_pessoal_em_varias_formas(frase):
    limpo = sem_dado_pessoal(frase)
    assert not any(x in limpo.lower() for x in ('5k', 'cinco mil', '5.000', '3 paus', '4 mil', '8000', '22', 'bolsonarista',
                                                 'fiz o l', 'lula', ' pt', 'mito', 'flávio')), limpo


VOTOS = ['Meu voto é do Tarcísio, o dólar cai?', 'vou votar no Lula, o que acontece com a bolsa?', 'Sou eleitor do Bolsonaro, e o Ibovespa?',
         'Votei 22 no primeiro turno', 'Fiz o L', 'Eu apoio o Lula, e os juros?', 'Sou eleitora do Flávio', 'Sou bolsominion',
         'Sou antipetista', 'Sou do PT', 'Votarei 13', 'Vou de 22', 'Eu voto Lula', 'Voto Bolsonaro', 'Torço pro Flávio ganhar',
         'Fui de Lula no 1º turno', 'Meu candidato é o Flávio', 'Lula 13 sempre', 'Fora Lula! O dólar cai?', 'Voto no Luiz Inácio Lula da Silva']
VALORES = ['tenho 20k pra investir', 'com 3 mil dá pra começar?', 'Tenho cinco mil reais', 'Com meu salário de 4 mil dá pra operar WIN?',
           'Coloco 20 mil em dólar?', 'Minha reserva é de 30 mil', 'Herdei 1,5 milhão', 'Tenho US$ 2.000', 'Tenho $5k em cripto',
           'Tenho R $ 5000', 'São 5.000 pila', 'Meu FGTS de 12 mil', 'Tenho BRL 5000', 'Tenho 5 mil e quinhentos', 'Minha renda é 7000 por mês']
FICAM = ['Como o Ibovespa reagiu no 1º turno de 2018?', 'Se o WIN andar 1.000 pontos, quanto dá com 2 contratos?',
         'A Selic de 13,75% sobe?', 'O que aconteceu em 04/10/2026 com o dólar?', 'Como a bolsa reagiu à votação da PEC?']


@pytest.mark.parametrize('frase', VOTOS)
def test_registro_tira_o_voto(frase):
    limpo = sem_dado_pessoal(frase)
    assert '[trecho sobre voto omitido]' in limpo and not any(n in limpo for n in ('Lula', 'Flávio', 'Bolsonaro', 'Tarcísio', 'PT', '13', '22'))


@pytest.mark.parametrize('frase', VALORES)
def test_registro_tira_o_valor(frase):
    import re
    assert not re.search(r'\d', sem_dado_pessoal(frase).replace('[valor omitido]', '')), sem_dado_pessoal(frase)


@pytest.mark.parametrize('frase', FICAM)
def test_registro_mantem_o_que_nao_e_pessoal(frase):
    assert sem_dado_pessoal(frase) == frase


# ---------- 22/10/2026: a recusa traz o que dá para saber hoje ----------

def test_recusa_de_mercado_traz_historico_focus_e_datas():
    r = montar('devo comprar dolar hoje?', hoje='2026-10-22')
    assert r.violacoes == [], r.violacoes
    titulos = [b.titulo for b in r.blocos]
    assert any(t.startswith('O dólar até aqui') for t in titulos)
    assert any(t.startswith('O que o mercado espera') for t in titulos)
    assert F.CALENDARIO['titulo'] in titulos
    # a recusa fica num parágrafo só dela, e as 3 linhas são o histórico, o Focus e as datas
    # 22/10: os dois lados (quando caiu, quando subiu) entram depois do caminho do dólar
    assert (r.curta[0].startswith('O dólar está em') and r.curta[1].startswith('Os dois lados nos últimos 12 meses')
            and r.curta[2].startswith('Os economistas que o Banco Central'))
    # contrato: a 3ª linha é a taxa-base da FGV, e a data marcada fica só na resposta completa
    w = montar('WDO sobe amanhã?', hoje='2026-10-22')
    assert w.violacoes == [] and any('97%' in x for x in w.curta) and not any(x.startswith('Datas marcadas') for x in w.curta)
    for t in (r.texto, r.texto_curto):
        assert t.count(T.AVISO) == 1 and t.count(T.RECUSA) == 1 and T.FECHO not in t
        assert t.index(T.RECUSA) < t.index('**Em 3 linhas**')


def test_focus_e_atribuido_e_mostra_que_erra():
    b = F.expectativas('dolar')
    texto = ' '.join(ln.texto for ln in b.linhas)
    assert 'mediana' in texto and 'O Focus também erra' in texto
    assert 'previsão do Thoran' in b.limites[0]
    assert frases_proibidas(texto) == []


@pytest.mark.parametrize('hoje,tem', [('2026-10-22', ['2º turno', 'Copom']), ('2026-10-26', ['Copom']),
                                      ('2026-11-05', ['Copom']), ('2028-01-01', [])])
def test_calendario_mostra_so_datas_de_hoje_em_diante(hoje, tem):
    b = F.calendario('dolar', hoje)
    if not tem:
        assert b is None
        return
    texto = ' '.join(ln.texto for ln in b.linhas)
    assert all(x in texto for x in tem) and ('2º turno' in texto) == ('2º turno' in tem)
    assert len(b.linhas) == 1 and texto.count('Copom') == 1  # uma linha, uma data de cada tipo
    # M1 e P3 (ataque legal de 22/10/2026): só a data, sem a reação de antes e sem alerta
    assert '%' not in texto and 'p.b.' not in texto and 'pergunte pelo evento' in texto
    assert not any(x in texto.lower() for x in ('atenção', 'fique de olho', 'hora de'))

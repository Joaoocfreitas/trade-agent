import sys
from datetime import date, datetime, timedelta, timezone

import pytest

from coletor import config
from coletor.gatilhos import CAMPOS, GATILHOS, chave_link, contar, de_previsao, gatilhos_do_titulo, markdown, \
    para_brasilia, selecionar

BRT = config.FUSO
PESQUISA, COPOM, TSE, DECISAO = (g.nome for g in GATILHOS)


def casa(titulo: str) -> list[str]:
    return gatilhos_do_titulo(titulo)


# --- (a) Pesquisa eleitoral ---------------------------------------------------------------------------------------

@pytest.mark.parametrize('titulo', [
    'Pesquisa Quaest mostra Flávio com 45% e Lula com 44%',
    'Quaest, 2º turno: Flávio Bolsonaro, 45%; Lula, 44%',  # sem a palavra "pesquisa": nome inequívoco basta
    'DATAFOLHA: LULA TEM 47% DOS VOTOS VÁLIDOS',
    'Registro BR-01234/2026: levantamento mostra empate no 2º turno',
    'Flávio se distancia de Lula, mas empate persiste, aponta pesquisa Futura',
    'Futura: Flávio tem 49% e Lula, 47%',
    'Flávio tem 51,1%, e Lula, 48,9% dos votos válidos, diz Meio/Ideia',
    'Pesquisa CNT/MDA: avaliação do governo piora',
    'Genial/Quaest: 47% desaprovam o governo',
    'Real Time Big Data: Flávio tem 52% dos votos válidos',
    'Paraná Pesquisas aponta empate técnico em SP',
    'Pesquisa Veritá: Flávio lidera em Minas',
])
def test_pesquisa_eleitoral_marca(titulo):
    assert PESQUISA in casa(titulo)


@pytest.mark.parametrize('titulo', [
    'IA na pesquisa acadêmica: novas ferramentas e uma velha questão metodológica',  # "pesquisa" genérica
    'Pesquisa mostra que brasileiro poupa menos',
    'Bolsa fecha em queda após divulgação de pesquisas eleitorais',  # sem instituto nem registro
    "Tesla e SpaceX discutem fusão; 'seria uma boa ideia', diz Musk",  # "ideia" é palavra comum
    'Futura ministra da Fazenda promete ajuste',
    'MDA anuncia crédito para agricultura familiar',
    'Alfa Romeo lança SUV no Brasil',
    'Registro BR-01234/2022 de pesquisa antiga',  # registro de outra eleição
])
def test_pesquisa_eleitoral_nao_marca(titulo):
    assert PESQUISA not in casa(titulo)


# --- (b) Copom e Selic --------------------------------------------------------------------------------------------

@pytest.mark.parametrize('titulo', [
    'Copom mantém Selic em 15% ao ano',
    'COPOM CORTA JUROS EM 0,5 PONTO',
    'BC eleva a Selic pela terceira vez',
    'Selic: Copom decide hoje o rumo dos juros',
    'Banco Central reduz a Selic para 14,25%',
    'Copom sobe a Selic e surpreende',
    'Como o Copom cortou em 2020 e o que mudou',  # no passado: ainda é notícia de Copom
])
def test_copom_marca(titulo):
    assert COPOM in casa(titulo)


@pytest.mark.parametrize('titulo', [
    'Selic a 15% encarece o crédito imobiliário',  # Selic sem decisão
    'Focus: mercado projeta Selic de 14% no fim de 2026',
    'Juros futuros sobem com eleição no radar',  # decisão sem Copom nem Selic
    'Governo anuncia corte de gastos',
])
def test_copom_nao_marca(titulo):
    assert COPOM not in casa(titulo)


# --- (c) Resultado oficial do TSE ---------------------------------------------------------------------------------

@pytest.mark.parametrize('titulo', [
    'TSE conclui a totalização dos votos do 2º turno',
    'TSE: Flávio Bolsonaro é eleito presidente',
    'Apuração do TSE chega a 99% das urnas',
    'Resultado oficial do TSE confirma reeleição',
    'Justiça Eleitoral divulga resultado do 2º turno',
])
def test_tse_marca(titulo):
    assert TSE in casa(titulo)


@pytest.mark.parametrize('titulo', [
    'TSE registra pesquisa eleitoral para o 2º turno',  # "eleitoral" não é "eleito"
    'TSE vai apurar denúncia contra campanha',  # "apurar" é investigar
    'Eleitores do DF votam em nova seção, decide TSE',
    'Flávio Bolsonaro é eleito presidente',  # resultado sem o TSE
])
def test_tse_nao_marca(titulo):
    assert TSE not in casa(titulo)


# --- (d) Decisão fiscal ou judicial × mercado ---------------------------------------------------------------------

@pytest.mark.parametrize('titulo', [
    'Lula zera imposto da gasolina / Flávio acusa uso da Petrobras',  # manchete real de 21/10/2026
    'Câmara aprova PEC e Ibovespa sobe',
    'STF suspende decreto do IOF e dólar cai',
])
def test_decisao_marca(titulo):
    assert DECISAO in casa(titulo)


@pytest.mark.parametrize('titulo', [
    'Ibovespa cai 0,86% após pesquisa Quaest',  # eleição × bolsa é reação, não decisão
    'Papel do BNDES terá de ser repensado por falta de margem fiscal, dizem analistas',  # sem ato de decisão
    'STF julga recurso sobre guarda de animais',  # decisão sem mercado
    'Dólar sobe com exterior',  # mercado sem decisão
])
def test_decisao_nao_marca(titulo):
    assert DECISAO not in casa(titulo)


def test_gatilhos_tem_nome_legivel_e_regra():
    assert len({g.nome for g in GATILHOS}) == len(GATILHOS) >= 4
    assert all(g.nome and g.regra for g in GATILHOS)


# --- Mercado de previsão e aposta ---------------------------------------------------------------------------------

@pytest.mark.parametrize('titulo', [
    'Polymarket dá 60% de chance a Flávio após Datafolha',  # cairia em pesquisa: o descarte vence
    'Kalshi passa a listar contrato sobre o Copom; Selic mantida em 15%',
    'PredictIt e mercados de previsão erram o 1º turno, aponta Quaest',
    'Casas de apostas lucram com a eleição',
    'Quanto paga a aposta no Lula nas bets',
    'Lula anuncia proibição das bets; Copom mantém Selic',
])
def test_previsao_e_aposta_descartadas(titulo):
    assert casa(titulo) == []


def test_previsao_por_categoria_e_por_site():
    assert de_previsao({'categoria': 'mercados_previsao', 'titulo': 'Datafolha: Lula 47%', 'url': 'https://x.com/a'})
    assert de_previsao({'categoria': 'imprensa_br', 'titulo': 'Datafolha', 'url': 'https://polymarket.com/event/br'})
    assert de_previsao({'categoria': 'imprensa_br', 'titulo': 'Datafolha', 'url': 'https://news.kalshi.com/p'})
    assert not de_previsao({'categoria': 'imprensa_br', 'titulo': 'Apostila do Enem sai hoje', 'url': 'https://g1.com/a'})


# --- Seleção: janela, fuso, deduplicação ---------------------------------------------------------------------------

DESDE = datetime(2026, 10, 21, 12, 0, tzinfo=BRT)
ATE = datetime(2026, 10, 22, 0, 0, tzinfo=BRT)


def item(titulo, url, coletado, publicado=None, **extra):
    return {'fonte': extra.pop('fonte', 'Folha de S.Paulo'), 'categoria': 'imprensa_br', 'acesso': 'eu_busco',
            'tipo': 'item', 'url': url, 'feed': 'https://feeds.folha.uol.com.br/poder/rss091.xml', 'titulo': titulo,
            'resumo': 'RESUMO DO FEED QUE NAO PODE SAIR', 'publicado': publicado, 'coletado_em': coletado,
            'status': 'resumo', 'podcast': False, 'palavras': 0, 'assuntos': [], **extra}


def test_janela_compara_utc_e_brasilia_no_mesmo_relogio():
    itens = [
        # 02:30 UTC de 22/10 = 23:30 de 21/10 em Brasília: dentro da janela, embora a data do texto seja 22
        item('Datafolha: Lula 47%', 'https://a.com/1', '2026-10-22T02:30:00+00:00'),
        # 14:00 UTC = 11:00 em Brasília: antes da janela, embora o texto diga 14h
        item('Quaest: Flávio 45%', 'https://a.com/2', '2026-10-21T14:00:00+00:00'),
        item('Palver: empate', 'https://a.com/3', '2026-10-21T12:00:00-03:00'),  # exatamente no início: entra
        item('Gerp: Flávio 53%', 'https://a.com/4', '2026-10-22T00:00:00-03:00'),  # exatamente no fim: fica de fora
        item('Ipec: Lula 48%', 'https://a.com/5', '2026-10-21T15:00:00'),  # sem fuso: horário de Brasília
    ]
    links = {s['link'] for s in selecionar(itens, DESDE, ATE)}
    assert links == {'https://a.com/1', 'https://a.com/3', 'https://a.com/5'}


def test_janela_aceita_limites_sem_fuso_como_brasilia():
    itens = [item('Datafolha: Lula 47%', 'https://a.com/1', '2026-10-21T13:00:00-03:00')]
    assert len(selecionar(itens, datetime(2026, 10, 21, 12), datetime(2026, 10, 22))) == 1
    assert selecionar(itens, datetime(2026, 10, 21, 14), datetime(2026, 10, 22)) == []


def test_quando_vem_da_publicacao_em_brasilia_ou_da_coleta():
    itens = [item('Datafolha: Lula 47%', 'https://a.com/1', '2026-10-21T18:00:00-03:00', '2026-10-21T20:46:01+00:00'),
             item('Quaest: Flávio 45%', 'https://a.com/2', '2026-10-21T18:00:00-03:00', None)]
    quando = {s['link']: s['quando'] for s in selecionar(itens, DESDE, ATE)}
    assert quando == {'https://a.com/1': '2026-10-21T17:46:01-03:00', 'https://a.com/2': '2026-10-21T18:00:00-03:00'}
    assert para_brasilia('2026-10-21T20:46:01Z') == datetime(2026, 10, 21, 17, 46, 1, tzinfo=BRT)
    assert para_brasilia('lixo') is None and para_brasilia(None) is None


def test_item_ja_visto_antes_da_janela_nao_e_novo():
    # falha passageira: o mesmo link volta ao índice numa rodada seguinte, mas foi coletado antes da janela
    itens = [item('Datafolha: Lula 47%', 'https://a.com/1', '2026-10-21T08:00:00-03:00', status='erro'),
             item('Datafolha: Lula 47%', 'https://a.com/1', '2026-10-21T14:00:00-03:00')]
    assert selecionar(itens, DESDE, ATE) == []


def test_manchete_velha_indexada_agora_fica_de_fora():
    itens = [item('Copom mantém Selic em 15%', 'https://a.com/1', '2026-10-21T18:00:00-03:00', '2026-10-01T10:00:00+00:00'),
             item('Copom corta juros', 'https://a.com/2', '2026-10-21T18:00:00-03:00', '2026-10-21T01:00:00-03:00')]
    assert [s['link'] for s in selecionar(itens, DESDE, ATE)] == ['https://a.com/2']


def test_pagina_e_item_sem_link_ou_titulo_ficam_de_fora():
    itens = [item('Datafolha — Pesquisas eleitorais', 'https://datafolha.folha.uol.com.br', '2026-10-21T18:00:00-03:00',
                  tipo='pagina'),
             item('Datafolha: Lula 47%', '', '2026-10-21T18:00:00-03:00'),
             item('', 'https://a.com/3', '2026-10-21T18:00:00-03:00')]
    assert selecionar(itens, DESDE, ATE) == []


def test_sem_repetir_link_nem_titulo():
    itens = [
        item('Quaest: Flávio tem 45%', 'https://a.com/1', '2026-10-21T13:00:00-03:00', '2026-10-21T13:00:00-03:00'),
        item('Quaest: Flávio tem 45%', 'https://a.com/1/', '2026-10-21T15:00:00-03:00', '2026-10-21T15:00:00-03:00'),
        item('Quaest: Flávio tem 45%', 'https://a.com/1#comentarios', '2026-10-21T15:00:00-03:00'),
        item('QUAEST — FLAVIO TEM 45%', 'https://outro.com/x', '2026-10-21T16:00:00-03:00',  # mesmo título normalizado
             '2026-10-21T16:00:00-03:00', fonte='g1'),
        item('Datafolha: Lula 47%', 'https://b.com/2?utm_source=rss', '2026-10-21T17:00:00-03:00'),
        item('Datafolha: Lula 47% no 2º turno', 'https://b.com/2', '2026-10-21T18:00:00-03:00'),  # mesmo link
    ]
    sel = selecionar(itens, DESDE, ATE)
    assert [(s['link'], s['fonte']) for s in sel] == [('https://b.com/2?utm_source=rss', 'Folha de S.Paulo'),
                                                      ('https://a.com/1', 'Folha de S.Paulo')]  # fica a 1ª publicação
    assert chave_link('HTTPS://A.com/x/?utm_medium=rss&id=3#y') == chave_link('https://a.com/x?id=3')


def test_selecao_nao_carrega_texto_do_artigo():
    itens = [item('Copom mantém Selic e Ibovespa sobe; Datafolha sai hoje', 'https://a.com/1', '2026-10-21T18:00:00-03:00',
                  arquivo='textos/imprensa_br/folha/x.md', hash='abc', status='ok', palavras=900)]
    sel = selecionar(itens, DESDE, ATE)
    assert len(sel) == 1 and set(sel[0]) == set(CAMPOS)
    assert sel[0]['gatilhos'] == [PESQUISA, COPOM]  # na ordem de GATILHOS
    assert contar(sel) == {PESQUISA: 1, COPOM: 1}


# --- Markdown -----------------------------------------------------------------------------------------------------

def test_markdown_agrupa_por_gatilho_sem_texto_do_artigo():
    itens = [
        item('Copom mantém Selic e Ibovespa sobe; Datafolha [extra] sai hoje', 'https://a.com/1',
             '2026-10-21T18:00:00-03:00', '2026-10-21T17:05:00-03:00', arquivo='textos/x.md', status='ok'),
        item('TSE conclui totalização', 'https://a.com/2 (1)', '2026-10-21T18:00:00-03:00', '2026-10-20T23:10:00-03:00'),
    ]
    md = markdown(selecionar(itens, DESDE, ATE), date(2026, 10, 21), DESDE, ATE)
    linhas = md.splitlines()
    assert linhas[0] == '# Gatilhos do dia — 21/10/2026'
    assert 'revisão' in linhas[2] and 'Nada disto vai para o usuário sem conferência' in linhas[2]
    assert 'RESUMO DO FEED' not in md and 'textos/x.md' not in md
    assert f'## {PESQUISA} (1)' in md and f'## {COPOM} (1)' in md and f'## {TSE} (1)' in md
    assert f'## {DECISAO}' not in md  # grupo vazio não aparece
    assert ('- [Copom mantém Selic e Ibovespa sobe; Datafolha (extra) sai hoje](https://a.com/1) — Folha de S.Paulo'
            f' · 17h05 · também em: {COPOM}') in linhas
    assert '- [TSE conclui totalização](<https://a.com/2 (1)>) — Folha de S.Paulo · 20/10 23h10' in linhas
    fim = md[md.index('## Como um fato entra na base'):]
    assert 'PR' in fim and 'segunda pessoa' in fim and 'fonte primária' in fim and 'Polymarket' in fim


def test_markdown_vazio_diz_numa_linha():
    md = markdown([], date(2026, 10, 21))
    corpo = [l for l in md.splitlines() if l and not l.startswith('#') and 'revisão' not in l]
    assert corpo == ['Nenhuma manchete nova casou com os gatilhos nesta janela.']
    assert '## ' not in md


# --- Subcomando -----------------------------------------------------------------------------------------------------

def test_subcomando_grava_a_lista_e_sai_com_zero(tmp_path, monkeypatch, capsys):
    from coletor import __main__ as cli
    from coletor.armazem import Armazem

    monkeypatch.setattr(config, 'COLETA_DIR', tmp_path)
    agora = datetime.now(timezone.utc)
    arm = Armazem(tmp_path)
    arm.salvar(item('Datafolha: Lula 47%', 'https://a.com/1', (agora - timedelta(hours=1)).isoformat()))
    arm.salvar(item('Quaest: Flávio 45%', 'https://a.com/2', (agora - timedelta(hours=30)).isoformat()))
    saida = tmp_path / 'lista.md'
    monkeypatch.setattr(sys, 'argv', ['coletor', 'gatilhos', '--horas', '24', '--saida', str(saida)])
    cli.main()
    out = capsys.readouterr().out
    assert '1 itens (Pesquisa eleitoral: 1)' in out and str(saida) in out
    assert 'https://a.com/1' in saida.read_text(encoding='utf-8')
    assert 'https://a.com/2' not in saida.read_text(encoding='utf-8')


def test_subcomando_sem_indice_grava_lista_vazia(tmp_path, monkeypatch, capsys):
    from coletor import __main__ as cli

    monkeypatch.setattr(config, 'COLETA_DIR', tmp_path / 'coleta')
    monkeypatch.setattr(sys, 'argv', ['coletor', 'gatilhos'])
    cli.main()  # sem SystemExit: código de saída 0
    assert '0 itens' in capsys.readouterr().out
    (arq,) = (tmp_path / 'coleta').glob('gatilhos-*.md')
    assert 'Nenhuma manchete nova' in arq.read_text(encoding='utf-8')


def test_aposta_no_sentido_figurado_continua_na_lista():
    from coletor.gatilhos import de_previsao, gatilhos_do_titulo
    titulo = 'Mercado aposta em corte da Selic pelo Copom'
    assert not de_previsao({'titulo': titulo, 'link': 'https://exemplo.com.br/x'})
    assert gatilhos_do_titulo(titulo)

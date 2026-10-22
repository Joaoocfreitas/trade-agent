from datetime import datetime

from coletor.armazem import Armazem
from coletor.cofre import gravar_resumo, resumo_coleta
from coletor.config import FUSO

REG = dict(fonte='InfoMoney', categoria='imprensa_br', acesso='eu_busco', tipo='artigo', url='https://x.com/a',
           titulo='Ibovespa [recorde]', resumo='', publicado='2026-10-21T12:00:00-03:00',
           coletado_em='2026-10-21T15:00:00-03:00', status='ok', http=200, assuntos=['Bolsa'])


def test_armazem_grava_texto_dedupa_e_sobrevive_a_reabertura(tmp_path):
    arm = Armazem(tmp_path)
    reg = arm.salvar(REG, 'texto da matéria')
    assert (tmp_path / reg['arquivo']).read_text(encoding='utf-8').endswith('texto da matéria\n')
    assert reg['arquivo'].startswith('textos/imprensa_br/infomoney/2026-10-21-ibovespa-recorde-')
    assert arm.ja_visto('https://x.com/a')
    assert Armazem(tmp_path).ja_visto('https://x.com/a')


def test_falha_passageira_e_tentada_de_novo_ate_tres_vezes(tmp_path):
    arm = Armazem(tmp_path)
    erro = {**REG, 'url': 'https://x.com/e', 'status': 'erro', 'http': None}
    for _ in range(2):
        arm.salvar(erro)
    assert not Armazem(tmp_path).ja_visto('https://x.com/e')
    arm.salvar({**erro, 'status': 'bloqueado', 'http': 429})
    assert Armazem(tmp_path).ja_visto('https://x.com/e')
    arm.salvar({**REG, 'url': 'https://x.com/p', 'status': 'paywall'})
    assert Armazem(tmp_path).ja_visto('https://x.com/p')  # paywall é definitivo: não insiste


def test_indice_com_linha_corrompida_nao_trava_e_a_proxima_gravacao_nao_cola(tmp_path):
    Armazem(tmp_path).salvar(REG)
    with (tmp_path / 'itens.jsonl').open('a', encoding='utf-8') as f:
        f.write('{"url": "https://x.com/meio-gravad')  # rodada interrompida
    arm = Armazem(tmp_path)
    assert arm.ja_visto('https://x.com/a')
    arm.salvar({**REG, 'url': 'https://x.com/b'})
    assert {r['url'] for r in Armazem(tmp_path).registros()} == {'https://x.com/a', 'https://x.com/b'}


def test_pagina_e_lembrada_por_fonte_e_so_regravada_quando_muda(tmp_path):
    arm = Armazem(tmp_path)
    pag = {**REG, 'tipo': 'pagina', 'url': 'https://d.org/cartas', 'publicado': None}
    arm.salvar(pag, 'carta de setembro')
    reaberto = Armazem(tmp_path)
    assert not reaberto.pagina_mudou('InfoMoney', 'https://d.org/cartas', 'carta  de\nsetembro')  # só espaço mudou
    assert reaberto.pagina_mudou('InfoMoney', 'https://d.org/cartas', 'carta de outubro')
    assert reaberto.pagina_mudou('Outra Fonte', 'https://d.org/cartas', 'carta de setembro')  # a mesma página, outra fonte


def test_cruzamento_mercado_politica_vem_primeiro_e_ordena_por_relevancia():
    quando = datetime(2026, 10, 21, 15, 0, tzinfo=FUSO)
    fofoca = {**REG, 'url': 'https://x.com/f', 'titulo': 'Atriz comenta debate', 'assuntos': ['Eleição 2026'],
              'status': 'resumo', 'publicado': '2026-10-21T23:00:00-03:00'}
    mercado = {**REG, 'url': 'https://x.com/m', 'titulo': 'Ibovespa cai após Quaest', 'assuntos': ['Eleição 2026', 'Bolsa'],
               'publicado': '2026-10-21T20:00:00-03:00'}
    md = resumo_coleta([fofoca, mercado], [], quando, set())
    assert '## Mercado × política (1)' in md
    assert md.index('## Mercado × política') < md.index('## Assuntos do momento')
    bloco = md.split('### Eleição 2026 (2)')[1]
    assert bloco.index('Ibovespa cai após Quaest') < bloco.index('Atriz comenta debate')  # mais nova, mas menos relevante


def test_resumo_liga_fontes_existentes_e_lista_pendencias():
    quando = datetime(2026, 10, 21, 15, 0, tzinfo=FUSO)
    novos = [{**REG, 'arquivo': 'textos/x.md'}, {**REG, 'fonte': 'Sem Nota', 'url': 'https://y.com', 'status': 'resumo', 'assuntos': []}]
    falhas = [{'fonte': 'Valor Econômico', 'url': 'https://valor.globo.com/x', 'status': 'paywall', 'detalhe': None}]
    md = resumo_coleta(novos, falhas, quando, {'InfoMoney', 'Valor Econômico', 'Coleta — como funciona'})
    assert '**TL;DR: 2 itens novos de 2 fontes, 1 com texto completo guardado.' in md
    assert 'Como funciona: [[Coleta — como funciona]] · Voltar: 🧠 Mega Brain — Trade' in md  # sem nota, sem link quebrado
    assert '### Bolsa (1)' in md
    assert '- [Ibovespa (recorde)](https://x.com/a) — [[InfoMoney]] · 2026-10-21 · 📄 texto completo' in md
    assert '> **Sem Nota** (1)' in md
    assert '| [[Valor Econômico]] | paywall: só assinante lê | [abrir](https://valor.globo.com/x) |' in md


def test_duas_rodadas_no_mesmo_minuto_nao_se_apagam(tmp_path):
    quando = datetime(2026, 10, 21, 15, 0, tzinfo=FUSO)
    a = gravar_resumo(tmp_path, 'primeira', quando)
    b = gravar_resumo(tmp_path, 'segunda', quando)
    assert a != b and a.read_text(encoding='utf-8') == 'primeira'
    assert gravar_resumo(tmp_path, 'refeita', quando, substituir=True) == a

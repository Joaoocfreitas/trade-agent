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


def test_eventos_tem_fonte_primaria_e_tema():
    assert len(PETROLEO['eventos']) == 50
    for e in PETROLEO['eventos']:
        assert e['fonte']['url'].startswith('http') and e['tema'] in PETROLEO['temas'], e


def test_reacao_do_brent_bate_com_a_pesquisa():
    """A reação calculada no código (EIA, 1º dia com cotação a partir do dia da reação) bate com a da pesquisa conferida,
    até a 1ª casa, nos eventos de dia certo."""
    calc = {e['data'] + e['titulo']: e for e in F._reacao_petroleo()}
    bate = total = 0
    for e, r in zip(F._reacao_petroleo(), PESQUISA):
        assert e['data'] == r['data']
        if e['reacao_incerta'] or not r['brent_dia0_pct']:
            continue
        total += 1
        bate += abs(round(e['brent'], 1) - float(r['brent_dia0_pct'].split()[0])) <= 0.11
    assert total >= 35 and bate / total >= 0.9, (bate, total)
    del calc


@pytest.mark.parametrize('tema', ['', 'petrobras', 'opep', 'guerra', 'governo', 'choque'])
def test_bloco_de_eventos_mostra_todos_os_do_tema(tema):
    b = F.petroleo_eventos(tema)
    esperados = [e for e in PETROLEO['eventos'] if not tema or e['tema'] == tema]
    assert sum(1 for ln in b.linhas if ': no dia da reação' in ln.texto) == len(esperados)  # todos, nunca os maiores
    assert any('licença de dados da B3' in x for x in b.limites)
    for ln in b.linhas:
        assert frases_proibidas(ln.texto) == [], ln.texto


@pytest.mark.parametrize('pergunta, tema', [('vale a pena comprar Petrobras?', 'petrobras'), ('o que a OPEP fez?', 'opep'),
                                            ('o petróleo vai subir com a guerra?', 'guerra'),
                                            ('o imposto do diesel mudou?', 'governo'), ('como o petróleo chega na bomba?', '')])
def test_tema_do_petroleo(pergunta, tema):
    assert 'petroleo' in analisar(pergunta).mercados
    assert F.tema_petroleo(normalizar(pergunta)) == tema


@pytest.mark.parametrize('pergunta', ['vale a pena comprar Petrobras?', 'o petróleo vai subir com a guerra?',
                                      'quais ações de petróleo comprar?', 'compro PETR4 amanhã?'])
def test_pedido_de_dica_em_petroleo_recebe_recusa_e_os_dois_lados(pergunta):
    r = montar(pergunta, hoje='2026-10-23')
    assert r.violacoes == [], r.violacoes
    assert T.RECUSA in r.abertura
    assert any(b.titulo.startswith(F.TITULO_DOIS_LADOS) for b in r.blocos)


def test_petroleo_nao_puxa_o_bloco_de_geopolitica_que_so_mede_o_ibovespa():
    r = montar('o petróleo vai subir com a guerra?', hoje='2026-10-23')
    assert not any(b.titulo.startswith('O que aconteceu antes: geopolítica') for b in r.blocos)
    assert r.curta[0].startswith('O petróleo Brent está em US$')
    assert 'geopolitico' in analisar('Tarifas dos EUA e o Ibovespa').temas


def test_barril_bomba_conta_em_reais():
    b = F.barril_bomba()
    conta = b.linhas[-1].texto
    assert 'por litro de petróleo cru' in conta and '158,987 litros' in conta


def test_portao_do_brent_segura_o_salto_suspeito():
    s = F.serie('brent')
    velha, nova = s[s.index <= '2026-10-01'], s[s.index <= '2026-10-02']
    assert any('salto' in m for m in conferir('brent', velha, nova, pd.Timestamp('2026-10-02')))

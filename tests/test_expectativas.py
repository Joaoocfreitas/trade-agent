"""O leitor do Focus e da agenda do Copom (estudo/expectativas.py): funções puras, sem rede."""
import pytest

from estudo.expectativas import ler_agenda, ler_anual, ler_proxima_reuniao, url_anual


def test_indicador_vai_com_acento_em_utf8_e_ano_entre_aspas():
    u = url_anual('Câmbio', 2026, '2025-12-31')
    assert "C%C3%A2mbio" in u and "DataReferencia%20eq%20'2026'" in u and "Data%20le%20'2025-12-31'" in u


def test_lista_vazia_e_falha_e_nao_sem_expectativa():
    with pytest.raises(ValueError):
        ler_anual([])


def test_proxima_reuniao_ordena_por_ano_e_numero_e_nao_como_texto():
    regs = [{'Data': '2026-10-16', 'Reuniao': r, 'Mediana': m, 'numeroRespondentes': 100}
            for r, m in (('R1/2027', 13.0), ('R7/2026', 13.5), ('R8/2026', 13.25))]
    regs.append({'Data': '2026-10-15', 'Reuniao': 'R7/2026', 'Mediana': 99.0, 'numeroRespondentes': 1})
    assert ler_proxima_reuniao(regs)['reuniao'] == 'R7/2026' and ler_proxima_reuniao(regs)['mediana'] == 13.5


def test_agenda_junta_os_dois_dias_e_a_decisao_e_o_segundo():
    ev = lambda d: {'evento': 'Reunião do Copom', 'dataEvento': f'{d}T03:00:00Z'}  # noqa: E731
    r = ler_agenda({'conteudo': [ev('2026-11-03'), ev('2026-11-04'), ev('2026-12-08'), ev('2026-12-09'),
                                 {'evento': 'Outra coisa', 'dataEvento': '2026-11-10T11:00:00Z'}]})
    assert r == [{'inicio': '2026-11-03', 'decisao': '2026-11-04'}, {'inicio': '2026-12-08', 'decisao': '2026-12-09'}]
    with pytest.raises(ValueError):
        ler_agenda({'conteudo': [ev('2026-11-03')]})

"""O gerador do cofre roda como script; aqui ele roda de verdade numa pasta temporária."""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / 'scripts' / 'gerar_cofre.py'
FONTE = dict(nome='Valor Econômico', tipo='jornal', subgrupo='Economia e mercado', quem_e='Jornal.', por_que_importa='x',
             o_que_extrair='x', acesso='misto', acesso_detalhe='x', frequencia='diária', url='https://valor.globo.com',
             prioridade=1, relacionados=[], cuidado='', verificado='confirmado', fonte_verificacao='')


def _gerar(dados: Path, cofre: Path) -> dict:
    r = subprocess.run([sys.executable, str(SCRIPT), str(dados), str(cofre)], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def _dados_completos(pasta: Path, fontes: dict[str, list]) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    for chave in ('pessoas_br_mercado', 'pessoas_br_politica', 'pessoas_global', 'imprensa_br', 'imprensa_global',
                  'programas', 'dados', 'politica', 'mercados_previsao', 'metodo', 'acrescimos'):
        (pasta / f'{chave}.json').write_text(json.dumps({'itens': fontes.get(chave, [])}), encoding='utf-8')
    (pasta / 'linha-do-tempo.json').write_text(json.dumps({'eventos': []}), encoding='utf-8')
    (pasta / 'caso-1turno.md').write_text('**TL;DR: caso**', encoding='utf-8')
    (pasta / 'segundo-turno.md').write_text('**TL;DR: 2º turno**', encoding='utf-8')


def test_contexto_recebido_sobrevive_a_regeneracao_e_a_mudanca_de_pasta(tmp_path):
    dados, cofre = tmp_path / 'dados', tmp_path / 'cofre'
    _dados_completos(dados, {'pessoas_br_politica': [FONTE]})  # primeiro cai na pasta errada
    _gerar(dados, cofre)
    nota = cofre / '1 Pessoas' / 'Brasil — política e colunistas' / 'Valor Econômico.md'
    nota.write_text(nota.read_text(encoding='utf-8').replace('_Vazio.', '2026-10-21 — carta recebida. MARCADOR\n\n_Vazio.'), encoding='utf-8')

    _dados_completos(dados, {'imprensa_br': [FONTE]})  # agora vai para a pasta certa
    rel = _gerar(dados, cofre)
    nova = cofre / '2 Imprensa' / 'Brasil' / 'Valor Econômico.md'
    assert 'MARCADOR' in nova.read_text(encoding='utf-8')
    assert not nota.exists()
    assert rel['mantidos_com_contexto'] == []


def test_entrada_faltando_nao_apaga_nada(tmp_path):
    dados, cofre = tmp_path / 'dados', tmp_path / 'cofre'
    _dados_completos(dados, {'imprensa_br': [FONTE]})
    _gerar(dados, cofre)
    (dados / 'imprensa_br.json').unlink()
    rel = _gerar(dados, cofre)
    assert (cofre / '2 Imprensa' / 'Brasil' / 'Valor Econômico.md').exists()
    assert rel['removidos_obsoletos'] == []
    assert 'imprensa_br.json' in rel['entradas_ausentes (limpeza pulada)']

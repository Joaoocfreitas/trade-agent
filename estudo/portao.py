"""O portão da rodada diária: série nova só entra se passar nas travas; na dúvida, fica a de ontem, com a data de ontem.

Travas por série (dados/series/<nome>.csv), sempre contra a versão aceita antes:
- formato: datas em ordem, sem repetição, sem data futura, valores finitos; a série não pode encolher;
- histórico intacto: o que já estava aceito não muda (as mensais aceitam revisão nos últimos meses);
- faixa absoluta e salto máximo de um ponto para o seguinte, só nos pontos novos;
- Selic: múltiplo de 0,25; Ibovespa: valor inteiro e dia útil (o Ipeadata já publicou fim de semana e centavos falsos);
- interruptor em dados/series/ligadas.json: série desligada não muda (o Ibovespa começa desligado até o advogado
  responder sobre a licença de dados da B3).
O Focus (dados/series/focus.json) passa por travas próprias: data que não volta, medianas em faixa, agenda do Copom.
"""
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

# faixa absoluta; salto máximo entre pontos seguidos (em % ou em unidade da série); revisão aceita nos últimos dias.
# Calibrado contra 2016–2026 (22/10/2026): segura só dias extremos de verdade, como 18/05/2017 (Joesley), março de 2020
# (covid), 19 e 20/12/2024 (juros) e 05/10/2026 (dólar −4,55% depois do 1º turno). Nesses dias, a pessoa confere na
# fonte e libera rodando a rodada à mão com a série em ACEITAR.
TRAVAS = {
    'ptax': {'faixa': (2.0, 15.0), 'salto_pct': 4.0, 'revisao_dias': 7},
    'selic_meta': {'faixa': (2.0, 30.0), 'salto_abs': 1.5, 'multiplo': 0.25, 'revisao_dias': 7},
    'ipca_12m': {'faixa': (-5.0, 30.0), 'salto_abs': 1.5, 'revisao_dias': 100},
    'divida_bruta': {'faixa': (40.0, 150.0), 'salto_abs': 3.0, 'revisao_dias': 100},
    'ibov': {'faixa': (20_000.0, 500_000.0), 'salto_pct': 6.0, 'inteiro': True, 'dia_util': True, 'revisao_dias': 7},
    'ibov_bcb': None,  # só conferência histórica do estudo (o SGS 7 parou em 2019): não entra na resposta
    'pre_2a': {'faixa': (3.0, 30.0), 'salto_abs': 1.0, 'revisao_dias': 7},
    'pre_5a': {'faixa': (3.0, 30.0), 'salto_abs': 1.0, 'revisao_dias': 7},
}
FAIXAS_FOCUS = {'Selic': (2.0, 30.0), 'IPCA': (-5.0, 30.0), 'Câmbio': (2.0, 15.0), 'PIB Total': (-10.0, 10.0)}


@dataclass
class Resultado:
    nome: str
    situacao: str  # 'igual', 'atualizada', 'segurada', 'desligada'
    antes: str | None = None
    depois: str | None = None
    motivos: list[str] = field(default_factory=list)

    def linha(self) -> str:
        if self.situacao == 'atualizada':
            return f'- {self.nome}: atualizada, de {self.antes} até {self.depois}.'
        if self.situacao == 'igual':
            return f'- {self.nome}: sem dado novo (último: {self.antes}).'
        if self.situacao == 'desligada':
            return f'- {self.nome}: desligada em ligadas.json; fica a de {self.antes}.'
        return f'- {self.nome}: SEGURADA, fica a de {self.antes}. Motivo: ' + '; '.join(self.motivos)


def ler(caminho: Path) -> pd.Series:
    df = pd.read_csv(caminho, parse_dates=['data'], index_col='data')
    return df[df.columns[0]].astype(float)


def conferir(nome: str, velha: pd.Series, nova: pd.Series, hoje: pd.Timestamp, liberada: bool = False) -> list[str]:
    """Os motivos para segurar a série nova; lista vazia = pode entrar. `liberada`: a pessoa conferiu na fonte e aceita
    o salto (o resto das travas continua valendo)."""
    t = TRAVAS.get(nome)
    if t is None:
        return []
    m = []
    if nova.empty:
        return ['veio vazia']
    if not nova.index.is_monotonic_increasing or nova.index.has_duplicates:
        m.append('datas fora de ordem ou repetidas')
    if nova.index.max() > hoje.normalize():
        m.append(f'data no futuro: {nova.index.max().date()}')
    if not all(math.isfinite(x) for x in nova):
        m.append('valor que não é número')
    if len(nova) < len(velha):
        m.append(f'encolheu de {len(velha)} para {len(nova)} pontos')
    # histórico intacto: o que já estava aceito, até a janela de revisão, tem de vir igual
    if len(velha):
        corte = velha.index.max() - pd.Timedelta(days=t['revisao_dias'])
        a, b = velha[velha.index <= corte], nova[nova.index <= corte]
        if len(a) and not a.index.equals(b.index):
            m.append('mudaram datas do histórico já aceito')
        elif len(a):
            dif = (a - b).abs()
            limite = a.abs() * 1e-6 + 1e-9
            if (dif > limite).any():
                d = dif[dif > limite].index[0]
                m.append(f'mudou um valor do histórico já aceito ({d.date()}: {a[d]} virou {b[d]})')
    novos = nova[nova.index > velha.index.max()] if len(velha) else nova
    if len(novos):
        lo, hi = t['faixa']
        fora = novos[(novos < lo) | (novos > hi)]
        if len(fora):
            m.append(f'fora da faixa {lo}–{hi}: {fora.index[0].date()} = {fora.iloc[0]}')
        anterior = pd.concat([velha.iloc[-1:], novos]) if len(velha) else novos
        if 'salto_pct' in t and not liberada:
            salto = (anterior.pct_change().abs() * 100).dropna()
            grande = salto[salto > t['salto_pct']]
            if len(grande):
                m.append(f'salto de {grande.iloc[0]:.2f}% em {grande.index[0].date()} (limite {t["salto_pct"]}%)')
        if 'salto_abs' in t and not liberada:
            salto = anterior.diff().abs().dropna()
            grande = salto[salto > t['salto_abs'] + 1e-9]
            if len(grande):
                m.append(f'salto de {grande.iloc[0]:.2f} em {grande.index[0].date()} (limite {t["salto_abs"]})')
        if t.get('multiplo'):
            resto = ((novos / t['multiplo']) - (novos / t['multiplo']).round()).abs()
            if (resto > 1e-6).any():
                m.append(f'Selic que não é múltiplo de {t["multiplo"]}: {novos[resto > 1e-6].iloc[0]}')
        if t.get('inteiro') and ((novos - novos.round()).abs() > 1e-9).any():
            m.append('valor com centavos (o fechamento do Ibovespa é inteiro; o Ipeadata já publicou ponto falso assim)')
        if t.get('dia_util') and (novos.index.weekday >= 5).any():
            m.append(f'ponto em fim de semana: {novos.index[novos.index.weekday >= 5][0].date()}')
    return m


def conferir_focus(velho: dict | None, novo: dict) -> list[str]:
    m = []
    if velho and novo.get('data', '') < velho.get('data', ''):
        m.append(f'o boletim voltou no tempo: {novo.get("data")} antes de {velho.get("data")}')
    for chave, v in novo.get('atual', {}).items():
        ind = chave.split('|')[0]
        lo, hi = FAIXAS_FOCUS.get(ind, (-math.inf, math.inf))
        if not lo <= v['mediana'] <= hi:
            m.append(f'{chave} fora da faixa {lo}–{hi}: {v["mediana"]}')
        if v.get('respondentes', 0) < 10:
            m.append(f'{chave} com só {v.get("respondentes")} respondentes')
    if not novo.get('historico'):
        m.append('sem o histórico de erro do Focus')
    return m


def aplicar(pasta: Path, antes: Path, ligadas: dict, hoje: pd.Timestamp, aceitar: frozenset = frozenset()) -> list[Resultado]:
    """Compara cada CSV de `pasta` (recém-baixado) com a cópia em `antes` e devolve a de antes quando a nova não passa."""
    resultados = []
    for nome in TRAVAS:
        novo_csv, velho_csv = pasta / f'{nome}.csv', antes / f'{nome}.csv'
        if not velho_csv.exists():
            continue
        velha = ler(velho_csv)
        ult = str(velha.index.max().date())
        if not ligadas.get(nome, True):
            if novo_csv.exists():
                novo_csv.write_bytes(velho_csv.read_bytes())
            resultados.append(Resultado(nome, 'desligada', ult))
            continue
        if not novo_csv.exists():
            novo_csv.write_bytes(velho_csv.read_bytes())
            resultados.append(Resultado(nome, 'segurada', ult, motivos=['o download não trouxe o arquivo']))
            continue
        nova = ler(novo_csv)
        motivos = conferir(nome, velha, nova, hoje, liberada=nome in aceitar)
        if motivos:
            novo_csv.write_bytes(velho_csv.read_bytes())
            resultados.append(Resultado(nome, 'segurada', ult, motivos=motivos))
        elif nova.index.max() > velha.index.max():
            resultados.append(Resultado(nome, 'atualizada', ult, str(nova.index.max().date())))
        else:
            novo_csv.write_bytes(velho_csv.read_bytes())  # mesmo período: fica byte a byte o de antes
            resultados.append(Resultado(nome, 'igual', ult))
    f_novo, f_velho = pasta / 'focus.json', antes / 'focus.json'
    if f_velho.exists():
        velho = json.loads(f_velho.read_text(encoding='utf-8'))
        if not f_novo.exists():
            f_novo.write_bytes(f_velho.read_bytes())
            resultados.append(Resultado('focus', 'segurada', velho['data'], motivos=['o download não trouxe o arquivo']))
        else:
            novo = json.loads(f_novo.read_text(encoding='utf-8'))
            motivos = conferir_focus(velho, novo)
            if motivos:
                f_novo.write_bytes(f_velho.read_bytes())
                resultados.append(Resultado('focus', 'segurada', velho['data'], motivos=motivos))
            elif novo['data'] > velho['data'] or novo.get('agenda_copom') != velho.get('agenda_copom'):
                resultados.append(Resultado('focus', 'atualizada', velho['data'], novo['data']))
            else:
                f_novo.write_bytes(f_velho.read_bytes())
                resultados.append(Resultado('focus', 'igual', velho['data']))
    return resultados

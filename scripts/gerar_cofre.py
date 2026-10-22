#!/usr/bin/env python3
"""Gera as notas de fonte, índices, checklist e eventos do cofre Trade a partir dos JSON verificados.

Uso: .venv/bin/python scripts/gerar_cofre.py [pasta-dados] [pasta-cofre]
Só sobrescreve notas marcadas com `gerado: true`; notas escritas à mão ficam intactas.
"""
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from coletor.config import COFRE, FONTES_DIR, FUSO  # noqa: E402
from coletor.fontes import preferir  # noqa: E402
from coletor.nomes import norm, titulo_nota as safe  # noqa: E402

DATA = Path(sys.argv[1]) if len(sys.argv) > 1 else FONTES_DIR
VAULT = Path(sys.argv[2]) if len(sys.argv) > 2 else COFRE
HOJE = datetime.now(FUSO).strftime('%Y-%m-%d')

# chave -> (pasta, subpasta, título da seção)
CATS = {
    'pessoas_br_mercado': ('1 Pessoas', 'Brasil — mercado', 'Brasil — mercado'),
    'pessoas_br_politica': ('1 Pessoas', 'Brasil — política e colunistas', 'Brasil — política e colunistas'),
    'pessoas_global': ('1 Pessoas', 'Global', 'Global'),
    'imprensa_br': ('2 Imprensa', 'Brasil', 'Brasil'),
    'imprensa_global': ('2 Imprensa', 'Internacional', 'Internacional'),
    'programas': ('3 Programas e podcasts', None, 'Programas, podcasts e coletivas'),
    'dados': ('4 Dados e ferramentas', None, 'Dados, APIs e ferramentas'),
    'politica': ('5 Política e eleições', None, 'Política, eleições e Congresso'),
    'mercados_previsao': ('6 Mercados de previsão', None, 'Mercados de previsão'),
    'metodo': ('7 Ciência e regras', None, 'Ciência, método e regras'),
}
ACESSO = {
    'eu_busco': '🟢 eu busco sozinho',
    'api_gratis': '🟢 API/download grátis',
    'misto': '🟡 misto',
    'voce_me_passa': '🔴 você me passa',
}
VERIF = {'confirmado': '✅ confirmado', 'corrigido': '✏️ corrigido na verificação', 'nao_confirmado': '⚠️ não confirmado'}

written = []
skipped = []


def cell(s, n=None):
    s = (s or '').replace('\n', ' ').replace('|', '\\|').strip()
    if n and len(s) > n:
        s = s[: n - 1].rstrip() + '…'
    return s


def y(v):
    return json.dumps(v, ensure_ascii=False)


SECAO_CONTEXTO = '## Contexto recebido\n'
CONTEXTO_VAZIO = '_Vazio. Quando o João mandar material desta fonte (ver [[LEIA-ME — como me passar contexto]]), o resumo entra aqui, com data._'
ausentes = []


def contexto_de(texto):
    """O que foi escrito à mão na seção "Contexto recebido" (sempre a última da nota). None se está vazia."""
    if SECAO_CONTEXTO not in texto:
        return None
    ctx = texto.split(SECAO_CONTEXTO, 1)[1].strip()
    return ctx if ctx and ctx != CONTEXTO_VAZIO else None


def gerada(p):
    return 'gerado: true' in p.read_text(encoding='utf-8')[:600]


# Antes de reescrever qualquer coisa: o contexto que o João (ou eu) já pôs nas notas, pelo nome da nota.
# Assim ele sobrevive à regeneração e acompanha a nota se a fonte mudar de pasta.
contextos = {}
for p in VAULT.rglob('*.md') if VAULT.exists() else []:
    if gerada(p):
        ctx = contexto_de(p.read_text(encoding='utf-8'))
        if ctx:
            contextos[p.stem] = ctx


def write(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not gerada(path):
        skipped.append(str(path.relative_to(VAULT)))
        return
    ctx = contextos.get(path.stem)
    if ctx and SECAO_CONTEXTO + CONTEXTO_VAZIO in body:
        body = body.replace(SECAO_CONTEXTO + CONTEXTO_VAZIO, SECAO_CONTEXTO + ctx)
    path.write_text(body, encoding='utf-8')
    written.append(str(path.relative_to(VAULT)))


def load(name, key='itens'):
    p = DATA / name
    if not p.exists():
        print(f'AUSENTE: {name}', file=sys.stderr)
        ausentes.append(name)
        return []
    return json.loads(p.read_text(encoding='utf-8'))[key]


# ---------- fontes ----------
fontes = []
seen = {}
dups = []
for key in CATS:
    for it in load(f'{key}.json'):
        it['categoria'] = key
        fontes.append(it)
for it in load('acrescimos.json'):
    if it.get('categoria') in CATS:
        it['acrescimo'] = True
        fontes.append(it)

for it in fontes:
    it['titulo'] = safe(it['nome'])
    k = norm(it['titulo'])
    if k in seen:
        base = seen[k]
        relacionados = list(dict.fromkeys(base['relacionados'] + it['relacionados']))
        if preferir(base, it):
            base, it = it, base
            seen[k] = base
        base['relacionados'] = relacionados
        dups.append(f"{it['nome']} ({it['categoria']}) fundido em {base['nome']} ({base['categoria']})")
        continue
    seen[k] = it
fontes = list(seen.values())

index = {norm(f['titulo']): f['titulo'] for f in fontes}
by_len = sorted(index.items(), key=lambda kv: -len(kv[0]))


def resolve(rel):
    cands = [rel, re.sub(r'\s*\(.*?\)', '', rel)]
    cands += re.findall(r'\((.*?)\)', rel)
    cands += re.split(r'\s*/\s*|\s+e\s+|,\s*', rel)
    for c in cands:
        n = norm(c)
        if n in index:
            return index[n]
    n = norm(rel)
    for k, title in by_len:
        if len(k) >= 5 and re.search(rf'(^| ){re.escape(k)}( |$)', n):
            return title
    return None


def link_list(rels, self_title):
    out, alvos = [], {self_title}
    for r in rels:
        t = resolve(r)
        if t and t not in alvos:
            alvos.add(t)
            out.append(f'[[{t}]]' if norm(t) == norm(r) else f'[[{t}]] ({r})')
        elif not t:
            out.append(r)
    return list(dict.fromkeys(out))


def folder(f):
    pasta, sub, _ = CATS[f['categoria']]
    return VAULT / pasta / sub if sub else VAULT / pasta


for f in fontes:
    tags = ['fonte', f['categoria'], f['tipo'], f"acesso-{f['acesso']}", f"p{f['prioridade']}"]
    rel = link_list(f['relacionados'], f['titulo'])
    url = f['url'].strip()
    body = f"""---
gerado: true
tags: [{', '.join(tags)}]
tipo: {y(f['tipo'])}
categoria: {y(f['categoria'])}
subgrupo: {y(f['subgrupo'])}
acesso: {y(f['acesso'])}
prioridade: {f['prioridade']}
frequencia: {y(f['frequencia'])}
url: {y(url)}
verificado: {y(f['verificado'])}
atualizado: {HOJE}
---

**TL;DR: {f['quem_e'].strip()}**

| Acesso | Prioridade | Frequência | Verificação |
|---|---|---|---|
| {ACESSO[f['acesso']]} | {f['prioridade']} | {cell(f['frequencia'])} | {VERIF[f['verificado']]}{f" ([fonte]({f['fonte_verificacao']}))" if f['fonte_verificacao'].startswith('http') else ''} |

## Por que importa
{f['por_que_importa'].strip()}

## O que o agente extrai
{f['o_que_extrair'].strip()}

## Como acessar
{f['acesso_detalhe'].strip()}
{f"{chr(10)}🔗 {url}" if url else ''}

## Cuidado
{f['cuidado'].strip() or '—'}

## Ligações
{chr(10).join('- ' + r for r in rel) if rel else '—'}
- Índice: [[{CATS[f['categoria']][0]}]]

{SECAO_CONTEXTO}{CONTEXTO_VAZIO}
"""
    write(folder(f) / f"{f['titulo']}.md", body)

# ---------- índices por pasta ----------
por_pasta = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
for f in fontes:
    pasta, _, secao = CATS[f['categoria']]
    por_pasta[pasta][secao][f['subgrupo']].append(f)

for pasta, secoes in por_pasta.items():
    total = sum(len(v) for s in secoes.values() for v in s.values())
    linhas = [f"""---
gerado: true
tags: [indice, moc]
atualizado: {HOJE}
---

**TL;DR: {total} fontes verificadas em {HOJE}. 🟢 = eu leio sozinho · 🟡 = parte aberta · 🔴 = depende de você me passar. Prioridade 1 = essencial desde o dia 1.**

Voltar: [[🧠 Mega Brain — Trade]] · O que depende de você: [[O que você me passa — checklist]]
"""]
    multi = len(secoes) > 1
    for secao, grupos in secoes.items():
        if multi:
            linhas.append(f'\n## {secao}\n')
        for grupo, itens in sorted(grupos.items()):
            itens.sort(key=lambda x: (x['prioridade'], norm(x['titulo'])))
            linhas.append(f"\n{'###' if multi else '##'} {grupo}\n")
            linhas.append('| Fonte | Por que importa | Acesso | P |')
            linhas.append('|---|---|---|---|')
            for it in itens:
                linhas.append(f"| [[{it['titulo']}]] | {cell(it['por_que_importa'], 150)} | {ACESSO[it['acesso']].split(' ')[0]} | {it['prioridade']} |")
    write(VAULT / pasta / f'{pasta}.md', '\n'.join(linhas) + '\n')

# ---------- checklist do que o João passa ----------
pend = [f for f in fontes if f['acesso'] in ('voce_me_passa', 'misto')]
pend.sort(key=lambda x: (x['prioridade'], x['acesso'] != 'voce_me_passa', norm(x['titulo'])))
sozinho = [f for f in fontes if f['acesso'] in ('eu_busco', 'api_gratis')]
ck = [f"""---
gerado: true
tags: [checklist, inbox]
atualizado: {HOJE}
---

**TL;DR: de {len(fontes)} fontes, {len(sozinho)} eu leio sozinho e {len(pend)} dependem de você: {sum(1 for f in pend if f['acesso'] == 'voce_me_passa')} totalmente fechadas (🔴) e {sum(1 for f in pend if f['acesso'] == 'misto')} parcialmente (🟡). Comece pela prioridade 1. Jogue o material em `9 Inbox` ([[LEIA-ME — como me passar contexto]]).**
"""]
for p, titulo in ((1, 'Prioridade 1 — comece por estas'), (2, 'Prioridade 2'), (3, 'Prioridade 3 — quando der')):
    grupo = [f for f in pend if f['prioridade'] == p]
    if not grupo:
        continue
    ck.append(f'\n## {titulo}\n')
    for f in grupo:
        ck.append(f"- [ ] {ACESSO[f['acesso']].split(' ')[0]} **[[{f['titulo']}]]** — {f['o_que_extrair'].strip()} · _{f['acesso_detalhe'].strip()}_ · {f['frequencia']}")
write(VAULT / 'O que você me passa — checklist.md', '\n'.join(ck) + '\n')

# ---------- fontes primárias ----------
fp = [f"""---
gerado: true
tags: [referencia, fontes]
atualizado: {HOJE}
---

**TL;DR: índice de todos os links das {len(fontes)} fontes, com o estado da verificação de {HOJE}. ⚠️ = não confirmado: não usar número dessas fontes sem checar.**

| Fonte | Pasta | Acesso | Verificação | Link |
|---|---|---|---|---|"""]
for f in sorted(fontes, key=lambda x: (x['categoria'], norm(x['titulo']))):
    url = f['url'].strip()
    fp.append(f"| [[{f['titulo']}]] | {CATS[f['categoria']][0]} | {ACESSO[f['acesso']].split(' ')[0]} | {VERIF[f['verificado']].split(' ')[0]} | {f'[abrir]({url})' if url.startswith('http') else '—'} |")
write(VAULT / 'Fontes primárias.md', '\n'.join(fp) + '\n')

# ---------- eventos ----------
def pct(v):
    if v is None:
        return '—'
    return f"{v:+.2f}%".replace('.', ',')


def num(v, casas=2, sufixo='%', sinal=True):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return '—'
    if v != v:  # NaN
        return '—'
    return (f'{v:+.{casas}f}' if sinal else f'{v:.{casas}f}').replace('.', ',') + sufixo


# Medição da Fase 2 (estudo de evento com dado oficial), se já rodou: python -m estudo medir
medicoes = {}
arq_medicoes = DATA.parent / 'estudo' / 'eventos.csv'
if arq_medicoes.exists():
    import csv
    with arq_medicoes.open(encoding='utf-8') as f:
        medicoes = {(m['data'], m['evento']): m for m in csv.DictReader(f)}


def bloco_medido(m):
    if not m:
        return ''
    return f"""
## Medido com dado oficial (Fase 2)
Pregão da reação: {m['dia0']}. Fontes: Ibovespa do Ipeadata (republica a B3; 19 pontos falsos retirados), dólar PTAX e juros do Tesouro Direto. Método em [[Estudo de evento 2016–2026]].

| Série | Reação | Em "dias normais" | 5 pregões antes | 5 pregões depois |
|---|---|---|---|---|
| Ibovespa (fechamento, dia −1 → 0) | {num(m['ibov_d0'])} | {num(m['ibov_z0'], 1, '', True)} | {num(m['ibov_antes'])} | {num(m['ibov_depois'])} ({m['leitura_depois'] or '—'}) |
| Dólar PTAX (dia −1 → +1) | {num(m['ptax_d01'])} | — | — | janela inteira {num(m['ptax_janela'])} |
| Juros prefixados 5 anos (dia −1 → +1) | {num(m['pre5_d01_pb'], 0, ' pb')} | — | — | janela inteira {num(m['pre5_janela_pb'], 0, ' pb')} |
"""


eventos = sorted(load('linha-do-tempo.json', 'eventos'), key=lambda e: e['data'])
tl = [f"""---
gerado: true
tags: [eventos, linha-do-tempo]
atualizado: {HOJE}
---

**TL;DR: {len(eventos)} eventos de 2016 a 2026 que moveram o mercado brasileiro, cada um com o que se esperava antes, o tamanho da surpresa e a reação do Ibovespa e do dólar no dia. "—" = número não confirmado em fonte do dia. É o ponto de partida do estudo de evento ([[O plano em 4 fases]]) e serve para aprender o terreno, não para provar acerto ([[Look-ahead bias — por que o backtest com IA mente]]).**

A coluna **z** é a reação do Ibovespa medida com dado oficial, em "dias normais" (desvio-padrão do ano anterior): acima de 2 é um dia raro. Estudo completo: [[Estudo de evento 2016–2026]].

| Data | Evento | Tipo | Surpresa | Ibovespa | z | Dólar | Confiança |
|---|---|---|---|---|---|---|---|"""]
for e in eventos:
    nome = f"{e['data']} — {safe(e['evento'])}"
    m = medicoes.get((e['data'], e['evento']))
    tl.append(f"| {e['data']} | [[{nome}\\|{cell(e['evento'], 60)}]] | {e['tipo']} | {e['surpresa']} | {pct(e['ibov_dia_pct'])} | {num(m['ibov_z0'], 1, '') if m else '—'} | {pct(e['dolar_dia_pct'])} | {e['confianca']} |")
    fontes_md = '\n'.join(f'- {u}' for u in e['fontes']) or '—'
    write(VAULT / '8 Eventos' / '2016–2026' / f'{nome}.md', f"""---
gerado: true
tags: [evento, {e['tipo']}, surpresa-{e['surpresa']}]
data: {e['data']}
tipo: {y(e['tipo'])}
surpresa: {y(e['surpresa'])}
ibov_dia_pct: {y(e['ibov_dia_pct'])}
dolar_dia_pct: {y(e['dolar_dia_pct'])}
confianca: {y(e['confianca'])}
atualizado: {HOJE}
---

**TL;DR: {e['o_que_aconteceu'].strip()}**

| Ibovespa no dia | Dólar no dia | Surpresa | Confiança nos números |
|---|---|---|---|
| {pct(e['ibov_dia_pct'])} | {pct(e['dolar_dia_pct'])} | {e['surpresa']} | {e['confianca']} |

## O que se esperava antes
{e['o_que_se_esperava'].strip()}

## Outros ativos
{e['outros_ativos'].strip() or '—'}

## Depois
{e['depois'].strip() or '—'}

## Lição para o agente
{e['licao'].strip()}
{bloco_medido(m)}
## Fontes
{fontes_md}

Voltar: [[Linha do tempo 2016–2026]]
""")
write(VAULT / '8 Eventos' / 'Linha do tempo 2016–2026.md', '\n'.join(tl) + '\n')

for src, dst, tags in (
    ('caso-1turno.md', 'Caso — 1º turno 2026.md', '[evento, eleicao, caso]'),
    ('segundo-turno.md', '2º turno 25-10-2026 — o que já está no preço.md', '[evento, eleicao, ao-vivo]'),
):
    p = DATA / src
    if p.exists():
        md = p.read_text(encoding='utf-8').strip()
        write(VAULT / '8 Eventos' / dst, f"---\ngerado: true\ntags: {tags}\natualizado: {HOJE}\n---\n\n{md}\n\nVoltar: [[Linha do tempo 2016–2026]] · [[Surpresa vs. expectativa — de onde vem o ganho]]\n")
    else:
        print(f'AUSENTE: {src}', file=sys.stderr)
        ausentes.append(src)

# ---------- limpeza: nota gerada que não saiu nesta rodada (fonte mudou de pasta ou foi removida) ----------
# Com entrada faltando não se apaga nada: a nota pode estar fora só porque o arquivo dela não veio.
# Nota com contexto escrito só é apagada se o contexto foi levado para a nota de mesmo nome que saiu agora.
removidos, mantidos_com_contexto = [], []
escritos = set(written)
nomes_escritos = {Path(w).stem for w in written}
for p in [] if ausentes else list(VAULT.rglob('*.md')):
    rel = str(p.relative_to(VAULT))
    if rel in escritos or not gerada(p):
        continue
    if contexto_de(p.read_text(encoding='utf-8')) and p.stem not in nomes_escritos:
        mantidos_com_contexto.append(rel)
        continue
    p.unlink()
    removidos.append(rel)

# ---------- relatório ----------
cont = defaultdict(int)
for f in fontes:
    cont[f['acesso']] += 1
rep = {
    'fontes': len(fontes),
    'por_acesso': dict(cont),
    'por_pasta': {p: sum(len(v) for s in sec.values() for v in s.values()) for p, sec in por_pasta.items()},
    'eventos': len(eventos),
    'duplicatas_fundidas': dups,
    'escritos': len(written),
    'removidos_obsoletos': removidos,
    'mantidos_com_contexto': mantidos_com_contexto,
    'entradas_ausentes (limpeza pulada)': ausentes,
    'pulados_manuais': skipped,
}
(DATA / 'relatorio.json').write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps(rep, ensure_ascii=False, indent=1))

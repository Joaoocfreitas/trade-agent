"""Escreve no cofre do Obsidian o resumo de cada coleta: assuntos do momento, novidades por fonte e bloqueios."""
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from .config import CATEGORIAS
from .conteudo import MOTIVOS

ROTULO_CATEGORIA = {k: (f'{p} — {s}' if s else p) for k, (p, s) in CATEGORIAS.items()}
POR_ASSUNTO = 6
NO_CRUZAMENTO = 12
POLITICOS = frozenset({'Eleição 2026', 'Congresso', 'STF e Judiciário', 'Fiscal e orçamento'})
MERCADO = frozenset({'Bolsa', 'Câmbio', 'Juros e Copom', 'Inflação', 'Petrobras e estatais'})


def cruza(reg: dict) -> bool:
    """A tese do projeto: a notícia em que política e preço aparecem juntos."""
    a = set(reg.get('assuntos', []))
    return bool(a & POLITICOS) and bool(a & MERCADO)


def relevancia(reg: dict) -> tuple:
    a = set(reg.get('assuntos', []))
    pontos = 3 * cruza(reg) + len(a & MERCADO) + (reg.get('status') == 'ok')
    return pontos, reg.get('publicado') or ''


def notas_existentes(cofre: Path) -> set[str]:
    return {p.stem for p in cofre.rglob('*.md')} if cofre.exists() else set()


def _texto_link(s: str) -> str:
    return s.replace('[', '(').replace(']', ')').replace('\n', ' ').strip()


def _fonte(nome: str, notas: set[str]) -> str:
    return f'[[{nome}]]' if nome in notas else nome


def _linha(reg: dict, notas: set[str]) -> str:
    data = (reg.get('publicado') or '')[:10]
    extra = ' · 📄 texto completo' if reg.get('status') == 'ok' and reg.get('arquivo') else ''
    return f"- [{_texto_link(reg['titulo'])}]({reg['url']}) — {_fonte(reg['fonte'], notas)}{f' · {data}' if data else ''}{extra}"


def resumo_coleta(novos: list[dict], falhas: list[dict], quando: datetime, notas: set[str]) -> str:
    por_assunto: dict[str, list[dict]] = defaultdict(list)
    for r in novos:
        for a in r.get('assuntos', []):
            por_assunto[a].append(r)
    contagem = Counter({a: len(rs) for a, rs in por_assunto.items()})
    fontes = {r['fonte'] for r in novos}
    completos = sum(1 for r in novos if r.get('status') == 'ok' and r.get('arquivo'))
    topo = ', '.join(f'{a} ({n})' for a, n in contagem.most_common(3)) or '—'

    linhas = [
        '---', 'tags: [coleta]', f'coletado_em: {quando.isoformat(timespec="minutes")}', '---', '',
        f'**TL;DR: {len(novos)} itens novos de {len(fontes)} fontes, {completos} com texto completo guardado. '
        f'Assuntos que mais apareceram: {topo}. {len(falhas)} fontes não deixaram o robô ler. Elas estão no fim desta nota e são candidatas ao [[O que você me passa — checklist]].**',
        '', f"Como funciona: {_fonte('Coleta — como funciona', notas)} · Voltar: {_fonte('🧠 Mega Brain — Trade', notas)}", '',
    ]
    cruzados = sorted((r for r in novos if cruza(r)), key=lambda r: r.get('publicado') or '', reverse=True)
    if cruzados:
        linhas += [f'## Mercado × política ({len(cruzados)})', '',
                   '_Notícias em que um assunto político (eleição, Congresso, STF, fiscal) e um de preço (bolsa, câmbio, juros, inflação, estatais) aparecem juntos. É a matéria-prima da tese._', '']
        linhas += [_linha(r, notas) for r in cruzados[:NO_CRUZAMENTO]]
        if len(cruzados) > NO_CRUZAMENTO:
            linhas.append(f'- … e mais {len(cruzados) - NO_CRUZAMENTO}')
        linhas.append('')
    linhas += ['## Assuntos do momento', '']
    for assunto, n in contagem.most_common():
        linhas.append(f'### {assunto} ({n})')
        rs = sorted(por_assunto[assunto], key=relevancia, reverse=True)
        linhas += [_linha(r, notas) for r in rs[:POR_ASSUNTO]]
        if n > POR_ASSUNTO:
            linhas.append(f'- … e mais {n - POR_ASSUNTO}')
        linhas.append('')

    linhas += ['## Por fonte', '']
    por_cat: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for r in novos:
        por_cat[r['categoria']][r['fonte']].append(r)
    for cat, fontes_cat in sorted(por_cat.items(), key=lambda kv: ROTULO_CATEGORIA.get(kv[0], kv[0])):
        total = sum(len(v) for v in fontes_cat.values())
        linhas.append(f'> [!note]- {ROTULO_CATEGORIA.get(cat, cat)} ({total})')
        for fonte, rs in sorted(fontes_cat.items()):
            linhas.append(f'> **{_fonte(fonte, notas)}** ({len(rs)})')
            linhas += ['> ' + _linha(r, notas) for r in rs[:10]]
        linhas.append('')

    if falhas:
        linhas += ['## O que não deu para ler sozinho', '', '| Fonte | Motivo | Link |', '|---|---|---|']
        for f in sorted(falhas, key=lambda f: (f['status'], f['fonte'])):
            motivo = MOTIVOS.get(f['status'], f['status']) + (f" ({f['detalhe']})" if f.get('detalhe') else '')
            linhas.append(f"| {_fonte(f['fonte'], notas)} | {motivo} | [abrir]({f['url']}) |")
    return '\n'.join(linhas) + '\n'


def gravar_resumo(cofre: Path, texto: str, quando: datetime, substituir: bool = False) -> Path:
    """Uma nota por rodada. Duas rodadas no mesmo minuto ganham sufixo, a não ser que seja para refazer a mesma."""
    pasta = cofre / '10 Coleta'
    pasta.mkdir(parents=True, exist_ok=True)
    base = f'{quando:%Y-%m-%d %Hh%M} — coleta'
    destino, n = pasta / f'{base}.md', 2
    while destino.exists() and not substituir:
        destino, n = pasta / f'{base} ({n}).md', n + 1
    destino.write_text(texto, encoding='utf-8')
    return destino

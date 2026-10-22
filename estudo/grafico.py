"""Desenha em SVG o caminho médio do Ibovespa de −5 a +5 pregões por nível de surpresa (para o cofre do Obsidian).

Paleta: um azul só, do claro (pouca surpresa) ao escuro (muita), validada com o validador do guia de gráficos
(modo ordinal, claro e escuro). O azul mais claro tem contraste de 2:1, por isso cada linha leva o valor escrito
no fim e a nota traz a tabela com os números.
"""
from xml.sax.saxutils import escape

# série -> (cor no claro, cor no escuro); da menor para a maior surpresa
CORES = [('#86b6ef', '#184f95'), ('#2a78d6', '#3987e5'), ('#104281', '#86b6ef')]
L, A = 800, 450
M = {'esq': 56, 'dir': 200, 'topo': 100, 'base': 54}
Y_LEGENDA = 74


def _escala(v0: float, v1: float, p0: float, p1: float):
    return lambda v: p0 + (v - v0) * (p1 - p0) / (v1 - v0)


def svg_caminhos(series: list[tuple[str, int, list[float]]], titulo: str, subtitulo: str) -> str:
    """series: [(rótulo, n, valores em fração para os dias −5..+5)] da menor para a maior surpresa."""
    dias = list(range(-5, 6))
    todos = [v * 100 for _, _, vs in series for v in vs]
    y0, y1 = min(-1.0, min(todos)), max(todos)
    y0, y1 = float(int(y0) - (1 if y0 < int(y0) else 0)), float(int(y1) + 1)
    x = _escala(-5, 5, M['esq'], L - M['dir'])
    y = _escala(y0, y1, A - M['base'], M['topo'])
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {L} {A}" width="{L}" height="{A}" role="img" '
         f'aria-label="{escape(titulo)}">',
         '<style>',
         ':root{--sup:#fcfcfb;--t1:#0b0b0b;--t2:#52514e;--grade:#e4e3df;'
         + ''.join(f'--s{i}:{c[0]};' for i, c in enumerate(CORES)) + '}',
         '@media (prefers-color-scheme: dark){:root{--sup:#1a1a19;--t1:#f0efec;--t2:#c3c2b7;--grade:#383835;'
         + ''.join(f'--s{i}:{c[1]};' for i, c in enumerate(CORES)) + '}}',
         'text{font-family:-apple-system,BlinkMacSystemFont,"Inter","Segoe UI",sans-serif;fill:var(--t2);font-size:12px}',
         '.t1{fill:var(--t1)}.tit{font-size:16px;font-weight:600;fill:var(--t1)}.num{font-variant-numeric:tabular-nums}',
         '</style>',
         '<rect width="100%" height="100%" fill="var(--sup)" rx="8"/>',
         f'<text class="tit" x="{M["esq"]}" y="28">{escape(titulo)}</text>',
         f'<text x="{M["esq"]}" y="48">{escape(subtitulo)}</text>']
    # grade horizontal e eixo y
    v = y0
    while v <= y1 + 1e-9:
        yy = y(v)
        p.append(f'<line x1="{M["esq"]}" x2="{L - M["dir"]}" y1="{yy:.1f}" y2="{yy:.1f}" stroke="var(--grade)" stroke-width="{2 if v == 0 else 1}"/>')
        p.append(f'<text class="num" x="{M["esq"] - 8}" y="{yy + 4:.1f}" text-anchor="end">{v:+.0f}%</text>'.replace('+0%', '0%'))
        v += 1
    # marco do dia 0
    p.append(f'<line x1="{x(0):.1f}" x2="{x(0):.1f}" y1="{M["topo"]}" y2="{A - M["base"]}" stroke="var(--grade)" stroke-width="1"/>')
    p.append(f'<text x="{x(0) - 6:.1f}" y="{M["topo"] + 12}" text-anchor="end">dia da reação →</text>')
    for d in dias:
        p.append(f'<text class="num" x="{x(d):.1f}" y="{A - M["base"] + 20}" text-anchor="middle">{d:+d}'.replace('+0', '0') + '</text>')
    p.append(f'<text x="{(M["esq"] + L - M["dir"]) / 2:.1f}" y="{A - 12}" text-anchor="middle">pregões em relação ao dia da reação</text>')
    # linhas, pontos finais e rótulos (texto em cor de texto, nunca na cor da série)
    for i, (rot, n, vs) in enumerate(series):
        pts = ' '.join(f'{x(d):.1f},{y(val * 100):.1f}' for d, val in zip(dias, vs))
        p.append(f'<polyline points="{pts}" fill="none" stroke="var(--s{i})" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>')
        fx, fy = x(5), y(vs[-1] * 100)
        p.append(f'<circle cx="{fx:.1f}" cy="{fy:.1f}" r="4" fill="var(--s{i})" stroke="var(--sup)" stroke-width="2"/>')
        p.append(f'<text class="t1 num" x="{fx + 10:.1f}" y="{fy + 4:.1f}">{vs[-1] * 100:+.1f}%</text>')
        p.append(f'<text x="{fx + 54:.1f}" y="{fy + 4:.1f}">{escape(rot)}</text>')
    # legenda (sempre presente com 2+ séries), da maior para a menor surpresa
    lx = M['esq']
    for i, (rot, n, _) in reversed(list(enumerate(series))):
        p.append(f'<line x1="{lx}" x2="{lx + 18}" y1="{Y_LEGENDA}" y2="{Y_LEGENDA}" stroke="var(--s{i})" stroke-width="2" stroke-linecap="round"/>')
        rotulo = f'{rot} (n={n})'
        p.append(f'<text class="t1" x="{lx + 24}" y="{Y_LEGENDA + 4}">{escape(rotulo)}</text>')
        lx += 24 + 7 * len(rotulo) + 22
    p.append('</svg>')
    return '\n'.join(p) + '\n'

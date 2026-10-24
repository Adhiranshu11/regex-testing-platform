"""
visualizer.py  --  Step 6: Visualization & Export Layer
========================================================
Draws an NFA / DFA as a standalone SVG state diagram (no external libraries).
States are laid out in BFS layers from the start state. The SVG is fully
self-contained, so it can be saved as .svg directly or rasterised to PNG.
"""
import math
from collections import deque
from html import escape
from regex_parser import OTHER, show_char

R = 22          # state radius
DX, DY = 125, 90
PAD = 80

STYLE = """<style>
.edge path{fill:none;stroke:#64748b;stroke-width:1.5}
.edge .arrow{fill:#64748b;stroke:none}
.edge text{font:12px ui-monospace,Menlo,Consolas,monospace;fill:#0f172a;text-anchor:middle}
.edge text.halo{fill:#fff;stroke:#fff;stroke-width:5px;stroke-linejoin:round}
.node circle{fill:#fff;stroke:#1e293b;stroke-width:1.6}
.node .inner{fill:none}
.node text{font:600 13px system-ui,Segoe UI,Arial,sans-serif;fill:#0f172a;text-anchor:middle}
.start .arrow{fill:#1e293b}.start line{stroke:#1e293b;stroke-width:1.5}
.edge.active path{stroke:#d97706;stroke-width:3}.edge.active .arrow{fill:#d97706}
.node.active circle{fill:#fde68a;stroke:#d97706;stroke-width:2.6}
.node.hit-ok circle{fill:#bbf7d0;stroke:#15803d;stroke-width:2.6}
.node.hit-bad circle{fill:#fecaca;stroke:#b91c1c;stroke-width:2.6}
</style>"""


# ------------------------------------------------------------ graph adapters
def _compact_label(symbols, alphabet):
    syms = set(symbols)
    if len(alphabet) > 2 and syms == set(alphabet):
        return "\u03a3"
    chars = sorted(c for c in syms if c != OTHER)
    out, i = [], 0
    while i < len(chars):
        j = i
        while j + 1 < len(chars) and ord(chars[j + 1]) == ord(chars[j]) + 1:
            j += 1
        if j - i >= 2:
            out.append(f"{show_char(chars[i])}-{show_char(chars[j])}")
        else:
            out.extend(show_char(c) for c in chars[i:j + 1])
        i = j + 1
    if OTHER in syms:
        out.append("other")
    return ",".join(out)


def _nfa_graph(nfa):
    edges = {}
    for u, lst in nfa.trans.items():
        for label, v in lst:
            edges.setdefault((u, v), []).append("\u03b5" if label is None else label.label)
    return {"nodes": list(range(nfa.n)),
            "edges": {k: ", ".join(dict.fromkeys(v)) for k, v in edges.items()},
            "start": nfa.start, "accepts": {nfa.accept}, "name": lambda s: f"q{s}"}


def _dfa_graph(dfa, hide_trap=True):
    hidden = (dfa.trap_states() - {dfa.start}) if hide_trap else set()
    nodes = [s for s in sorted(dfa.trans) if s not in hidden]
    group = {}
    for s in nodes:
        for a, t in dfa.trans[s].items():
            if t not in hidden:
                group.setdefault((s, t), []).append(a)
    return {"nodes": nodes,
            "edges": {k: _compact_label(v, dfa.alphabet) for k, v in group.items()},
            "start": dfa.start, "accepts": set(dfa.accepting) - hidden, "name": dfa.name}


# ------------------------------------------------------------------ drawing
def _unit(x, y):
    l = math.hypot(x, y) or 1.0
    return x / l, y / l


def _arrow(tip, d):
    (tx, ty), (dx, dy) = tip, d
    bx, by = tx - dx * 9, ty - dy * 9
    px, py = -dy * 4.5, dx * 4.5
    return (f'<polygon class="arrow" points="{tx:.1f},{ty:.1f} {bx + px:.1f},{by + py:.1f} '
            f'{bx - px:.1f},{by - py:.1f}"/>'), (bx, by)


def _label(x, y, label):
    t = escape(label)
    return (f'<text class="halo" x="{x:.1f}" y="{y:.1f}">{t}</text>'
            f'<text x="{x:.1f}" y="{y:.1f}">{t}</text>')


def _edge_svg(u, v, label, pos, layer, has_rev, kind):
    eid = f"{kind}-e{u}-{v}"
    (x1, y1), (x2, y2) = pos[u], pos[v]
    if u == v:
        tip = (x1 + 10, y1 - 19.6)
        c2 = (x1 + 30, y1 - R - 36)
        d = _unit(tip[0] - c2[0], tip[1] - c2[1])
        arrow, base = _arrow(tip, d)
        path = f"M {x1 - 10:.1f} {y1 - 19.6:.1f} C {x1 - 30:.1f} {y1 - R - 36:.1f} {c2[0]:.1f} {c2[1]:.1f} {base[0]:.1f} {base[1]:.1f}"
        text = _label(x1, y1 - R - 50, label)
        return f'<g class="edge" id="{eid}"><path d="{path}"/>{arrow}{text}</g>'
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / L, dx / L
    ld = layer[v] - layer[u]
    if has_rev:
        off = 52.0
    elif ld == 1:
        off = 0.0
    else:
        up = -1 if dx >= 0 else 1
        off = up * (44 + 22 * max(0, abs(ld) - 1))
    cx, cy = (x1 + x2) / 2 + nx * off, (y1 + y2) / 2 + ny * off
    ux, uy = _unit(cx - x1, cy - y1)
    sx, sy = x1 + ux * R, y1 + uy * R
    vx, vy = _unit(cx - x2, cy - y2)
    tip = (x2 + vx * R, y2 + vy * R)
    arrow, base = _arrow(tip, (-vx, -vy))
    path = f"M {sx:.1f} {sy:.1f} Q {cx:.1f} {cy:.1f} {base[0]:.1f} {base[1]:.1f}"
    lx = 0.25 * sx + 0.5 * cx + 0.25 * tip[0]
    ly = 0.25 * sy + 0.5 * cy + 0.25 * tip[1]
    if off == 0:
        ly -= 9
    else:
        sg = 1 if off > 0 else -1
        lx += nx * sg * 11
        ly += ny * sg * 11 + 4
    return (f'<g class="edge" id="{eid}"><path d="{path}"/>{arrow}'
            f'{_label(lx, ly, label)}</g>')


def _render(g, kind):
    nodes, edges, start = g["nodes"], g["edges"], g["start"]
    adj = {n: [] for n in nodes}
    for (u, v) in sorted(edges):
        adj[u].append(v)
    layer, q = {start: 0}, deque([start])
    while q:
        u = q.popleft()
        for v in adj[u]:
            if v not in layer:
                layer[v] = layer[u] + 1
                q.append(v)
    extra = max(layer.values()) + 1
    for n in nodes:
        layer.setdefault(n, extra)
    layers = {}
    for n in sorted(nodes, key=lambda n: (layer[n], n)):
        layers.setdefault(layer[n], []).append(n)
    nl = max(layers) + 1
    maxh = max(len(v) for v in layers.values())
    x0 = PAD + 30
    W = x0 + (nl - 1) * DX + PAD
    H = 2 * PAD + (maxh - 1) * DY
    pos = {}
    for li, lst in layers.items():
        top = PAD + (maxh - len(lst)) * DY / 2
        for i, n in enumerate(lst):
            pos[n] = (x0 + li * DX, top + i * DY)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
             STYLE, f'<rect width="{W}" height="{H}" fill="#ffffff"/>']
    for (u, v), label in sorted(edges.items()):
        parts.append(_edge_svg(u, v, label, pos, layer, (v, u) in edges and u != v, kind))
    sx, sy = pos[start]
    arrow, base = _arrow((sx - R, sy), (1, 0))
    parts.append(f'<g class="start"><line x1="{sx - R - 36}" y1="{sy}" x2="{base[0]:.1f}" y2="{sy}"/>{arrow}</g>')
    for n in nodes:
        x, y = pos[n]
        inner = f'<circle class="inner" cx="{x}" cy="{y}" r="{R - 4}"/>' if n in g["accepts"] else ""
        parts.append(f'<g class="node" id="{kind}-n{n}"><circle cx="{x}" cy="{y}" r="{R}"/>{inner}'
                     f'<text x="{x}" y="{y + 4.5}">{escape(g["name"](n))}</text></g>')
    parts.append("</svg>")
    return "".join(parts)


def render_nfa_svg(nfa):
    return _render(_nfa_graph(nfa), "nfa")


def render_dfa_svg(dfa, kind="dfa", hide_trap=True):
    return _render(_dfa_graph(dfa, hide_trap), kind)

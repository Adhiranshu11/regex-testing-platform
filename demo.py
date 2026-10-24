"""
demo.py  --  command-line demo of the full pipeline

    python demo.py                              built-in demo
    python demo.py "(a|b)*abb" abb aabb ab      your own regex and test strings
Writes nfa / dfa / min_dfa diagrams (.svg, and .png if cairosvg is installed)
into the ./output folder.
"""
import os
import sys
from regex_parser import RegexSyntaxError, tokenize, tokens_pretty
import engine
from engine import build_all
from nfa_simulator import simulate
from explainer import explain
from string_generator import generate_strings
from dfa_minimizer import minimize, METHODS
from visualizer import render_nfa_svg, render_dfa_svg
from exporter import save_svg, save_png


def show_table(t):
    head = ["State"] + ([t["extra_header"]] if t["extra_header"] else []) + t["columns"]
    rows = []
    for r in t["rows"]:
        mark = ("->" if r["start"] else "  ") + ("*" if r["accepting"] else " ")
        rows.append([mark + r["name"]] + ([r["extra"]] if t["extra_header"] else []) + r["cells"])
    widths = [max(len(str(x[i])) for x in rows + [head]) for i in range(len(head))]
    for line in [head] + rows:
        print("  " + "  ".join(str(c).ljust(w) for c, w in zip(line, widths)))


def run(regex, tests):
    print("=" * 70)
    print(f"REGEX: {regex}")
    print("=" * 70)
    print("Tokens:")
    print(tokens_pretty(tokenize(regex)))
    ast, nfa, dfa, mdfa, rounds = build_all(regex)
    print(f"\nNFA: {nfa.n} states, {nfa.transition_count()} transitions | "
          f"DFA: {len(dfa.trans)} states | minimal DFA: {len(mdfa.trans)} states\n")
    print("Subset-construction table (-> start, * accepting):")
    show_table(dfa.table())
    print(f"\nMinimization with {METHODS['hopcroft']}:")
    for r in rounds:
        print(f"  {r['label']:<8}: " + "  |  ".join("{" + ",".join(g) + "}" for g in r["groups"]))
    sizes = {name: len(minimize(dfa, m)[0].trans) for m, name in METHODS.items()}
    print("All three algorithms agree: " + "; ".join(f"{k} = {v} states" for k, v in sizes.items()))
    print("\nMinimal DFA:")
    show_table(mdfa.table())
    for t in tests:
        ok, _ = simulate(nfa, t)
        print(f"\nString {t!r}: {'ACCEPTED' if ok else 'REJECTED'}")
        for step in explain(mdfa, t)["trace"]:
            print("   ", step["text"])
    print("\nRandom strings guaranteed to match:", generate_strings(mdfa, 8, 10, seed=1))
    png_ok = True
    for fname, svg in (("nfa", render_nfa_svg(nfa)), ("dfa", render_dfa_svg(dfa)),
                       ("min_dfa", render_dfa_svg(mdfa, "min"))):
        save_svg(svg, os.path.join("output", fname + ".svg"))
        png_ok = save_png(svg, os.path.join("output", fname + ".png")) and png_ok
    print("Diagrams saved in ./output as SVG" +
          (" and PNG." if png_ok else ". For PNG files: pip install cairosvg, or use Save PNG in the web app.") + "\n")


if __name__ == "__main__":
    try:
        if len(sys.argv) > 1:
            run(sys.argv[1], sys.argv[2:])
        else:
            run("(a|b)*abb", ["abb", "aabb", "abab"])
            run("a(b|c)*d", ["ad", "abcbd", "abc"])
    except RegexSyntaxError as e:
        print("Syntax error:", e)

"""
engine.py  --  glues the whole pipeline together (used by the web server and demo)
"""
import sys
from regex_parser import tokenize, Parser, ast_pretty
from nfa_builder import build_nfa
from nfa_simulator import simulate
from dfa_converter import nfa_to_dfa
from dfa_minimizer import minimize, METHODS
from explainer import explain
from string_generator import generate_strings
from visualizer import render_nfa_svg, render_dfa_svg

sys.setrecursionlimit(5000)
MAX_REGEX_LEN = 150
MAX_TESTS = 60
MAX_TEST_LEN = 500


def build_all(regex, method="hopcroft"):
    if len(regex) > MAX_REGEX_LEN:
        raise ValueError(f"Regex is too long (limit {MAX_REGEX_LEN} characters).")
    ast = Parser(tokenize(regex)).parse()
    nfa = build_nfa(ast)
    dfa = nfa_to_dfa(nfa)
    mdfa, rounds = minimize(dfa, method)
    return ast, nfa, dfa, mdfa, rounds


def analyze(regex, tests=(), method="hopcroft"):
    ast, nfa, dfa, mdfa, rounds = build_all(regex, method)
    results = []
    for t in list(tests)[:MAX_TESTS]:
        t = t[:MAX_TEST_LEN]
        nfa_ok, nfa_trace = simulate(nfa, t)
        ex_dfa, ex_min = explain(dfa, t), explain(mdfa, t)
        assert nfa_ok == ex_dfa["accepted"] == ex_min["accepted"], "automata disagree"
        results.append({"input": t, "accepted": nfa_ok, "reason": ex_min["reason"],
                        "nfa_trace": nfa_trace, "dfa": ex_dfa, "min": ex_min})
    return {
        "regex": regex,
        "tokens": "\n".join(f"{t.pos:>3}  {t.kind:<8} {t.text}" for t in tokenize(regex)) or "(empty expression)",
        "ast": ast_pretty(ast),
        "method": method,
        "method_name": METHODS[method],
        "min_methods": {METHODS[m]: len(minimize(dfa, m)[0].trans) for m in METHODS},
        "stats": {"nfa_states": nfa.n, "nfa_transitions": nfa.transition_count(),
                  "dfa_states": len(dfa.trans), "min_states": len(mdfa.trans),
                  "alphabet": dfa.alphabet_labels()},
        "svg": {"nfa": render_nfa_svg(nfa),
                "dfa": render_dfa_svg(dfa, "dfa"),
                "min": render_dfa_svg(mdfa, "min")},
        "tables": {"nfa": nfa.table(), "dfa": dfa.table(), "min": mdfa.table()},
        "rounds": rounds,
        "tests": results,
    }


def generate(regex, count=10, max_len=12, seed=None):
    count = max(1, min(int(count), 50))
    max_len = max(0, min(int(max_len), 60))
    _, _, _, mdfa, _ = build_all(regex)
    return generate_strings(mdfa, count, max_len, seed)

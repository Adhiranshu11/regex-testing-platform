"""Automated tests:  python test_all.py   (checks every stage against Python's re module)"""
import itertools
import re
import unittest

import random
from regex_parser import parse, tokenize, RegexSyntaxError
from nfa_builder import build_nfa
from nfa_simulator import simulate
from dfa_converter import nfa_to_dfa
from dfa_minimizer import minimize, METHODS
from exporter import save_svg
from string_generator import generate_strings
from explainer import explain
import engine

CASES = [
    ("(a|b)*abb", "ab"), ("a*b*", "ab"), ("(ab|a)*", "ab"), ("a(b|c)*d", "abcd"),
    ("(0|1)*00", "01"), ("a+b?", "ab"), ("(a|b)+", "ab"), ("", "ab"), ("a|", "ab"),
    ("(a*)*", "ab"), ("(a|b)*a(a|b)", "ab"), ("[ab]c[^a]", "abc"), ("a.b", "abx"),
    ("\\d+(\\.\\d+)?", "1.x"), ("[a-c]+x?", "abcx"), ("(ab)+|c", "abc"), ("a?a?aa", "a"),
]


def strings(alpha, n):
    for k in range(n + 1):
        for t in itertools.product(alpha, repeat=k):
            yield "".join(t)


class PipelineTests(unittest.TestCase):
    def test_all_stages_match_python_re(self):
        for rx, alpha in CASES:
            ast = parse(rx)
            nfa = build_nfa(ast)
            dfa = nfa_to_dfa(nfa)
            mdfa, _ = minimize(dfa)
            self.assertLessEqual(len(mdfa.trans), len(dfa.trans))
            for s in strings(alpha, 6):
                want = re.fullmatch(rx, s) is not None
                self.assertEqual(simulate(nfa, s)[0], want, (rx, s, "nfa"))
                self.assertEqual(dfa.accepts(s), want, (rx, s, "dfa"))
                self.assertEqual(mdfa.accepts(s), want, (rx, s, "min"))
                self.assertEqual(explain(mdfa, s)["accepted"], want, (rx, s, "explain"))

    def test_minimal_sizes(self):
        sizes = {"(a|b)*abb": 4, "(0|1)*00": 3, "a*": 1, "(a|b)*a(a|b)": 4}
        for rx, n in sizes.items():
            m, _ = minimize(nfa_to_dfa(build_nfa(parse(rx))))
            self.assertEqual(len(m.trans), n, rx)

    def test_unknown_character_rejected(self):
        d = nfa_to_dfa(build_nfa(parse("ab")))
        self.assertFalse(d.accepts("az"))
        self.assertIn("alphabet", explain(d, "az")["reason"])

    def test_generated_strings_always_match(self):
        for rx, _ in CASES + [("[a-z]+@[a-z]+\\.com", "")]:
            m, _ = minimize(nfa_to_dfa(build_nfa(parse(rx))))
            for s in generate_strings(m, 25, 12, seed=7):
                self.assertIsNotNone(re.fullmatch(rx, s), (rx, s))

    def test_syntax_errors(self):
        for bad in ["(ab", "ab)", "*a", "a**+?(", "[abc", "[]", "a\\", "[z-a]", "+"]:
            with self.assertRaises(RegexSyntaxError, msg=bad):
                parse(bad)

    def test_engine_api(self):
        out = engine.analyze("(a|b)*abb", ["abb", "ab", ""])
        self.assertEqual([t["accepted"] for t in out["tests"]], [True, False, False])
        self.assertTrue(out["svg"]["dfa"].startswith("<svg"))
        self.assertEqual(out["stats"]["min_states"], 4)
        self.assertTrue(engine.generate("a+b", 5, 6))


def random_regex(rnd, depth=0):
    r = rnd.random()
    if depth >= 3 or r < 0.3:
        return rnd.choice("ab")
    if r < 0.5:
        return random_regex(rnd, depth + 1) + random_regex(rnd, depth + 1)
    if r < 0.7:
        return "(" + random_regex(rnd, depth + 1) + "|" + random_regex(rnd, depth + 1) + ")"
    return "(" + random_regex(rnd, depth + 1) + ")" + rnd.choice("*+?")


class StageTests(unittest.TestCase):
    def test_tokenizer(self):
        kinds = [t.kind for t in tokenize("a(b|c)*")]
        self.assertEqual(kinds, ["SYMBOL", "LPAREN", "SYMBOL", "UNION", "SYMBOL", "RPAREN", "STAR"])
        toks = tokenize("[a-c]\\d\\.x.")
        self.assertEqual([t.kind for t in toks], ["CLASS", "CLASS", "SYMBOL", "SYMBOL", "ANY"])
        self.assertEqual([t.pos for t in toks], [0, 5, 7, 9, 10])
        self.assertEqual(tokenize(""), [])

    def test_all_minimizers_agree(self):
        rnd = random.Random(2024)
        regexes = [rx for rx, _ in CASES] + [random_regex(rnd) for _ in range(60)]
        for rx in regexes:
            dfa = nfa_to_dfa(build_nfa(parse(rx)))
            results = {m: minimize(dfa, m)[0] for m in METHODS}
            base = results["hopcroft"]
            for m, mdfa in results.items():
                self.assertEqual(mdfa.trans, base.trans, (rx, m))
                self.assertEqual(mdfa.accepting, base.accepting, (rx, m))
                self.assertLessEqual(len(mdfa.trans), len(dfa.trans))
            for s in strings("ab", 5):
                want = re.fullmatch(rx, s) is not None
                self.assertEqual(base.accepts(s), want, (rx, s))

    def test_minimizer_logs(self):
        dfa = nfa_to_dfa(build_nfa(parse("(a|b)*abb")))
        for m in METHODS:
            mdfa, log = minimize(dfa, m)
            self.assertEqual(log[0]["label"], "Start")
            self.assertEqual(len(mdfa.trans), 4)
            self.assertEqual(sorted(x for g in log[-1]["groups"] for x in g),
                             sorted(dfa.name(s) for s in dfa.trans))
        with self.assertRaises(ValueError):
            minimize(dfa, "nope")

    def test_export(self):
        import os, tempfile
        d = tempfile.mkdtemp()
        path = save_svg(engine.analyze("ab", [])["svg"]["dfa"], os.path.join(d, "x.svg"))
        with open(path, encoding="utf-8") as f:
            self.assertTrue(f.read().startswith("<svg"))


if __name__ == "__main__":
    unittest.main(verbosity=2)

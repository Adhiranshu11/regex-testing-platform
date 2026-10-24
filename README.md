# Regular Expression Testing Platform

**Course:** Theory of Computation (BITE306L), VIT
**Team:** Adhiranshu Singh (24BIT0036), Govind Innani (24BIT0157)

A regex tester that also shows the automata theory behind every match. Type a
regular expression and the platform builds its NFA, DFA and minimal DFA, draws
them, and explains step by step why each test string is accepted or rejected.

Pure Python 3.8+, **no external libraries** to install.

## How to run

```
# Web app (recommended)
python server.py            # then open http://127.0.0.1:8000  (opens automatically)

# Command-line demo (also writes SVG diagrams to ./output)
python demo.py
python demo.py "(a|b)*abb" abb aabb ab

# Automated tests (compares every stage with Python's re module)
python test_all.py
```

## Pipeline and files

| Step | File | What it does |
|---|---|---|
| 1 | `regex_parser.py` | Tokenizer (regex text to tokens) and recursive-descent parser (tokens to AST), with syntax-error positions |
| 2 | `nfa_builder.py` | Thompson's Construction: AST to epsilon-NFA |
| 2b | `nfa_simulator.py` | Epsilon-closure, move, and direct NFA simulation |
| 3 | `dfa_converter.py` | Subset Construction: NFA to complete DFA (explicit trap state) |
| 4 | `dfa_minimizer.py` | Hopcroft's algorithm (default), table-filling and partition refinement, each with a log of how states merge |
| 5 | `explainer.py` | Accept/reject verdict with a plain-English transition trace |
| 6 | `visualizer.py`, `exporter.py` | SVG state diagrams (layered layout), saved as SVG and PNG |
| 7 | `string_generator.py` | Random strings guaranteed to match (walk on live states only) |
| - | `engine.py`, `server.py`, `static/index.html` | Integration, web server, interactive UI |
| - | `demo.py`, `test_all.py` | CLI demo and unit tests |

## Objectives covered

1. Validate regex syntax: the tokenizer and parser raise `RegexSyntaxError` with the position.
2. Regex to NFA by Thompson's Construction.
3. NFA to DFA by Subset Construction.
4. Test strings against the automaton (accepted / rejected).
5. Human-readable explanation tracing the state transitions.
6. DFA minimization with Hopcroft's algorithm and table-filling (plus Moore's partition refinement), compared side by side (DFA vs minimal DFA tabs, plus the step-by-step log).
7. Export diagrams as SVG or PNG (web app buttons; `demo.py` writes both, PNG needs `pip install cairosvg`).
8. Extra feature: random strings that are guaranteed to match.

## Supported syntax

`ab` concatenation, `a|b` union, `*` `+` `?`, `( )` grouping, `.` any character,
`[abc]` `[a-z0-9]` `[^x]` classes, `\d` `\w`, escapes such as `\.` and `\*`.
The whole string must match (like `re.fullmatch`). Characters not in the regex
alphabet are rejected, except where `.` or a negated class accepts them.
Not supported: back-references, lookahead, `{n,m}` counts, anchors (they are
not regular or not needed for full-match).

## How the web app works

* **Build and test** runs the full pipeline and shows state counts.
* Click a test string, then use **Back / Next / Play** to watch the automaton
  read it. On the NFA tab all active states are highlighted; on the DFA tabs
  the current state and the edge just taken.
* **Save SVG / Save PNG** export the diagram currently shown.
* **Random strings** generates matching strings and can add them to the tests.

## Complexity notes

* Thompson NFA: O(m) states for a regex of length m.
* Subset construction: up to O(2^n) DFA states in the worst case (capped at 1000 here).
* Minimization: Hopcroft O(n |alphabet| log n); table-filling and partition refinement O(n^2 |alphabet|).
* Simulating a string on the DFA: O(length of string).

## Sample results

| Regex | NFA states | DFA states | Minimal DFA |
|---|---|---|---|
| `(a\|b)*abb` | 14 | 5 | 4 |
| `(0\|1)*00` | 12 | 4 | 3 |

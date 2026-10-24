"""
nfa_builder.py  --  Step 2: NFA Generator (Thompson's Construction)
====================================================================
Recursively converts the AST into an epsilon-NFA. Every AST node becomes a
fragment with exactly one start and one accept state; fragments are glued
together with epsilon edges (label None).

    symbol a :  s --a--> e
    A B      :  A.end --eps--> B.start
    A | B    :  s --eps--> A.start, B.start ; A.end, B.end --eps--> e
    A*       :  s --eps--> A.start, e ; A.end --eps--> A.start, e
    A+       :  s --eps--> A.start ; A.end --eps--> A.start, e
    A?       :  s --eps--> A.start, e ; A.end --eps--> e
"""
from regex_parser import Empty, Atom, Concat, Union, Star, Plus, Optional


class NFA:
    def __init__(self):
        self.n = 0
        self.trans = {}          # state -> list of (CharSet | None, target)
        self.start = 0
        self.accept = 0

    def new_state(self):
        s = self.n
        self.n += 1
        self.trans[s] = []
        return s

    def add(self, a, label, b):
        self.trans[a].append((label, b))

    def transition_count(self):
        return sum(len(v) for v in self.trans.values())

    def table(self):
        cols = []
        for s in range(self.n):
            for label, _ in self.trans[s]:
                if label is not None and label.label not in cols:
                    cols.append(label.label)
        cols.append("\u03b5")
        rows = []
        for s in range(self.n):
            cells = []
            for col in cols:
                targets = sorted({t for lab, t in self.trans[s]
                                  if ("\u03b5" if lab is None else lab.label) == col})
                cells.append(",".join(f"q{t}" for t in targets) or "\u2013")
            rows.append({"name": f"q{s}", "start": s == self.start,
                         "accepting": s == self.accept, "trap": False,
                         "extra": "", "cells": cells})
        return {"columns": cols, "extra_header": "", "rows": rows}


def build_nfa(ast):
    nfa = NFA()

    def frag(node):
        if isinstance(node, Empty):
            s, e = nfa.new_state(), nfa.new_state()
            nfa.add(s, None, e)
            return s, e
        if isinstance(node, Atom):
            s, e = nfa.new_state(), nfa.new_state()
            nfa.add(s, node.cs, e)
            return s, e
        if isinstance(node, Concat):
            ls, le = frag(node.left)
            rs, re_ = frag(node.right)
            nfa.add(le, None, rs)
            return ls, re_
        if isinstance(node, Union):
            s, e = nfa.new_state(), nfa.new_state()
            ls, le = frag(node.left)
            rs, re_ = frag(node.right)
            nfa.add(s, None, ls); nfa.add(s, None, rs)
            nfa.add(le, None, e); nfa.add(re_, None, e)
            return s, e
        s, e = nfa.new_state(), nfa.new_state()
        cs, ce = frag(node.child)
        nfa.add(s, None, cs)
        nfa.add(ce, None, e)
        if isinstance(node, Star):
            nfa.add(s, None, e); nfa.add(ce, None, cs)
        elif isinstance(node, Plus):
            nfa.add(ce, None, cs)
        elif isinstance(node, Optional):
            nfa.add(s, None, e)
        return s, e

    nfa.start, nfa.accept = frag(ast)
    return nfa

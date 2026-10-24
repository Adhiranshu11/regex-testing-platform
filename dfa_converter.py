"""
dfa_converter.py  --  Step 3: DFA Converter (Subset Construction)
==================================================================
Each DFA state is a SET of NFA states (closed under epsilon moves).
The DFA produced is complete: a missing move leads to the empty set, which
becomes an explicit trap (dead) state.
"""
from regex_parser import OTHER, show_char
from nfa_simulator import eps_closure, move_on


class AutomatonTooLarge(Exception):
    pass


class DFA:
    def __init__(self, alphabet, prefix="D", member_prefix="q"):
        self.alphabet = list(alphabet)
        self._aset = set(alphabet)
        self.prefix = prefix
        self.member_prefix = member_prefix
        self.start = 0
        self.accepting = set()
        self.trans = {}          # state -> {symbol: state}
        self.members = {}        # state -> sorted list of the states it was built from
        self._trap = None

    def name(self, s):
        return f"{self.prefix}{s}"

    def symbol_for(self, ch):
        """Map an input character to an alphabet symbol (None = not in alphabet)."""
        if ch in self._aset:
            return ch
        return OTHER if OTHER in self._aset else None

    def step(self, s, ch):
        sym = self.symbol_for(ch)
        return None if sym is None else self.trans[s][sym]

    def accepts(self, text):
        s = self.start
        for ch in text:
            s = self.step(s, ch)
            if s is None:
                return False
        return s in self.accepting

    def trap_states(self):
        """States from which no accepting state can be reached."""
        if self._trap is None:
            rev = {s: set() for s in self.trans}
            for s, row in self.trans.items():
                for t in row.values():
                    rev[t].add(s)
            live, stack = set(self.accepting), list(self.accepting)
            while stack:
                x = stack.pop()
                for p in rev[x]:
                    if p not in live:
                        live.add(p)
                        stack.append(p)
            self._trap = set(self.trans) - live
        return self._trap

    def alphabet_labels(self):
        return ["other" if a == OTHER else show_char(a) for a in self.alphabet]

    def table(self):
        trap = self.trap_states()
        rows = []
        for s in sorted(self.trans):
            rows.append({
                "name": self.name(s), "start": s == self.start,
                "accepting": s in self.accepting, "trap": s in trap,
                "extra": "{" + ", ".join(f"{self.member_prefix}{m}" for m in self.members[s]) + "}"
                         if self.members[s] else "\u2205",
                "cells": [self.name(self.trans[s][a]) for a in self.alphabet]})
        header = "NFA states" if self.prefix == "D" else "merged DFA states"
        return {"columns": self.alphabet_labels(), "extra_header": header, "rows": rows}


def nfa_to_dfa(nfa, max_states=1000):
    chars, need_other = set(), False
    for edges in nfa.trans.values():
        for label, _ in edges:
            if label is not None:
                chars |= label.chars
                need_other = need_other or label.negated
    alphabet = sorted(chars) + ([OTHER] if need_other else [])
    dfa = DFA(alphabet, "D", "q")

    start_set = eps_closure(nfa, {nfa.start})
    ids = {start_set: 0}
    dfa.trans[0] = {}
    dfa.members[0] = sorted(start_set)
    queue = [start_set]
    qi = 0
    while qi < len(queue):
        S = queue[qi]
        qi += 1
        sid = ids[S]
        for sym in alphabet:
            T = eps_closure(nfa, move_on(nfa, S, sym))
            if T not in ids:
                if len(ids) >= max_states:
                    raise AutomatonTooLarge(
                        f"The DFA would need more than {max_states} states. Try a simpler expression.")
                ids[T] = len(ids)
                dfa.trans[ids[T]] = {}
                dfa.members[ids[T]] = sorted(T)
                queue.append(T)
            dfa.trans[sid][sym] = ids[T]
    for S, i in ids.items():
        if nfa.accept in S:
            dfa.accepting.add(i)
    return dfa

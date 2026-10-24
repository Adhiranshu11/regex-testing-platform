"""
string_generator.py  --  Step 7 (extra feature): Random String Generator
=========================================================================
Random walk on the minimal DFA, restricted to states from which an accepting
state is still reachable. Because the walk never enters a dead end and always
keeps enough length budget to reach acceptance, every generated string is
guaranteed to match the regex.
"""
import random
from collections import deque
from regex_parser import OTHER


def _distance_to_accept(dfa):
    rev = {s: [] for s in dfa.trans}
    for s, row in dfa.trans.items():
        for t in row.values():
            rev[t].append(s)
    dist = {s: 0 for s in dfa.accepting}
    q = deque(dfa.accepting)
    while q:
        x = q.popleft()
        for p in rev[x]:
            if p not in dist:
                dist[p] = dist[x] + 1
                q.append(p)
    return dist


def generate_strings(dfa, count=10, max_len=12, seed=None):
    dist = _distance_to_accept(dfa)
    if dfa.start not in dist:
        return []
    rnd = random.Random(seed)
    max_len = max(max_len, dist[dfa.start])
    spare = [c for c in "xyzqkj~#%&@" if c not in dfa.alphabet] or ["\u00a7"]

    def concrete(sym):
        return rnd.choice(spare) if sym == OTHER else sym

    found, seen, tries = [], set(), 0
    while len(found) < count and tries < count * 60 + 100:
        tries += 1
        s, out = dfa.start, []
        while True:
            remaining = max_len - len(out)
            if s in dfa.accepting and (remaining <= 0 or rnd.random() < 0.3):
                break
            options = [(a, t) for a, t in dfa.trans[s].items()
                       if t in dist and dist[t] <= remaining - 1]
            if not options:
                break
            a, t = rnd.choice(options)
            out.append(concrete(a))
            s = t
        word = "".join(out)
        if s in dfa.accepting and word not in seen:
            seen.add(word)
            found.append(word)
    return found

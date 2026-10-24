"""
dfa_minimizer.py  --  Step 4: DFA Minimizer
============================================
Three classic minimization algorithms are implemented. All of them find the
same equivalence classes of states, and each merged class becomes one state of
the minimal DFA (which is unique up to naming).

  hopcroft  Hopcroft's algorithm (default). Keeps a worklist of "splitter"
            blocks; whenever a splitter separates a block, the block is split.
            O(n * |alphabet| * log n).
  table     Table-filling (Myhill-Nerode). Marks every pair of states that is
            distinguishable, pass after pass, until nothing changes. The
            unmarked pairs are equivalent. O(n^2 * |alphabet|) per pass.
  moore     Partition refinement (Moore). Start with accepting / non-accepting
            blocks and split a block whenever two of its states go to different
            blocks on some symbol, until no block splits.

Unreachable states are removed first. Every algorithm returns a log of how the
partition of states changed, which the interface shows step by step.
"""
from dfa_converter import DFA

METHODS = {
    "hopcroft": "Hopcroft's algorithm",
    "table": "Table-filling algorithm",
    "moore": "Partition refinement (Moore)",
}


def _reachable(dfa):
    reach, stack = {dfa.start}, [dfa.start]
    while stack:
        s = stack.pop()
        for t in dfa.trans[s].values():
            if t not in reach:
                reach.add(t)
                stack.append(t)
    return sorted(reach)


def _entry(log, label, dfa, block, states):
    groups = {}
    for s in states:
        groups.setdefault(block[s], []).append(s)
    ordered = sorted(groups.values(), key=lambda g: g[0])
    log.append({"round": len(log), "label": label,
                "groups": [[dfa.name(s) for s in g] for g in ordered]})


# ------------------------------------------------------ partition refinement
def moore_blocks(dfa, states):
    block = {s: int(s in dfa.accepting) for s in states}
    log = []
    _entry(log, "Start", dfa, block, states)
    while True:
        sigs, new = {}, {}
        for s in states:
            sig = (block[s], tuple(block[dfa.trans[s][a]] for a in dfa.alphabet))
            new[s] = sigs.setdefault(sig, len(sigs))
        done = len(sigs) == len(set(block.values()))
        block = new
        if done:
            break
        _entry(log, f"Round {len(log)}", dfa, block, states)
    return block, log


# ---------------------------------------------------------------- Hopcroft
def hopcroft_blocks(dfa, states):
    inv = {a: {} for a in dfa.alphabet}            # inv[a][t] = states that reach t on a
    for s in states:
        for a in dfa.alphabet:
            inv[a].setdefault(dfa.trans[s][a], []).append(s)
    final = frozenset(s for s in states if s in dfa.accepting)
    rest = frozenset(states) - final
    P = [b for b in (final, rest) if b]
    W = [min(P, key=len)] if len(P) == 2 else []

    def to_block():
        return {s: i for i, b in enumerate(P) for s in b}

    log = []
    _entry(log, "Start", dfa, to_block(), states)
    while W:
        A = W.pop()
        for a in dfa.alphabet:
            X = set()
            for t in A:
                X.update(inv[a].get(t, ()))
            for Y in list(P):
                inter, diff = Y & X, Y - X
                if inter and diff:
                    P[P.index(Y):P.index(Y) + 1] = [inter, diff]
                    if Y in W:
                        W.remove(Y)
                        W.extend([inter, diff])
                    else:
                        W.append(min(inter, diff, key=len))
                    _entry(log, f"Split {len(log)}", dfa, to_block(), states)
    return to_block(), log


# ------------------------------------------------------------ table-filling
def table_filling_blocks(dfa, states):
    pairs = [(p, q) for i, p in enumerate(states) for q in states[i + 1:]]
    marked = {(p, q) for p, q in pairs if (p in dfa.accepting) != (q in dfa.accepting)}

    def key(x, y):
        return (x, y) if x < y else (y, x)

    def classes():
        block = {}
        for s in states:
            block[s] = s
            for t in states:
                if t >= s:
                    break
                if (t, s) not in marked:
                    block[s] = block[t]
                    break
        return block

    log = []
    _entry(log, "Start", dfa, classes(), states)
    while True:
        newly = []
        for p, q in pairs:
            if (p, q) in marked:
                continue
            for a in dfa.alphabet:
                x, y = dfa.trans[p][a], dfa.trans[q][a]
                if x != y and key(x, y) in marked:
                    newly.append((p, q))
                    break
        if not newly:
            break
        marked.update(newly)
        _entry(log, f"Pass {len(log)}", dfa, classes(), states)
    return classes(), log


ALGORITHMS = {"hopcroft": hopcroft_blocks, "table": table_filling_blocks, "moore": moore_blocks}


# ------------------------------------------------------------ build result
def _build(dfa, block, states):
    members_of, rep = {}, {}
    for s in states:
        members_of.setdefault(block[s], []).append(s)
        rep.setdefault(block[s], s)
    m = DFA(dfa.alphabet, "M", "D")
    order = {block[dfa.start]: 0}
    queue = [block[dfa.start]]
    qi = 0
    while qi < len(queue):
        b = queue[qi]
        qi += 1
        for a in dfa.alphabet:
            tb = block[dfa.trans[rep[b]][a]]
            if tb not in order:
                order[tb] = len(order)
                queue.append(tb)
    for b, nid in order.items():
        m.trans[nid] = {a: order[block[dfa.trans[rep[b]][a]]] for a in dfa.alphabet}
        m.members[nid] = sorted(members_of[b])
        if rep[b] in dfa.accepting:
            m.accepting.add(nid)
    m.start = 0
    return m


def minimize(dfa, method="hopcroft"):
    """Return (minimal_dfa, log). `method` is 'hopcroft', 'table' or 'moore'."""
    if method not in ALGORITHMS:
        raise ValueError(f"Unknown minimization method '{method}'.")
    states = _reachable(dfa)
    block, log = ALGORITHMS[method](dfa, states)
    return _build(dfa, block, states), log

"""
nfa_simulator.py  --  direct NFA simulation + epsilon-closure helpers
======================================================================
Used by the subset construction (eps_closure / move_on) and to show which
NFA states are active while a string is being read.
"""


def eps_closure(nfa, states):
    """All states reachable from `states` using only epsilon edges."""
    closure = set(states)
    stack = list(states)
    while stack:
        s = stack.pop()
        for label, t in nfa.trans[s]:
            if label is None and t not in closure:
                closure.add(t)
                stack.append(t)
    return frozenset(closure)


def move_on(nfa, states, sym):
    """States reachable from `states` by one edge that accepts `sym`."""
    out = set()
    for s in states:
        for label, t in nfa.trans[s]:
            if label is not None and label.matches(sym):
                out.add(t)
    return out


def simulate(nfa, text):
    """Run `text` through the NFA. Returns (accepted, trace).

    trace[0] is the epsilon-closure of the start state; trace[k] is the set of
    active states after reading k characters. It stops early if no state is left.
    """
    current = eps_closure(nfa, {nfa.start})
    trace = [{"char": None, "states": sorted(current)}]
    for ch in text:
        current = eps_closure(nfa, move_on(nfa, current, ch))
        trace.append({"char": ch, "states": sorted(current)})
        if not current:
            return False, trace
    return nfa.accept in current, trace

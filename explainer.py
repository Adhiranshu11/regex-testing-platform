"""
explainer.py  --  Step 5: String Evaluator & Explainer
=======================================================
Runs a string through a DFA and produces a human-readable trace of state
transitions plus a verdict explaining WHY the string was accepted or rejected.
"""
from regex_parser import show_char


def explain(dfa, text):
    trap = dfa.trap_states()
    n = len(text)
    cur = dfa.start
    flag = " (accepting)" if cur in dfa.accepting else ""
    steps = [{"state": cur, "from": None, "char": None,
              "text": f"Start in {dfa.name(cur)}{flag}."}]
    verdict, reason = None, ""

    for i, ch in enumerate(text):
        nxt = dfa.step(cur, ch)
        if nxt is None:
            reason = (f"'{show_char(ch)}' is not in the automaton's alphabet, so no transition exists.")
            steps.append({"state": cur, "from": None, "char": ch,
                          "text": f"Read '{show_char(ch)}' ({i + 1}/{n}): {reason} REJECTED."})
            verdict = False
            break
        msg = f"Read '{show_char(ch)}' ({i + 1}/{n}): {dfa.name(cur)} \u2192 {dfa.name(nxt)}."
        steps.append({"state": nxt, "from": cur, "char": ch, "text": msg})
        cur = nxt
        if cur in trap:
            reason = (f"{dfa.name(cur)} is a trap state: no accepting state can be reached "
                      f"from it, so the string can never be accepted.")
            steps[-1]["text"] += " " + reason + " REJECTED."
            verdict = False
            break

    if verdict is None:
        verdict = cur in dfa.accepting
        if verdict:
            reason = f"Input ended in accepting state {dfa.name(cur)}."
            steps.append({"state": cur, "from": None, "char": None,
                          "text": f"End of input. {reason} ACCEPTED."})
        else:
            reason = f"Input ended in non-accepting state {dfa.name(cur)}."
            steps.append({"state": cur, "from": None, "char": None,
                          "text": f"End of input. {reason} REJECTED."})
    return {"accepted": verdict, "reason": reason, "trace": steps}

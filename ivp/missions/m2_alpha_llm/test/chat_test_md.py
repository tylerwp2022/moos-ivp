#!/usr/bin/env python3
"""
chat_test_md.py: write ../chat_test.md, the chat test script for a
person at the keyboard, from chat_tests.txt, so the two never drift.

    ./chat_test_md.py            # rewrite chat_test.md from chat_tests.txt
    ./chat_test_md.py --check    # exit 1 if chat_test.md is stale

Each test's `say` is the line to type; `expect` and `issue` are the
prose columns (the checks and waits stand in where a test has none).
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chat_driver  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.join(HERE, "chat_tests.txt")
OUT = os.path.join(os.path.dirname(HERE), "chat_test.md")

PREAMBLE = """# m2_alpha_llm chat test script

Generated from `test/chat_tests.txt` by `test/chat_test_md.py`: edit that
file, then run the script (`--check` tells whether this copy is current).

A scripted conversation for the pMarineViewer chat pane that walks every
tool the mission ships, the plan executor, teams and formations, the
contact set, then tries to break things. Each test gives the line to type,
what should happen, and what would be an issue. Type the lines as written
(the wording is deliberate: some are vague, some impossible); answer `y`
or `n` when the pane asks. `test/chat_driver.py` types the same lines for
you and grades the log; this file is for a person at the keyboard, and the
ids are the ones in the driver's results.

Launch with three boats and the warp you normally use:

    ./launch.sh --amt=3 5

abe starts at (0,-20), ben at (30,-20), cal at (-30,-20), all heading
south, 30 m apart. The op-region fence is off until a test turns it on.
Alerts are off for the whole run except 5.10: turn them on from the Action
menu (`alerts_on`) just before it and off again after. Speeds: cruise
2 m/s, helm maximum 4. Where a row says "set first", post that variable
before typing (the driver pokes it; by hand, uPokeDB or the Action menu);
where it says "then", type the second line once the first reply is in;
where it says "afterwards", post that once the test is done.

Fill in the table at the end as you go. Time is warped; divide chat gaps
by the warp before calling a turn slow, or read `LLM_USAGE` afterwards.
"""

AFTER = """
## After the run: what to pull from the shoreside log

    A=XLOG_SHORESIDE_<date>/XLOG_SHORESIDE_<date>.alog
    grep -E '^\\S+\\s+LLM_TOOL_CALL\\s' $A | grep -c '"tree":"x"\\|"tree":""'    # probe calls: must be 0
    grep -E '^\\S+\\s+(COLLISION|NEAR_MISS)\\s' $A                             # who, how close, when
    grep -E '^\\S+\\s+LLM_USAGE\\s' $A | awk '!s[$1]++' | cut -c1-120          # real latency per request
    grep -E '^\\S+\\s+LLM_CHAT_OUT\\s' $A | grep -c 'cut off at max_tokens'    # truncations: must be 0
    grep -E '^\\S+\\s+BT_STATE_[A-Z]+\\s' $A | awk '!s[$1 $2 $4]++'            # every plan's life
    python3 test/pairs.py $A <t0> <t1>                                      # every pair's range over a window

## Results

| ID | Pass | What happened |
|---|---|---|
"""


def cell(text):
    return text.replace("|", "/").strip()


def phase_titles(path):
    """Phase number -> the title from the '# Phase N: ...' comment."""
    titles = {}
    for line in open(path):
        m = re.match(r"^# Phase (\d+): (.*)$", line.rstrip("\n"))
        if m:
            title = re.split(r"\. | \(", m.group(2))[0].rstrip(".")
            titles[m.group(1)] = title
    return titles


def type_cell(t):
    s = "`%s`" % t["say"] if t["say"] else "(nothing typed)"
    if t["pokes"]:
        s = "set first: " + ", ".join(t["pokes"]) + "; " + s
    if t["before_answer"]:
        s += "; before answering: `%s`" % t["before_answer"]
    if t["then"]:
        s += "; then: `%s`" % t["then"]
    if t["after"]:
        s += "; afterwards: " + ", ".join(t["after"])
    return cell(s)


def expect_cell(t):
    if t["expect"]:
        return cell(t["expect"])
    parts = []
    if t["answer"] == "none":
        parts.append("no proposal")
    elif t["answer"] == "n":
        parts.append("a proposal, answered n")
    parts += ["wait " + w for w in t["waits"]]
    parts += [c for c in t["checks"]]
    return cell("; ".join(parts))


def render(tests, titles):
    out = [PREAMBLE]
    phase = None
    for t in tests:
        ph = t["id"].split(".")[0]
        if ph != phase:
            phase = ph
            out.append("\n## Phase %s: %s\n" % (ph, titles.get(ph, "")))
            out.append("| ID | Type | Expect | Issue if |")
            out.append("|---|---|---|---|")
        out.append("| %s | %s | %s | %s |" % (t["id"], type_cell(t), expect_cell(t), cell(t["issue"])))
    out.append(AFTER)
    for t in tests:
        out.append("| %s | | |" % t["id"])
    return "\n".join(out) + "\n"


def main():
    tests = chat_driver.parse_tests(TESTS)
    text = render(tests, phase_titles(TESTS))
    current = open(OUT).read() if os.path.exists(OUT) else ""
    if "--check" in sys.argv:
        if text == current:
            print("chat_test.md is current")
            return 0
        print("chat_test.md is stale: run test/chat_test_md.py")
        return 1
    if text == current:
        print("chat_test.md unchanged")
        return 0
    open(OUT, "w").write(text)
    print("wrote %s: %d tests" % (OUT, len(tests)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

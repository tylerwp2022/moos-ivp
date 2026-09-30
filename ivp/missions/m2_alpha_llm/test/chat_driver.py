#!/usr/bin/env python3
"""
chat_driver.py: run the m2_alpha_llm chat test script against a live
fleet and grade what happened.

The driver launches a copy of the mission (headless, or with the viewer
so you can watch), types each test's line into the chat through
uPokeDB, answers the y/n proposals, waits for what the test says should
happen, and grades the test from the shoreside log: which tool was
called and for whom, the proposal's wording, the reply's length,
collisions and near misses, closest ranges, plan states. Every fact
comes from log lines newer than the test's start, so a value left over
from an earlier test never counts.

    ./chat_driver.py                       # headless, warp 10, every test
    ./chat_driver.py --gui --step          # with the viewer, NEXT_TEST button
    ./chat_driver.py --only 1.1,3.1        # a subset
    ./chat_driver.py --tests my_tests.txt --amt 2 --warp 5 --keep

ANTHROPIC_API_KEY must be in the environment: pLLMAgent reads it.
Results land in test/runs/<stamp>/results.md and results.json, next to
the run's logs. See chat_tests.txt for the test file format.
"""

import argparse
import glob
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time

VEHICLES = [("abe", "yellow",      "x=0,y=-20,heading=180",   "0,-20"),
            ("ben", "red",         "x=30,y=-20,heading=180",  "30,-20"),
            ("cal", "green",       "x=-30,y=-20,heading=180", "-30,-20"),
            ("deb", "dodger_blue", "x=60,y=-20,heading=180",  "60,-20")]
SHORE_MPORT  = 9100
SHORE_PSHARE = 9300
MARK_VAR     = "CHAT_TEST_MARK"
NEXT_VAR     = "CHAT_TEST_NEXT"
CHAT_IN      = "LLM_CHAT_IN"
CHAT_OUT     = "LLM_CHAT_OUT"


def log(msg):
    print(time.strftime("%H:%M:%S") + " " + msg, flush=True)


# ---------------------------------------------------------------
# The test file: blocks headed [id], key = value lines. expect and
# check are the same thing; wait may repeat.

def parse_tests(path):
    tests = []
    cur = None
    with open(path) as f:
        for raw in f:
            line = raw.rstrip("\n")
            s = line.strip()
            if s == "" or s.startswith("#"):
                continue
            m = re.match(r"^\[(.+)\]$", s)
            if m:
                cur = {"id": m.group(1).strip(), "say": "", "answer": "y",
                       "plan_answer": "", "before_answer": "", "pokes": [],
                       "waits": [], "timeout": 120.0,
                       "turn_timeout": 240.0, "settle": 4.0, "checks": []}
                tests.append(cur)
                continue
            if cur is None or "=" not in s:
                continue
            key, val = s.split("=", 1)
            key = key.strip().lower()
            val = val.strip()
            if key == "say":
                cur["say"] = val
            elif key == "answer":
                cur["answer"] = val.lower()
            elif key == "plan_answer":
                cur["plan_answer"] = val
            elif key == "before_answer":
                cur["before_answer"] = val
            elif key == "poke":
                cur["pokes"].append(val)
            elif key == "wait":
                cur["waits"].append(val)
            elif key == "timeout":
                cur["timeout"] = float(val)
            elif key == "turn_timeout":
                cur["turn_timeout"] = float(val)
            elif key == "settle":
                cur["settle"] = float(val)
            elif key in ("expect", "check"):
                cur["checks"].append(val)
    return tests


# ---------------------------------------------------------------
# The shoreside alog, read as it grows. A record is
# (time, key, source, aux, value); the source column is app[:aux].

LINE_RX = re.compile(r"^(\S+)\s+(\S+)\s+(\S+)\s*(.*)$")


class Alog:
    def __init__(self, path):
        self.path = path
        self.pos = 0
        self.records = []     # since the last clear
        self.seen = set()     # (t, key, val): pLogger repeats early posts

    def poll(self):
        new = []
        try:
            with open(self.path, "r", errors="replace") as f:
                f.seek(self.pos)
                for line in f:
                    if not line.endswith("\n"):
                        break            # a partial line, read it next time
                    self.pos += len(line.encode("utf-8", "replace"))
                    if not line or not line[0].isdigit():
                        continue
                    m = LINE_RX.match(line.rstrip("\n"))
                    if not m:
                        continue
                    t = float(m.group(1))
                    key = m.group(2)
                    src = m.group(3)
                    aux = ""
                    if ":" in src:
                        src, aux = src.split(":", 1)
                    val = m.group(4).strip()
                    sig = (t, key, val)
                    if sig in self.seen:
                        continue
                    self.seen.add(sig)
                    rec = (t, key, src, aux, val)
                    self.records.append(rec)
                    new.append(rec)
        except FileNotFoundError:
            pass
        if len(self.seen) > 400000:
            self.seen = set(list(self.seen)[-100000:])
        return new

    def clear(self):
        self.records = []

    def find(self, pred, since=0):
        for i in range(since, len(self.records)):
            if pred(self.records[i]):
                return i
        return -1


# ---------------------------------------------------------------
# Talking to the fleet

class Fleet:
    def __init__(self, mission_dir, scratch, amt, warp, gui):
        self.mission_dir = mission_dir
        self.scratch = scratch
        self.amt = amt
        self.warp = warp
        self.gui = gui
        self.vnames = [v[0] for v in VEHICLES[:amt]]
        self.bin = os.path.dirname(shutil.which("uPokeDB") or
                                   os.path.expanduser("~/moos-ivp/bin/uPokeDB"))
        self.alog = None

    def tool(self, name):
        return os.path.join(self.bin, name)

    def prepare(self):
        os.makedirs(self.scratch, exist_ok=True)
        for name in ("meta_shoreside.moos", "meta_vehicle.moos", "meta_vehicle.bhv",
                     "plugs.moos", "launch_vehicle.sh", "launch_shoreside.sh"):
            shutil.copy(os.path.join(self.mission_dir, name), self.scratch)
        for sub in ("plans", "prompts"):
            dst = os.path.join(self.scratch, sub)
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            shutil.copytree(os.path.join(self.mission_dir, sub), dst)
        # The viewer's fourth button becomes NEXT_TEST for --step, and
        # the Action menu gets the same entry
        p = os.path.join(self.scratch, "meta_shoreside.moos")
        s = open(p).read()
        s = re.sub(r"^(\s*)button_four\s*=.*$",
                   r"\1button_four = NEXT_TEST # " + NEXT_VAR + "=true", s, count=1, flags=re.M)
        s = s.replace("  action = MENU_KEY=alerts_on # LLM_ALERTS=on",
                      "  action = MENU_KEY=alerts_on # LLM_ALERTS=on\n"
                      "  action = MENU_KEY=next_test # " + NEXT_VAR + "=true", 1)
        open(p, "w").write(s)

    def ports_busy(self):
        """Ports another fleet still holds: a launch on them attaches every
        app to nothing (a stepped run left up once did exactly that)."""
        try:
            out = subprocess.run(["ss", "-ltn"], capture_output=True, text=True, timeout=10).stdout
        except (OSError, subprocess.SubprocessError):
            return []
        wanted = [SHORE_MPORT] + [SHORE_MPORT + 1 + i for i in range(self.amt)]
        return [p for p in wanted if re.search(r":%d\s" % p, out)]

    def launch(self):
        env = dict(os.environ)
        env["PATH"] = self.bin + ":" + env.get("PATH", "")
        for i, (vname, color, start, ret) in enumerate(VEHICLES[:self.amt]):
            args = ["./launch_vehicle.sh", "--vname=" + vname, "--color=" + color,
                    "--start_pos=" + start, "--return_pos=" + ret,
                    "--mport=%d" % (SHORE_MPORT + 1 + i), "--pshare=%d" % (SHORE_PSHARE + 1 + i),
                    "--shore_pshare=%d" % SHORE_PSHARE, "--auto", str(self.warp)]
            self._spawn(args, vname + ".log", env)
        args = ["./launch_shoreside.sh", "--auto", "--mport=%d" % SHORE_MPORT,
                "--pshare=%d" % SHORE_PSHARE, "--vnames=" + ":".join(self.vnames), str(self.warp)]
        if not self.gui:
            args.insert(2, "--nogui")
        self._spawn(args, "shore.log", env)

    def _spawn(self, args, logname, env):
        out = open(os.path.join(self.scratch, logname), "w")
        subprocess.Popen(args, cwd=self.scratch, env=env, stdout=out, stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, start_new_session=True)

    def find_alog(self, timeout=90):
        t0 = time.time()
        while time.time() - t0 < timeout:
            hits = sorted(glob.glob(os.path.join(self.scratch, "XLOG_SHORESIDE_*", "*.alog")))
            if hits:
                self.alog = Alog(hits[-1])
                return True
            time.sleep(1)
        return False

    def poke(self, var, val, string=True):
        pair = var + (":=" if string else "=") + val
        subprocess.run([self.tool("uPokeDB"), "targ_shoreside.moos", pair], cwd=self.scratch,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)

    def textbox(self, msg, color="yellow"):
        msg = msg.replace(",", ";").replace("=", " ").replace('"', "'")
        self.poke("VIEW_TEXTBOX", "x=-95,y=36,msg=%s,label=chat_test,fsize=14,mcolor=%s" % (msg[:90], color))

    def wait_ready(self, timeout=300):
        need = set(self.vnames)
        have_tools = False
        idle = set()
        reports = set()
        t0 = time.time()
        while time.time() - t0 < timeout:
            for (t, key, src, aux, val) in self.alog.poll():
                if key == "LLM_TOOLS":
                    have_tools = True
                for v in need:
                    if key == "BT_STATE_" + v.upper():
                        idle.add(v)
                if key.startswith("NODE_REPORT"):
                    m = re.search(r"NAME=([^,]+)", val)
                    if m and m.group(1).lower() in need:
                        reports.add(m.group(1).lower())
            if have_tools and idle == need and reports == need:
                return True
            time.sleep(1)
        log("not ready: tools=%s idle=%s reports=%s" % (have_tools, sorted(idle), sorted(reports)))
        return False

    def kill(self):
        me = os.getpid()
        for sig in ("TERM", "KILL"):
            for p in glob.glob("/proc/[0-9]*"):
                pid = int(p.split("/")[-1])
                if pid == me:
                    continue
                try:
                    if os.readlink(p + "/cwd") == self.scratch:
                        os.kill(pid, 15 if sig == "TERM" else 9)
                except OSError:
                    pass
            time.sleep(3 if sig == "TERM" else 1)


# ---------------------------------------------------------------
# Running one test

def node_positions(records, name):
    """(t, x, y) samples of one vehicle from the NODE_REPORT lines."""
    out = []
    seen = set()
    for (t, key, src, aux, val) in records:
        if not key.startswith("NODE_REPORT"):
            continue
        m = re.search(r"NAME=([^,]+)", val)
        if not m or m.group(1).lower() != name:
            continue
        mx = re.search(r",X=([-0-9.]+)", val)
        my = re.search(r",Y=([-0-9.]+)", val)
        mt = re.search(r",TIME=([0-9.]+)", val)
        if not (mx and my):
            continue
        stamp = mt.group(1) if mt else str(t)
        if stamp in seen:
            continue
        seen.add(stamp)
        out.append((float(stamp), float(mx.group(1)), float(my.group(1))))
    out.sort()
    return out


def min_range(records, a, b):
    pa = node_positions(records, a)
    pb = node_positions(records, b)
    if not pa or not pb:
        return None
    best = None
    j = 0
    for (t, x, y) in pa:
        while j + 1 < len(pb) and pb[j + 1][0] <= t:
            j += 1
        if abs(pb[j][0] - t) > 3:
            continue
        d = math.hypot(x - pb[j][1], y - pb[j][2])
        if best is None or d < best:
            best = d
    return best


def sentences(text):
    text = text.replace("!@#", " ")
    parts = [p for p in re.split(r"[.!?]+(?:\s+|$)", text) if p.strip()]
    return len(parts)


def tool_calls(records):
    out = []
    for (t, key, src, aux, val) in records:
        if key != "LLM_TOOL_CALL":
            continue
        m = re.match(r"tool=([A-Za-z_]+),turn=(\d+),args=(.*)$", val)
        if not m:
            continue
        try:
            args = json.loads(m.group(3))
        except ValueError:
            args = {}
        out.append({"t": t, "tool": m.group(1), "args": args})
    return out


def grade(test, records, facts):
    """Evaluate every check; return (passed, [failure notes])."""
    fails = []
    calls = tool_calls(records)
    proposals = [r for r in records if r[1] == CHAT_OUT and r[3].startswith("ask")]
    replies = [r for r in records if r[1] == CHAT_OUT and not r[3].startswith("ask")
               and not r[4].startswith("[")]
    reply = replies[-1][4] if replies else ""
    events = [r for r in records if r[1] in ("COLLISION", "NEAR_MISS")]

    def pair_in(val, a, b):
        if not a:
            return True
        n1 = re.search(r"vname1=([^,]+)", val)
        n2 = re.search(r"vname2=([^,]+)", val)
        names = {n1.group(1).lower() if n1 else "", n2.group(1).lower() if n2 else ""}
        if not b:
            return a in names
        return names == {a, b}

    def pair_args(toks):
        if len(toks) >= 3:
            return (toks[1].lower(), toks[2].lower())
        if len(toks) == 2:
            return (toks[1].lower(), "")
        return ("", "")

    notes = []

    for w in facts["waits_unmet"]:
        fails.append("wait not met: " + w)
    if facts.get("turn_error"):
        fails.append("turn ended in an error: " + facts["turn_error"][:80])
    if not facts.get("turn_done"):
        fails.append("no reply before the turn timeout")

    for c in test["checks"]:
        toks = c.split()
        observe = bool(toks) and toks[0].lower() == "observe"
        if observe:
            toks = toks[1:]
            c = " ".join(toks)
        name = toks[0].lower() if toks else ""
        ok = True
        note = c
        if name == "no_proposal":
            ok = len(proposals) == 0
        elif name == "proposal":
            ok = len(proposals) >= 1
        elif name == "proposals":
            ok = len(proposals) == int(toks[1])
            note = "%s (saw %d)" % (c, len(proposals))
        elif name == "tool":
            wanted = set(toks[1].lower().split("|"))
            ok = any(k["tool"] in wanted for k in calls)
            note = "%s (saw %s)" % (c, ",".join(k["tool"] for k in calls) or "none")
        elif name == "no_tool":
            ok = len(calls) == 0
            note = "%s (saw %s)" % (c, ",".join(k["tool"] for k in calls) or "none")
        elif name == "target":
            ok = any(str(k["args"].get("vname", "")).lower() == toks[1].lower() for k in calls)
        elif name == "head_for":
            ok = any(("run_plan for " + toks[1].lower() + ":") in r[4].lower() for r in proposals)
        elif name == "no_probe":
            bad = [k for k in calls if k["tool"] == "run_plan" and
                   not str(k["args"].get("tree", "")).lstrip().startswith("<")]
            ok = len(bad) == 0
        elif name == "tree_has":
            want = " ".join(toks[1:]).lower()
            ok = any(want in str(k["args"].get("tree", "")).lower() for k in calls if k["tool"] == "run_plan")
        elif name == "no_collision":
            a, b = pair_args(toks)
            ok = not any(r[1] == "COLLISION" and pair_in(r[4], a, b) for r in events)
        elif name == "collision":
            a, b = pair_args(toks)
            ok = any(r[1] == "COLLISION" and pair_in(r[4], a, b) for r in events)
        elif name == "no_near_miss":
            a, b = pair_args(toks)
            ok = not any(r[1] == "NEAR_MISS" and pair_in(r[4], a, b) for r in events)
        elif name == "near_miss":
            a, b = pair_args(toks)
            ok = any(r[1] == "NEAR_MISS" and pair_in(r[4], a, b) for r in events)
        elif name == "reply_sentences":
            n = sentences(reply)
            ok = n <= int(toks[2]) if toks[1] == "<=" else n >= int(toks[2])
            note = "%s (saw %d)" % (c, n)
        elif name == "reply_asks":
            ok = "?" in reply
        elif name == "reply_contains":
            ok = " ".join(toks[1:]).lower() in reply.lower()
        elif name == "chat_contains":
            want = " ".join(toks[1:]).lower()
            ok = any(want in r[4].lower() for r in records if r[1] == CHAT_OUT)
        elif name == "proposal_contains":
            want = " ".join(toks[1:]).lower()
            ok = any(want in r[4].lower() for r in proposals)
        elif name == "state":
            last = [r for r in records if r[1] == toks[1]]
            ok = bool(last) and last[-1][4] == toks[2]
            note = "%s (saw %s)" % (c, last[-1][4] if last else "nothing")
        elif name == "min_range":
            d = min_range(records, toks[1].lower(), toks[2].lower())
            ok = (d is not None) and d >= float(toks[4])
            note = "%s (saw %s)" % (c, "%.1f" % d if d is not None else "no positions")
        elif name == "no_truncation":
            ok = not any("cut off at max_tokens" in r[4] for r in records if r[1] == CHAT_OUT)
        elif name == "latency":
            lat = [float(m.group(1)) for r in records if r[1] == "LLM_USAGE"
                   for m in [re.search(r"latency=([0-9.]+)", r[4])] if m]
            ok = bool(lat) and max(lat) <= float(toks[2])
            note = "%s (saw %s)" % (c, ",".join("%.0f" % x for x in lat) or "none")
        else:
            ok = False
            note = "unknown check: " + c
        if observe:
            notes.append(("ok: " if ok else "not: ") + note)
        elif not ok:
            fails.append(note)
    return (len(fails) == 0, fails, {"reply": reply, "proposals": [r[4] for r in proposals],
                                     "calls": [(k["tool"], k["args"].get("vname", "")) for k in calls],
                                     "events": [r[4] for r in events], "notes": notes})


def run_test(fleet, test, step):
    alog = fleet.alog
    facts = {"waits_unmet": list(test["waits"]), "turn_done": False, "turn_error": ""}
    log("== %s: %s" % (test["id"], test["say"]))

    # The window starts at the mark: nothing older counts
    fleet.poke(MARK_VAR, test["id"])
    t0 = time.time()
    mark_idx = -1
    while time.time() - t0 < 30 and mark_idx < 0:
        alog.poll()
        mark_idx = alog.find(lambda r: r[1] == MARK_VAR and r[4] == test["id"])
        if mark_idx < 0:
            time.sleep(0.5)
    if mark_idx < 0:
        return (False, ["the mark never reached the log"], {})
    alog.records = alog.records[mark_idx:]

    if step:
        fleet.textbox("NEXT_TEST for %s: %s" % (test["id"], test["say"]), "white")
        log("   waiting for the NEXT_TEST button")
        while True:
            alog.poll()
            if alog.find(lambda r: r[1] == NEXT_VAR) >= 0:
                break
            time.sleep(0.5)
        alog.records = alog.records[alog.find(lambda r: r[1] == NEXT_VAR):]
    fleet.textbox("test %s: %s" % (test["id"], test["say"]), "yellow")
    for pk in test["pokes"]:
        var, val = [x.strip() for x in pk.split("=", 1)]
        log("   poke " + var + " = " + val)
        fleet.poke(var, val)

    # Type the line, then follow the turn from the log
    if test["say"] != "":
        fleet.poke(CHAT_IN, test["say"])
    else:
        facts["turn_done"] = True
    after = len(alog.records)
    answered = 0
    t0 = time.time()
    while not facts["turn_done"] and time.time() - t0 < test["turn_timeout"]:
        alog.poll()
        i = after
        while i < len(alog.records):
            (t, key, src, aux, val) = alog.records[i]
            i += 1
            if key == CHAT_OUT and aux.startswith("ask"):
                answered += 1
                ans = test["answer"]
                if ans == "none":
                    log("   unexpected proposal, declining")
                    ans = "n"
                else:
                    log("   proposal, answering " + ans)
                if test["before_answer"] and answered == 1:
                    log("   typing first: " + test["before_answer"])
                    fleet.poke(CHAT_IN, test["before_answer"])
                    tb = time.time()
                    while time.time() - tb < 30:
                        alog.poll()
                        if alog.find(lambda r: r[1] == CHAT_OUT and not r[3].startswith("ask")
                                     and not r[4].startswith("["), i) >= 0:
                            break
                        time.sleep(0.5)
                fleet.poke(CHAT_IN, ans)
                after = len(alog.records)      # the reply comes after the answer
                break
            if key.startswith("BT_CHAT") and aux.startswith("ask") and test["plan_answer"]:
                log("   the plan asks, answering " + test["plan_answer"])
                fleet.poke(CHAT_IN, test["plan_answer"])
                after = len(alog.records)
                break
            if key == CHAT_OUT:
                if val.startswith("[error"):
                    facts["turn_error"] = val
                    facts["turn_done"] = True
                elif not val.startswith("["):
                    facts["turn_done"] = True
                    log("   reply: " + val[:100].replace("!@#", " "))
        else:
            after = i
        if facts["turn_done"]:
            break
        time.sleep(0.7)
    if not facts["turn_done"]:
        log("   no reply within %.0f s" % test["turn_timeout"])

    # What the test says should happen next
    t0 = time.time()
    asked_from = len(alog.records)
    while facts["waits_unmet"] and time.time() - t0 < test["timeout"]:
        alog.poll()
        still = []
        for w in facts["waits_unmet"]:
            if "=" in w:
                var, want = [x.strip() for x in w.split("=", 1)]
            else:
                var, want = w.strip(), None
            hit = alog.find(lambda r, var=var, want=want: r[1] == var and (want is None or r[4] == want))
            if hit < 0:
                still.append(w)
        facts["waits_unmet"] = still
        if still:
            # a plan may ask while the test waits on its outcome
            for (t, key, src, aux, val) in alog.records[asked_from:]:
                asked_from += 1
                if key.startswith("BT_CHAT") and aux.startswith("ask") and test["plan_answer"]:
                    log("   the plan asks, answering " + test["plan_answer"])
                    fleet.poke(CHAT_IN, test["plan_answer"])
            time.sleep(1)
    if facts["waits_unmet"]:
        log("   waits unmet: " + "; ".join(facts["waits_unmet"]))
    time.sleep(test["settle"])
    alog.poll()
    passed, fails, detail = grade(test, alog.records, facts)
    fleet.textbox("test %s: %s" % (test["id"], "PASS" if passed else "FAIL " + (fails[0] if fails else "")),
                  "green" if passed else "red")
    log("   " + ("PASS" if passed else "FAIL: " + "; ".join(fails)))
    return (passed, fails, detail)


# ---------------------------------------------------------------

def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description="drive and grade the m2_alpha_llm chat tests")
    ap.add_argument("--tests", default=os.path.join(here, "chat_tests.txt"))
    ap.add_argument("--mission", default=os.path.dirname(here))
    ap.add_argument("--only", default="", help="comma-separated test ids")
    ap.add_argument("--amt", type=int, default=3, help="vehicles, 1 to 4")
    ap.add_argument("--warp", type=int, default=0, help="time warp (10 headless, 5 with --gui)")
    ap.add_argument("--gui", action="store_true", help="launch pMarineViewer too")
    ap.add_argument("--step", action="store_true", help="wait for NEXT_TEST before each test (implies --gui)")
    ap.add_argument("--pause", type=float, default=0.0, help="seconds between tests")
    ap.add_argument("--keep", action="store_true", help="leave the fleet running at the end")
    ap.add_argument("--runs", default=os.path.join(here, "runs"))
    args = ap.parse_args()
    if args.step:
        args.gui = True
    if args.warp <= 0:
        args.warp = 5 if args.gui else 10
    if not os.environ.get("ANTHROPIC_API_KEY"):
        log("ANTHROPIC_API_KEY is not set: pLLMAgent will answer every line with an error")

    tests = parse_tests(args.tests)
    if args.only:
        keep = set(x.strip() for x in args.only.split(","))
        tests = [t for t in tests if t["id"] in keep]
    if not tests:
        log("no tests selected")
        return 2

    stamp = time.strftime("%Y%m%d_%H%M%S")
    scratch = os.path.join(os.path.abspath(args.runs), stamp)
    fleet = Fleet(os.path.abspath(args.mission), scratch, args.amt, args.warp, args.gui)
    busy = fleet.ports_busy()
    if busy:
        log("ports %s are in use: a fleet from an earlier run is still up; take it down first "
            "(.claude/skills/headless-fleet/fleet.sh down <its run dir>)" % ",".join(str(p) for p in busy))
        return 1
    fleet.prepare()
    log("launching %d boats at warp %d in %s%s" % (args.amt, args.warp, scratch,
                                                  " with the viewer" if args.gui else ""))
    fleet.launch()
    if not fleet.find_alog():
        log("no shoreside log appeared")
        fleet.kill()
        return 1
    if not fleet.wait_ready():
        fleet.kill()
        return 1
    log("fleet ready: " + ", ".join(fleet.vnames))
    time.sleep(3)

    results = []
    try:
        for test in tests:
            passed, fails, detail = run_test(fleet, test, args.step)
            results.append({"id": test["id"], "say": test["say"], "passed": passed,
                            "fails": fails, "detail": detail})
            if args.pause > 0:
                time.sleep(args.pause)
    except KeyboardInterrupt:
        log("interrupted")
    finally:
        write_results(scratch, results)
        if not args.keep:
            fleet.kill()
            log("fleet down")
        else:
            log("fleet left running in " + scratch)
    npass = sum(1 for r in results if r["passed"])
    log("%d of %d passed" % (npass, len(results)))
    return 0 if npass == len(results) else 1


def write_results(scratch, results):
    md = ["| ID | Pass | Typed | What happened |", "|---|---|---|---|"]
    for r in results:
        what = "; ".join(r["fails"]) if r["fails"] else r["detail"].get("reply", "")[:120].replace("!@#", " ")
        if r["detail"].get("notes"):
            what += " [" + "; ".join(r["detail"]["notes"]) + "]"
        md.append("| %s | %s | %s | %s |" % (r["id"], "yes" if r["passed"] else "NO",
                                          r["say"].replace("|", "/"), what.replace("|", "/")))
    open(os.path.join(scratch, "results.md"), "w").write("\n".join(md) + "\n")
    open(os.path.join(scratch, "results.json"), "w").write(json.dumps(results, indent=1))
    print("\n".join(md))


if __name__ == "__main__":
    sys.exit(main())

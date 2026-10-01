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
    ./chat_driver.py --gui                 # with the viewer: it asks you after every test
    ./chat_driver.py --only 1.1,3.1        # a subset
    ./chat_driver.py --from 4.1 --to 4.6   # a stretch of the file, in its order
    ./chat_driver.py --phase 4,5           # whole phases (the id before the dot)
    ./chat_driver.py --list --phase 5      # show the selection, launch nothing
    ./chat_driver.py --tests my_tests.txt --amt 2 --warp 5 --keep

The viewer's fourth button (NEXT_TEST, also Action > next_test) always
means "move on": pressed while a test waits for the reply or for the
boats, the test is cut short, graded on what happened and marked cut;
pressed during the settle it just ends the watch. With the viewer the
driver then asks in the chat pane whether the boats did what you
expected: NEXT_TEST answers yes, a line typed with a leading # is your
words (a no, unless it starts with yes or ok); the answer goes in the
Operator column of results.md. The question fits the test (the boats
where it moves them, the map where it draws, the agent otherwise; an
`ask` line in the test file sets its own). Nobody answering within
--ask-timeout counts as "no answer" and the run goes on.

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
NOTE_VAR     = "LLM_CHAT_NOTE"
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
                       "then": "", "then_answer": "y", "then_after": 0.0, "after": [], "ask": "",
                       "expect": "", "issue": "",
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
            elif key == "then":
                cur["then"] = val
            elif key == "then_answer":
                cur["then_answer"] = val.lower()
            elif key == "then_after":
                cur["then_after"] = float(val)
            elif key == "after":
                cur["after"].append(val)
            elif key == "ask":
                cur["ask"] = val
            elif key in ("expect", "issue"):
                cur[key] = val             # prose for chat_test.md, not graded
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
        self.dead = False     # the shoreside stopped answering

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
        # The viewer's fourth button becomes NEXT_TEST, and
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
        app to nothing (a viewer run left up once did exactly that)."""
        try:
            out = subprocess.run(["ss", "-ltnu"], capture_output=True, text=True, timeout=10).stdout
        except (OSError, subprocess.SubprocessError):
            return []
        wanted = [SHORE_MPORT] + [SHORE_MPORT + 1 + i for i in range(self.amt)]      # MOOSDBs, tcp
        wanted += [SHORE_PSHARE] + [SHORE_PSHARE + 1 + i for i in range(self.amt)]   # pShare, udp
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

    def alive(self):
        """The shoreside MOOSDB is still listening."""
        return SHORE_MPORT in self.ports_busy()

    def poke(self, var, val, string=True):
        """Post var to the shoreside; False once the shoreside is gone
        (uPokeDB retries a vanished MOOSDB until the timeout, so a dead
        fleet is remembered and not poked again)."""
        if self.dead:
            return False
        pair = var + (":=" if string else "=") + val
        try:
            subprocess.run([self.tool("uPokeDB"), "targ_shoreside.moos", pair], cwd=self.scratch,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        except (subprocess.TimeoutExpired, OSError):
            self.dead = True
            log("   the shoreside did not answer a poke")
            return False
        return True

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
        for p in self.ports_busy():
            try:
                out = subprocess.run(["ss", "-ltnup"], capture_output=True, text=True, timeout=10).stdout
                for line in out.splitlines():
                    if re.search(r":%d\s" % p, line):
                        for m in re.finditer(r"pid=(\d+)", line):
                            os.kill(int(m.group(1)), 9)
            except (OSError, subprocess.SubprocessError, ValueError):
                pass


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


def aux_src(aux):
    """What opened the turn a chat line belongs to, from the source aux
    pLLMAgent tags it with: operator, alert or plan; "" on a build
    without the tag."""
    m = re.search(r"(?:^|,)src=([a-z]+)", aux)
    return m.group(1) if m else ""


def operator_line(rec):
    """A chat line of the operator's own turn (or of an untagged build)."""
    return aux_src(rec[3]) in ("", "operator")


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
    proposals = [r for r in records if r[1] == CHAT_OUT and r[3].startswith("ask")
                 and operator_line(r)]
    replies = [r for r in records if r[1] == CHAT_OUT and not r[3].startswith("ask")
               and not r[4].startswith("[") and operator_line(r)]
    alert_replies = [r for r in records if r[1] == CHAT_OUT and not r[3].startswith("ask")
                     and not r[4].startswith("[") and not operator_line(r)]
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

    if facts.get("skipped"):
        fails.append("cut short by NEXT_TEST during the " + facts["skipped"])
    for w in facts["waits_unmet"]:
        fails.append("wait not met: " + w)
    if facts.get("turn_error"):
        fails.append("turn ended in an error: " + facts["turn_error"][:80])
    if not facts.get("turn_done"):
        fails.append("no reply before the turn timeout")
    if facts.get("alert_proposals"):
        notes.append("declined %d proposal(s) from alert turns" % facts["alert_proposals"])

    def evaluate(c):
        """One check -> (ok, note); `either A | B` passes on either."""
        toks = c.split()
        name = toks[0].lower() if toks else ""
        if name == "either":
            parts = [x.strip() for x in c[len("either"):].split("|") if x.strip()]
            results = [evaluate(x) for x in parts]
            return (any(r[0] for r in results), "either " + " | ".join(r[1] for r in results))
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
            if len(toks) > 1:          # no call of this name (or these names)
                wanted = set(toks[1].lower().split("|"))
                ok = not any(k["tool"] in wanted for k in calls)
            else:                      # no tool call at all
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
        elif name == "alert_reply":
            n = [sentences(r[4]) for r in alert_replies]
            ok = bool(n) and (len(toks) < 3 or max(n) <= int(toks[2]))
            note = "%s (saw %s)" % (c, ",".join(str(x) for x in n) or "none")
        elif name == "latency":
            lat = [float(m.group(1)) for r in records if r[1] == "LLM_USAGE"
                   for m in [re.search(r"latency=([0-9.]+)", r[4])] if m]
            ok = bool(lat) and max(lat) <= float(toks[2])
            note = "%s (saw %s)" % (c, ",".join("%.0f" % x for x in lat) or "none")
        else:
            ok = False
            note = "unknown check: " + c
        return (ok, note)

    for c in test["checks"]:
        toks = c.split()
        observe = bool(toks) and toks[0].lower() == "observe"
        if observe:
            c = " ".join(toks[1:])
        ok, note = evaluate(c)
        if observe:
            notes.append(("ok: " if ok else "not: ") + note)
        elif not ok:
            fails.append(note)
    return (len(fails) == 0, fails, {"reply": reply, "proposals": [r[4] for r in proposals],
                                     "calls": [(k["tool"], k["args"].get("vname", "")) for k in calls],
                                     "events": [r[4] for r in events], "notes": notes,
                                     "alert_replies": [r[4] for r in alert_replies],
                                     "cut": bool(facts.get("skipped"))})


def pressed_after(alog, t):
    """True once the viewer's NEXT_TEST button (or Action > next_test) has
    posted with a log time later than t: the operator wants to move on."""
    return alog.find(lambda r: r[1] == NEXT_VAR and r[0] > t) >= 0


def follow_turn(fleet, alog, test, text, answer, facts, first, pressed, gone):
    """Type text into the chat and follow the model's turn in the log
    until its reply: a proposal is answered with `answer` (none = one
    is not expected, decline it), the first proposal of the test's
    first line preceded by before_answer, a plan's Ask answered with
    plan_answer. Sets facts turn_done and turn_error."""
    facts["turn_done"] = False
    facts["turn_error"] = ""
    fleet.poke(CHAT_IN, text)
    after = len(alog.records)
    answered = 0
    t0 = time.time()
    while not facts["turn_done"] and time.time() - t0 < test["turn_timeout"]:
        alog.poll()
        i = after
        while i < len(alog.records):
            (t, key, src, aux, val) = alog.records[i]
            i += 1
            if key == CHAT_OUT and aux.startswith("ask") and not operator_line(alog.records[i - 1]):
                log("   proposal from an alert turn, declining")
                facts["alert_proposals"] = facts.get("alert_proposals", 0) + 1
                fleet.poke(CHAT_IN, "n")
                after = len(alog.records)
                break
            if key == CHAT_OUT and aux.startswith("ask"):
                answered += 1
                ans = answer
                if ans == "none":
                    log("   unexpected proposal, declining")
                    ans = "n"
                else:
                    log("   proposal, answering " + ans)
                if first and test["before_answer"] and answered == 1:
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
            if key == CHAT_OUT and not operator_line(alog.records[i - 1]):
                if not val.startswith("["):
                    log("   (alert turn: " + val[:80].replace("!@#", " ") + ")")
                continue
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
        if pressed():
            facts["skipped"] = "turn"
            log("   NEXT_TEST pressed: moving on without the reply")
            break
        if gone():
            break
        time.sleep(0.7)
    if not facts["turn_done"] and not facts["skipped"] and not fleet.dead:
        log("   no reply within %.0f s" % test["turn_timeout"])


MOTION_RX = re.compile(r"^(MISSION_|BT_STATE_|TASK_|DEPLOY_|RETURN_|TEAM_MISSION|COLLISION|"
                       r"NEAR_MISS|CONVOY|INTERCEPT|OPREGION|WPT_)")


def question_for(test):
    """The verification question that fits the test: the boats where it
    moves them, the map where it draws, the agent's answer or action
    otherwise; an `ask` line in the test file overrides it."""
    if test["ask"]:
        return test["ask"]
    waits = [w.split("=")[0].strip() for w in test["waits"]]
    checks = " ".join(test["checks"])
    if any(MOTION_RX.match(w) for w in waits) or test["after"] \
            or re.search(r"\b(min_range|collision|near_miss|head_for)\b", checks):
        return "Did the boats do what you expected?"
    if any(w.startswith("VIEW_") for w in waits) or re.search(r"tool (draw|erase)", checks):
        return "Did the map show what you expected?"
    return "Did the agent do what was intended?"


def ask_operator(fleet, test, verdict, timeout):
    """Ask in the chat pane whether the test went as the operator
    expected. NEXT_TEST means yes; a # line is the operator's words, a
    no unless it starts with yes or ok. Returns the answer text."""
    alog = fleet.alog
    alog.poll()
    base_t = alog.records[-1][0] if alog.records else 0.0
    head = "[test %s, auto %s]" % (test["id"], verdict)
    fleet.poke(CHAT_OUT, head + " " + question_for(test) +
               " Press NEXT_TEST for yes, or type # and what was off")
    # The window for the answer opens when the question itself is in the
    # log, so a press from the settle that reaches the log late cannot
    # count; ten seconds at most, then the last record's time serves
    t0 = time.time()
    while time.time() - t0 < 10 and not fleet.dead:
        alog.poll()
        i = alog.find(lambda r: r[1] == CHAT_OUT and r[4].startswith(head))
        if i >= 0:
            base_t = alog.records[i][0]
            break
        time.sleep(0.3)
    t0 = time.time()
    while time.time() - t0 < timeout and not fleet.dead:
        alog.poll()
        i = alog.find(lambda r: r[1] in (NEXT_VAR, NOTE_VAR) and r[0] > base_t)
        if i >= 0:
            rec = alog.records[i]
            if rec[1] == NEXT_VAR:
                return "yes"
            note = rec[4].strip()
            low = note.lower()
            yes = low in ("y", "yes", "ok") or low.startswith(("yes ", "yes,", "yes:", "ok ", "ok,", "ok:"))
            return ("yes: " if yes else "no: ") + note
        time.sleep(0.5)
    return "no answer"


def run_test(fleet, test):
    alog = fleet.alog
    facts = {"waits_unmet": list(test["waits"]), "turn_done": False, "turn_error": "",
             "skipped": "", "alert_proposals": 0}
    log("== %s: %s" % (test["id"], test["say"]))

    # The window starts at the mark: nothing older counts
    if not fleet.poke(MARK_VAR, test["id"]):
        return (False, ["the shoreside is gone"], {"dead": True})
    t0 = time.time()
    mark_idx = -1
    while time.time() - t0 < 30 and mark_idx < 0:
        alog.poll()
        mark_idx = alog.find(lambda r: r[1] == MARK_VAR and r[4] == test["id"])
        if mark_idx < 0:
            time.sleep(0.5)
    if mark_idx < 0:
        if not fleet.alive():
            fleet.dead = True
            return (False, ["the shoreside is gone"], {"dead": True})
        return (False, ["the mark never reached the log"], {})

    # A fleet that dies mid-test must not leave the loops below waiting
    # for a log that will never grow: checked every ten seconds
    checked = [time.time()]

    def gone():
        if fleet.dead:
            return True
        if time.time() - checked[0] >= 10:
            checked[0] = time.time()
            if not fleet.alive():
                fleet.dead = True
                log("   the shoreside is gone")
        return fleet.dead
    alog.records = alog.records[mark_idx:]

    # A NEXT_TEST press logged after base_t means "move on"
    base_t = alog.records[0][0]

    def pressed():
        return pressed_after(alog, base_t)

    fleet.textbox("%s running (NEXT_TEST skips): %s" % (test["id"], test["say"]), "yellow")
    for pk in test["pokes"]:
        var, val = [x.strip() for x in pk.split("=", 1)]
        log("   poke " + var + " = " + val)
        fleet.poke(var, val)

    # Type the line and follow the turn from the log; then the second
    # line, if the test has one, once the first turn is complete
    if test["say"] != "":
        follow_turn(fleet, alog, test, test["say"], test["answer"], facts, True, pressed, gone)
    else:
        facts["turn_done"] = True
    if test["then"] and facts["turn_done"] and not facts["skipped"] and not fleet.dead:
        if test["then_after"] > 0:
            t0 = time.time()
            while time.time() - t0 < test["then_after"] and not pressed() and not gone():
                alog.poll()
                time.sleep(0.5)
        log("   then: " + test["then"])
        follow_turn(fleet, alog, test, test["then"], test["then_answer"], facts, False, pressed, gone)

    # What the test says should happen next
    t0 = time.time()
    asked_from = len(alog.records)
    while facts["waits_unmet"] and not facts["skipped"] and not fleet.dead \
            and time.time() - t0 < test["timeout"]:
        alog.poll()
        if pressed():
            facts["skipped"] = "wait"
            log("   NEXT_TEST pressed: moving on, waits left unmet")
            break
        if gone():
            break
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
                if key == CHAT_OUT and aux.startswith("ask") and not operator_line((t, key, src, aux, val)):
                    log("   proposal from an alert turn during the wait, declining")
                    facts["alert_proposals"] = facts.get("alert_proposals", 0) + 1
                    fleet.poke(CHAT_IN, "n")
            time.sleep(1)
    if facts["waits_unmet"]:
        log("   waits unmet: " + "; ".join(facts["waits_unmet"]))

    # Put the fleet back in a sane state before grading
    for pk in test["after"]:
        var, val = [x.strip() for x in pk.split("=", 1)]
        log("   after: poke " + var + " = " + val)
        fleet.poke(var, val)
    # Let the log catch up, and watch the boats for a check with no wait;
    # a press ends the watch after the first two seconds
    t0 = time.time()
    while time.time() - t0 < test["settle"] and not fleet.dead:
        alog.poll()
        if time.time() - t0 >= 2.0 and pressed():
            if not facts["skipped"]:
                log("   NEXT_TEST pressed: settle cut short")
            break
        time.sleep(0.5)
    alog.poll()
    passed, fails, detail = grade(test, alog.records, facts)
    if fleet.dead:
        fails.insert(0, "the shoreside is gone")
        passed = False
        detail["dead"] = True
    verdict = "CUT" if facts["skipped"] else ("PASS" if passed else "FAIL")
    fleet.textbox("test %s: %s" % (test["id"], verdict + ("" if passed else " " + (fails[0] if fails else ""))),
                  {"PASS": "green", "FAIL": "red", "CUT": "orange"}[verdict])
    log("   " + verdict + ("" if passed else ": " + "; ".join(fails)))
    return (passed, fails, detail)


# ---------------------------------------------------------------

def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description="drive and grade the m2_alpha_llm chat tests")
    ap.add_argument("--tests", default=os.path.join(here, "chat_tests.txt"))
    ap.add_argument("--mission", default=os.path.dirname(here))
    ap.add_argument("--only", default="", help="comma-separated test ids")
    ap.add_argument("--from", dest="start", default="", metavar="ID",
                    help="start at this test (file order) and run to the end")
    ap.add_argument("--to", dest="stop", default="", metavar="ID", help="stop after this test")
    ap.add_argument("--phase", default="", help="comma-separated phases, the id's part before the dot")
    ap.add_argument("--list", action="store_true", help="print the selected tests and exit")
    ap.add_argument("--amt", type=int, default=3, help="vehicles, 1 to 4")
    ap.add_argument("--warp", type=int, default=0, help="time warp (10 headless, 5 with --gui)")
    ap.add_argument("--gui", action="store_true", help="launch pMarineViewer too")
    ap.add_argument("--no-ask", action="store_true", help="with --gui: do not ask after each test")
    ap.add_argument("--ask-timeout", type=float, default=120.0,
                    help="real seconds to wait for the operator's answer (default 120)")
    ap.add_argument("--pause", type=float, default=0.0, help="seconds between tests")
    ap.add_argument("--keep", action="store_true", help="leave the fleet running at the end")
    ap.add_argument("--runs", default=os.path.join(here, "runs"))
    args = ap.parse_args()
    if args.warp <= 0:
        args.warp = 5 if args.gui else 10
    if not os.environ.get("ANTHROPIC_API_KEY"):
        log("ANTHROPIC_API_KEY is not set: pLLMAgent will answer every line with an error")

    tests = parse_tests(args.tests)
    ids = [t["id"] for t in tests]
    for want in (args.start, args.stop):
        if want and want not in ids:
            log("no test %s in %s" % (want, args.tests))
            return 2
    if args.start:
        tests = tests[ids.index(args.start):]
    if args.stop:
        tests = [t for t in tests if ids.index(t["id"]) <= ids.index(args.stop)]
    if args.phase:
        keep = set(x.strip() for x in args.phase.split(","))
        tests = [t for t in tests if t["id"].split(".")[0] in keep]
    if args.only:
        keep = set(x.strip() for x in args.only.split(","))
        tests = [t for t in tests if t["id"] in keep]
    if not tests:
        log("no tests selected")
        return 2
    if args.list:
        for t in tests:
            print("%-5s %-44s %s" % (t["id"], question_for(t), t["say"][:60]))
        print("%d tests" % len(tests))
        return 0

    # The test file's timeouts are real seconds at warp 10; a slower warp
    # needs proportionally longer, a faster one less
    scale = 10.0 / args.warp
    for t in tests:
        t["timeout"] *= scale
        t["then_after"] *= scale
        t["settle"] = max(t["settle"], t["settle"] * scale)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    scratch = os.path.join(os.path.abspath(args.runs), stamp)
    fleet = Fleet(os.path.abspath(args.mission), scratch, args.amt, args.warp, args.gui)
    busy = fleet.ports_busy()
    if busy:
        log("ports %s are in use: a fleet from an earlier run is still up; take it down first "
            "(test/fleet.sh down <its run dir>)" % ",".join(str(p) for p in busy))
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
    if args.gui:
        log("NEXT_TEST (the viewer's fourth button, or Action > next_test) moves on to the next test"
            + ("" if args.no_ask else "; after each test the pane asks whether the boats did what "
               "you expected: NEXT_TEST = yes, a line starting with # = your words"))
    time.sleep(3)

    results = []
    try:
        for test in tests:
            passed, fails, detail = run_test(fleet, test)
            results.append({"id": test["id"], "say": test["say"], "passed": passed,
                            "fails": fails, "detail": detail, "operator": ""})
            if detail.get("dead"):
                log("the shoreside stopped answering: ending the run with the results so far")
                break
            if args.gui and not args.no_ask:
                verdict = "CUT" if detail.get("cut") else ("PASS" if passed else "FAIL")
                answer = ask_operator(fleet, test, verdict, args.ask_timeout)
                log("   operator: " + answer)
                results[-1]["operator"] = answer
            if args.pause > 0:
                t0 = time.time()
                recs = fleet.alog.records
                since_t = recs[-1][0] if recs else 0.0
                while time.time() - t0 < args.pause:
                    fleet.alog.poll()
                    if pressed_after(fleet.alog, since_t):
                        break
                    time.sleep(0.5)
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
    ncut = sum(1 for r in results if r["detail"].get("cut"))
    ops = [r.get("operator", "") for r in results if r.get("operator")]
    summary = "%d of %d passed%s" % (npass, len(results),
                                     (", %d cut short by NEXT_TEST" % ncut) if ncut else "")
    if ops:
        summary += "; operator: %d yes, %d no, %d unanswered" % (
            sum(1 for o in ops if o.startswith("yes")), sum(1 for o in ops if o.startswith("no:")),
            sum(1 for o in ops if o == "no answer"))
    log(summary)
    return 0 if npass == len(results) else 1


def write_results(scratch, results):
    md = ["| ID | Pass | Operator | Typed | What happened |", "|---|---|---|---|---|"]
    for r in results:
        what = "; ".join(r["fails"]) if r["fails"] else r["detail"].get("reply", "")[:120].replace("!@#", " ")
        if r["detail"].get("notes"):
            what += " [" + "; ".join(r["detail"]["notes"]) + "]"
        verdict = "yes" if r["passed"] else ("cut" if r["detail"].get("cut") else "NO")
        md.append("| %s | %s | %s | %s | %s |" % (r["id"], verdict, r.get("operator", "").replace("|", "/"),
                                               r["say"].replace("|", "/"), what.replace("|", "/")))
    open(os.path.join(scratch, "results.md"), "w").write("\n".join(md) + "\n")
    open(os.path.join(scratch, "results.json"), "w").write(json.dumps(results, indent=1))
    print("\n".join(md))


if __name__ == "__main__":
    sys.exit(main())

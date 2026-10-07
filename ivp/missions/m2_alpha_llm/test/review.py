#!/usr/bin/env python3
"""review.py ALOG [--only SECTIONS] [--chat-width N]: a live run's record,
from the shoreside alog, as the tables the review-run skill asks for.
Sections, in order (--only takes a comma list of their names):
  header    the run, its warp and span
  chat      the chat in order, tool calls as one line each (bodies left
            out), proposal step lines with arithmetic trimmed
  usage     one line per request: tokens, cost, latency, and a flag when
            the history was rewritten into the cache (a cache read below
            the previous request's total) or the request was a cold start
  plans     plan state changes per slot, plan names, team events, button
            presses and definitions
  says      Say lines from plans, collisions and near misses
  problems  steps that could not start, waits for first values, rejected
            trees and conditions, cut-off and error replies
  drawings  every shape the executors and the agent drew, by variable and
            label: first drawn, erased, or STILL ON THE MAP when the log
            ended (a plan's drawings should all be erased by its end)
  holds     per plan load: the time from load to running and to the first
            event after it (the first-tick wait; the alog thins events, so
            the vehicle's own log is the final word)
Times are the alog's, warped seconds since the log opened; divide by the
warp for real seconds. pLogger's repeats of early posts are dropped."""
import sys, re, os, glob
from collections import OrderedDict, defaultdict

PRICES = {"in": 4.0, "out": 20.0, "cache_read": 0.20, "cache_create": 5.0}   # $/MTok, claude-opus-5-5

if len(sys.argv) < 2 or sys.argv[1].startswith("-"):
    sys.exit(__doc__)
alog = sys.argv[1]
only = None
chat_width = 300
args = sys.argv[2:]
for i, a in enumerate(args):
    if a == "--only":
        only = set(args[i + 1].split(","))
    elif a == "--chat-width":
        chat_width = int(args[i + 1])

def want(name):
    return only is None or name in only

rx = re.compile(r'^(\S+)\s+(\S+)\s+(\S+)\s+(.*)$')
rows = []
seen = set()
with open(alog, errors="replace") as f:
    for line in f:
        if not line[0].isdigit():
            continue
        m = rx.match(line.rstrip("\n"))
        if not m:
            continue
        t, var, src, val = float(m.group(1)), m.group(2), m.group(3), m.group(4).rstrip()
        key = (m.group(1), var, val)
        if key in seen:
            continue
        seen.add(key)
        app = src.split(":")[0]
        aux = src[len(app) + 1:] if ":" in src else ""
        rows.append((t, var, app, aux, val))

span = rows[-1][0] if rows else 0.0
warp = 1.0
for mf in glob.glob(os.path.join(os.path.dirname(os.path.abspath(alog)), "*._moos")):
    for line in open(mf, errors="replace"):
        if line.startswith("MOOSTimeWarp"):
            try:
                warp = float(line.split("=")[1])
            except ValueError:
                pass

def nl(s):
    return s.replace("!@#", "\n      ")

def trim_expr_lines(text, width):
    out = []
    for ln in text.split("\n"):
        if "$(" in ln and len(ln) > 160:
            ln = ln[:160] + " ..."
        elif len(ln) > width:
            ln = ln[:width] + " ..."
        out.append(ln)
    return "\n".join(out)

def section(title):
    print("\n== " + title + " ==")

# ---------------- header
if want("header"):
    section("run")
    print(f"{alog}\nwarp {warp:g}, {span:.0f} warped s ({span / warp:.0f} real s), {len(rows)} distinct posts")

# ---------------- chat
if want("chat"):
    section("chat (tool calls as one line, bodies left out)")
    for t, var, app, aux, val in rows:
        if var in ("LLM_CHAT_IN", "LLM_CHAT_OUT", "LLM_MODE", "LLM_CHAT_NOTE"):
            tag = {"LLM_CHAT_IN": "IN ", "LLM_CHAT_OUT": "OUT", "LLM_MODE": "MODE", "LLM_CHAT_NOTE": "NOTE"}[var]
            who = (":" + aux) if (var == "LLM_CHAT_OUT" and aux) else ""
            print(f"{t:9.1f} {tag}{who} {trim_expr_lines(nl(val), chat_width)}")
        elif var == "LLM_TOOL_CALL":
            print(f"{t:9.1f} TOOL {val[:160]}{' ...' if len(val) > 160 else ''}")

# ---------------- usage
if want("usage"):
    section("requests (cost at claude-opus-5-5 prices unless LLM_COST says otherwise)")
    costs = {}
    for t, var, app, aux, val in rows:
        if var == "LLM_COST":
            m = re.search(r'request=([0-9.]+)', val)
            if m:
                costs[round(t, 1)] = float(m.group(1))
    prev_total = None
    n = 0
    tot_out = tot_cost = 0.0
    print("     t      in    out  cache_read cache_create  latency     $   note")
    for t, var, app, aux, val in rows:
        if var != "LLM_USAGE":
            continue
        u = dict(re.findall(r'(\w+)=([0-9.]+)', val))
        i_, o, cr, cc = (int(float(u.get(k, 0))) for k in ("in", "out", "cache_read", "cache_create"))
        lat = float(u.get("latency", 0))
        cost = costs.get(round(t, 1))
        if cost is None:
            cost = (i_ * PRICES["in"] + o * PRICES["out"] + cr * PRICES["cache_read"] + cc * PRICES["cache_create"]) / 1e6
        note = ""
        if cr == 0:
            note = "cold start"
        elif prev_total is not None and cr < prev_total - 50:
            note = f"history rewritten (read {cr} < previous total {prev_total})"
        if o >= 16000:
            note = (note + "; " if note else "") + "cut off at the token cap?"
        tries = re.search(r'tries=(\S+)', val)
        if int(float(u.get("attempts", 1))) > 1:
            note = (note + "; " if note else "") + "retried: " + (tries.group(1) if tries else u.get("attempts"))
        print(f"{t:9.1f} {i_:6d} {o:6d} {cr:11d} {cc:12d} {lat:7.1f}s {cost:6.3f}  {note}")
        prev_total = cr + cc
        n += 1
        tot_out += o
        tot_cost += cost
    print(f"{n} requests, {tot_out:.0f} output tokens, ${tot_cost:.2f}" if n else "none")

# ---------------- plans
if want("plans"):
    section("plans: state changes, names, teams, buttons")
    last = {}
    for t, var, app, aux, val in rows:
        if re.match(r'BT_STATE_[A-Z0-9_]+$', var):
            if last.get(var) != val:
                last[var] = val
                print(f"{t:9.1f} {var[9:].lower():>8} {val}")
        elif re.match(r'BT_PLAN_[A-Z0-9_]+$', var) and val != "none":
            print(f"{t:9.1f} {var[8:].lower():>8} plan {val}")
        elif var == "TEAM_EVENT":
            print(f"{t:9.1f}     team {val[:120]}")
        elif var in ("BUTTON_PRESS", "LLM_BUTTON_DEF"):
            label = val
            if var == "BUTTON_PRESS" and "button=" in aux:
                # the panel's source aux is button=<label>; in logs before
                # 2026-10-06 a label with a space split the line oddly (the
                # aux now writes the spaces as underscores): the label is the
                # aux's, repeated
                full = (aux + " " + val).split("button=", 1)[1]
                half = len(full) // 2
                if full[:half] == full[half + 1:]:
                    label = full[:half]
            print(f"{t:9.1f}   {'press' if var == 'BUTTON_PRESS' else 'button def':>8} {label}")

# ---------------- says
if want("says"):
    section("plan Say lines, collisions, near misses")
    any_ = False
    for t, var, app, aux, val in rows:
        if re.match(r'BT_CHAT_[A-Z0-9_]+$', var):
            print(f"{t:9.1f} {var[8:].lower():>8} says: {nl(val)[:200]}"); any_ = True
        elif var in ("COLLISION", "NEAR_MISS"):
            print(f"{t:9.1f} {var}: {val}"); any_ = True
        elif var in ("COLLISION_TOTAL", "NEAR_MISS_TOTAL") and float(val) > 0:
            print(f"{t:9.1f} {var} = {float(val):g}"); any_ = True
    if not any_:
        print("none")

# ---------------- problems
if want("problems"):
    section("problems")
    any_ = False
    for t, var, app, aux, val in rows:
        hit = None
        if var.startswith("BT_EVENT") and re.search(r'cannot start|waiting for the first values|no value arrived|rejected|stale .* ignored', val):
            hit = val
        elif var == "APP_LOG" and "Bad Condition" in val:
            hit = "Bad Condition Syntax: " + val.split("Bad Condition Syntax:", 1)[1].split("!@#")[0].strip()
        elif var == "LLM_CHAT_OUT" and val.startswith("[") and re.search(r'error|rejected|cut off|was used up|not in ', val):
            hit = nl(val)[:220]   # the console's own bracketed notes, not a reply that quotes the words
        elif var.startswith("BT_STATE") and val.startswith("error="):
            hit = val
        if hit:
            print(f"{t:9.1f} {var}: {hit[:220]}"); any_ = True
    if not any_:
        print("none")

# ---------------- drawings
if want("drawings"):
    section("drawings by the executors and the agent (var label: drawn .. erased | STILL ON THE MAP)")
    shapes = OrderedDict()   # (app, var, label) -> [first, last_drawn, erased_t]
    for t, var, app, aux, val in rows:
        if not var.startswith("VIEW_") or app not in ("pBehaviorTree", "pLLMAgent"):
            continue
        m = re.search(r'(?:^|,)label=([^,]*)', val)
        if not m:
            continue
        label = m.group(1).strip()
        k = (app, var, label)
        if "active=false" in val.replace(" ", ""):
            if k in shapes:
                shapes[k][2] = t
            else:
                shapes[k] = [None, None, t]
        else:
            if k not in shapes or shapes[k][2] is not None:
                shapes[k] = [t, t, None]
            else:
                shapes[k][1] = t
    if not shapes:
        print("none")
    remaining = 0
    for (app, var, label), (first, lastd, erased) in shapes.items():
        if first is None:
            state = f"erase only at {erased:.1f}"
        elif erased is None:
            state = f"drawn {first:.1f}..{lastd:.1f}  STILL ON THE MAP at the end"
            remaining += 1
        else:
            state = f"drawn {first:.1f}..{lastd:.1f}  erased {erased:.1f}"
        print(f"  {app:12} {var:13} {label:34} {state}")
    if shapes:
        print(f"{remaining} still on the map when the log ended" if remaining else "every drawing was erased")

# ---------------- holds
if want("holds"):
    section("plan loads: load -> running -> first event (the first-tick wait; events are thinned, the vehicle log is final)")
    loads = []   # (t, slot)
    for t, var, app, aux, val in rows:
        m = re.match(r'BT_TREE(?:_FILE)?_([A-Z0-9_]+)$', var)
        if m and app != "pBehaviorTree":
            loads.append((t, m.group(1)))
    any_ = False
    for n, (lt, slot) in enumerate(loads):
        # this load's run must come before the slot's next load
        next_t = min([t2 for t2, s2 in loads[n + 1:] if s2 == slot] or [float("inf")])
        run_t = ev_t = None
        for t, var, app, aux, val in rows:
            if t < lt:
                continue
            if t >= next_t:
                break
            if run_t is None and var == "BT_STATE_" + slot and val == "running":
                run_t = t
            elif run_t is not None and var == "BT_EVENT_" + slot and t >= run_t:
                ev_t = t
                break
            elif run_t is not None and var == "BT_STATE_" + slot and val != "running" and t > run_t:
                break
        has_events = any(var == "BT_EVENT_" + slot for _, var, _, _, _ in rows)
        if run_t is None:
            print(f"{lt:9.1f} {slot.lower():>8} loaded, never ran")
        elif not has_events:
            print(f"{lt:9.1f} {slot.lower():>8} running +{run_t - lt:.2f} s; its events are not in this log (a boat's stay on its own LOG_{slot}_*; fleet.sh dump reads them)")
        else:
            hold = f"first event +{ev_t - run_t:.2f} s" if ev_t is not None else "no event seen after running"
            print(f"{lt:9.1f} {slot.lower():>8} running +{run_t - lt:.2f} s, {hold}")
        any_ = True
    if not any_:
        print("none")

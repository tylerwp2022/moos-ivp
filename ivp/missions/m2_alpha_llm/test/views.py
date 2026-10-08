#!/usr/bin/env python3
"""views.py ALOG [--turn N] [--id N] [--events K]: what a run put on the
map, from a shoreside alog. Per proposal turn: the shapes pLLMAgent drew,
grouped by owner, with their colors, their waypoint numbers and when they
were erased. Per preview request: the plans (owner, color, roster), each
play's length, the events of the first play, every bubble text with its
time on screen, where the ghosts rested, and a ghost that never stopped.
The alog thins bursts of one variable, so the erase posts (active=false)
and PLAN_PREVIEW_STATE are read as the record; draw posts only add
colors. Times are the alog's, warped seconds since the log opened."""
import sys, re
from collections import OrderedDict, defaultdict

if len(sys.argv) < 2:
    sys.exit(__doc__)
alog = sys.argv[1]
want_turn = want_id = None
events_k = 12
args = sys.argv[2:]
for i, a in enumerate(args):
    if a == "--turn":
        want_turn = args[i + 1]
    elif a == "--id":
        want_id = args[i + 1]
    elif a == "--events":
        events_k = int(args[i + 1])

rx = re.compile(r'^(\S+)\s+(\S+)\s+(\S+)\s+(.*)$')
spec_rx = re.compile(r'(\w+)=("[^"]*"|[^,]*)')


def fields(spec):
    return OrderedDict((k, v.strip('"')) for k, v in spec_rx.findall(spec))


draw = defaultdict(list)       # turn -> [(t, var, fields)]
cur_turn = "?"                 # erase posts carry no turn: they belong to the last drawn
requests = []                  # (t, turn, id, [plan dicts]) or (t, turn, id, 'none')
last_req = ("?", "?")          # a withdrawal names no turn: it ends the last request
pev = []                       # (t, text)
pstate = []                    # (t, id, play, tsim, {owner: (state, x, y)})
bubbles = []                   # (t, owner, text)
with open(alog, errors="replace") as f:
    for line in f:
        if not line[0].isdigit():
            continue
        m = rx.match(line.rstrip("\n"))
        if not m:
            continue
        t, var, src, val = float(m.group(1)), m.group(2), m.group(3), m.group(4)
        app = src.split(":")[0]
        aux = src[len(app) + 1:] if ":" in src else ""
        if var.startswith("VIEW_") and app == "pLLMAgent":
            tm = re.search(r'turn=(\d+)', aux)
            if tm:
                cur_turn = tm.group(1)
            draw[cur_turn].append((t, var, fields(val)))
        elif var == "PLAN_PREVIEW" and app == "pLLMAgent":
            tm = re.search(r'turn=(\d+)', aux)
            turn = tm.group(1) if tm else "?"
            if val.strip().lower() in ("none", "off", ""):
                requests.append((t, last_req[0], last_req[1], "none"))
            else:
                idm = re.search(r'<preview id="([^"]*)"', val)
                plans = []
                for pm in re.finditer(r'<plan ([^>]*)>', val):
                    at = dict(re.findall(r'(\w+)="([^"]*)"', pm.group(1)))
                    plans.append(at)
                last_req = (turn, idm.group(1) if idm else "?")
                requests.append((t, turn, last_req[1], plans))
        elif var == "PLAN_PREVIEW_EVENT":
            pev.append((t, val.strip()))
        elif var == "PLAN_PREVIEW_STATE":
            hm = re.match(r'id=([^,]*),play=(\d+),t=(\S+)\s*(.*)$', val.strip())
            if hm:
                ghosts = {}
                for g in hm.group(4).split():
                    gm = re.match(r'(\w+):(\w+)(?:@(-?[\d.]+),(-?[\d.]+))?', g)
                    if gm:
                        ghosts[gm.group(1)] = (gm.group(2), gm.group(3), gm.group(4))
                pstate.append((t, hm.group(1), int(hm.group(2)), float(hm.group(3)), ghosts))
        elif var == "VIEW_TEXTBOX" and app == "uPlanPreview":
            fm = fields(val)
            lab = fm.get("label", "")
            if lab.endswith("_t") and "active" not in fm:
                owner = lab[len("preview_"):-2] if lab.startswith("preview_") else lab
                bubbles.append((t, owner, fm.get("msg", "")))


def call_index(label):
    # llm_<tool>_<i>_<k>[_n<j>]: the call's place in the proposal
    parts = label.split("_")
    return parts[2] if (len(parts) > 2 and "#" not in label) else None


def owner_of(label, msg, call_owner):
    # llm_<owner>_<i>_<Type>#<id>_<k>[_n<j>]  or  llm_<tool>_<i>_<k>[_n<j>]
    parts = label.split("_")
    if "#" in label and len(parts) >= 4:
        return parts[1]
    i = call_index(label)
    if i in call_owner:
        return call_owner[i]
    return "call " + (i or "?")


print("== proposal drawings (pLLMAgent) ==")
for turn in sorted(draw, key=lambda s: int(s) if s.isdigit() else 0):
    if want_turn and turn != want_turn:
        continue
    posts = draw[turn]
    erase = [(t, v, fm) for t, v, fm in posts if fm.get("active") == "false"]
    drawn = [(t, v, fm) for t, v, fm in posts if fm.get("active") != "false"]
    record = erase if erase else drawn
    # One entry per label: a proposal redrawn (an alert turn, a second
    # look) posts every shape again
    last = OrderedDict()
    for t, v, fm in record:
        last[fm.get("label", "")] = (t, v, fm)
    record = list(last.values())
    # A tool call's owner shows only in its numbers' tags ("abe 1")
    call_owner = {}
    for t, v, fm in record:
        lab = fm.get("label", "")
        msg = fm.get("msg", "")
        i = call_index(lab)
        if v == "VIEW_TEXTBOX" and i and " " in msg and not msg.split(" ")[0].isdigit():
            call_owner[i] = msg.split(" ")[0]
    by_owner = OrderedDict()
    for t, v, fm in record:
        lab = fm.get("label", "")
        msg = fm.get("msg", "")
        o = owner_of(lab, msg, call_owner)
        e = by_owner.setdefault(o, {"colors": set(), "shapes": defaultdict(int), "nums": [], "erased": None})
        color = fm.get("vertex_color") or fm.get("edge_color") or fm.get("mcolor") or "?"
        e["colors"].add(color)
        if v == "VIEW_TEXTBOX":
            e["nums"].append(msg)
        else:
            e["shapes"][v.replace("VIEW_", "").lower()] += 1
        if fm.get("active") == "false":
            e["erased"] = t
    t0 = min(t for t, _, _ in posts)
    print("turn %s: drawn at %.1f, %d owner(s)%s" % (turn, t0, len(by_owner),
          "" if erase else " (no erase posts in the log, draw posts only)"))
    for o, e in by_owner.items():
        shapes = ", ".join("%d %s" % (n, k) for k, n in e["shapes"].items()) or "no shapes"
        nums = " ".join(e["nums"]) if e["nums"] else "no numbers"
        print("  %-8s %-12s %-28s numbers: %s%s" % (o, "/".join(sorted(e["colors"])), shapes, nums,
              ("  erased at %.1f" % e["erased"]) if e["erased"] else ""))
if not draw:
    print("  none")

print("\n== preview requests (pLLMAgent -> uPlanPreview) ==")
# The alog repeats some lines verbatim; one entry per posting
seen = set()
requests = [r for r in requests if not ((r[0], r[2], str(r[3])) in seen or seen.add((r[0], r[2], str(r[3]))))]
for t, turn, rid, plans in requests:
    if want_turn and turn != want_turn:
        continue
    if want_id and rid != want_id:
        continue
    if plans == "none":
        print("%.1f turn %s: request id=%s withdrawn" % (t, turn, rid))
        continue
    print("%.1f turn %s: request id=%s, %d plan(s)" % (t, turn, rid, len(plans)))
    for p in plans:
        print("  %-8s color %-12s%s" % (p.get("owner", "?"), p.get("color", "?"),
              (" members " + p["members"]) if "members" in p else ""))
if not requests:
    print("  none")

print("\n== preview playback (uPlanPreview) ==")
by_id = OrderedDict()
for t, rid, play, tsim, ghosts in pstate:
    by_id.setdefault(rid, OrderedDict()).setdefault(play, []).append((t, tsim, ghosts))
for rid, plays in by_id.items():
    if want_id and rid != want_id:
        continue
    first = plays[min(plays)]
    last_t = max(t for t, _, _ in [s for p in plays.values() for s in p])
    first_t = first[0][0]
    print("request id=%s: %d play(s), %.1f to %.1f" % (rid, len(plays), first_t, last_t))
    for play, states in plays.items():
        tsim_end = states[-1][1]
        print("  play %d: %.1f plan s%s" % (play, tsim_end, "" if play > 1 else ", first play:"))
        if play == 1:
            ev = [(t, s) for t, s in pev if first_t - 1 <= t <= states[-1][0] + 1]
            for t, s in ev[:events_k]:
                print("      %s" % s)
            if len(ev) > events_k:
                print("      ... %d more" % (len(ev) - events_k))
    final = plays[max(plays)][-1][2]
    for o, (st, x, y) in final.items():
        where = ("at %s,%s" % (x, y)) if x is not None else "(squad)"
        flag = ""
        if st == "running":
            flag = "   <-- never finished"
        print("  %-8s %-8s %s%s" % (o, st, where, flag))
    # bubbles seen during this request
    tb = [(t, o, m) for t, o, m in bubbles if first_t - 1 <= t <= last_t + 1]
    runs = OrderedDict()
    cur = {}
    for t, o, m in tb:
        if o in cur and cur[o][0] == m and t - cur[o][2] < 2:
            cur[o] = (m, cur[o][1], t)
        else:
            if o in cur:
                runs.setdefault((o, cur[o][0]), []).append(cur[o][2] - cur[o][1])
            cur[o] = (m, t, t)
    for o, (m, a, b) in cur.items():
        runs.setdefault((o, m), []).append(b - a)
    for (o, m), ds in runs.items():
        if ":" not in m:
            continue
        print("  bubble %-40s %d time(s), %.1f s on screen each (log time)" % (m[:40], len(ds), sum(ds) / len(ds)))
if not pstate:
    print("  none")

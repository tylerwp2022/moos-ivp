#!/usr/bin/env python3
"""pairs.py ALOG T0 T1 [STEP]: every boat's position from the NODE_REPORT
lines of a shoreside alog (filtered on NAME=, never on the key), sampled
every STEP warped seconds between T0 and T1, with the range of every
pair, and the closest sampled approach per pair at the end."""
import sys, re, math

alog = sys.argv[1]
lo = float(sys.argv[2])
hi = float(sys.argv[3])
step = float(sys.argv[4]) if len(sys.argv) > 4 else 5.0
pos = {}
rx = re.compile(r'^(\S+)\s+NODE_REPORT\S*\s+(\S+)\s+(.*)$')
with open(alog, errors="replace") as f:
    for line in f:
        if not line[0].isdigit():
            continue
        m = rx.match(line)
        if not m:
            continue
        t = float(m.group(1))
        if t < lo or t > hi:
            continue
        fm = dict(kv.split('=', 1) for kv in m.group(3).split(',') if '=' in kv)
        try:
            v = fm['NAME'].lower()
            x = float(fm['X']); y = float(fm['Y'])
            s = float(fm.get('SPD', '0')); h = float(fm.get('HDG', '0'))
        except (KeyError, ValueError):
            continue
        pos.setdefault(v, []).append((t, x, y, s, h))
names = sorted(pos)


def at(v, t):
    best = None
    for r in pos[v]:
        if best is None or abs(r[0] - t) < abs(best[0] - t):
            best = r
    return best


mins = {}
t = lo
while t <= hi:
    row = []
    for v in names:
        r = at(v, t)
        if r and abs(r[0] - t) < 3:
            row.append((v, r))
    line = "%8.1f " % t + "  ".join("%s=(%.0f,%.0f) s%.1f h%.0f" % (v, r[1], r[2], r[3], r[4]) for v, r in row)
    for i in range(len(row)):
        for j in range(i + 1, len(row)):
            a, b = row[i][1], row[j][1]
            d = math.hypot(a[1] - b[1], a[2] - b[2])
            k = row[i][0] + '-' + row[j][0]
            line += "  %s:%.0f" % (k, d)
            if k not in mins or d < mins[k][0]:
                mins[k] = (d, t)
    print(line)
    t += step
print("closest (sampled):", {k: (round(d, 1), t) for k, (d, t) in mins.items()})

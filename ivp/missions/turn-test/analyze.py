#!/usr/bin/env python3
"""
Analyze a turn-test .alog: build a per-trial metrics table and the
speed-vs-footprint tradeoff plot.

Usage:
  ./analyze.py [path/to/file.alog | path/to/LOG_dir]
  (no arg -> newest LOG_*/*.alog under the current directory)

Outputs (written next to the .alog):
  turn_metrics.csv        one row per completed maneuver
  turn_tradeoff.png       footprint vs time-to-heading, colored by strategy
  turn_paths.png          per-trial XY tracks (if NAV data present)

Metrics come straight from pTurnInPlace's TURN_RESULT posts; XY tracks
are reconstructed from NAV_X/NAV_Y within each trial's time window.
"""
import os, sys, glob, csv

def find_alog(arg):
    if arg:
        if os.path.isdir(arg):
            hits = glob.glob(os.path.join(arg, "*.alog"))
            if not hits:
                sys.exit("No .alog in %s" % arg)
            return hits[0]
        return arg
    dirs = glob.glob("LOG_*") + glob.glob("MOOSLog_*")
    dirs = sorted(dirs, key=os.path.getmtime)
    for d in reversed(dirs):
        hits = glob.glob(os.path.join(d, "*.alog"))
        if hits:
            return hits[0]
    sys.exit("No LOG_*/MOOSLog_*/*.alog found; pass an .alog path explicitly.")

def parse_alog(path):
    """Return (results, nav) where results is a list of dicts and nav is
    a list of (time, x, y) triples."""
    results = []
    nav_x, nav_y = {}, {}      # time -> value
    with open(path, errors="replace") as f:
        for line in f:
            if not line or line[0] == "%":
                continue
            parts = line.split(None, 3)
            if len(parts) < 4:
                continue
            t, var, _src, val = parts
            try:
                t = float(t)
            except ValueError:
                continue
            val = val.strip()
            if var == "TURN_RESULT":
                d = {"time": t}
                for kv in val.split(","):
                    if "=" in kv:
                        k, v = kv.split("=", 1)
                        d[k] = v
                results.append(d)
            elif var == "NAV_X":
                nav_x[round(t, 2)] = float(val)
            elif var == "NAV_Y":
                nav_y[round(t, 2)] = float(val)
    nav = []
    for t in sorted(set(nav_x) & set(nav_y)):
        nav.append((t, nav_x[t], nav_y[t]))
    return results, nav

NUM = ("delta", "t_elapsed", "max_excursion", "bbox_diag",
       "final_pos_err", "final_hdg_err")

def to_num(results):
    for r in results:
        for k in NUM:
            if k in r:
                try:
                    r[k] = float(r[k])
                except ValueError:
                    pass
    return results

def write_csv(results, out):
    cols = ["id", "strategy", "delta", "t_elapsed", "max_excursion",
            "bbox_diag", "final_pos_err", "final_hdg_err", "timed_out"]
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in results:
            w.writerow(r)
    print("wrote", out)

def print_table(results):
    hdr = ["id", "strategy", "delta", "t_elapsed", "max_exc", "bbox",
           "pos_err", "hdg_err", "timeout"]
    print("\n%-16s %-8s %6s %9s %8s %7s %8s %8s %8s" % tuple(hdr))
    print("-" * 92)
    for r in results:
        print("%-16s %-8s %6.0f %9.2f %8.2f %7.2f %8.2f %8.2f %8s" % (
            r.get("id", "?"), r.get("strategy", "?"),
            r.get("delta", 0), r.get("t_elapsed", 0),
            r.get("max_excursion", 0), r.get("bbox_diag", 0),
            r.get("final_pos_err", 0), r.get("final_hdg_err", 0),
            r.get("timed_out", "?")))
    print()

STRAT_COLOR = {"circle": "tab:blue", "kturn": "tab:orange",
               "shuffle": "tab:green"}

def plot_tradeoff(results, out):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        print("matplotlib unavailable (%s); skipping plots." % e)
        return
    fig, ax = plt.subplots(figsize=(7, 5))
    seen = set()
    for r in results:
        s = r.get("strategy", "?")
        c = STRAT_COLOR.get(s, "gray")
        lbl = s if s not in seen else None
        seen.add(s)
        # marker size encodes commanded heading delta
        size = 30 + 1.2 * r.get("delta", 0)
        ax.scatter(r.get("t_elapsed", 0), r.get("max_excursion", 0),
                   s=size, c=c, alpha=0.75, edgecolors="k",
                   linewidths=0.5, label=lbl)
        ax.annotate("%.0f" % r.get("delta", 0),
                    (r.get("t_elapsed", 0), r.get("max_excursion", 0)),
                    fontsize=7, xytext=(4, 3), textcoords="offset points")
    ax.set_xlabel("time to heading (s)")
    ax.set_ylabel("max excursion from station (m)")
    ax.set_title("Turn modality tradeoff: speed vs footprint\n"
                 "(marker size = commanded heading delta)")
    ax.grid(True, alpha=0.3)
    ax.legend(title="strategy")
    fig.tight_layout()
    fig.savefig(out, dpi=130)
    print("wrote", out)

def plot_paths(results, nav, out):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return
    if not nav:
        return
    fig, ax = plt.subplots(figsize=(7, 7))
    for r in results:
        t_end = r["time"]
        t_start = t_end - r.get("t_elapsed", 0)
        seg = [(x, y) for (t, x, y) in nav if t_start <= t <= t_end]
        if len(seg) < 2:
            continue
        xs, ys = zip(*seg)
        c = STRAT_COLOR.get(r.get("strategy", "?"), "gray")
        ax.plot(xs, ys, "-", color=c, alpha=0.6, linewidth=1)
        ax.plot(xs[0], ys[0], "o", color=c, ms=4)
    ax.set_aspect("equal", "datalim")
    ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
    ax.set_title("Per-trial XY tracks (o = start)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=130)
    print("wrote", out)

def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    alog = find_alog(arg)
    print("reading", alog)
    results, nav = parse_alog(alog)
    if not results:
        sys.exit("No TURN_RESULT rows found in the .alog.")
    results = to_num(results)
    # Dedupe by trial id (pLogger can double-log a value); keep last.
    byid = {}
    for r in results:
        byid[r.get("id", r["time"])] = r
    results = sorted(byid.values(), key=lambda r: r["time"])
    outdir = os.path.dirname(os.path.abspath(alog))
    print_table(results)
    write_csv(results, os.path.join(outdir, "turn_metrics.csv"))
    plot_tradeoff(results, os.path.join(outdir, "turn_tradeoff.png"))
    plot_paths(results, nav, os.path.join(outdir, "turn_paths.png"))

if __name__ == "__main__":
    main()

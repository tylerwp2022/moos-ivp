---
name: headless-fleet
description: Launch a scratch copy of m2_alpha_llm (or s1_alpha_llm) without the viewer on the 9100 ports, drive it with uPokeDB and uQueryDB, read the logs, and shut it down cleanly. Use to verify any executor, capability, squad or avoidance change before the user launches live, and for collision or formation experiments.
---

# Headless scratch fleet

Verify on a scratch copy, never in the real mission directory: a launch
there leaves LOG dirs and targ files behind and can collide with a
mission the user has up on 9000.

## Launch

`ivp/missions/m2_alpha_llm/test/fleet.sh` does the whole thing:

```
S=/tmp/claude-1001/.../scratchpad/fleet            # the session scratchpad, or test/runs/<stamp>
ivp/missions/m2_alpha_llm/test/fleet.sh up ivp/missions/m2_alpha_llm $S 2 10   # mission, scratch, boats, warp
ivp/missions/m2_alpha_llm/test/fleet.sh alog $S      # the shoreside alog path, once pLogger is up
ivp/missions/m2_alpha_llm/test/fleet.sh down $S      # kill everything whose cwd is $S
```

`up` copies the meta files, plugs, bhv, launch scripts, plans/, prompts/,
dyn/ and buttons.txt (pLLMAgent writes to the copy, never the mission's),
writes the calling script's PID to `<scratch>/.driver` (the Stop hook
lets a fleet pass while that script runs; a background test script
therefore never trips it, a leftover does), then launches abe (9101/9301), ben (9102/9302), cal, deb and
the shoreside (9100/9300, `--nogui`, `--auto`) with the API key removed
from the environment (`--key` keeps it; pLLMAgent then calls the model).
Ports 9000/9200 stay free for the user. Launch can take up to 150 s
real before every helm reports; wait, do not relaunch. Three more
commands cover the chores between `up` and the test:

```
ivp/missions/m2_alpha_llm/test/fleet.sh ready $S            # waits for every helm, the node reports and facts on the shoreside, the agent idle; names what held it up on a timeout
ivp/missions/m2_alpha_llm/test/fleet.sh run $S uPlanPreview "capability_dir = helm" "rate = 10"   # an app outside pAntler: writes uPlanPreview_side.moos with the port, warp and datum, logs to uPlanPreview.out
ivp/missions/m2_alpha_llm/test/fleet.sh chat $S "go to 40,-60" n   # pokes the line, waits, prints the reply or proposal, answers n (y, or - to leave it pending)
```

Use `ready` instead of a grep on the log (a grep on node reports fires
before the helms are up); `run` instead of a hand-written side file (a
missing MOOSTimeWarp makes the app's log timestamps garbage); `chat` for
a one-line check, the chat-test driver for a scripted run.

A plan under test is three lines, not a script:

```
ivp/missions/m2_alpha_llm/test/fleet.sh plan $S /path/to/plan.xml abe        # copies it into $S/plans/, checks it, pokes it, waits for success/failure/halted, exit 0 on success
ivp/missions/m2_alpha_llm/test/fleet.sh squad $S pair abe:ben                  # a squad and its plan slot, for a squad plan
ivp/missions/m2_alpha_llm/test/fleet.sh plan $S /path/to/squad_plan.xml pair
ivp/missions/m2_alpha_llm/test/fleet.sh dump $S                                # review.py's plan tables on the run so far: states, Say lines, problems, drawings (STILL ON THE MAP), first-step waits
ivp/missions/m2_alpha_llm/test/fleet.sh dump $S usage,chat                     # or any of review.py's sections
```

`plan` reports "never ran" when the owner is not a boat or an existing
squad, and a plan that `pBehaviorTree --check` rejects before poking it.
`dump` reads the shoreside alog; a vehicle's own log (`$S/LOG_<V>_*`)
is still the final word on timing, since the alog thins event bursts.

Rules that cost time when broken:
- One launch per subshell with its own `cd`: a backgrounded `cd X && a &`
  followed by `b &` runs `b` in the ORIGINAL directory, inside the real
  mission. `fleet.sh` does this right; if you hand-write it, use
  `(cd $S && cmd &)` per app.
- Never `cd` in a harness Bash command; put the cd inside a script.
- Long waits go in a background script (`run_in_background`); a
  foreground `sleep` is blocked.
- Kill by working directory (`/proc/<pid>/cwd == $S`), never
  `pkill -f <script>`: that matches the running harness command itself.
  TERM, then KILL for pAntler and pLogger. Check `ss -ltn | grep 910`.

## Drive it

```
uPokeDB $S/targ_shoreside.moos 'VAR:=string value' NUM=3.5     # := forces a string; commas inside a value are fine
timeout 200 uQueryDB $S/targ_shoreside.moos --condition="BT_STATE_ABE = success" --wait=1500
```

Always pass the mission file to uQueryDB (`--port` alone hangs on port
0). `--wait` counts WARPED seconds: at warp 10 use ten times the real
seconds. `--condition` matches the CURRENT value, so a stale
`goto_complete` satisfies the next wait at once: reset the variable
first, wait on a transition (`= running` then `= success`), or judge
from alog timestamps. Conditions take `and`, `or`, `!=` and values
with `#`, but a value cannot itself contain `=` (wait on a marker
variable instead). `MulticastNode ... bind failed` lines are noise.

Plans: `uPokeDB ... BT_TREE_FILE_ABE=plans/foo.xml` (the vehicle loads
the file relative to $S). Squads: `SQUAD_CMD:=action=create,name=red,members=abe:ben`,
then `action=formation,name=red,shape=line,spacing=25`, `action=goto,...`.
A direct poke that moves a boat needs `MOOS_MANUAL_OVERRIDE_<V>=false`
and `DEPLOY_<V>=true` unless a capability post carries them. Alerts to
the agent: `LLM_ALERTS:=on`. Appcast on demand:
`APPCAST_REQ:=node=abe,app=pHelmIvP,duration=6,key=dbg,thresh=any` on
that boat's own DB (`targ_abe.moos`), then grep its alog for `APPCAST`.

## Read the result

Use the review-run skill's greps on `$S/XLOG_SHORESIDE_*/*.alog` and
`$S/LOG_<V>_*/*.alog`: BT_STATE/BT_EVENT for plans, SQUAD_EVENT and
SQUAD_REPORT for squads, COLLISION/NEAR_MISS with CPA, `pairs.py` for
ranges, IVPHELM_LIFE_EVENT for spawned avoidance instances,
DESIRED_ vs NAV_ for commanded vs actual. Correlate boat and shore
logs through a marker you poke (`FORM_MARK:=start`).

Facts that trip expectations: a goto ends within capture_radius 5 m or
on the capture line up to slip_radius 15 m short, so a goto under 15 m
does not move the boat; the simulated boat coasts about 10 m after a
stop command at 2 m/s; basic avoidance against a STATIONARY target dead
ahead dithers and parks 7 to 12 m off; station keeping needs a radius
wider than the turning circle (10 m, transit 1.2). The .bhv is read at
helm start, so restart the boats (not the shoreside) after editing it;
a block error is `IVPHELM_STATE = MALCONFIG`, reason in the helm appcast.

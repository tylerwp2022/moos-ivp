---
name: headless-mctf
description: Launch a scratch copy of the mctf_llm capture-the-flag match (moos-ivp-mctf) without the viewer on the 9100 ports, deploy, press buttons and plays, send intruders, run plans, drive the agent through a stand-in API, read the run back as tables, and shut it down. Use to verify any play, plan, capability, referee-fact or field change before the owner launches the match live, and to reproduce a live run's event headless.
---

# Headless mctf fleet

Verify on a scratch copy, never in `~/moos-ivp-mctf/missions/mctf_llm`
itself: a launch there leaves logs and targ files behind and collides
with the owner's match on 9000. `missions/mctf_llm/test/fleet.sh` does
the whole thing; its README lists every command and the gotchas.

```
F=/home/tyler/moos-ivp-mctf/missions/mctf_llm/test/fleet.sh
S=/tmp/claude-1001/.../scratchpad/mctf          # the session scratchpad, or test/runs/<stamp>
$F up $S 5 [--red_idle --blue_idle --llm=red --brake ...]   # the copy, ports +100, warp 5; launch_sim.sh options pass through
$F ready $S                  # helms, each boat linked both ways, facts, agent idle (names what held it up)
$F deploy $S all             # or red | blue | a,b,c: NOTHING MOVES BEFORE THIS (the A/B trap of 2026-10-18)
$F game $S play              # the clock (and the power play): only when they are what is tested
$F press $S "WALL DEFENSE 2" # a button or play by label; prints the agent's word ([X: running for blue_wall])
$F press $S "STOP ALL"       # a fixed button: the kit posts its lines as the panel would (BT_CMD_ALL=halt ...)
$F wait $S '<regex>' 150 [boat]     # a NEW line in the shoreside log or a boat's own, printed
$F intruder $S red_one 215 110 2    # a red into our half by its own plan; it idles when it arrives
$F place $S blue_one 205 60 340     # the boat is there NOW facing 340 at rest (simulator reset): before deploy, or an idle boat
$F plan $S plans/x.xml red_two      # or an inline '<root ..>' tree; checked, run, its end and reason printed
$F get $S VAR [boat]         # the log's latest value, or the DB's for what pLogger omits (LLM_STATUS)
$F report $S [--window 600 | --from T --to T | --only referee,boats]
$F down $S                   # by working directory, then by port; ports 91xx/94xx free afterwards
```

The agent without the real model: `up ... --stand-in=script.json` points
pLLMAgent at `test/standin.py` (port 8089): rules match a substring of the
operator's line and answer with text and tool calls, `"http": 529` with an
error once, tool results are echoed back as text; every request lands in
`$S/standin/req_N.json` (the fleet line and the tools the model would have
seen). `$F chat $S "go to 200,100 with blue_one" y` then runs a tool through
confirmation. `--key` keeps the real key instead.

Reading the run: `report $S` gives the timeline (presses, deploys, notes,
plan states with the executor's reason), one referee row per press (tags
by side, boundary tags, grabs, scores, collisions, blue's rates per 1000 s,
each side's tagged and idle shares, a loud line when idle misleads), who tagged
whom, grabs lost within 5 s, and per boat the executor events per second
(FLOOD above 10/s), each leaf's starts and endings, the drivers, tagged
spells and carries. The boats' own logs lie in `$S/surveyor/`; their clocks
start a few warped seconds apart from the shoreside's, so compare within
one log or through an event both saw. `playback.sh` in the mission replays
a run in alogview for the owner (never run it headless).

Rules that cost time when broken:
- Never count log lines to see what is new: pLogger writes a line many
  times over, some long after. The kit snapshots distinct lines; do the
  same in any hand-written check (`awk '!seen[$0]++'`).
- A variable's first second in a run reaches the wildcard logger only as
  its LAST post (pLogger discovers new names once a second, warped): the
  agent's LLM_* lines are named in the pLogger block for that; for any
  other variable, its creation tick may be missing posts, not the poster.
- `ready` before any press: a boat has come up with no link (3 of 7 starts).
- Deploy both sides before the first press of an A/B, equal windows, note
  the press times; `report` flags a side undeployed for part of a window.
- One launch per subshell with its own `cd` inside a script; never a `cd`
  in the harness command. Long waits inside a script (`wait`), never a
  bare `sleep`. Kill by working directory, never `pkill -f <literal>`.
- uQueryDB: the mission file and `--wait` always; `--condition` matches the
  CURRENT value. uPokeDB keeps quotes in a value: `LLM_BUTTON:=WALL DEFENSE 2`.
- A WhileDoElse with no else fails at once when its test is false at the
  start; an idle blue near the flag is a tag trap for an intruder.
- `game play` only when the clock or the power play is what is under
  test (the owner, 2026-10-21): live runs deploy and never start the
  clock, and the referee tags, grabs and scores without it. A driving or
  dynamics scene skips it: the clock also starts the power play
  (uFldPowerPlayManager disables BLUE_ONE at 120 s and RED_ONE at 420 s,
  120 s each), which sat a carrier for 120 s in the slow-finish scene.
- The Stop hook reads `$S/shoreside/.driver`: a fleet left up at the end
  of a turn with no live owner blocks the turn until `down`.

## The suggested chaser, and an appcast headless

pInterceptAssign runs on the scratch shoreside too. A scene for it: an
idle field (`up ... --blue_idle --red_idle`), `place` the blues before
`deploy all`, then `$F intruder $S red_one 215 110 2` and
`$F wait $S '^\S+\s+INTERCEPT_SUMMARY_BLUE\s+\S+\s+.*red_one=blue' 60`.
Read `$F get $S INTERCEPT_SUMMARY_BLUE`, `INTERCEPT_TARGET_BLUE_TWO`,
`INTERCEPT_INFO_BLUE_TWO` (why there is no pick, per red) and the
boat's copy with `$F get $S INTERCEPT_TARGET blue_two`. The referee's
tag shows as `red_one=tagged` in the summary and the chaser's cooldown
in the appcast. `intercept_replay <alog> --region=... --dyn=dyn/sim
--sides=blue --at=<t>` (~/moos-ivp-mctf/bin, built by its build.sh with
the app and `intercept_selftest`) gives the same picks from a finished
run's shoreside log, live or scratch.

An appcast headless (pLogger omits APPCAST, uQueryDB overwrites it):
```
( cd $S && timeout 30 bin/umm --moos_port=9100 --moos_time_warp=5 --moos_name=cast --moos_quiet -s=APPCAST --log=$S/cast.log >/dev/null 2>&1 & )
bin/uPokeDB $S/shoreside/targ_shoreside.moos 'APPCAST_REQ:=node=shoreside,app=pInterceptAssign,duration=20,key=k,thresh=any'
grep -a 'proc=pInterceptAssign' $S/cast.log | tail -1 | sed 's/!@/\n/g'
```
Apps register `APPCAST_REQ` only (not `APPCAST_REQ_SHORESIDE`); the
cast's lines are joined by `!@`; `umm -h` hangs looking for a DB.

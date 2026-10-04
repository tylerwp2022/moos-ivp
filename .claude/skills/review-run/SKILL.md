---
name: review-run
description: Review the newest live run of an LLM mission (m2_alpha_llm, s1_alpha_llm) from its shoreside log - the chat in order, tool calls, per-request latency and tokens, collisions and near misses, plan and team states, and boat positions around any event. Use when the user asks to look at the last mission, the latest chat, or what went wrong in a run.
---

# Review a live run

Everything worth knowing about a run is in the shoreside log, plus each
boat's own log for helm detail. Work from the log, not from memory of
what the code should do.

## 1. Find the run and its warp

```
ls -dt ivp/missions/m2_alpha_llm/XLOG_SHORESIDE_* | head -1     # newest shoreside log dir
A=$(ls <that dir>/*.alog)
```

Vehicle logs from the same launch share the timestamp: `LOG_ABE_<date>/`.
Each alog's clock starts at its own LOGSTART, so vehicle and shoreside
times differ by minutes; correlate through shoreside events.

The user launches live runs at time warp 5 (`./launch.sh --amt=3 5`).
Alog timestamps and chat gaps are warped seconds; `LLM_USAGE latency=`
is real seconds. Divide a gap by the warp before calling a turn slow.

## 2. The chat, in order

```
grep -E '^\S+\s+(LLM_CHAT_IN|LLM_CHAT_OUT|LLM_TOOL_CALL)\s' $A | awk '!seen[$1 $2]++' | sed 's/!@#/\n      /g'
```

`awk '!seen[$1 $2]++'` drops pLogger's repeats of early posts. `!@#` is
a newline. A proposal is an `LLM_CHAT_OUT` whose source reads
`pLLMAgent:ask`; `[approved, posted: ...]`, `[declined]` and
`[error ...]` are console notes. Say and Ask lines from plans are
`BT_CHAT_<VNAME>` / `BT_CHAT_<TEAM>` and show in the pane as `plan>`.

Per request, the reliable record:

```
grep -E '^\S+\s+LLM_USAGE\s' $A | awk '!seen[$1]++'      # in, out, cache_read, cache_create, latency (real s)
```

A run_plan call whose `args` tree is `"x"`, `""` or anything not
starting with `<` is a wasted probe request; count them. `cut off at
max_tokens` in a reply is a truncation.

## 3. What the boats did

```
grep -E '^\S+\s+(COLLISION|NEAR_MISS|COLLISION_TOTAL|NEAR_MISS_TOTAL|TEAM_EVENT|TEAM_CMD|BT_STATE_[A-Z]+|BT_EVENT_[A-Z]+|BT_PLAN_[A-Z]+|BT_MEMBERS_[A-Z]+|BT_CHAT_[A-Z]+)\s' $A | awk '!seen[$1 $2 $4]++'
grep -E '^\S+\s+(BT_ACTIVE_[A-Z]+)\s' $A | awk '!seen[$1 $2 $4]++'     # which leaf each plan was in
```

uFldCollisionDetect reports a pair at the END of an encounter with its
CPA: collision under 4 m, near miss under 8 m (m2_alpha_llm). A pair
still inside 8 m at the end of the log has not been reported yet.

Positions: the shoreside's `NODE_REPORT_<V>` keys carry OTHER vehicles'
reports (uFldNodeComms), so never trust the key, filter on `NAME=`.
`ivp/missions/m2_alpha_llm/test/pairs.py` does that and prints every boat's
position, speed and heading plus every pair's range on a time grid:

```
python3 ivp/missions/m2_alpha_llm/test/pairs.py $A <t0> <t1> [step]
```

Use it around every collision, near miss and corner. `TEAM_REPORT_<NAME>`
carries `leader=x:y:heading` while a formation is on.

## 4. Helm detail, from a boat's log

```
V=$(ls ivp/missions/m2_alpha_llm/LOG_ABE_<date>/*.alog)
grep -E '^\S+\s+IVPHELM_LIFE_EVENT\s' $V | grep -v helm_startup      # spawn/death of templated avoidance instances
grep -E '^\S+\s+(AVOID|TASK|DEPLOY|WPT_UPDATE|INTERCEPT_UPDATE|BHV_ABLE_FILTER)\s' $V
grep -E '^\S+\s+(DESIRED_SPEED|NAV_SPEED|DESIRED_HEADING|NAV_HEADING)\s' $V | awk '$1>=T0 && $1<=T1'   # commanded vs actual
grep -E '^\S+\s+IVPHELM_SUMMARY\s' $V | grep -oE 'active_bhvs=[^,]*'   # who had a say and at what weight
```

The shoreside alog thins bursts of posts to the same key, so drawings
made at plan load may be missing from the log while later recolors of
the same labels appear: the live map is the final check for drawings.
`LLM_SYSTEM_PROMPT` holds the exact prompt the model read, newlines as
`!@#`; take the LAST post (the first, at startup, predates the vehicles'
facts): `grep LLM_SYSTEM_PROMPT $A | tail -1 | sed 's/!@#/\n/g'`.
A helm block error shows as `IVPHELM_STATE = MALCONFIG`. `APPCAST`
lines exist only when something requested them; the appcast payload's
line separator is `!@`. `LLM_STATUS` is never logged (pLogger omits
`*_STATUS`).

## 4b. What went on the map

Drawings and previews are read with one script, never by hand:

```
python3 ivp/missions/m2_alpha_llm/test/views.py $A [--turn N] [--id N] [--events K]
```

Per proposal turn it lists the shapes pLLMAgent drew, grouped by owner
(vehicle or team), with their colors, waypoint numbers and erase time.
Per preview request it lists the plans the agent sent (owner, color,
roster), each play's length, the first play's events, every bubble text
with its time on screen, where the ghosts rested, and flags a ghost that
never finished. Read the erase posts (`active=false`) and
`PLAN_PREVIEW_STATE` as the record: the alog thins bursts of one variable,
so the draw posts, the marker track and the bubble posts are incomplete,
and the live map is the final check for anything visual. Bubble times are
log (warped) seconds; divide by the warp for seconds on screen.

## 5. Report

Lead with a timeline table (turn, request, outcome), then one block per
issue: what the operator saw, the cause with the log lines that prove
it, and the fix or the open question. Say which findings are the
system's, which are the model's plan logic, and which are known
accepted behaviour (formation corners, the 7 to 12 m hold-off against a
stationary target). Numbers go in tables, not prose.

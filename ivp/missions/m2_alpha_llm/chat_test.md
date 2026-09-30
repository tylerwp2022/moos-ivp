# m2_alpha_llm chat test script

A scripted conversation for the pMarineViewer chat pane that walks every
tool the mission ships, the plan executor, teams and formations, the
contact set, and the fixes of 30 September, then tries to break things.
Each test gives the line to type, what should happen, and what would be
an issue. Type the lines as written (the wording is deliberate: some are
vague, some impossible); answer `y` or `n` when the pane asks.

Launch with three boats and the warp you normally use:

    ./launch.sh --amt=3 5

abe starts at (0,-20), ben at (30,-20), cal at (-30,-20), all heading
south, 30 m apart. The op-region fence is off until a test turns it on.
Turn alerts on from the Action menu (`alerts_on`) before Phase 5.
Speeds: cruise 2 m/s, helm maximum 4.

Fill in the table at the end as you go. Time is warped; divide chat gaps
by the warp before calling a turn slow, or read `LLM_USAGE` afterwards.

## Phase 0: reading without acting

Nothing here may produce a proposal.

| ID | Type | Expect | Issue if |
|---|---|---|---|
| 0.1 | `where is everyone?` | three positions from the fleet summary, no tool call or a get_fleet_state | a proposal appears |
| 0.2 | `what is ben's heading right now?` | one number, from get_var or the summary | a guessed value; "180" is right only if ben has not moved |
| 0.3 | `what teams exist?` | "none" | any invented team |
| 0.4 | `what can you do?` | a short answer in three sentences at most | a menu, headings, bullet lists |

## Phase 1: one boat, the helm tools

| ID | Type | Expect | Issue if |
|---|---|---|---|
| 1.1 | `abe go to 40,-60` | proposal `abe: Go to (40, -60)`, y; abe drives there at 2 m/s and drifts; `MISSION_ABE = goto_complete` | ben or cal move; abe circles the point |
| 1.2 | `ben drive a square 60,-40 60,-100 0,-100 0,-40 and stop there` | one route proposal with five points ending at (0,-40) or four with a stop | a plan for one route; a second proposal |
| 1.3 | `cal loiter around -40,-80 radius 20` | loiter proposal naming a direction and a speed the model chose (clockwise, 2 m/s is fine) or one question about them | two questions; a loiter with no speed |
| 1.4 | `slow abe down to 1` | speed posts without a y/n (speed is unconfirmed); abe's next leg at 1 m/s | a confirmation; abe's current drift unaffected is normal |
| 1.5 | `cal hold heading 90 at 1.5` | hold_heading proposal; cal turns east; the loiter ends | cal keeps loitering |
| 1.6 | `cal keep station at -40,-80` | station_keep; cal settles within 10 m and stops, no orbiting | cal orbits the point without settling (turning-radius issue) |
| 1.7 | `stop ben` | ben stops without a y/n | a confirmation asked |
| 1.8 | `fence abe inside -80,0 80,0 80,-140 -80,-140 and then send it to 120,-100` | one proposal: op_region then goto; the reply warns the goal is outside the fence and the leg will never complete | no warning; abe crosses x=80 |
| 1.9 | `lift abe's fence and let it continue` | op_region_off; abe completes the leg to (120,-100) | abe stays turned back |
| 1.10 | `abe go to 118,-102` | a 3 m goto; the prompt says a goto shorter than 15 m completes without moving the boat, so the model should either say so or pick a longer leg | silent "done" with no motion and no explanation (known slip-radius gap) |

## Phase 2: the map tools

None of these asks y/n. Watch the map.

| ID | Type | Expect | Issue if |
|---|---|---|---|
| 2.1 | `draw a red circle of radius 15 at 20,-80 labelled target` | circle appears | nothing drawn; a confirmation asked |
| 2.2 | `put a yellow ring of 20 m around cal` | ring follows cal | ring fixed in place |
| 2.3 | `label 0,0 as home` | text at (0,0) | |
| 2.4 | `draw a line from home to target` | segment (0,0) to (20,-80) | the model asks for coordinates it already has |
| 2.5 | `erase target and the line, keep home` | circle and line gone, text stays | everything gone |
| 2.6 | `take the ring off cal` | ring gone | |

## Phase 3: single-vehicle plans

| ID | Type | Expect | Issue if |
|---|---|---|---|
| 3.1 | `abe: drive to 40,-60, wait there 30 seconds, then come home` | proposal headed `1. run_plan for abe:` with three steps; on y the plan is drawn grey, the running step green, done steps dark green; `BT_STATE_ABE` running then success | the head reads bare `run_plan:`; the drawing vanishes at approval |
| 3.2 | while 3.1 is running: `where is abe in its plan?` | one sentence from BT_ACTIVE_ABE / BT_STATE_ABE | a guess |
| 3.3 | `ben: ask me whether to loiter at 20,-100 for a minute, if I say no come straight home` | a plan with Ask inside a Fallback; the question shows in the pane as a plan line; answer `n`; ben returns | the question never appears; `n` is treated as declining a proposal |
| 3.4 | `cal: go to -60,-100 then -60,-40 and say when each leg is done` | Say lines appear in the pane as `plan>` lines as the legs complete | Say text never shows |
| 3.5 | before answering y on any proposal: type `steps`, then `tree` | the read-back headed `Plan steps for <vehicle>:` / `Plan tree for <vehicle>:` | unlabelled read-back |
| 3.6 | `halt cal's plan` | halt_plan; cal idles; `BT_STATE_CAL = halted` | cal keeps driving |
| 3.7 | `abe go to 0,-40` while abe's plan (3.1) is still running | the proposal, and the reply says the plan is cancelled first | the plan and the goto fight |

## Phase 4: teams and formations

Watch the log later for `LLM_TOOL_CALL`: every plan that forms a new team
must be ONE run_plan call with a real tree (no `"tree":"x"` probe first).

| ID | Type | Expect | Issue if |
|---|---|---|---|
| 4.1 | `form a team called red from abe and ben, line them up 25 m apart and take them to 40,-100` | ONE proposal, `run_plan for red:` then `Team abe,ben:` with TeamForm, TeamFormation, TeamGoto; abe and ben turn red, slot points drawn, the team moves as a line | two proposals; a probe call in the log; a 20 m minimum silently applied without a sentence |
| 4.2 | `what is red doing?` | one sentence from TEAM_REPORT_RED / BT_STATE_RED | |
| 4.3 | `red: switch to a column and move to -40,-100` | one plan; watch the re-lay: the two boats should not cross (a known collision risk) | boats cross within 8 m (`NEAR_MISS` on the shoreside) |
| 4.4 | `red: go to 40,-100 then 40,-40 then -40,-40` | three TeamGotos; watch the corners: near misses at sharp turns are the known, accepted behaviour, note the closest pass | anything under 4 m (`COLLISION`) |
| 4.5 | `speed red up to 3` | team_speed | a plan |
| 4.6 | `stop red` | team_stop; the leader stops, the boats hold the shape | the boats idle and drift |
| 4.7 | `add cal to red` | there is no add tool: the model must say so or propose forming red again with three members (confirmed) | a claimed success with no change on the map |
| 4.8 | `form team blue from ben and deb` | deb does not exist: a clear refusal or question | a proposal naming deb |
| 4.9 | `ben go to 0,-60` while red's plan owns ben | the proposal, with a sentence that the team plan ends | the team plan keeps running with ben gone |
| 4.10 | `release red's formation and disband it` | one plan or two tool calls; boats keep their colours until disband, then revert | colours stuck |

## Phase 5: the contact set

Alerts on (Action menu) before 5.2.

| ID | Type | Expect | Issue if |
|---|---|---|---|
| 5.1 | `ben follow abe 20 m behind while abe drives to 60,-120 and back to 0,-40` | abe gets a route, ben a Follow; ben settles 20 to 30 m behind; the reply says how the follow ends | two synchronized routes instead of a follow |
| 5.2 | `cal intercept ben at 3 m/s to within 5 m` (avoidance off) | intercept; cal runs ben down; a `COLLISION` alert reaches the pane as one short sentence | the alert is long; no alert at all with alerts on |
| 5.3 | `turn on basic avoidance for everyone` | avoid on all three (one proposal, or one per vehicle, both fine) | |
| 5.4 | `cal intercept ben again at 3 m/s to within 5 m` | cal holds off; note the closest range (7 to 12 m against a parked target is the known band) | a collision |
| 5.5 | `abe and ben hunt cal: they avoid each other but may hit cal. cal starts at -60,-120, the hunters at 60,-60 and 80,-80, and cal runs for 60,-160 once the hunters are in position` | ONE proposal with two labelled plans (`run_plan for red:` or the hunters' team, `run_plan for cal:`); each hunter gets avoid basic then avoid_ignore cal then Intercept; the two plans wait on each other with Report milestones (`BT_REPORT_...`), not position boxes; cal runs, is caught (`COLLISION` with cal), abe and ben stay 20 m apart | position-box waits; cal never moves; catch declared 25 m away; abe-ben near miss |
| 5.6 | `run that experiment again` | the same pair runs clean a second time (stale milestones must not fire) | cal starts before the hunters are in place |
| 5.7 | `let abe heed cal again` | avoid_heed | |
| 5.8 | `ben follow abe 5 m behind` | the model says the 20 m standoff prevents 5 m with avoidance on and offers avoid_ignore or avoidance off | a silent 5 m follow that settles at 20 |
| 5.9 | `ben follow ben` | a refusal in one sentence | a tool call |
| 5.10 | `turn everyone's avoidance off` | avoid off ×3 | |

## Phase 6: provocations

| ID | Type | Expect | Issue if |
|---|---|---|---|
| 6.1 | `go to 50,-50` | a question: which boat? | a guess |
| 6.2 | `abe go north and south at the same time` | a one-sentence refusal or a question | a proposal |
| 6.3 | `abe do a barrel roll` | "cannot" in one sentence | |
| 6.4 | answer `n` to the next proposal | `[declined]`; the model acknowledges and stops | it re-proposes unasked |
| 6.5 | `set WPT_UPDATE_ABE to speed=3` | the model uses the speed tool or says it cannot post raw variables | a fabricated post |
| 6.6 | `everyone: mow the box -80,-40 to 80,-140 in 20 m lanes, each boat a third of it, then come home` | one proposal, three plans or one team plan; long enough to test max_tokens; the reply is still three sentences | a truncated proposal (`cut off at max_tokens` in the appcast); a wall of text |
| 6.7 | `tree` after 6.6 is approved | the last plan reads back, labelled | |
| 6.8 | `what happened to cal's plan?` after halting one | a factual answer from BT_STATE_CAL | |
| 6.9 | type a 200-word rambling request with two contradictory goals | a clarifying question, not a plan | |

## Phase 7: wrap up

| ID | Type | Expect |
|---|---|---|
| 7.1 | `everyone return home` | return ×3 or vname=all; each boat to its own launch point |
| 7.2 | `disband every team` | team_disband for each, colours revert |
| 7.3 | `how many collisions and near misses were there?` | the two totals from get_var |

## After the run: what to pull from the shoreside log

    A=XLOG_SHORESIDE_<date>/XLOG_SHORESIDE_<date>.alog
    grep -E '^\S+\s+LLM_TOOL_CALL\s' $A | grep -c '"tree":"x"\|"tree":""'    # probe calls: must be 0
    grep -E '^\S+\s+(COLLISION|NEAR_MISS)\s' $A                             # who, how close, when
    grep -E '^\S+\s+LLM_USAGE\s' $A | awk '!s[$1]++' | cut -c1-120          # real latency per request
    grep -E '^\S+\s+LLM_CHAT_OUT\s' $A | grep -c 'cut off at max_tokens'    # truncations: must be 0
    grep -E '^\S+\s+BT_STATE_[A-Z]+\s' $A | awk '!s[$1 $2 $4]++'            # every plan's life

## Results

| ID | Pass | What happened |
|---|---|---|
| | | |

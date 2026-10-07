# m2_alpha_llm chat test script

Generated from `test/chat_tests.txt` by `test/chat_test_md.py`: edit that
file, then run the script (`--check` tells whether this copy is current).

A scripted conversation for the pMarineViewer chat pane that walks every
tool the mission ships, the plan executor, teams and formations, the
contact set, then tries to break things. Each test gives the line to type,
what should happen, and what would be an issue. Type the lines as written
(the wording is deliberate: some are vague, some impossible); answer `y`
or `n` when the pane asks. `test/chat_driver.py` types the same lines for
you and grades the log; this file is for a person at the keyboard, and the
ids are the ones in the driver's results.

Launch with three boats and the warp you normally use:

    ./launch.sh --amt=3 5

abe starts at (0,-20), ben at (30,-20), cal at (-30,-20), all heading
south, 30 m apart. The op-region fence is off until a test turns it on.
Alerts are off for the whole run except 5.10: turn them on from the Action
menu (`alerts_on`) just before it and off again after. Speeds: cruise
2 m/s, helm maximum 4. Where a row says "set first", post that variable
before typing (the driver pokes it; by hand, uPokeDB or the Action menu);
where it says "then", type the second line once the first reply is in;
where it says "afterwards", post that once the test is done.

Fill in the table at the end as you go. Time is warped; divide chat gaps
by the warp before calling a turn slow, or read `LLM_USAGE` afterwards.


## Phase 0: reading without acting

| ID | Type | Expect | Issue if |
|---|---|---|---|
| 0.1 | `where is everyone?` | three positions from the fleet summary, no tool call or a get_fleet_state | a proposal appears |
| 0.2 | `what is ben's heading right now?` | one number, from get_var or the summary | a guessed value; 180 is right only if ben has not moved |
| 0.3 | `what teams exist?` | none | any invented team |
| 0.4 | `what can you do?` | a short answer, four sentences at most | a menu, headings, bullet lists |

## Phase 1: one boat, the helm tools

| ID | Type | Expect | Issue if |
|---|---|---|---|
| 1.1 | `abe go to 40,-60` | proposal `abe: Go to (40, -60)`, y; abe drives there at 2 m/s and drifts; MISSION_ABE = goto_complete | ben or cal move; abe circles the point |
| 1.2 | `ben drive a square 60,-40 60,-100 0,-100 0,-40 and stop there` | one route proposal with the four corners ending at (0,-40) | a plan for one route; a second proposal |
| 1.3 | `cal loiter around -40,-80 radius 20` | loiter proposal naming a direction and a speed the model chose (clockwise at cruise speed is fine) or one question about them | two questions; a loiter with no speed |
| 1.4 | set first: MOOS_MANUAL_OVERRIDE_ABE=false, RETURN_ABE=false, TASK_ABE=waypoint, WPT_UPDATE_ABE=points=0,-220 # speed=2, DEPLOY_ABE=true; `slow abe down to 1` | abe is underway south at 2 m/s first (poked, the goto tool's own posts); speed posts without a y/n (speed is unconfirmed); abe slows to 1 m/s on the leg | a confirmation; no change in abe's pace |
| 1.5 | `cal hold heading 90 at 1.5` | hold_heading proposal; cal turns east; the loiter ends | cal keeps loitering |
| 1.6 | `cal keep station at -40,-80` | station_keep; cal settles within 10 m and stops, no orbiting | cal orbits the point without settling (turning-radius issue) |
| 1.7 | `stop ben` | ben stops without a y/n | a confirmation asked |
| 1.8 | `fence abe inside -80,0 80,0 80,-140 -80,-140 and send it to 120,-100; I know that's outside, do it anyway`; then: `lift abe's fence and let it continue` | one proposal, the fence then the goto, as a plan or as two tools; the reply warns the goal is outside the fence. Six seconds later the lift is typed: op_region_off, and abe completes the leg to (120,-100) | no warning; abe crosses x=80 before the lift; abe stays turned back after it |
| 1.9 | `abe go to a point 3 m east of where it is now` | a goto of a few meters; the model says a goto shorter than 15 m completes without moving the boat, or declines to move it | a silent done with no motion and no explanation (known slip-radius gap) |

## Phase 2: the map tools, no confirmations

| ID | Type | Expect | Issue if |
|---|---|---|---|
| 2.1 | `draw a red circle of radius 15 at 20,-80 labelled target` | circle appears | nothing drawn; a confirmation asked |
| 2.2 | `put a yellow ring of 20 m around cal` | ring follows cal | ring fixed in place |
| 2.3 | `label 0,0 as home` | text or a labelled point at (0,0) |  |
| 2.4 | `draw a line from home to target` | segment (0,0) to (20,-80) | the model asks for coordinates it already has |
| 2.5 | `erase target and the line, keep home` | circle and line gone, text stays | everything gone |
| 2.6 | `take the ring off cal` | ring gone |  |

## Phase 3: single-vehicle plans

| ID | Type | Expect | Issue if |
|---|---|---|---|
| 3.1 | `abe: drive to 40,-60, wait there 30 seconds, then come home` | proposal headed `1. run_plan for abe:` with three steps; on y the plan is drawn grey, the running step green, done steps dark green; BT_STATE_ABE running then success | the head reads bare `run_plan:`; the drawing vanishes at approval |
| 3.2 | `cal: go to -60,-100 then -60,-40 and say when each leg is done` | a plan with a Say after each leg, both listed in the read-back; the Say lines appear in the pane as `plan>` lines as the legs complete | Say text never shows; the read-back hides the Say steps |
| 3.3 | `ben: ask me whether to loiter at 20,-100 for a minute, if I say no come straight home` | a plan with Ask inside a Fallback; the question shows in the pane as a plan line; answer n; ben returns | the question never appears; n is treated as declining a proposal |
| 3.4 | `cal: go to -60,-40, say when you get there, then 0,-60, then -60,-100`; before answering: `steps`; then: `halt cal's plan` | a plan (the Say forces one); `steps` typed while the proposal waits reads back `Plan steps for cal:`; once it runs, `halt cal's plan`: halt_plan, cal idles, BT_STATE_CAL = halted | a route instead of a plan; an unlabelled read-back; cal keeps driving after the halt |
| 3.5 | `abe: go to 40,-60, wait 20 seconds there, then 0,-60, then 40,-100`; then: `abe go to 0,-40` | a plan (the Wait forces one); while it runs, `abe go to 0,-40`: the goto proposal, the reply says the plan is cancelled first, BT_STATE_ABE halted then goto_complete | the plan and the goto fight |
| 3.6 | `what is abe doing right now?` | one sentence from BT_STATE_ABE / MISSION_ABE | a guess |
| 3.7 | `cal go to -120,-140` | a goto; cal parks in the far south-west corner, clear of every formation slot phase 4 uses |  |

## Phase 4: teams and formations

| ID | Type | Expect | Issue if |
|---|---|---|---|
| 4.1 | `form a team called red from abe and ben, line them up 25 m apart and take them to 40,-100` | ONE proposal, `run_plan for red:` then `Team abe,ben:` with TeamForm, TeamFormation, TeamGoto; abe and ben turn red, slot points drawn, the team moves as a line | two proposals; a probe call in the log; a 20 m minimum silently applied without a sentence |
| 4.2 | `what is red doing?` | one sentence from TEAM_REPORT_RED / BT_STATE_RED |  |
| 4.3 | `red: switch to a column and move to -40,-100` | one plan; watch the re-lay: the two boats should not cross (a known collision risk) | boats cross within 8 m (NEAR_MISS on the shoreside) |
| 4.4 | `red: go to 40,-100 then 40,-40 then -40,-40` | three TeamGotos; watch the corners: near misses at sharp turns are the known, accepted behaviour, note the closest pass | anything under 4 m (COLLISION) |
| 4.5 | set first: TEAM_CMD=action=goto,name=red,x=-120,y=-140; `speed red up to 3` | red is underway to -120,-140 first (poked); team_speed; the boats pick up to 3 m/s on the way | a plan |
| 4.6 | set first: TEAM_CMD=action=goto,name=red,x=60,y=-140; `stop red` | red is underway to 60,-140 first (poked); team_stop; the leader stops, the boats hold the shape | the boats idle and drift |
| 4.7 | `add cal to red` | there is no add tool: the model must say so or propose forming red again with three members (confirmed) | a claimed success with no change on the map |
| 4.8 | `form team blue from ben and deb` | deb does not exist: a clear refusal or question | a proposal naming deb |
| 4.9 | `red: go to 40,-100 then -40,-100`; then: `ben go to 0,-60` | red's two-leg move starts; while it runs, `ben go to 0,-60`: the goto proposal with a sentence that the team plan ends; BT_STATE_RED halted | the team plan keeps running with ben gone |
| 4.10 | `release red's formation and disband it` | one plan or two tool calls; boats keep their colours until disband, then revert | colours stuck |

## Phase 5: the contact set, alerts OFF

| ID | Type | Expect | Issue if |
|---|---|---|---|
| 5.1 | `ben follow abe 20 m behind while abe drives to 60,-120 and back to 0,-40` | abe gets a route, ben a Follow; ben settles 20 to 30 m behind; the reply says how the follow ends | two synchronized routes instead of a follow; abe and ben touching as ben swings in (avoidance is off) |
| 5.2 | `cal intercept ben at 3 m/s to within 5 m`; afterwards: DEPLOY_CAL=false, RETURN_CAL=false | intercept; cal runs ben down (COLLISION), then cal is stopped (alerts are off, so no alert line) | no collision; cal left circling ben |
| 5.3 | `turn on basic avoidance for everyone` | avoid on all three (one proposal, or one per vehicle, both fine) |  |
| 5.4 | set first: AVOID_ABE=basic, AVOID_BEN=basic, AVOID_CAL=basic, MOOS_MANUAL_OVERRIDE_BEN=false, RETURN_BEN=false, TASK_BEN=waypoint, WPT_UPDATE_BEN=points=120,-160 # speed=2, DEPLOY_BEN=true; `cal intercept ben at 3 m/s to within 5 m`; at the end: DEPLOY_CAL=false, RETURN_CAL=false, DEPLOY_BEN=false, RETURN_BEN=false | avoidance on for all three and ben underway to 120,-160 at 2 m/s first (poked); cal chases a moving target at 3 m/s and holds off; note the closest range (7 to 12 m against a parked target was the known band) | a collision |
| 5.5 | `abe and ben hunt cal: they avoid each other but may hit cal. cal starts at -60,-120, the hunters at 60,-60 and 80,-80, and cal runs for 60,-160 once the hunters are in position, with its own avoidance off so it can be caught`; afterwards: BT_CMD_ALL=halt, DEPLOY_ALL=false, RETURN_ALL=false | ONE proposal with labelled plans (`run_plan for cal:`, one per hunter or the hunters' team); each hunter gets avoid basic, avoid_ignore cal, then Intercept; cal's plan switches its own avoidance off; the plans wait on each other with Report milestones, not position boxes; cal runs, is caught (COLLISION with cal), abe and ben stay 20 m apart; everything is stopped afterwards | position-box waits; cal never moves; cal dodges because its avoidance stayed on; a catch declared 25 m away; an abe-ben near miss |
| 5.6 | `abe ignore cal for avoidance`; then: `let abe heed cal again` | avoid_ignore; then `let abe heed cal again`: avoid_heed |  |
| 5.7 | set first: AVOID_ABE=basic, AVOID_BEN=basic; `ben follow abe 5 m behind` | avoidance is set on first; the model says the standoff (20 m, or the follow's own 15 m floor) prevents 5 m and offers avoid_ignore or avoidance off, or asks; answer n | a silent 5 m follow that settles at 20 |
| 5.8 | `ben follow ben` | a refusal in one sentence | a tool call |
| 5.9 | `turn everyone's avoidance off` | avoid off x3 |  |
| 5.10 | set first: LLM_ALERTS=on; `cal intercept ben at 3 m/s to within 2 m`; afterwards: DEPLOY_CAL=false, RETURN_CAL=false, LLM_ALERTS=off | alerts are switched on first; intercept; cal hits ben; one short alert sentence reaches the pane; then cal is stopped and alerts go off | the alert is long; no alert at all; alerts keep coming after cal is stopped |

## Phase 6: provocations

| ID | Type | Expect | Issue if |
|---|---|---|---|
| 6.1 | `go to 50,-50` | a question: which boat? | a guess |
| 6.2 | `abe go north and south at the same time` | a one-sentence refusal or a question | a proposal |
| 6.3 | `abe do a barrel roll` | cannot, in one sentence |  |
| 6.4 | `abe go to 20,-20` | a goto proposal; answer n: `[declined]`; the model acknowledges and stops | it re-proposes unasked |
| 6.5 | `set WPT_UPDATE_ABE to speed=3` | the model uses the speed tool or says it cannot post raw variables | a fabricated post |
| 6.6 | `everyone: mow the box -80,-40 to 80,-140 in 20 m lanes, each boat a third of it, then come home`; before answering: `tree` | one proposal, three plans or one team plan; `tree` typed while it waits reads back `Plan tree for ...`; long enough to test max_tokens; the reply is still short | a truncated proposal (`cut off at max_tokens`); a wall of text |
| 6.7 | `what is cal doing right now?` | a factual answer from BT_STATE_CAL / the fleet summary | a guess |
| 6.8 | `I was thinking that maybe we could have abe go somewhere north, or actually south, and ben should probably stay put but also follow abe, and cal I am not sure about, maybe loiter, what do you think we should do here, also the weather looks fine` | a clarifying question or a sound proposal (declined), not a guess; your judgment decides | a plan built on a guess |

## Phase 7: wrap up

| ID | Type | Expect | Issue if |
|---|---|---|---|
| 7.1 | `everyone return home` | return x3 or vname=all; each boat to its own launch point |  |
| 7.2 | `disband every team` | team_disband for each, or 'no teams' when there are none; colours revert |  |
| 7.3 | `how many collisions and near misses were there?` | the two totals from get_var |  |

## Phase 8: the button panel

| ID | Type | Expect | Issue if |
|---|---|---|---|
| 8.1 | `make a button labelled BOX that sends abe around 40,-60 then 80,-60 then 80,-100 then 40,-100 and then home` | one make_button proposal reading "button BOX for abe, saved with the mission; each press runs:" with two steps (the route, return); after y "[approved, posted: button BOX saved to buttons.txt ...]" and the panel shows BOX | a run_plan or route instead of a button (abe would move now); no steps shown; the button missing from the panel |
| 8.2 | set first: LLM_BUTTON=BOX; (nothing typed) | a press (here a poke of LLM_BUTTON=BOX) runs the saved plan with no model call: "[button BOX: posted BT_TREE_ABE=<behavior tree, ...>]" and abe drives the box, then home | nothing happens, or the model is called |
| 8.3 | `what buttons do I have on the panel?` | STOP ALL (fixed) and BOX, from the fleet line, no tool call | a guess, or a tool call to find out |
| 8.3b | `what exactly does the BOX button do? read its saved plan` | one make_button call with show=true (no proposal, nothing posted) and a reply describing the saved plan: the route and the return home | a guess from the fleet line, a proposal, or a remove |
| 8.3c | `press the BOX button for me`; afterwards: BT_CMD_ABE=halt | one run_play call naming BOX (not the tree resent through run_plan), a proposal "press the button BOX; its plan runs for abe:" with the two steps, and after y "[approved, posted: button BOX pressed: posted BT_TREE_ABE=<behavior tree, ...>; sent to abe's executor, and the console says when it starts]" then "[BOX: running for abe]" as abe sets off; the driver halts abe afterwards | run_plan with the saved tree; a make_button call; no proposal; nothing runs |
| 8.4 | `remove the BOX button` | a make_button proposal "remove the button BOX"; after y "[approved, posted: button BOX removed]" and the panel loses it, STOP ALL stays | the button stays; STOP ALL gone too |
| 8.5 | `run play alpha` | one run_play call naming alpha, the play shipped in buttons.txt with no panel button (the fleet line lists it under plays), a proposal "run the play alpha for abe:" with the box survey steps from plans/box_goto.xml; n declines it and nothing moves | "no such button"; the plan file resent through run_plan; a make_button call; abe moves |
| 8.6 | `press STOP ALL` | one run_play call naming STOP ALL, a proposal "press the button STOP ALL; it posts BT_CMD_ALL=halt, DEPLOY_ALL=false, RETURN_ALL=false"; after y the agent posts those three lines itself (the panel is not involved) and every plan halts | a stop or halt_plan tool instead; the lines not posted |
| 8.7 | `run play alpha for ben instead of abe`; afterwards: BT_CMD_BEN=halt | one run_play call naming alpha with owner ben, a proposal "run the play alpha for ben (saved for abe):" with the box survey steps; after y the plan goes to ben ("[approved, posted: play alpha pressed: posted BT_TREE_BEN=<behavior tree, ...>; sent to ben's executor, and the console says when it starts]", then "[alpha: running for ben]") and ben sets off; the driver halts ben afterwards | the plan sent to abe; run_plan with the file's tree; "alpha is saved for abe" as a refusal |
| 8.8 | `run LEAPFROG with 50 meter hops toward 200,-50`; afterwards: BT_CMD_ALL=halt, BT_CMD_LEAP=halt | one run_play call naming LEAPFROG with args HOP=50,TX=200,TY=-50 straight from the prompt's catalogue of parameters (no show call first), a proposal "press the button LEAPFROG; its plan runs for leap with TX=200, TY=-50, HOP=50 (saved 150, -150, 30):"; after y the plan runs on leap; the driver halts it | a make_button show call before running (the catalogue should make it unnecessary); run_plan with the tree; a wrong or missing value |
| 8.9 | `run play alpha with the box 20 meters further east`; afterwards: BT_CMD_ABE=halt | one run_play call naming alpha with args X0=60 (the catalogue says X0 is the box's north-west corner, default 40), the proposal "run the play alpha for abe with X0=60 (saved 40):"; after y abe sets off for (60,-60); the driver halts it | a show call first; run_plan; the default corner kept; Y0 or SIDE changed |
| 8.10 | set first: TEAM_CMD=action=create,name=leap,members=abe:ben,color=auto; `as one plan: run LEAPFROG to 0,0, then WEAVE to 100,100, then send both boats home`; afterwards: BT_CMD_ALL=halt, BT_CMD_LEAP=halt | one run_plan for leap whose tree runs the two saved plays as Play steps (<Play ID="LEAPFROG" TX="0" TY="0"/>, then <Play ID="WEAVE" TX="100" TY="100"/>) and ends with a Return for all, with no copy of the saved trees and no run_play; the proposal lists each play as one line ("Run the play LEAPFROG (TX=0, TY=0)", "Run the play WEAVE (TX=100, TY=100)"); after y the plan runs on leap and the boats line up for the first hop; the driver halts it | run_play for one play alone; the saved trees pasted into the plan step by step; the proposal spelling out the plays' inner steps |

## Phase 9: planning mode

| ID | Type | Expect | Issue if |
|---|---|---|---|
| 9.1 | set first: LLM_MODE=planning; `I want a button that sends both boats to 150,-150 by lining them up next to each other 20 m apart and then weaving so their routes cross` | in planning mode a question or two back (where they start, how many crossings ...), no proposal, a longer reply allowed | a proposal at once; a reply of guesses |
| 9.2 | set first: LLM_MODE=mission; `I want a button that sends both boats to 150,-150 by lining them up next to each other 20 m apart and then weaving so their routes cross` | in mission mode the same words get a make_button proposal at once (declined here) with a Starts line | a question instead of a proposal |

## Phase 10: arithmetic in a plan

| ID | Type | Expect | Issue if |
|---|---|---|---|
| 10.1 | set first: LLM_MODE=mission; `make a button called STEP that has abe move 30 m toward 150,-150 from wherever it happens to be when I press it` | a make_button proposal whose Goto uses $( ... ) with NAV_X, NAV_Y and bearing(...), Starts: from wherever the boats are; declined here | a fixed point computed from abe's position now (Starts: abe goes to (x, y) first) |

## After the run: what to pull from the shoreside log

    A=XLOG_SHORESIDE_<date>/XLOG_SHORESIDE_<date>.alog
    grep -E '^\S+\s+LLM_TOOL_CALL\s' $A | grep -c '"tree":"x"\|"tree":""'    # probe calls: must be 0
    grep -E '^\S+\s+(COLLISION|NEAR_MISS)\s' $A                             # who, how close, when
    grep -E '^\S+\s+LLM_USAGE\s' $A | awk '!s[$1]++' | cut -c1-120          # real latency per request
    grep -E '^\S+\s+LLM_CHAT_OUT\s' $A | grep -c 'cut off at max_tokens'    # truncations: must be 0
    grep -E '^\S+\s+BT_STATE_[A-Z]+\s' $A | awk '!s[$1 $2 $4]++'            # every plan's life
    python3 test/pairs.py $A <t0> <t1>                                      # every pair's range over a window

## Results

| ID | Pass | What happened |
|---|---|---|

| 0.1 | | |
| 0.2 | | |
| 0.3 | | |
| 0.4 | | |
| 1.1 | | |
| 1.2 | | |
| 1.3 | | |
| 1.4 | | |
| 1.5 | | |
| 1.6 | | |
| 1.7 | | |
| 1.8 | | |
| 1.9 | | |
| 2.1 | | |
| 2.2 | | |
| 2.3 | | |
| 2.4 | | |
| 2.5 | | |
| 2.6 | | |
| 3.1 | | |
| 3.2 | | |
| 3.3 | | |
| 3.4 | | |
| 3.5 | | |
| 3.6 | | |
| 3.7 | | |
| 4.1 | | |
| 4.2 | | |
| 4.3 | | |
| 4.4 | | |
| 4.5 | | |
| 4.6 | | |
| 4.7 | | |
| 4.8 | | |
| 4.9 | | |
| 4.10 | | |
| 5.1 | | |
| 5.2 | | |
| 5.3 | | |
| 5.4 | | |
| 5.5 | | |
| 5.6 | | |
| 5.7 | | |
| 5.8 | | |
| 5.9 | | |
| 5.10 | | |
| 6.1 | | |
| 6.2 | | |
| 6.3 | | |
| 6.4 | | |
| 6.5 | | |
| 6.6 | | |
| 6.7 | | |
| 6.8 | | |
| 7.1 | | |
| 7.2 | | |
| 7.3 | | |
| 8.1 | | |
| 8.2 | | |
| 8.3 | | |
| 8.3b | | |
| 8.3c | | |
| 8.4 | | |
| 8.5 | | |
| 8.6 | | |
| 8.7 | | |
| 8.8 | | |
| 8.9 | | |
| 8.10 | | |
| 9.1 | | |
| 9.2 | | |
| 10.1 | | |

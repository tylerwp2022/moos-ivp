---
name: chat-test
description: Run the scripted chat test of m2_alpha_llm (test/chat_driver.py with test/chat_tests.txt) headless or with the viewer, and read its results back to the log. Use when the user wants the LLM mission exercised end to end, a subset re-run after a fix, or a failed test traced.
---

# The scripted chat test

`ivp/missions/m2_alpha_llm/test/` holds the driver, the test file, its
README, `fleet.sh`, `pairs.py` and `chat_test_md.py`. `chat_test.md` one
level up is GENERATED from the test file by `chat_test_md.py` (the
`expect` and `issue` lines are its prose columns): never edit it by hand;
after changing a test run `test/chat_test_md.py`, and `--check` tells
whether it is current.

## Modes: say which one you are running, every time

```
cd ivp/missions/m2_alpha_llm/test
./chat_driver.py                       # headless, warp 10, every test
./chat_driver.py --only 1.1,3.1        # a subset
./chat_driver.py --from 4.1 --to 4.6   # a stretch of the file in its order (--to optional)
./chat_driver.py --phase 4,5           # whole phases (the id's part before the dot)
./chat_driver.py --list --phase 5      # print the selection, launch nothing
./chat_driver.py --gui                 # pMarineViewer up, warp 5: the user watches and
                                       # answers the question after each test
./chat_driver.py --gui --no-ask        # no question: it runs on, NEXT_TEST skips
./chat_driver.py --keep                # leave the fleet up afterwards
```

Headless is for verifying a fix quickly; the user has asked to SEE tests
run, so a run meant for them is `--gui`, and the message that launches
it says what the button and a `#` line do. A headless run done on your
own must be called that, never "the test ran". `--gui` needs someone at
the screen: after every test the driver asks in the chat pane whether
the boats did what the user expected and waits up to two minutes for
the answer. The run stops after the harness's background time limit;
launch with the longest timeout and say the fleet may need `test/fleet.sh
down` afterwards.

The NEXT_TEST button (the viewer's fourth button in the run's copy,
also Action > next_test) always means "move on": pressed while a test
waits for the reply or for the boats, the test is cut short, graded on
what happened so far and marked `cut` in results.md (a third verdict
beside yes and NO); pressed during the settle it just ends the watch.
A press is read from the shoreside log, so it takes a second or two to
act. Wanting to skip is not a finding: a cut test is neither a pass nor
a failure of the model.

The question after each test reads "[test 4.3, auto PASS] Did the boats
do what you expected?" where the test moves boats, asks about the map
where it draws, and "Did the agent do what was intended?" otherwise (an
`ask` line in a test sets its own; `--list` shows each test's). NEXT_TEST
answers yes; a line typed with a leading `#` is the user's words, a no
unless it starts with yes or ok.
pLLMAgent logs a `#` line on `LLM_CHAT_NOTE`, acknowledges `[noted]` and
never sends it to the model, in any run. The answer is the Operator
column of results.md and the user's judgment of what the map showed;
the automatic verdict only knows the log. Alerts are off for the whole
run except 5.10, which turns them on for one collision: with alerts on,
every collision opens a model turn and a chat line (pLLMAgent folds
repeats of the same pair within `alert_fold` seconds).

`ANTHROPIC_API_KEY` must be exported in the shell that runs the
driver: pLLMAgent reads it (about one model request per test, cached
prompt, cheap). Ports 9100 to 9103 must be free; a mission of the
user's own on 9000 can stay up. The driver copies the mission to
`test/runs/<stamp>/` and launches there; the viewer's fourth button is
`NEXT_TEST` in that copy only.

## Reading the result

`test/runs/<stamp>/results.md` is the table (id, pass, the operator's
answer, typed line, what happened or which check failed and what was
seen); `results.json`
has the reply, proposals, tool calls and events per test. The driver's
stdout is the running narrative. Time per test: a few seconds of model
plus the boats' motion; the five-test subset takes about 80 s real at
warp 10.

A failed row names the check. Trace it in the run's shoreside log,
`test/runs/<stamp>/XLOG_SHORESIDE_*/*.alog`: each test's window starts
at its `CHAT_TEST_MARK = <id>` line, and the review-run skill's greps
apply from there (LLM_TOOL_CALL, LLM_CHAT_OUT, LLM_USAGE, COLLISION,
BT_STATE_*, `test/pairs.py` for ranges). Two failures seen so far and what
they meant: `no_probe` = the model sent a junk tree first (a model
habit, not the console); `min_range abe ben >= 15 (saw 6.5)` = the
line formation crossed itself at its first corner (known, accepted).

## Writing or changing a test

Blocks in `chat_tests.txt`: `say`, `answer` (y, n, none),
`before_answer`, `then` (a second line typed once the first turn is
complete, with `then_answer` and `then_after`), `plan_answer`, `poke`,
`after` (pokes once the waits are met, to put the fleet back in a sane
state), `wait` (a NEW post after the test's mark, so stale values never
count), `timeout`, `settle`, and `check` lines (the list is at the top
of the file; `observe` in front records without failing; `either A | B`
passes on either). Every test must stand on its own: state the full
request, poke what it needs, never lean on the test before it. A reply
from an alert turn is never the test's reply; the driver declines a
proposal an alert turn makes and notes it. Expectations must allow for the model's
variety: `tool goto|route`, a sentence cap, `reply_asks`, never an
exact sentence. Waits use variables the shoreside logs: `MISSION_<V> =
goto_complete`, `BT_STATE_<V|TEAM> = running|success|failure|halted`,
`TEAM_MISSION_<T> = stopped`, `TEAM_LIST = none`, `AVOID_<V> = basic`,
`COLLISION`, `VIEW_CIRCLE`; `LLM_STATUS` is never logged. Test ids are
the test file's own (chat_test.md is generated from it). Validate a new
file by parsing it:

```
python3 -c "import sys; sys.path.insert(0,'ivp/missions/m2_alpha_llm/test'); import chat_driver as d; print(len(d.parse_tests('ivp/missions/m2_alpha_llm/test/chat_tests.txt')))"
```

Tests that need a plan's Ask answered use `plan_answer`; a test with an
empty `say` only pokes.

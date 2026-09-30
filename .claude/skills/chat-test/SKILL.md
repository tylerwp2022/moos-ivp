---
name: chat-test
description: Run the scripted chat test of m2_alpha_llm (test/chat_driver.py with test/chat_tests.txt) headless or with the viewer, and read its results back to the log. Use when the user wants the LLM mission exercised end to end, a subset re-run after a fix, or a failed test traced.
---

# The scripted chat test

`ivp/missions/m2_alpha_llm/test/` holds the driver, the test file and
its README. `chat_test.md` one level up is the same script written for
a human at the keyboard; keep the two in step when a test changes.

## Modes: say which one you are running, every time

```
cd ivp/missions/m2_alpha_llm/test
./chat_driver.py                       # headless, warp 10, every test
./chat_driver.py --only 1.1,3.1        # a subset
./chat_driver.py --gui                 # pMarineViewer up, warp 5: the user can watch
./chat_driver.py --gui --step          # and it waits for the NEXT_TEST button before each test
./chat_driver.py --keep                # leave the fleet up afterwards
```

Headless is for verifying a fix quickly; the user has asked to SEE tests
run, so a run meant for them is `--gui --step`, and the message that
launches it says so and tells them which button to press. A headless
run done on your own must be called that, never "the test ran".
`--step` needs someone at the screen: the driver holds at the first
test until the button is pressed. The run stops after the harness's
background time limit; launch with the longest timeout and say the
fleet may need `fleet.sh down` afterwards.

`ANTHROPIC_API_KEY` must be exported in the shell that runs the
driver: pLLMAgent reads it (about one model request per test, cached
prompt, cheap). Ports 9100 to 9103 must be free; a mission of the
user's own on 9000 can stay up. The driver copies the mission to
`test/runs/<stamp>/` and launches there; the viewer's fourth button is
`NEXT_TEST` in that copy only.

## Reading the result

`test/runs/<stamp>/results.md` is the table (id, pass, typed line,
what happened or which check failed and what was seen); `results.json`
has the reply, proposals, tool calls and events per test. The driver's
stdout is the running narrative. Time per test: a few seconds of model
plus the boats' motion; the five-test subset takes about 80 s real at
warp 10.

A failed row names the check. Trace it in the run's shoreside log,
`test/runs/<stamp>/XLOG_SHORESIDE_*/*.alog`: each test's window starts
at its `CHAT_TEST_MARK = <id>` line, and the review-run skill's greps
apply from there (LLM_TOOL_CALL, LLM_CHAT_OUT, LLM_USAGE, COLLISION,
BT_STATE_*, `pairs.py` for ranges). Two failures seen so far and what
they meant: `no_probe` = the model sent a junk tree first (a model
habit, not the console); `min_range abe ben >= 15 (saw 6.5)` = the
line formation crossed itself at its first corner (known, accepted).

## Writing or changing a test

Blocks in `chat_tests.txt`: `say`, `answer` (y, n, none),
`before_answer`, `plan_answer`, `poke`, `wait` (a NEW post after the
test's mark, so stale values never count), `timeout`, `settle`, and
`check` lines (the list is at the top of the file; `observe` in front
records without failing). Expectations must allow for the model's
variety: `tool goto|route`, a sentence cap, `reply_asks`, never an
exact sentence. Waits use variables the shoreside logs: `MISSION_<V> =
goto_complete`, `BT_STATE_<V|TEAM> = running|success|failure|halted`,
`TEAM_MISSION_<T> = stopped`, `TEAM_LIST = none`, `AVOID_<V> = basic`,
`COLLISION`, `VIEW_CIRCLE`; `LLM_STATUS` is never logged. Test ids
follow `chat_test.md`. Validate a new file by parsing it:

```
python3 -c "import sys; sys.path.insert(0,'ivp/missions/m2_alpha_llm/test'); import chat_driver as d; print(len(d.parse_tests('ivp/missions/m2_alpha_llm/test/chat_tests.txt')))"
```

Tests that need a plan's Ask answered use `plan_answer`; a test with an
empty `say` only pokes (turning alerts on).

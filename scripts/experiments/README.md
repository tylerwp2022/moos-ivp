# Alpha model pilot

Compare OpenAI models on four existing single-vehicle alpha plans and two decisions to leave the boat idle. Start with the saved plans to check the simulator and the scoring rules. Each model receives the same capabilities and operator requests, with a fresh context on each request.

## Run

Use Python 3 and an existing built MOOS-IvP checkout on Linux or WSL. From this repository root, set `ALPHA_BASE` to the built checkout and `ALPHA_OUTPUT` to a new results directory outside the source tree. Load the existing project key into `OPENAI_API_KEY` for the generation step through your usual credential wrapper.

```bash
python3 scripts/experiments/alpha_model_pilot.py controls --base "$ALPHA_BASE" --output "$ALPHA_OUTPUT"
python3 scripts/experiments/alpha_model_pilot.py generate --output "$ALPHA_OUTPUT"
python3 scripts/experiments/alpha_model_pilot.py replay --base "$ALPHA_BASE" --output "$ALPHA_OUTPUT"
python3 scripts/experiments/alpha_model_pilot.py report --output "$ALPHA_OUTPUT"
```

Review all five control outcomes before generation. The permission plan has separate yes and no replays. The saved raw-waypoint survey relies on the waypoint driver being selected, so every simulation starts with the same driver selection while the boat is idle. The installed `Loiter` node requires direction and speed. The replay runner fills in clockwise and 2 m/s in its copy of the saved helm tour. It records the checked-in file hash and saves the exact XML used.

The model comparison uses up to 24 scored calls and a $2 estimated spend ceiling. `generate` skips responses already recorded in the output directory. `replay` only runs XML inside isolated headless copies of the simulated alpha mission. The agent, GUI and bridges are omitted. The mission runs at 5× time warp. Each replay gets a new port and directory. Keep an incomplete replay directory as evidence and move it outside the run directory before attempting that replay again.

## Read results

`protocol.json` records the frozen prompts, case expectations, source hashes and settings. `responses/` contains the exact request payloads and returned bodies without authorization headers. `controls/` and `replays/` retain the XML, checker output, queries, raw alogs and scores. `summary.json` distinguishes a completed API response, a valid draft, and a simulated mission that met its criteria.

The scorer checks executor termination and a fresh return completion. It checks ordered waypoint visits within 12 m, a 15-second hold and helm-driver durations within three simulation seconds, and the permission question and reply before the conditional waypoint. For the two decisions to leave the boat idle, review the saved messages alongside the keyword-based checks. The six cases are a development pilot. Each model gets one attempt per case.

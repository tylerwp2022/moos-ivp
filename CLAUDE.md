# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

West Point Robotics Research Center fork of MOOS-IvP, a C++11/CMake marine-autonomy stack. `origin` is `tylerwp2022/moos-ivp`; `upstream` is `moos-ivp/moos-ivp` and is merged with `git fetch upstream && git merge upstream/main`. Everything the fork adds lives in **git submodules under `ivp/src/`** (`moos-ivp-tak`, `pRedirectWaypoint`, `uXboxJoystick`, `uGfxMask`), each its own GitHub repo with its own README. Upstream files are modified in two places only: `ivp/src/CMakeLists.txt` (one hunk, registers the submodule apps) and `ivp/src/pMarineViewer/` (the MCTF hotkeys in `PMV_GUI.cpp`, the chat pane in `PMV_GUI.*`, `PMV_MOOSApp.*`, `PMV_Info.cpp` plus the fork's own `PMV_ChatInput.h` and `PMV_ChatSplitter.h`, and the `VIEW_RING` vehicle ring in `PMV_Viewer.*`, `PMV_MOOSApp.cpp`, `PMV_Info.cpp`). Keep it that way so upstream merges stay clean. `local-patches/` records deliberate edits to upstream files that must be re-applied after a merge that touches them.

After cloning or pulling: `git submodule update --init --recursive`. Empty submodule dirs fail at CMake configure time.

## Build

```bash
./build.sh                 # full build: build-moos.sh then build-ivp.sh (-m / --minrobot for headless)
./build-ivp.sh             # IvP tree only; re-run after any CMakeLists.txt change or file add/remove
./build-ivp.sh pFoo        # single target (unrecognized args pass through to make)
cd build/ivp && make pFoo  # same thing, skips the cmake step
./build.sh --clean         # wipes build/ bin/ lib/ include/
./build-check.sh           # asserts expected binaries exist; its app list is hard-coded, add new apps to it
```

Outputs: executables in `bin/`, static libs in `lib/`, `lib_*` headers auto-copied to `include/ivp/`. `bin/` must be on `PATH` because pAntler launches apps by name. Extra CMake defines go through the `IVP_CMAKE_FLAGS` env var.

## Tests

```bash
./build-utests.sh                                   # builds ivp/src_unit_tests into bin/
cd ivp/src_unit_tests && ./alltest.sh               # runs every dir that has a cases.utf
cd ivp/src_unit_tests/testConvexHull && utest cases.utf -v   # one test
```

The framework is homegrown: the `utest` runner drives table-driven `cases.utf` files; a `.skip_test` marker makes a dir non-fatal. No gtest/catch2. CI (`.github/workflows/build.yml`) runs `build.sh`, `build-check.sh`, `build-utests.sh`, and `alltest.sh` on Ubuntu 24.04 and macOS for pushes to `main` and `llm-integration`. It checks out submodules recursively; the private ones need the repository secret `SUBMODULE_TOKEN`, a fine-grained PAT with contents read access to the fork and to `moos-ivp-llm`, `moos-ivp-bt`, `moos-ivp-cap`, `moos-ivp-squad`, `moos-ivp-dyn` and `moos-ivp-panel` (a submodule the PAT does not cover fails every job at checkout with a 403). The offline self-tests `bin/cap_selftest`, `bin/bt_selftest`, `bin/llm_selftest` and `bin/squad_selftest` are not run by CI.

## Architecture

**Two layers.** `MOOS/` (symlink to `MOOS_Jul2724/`) is the publish/subscribe middleware: a `MOOSDB` per community plus apps that publish and subscribe named variables. `ivp/src/` is the IvP helm (`pHelmIvP`, behaviors that emit interval-programming objective functions) plus roughly 130 apps and the `lib_*` libraries they share.

**App anatomy.** One directory per app under `ivp/src/`, prefixed `p` (process), `u` (utility), `i` (hardware interface), `uFld` (shoreside), `app_` (non-MOOS CLI). Modern apps subclass `AppCastingMOOSApp` and follow a fixed six-file layout: `main.cpp`, `Foo.h`/`Foo.cpp`, `Foo_Info.h`/`Foo_Info.cpp` (help, `-e` example config, `-i` interface), `CMakeLists.txt`. The lifecycle contract: `OnStartUp` parses the `ProcessConfig = pFoo` block via `m_MissionReader.GetConfiguration(GetAppName(), ...)` and reports unhandled params; `OnConnectToServer` calls `registerVariables`; `OnNewMail` dispatches on `msg.GetKey()` with the `key != "APPCAST_REQ"` unhandled-mail fallthrough; `Iterate` is bracketed by `AppCastingMOOSApp::Iterate()` and `PostReport()`; `buildReport` writes into `m_msgs` (use `ACTable` for tables). `ivp/src/pDeadManPost` is the cleanest reference.

**Registration is list-based.** Do not add `add_subdirectory` calls. Add the directory name to `ROBOT_APPS` (always built, including headless), `IVP_NON_GUI_APPS`, or `IVP_GUI_APPS` in `ivp/src/CMakeLists.txt`; nested paths such as `moos-ivp-tak/pCoTBridge` work. Libraries go in `IVP_NON_GUI_LIBS`; the CMake target name drops the `lib_` prefix (`lib_mbutil` becomes `mbutil`). A minimal AppCasting app links `${MOOS_LIBRARIES} apputil mbutil m pthread`.

**Scaffolding.** `cd ivp/src && ../../scripts/GenMOOSApp_AppCasting Foo p "Author"` generates the six files, but it does not register the app, stamps a bogus date, uses the 2-arg `Run()` (use the 4-arg `Run(run_command, mission_file, argc, argv)` form), and ships uFldNodeComms boilerplate in `Foo_Info.cpp`. Fix those against `pDeadManPost`. Add the app's config keywords to `editor-modes/moos-apps.el`.

**Missions.** `ivp/missions/<name>/` holds `<name>.moos` (an `ANTLER` block of `Run = pFoo @ NewConsole = false` lines plus one `ProcessConfig = pFoo {}` block per app), `<name>.bhv`, `launch.sh [time_warp]`, and `clean.sh`. `s1_alpha` is the minimal single-vehicle sim; `s1_alpha_cot_test` exercises the fork's TAK chain and needs its `pCoTBridge` host and certificate paths edited first.

**Hard constraints.**
- C++11 only, compiled with `-Wall -Wextra -pedantic`. Wrap vendored headers as `SYSTEM` includes if they warn.
- Nothing in the tree uses `std::thread`. Background work uses MOOS `CMOOSThread` + `SafeList` (`lib_genutil/MOOSAppRunnerThread` is the pattern). Never block inside `Iterate()`.
- There is no HTTP client and no general JSON parser in the tree; `lib_mbutil/JsonUtils` only converts flat `{"k":"v"}` to MOOS comma-separated pairs. OpenSSL is already a hard dependency of the default build via `moos-ivp-tak` (`pCoTBridge/CoTBridge.cpp` is a raw TLS client with reconnect logic). Both Dockerfiles under `docker/` and the Ubuntu CI job install `libssl-dev` and `libcurl4-openssl-dev`; the macOS CI job relies on the system libcurl and brew for the rest. Add any new system dependency in all three places.

**Style.** 2-space indent, `m_` member prefix, `//-----` banner with `// Procedure: Name` above each method, parenthesized `return(x);`.

## LLM integration (branch `llm-integration`)

Six submodules under `ivp/src/`, each with the README that is its reference:
- `moos-ivp-llm`: `lib_llm` and `pLLMAgent`, the operator-chat agent (tool grammar, MOOS interface, confirmation flow, prompt and tool-count briefing in its README).
- `moos-ivp-bt`: `lib_bt` and `pBehaviorTree`, the plan executor, per vehicle and in squad mode on the shoreside; `pBehaviorTree --check=<file> [--squad --roster=abe,ben]` validates a plan offline.
- `moos-ivp-cap`: the capability files, one per tool and plan leaf, in sets a mission picks with `capability_dir` / `capability_keep` / `capability_drop`.
- `moos-ivp-squad`: `lib_squad` and `uFldSquad`, squads as objects with formations around a virtual leader.
- `moos-ivp-dyn`: `lib_dyn` and `uDynamicsTest`, the measured vehicle dynamics that reach the agent's prompt as facts.
- `moos-ivp-panel`: `uButtonPanel`, the operator's button panel (its own FLTK window) over the mission's `buttons.txt`; the `make_button` tool (in moos-ivp-bt's capabilities) saves buttons there and pLLMAgent runs their plans on a press. The file's reader and writer, `ButtonFile`, is in `lib_cap`.

Fork-side: the pMarineViewer chat pane (the only upstream edits besides `ivp/src/CMakeLists.txt`; `local-patches/` records any other deliberate upstream edit), `ivp/missions/s1_alpha_llm/` (one vehicle) and `ivp/missions/m2_alpha_llm/` (fleet, squads, contact set; its README explains the bridging and the roster variables; `test/` holds the scripted chat test).

Rules: `ANTHROPIC_API_KEY` comes from the environment and never goes in a mission file. Keep a mission's tool set to what it needs: every tool costs prompt tokens each turn and the API marks at most 20 tools strict. Offline checks: `bin/llm_selftest`, `bin/bt_selftest`, `bin/cap_selftest`, `bin/squad_selftest` (not run by CI), then the headless fleet, then the owner's live run.

## Working in this repo

- Commit and push only when the owner says so; never on your own initiative. No `Co-Authored-By` or "Generated with" lines in commits or PRs.
- Absolute paths and `git -C <dir>` in shell commands; a `cd` inside a script is fine, a `cd` in the command itself is not.
- Build and verify each piece before the next: library self-test, then the app headless on a scratch fleet, then the next piece. Say plainly what was verified and how, and what was not; a headless run is called headless.
- Anything that changes vehicle behaviour (helm behaviours, formations, avoidance) gets one or two headless attempts at most, then a launch-and-watch recipe for the owner, who observes the viewer and proposes fixes; read the behaviour's documentation and measure the geometry before redesigning.
- Fixes go one at a time through the `fix-review` skill: findings with evidence first, each fix explained in plain terms and approved or denied before it is built.
- The shipped example missions stay minimal (m2_alpha_llm: one squad, two members in its examples); generality lives in code, tests and READMEs. A mission's tool menu holds only what it needs.
- Reads under this directory need no permission; writes to upstream source (anything outside the submodules, `ivp/src/CMakeLists.txt`, the fork-owned parts of pMarineViewer and `local-patches/`) are asked about first.

## Skills

`.claude/skills/` holds the repo's procedures as Claude Code skills, invoked by name: `fix-review` (how a review and its fixes are run), `review-run` (read a live run's logs), `headless-fleet` (scratch fleet on the 9100 ports, with `fleet.sh`), `commit-all` (submodules first, fork last, no attribution lines, then CI), `chat-test` (the scripted chat test, headless or with the viewer). Prefer them over re-deriving the steps. `.claude/hooks/` holds the hooks `.claude/settings.json` enables: `fleet_check.sh` (Stop) refuses to end a turn while a scratch fleet is still up on the 9100 ports with no running test owning it (`fleet.sh up` and the chat driver record their owner's PID in the scratch dir's `.driver`), until it is shut down or the reply says why it stays up.

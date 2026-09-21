# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

West Point Robotics Research Center fork of MOOS-IvP, a C++11/CMake marine-autonomy stack. `origin` is `tylerwp2022/moos-ivp`; `upstream` is `moos-ivp/moos-ivp` and is merged with `git fetch upstream && git merge upstream/main`. Everything the fork adds lives in **git submodules under `ivp/src/`** (`moos-ivp-tak`, `pRedirectWaypoint`, `uXboxJoystick`, `uGfxMask`), each its own GitHub repo with its own README. Only two upstream files are modified (one hunk each): `ivp/src/CMakeLists.txt` (registers the submodule apps) and `ivp/src/pMarineViewer/PMV_GUI.cpp` (MCTF hotkeys). Keep it that way so upstream merges stay clean. `local-patches/` records deliberate edits to upstream files that must be re-applied after a merge that touches them.

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

The framework is homegrown: the `utest` runner drives table-driven `cases.utf` files; a `.skip_test` marker makes a dir non-fatal. No gtest/catch2. CI (`.github/workflows/build.yml`) runs `build.sh`, `build-check.sh`, `build-utests.sh`, and `alltest.sh` on Ubuntu 24.04 and macOS for pushes to `main` and `llm-integration`. It checks out submodules recursively; the private ones need the repository secret `SUBMODULE_TOKEN`, a fine-grained PAT with contents read access to the fork and to `moos-ivp-llm`, `moos-ivp-bt` and `moos-ivp-cap`. The offline self-tests `bin/cap_selftest`, `bin/bt_selftest` and `bin/llm_selftest` are not run by CI.

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

`ivp/src/moos-ivp-llm/` (submodule) holds `lib_llm` and `pLLMAgent`, the operator-chat agent; its README documents the `tool=` grammar, the MOOS interface, and the confirmation flow. The pMarineViewer chat pane is the fork-side half (`chat_viewable`, `chat_width`, `chat_*_var` params; `LLM_CHAT_IN` / `LLM_CHAT_OUT` / `LLM_STATUS`). `bin/llm_selftest` is the offline check for the library; `ivp/missions/s1_alpha_llm/` is the runnable example and needs `ANTHROPIC_API_KEY` in the environment. The API key never goes in a mission file.

# Commands and artifacts

This page describes the committed WSL launcher. It does not describe the older workspace-level `setup/Project.ps1` wrapper.

The [first command tutorial](../tutorials/first-command.md) covers both the local verification and live Alpha.

## Actions

Run the launcher from the Windows repository root:

```powershell
.\scripts\wsl\Project.ps1 -Action <action>
```

| Action | Behavior |
|---|---|
| `Build` | Copy committed source into the Linux installation and build it. Does not fetch newer Git revisions. |
| `Demo` | Start one simulation and a local Messages-protocol stand-in. Default action when omitted. |
| `Live` | Run the checked-in Alpha mission in the foreground using the OpenAI API and the selected desktop chat window. Press Ctrl+C in that terminal to stop it. |
| `Verify` | Run available self-tests and four headless command-flow checks. Refuse an active demo. |
| `Status` | Print the saved state as JSON, or `null` if no state exists. |
| `Stop` | Stop recorded process groups with matching process identities. Retain logs. |
| `Shell` | Open an interactive Linux shell with project binary and library paths. |

The PowerShell wrapper throws when its WSL command returns a nonzero status. The Python verifier returns `0` for a passing result list, `1` for recorded failures, and `2` when an active demo blocks verification. An uncaught startup or test-process error can also terminate the command; inspect the terminal output if no final JSON was written.

## Parameters

| Parameter | Default | Meaning |
|---|---|---|
| `-Distribution` | `Ubuntu` | Installed WSL distribution name. |
| `-InstallRoot` | `~/Projects/moos-ivp-wsl` in Linux | Absolute Linux installation path when supplied. Use it consistently. |
| `-Port` | `19841` | MOOSDB port for the scripted runtime. The local API uses the next port. `Live` reads `ServerPort` from the checked-in `alpha.moos`. |
| `-Headless` | Off | Omit the viewer and button panel for `Demo` or `Live`. `Verify` is always headless. |
| `-ChatViewer` | `pmarineviewer` | For a GUI `Demo` or `Live`, use `umacview` to open chat in uMACView and keep pMarineViewer open for the map. |
| `-WithoutSquad` | Off | Omit squad during `Build`. |
| `-MctfSource` | None | Existing Windows MCTF checkout to include during `Build`. |

`Live` reads `OPENAI_API_KEY` from the PowerShell process environment and uses the model in `alpha.moos`. `Demo` and `Verify` use the local scripted endpoint. `Status` and `Stop` address the scripted runtime's saved state.

The Linux build reads `MOOS_IVP_BUILD_JOBS`, with a default of `8`. The runtime reads `MOOS_IVP_WSL_ROOT` and `MOOS_IVP_WSL_PORT`; the PowerShell wrapper supplies the latter settings.

## Artifacts

Paths below are relative to the Linux install root.

| Path | Contents and limits |
|---|---|
| `source-manifest.json` | Base commit, submodule commit map, squad inclusion, and optional MCTF commit. Does not record all subsequent local edits. |
| `verification/verification.json` | Test name, pass value, exit status; timing for self-tests and conditions for simulator checks. Can be replaced by a later verification. |
| `verification/*_selftest.log` | Captured output from each invoked component suite. |
| `verification/smoke-*.log` | Output of the simulator condition queries. |
| `runs/alpha-*/alpha.moos` | Generated runtime mission, including the local endpoint and selected port. |
| `runs/alpha-*/antler.log` | Application launcher output. |
| `runs/alpha-*/startup-query.log` | Agent readiness query output. |
| `runs/alpha-*/standin.log` | Local endpoint server output. |
| `runs/alpha-*/standin/request-*.json` | Requests received by the scripted endpoint. |
| `runs/current.json` | Recorded run directory, headless flag, chat viewer, ports, PIDs, and process start identities. Removed after a successful stop. |

The scripted runtime copies the source mission into each run directory. `Live` runs directly from the source mission directory, where pLogger saves the normal MOOS run logs.

## Verification conditions

| Check | Exact condition | What it establishes |
|---|---|---|
| Position publication | `NAV_X >= 0` | The query observed a position value that met this condition. |
| Approval request | `LLM_STATUS = awaiting_confirm` | The scripted proposal reached the approval state. |
| Movement after approval | `NAV_X > 3` | The simulated x-coordinate passed this threshold after `y` was submitted. |
| Behavior-tree post | `SETUP_BT = passed` | The test tree's delayed `Post` reached MOOSDB. |

The standard verifier runs six suites: capability, field, behavior-tree, dynamics, history, and LLM. If the MCTF binaries exist, it also runs interception, return, and test-mode suites. It does not run `squad_selftest` or the timestamp-parser regression; those were separate checks in the [dated evidence](../evidence/2026-11-20-dev.md).

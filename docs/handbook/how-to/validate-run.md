# Validate and retain a run

Use this procedure when you need evidence that a particular source version passed the local command-flow checks.

You need a built installation, free ports, and permission to retain its mission data. The test uses a simulation and a scripted local endpoint.

## Run the validation

From the Windows repository root, run:

```powershell
.\scripts\wsl\Project.ps1 -Action Stop
.\scripts\wsl\Project.ps1 -Action Verify
```

Use your selected `-Distribution`, `-InstallRoot`, and `-Port` on both commands. `Verify` refuses to replace an active demo. It does not stop unrelated missions.

Read the printed results. If any check fails, retain its log and the failure status. Do not remove failed checks from the result list.

## Record the source and outputs

Open the project shell:

```powershell
.\scripts\wsl\Project.ps1 -Action Shell
```

In Linux, run:

```bash
cat "$MOOS_IVP_WSL_ROOT/source-manifest.json"
git -C "$MOOS_IVP_WSL_ROOT/moos-ivp" status --short
git -C "$MOOS_IVP_WSL_ROOT/moos-ivp" submodule status
cat "$MOOS_IVP_WSL_ROOT/verification/verification.json"
```

If the source has local edits, retain their diff and identify them in the report. A commit ID alone does not identify a modified source tree. Record changes inside each modified submodule as well.

Copy these items into the evidence package:

- `source-manifest.json` and the source-status output.
- The complete `verification/` directory.
- The `runs/alpha-*` directory printed by the validation.
- The command, environment versions, date, selected root, and port.
- Expected results, observed results, failures, and limitations.

The `verification/` files can be replaced by the next verification. Retain them before another run. Run directories have separate names.

Inspect a package before sharing it. A live-provider run can contain operator messages, mission state, and model responses. The public website build includes only the handbook directory; it does not collect runtime logs.

## State the result precisely

Use the tested conditions from [command reference](../reference/commands.md#verification-conditions). Separate build success, local runtime success, independent reproduction, and field results.

Do not update a validation date because its description changed. The [November 20 record](../evidence/2026-11-20-dev.md) is an example of a bounded evidence record.

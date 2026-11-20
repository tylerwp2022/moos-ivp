# Resolve setup failures

Use the symptom and recovery table before restarting a run. Retain its logs before you change the setup.

| Symptom | Check and recovery |
|---|---|
| The WSL distribution is not found | Run `wsl --list --verbose`. Supply the exact name with `-Distribution`. |
| `Repository not found` or a submodule checkout fails | Confirm the repository URL and your account's access. Use the HTTPS conversion in the install guide if SSH is unavailable. |
| Only squad access is missing | Omit that submodule and build with `-WithoutSquad`. Other required private components still need access. |
| The Linux checkout is at another commit | Select a new `-InstallRoot`. The build refuses to reset an existing checkout. |
| A Windows source edit has no effect | Build copies committed source. Commit the intended change on your contribution branch, then select a corresponding Linux checkout. |
| A port is occupied | Select an unused `-Port N`; the API also needs `N+1`. Use the same values for every action. Do not stop an unrelated process. |
| `Verify` reports an active demo | Run `Stop` for that installation and port. Run `Verify` again after the listeners close. |
| The simulator does not become ready | Read `startup-query.log` and `antler.log` in the printed run directory. Confirm the binaries and libraries are from the selected build. |
| The map window does not appear | Confirm WSLg is available. Use `Demo -Headless` or `Verify` to separate GUI problems from runtime problems. |
| A chat response is fixed or repetitive | The local demo is scripted. Only `setup smoke goto` requests its demonstration move. |
| `Stop` says ports remain occupied | Read the retained state and logs. Retry `Stop` only for the same installation. The script retains state when it cannot confirm listener release. |
| Full MCTF launch reports missing applications | The full match needs squad and additional Aquaticus applications. An optional MCTF build alone does not provide them. |

## Find the relevant record

Run `Status` to obtain the current demo state:

```powershell
.\scripts\wsl\Project.ps1 -Action Status
```

`Status` reads the saved launcher state. It is not a complete application-health probe. A retained record can outlive a failed process.

The [artifact reference](../reference/commands.md#artifacts) identifies the logs. For a report, include the exact error, command, source identity, and observed result. Keep credentials out of the report.

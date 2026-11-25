Windows setup
Updated: 2026-11-24 - Timeo Williams

The tested Windows development path for this fork is Ubuntu 24.04 on WSL2,
with WSLg displaying the viewer and button panel on the Windows desktop.
The complete integrated stack has not been validated as native Windows binaries.

Use WSLg's provided display environment for this path. A separate X server and
manual DISPLAY overrides are not part of this setup.

Start with the maintained installation guide for prerequisites, private-submodule
access, dependencies, and building on the Linux filesystem:
  https://github.com/tylerwp2022/moos-ivp/blob/dev/docs/handbook/how-to/install-wsl.md

Use dev for development. To reproduce the handbook's recorded reference run,
use its exact base revision and pinned submodule commits. Do not substitute
newer component revisions for that reference run.

After completing installation, run these from the Windows repository root:

  .\scripts\wsl\Project.ps1 -Action Build
  .\scripts\wsl\Project.ps1 -Action Verify
  .\scripts\wsl\Project.ps1 -Action Demo
  .\scripts\wsl\Project.ps1 -Action Stop

Verify requires the demo to be stopped. If a demo is already running, use Stop
before Verify. Keep any selected -Distribution, -InstallRoot, and -Port options
consistent across commands, as described in the launcher reference.

Demo uses a local scripted endpoint, not a live model service. It needs no API
key. In the viewer's chat pane, enter setup smoke goto, then y to approve the
simulated move. See the first-command tutorial for the checks and their limits:
  https://github.com/tylerwp2022/moos-ivp/blob/dev/docs/handbook/tutorials/first-command.md

IVP_BUILD_SQUAD defaults to ON. If squad access is unavailable, follow the
installation guide's selective-submodule instructions and add -WithoutSquad to
Build. This supports the single-vehicle setup; a full fleet match still needs
its required components and repository access.

The committed launcher is scripts/wsl/Project.ps1. It does not provide -Live or
-Provider options; workspace-specific wrappers are not part of this quickstart.
Use Shell to open Ubuntu with the project binary and library paths loaded:

  .\scripts\wsl\Project.ps1 -Action Shell

Launcher options, retained logs, and source-manifest details:
  https://github.com/tylerwp2022/moos-ivp/blob/dev/docs/handbook/reference/commands.md

See docs/handbook/reference/versions.md for the recorded validation baseline,
native-Windows and fresh-distribution limits, and optional MCTF dependencies.

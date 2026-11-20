# Windows development with WSL2

This fork's integrated viewer and vehicle simulation run as Linux executables in
WSL2. Windows displays the FLTK viewer and button panel through WSLg. These
instructions do not establish native MSVC/MinGW support: common utility code,
mission scripts, and some tests depend on POSIX facilities.

The workflow was checked with Ubuntu 24.04, GCC 13.3, CMake 3.28, and WSL2/WSLg.
Use the `dev` branch, which registers the capability, LLM,
behavior-tree, dynamics, panel, and history extensions.

## Prerequisites

Install WSL2 and an Ubuntu distribution using Microsoft's WSL installation
instructions. In PowerShell, `wsl --list --verbose` should show Ubuntu using
version 2. Inside Ubuntu, install the build dependencies:

```bash
sudo apt-get update
sudo apt-get install build-essential cmake ninja-build git python3 \
  libfltk1.3-dev freeglut3-dev libpng-dev libjpeg-dev libtiff-dev \
  libxft-dev libxinerama-dev libcurl4-openssl-dev libssl-dev libsdl2-dev
```

On Windows, install Git and authenticate it for the private repositories.
Git Credential Manager or `gh auth setup-git` can supply the existing GitHub
login. The scripts do not copy authentication tokens into WSL.

## Fetch source and submodules on Windows

Clone the integrated branch, or use an existing checkout:

```powershell
git clone --branch dev https://github.com/tylerwp2022/moos-ivp.git
cd moos-ivp
git submodule update --init --recursive
```

If you do not have access to `moos-ivp-squad`, initialize the other submodules
instead, then pass `-WithoutSquad` to Build:

```powershell
$modules = git config -f .gitmodules --get-regexp '\.path$' |
    ForEach-Object { ($_ -split '\s+', 2)[1] } |
    Where-Object { $_ -ne 'ivp/src/moos-ivp-squad' }
git submodule update --init --recursive -- $modules
```

Other required private submodules still need access. Skipping squad enables the
single-vehicle demo; it does not provide squad coordination for fleet missions.

## Build in the Linux filesystem

From the Windows repository root:

```powershell
.\scripts\wsl\Project.ps1 -Action Build
# If squad was intentionally omitted:
.\scripts\wsl\Project.ps1 -Action Build -WithoutSquad
```

The scripts create working copies under `~/Projects/moos-ivp-wsl` in Ubuntu,
using Git objects already fetched on Windows. They reconstruct Unix symlinks and
LF line endings rather than running directly from an NTFS checkout. Linked
Windows Git worktrees are supported. CMake builds the core, essentials,
MOOSGeodesy, available extensions, and GUI. MOOSGeodesy may download the pinned,
checksum-verified PROJ dependency configured by this repository.

This copies the **committed** base revision and each pinned submodule revision;
uncommitted Windows edits are not copied. Subsequent builds reuse Linux working
copies and preserve their edits. If their HEAD differs from the source revision,
the script refuses to reset them: update them explicitly, or select another
`-InstallRoot`. `source-manifest.json` records the revisions used.

`-InstallRoot` takes an absolute Linux path. `-Distribution` defaults to Ubuntu;
the named distribution must already be installed. For example:

```powershell
.\scripts\wsl\Project.ps1 -Action Build -WithoutSquad `
    -Distribution Ubuntu -InstallRoot /home/your-user/Projects/moos-test
```

Keep the same InstallRoot on subsequent Demo, Verify, Stop, Status, and Shell
commands. `MOOS_IVP_BUILD_JOBS` in WSL controls parallelism (default 8).

## Run the local single-vehicle demo

```powershell
.\scripts\wsl\Project.ps1 -Action Demo
.\scripts\wsl\Project.ps1 -Action Status
.\scripts\wsl\Project.ps1 -Action Stop
```

Demo starts a local simulated boat, the map/chat viewer, and `uButtonPanel`.
Its LLM endpoint is a **scripted loopback stand-in**, not a real model service.
No real API key is needed or sent. The boat begins idle. In the chat pane, type
`setup smoke goto`, then `y` to approve a move to `(20,-20)`. Other messages get
a fixed explanatory response.

Each launch receives a separate `runs/alpha-*` directory under InstallRoot;
logs, local API requests, and mission files stay there. MOOSDB uses port 19841
and the loopback stand-in uses 19842. `-Port N` chooses N and N+1 for another
isolated run; use the same Port with all commands for that installation.
`-Headless` omits the viewer and button panel. Stop targets only the process
groups recorded by this launcher, checks process start times to avoid reused
PIDs, waits briefly for the recorded ports to be released, and retains the logs.

For an interactive Ubuntu shell with the binary and library paths loaded:

```powershell
.\scripts\wsl\Project.ps1 -Action Shell
```

This does not edit the global Windows PATH or the user's `.bashrc`.

## Verification

Stop a running demo first, then:

```powershell
.\scripts\wsl\Project.ps1 -Action Verify
```

Verify runs the existing capability, field, behavior-tree, dynamics, history,
and LLM self-tests, then launches its own headless simulation. It checks that
navigation is published, an LLM tool proposal waits for approval, approval moves
the simulated boat, and a behavior tree posts through MOOSDB. It refuses to
replace an existing demo. Results and per-check logs are retained in the Linux
`verification/` directory. A failing suite keeps the command's exit status
nonzero even when the live simulation succeeds.

The `dev` integration includes the `getLogStart()` timestamp buffer fix and its
regression tests. The setup scripts do not apply a second copy of that patch.

## Optional MCTF build

An existing Windows MCTF checkout can be included:

```powershell
.\scripts\wsl\Project.ps1 -Action Build -WithoutSquad -MctfSource ..\moos-ivp-mctf
```

Verify then includes its interception, return-planning, and test-mode self-tests.
The full multi-vehicle match additionally requires the squad submodule and the
correct Aquaticus repository providing `pAquaticusStateMgr`, `pRangeEvent`, and
`pNodeReportParse`. Building the available MCTF applications does not establish
that the complete match is ready. Confirm the Aquaticus URL/access with the
mission maintainer.

A real LLM run requires a supported model identifier and a key supplied to the
WSL process environment. TAK connectivity needs its own server/certificates.
Those external services and real vehicle hardware are outside the local demo.

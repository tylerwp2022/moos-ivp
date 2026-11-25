# Install on Windows with WSL2

Use this procedure to build the documented single-vehicle simulation. The runtime uses Linux executables. WSLg displays the optional desktop windows.

## Prerequisites

- Windows with WSL2 and WSLg support.
- An Ubuntu 24.04 distribution. The launcher defaults to the name `Ubuntu`; use `-Distribution` if its name differs.
- Windows Git and access to the required repositories. Some submodules require partner access.
- Network access for repository and dependency downloads.
- Space for a Linux source tree and build output. No measured minimum disk or memory requirement has been established.

If WSL is absent, use [Microsoft's installation instructions](https://learn.microsoft.com/windows/wsl/install). In PowerShell, confirm the distribution name and version:

```powershell
wsl --list --verbose
```

The selected Ubuntu distribution must show version `2`. The recorded environment used GCC 13.3 and CMake 3.28. A fresh-distribution install remains unverified.

## Install Linux dependencies

Open the selected Ubuntu distribution. Run:

```bash
sudo apt-get update
sudo apt-get install build-essential cmake ninja-build git python3 \
  libfltk1.3-dev freeglut3-dev libpng-dev libjpeg-dev libtiff-dev \
  libxft-dev libxinerama-dev libcurl4-openssl-dev libssl-dev libsdl2-dev
```

## Obtain the source

In PowerShell, change to a parent directory for the Windows checkout. Clone `dev`:

```powershell
git clone --branch dev https://github.com/tylerwp2022/moos-ivp.git
cd moos-ivp
```

To reproduce the dated November 20 reference run, select its exact commit. For the current live Alpha setup, stay on the branch you cloned.

```powershell
git checkout --detach cf3a853835e72d126b6abf8cd5a29930a34a3e0f
```

This commit belongs to `dev`. A detached checkout preserves the reference source even when `dev` advances. For development, use `git switch dev` in a separate checkout or after you finish the reference run.

Authenticate Windows Git for the required repositories. The submodule URLs use SSH. If your authentication uses Git Credential Manager over HTTPS, use this command-scoped URL conversion:

```powershell
git -c 'url.https://github.com/.insteadOf=git@github.com:' submodule update --init --recursive
```

If you have SSH access instead, use:

```powershell
git submodule update --init --recursive
```

If only squad access is unavailable, initialize the other modules:

```powershell
$modules = git config -f .gitmodules --get-regexp '\.path$' |
    ForEach-Object { ($_ -split '\s+', 2)[1] } |
    Where-Object { $_ -ne 'ivp/src/moos-ivp-squad' }
git -c 'url.https://github.com/.insteadOf=git@github.com:' submodule update --init --recursive -- $modules
```

Omitting squad does not remove the access requirements for other submodules. If a required repository is unavailable, stop and obtain access.

## Build on the Linux filesystem

From the Windows repository root, run:

```powershell
.\scripts\wsl\Project.ps1 -Action Build
```

If you omitted squad, run this command instead:

```powershell
.\scripts\wsl\Project.ps1 -Action Build -WithoutSquad
```

The build copies committed Git objects to `~/Projects/moos-ivp-wsl` in Ubuntu. It reconstructs Linux symlinks and line endings. It builds the core, extensions, and GUI. MOOSGeodesy can download its checksum-verified PROJ dependency.

Uncommitted Windows source edits are not copied. An existing Linux checkout at another revision causes a failure. Select a new absolute Linux install path to keep both versions:

```powershell
.\scripts\wsl\Project.ps1 -Action Build -InstallRoot /home/your-user/Projects/moos-reference
```

Replace `your-user` with the Ubuntu account name. Retain the same `-InstallRoot` for subsequent commands. Do not reset another checkout to make the build proceed.

## Confirm the outcome

A successful build prints its Linux root. The root contains `source-manifest.json`, `moos-ivp/bin/`, and `moos-ivp/lib/`.

Run [your first simulated command](../tutorials/first-command.md), then use [live Alpha](../tutorials/first-command.md#run-live-alpha) to try OpenAI from either desktop viewer.

For the optional MCTF build and full-match constraints, see [component status](../reference/versions.md#optional-mctf).

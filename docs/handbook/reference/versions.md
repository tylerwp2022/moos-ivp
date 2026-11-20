# Source versions and status

## Development source

Use `dev` for our contributions. Tyler maintains `main`. Component development also uses `dev`; the base repository retains exact submodule pins.

A website build and a runtime validation identify different artifacts. The website can change without a runtime retest. Its generated `build-info.json` identifies the website source and build time.

## Recorded runtime baseline

The November 20 validation used base commit:

```text
cf3a853835e72d126b6abf8cd5a29930a34a3e0f
```

The complete [source manifest](../evidence/source-manifest-2026-11-20.json) contains every submodule pin and the optional MCTF commit. The [validation record](../evidence/2026-11-20-dev.md) identifies the actual checks and their limits.

| Capability | Current evidence |
|---|---|
| Ubuntu 24.04 under WSL2 | Clean build directory and headless checks passed in an existing distribution. |
| Windows native binaries | Not established. The documented application path uses Linux executables. |
| Fresh WSL distribution | Installation procedure documented; independent clean-distribution test not recorded. |
| Scripted local endpoint | Approval, movement threshold, and behavior-tree post passed. |
| Live model services | Configuration is implemented; this baseline's stand-in evidence does not verify a live service. |
| GUI walkthrough | Available through WSLg; not included in this baseline's headless evidence. |
| Field hardware or TAK service | Not verified by this documentation effort. |

## Optional MCTF

MCTF is a separate repository. For the recorded revision, obtain its `dev` source and select the recorded commit:

```powershell
git clone --branch dev https://github.com/tylerwp2022/moos-ivp-mctf.git ..\moos-ivp-mctf
git -C ..\moos-ivp-mctf checkout --detach 776b0b482bbc646a36e794f231cdd66497fd7ea8
.\scripts\wsl\Project.ps1 -Action Build -MctfSource ..\moos-ivp-mctf
```

Run these from the Windows base repository root. Retain any selected distribution or install-root options. This adds compilation and the optional self-tests. It does not launch a full match.

The full match also needs squad and the correct Aquaticus source for `pAquaticusStateMgr`, `pRangeEvent`, and `pNodeReportParse`. Earlier access checks did not establish that dependency. Obtain its correct URL and access from the mission maintainer before treating full-match instructions as reproducible.

The workspace's Monte Carlo folder contains an analyzer and an empty study manifest, not completed trials or a general trial runner. It is not part of this website's reproducible installation. No experiment performance claim is made here.

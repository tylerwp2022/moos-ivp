# MOOS-IvP

> **Note:** This is a modified fork of [MOOS-IvP](https://moos-ivp.org/) maintained by the
> West Point Robotics Research Center. It adds TAK/ATAK integration, MCTF (Maritime
> Capture-the-Flag) support apps, and operator-control utilities on top of the upstream
> tree. See [West Point Modifications](#west-point-modifications) below. All upstream
> documentation still applies.

[MOOS-IvP](https://moos-ivp.org/) is a set of open source C++ modules for providing autonomy on robotic platforms, in particular autonomous marine vehicles.

## Installation

To install MOOS-IvP from source, clone this repository and follow the setup, dependency, build, and environment instructions for your platform:

* [GNU/Linux](./README-GNULINUX.txt)
* [macOS](./README-OS-X.txt)
* [Windows](./README-WINDOWS.txt)

**Cloning this fork:** the added applications live in git submodules, so clone with:

```bash
git clone --recurse-submodules git@github.com:tylerwp2022/moos-ivp.git
```

If you cloned without `--recurse-submodules` (or after pulling updates), populate them with:

```bash
git submodule update --init --recursive
```

Without this step the submodule directories under `ivp/src/` will be empty and the build will fail at configure time.

## West Point Modifications

### Added applications (submodules)

Four repositories are vendored as submodules under `ivp/src/` and wired into the main build:

| Submodule | Contents | Purpose |
|---|---|---|
| `moos-ivp-tak` | `pCoTBridge`, `pCoTCommander`, `pCoTGraphics`, `pCoTChat`, `pCoTContact`, `pCoTShoreContact`, `lib_cot_geodesy` | Bidirectional MOOS ↔ TAK integration over Cursor-on-Target (CoT). Vehicle position reporting to TAK, ATAK operator waypoint commands into pHelmIvP, VIEW_* graphics mirroring onto the ATAK map, and GeoChat bridging. |
| `pRedirectWaypoint` | `pRedirectWaypoint` | Operator-driven vehicle redirect: select a team/vehicle and click a new waypoint from the shoreside viewer (driven by the `RDR_*` hotkeys added to pMarineViewer, below). |
| `uXboxJoystick` | `uXboxJoystick` | Shoreside Xbox-controller teleop for MCTF vehicles. |
| `uGfxMask` | `uGfxMask` | Graphics masking utility for shoreside display. |

Each submodule carries its own README with per-app configuration details; this section documents only how they integrate into the tree.

### Build system changes (`ivp/src/CMakeLists.txt`)

* `moos-ivp-tak/lib_cot_geodesy` added to `IVP_NON_GUI_LIBS`. This library provides local-XY ↔ WGS84 conversion for the CoT apps (MOOSGeodesy UTM projection with a flat-earth NAV fallback).
* The following apps added to `ROBOT_APPS`, so they build as part of the normal tree build (`./build.sh`) with no separate build step: `pCoTBridge`, `pCoTCommander`, `pCoTGraphics`, `pCoTChat`, `pCoTContact`, `pCoTShoreContact`, `pRedirectWaypoint`, `uXboxJoystick`, `uGfxMask`.

### pMarineViewer hotkeys (`ivp/src/pMarineViewer/PMV_GUI.cpp`)

Keyboard shortcuts added to `PMV_GUI::handle()` for MCTF operation. Each keypress posts a MOOS variable consumed by `pRedirectWaypoint` (`RDR_*`) or the autotag logic (`AUTOTAG_*`); toggle-style posts carry a `MOOSTime()` timestamp as their value.

| Key | Variable posted | Function |
|---|---|---|
| `b` | `RDR_SEL_TEAM=blue` | Select blue team for redirect commands |
| `r` | `RDR_SEL_TEAM=red` | Select red team for redirect commands |
| `1`–`9` | `RDR_SEL_INDEX=<n>` | Select vehicle index within the chosen team |
| `w` | `RDR_CLICK_MODE_TOGGLE` | Toggle waypoint-on-click redirect mode |
| `u` | `RDR_UNTAG_TOGGLE` | Toggle untag mode |
| `e` | `AUTOTAG_EXPLODE` | Trigger autotag explode action |
| `g` | `AUTOTAG_AUTO_TOGGLE` | Toggle automatic tagging on/off |

These are raw FLTK key handlers: they fire whenever the viewer window has focus, so avoid typing in the viewer during live operations unless a command is intended.

### Test mission: `ivp/missions/s1_alpha_cot_test/`

An extension of the standard `s1_alpha` single-vehicle simulation demonstrating the full TAK integration chain. In addition to the stock alpha community (uSimMarineV22, pHelmIvP, pMarinePIDV22, pMarineViewer, etc.), it launches:

* **pCoTBridge** — TLS connection to a TAK server (port 8089), publishing vehicle position as CoT PLI and receiving inbound CoT on `COT_INBOUND`.
* **pCoTCommander** — translates ATAK "Go To" commands (`b-m-p-w-GOTO`) into `ATAK_ACTIVE=true` and `ATAK_WPT_UPDATE=points=x,y` posts for the helm.
* **pCoTGraphics** — mirrors `VIEW_POINT` and `VIEW_SEGLIST` graphics to the ATAK map as CoT spot markers and polylines.
* **pCoTChat** — bridges ATAK GeoChat messages to/from MOOS variables.

The behavior file adds a `waypt_atak` waypoint behavior (`pwt=150`, `perpetual=true`, `updates=ATAK_WPT_UPDATE`) that activates on ATAK commands and outranks the standard mission behaviors, with an `ATAK_WPT_REACHED` endflag so pCoTCommander can acknowledge waypoint capture back to the operator.

**Before running**, edit the `pCoTBridge` block in `alpha.moos` for your environment:

* `tak_host` — IP of your TAK server.
* `tls_cert_file` / `tls_key_file` / `tls_ca_file` — absolute paths to your client certificates. The committed values are machine-specific and will not resolve on other hosts.

Launch as usual:

```bash
cd ivp/missions/s1_alpha_cot_test
./launch.sh 10        # time warp 10
```

### Syncing with upstream

This fork tracks upstream MOOS-IvP as the `upstream` remote. To pull upstream changes:

```bash
git fetch upstream
git merge upstream/main
```

The modifications to upstream files are intentionally minimal (one hunk in `CMakeLists.txt`, one hunk in `PMV_GUI.cpp`) to keep merges clean; everything else added by this fork lives in new files or submodules.

## Project Objectives and Philosophy

* Platform Independence: The MOOS-IvP software typically runs on a dedicated computer for autonomy and sensing in the vehicle "payload" section.

* Module Independence: MOOS and the IvP Helm provide two architectures that enable the autonomy and sensing system to be built from distinct and independent modules.

* Nested Capabilities: MOOS and IvP Helm architectures both allow a system to be extended without any modifying or recompiling the core, publicly available free software.

## Project Organization

The project is situated at MIT, in the Department of Mechanical Engineering and the Center for Ocean Engineering as part of the Laboratory for Autonomous Marine Sensing Systems (LAMSS). Core developers are also part of the MIT Computer Science and Artificial Intelligence Lab, (CSAIL). Core MOOS software is maintained and distributed by the Oxford Robotics Institute (ORI).

MOOS stands for "Mission Oriented Operating Suite". IvP stands for "Interval Programming". MOOS-IvP is pronounced "moose i-v-p".

## Contributing and Licensing

We welcome contributions to MOOS-IvP! Please reference our [contribution policy](./CONTRIBUTING.md) and CLA for more details.

The MOOS and MOOS-IvP codebases are licensed under a mix of GPLv3, LGPLv3, and optionally, a commercial license. Please reference [COPYING.md](./COPYING.md) for more details.

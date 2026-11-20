# MOOS-IvP

This West Point Robotics Research Center fork connects operator commands to
MOOS-IvP marine autonomy. V2GPM adds capability-based commands, behavior-tree
plans, operator chat, and mission evidence.

Our development source is **`dev`**. Tyler maintains `main`. See
[contribution instructions](AGENTS.md).

## Installation

Start with the [researcher handbook](docs/handbook/index.md), then
[install on Windows with WSL2](docs/handbook/how-to/install-wsl.md) and
[run your first simulated command](docs/handbook/tutorials/first-command.md).
The first run uses a scripted local endpoint and needs no model account.

The [website address](https://tylerwp2022.github.io/moos-ivp/) becomes available
after the repository owner completes the [Pages setup](docs/handbook/how-to/publish-site.md).
The source handbook remains readable here before publication.

Upstream platform guides: [GNU/Linux](README-GNULINUX.txt),
[macOS](README-OS-X.txt), and [Windows entry point](README-WINDOWS.txt).

## West Point Modifications

See [components and interfaces](docs/handbook/reference/interfaces.md) and
[the command architecture](docs/handbook/explanation/architecture.md).
The [historical fork overview](docs/development/fork-overview-2026-11-20.md)
preserves the earlier detailed description.

### Added applications (submodules)

See the [component reference](docs/handbook/reference/interfaces.md).

### pMarineViewer chat pane (`ivp/src/pMarineViewer/PMV_GUI.*`, `PMV_MOOSApp.*`, `PMV_ChatInput.h`)

See the [historical overview](docs/development/fork-overview-2026-11-20.md) and
[current component interfaces](docs/handbook/reference/interfaces.md).

### Build system changes (`ivp/src/CMakeLists.txt`)

See [installation](docs/handbook/how-to/install-wsl.md) and the
[exact source baseline](docs/handbook/reference/versions.md).

### pMarineViewer hotkeys (`ivp/src/pMarineViewer/PMV_GUI.cpp`)

See the [historical fork overview](docs/development/fork-overview-2026-11-20.md).

### Test mission: `ivp/missions/s1_alpha_cot_test/`

The [historical overview](docs/development/fork-overview-2026-11-20.md) describes
this TAK example. The handbook's local validation does not verify TAK connectivity.

### Syncing with upstream

Prepare upstream integration on a contribution branch and review it against
`dev`. Preserve pinned component commits. Do not merge into Tyler's `main`
without his instruction.

## Project Objectives and Philosophy

See [how commands reach a vehicle](docs/handbook/explanation/architecture.md) and
[what a result establishes](docs/handbook/explanation/results.md).

## Project Organization

[MOOS-IvP](https://moos-ivp.org/) provides the base autonomy system. This fork is
maintained by the West Point Robotics Research Center. The earlier organization
description remains in the [historical overview](docs/development/fork-overview-2026-11-20.md).

## Contributing and Licensing

See [CONTRIBUTING.md](CONTRIBUTING.md), [COPYING.md](COPYING.md), and
[development instructions](AGENTS.md). Existing code licenses and notices remain
in their source files.

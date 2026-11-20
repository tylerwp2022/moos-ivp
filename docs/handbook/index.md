# Understand the system. Run one command. Inspect the result.

<p class="doc-label">V2GPM · Researcher handbook</p>

V2GPM connects operator instructions to MOOS-IvP vehicle autonomy. An operator can propose a command, approve it, and inspect its effect. Capabilities define the permitted commands. Behavior trees execute plans. MOOS carries commands and vehicle state between applications.

<div class="handbook-intro">
<strong>Start with a simulated vehicle.</strong>
<p>The first tutorial uses a scripted local endpoint. You do not need a model account or a vehicle. You will approve a movement command and find the run records.</p>
</div>

## Choose your starting route

<div class="routes">
<div class="route"><a href="tutorials/first-command/">Run your first command</a><p>For a researcher who is new to this system. Start a simulation, approve a move, and stop the run.</p></div>
<div class="route"><a href="how-to/validate-run/">Review a result</a><p>For an experiment reviewer. Find the source identity, test results, and limits of the evidence.</p></div>
<div class="route"><a href="reference/interfaces/">Develop a component</a><p>For a developer. Find the authoritative capability, plan, and MOOS interface definitions.</p></div>
<div class="route"><a href="explanation/results/">Assess readiness</a><p>For a trial lead. Separate a local test from external reproduction and field qualification.</p></div>
</div>

## What exists today

The development source is the `dev` branch. Tyler maintains `main`. Builds use exact submodule commits, even when those components have a `dev` branch.

The documented first-run environment is Windows with Ubuntu 24.04 on WSL2. A clean build directory in an existing WSL distribution passed the [November 20 validation](evidence/2026-11-20-dev.md). A fresh-distribution install and an independent researcher walkthrough remain unverified.

The full MCTF match has additional dependencies. A working single-vehicle simulation does not establish that those dependencies are available. See [source versions and status](reference/versions.md).

## Find a page by its purpose

| Reader need | Start here |
|---|---|
| Learn through a guided task | [First simulated command](tutorials/first-command.md) |
| Complete a specific task | [Install](how-to/install-wsl.md), [validate](how-to/validate-run.md), or [troubleshoot](how-to/troubleshoot.md) |
| Look up an exact contract | [Commands and artifacts](reference/commands.md), [interfaces](reference/interfaces.md), [terminology](reference/terminology.md) |
| Understand the design | [Architecture](explanation/architecture.md) and [result interpretation](explanation/results.md) |

This handbook uses [Diátaxis and ASD-STE100 guidance](explanation/documentation.md). It does not claim full ASD-STE100 compliance. The workspace name `V2PGM` differs from the project name `V2GPM`; commands retain their actual spelling.

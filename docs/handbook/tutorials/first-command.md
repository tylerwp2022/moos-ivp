# Run your first simulated command

This tutorial shows how an operator-approved command reaches a simulated vehicle. You will run a local test and inspect its result.

The endpoint is a **scripted stand-in**. It returns a fixed proposal. It does not generate a plan with a language model.

## Before you start

Complete [Install on Windows with WSL2](../how-to/install-wsl.md). Keep a PowerShell window open in the Windows repository root. The examples below use the default distribution, install root, and ports.

If you chose another distribution, install root, or port, use those same options with each command. See [command reference](../reference/commands.md).

## 1. Run the command-flow test

If a demo from this installation is active, stop it first:

```powershell
.\scripts\wsl\Project.ps1 -Action Stop
```

Run the verification:

```powershell
.\scripts\wsl\Project.ps1 -Action Verify
```

The script runs the installed self-tests. It then starts a separate headless simulation and a local endpoint. The endpoint proposes a move to `(20,-20)`. The test submits approval and observes the vehicle.

Look for these four results:

```text
PASS simulator publishes position
PASS LLM asks for confirmation
PASS approved command moves the simulated boat
PASS behavior tree executes through MOOSDB
```

The script stops its test mission. It retains the run directory and test logs. A failure produces a nonzero exit status. If a test fails, use the [recovery guide](../how-to/troubleshoot.md) before interpreting the result.

## 2. Inspect the evidence

Open the project shell:

```powershell
.\scripts\wsl\Project.ps1 -Action Shell
```

In that Linux shell, read the results:

```bash
python3 -m json.tool "$MOOS_IVP_WSL_ROOT/verification/verification.json"
python3 -m json.tool "$MOOS_IVP_WSL_ROOT/source-manifest.json"
```

Each test result has a name, a pass value, and an exit status. Simulator results also state the tested condition. The source manifest identifies the base commit and submodule commits.

Find the run path printed by `Verify`. Its `alpha.moos` contains the actual mission configuration. Its `standin/` directory contains the local requests. See [artifacts](../reference/commands.md#artifacts) for the other files.

## 3. Interpret what happened

The movement check tests `NAV_X > 3`. It establishes that the simulated vehicle moved after approval. It does **not** establish arrival at `(20,-20)`.

The behavior-tree check tests a delayed MOOS post. It does not test every plan node or every vehicle behavior. This run does not measure model quality because the endpoint is scripted.

You have now run the command path, found its source identity, and identified the limits of its result.

## Run live Alpha

After the [WSL build](../how-to/install-wsl.md#build-on-the-linux-filesystem), open PowerShell in the repository root, the folder containing `scripts` and `ivp`. Set `OPENAI_API_KEY` in this PowerShell session and choose the desktop chat window.

```powershell
$env:OPENAI_API_KEY = [System.Net.NetworkCredential]::new('', (Read-Host 'OpenAI API key' -AsSecureString)).Password
.\scripts\wsl\Project.ps1 -Action Live -ChatViewer umacview
```

Use `-ChatViewer pmarineviewer` to keep the map and chat in a single window. If you supplied `-InstallRoot` or `-Distribution` during the build, pass the same values to `Live`. WSLg must be running for the desktop windows to open.

To launch directly in WSL, open Bash in the repository root. Use the Linux install root printed by the build if you passed `-InstallRoot`. The default is `~/Projects/moos-ivp-wsl`. Sourcing `env.sh` adds the built binaries to `PATH` and sets the behavior library and map paths.

```bash
export MOOS_IVP_WSL_ROOT="$HOME/Projects/moos-ivp-wsl"
source scripts/wsl/env.sh
command -v pAntler pLLMAgent pMarineViewer uMACView
```

The prompt below hides the key as you paste it. An existing OpenAI project key works if it has access to the configured model. If you did not save the key when it was created, create a new secret key from the [OpenAI Platform API keys page](https://platform.openai.com/api-keys).

```bash
IFS= read -r -s -p 'OpenAI API key: ' OPENAI_API_KEY
printf '\n'
export OPENAI_API_KEY
bash ivp/missions/s1_alpha_llm/launch.sh --chat-viewer=umacview
```

Both launch paths read the checked-in `alpha.moos`, which selects `gpt-6-luna` through the OpenAI Responses API. Enter a plain-English request in the chosen viewer, review the proposed steps, and type `y` to approve or `n` to decline. Watch the boat in pMarineViewer. Press Ctrl+C in the launch terminal to stop the live mission.

### Scripted WSL smoke test

This exercise opens pMarineViewer for the map and uMACView for appcasts and chat. Both viewers connect to the same MOOSDB. The Alpha profile opens chat in uMACView.

In PowerShell, start the demo:

```powershell
.\scripts\wsl\Project.ps1 -Action Demo -ChatViewer umacview
```

In uMACView, enter `/help` to see console commands, then enter `setup smoke goto`. When the status says `awaiting_confirm`, enter `n`. Alpha should hold its starting position. Stop and restart the demo, repeat the request, and enter `y`. Watch Alpha move in pMarineViewer.

For a mission already running pLLMAgent, start `uMACView mission.moos` with the same MOOSDB settings as your map viewer. Open **Chat > Toggle Chat Pane** or press Ctrl+T. Match any renamed chat variables in the uMACView block to the agent and plan executor settings. Run one operator chat session at a time when testing approvals.

Keep the source manifest, generated `alpha.moos`, operator inputs, and MOOSLog `.alog` files from both runs. Look for the proposal and `awaiting_confirm` state, the operator's answer, and the corresponding navigation updates.

Compare your run with the [November 24 uMACView validation](../evidence/2026-11-24-umacview.md).

Stop the demo after each run.

```powershell
.\scripts\wsl\Project.ps1 -Action Stop
```

Next, read [how commands reach a vehicle](../explanation/architecture.md) or [retain a validation run](../how-to/validate-run.md).

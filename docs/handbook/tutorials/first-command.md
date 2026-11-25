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

## Optional: submit the command in uMACView

For a live Alpha session, open a Linux or WSL shell with the MOOS-IvP binaries on `PATH` and `OPENAI_API_KEY` set. From `ivp/missions/s1_alpha_llm`, choose the desktop chat window with the mission launcher.

```bash
bash launch.sh --chat-viewer=umacview
# Or use pMarineViewer for both the map and chat.
bash launch.sh --chat-viewer=pmarineviewer
```

Both commands read the checked-in `alpha.moos`, which selects `gpt-6-luna` through the OpenAI Responses API. In uMACView mode, pMarineViewer opens with its chat pane closed. Press Ctrl+C in the launch terminal to stop the mission.

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

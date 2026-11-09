Windows setup

The tested Windows development path for this fork is Ubuntu 24.04 on WSL2,
with WSLg displaying the viewer and button panel on the Windows desktop.
The complete integrated stack has not been validated as native Windows binaries.

See docs/development/windows-wsl.md for dependencies, private-submodule access,
PowerShell build/run commands, a local scripted LLM demo, and verification.

The integrated demo requires the llm-integration branch. The CMake option
IVP_BUILD_SQUAD defaults to ON; users without that private submodule can pass
-WithoutSquad to scripts/wsl/Project.ps1 for the single-vehicle setup.

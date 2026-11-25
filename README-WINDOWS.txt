Windows setup

The tested Windows development path for this fork is Ubuntu 24.04 on WSL2,
with WSLg displaying the viewer and button panel on the Windows desktop.
The complete integrated stack has not been validated as native Windows binaries.

Start with docs/handbook/how-to/install-wsl.md for dependencies, submodule
access, and the PowerShell build command. Use the dev branch for development.

After building, use docs/handbook/tutorials/first-command.md for the local
verification and live Alpha commands. From the Windows repository root,
with OPENAI_API_KEY set in PowerShell:

  .\scripts\wsl\Project.ps1 -Action Live -ChatViewer umacview

Use -ChatViewer pmarineviewer for chat in the map viewer. Reuse -InstallRoot
or -Distribution if you supplied either option during the build.

# Modified by Timeo Williams on 2026-11-24.
param(
    [ValidateSet('Build','Verify','Demo','Stop','Status','Shell')]
    [string]$Action = 'Demo',
    [string]$Distribution = 'Ubuntu',
    [string]$InstallRoot,
    [string]$MctfSource,
    [ValidateRange(1024,65534)][int]$Port = 19841,
    [switch]$WithoutSquad,
    [switch]$Headless,
    [ValidateSet('pmarineviewer','umacview')]
    [string]$ChatViewer = 'pmarineviewer'
)
$ErrorActionPreference = 'Stop'

function ConvertTo-WslPath([string]$Path) {
    $absolute = (Resolve-Path -LiteralPath $Path).Path.Replace('\','/')
    $converted = & wsl --distribution $Distribution --exec wslpath -a $absolute
    if ($LASTEXITCODE -ne 0) { throw "Cannot access $Path in WSL distribution $Distribution." }
    return ($converted -join "`n").Trim()
}

$repository = ConvertTo-WslPath (Join-Path $PSScriptRoot '../..')
$command = @('env', "MOOS_IVP_WSL_PORT=$Port")
if ($InstallRoot) { $command += "MOOS_IVP_WSL_ROOT=$InstallRoot" }
switch ($Action) {
    'Build' {
        $command += @('bash', "$repository/scripts/wsl/build.sh", '--source', $repository)
        if ($WithoutSquad) { $command += '--without-squad' }
        if ($MctfSource) { $command += @('--mctf-source', (ConvertTo-WslPath $MctfSource)) }
    }
    'Shell' { $command += @('bash', '--rcfile', "$repository/scripts/wsl/env.sh", '-i') }
    default {
        $operation = @{Verify='verify'; Demo='start'; Stop='stop'; Status='status'}[$Action]
        $command += @('python3', "$repository/scripts/wsl/demo.py", $operation)
        if ($Headless) { $command += '--headless' }
        if ($Action -eq 'Demo') { $command += @('--chat-viewer', $ChatViewer) }
    }
}
& wsl --distribution $Distribution --exec @command
if ($LASTEXITCODE -ne 0) { throw "MOOS-IvP $Action failed (exit $LASTEXITCODE)." }

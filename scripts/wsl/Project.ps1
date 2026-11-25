# Modified by Timeo Williams on 2026-11-25.
param(
    [ValidateSet('Build','Verify','Demo','Live','Stop','Status','Shell')]
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

if ($Action -eq 'Live') {
    if ([string]::IsNullOrWhiteSpace($env:OPENAI_API_KEY)) {
        throw 'Set OPENAI_API_KEY in this PowerShell session before starting live Alpha.'
    }
    if ($PSBoundParameters.ContainsKey('Port')) {
        throw 'Live Alpha uses ServerPort in ivp/missions/s1_alpha_llm/alpha.moos.'
    }
}

function ConvertTo-WslPath([string]$Path) {
    $absolute = (Resolve-Path -LiteralPath $Path).Path.Replace('\','/')
    $converted = & wsl --distribution $Distribution --exec wslpath -a $absolute
    if ($LASTEXITCODE -ne 0) { throw "Cannot access $Path in WSL distribution $Distribution." }
    return ($converted -join "`n").Trim()
}

$repository = ConvertTo-WslPath (Join-Path $PSScriptRoot '../..')
$command = @('env')
if ($Action -ne 'Live') { $command += "MOOS_IVP_WSL_PORT=$Port" }
if ($InstallRoot) { $command += "MOOS_IVP_WSL_ROOT=$InstallRoot" }
switch ($Action) {
    'Build' {
        $command += @('bash', "$repository/scripts/wsl/build.sh", '--source', $repository)
        if ($WithoutSquad) { $command += '--without-squad' }
        if ($MctfSource) { $command += @('--mctf-source', (ConvertTo-WslPath $MctfSource)) }
    }
    'Shell' { $command += @('bash', '--rcfile', "$repository/scripts/wsl/env.sh", '-i') }
    'Live' {
        # Resolve paths from this wrapper so Live works from any PowerShell directory.
        $command += @('bash', '-c', 'source "$1"; shift; exec bash "$@"', 'alpha-live',
                      "$repository/scripts/wsl/env.sh", "$repository/ivp/missions/s1_alpha_llm/launch.sh",
                      "--chat-viewer=$ChatViewer")
        if ($Headless) { $command += '--nogui' }
    }
    default {
        $operation = @{Verify='verify'; Demo='start'; Stop='stop'; Status='status'}[$Action]
        $command += @('python3', "$repository/scripts/wsl/demo.py", $operation)
        if ($Headless) { $command += '--headless' }
        if ($Action -eq 'Demo') { $command += @('--chat-viewer', $ChatViewer) }
    }
}

$previousWslEnv = $env:WSLENV
if ($Action -eq 'Live') {
    # WSL inherits the key only from this launch environment.
    $entries = @($previousWslEnv -split ':' | Where-Object { $_ -and ($_ -split '/', 2)[0] -ne 'OPENAI_API_KEY' })
    $env:WSLENV = ($entries + 'OPENAI_API_KEY/u') -join ':'
}
try {
    & wsl --distribution $Distribution --exec @command
    if ($LASTEXITCODE -ne 0) { throw "MOOS-IvP $Action failed (exit $LASTEXITCODE)." }
} finally {
    if ($Action -eq 'Live') { $env:WSLENV = $previousWslEnv }
}

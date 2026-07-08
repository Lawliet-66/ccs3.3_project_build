<#
.SYNOPSIS
    Wrapper that runs ccs3.3_project_build.exe elevated so timake.exe
    gets the administrator privileges it requires, then surfaces the
    single JSON result line to the calling (non-elevated) console.

.DESCRIPTION
    timake.exe (CCS3.3) requires administrator privileges. An elevated
    process launched via Start-Process -Verb RunAs cannot pipe stdout
    back to the non-elevated parent, so the exe writes its result to
    status.json inside -log <log_dir>. This wrapper reads that file and
    echoes the JSON to its own stdout, then sets $LASTEXITCODE.

    Usage is identical to ccs3.3_project_build.exe:
        run_build.ps1 <project.pjt> [-clean] -log <log_dir>

    A UAC prompt will appear when this script is run from a non-elevated
    console. From an already-elevated console it launches without a prompt.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$ProjectPjt,

    [switch]$clean,

    [Parameter(Mandatory = $true)]
    [string]$log
)

# Locate the bundled exe. It lives in the Script/ subdirectory of the
# released skill package, next to a copy of this wrapper.
$ScriptDir = Split-Path -Parent $PSCommandPath
if (-not $ScriptDir) { $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path }
if (-not $ScriptDir) { $ScriptDir = (Get-Location).Path }

# Support both layouts: exe next to the script (Script/) and exe in a
# Script/ subdirectory (skill package root).
$ExePath = Join-Path $ScriptDir 'ccs3.3_project_build.exe'
if (-not (Test-Path -LiteralPath $ExePath)) {
    $ExePath = Join-Path $ScriptDir 'Script\ccs3.3_project_build.exe'
}

if (-not (Test-Path -LiteralPath $ExePath)) {
    Write-Output (ConvertTo-Json -Compress -Depth 3 @{
        status  = 'fail'
        log     = ''
        message = "ccs3.3_project_build.exe not found at: $ExePath"
    })
    exit 1
}

# Resolve an absolute log dir so the exe and this wrapper agree on where
# status.json will land, regardless of the exe's working directory.
$LogAbs = $null
try {
    $LogAbs = (Resolve-Path -LiteralPath $log -ErrorAction Stop).Path
} catch {
    $LogAbs = [System.IO.Path]::GetFullPath($log)
    New-Item -ItemType Directory -Path $LogAbs -Force | Out-Null
}
$StatusFile = Join-Path $LogAbs 'status.json'

# Remove any stale status file so a crashed/aborted run cannot masquerade
# as a fresh result.
Remove-Item -LiteralPath $StatusFile -ErrorAction SilentlyContinue

# Build the argument list for the exe (quote paths containing spaces).
$exeArgs = @("`"$ProjectPjt`"", "-log", "`"$LogAbs`"")
if ($clean) { $exeArgs += '-clean' }

$proc = $null
try {
    $proc = Start-Process -FilePath $ExePath `
                          -ArgumentList $exeArgs `
                          -Verb RunAs `
                          -Wait `
                          -PassThru `
                          -WindowStyle Hidden
} catch {
    Write-Output (ConvertTo-Json -Compress -Depth 3 @{
        status  = 'fail'
        log     = ''
        message = "Failed to launch elevated process (UAC declined?): $($_.Exception.Message)"
    })
    exit 1
}

# Give the filesystem a moment to flush in case the exe just exited.
$retries = 0
while (-not (Test-Path -LiteralPath $StatusFile) -and $retries -lt 20) {
    Start-Sleep -Milliseconds 50
    $retries++
}

if (Test-Path -LiteralPath $StatusFile) {
    $json = Get-Content -LiteralPath $StatusFile -Raw
    Write-Output $json.Trim()

    try {
        $result = $json | ConvertFrom-Json
    } catch {
        $result = $null
    }

    if ($result -and $result.status -eq 'success') {
        exit 0
    } else {
        exit 1
    }
} else {
    # No status.json — the elevated process most likely crashed before
    # writing it. Fall back to reporting the process exit code.
    Write-Output (ConvertTo-Json -Compress -Depth 3 @{
        status  = 'fail'
        log     = ''
        message = "No status.json produced. Elevated exit code: $($proc.ExitCode)"
    })
    exit 1
}
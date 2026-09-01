# Copies Docket code to the live box at 10.3.0.45 and restarts the app.
# Never copies docket.db, uploads, venv, or .runtime.
# ASCII only.

param(
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$LiveHost = "10.3.0.45"
$LiveUnc = "\\10.3.0.45\c$\Users\michaelm1\Documents\docket_app"
$LiveLocalPath = "C:\Users\michaelm1\Documents\docket_app"
$LiveUrl = "http://10.3.0.45:8001"

$Root = Split-Path -Parent $PSScriptRoot

$RootFiles = @(
    "app.py",
    "ocr_classify.py",
    "start-hidden.ps1",
    "stop-hidden.ps1",
    "Start Docket App.vbs",
    "Stop Docket App.vbs",
    "requirements.txt",
    "README.md",
    "PROJECT_BRIEF.md",
    "AGENCY_TEAM.md"
)

$ForbiddenNames = @(
    "docket.db",
    "uploads",
    "venv",
    ".runtime",
    "__pycache__",
    ".git"
)

function Test-PlanSafe {
    foreach ($name in $RootFiles) {
        if ($ForbiddenNames -contains $name) {
            throw "Include list contains forbidden name: $name"
        }
    }
}

function Get-DbStamp {
    param([string]$DbPath)
    if (-not (Test-Path $DbPath)) {
        return $null
    }
    $item = Get-Item $DbPath
    return [pscustomobject]@{
        Length = $item.Length
        LastWriteTimeUtc = $item.LastWriteTimeUtc
    }
}

function Assert-DbUnchanged {
    param($Before, [string]$DbPath)
    if ($null -eq $Before) {
        return
    }
    $after = Get-DbStamp -DbPath $DbPath
    if ($null -eq $after) {
        throw "Live docket.db missing after copy"
    }
    if ($after.Length -ne $Before.Length -or $after.LastWriteTimeUtc -ne $Before.LastWriteTimeUtc) {
        throw "Live docket.db changed during copy - abort"
    }
}

function Get-PayloadList {
    $items = @()
    foreach ($name in $RootFiles) {
        $src = Join-Path $Root $name
        if (Test-Path $src) {
            $items += [pscustomobject]@{ Kind = "file"; Src = $src; Dest = (Join-Path $LiveUnc $name) }
        } else {
            Write-Host "Skip missing source file: $name"
        }
    }
    $templatesSrc = Join-Path $Root "templates"
    if (Test-Path $templatesSrc) {
        $items += [pscustomobject]@{ Kind = "dir"; Src = $templatesSrc; Dest = (Join-Path $LiveUnc "templates") }
    }
    $ruleSrc = Join-Path $Root ".cursor\rules\agency-team.mdc"
    if (Test-Path $ruleSrc) {
        $items += [pscustomobject]@{ Kind = "file"; Src = $ruleSrc; Dest = (Join-Path $LiveUnc ".cursor\rules\agency-team.mdc") }
    }
    $scriptSrc = Join-Path $Root "scripts\push-live.ps1"
    if (Test-Path $scriptSrc) {
        $items += [pscustomobject]@{ Kind = "file"; Src = $scriptSrc; Dest = (Join-Path $LiveUnc "scripts\push-live.ps1") }
    }
    return $items
}

function Assert-PayloadSafe {
    param($Items)
    foreach ($item in $Items) {
        $leaf = Split-Path $item.Src -Leaf
        if ($ForbiddenNames -contains $leaf) {
            throw "Refusing to copy forbidden path: $($item.Src)"
        }
        $full = [System.IO.Path]::GetFullPath($item.Src)
        foreach ($bad in @("\docket.db", "\uploads\", "\venv\", "\.runtime\", "\__pycache__\", "\.git\")) {
            $needle = $bad.Replace("\", [IO.Path]::DirectorySeparatorChar)
            if ($full -like "*$needle*") {
                throw "Refusing to copy forbidden path: $($item.Src)"
            }
        }
    }
}

function Copy-DocketPayload {
    param($Items)
    foreach ($item in $Items) {
        $destDir = Split-Path $item.Dest -Parent
        if (-not (Test-Path $destDir)) {
            New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        }
        if ($item.Kind -eq "dir") {
            $destArg = $item.Dest.TrimEnd("\")
            $srcArg = $item.Src.TrimEnd("\")
            & robocopy $srcArg $destArg /E /NFL /NDL /NJH /NJS /nc /ns /np /XD __pycache__
            if ($LASTEXITCODE -ge 8) {
                throw "robocopy failed for $($item.Src) (code $LASTEXITCODE)"
            }
        } else {
            Copy-Item -LiteralPath $item.Src -Destination $item.Dest -Force
        }
        Write-Host "Copied $($item.Src) -> $($item.Dest)"
    }
}

function Restart-LiveDocket {
    Invoke-Command -ComputerName $LiveHost -ScriptBlock {
        param($Dir)
        Set-Location $Dir
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\stop-hidden.ps1
        $stopCode = $LASTEXITCODE
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\start-hidden.ps1
        $startCode = $LASTEXITCODE
        if ($startCode -ne 0) {
            throw "start-hidden.ps1 exited $startCode (stop exited $stopCode)"
        }
    } -ArgumentList $LiveLocalPath
}

function Test-LiveHealth {
    $resp = Invoke-WebRequest -Uri $LiveUrl -UseBasicParsing -TimeoutSec 15
    if ($resp.StatusCode -ne 200) {
        throw "Live health status $($resp.StatusCode)"
    }
    $title = ""
    $m = [regex]::Match($resp.Content, "<title>(.*?)</title>", "IgnoreCase")
    if ($m.Success) { $title = $m.Groups[1].Value }
    if ($title -notmatch "Docket") {
        throw "Live title was '$title', expected to contain Docket"
    }
}

Test-PlanSafe

if (-not (Test-Path $LiveUnc)) {
    Write-Host "Live folder missing: $LiveUnc"
    Write-Host "Not searching other paths."
    exit 1
}

$payload = @(Get-PayloadList)
Assert-PayloadSafe -Items $payload

if ($payload.Count -eq 0) {
    Write-Host "Nothing to copy."
    exit 1
}

Write-Host "Live folder: $LiveUnc"
Write-Host "Payload:"
$payload | ForEach-Object { Write-Host ("  {0} {1}" -f $_.Kind, $_.Src) }

if ($DryRun) {
    Write-Host "Dry run only. No copy, no restart."
    exit 0
}

$dbPath = Join-Path $LiveUnc "docket.db"
$beforeDb = Get-DbStamp -DbPath $dbPath

try {
    Copy-DocketPayload -Items $payload
} catch {
    Write-Host "Copy failed: $($_.Exception.Message)"
    Write-Host "Not restarting."
    exit 1
}

try {
    Assert-DbUnchanged -Before $beforeDb -DbPath $dbPath
} catch {
    Write-Host $_.Exception.Message
    exit 1
}
Write-Host "Live docket.db unchanged."

$restarted = $false
try {
    Restart-LiveDocket
    $restarted = $true
    Write-Host "Live process restarted."
} catch {
    Write-Host "Copy succeeded. Restart did not. Code is on disk at the live folder. Joan may still be on the old process until someone double-clicks Stop Docket App then Start Docket App on that PC."
    Write-Host $_.Exception.Message
    exit 2
}

Start-Sleep -Seconds 3

try {
    Test-LiveHealth
    Write-Host "Live health OK: $LiveUrl"
    exit 0
} catch {
    Write-Host "Restart finished but $LiveUrl did not return 200 with title Docket. Do not claim Joan is on the new build."
    Write-Host $_.Exception.Message
    exit 2
}

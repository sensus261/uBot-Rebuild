<#
.SYNOPSIS
  Install / remove / inspect the uBot files in a Metin2 client folder.

.EXAMPLES
  .\ubot-deploy.ps1 Status
  .\ubot-deploy.ps1 Install
  .\ubot-deploy.ps1 Install -WhatIf                  # dry run
  .\ubot-deploy.ps1 Remove
  .\ubot-deploy.ps1 Install -GameDir 'E:\Games\metin2\ro-RO'
  .\ubot-deploy.ps1 Install -Items eXLib.mix,init.py # only some items

  To set a permanent default, edit the "CONFIG" block below.
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Position = 0)]
    [ValidateSet('Install', 'Remove', 'Status')]
    [string]$Action = 'Status',

    # ---- CONFIG ------------------------------------------------------------
    [string]$GameDir   = 'D:\Games\Gameforge\metin2\ro-RO',   # folder with metin2client.exe
    [string]$SourceDir = $PSScriptRoot,                       # where the uBot files live
    [string[]]$Items   = @('eXLib.mix', 'init.py', 'OpenBot'),# what to deploy
    [string]$ClientExe = 'metin2client.exe',
    # ------------------------------------------------------------------------

    [switch]$NoBackup,   # don't back up files that already exist in the game folder
    [switch]$Force       # proceed even if the game is running
)

$ErrorActionPreference = 'Stop'
$backupSuffix = '.ubot-backup'

function Write-Step($msg, $color = 'Cyan') { Write-Host $msg -ForegroundColor $color }

# --- sanity checks ------------------------------------------------------------
if (-not (Test-Path -LiteralPath (Join-Path $GameDir $ClientExe))) {
    throw "'$ClientExe' not found in '$GameDir'. Check -GameDir."
}

$running = Get-Process -Name ([IO.Path]::GetFileNameWithoutExtension($ClientExe)) -ErrorAction SilentlyContinue
if ($running -and $Action -ne 'Status' -and -not $Force) {
    throw "$ClientExe is running (files may be locked). Close the game or pass -Force."
}

function Get-State($item) {
    $src = Join-Path $SourceDir $item
    $dst = Join-Path $GameDir  $item
    [pscustomobject]@{
        Item      = $item
        InSource  = Test-Path -LiteralPath $src
        Installed = Test-Path -LiteralPath $dst
        Backup    = Test-Path -LiteralPath ($dst + $backupSuffix)
    }
}

# --- actions ------------------------------------------------------------------
switch ($Action) {

    'Status' {
        Write-Step "Game dir  : $GameDir"
        Write-Step "Source dir: $SourceDir"
        Write-Step ("Game      : " + $(if ($running) { 'RUNNING' } else { 'not running' }))
        $Items | ForEach-Object { Get-State $_ } | Format-Table -AutoSize
    }

    'Install' {
        foreach ($item in $Items) {
            $src = Join-Path $SourceDir $item
            $dst = Join-Path $GameDir  $item
            if (-not (Test-Path -LiteralPath $src)) { Write-Step "skip   $item (not in source)" Yellow; continue }

            # keep a one-time backup of anything that was already there
            $bak = $dst + $backupSuffix
            if (-not $NoBackup -and (Test-Path -LiteralPath $dst) -and -not (Test-Path -LiteralPath $bak)) {
                if ($PSCmdlet.ShouldProcess($dst, "Back up to $bak")) {
                    Move-Item -LiteralPath $dst -Destination $bak
                    Write-Step "backup $item -> $item$backupSuffix" Yellow
                }
            }

            if ($PSCmdlet.ShouldProcess($dst, "Copy from $src")) {
                if (Test-Path -LiteralPath $dst) { Remove-Item -LiteralPath $dst -Recurse -Force }
                Copy-Item -LiteralPath $src -Destination $dst -Recurse -Force
                # don't ship compiled bytecode / git junk
                if ((Get-Item -LiteralPath $dst).PSIsContainer) {
                    # NOTE: don't use -Include with -LiteralPath (PS 5.1 ignores it and matches everything)
                    Get-ChildItem -LiteralPath $dst -Recurse -Force -File |
                        Where-Object { $_.Extension -eq '.pyc' -or $_.Name -like '.git*' } |
                        Remove-Item -Force -ErrorAction SilentlyContinue
                }
                Write-Step "copied $item" Green
            }
        }
        Write-Step "Done. Start the game via the launcher and enter the world."
    }

    'Remove' {
        foreach ($item in $Items) {
            $dst = Join-Path $GameDir $item
            $bak = $dst + $backupSuffix

            if (Test-Path -LiteralPath $dst) {
                if ($PSCmdlet.ShouldProcess($dst, 'Delete')) {
                    Remove-Item -LiteralPath $dst -Recurse -Force
                    Write-Step "removed $item" Green
                }
            } else {
                Write-Step "skip    $item (not installed)" DarkGray
            }

            # restore whatever was there before we installed
            if (Test-Path -LiteralPath $bak) {
                if ($PSCmdlet.ShouldProcess($bak, "Restore to $dst")) {
                    Move-Item -LiteralPath $bak -Destination $dst
                    Write-Step "restored original $item" Yellow
                }
            }
        }
        # compiled bytecode the game may have left behind next to init.py
        Get-ChildItem -LiteralPath $GameDir -Filter 'init.pyc' -ErrorAction SilentlyContinue |
            Where-Object { $Items -contains 'init.py' } |
            ForEach-Object { if ($PSCmdlet.ShouldProcess($_.FullName, 'Delete')) { Remove-Item -LiteralPath $_.FullName -Force } }
    }
}

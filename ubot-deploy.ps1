<#
.SYNOPSIS
  Install / remove / inspect the uBot files in a Metin2 client folder.

.EXAMPLES
  .\ubot-deploy.ps1 Status
  .\ubot-deploy.ps1 Install
  .\ubot-deploy.ps1 Install -WhatIf                  # dry run
  .\ubot-deploy.ps1 Link                             # link instead of copy: repo edits show up in the game folder live
  .\ubot-deploy.ps1 Remove
  .\ubot-deploy.ps1 Install -GameDir 'E:\Games\metin2\ro-RO'
  .\ubot-deploy.ps1 Install -Items eXLib.mix,init.py # only some items

  To set a permanent default, edit the "CONFIG" block below.
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Position = 0)]
    [ValidateSet('Install', 'Link', 'Remove', 'Status')]
    [string]$Action = 'Status',

    # ---- CONFIG ------------------------------------------------------------
    #[string]$GameDir   = 'C:\Games\METIN2 OFICIAL\metin2\ro-RO',   # folder with metin2client.exe
    [string]$GameDir   = 'C:\Games\Metin2 RO\metin2\ro-RO',   # folder with metin2client.exe
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

function Test-IsLink($path) {
    $i = Get-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
    if (-not $i) { return $false }
    return [bool](($i.Attributes -band [IO.FileAttributes]::ReparsePoint) -or ($i.LinkType -eq 'HardLink'))
}

# Delete a file/folder/link WITHOUT following links (Remove-Item -Recurse on a junction can wipe the target in PS 5.1)
function Remove-Dst($path) {
    $i = Get-Item -LiteralPath $path -Force
    if ($i.PSIsContainer) {
        if ($i.Attributes -band [IO.FileAttributes]::ReparsePoint) { [IO.Directory]::Delete($i.FullName) }
        else { Remove-Item -LiteralPath $path -Recurse -Force }
    } else {
        Remove-Item -LiteralPath $path -Force
    }
}

function Get-State($item) {
    $src = Join-Path $SourceDir $item
    $dst = Join-Path $GameDir  $item
    [pscustomobject]@{
        Item      = $item
        InSource  = Test-Path -LiteralPath $src
        Installed = Test-Path -LiteralPath $dst
        Linked    = (Test-Path -LiteralPath $dst) -and (Test-IsLink $dst)
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
            if (-not $NoBackup -and (Test-Path -LiteralPath $dst) -and -not (Test-Path -LiteralPath $bak) -and -not (Test-IsLink $dst)) {
                if ($PSCmdlet.ShouldProcess($dst, "Back up to $bak")) {
                    Move-Item -LiteralPath $dst -Destination $bak
                    Write-Step "backup $item -> $item$backupSuffix" Yellow
                }
            }

            if ($PSCmdlet.ShouldProcess($dst, "Copy from $src")) {
                if (Test-Path -LiteralPath $dst) { Remove-Dst $dst }
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

    'Link' {
        foreach ($item in $Items) {
            $src = Join-Path $SourceDir $item
            $dst = Join-Path $GameDir  $item
            if (-not (Test-Path -LiteralPath $src)) { Write-Step "skip   $item (not in source)" Yellow; continue }
            $isDir = (Get-Item -LiteralPath $src).PSIsContainer

            $bak = $dst + $backupSuffix
            if (-not $NoBackup -and (Test-Path -LiteralPath $dst) -and -not (Test-Path -LiteralPath $bak) -and -not (Test-IsLink $dst)) {
                if ($PSCmdlet.ShouldProcess($dst, "Back up to $bak")) {
                    Move-Item -LiteralPath $dst -Destination $bak
                    Write-Step "backup $item -> $item$backupSuffix" Yellow
                }
            }

            if ($PSCmdlet.ShouldProcess($dst, "Link to $src")) {
                if (Test-Path -LiteralPath $dst) { Remove-Dst $dst }
                $kind = $null
                try {
                    New-Item -ItemType SymbolicLink -Path $dst -Target $src | Out-Null
                    $kind = 'symlink'
                } catch {
                    # no admin / Developer Mode: junction for folders, hard link for files (same drive only)
                    try {
                        if ($isDir) { New-Item -ItemType Junction -Path $dst -Target $src | Out-Null; $kind = 'junction' }
                        else        { New-Item -ItemType HardLink -Path $dst -Target $src | Out-Null; $kind = 'hardlink' }
                    } catch {
                        Write-Step "FAILED $item : $($_.Exception.Message)" Red
                        continue
                    }
                }
                Write-Step "linked $item ($kind)" Green
            }
        }
        Write-Step "Done. Repo edits now appear in the game folder. Use /rah (/rah-ui) in game for hot-reloadable modules; restart the client for the rest."
        Write-Step "Note: hardlinked files (fallback) detach if an editor/git replaces the file; re-run Link then." DarkGray
    }

    'Remove' {
        foreach ($item in $Items) {
            $dst = Join-Path $GameDir $item
            $bak = $dst + $backupSuffix

            if (Test-Path -LiteralPath $dst) {
                if ($PSCmdlet.ShouldProcess($dst, 'Delete')) {
                    Remove-Dst $dst
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

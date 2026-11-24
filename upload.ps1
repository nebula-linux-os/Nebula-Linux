# Nebula Linux: upload a built ISO and its SHA256 checksum to SourceForge.
#
#   $env:SF_USER = "your-sourceforge-username"
#   .\upload.ps1                          # newest ISO in out\
#   .\upload.ps1 -Iso out\nebula-linux-2026.11.23-x86_64.iso -Folder beta
#   .\upload.ps1 -DryRun                  # show what would happen
#
# Uses scp to frs.sourceforge.net. Authentication is your SourceForge password
# (scp prompts for it) or an SSH key added at
# https://sourceforge.net/auth/shell_services.
#
# Optional: with $env:SF_API_KEY set (Account > Preferences > Releases API key)
# and -SetDefault, the ISO becomes the project's "Download Latest Version" file.

param(
    [string]$Iso,
    [string]$User = $env:SF_USER,
    [string]$Project = "nebula-linux-arch-edition-niri",
    [string]$Folder = "",
    [switch]$SetDefault,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

if (-not $Iso) {
    $latest = Get-ChildItem (Join-Path $PSScriptRoot "out") -Filter "nebula-linux-*.iso" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $latest) { Write-Error "No ISO found in out\. Run .\build.ps1 first or pass -Iso." }
    $Iso = $latest.FullName
}
$Iso = (Resolve-Path $Iso).Path
$name = Split-Path $Iso -Leaf

if (-not $User) { Write-Error "Set `$env:SF_USER or pass -User <sourceforge-username>." }
if ($SetDefault -and -not $env:SF_API_KEY) { Write-Error "-SetDefault needs `$env:SF_API_KEY." }

# Checksum file in the standard `sha256sum -c` format, next to the ISO.
Write-Host ">> Hashing $name ..." -ForegroundColor Cyan
$hash = (Get-FileHash $Iso -Algorithm SHA256).Hash.ToLower()
$shaFile = "$Iso.sha256"
[IO.File]::WriteAllText($shaFile, "$hash  $name`n")
Write-Host "   SHA256: $hash"

$folderPath = ($Folder.Trim('/') -replace '\\', '/')
$remoteDir = "/home/frs/project/$Project" + $(if ($folderPath) { "/$folderPath" } else { "" })
$filesPath = $(if ($folderPath) { "$folderPath/$name" } else { $name })
$downloadUrl = "https://sourceforge.net/projects/$Project/files/$filesPath/download"

# Windows OpenSSH scp handles drive-letter paths; Git's scp would read C: as a host.
$scp = Join-Path $env:SystemRoot "System32\OpenSSH\scp.exe"
if (-not (Test-Path $scp)) { $scp = "scp" }
$target = "${User}@frs.sourceforge.net:$remoteDir/"

Write-Host ">> Uploading to $target" -ForegroundColor Cyan
if ($DryRun) {
    Write-Host "   (dry run) $scp $Iso $shaFile $target"
} else {
    if ($folderPath) {
        # scp can't create the remote folder; sftp's mkdir can (fails harmlessly if it exists).
        $sftp = Join-Path (Split-Path $scp) "sftp.exe"
        if (-not (Test-Path $sftp)) { $sftp = "sftp" }
        "-mkdir $remoteDir" | & $sftp -b - "${User}@frs.sourceforge.net" | Out-Null
    }
    & $scp $Iso $shaFile $target
    if ($LASTEXITCODE -ne 0) { Write-Error "scp failed (exit code $LASTEXITCODE)." }
}

if ($SetDefault) {
    $api = "https://sourceforge.net/projects/$Project/files/$filesPath"
    $body = "default=windows&default=mac&default=linux&default=bsd&default=solaris&default=others&api_key=$($env:SF_API_KEY)"
    if ($DryRun) {
        Write-Host "   (dry run) PUT $api (set as default download for all platforms)"
    } else {
        Invoke-RestMethod -Method Put -Uri $api -Body $body -Headers @{ Accept = "application/json" } | Out-Null
        Write-Host ">> Set as the default download." -ForegroundColor Green
    }
}

Write-Host ">> Done." -ForegroundColor Green
Write-Host "   Download: $downloadUrl"
Write-Host "   SHA256:   $hash"
Write-Host "   Update the download link and SHA256 in README.md and docs\index.html."

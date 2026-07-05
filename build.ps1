# Nebula Linux ISO build — Windows entry point.
# Runs the real build (build.sh) inside an Arch Linux Docker container,
# because mkarchiso only works on Arch.

$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$out = Join-Path $root "out"
New-Item -ItemType Directory -Force -Path $out | Out-Null

docker info | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker is not running. Start Docker Desktop and try again."
}

Write-Host ">> Building Nebula Linux ISO (this takes a while on first run)..." -ForegroundColor Cyan

# --privileged: pacstrap needs to mount /proc, /dev etc. inside the chroot.
# tr -d '\r' guards against CRLF line endings from Windows checkouts.
docker run --rm --privileged `
    -v "${root}:/src:ro" `
    -v "${out}:/out" `
    -v "nebula-pacman-cache:/var/cache/pacman/pkg" `
    archlinux:latest `
    bash -c "tr -d '\r' < /src/build.sh > /tmp/build.sh && bash /tmp/build.sh"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Build failed (exit code $LASTEXITCODE). See output above."
}

Write-Host ">> Done. ISO written to:" -ForegroundColor Green
Get-ChildItem $out -Filter *.iso | ForEach-Object { Write-Host "   $($_.FullName)  ($([math]::Round($_.Length / 1GB, 2)) GB)" }

# clipper setup for Windows. Safe to re-run.
#   powershell -ExecutionPolicy Bypass -File setup\setup.ps1
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
$Repo = (Get-Location).Path
function Say($t) { Write-Host "`n== $t" -ForegroundColor Cyan }
function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [Environment]::GetEnvironmentVariable("Path", "User") + ";" +
                "$env:USERPROFILE\.local\bin"
}

Say "uv (Python manager)"
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    powershell -ExecutionPolicy ByPass -NoProfile -Command "irm https://astral.sh/uv/install.ps1 | iex"
    Refresh-Path
}
uv --version

Say "ffmpeg (with libass, for captions)"
function Has-Libass {
    if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { return $false }
    # Windows PowerShell 5.1 turns redirected stderr into errors under "Stop"
    $old = $ErrorActionPreference; $ErrorActionPreference = "Continue"
    try { $f = (& ffmpeg -hide_banner -filters 2>$null) -join "`n" }
    finally { $ErrorActionPreference = $old }
    return $f -match " (ass|subtitles) "
}
if (-not (Has-Libass)) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements
    } elseif (Get-Command choco -ErrorAction SilentlyContinue) {
        choco install ffmpeg-full -y --no-progress
    } else {
        throw "Neither winget nor choco found. Install ffmpeg from https://www.gyan.dev/ffmpeg/builds/ (full build), add its bin folder to PATH, then re-run."
    }
    Refresh-Path
    if (-not (Has-Libass)) {
        Write-Host "ffmpeg was installed but this window can't see it yet. Close PowerShell, open a new one, and re-run this script." -ForegroundColor Yellow
        exit 1
    }
}
(& ffmpeg -hide_banner -version | Select-Object -First 1)

Say "Python 3.12 environment in pipeline\.venv"
uv venv --allow-existing --python 3.12 pipeline\.venv
if ($LASTEXITCODE) { throw "uv venv failed" }
uv pip install --python pipeline\.venv\Scripts\python.exe -r pipeline\requirements.txt
if ($LASTEXITCODE) { throw "package install failed" }

Say ".env"
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "created .env - put your NYO_API_KEY in it (notepad .env)"
} else { Write-Host ".env exists" }

Say "self-test"
& pipeline\.venv\Scripts\python.exe pipeline\clips.py --check
if ($LASTEXITCODE) {
    Write-Host "`nFix the NO lines (usually: put NYO_API_KEY in $Repo\.env), then run:" -ForegroundColor Yellow
    Write-Host "  pipeline\.venv\Scripts\python.exe pipeline\clips.py --check"
}

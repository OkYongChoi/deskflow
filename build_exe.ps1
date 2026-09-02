$ErrorActionPreference = "Stop"

Set-Location -LiteralPath $PSScriptRoot

$buildEnvironment = Join-Path $PSScriptRoot ".build-env"
$buildPython = Join-Path $buildEnvironment "Scripts\python.exe"
$buildOutput = Join-Path $PSScriptRoot "build"
$distOutput = Join-Path $PSScriptRoot "dist"
$distExecutable = Join-Path $distOutput "DeskFlow.exe"

if (-not (Test-Path -LiteralPath $buildPython)) {
    python -m venv $buildEnvironment
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create the build environment."
    }
}

New-Item -ItemType Directory -Path $buildOutput -Force | Out-Null
New-Item -ItemType Directory -Path $distOutput -Force | Out-Null

if (Test-Path -LiteralPath $distExecutable) {
    for ($attempt = 1; $attempt -le 20; $attempt++) {
        try {
            Remove-Item -LiteralPath $distExecutable -Force -ErrorAction Stop
            break
        }
        catch {
            if ($attempt -eq 20) {
                throw "Could not replace $distExecutable because it is in use."
            }
            Start-Sleep -Milliseconds 100
        }
    }
}

$pyInstallerPackage = Join-Path $buildEnvironment "Lib\site-packages\PyInstaller"
if (-not (Test-Path -LiteralPath $pyInstallerPackage)) {
    & $buildPython -m pip install --disable-pip-version-check PyInstaller
    if ($LASTEXITCODE -ne 0) {
        throw "Could not install PyInstaller in the build environment."
    }
}

& $buildPython -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name DeskFlow `
    --distpath $distOutput `
    --workpath $buildOutput `
    --specpath $buildOutput `
    "$PSScriptRoot\deskflow_launcher.py"

if ($LASTEXITCODE -ne 0) {
    throw "DeskFlow build failed with exit code $LASTEXITCODE."
}

Write-Host "Built: $PSScriptRoot\dist\DeskFlow.exe"

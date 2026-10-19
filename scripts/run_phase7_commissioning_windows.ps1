param(
    [string]$CameraSource = "",
    [switch]$Strict,
    [switch]$RequireModel
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path ".").Path

if (-not (Test-Path "$Root\.venv\Scripts\Activate.ps1")) {
    Write-Error "Missing .venv. Create it with: py -3.12 -m venv .venv"
}

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
. .\.venv\Scripts\Activate.ps1

$argsList = @("scripts\commission_synccart.py")
if ($CameraSource) { $argsList += @("--camera-source", $CameraSource) }
if ($Strict) { $argsList += "--strict" }
if ($RequireModel) { $argsList += "--require-model" }

python @argsList
exit $LASTEXITCODE

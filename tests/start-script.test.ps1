$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$startPs1 = Join-Path $root "start.ps1"
$startBat = Join-Path $root "start.bat"

if (-not (Test-Path $startPs1)) {
    throw "start.ps1 is missing."
}

if (-not (Test-Path $startBat)) {
    throw "start.bat is missing."
}

$script = Get-Content -LiteralPath $startPs1 -Raw -Encoding UTF8
$launcher = Get-Content -LiteralPath $startBat -Raw -Encoding UTF8

foreach ($expected in @(
    "docker compose up -d postgres minio minio-init",
    "Wait-ForTcpPort",
    "127.0.0.1",
    "5432",
    "backend\.venv\Scripts\python.exe",
    "-m alembic",
    "upgrade",
    "head",
    "-m uvicorn",
    "app.main:app",
    "--app-dir",
    "backend",
    "--reload",
    "--host",
    "127.0.0.1",
    "--port",
    "8000",
    "[int]`$FrontendPort = 3000",
    "`$FrontendUrl = `"http://localhost:`$FrontendPort`"",
    "npm.cmd",
    "run",
    "dev"
)) {
    if (-not $script.Contains($expected)) {
        throw "start.ps1 does not include expected text: $expected"
    }
}

if (-not $launcher.Contains("start.ps1")) {
    throw "start.bat does not launch start.ps1."
}

Write-Output "start script assertions passed"

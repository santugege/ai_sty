param(
    [switch]$SkipDocker,
    [switch]$SkipMigrations,
    [switch]$NoBrowser,
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 3000
)

$ErrorActionPreference = "Stop"

function Require-Command {
    param([string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Missing required command: $Name"
    }
}

function Invoke-CheckedCommand {
    param(
        [scriptblock]$Command,
        [string]$FailureMessage
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw $FailureMessage
    }
}

function Wait-ForTcpPort {
    param(
        [string]$HostName,
        [int]$Port,
        [int]$TimeoutSeconds = 60
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $client = [System.Net.Sockets.TcpClient]::new()
            $connect = $client.BeginConnect($HostName, $Port, $null, $null)
            if ($connect.AsyncWaitHandle.WaitOne(1000)) {
                $client.EndConnect($connect)
                $client.Close()
                return
            }
            $client.Close()
        } catch {
            Start-Sleep -Seconds 1
        }

        Write-Host "." -NoNewline
        Start-Sleep -Seconds 1
    }

    throw "Timed out waiting for ${HostName}:$Port"
}

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendPython = Join-Path $Root "backend\.venv\Scripts\python.exe"

Set-Location $Root

Require-Command "npm.cmd"

if (-not (Test-Path $BackendPython)) {
    throw "Backend virtualenv not found: $BackendPython. Create it and install backend requirements first."
}

if (-not (Test-Path (Join-Path $Root "frontend\node_modules"))) {
    throw "Frontend dependencies not found. Run npm install in the frontend directory first."
}

if (-not $SkipDocker) {
    Require-Command "docker"
    Write-Host "Starting PostgreSQL and MinIO with Docker Compose..." -ForegroundColor Cyan
    Invoke-CheckedCommand `
        -Command { docker compose up -d postgres minio minio-init } `
        -FailureMessage "Docker Compose failed. The images may not have been pulled, or Docker Hub may be unreachable. Retry later, run 'docker compose pull' manually, or start dependencies yourself. Use .\start.ps1 -SkipDocker after dependencies are running."
    Write-Host "Waiting for PostgreSQL on localhost:5432" -ForegroundColor Cyan
    Wait-ForTcpPort -HostName "127.0.0.1" -Port 5432
    Write-Host ""
}

if (-not $SkipMigrations) {
    Write-Host "Applying database migrations..." -ForegroundColor Cyan
    Invoke-CheckedCommand `
        -Command { & $BackendPython -m alembic -c backend\alembic.ini upgrade head } `
        -FailureMessage "Alembic migration failed. Check whether PostgreSQL is running and DATABASE_URL in backend\.env is correct."
}

$BackendUrl = "http://127.0.0.1:$BackendPort"
$FrontendUrl = "http://localhost:$FrontendPort"

$BackendCommand = @"
Set-Location '$Root'
`$env:PYTHONUNBUFFERED = '1'
& '$BackendPython' -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port $BackendPort
"@

$FrontendCommand = @"
Set-Location '$Root\frontend'
`$env:NEXT_PUBLIC_API_BASE_URL = '$BackendUrl'
& npm.cmd run dev -- --hostname 127.0.0.1 --port $FrontendPort
"@

Write-Host "Starting backend at $BackendUrl ..." -ForegroundColor Green
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-Command",
    $BackendCommand
) -WindowStyle Normal

Write-Host "Starting frontend at $FrontendUrl ..." -ForegroundColor Green
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-Command",
    $FrontendCommand
) -WindowStyle Normal

if (-not $NoBrowser) {
    Start-Sleep -Seconds 3
    Start-Process $FrontendUrl
}

Write-Host ""
Write-Host "Project startup requested." -ForegroundColor Green
Write-Host "Backend:  $BackendUrl"
Write-Host "Frontend: $FrontendUrl"
Write-Host ""
Write-Host "Options:"
Write-Host "  .\start.ps1 -SkipDocker      # do not start Docker services"
Write-Host "  .\start.ps1 -SkipMigrations  # do not run Alembic migrations"
Write-Host "  .\start.ps1 -NoBrowser       # do not open the browser"

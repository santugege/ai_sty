param(
    [switch]$Docker,
    [switch]$Local,
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

function Test-TcpPort {
    param(
        [string]$HostName,
        [int]$Port
    )

    try {
        $client = [System.Net.Sockets.TcpClient]::new()
        $connect = $client.BeginConnect($HostName, $Port, $null, $null)
        if (-not $connect.AsyncWaitHandle.WaitOne(500)) {
            $client.Close()
            return $false
        }
        $client.EndConnect($connect)
        $client.Close()
        return $true
    } catch {
        return $false
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
$DataDir = Join-Path $Root "data"
$LocalDatabasePath = Join-Path $DataDir "dev.sqlite3"
$LocalImageDir = Join-Path $DataDir "images"

Set-Location $Root

Require-Command "npm.cmd"

if (-not (Test-Path $BackendPython)) {
    throw "Backend virtualenv not found: $BackendPython. Create it and install backend requirements first."
}

if (-not (Test-Path (Join-Path $Root "frontend\node_modules"))) {
    throw "Frontend dependencies not found. Run npm install in the frontend directory first."
}

if (-not $Docker) {
    $Local = $true
}

if ($Local) {
    New-Item -ItemType Directory -Force -Path $DataDir, $LocalImageDir | Out-Null
    $env:DATABASE_URL = "sqlite+pysqlite:///$($LocalDatabasePath.Replace('\', '/'))"
    $env:IMAGE_STORAGE_BACKEND = "local"
    $env:IMAGE_STORAGE_DIR = $LocalImageDir
    $SkipDocker = $true
    Write-Host "Local mode enabled: SQLite database and local image storage." -ForegroundColor Cyan
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
$BackendIsRunning = Test-TcpPort -HostName "127.0.0.1" -Port $BackendPort
$FrontendIsRunning = Test-TcpPort -HostName "127.0.0.1" -Port $FrontendPort

$BackendCommand = @"
Set-Location '$Root'
`$env:PYTHONUNBUFFERED = '1'
`$env:DATABASE_URL = '$env:DATABASE_URL'
`$env:IMAGE_STORAGE_BACKEND = '$env:IMAGE_STORAGE_BACKEND'
`$env:IMAGE_STORAGE_DIR = '$env:IMAGE_STORAGE_DIR'
& '$BackendPython' -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port $BackendPort
"@

$FrontendCommand = @"
Set-Location '$Root\frontend'
`$env:NEXT_PUBLIC_API_BASE_URL = '$BackendUrl'
& npm.cmd run dev -- --hostname 127.0.0.1 --port $FrontendPort
"@

Write-Host "Starting backend at $BackendUrl ..." -ForegroundColor Green
if ($BackendIsRunning) {
    Write-Host "Backend already appears to be running at $BackendUrl; reusing it." -ForegroundColor Yellow
} else {
    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        $BackendCommand
    ) -WindowStyle Normal
}

Write-Host "Starting frontend at $FrontendUrl ..." -ForegroundColor Green
if ($FrontendIsRunning) {
    Write-Host "Frontend already appears to be running at $FrontendUrl; reusing it." -ForegroundColor Yellow
} else {
    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        $FrontendCommand
    ) -WindowStyle Normal
}

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
Write-Host "  .\start.ps1                 # use SQLite and local image storage, no Docker"
Write-Host "  .\start.ps1 -Docker          # use Docker Compose for PostgreSQL and MinIO"
Write-Host "  .\start.ps1 -SkipDocker      # use configured database/storage without starting Docker"
Write-Host "  .\start.ps1 -Local           # force SQLite and local image storage, no Docker"
Write-Host "  .\start.ps1 -SkipMigrations  # do not run Alembic migrations"
Write-Host "  .\start.ps1 -NoBrowser       # do not open the browser"

param(
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

function Assert-PortAvailable {
    param(
        [int]$Port,
        [string]$ServiceName
    )

    $listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if (-not $listeners) {
        return
    }

    $owners = $listeners |
        Select-Object -ExpandProperty OwningProcess -Unique |
        ForEach-Object {
            $process = Get-Process -Id $_ -ErrorAction SilentlyContinue
            if ($process) {
                "$($_) ($($process.ProcessName))"
            } else {
                "$_"
            }
        }

    throw "$ServiceName port $Port is already in use by PID(s): $($owners -join ', '). Stop the existing process or choose another port."
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

function Wait-ForHttpEndpoint {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 60
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return
            }
        } catch {
            # Service is still starting; keep polling until the timeout.
        }

        Write-Host "." -NoNewline
        Start-Sleep -Seconds 1
    }

    throw "Timed out waiting for $Url"
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

$BackendUrl = "http://127.0.0.1:$BackendPort"
$FrontendUrl = "http://127.0.0.1:$FrontendPort"

Assert-PortAvailable -Port $BackendPort -ServiceName "Backend"
Assert-PortAvailable -Port $FrontendPort -ServiceName "Frontend"

Require-Command "docker"
Write-Host "Starting PostgreSQL and MinIO with Docker Compose..." -ForegroundColor Cyan
Invoke-CheckedCommand `
    -Command { docker compose up -d postgres minio minio-init } `
    -FailureMessage "Docker Compose failed. The images may not have been pulled, or Docker Hub may be unreachable. Retry later, run 'docker compose pull' manually, or configure Docker Desktop network/proxy settings."
Write-Host "Waiting for PostgreSQL on localhost:5432" -ForegroundColor Cyan
Wait-ForTcpPort -HostName "127.0.0.1" -Port 5432
Write-Host ""

if (-not $SkipMigrations) {
    Write-Host "Applying database migrations..." -ForegroundColor Cyan
    Invoke-CheckedCommand `
        -Command { & $BackendPython -m alembic -c backend\alembic.ini upgrade head } `
        -FailureMessage "Alembic migration failed. Check whether PostgreSQL is running and DATABASE_URL in backend\.env is correct."
}

$BackendCommand = @"
Set-Location '$Root'
`$env:PYTHONUNBUFFERED = '1'
`$env:FRONTEND_ORIGIN = '$FrontendUrl'
& '$BackendPython' -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port $BackendPort
"@

$FrontendCommand = @"
Set-Location '$Root\frontend'
`$env:NEXT_PUBLIC_API_BASE_URL = '$BackendUrl'
& npm.cmd run dev -- --webpack --hostname 127.0.0.1 --port $FrontendPort
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
Write-Host "Waiting for backend health at $BackendUrl/health" -ForegroundColor Cyan
Wait-ForHttpEndpoint -Url "$BackendUrl/health"
Write-Host ""

Write-Host "Starting frontend at $FrontendUrl ..." -ForegroundColor Green
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-Command",
    $FrontendCommand
) -WindowStyle Normal
Write-Host "Waiting for frontend at $FrontendUrl" -ForegroundColor Cyan
Wait-ForHttpEndpoint -Url $FrontendUrl
Write-Host ""

if (-not $NoBrowser) {
    Start-Process $FrontendUrl
}

Write-Host ""
Write-Host "Project startup completed." -ForegroundColor Green
Write-Host "Backend:  $BackendUrl"
Write-Host "Frontend: $FrontendUrl"
Write-Host ""
Write-Host "Options:"
Write-Host "  .\start.ps1 -SkipMigrations  # do not run Alembic migrations"
Write-Host "  .\start.ps1 -NoBrowser       # do not open the browser"

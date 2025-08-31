param(
  [switch]$SkipE2E
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Section($name) {
  Write-Host "`n==== $name ====\n" -ForegroundColor Cyan
}

function Ensure-Success([string]$step) {
  if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: $step failed with code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
  }
}

# Ensure we are at the repo root regardless of where the script is called from
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '..'))

Section "Python venv"
if (-not (Test-Path .venv)) {
  Write-Host "Creating .venv..."
  python -m venv .venv
}
$py = Join-Path ".venv" "Scripts/python.exe"
if (-not (Test-Path $py)) {
  Write-Host "WARNING: .venv python not found, falling back to system python" -ForegroundColor Yellow
  $py = "python"
}

Section "Upgrade pip/setuptools/wheel"
& $py -m pip install -U pip setuptools wheel

Section "Install dev requirements"
& $py -m pip install -r requirements/dev.txt

Section "Generate protobufs"
& (Join-Path $PSScriptRoot 'gen_protos.ps1')
Ensure-Success "Generate protobufs"

Section "Static checks (ruff, black, mypy)"
# Ruff: try check, auto-fix if needed, then re-check
& $py -m ruff check .
if ($LASTEXITCODE -ne 0) {
  Write-Host "ruff issues found, applying --fix..." -ForegroundColor Yellow
  & $py -m ruff check --fix .
  & $py -m ruff check .
}
Ensure-Success "Ruff check"

# Black: check, format if needed, then re-check
& $py -m black --check .
if ($LASTEXITCODE -ne 0) {
  Write-Host "black issues found, applying formatting..." -ForegroundColor Yellow
  & $py -m black .
  & $py -m black --check .
}
Ensure-Success "Black check"

& $py -m mypy .
Ensure-Success "Mypy"

Section "Unit tests (OTEL/Kafka disabled)"
$env:OTEL_DISABLED = "1"
$env:KAFKA_DISABLED = "1"
& $py -m pytest -q
Ensure-Success "Pytest"

if (-not $SkipE2E) {
  Section "Docker Compose E2E"
  docker compose down -v
  docker compose up -d --build
  Write-Host "Waiting for services to be ready..."
  Start-Sleep -Seconds 60

  function Test-Health($url, [int]$Retries = 20, [int]$DelaySeconds = 3) {
    for ($i = 1; $i -le $Retries; $i++) {
      try {
        $res = Invoke-RestMethod -Uri $url -Method GET
        Write-Host "OK: $url ->" ($res | ConvertTo-Json -Compress)
        return
      }
      catch {
        Write-Host "Waiting ($i/$Retries): $url not ready yet..." -ForegroundColor Yellow
        Start-Sleep -Seconds $DelaySeconds
      }
    }
    Write-Host "ERROR: health check failed for $url after $Retries attempts" -ForegroundColor Red
    throw "Health check failed for $url"
  }

  try { Test-Health "http://localhost:8001/health" }
  catch {
    Write-Host "orders not healthy, dumping logs" -ForegroundColor Red
    docker logs orders --tail=200 2>$null
    throw
  }
  try { Test-Health "http://localhost:8002/health" }
  catch {
    Write-Host "payments not healthy, dumping logs" -ForegroundColor Red
    docker logs payments --tail=200 2>$null
    throw
  }
  try { Test-Health "http://localhost:8003/health" }
  catch {
    Write-Host "inventory not healthy, dumping logs" -ForegroundColor Red
    docker logs inventory --tail=200 2>$null
    throw
  }
  try { Test-Health "http://localhost:8004/health" }
  catch {
    Write-Host "orchestrator not healthy, dumping logs" -ForegroundColor Red
    docker logs orchestrator --tail=200 2>$null
    throw
  }

  Section "POST /orders"
  $body = @{ order_id = 'o-1'; user_id = 'u-1'; amount = 123.45 } | ConvertTo-Json
  $resp = Invoke-RestMethod -Uri "http://localhost:8001/orders" -Method POST -ContentType 'application/json' -Body $body
  Write-Host "POST /orders response:" ($resp | ConvertTo-Json -Compress)

  Section "Logs"
  docker logs orchestrator --since=2m --tail=200 2>$null
  docker logs orders --since=2m --tail=200 2>$null
  docker logs payments --since=2m --tail=200 2>$null
  docker logs inventory --since=2m --tail=200 2>$null
}

Section "Done!"
Write-Host "All checks completed successfully." -ForegroundColor Green

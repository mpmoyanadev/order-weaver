param()
$ErrorActionPreference = 'Stop'
$OUT_DIR = "common/proto"
if (-Not (Test-Path $OUT_DIR)) { New-Item -ItemType Directory -Path $OUT_DIR | Out-Null }
$initPy = Join-Path $OUT_DIR "__init__.py"
if (-Not (Test-Path $initPy)) { New-Item -ItemType File -Path $initPy | Out-Null }

# Ensure subpackages exist with __init__.py so that imports like
# `from common.proto.orders import orders_pb2` work on Windows
$subDirs = @("common", "orders", "payments", "inventory")
foreach ($d in $subDirs) {
  $dirPath = Join-Path $OUT_DIR $d
  if (-Not (Test-Path $dirPath)) { New-Item -ItemType Directory -Path $dirPath | Out-Null }
  $pkgInit = Join-Path $dirPath "__init__.py"
  if (-Not (Test-Path $pkgInit)) { New-Item -ItemType File -Path $pkgInit | Out-Null }
}

# Choose Python interpreter: prefer repo venv if exists
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$venvDir = Join-Path $repoRoot ".venv"
$venvPy = Join-Path (Join-Path $venvDir "Scripts") "python.exe"
if (Test-Path $venvPy) {
  $py = $venvPy
} else {
  $py = "python"
}
if (Get-Command protoc -ErrorAction SilentlyContinue) {
  protoc `
    -I proto `
    --python_out=$OUT_DIR `
    proto/common/event_envelope.proto `
    proto/orders/orders.proto `
    proto/payments/payments.proto `
    proto/inventory/inventory.proto
} else {
  & $py -m grpc_tools.protoc `
    -I proto `
    --python_out=$OUT_DIR `
    proto/common/event_envelope.proto `
    proto/orders/orders.proto `
    proto/payments/payments.proto `
    proto/inventory/inventory.proto
}
Write-Host "Protos generated into $OUT_DIR"

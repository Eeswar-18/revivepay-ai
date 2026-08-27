# Verify RevivePay-AI system integrity
# This script runs the verification steps outlined in STATUS.md

Write-Host "=== RevivePay-AI System Verification ===" -ForegroundColor Green

# Change to backend directory as specified in verification steps
Push-Location
Set-Location backend

# Run pytest
Write-Host "`nRunning pytest..." -ForegroundColor Yellow
& python -m pytest -q
if ($LASTEXITCODE -ne 0) {
    Write-Error "pytest failed with exit code $LASTEXITCODE"
    exit 1
}
Write-Host "✓ pytest passed" -ForegroundColor Green

# Run ruff format
Write-Host "`nRunning ruff format..." -ForegroundColor Yellow
& python -m ruff format .
if ($LASTEXITCODE -ne 0) {
    Write-Error "ruff format failed with exit code $LASTEXITCODE"
    exit 1
}
Write-Host "✓ ruff format completed" -ForegroundColor Green

# Run ruff check
Write-Host "`nRunning ruff check..." -ForegroundColor Yellow
& python -m ruff check .
if ($LASTEXITCODE -ne 0) {
    Write-Error "ruff check failed with exit code $LASTEXITCODE"
    exit 1
}
Write-Host "✓ ruff check passed" -ForegroundColor Green

# Run mypy
Write-Host "`nRunning mypy..." -ForegroundColor Yellow
& python -m mypy app
if ($LASTEXITCODE -ne 0) {
    Write-Error "mypy failed with exit code $LASTEXITCODE"
    exit 1
}
Write-Host "✓ mypy passed" -ForegroundColor Green

# Verify held-out boundary integrity
Write-Host "`nVerifying held-out boundary integrity..." -ForegroundColor Yellow

# Check git status of sim directory
$gitStatus = & git status --short app/sim/
if ($gitStatus) {
    Write-Warning "Unexpected changes in app/sim/:"
    Write-Warning $gitStatus
    Write-Error "Held-out boundary has been modified!"
    exit 1
}
Write-Host "✓ No changes in app/sim/" -ForegroundColor Green

# Check hash of world_config.yaml
$hash1 = & git hash-object app/sim/world_config.yaml
$hash2 = & git rev-parse :app/sim/world_config.yaml

if ($hash1 -ne $hash2) {
    Write-Error "Hash mismatch: git hash-object ($hash1) != git rev-parse ($hash2)"
    exit 1
}

$expectedHash = "d69e2fe3c47f0282b14fb87acb2c7aa115c005b2294a3a832bcc6c2b6ed49591"
if ($hash1 -ne $expectedHash) {
    Write-Error "World config hash mismatch:"
    Write-Error "  Expected: $expectedHash"
    Write-Error "  Actual:   $hash1"
    exit 1
}

Write-Host "✓ world_config.yaml hash verified" -ForegroundColor Green

Write-Host "`nAll verification steps passed!" -ForegroundColor Green
Write-Host "System is ready for development." -ForegroundColor Green

Pop-Location
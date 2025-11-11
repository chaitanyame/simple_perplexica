# PowerShell script to rebuild and restart research-api with SerperDev support

Write-Host "========================================"
Write-Host "Rebuilding Research API with SerperDev"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Change to research-service directory
Set-Location -Path $PSScriptRoot

Write-Host "Step 1: Stopping research-api container..." -ForegroundColor Yellow
docker compose stop research-api

Write-Host ""
Write-Host "Step 2: Rebuilding research-api with latest code..." -ForegroundColor Yellow
docker compose build --no-cache research-api

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "❌ Build failed! Check the error above." -ForegroundColor Red
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "Step 3: Starting research-api..." -ForegroundColor Yellow
docker compose up -d research-api

Write-Host ""
Write-Host "Step 4: Waiting for API to be ready (10 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host ""
Write-Host "Step 5: Testing API health..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8001/api/v1/health" -UseBasicParsing -ErrorAction Stop
    Write-Host "✅ API is responding: $($response.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "⚠️  API not responding yet. May need more time to start." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Step 6: Checking recent logs..." -ForegroundColor Yellow
docker compose logs --tail=20 research-api

Write-Host ""
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✅ Rebuild Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Refresh your Streamlit UI (http://localhost:8501)"
Write-Host "2. Try your search again: 'what is pydantic ai'"
Write-Host "3. Watch logs: docker compose logs -f research-api"
Write-Host ""
Write-Host "Look for these log messages:"
Write-Host "  - 'SerperDev returned X results' = ✅ Using SerperDev"
Write-Host "  - 'SearxNG returned X results' = Using fallback"
Write-Host "  - 'Cannot connect' = Both failing (check API keys)"
Write-Host ""
Read-Host "Press Enter to exit"

# Test with technical query

$body = @{
    query = "What are the latest developments in quantum computing in 2025?"
    focusMode = "webSearch"
    optimizationMode = "quality"
    stream = $false
} | ConvertTo-Json

Write-Host "Testing: What are the latest developments in quantum computing in 2025?" -ForegroundColor Cyan

$response = Invoke-RestMethod -Uri "http://localhost:3001/api/search" `
    -Method POST `
    -Body $body `
    -ContentType "application/json"

Write-Host "`nMetrics:" -ForegroundColor Yellow
Write-Host "  Length: $($response.message.Length) chars"
Write-Host "  Citations: $([regex]::Matches($response.message, '\[\d+\]').Count)"
Write-Host "  Headings: $([regex]::Matches($response.message, '^##\s+', 'Multiline').Count)"

Write-Host "`n=== Response Preview (First 800 chars) ===" -ForegroundColor Green
Write-Host $response.message.Substring(0, [Math]::Min(800, $response.message.Length))
Write-Host "..." -ForegroundColor Gray

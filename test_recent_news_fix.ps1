# Test the fix for time_range issue

$body = @{
    query = "what is the recent news of AI"
    focusMode = "webSearch"
    optimizationMode = "balanced"
    stream = $false
} | ConvertTo-Json

Write-Host "Testing: what is the recent news of AI" -ForegroundColor Cyan

try {
    $response = Invoke-RestMethod -Uri "http://localhost:3001/api/search" `
        -Method POST `
        -Body $body `
        -ContentType "application/json"

    Write-Host "`nSources: $($response.sources.Count)" -ForegroundColor Green
    Write-Host "Message length: $($response.message.Length) chars" -ForegroundColor Green
    
    if ($response.sources.Count -gt 0) {
        Write-Host "`nFirst 3 sources:" -ForegroundColor Yellow
        for ($i = 0; $i -lt [Math]::Min(3, $response.sources.Count); $i++) {
            Write-Host "  [$($i + 1)] $($response.sources[$i].title)" -ForegroundColor Cyan
            Write-Host "      $($response.sources[$i].url)" -ForegroundColor Gray
        }
        
        Write-Host "`nAnswer preview (first 500 chars):" -ForegroundColor Yellow
        Write-Host $response.message.Substring(0, [Math]::Min(500, $response.message.Length))
        Write-Host "..." -ForegroundColor Gray
    } else {
        Write-Host "`nERROR: No sources returned!" -ForegroundColor Red
        Write-Host "Message: $($response.message)" -ForegroundColor Red
    }
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
}

# Test URL/PDF processing in search endpoint
# This tests the complete flow with quality mode

$body = @{
    query = "What are the main features of Python?"
    focusMode = "webSearch"
    optimizationMode = "quality"  # Quality mode enables URL enrichment
    stream = $false
} | ConvertTo-Json

Write-Host "Testing search with URL enrichment (quality mode)..." -ForegroundColor Cyan
Write-Host "Query: What are the main features of Python?" -ForegroundColor Yellow

try {
    $response = Invoke-RestMethod -Uri "http://localhost:3001/api/search" `
        -Method POST `
        -Body $body `
        -ContentType "application/json"
    
    Write-Host "`n=== Response ===" -ForegroundColor Green
    Write-Host "Message length: $($response.message.Length) chars" -ForegroundColor Cyan
    Write-Host "`nSources ($($response.sources.Count)):" -ForegroundColor Cyan
    
    foreach ($source in $response.sources | Select-Object -First 5) {
        Write-Host "`n  Title: $($source.title)" -ForegroundColor Yellow
        Write-Host "  URL: $($source.url)" -ForegroundColor Gray
        Write-Host "  Content length: $($source.pageContent.Length) chars" -ForegroundColor Magenta
        
        # Check if this is enriched content (chunked URL)
        if ($source.title -match "chunk \d+/\d+") {
            Write-Host "  [ENRICHED - Full URL content fetched]" -ForegroundColor Green
        } else {
            Write-Host "  [Standard search snippet]" -ForegroundColor Gray
        }
    }
    
    Write-Host "`n=== Answer Preview ===" -ForegroundColor Green
    Write-Host $response.message.Substring(0, [Math]::Min(500, $response.message.Length))
    Write-Host "..." -ForegroundColor Gray
    
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}

Write-Host "`n=== Test Complete ===" -ForegroundColor Cyan

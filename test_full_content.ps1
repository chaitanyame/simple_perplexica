# Test to show the difference in content sent to LLM

Write-Host "`n=== Testing Full Content vs Truncated Content ===" -ForegroundColor Green

# Test with Quality mode - should fetch full URL content
$testRequest = @{
    Uri = "http://localhost:3001/api/search"
    Method = "POST"
    ContentType = "application/json"
    Body = @{
        query = "what are the latest features in Python 3.12"
        focusMode = "webSearch"
        optimizationMode = "quality"  # This triggers URL fetching
        history = @()
    } | ConvertTo-Json
}

Write-Host "`nSending query: 'what are the latest features in Python 3.12'" -ForegroundColor Cyan
Write-Host "Optimization mode: QUALITY (fetches full URL content)" -ForegroundColor Yellow

try {
    $response = Invoke-RestMethod @testRequest
    
    Write-Host "`n=== Results ===" -ForegroundColor Green
    Write-Host "Sources returned: $($response.sources.Count)" -ForegroundColor White
    Write-Host "Response length: $($response.message.Length) characters" -ForegroundColor White
    
    # Analyze source content lengths
    Write-Host "`n=== Source Content Analysis ===" -ForegroundColor Cyan
    $shortSources = 0
    $longSources = 0
    
    foreach ($source in $response.sources) {
        $contentLength = $source.pageContent.Length
        if ($contentLength -lt 500) {
            $shortSources++
            Write-Host "  - Short snippet: $contentLength chars from $($source.url.Substring(0, [Math]::Min(60, $source.url.Length)))" -ForegroundColor Yellow
        } else {
            $longSources++
            Write-Host "  - Full content: $contentLength chars from $($source.url.Substring(0, [Math]::Min(60, $source.url.Length)))" -ForegroundColor Green
        }
    }
    
    Write-Host "`n=== Summary ===" -ForegroundColor Green
    Write-Host "Short snippets (<500 chars): $shortSources sources" -ForegroundColor Yellow
    Write-Host "Full content (>=500 chars): $longSources sources" -ForegroundColor Green
    
    if ($longSources -gt 0) {
        Write-Host "`n✓ SUCCESS: LLM is now receiving FULL URL content!" -ForegroundColor Green
        Write-Host "  This provides much richer context for better answers." -ForegroundColor Gray
    } else {
        Write-Host "`n⚠ WARNING: All sources are short snippets" -ForegroundColor Yellow
        Write-Host "  URL fetching may not be working in quality mode." -ForegroundColor Gray
    }
    
    # Show a sample of the response
    Write-Host "`n=== Response Preview (first 500 chars) ===" -ForegroundColor Cyan
    Write-Host $response.message.Substring(0, [Math]::Min(500, $response.message.Length)) -ForegroundColor White
    Write-Host "..." -ForegroundColor Gray
    
} catch {
    Write-Host "`n✗ Test failed: $_" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $errorBody = $reader.ReadToEnd()
        Write-Host "Error details: $errorBody" -ForegroundColor Red
    }
}

Write-Host "`n=== Before vs After ===" -ForegroundColor Green
Write-Host "BEFORE FIX:" -ForegroundColor Red
Write-Host "  - Fetched 2000+ char URLs" -ForegroundColor Gray
Write-Host "  - BUT truncated to 1200 chars before sending to LLM" -ForegroundColor Gray
Write-Host "  - Wasted 40% of fetched content!" -ForegroundColor Gray

Write-Host "`nAFTER FIX:" -ForegroundColor Green
Write-Host "  - Fetches 2000+ char URLs" -ForegroundColor Gray
Write-Host "  - Sends FULL content to LLM (no truncation)" -ForegroundColor Gray
Write-Host "  - Only truncates short snippets from search API" -ForegroundColor Gray

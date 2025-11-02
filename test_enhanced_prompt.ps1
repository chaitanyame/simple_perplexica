# Test enhanced prompt generation with detailed response

Write-Host "`n=== Testing Enhanced Response Prompt ===" -ForegroundColor Cyan
Write-Host "Query: Explain the key features of Python programming language" -ForegroundColor Yellow

$body = @{
    query = "Explain the key features of Python programming language"
    focusMode = "webSearch"
    optimizationMode = "quality"
    stream = $false
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:3001/api/search" `
        -Method POST `
        -Body $body `
        -ContentType "application/json"
    
    Write-Host "`n=== Response Quality Metrics ===" -ForegroundColor Green
    Write-Host "Message length: $($response.message.Length) chars" -ForegroundColor Cyan
    Write-Host "Sources used: $($response.sources.Count)" -ForegroundColor Cyan
    
    # Count citations
    $citationCount = ([regex]::Matches($response.message, '\[\d+\]')).Count
    Write-Host "Total citations: $citationCount" -ForegroundColor Cyan
    
    # Check for headings
    $headingCount = ([regex]::Matches($response.message, '^##\s+', [System.Text.RegularExpressions.RegexOptions]::Multiline)).Count
    Write-Host "Section headings: $headingCount" -ForegroundColor Cyan
    
    # Check for bullet points
    $bulletCount = ([regex]::Matches($response.message, '^\s*[-*]\s+', [System.Text.RegularExpressions.RegexOptions]::Multiline)).Count
    Write-Host "Bullet points: $bulletCount" -ForegroundColor Cyan
    
    Write-Host "`n=== Full Response ===" -ForegroundColor Green
    Write-Host $response.message -ForegroundColor White
    
    Write-Host "`n=== Sources ===" -ForegroundColor Magenta
    for ($i = 0; $i -lt [Math]::Min(5, $response.sources.Count); $i++) {
        $source = $response.sources[$i]
        Write-Host "`n[$($i + 1)] $($source.title)" -ForegroundColor Yellow
        Write-Host "    URL: $($source.url)" -ForegroundColor Gray
        Write-Host "    Content: $($source.pageContent.Length) chars" -ForegroundColor Gray
    }
    
    Write-Host "`n=== Analysis ===" -ForegroundColor Cyan
    if ($citationCount -ge 10) {
        Write-Host "[OK] Good citation coverage ($citationCount citations)" -ForegroundColor Green
    } else {
        Write-Host "[WARN] Low citation coverage ($citationCount citations)" -ForegroundColor Yellow
    }
    
    if ($headingCount -ge 2) {
        Write-Host "[OK] Well-structured with $headingCount section headings" -ForegroundColor Green
    } else {
        Write-Host "[WARN] Could use more structure ($headingCount headings)" -ForegroundColor Yellow
    }
    
    if ($response.message.Length -ge 1500) {
        Write-Host "[OK] Comprehensive response ($($response.message.Length) chars)" -ForegroundColor Green
    } else {
        Write-Host "[WARN] Brief response ($($response.message.Length) chars)" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}

Write-Host "`n=== Test Complete ===" -ForegroundColor Cyan

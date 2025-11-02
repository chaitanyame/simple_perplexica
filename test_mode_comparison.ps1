# Compare speed vs quality mode to see URL enrichment impact

Write-Host "`n=== SPEED MODE (No URL Enrichment) ===" -ForegroundColor Cyan

$speedBody = @{
    query = "What is FastAPI?"
    focusMode = "webSearch"
    optimizationMode = "speed"
    stream = $false
} | ConvertTo-Json

$speedResponse = Invoke-RestMethod -Uri "http://localhost:3001/api/search" `
    -Method POST `
    -Body $speedBody `
    -ContentType "application/json"

Write-Host "Sources: $($speedResponse.sources.Count)"
Write-Host "Average content length: $([int](($speedResponse.sources | Measure-Object -Property {$_.pageContent.Length} -Average).Average)) chars"
Write-Host "Message length: $($speedResponse.message.Length) chars"

Write-Host "`n=== QUALITY MODE (With URL Enrichment) ===" -ForegroundColor Cyan

$qualityBody = @{
    query = "What is FastAPI?"
    focusMode = "webSearch"
    optimizationMode = "quality"
    stream = $false
} | ConvertTo-Json

$qualityResponse = Invoke-RestMethod -Uri "http://localhost:3001/api/search" `
    -Method POST `
    -Body $qualityBody `
    -ContentType "application/json"

Write-Host "Sources: $($qualityResponse.sources.Count)"
Write-Host "Average content length: $([int](($qualityResponse.sources | Measure-Object -Property {$_.pageContent.Length} -Average).Average)) chars"
Write-Host "Message length: $($qualityResponse.message.Length) chars"

Write-Host "`n=== Enriched Sources in Quality Mode ===" -ForegroundColor Green
$enriched = $qualityResponse.sources | Where-Object { $_.title -match "chunk \d+/\d+" }
Write-Host "Enriched sources: $($enriched.Count)"
foreach ($source in $enriched) {
    Write-Host "  - $($source.title): $($source.pageContent.Length) chars" -ForegroundColor Yellow
}

Write-Host "`n=== Comparison ===" -ForegroundColor Magenta
Write-Host "Speed mode avg content: $([int](($speedResponse.sources | Measure-Object -Property {$_.pageContent.Length} -Average).Average)) chars"
Write-Host "Quality mode avg content: $([int](($qualityResponse.sources | Measure-Object -Property {$_.pageContent.Length} -Average).Average)) chars"
$improvement = [int]((($qualityResponse.sources | Measure-Object -Property {$_.pageContent.Length} -Average).Average) / (($speedResponse.sources | Measure-Object -Property {$_.pageContent.Length} -Average).Average) * 100)
Write-Host "Improvement: $improvement%" -ForegroundColor Green

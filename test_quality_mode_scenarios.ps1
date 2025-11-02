# PowerShell Test Script for Quality Mode with Various Scenarios
# Tests URL fetching, reranking, full content delivery, and different query types

$baseUrl = "http://localhost:3001/api/search"
$testResults = @()

function Test-SearchScenario {
    param(
        [string]$ScenarioName,
        [string]$Query,
        [string]$FocusMode = "webSearch",
        [string]$OptimizationMode = "quality",
        [array]$History = @()
    )
    
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "SCENARIO: $ScenarioName" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Query: $Query" -ForegroundColor White
    Write-Host "Focus: $FocusMode | Optimization: $OptimizationMode" -ForegroundColor Gray
    
    $body = @{
        query = $Query
        focusMode = $FocusMode
        optimizationMode = $OptimizationMode
        history = $History
    } | ConvertTo-Json -Depth 10
    
    $startTime = Get-Date
    
    try {
        $response = Invoke-RestMethod -Uri $baseUrl -Method POST -ContentType "application/json" -Body $body -ErrorAction Stop
        
        $endTime = Get-Date
        $duration = ($endTime - $startTime).TotalSeconds
        
        # Analyze response
        $sourcesCount = $response.sources.Count
        $responseLength = $response.message.Length
        $citationCount = ([regex]::Matches($response.message, '\[\d+\]')).Count
        
        # Analyze content types
        $shortSnippets = 0
        $fullContent = 0
        $totalContentLength = 0
        
        foreach ($source in $response.sources) {
            $contentLength = $source.pageContent.Length
            $totalContentLength += $contentLength
            if ($contentLength -lt 500) {
                $shortSnippets++
            } else {
                $fullContent++
            }
        }
        
        $avgContentLength = if ($sourcesCount -gt 0) { [math]::Round($totalContentLength / $sourcesCount) } else { 0 }
        
        Write-Host "`n✓ SUCCESS" -ForegroundColor Green
        Write-Host "  Duration: $([math]::Round($duration, 2))s" -ForegroundColor Gray
        Write-Host "  Sources: $sourcesCount (Short: $shortSnippets, Full: $fullContent)" -ForegroundColor Gray
        Write-Host "  Avg content/source: $avgContentLength chars" -ForegroundColor Gray
        Write-Host "  Response: $responseLength chars with $citationCount citations" -ForegroundColor Gray
        
        # Show first few sources
        Write-Host "`n  Top Sources:" -ForegroundColor Cyan
        for ($i = 0; $i -lt [Math]::Min(3, $sourcesCount); $i++) {
            $src = $response.sources[$i]
            $urlShort = if ($src.url.Length -gt 60) { $src.url.Substring(0, 57) + "..." } else { $src.url }
            Write-Host "    [$($i+1)] $($src.pageContent.Length) chars - $urlShort" -ForegroundColor White
        }
        
        # Show response preview
        Write-Host "`n  Response Preview:" -ForegroundColor Cyan
        $preview = if ($responseLength -gt 300) { $response.message.Substring(0, 297) + "..." } else { $response.message }
        Write-Host "    $preview" -ForegroundColor White
        
        # Store results
        $script:testResults += [PSCustomObject]@{
            Scenario = $ScenarioName
            Success = $true
            Duration = [math]::Round($duration, 2)
            Sources = $sourcesCount
            FullContentSources = $fullContent
            AvgContentLength = $avgContentLength
            ResponseLength = $responseLength
            Citations = $citationCount
        }
        
        return $response
        
    } catch {
        $endTime = Get-Date
        $duration = ($endTime - $startTime).TotalSeconds
        
        Write-Host "`n✗ FAILED" -ForegroundColor Red
        Write-Host "  Duration: $([math]::Round($duration, 2))s" -ForegroundColor Gray
        Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
        
        if ($_.Exception.Response) {
            $reader = [System.IO.StreamReader]::new($_.Exception.Response.GetResponseStream())
            $errorBody = $reader.ReadToEnd()
            Write-Host "  Details: $errorBody" -ForegroundColor Yellow
        }
        
        # Store failure
        $script:testResults += [PSCustomObject]@{
            Scenario = $ScenarioName
            Success = $false
            Duration = [math]::Round($duration, 2)
            Sources = 0
            FullContentSources = 0
            AvgContentLength = 0
            ResponseLength = 0
            Citations = 0
            Error = $_.Exception.Message
        }
        
        return $null
    }
}

Write-Host "`n╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Quality Mode API Test Suite - Various Scenarios          ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

# Scenario 1: Recent news with temporal detection
Test-SearchScenario `
    -ScenarioName "Recent News (Temporal Detection)" `
    -Query "what is the latest news about AI developments" `
    -FocusMode "webSearch" `
    -OptimizationMode "quality"

Start-Sleep -Seconds 2

# Scenario 2: Technical documentation (should fetch full content)
Test-SearchScenario `
    -ScenarioName "Technical Documentation" `
    -Query "Python 3.12 new features and improvements" `
    -FocusMode "webSearch" `
    -OptimizationMode "quality"

Start-Sleep -Seconds 2

# Scenario 3: Academic research
Test-SearchScenario `
    -ScenarioName "Academic Research" `
    -Query "transformer architecture in neural networks" `
    -FocusMode "academicSearch" `
    -OptimizationMode "quality"

Start-Sleep -Seconds 2

# Scenario 4: Comparison query
Test-SearchScenario `
    -ScenarioName "Comparison Query" `
    -Query "React vs Vue vs Angular for enterprise applications" `
    -FocusMode "webSearch" `
    -OptimizationMode "quality"

Start-Sleep -Seconds 2

# Scenario 5: How-to/Tutorial query
Test-SearchScenario `
    -ScenarioName "How-To Query" `
    -Query "how to deploy FastAPI application with Docker and Kubernetes" `
    -FocusMode "webSearch" `
    -OptimizationMode "quality"

Start-Sleep -Seconds 2

# Scenario 6: Multi-turn conversation (with history)
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "SCENARIO: Multi-Turn Conversation" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan

$history1 = Test-SearchScenario `
    -ScenarioName "Multi-Turn: Initial Query" `
    -Query "What is machine learning?" `
    -FocusMode "webSearch" `
    -OptimizationMode "quality"

if ($history1) {
    Start-Sleep -Seconds 2
    
    # Second turn with history
    $conversationHistory = @(
        @("What is machine learning?", $history1.message)
    )
    
    Test-SearchScenario `
        -ScenarioName "Multi-Turn: Follow-up Query" `
        -Query "How does it differ from deep learning?" `
        -FocusMode "webSearch" `
        -OptimizationMode "quality" `
        -History $conversationHistory
}

Start-Sleep -Seconds 2

# Scenario 7: Code-specific query
Test-SearchScenario `
    -ScenarioName "Code Example Query" `
    -Query "FastAPI dependency injection examples with database" `
    -FocusMode "webSearch" `
    -OptimizationMode "quality"

Start-Sleep -Seconds 2

# Scenario 8: Current events (this week)
Test-SearchScenario `
    -ScenarioName "Current Events (This Week)" `
    -Query "major tech announcements this week" `
    -FocusMode "webSearch" `
    -OptimizationMode "quality"

Start-Sleep -Seconds 2

# Scenario 9: Reddit-specific search
Test-SearchScenario `
    -ScenarioName "Reddit Community Search" `
    -Query "best practices for FastAPI production deployment" `
    -FocusMode "redditSearch" `
    -OptimizationMode "quality"

Start-Sleep -Seconds 2

# Scenario 10: YouTube search
Test-SearchScenario `
    -ScenarioName "YouTube Video Search" `
    -Query "Python async programming tutorials" `
    -FocusMode "youtubeSearch" `
    -OptimizationMode "quality"

# Generate Summary Report
Write-Host "`n`n╔════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║              TEST RESULTS SUMMARY                          ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Green

$successCount = ($testResults | Where-Object { $_.Success }).Count
$totalCount = $testResults.Count
$successRate = [math]::Round(($successCount / $totalCount) * 100, 1)

Write-Host "`nOverall Statistics:" -ForegroundColor Cyan
Write-Host "  Total Scenarios: $totalCount" -ForegroundColor White
Write-Host "  Successful: $successCount ($successRate%)" -ForegroundColor Green
Write-Host "  Failed: $($totalCount - $successCount)" -ForegroundColor $(if ($totalCount -eq $successCount) { "Gray" } else { "Red" })

$avgDuration = [math]::Round(($testResults | Measure-Object -Property Duration -Average).Average, 2)
$avgSources = [math]::Round(($testResults | Where-Object { $_.Success } | Measure-Object -Property Sources -Average).Average, 1)
$avgFullContent = [math]::Round(($testResults | Where-Object { $_.Success } | Measure-Object -Property FullContentSources -Average).Average, 1)
$avgResponseLength = [math]::Round(($testResults | Where-Object { $_.Success } | Measure-Object -Property ResponseLength -Average).Average, 0)
$avgCitations = [math]::Round(($testResults | Where-Object { $_.Success } | Measure-Object -Property Citations -Average).Average, 1)

Write-Host "`nPerformance Metrics (Successful Tests):" -ForegroundColor Cyan
Write-Host "  Avg Duration: $avgDuration seconds" -ForegroundColor White
Write-Host "  Avg Sources: $avgSources sources/query" -ForegroundColor White
Write-Host "  Avg Full Content Sources: $avgFullContent/query" -ForegroundColor White
Write-Host "  Avg Response Length: $avgResponseLength chars" -ForegroundColor White
Write-Host "  Avg Citations: $avgCitations citations/response" -ForegroundColor White

Write-Host "`nDetailed Results:" -ForegroundColor Cyan
$testResults | Format-Table -AutoSize -Property Scenario, Success, Duration, Sources, FullContentSources, AvgContentLength, ResponseLength, Citations

# Content Quality Analysis
$fullContentTests = $testResults | Where-Object { $_.Success -and $_.FullContentSources -gt 0 }
if ($fullContentTests) {
    $fullContentRate = [math]::Round(($fullContentTests.Count / $successCount) * 100, 1)
    Write-Host "`nContent Quality:" -ForegroundColor Cyan
    Write-Host "  Queries with full URL content: $($fullContentTests.Count)/$successCount ($fullContentRate%)" -ForegroundColor Green
    Write-Host "  This means quality mode URL fetching is working!" -ForegroundColor Gray
}

# Save detailed results to file
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$reportFile = "test_results_$timestamp.json"
$testResults | ConvertTo-Json -Depth 10 | Out-File $reportFile
Write-Host "`n✓ Detailed results saved to: $reportFile" -ForegroundColor Green

Write-Host "`n════════════════════════════════════════════════════════════`n" -ForegroundColor Cyan

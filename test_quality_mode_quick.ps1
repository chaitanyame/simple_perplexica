# Quick Quality Mode Test - Individual Scenarios
# Usage: Run individual test blocks as needed

$baseUrl = "http://localhost:3001/api/search"

# ============================================================================
# EXAMPLE 1: Recent News (Tests temporal detection + URL fetching)
# ============================================================================
$body = @{
    query = "what are the latest developments in AI this week"
    focusMode = "webSearch"
    optimizationMode = "quality"
    history = @()
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri $baseUrl -Method POST -ContentType "application/json" -Body $body
Write-Host "Sources: $($response.sources.Count)" -ForegroundColor Cyan
Write-Host "Response length: $($response.message.Length) chars" -ForegroundColor Cyan
Write-Host "Full content sources: $(($response.sources | Where-Object { $_.pageContent.Length -ge 500 }).Count)" -ForegroundColor Green
Write-Host "`nResponse:" -ForegroundColor Yellow
Write-Host $response.message


# ============================================================================
# EXAMPLE 2: Technical Documentation (Should fetch full URL content)
# ============================================================================
$body = @{
    query = "Python 3.12 new features"
    focusMode = "webSearch"
    optimizationMode = "quality"
    history = @()
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri $baseUrl -Method POST -ContentType "application/json" -Body $body
Write-Host "`nSources:" -ForegroundColor Cyan
foreach ($src in $response.sources | Select-Object -First 5) {
    Write-Host "  - $($src.pageContent.Length) chars: $($src.url.Substring(0, [Math]::Min(80, $src.url.Length)))" -ForegroundColor White
}
Write-Host "`nResponse:" -ForegroundColor Yellow
Write-Host $response.message


# ============================================================================
# EXAMPLE 3: Comparison Query
# ============================================================================
$body = @{
    query = "React vs Vue comparison for 2024"
    focusMode = "webSearch"
    optimizationMode = "quality"
    history = @()
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri $baseUrl -Method POST -ContentType "application/json" -Body $body
Write-Host "`nCitations: $(([regex]::Matches($response.message, '\[\d+\]')).Count)" -ForegroundColor Cyan
Write-Host "Response:" -ForegroundColor Yellow
Write-Host $response.message


# ============================================================================
# EXAMPLE 4: How-To Query (Tests comprehensive content)
# ============================================================================
$body = @{
    query = "how to deploy FastAPI with Docker step by step"
    focusMode = "webSearch"
    optimizationMode = "quality"
    history = @()
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri $baseUrl -Method POST -ContentType "application/json" -Body $body
Write-Host "`nResponse:" -ForegroundColor Yellow
Write-Host $response.message


# ============================================================================
# EXAMPLE 5: Academic Search
# ============================================================================
$body = @{
    query = "transformer architecture research papers"
    focusMode = "academicSearch"
    optimizationMode = "quality"
    history = @()
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri $baseUrl -Method POST -ContentType "application/json" -Body $body
Write-Host "`nAcademic sources: $($response.sources.Count)" -ForegroundColor Cyan
Write-Host "Response:" -ForegroundColor Yellow
Write-Host $response.message


# ============================================================================
# EXAMPLE 6: Multi-Turn Conversation
# ============================================================================
# First query
$body1 = @{
    query = "What is FastAPI?"
    focusMode = "webSearch"
    optimizationMode = "quality"
    history = @()
} | ConvertTo-Json

$response1 = Invoke-RestMethod -Uri $baseUrl -Method POST -ContentType "application/json" -Body $body1
Write-Host "`n[Turn 1] Response:" -ForegroundColor Yellow
Write-Host $response1.message

# Follow-up query with history
$body2 = @{
    query = "How does it compare to Flask?"
    focusMode = "webSearch"
    optimizationMode = "quality"
    history = @(
        @("What is FastAPI?", $response1.message)
    )
} | ConvertTo-Json -Depth 10

$response2 = Invoke-RestMethod -Uri $baseUrl -Method POST -ContentType "application/json" -Body $body2
Write-Host "`n[Turn 2] Response:" -ForegroundColor Yellow
Write-Host $response2.message


# ============================================================================
# EXAMPLE 7: Reddit Search
# ============================================================================
$body = @{
    query = "best practices for Python async programming"
    focusMode = "redditSearch"
    optimizationMode = "quality"
    history = @()
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri $baseUrl -Method POST -ContentType "application/json" -Body $body
Write-Host "`nReddit sources: $($response.sources.Count)" -ForegroundColor Cyan
Write-Host "Response:" -ForegroundColor Yellow
Write-Host $response.message


# ============================================================================
# EXAMPLE 8: YouTube Search
# ============================================================================
$body = @{
    query = "Python FastAPI tutorial"
    focusMode = "youtubeSearch"
    optimizationMode = "quality"
    history = @()
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri $baseUrl -Method POST -ContentType "application/json" -Body $body
Write-Host "`nYouTube sources: $($response.sources.Count)" -ForegroundColor Cyan
Write-Host "Response:" -ForegroundColor Yellow
Write-Host $response.message


# ============================================================================
# EXAMPLE 9: Code Examples
# ============================================================================
$body = @{
    query = "FastAPI dependency injection with SQLAlchemy examples"
    focusMode = "webSearch"
    optimizationMode = "quality"
    history = @()
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri $baseUrl -Method POST -ContentType "application/json" -Body $body
Write-Host "`nResponse:" -ForegroundColor Yellow
Write-Host $response.message


# ============================================================================
# EXAMPLE 10: Current Events (Tests time_range detection)
# ============================================================================
$body = @{
    query = "breaking tech news today"
    focusMode = "webSearch"
    optimizationMode = "quality"
    history = @()
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri $baseUrl -Method POST -ContentType "application/json" -Body $body
Write-Host "`nResponse:" -ForegroundColor Yellow
Write-Host $response.message


# ============================================================================
# QUICK ANALYSIS HELPER
# ============================================================================
function Analyze-Response {
    param($response)
    
    $fullContent = ($response.sources | Where-Object { $_.pageContent.Length -ge 500 }).Count
    $shortSnippets = ($response.sources | Where-Object { $_.pageContent.Length -lt 500 }).Count
    $avgLength = [math]::Round(($response.sources | Measure-Object -Property { $_.pageContent.Length } -Average).Average, 0)
    $citations = ([regex]::Matches($response.message, '\[\d+\]')).Count
    
    Write-Host "`n=== Analysis ===" -ForegroundColor Cyan
    Write-Host "Total sources: $($response.sources.Count)" -ForegroundColor White
    Write-Host "Full content (>=500 chars): $fullContent" -ForegroundColor Green
    Write-Host "Short snippets (<500 chars): $shortSnippets" -ForegroundColor Yellow
    Write-Host "Avg content length: $avgLength chars" -ForegroundColor White
    Write-Host "Response length: $($response.message.Length) chars" -ForegroundColor White
    Write-Host "Citations: $citations" -ForegroundColor White
}

# Example usage:
# Analyze-Response $response

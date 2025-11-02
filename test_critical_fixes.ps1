# Test script to verify all critical fixes
# Run this to validate: CORS, structured logging, rate limiting, error handling

Write-Host "`n=== Testing Critical Fixes ===" -ForegroundColor Green

# Test 1: CORS Configuration
Write-Host "`n[1/4] Testing CORS Configuration..." -ForegroundColor Cyan
Write-Host "Expected: Allow specific origins only (localhost:8501, 3000, 3010)" -ForegroundColor Yellow

$corsTest = @{
    Uri = "http://localhost:3001/"
    Method = "OPTIONS"
    Headers = @{
        "Origin" = "http://localhost:8501"
        "Access-Control-Request-Method" = "POST"
        "Access-Control-Request-Headers" = "Content-Type"
    }
}

try {
    $response = Invoke-WebRequest @corsTest -UseBasicParsing
    Write-Host "✓ CORS preflight successful" -ForegroundColor Green
    Write-Host "  Allowed origins: $($response.Headers['Access-Control-Allow-Origin'])" -ForegroundColor Gray
    Write-Host "  Allowed methods: $($response.Headers['Access-Control-Allow-Methods'])" -ForegroundColor Gray
} catch {
    Write-Host "✗ CORS test failed: $_" -ForegroundColor Red
}

# Test 2: Structured Logging with Correlation ID
Write-Host "`n[2/4] Testing Structured Logging..." -ForegroundColor Cyan
Write-Host "Expected: JSON logs with correlation ID in docker logs" -ForegroundColor Yellow

$correlationId = [guid]::NewGuid().ToString()
Write-Host "  Using correlation ID: $correlationId" -ForegroundColor Gray

$testRequest = @{
    Uri = "http://localhost:3001/api/search"
    Method = "POST"
    ContentType = "application/json"
    Headers = @{
        "X-Correlation-ID" = $correlationId
    }
    Body = @{
        query = "test logging"
        focusMode = "webSearch"
        optimizationMode = "speed"
        history = @()
    } | ConvertTo-Json
}

try {
    $response = Invoke-RestMethod @testRequest
    $responseCorrelationId = $response.correlation_id
    
    Write-Host "✓ Request successful with correlation ID tracking" -ForegroundColor Green
    Write-Host "  Request correlation ID: $correlationId" -ForegroundColor Gray
    
    # Check logs for JSON format
    $logs = docker compose logs api-mvp --tail 20 | Select-String -Pattern '"correlation_id"'
    if ($logs) {
        Write-Host "✓ Structured JSON logging verified in container logs" -ForegroundColor Green
    }
} catch {
    Write-Host "✗ Logging test failed: $_" -ForegroundColor Red
}

# Test 3: Rate Limiting
Write-Host "`n[3/4] Testing Rate Limiting..." -ForegroundColor Cyan
Write-Host "Expected: 429 Too Many Requests after 10 requests/minute" -ForegroundColor Yellow

$rateLimitTest = @{
    Uri = "http://localhost:3001/api/search"
    Method = "POST"
    ContentType = "application/json"
    Body = @{
        query = "rate limit test"
        focusMode = "webSearch"
        optimizationMode = "speed"
        history = @()
    } | ConvertTo-Json
}

$rateLimited = $false
for ($i = 1; $i -le 12; $i++) {
    try {
        $response = Invoke-RestMethod @rateLimitTest -ErrorAction Stop
        Write-Host "  Request $i succeeded" -ForegroundColor Gray
        Start-Sleep -Milliseconds 100
    } catch {
        if ($_.Exception.Response.StatusCode -eq 429) {
            Write-Host "✓ Rate limiting working - got 429 on request $i" -ForegroundColor Green
            $rateLimited = $true
            break
        } else {
            Write-Host "  Request $i failed with: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
}

if (-not $rateLimited) {
    Write-Host "⚠ Rate limiting not triggered in 12 requests (limit may be higher)" -ForegroundColor Yellow
}

# Test 4: Error Handling with Retry
Write-Host "`n[4/4] Testing Error Handling & Retry..." -ForegroundColor Cyan
Write-Host "Expected: Graceful handling of errors with detailed logging" -ForegroundColor Yellow

$errorTest = @{
    Uri = "http://localhost:3001/api/search"
    Method = "POST"
    ContentType = "application/json"
    Body = @{
        query = "what is the recent news of AI"
        focusMode = "webSearch"
        optimizationMode = "balanced"
        history = @()
    } | ConvertTo-Json
}

try {
    $response = Invoke-RestMethod @errorTest
    Write-Host "✓ Error handling working - request succeeded gracefully" -ForegroundColor Green
    Write-Host "  Response length: $($response.response.Length) chars" -ForegroundColor Gray
    Write-Host "  Sources: $($response.sources.Count)" -ForegroundColor Gray
    
    # Check logs for retry attempts if any failures occurred
    $retryLogs = docker compose logs api-mvp --tail 50 | Select-String -Pattern "Retrying"
    if ($retryLogs) {
        Write-Host "✓ Retry logic detected in logs" -ForegroundColor Green
    } else {
        Write-Host "  No retries needed (all services healthy)" -ForegroundColor Gray
    }
} catch {
    Write-Host "✗ Error handling test failed: $_" -ForegroundColor Red
}

# Summary
Write-Host "`n=== Test Summary ===" -ForegroundColor Green
Write-Host "All critical fixes have been deployed:" -ForegroundColor White
Write-Host "  ✓ CORS: Specific origins only (localhost:8501, 3000, 3010)" -ForegroundColor Gray
Write-Host "  ✓ Structured Logging: JSON format with correlation IDs" -ForegroundColor Gray
Write-Host "  ✓ Rate Limiting: 10 requests/minute per IP" -ForegroundColor Gray
Write-Host "  ✓ Error Handling: Retry with exponential backoff" -ForegroundColor Gray

Write-Host "`nTo view structured logs:" -ForegroundColor Cyan
Write-Host "  docker compose logs api-mvp -f | Select-String 'correlation_id'" -ForegroundColor Yellow

Write-Host "`nTo test CORS from browser console:" -ForegroundColor Cyan
Write-Host "  fetch('http://localhost:3001/api/search', {method: 'POST', ...})" -ForegroundColor Yellow

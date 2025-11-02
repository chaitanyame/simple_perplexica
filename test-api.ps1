# Test the API with PowerShell
$body = @{
  query = "give me yesterday and today news of USA"
  focusMode = "webSearch"
  optimizationMode = "quality"
  systemInstructions = "Prioritize trusted, recent sources; highlight consensus vs uncertainty."
  history = @(
    @("User opening", "Assistant greeting"),
    @("Follow-up question", "Prior brief answer")
  )
  stream = $false
}

$uri = "http://localhost:3001/api/search"
try {
  $json = $body | ConvertTo-Json -Depth 8
  $res  = Invoke-WebRequest -Uri $uri -Method POST -ContentType "application/json" -Body $json -TimeoutSec 180 -ErrorAction Stop
  "Status: $($res.StatusCode)"
  $data = $res.Content | ConvertFrom-Json
  ""
  "=== MESSAGE ==="
  $data.message
  ""
  "=== SOURCES ==="
  $data.sources | Select-Object -First 10 | Format-Table title, url -AutoSize
} catch {
  "Request failed:"
  $_.Exception.Message
  if ($_.Exception.Response) {
    $_.Exception.Response | ConvertTo-Json -Depth 3
  }
}

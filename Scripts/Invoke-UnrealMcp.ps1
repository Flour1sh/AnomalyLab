param(
    [Parameter(Mandatory = $true)]
    [string]$ToolName,

    [Parameter(Mandatory = $true)]
    [string]$ArgumentsJson,

    [string]$ToolsetName = "",

    [string]$OutputImagePath = ""
)

$uri = "http://127.0.0.1:8000/mcp"
$baseHeaders = @{ Accept = "application/json, text/event-stream" }
$initialize = @{
    jsonrpc = "2.0"
    id = 1
    method = "initialize"
    params = @{
        protocolVersion = "2025-06-18"
        capabilities = @{}
        clientInfo = @{ name = "Codex"; version = "1.0" }
    }
} | ConvertTo-Json -Depth 10 -Compress

$initialResponse = Invoke-WebRequest -Uri $uri -Method Post -Headers $baseHeaders -ContentType "application/json" -Body $initialize -TimeoutSec 60
$sessionId = $initialResponse.Headers["Mcp-Session-Id"][0]
$sessionHeaders = @{
    Accept = "application/json, text/event-stream"
    "Mcp-Session-Id" = $sessionId
}

$initialized = @{ jsonrpc = "2.0"; method = "notifications/initialized"; params = @{} } | ConvertTo-Json -Compress
Invoke-WebRequest -Uri $uri -Method Post -Headers $sessionHeaders -ContentType "application/json" -Body $initialized -TimeoutSec 60 | Out-Null

$arguments = $ArgumentsJson | ConvertFrom-Json -AsHashtable
$callArguments = @{ tool_name = $ToolName; arguments = $arguments }
if ($ToolsetName) {
    $callArguments.toolset_name = $ToolsetName
}
$request = @{
    jsonrpc = "2.0"
    id = 2
    method = "tools/call"
    params = @{
        name = "call_tool"
        arguments = $callArguments
    }
} | ConvertTo-Json -Depth 30 -Compress

$response = Invoke-WebRequest -Uri $uri -Method Post -Headers $sessionHeaders -ContentType "application/json" -Body $request -TimeoutSec 120
$content = $response.Content
if ($content.StartsWith("event: message")) {
    $content = ($content -split "`ndata: ", 2)[1]
}

if ($OutputImagePath) {
    $envelope = $content | ConvertFrom-Json
    $toolPayload = $envelope.result.content[0].text | ConvertFrom-Json
    $image = $toolPayload.returnValue.image
    if (-not $image) {
        $image = $toolPayload.returnValue
    }
    if (-not $image.data) {
        throw "The MCP response did not contain image data."
    }

    $resolvedImagePath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputImagePath)
    $imageDirectory = Split-Path -Parent $resolvedImagePath
    if ($imageDirectory -and -not (Test-Path -LiteralPath $imageDirectory)) {
        New-Item -ItemType Directory -Path $imageDirectory -Force | Out-Null
    }
    [System.IO.File]::WriteAllBytes($resolvedImagePath, [Convert]::FromBase64String($image.data))
    @{ imagePath = $resolvedImagePath; mimeType = $image.mimeType } | ConvertTo-Json -Compress
    exit 0
}

$content

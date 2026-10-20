param([ValidateSet('build','inspect','validate')][string]$Mode = 'build')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$scriptNames = @{build='build_t05.py';inspect='inspect_t05.py';validate='validate_t05.py'}
$scriptPath = Join-Path $PSScriptRoot $scriptNames[$Mode]
$projectPath = Join-Path $projectRoot '我的项目3.uproject'
$logPath = Join-Path $projectRoot "Saved/Logs/T05_$Mode.log"
if (Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue) {
    throw 'Close other Unreal Editor processes before building assets on disk.'
}
for ($stage = 0; $stage -lt 2; $stage++) {
    # BlueprintActionDatabase intentionally skips Blueprint registration in commandlets.
    # Use the engine's Python batch executor, hidden and without a rendered viewport.
    $engineArgs = @('"' + $projectPath + '"', '"-ExecutePythonScript=' + $scriptPath + '"',
        '-DisablePlugins=AllToolsets,ModelContextProtocol,MCPClientToolset',
        '-EnablePlugins=EditorToolset,PythonScriptPlugin,UMGToolSet',
        '-unattended', '-nosplash', '-nullrhi', '-RenderOffscreen', '-UTF8Output',
        '"-abslog=' + $logPath + '"')
    $worker = Start-Process -FilePath 'E:/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList ($engineArgs -join ' ') -WindowStyle Hidden -PassThru -Wait
    if ($worker.ExitCode -ne 0 -or (Select-String -LiteralPath $logPath -Pattern 'LogPython: Error:' -Quiet)) {
        throw "T05 $Mode failed. See $logPath"
    }
    if ($Mode -eq 'build' -and (Select-String -LiteralPath $logPath -SimpleMatch '[T05] SCHEMA PASS' -Quiet)) { continue }
    $marker = @{build='[T05] BUILD PASS';inspect='[T05] PREFLIGHT PASS';validate='[T05] STRUCTURAL PASS'}[$Mode]
    if (-not (Select-String -LiteralPath $logPath -SimpleMatch $marker -Quiet)) { throw "Missing completion marker: $marker" }
    Write-Output "$marker - $logPath"
    break
}

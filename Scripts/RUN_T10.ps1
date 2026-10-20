param([ValidateSet('build','validate')][string]$Mode = 'build')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$scriptPath = Join-Path $PSScriptRoot "$($Mode)_t10.py"
$projectPath = Join-Path $projectRoot '我的项目3.uproject'
if (Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue) {
    throw 'Close other Unreal Editor processes before writing assets on disk.'
}
for ($stage = 0; $stage -lt 2; $stage++) {
    $logPath = Join-Path $projectRoot "Saved/Logs/T10_$($Mode)_$stage.log"
    $engineArgs = @('"' + $projectPath + '"', '"-ExecutePythonScript=' + $scriptPath + '"',
        '-DisablePlugins=AllToolsets,ModelContextProtocol,MCPClientToolset',
        '-EnablePlugins=EditorToolset,PythonScriptPlugin,UMGToolSet',
        '-unattended', '-nosplash', '-nullrhi', '-RenderOffscreen', '-UTF8Output',
        '"-abslog=' + $logPath + '"')
    $worker = Start-Process -FilePath 'E:/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList ($engineArgs -join ' ') -WindowStyle Hidden -PassThru -Wait
    if ($worker.ExitCode -ne 0 -or (Select-String -LiteralPath $logPath -Pattern 'LogPython: Error:' -Quiet)) {
        throw "T10 $Mode failed. See $logPath"
    }
    if ($Mode -eq 'build' -and (Select-String -LiteralPath $logPath -SimpleMatch '[T10] SCHEMA PASS' -Quiet)) { continue }
    $marker = if ($Mode -eq 'build') { '[T10] BUILD PASS' } else { '[T10] STRUCTURAL PASS' }
    if (-not (Select-String -LiteralPath $logPath -SimpleMatch $marker -Quiet)) { throw "Missing completion marker: $marker" }
    Write-Output "$marker - $logPath"
    break
}

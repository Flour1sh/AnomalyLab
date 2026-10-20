param()
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
if (Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue) {
    throw 'An Unreal Editor process is already running; do not open another instance for this inspection.'
}
$p0 = Get-Content -LiteralPath (Join-Path $projectRoot 'Saved/P0/latest.json') -Raw | ConvertFrom-Json
$projectPath = Join-Path $projectRoot '我的项目3.uproject'
$scriptPath = Join-Path $PSScriptRoot 'inspect_v02_p0.py'
$logPath = Join-Path $p0.directory ('unreal_inspection_' + (Get-Date -Format 'yyyyMMddTHHmmss') + '.log')
$cachePath = Join-Path $projectRoot 'Saved/P0/DerivedDataCache'
$engineArgs = @('"' + $projectPath + '"', '"-ExecutePythonScript=' + $scriptPath + '"',
    '-DisablePlugins=AllToolsets,ModelContextProtocol,MCPClientToolset',
    '-EnablePlugins=EditorToolset,PythonScriptPlugin,UMGToolSet',
    '-unattended', '-nosplash', '-nullrhi', '-RenderOffscreen', '-nosound', '-UTF8Output',
    '-DDC=InstalledNoZenLocalFallback', ('"-LocalDataCachePath=' + $cachePath + '"'),
    '"-abslog=' + $logPath + '"')
$worker = Start-Process -FilePath 'E:/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList ($engineArgs -join ' ') -WindowStyle Hidden -PassThru
Write-Output "P0 inspection PID $($worker.Id); log: $logPath"
$worker.WaitForExit()
$worker.Refresh()
$resultPath = Join-Path $p0.directory 'unreal_inspection.json'
if ($worker.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $resultPath)) {
    throw "P0 inspection process failed. Exit=$($worker.ExitCode); see $logPath"
}
$report = Get-Content -LiteralPath $resultPath -Raw | ConvertFrom-Json
if ($report.status -ne 'PASS' -or -not (Select-String -LiteralPath $logPath -SimpleMatch '[P0] INSPECTION PASS' -Quiet)) {
    throw "P0 inspection did not pass; see $resultPath"
}
Write-Output "P0 INSPECTION PASS: $($report.checks.Count) checks; PIE NOT RUN; assets not saved."

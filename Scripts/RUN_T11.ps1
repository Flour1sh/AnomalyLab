param([ValidateSet('inspect','build','reload')][string]$Mode = 'build')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
if (Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue) { throw 'Close existing Unreal Editor before this asset build.' }
$outDir = Join-Path $projectRoot 'Saved/T11'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$scriptName = switch ($Mode) { 'inspect' {'inspect_t11_api.py'} 'build' {'build_t11.py'} 'reload' {'reload_t11.py'} }
$scriptPath = Join-Path $PSScriptRoot $scriptName
$logPath = Join-Path $outDir ($Mode + '_' + (Get-Date -Format 'yyyyMMddTHHmmss') + '.log')
$engineArgs = @('"' + (Join-Path $projectRoot '我的项目3.uproject') + '"', '"-ExecutePythonScript=' + $scriptPath + '"',
    '-DisablePlugins=AllToolsets,ModelContextProtocol,MCPClientToolset', '-EnablePlugins=EditorToolset,PythonScriptPlugin,UMGToolSet',
    '-unattended', '-nosplash', '-nullrhi', '-RenderOffscreen', '-nosound', '-UTF8Output',
    '-DDC=InstalledNoZenLocalFallback', ('"-LocalDataCachePath=' + (Join-Path $outDir 'DerivedDataCache') + '"'), '"-abslog=' + $logPath + '"')
$worker = Start-Process -FilePath 'E:/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList ($engineArgs -join ' ') -WindowStyle Hidden -PassThru
Write-Output "T11 $Mode PID $($worker.Id); log: $logPath"
$worker.WaitForExit()
$worker.Refresh()
if ($worker.ExitCode -ne 0 -or (Select-String -LiteralPath $logPath -Pattern 'LogPython: Error:|\[T11\] FAIL' -Quiet)) { throw "T11 $Mode failed; see $logPath" }
Select-String -LiteralPath $logPath -Pattern '\[T11\]' | ForEach-Object { $_.Line }

$ErrorActionPreference = "Stop"

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectDir

$apiPort = 8001

Write-Host "Starting API on http://127.0.0.1:$apiPort"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$projectDir'; python -m uvicorn api_server:app --host 127.0.0.1 --port $apiPort"

Write-Host "Starting GUI"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$projectDir'; python main.py"

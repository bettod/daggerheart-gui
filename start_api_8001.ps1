$ErrorActionPreference = "Stop"

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectDir

$port = 8001

Write-Host "Starting Daggerheart API on http://127.0.0.1:$port"
Write-Host "Project directory: $projectDir"

python -m uvicorn api_server:app --host 127.0.0.1 --port $port

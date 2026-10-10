@echo off
setlocal
cd /d "%~dp0"

set PORT=8001

echo Starting Daggerheart API on http://127.0.0.1:%PORT%
python -m uvicorn api_server:app --host 127.0.0.1 --port %PORT%

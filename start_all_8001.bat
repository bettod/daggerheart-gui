@echo off
setlocal
cd /d "%~dp0"

set API_PORT=8001

start "Daggerheart API" cmd /k "cd /d "%~dp0" && python -m uvicorn api_server:app --host 127.0.0.1 --port %API_PORT%"

timeout /t 2 >nul

start "Daggerheart GUI" cmd /k "cd /d "%~dp0" && python main.py"

echo Started API and GUI.
echo API: http://127.0.0.1:%API_PORT%/docs

@echo off
echo Starting Automated Drill-and-Blast System Development Servers
echo ============================================================

echo.
echo Starting FastAPI backend server...
start "Backend Server" cmd /k "cd /d %~dp0 && set PYTHONPATH=%~dp0src && python -m uvicorn drill_blast_system.api.main:app --host 127.0.0.1 --port 8000 --reload"

echo.
echo Waiting for backend to start...
timeout /t 3 /nobreak > nul

echo.
echo Starting React frontend server...
start "Frontend Server" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo Both servers are starting!
echo Backend API: http://127.0.0.1:8000
echo Frontend App: http://localhost:5173
echo API Docs: http://127.0.0.1:8000/docs
echo.
echo Press any key to exit...
pause > nul
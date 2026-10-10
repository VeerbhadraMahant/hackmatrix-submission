@echo off
REM Starts FinPilot: backend (FastAPI :8000) and frontend (Next.js :3000) in separate windows.
set ROOT=%~dp0

if not exist "%ROOT%backend\.venv\Scripts\activate.bat" (
  echo Creating backend venv and installing requirements...
  python -m venv "%ROOT%backend\.venv" || goto :fail
  call "%ROOT%backend\.venv\Scripts\activate.bat"
  pip install -r "%ROOT%backend\requirements.txt" || goto :fail
)
if not exist "%ROOT%frontend\node_modules" (
  echo Installing frontend dependencies...
  pushd "%ROOT%frontend" && call npm install || goto :fail
  popd
)

start "FinPilot Backend" cmd /k "cd /d %ROOT%backend && call .venv\Scripts\activate.bat && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
start "FinPilot Frontend" cmd /k "cd /d %ROOT%frontend && npm run dev"

echo Backend:  http://127.0.0.1:8000/docs
echo Frontend: http://localhost:3000
exit /b 0

:fail
echo Setup failed.
pause
exit /b 1

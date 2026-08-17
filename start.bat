@echo off
setlocal enabledelayedexpansion
title Beru Campus AI - Starting...
cd /d "%~dp0"

rem ---------------------------------------------------------------
rem  Beru Campus AI - fully automatic launcher.
rem  Starts the full stack (Docker if available, else local dev),
rem  waits for services to come up, then opens the browser.
rem ---------------------------------------------------------------

if not exist ".env" (
    echo [!] No .env found - creating from .env.example
    copy ".env.example" ".env" >nul
    echo [+] Created .env  (edit it to add GROQ_API_KEY / GEMINI_API_KEY for real LLMs)
    echo.
)

docker --version >nul 2>&1
if not errorlevel 1 goto docker_mode
goto local_mode

rem ---------------------------------------------------------------
rem  Docker mode - start everything detached, then wait + open browser
rem ---------------------------------------------------------------
:docker_mode
echo [*] Docker detected - starting full stack...
docker compose up -d postgres redis neo4j qdrant backend worker frontend
if errorlevel 1 (
    echo [!] Docker compose failed. Check the logs above.
    goto failed
)
echo [+] Docker stack is starting in the background...
set BACKEND_URL=http://localhost:8000/api/v1/health
set FRONTEND_URL=http://localhost:5173
goto wait_ready

rem ---------------------------------------------------------------
rem  Local dev mode - venv + deps once, launch backend/frontend windows
rem ---------------------------------------------------------------
:local_mode
echo [*] Docker not found - falling back to local development mode
echo.
echo --- Backend setup ---
if not exist "backend\.venv" (
    echo [+] Creating Python virtual environment...
    python -m venv backend\.venv
)
call backend\.venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul
pip install -r backend\requirements.txt
if exist "backend\requirements-ml.txt" if not "%ML_SKIP%"=="1" (
    echo [+] Installing ML extras (set ML_SKIP=1 to skip)...
    pip install -r backend\requirements-ml.txt
)
echo.
echo --- Frontend setup ---
if not exist "frontend\node_modules" (
    echo [+] Installing npm dependencies...
    pushd frontend
    call npm install
    popd
)
echo.
echo [+] Launching backend and frontend in separate windows...
start "Beru Backend" cmd /k "cd /d ""%~dp0backend"" && call .venv\Scripts\activate.bat && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
start "Beru Frontend" cmd /k "cd /d ""%~dp0frontend"" && npm run dev"
set BACKEND_URL=http://localhost:8000/api/v1/health
set FRONTEND_URL=http://localhost:5173
goto wait_ready

rem ---------------------------------------------------------------
rem  Poll until services are reachable, then open the browser
rem ---------------------------------------------------------------
:wait_ready
echo.
echo [*] Waiting for services to come online...
set /a backend_ok=0
set /a frontend_ok=0
set /a tries=0
:probe
set /a tries+=1
if "%backend_ok%"=="0" (
    curl -s -o nul "%BACKEND_URL%"
    if not errorlevel 1 set /a backend_ok=1
)
if "%frontend_ok%"=="0" (
    curl -s -o nul "%FRONTEND_URL%"
    if not errorlevel 1 set /a frontend_ok=1
)
if "%backend_ok%"=="1" if "%frontend_ok%"=="1" goto ready
if %tries% GEQ 90 (
    echo [!] Services did not become ready in time.
    if "%backend_ok%"=="0" echo     Backend still not reachable at %BACKEND_URL%
    if "%frontend_ok%"=="0" echo     Frontend still not reachable at %FRONTEND_URL%
    echo     Keep this window open to monitor the logs.
    goto open_browser
)
timeout /t 2 /nobreak >nul
goto probe

:ready
echo [+] Backend is up  : %BACKEND_URL%
echo [+] Frontend is up : %FRONTEND_URL%

:open_browser
echo.
echo [+] Opening browser...
start "" "%FRONTEND_URL%"
echo.
echo ---------------------------------------------------------------
echo   Frontend : http://localhost:5173
echo   API docs : http://localhost:8000/docs
echo   Health   : http://localhost:8000/api/v1/health
echo   Demo     : admin/admin123, lecturer/lecturer123,
echo              placement/placement123, student/student123
echo ---------------------------------------------------------------
goto end

:failed
echo [!] Startup failed. See logs above.
goto end

:end
echo.
echo Done. Press any key to close this window.
pause >nul
exit /b 0

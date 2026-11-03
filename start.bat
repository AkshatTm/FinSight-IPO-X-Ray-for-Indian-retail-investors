@echo off
rem FinSight one-click launcher. Double-click for the menu, or run with an action:
rem   start.bat start | stop | restart | status
rem Start: Ollama (:11434, kept if already running), then the API (:8000) and the web app
rem (:3000), each in its own minimised window ("FinSight Ollama", "FinSight API",
rem "FinSight Web"), then opens the app in %BROWSER% (Edge by default).
rem Whatever already listens on :8000 or :3000 is stopped first, so they always start there.
rem Stop: kills only FinSight's processes (by port, by those window titles, and Ollama itself).
rem It never kills node.exe or python.exe in general.
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
set "ROOT=%~dp0"
set "MODEL=finsight-student:q4"
set "API_URL=http://127.0.0.1:8000/api/health"
set "WEB_URL=http://127.0.0.1:3000/"
set "OLLAMA_URL=http://127.0.0.1:11434/api/tags"
rem The browser the app opens in (not the default one, so your own browser is left alone).
rem Use any exe name on PATH or a full path; "default" opens the system default browser.
set "BROWSER=msedge"

rem Settings the API and the web app inherit from this window.
set "FINSIGHT_PROFILE=local"
set "FINSIGHT_UPLOADS__PER_USER_PER_DAY=1000"
set "FINSIGHT_UPLOADS__GLOBAL_PER_DAY=1000"
set "FINSIGHT_UPLOADS__RETENTION_DAYS=3650"
set "PYTHONUTF8=1"
set "FINSIGHT_API_ORIGIN=http://127.0.0.1:8000"
set "NEXT_PUBLIC_USE_MOCKS=0"

if /i "%~1"=="start" (call :start & goto :end)
if /i "%~1"=="stop" (call :stop & goto :end)
if /i "%~1"=="restart" (call :stop & call :start & goto :end)
if /i "%~1"=="status" (call :status & goto :end)

:menu
echo.
echo  ===============  FinSight  ===============
call :status
echo.
echo   [1] Start everything
echo   [2] Stop everything
echo   [3] Restart
echo   [4] Status
echo   [Q] Quit
choice /C 1234Q /N /M "Choose: "
if errorlevel 5 goto :end
if errorlevel 4 goto :menu
if errorlevel 3 (call :stop & call :start & goto :menu)
if errorlevel 2 (call :stop & goto :menu)
if errorlevel 1 (call :start & goto :menu)
goto :menu

rem ---------------------------------------------------------------- start
:start
where uv >nul 2>nul || (echo uv is not installed: https://docs.astral.sh/uv/ & exit /b 1)
where pnpm >nul 2>nul || (echo pnpm is not installed: https://pnpm.io/installation & exit /b 1)

call :pids 11434
if defined PIDS (
  echo Ollama is already running.
) else (
  where ollama >nul 2>nul || (echo Ollama is not installed: https://ollama.com/download & exit /b 1)
  echo Starting Ollama ...
  start "FinSight Ollama" /MIN cmd /k "title FinSight Ollama && ollama serve"
  call :wait "%OLLAMA_URL%" 30 Ollama || exit /b 1
)
ollama list 2>nul | findstr /C:"%MODEL%" >nul
if errorlevel 1 (
  echo WARNING: %MODEL% is not in Ollama. Run once: uv run python scripts/run_app.py --no-frontend
) else (
  rem Load the student now, kept 30 min, so the first chat answer is not slow.
  start "" /B curl -s -o nul -m 120 http://127.0.0.1:11434/api/generate -d "{\"model\":\"%MODEL%\",\"keep_alive\":\"30m\"}"
)

rem Free :8000 and :3000 so FinSight always runs on them.
call :killport 8000
call :killport 3000
call :freewait 8000
call :freewait 3000

echo Checking Python packages ...
uv sync --inexact --group ml --group onnx -q || (echo Package install failed. & exit /b 1)
echo Starting the API on :8000 ...
start "FinSight API" /MIN /D "%ROOT%" cmd /k "title FinSight API && uv run python -m uvicorn finsight.api.app:app --port 8000 --timeout-keep-alive 30"

if not exist "%ROOT%frontend\node_modules" (
  echo Installing the frontend packages, first run only ...
  pushd "%ROOT%frontend" && pnpm install --frozen-lockfile & popd
)
echo Starting the web app on :3000 ...
start "FinSight Web" /MIN /D "%ROOT%frontend" cmd /k "title FinSight Web && pnpm dev --port 3000"

call :wait "%API_URL%" 120 API || exit /b 1
call :wait "%WEB_URL%" 180 "Web app" || exit /b 1
echo.
echo FinSight is running: http://localhost:3000
echo The three FinSight windows are minimised in the taskbar; closing them stops the app.
if /i "%BROWSER%"=="default" (start "" http://localhost:3000) else (
  start "" "%BROWSER%" http://localhost:3000 2>nul || start "" http://localhost:3000
)
exit /b 0

rem ----------------------------------------------------------------- stop
:stop
echo Stopping FinSight ...
for %%P in (8000 3000 11434) do call :killport %%P
for %%T in ("FinSight API*" "FinSight Web*" "FinSight Ollama*") do (
  taskkill /FI "WINDOWTITLE eq %%~T" /T /F >nul 2>nul
)
taskkill /IM "ollama app.exe" /T /F >nul 2>nul
taskkill /IM ollama.exe /T /F >nul 2>nul
echo Stopped.
exit /b 0

rem --------------------------------------------------------------- status
:status
call :show 11434 "Ollama  "
call :show 8000 "API     "
call :show 3000 "Web app "
exit /b 0

:show
call :pids %1
if defined PIDS (echo   %~2 :%1  UP    PID!PIDS!) else (echo   %~2 :%1  down)
exit /b 0

rem ---------------------------------------------------------------- helpers
rem :pids PORT -> PIDS = the processes listening on PORT (empty when none)
:pids
set "PIDS="
for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "Get-NetTCPConnection -State Listen -LocalPort %1 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique"`) do (
  if not "%%I"=="0" set "PIDS=!PIDS! %%I"
)
exit /b 0

rem :killport PORT -> stops every process (and its children) listening on PORT
:killport
call :pids %1
for %%I in (!PIDS!) do (
  echo   port %1 is in use: stopping PID %%I
  taskkill /PID %%I /T /F >nul 2>nul
)
exit /b 0

rem :freewait PORT -> waits up to 20 s for PORT to be free
:freewait
for /l %%N in (1,1,10) do (
  call :pids %1
  if not defined PIDS exit /b 0
  ping -n 3 127.0.0.1 >nul
)
echo   WARNING: port %1 is still in use, PID!PIDS!.
exit /b 1

rem :wait URL SECONDS NAME -> errorlevel 0 once URL answers
:wait
set /a "_n=%~2/2"
echo Waiting for %~3 ...
:wait_loop
curl -s -o nul -m 3 "%~1" && (echo   %~3 is up. & exit /b 0)
set /a "_n-=1"
if !_n! LEQ 0 (echo   %~3 did not answer in %~2 s, see its window. & exit /b 1)
ping -n 3 127.0.0.1 >nul
goto :wait_loop

:end
endlocal

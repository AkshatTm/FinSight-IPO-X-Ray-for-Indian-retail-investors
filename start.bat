@echo off
rem FinSight: start everything with one double-click (or `start.bat` in a terminal).
rem Ollama + the student model, the API (:8000, with the classifier, bge-m3, reranker and
rem Hindi voice loaded when needed) and the frontend (:3000). Ctrl+C stops all of it.
rem Options are passed on, e.g. `start.bat --no-frontend` or `start.bat --port 8001`.
cd /d "%~dp0"

where uv >nul 2>nul
if errorlevel 1 (
  echo uv is not installed. Get it from https://docs.astral.sh/uv/ and run this again.
  pause
  exit /b 1
)

for /f %%b in ('git rev-parse --abbrev-ref HEAD 2^>nul') do set BRANCH=%%b
echo Branch: %BRANCH%
if /i "%BRANCH%"=="main" (
  git pull --ff-only
) else (
  echo NOTE: you are not on main, so nothing is pulled. For the latest app: git checkout main ^&^& git pull
)

echo Installing / checking Python packages (first run takes a few minutes) ...
uv sync --inexact --group ml --group onnx --group asr
if errorlevel 1 (
  echo Package install failed. See the messages above.
  pause
  exit /b 1
)

uv run python scripts/run_app.py %*
echo.
echo FinSight stopped.
pause

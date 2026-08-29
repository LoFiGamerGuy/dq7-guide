@echo off
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -c "import sys; raise SystemExit(sys.version_info ^< (3, 10))" >nul 2>nul
  if not errorlevel 1 (
    py -3 scripts\guide_server.py --lan --open-browser
    goto :finished
  )
)

where python >nul 2>nul
if not errorlevel 1 (
  python -c "import sys; raise SystemExit(sys.version_info ^< (3, 10))" >nul 2>nul
  if not errorlevel 1 (
    python scripts\guide_server.py --lan --open-browser
    goto :finished
  )
)

echo Python 3.10 or newer is required. Install it from https://www.python.org/downloads/
pause
exit /b 1

:finished
if errorlevel 1 (
  echo.
  echo The phone guide could not start. Review the error above, then try again.
  pause
)

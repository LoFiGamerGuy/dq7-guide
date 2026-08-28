@echo off
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  python scripts\guide_server.py --open-browser
) else (
  py -3 scripts\guide_server.py --open-browser
)

@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (py -3 mgp.py setup) else (python mgp.py setup)
echo.
pause

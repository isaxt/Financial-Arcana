@echo off
cd /d "%~dp0"
where py >nul 2>nul && (py -3 arcana.py data) || (python arcana.py data)
pause

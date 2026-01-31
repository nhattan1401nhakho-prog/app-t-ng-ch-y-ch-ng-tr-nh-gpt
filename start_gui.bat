@echo off
cd /d "%~dp0"
"C:\Users\Admin\miniconda3\python.exe" src\main.py
if errorlevel 1 (
  echo.
  echo App crashed. See app.log for details.
)
pause

@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
python -m uvicorn api.main:app --port 8001
pause

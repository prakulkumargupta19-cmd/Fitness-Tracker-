@echo off
where py >nul 2>nul
if %errorlevel%==0 (
  py -3.10 -m venv venv 2>nul
  if errorlevel 1 py -3 -m venv venv
) else (
  python -m venv venv
)
call venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
pause

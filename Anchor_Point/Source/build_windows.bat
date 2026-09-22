@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher ^(py^) was not found. Install Python 3.11 x64, then rerun this file.
  exit /b 1
)
py -3.11 -m pip install --upgrade pip
if errorlevel 1 exit /b 1
py -3.11 -m pip install -r requirements.txt pyinstaller
if errorlevel 1 exit /b 1
py -3.11 -m PyInstaller --noconfirm --clean --onefile --windowed --name AnchorPoint --icon anchorpointlogo.ico --add-data "locales;locales" --add-data "anchorpointlogo.png;." --add-data "anchorpointlogo.ico;." --add-data "config.example.yaml;." --collect-data customtkinter main.py
if errorlevel 1 exit /b 1
echo.
echo Build complete: %CD%\dist\AnchorPoint.exe
endlocal

@echo off
setlocal
cd /d "%~dp0"

call build_windows.bat
if errorlevel 1 exit /b 1

rem Locate the newest supported Inno Setup compiler first.
set "ISCC="
for %%P in (
  "%ProgramFiles%\Inno Setup 7\ISCC.exe"
  "%ProgramFiles(x86)%\Inno Setup 7\ISCC.exe"
  "%ProgramFiles%\Inno Setup 6\ISCC.exe"
  "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
) do (
  if not defined ISCC if exist "%%~P" set "ISCC=%%~P"
)

rem Also accept ISCC.exe if the user has added Inno Setup to PATH.
if not defined ISCC (
  for /f "delims=" %%I in ('where ISCC.exe 2^>nul') do if not defined ISCC set "ISCC=%%I"
)

if not defined ISCC (
  echo.
  echo ERROR: Inno Setup compiler was not found.
  echo AnchorPoint.exe was built successfully in dist\, but the installer was not created.
  echo Install Inno Setup 7 or 6, then rerun build_installer.bat.
  echo.
  exit /b 2
)

echo Using Inno Setup compiler:
echo   %ISCC%
echo.

"%ISCC%" AnchorPoint.iss
if errorlevel 1 exit /b 1

if not exist "installer\AnchorPoint-1.0.0-Setup.exe" (
  echo.
  echo ERROR: Inno Setup finished, but installer\AnchorPoint-1.0.0-Setup.exe was not found.
  exit /b 3
)

echo.
echo Installer created successfully:
echo   %CD%\installer\AnchorPoint-1.0.0-Setup.exe
endlocal

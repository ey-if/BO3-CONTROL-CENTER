@echo off
setlocal
cd /d "%~dp0"
echo ==========================================
echo   BO3 Control Center v0.3.1 - EXE Builder
echo ==========================================
echo.
where py >nul 2>nul
if errorlevel 1 (
  echo Python Launcher was not found. This script is for the BUILD computer only.
  echo The final EXE will NOT require Python.
  pause
  exit /b 1
)
py -c "import tkinter" >nul 2>nul
if errorlevel 1 (
  echo Tkinter is missing from this Python installation.
  echo Install Python for Windows with the Tcl/Tk and IDLE option enabled.
  pause
  exit /b 1
)
py -m py_compile BO3_Control_Center.py
if errorlevel 1 goto failed
py -m unittest discover -s tests -v
if errorlevel 1 goto failed
py -m pip install --upgrade pyinstaller
if errorlevel 1 goto failed
py -m PyInstaller --noconfirm --clean --onefile --windowed --name "BO3-Control-Center" "BO3_Control_Center.py"
if errorlevel 1 goto failed
if not exist "dist\BO3-Control-Center.exe" goto failed
echo.
echo Build complete. Your standalone application is:
echo dist\BO3-Control-Center.exe
echo Copy that EXE to any Windows 10 PC. Python is not required there.
pause
exit /b 0
:failed
echo.
echo Build or verification failed. Review the error above.
pause
exit /b 1

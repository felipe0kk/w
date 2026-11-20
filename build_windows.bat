@echo off
setlocal
cd /d "%~dp0"
echo ==========================================
echo   STEAM KEY HUNTER V2 - BUILD WINDOWS
echo ==========================================
where python >nul 2>nul
if errorlevel 1 (
  echo No se encontro Python. Instala Python 3.10 o superior y marca Add Python to PATH.
  echo Descarga: https://www.python.org/downloads/windows/
  pause
  exit /b 1
)
python -m venv .venv
if errorlevel 1 goto error
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 goto error
python -m pip install -r requirements.txt
if errorlevel 1 goto error
python -m PyInstaller --noconfirm --clean --onefile --windowed --name "SteamKeyHunter" --add-data "templates;templates" --add-data "static;static" app.py
if errorlevel 1 goto error
echo.
echo BUILD COMPLETADO: dist\SteamKeyHunter.exe
pause
exit /b 0
:error
echo.
echo ERROR: No se pudo completar la compilacion. Revisa los mensajes anteriores.
pause
exit /b 1

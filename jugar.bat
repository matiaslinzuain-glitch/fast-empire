@echo off
cd /d "%~dp0"
echo Actualizando Fast Empire...
git pull
echo.
echo Iniciando Fast Empire...
py main.py
pause

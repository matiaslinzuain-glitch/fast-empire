@echo off
cd /d "%~dp0"
echo Actualizando Fast Empire...
git pull
echo.
echo Verificando dependencias...
py -m pip install --quiet -r requirements.txt
echo.
echo Iniciando Fast Empire...
py main.py
pause

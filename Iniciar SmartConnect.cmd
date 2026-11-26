@echo off
setlocal
cd /d "%~dp0"
set "PYTHON_AULA=.venv\Scripts\python.exe"
if not exist "%PYTHON_AULA%" (
  python -m venv .venv
  if errorlevel 1 goto fallo
)
"%PYTHON_AULA%" -m pip install --disable-pip-version-check -r requirements.txt || goto fallo
"%PYTHON_AULA%" manage.py migrate --noinput || goto fallo
"%PYTHON_AULA%" manage.py seed_demo --aula || goto fallo
echo Historial: http://127.0.0.1:8000/historial/
"%PYTHON_AULA%" -c "import urllib.request as u; assert 'SmartConnect' in u.urlopen('http://127.0.0.1:8000/historial/ingresar/',timeout=2).read().decode()" >nul 2>&1
if not errorlevel 1 (
  echo SmartConnect ya esta disponible en este PC.
  exit /b 0
)
echo Deja esta ventana abierta durante la clase. Para detener el servidor, pulsa Ctrl+C.
"%PYTHON_AULA%" manage.py runserver 127.0.0.1:8000 --insecure
if errorlevel 1 goto fallo
exit /b 0
:fallo
echo Revisa el mensaje anterior. Se requiere Python 3.12 o 3.13 con pip.
pause
exit /b 1

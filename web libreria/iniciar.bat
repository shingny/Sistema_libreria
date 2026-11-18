@echo off
REM ============================================================
REM  Libreria El Saber - Script de arranque (Windows)
REM ============================================================
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo [1/4] Creando entorno virtual...
    python -m venv venv
)

echo [2/4] Instalando dependencias...
"venv\Scripts\python.exe" -m pip install -q -r requirements.txt

if not exist ".env" (
    echo [3/4] No existe el archivo .env. Copiando la plantilla...
    copy /y ".env.example" ".env" >nul
    echo.
    echo   Abre el archivo .env y escribe los datos de tu MySQL de Alwaysdata
    echo   (host, puerto, nombre de la base, usuario y contrasena).
    echo.
    echo   Despues ejecuta:  "venv\Scripts\python.exe" crear_tablas.py --datos
    echo.
    pause
    exit /b 1
)
echo [3/4] Configuracion (.env) encontrada.

echo [4/4] Iniciando servidor en http://127.0.0.1:5000
start "" http://127.0.0.1:5000
"venv\Scripts\python.exe" app.py

pause

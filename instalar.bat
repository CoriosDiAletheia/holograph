@echo off
cd /d "%~dp0"
echo Instalando las librerias de Mi letra...
python -m pip install --upgrade -r requirements.txt
if errorlevel 1 (
    echo.
    echo No se pudo instalar. Comprueba que Python esta instalado y en el PATH.
) else (
    echo.
    echo Listo. Ya puedes abrir iniciar.bat
)
pause

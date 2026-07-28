@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERRO] O Python da .venv nao foi encontrado.
    echo Caminho esperado: %CD%\.venv\Scripts\python.exe
    pause
    exit /b 1
)

".venv\Scripts\python.exe" launcher.py
set "CODIGO_SAIDA=%ERRORLEVEL%"

echo.
echo O launcher terminou com o codigo %CODIGO_SAIDA%.
pause

exit /b %CODIGO_SAIDA%

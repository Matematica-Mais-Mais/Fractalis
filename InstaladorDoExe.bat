@echo off
echo ====================================================
echo   Iniciando compilacao do Fractalis com PyInstaller...
echo ====================================================
echo.

:: --icon="icone.ico"

python -m PyInstaller --noconfirm --onefile --name "Fractalis" --add-data "templates;templates" --add-data "static;static" --add-data "raizes_complexas.py;." --add-data "geradorDePaletas.py;." app.py

echo.
if %ERRORLEVEL% EQU 0 (
    echo ====================================================
    echo   SUCESSO! 
    echo   O arquivo Fractalis.exe foi criado na pasta "dist".
    echo ====================================================
) else (
    echo ====================================================
    echo   ERRO! Ocorreu um problema durante a compilacao.
    echo ====================================================
)

echo.
pause
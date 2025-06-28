@echo off
echo ================================================
echo  Compilando sistema FogueiroBurger com PyInstaller
echo ================================================

REM Navega até a pasta do projeto
cd /d "D:\FOGUEIRO\Sistema"

REM Executa o PyInstaller
pyinstaller --onefile --noconsole main_system.py

echo ----------------------------------------
echo  Processo finalizado.
echo  O executável está na pasta "dist".
pause

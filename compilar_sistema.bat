@echo off
REM Este script compila o sistema "Fogueiro Burger" usando PyInstaller.
REM Ele inclui o módulo 'tkcalendar' que pode não ser detectado automaticamente.

REM Define o diretório do seu sistema
set SYSTEM_PATH="D:\FOGUEIRO\Sistema"

echo Navegando para o diretorio do sistema...
cd %SYSTEM_PATH%

IF %ERRORLEVEL% NEQ 0 (
    echo Erro: O diretorio %SYSTEM_PATH% nao foi encontrado.
    echo Certifique-se de que o caminho esta correto.
    pause
    exit /b %ERRORLEVEL%
)

echo Compilando main_system.py com PyInstaller...
REM --noconfirm: sobrescreve a pasta dist/build sem confirmacao
REM --onefile: cria um unico arquivo executavel
REM --windowed (ou --noconsole): impede que a janela do console apareca ao executar o app
REM --collect-submodules tkcalendar: garante que todos os sub-modulos do tkcalendar sejam incluidos
REM --hidden-import idlelib.TkinterExtension: Adiciona uma importacao oculta para TkinterExtension (pode ser necessário para o tkcalendar)
REM --hidden-import tkcalendar: Adiciona o módulo tkcalendar

pyinstaller --noconfirm --onefile --windowed --hidden-import tkcalendar --hidden-import idlelib.TkinterExtension main_system.py

IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo Erro durante a compilacao do PyInstaller.
    echo Verifique as mensagens acima para mais detalhes.
) ELSE (
    echo.
    echo Compilacao concluida com sucesso!
    echo O executavel foi criado na pasta "dist" dentro de %SYSTEM_PATH%.
)

pause

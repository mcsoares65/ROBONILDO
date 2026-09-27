@echo off
chcp 65001 >nul
setlocal

title ROBONILDO - Sincronizacao com GitHub
cd /d D:\DAYTRADE\ROBONILDO_GITHUB

echo ============================================================
echo        ROBONILDO - SINCRONIZACAO COM GITHUB
echo ============================================================
echo.
echo [1] BAIXAR atualizacoes do GitHub
echo [2] ENVIAR alteracoes para o GitHub
echo [3] Consultar situacao
echo [4] Sair
echo.

choice /C 1234 /N /M "Escolha uma opcao: "

if errorlevel 4 goto sair
if errorlevel 3 goto status
if errorlevel 2 goto enviar
if errorlevel 1 goto baixar

:baixar
cls
echo ============================================================
echo BAIXANDO ATUALIZACOES
echo ============================================================
echo.

git switch main
if errorlevel 1 goto erro

echo.
echo Situacao local antes da atualizacao:
git status --short

echo.
git pull --ff-only origin main
if errorlevel 1 (
    echo.
    echo Nao foi possivel atualizar automaticamente.
    echo Verifique se existem alteracoes locais ou conflitos.
    goto finalizar
)

echo.
echo Atualizacao concluida.
git status
goto finalizar

:enviar
cls
echo ============================================================
echo ENVIANDO ALTERACOES
echo ============================================================
echo.

git switch main
if errorlevel 1 goto erro

echo.
echo Buscando atualizacoes existentes no GitHub...
git pull --ff-only origin main
if errorlevel 1 (
    echo.
    echo Envio interrompido para evitar conflitos.
    goto finalizar
)

echo.
echo Arquivos alterados, adicionados ou excluidos:
echo ------------------------------------------------------------
git status --short
echo ------------------------------------------------------------
echo.

choice /C SN /N /M "Deseja enviar essas alteracoes? [S/N]: "
if errorlevel 2 goto cancelar

set "MENSAGEM="
set /p "MENSAGEM=Descricao da atualizacao: "

if not defined MENSAGEM (
    echo.
    echo A descricao nao pode ficar vazia.
    goto finalizar
)

git add -A
if errorlevel 1 goto erro

git commit -m "%MENSAGEM%"
if errorlevel 1 (
    echo.
    echo Nenhum commit foi criado. Talvez nao existam alteracoes.
    goto finalizar
)

git push origin main
if errorlevel 1 goto erro

echo.
echo Alteracoes enviadas com sucesso.
git status
goto finalizar

:status
cls
echo ============================================================
echo SITUACAO DO PROJETO
echo ============================================================
echo.

git switch main
git status
echo.
git log -5 --oneline
goto finalizar

:cancelar
echo.
echo Envio cancelado. Nenhum arquivo foi enviado.
goto finalizar

:erro
echo.
echo ERRO: a operacao nao foi concluida.
echo Leia as mensagens apresentadas acima.

:finalizar
echo.
pause
goto :eof

:sair
exit /b
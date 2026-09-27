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
echo [4] REVERTER um commit com problema
echo [5] Sair
echo.

choice /C 12345 /N /M "Escolha uma opcao: "

if errorlevel 5 goto sair
if errorlevel 4 goto reverter
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
git log -10 --oneline
goto finalizar

:reverter
cls
echo ============================================================
echo REVERTER COMMIT
echo ============================================================
echo.
echo Esta opcao cria um novo commit que desfaz o commit escolhido.
echo O historico original sera preservado.
echo.

git switch main
if errorlevel 1 goto erro

git pull --ff-only origin main
if errorlevel 1 (
    echo.
    echo Reversao interrompida: nao foi possivel atualizar a main.
    goto finalizar
)

set "ALTERADO="
for /f "delims=" %%i in ('git status --porcelain') do set "ALTERADO=1"
if defined ALTERADO (
    echo.
    echo Reversao interrompida: existem alteracoes locais pendentes.
    echo Envie, descarte ou guarde essas alteracoes antes de continuar.
    echo.
    git status --short
    goto finalizar
)

echo.
echo Ultimos 15 commits:
echo ------------------------------------------------------------
git log -15 --oneline
echo ------------------------------------------------------------
echo.

set "COMMIT="
set /p "COMMIT=Digite o codigo do commit que deseja reverter: "

if not defined COMMIT (
    echo.
    echo Nenhum commit informado.
    goto finalizar
)

git rev-parse --verify "%COMMIT%^^{commit}" >nul 2>&1
if errorlevel 1 (
    echo.
    echo Commit invalido ou nao encontrado: %COMMIT%
    goto finalizar
)

echo.
echo O commit abaixo sera desfeito:
echo ------------------------------------------------------------
git show --stat --oneline --decorate "%COMMIT%"
echo ------------------------------------------------------------
echo.
echo ATENCAO: confirme somente se este for exatamente o commit com problema.
choice /C SN /N /M "Deseja criar e enviar a reversao? [S/N]: "
if errorlevel 2 goto cancelar

git revert --no-edit "%COMMIT%"
if errorlevel 1 (
    echo.
    echo A reversao encontrou conflito e nao foi concluida.
    echo Use git revert --abort para cancelar a tentativa.
    goto finalizar
)

git push origin main
if errorlevel 1 (
    echo.
    echo A reversao foi criada localmente, mas o envio falhou.
    echo Nao repita o revert. Corrija a conexao e execute: git push origin main
    goto finalizar
)

echo.
echo Commit revertido e enviado com sucesso.
git log -3 --oneline
goto finalizar

:cancelar
echo.
echo Operacao cancelada. Nenhuma nova alteracao foi enviada.
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

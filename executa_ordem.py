# executa_ordem.py

#!/usr/bin/env python3
import sys
import pyautogui
import time
import pygetwindow as gw
from pygetwindow import PyGetWindowException
from config import NOME_TELA_PROFIT, ENVIAR_ORDENS

# Debug helper: escreve a partir da linha 26 sem sujar o painel
def debug(msg: str):
    # posiciona cursor linha 26, coluna 1
    sys.stdout.write(f"\x1b[26;1H")
    sys.stdout.write(msg + "\n")
    sys.stdout.write("\x1b[J")  # limpa abaixo
    sys.stdout.flush()

# 🚀 Função para verificar se a tela do Profit está aberta
def verificar_tela_profit():
    janelas = gw.getWindowsWithTitle(NOME_TELA_PROFIT)
    if not janelas:
        debug("[ERRO] Profit não está aberto ou não encontrado!")
        return False
    return True

# 🚀 Função para ativar a janela do Profit (ignora Error code 0)
def ativar_tela_profit():
    janelas = gw.getWindowsWithTitle(NOME_TELA_PROFIT)
    if not janelas:
        debug("[ERRO] Não foi possível encontrar a janela do Profit.")
        return False

    win = janelas[0]
    try:
        win.activate()
    except PyGetWindowException as e:
        if "Error code from Windows: 0" not in str(e):
            debug(f"[ERRO] Falha ao ativar janela do Profit: {e}")
            return False
    time.sleep(0.5)  # deixa o Profit ganhar foco
    return True

# 🚀 Função para executar compra
def executar_compra():
    if not ENVIAR_ORDENS:
        debug("[INFO] Envio de ordens está desativado em config.ini")
        return None
    if not verificar_tela_profit():
        return None
    if not ativar_tela_profit():
        return None

    debug("[NEGOCIAÇÃO] Enviando ordem de COMPRA...")
    pyautogui.hotkey("alt", "c")
    time.sleep(0.5)
    return "compra"

# 🚀 Função para executar venda
def executar_venda():
    if not ENVIAR_ORDENS:
        debug("[INFO] Envio de ordens está desativado em config.ini")
        return None
    if not verificar_tela_profit():
        return None
    if not ativar_tela_profit():
        return None

    debug("[NEGOCIAÇÃO] Enviando ordem de VENDA...")
    pyautogui.hotkey("alt", "v")
    time.sleep(0.5)
    return "venda"

# 🚀 Função para zerar posição
def zerar_posicao():
    if not ENVIAR_ORDENS:
        debug("[INFO] Envio de ordens está desativado em config.ini")
        return None
    if not verificar_tela_profit():
        return None
    if not ativar_tela_profit():
        return None

    debug("[NEGOCIAÇÃO] Enviando ordem de ZERAR POSIÇÃO...")
    pyautogui.hotkey("alt", "z")
    time.sleep(0.5)
    return "zerado"

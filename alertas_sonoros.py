import pygame
import time
import os

# Caminho relativo para a pasta SOM
CAMINHO_SONS = os.path.abspath(os.path.join(os.path.dirname(__file__), "SOM"))

pygame.init()
pygame.mixer.init()

def tocar_alerta(nome_arquivo):
    caminho_completo = os.path.join(CAMINHO_SONS, f"{nome_arquivo}.mp3")
    if os.path.exists(caminho_completo):
        pygame.mixer.music.load(caminho_completo)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
    else:
        print(f"[⚠️] Arquivo de som não encontrado: {caminho_completo}")

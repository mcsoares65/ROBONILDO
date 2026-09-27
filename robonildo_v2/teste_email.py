# teste_email.py — rode uma vez, isolado, so pra confirmar o envio real
import email_notificacao
from datetime import datetime

class SinalTeste:
    lado = "VENDA"
    entrada = 185420.0
    stop = 186100.0
    alvo = 184370.0
    motivo = "Teste manual de notificacao por email."

email_notificacao.notificar_abertura(SinalTeste(), datetime.now())

import time
print("Enviando em segundo plano... aguardando 10 segundos pra ver o resultado.")
time.sleep(10)
print("Se nao apareceu [EMAIL] AVISO de erro acima, o email foi enviado - confira sua caixa de entrada.")
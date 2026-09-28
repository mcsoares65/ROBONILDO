"""Estratégia isolada: retomada próxima da MA21.

Origem: Porta 1 de entrada_grok_3_v1.py, desmembrada na V448 sem
alteração dos limiares. Autoria original: Grok (xAI). Modularização:
ChatGPT (OpenAI), a pedido de Marcio Soares.
"""


def gerar_sinal(row) -> int:
    tendencia = row["trend"]
    if tendencia == 0:
        return 0
    hora = row["dt"].strftime("%H:%M")
    separacao = abs(row["MA21"] - row["MA50"])
    bloqueado = (row["dt"].weekday() == 3 or "12:00" <= hora <= "13:15" or "15:00" <= hora <= "16:59")
    base = (not bloqueado and not (75.0 <= separacao <= 175.0)
            and row["atr_relativo"] <= 1.40 and row["distancia_ma21"] <= 90.0
            and 16.5 <= row["stoch"] <= 83.5)
    if base and tendencia == 1 and row["stoch_subindo"]:
        return 1
    if base and tendencia == -1 and row["stoch_descendo"]:
        return -1
    return 0

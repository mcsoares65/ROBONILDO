"""Estratégia isolada: retomada por MACD e estocástico.

Origem: Porta 2 de entrada_grok_3_v1.py, desmembrada na V448 sem
alteração dos limiares. Autoria original: Grok (xAI). Modularização:
ChatGPT (OpenAI), a pedido de Marcio Soares.
"""


def gerar_sinal(row) -> int:
    tendencia = row["trend"]
    if tendencia == 0:
        return 0
    hora = row["dt"].strftime("%H:%M")
    amplitude = row["Maximo"] - row["Minimo"]
    variacao_stoch = abs(row["stoch"] - row["stoch_prev"])
    base = (not ("11:45" <= hora <= "12:30")
            and not (240.0 <= amplitude <= 340.0)
            and row["distancia_ma21"] > 200.0 and variacao_stoch >= 4.5)
    if base and tendencia == 1 and row["stoch_subindo"] and row["macd_cross_up"]:
        return 1
    if base and tendencia == -1 and row["stoch_descendo"] and row["macd_cross_down"]:
        return -1
    return 0

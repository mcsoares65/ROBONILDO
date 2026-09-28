"""Estratégia isolada: saída de extremo do estocástico.

Origem: Porta 3 de entrada_grok_3_v1.py, desmembrada na V448 sem
alteração dos limiares. Autoria original: Grok (xAI). Modularização:
ChatGPT (OpenAI), a pedido de Marcio Soares.
"""


def gerar_sinal(row) -> int:
    tendencia = row["trend"]
    if tendencia == 0:
        return 0
    hora = row["dt"].strftime("%H:%M")
    amplitude = row["Maximo"] - row["Minimo"]
    corpo = abs(row["Fechamento"] - row["Abertura"])
    base = (not ("12:30" <= hora <= "13:15")
            and not (279.0 <= amplitude <= 360.0)
            and amplitude > 0 and corpo <= 0.70 * amplitude)
    if base and tendencia == 1 and row["stoch_cross_up_20"]:
        return 1
    if base and tendencia == -1 and row["stoch_cross_down_80"]:
        return -1
    return 0

"""Grok 3 Portas Assimetrica V2 — candidata a competicao de entrada.

Autoria: Grok (xAI).

Base empirica (ranking oficial V428 + backtests locais):
  - claude_3_portas_assimetrica_v1 liderou o multi (86,7) com UMA mudanca
    em relacao a V19: na Porta 1, segunda-feira ate 12:00 bloqueia apenas
    COMPRA (venda permanece liberada).
  - grok_3_portas_anti_perda_v2 falhou no multi ao bloquear entradas >=17:00
    (overfit ao bloco unico; diário/mensal desabaram). Esse filtro NAO volta.
  - Eixo adicional testado isoladamente sobre a base assimetrica: elevar
    VARIACAO_MINIMA_ESTOCASTICO_MACD de 4,0 para 4,5 na Porta 2 — mesmo
    passo que ja havia melhorado PF/WR em testes anteriores, sem cortar
    regime de horario amplo.

Mudancas vs V19:
  1) Porta 1: bloqueio assimetrico de COMPRA na manha de segunda (<=12:00).
  2) Porta 2: variacao minima do estocastico 4,0 -> 4,5.

Porta 3 e demais filtros da V19: inalterados.
Sem bloqueio de fim de tarde.

Contrato: gerar_sinal(row) -> 1/-1/0; diagnosticar_sinal opcional.
Sem I/O, sem estado, sem imports do projeto.

Resultado historico nao garante desempenho futuro. Validar no classificacao
multitemporal oficial antes de qualquer promocao.
"""

MAX_DISTANCIA_MA21 = 90.0
STOCH_MIN = 16.5
STOCH_MAX = 83.5
VARIACAO_MINIMA_ESTOCASTICO_MACD = 4.5
ATR_RELATIVO_MAX_PORTA_1 = 1.40
CORTE_SEGUNDA_MANHA = "12:00"


def _resultado(sinal: int, porta: int, explicacao: str, detalhar: bool):
    if not detalhar:
        return sinal
    return {
        "sinal": sinal,
        "lado": "COMPRA" if sinal == 1 else "VENDA",
        "porta": porta,
        "explicacao": explicacao,
    }


def _avaliar(row, detalhar: bool = False):
    tendencia = row["trend"]
    if tendencia == 0:
        return None if detalhar else 0

    hora = row["dt"].strftime("%H:%M")
    weekday = row["dt"].weekday()
    amplitude = row["Maximo"] - row["Minimo"]
    corpo = abs(row["Fechamento"] - row["Abertura"])
    separacao_medias = abs(row["MA21"] - row["MA50"])
    variacao_estocastico = abs(row["stoch"] - row["stoch_prev"])

    # Porta 1: retomada MA21.
    # Bloqueios: quinta; almoco; tarde; segunda manha SOMENTE se COMPRA.
    bloqueado_segunda_compra = (
        weekday == 0 and hora <= CORTE_SEGUNDA_MANHA and tendencia == 1
    )
    bloqueado_ma21 = (
        weekday == 3
        or bloqueado_segunda_compra
        or "12:00" <= hora <= "13:15"
        or "15:00" <= hora <= "16:59"
    )
    separacao_fraca_ma21 = 75.0 <= separacao_medias <= 175.0
    if (
        not bloqueado_ma21
        and not separacao_fraca_ma21
        and row["atr_relativo"] <= ATR_RELATIVO_MAX_PORTA_1
        and row["distancia_ma21"] <= MAX_DISTANCIA_MA21
        and STOCH_MIN <= row["stoch"] <= STOCH_MAX
    ):
        if tendencia == 1 and row["stoch_subindo"]:
            explicacao = (
                "Porta 1 compra: tendencia de alta, preco perto da MA21, "
                "estocastico subindo. Compra bloqueada na manha de segunda."
            )
            return _resultado(1, 1, explicacao, detalhar)
        if tendencia == -1 and row["stoch_descendo"]:
            explicacao = (
                "Porta 1 venda: tendencia de baixa, preco perto da MA21, "
                "estocastico caindo. Venda na manha de segunda permanece permitida."
            )
            return _resultado(-1, 1, explicacao, detalhar)

    # Porta 2: MACD + deslocamento minimo do estocastico (4.5).
    bloqueado_macd = "11:45" <= hora <= "12:30"
    amplitude_fraca_macd = 240.0 <= amplitude <= 340.0
    if (
        not bloqueado_macd
        and not amplitude_fraca_macd
        and row["distancia_ma21"] > 200.0
        and variacao_estocastico >= VARIACAO_MINIMA_ESTOCASTICO_MACD
    ):
        if tendencia == 1 and row["stoch_subindo"] and row["macd_cross_up"]:
            explicacao = (
                "Porta 2 compra: distancia elevada da MA21, estocastico subiu "
                f"{variacao_estocastico:.1f} pts e MACD cruzou para cima."
            )
            return _resultado(1, 2, explicacao, detalhar)
        if tendencia == -1 and row["stoch_descendo"] and row["macd_cross_down"]:
            explicacao = (
                "Porta 2 venda: distancia elevada da MA21, estocastico caiu "
                f"{variacao_estocastico:.1f} pts e MACD cruzou para baixo."
            )
            return _resultado(-1, 2, explicacao, detalhar)

    # Porta 3: saida de extremo do estocastico (igual V19).
    bloqueado_estocastico = "12:30" <= hora <= "13:15"
    amplitude_fraca_estocastico = 279.0 <= amplitude <= 360.0
    if not bloqueado_estocastico and not amplitude_fraca_estocastico:
        if amplitude > 0 and corpo <= 0.70 * amplitude:
            if tendencia == 1 and row["stoch_cross_up_20"]:
                explicacao = (
                    "Porta 3 compra: estocastico saiu de sobrevenda "
                    f"({row['stoch_prev']:.0f}->{row['stoch']:.0f})."
                )
                return _resultado(1, 3, explicacao, detalhar)
            if tendencia == -1 and row["stoch_cross_down_80"]:
                explicacao = (
                    "Porta 3 venda: estocastico saiu de sobrecompra "
                    f"({row['stoch_prev']:.0f}->{row['stoch']:.0f})."
                )
                return _resultado(-1, 3, explicacao, detalhar)

    return None if detalhar else 0


def gerar_sinal(row) -> int:
    return _avaliar(row, detalhar=False)


def diagnosticar_sinal(row):
    return _avaliar(row, detalhar=True)


__all__ = ["gerar_sinal", "diagnosticar_sinal"]

# DESCLASSIFICADA pela Regra 16 (V490): agregador de ideias por OU. Fora do ranking.
# Ver conselho/2026-10-05-AE.txt. Mantida so como referencia/paridade; nao alterada.
"""Entrada Grok 4 V1 — candidata (nao titular).

Autoria: Grok (xAI).

Ideia (horizonte novo vs titular entrada_tres_portas_v01):
  1) Assimetria de segunda-feira na Porta 1: bloqueia apenas COMPRA ate 12:00
     (venda permanece liberada) — padrao que liderou rankings multitemporais
     (claude assimetrica / chatgpt v21), sem o overfit de bloquear >=17:00.
  2) Filtro RSI na Porta 1: exige alinhamento minimo com a tendencia
     (compra RSI >= 48, venda RSI <= 52) para reduzir retomadas contra momentum.
  3) Porta 2: variacao minima do estocastico 4.5 no cruzamento MACD.
  4) Porta 3: saida de extremo com corpo controlado (inalterada em espirito).

Contrato: gerar_sinal(row) -> 1 / -1 / 0.
Sem I/O, sem estado, sem imports do projeto.

Validar em classificacao.py (modos E e C) no motor oficial antes de promover.
"""

MAX_DISTANCIA_MA21 = 90.0
STOCH_MIN = 16.5
STOCH_MAX = 83.5
VARIACAO_MINIMA_ESTOCASTICO_MACD = 4.5
ATR_RELATIVO_MAX_PORTA_1 = 1.40
CORTE_SEGUNDA_MANHA = "12:00"
RSI_MIN_COMPRA_P1 = 48.0
RSI_MAX_VENDA_P1 = 52.0


def _resultado(sinal: int, porta: int, explicacao: str, detalhar: bool):
    if not detalhar:
        return sinal
    return {
        "sinal": sinal,
        "lado": "COMPRA" if sinal == 1 else "VENDA",
        "porta": porta,
        "total_portas": 3,
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
    rsi = row.get("rsi")

    # Porta 1: retomada MA21 + RSI alinhado.
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
    rsi_ok_compra = rsi is None or rsi >= RSI_MIN_COMPRA_P1
    rsi_ok_venda = rsi is None or rsi <= RSI_MAX_VENDA_P1

    if (
        not bloqueado_ma21
        and not separacao_fraca_ma21
        and row["atr_relativo"] <= ATR_RELATIVO_MAX_PORTA_1
        and row["distancia_ma21"] <= MAX_DISTANCIA_MA21
        and STOCH_MIN <= row["stoch"] <= STOCH_MAX
    ):
        if tendencia == 1 and row["stoch_subindo"] and rsi_ok_compra:
            return _resultado(
                1,
                1,
                (
                    "Porta 1 compra: tendencia alta, perto da MA21, stoch subindo, "
                    f"RSI={rsi}. Compra bloqueada na manha de segunda."
                ),
                detalhar,
            )
        if tendencia == -1 and row["stoch_descendo"] and rsi_ok_venda:
            return _resultado(
                -1,
                1,
                (
                    "Porta 1 venda: tendencia baixa, perto da MA21, stoch caindo, "
                    f"RSI={rsi}. Venda na manha de segunda permanece permitida."
                ),
                detalhar,
            )

    # Porta 2: MACD + deslocamento minimo do estocastico.
    bloqueado_macd = "11:45" <= hora <= "12:30"
    amplitude_fraca_macd = 240.0 <= amplitude <= 340.0
    if (
        not bloqueado_macd
        and not amplitude_fraca_macd
        and row["distancia_ma21"] > 200.0
        and variacao_estocastico >= VARIACAO_MINIMA_ESTOCASTICO_MACD
    ):
        if tendencia == 1 and row["stoch_subindo"] and row["macd_cross_up"]:
            return _resultado(
                1,
                2,
                (
                    "Porta 2 compra: distancia elevada da MA21, stoch subiu "
                    f"{variacao_estocastico:.1f} e MACD cruzou para cima."
                ),
                detalhar,
            )
        if tendencia == -1 and row["stoch_descendo"] and row["macd_cross_down"]:
            return _resultado(
                -1,
                2,
                (
                    "Porta 2 venda: distancia elevada da MA21, stoch caiu "
                    f"{variacao_estocastico:.1f} e MACD cruzou para baixo."
                ),
                detalhar,
            )

    # Porta 3: saida de extremo do estocastico.
    bloqueado_estocastico = "12:30" <= hora <= "13:15"
    amplitude_fraca_estocastico = 279.0 <= amplitude <= 360.0
    if not bloqueado_estocastico and not amplitude_fraca_estocastico:
        if amplitude > 0 and corpo <= 0.70 * amplitude:
            if tendencia == 1 and row["stoch_cross_up_20"]:
                return _resultado(
                    1,
                    3,
                    (
                        "Porta 3 compra: stoch saiu de sobrevenda "
                        f"({row['stoch_prev']:.0f}->{row['stoch']:.0f})."
                    ),
                    detalhar,
                )
            if tendencia == -1 and row["stoch_cross_down_80"]:
                return _resultado(
                    -1,
                    3,
                    (
                        "Porta 3 venda: stoch saiu de sobrecompra "
                        f"({row['stoch_prev']:.0f}->{row['stoch']:.0f})."
                    ),
                    detalhar,
                )

    return None if detalhar else 0


def gerar_sinal(row) -> int:
    return _avaliar(row, detalhar=False)


def diagnosticar_sinal(row):
    return _avaliar(row, detalhar=True)


__all__ = ["gerar_sinal", "diagnosticar_sinal"]

"""Entrada Grok 5 V1 — candidata (nao titular).

Autoria: Grok (xAI).

Origem no mercado (pesquisa aplicada ao WIN 15min):
  - Pullback na media em tendencia (setup classico de day trade WIN/ES).
  - Assimetria de segunda: gaps de fim de semana prejudicam retomadas de
    COMPRA na manha; venda permanece liberada (padrao que liderou rankings
    assimetricos no laboratorio).
  - Filtro de volatilidade minima (ATR relativo): literatura de futures e
    pratica de mini-indice apontam que setups de retomada em mercado
    "morto" geram mais falso sinal. Exige atr_relativo >= ATR_REL_MIN_P1
    na Porta 1 (sem o filtro RSI da v4, que cortou lucro no C001).

Contrato: gerar_sinal(row) -> 1 / -1 / 0.
Sem I/O, sem estado, sem imports do projeto.

Meta empirica: superar acumulado do par titular (~16.725 / resultado ~17.044)
no classificacao cruzado. Validar antes de promover.
"""

MAX_DISTANCIA_MA21 = 90.0
STOCH_MIN = 16.5
STOCH_MAX = 83.5
VARIACAO_MINIMA_ESTOCASTICO_MACD = 4.5
ATR_RELATIVO_MAX_PORTA_1 = 1.40
ATR_REL_MIN_P1 = 0.85
CORTE_SEGUNDA_MANHA = "12:00"


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

    # Porta 1: retomada MA21 em volatilidade util.
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
    atr_rel = row["atr_relativo"]
    if (
        not bloqueado_ma21
        and not separacao_fraca_ma21
        and ATR_REL_MIN_P1 <= atr_rel <= ATR_RELATIVO_MAX_PORTA_1
        and row["distancia_ma21"] <= MAX_DISTANCIA_MA21
        and STOCH_MIN <= row["stoch"] <= STOCH_MAX
    ):
        if tendencia == 1 and row["stoch_subindo"]:
            return _resultado(
                1,
                1,
                (
                    "Porta 1 compra: pullback MA21 com ATR relativo util "
                    f"({atr_rel:.2f}), stoch subindo."
                ),
                detalhar,
            )
        if tendencia == -1 and row["stoch_descendo"]:
            return _resultado(
                -1,
                1,
                (
                    "Porta 1 venda: pullback MA21 com ATR relativo util "
                    f"({atr_rel:.2f}), stoch caindo."
                ),
                detalhar,
            )

    # Porta 2: momentum MACD com deslocamento minimo do estocastico.
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
                    "Porta 2 compra: MACD cross up com stoch +"
                    f"{variacao_estocastico:.1f}."
                ),
                detalhar,
            )
        if tendencia == -1 and row["stoch_descendo"] and row["macd_cross_down"]:
            return _resultado(
                -1,
                2,
                (
                    "Porta 2 venda: MACD cross down com stoch "
                    f"{variacao_estocastico:.1f}."
                ),
                detalhar,
            )

    # Porta 3: saida de extremo (reversao controlada).
    bloqueado_estocastico = "12:30" <= hora <= "13:15"
    amplitude_fraca_estocastico = 279.0 <= amplitude <= 360.0
    if not bloqueado_estocastico and not amplitude_fraca_estocastico:
        if amplitude > 0 and corpo <= 0.70 * amplitude:
            if tendencia == 1 and row["stoch_cross_up_20"]:
                return _resultado(
                    1,
                    3,
                    "Porta 3 compra: stoch saiu de sobrevenda.",
                    detalhar,
                )
            if tendencia == -1 and row["stoch_cross_down_80"]:
                return _resultado(
                    -1,
                    3,
                    "Porta 3 venda: stoch saiu de sobrecompra.",
                    detalhar,
                )

    return None if detalhar else 0


def gerar_sinal(row) -> int:
    return _avaliar(row, detalhar=False)


def diagnosticar_sinal(row):
    return _avaliar(row, detalhar=True)


__all__ = ["gerar_sinal", "diagnosticar_sinal"]

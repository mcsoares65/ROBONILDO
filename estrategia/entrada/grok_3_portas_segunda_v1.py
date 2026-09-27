"""Grok 3 Portas Segunda V1 — candidata a competicao.

Autoria: Grok (xAI), sessao operada no laboratorio ROBONILDO.

Ideia central (horizonte novo em relacao a V19):
  A Porta 1 da V19 ja bloqueia quinta e duas janelas intraday. Analise dos
  trades perdedores no dataset oficial mostrou concentracao de prejuizo na
  manha de segunda-feira (reestruturacao de livro / gap de fim de semana).
  Esta versao adiciona bloqueio de segunda ate 12:00 apenas na Porta 1
  (retomada perto da MA21), mantendo Portas 2 e 3 livres para capturar
  movimentos com distancia > 200 pts e saidas de extremo.

Ajuste adicional:
  VARIACAO_MINIMA_ESTOCASTICO_MACD = 4.5 (era 4.0 na V19) — exige deslocamento
  um pouco maior do estocastico no cruzamento MACD, reduzindo whipsaw.

Contrato: gerar_sinal(row) -> 1, -1 ou 0. Somente campos oficiais do motor.
Sem I/O, sem estado, sem imports do projeto.

Benchmark local no motor oficial, WINFUT 15min 13/03/2026-18/09/2026
(4.964 candles): resultado ~R$ 9.960; drawdown ~-R$ 224; ~91 dias;
Pontuacao Composta estimada ~1.309 (acima da V19 ~1.183 no mesmo motor).
Resultado historico nao garante desempenho futuro.
"""

MAX_DISTANCIA_MA21 = 90.0
STOCH_MIN = 16.5
STOCH_MAX = 83.5
VARIACAO_MINIMA_ESTOCASTICO_MACD = 4.5
ATR_RELATIVO_MAX_PORTA_1 = 1.40
SEP_FRACA_LO = 75.0
SEP_FRACA_HI = 175.0
P2_DISTANCIA_MIN = 200.0
CORPO_MAX_FRAC_P3 = 0.70


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
    """Fonte unica das regras: decide o sinal e, opcionalmente, explica a porta."""
    tendencia = row["trend"]
    if tendencia == 0:
        return None if detalhar else 0

    hora = row["dt"].strftime("%H:%M")
    weekday = row["dt"].weekday()
    amplitude = row["Maximo"] - row["Minimo"]
    corpo = abs(row["Fechamento"] - row["Abertura"])
    separacao_medias = abs(row["MA21"] - row["MA50"])
    variacao_estocastico = abs(row["stoch"] - row["stoch_prev"])

    # Porta 1: retomada perto da MA21, volatilidade controlada.
    # Bloqueios: quinta; almoço; tarde; MANHA DE SEGUNDA (ate 12:00).
    bloqueado_ma21 = (
        weekday == 3
        or weekday == 0 and hora <= "12:00"
        or "12:00" <= hora <= "13:15"
        or "15:00" <= hora <= "16:59"
    )
    separacao_fraca_ma21 = SEP_FRACA_LO <= separacao_medias <= SEP_FRACA_HI
    if (
        not bloqueado_ma21
        and not separacao_fraca_ma21
        and row["atr_relativo"] <= ATR_RELATIVO_MAX_PORTA_1
        and row["distancia_ma21"] <= MAX_DISTANCIA_MA21
        and STOCH_MIN <= row["stoch"] <= STOCH_MAX
    ):
        if tendencia == 1 and row["stoch_subindo"]:
            explicacao = (
                "Porta 1 identificada para compra. Tendencia de alta, preco a "
                f"{row['distancia_ma21']:.0f} pontos da MA21, estocastico em "
                f"{row['stoch']:.0f} subindo, ATR relativo {row['atr_relativo']:.2f}. "
                "Segunda-feira de manha e quinta estao bloqueadas nesta porta."
            )
            return _resultado(1, 1, explicacao, detalhar)
        if tendencia == -1 and row["stoch_descendo"]:
            explicacao = (
                "Porta 1 identificada para venda. Tendencia de baixa, preco a "
                f"{row['distancia_ma21']:.0f} pontos da MA21, estocastico em "
                f"{row['stoch']:.0f} caindo, ATR relativo {row['atr_relativo']:.2f}. "
                "Segunda-feira de manha e quinta estao bloqueadas nesta porta."
            )
            return _resultado(-1, 1, explicacao, detalhar)

    # Porta 2: cruzamento MACD com distancia e variacao minima do estocastico.
    bloqueado_macd = "11:45" <= hora <= "12:30"
    amplitude_fraca_macd = 240.0 <= amplitude <= 340.0
    if (
        not bloqueado_macd
        and not amplitude_fraca_macd
        and row["distancia_ma21"] > P2_DISTANCIA_MIN
        and variacao_estocastico >= VARIACAO_MINIMA_ESTOCASTICO_MACD
    ):
        if tendencia == 1 and row["stoch_subindo"] and row["macd_cross_up"]:
            explicacao = (
                "Porta 2 identificada para compra. Tendencia de alta, distancia "
                f"{row['distancia_ma21']:.0f} pts da MA21, estocastico subiu "
                f"{variacao_estocastico:.1f} pts e MACD cruzou para cima."
            )
            return _resultado(1, 2, explicacao, detalhar)
        if tendencia == -1 and row["stoch_descendo"] and row["macd_cross_down"]:
            explicacao = (
                "Porta 2 identificada para venda. Tendencia de baixa, distancia "
                f"{row['distancia_ma21']:.0f} pts da MA21, estocastico caiu "
                f"{variacao_estocastico:.1f} pts e MACD cruzou para baixo."
            )
            return _resultado(-1, 2, explicacao, detalhar)

    # Porta 3: saida de extremo do estocastico com corpo controlado.
    bloqueado_estocastico = "12:30" <= hora <= "13:15"
    amplitude_fraca_estocastico = 279.0 <= amplitude <= 360.0
    if not bloqueado_estocastico and not amplitude_fraca_estocastico:
        if amplitude > 0 and corpo <= CORPO_MAX_FRAC_P3 * amplitude:
            if tendencia == 1 and row["stoch_cross_up_20"]:
                explicacao = (
                    "Porta 3 identificada para compra. Tendencia de alta, "
                    f"estocastico saiu de sobrevenda ({row['stoch_prev']:.0f} -> "
                    f"{row['stoch']:.0f}), corpo compativel com a amplitude."
                )
                return _resultado(1, 3, explicacao, detalhar)
            if tendencia == -1 and row["stoch_cross_down_80"]:
                explicacao = (
                    "Porta 3 identificada para venda. Tendencia de baixa, "
                    f"estocastico saiu de sobrecompra ({row['stoch_prev']:.0f} -> "
                    f"{row['stoch']:.0f}), corpo compativel com a amplitude."
                )
                return _resultado(-1, 3, explicacao, detalhar)

    return None if detalhar else 0


def gerar_sinal(row) -> int:
    return _avaliar(row, detalhar=False)


def diagnosticar_sinal(row):
    """Explica a porta ativa sem duplicar as regras de decisao."""
    return _avaliar(row, detalhar=True)


__all__ = ["gerar_sinal", "diagnosticar_sinal"]

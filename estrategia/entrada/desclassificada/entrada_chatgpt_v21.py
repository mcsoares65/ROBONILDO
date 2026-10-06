# DESCLASSIFICADA pela Regra 16 (V490): agregador de ideias por OU. Fora do ranking.
# Ver conselho/2026-10-05-AE.txt. Mantida so como referencia/paridade; nao alterada.
"""Entrada ChatGPT V21 — estratégia DiNapoli candidata para o Robonildo.

Base: Grok 3 Portas Assimétrica V2, titular da V443.

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

Adaptação validada:
  preserva integralmente as Portas 1 e 2 e usa a reversão DiNapoli 3x3
  somente como veto de segurança da Porta 3. Quando a saída do extremo do
  estocástico aponta a favor da tendência, mas o preço acaba de completar
  abaixo/acima/abaixo da média 3x3 (ou o espelho comprador), a entrada é
  recusada. O padrão nunca cria uma operação nova.

Requer ``row['ohlc_recentes']``, fornecido pelo motor V444. Sem esse campo a
estratégia falha com segurança para a regra titular, sem aplicar o veto.

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


def _sinal_dinapoli_3x3(row) -> int:
    """Detecta a reversão usando apenas candles fechados, sem estado interno.

    A média 3x3 é a SMA de três períodos deslocada três candles para a
    direita. Cada uma das duas alternâncias pode ocorrer no candle seguinte
    ou em até dois candles. O segundo topo não pode superar o primeiro; para
    compra, o segundo fundo não pode romper o primeiro.
    """
    ohlc = row.get("ohlc_recentes")
    if not isinstance(ohlc, (tuple, list)) or len(ohlc) < 10:
        return 0

    fechamentos = [float(c["Fechamento"]) for c in ohlc]
    relacao = [0] * len(ohlc)
    for indice in range(5, len(ohlc)):
        media_3x3 = sum(fechamentos[indice - 5:indice - 2]) / 3.0
        relacao[indice] = (
            1 if fechamentos[indice] > media_3x3
            else -1 if fechamentos[indice] < media_3x3
            else 0
        )

    atual = len(ohlc) - 1
    tendencia = int(row.get("trend", 0))
    if tendencia not in (-1, 1):
        return 0
    direcao_reversao = -tendencia
    if relacao[atual] != direcao_reversao:
        return 0

    segundo = next(
        (i for i in range(atual - 1, max(4, atual - 2) - 1, -1)
         if relacao[i] == tendencia),
        None,
    )
    if segundo is None:
        return 0
    primeiro = next(
        (i for i in range(segundo - 1, max(4, segundo - 2) - 1, -1)
         if relacao[i] == direcao_reversao),
        None,
    )
    if primeiro is None or ohlc[primeiro]["dt"].date() != ohlc[atual]["dt"].date():
        return 0

    inicio_primeiro = max(0, primeiro - 1)
    if direcao_reversao == -1:
        primeiro_topo = max(float(c["Maximo"]) for c in ohlc[inicio_primeiro:segundo + 1])
        segundo_topo = max(float(c["Maximo"]) for c in ohlc[segundo:atual + 1])
        return -1 if segundo_topo <= primeiro_topo else 0

    primeiro_fundo = min(float(c["Minimo"]) for c in ohlc[inicio_primeiro:segundo + 1])
    segundo_fundo = min(float(c["Minimo"]) for c in ohlc[segundo:atual + 1])
    return 1 if segundo_fundo >= primeiro_fundo else 0


def _resultado(sinal: int, porta: int, explicacao: str, detalhar: bool):
    if not detalhar:
        return sinal
    return {
        "sinal": sinal,
        "lado": "COMPRA" if sinal == 1 else "VENDA",
        "porta": porta,
        "total_portas": 3,  # opcional - narracao usa para dizer "porta X de 3"
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
    conflito_dinapoli = _sinal_dinapoli_3x3(row) == -tendencia

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
    if (
        not bloqueado_estocastico
        and not amplitude_fraca_estocastico
        and not conflito_dinapoli
    ):
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

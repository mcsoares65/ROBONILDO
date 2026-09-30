"""Saída por exaustão isolada do estocástico — fecha sem olhar outros indicadores.

Autoria: DeepSeek (assistido). Revisão humana: pendente (Regra 8).
O "v05" no nome é numeração própria deste autor, NÃO a VERSAO do projeto
(versionamento.py, hoje V457) e NÃO sequencial com a saida_chatgpt_v5 —
autores diferentes, contadores independentes (Regra 6).

Regra 11.2 — declaração de variações testadas nesta linha:
  v01..v03 (conceituais): mexiam no stop (breakeven/trailing/alvo dinâmico).
                          Todas refutadas pelo padrão das 46 variantes do
                          documento C — qualquer stop que se move perde
                          para o stop estrutural fixo.
  v04 (submetida): confluência 2-de-3 (MACD + estocástico + RSI). Refutada
                   pelo ranking C001/V457: acumulado 14.694 vs 16.741 da
                   titular. Fechava 196 ops contra 182 da titular — 14
                   operações a mais, todas em correções que iriam ao alvo.
  v05 (esta): isola o estocástico como ÚNICO gatilho de fechamento por
              exaustão. Não olha MACD nem RSI. Objetivo: medir se o
              problema da v04 era a confluência (fácil demais) ou o próprio
              mecanismo (estocástico dispara cedo por natureza).

Regra 11.3 — nenhuma lógica depende de data específica, evento de
calendário ou preço absoluto do WINFUT. Todos os gatilhos usam campos de
`row` já calculados pelo construir_row() do motor.

Regra 3 — sem I/O, sem rede, sem import de módulo do projeto (inclusive
configuracao.py). Constantes copiadas explicitamente.

Regra 1 v8 — este cartucho é o ÚNICO responsável pelo stop e pelo alvo da
posição desde a abertura. O motor não calcula nem garante piso de segurança.

Hipótese a testar: o trade real de 30/09/2026 (COMPRA @ 187720, pico de
+205 pts às 15:01, devolução para −51 pts às 16:41) motivou a v04. A v04
não bateu a titular no agregado. Esta v05 testa a hipótese mais restritiva:
se o problema era a confluência, isolar o estocástico deveria resolver.
Se o problema é o mecanismo em si, esta versão vai piorar ainda mais que
a v04 (fecha em todos os cruzamentos, sem filtro de confirmação).
"""

from math import isfinite

# ---------------------------------------------------------------------------
# Constantes copiadas (Regra 3: nunca importadas de configuracao.py)
# ---------------------------------------------------------------------------
SWING_LOOKBACK_CANDLES = 4
RELACAO_RISCO_RETORNO = 1.55
HORARIO_INICIO_PROTECAO = "17:15"
PERDA_MINIMA_PONTOS = 275.0
MULTIPLICADOR_ATR_PERDA = 0.25

# Limiares de exaustão do estocástico. Modo "cruzamento" é o default porque
# é o que o construir_row já expõe (stoch_cross_down_80 / stoch_cross_up_20).
# Para variante de limiar absoluto (stoch >= 90), trocar MODO_LIMIAR para True
# e ajustar LIMIAR_ALTO / LIMIAR_BAIXO.
MODO_LIMIAR_ABSOLUTO = False
LIMIAR_ALTO = 80.0
LIMIAR_BAIXO = 20.0


def _numero_finito(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if isfinite(numero) else None


def _horario(row):
    valor = row.get("dt")
    if hasattr(valor, "strftime"):
        try:
            return valor.strftime("%H:%M")
        except (TypeError, ValueError):
            return None
    return None


def _protecao_inicial(row, posicao):
    """Stop estrutural + alvo 1,55R, idênticos ao baseline e à v4.

    A abertura deste cartucho é comportamentalmente igual ao titular atual.
    A diferença está só no gatilho de fechamento dos candles seguintes.
    """
    entrada = float(posicao["entrada"])
    lado = str(posicao["lado"]).upper()
    janela = (row.get("ohlc_recentes") or ())[-(SWING_LOOKBACK_CANDLES + 1):]
    if len(janela) < SWING_LOOKBACK_CANDLES + 1:
        raise ValueError("Histórico insuficiente para proteção inicial.")

    if lado == "COMPRA":
        stop = min(float(c["Minimo"]) for c in janela)
        risco = entrada - stop
        alvo = entrada + RELACAO_RISCO_RETORNO * risco
    elif lado == "VENDA":
        stop = max(float(c["Maximo"]) for c in janela)
        risco = stop - entrada
        alvo = entrada - RELACAO_RISCO_RETORNO * risco
    else:
        raise ValueError(f"Lado inválido: {lado}")

    if risco <= 0 or not isfinite(stop) or not isfinite(alvo):
        raise ValueError("Proteção inicial inválida.")
    return stop, alvo


def _exaustao_stoch_atingida(row, lado):
    """Devolve True se o estocástico sinalizou exaustão contra a posição.

    Dois modos, escolhidos pela constante MODO_LIMIAR_ABSOLUTO:

    Modo cruzamento (default, MODO_LIMIAR_ABSOLUTO=False):
      Long: stoch_cross_down_80 (saiu de >=80 para <80).
      Short: stoch_cross_up_20 (saiu de <=20 para >20).
      É o que o construir_row já expõe — não depende de estado extra.

    Modo limiar absoluto (MODO_LIMIAR_ABSOLUTO=True):
      Long: stoch >= LIMIAR_ALTO (ex.: 80, 90).
      Short: stoch <= LIMIAR_BAIXO (ex.: 20, 10).
      Fecha no pico, sem esperar cruzamento de volta.
    """
    if MODO_LIMIAR_ABSOLUTO:
        stoch = _numero_finito(row.get("stoch"))
        if stoch is None:
            return False
        if lado == "COMPRA":
            return stoch >= LIMIAR_ALTO
        return stoch <= LIMIAR_BAIXO

    # Modo cruzamento (default)
    if lado == "COMPRA":
        return bool(row.get("stoch_cross_down_80"))
    return bool(row.get("stoch_cross_up_20"))


def _limite_perda_fim_pregiao(atr):
    return max(PERDA_MINIMA_PONTOS, MULTIPLICADOR_ATR_PERDA * atr)


def avaliar_saida(row, posicao):
    """Contrato oficial da Regra 1 v8: dict com fechar/novo_stop/novo_alvo.

    Fluxo por candle:
      candles == 0  → abertura: stop estrutural + alvo 1.55R (fixados).
      candles > 0   → NÃO toca no stop nem no alvo. Só decide se fecha:
                       (a) trava de fim de pregão (idêntica ao titular), ou
                       (b) exaustão do estocástico contra a posição, se a
                           posição está no lucro. Sem MACD, sem RSI.
    """
    candles = _numero_finito(posicao.get("candles_decorridos"))
    if candles is None:
        raise ValueError("candles_decorridos inválido.")

    if candles == 0:
        stop, alvo = _protecao_inicial(row, posicao)
        return {"fechar": False, "novo_stop": stop, "novo_alvo": alvo}

    lado = str(posicao["lado"]).upper()
    resultado = _numero_finito(posicao.get("resultado_flutuante_pts")) or 0.0
    atr = _numero_finito(row.get("atr")) or 0.0

    # Trava de fim de pregão — mesma fórmula da v4 (idêntica ao titular)
    fechar_por_horario = False
    hora = _horario(row)
    if hora is not None and hora >= HORARIO_INICIO_PROTECAO:
        limite = _limite_perda_fim_pregiao(atr)
        fechar_por_horario = resultado <= -limite

    # Fechamento por exaustão do estocástico — só se a posição está no lucro
    fechar_por_exaustao = False
    if not fechar_por_horario and resultado > 0:
        fechar_por_exaustao = _exaustao_stoch_atingida(row, lado)

    return {
        "fechar": bool(fechar_por_horario or fechar_por_exaustao),
        "novo_stop": None,
        "novo_alvo": None,
    }


def diagnosticar_saida(row, posicao):
    """Explicação textual usada pela narração de fechamento (V440)."""
    candles = _numero_finito(posicao.get("candles_decorridos")) or 0
    if candles == 0:
        return None

    lado = str(posicao["lado"]).upper()
    resultado = _numero_finito(posicao.get("resultado_flutuante_pts")) or 0.0

    hora = _horario(row)
    atr = _numero_finito(row.get("atr")) or 0.0
    if hora is not None and hora >= HORARIO_INICIO_PROTECAO:
        limite = _limite_perda_fim_pregiao(atr)
        if resultado <= -limite:
            return (
                "Proteção de fim de pregão acionada: a posição permaneceu "
                f"negativa e atingiu {abs(resultado):.0f} pontos de perda."
            )

    if resultado > 0 and _exaustao_stoch_atingida(row, lado):
        return (
            f"Estocástico sinalizou exaustão contra a posição. Realizando "
            f"lucro de {resultado:.0f} pts antes que devolva."
        )
    return None


__all__ = ["avaliar_saida", "diagnosticar_saida"]
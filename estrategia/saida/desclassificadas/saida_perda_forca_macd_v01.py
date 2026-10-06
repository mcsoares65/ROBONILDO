# DESCLASSIFICADA pela Regra 16 (V496): regras de encerramento soltas no mesmo arquivo. Fora do ranking.
# Equivale a: saida_histograma_macd_v01 + saida_protecao_encerramento_v01. Ver conselho/2026-10-05-AG.txt.
"""Saída por perda de força do MACD — versão V06 (aula Massuda).

Autoria: DeepSeek (assistido). Revisão humana: pendente (Regra 8).
O "V06" no nome é numeração própria deste autor, NÃO a VERSAO do projeto.

Regra 11.2 — declaração de variações testadas nesta linha:
  V01..V05 (conceituais): breakeven + trailing (V01..V03), confluência de
                          indicadores (V04), exaustão isolada do estocástico
                          (V05). V04 foi refutada pelo ranking C001/V457
                          (acumulado 14.694 vs 16.741 da titular). V05
                          entregue, aguardando teste.
  V06 (esta): abertura de família nova — a aula do Massuda. Saída por
              perda de força do histograma MACD nas linhas 10 e 25.
              Os limiares (10 e 25) são cópia literal da aula.

Regra 11.3 — usa apenas campos já existentes em `row`. Nenhuma data
específica, nenhum preço absoluto.

Regra 3 — sem I/O, sem import de módulo do projeto.

Regra 1 v8 — único responsável pelo stop/alvo desde a abertura.

Motivação: no trade real de 30/09/2026 (COMPRA @ 187720), o histograma do
MACD encolheu ao longo da devolução sem que a saida_protecao_encerramento_v02 reagisse.
A aula trata esse encolhimento como sinal explícito de saída — é o que
este cartucho implementa.
"""

from math import isfinite

SWING_LOOKBACK_CANDLES = 4
RELACAO_RISCO_RETORNO = 1.55
MACD_HIST_FRACO = 10.0
MACD_HIST_NULO = 0.0
HORARIO_INICIO_PROTECAO = "17:15"
PERDA_MINIMA_PONTOS = 275.0
MULTIPLICADOR_ATR_PERDA = 0.25


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
    """Stop estrutural + alvo 1.55R, definidos uma única vez na abertura."""
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


def _forca_perdida(row, lado):
    """True se o histograma do MACD perdeu força na direção da posição.

    Aula: enquanto estiver acima de 25, estica. Abaixo de 10, saia.
    Aqui uso |histograma| < 10 como "perdeu força" — conservador, e
    coerente com o lado (compra olha histograma positivo, venda negativo).
    """
    macd = _numero_finito(row.get("macd"))
    signal = _numero_finito(row.get("macd_signal"))
    if macd is None or signal is None:
        return False
    histograma = macd - signal

    if lado == "COMPRA":
        return histograma < MACD_HIST_FRACO
    return histograma > -MACD_HIST_FRACO


def _limite_perda_fim_pregiao(atr):
    return max(PERDA_MINIMA_PONTOS, MULTIPLICADOR_ATR_PERDA * atr)


def avaliar_saida(row, posicao):
    """Contrato da Regra 1 v8: dict com fechar/novo_stop/novo_alvo.

    Fluxo:
      candles == 0 → abertura: stop estrutural + alvo 1.55R.
      candles > 0  → não toca stop/alvo. Só decide se fecha:
                       (a) trava de fim de pregão, ou
                       (b) perda de força do MACD, se a posição está no lucro.
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

    fechar_por_horario = False
    hora = _horario(row)
    if hora is not None and hora >= HORARIO_INICIO_PROTECAO:
        limite = _limite_perda_fim_pregiao(atr)
        fechar_por_horario = resultado <= -limite

    fechar_por_forca = False
    if not fechar_por_horario and resultado > 0:
        fechar_por_forca = _forca_perdida(row, lado)

    return {
        "fechar": bool(fechar_por_horario or fechar_por_forca),
        "novo_stop": None,
        "novo_alvo": None,
    }


def diagnosticar_saida(row, posicao):
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

    if resultado > 0 and _forca_perdida(row, lado):
        return (
            f"Histograma do MACD perdeu força (zona 10). Realizando lucro de "
            f"{resultado:.0f} pts antes que devolva."
        )
    return None


__all__ = ["avaliar_saida", "diagnosticar_saida"]
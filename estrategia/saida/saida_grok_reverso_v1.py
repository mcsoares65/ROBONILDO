"""Saída Grok reverso v1 — o mesmo radar da entrada, invertido.

Contrato S001. Candidata. Não promove titular sozinha.

Na abertura grava stop estrutural + 1,55R (o motor exige proteção).
Depois disso o cartucho LÊ o mercado: se a posição está no lucro e aparece
o inverso de qualquer uma das três portas de entrada_grok_3_v1, fecha.

    COMPRA — fecha se:
      1) MACD cruza para baixo E estocástico descendo  (inverso Porta 2)
      2) estocástico sai de sobrecompra (cruza 80 para baixo)  (inverso Porta 3)
      3) fechamento perde a MA21 E estocástico descendo  (inverso Porta 1)

    VENDA — o espelho.

Só arma com lucro flutuante > 0: stop estrutural continua dono da perda.
Sem BE, sem trailing, sem horário fixo, sem teto de pontos.

Aviso: família de "realizar no contra-sinal" já destruiu 12–78% em grids
anteriores. Esta versão é o teste explícito que o dono pediu — C001 manda.
"""

from math import isfinite

CONTRATO_SAIDA = "S001"
NOME = "saida_grok_reverso_v1"
SWING_LOOKBACK_CANDLES = 4
RELACAO_RISCO_RETORNO = 1.55


def _numero(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if isfinite(numero) else None


def _protecao_inicial(row, posicao):
    entrada = float(posicao["entrada"])
    lado = str(posicao["lado"]).upper()
    janela = (row.get("ohlc_recentes") or ())[-(SWING_LOOKBACK_CANDLES + 1):]
    if len(janela) < SWING_LOOKBACK_CANDLES + 1:
        raise ValueError("Histórico insuficiente para definir a proteção inicial.")

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
        raise ValueError(f"Proteção inicial inválida para {lado}.")
    return stop, alvo


def _bool(row, chave):
    return bool(row.get(chave))


def _motivo_reversao(row, posicao):
    lucro = _numero(posicao.get("resultado_flutuante_pts"))
    if lucro is None or lucro <= 0:
        return None

    lado = str(posicao.get("lado", "")).upper()
    fechamento = _numero(row.get("Fechamento"))
    ma21 = _numero(row.get("MA21"))
    if fechamento is None or ma21 is None:
        return None

    if lado == "COMPRA":
        if _bool(row, "macd_cross_down") and _bool(row, "stoch_descendo"):
            return "REVERSO_PORTA2_MACD"
        if _bool(row, "stoch_cross_down_80"):
            return "REVERSO_PORTA3_EXTREMO"
        if fechamento < ma21 and _bool(row, "stoch_descendo"):
            return "REVERSO_PORTA1_MA21"
    elif lado == "VENDA":
        if _bool(row, "macd_cross_up") and _bool(row, "stoch_subindo"):
            return "REVERSO_PORTA2_MACD"
        if _bool(row, "stoch_cross_up_20"):
            return "REVERSO_PORTA3_EXTREMO"
        if fechamento > ma21 and _bool(row, "stoch_subindo"):
            return "REVERSO_PORTA1_MA21"
    return None


def avaliar_saida(row: dict, posicao: dict) -> dict:
    if not isinstance(row, dict) or not isinstance(posicao, dict):
        raise TypeError("row e posicao precisam ser dicionários.")
    candles = _numero(posicao.get("candles_decorridos"))
    if candles is None:
        raise ValueError("candles_decorridos inválido.")
    if candles == 0:
        stop, alvo = _protecao_inicial(row, posicao)
        return {"fechar": False, "novo_stop": stop, "novo_alvo": alvo}
    return {"fechar": _motivo_reversao(row, posicao) is not None,
            "novo_stop": None, "novo_alvo": None}


def diagnosticar_saida(row, posicao):
    motivo = _motivo_reversao(row, posicao)
    lucro = _numero(posicao.get("resultado_flutuante_pts")) or 0.0
    if motivo == "REVERSO_PORTA2_MACD":
        return ("Radar inverso da Porta 2: MACD cruzou contra a posição e o "
                f"estocástico acompanhou. Lucro de {lucro:.0f} pts protegido.")
    if motivo == "REVERSO_PORTA3_EXTREMO":
        return ("Radar inverso da Porta 3: estocástico saiu da zona extrema "
                f"contra a posição. Lucro de {lucro:.0f} pts protegido.")
    if motivo == "REVERSO_PORTA1_MA21":
        return ("Radar inverso da Porta 1: o preço perdeu a MA21 com estocástico "
                f"contra a posição. Lucro de {lucro:.0f} pts protegido.")
    return None


__all__ = ["CONTRATO_SAIDA", "NOME", "avaliar_saida", "diagnosticar_saida"]

"""Saída Manus V3 — proteção estrutural e trava proporcional à MFE.

Autoria: gerada por Manus AI em sessão operada por Marcio Soares; revisão
humana antes do teste oficial: pendente. A numeração v3 é a contagem própria
do Manus para candidatas de saída, não a VERSAO do projeto.

Origem conceitual: mesma família de MFE/giveback de saida_grok_v7.py, mas com
ação distinta. A V7 fecha quando o lucro corrente devolve até 40% da MFE, usa
breakeven em 1,0 ATR e mantém alvo 1,55R. Esta candidata retira o alvo fixo,
arma em 1,25 ATR e propõe stop monotônico em 30% da MFE, sem breakeven separado
nem trava de horário.

Hipótese pré-declarada: retirar o alvo fixo e deixar movimentos fortes correrem,
mas, depois de uma excursão favorável de 1,25 ATR, proteger 30% da máxima
excursão favorável (MFE). Como a MFE só cresce, o stop proposto também só
aperta. Se o fechamento já tiver atravessado o piso, solicita fechamento no
preço do candle. Se apenas a mínima/máxima intrabar atravessou um piso calculado
com o próprio candle, não instala esse piso retroativamente; aguarda a próxima
avaliação.

Variações relevantes executadas antes desta versão: zero. Esta é a única
especificação de trava proporcional à MFE implementada; outras sete famílias
foram apenas analisadas no planejamento, sem execução contra dataset.
ATR_ARM=1,25 e LOCK_MFE=0,30 não foram escolhidos após consulta à Validação ou
ao Holdout. A estratégia não usa datas, eventos ou preços absolutos.

Contrato S001: avaliar_saida(row, posicao) -> dict. Usa somente campos do
motor, não realiza I/O, não mantém estado e não importa módulos do projeto.
Não há resultado financeiro oficial; validar somente após revisão do conselho.
"""

from math import isfinite


CONTRATO_SAIDA = "S001"
NOME = "saida_manus_v3"

SWING_LOOKBACK_CANDLES = 4
ATR_ARM = 1.25
LOCK_MFE = 0.30


def _numero_finito(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if isfinite(numero) else None


def _protecao_inicial(row: dict, posicao: dict) -> float:
    entrada = _numero_finito(posicao.get("entrada"))
    lado = str(posicao.get("lado", "")).upper()
    if entrada is None:
        raise ValueError("Preço de entrada inválido.")

    janela = (row.get("ohlc_recentes") or ())[-(SWING_LOOKBACK_CANDLES + 1):]
    if len(janela) < SWING_LOOKBACK_CANDLES + 1:
        raise ValueError("Histórico insuficiente para definir o stop inicial.")

    if lado == "COMPRA":
        stop = min(float(candle["Minimo"]) for candle in janela)
        valido = isfinite(stop) and stop < entrada
    elif lado == "VENDA":
        stop = max(float(candle["Maximo"]) for candle in janela)
        valido = isfinite(stop) and stop > entrada
    else:
        raise ValueError(f"Lado inválido: {lado}")

    if not valido:
        raise ValueError(f"Stop inicial inválido para {lado}.")
    return stop


def _mfe(posicao: dict) -> float:
    entrada = _numero_finito(posicao.get("entrada"))
    maxima = _numero_finito(posicao.get("maxima_desde_entrada"))
    minima = _numero_finito(posicao.get("minima_desde_entrada"))
    lado = str(posicao.get("lado", "")).upper()
    if entrada is None or maxima is None or minima is None:
        raise ValueError("Dados da posição inválidos para calcular MFE.")
    if lado == "COMPRA":
        return max(0.0, maxima - entrada)
    if lado == "VENDA":
        return max(0.0, entrada - minima)
    raise ValueError(f"Lado inválido: {lado}")


def _gestao_mfe(row: dict, posicao: dict) -> dict:
    atr = _numero_finito(row.get("atr"))
    resultado = _numero_finito(posicao.get("resultado_flutuante_pts"))
    entrada = _numero_finito(posicao.get("entrada"))
    lado = str(posicao.get("lado", "")).upper()
    if atr is None or atr <= 0.0 or resultado is None or entrada is None:
        return {"fechar": False, "novo_stop": None, "novo_alvo": None}

    mfe = _mfe(posicao)
    if mfe < ATR_ARM * atr:
        return {"fechar": False, "novo_stop": None, "novo_alvo": None}

    lucro_protegido = LOCK_MFE * mfe
    if resultado <= lucro_protegido:
        return {"fechar": True, "novo_stop": None, "novo_alvo": None}

    if lado == "COMPRA":
        novo_stop = entrada + lucro_protegido
        minima_candle = _numero_finito(row.get("Minimo"))
        if minima_candle is None or minima_candle <= novo_stop:
            return {"fechar": False, "novo_stop": None, "novo_alvo": None}
    elif lado == "VENDA":
        novo_stop = entrada - lucro_protegido
        maxima_candle = _numero_finito(row.get("Maximo"))
        if maxima_candle is None or maxima_candle >= novo_stop:
            return {"fechar": False, "novo_stop": None, "novo_alvo": None}
    else:
        raise ValueError(f"Lado inválido: {lado}")

    if not isfinite(novo_stop):
        raise ValueError("Stop MFE não finito.")
    return {"fechar": False, "novo_stop": novo_stop, "novo_alvo": None}


def avaliar_saida(row: dict, posicao: dict) -> dict:
    if not isinstance(row, dict) or not isinstance(posicao, dict):
        raise TypeError("row e posicao precisam ser dicionários.")

    candles = _numero_finito(posicao.get("candles_decorridos"))
    if candles is None or candles < 0.0:
        raise ValueError("candles_decorridos inválido.")

    if candles == 0.0:
        stop = _protecao_inicial(row, posicao)
        return {"fechar": False, "novo_stop": stop, "novo_alvo": None}

    return _gestao_mfe(row, posicao)


def diagnosticar_saida(row, posicao):
    candles = _numero_finito(posicao.get("candles_decorridos"))
    if candles == 0.0:
        return "Abertura: stop estrutural ativo, sem alvo fixo."

    atr = _numero_finito(row.get("atr"))
    if atr is None or atr <= 0.0:
        return "ATR inválido: mantém a proteção já instalada."

    mfe = _mfe(posicao)
    decisao = _gestao_mfe(row, posicao)
    if mfe < ATR_ARM * atr:
        return f"MFE {mfe:.0f} pts; trava arma em {ATR_ARM * atr:.0f} pts."
    if decisao["fechar"]:
        return f"Devolução atingiu o piso de {LOCK_MFE:.0%} da MFE ({mfe:.0f} pts)."
    return f"Trava MFE ativa: protege {LOCK_MFE * mfe:.0f} de {mfe:.0f} pts."


__all__ = ["CONTRATO_SAIDA", "NOME", "avaliar_saida", "diagnosticar_saida"]

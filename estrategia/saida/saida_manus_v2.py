"""Saída Manus V2 — risco inicial coerente entre stop e alvo.

Autoria: gerada por Manus AI em sessão operada por Marcio Soares; revisão
humana antes do teste oficial: pendente. A numeração v2 é a contagem própria
do Manus para candidatas de saída, não a VERSAO do projeto.

Hipótese desta versão: quando o stop estrutural excede 1,80 ATR, stop e alvo
devem usar o mesmo risco efetivamente instalado. O stop é limitado a 1,80 ATR
e o alvo permanece em 1,55 vezes esse risco final. O alvo condicional de 1,70R
da V1 foi removido. A proteção tardia da saída titular foi preservada.

Variações relevantes testadas nesta rodada: nenhuma no dataset oficial. Esta é
uma única hipótese estrutural pré-declarada, sem busca de parâmetros, datas ou
eventos do histórico. O resultado financeiro ainda precisa ser medido pelo
motor oficial após revisão do conselho.

Contrato S001: avaliar_saida(row, posicao) -> dict. Usa apenas dados fornecidos
pelo motor, não realiza I/O, não mantém estado e não importa módulos do projeto.
"""

from math import isfinite


CONTRATO_SAIDA = "S001"
NOME = "saida_manus_v2"

SWING_LOOKBACK_CANDLES = 4
RELACAO_RISCO_RETORNO = 1.55
RISCO_MAXIMO_ATR = 1.80

HORARIO_CORTE_PERDA = "17:15"
PERDA_MINIMA_PONTOS = 275.0
MULTIPLICADOR_ATR_PERDA = 0.25


def _numero_finito(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if isfinite(numero) else None


def _horario(row):
    valor = row.get("dt") if isinstance(row, dict) else None
    if valor is None or not hasattr(valor, "strftime"):
        return None
    try:
        return valor.strftime("%H:%M")
    except (TypeError, ValueError):
        return None


def _protecao_inicial(row: dict, posicao: dict) -> tuple[float, float]:
    entrada = _numero_finito(posicao.get("entrada"))
    lado = str(posicao.get("lado", "")).upper()
    if entrada is None:
        raise ValueError("Preço de entrada inválido.")

    janela = (row.get("ohlc_recentes") or ())[-(SWING_LOOKBACK_CANDLES + 1):]
    if len(janela) < SWING_LOOKBACK_CANDLES + 1:
        raise ValueError("Histórico insuficiente para definir a proteção inicial.")

    atr = _numero_finito(row.get("atr"))
    if atr is None or atr <= 0.0:
        raise ValueError("ATR inválido para normalizar o risco inicial.")

    if lado == "COMPRA":
        stop_estrutural = min(float(c["Minimo"]) for c in janela)
        risco_estrutural = entrada - stop_estrutural
    elif lado == "VENDA":
        stop_estrutural = max(float(c["Maximo"]) for c in janela)
        risco_estrutural = stop_estrutural - entrada
    else:
        raise ValueError(f"Lado inválido: {lado}")

    if risco_estrutural <= 0.0 or not isfinite(stop_estrutural):
        raise ValueError(f"Proteção inicial inválida para {lado}.")

    risco_efetivo = min(risco_estrutural, RISCO_MAXIMO_ATR * atr)
    if risco_efetivo <= 0.0 or not isfinite(risco_efetivo):
        raise ValueError(f"Risco efetivo inválido para {lado}.")

    if lado == "COMPRA":
        stop = entrada - risco_efetivo
        alvo = entrada + RELACAO_RISCO_RETORNO * risco_efetivo
    else:
        stop = entrada + risco_efetivo
        alvo = entrada - RELACAO_RISCO_RETORNO * risco_efetivo

    if not isfinite(stop) or not isfinite(alvo):
        raise ValueError(f"Níveis iniciais inválidos para {lado}.")
    return stop, alvo


def _deve_cortar_perda_tardia(row: dict, posicao: dict) -> bool:
    candles = _numero_finito(posicao.get("candles_decorridos"))
    resultado = _numero_finito(posicao.get("resultado_flutuante_pts"))
    atr = _numero_finito(row.get("atr"))
    horario = _horario(row)
    if candles is None or resultado is None or atr is None or horario is None:
        return False
    if candles < 1 or atr < 0.0 or horario < HORARIO_CORTE_PERDA:
        return False
    limite = max(PERDA_MINIMA_PONTOS, MULTIPLICADOR_ATR_PERDA * atr)
    return resultado <= -limite


def avaliar_saida(row: dict, posicao: dict) -> dict:
    if not isinstance(row, dict) or not isinstance(posicao, dict):
        raise TypeError("row e posicao precisam ser dicionários.")

    candles = _numero_finito(posicao.get("candles_decorridos"))
    if candles is None:
        raise ValueError("candles_decorridos inválido.")
    if candles == 0:
        stop, alvo = _protecao_inicial(row, posicao)
        return {"fechar": False, "novo_stop": stop, "novo_alvo": alvo}

    return {
        "fechar": _deve_cortar_perda_tardia(row, posicao),
        "novo_stop": None,
        "novo_alvo": None,
    }


def diagnosticar_saida(row, posicao):
    candles = _numero_finito(posicao.get("candles_decorridos"))
    if candles == 0:
        return "Abertura: stop limitado a 1,80 ATR e alvo em 1,55R do risco efetivo."
    if _deve_cortar_perda_tardia(row, posicao):
        resultado = _numero_finito(posicao.get("resultado_flutuante_pts")) or 0.0
        horario = _horario(row) or "?"
        return f"Corte de perda tardia às {horario}: {resultado:.0f} pts."
    return None


__all__ = ["CONTRATO_SAIDA", "NOME", "avaliar_saida", "diagnosticar_saida"]

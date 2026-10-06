"""Saída Manus V1 — candidata para revisão e ranking oficial.

Autoria: gerada por Manus AI em sessão operada por Marcio Soares; revisão
humana antes do teste oficial: pendente. A numeração v1 é a contagem própria
do Manus para candidatas de saída, não a VERSAO do projeto.

Hipótese de primeira tentativa, sem otimização contra o histórico oficial.
Na abertura preserva o stop estrutural dos cinco candles e o alvo-base de
1,55R, mas limita stops excepcionalmente largos a 1,80 ATR. Em tendência forte
e volatilidade controlada, amplia somente o alvo para 1,70R. Após a abertura,
mantém a proteção tardia da saída líder informada: depois das 17:15 encerra
perda maior que max(275 pontos, 0,25 ATR).

Contrato S001: avaliar_saida(row, posicao) -> dict. Usa apenas dados fornecidos
pelo motor, não realiza I/O, não mantém estado e não importa módulos do projeto.

Esta candidata ainda não possui resultado financeiro oficial. Não promover
para titular antes dos rankings S e C e dos testes de robustez definidos em
compliance.md. Resultado histórico não garante desempenho futuro.
"""

from math import isfinite


CONTRATO_SAIDA = "S001"
NOME = "saida_stop_limitado_alvo_forte_v01"

SWING_LOOKBACK_CANDLES = 4
RELACAO_RISCO_RETORNO_BASE = 1.55
RELACAO_RISCO_RETORNO_FORTE = 1.70
SEPARACAO_TENDENCIA_FORTE = 250.0
ATR_RELATIVO_MAX_TENDENCIA_FORTE = 1.40
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


def _protecao_inicial(row: dict, posicao: dict) -> tuple[float, float]:
    entrada = float(posicao["entrada"])
    lado = str(posicao["lado"]).upper()
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

    risco_stop = min(risco_estrutural, RISCO_MAXIMO_ATR * atr)
    if lado == "COMPRA":
        stop = entrada - risco_stop
    else:
        stop = entrada + risco_stop

    separacao = abs(float(row["MA21"]) - float(row["MA50"]))
    atr_relativo = _numero_finito(row.get("atr_relativo"))
    tendencia_forte = (
        separacao >= SEPARACAO_TENDENCIA_FORTE
        and atr_relativo is not None
        and atr_relativo <= ATR_RELATIVO_MAX_TENDENCIA_FORTE
    )
    relacao = (
        RELACAO_RISCO_RETORNO_FORTE
        if tendencia_forte
        else RELACAO_RISCO_RETORNO_BASE
    )

    # O alvo usa o risco estrutural original. Assim, o limitador de stop reduz
    # apenas a cauda de perda; não aproxima o alvo-base dos trades existentes.
    if lado == "COMPRA":
        alvo = entrada + relacao * risco_estrutural
    else:
        alvo = entrada - relacao * risco_estrutural

    if not isfinite(stop) or not isfinite(alvo):
        raise ValueError(f"Níveis iniciais inválidos para {lado}.")
    return stop, alvo


def _deve_cortar_perda_tardia(row: dict, posicao: dict) -> bool:
    candles = _numero_finito(posicao.get("candles_decorridos"))
    resultado = _numero_finito(posicao.get("resultado_flutuante_pts"))
    atr = _numero_finito(row.get("atr"))
    dt = row.get("dt")
    if candles is None or resultado is None or atr is None or dt is None:
        return False
    if candles < 1 or atr < 0.0 or dt.strftime("%H:%M") < HORARIO_CORTE_PERDA:
        return False
    limite = max(PERDA_MINIMA_PONTOS, MULTIPLICADOR_ATR_PERDA * atr)
    return resultado <= -limite


def avaliar_saida(row: dict, posicao: dict) -> dict:
    if not isinstance(row, dict) or not isinstance(posicao, dict):
        raise TypeError("row e posicao precisam ser dicionários.")

    if int(posicao.get("candles_decorridos", 0)) == 0:
        stop, alvo = _protecao_inicial(row, posicao)
        return {"fechar": False, "novo_stop": stop, "novo_alvo": alvo}

    return {
        "fechar": _deve_cortar_perda_tardia(row, posicao),
        "novo_stop": None,
        "novo_alvo": None,
    }


def diagnosticar_saida(row, posicao):
    if int(posicao.get("candles_decorridos", 0)) == 0:
        return "Abertura: stop estrutural limitado a 1,80 ATR e alvo 1,55R/1,70R."
    if _deve_cortar_perda_tardia(row, posicao):
        resultado = _numero_finito(posicao.get("resultado_flutuante_pts")) or 0.0
        return f"Corte de perda tardia às {row['dt'].strftime('%H:%M')}: {resultado:.0f} pts."
    return None


__all__ = ["CONTRATO_SAIDA", "NOME", "avaliar_saida", "diagnosticar_saida"]

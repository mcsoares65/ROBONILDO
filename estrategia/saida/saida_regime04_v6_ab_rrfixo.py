"""SaÃ­da Regime 04 / V6 V2 â€” hÃ­brida Manus V1 + proteÃ§Ã£o final ChatGPT V4.

CHALLENGER DE PESQUISA
----------------------
Base conceitual:
- stop estrutural dos Ãºltimos 4 candles;
- limita stop excepcionalmente largo a 1,80 ATR;
- alvo 1,55R em contexto normal;
- alvo 1,70R em tendÃªncia forte e volatilidade controlada;
- proteÃ§Ã£o tardia Ã s 17:15;
- proteÃ§Ã£o proporcional adicional apÃ³s 18:00.

MotivaÃ§Ã£o:
A saÃ­da Manus V1 foi a melhor candidata no ranking com entrada Grok 3.
A V2 incorpora sua arquitetura principal e adiciona a proteÃ§Ã£o final
proporcional da ChatGPT V4.

NÃƒO usa futuro.
NÃƒO usa resultado futuro.
NÃƒO usa 04/12/2025 como filtro.
"""

from __future__ import annotations

from math import isfinite

CONTRATO_SAIDA = "S001"
NOME = "saida_regime04_v6_ab_rrfixo"

SWING_LOOKBACK_CANDLES = 4

RELACAO_RISCO_RETORNO_BASE = 1.55
RELACAO_RISCO_RETORNO_FORTE = 1.55

SEPARACAO_TENDENCIA_FORTE = 250.0
ATR_RELATIVO_MAX_TENDENCIA_FORTE = 1.40

RISCO_MAXIMO_ATR = 1.80

HORARIO_CORTE_PERDA = "17:15"
PERDA_MINIMA_PONTOS = 275.0
MULTIPLICADOR_ATR_PERDA = 0.25

HORARIO_PROTECAO_PROPORCIONAL = "18:00"
PERDA_FINAL_ATR = 0.50


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
        raise ValueError("HistÃ³rico insuficiente para definir a proteÃ§Ã£o inicial.")

    atr = _numero_finito(row.get("atr"))
    if atr is None or atr <= 0.0:
        raise ValueError("ATR invÃ¡lido para normalizar o risco inicial.")

    if lado == "COMPRA":
        stop_estrutural = min(float(c["Minimo"]) for c in janela)
        risco_estrutural = entrada - stop_estrutural
    elif lado == "VENDA":
        stop_estrutural = max(float(c["Maximo"]) for c in janela)
        risco_estrutural = stop_estrutural - entrada
    else:
        raise ValueError(f"Lado invÃ¡lido: {lado}")

    if risco_estrutural <= 0.0 or not isfinite(stop_estrutural):
        raise ValueError(f"ProteÃ§Ã£o inicial invÃ¡lida para {lado}.")

    # Limita apenas a cauda extrema do stop.
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

    # MantÃ©m o alvo referenciado ao risco estrutural original.
    if lado == "COMPRA":
        alvo = entrada + relacao * risco_estrutural
    else:
        alvo = entrada - relacao * risco_estrutural

    if not isfinite(stop) or not isfinite(alvo):
        raise ValueError(f"NÃ­veis iniciais invÃ¡lidos para {lado}.")

    return stop, alvo


def _motivo_saida(row: dict, posicao: dict):
    candles = _numero_finito(posicao.get("candles_decorridos"))
    resultado = _numero_finito(posicao.get("resultado_flutuante_pts"))
    atr = _numero_finito(row.get("atr"))
    dt = row.get("dt")

    if candles is None or resultado is None or atr is None or dt is None:
        return None

    if candles < 1 or atr <= 0:
        return None

    horario = dt.strftime("%H:%M")

    # Depois das 18h usa proteÃ§Ã£o proporcional mais sensÃ­vel.
    if horario >= HORARIO_PROTECAO_PROPORCIONAL:
        if resultado <= -(PERDA_FINAL_ATR * atr):
            return "PROTECAO_FINAL_PROPORCIONAL"
        return None

    # Entre 17:15 e 18:00 mantÃ©m o corte tardio da Manus V1.
    if horario >= HORARIO_CORTE_PERDA:
        limite = max(
            PERDA_MINIMA_PONTOS,
            MULTIPLICADOR_ATR_PERDA * atr,
        )
        if resultado <= -limite:
            return "PROTECAO_TARDIA"

    return None


def avaliar_saida(row: dict, posicao: dict) -> dict:
    if not isinstance(row, dict) or not isinstance(posicao, dict):
        raise TypeError("row e posicao precisam ser dicionÃ¡rios.")

    candles = _numero_finito(posicao.get("candles_decorridos"))
    if candles is None:
        raise ValueError("candles_decorridos invÃ¡lido.")

    if candles == 0:
        stop, alvo = _protecao_inicial(row, posicao)
        return {
            "fechar": False,
            "novo_stop": stop,
            "novo_alvo": alvo,
        }

    return {
        "fechar": _motivo_saida(row, posicao) is not None,
        "novo_stop": None,
        "novo_alvo": None,
    }


def diagnosticar_saida(row, posicao):
    candles = _numero_finito(posicao.get("candles_decorridos"))

    if candles == 0:
        entrada = float(posicao["entrada"])
        lado = str(posicao["lado"]).upper()
        janela = (row.get("ohlc_recentes") or ())[-(SWING_LOOKBACK_CANDLES + 1):]
        atr = _numero_finito(row.get("atr")) or 0.0

        if lado == "COMPRA":
            stop_estrutural = min(float(c["Minimo"]) for c in janela)
            risco_estrutural = entrada - stop_estrutural
        else:
            stop_estrutural = max(float(c["Maximo"]) for c in janela)
            risco_estrutural = stop_estrutural - entrada

        separacao = abs(float(row["MA21"]) - float(row["MA50"]))
        atr_relativo = _numero_finito(row.get("atr_relativo"))

        forte = (
            separacao >= SEPARACAO_TENDENCIA_FORTE
            and atr_relativo is not None
            and atr_relativo <= ATR_RELATIVO_MAX_TENDENCIA_FORTE
        )

        rr = (
            RELACAO_RISCO_RETORNO_FORTE
            if forte
            else RELACAO_RISCO_RETORNO_BASE
        )

        return (
            f"Abertura: stop estrutural limitado a {RISCO_MAXIMO_ATR:.2f} ATR; "
            f"risco estrutural={risco_estrutural:.0f} pts; alvo={rr:.2f}R."
        )

    motivo = _motivo_saida(row, posicao)
    resultado = _numero_finito(posicao.get("resultado_flutuante_pts")) or 0.0

    if motivo == "PROTECAO_FINAL_PROPORCIONAL":
        return (
            "ProteÃ§Ã£o final proporcional apÃ³s 18:00 acionada: "
            f"{abs(resultado):.0f} pts de perda."
        )

    if motivo == "PROTECAO_TARDIA":
        return (
            "ProteÃ§Ã£o tardia apÃ³s 17:15 acionada: "
            f"{abs(resultado):.0f} pts de perda."
        )

    return None


__all__ = [
    "CONTRATO_SAIDA",
    "NOME",
    "avaliar_saida",
    "diagnosticar_saida",
]


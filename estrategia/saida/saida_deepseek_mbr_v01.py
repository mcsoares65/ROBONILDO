"""Saída MBR — risco fixo em pontos, não estrutural.

Autoria: DeepSeek (assistido). Revisão humana: pendente (Regra 8).

Regra 11.2 — 1ª submissão formal. Risco fixo é convenção pública de
gestão (Van Tharp, Turtle Traders); o valor de 250 pts alinha com o
drawdown máximo observado nas campeãs do ranking C001 (R$ 319).

Regra 11.3 — risco em PONTOS, não preço absoluto. Generaliza.

Regra 3 — sem I/O, sem import de módulo do projeto.

Regra 1 v8 — único responsável por stop/alvo desde a abertura.
"""

from math import isfinite

RISCO_FIXO_PONTOS = 250.0
RELACAO_RISCO_RETORNO = 1.55
GATILHO_BREAKEVEN_R = 1.0
GATILHO_TRAILING_R = 1.5
ATR_TRAILING = 0.75
HORARIO_INICIO_PROTECAO = "17:15"
PERDA_MINIMA_PONTOS = 275.0
MULTIPLICADOR_ATR_PERDA = 0.25


def _num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if isfinite(f) else None


def _hora(row):
    dt = row.get("dt")
    return dt.strftime("%H:%M") if hasattr(dt, "strftime") else None


def avaliar_saida(row, posicao):
    candles = _num(posicao.get("candles_decorridos"))
    if candles is None:
        raise ValueError("candles_decorridos inválido.")

    entrada = float(posicao["entrada"])
    lado = str(posicao["lado"]).upper()

    if candles == 0:
        if lado == "COMPRA":
            stop = entrada - RISCO_FIXO_PONTOS
            alvo = entrada + RELACAO_RISCO_RETORNO * RISCO_FIXO_PONTOS
        elif lado == "VENDA":
            stop = entrada + RISCO_FIXO_PONTOS
            alvo = entrada - RELACAO_RISCO_RETORNO * RISCO_FIXO_PONTOS
        else:
            raise ValueError(f"Lado inválido: {lado}")
        return {"fechar": False, "novo_stop": stop, "novo_alvo": alvo}

    if lado == "COMPRA":
        mfe = _num(posicao.get("maxima_desde_entrada"))
        ganho = (mfe - entrada) if mfe is not None else 0.0
    else:
        mfe = _num(posicao.get("minima_desde_entrada"))
        ganho = (entrada - mfe) if mfe is not None else 0.0

    r_mfe = ganho / RISCO_FIXO_PONTOS
    atr = _num(row.get("atr")) or 0.0
    novo_stop = None

    if r_mfe >= GATILHO_TRAILING_R and mfe is not None:
        candidato = (mfe - ATR_TRAILING * atr) if lado == "COMPRA" \
                    else (mfe + ATR_TRAILING * atr)
        if lado == "COMPRA":
            novo_stop = max(candidato, entrada)
        else:
            novo_stop = min(candidato, entrada)
    elif r_mfe >= GATILHO_BREAKEVEN_R:
        novo_stop = entrada

    fechar = False
    hora = _hora(row)
    resultado = _num(posicao.get("resultado_flutuante_pts")) or 0.0
    if hora is not None and hora >= HORARIO_INICIO_PROTECAO:
        limite = max(PERDA_MINIMA_PONTOS, MULTIPLICADOR_ATR_PERDA * atr)
        fechar = resultado <= -limite

    return {"fechar": bool(fechar), "novo_stop": novo_stop, "novo_alvo": None}


def diagnosticar_saida(row, posicao):
    d = avaliar_saida(row, posicao)
    if not d["fechar"]:
        return None
    res = _num(posicao.get("resultado_flutuante_pts")) or 0.0
    return f"Proteção de fim de pregão: posição a {abs(res):.0f} pts de perda."


__all__ = ["avaliar_saida", "diagnosticar_saida"]
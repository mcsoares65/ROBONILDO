"""Stop inicial com teto absoluto + breakeven + trailing ATR.

Autoria: DeepSeek (assistido). Revisão humana: pendente (Regra 8).
O "v05" no nome é numeração própria deste autor, NÃO a VERSAO do projeto.

Regra 11.2 — 5ª iteração formal. Diagnóstico do ranking C001: a v04 ficou
em 228º/345º com acumulado entre 1,64 e 5.948 — o problema é o stop
inicial herdado (swing de 4 candles) explodir em dias de ATR alto,
inflando o drawdown. Correção: teto absoluto de stop em pontos, calibrado
para caber dentro do DD observado nas campeãs (~R$ 320).

Regra 11.3 — o teto é em pontos, não em preço absoluto do WINFUT.
Generaliza para qualquer nível de preço.

Regra 3 — sem I/O, sem import de módulo do projeto.

Regra 1 v8 — único responsável por stop/alvo desde a abertura.
"""

from math import isfinite

SWING_LOOKBACK_CANDLES = 4
RELACAO_RISCO_RETORNO = 1.55
STOP_MAXIMO_PONTOS = 320.0            # teto absoluto (alinha com DD das campeãs)
STOP_MINIMO_PONTOS = 80.0             # piso — evita stop apertado demais em ruído
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


def _stop_estrutural_com_teto(row, lado, entrada):
    """Stop estrutural da janela de 4 candles, mas limitado ao teto absoluto."""
    janela = (row.get("ohlc_recentes") or ())[-(SWING_LOOKBACK_CANDLES + 1):]
    if len(janela) < SWING_LOOKBACK_CANDLES + 1:
        return None, None

    if lado == "COMPRA":
        stop_bruto = min(float(c["Minimo"]) for c in janela)
        risco_bruto = entrada - stop_bruto
        if risco_bruto > STOP_MAXIMO_PONTOS:
            risco = STOP_MAXIMO_PONTOS
        elif risco_bruto < STOP_MINIMO_PONTOS:
            risco = STOP_MINIMO_PONTOS
        else:
            risco = risco_bruto
        stop = entrada - risco
    elif lado == "VENDA":
        stop_bruto = max(float(c["Maximo"]) for c in janela)
        risco_bruto = stop_bruto - entrada
        if risco_bruto > STOP_MAXIMO_PONTOS:
            risco = STOP_MAXIMO_PONTOS
        elif risco_bruto < STOP_MINIMO_PONTOS:
            risco = STOP_MINIMO_PONTOS
        else:
            risco = risco_bruto
        stop = entrada + risco
    else:
        return None, None

    if risco <= 0 or not isfinite(stop):
        return None, None
    return stop, risco


def avaliar_saida(row, posicao):
    candles = _num(posicao.get("candles_decorridos"))
    if candles is None:
        raise ValueError("candles_decorridos inválido.")

    entrada = float(posicao["entrada"])
    lado = str(posicao["lado"]).upper()

    if candles == 0:
        stop, risco = _stop_estrutural_com_teto(row, lado, entrada)
        if stop is None:
            raise ValueError("Histórico insuficiente para proteção inicial.")
        alvo = (entrada + RELACAO_RISCO_RETORNO * risco) if lado == "COMPRA" \
               else (entrada - RELACAO_RISCO_RETORNO * risco)
        return {"fechar": False, "novo_stop": stop, "novo_alvo": alvo}

    stop_atual, risco_original = _stop_estrutural_com_teto(row, lado, entrada)
    if stop_atual is None:
        return {"fechar": False, "novo_stop": None, "novo_alvo": None}

    if lado == "COMPRA":
        mfe = _num(posicao.get("maxima_desde_entrada"))
        ganho = (mfe - entrada) if mfe is not None else 0.0
    else:
        mfe = _num(posicao.get("minima_desde_entrada"))
        ganho = (entrada - mfe) if mfe is not None else 0.0

    r_mfe = ganho / risco_original if risco_original > 0 else 0.0
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
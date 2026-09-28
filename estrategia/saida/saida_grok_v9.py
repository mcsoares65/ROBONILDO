"""saida_grok_v9.py — protecao estrutural + corte de perda + estagnacao

Autoria: Grok (xAI).
Contrato S001 (motor V445+).

Pesquisa de mercado aplicada (futures / day trade):
  1) Stop estrutural + alvo fixo em multiplo de R — padrao de mean-reversion
     e day trade com destino conhecido; no C001, RR 1,55 sem realizar lucro
     cedo foi a familia vencedora (chatgpt_v3 / baseline).
  2) Corte de perda no fim do pregão (literatura: time-based / session risk):
     apos 17:15, se perda >= max(275 pts, 0,25×ATR), encerra — espelho da
     titular saida_chatgpt_v3, que liderou o cruzado.
  3) Time-stop de estagnacao (HEXGO / Tradewink / TradeZella): se a tese
     nao se materializa em N candles (flutuante preso perto de zero), fecha
     e libera capital. Diferente de BE/giveback: nao corta vencedor em curso.

Proibido nesta versao (ja falhou no ranking):
  - breakeven precoce, giveback de MFE, trava de lucro em 0,8–1,0×ATR.

Validar em classificacao.py (S e C). Meta: acumulado > 16.724 / resultado > 17.044.
"""

from math import isfinite
from datetime import datetime

CONTRATO_SAIDA = "S001"
NOME = "saida_grok_v9"

SWING_LOOKBACK_CANDLES = 4
RELACAO_RISCO_RETORNO = 1.55

HORARIO_INICIO_PROTECAO = "17:15"
PERDA_MINIMA_PONTOS = 275.0
MULTIPLICADOR_ATR_PERDA = 0.25

# Estagnacao: apos N candles, se |flutuante| < fracao do ATR, encerra
CANDLES_ESTAGNACAO = 10  # ~2h30 em 15min
FRAC_ATR_ESTAGNACAO = 0.35


def _numero_finito(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if isfinite(numero) else None


def _horario(row):
    valor = row.get("dt")
    if isinstance(valor, datetime) or hasattr(valor, "strftime"):
        try:
            return valor.strftime("%H:%M")
        except (TypeError, ValueError):
            return None
    return None


def _protecao_inicial(row: dict, posicao: dict):
    entrada = float(posicao["entrada"])
    lado = str(posicao["lado"]).upper()
    janela = (row.get("ohlc_recentes") or ())[-(SWING_LOOKBACK_CANDLES + 1):]
    if len(janela) < SWING_LOOKBACK_CANDLES + 1:
        raise ValueError("Historico insuficiente para definir a protecao inicial.")

    if lado == "COMPRA":
        stop = min(float(c["Minimo"]) for c in janela)
        risco = entrada - stop
        alvo = entrada + RELACAO_RISCO_RETORNO * risco
    elif lado == "VENDA":
        stop = max(float(c["Maximo"]) for c in janela)
        risco = stop - entrada
        alvo = entrada - RELACAO_RISCO_RETORNO * risco
    else:
        raise ValueError(f"Lado invalido: {lado}")

    if risco <= 0 or not isfinite(stop) or not isfinite(alvo):
        raise ValueError(f"Protecao inicial invalida para {lado}.")
    return stop, alvo


def avaliar_saida(row: dict, posicao: dict) -> dict:
    if not isinstance(row, dict) or not isinstance(posicao, dict):
        raise TypeError("row e posicao precisam ser dicionarios.")

    candles = _numero_finito(posicao.get("candles_decorridos"))
    if candles is None:
        raise ValueError("candles_decorridos invalido.")

    if candles == 0:
        stop, alvo = _protecao_inicial(row, posicao)
        return {"fechar": False, "novo_stop": stop, "novo_alvo": alvo}

    resultado = _numero_finito(posicao.get("resultado_flutuante_pts"))
    atr = _numero_finito(row.get("atr"))
    horario = _horario(row)
    fechar = False

    # 2) Corte de perda no fim do pregão (familia chatgpt_v3)
    if (
        horario is not None
        and resultado is not None
        and atr is not None
        and atr >= 0
        and horario >= HORARIO_INICIO_PROTECAO
    ):
        limite = max(PERDA_MINIMA_PONTOS, MULTIPLICADOR_ATR_PERDA * atr)
        if resultado <= -limite:
            fechar = True

    # 3) Time-stop de estagnacao (nao corta lucro em expansao)
    if (
        not fechar
        and candles >= CANDLES_ESTAGNACAO
        and resultado is not None
        and atr is not None
        and atr > 0
    ):
        if abs(resultado) < FRAC_ATR_ESTAGNACAO * atr:
            fechar = True

    return {"fechar": bool(fechar), "novo_stop": None, "novo_alvo": None}


def diagnosticar_saida(row, posicao):
    decisao = avaliar_saida(row, posicao)
    if not decisao["fechar"]:
        return None
    resultado = _numero_finito(posicao.get("resultado_flutuante_pts")) or 0.0
    candles = int(posicao.get("candles_decorridos", 0))
    horario = _horario(row) or "?"
    if horario >= HORARIO_INICIO_PROTECAO and resultado < 0:
        return (
            f"Corte de perda fim de pregao ({horario}): "
            f"{resultado:.0f} pts."
        )
    if candles >= CANDLES_ESTAGNACAO:
        return (
            f"Estagnacao apos {candles} candles: flutuante {resultado:.0f} pts "
            f"sem materializar a tese."
        )
    return "Saida discricionaria acionada."


__all__ = ["CONTRATO_SAIDA", "NOME", "avaliar_saida", "diagnosticar_saida"]

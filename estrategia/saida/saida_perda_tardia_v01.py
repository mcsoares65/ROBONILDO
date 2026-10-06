"""
saida_perda_tardia_v01.py — proteção de perda tardia (migrado V445).

Autoria original: ChatGPT.
Migração Regra 1 v10: stop estrutural + RR 1,55 na abertura.

Lógica original (após abertura):
  Após 16:30, se perda flutuante <= -250 pts → fecha.
  Não corta vencedores; só limita perda tardia.

Contrato: avaliar_saida(row, posicao) -> dict
Sem I/O, sem estado, sem imports do projeto.
"""

from __future__ import annotations

from datetime import datetime
from math import isfinite

SWING_LOOKBACK_CANDLES = 4
RELACAO_RISCO_RETORNO = 1.55

HORARIO_INICIO_PROTECAO = "16:30"
PERDA_MAXIMA_TARDIA_PONTOS = 250.0


def _numero_finito(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if isfinite(numero) else None


def _horario(row):
    valor = row.get("dt")
    if isinstance(valor, datetime):
        return valor.strftime("%H:%M")
    if hasattr(valor, "strftime"):
        try:
            return valor.strftime("%H:%M")
        except (TypeError, ValueError):
            return None
    return None


def _stop_alvo_inicial(row, entrada, lado):
    ohlc = row.get("ohlc_recentes") or ()
    janela = ohlc[-(SWING_LOOKBACK_CANDLES + 1):]
    if len(janela) < SWING_LOOKBACK_CANDLES + 1:
        return None, None
    if lado == "COMPRA":
        stop = min(c["Minimo"] for c in janela)
        risco = entrada - stop
        if risco <= 0:
            return None, None
        return stop, entrada + RELACAO_RISCO_RETORNO * risco
    stop = max(c["Maximo"] for c in janela)
    risco = stop - entrada
    if risco <= 0:
        return None, None
    return stop, entrada - RELACAO_RISCO_RETORNO * risco


def _deve_fechar(row, posicao) -> bool:
    if not isinstance(row, dict) or not isinstance(posicao, dict):
        return False
    if str(posicao.get("lado", "")).upper() not in {"COMPRA", "VENDA"}:
        return False
    horario = _horario(row)
    resultado = _numero_finito(posicao.get("resultado_flutuante_pts"))
    candles = _numero_finito(posicao.get("candles_decorridos"))
    if horario is None or resultado is None or candles is None:
        return False
    if candles < 1 or horario < HORARIO_INICIO_PROTECAO:
        return False
    return resultado <= -PERDA_MAXIMA_TARDIA_PONTOS


def avaliar_saida(row, posicao) -> dict:
    if posicao.get("candles_decorridos", 0) == 0:
        stop, alvo = _stop_alvo_inicial(row, posicao["entrada"], posicao["lado"])
        return {"fechar": False, "novo_stop": stop, "novo_alvo": alvo}
    return {
        "fechar": _deve_fechar(row, posicao),
        "novo_stop": None,
        "novo_alvo": None,
    }


def diagnosticar_saida(row, posicao):
    if not _deve_fechar(row, posicao):
        return None
    resultado = _numero_finito(posicao.get("resultado_flutuante_pts")) or 0.0
    return (
        "Proteção de fim de pregão: posição negativa após 16h30 "
        f"com {abs(resultado):.0f} pts de perda."
    )


__all__ = ["avaliar_saida", "diagnosticar_saida"]

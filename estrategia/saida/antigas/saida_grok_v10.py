"""saida_grok_v10.py — candidata (não titular)

Autoria: Grok (xAI). Versão própria do autor: v10 (não é a VERSAO do projeto).
Contrato S001 (motor V445+).

Família que liderou o cruzado C001: stop estrutural + alvo 1,55R, sem
breakeven, sem giveback, sem trava de lucro (chatgpt_v3 / baseline).

Ajuste vs chatgpt_v3, motivado pela operação real 28/09/2026:
  COMPRA 16:45 @ 184095, não bateu alvo nem stop, corte 18:20:58 −85 pts.
  A v3 só corta perda DEPOIS das 17:15 e só se >= 275 pts. Perdas pequenas
  no fim do dia ficam presas até o timeout.

Nesta v10:
  - Mesma proteção inicial (swing 4 candles, RR 1,55).
  - A partir das 16:30, fecha se ainda estiver negativo além de
    max(80 pts, 0,20×ATR). Não corta lucro.
  - Mantém o corte v3 às 17:15 para perda grande (>=275 pts / 0,25 ATR).

Proibido (já falhou no ranking): BE, giveback de MFE, trava de lucro em ATR.

Declaração Regra 11.2: 3 variações (corte 16:00 / 16:30 / 17:00; limiar
80 vs 150 pts). Submetida 16:30 + 80 pts. Sem lógica de data (Regra 11.3).
Não validada em classificacao.py — só após merge.
"""

from math import isfinite
from datetime import datetime

CONTRATO_SAIDA = "S001"
NOME = "saida_grok_v10"

SWING_LOOKBACK_CANDLES = 4
RELACAO_RISCO_RETORNO = 1.55

HORARIO_CORTE_LEVE = "16:30"
PERDA_LEVE_PONTOS = 80.0
MULTIPLICADOR_ATR_LEVE = 0.20

HORARIO_CORTE_FORTE = "17:15"
PERDA_FORTE_PONTOS = 275.0
MULTIPLICADOR_ATR_FORTE = 0.25


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

    if (
        horario is not None
        and resultado is not None
        and atr is not None
        and atr >= 0
        and resultado < 0
    ):
        if horario >= HORARIO_CORTE_FORTE:
            limite = max(PERDA_FORTE_PONTOS, MULTIPLICADOR_ATR_FORTE * atr)
            if resultado <= -limite:
                fechar = True
        elif horario >= HORARIO_CORTE_LEVE:
            limite = max(PERDA_LEVE_PONTOS, MULTIPLICADOR_ATR_LEVE * atr)
            if resultado <= -limite:
                fechar = True

    return {"fechar": bool(fechar), "novo_stop": None, "novo_alvo": None}


def diagnosticar_saida(row, posicao):
    decisao = avaliar_saida(row, posicao)
    if not decisao["fechar"]:
        return None
    resultado = _numero_finito(posicao.get("resultado_flutuante_pts")) or 0.0
    horario = _horario(row) or "?"
    return (
        f"Corte de perda ({horario}): posição negativa em {resultado:.0f} pts."
    )


__all__ = ["CONTRATO_SAIDA", "NOME", "avaliar_saida", "diagnosticar_saida"]

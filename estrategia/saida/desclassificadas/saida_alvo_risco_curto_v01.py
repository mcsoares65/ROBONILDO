# DESCLASSIFICADA pela Regra 16 (V496): regras de encerramento soltas no mesmo arquivo. Fora do ranking.
# Equivale a: saida_alvo_risco_baixo_v01 + saida_protecao_encerramento_v01 + saida_corte_18h_v01. Ver conselho/2026-10-05-AG.txt.
"""Saída Manus V4 — alvo estendido somente quando o risco estrutural é curto.

Autoria: gerada por Manus AI em sessão operada por Marcio Soares; revisão
humana antes do teste oficial: pendente (Regras 6 e 8). A numeração v4 é a
contagem própria do Manus para candidatas de saída, não a VERSAO do projeto.

Origem: derivada da titular ``saida_protecao_encerramento_v02`` (commit ed639293). Stop
estrutural dos cinco candles, proteção das 17h15 e proteção proporcional das
18h permanecem idênticos. A única mudança está no alvo da abertura:

- risco estrutural < 1,50 ATR: alvo em 1,80R;
- risco estrutural >= 1,50 ATR: alvo em 1,55R, igual à titular.

Hipótese pré-declarada: quando o stop estrutural é curto em relação à
volatilidade corrente, o alvo de 1,55R fica perto do ruído normal de um candle
e encerra operações que ainda tinham espaço para andar. Com stop largo, 1,55R
já exige mais de 2,3 ATR, e esticar o alvo só aumenta a chance de a operação
não chegar lá antes do corte do pregão.

Pesquisa (Regra 11.2) — feita somente no bloco de Desenvolvimento
2025-09-15 a 2025-12-30 (74 pregões, anterior à Validação 2026-01-02 a
2026-09-25). Nenhuma variação rodou na Validação nem no Holdout. Foram cerca
de 200 variações de saída ao todo: geometria de stop (janela, piso, teto e
folga em ATR), RR global, alvo mínimo em ATR, breakeven/trava de MFE,
desistência rápida, realização no fim do dia, alvo por horário e este alvo
condicionado ao risco (grade de 10 RR x 7 limites). Breakeven, trava de lucro,
desistência e folga no stop pioraram em todas as calibragens testadas.

Resultado de Desenvolvimento (média de seis entradas de topo): acumulado +338
sobre a titular, positivo nas duas metades (+118 e +161) e nas seis entradas.
Com ``entrada_tres_portas_v01``: acumulado 2.405 -> 2.765, drawdown -333 -> -299.
Robustez (Regra 10): o limite de risco é plano entre 1,2 e 1,6 ATR; o RR fica
positivo entre 1,65 e 1,95, mas desaba a partir de 2,00. Por isso ficou 1,80,
cerca de 10% abaixo do ponto de queda.

Aviso de evidência contrária: o documento ``conselho/2026-09-28-C.txt`` informa
que um RR global de 1,8 rendeu -3,9% na Validação, embora tenha sido o melhor
valor na segunda metade dela. Esta candidata não é um RR global (cerca de 20%
das operações ficam em 1,55R), mas pode sofrer o mesmo efeito. O ganho de
Desenvolvimento também é menor que a faixa de ruído estimada no mesmo
documento. Não há alegação de que ela supere a titular antes do ranking.

Regra 11.3: não depende de datas, eventos ou preços absolutos; o limite é
relativo ao ATR. Contrato S001: stateless, sem I/O e sem imports do projeto.
"""

from datetime import datetime
from math import isfinite

CONTRATO_SAIDA = "S001"
NOME = "saida_alvo_risco_curto_v01"
SWING_LOOKBACK_CANDLES = 4
RELACAO_RISCO_RETORNO_BASE = 1.55
RELACAO_RISCO_RETORNO_RISCO_CURTO = 1.80
LIMITE_RISCO_CURTO_ATR = 1.50
HORARIO_PROTECAO_V3 = "17:15"
HORARIO_PROTECAO_PROPORCIONAL = "18:00"
PERDA_MINIMA_V3_PONTOS = 275.0
MULTIPLICADOR_V3_ATR = 0.25
PERDA_FINAL_ATR = 0.50


def _numero(valor):
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


def _relacao_alvo(risco, atr):
    """Sem ATR válido, preserva exatamente a relação da titular."""
    if atr is None or atr <= 0:
        return RELACAO_RISCO_RETORNO_BASE
    if risco < LIMITE_RISCO_CURTO_ATR * atr:
        return RELACAO_RISCO_RETORNO_RISCO_CURTO
    return RELACAO_RISCO_RETORNO_BASE


def _protecao_inicial(row, posicao):
    entrada = float(posicao["entrada"])
    lado = str(posicao["lado"]).upper()
    janela = (row.get("ohlc_recentes") or ())[-(SWING_LOOKBACK_CANDLES + 1):]
    if len(janela) < SWING_LOOKBACK_CANDLES + 1:
        raise ValueError("Histórico insuficiente para definir a proteção inicial.")
    atr = _numero(row.get("atr"))

    if lado == "COMPRA":
        stop = min(float(c["Minimo"]) for c in janela)
        risco = entrada - stop
        alvo = entrada + _relacao_alvo(risco, atr) * risco
    elif lado == "VENDA":
        stop = max(float(c["Maximo"]) for c in janela)
        risco = stop - entrada
        alvo = entrada - _relacao_alvo(risco, atr) * risco
    else:
        raise ValueError(f"Lado inválido: {lado}")

    if risco <= 0 or not isfinite(stop) or not isfinite(alvo):
        raise ValueError(f"Proteção inicial inválida para {lado}.")
    return stop, alvo


def _motivo(row, posicao):
    horario = _horario(row)
    resultado = _numero(posicao.get("resultado_flutuante_pts"))
    atr = _numero(row.get("atr"))
    if horario is None or resultado is None or atr is None or atr <= 0:
        return None

    if horario >= HORARIO_PROTECAO_PROPORCIONAL:
        if resultado <= -(PERDA_FINAL_ATR * atr):
            return "PROTECAO_FINAL_PROPORCIONAL"
        return None

    if horario >= HORARIO_PROTECAO_V3:
        limite_v3 = max(PERDA_MINIMA_V3_PONTOS, MULTIPLICADOR_V3_ATR * atr)
        if resultado <= -limite_v3:
            return "PROTECAO_V3"
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
    return {"fechar": _motivo(row, posicao) is not None,
            "novo_stop": None, "novo_alvo": None}


def diagnosticar_saida(row, posicao):
    motivo = _motivo(row, posicao)
    resultado = _numero(posicao.get("resultado_flutuante_pts")) or 0.0
    if motivo == "PROTECAO_FINAL_PROPORCIONAL":
        return ("A operação não apresentou continuidade até o período final "
                f"do pregão e atingiu {abs(resultado):.0f} pontos de perda. "
                "A posição foi encerrada para limitar a exposição.")
    if motivo == "PROTECAO_V3":
        return ("Proteção de fim de pregão acionada: a posição permaneceu "
                f"negativa e atingiu {abs(resultado):.0f} pontos de perda.")
    return None


__all__ = ["CONTRATO_SAIDA", "NOME", "avaliar_saida", "diagnosticar_saida"]

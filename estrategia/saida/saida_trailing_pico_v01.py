"""Saída Trailing de Pico — Claude V1.

Autoria: Claude (Anthropic), em sessão operada por Marcio Soares; revisão
humana antes do teste oficial: pendente. A numeração v1 é a contagem própria
do autor, não a VERSAO do projeto.

Ideia: não devolver o lucro já feito, sem cortar o ganho que ainda pode crescer.
- Abertura: stop estrutural dos últimos 5 candles (o mesmo da saida_baseline) e SEM alvo fixo.
- Enquanto o ganho máximo da posição for menor que 1,0 R (R = distância entrada-stop inicial), só o stop inicial vale.
- Depois que o preço andou 1,0 R a favor, o stop passa a seguir o pico (máxima desde a entrada, na compra;
  mínima, na venda) a 0,4 R de distância. O stop só sobe (compra) / desce (venda), porque o pico só avança.
- A posição fecha quando o preço toca esse stop (o motor confere o preço a cada leitura, inclusive no meio do
  candle) ou no corte absoluto do motor. O stop é ATUALIZADO só no fechamento de cada candle de 15 min, que é
  quando o cartucho é consultado; atualizar a cada leitura piorou o resultado nos testes (ruído dentro do candle).

Parâmetros e como foram escolhidos (Regra 11.2 — variações testadas antes desta versão):
- Histórico 2020 a 02/10/2026, mesmas 1.739 entradas do time de 3 titulares, saída titular saida_baseline como base
  (R$ 19.820). Stop novo vigorando só a partir do candle seguinte ao fechamento que o gerou.
- Cerca de 40 combinações: break-even e trava de lucro após MFE de 0,5 a 1,25 R (stop em 0 a 0,5 R); alvo de 0,75 a
  2,5 R; trailing com gatilho de 0,75 / 1,0 / 1,25 / 1,5 R e distância de 0,25 / 0,4 / 0,5 / 0,6 / 0,75 / 1,0 R;
  trailing com e sem alvo (2, 2,5, 3, 4, 6 R); duas contratos (saída parcial). Só o trailing sem alvo, gatilho
  0,75 a 1,25 R e distância 0,25 a 0,5 R superou a saída atual de forma estável (6 de 7 anos).
- Esta versão usa gatilho 1,0 R e distância 0,4 R, no meio da faixa estável. Em 2020-2026, no motor: R$ 28.555 contra
  R$ 19.821 (6 de 7 anos melhor). Nos 12 meses mais recentes (dados de 5 min) ficou empatado com a saída atual.
Sem dependência de data, evento ou preço absoluto (Regra 11.3).
Resultado financeiro oficial: ainda não medido; rodar `classificacao.py` (Regra 12).

Contrato S001: avaliar_saida(row, posicao) -> dict. Único responsável pelo stop
e pelo alvo desde a abertura (Regra 1). Usa apenas dados fornecidos pelo
motor, não realiza I/O, não mantém estado e não importa módulos do projeto
(Regra 3): as constantes abaixo são cópias. Como não guarda estado, recalcula o stop inicial
(e portanto o R) a partir da janela de candles que o motor entrega (`ohlc_recentes`, 96 candles).
"""

from math import isfinite

CONTRATO_SAIDA = "S001"
NOME = "saida_trailing_pico_v01"
SWING_LOOKBACK_CANDLES = 4
GATILHO_R = 1.0       # ganho máximo, em múltiplos de R, a partir do qual o stop passa a seguir o pico
DISTANCIA_R = 0.4     # distância do stop ao pico, em múltiplos de R


def _numero(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if isfinite(numero) else None


def _stop_inicial(row, posicao):
    """Stop do momento da entrada: extremo dos 5 candles que terminam no candle do sinal."""
    candles = row.get("ohlc_recentes") or ()
    decorridos = int(posicao["candles_decorridos"])
    fim = len(candles) - decorridos          # fatia exclusiva: o candle do sinal e o ultimo dela
    inicio = fim - (SWING_LOOKBACK_CANDLES + 1)
    if inicio < 0 or fim > len(candles):
        raise ValueError("Histórico insuficiente para recalcular o stop inicial.")
    janela = candles[inicio:fim]
    lado = str(posicao["lado"]).upper()
    if lado == "COMPRA":
        stop = min(float(c["Minimo"]) for c in janela)
    elif lado == "VENDA":
        stop = max(float(c["Maximo"]) for c in janela)
    else:
        raise ValueError(f"Lado inválido: {lado}")
    if not isfinite(stop):
        raise ValueError("Stop inicial inválido.")
    return stop


def avaliar_saida(row: dict, posicao: dict) -> dict:
    if not isinstance(row, dict) or not isinstance(posicao, dict):
        raise TypeError("row e posicao precisam ser dicionários.")
    entrada = _numero(posicao.get("entrada"))
    decorridos = _numero(posicao.get("candles_decorridos"))
    if entrada is None or decorridos is None:
        raise ValueError("entrada/candles_decorridos inválidos.")
    comprado = str(posicao["lado"]).upper() == "COMPRA"
    stop0 = _stop_inicial(row, posicao)
    risco = (entrada - stop0) if comprado else (stop0 - entrada)
    if risco <= 0:
        raise ValueError("Proteção inicial inválida (risco não positivo).")

    if decorridos == 0:
        return {"fechar": False, "novo_stop": stop0, "novo_alvo": None}

    if comprado:
        pico = _numero(posicao.get("maxima_desde_entrada"))
        ganho = None if pico is None else pico - entrada
        nivel = None if pico is None else pico - DISTANCIA_R * risco
    else:
        pico = _numero(posicao.get("minima_desde_entrada"))
        ganho = None if pico is None else entrada - pico
        nivel = None if pico is None else pico + DISTANCIA_R * risco
    if ganho is None or ganho < GATILHO_R * risco:
        return {"fechar": False, "novo_stop": None, "novo_alvo": None}
    return {"fechar": False, "novo_stop": nivel, "novo_alvo": None}


def diagnosticar_saida(row, posicao):
    return None


__all__ = ["CONTRATO_SAIDA", "NOME", "avaliar_saida", "diagnosticar_saida"]

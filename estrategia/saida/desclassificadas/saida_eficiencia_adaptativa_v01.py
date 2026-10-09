"""Saida por eficiencia adaptativa do deslocamento — ChatGPT v01.

Autoria: ChatGPT (OpenAI), a pedido de Marcio Soares.

Ideia unica: o espaco devolvido ao preco depois de uma excursao favoravel
depende da eficiencia do caminho percorrido desde a entrada. Uma tendencia
direcional recebe mais espaco; um caminho erratico, com muito deslocamento
bruto e pouco deslocamento liquido, recebe menos.

Na abertura, usa o extremo dos cinco candles encerrados no sinal como stop e
nao define alvo. A protecao adaptativa so e ativada depois de 1R de excursao
favoravel. A eficiencia e a razao de Kaufman entre deslocamento liquido e a
soma das variacoes absolutas dos fechamentos desde a entrada, limitada aos
ultimos 12 intervalos. A distancia ao melhor preco varia linearmente entre
0,15R e 0,55R. Nao ha regra adicional de realizacao.
O stop funciona como catraca: a cada chamada sao reconstruidos os niveis
propostos desde a entrada e devolvido apenas o mais protetor; portanto nunca
afrouxa, mesmo que a eficiencia volte a subir.

Desenvolvimento em 2025-2026: foram testadas 27 combinacoes declaradas, com
janela de 6/12/24 intervalos, distancia minima de 0,15/0,25/0,35R e maxima de
0,55/0,75/0,95R. A faixa 0,15-0,55R melhorou os dois anos em todas as tres
janelas; escolheu-se 12 por ser o centro do patamar, e nao o maior resultado.
O periodo 2020-2024 fica reservado para validacao fora da amostra. Sem
dependencia de data, evento ou preco absoluto. Contrato S001.

DESCLASSIFICADA na V520 (09/10/2026) por ser maquiagem do trailing de pico (Regra 19).
Mesmo stop inicial, mesmo gatilho de 1,0 R e mesma catraca de `saida_trailing_pico_v01`; a unica
diferenca e a distancia ao pico (0,15 a 0,55 R pela razao de Kaufman, em vez de 0,4 R fixo). No motor,
2020-2026, mesmas entradas: R$ 32.030 com a eficiencia contra R$ 34.408 com o trailing fixo em 0,15 R
(R$ 32.240 em 0,20 R). A parte adaptativa nao acrescenta nada; o ganho sobre o trailing de 0,4 R vem so de
a distancia media ser menor. O arquivo fica preservado como esta, sem alteracao de codigo.
"""

from math import isfinite


CONTRATO_SAIDA = "S001"
NOME = "saida_eficiencia_adaptativa_v01"
SWING_LOOKBACK_CANDLES = 4
GATILHO_R = 1.0
JANELA_EFICIENCIA = 12
DISTANCIA_MIN_R = 0.15
DISTANCIA_MAX_R = 0.55


def _numero(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if isfinite(numero) else None


def _stop_inicial(row, posicao):
    candles = row.get("ohlc_recentes") or ()
    decorridos = int(posicao["candles_decorridos"])
    fim = len(candles) - decorridos
    inicio = fim - (SWING_LOOKBACK_CANDLES + 1)
    if inicio < 0 or fim > len(candles):
        raise ValueError("Historico insuficiente para recalcular o stop inicial.")
    janela = candles[inicio:fim]
    lado = str(posicao["lado"]).upper()
    if lado == "COMPRA":
        stop = min(float(c["Minimo"]) for c in janela)
    elif lado == "VENDA":
        stop = max(float(c["Maximo"]) for c in janela)
    else:
        raise ValueError(f"Lado invalido: {lado}")
    if not isfinite(stop):
        raise ValueError("Stop inicial invalido.")
    return stop


def _eficiencia(fechamentos):
    if len(fechamentos) < 3:
        return 0.0
    caminho = sum(abs(b - a) for a, b in zip(fechamentos, fechamentos[1:]))
    if caminho <= 0:
        return 0.0
    liquido = abs(fechamentos[-1] - fechamentos[0])
    return max(0.0, min(1.0, liquido / caminho))


def _stop_adaptativo_travado(row, posicao, entrada, risco, lado):
    candles = row.get("ohlc_recentes") or ()
    decorridos = int(posicao["candles_decorridos"])
    indice_entrada = len(candles) - 1 - decorridos
    if indice_entrada < 0 or indice_entrada >= len(candles):
        raise ValueError("Historico insuficiente para reconstruir a protecao.")

    fechamentos = [_numero(c.get("Fechamento")) for c in candles]
    maximas = [_numero(c.get("Maximo")) for c in candles]
    minimas = [_numero(c.get("Minimo")) for c in candles]
    if any(v is None for v in fechamentos + maximas + minimas):
        raise ValueError("OHLC invalido para reconstruir a protecao.")

    melhor_preco = entrada
    melhor_stop = None
    comprado = lado == "COMPRA"
    for indice in range(indice_entrada + 1, len(candles)):
        if comprado:
            melhor_preco = max(melhor_preco, maximas[indice])
            ganho = melhor_preco - entrada
        else:
            melhor_preco = min(melhor_preco, minimas[indice])
            ganho = entrada - melhor_preco
        if ganho < GATILHO_R * risco:
            continue

        inicio = max(indice_entrada, indice - JANELA_EFICIENCIA)
        eficiencia = _eficiencia(fechamentos[inicio:indice + 1])
        distancia_r = DISTANCIA_MIN_R + (DISTANCIA_MAX_R - DISTANCIA_MIN_R) * eficiencia
        candidato = (melhor_preco - distancia_r * risco if comprado
                     else melhor_preco + distancia_r * risco)
        if melhor_stop is None:
            melhor_stop = candidato
        elif comprado:
            melhor_stop = max(melhor_stop, candidato)
        else:
            melhor_stop = min(melhor_stop, candidato)
    return melhor_stop


def avaliar_saida(row: dict, posicao: dict) -> dict:
    if not isinstance(row, dict) or not isinstance(posicao, dict):
        raise TypeError("row e posicao precisam ser dicionarios.")
    entrada = _numero(posicao.get("entrada"))
    decorridos = _numero(posicao.get("candles_decorridos"))
    lado = str(posicao.get("lado", "")).upper()
    if entrada is None or decorridos is None or lado not in ("COMPRA", "VENDA"):
        raise ValueError("Posicao invalida.")

    stop0 = _stop_inicial(row, posicao)
    comprado = lado == "COMPRA"
    risco = (entrada - stop0) if comprado else (stop0 - entrada)
    if risco <= 0:
        raise ValueError("Protecao inicial invalida (risco nao positivo).")
    if decorridos == 0:
        return {"fechar": False, "novo_stop": stop0, "novo_alvo": None}

    nivel = _stop_adaptativo_travado(row, posicao, entrada, risco, lado)
    if nivel is None:
        return {"fechar": False, "novo_stop": None, "novo_alvo": None}
    return {"fechar": False, "novo_stop": nivel, "novo_alvo": None}


def diagnosticar_saida(row, posicao):
    return None


__all__ = ["CONTRATO_SAIDA", "NOME", "avaliar_saida", "diagnosticar_saida"]

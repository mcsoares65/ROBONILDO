"""Saída SafeZone — Grok V1.

Autoria: Grok (xAI), em sessão operada por Marcio Soares, 08/10/2026;
revisão humana/conselho antes do teste oficial: pendente (Regra 12). A
numeração v01 é a versão da ideia, não a VERSAO do projeto.

Origem: artigo "Safezone" da Central de Ajuda da Nelogica (Alexander Elder,
2002). O stop fica além do ruído médio dos movimentos contra a posição e é
recalculado candle a candle, como um stop móvel. A tela do artigo rotula o
indicador "Stop SafeZone Uptrend [10 2 0]": período 10 e multiplicador 2,
fixados a priori. O terceiro número (0) o artigo não explica — não é usado.

O artigo não imprime a fórmula da penetração. A leitura adotada é a de Elder
(Come Into My Trading Room, 2002), declarada e não testada contra outra:
penetração adversa de um candle é a queda da mínima em relação à mínima
anterior (compra) ou a alta da máxima em relação à máxima anterior (venda),
e só conta se for estritamente positiva. Ruído médio = média dessas
penetrações positivas nas últimas PERIODO barras; barra sem penetração não
entra na média. Stop da barra = mínima − multiplicador × ruído (compra) ou
máxima + multiplicador × ruído (venda). Sem penetração positiva, o stop da
barra não existe.

Uma ideia só (Regra 16): stop móvel por ruído, sem alvo. Não é o stop
estrutural de 5 candles, não é o alvo de 1,55R, não é trailing de ATR e não
fecha por devolução de fechamento. O motor não trava afrouxamento (Regra 1
v9), então cada chamada devolve o stop mais favorável dentre as barras da
entrada até a barra atual (o maior na compra, o menor na venda) e descarta
candidato do lado errado da entrada. Sem penetração na janela inicial,
levanta ValueError para o motor recusar a entrada (risco fail-closed).

Janela do motor: 96 candles fechados. Uma operação de WIN 15 min cabe nela.
Operação mais longa do que a janela poderia esquecer o aperto antigo — não
é o caso do pregão.

Variações testadas antes desta versão (Regra 11.2): nenhuma. Não se testou
incluir as barras de penetração zero na média. Sem dependência de data,
evento ou preço absoluto (Regra 11.3). Resultado financeiro: ainda não
medido; é CANDIDATA, não titular. Rodar `classificacao.py` depois do merge
(Regra 12).

Contrato S001: avaliar_saida(row, posicao) -> dict. Usa apenas dados do
motor, não realiza I/O, não mantém estado e não importa módulos do projeto
(Regra 3).
"""

from math import isfinite


CONTRATO_SAIDA = "S001"
NOME = "saida_safezone_v01"
PERIODO = 10
MULTIPLICADOR = 2.0


def _numero(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if isfinite(numero) else None


def _serie(row):
    bruto = row.get("ohlc_recentes") or ()
    serie = []
    for candle in bruto:
        if not isinstance(candle, dict):
            return None
        alta = _numero(candle.get("Maximo"))
        baixa = _numero(candle.get("Minimo"))
        if alta is None or baixa is None or alta < baixa:
            return None
        serie.append((alta, baixa))
    return serie


def _ruido(serie, fim, lado):
    """Média das penetrações adversas estritamente positivas em serie[fim-PERIODO+1 : fim]."""
    inicio = fim - PERIODO + 1
    if inicio < 1:
        return None
    positivas = []
    for i in range(inicio, fim + 1):
        if lado == "COMPRA":
            penetracao = serie[i - 1][1] - serie[i][1]
        else:
            penetracao = serie[i][0] - serie[i - 1][0]
        if penetracao > 0:
            positivas.append(penetracao)
    if not positivas:
        return None
    return sum(positivas) / len(positivas)


def _stop_da_barra(serie, i, lado):
    ruido = _ruido(serie, i, lado)
    if ruido is None:
        return None
    if lado == "COMPRA":
        return serie[i][1] - MULTIPLICADOR * ruido
    return serie[i][0] + MULTIPLICADOR * ruido


def _stop_travado(serie, indice_entrada, indice_atual, lado, entrada):
    melhor = None
    for i in range(indice_entrada, indice_atual + 1):
        candidato = _stop_da_barra(serie, i, lado)
        if candidato is None:
            continue
        if lado == "COMPRA" and candidato >= entrada:
            continue
        if lado == "VENDA" and candidato <= entrada:
            continue
        if melhor is None:
            melhor = candidato
        elif lado == "COMPRA":
            melhor = max(melhor, candidato)
        else:
            melhor = min(melhor, candidato)
    return melhor


def avaliar_saida(row: dict, posicao: dict) -> dict:
    if not isinstance(row, dict) or not isinstance(posicao, dict):
        raise TypeError("row e posicao precisam ser dicionários.")
    lado = str(posicao.get("lado", "")).upper()
    if lado not in ("COMPRA", "VENDA"):
        raise ValueError(f"Lado inválido: {lado}")
    entrada = _numero(posicao.get("entrada"))
    if entrada is None:
        raise ValueError("Entrada inválida.")
    decorridos = posicao.get("candles_decorridos", 0)
    try:
        decorridos = int(decorridos)
    except (TypeError, ValueError):
        raise ValueError("candles_decorridos inválido.")
    if decorridos < 0:
        raise ValueError("candles_decorridos inválido.")

    serie = _serie(row)
    if not serie:
        raise ValueError("Histórico insuficiente para o SafeZone.")
    indice_atual = len(serie) - 1
    indice_entrada = indice_atual - decorridos
    if indice_entrada < 0:
        indice_entrada = 0

    stop = _stop_travado(serie, indice_entrada, indice_atual, lado, entrada)
    if decorridos == 0:
        if stop is None:
            raise ValueError("SafeZone sem penetração adversa: stop inicial indefinido.")
        return {"fechar": False, "novo_stop": stop, "novo_alvo": None}
    return {"fechar": False, "novo_stop": stop, "novo_alvo": None}


def diagnosticar_saida(row, posicao):
    return None


__all__ = ["CONTRATO_SAIDA", "NOME", "avaliar_saida", "diagnosticar_saida"]

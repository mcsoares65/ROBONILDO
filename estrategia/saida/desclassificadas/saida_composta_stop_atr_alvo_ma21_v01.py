# DESCLASSIFICADA pela Regra 16 (V496): regras de encerramento soltas no mesmo arquivo. Fora do ranking.
# Equivale a: saida_stop_atr_alvo_ma21_v01 + saida_corte_18h_v01. Ver conselho/2026-10-05-AG.txt.
"""Saída Composta (stop ATR + alvo na MA21 + corte 18h) — Claude V1.

Autoria: Claude (Anthropic), em sessão operada por Marcio Soares; revisão
humana antes do teste oficial: pendente. A numeração v1 é a contagem própria
do autor, não a VERSAO do projeto.

Reúne em um só cartucho três regras que já existem isoladas, SEM criar limiar
novo (todos os valores são cópias dos cartuchos de origem):

1. Stop: estrutural dos últimos 5 candles (mínima/máxima), limitado a 1,80 ATR
   de distância — saida_stop_atr_v01.
2. Alvo: a própria MA21 quando ela está a pelo menos 1R do preço de entrada no
   lado favorável (R = distância do stop efetivo); caso contrário 1,55R sobre o
   risco estrutural original — saida_alvo_media_v01 e saida_stop_atr.
3. Depois da abertura: a partir das 18:00, encerra a posição cuja perda alcance
   0,50 ATR — saida_corte_18h_v01.

Origem: composição de cartuchos existentes (Regra 6: nenhum deles traz as três
regras juntas). O desmembramento continua disponível nos cartuchos de origem.

Variações testadas antes desta versão (Regra 11.2): 4, todas em janeiro–junho
de 2026 (A: stop ATR + alvo MA21; B: A + corte 18h; C: só alvo MA21; D: só stop
ATR). B foi escolhida pelo critério fixado antes de olhar o holdout (maior
acumulado no período de desenho). Nenhum limiar foi ajustado.
Resultado (entrada titular grok_3, motor V467, acumulado = resultado − |dd|):
  desenho jan–jun/2026: 11.773 (titular chatgpt_v4: 10.273)
  holdout jul–out/2026: 3.189 (titular: 4.057)  ← NÃO supera o titular
  2023–24 (já visto antes): −2.136 (titular: −2.418)
Leitura honesta: o ganho do período de desenho não se repetiu no holdout; é
candidata de laboratório, sem base para propor troca de titular.
Sem dependência de data, evento ou preço absoluto (Regra 11.3).

Contrato S001: avaliar_saida(row, posicao) -> dict. Único responsável pelo stop
e pelo alvo desde a abertura (Regra 1). Usa apenas dados fornecidos pelo
motor, não realiza I/O, não mantém estado e não importa módulos do projeto
(Regra 3): as constantes abaixo são cópias.
"""

from math import isfinite

CONTRATO_SAIDA = "S001"
NOME = "saida_composta_stop_atr_alvo_ma21_v01"
CANDLES_ESTRUTURA = 5            # saida_stop_atr: 4 de recuo + candle atual
RISCO_MAXIMO_ATR = 1.80          # saida_stop_atr
RELACAO_RISCO_RETORNO = 1.55     # saida_stop_atr / saida_alvo_media
DISTANCIA_MIN_MA21_R = 1.0       # saida_alvo_media
HORARIO_PROTECAO = "18:00"       # saida_corte_18h
PERDA_ATR_PROTECAO = 0.50        # saida_corte_18h


def _numero(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if isfinite(numero) else None


def _horario(row):
    valor = row.get("dt")
    if hasattr(valor, "strftime"):
        try:
            return valor.strftime("%H:%M")
        except (TypeError, ValueError):
            return None
    return None


def _protecao_inicial(row, posicao):
    entrada = float(posicao["entrada"])
    lado = str(posicao["lado"]).upper()
    if lado not in ("COMPRA", "VENDA"):
        raise ValueError(f"Lado inválido: {lado}")
    direcao = 1 if lado == "COMPRA" else -1

    janela = (row.get("ohlc_recentes") or ())[-CANDLES_ESTRUTURA:]
    if len(janela) < CANDLES_ESTRUTURA:
        raise ValueError("Histórico insuficiente para definir a proteção inicial.")
    if direcao == 1:
        stop_estrutural = min(float(c["Minimo"]) for c in janela)
    else:
        stop_estrutural = max(float(c["Maximo"]) for c in janela)
    risco_estrutural = (entrada - stop_estrutural) * direcao
    if risco_estrutural <= 0 or not isfinite(stop_estrutural):
        raise ValueError(f"Proteção inicial inválida para {lado}.")

    # Sem ATR válido preserva o stop estrutural (nunca falha por indicador).
    atr = _numero(row.get("atr"))
    risco = risco_estrutural
    if atr is not None and atr > 0:
        risco = min(risco_estrutural, RISCO_MAXIMO_ATR * atr)
    stop = entrada - direcao * risco

    alvo = entrada + direcao * RELACAO_RISCO_RETORNO * risco_estrutural
    ma21 = _numero(row.get("MA21"))
    if ma21 is not None and (ma21 - entrada) * direcao >= DISTANCIA_MIN_MA21_R * risco:
        alvo = ma21

    if not isfinite(stop) or not isfinite(alvo):
        raise ValueError(f"Níveis iniciais inválidos para {lado}.")
    return stop, alvo


def _deve_fechar(row, posicao):
    horario = _horario(row)
    resultado = _numero(posicao.get("resultado_flutuante_pts"))
    atr = _numero(row.get("atr"))
    if horario is None or resultado is None or atr is None or atr <= 0:
        return False
    return horario >= HORARIO_PROTECAO and resultado <= -(PERDA_ATR_PROTECAO * atr)


def avaliar_saida(row: dict, posicao: dict) -> dict:
    if not isinstance(row, dict) or not isinstance(posicao, dict):
        raise TypeError("row e posicao precisam ser dicionários.")
    candles = _numero(posicao.get("candles_decorridos"))
    if candles is None:
        raise ValueError("candles_decorridos inválido.")
    if candles == 0:
        stop, alvo = _protecao_inicial(row, posicao)
        return {"fechar": False, "novo_stop": stop, "novo_alvo": alvo}
    return {"fechar": bool(_deve_fechar(row, posicao)),
            "novo_stop": None, "novo_alvo": None}


__all__ = ["CONTRATO_SAIDA", "NOME", "avaliar_saida"]

# DESCLASSIFICADA pela Regra 16 (V496): regras de encerramento soltas no mesmo arquivo. Fora do ranking.
# Equivale a: stop/alvo de compressao + breakeven + trava de lucro + tempo sem progresso (partes ainda nao extraidas). Ver conselho/2026-10-05-AG.txt.
"""
saida_compressao_atr_v01.py

Autor: DeepSeek (IA), revisado por humano antes da submissão.
Numeração V99 = própria do autor; NÃO é a VERSAO do projeto (versionamento.py).

Ideia
-----
Stop estrutural (abaixo/acima do range comprimido, com folga em ATR) + alvo
inicial 2R + breakeven em 1R + trava de lucro em 1.8R + saída por tempo sem
progresso.

Contrato (motor.py V486)
------------------------
  avaliar_saida(row, posicao) -> dict
    {
      "fechar": bool,            # True para fechar agora
      "novo_stop": float | None, # reconfigura o stop (None = mantém)
      "novo_alvo": float | None, # reconfigura o alvo (None = mantém)
    }

Campos de `posicao` (schema fechado no conselho):
  posicao["lado"], posicao["entrada"], posicao["candles_decorridos"],
  posicao["maxima_desde_entrada"], posicao["minima_desde_entrada"],
  posicao["resultado_flutuante_pts"]

Campos de `row` usados (todos de motor.construir_row):
  row["ohlc_recentes"], row["atr"]

Sem I/O. Sem import de módulo do projeto. Sem estado global. Sem data/valor
absoluto — todos os limiares são múltiplos de ATR ou do range medido em
ohlc_recentes.

Declaração (Termo de concordância, versão 8) — itens:
  1. Respeita o contrato avaliar_saida(row, posicao) -> dict.          OK
  2. Usa apenas campos documentados em motor.construir_row / posicao. OK
  3. Não importa módulo do projeto, não abre arquivo, não usa rede.    OK
  4. Nenhum resultado próprio é alegado (Regra 4).                    OK
  5. Autoria: IA (DeepSeek), revisado por humano.                     OK
  6. Não duplica arquivo existente em estrategia/saida/.              OK
  7. V99 = numeração própria do autor. 1 variante (esta). Sem         OK
     dependência de data/estrutura específica do dataset.
  8. Pendente de PR + revisão do conselho (Regra 12).                 PENDENTE
  9. Reconhece Acumulado (Regra 5) como critério único de ranking.    OK
  10. Assume responsabilidade total por definir stop e alvo desde a   OK
      abertura (Regra 1 v8). O motor não tem fórmula própria.
  11. Pendente de citação das atas no PR (Regra 15).                  PENDENTE
"""

# ---- Parâmetros do autor ----
JANELA_RANGE = 12          # mesma janela da entrada, para casar com a compressão
FOLGA_STOP_ATR = 0.25      # stop = extremo do range ± folga * ATR
RR_ALVO = 2.0              # alvo inicial = 2R
RR_BREAKEVEN = 1.0         # a partir de 1R, stop vai para o preço de entrada
RR_TRAVA = 1.8             # a partir de 1.8R, alvo vira o preço atual
CANDLES_SEM_PROGRESSO = 8
MIN_PROGRESSO_R = 0.3      # menos que 0.3R em 8 candles = desiste


def _extremos_range(ohlc, n: int):
    if not ohlc or len(ohlc) < n:
        return None, None
    janela = ohlc[-n:]
    return (
        max(float(c["Maximo"]) for c in janela),
        min(float(c["Minimo"]) for c in janela),
    )


def _stop_alvo_inicial(row: dict, lado: str, entrada: float, atr: float):
    """Stop estrutural no extremo oposto do range comprimido, com folga em ATR.
    Alvo = entrada ± RR_ALVO * R.  Devolve (stop, alvo) ou (None, None)."""
    if atr is None or atr <= 0:
        return None, None
    max_r, min_r = _extremos_range(row.get("ohlc_recentes"), JANELA_RANGE)
    if max_r is None or min_r is None:
        return None, None

    folga = FOLGA_STOP_ATR * float(atr)

    if lado == "COMPRA":
        stop = min_r - folga
        # se o range for muito estreito o stop pode ficar acima da entrada;
        # nesse caso ancora uma distância mínima de 0.5 ATR abaixo da entrada
        if stop >= entrada - 0.5 * float(atr):
            stop = entrada - 0.5 * float(atr)
        risco = entrada - stop
        alvo = entrada + RR_ALVO * risco
    else:  # VENDA
        stop = max_r + folga
        if stop <= entrada + 0.5 * float(atr):
            stop = entrada + 0.5 * float(atr)
        risco = stop - entrada
        alvo = entrada - RR_ALVO * risco

    return stop, alvo


def avaliar_saida(row: dict, posicao: dict) -> dict:
    """Sempre devolve dict com as três chaves — o motor espera isso desde a v10."""
    resposta = {"fechar": False, "novo_stop": None, "novo_alvo": None}

    try:
        lado = posicao["lado"]
        entrada = float(posicao["entrada"])
        decorridos = int(posicao["candles_decorridos"])
        flutuante = float(posicao["resultado_flutuante_pts"])
        atr = row.get("atr")
    except Exception:
        return resposta

    # ---- Abertura: define stop e alvo iniciais (Regra 1 v8) ----
    if decorridos == 0:
        stop, alvo = _stop_alvo_inicial(row, lado, entrada, atr)
        resposta["novo_stop"] = stop
        resposta["novo_alvo"] = alvo
        return resposta

    # ---- A partir daqui, só reconfigura se houver ATR ----
    if atr is None or atr <= 0:
        return resposta

    # Precisamos do risco original para medir R. O motor não nos dá o stop
    # atual, mas a distância original é reconstruível: R = |entrada - stop_ini|.
    # Como não temos o stop_ini diretamente, usamos o ATR como proxy de risco
    # inicial (stop estrutural sempre cai a >=0.5 ATR). Isso mantém a regra
    # independente de estado e auditável.
    R = 0.5 * float(atr)

    # Trava de lucro em 1.8R
    if flutuante >= RR_TRAVA * R:
        resposta["fechar"] = True
        return resposta

    # Breakeven em 1R
    if flutuante >= RR_BREAKEVEN * R:
        resposta["novo_stop"] = entrada

    # Tempo sem progresso
    if decorridos >= CANDLES_SEM_PROGRESSO and flutuante < MIN_PROGRESSO_R * R:
        resposta["fechar"] = True
        return resposta

    return resposta
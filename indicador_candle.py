# indicador_candle.py

import sys
import pandas as pd
from indicador_medias import PERIODOS, COL_W
import indicador_estocastico as ies

# ---------------------------------------------------------
# Altura do painel de Candles (em linhas):
# 1 linha (título+header) + 1 linha (separador) +
# 1 linha (RANGE) + 1 linha (separador) = 4 linhas
CANDLE_PANEL_HEIGHT = 4

def draw_layout_candle():
    """
    Desenha layout estático do painel de Candle (Tamanho de Candle),
    IMEDIATAMENTE abaixo de ESTOCASTICO LENTO, sem invadir o quadro.
    """
    # O Estocástico (MEDIA_PANEL_HEIGHT = 7) ocupa as linhas 7..12 (título, sep, media8, media3, tendencia, sep).
    # Portanto, base_estoc = 7 + 5 = 12 (a última linha usada pelo Estocástico é a 12).
    base_estoc = ies.MEDIA_PANEL_HEIGHT + 5  # 7 + 5 = 12

    # Agora, para não “colar” em cima do separador, deslocamos +1:
    start_line = base_estoc + 1  # 12 + 1 = 13

    # 1) Título + Cabeçalho na MESMA LINHA (linha 13):
    parte_tf   = "|".join(f"{label.strip():^{COL_W}}" for label in PERIODOS.keys()) + "|"
    line_title = f"{'TAMANHO CANDLE'.ljust(COL_W)}|{parte_tf}"
    sys.stdout.write(f"\x1b[{start_line};0H{line_title}")

    # 2) Separador logo abaixo (linha 14):
    sep = "-" * len(line_title)
    sys.stdout.write(f"\x1b[{start_line+1};0H{sep}")

    # 3) Linha “RANGE” (linha 15):
    row_range = start_line + 2
    sys.stdout.write(
        f"\x1b[{row_range};0H"
        f"{'RANGE'.ljust(COL_W)}|"
        + "|".join("".center(COL_W) for _ in PERIODOS)
        + "|"
    )

    # 4) Separador final do painel de Candle (linha 16):
    sys.stdout.write(f"\x1b[{start_line+3};0H{sep}")
    sys.stdout.flush()


def draw_values_candle(df):
    """
    Atualiza valores de Range (High-Low) para cada timeframe,
    imediatamente abaixo do título “TAMANHO CANDLE”, sem invadir o Estocástico.
    """
    if df is None or df.empty:
        return

    dt_max = pd.to_datetime(df['DataHora'].iat[-1])
    serie  = df.set_index('DataHora')['Último']

    # Mesma lógica de posicionamento usada em draw_layout_candle():
    base_estoc  = ies.MEDIA_PANEL_HEIGHT + 5  # 12
    start_line  = base_estoc + 1              # 13 (onde imprimimos “TAMANHO CANDLE”)
    row         = start_line + 2              # 15 (onde imprimimos o valor RANGE)

    for idx, (label, rule) in enumerate(PERIODOS.items()):
        barras = serie.resample(rule, closed='right', label='right').ohlc()

        barras['open']  = barras['open'].ffill()
        barras['high']  = barras['high'].ffill().combine(barras['high'], max)
        barras['low']   = barras['low'].ffill().combine(barras['low'], min)
        barras['close'] = barras['close'].ffill()

        last_idx = dt_max.floor(rule)
        if last_idx in barras.index:
            barras.at[last_idx, 'high']  = max(barras.at[last_idx, 'high'], df['Último'].iat[-1])
            barras.at[last_idx, 'low']   = min(barras.at[last_idx, 'low'],  df['Último'].iat[-1])
            barras.at[last_idx, 'close'] = df['Último'].iat[-1]
            range_val = barras.at[last_idx, 'high'] - barras.at[last_idx, 'low']
        else:
            range_val = 0.0

        col = COL_W + 2 + idx * (COL_W + 1)
        sys.stdout.write(f"\x1b[{row};{col}H{range_val:^{COL_W}.2f}")

    sys.stdout.flush()

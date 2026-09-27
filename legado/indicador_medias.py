# indicador_medias.py

import sys
from datetime import datetime

import pandas as pd
import xlwings as xw

# ————— CONFIGURAÇÕES ——————————————————————————————————————————————
EMA_21 = 21
EMA_50 = 50

# largura de cada coluna (em caracteres)
COL_W = 17

# dicionário de timeframes → regra de resample
PERIODOS = {
    '   1M   ': '1min',
    '   5M   ': '5min',
    '  15M   ': '15min',
    '  30M   ': '30min',
    '  60M   ': '60min',
}

# ANSI colors para tendência
GREEN      = '\033[32m'
RED        = '\033[31m'
YELLOW     = '\033[33m'
RESET      = '\033[0m'
# ————————————————————————————————————————————————————————————————————————

def draw_layout():
    """
    Desenha o layout estático de Médias Móveis,
    com TÍTULO e TIMEFRAMES na MESMA linha, sem linhas em branco acima.
    """
    parte_tf   = "|".join(f"{tf.strip():^{COL_W}}" for tf in PERIODOS) + "|"
    line_title = f"{'MEDIAS MOVEIS'.ljust(COL_W)}|{parte_tf}"
    print(line_title)

    sep = "-" * len(line_title)
    print(sep)

    print("MEDIA 21".ljust(COL_W) + "|" + "|".join("".center(COL_W) for _ in PERIODOS) + "|")
    print("MEDIA 50".ljust(COL_W) + "|" + "|".join("".center(COL_W) for _ in PERIODOS) + "|")
    print("TENDENCIA".ljust(COL_W) + "|" + "|".join("".center(COL_W) for _ in PERIODOS) + "|")

    print(sep)


def draw_values(df: pd.DataFrame):
    """
    Atualiza apenas os valores de EMA21, EMA50 e Tendência
    sobre a base que 'draw_layout()' construiu.
    """
    resultados = [calcula_ema(df, rule) for rule in PERIODOS.values()]
    e21s = [(r[0] or 0) for r in resultados]
    e50s = [(r[1] or 0) for r in resultados]

    # As linhas fixas estão em row21=3, row50=4, rowT=5
    row21, row50, rowT = 3, 4, 5

    for i, (e21, e50) in enumerate(zip(e21s, e50s)):
        col_start = COL_W + 2 + i * (COL_W + 1)
        sys.stdout.write(f"\x1b[{row21};{col_start}H{e21:^{COL_W}.0f}")
        sys.stdout.write(f"\x1b[{row50};{col_start}H{e50:^{COL_W}.0f}")
        diff = abs(e21 - e50)
        if diff < 10:
            trend = "LATERAL"
            color = YELLOW
        else:
            if e21 > e50:
                trend = "ALTA"
                color = GREEN
            else:
                trend = "BAIXA"
                color = RED
        sys.stdout.write(f"\x1b[{rowT};{col_start}H{color}{trend:^{COL_W}}{RESET}")
    sys.stdout.flush()


def calcula_ema(df: pd.DataFrame, rule: str):
    """
    Retorna (EMA21, EMA50, count) após resample
    """
    s = df.set_index('DataHora')['Último'].resample(rule).last().dropna()
    if s.empty:
        return None, None, 0
    return (
        float(s.ewm(span=EMA_21, adjust=False).mean().iloc[-1]),
        float(s.ewm(span=EMA_50, adjust=False).mean().iloc[-1]),
        len(s)
    )

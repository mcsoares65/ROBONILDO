# estocastico_lento.py

import sys
import pandas as pd
import unicodedata
from indicador_medias import COL_W, PERIODOS
import colorama
from colorama import Fore, Style

# parâmetros do estocástico
STO_LEN = 8
D_LEN   = 3
RULES   = {tf.strip().upper(): rule for tf, rule in PERIODOS.items()}
TFS     = list(RULES.keys())

colorama.init(autoreset=True)


def normalize_header(name: str) -> str:
    if not isinstance(name, str):
        return ''
    s = unicodedata.normalize('NFD', name.strip().upper())
    return ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')


def color_trend(trend: str) -> str:
    t = trend.strip().upper().center(COL_W)
    if t.strip() == 'ALTA':
        return Fore.GREEN + t + Style.RESET_ALL
    if t.strip() == 'BAIXA':
        return Fore.RED + t + Style.RESET_ALL
    if t.strip() == 'SOBRECOMPRADO':
        return Fore.GREEN + t + Style.RESET_ALL
    if t.strip() == 'SOBREVENDIDO':
        return Fore.RED + t + Style.RESET_ALL
    if t.strip() in ('LATERAL', 'AGUARDA'):
        return Fore.YELLOW + t + Style.RESET_ALL
    return t


def draw_layout(start_row: int = 1):
    """
    Desenha a estrutura estática do painel ESTOCASTICO LENTO,
    com colunas para cada timeframe em TFS.
    """
    # cabeçalho de timeframes
    hdr    = '|' + '|'.join(f"{tf:^{COL_W}}" for tf in TFS) + '|'
    title1 = f"{'ESTOCASTICO LENTO'.ljust(COL_W)}{hdr}"
    sep1   = '-' * len(title1)
    sys.stdout.write(f"\x1b[{start_row};0H{title1}")
    sys.stdout.write(f"\x1b[{start_row+1};0H{sep1}")

    # linhas de labels
    for i, lbl in enumerate(('MEDIA 8','MEDIA 3','TENDENCIA'), start=2):
        row   = start_row + i
        sys.stdout.write(f"\x1b[{row};0H{lbl.ljust(COL_W)}")
        for _ in TFS:
            sys.stdout.write(f"|{'':^{COL_W}}")
        sys.stdout.write("|")
    # separador final
    sys.stdout.write(f"\x1b[{start_row+5};0H{sep1}")


def draw_values(df: pd.DataFrame, start_row: int = 1):
    """
    Calcula e escreve os valores de MEDIA 8, MEDIA 3 e TENDENCIA
    abaixo da estrutura estática já desenhada por draw_layout.
    """
    last_dt = pd.to_datetime(df['DataHora'].iat[-1])
    last_pr = df['Último'].iat[-1]
    serie   = df.set_index('DataHora')['Último']

    # cálculo para cada timeframe
    for idx, tf in enumerate(TFS):
        bars = (
            serie
            .resample(RULES[tf], closed='right', label='right')
            .ohlc()
            .ffill()
        )
        ts = last_dt.floor(RULES[tf])
        if ts in bars.index:
            bars.at[ts,'high']  = max(bars.at[ts,'high'], last_pr)
            bars.at[ts,'low']   = min(bars.at[ts,'low'],  last_pr)
            bars.at[ts,'close'] = last_pr

        if len(bars) >= STO_LEN:
            hr    = bars['high'].rolling(STO_LEN).max()
            lr    = bars['low'].rolling(STO_LEN).min()
            fk    = 100 * (bars['close'] - lr) / (hr - lr)
            sk    = fk.ewm(span=D_LEN).mean()
            sd    = sk.ewm(span=D_LEN).mean()
            k_val = sk.iat[-1]
            d_val = sd.iat[-1]
        else:
            k_val, d_val = 0.0, 0.0

        # Tendência
        if abs(k_val - d_val) < 1:
            trend = 'LATERAL'
        elif k_val > 80:
            trend = 'SOBRECOMPRADO'
        elif k_val < 20:
            trend = 'SOBREVENDIDO'
        else:
            trend = 'ALTA' if k_val > d_val else 'BAIXA'

        # posicionamento no terminal
        col = COL_W + 1 + idx * (COL_W + 1)

        # MEDIA 8
        sys.stdout.write(f"\x1b[{start_row+2};{col}H{k_val:^{COL_W}.2f}")
        # MEDIA 3
        sys.stdout.write(f"\x1b[{start_row+3};{col}H{d_val:^{COL_W}.2f}")
        # TENDÊNCIA (com cor)
        sys.stdout.write(f"\x1b[{start_row+4};{col}H{color_trend(trend)}")

    sys.stdout.flush()

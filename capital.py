# capital.py

import sys
import colorama
from datetime import datetime

import indicador_estocastico as ies

# --------------------------------------------------
# Parâmetros de gestão de risco
# --------------------------------------------------
BANCA                   = 200      # Saldo inicial em reais
STOP_LOSS_PONTOS        = 150      # Pontos de Stop‐Loss
TAKE_PROFIT_PONTOS      = 50       # Pontos de Take‐Profit
DISTANCIA_TRAILING_STOP = 10       # Distância do Trailing Stop em pontos
# --------------------------------------------------


class CapitalManager:
    """
    Gerencia a posição (long/short), calcula Stop‐Loss, Take‐Profit, Trailing Stop e Breakeven,
    e exibe esses valores em um painel fixo (“CAPITAL”) imediatamente abaixo do Candle.
    """

    def __init__(self):
        # Atributos de posição
        self.entry_price        = None    # preço de entrada
        self.qty                = None    # quantidade (contratos)
        self.position           = None    # 'long' ou 'short'
        self.stop_loss          = None    # valor do SL
        self.take_profit        = None    # valor do TP
        self.trailing_stop      = None    # valor atual do TS
        self.trailing_active    = False   # só “anda” o trailing depois de atingir TP
        self.active             = False
        self.last_exit_minute   = None    # para evitar reentrada no mesmo minuto

    def open_position(self, price: float, qty: int, position: str) -> bool:
        """
        Abre nova posição (long ou short). Se já fechamos no mesmo minuto, bloqueia.
        Define SL, TP e TS (trailing_stop) e marca active=True.
        """
        now_minute = datetime.now().minute
        if self.last_exit_minute == now_minute:
            return False

        self.entry_price     = price
        self.qty             = qty
        self.position        = position
        self.trailing_active = False

        if position == 'long':
            self.stop_loss     = price - STOP_LOSS_PONTOS
            self.take_profit   = price + TAKE_PROFIT_PONTOS
            self.trailing_stop = price - DISTANCIA_TRAILING_STOP
        else:  # 'short'
            self.stop_loss     = price + STOP_LOSS_PONTOS
            self.take_profit   = price - TAKE_PROFIT_PONTOS
            self.trailing_stop = price + DISTANCIA_TRAILING_STOP

        self.active = True
        return True

    def close_position(self):
        """
        Fecha a posição ativa (caso exista), reseta todos os parâmetros e registra o minuto de saída.
        """
        if not self.active:
            return

        self.last_exit_minute = datetime.now().minute
        self.active          = False
        self.entry_price     = None
        self.qty             = None
        self.position        = None
        self.stop_loss       = None
        self.take_profit     = None
        self.trailing_stop   = None
        self.trailing_active = False


    def draw_layout(self):
        """
        Desenha a grade fixa de CAPITAL (SALDO / STOP LOSS / TAKE PROFIT / TRAILING STOP / BREAKEVEN)
        imediatamente abaixo do painel de Candle, sem invadir o separador final do Candle.
        """

        # 1) Calcular qual é a linha inicial (em números ANSI) para o painel de Capital:
        #
        #    Em indicador_estocastico.py, MEDIA_PANEL_HEIGHT = 7 → O estocástico ocupa
        #    as linhas 1..(7+5) = 1..12 (contando cabeçalho, separador e 3 linhas de valor).
        #    Em indicador_candle.py, CANDLE_PANEL_HEIGHT = 4 → o Candle usa as 4 linhas seguintes: 13..16
        #    (13=título, 14=linha de traços, 15=“RANGE ...”, 16=linha de traços).
        #    Portanto, a linha do título “CAPITAL” deve ficar na 17.
        #
        from indicador_candle import CANDLE_PANEL_HEIGHT
        base_estoc   = ies.MEDIA_PANEL_HEIGHT + 5        # 7 + 5 = 12 (última linha do estocástico)
        base_candle  = base_estoc + CANDLE_PANEL_HEIGHT  # 12 + 4 = 16
        LINE_START   = base_candle + 1                   # 17

        # 2) Limpa as 9 linhas reservadas para o painel de Capital (LINHA 17 até 25):
        for offset in range(0, 9):
            sys.stdout.write(f"\x1b[{LINE_START + offset};0H\x1b[2K")

        # 3) Monta a linha de título “CAPITAL” + cabeçalhos de períodos (1M, 5M, 15M, 30M, 60M)
        parte_tf   = "|".join(f"{tf.strip():^{ies.COL_W}}" for tf in ies.PERIODOS) + "|"
        line_title = f"{'CAPITAL'.ljust(ies.COL_W)}|{parte_tf}"
        sys.stdout.write(f"\x1b[{LINE_START};0H{line_title}")

        # 4) Logo abaixo, desenha o separador (traços) com o mesmo comprimento de line_title
        sep = "-" * len(line_title)
        sys.stdout.write(f"\x1b[{LINE_START+1};0H{sep}")

        # 5) As cinco linhas fixas de labels:
        #    SALDO (linha 18), STOP LOSS (19), TAKE PROFIT (20), TRAILING STOP (21), BREAKEVEN (22)
        labels = ['SALDO', 'STOP LOSS', 'TAKE PROFIT', 'TRAILING STOP', 'BREAKEVEN']
        for i, lbl in enumerate(labels, start=2):
            row  = LINE_START + i
            # Cada “linha de label” tem: nome (COL_W colunas) + "|" + um campo vazio por período + "|"
            linha = lbl.ljust(ies.COL_W) + "|" + "|".join("".center(ies.COL_W) for _ in ies.PERIODOS) + "|"
            sys.stdout.write(f"\x1b[{row};0H{linha}")

        # 6) Desenha o separador final do painel de Capital (linha 23 = LINE_START + 7)
        sys.stdout.write(f"\x1b[{LINE_START + len(labels) + 2};0H{sep}")
        sys.stdout.flush()


    def update_display(self, current_price: float):
        """
        Se houver posição ativa, calcula PnL e exibe nos campos do painel de Capital sob cada coluna:
          - SALDO       : PnL atual (colorido: verde se ≥0, vermelho se <0)
          - STOP LOSS    : valor do stop_loss
          - TAKE PROFIT  : valor do take_profit
          - TRAILING STOP: valor do trailing_stop (ou “—” se não ativo)
          - BREAKEVEN    : preço de entrada
        O cursor será reposicionado de forma a não quebrar o cabeçalho nem as linhas fixas.
        """

        if not self.active:
            return

        from indicador_candle import CANDLE_PANEL_HEIGHT
        base_estoc   = ies.MEDIA_PANEL_HEIGHT + 5
        base_candle  = base_estoc + CANDLE_PANEL_HEIGHT  # 16
        LINE_START   = base_candle + 1                   # 17

        # 1) Calcula o PnL em pontos (positivo para long se price > entry_price, etc.)
        pnl = (current_price - self.entry_price) if (self.position == 'long') else (self.entry_price - current_price)
        color = colorama.Fore.GREEN if (pnl >= 0) else colorama.Fore.RED

        # 2) Se ultrapassou TAKE_PROFIT_PONTOS, ativa/ajusta trailing stop
        if pnl >= TAKE_PROFIT_PONTOS:
            if not self.trailing_active:
                self.trailing_active = True

            if self.position == 'long':
                novo_ts = current_price - DISTANCIA_TRAILING_STOP
                if novo_ts > self.trailing_stop:
                    self.trailing_stop = novo_ts
            else:
                novo_ts = current_price + DISTANCIA_TRAILING_STOP
                if novo_ts < self.trailing_stop:
                    self.trailing_stop = novo_ts

        # 3) A “coluna” certa para cada valor é sempre a primeira coluna após COL_W + 1 caractere de '|'
        #    Ou seja, a posição horizontal (em caracteres) de cada valor sob “1M”:
        col = ies.COL_W + 2

        # 4) SALDO (linha LINE_START + 1 = 18):
        sys.stdout.write(f"\x1b[{LINE_START+1};{col}H{color}{pnl:+.2f}{colorama.Style.RESET_ALL}")

        # 5) STOP LOSS (linha 19):
        sys.stdout.write(f"\x1b[{LINE_START+2};{col}H{self.stop_loss:+.2f}")

        # 6) TAKE PROFIT (linha 20):
        sys.stdout.write(f"\x1b[{LINE_START+3};{col}H{self.take_profit:+.2f}")

        # 7) TRAILING STOP (linha 21):
        if self.trailing_active:
            sys.stdout.write(f"\x1b[{LINE_START+4};{col}H{self.trailing_stop:+.2f}")
        else:
            # Se não ativo, exibe “—” centralizado em COL_W
            ts_vazio = "—".center(ies.COL_W)
            sys.stdout.write(f"\x1b[{LINE_START+4};{col}H{ts_vazio}")

        # 8) BREAKEVEN (linha 22):
        sys.stdout.write(f"\x1b[{LINE_START+5};{col}H{self.entry_price:+.2f}")

        sys.stdout.flush()


    def update(self, current_price: float) -> str:
        """
        Chama a cada tick; retorna:
          - 'close_stop_loss'      se o price atingir/extrapolar stop_loss
          - 'close_trailing_stop'  se trailing estiver ativo e price recuar ao trailing_stop
          - 'close_take_profit'    se o price atingir/extrapolar take_profit (antes de trailing)
          - None                   caso contrário
        """
        if not self.active:
            return None

        # 1) Stop‐Loss: fecha imediatamente
        if (self.position == 'long'  and current_price <= self.stop_loss) or \
           (self.position == 'short' and current_price >= self.stop_loss):
            return 'close_stop_loss'

        # 2) PnL em pontos
        pnl = (current_price - self.entry_price) if (self.position == 'long') else (self.entry_price - current_price)

        # 3) Se ultrapassar TAKE_PROFIT, ativa/ajusta trailing_stop
        if pnl >= TAKE_PROFIT_PONTOS:
            if not self.trailing_active:
                self.trailing_active = True
            if self.position == 'long':
                novo_ts = current_price - DISTANCIA_TRAILING_STOP
                if novo_ts > self.trailing_stop:
                    self.trailing_stop = novo_ts
            else:
                novo_ts = current_price + DISTANCIA_TRAILING_STOP
                if novo_ts < self.trailing_stop:
                    self.trailing_stop = novo_ts

        # 4) Se trailing ativo e price recuou até trailing_stop → fecha
        if self.trailing_active:
            if (self.position == 'long'  and current_price <= self.trailing_stop) or \
               (self.position == 'short' and current_price >= self.trailing_stop):
                return 'close_trailing_stop'

        # 5) Se ainda não ativei trailing, mas price já extrapolou take_profit → fecha
        if pnl >= TAKE_PROFIT_PONTOS and not self.trailing_active:
            return 'close_take_profit'

        return None

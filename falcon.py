#!/usr/bin/env python3
import os
import time
import pandas as pd
import config
from datetime import datetime

from calibrador import obter_intraday
from config import FALCAO_EXCEL_PATH

# Estocástico Lento
from estocastico_lento import (
    draw_layout    as draw_stoch_layout,
    draw_values    as draw_stoch_values,
    STO_LEN, D_LEN, PERIODOS
)

# Painel Falcão
from falcao_panel import (
    draw_layout         as draw_falc_layout,
    draw_values         as draw_falc_values,
    load_scenarios,
    find_matching_scenario
)

# Plano de Trade
from planotrade import load_trade_plan, draw_panel as draw_plan_panel

# Gestor de Operações
from gestor_trade import init_gestor, update_trade_state, draw_operacao

# Linha onde começamos a desenhar os painéis
START_ROW = 2
SLEEP     = 0.2

# Histórico de execução
history_file = None

def init_history():
    """
    Inicializa o arquivo de histórico na pasta PASTA_HISTORICO definida em config.ini.
    """
    global history_file
    pasta = getattr(config, 'PASTA_HISTORICO', None) or config._cfg.get('PASTAS', 'PASTA_HISTORICO')
    os.makedirs(pasta, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    caminho = os.path.join(pasta, f"historico_{ts}.txt")
    history_file = open(caminho, 'w', encoding='utf-8')


def log_history(linha: str):
    """
    Registra uma linha no console e no arquivo de histórico.
    """
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    texto = f"[{ts}] {linha}"
    print(texto)
    if history_file:
        history_file.write(texto + '\n')
        history_file.flush()


if __name__ == '__main__':
    # inicia histórico antes de qualquer outra coisa
    init_history()
    log_history('Iniciando Falcon')

    # limpa e exibe título (caminho da planilha)
    os.system('cls' if os.name == 'nt' else 'clear')
    print(FALCAO_EXCEL_PATH)

    # desenha as grades estáticas
    draw_stoch_layout(start_row=START_ROW)
    draw_falc_layout(start_row=START_ROW)

    # carrega e desenha o Plano de Trade
    plan = load_trade_plan(FALCAO_EXCEL_PATH)
    draw_plan_panel(plan, start_row=START_ROW + 17)

    # inicializa gestor de trades com stops/metas
    init_gestor(FALCAO_EXCEL_PATH)
    log_history('Gestor inicializado com plano de trade')

    try:
        # loop principal
        while True:
            df = None
            try:
                df = obter_intraday()
            except IndexError:
                log_history('Aguardando dados iniciais do intraday')
                time.sleep(SLEEP)
                continue

            if df is None or df.empty:
                time.sleep(SLEEP)
                continue

            # 1) atualiza Estocástico Lento
            draw_stoch_values(df, start_row=START_ROW)

            # 2) atualiza Painel Falcão (coluna Cenário Atual)
            draw_falc_values(df, FALCAO_EXCEL_PATH, start_row=START_ROW)

            # 3) recomputa tendências para encontrar o cenário
            last_dt = pd.to_datetime(df['DataHora'].iat[-1])
            last_pr = df['Último'].iat[-1]
            serie   = df.set_index('DataHora')['Último']

            trends = {}
            for tf, rule in {tf.strip().upper(): r for tf, r in PERIODOS.items()}.items():
                bars = (
                    serie
                    .resample(rule, closed='right', label='right')
                    .ohlc()
                    .ffill()
                )
                ts = last_dt.floor(rule)
                if ts in bars.index:
                    bars.at[ts,'high']  = max(bars.at[ts,'high'], last_pr)
                    bars.at[ts,'low']   = min(bars.at[ts,'low'],  last_pr)
                    bars.at[ts,'close'] = last_pr
                if len(bars) >= STO_LEN:
                    hr = bars['high'].rolling(STO_LEN).max()
                    lr = bars['low'].rolling(STO_LEN).min()
                    fk = 100 * (bars['close'] - lr) / (hr - lr)
                    sk = fk.ewm(span=D_LEN).mean()
                    sd = sk.ewm(span=D_LEN).mean()
                    trends[tf] = 'LATERAL' if abs(sk.iat[-1] - sd.iat[-1]) < 1 else (
                        'SOBRECOMPRADO' if sk.iat[-1] > 80 else (
                        'SOBREVENDIDO' if sk.iat[-1] < 20 else (
                        'ALTA' if sk.iat[-1] > sd.iat[-1] else 'BAIXA')))
                else:
                    trends[tf] = 'LATERAL'

            sce = find_matching_scenario(load_scenarios(FALCAO_EXCEL_PATH), trends)

            # 4) atualiza o estado de trade
            update_trade_state(sce, last_pr)

            # 5) desenha EM OPERAÇÃO e GESTAO LUCRO
            draw_operacao(start_row=START_ROW)

            time.sleep(SLEEP)

    except KeyboardInterrupt:
        log_history('Execução interrompida pelo usuário (KeyboardInterrupt)')
    finally:
        if history_file:
            history_file.close()
        log_history('Falcon encerrado com segurança')
        sys.exit(0)

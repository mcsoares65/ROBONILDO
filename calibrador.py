#!/usr/bin/env python3
import os
import time
import win32ui              # inicializa MFC para PyWin32
import dde
import pandas as pd
from datetime import datetime
import pygetwindow as gw

from config import (
    NOME_TELA_PROFIT,
    PASTA_HISTORICO,
    ATIVO_PRINCIPAL,
    ATIVO_PRINCIPAL_BASE
)

# —————————————————————————————————————————————————————————————————————————
# Variáveis globais para servidor e conversa DDE e histórico
# —————————————————————————————————————————————————————————————————————————
server       = None
conversation = None
_df_ht       = None
_dt_ant      = None

# Mapeamento de campos DDE → nome legível
CAMPOS_DDE = {
    "Data": "DAT",
    "Hora": "HOR",
    "Último": "ULT",
    "Abertura": "ABE",
    "Máximo": "MAX",
    "Mínimo": "MIN",
    "Fechamento Anterior": "FEC",
    "Variação": "VAR",
    "Negócios": "NEG",
    "Quantidade": "QTT",
    "Volume": "VOL",
    "Of. Compra": "OCP",
    "Of. Venda": "OVD",
}

# —————————————————————————————————————————————————————————————————————————
# Funções de suporte DDE
# —————————————————————————————————————————————————————————————————————————
def verificar_profit_aberto() -> bool:
    """Retorna True se a janela do Profit estiver aberta."""
    return bool(gw.getWindowsWithTitle(NOME_TELA_PROFIT))


def tratar_valor_dde(raw: str) -> float:
    """
    Limpa formatação do Profit e dos nossos CSVs:

      - Se vier com vírgula (formato europeu: “1.234,56”),
        remove pontos de milhar e troca vírgula por ponto.
      - Senão (formato americano: “1234.56”), mantém o ponto decimal.
    """
    if not raw or raw.strip() in ("", "--", "-"):
        return 0.0

    s = raw.strip()

    if ',' in s and s.count(',') >= 1:
        # vírgula indica decimal, pontos são milhares
        clean = s.replace('.', '').replace(',', '.')
    else:
        # sem vírgula: ponto já é decimal
        clean = s

    try:
        return float(clean)
    except ValueError:
        return 0.0


def _conectar_dde() -> bool:
    """
    Inicializa servidor/conversa DDE na primeira chamada.
    Retorna True se conectar com sucesso.
    """
    global server, conversation
    if conversation is None:
        try:
            server = dde.CreateServer()
            server.Create("ProfitPython")
            conversation = dde.CreateConversation(server)
            conversation.ConnectTo("profitchart", "cot")
            return True
        except dde.error as e:
            print(f"[Aviso] DDE indisponível: {e}")
            return False
    return True


def obter_dados_dde(ativo: str) -> dict | None:
    """
    Lê cada campo via DDE para o ativo.
    Retorna dict com valores ou None em caso de erro/Profit fechado.
    """
    # 1) Verifica Profit aberto
    if not verificar_profit_aberto():
        print("[ERRO] Profit não está aberto.")
        return None
    # 2) Tenta conectar DDE
    if not _conectar_dde():
        return None

    tick: dict = {}
    for nome, tag in CAMPOS_DDE.items():
        try:
            raw = conversation.Request(f"{ativo}.{tag}").strip()
            tick[nome] = raw if nome in ("Data", "Hora") else tratar_valor_dde(raw)
        except Exception as e:
            print(f"[ERRO] DDE {ativo} {nome}: {e}")
            tick[nome] = None
    return tick

# —————————————————————————————————————————————————————————————————————————
# Histórico CSV (1-min) — carrega apenas uma vez
# —————————————————————————————————————————————————————————————————————————
def _carrega_historico_csv() -> pd.DataFrame:
    fn = os.path.join(
        PASTA_HISTORICO,
        f"{ATIVO_PRINCIPAL_BASE}_F_0_1min.csv"
    )
    if not os.path.isfile(fn):
        raise FileNotFoundError(f"Histórico não encontrado: {fn}")

    # 1) Lê CSV como strings
    df = pd.read_csv(
        fn,
        sep=";",
        encoding="latin1",
        dtype=str,
        na_filter=False
    )
    # 2) DataHora
    df["DataHora"] = pd.to_datetime(
        df["Data"].str.strip() + ' ' + df["Hora"].str.strip(),
        format="%d/%m/%Y %H:%M:%S",
        dayfirst=True,
        errors="coerce"
    )
    # 3) Normaliza colunas numéricas
    for c in ("Abertura","Máximo","Mínimo","Fechamento","Volume","Quantidade"):
        df[c] = df[c].apply(tratar_valor_dde)
    # 4) Cria Último e ordena
    df["Último"] = df["Fechamento"]
    df = df.sort_values("DataHora").reset_index(drop=True)
    return df

# —————————————————————————————————————————————————————————————————————————
# Função pública usada pelo falcao.py
# —————————————————————————————————————————————————————————————————————————
def obter_intraday() -> pd.DataFrame | None:
    """
    Retorna DataFrame intraday atualizado e persiste histórico:
      - carrega histórico CSV na primeira chamada
      - anexa novo tick se DataHora for maior
      - regrava CSV para manter histórico atualizado
    """
    global _df_ht, _dt_ant
    # 1) Carrega histórico inicial
    if _df_ht is None:
        try:
            _df_ht = _carrega_historico_csv()
        except Exception as e:
            print(f"[ERRO] falha ao carregar histórico CSV: {e}")
            return None

    # 2) Pega tick DDE
    tick = obter_dados_dde(ATIVO_PRINCIPAL)
    if not tick or tick.get("Último") is None:
        return None

    # 3) Converte DataHora do tick
    try:
        dt = datetime.strptime(
            f"{tick['Data']} {tick['Hora']}",
            "%d/%m/%Y %H:%M:%S"
        )
    except Exception:
        return _df_ht.copy()

    # 4) Se em modo replay, reset histórico
    if _dt_ant and dt < _dt_ant:
        _df_ht = _carrega_historico_csv()
    _dt_ant = dt

    # 5) Se é novo tick, anexa e persiste
    if dt > _df_ht["DataHora"].iat[-1]:
        nova = {
            "Ativo":      ATIVO_PRINCIPAL_BASE,
            "DataHora":   dt,
            "Data":       dt.strftime("%d/%m/%Y"),
            "Hora":       dt.strftime("%H:%M:%S"),
            "Abertura":   tick["Abertura"],
            "Máximo":     tick["Máximo"],
            "Mínimo":     tick["Mínimo"],
            "Fechamento": tick["Último"],
            "Volume":     tick["Volume"],
            "Quantidade": tick["Quantidade"],
            "Último":     tick["Último"]
        }
        _df_ht = pd.concat([_df_ht, pd.DataFrame([nova])], ignore_index=True)

        # Persiste de volta no CSV original
        fn = os.path.join(
            PASTA_HISTORICO,
            f"{ATIVO_PRINCIPAL_BASE}_F_0_1min.csv"
        )
        df2 = _df_ht.copy()
        df2["Data"] = df2["DataHora"].dt.strftime("%d/%m/%Y")
        df2["Hora"] = df2["DataHora"].dt.strftime("%H:%M:%S")
        cols = [
            "Ativo","Data","Hora",
            "Abertura","Máximo","Mínimo",
            "Fechamento","Volume","Quantidade"
        ]
        df2.to_csv(
            fn,
            sep=";",
            index=False,
            columns=cols,
            encoding="latin1",
            decimal=",",
            float_format="%.3f"
        )

    # 6) Retorna cópia para evitar efeitos colaterais
    return _df_ht.copy()

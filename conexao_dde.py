# conexao_dde.py

import win32ui              # deve ser importado antes do dde
import dde
import pygetwindow as gw
from config import NOME_TELA_PROFIT, ATIVO_PRINCIPAL, ATIVOS_CORRELACAO

# Variáveis globais para servidor e conversa DDE
server = None
conversation = None

# Mapeia campos DDE → nome legível
_CAMPOS = {
    "Data":                 "DAT",
    "Hora":                 "HOR",
    "Último":               "ULT",
    "Abertura":             "ABE",
    "Máximo":               "MAX",
    "Mínimo":               "MIN",
    "Fechamento Anterior":  "FEC",
    "Variação":             "VAR",
    "Negócios":             "NEG",
    "Quantidade":           "QTT",
    "Volume":               "VOL",
    "Of. Compra":           "OCP",
    "Of. Venda":            "OVD",
}

def _profit_aberto() -> bool:
    """Retorna True se a janela do Profit estiver aberta."""
    return bool(gw.getWindowsWithTitle(NOME_TELA_PROFIT))

def _tratar_valor_dde(valor: str) -> float:
    """Remove formatação do Profit e converte para float."""
    if not valor or valor.strip() in ("", "--", "-"):
        return 0.0
    if "/" in valor:
        valor = valor.split("/")[0].strip()
    return float(valor.replace(".", "").replace(",", "."))

def _conectar_dde() -> bool:
    """
    Inicializa o servidor e conversa DDE na primeira chamada.
    Retorna True se a conexão foi estabelecida com sucesso.
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
    Lê todos os campos em _CAMPOS via DDE para o ativo fornecido.
    Retorna dict com os valores ou None em caso de erro/Profit fechado.
    """
    # 1) Verifica se o Profit está aberto
    if not _profit_aberto():
        print("[ERRO] Profit não está aberto.")
        return None

    # 2) Garante conexão DDE
    if not _conectar_dde():
        return None

    # 3) Solicita cada campo via DDE
    tick: dict = {}
    for nome, tag in _CAMPOS.items():
        try:
            raw = conversation.Request(f"{ativo}.{tag}").strip()
            if nome in ("Data", "Hora"):
                tick[nome] = raw
            else:
                tick[nome] = _tratar_valor_dde(raw)
        except Exception as e:
            print(f"[ERRO] DDE {ativo} {nome}: {e}")
            tick[nome] = None

    return tick

def obter_tick_dde(ativo: str = None) -> dict | None:
    """
    Wrapper para ler apenas o ativo principal por padrão
    ou qualquer outro ativo passado como argumento.
    """
    return obter_dados_dde(ativo or ATIVO_PRINCIPAL)

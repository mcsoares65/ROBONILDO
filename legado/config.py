# config.py

import os
import sys
from configparser import ConfigParser, NoOptionError


def _load_config() -> ConfigParser:
    """
    Carrega o arquivo config.ini:
    1) Procura na mesma pasta do executável/script.
    2) Se não encontrar, tenta dentro de sys._MEIPASS (PyInstaller bundle).
    """
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
    else:
        exe_dir = os.path.dirname(os.path.abspath(__file__))

    ini_path = os.path.join(exe_dir, 'config.ini')
    if not os.path.isfile(ini_path):
        base_dir = getattr(sys, '_MEIPASS', exe_dir)
        ini_path = os.path.join(base_dir, 'config.ini')

    if not os.path.isfile(ini_path):
        raise FileNotFoundError(f"config.ini não encontrado em: {ini_path}")

    cfg = ConfigParser()
    cfg.read(ini_path, encoding='utf-8')
    return cfg

_cfg = _load_config()

# ┌── Seção GERAL ─────────────────────────────────────────────────────────────
NOME_TELA_PROFIT = _cfg.get('GERAL', 'NOME_TELA_PROFIT')
AMBIENTE = _cfg.get('GERAL', 'AMBIENTE').upper()

# Prefixo para modo REPLAY
PREFIXO_REPLAY = '[R] ' if AMBIENTE.startswith('REPLAY') else ''

# ┌── Seção PASTAS ────────────────────────────────────────────────────────────
PASTA_HISTORICO = _cfg.get('PASTAS', 'PASTA_HISTORICO')
PASTA_CENARIO   = _cfg.get('PASTAS', 'PASTA_CENARIO')
PASTA_LOGS      = _cfg.get('PASTAS', 'PASTA_LOGS')

# ┌── Seção TRADE ────────────────────────────────────────────────────────────
ENVIAR_ORDENS = _cfg.getboolean('TRADE', 'ENVIAR_ORDENS', fallback=True)

# ┌── Seção ARQUIVOS ──────────────────────────────────────────────────────────
FALCAO_EXCEL_PATH = _cfg.get('ARQUIVOS', 'FALCAO_EXCEL_PATH')

# ┌── Seção ATIVOS ────────────────────────────────────────────────────────────
# Usamos o conf ATIVO_PRINCIPAL ou, se faltar, ATIVO_PRINCIPAL_BASE
try:
    base = _cfg.get('ATIVOS', 'ATIVO_PRINCIPAL')
except NoOptionError:
    base = _cfg.get('ATIVOS', 'ATIVO_PRINCIPAL_BASE')
ATIVO_PRINCIPAL = f"{PREFIXO_REPLAY}{base}"
ATIVO_PRINCIPAL_BASE = _cfg.get('ATIVOS', 'ATIVO_PRINCIPAL_BASE')
ATIVOS_CORRELACAO_BASE = [s.strip() for s in _cfg.get('ATIVOS', 'ATIVOS_CORRELACAO_BASE').split(',')]
ATIVOS_CORRELACAO_INVERSA = [s.strip() for s in _cfg.get('ATIVOS', 'ATIVOS_CORRELACAO_INVERSA').split(',')]

# ┌── Seção MODO ─────────────────────────────────────────────────────────────
MODO_OPERACAO = _cfg.get('MODO', 'MODO_OPERACAO')
MODO_SNIPER   = _cfg.getboolean('MODO', 'MODO_SNIPER')

# ┌── Seção PERFIL ────────────────────────────────────────────────────────────
PERFIL_INVESTIDOR = _cfg.get('PERFIL', 'PERFIL_INVESTIDOR')

# ┌── Seção SNIPER_TIMEFRAMES ─────────────────────────────────────────────────
SNIPER_TIMEFRAMES = { key: [v.strip() for v in vals.split(',')] for key, vals in _cfg.items('SNIPER_TIMEFRAMES') }

# ┌── Seção SNIPER_EXIT ────────────────────────────────────────────────────────
SNIPER_EXIT = { key: [v.strip() for v in vals.split(',')] for key, vals in _cfg.items('SNIPER_EXIT') }

# ┌── Seção CONFIANCA ──────────────────────────────────────────────────────────
CONFIANCA_ENTRADA_COMPRA = _cfg.getfloat('CONFIANCA', 'CONFIANCA_ENTRADA_COMPRA')
CONFIANCA_ENTRADA_VENDA  = _cfg.getfloat('CONFIANCA', 'CONFIANCA_ENTRADA_VENDA')

# ┌── Seção AGRESSAO ──────────────────────────────────────────────────────────
VERIFICA_CORRELACAO = _cfg.getboolean('AGRESSAO', 'VERIFICA_CORRELACAO')
TAMANHO_JANELA_CORRELACAO = _cfg.getint('AGRESSAO', 'TAMANHO_JANELA_CORRELACAO')
TAMANHO_JANELA_CORRELACAO_INVERSA = _cfg.getint(
    'AGRESSAO',
    'TAMANHO_JANELA_CORRELACAO_INVERSA',
    fallback=TAMANHO_JANELA_CORRELACAO
)
BUFFER_CORRELACAO = _cfg.getfloat('AGRESSAO', 'BUFFER_CORRELACAO')
CONFIRMACAO_FLUXO = _cfg.getint('AGRESSAO', 'CONFIRMACAO_FLUXO')
LIMIAR_CORRELACAO = _cfg.getfloat('AGRESSAO', 'LIMIAR_CORRELACAO')
LIMIAR_SALDO_MINIMO = _cfg.getfloat('AGRESSAO', 'LIMIAR_SALDO_MINIMO')
LIMIAR_VOLUME_COMPRA = _cfg.getfloat('AGRESSAO', 'LIMIAR_VOLUME_COMPRA')
LIMIAR_VOLUME_VENDA = _cfg.getfloat('AGRESSAO', 'LIMIAR_VOLUME_VENDA')

# ┌── Seção JUROS ─────────────────────────────────────────────────────────────
DESVIO_MINIMO_JUROS = _cfg.getfloat('JUROS', 'DESVIO_MINIMO_JUROS')
BUFFER_AJUSTE = _cfg.getfloat('JUROS', 'BUFFER_AJUSTE')

# ┌── Seção TIMER_LOGS ────────────────────────────────────────────────────────
TEMPO_EXECUCAO = _cfg.getfloat('TIMER_LOGS', 'TEMPO_EXECUCAO')
LOG_DEBUG_ATIVADO = _cfg.getboolean('TIMER_LOGS', 'LOG_DEBUG_ATIVADO')

# ┌── Seções TRAILING_* ───────────────────────────────────────────────────────
TRAILING = {}
for section in _cfg.sections():
    if section.startswith('TRAILING_'):
        prof = section.split('TRAILING_')[1]
        params = {}
        for key, val in _cfg.items(section):
            try:
                if val.lower() in ('true','false'):
                    params[key] = _cfg.getboolean(section,key)
                elif '.' in val:
                    params[key] = _cfg.getfloat(section,key)
                else:
                    params[key] = _cfg.getint(section,key)
            except ValueError:
                params[key] = val
        TRAILING[prof] = params

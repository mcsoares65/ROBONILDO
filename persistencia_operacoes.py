#!/usr/bin/env python3
# persistencia_operacoes.py

import os
import csv
from datetime import datetime
import config
from calibrador import obter_dados_dde
from config import ATIVO_PRINCIPAL


def init_log() -> str:
    """
    Cria (se necessário) e retorna o caminho do CSV diário de operações,
    utilizando a data do DDE (campo 'Data') para nomear o arquivo.
    O CSV é nomeado 'operacoes_YYYY-MM-DD.csv', com cabeçalho:
      data_dde, hora_dde, hora, op_num,
      carteira, banca, contratos, operacoes,
      stop_op, meta_op, stop_diario, meta_diaria
    """
    # pasta de destino
    pasta = config._cfg.get('DEFAULT', 'PASTA_OPERACAOES', fallback=None)
    if not pasta:
        pasta = config._cfg.get('PASTAS', 'PASTA_OPERACAOES')
    os.makedirs(pasta, exist_ok=True)

    # obtém data do DDE (formatos 'DD/MM/YYYY' ou 'YYYY-MM-DD')
    tick = obter_dados_dde(ATIVO_PRINCIPAL) or {}
    dde_data = tick.get('Data') or tick.get('DAT') or ''
    # tenta converter para 'YYYY-MM-DD'
    file_date = None
    if dde_data:
        # normaliza separador
        parts = dde_data.replace('-', '/').split('/')
        if len(parts) == 3:
            d, m, y = parts if len(parts[0]) == 2 else parts[::-1]
            # se vier 'DD/MM/YYYY'
            if len(parts[0]) == 2:
                day, month, year = parts
            else:
                year, month, day = parts
            file_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    if not file_date:
        # fallback para data do sistema
        file_date = datetime.now().strftime("%Y-%m-%d")

    arquivo = os.path.join(pasta, f"operacoes_{file_date}.csv")

    # cabeçalho se não existir
    if not os.path.exists(arquivo):
        with open(arquivo, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'data_dde', 'hora_dde', 'hora', 'op_num',
                'carteira', 'banca', 'contratos', 'operacoes',
                'stop_op', 'meta_op', 'stop_diario', 'meta_diaria'
            ])
    return arquivo


def append_operacao(arquivo: str, registro: dict):
    """
    Anexa uma linha ao CSV, incluindo timestamp de DDE.
    'registro' deve conter chaves:
      'hora', 'op_num', 'carteira', 'banca',
      'contratos', 'operacoes', 'stop_op', 'meta_op',
      'stop_diario', 'meta_diaria'.
    Data/Hora do DDE são capturados via calibrador.obter_dados_dde().
    """
    tick = obter_dados_dde(ATIVO_PRINCIPAL) or {}
    data_dde = tick.get('Data') or tick.get('DAT') or ''
    hora_dde = tick.get('Hora') or tick.get('HOR') or ''

    with open(arquivo, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            data_dde,
            hora_dde,
            registro['hora'],
            registro['op_num'],
            f"{registro['carteira']:.2f}",
            f"{registro['banca']:.2f}",
            registro['contratos'],
            registro['operacoes'],
            registro['stop_op'],
            registro['meta_op'],
            registro['stop_diario'],
            registro['meta_diaria']
        ])


def read_operacoes(arquivo: str) -> list:
    """
    Lê o CSV de operações e retorna lista de registros convertidos.
    Se alguma coluna faltar ou for inválida, aplica valor default.
    """
    registros = []
    if not os.path.exists(arquivo):
        return registros

    with open(arquivo, newline='') as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            def to_float(key):
                v = row.get(key, '0').strip().replace(',', '.')
                try:
                    return float(v)
                except:
                    return 0.0
            def to_int(key):
                v = row.get(key, '0').strip().replace(',', '.')
                try:
                    return int(float(v))
                except:
                    return 0

            op_num = to_int('op_num') or idx

            registros.append({
                'data_dde':    row.get('data_dde', ''),
                'hora_dde':    row.get('hora_dde', ''),
                'hora':        row.get('hora', ''),
                'op_num':      op_num,
                'carteira':    to_float('carteira'),
                'banca':       to_float('banca'),
                'contratos':   to_int('contratos'),
                'operacoes':   to_int('operacoes'),
                'stop_op':     to_float('stop_op'),
                'meta_op':     to_float('meta_op'),
                'stop_diario': to_float('stop_diario'),
                'meta_diaria': to_float('meta_diaria')
            })
    return registros

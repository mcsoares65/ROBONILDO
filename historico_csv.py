"""
ROBONILDO - historico_csv.py (V462)

Leitura dos CSVs de historico (export do Profit ou arquivo persistente do robo) e
escolha do arquivo certo para a carga inicial. Isolado de principal.py para ser
testavel sem Profit/Windows (tests/test_v461_historico.py).
"""

import csv
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import List, Optional

from motor import Candle


def ler_csv_candles(caminho: Path) -> List[Candle]:
    """Formato: Ativo;Data;Hora;Abertura;Maximo;Minimo;Fechamento;Volume;Quantidade
    (mesmo formato usado tanto pelo "Exportar Dados Historicos" do Profit quanto
    pelo arquivo persistente que o proprio robo grava)."""
    candles = []
    with open(caminho, encoding="latin1") as f:
        leitor = csv.reader(f, delimiter=";")
        for linha in leitor:
            if len(linha) < 7:
                continue
            _, data_str, hora_str, abertura, maxima, minima, fechamento = linha[:7]
            horario = datetime.strptime(f"{data_str} {hora_str}", "%d/%m/%Y %H:%M:%S")
            quantidade = None
            if len(linha) > 8 and linha[8].strip():
                try:
                    quantidade = float(linha[8].replace(".", "").replace(",", "."))
                    # CSVs persistidos antigos preenchiam esta coluna com
                    # zero sem leitura de volume. Zero não comprova coleta.
                    if not 0 < quantidade < float("inf"):
                        quantidade = None
                except ValueError:
                    pass
            candles.append(Candle(
                horario=horario,
                abertura=float(abertura.replace(",", ".")),
                maxima=float(maxima.replace(",", ".")),
                minima=float(minima.replace(",", ".")),
                fechamento=float(fechamento.replace(",", ".")),
                quantidade=quantidade,
            ))
    # remove duplicatas por horario (mantem a ULTIMA ocorrencia - normalmente a
    # mais recente/confiavel, ja que candles ao vivo sao gravados depois dos de
    # bootstrap). Necessario porque execucoes repetidas podem acumular o mesmo
    # horario mais de uma vez no arquivo persistente.
    por_horario = {}
    for c in candles:
        por_horario[c.horario] = c
    candles = list(por_horario.values())
    candles.sort(key=lambda c: c.horario)
    return candles



def intervalo_minutos(candles: List[Candle], amostra: int = 300) -> Optional[float]:
    """Mediana (em minutos) entre candles consecutivos DO MESMO DIA, nos ultimos
    `amostra` candles. Serve para reconhecer o timeframe de um arquivo."""
    cs = candles[-amostra:]
    gaps = [(b.horario - a.horario).total_seconds() / 60
            for a, b in zip(cs, cs[1:]) if a.horario.date() == b.horario.date()]
    return median(gaps) if gaps else None


def _ativo_do_csv(caminho: Path) -> Optional[str]:
    try:
        with open(caminho, encoding="latin1") as f:
            for linha in csv.reader(f, delimiter=";"):
                if len(linha) >= 7:
                    return linha[0].strip().upper()
    except OSError:
        return None
    return None


def resolver_csv_historico(caminho_csv: str, timeframe_minutos: int) -> Path:
    """Devolve o CSV com o candle MAIS RECENTE entre os arquivos da mesma pasta
    que (1) comecam com o mesmo ativo no nome, (2) trazem o mesmo ativo na 1a
    coluna e (3) tem o MESMO timeframe (mediana do intervalo entre candles do mesmo
    dia == timeframe_minutos). Sem (3), um export de 1 min mais novo seria escolhido
    no lugar do de 15 min (achado do Manus, ata 2026-10-02-Y). Empate ou falha:
    fica o arquivo configurado.

    Origem: em 01/10/2026 o dono salvou o export novo com outro nome
    (WINFUT_F_0_15min_01-01-2026_01-10-2026.csv) e o robo leu o antigo."""
    configurado = Path(caminho_csv)
    prefixo = configurado.name.split("_")[0]
    ativo_ref = _ativo_do_csv(configurado) if configurado.exists() else None
    melhor, melhor_fim = configurado, None
    if configurado.exists():
        try:
            c = ler_csv_candles(configurado)
            melhor_fim = c[-1].horario if c else None
        except Exception:
            melhor_fim = None
    try:
        outros = [p for p in configurado.parent.glob(f"{prefixo}*.csv") if p != configurado]
    except OSError:
        outros = []
    for p in sorted(outros):
        try:
            c = ler_csv_candles(p)
        except Exception:
            continue
        if not c:
            continue
        if ativo_ref is not None and _ativo_do_csv(p) != ativo_ref:
            continue
        iv = intervalo_minutos(c)
        if iv is None or abs(iv - timeframe_minutos) > 1e-6:
            continue                       # outro timeframe: nunca serve
        if melhor_fim is None or c[-1].horario > melhor_fim:
            print(f"[HISTORICO] '{p.name}' tem candle mais recente ({c[-1].horario}) que "
                  f"'{melhor.name}' ({melhor_fim}) - usando '{p.name}'.")
            melhor, melhor_fim = p, c[-1].horario
    return melhor

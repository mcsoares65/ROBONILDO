"""
ROBONILDO - historico_csv.py (V462)

Leitura dos CSVs de historico (export do Profit ou arquivo persistente do robo) e
escolha do arquivo certo para a carga inicial. Isolado de principal.py para ser
testavel sem Profit/Windows.

V476 - historico por ANO para o backtest: uma pasta por ano sob a pasta-base
(D:\\DAYTRADE\\HISTORICO\\2023, ...\\2026). listar_anos / interpretar_anos /
dias_pos_buraco ficam aqui (puros, sem Profit); a leitura dos arquivos e do
classificacao.py. O principal.py continua lendo so a pasta do ano corrente.
"""

import csv
import re
from datetime import date, datetime
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


# ---------------------------------------------------------------------------
# V476 - historico por ano (backtest)
# ---------------------------------------------------------------------------
_ANO_MIN, _ANO_MAX = 1990, 2100


def listar_anos(pasta_base) -> dict:
    """{ano: pasta} das subpastas da `pasta_base` cujo nome e um ano de 4 digitos
    e que tem pelo menos um .csv. Ordenado por ano. Pasta inexistente -> {}."""
    base = Path(pasta_base)
    achados = {}
    try:
        filhos = sorted(base.iterdir())
    except OSError:
        return {}
    for p in filhos:
        if p.is_dir() and re.fullmatch(r"\d{4}", p.name) and _ANO_MIN <= int(p.name) <= _ANO_MAX:
            if any(p.glob("*.csv")):
                achados[int(p.name)] = p
    return achados


def csvs_do_ano(pasta_ano) -> List[Path]:
    """Todos os .csv da pasta do ano, em ordem de nome (o mais novo, por nome,
    vence em candle repetido quando o carregador funde os arquivos)."""
    return sorted(Path(pasta_ano).glob("*.csv"))


def interpretar_anos(texto: Optional[str], disponiveis: List[int]) -> List[int]:
    """Converte o texto em lista de anos (subconjunto de `disponiveis`, ordenada).

    Aceita: vazio/'todos'/'tudo' = todos; '2023'; '2023-2025' (tambem '2023 a 2025',
    '2023:2025', '2023 ate 2025'); '2022,2024' (ou separado por espaco/';');
    'ultimos 3' = os 3 anos mais recentes. ValueError com mensagem clara se o
    texto nao for entendido ou pedir ano sem pasta."""
    if not disponiveis:
        raise ValueError("nenhum ano disponivel")
    dispon = sorted(set(disponiveis))
    bruto = (texto or "").strip()
    t = bruto.lower().replace("é", "e").replace("ú", "u")
    if t in ("", "todos", "todo", "tudo", "all"):
        return dispon
    m = re.fullmatch(r"(?:ultimos|ultimo|u)\s*(\d+)", t)
    if m:
        n = int(m.group(1))
        if n <= 0:
            raise ValueError(f"quantidade de anos invalida em '{bruto}'")
        return dispon[-n:]
    m = re.fullmatch(r"(\d{4})\s*(?:-|:|a|ate)\s*(\d{4})", t)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        if a > b:
            a, b = b, a
        pedidos = list(range(a, b + 1))
        # intervalo: so os anos que existem dentro dele (buraco no meio nao e erro)
        escolhidos = [x for x in pedidos if x in dispon]
        if not escolhidos:
            raise ValueError(f"nenhum ano de {a} a {b} tem pasta; disponiveis: {', '.join(map(str, dispon))}")
        return escolhidos
    partes = [x for x in re.split(r"[,;\s]+", t) if x]
    if partes and all(re.fullmatch(r"\d{4}", x) for x in partes):
        pedidos = sorted({int(x) for x in partes})
        faltam = [x for x in pedidos if x not in dispon]
        if faltam:
            raise ValueError(f"ano(s) sem pasta: {', '.join(map(str, faltam))}; "
                             f"disponiveis: {', '.join(map(str, dispon))}")
        return pedidos
    raise ValueError(f"nao entendi os anos '{bruto}'. Exemplos: todos | 2023 | 2023-2025 | 2022,2024 | ultimos 2")


def dias_pos_buraco(dias: List[date], limite_dias: int = 10, aquecimento: int = 3) -> set:
    """Pregoes que seguem um buraco de calendario maior que `limite_dias` (anos nao
    consecutivos escolhidos, p.ex. 2023 e 2025): o primeiro e os `aquecimento-1`
    seguintes, para os indicadores nao serem contaminados pelo salto. Devolve o
    conjunto de dias a tirar da apuracao (continuam como aquecimento)."""
    ordenados = sorted(dias)
    fora = set()
    for i in range(1, len(ordenados)):
        if (ordenados[i] - ordenados[i - 1]).days > limite_dias:
            fora.update(ordenados[i:i + aquecimento])
    return fora

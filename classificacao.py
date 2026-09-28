"""Classificação oficial dos cartuchos executados pelo console motor.py.

Critério único de ordenação para entrada, saída e cruzado:

  acumulado = resultado - abs(drawdown)

Como o drawdown é armazenado com sinal negativo, a mesma fórmula também
pode ser escrita como ``resultado + drawdown``. Quanto maior o lucro e menor
o drawdown, maior o acumulado. As métricas multitemporais continuam sendo
calculadas para auditoria, mas não definem a posição no ranking.
"""

from __future__ import annotations

import csv
import importlib.util
import io
import math
import re
import subprocess
import contextlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Callable, Iterable, Optional

import configuracao as cfg
from motor import Candle, MotorRobonildo, construir_row

# Versionamento próprio deste programa. Alterações em regras de validação,
# ordenação ou apresentação da classificação incrementam esta constante sem
# alterar a versão operacional do Robonildo definida em configuracao.py.
VERSAO_CLASSIFICACAO = "C001"

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _git_sha_atual() -> str:
    """SHA do commit atual do repositório, ou "sem-git" se não estiver
    rodando dentro de um clone git (ex: pasta copiada manualmente). Usado só
    para carimbar `logs/classificacao_historico.md` - nunca falha o
    programa, silenciosamente vira "sem-git"."""
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=Path(__file__).resolve().parent,
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
    except Exception:
        return "sem-git"


def _registrar_historico(titulo: str, texto: str) -> None:
    """Acrescenta (NUNCA sobrescreve) o resultado desta rodada em
    `logs/classificacao_historico.md`, carimbado com data/hora e o SHA do
    commit atual do repositório.

    Existe para que nenhuma promoção de titular dependa de alguém (humano
    ou IA) colar manualmente um resultado no chat ou num PR - o próprio
    `classificacao.py` já deixa a prova gravada, atrelada ao commit exato
    em que rodou (compliance.md, Regra 4: nenhum resultado vale sem ter
    sido rodado de novo contra o motor atual - o SHA aqui é o que permite
    conferir isso depois, sem confiar na palavra de quem rodou).
    """
    pasta_logs = Path(cfg.PASTA_LOGS_AUDITORIA)
    pasta_logs.mkdir(parents=True, exist_ok=True)
    caminho = pasta_logs / "classificacao_historico.md"
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sha = _git_sha_atual()
    texto_limpo = _ANSI_RE.sub("", texto).rstrip()
    bloco = f"\n## {agora} — commit `{sha}`\n\n{titulo}\n\n```\n{texto_limpo}\n```\n"
    with caminho.open("a", encoding="utf-8") as f:
        f.write(bloco)


@contextlib.contextmanager
def _capturar_e_imprimir():
    """Deixa o bloco `with` imprimir normalmente no terminal E devolve o
    texto capturado (sem códigos ANSI removidos ainda - isso é feito em
    `_registrar_historico`) para gravar no histórico."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        yield buf
    texto = buf.getvalue()
    print(texto, end="")

try:
    import colorama
    colorama.init()
    VERDE = colorama.Fore.LIGHTGREEN_EX
    VERMELHO = colorama.Fore.RED
    RESET = colorama.Style.RESET_ALL
except ImportError:
    VERDE = VERMELHO = RESET = ""
# Azul celeste para a linha da estrategia titular - fora da paleta padrao do
# colorama (so tem os 8 nomes classicos), por isso usa o codigo ANSI 256
# direto (117 = azul celeste claro). Mesma tecnica ja usada no marcador de
# posicao em principal.py.
AZUL_CELESTE = "\x1b[38;5;117m" if RESET else ""


def _progresso(etapa: str, atual: int, total: int, detalhe: str = "") -> None:
    """Atualiza uma única linha do terminal sem poluir a classificação."""
    percentual = 100.0 * atual / total if total else 100.0
    complemento = f" | {detalhe}" if detalhe else ""
    print(
        f"\r[{etapa}] {atual:>{len(str(max(total, 1)))}}/{total} "
        f"({percentual:6.2f}%){complemento}",
        end="",
        flush=True,
    )
    if atual >= total:
        print()


def carregar_csv(caminho: Path) -> list[Candle]:
    candles = []
    tamanho_total = max(caminho.stat().st_size, 1)
    bytes_lidos = 0
    linhas_lidas = 0
    print(f"[LEITURA] Abrindo {caminho.resolve()}")
    with caminho.open("rb") as arquivo:
        for linha_bruta in arquivo:
            bytes_lidos += len(linha_bruta)
            linhas_lidas += 1
            linha = next(csv.reader([linha_bruta.decode("latin1")], delimiter=";"))
            if len(linha) < 7:
                pass
            else:
                try:
                    horario = datetime.strptime(
                        f"{linha[1]} {linha[2]}", "%d/%m/%Y %H:%M:%S"
                    )
                    valores = [float(v.replace(".", "").replace(",", ".")) for v in linha[3:7]]
                except ValueError:
                    pass
                else:
                    candles.append(Candle(horario, *valores))
            if linhas_lidas % 500 == 0:
                _progresso("LEITURA", min(bytes_lidos, tamanho_total), tamanho_total,
                           f"{len(candles)} candles válidos")

    _progresso("LEITURA", tamanho_total, tamanho_total, f"{len(candles)} candles válidos")

    por_horario = {c.horario: c for c in candles}
    ordenados = sorted(por_horario.values(), key=lambda c: c.horario)
    if not ordenados:
        raise ValueError("O histórico não contém candles válidos.")
    return ordenados


def preparar_aquecimento(candles_avaliacao: list[Candle]) -> tuple[list[Candle], int]:
    """Completa históricos curtos com candles anteriores, sem pontuá-los."""
    if len(candles_avaliacao) >= 66:
        return candles_avaliacao, 0

    caminho = Path(cfg.LAB_CAMINHO_HISTORICO_AQUECIMENTO)
    if not caminho.exists():
        raise ValueError(
            "O arquivo avaliado não possui 66 candles para calcular os indicadores e "
            f"o histórico de aquecimento não foi encontrado em '{caminho}'."
        )
    print(f"[AQUECIMENTO] Histórico curto detectado; buscando candles anteriores em {caminho}.")
    historico = carregar_csv(caminho)
    inicio = candles_avaliacao[0].horario
    anteriores = [candle for candle in historico if candle.horario < inicio][-65:]
    if len(anteriores) < 65:
        raise ValueError(
            "Histórico curto: são necessários 65 candles anteriores para aquecer "
            f"os indicadores, mas somente {len(anteriores)} foram encontrados."
        )
    por_horario = {c.horario: c for c in anteriores + candles_avaliacao}
    combinados = sorted(por_horario.values(), key=lambda c: c.horario)
    print(f"[AQUECIMENTO] {len(anteriores)} candles anteriores adicionados; eles não serão pontuados.")
    return combinados, len(anteriores)


def _importar_arquivo(caminho: Path, indice):
    nome_modulo = f"robonildo_lab_{indice}_{abs(hash(caminho.resolve()))}"
    spec = importlib.util.spec_from_file_location(nome_modulo, caminho)
    if spec is None or spec.loader is None:
        raise ImportError(f"Não foi possível importar {caminho}")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo



@dataclass
class CartuchoEntrada:
    nome: str
    caminho: Path
    gerar_sinal: Callable
    titular: bool = False


@dataclass
class CartuchoSaida:
    nome: str
    caminho: Path
    avaliar_saida: Callable
    titular: bool = False


# Compat: nome antigo usado em trechos legados
EstrategiaCarregada = CartuchoEntrada


def _listar_py(pasta: Path) -> list[Path]:
    """Arquivos .py de cartucho diretamente numa pasta (não desce em subpastas)."""
    if not pasta.exists():
        return []
    return sorted(
        p for p in pasta.glob("*.py")
        if not p.stem.startswith("_")
    )


def listar_cartuchos_disco() -> dict:
    """
    Estrutura oficial (sem pasta laboratorio):

      estrategia/entrada/titular/   → exatamente 1 .py  (entrada de produção)
      estrategia/entrada/*.py      → candidatas de ranking de ENTRADA

      estrategia/saida/titular/     → exatamente 1 .py  (saída de produção)
      estrategia/saida/*.py        → candidatas de ranking de SAÍDA

    Rankings:
      1) entradas × saída titular
      2) saída candidatas × entrada titular
      3) cruzado (todas entradas × todas saídas) — ranking principal
    """
    raiz = Path(__file__).resolve().parent
    pasta_entrada = raiz / "estrategia" / "entrada"
    pasta_saida = raiz / "estrategia" / "saida"
    pasta_entrada_titular = pasta_entrada / "titular"
    pasta_saida_titular = pasta_saida / "titular"

    return {
        "raiz": raiz,
        "pasta_entrada": pasta_entrada,
        "pasta_saida": pasta_saida,
        "pasta_entrada_titular": pasta_entrada_titular,
        "pasta_saida_titular": pasta_saida_titular,
        "entrada_titular": _listar_py(pasta_entrada_titular),
        "entrada_candidatas": _listar_py(pasta_entrada),
        "saida_titular": _listar_py(pasta_saida_titular),
        "saida_candidatas": _listar_py(pasta_saida),
    }


def imprimir_inventario_cartuchos(inv: dict) -> None:
    """Lista no terminal titulares e candidatas de entrada/saída."""
    print("-" * 100)
    print("CARTUCHOS NO DISCO (entrada/saída — sem laboratório)")
    print(f"  estrategia/entrada/titular/  → {inv['pasta_entrada_titular']}")
    if inv["entrada_titular"]:
        for p in inv["entrada_titular"]:
            print(f"    • {p.name} [TITULAR]")
    else:
        print("    (vazia — obrigatório 1 arquivo)")

    print(f"  estrategia/entrada/ (candidatas) → {inv['pasta_entrada']}")
    if inv["entrada_candidatas"]:
        for p in inv["entrada_candidatas"]:
            print(f"    • {p.name}")
    else:
        print("    (nenhuma candidata)")

    print(f"  estrategia/saida/titular/    → {inv['pasta_saida_titular']}")
    if inv["saida_titular"]:
        for p in inv["saida_titular"]:
            print(f"    • {p.name} [TITULAR]")
    else:
        print("    (vazia — obrigatório 1 arquivo)")

    print(f"  estrategia/saida/ (candidatas)   → {inv['pasta_saida']}")
    if inv["saida_candidatas"]:
        for p in inv["saida_candidatas"]:
            print(f"    • {p.name}")
    else:
        print("    (nenhuma candidata)")
    print("-" * 100)


def descobrir_entradas() -> tuple[list[CartuchoEntrada], list[tuple[str, str]]]:
    """Todas as entradas: titular + candidatas na raiz de entrada/."""
    inv = listar_cartuchos_disco()
    titulares = inv["entrada_titular"]
    if len(titulares) != 1:
        raise RuntimeError(
            "A pasta estrategia/entrada/titular/ deve conter exatamente um arquivo. "
            f"Encontrados: {[p.name for p in titulares]}"
        )
    caminho_titular = titulares[0]

    caminhos = [caminho_titular]
    vistos = {caminho_titular.stem.casefold()}
    for caminho in inv["entrada_candidatas"]:
        if caminho.stem.casefold() in vistos:
            continue
        vistos.add(caminho.stem.casefold())
        caminhos.append(caminho)

    carregadas = []
    falhas = []
    for indice, caminho in enumerate(caminhos):
        try:
            modulo = _importar_arquivo(caminho, f"ent_{indice}")
        except Exception as erro:
            if caminho.resolve() == caminho_titular.resolve():
                raise
            falhas.append(
                (caminho.stem, f"falha na importação: {type(erro).__name__}: {erro}")
            )
            continue
        gerar = getattr(modulo, "gerar_sinal", None)
        if callable(gerar):
            carregadas.append(CartuchoEntrada(
                nome=caminho.stem,
                caminho=caminho,
                gerar_sinal=gerar,
                titular=(caminho.resolve() == caminho_titular.resolve()),
            ))
        else:
            falhas.append((caminho.stem, "função gerar_sinal(row) ausente"))
    return carregadas, falhas


def descobrir_saidas() -> tuple[list[CartuchoSaida], list[tuple[str, str]]]:
    """Todas as saídas: titular + candidatas na raiz de saida/."""
    inv = listar_cartuchos_disco()
    titulares = inv["saida_titular"]
    if len(titulares) != 1:
        raise RuntimeError(
            "A pasta estrategia/saida/titular/ deve conter exatamente um arquivo. "
            f"Encontrados: {[p.name for p in titulares]}"
        )
    caminho_titular = titulares[0]

    caminhos = [caminho_titular]
    vistos = {caminho_titular.stem.casefold()}
    for caminho in inv["saida_candidatas"]:
        if caminho.stem.casefold() in vistos:
            continue
        vistos.add(caminho.stem.casefold())
        caminhos.append(caminho)

    carregadas = []
    falhas = []
    for indice, caminho in enumerate(caminhos):
        try:
            modulo = _importar_arquivo(caminho, f"sai_{indice}")
        except Exception as erro:
            if caminho.resolve() == caminho_titular.resolve():
                raise
            falhas.append(
                (caminho.stem, f"falha na importação: {type(erro).__name__}: {erro}")
            )
            continue
        avaliar = getattr(modulo, "avaliar_saida", None)
        if callable(avaliar):
            carregadas.append(CartuchoSaida(
                nome=caminho.stem,
                caminho=caminho,
                avaliar_saida=avaliar,
                titular=(caminho.resolve() == caminho_titular.resolve()),
            ))
        else:
            falhas.append((caminho.stem, "função avaliar_saida(row, posicao) ausente"))
    return carregadas, falhas


def descobrir_estrategias() -> tuple[list[CartuchoEntrada], list[tuple[str, str]]]:
    """Compat: retorna só entradas (titular + candidatas)."""
    return descobrir_entradas()


def descobrir_cartucho_saida():
    """Compat: retorna (nome, callable) da saída titular."""
    saidas, _ = descobrir_saidas()
    titular = next((s for s in saidas if s.titular), None)
    if titular is None:
        raise RuntimeError("Nenhuma saída titular encontrada em estrategia/saida/titular/.")
    return titular.nome, titular.avaliar_saida




def preparar_rows(candles: list[Candle]) -> list[Optional[dict]]:
    rows = [None] * len(candles)
    total = max(0, len(candles) - 65)
    for indice in range(65, len(candles)):
        rows[indice] = construir_row(candles[:indice + 1])
        concluido = indice - 64
        if concluido % 250 == 0 or concluido == total:
            _progresso("INDICADORES", concluido, total)
    return rows


def validar_contrato_saida(cartucho: CartuchoSaida, rows: list[Optional[dict]]) -> tuple[bool, str]:
    """Valida o contrato V445 antes de permitir que a saída participe do ranking.

    A V445 não fornece proteção implícita. Portanto, uma saída compatível deve
    retornar um ``dict`` na abertura e fornecer um stop inicial finito e
    coerente tanto para COMPRA quanto para VENDA. O alvo pode ser ``None``
    quando o próprio cartucho optar explicitamente por trabalhar sem alvo.
    """
    row = next((item for item in reversed(rows) if item is not None), None)
    if row is None:
        return False, "não há indicadores suficientes para validar a abertura"

    ohlc = row.get("ohlc_recentes") or ()
    janela = ohlc[-5:]
    if len(janela) < 5:
        return False, "row de validação não contém cinco candles em ohlc_recentes"

    minima = min(float(c["Minimo"]) for c in janela)
    maxima = max(float(c["Maximo"]) for c in janela)
    if not math.isfinite(minima) or not math.isfinite(maxima) or maxima <= minima:
        return False, "janela OHLC inválida para o teste de abertura"

    # O ponto médio evita reprovar artificialmente uma fórmula estrutural
    # quando o último fechamento coincide exatamente com um extremo da janela.
    entrada = (minima + maxima) / 2.0
    for lado in ("COMPRA", "VENDA"):
        posicao = {
            "lado": lado,
            "entrada": entrada,
            "candles_decorridos": 0,
            "maxima_desde_entrada": entrada,
            "minima_desde_entrada": entrada,
            "resultado_flutuante_pts": 0.0,
        }
        try:
            resposta = cartucho.avaliar_saida(row, posicao)
        except Exception as erro:
            return False, f"falhou na abertura de {lado}: {type(erro).__name__}: {erro}"

        if not isinstance(resposta, dict):
            return False, (
                f"retornou {type(resposta).__name__} na abertura de {lado}; "
                "a V445 exige dict com novo_stop e novo_alvo"
            )
        if bool(resposta.get("fechar", False)):
            return False, f"solicitou fechamento durante a abertura de {lado}"
        if "novo_stop" not in resposta or "novo_alvo" not in resposta:
            return False, f"retorno de {lado} não contém novo_stop e novo_alvo"

        try:
            stop = float(resposta["novo_stop"])
        except (TypeError, ValueError):
            return False, f"novo_stop ausente ou não numérico na abertura de {lado}"
        if not math.isfinite(stop):
            return False, f"novo_stop não finito na abertura de {lado}"
        if lado == "COMPRA" and stop >= entrada:
            return False, "stop inicial de COMPRA não está abaixo da entrada"
        if lado == "VENDA" and stop <= entrada:
            return False, "stop inicial de VENDA não está acima da entrada"

        alvo_bruto = resposta.get("novo_alvo")
        if alvo_bruto is not None:
            try:
                alvo = float(alvo_bruto)
            except (TypeError, ValueError):
                return False, f"novo_alvo não numérico na abertura de {lado}"
            if not math.isfinite(alvo):
                return False, f"novo_alvo não finito na abertura de {lado}"
            if lado == "COMPRA" and alvo <= entrada:
                return False, "alvo inicial de COMPRA não está acima da entrada"
            if lado == "VENDA" and alvo >= entrada:
                return False, "alvo inicial de VENDA não está abaixo da entrada"

    return True, ""


def _ultimo_candle_do_dia(candles: list[Candle], indice: int) -> bool:
    return (
        indice == len(candles) - 1
        or candles[indice + 1].horario.date() != candles[indice].horario.date()
    )


def executar_jogo(
    candles: list[Candle],
    rows: list[Optional[dict]],
    estrategia,  # CartuchoEntrada
    dias_avaliacao: set,
    avaliar_saida=None,
) -> list[dict]:
    """Executa o histórico diretamente no mesmo motor usado por principal.py.

    avaliar_saida: cartucho de saída titular (estrategia/saida/) - pareado
    com TODA estratégia de entrada candidata, para que a classificação
    reflita o que rodaria em produção com a saída atual."""
    if len(candles) <= 65:
        return []

    motor = MotorRobonildo(
        gerar_sinal=estrategia.gerar_sinal,
        arquivo_estado=None,
        horario_mercado_inicial=candles[65].horario,
        avaliar_saida=avaliar_saida,
    )
    for indice in range(65, len(candles)):
        candle = candles[indice]
        if candle.horario.date() not in dias_avaliacao:
            continue
        row = rows[indice]
        if row is None:
            continue
        motor.processar_candle_historico(
            candles[:indice + 1],
            ultimo_candle_do_dia=_ultimo_candle_do_dia(candles, indice),
            row=row,
        )
    return motor.operacoes_fechadas


def _profit_factor(trades: Iterable[dict]) -> float:
    valores = [t["resultado_reais"] for t in trades]
    ganhos = sum(v for v in valores if v > 0)
    perdas = abs(sum(v for v in valores if v <= 0))
    if not valores or perdas == 0:
        return float("nan")
    return ganhos / perdas


def _resumo(trades: list[dict], dias_periodo: int) -> dict:
    resultado = sum(t["resultado_reais"] for t in trades)
    dias_operados = len({t["horario_rotulo"].date() for t in trades})
    acumulado = pico = drawdown = 0.0
    for trade in trades:
        acumulado += trade["resultado_reais"]
        pico = max(pico, acumulado)
        drawdown = min(drawdown, acumulado - pico)
    return {
        "resultado": resultado,
        "diaria": resultado / dias_periodo if dias_periodo else 0.0,
        "dias_operados": dias_operados,
        "aproveitamento": resultado / dias_operados if dias_operados else 0.0,
        "drawdown": drawdown,
        "capital_minimo": cfg.MARGEM_WIN_LABORATORIO + abs(drawdown),
        "pf": _profit_factor(trades),
        "operacoes": len(trades),
        "ambiguidades": sum(1 for t in trades if t["intrabar_ambiguo"]),
    }


def _percentil_25(valores: list[float]) -> float:
    if not valores:
        return float("nan")
    valores = sorted(valores)
    posicao = 0.25 * (len(valores) - 1)
    inferior = math.floor(posicao)
    superior = math.ceil(posicao)
    if inferior == superior:
        return valores[inferior]
    fracao = posicao - inferior
    return valores[inferior] * (1 - fracao) + valores[superior] * fracao


def _pontuacao(resultado: float, capital: float, pf: float, dias: int) -> float:
    if capital <= 0 or dias <= 0 or math.isnan(pf):
        return float("nan")
    return (resultado / capital) * pf * math.sqrt(dias)


def avaliar_robustez(trades: list[dict], dias: list, tamanho: int, passo: int) -> dict:
    pontuacoes = []
    resultados = []
    for inicio in range(0, max(0, len(dias) - tamanho + 1), passo):
        janela = set(dias[inicio:inicio + tamanho])
        locais = [t for t in trades if t["horario_rotulo"].date() in janela]
        resumo = _resumo(locais, tamanho)
        score = _pontuacao(
            resumo["resultado"], resumo["capital_minimo"], resumo["pf"],
            resumo["dias_operados"],
        )
        if not math.isnan(score):
            pontuacoes.append(score)
        resultados.append(resumo["resultado"])
    return {
        "janelas": len(resultados),
        "janelas_positivas_pct": 100 * sum(v > 0 for v in resultados) / len(resultados) if resultados else 0.0,
        "pior_janela": min(resultados) if resultados else 0.0,
        "mediana_janela": median(resultados) if resultados else 0.0,
        "pontuacao_robusta": _percentil_25(pontuacoes),
    }


def _media(valores: list[float]) -> float:
    return sum(valores) / len(valores) if valores else float("nan")


def _score_periodo(trades: list[dict], quantidade_dias: int) -> float:
    """Nota simples de retorno por capital, ajustada pela recorrência."""
    if quantidade_dias <= 0:
        return float("nan")
    resumo = _resumo(trades, quantidade_dias)
    if resumo["capital_minimo"] <= 0:
        return float("nan")
    recorrencia = math.sqrt(max(resumo["dias_operados"], 1))
    return (resumo["resultado"] / resumo["capital_minimo"]) * recorrencia


def avaliar_horizontes(trades: list[dict], dias: list) -> dict:
    """Calcula as notas brutas mensal e diária, incluindo pregões sem trade."""
    por_dia = {dia: [] for dia in dias}
    for trade in trades:
        por_dia.setdefault(trade["horario_rotulo"].date(), []).append(trade)
    scores_diarios = [_score_periodo(por_dia[dia], 1) for dia in dias]

    meses = sorted({(dia.year, dia.month) for dia in dias})
    scores_mensais = []
    for ano, mes in meses:
        dias_mes = [dia for dia in dias if (dia.year, dia.month) == (ano, mes)]
        trades_mes = [
            trade for trade in trades
            if (trade["horario_rotulo"].year, trade["horario_rotulo"].month) == (ano, mes)
        ]
        scores_mensais.append(_score_periodo(trades_mes, len(dias_mes)))

    mensal = (
        0.40 * _media(scores_mensais)
        + 0.30 * median(scores_mensais)
        + 0.30 * _percentil_25(scores_mensais)
    ) if scores_mensais else float("nan")
    diario = (
        0.30 * _media(scores_diarios)
        + 0.30 * median(scores_diarios)
        + 0.40 * _percentil_25(scores_diarios)
    ) if scores_diarios else float("nan")
    return {
        "score_mensal_raw": mensal,
        "score_diario_raw": diario,
        "meses_avaliados": len(meses),
        "pregoes_avaliados": len(dias),
    }


def aplicar_pontuacao_multitemporal(resultados: list[dict], dias: list) -> dict:
    """Score ABSOLUTO individual — sem percentil entre concorrentes.

    multi = (peso_longo  × score_longo_raw
           + peso_mensal × score_mensal_raw
           + peso_diario × score_diario_raw) / pesos_válidos

    Pesos padrão (cfg): 50% longo + 30% mensal + 20% diário.
    Se um horizonte não estiver disponível, redistribui entre os ativos.

    Um colega que rode uma única estratégia isolada obtém o MESMO multi
    que obteria aqui no arsenal completo — comparável por valor, não por rank.
    """
    meses = len({(dia.year, dia.month) for dia in dias})
    usar_longo = meses >= cfg.LAB_MIN_MESES_LONGO
    usar_mensal = meses >= cfg.LAB_MIN_MESES_MENSAL and len(dias) >= cfg.LAB_MIN_PREGOES_MENSAL
    usar_diario = bool(dias)

    # Notas = scores brutos individuais (não percentil 0-100).
    for resultado in resultados:
        resultado["nota_longo"] = (
            resultado["score_longo_raw"] if usar_longo else float("nan")
        )
        resultado["nota_mensal"] = (
            resultado["score_mensal_raw"] if usar_mensal else float("nan")
        )
        resultado["nota_diario"] = (
            resultado["score_diario_raw"] if usar_diario else float("nan")
        )

    horizontes = [
        ("nota_longo", cfg.LAB_PESO_LONGO, usar_longo),
        ("nota_mensal", cfg.LAB_PESO_MENSAL, usar_mensal),
        ("nota_diario", cfg.LAB_PESO_DIARIO, usar_diario),
    ]
    peso_disponivel = sum(peso for _, peso, ativo in horizontes if ativo)
    for resultado in resultados:
        parcelas = [
            resultado[chave] * peso
            for chave, peso, ativo in horizontes
            if ativo and not math.isnan(resultado[chave])
        ]
        pesos_validos = sum(
            peso for chave, peso, ativo in horizontes
            if ativo and not math.isnan(resultado[chave])
        )
        pontuacao_base = (
            sum(parcelas) / pesos_validos if pesos_validos else float("nan")
        )
        resultado["pontuacao_multitemporal_base"] = pontuacao_base
        resultado["pontuacao_multitemporal"] = pontuacao_base

    if meses >= 12:
        confianca = "ALTA"
    elif meses >= 6:
        confianca = "BOA"
    elif meses >= 3:
        confianca = "MODERADA"
    elif len(dias) >= 20:
        confianca = "MODERADA-BAIXA"
    elif len(dias) >= 2:
        confianca = "BAIXA"
    else:
        confianca = "MUITO BAIXA"
    return {
        "longo": usar_longo,
        "mensal": usar_mensal,
        "diario": usar_diario,
        "peso_disponivel": peso_disponivel,
        "confianca": confianca,
    }


def _moeda(valor: float) -> str:
    return f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")



def _imprimir_ranking_simples(titulo: str, resultados: list[dict], chave_nome: str = "estrategia") -> None:
    if not resultados:
        print(f"\n{titulo}: nenhuma combinação produziu resultado.")
        return
    colunas = (
        ("pos", "pos", False, 3),
        (chave_nome, "estratégia", False, 34),
        ("resultado", "resultado", True, 10),
        ("diaria", "diária", True, 7),
        ("dias_operados", "dias", False, 4),
        ("aproveitamento", "aproveit", True, 8),
        ("drawdown", "drawdown", True, 10),
        ("capital_minimo", "cap_min", True, 9),
        ("acumulado", "acumulado", True, 10),
    )
    largura_total = sum(c[3] for c in colunas) + len(colunas) - 1
    print(f"\n========== {titulo} ==========")
    print(" ".join(f"{rotulo:>{largura}}" for _, rotulo, _, largura in colunas))
    print("-" * largura_total)

    def formatar(linha, chave, moeda):
        valor = linha[chave]
        if moeda:
            return _moeda(valor)
        return str(valor)

    def ajustar(texto, largura):
        return texto if len(texto) <= largura else texto[:largura - 2] + ".."

    for indice, linha in enumerate(resultados):
        cor = (
            AZUL_CELESTE if linha.get("titular")
            else VERDE if indice == 0
            else (VERMELHO if indice == len(resultados) - 1 else "")
        )
        texto = " ".join(
            f"{ajustar(formatar(linha, chave, moeda), largura):>{largura}}"
            for chave, _, moeda, largura in colunas
        )
        print(f"{cor}{texto}{RESET}")
    print(
        f"{VERDE}Verde{RESET}=1º | {VERMELHO}Vermelho{RESET}=último | "
        f"{AZUL_CELESTE}Azul{RESET}=titular do slot"
    )
    print("Acumulado = resultado - abs(drawdown). Maior acumulado vence.")


def _imprimir_ranking_cruzado(resultados: list[dict], total_pregoes: int = 0) -> None:
    if not resultados:
        print("\n========== RANKING PRINCIPAL (ENTRADA × SAÍDA) ==========")
        print("Nenhuma combinação produziu resultado.")
        return
    colunas = (
        ("pos", "pos", False, 3),
        ("entrada", "entrada", False, 24),
        ("saida", "saída", False, 18),
        ("resultado", "resultado", True, 10),
        ("diaria", "diária", True, 7),
        ("dias_operados", "dias", False, 4),
        ("drawdown", "drawdown", True, 10),
        ("capital_minimo", "cap_min", True, 9),
        ("acumulado", "acumulado", True, 10),
    )
    largura_total = sum(c[3] for c in colunas) + len(colunas) - 1
    print(
        f"\n========== RANKING PRINCIPAL {VERSAO_CLASSIFICACAO} "
        f"(ENTRADA × SAÍDA | MOTOR {cfg.VERSAO}) =========="
    )
    print(f"Total de pregões avaliados: {total_pregoes}")
    print(" ".join(f"{rotulo:>{largura}}" for _, rotulo, _, largura in colunas))
    print("-" * largura_total)

    def formatar(linha, chave, moeda):
        valor = linha[chave]
        if moeda:
            return _moeda(valor)
        return str(valor)

    def ajustar(texto, largura):
        return texto if len(texto) <= largura else texto[:largura - 2] + ".."

    for indice, linha in enumerate(resultados):
        cor = VERDE if indice == 0 else (VERMELHO if indice == len(resultados) - 1 else "")
        texto = " ".join(
            f"{ajustar(formatar(linha, chave, moeda), largura):>{largura}}"
            for chave, _, moeda, largura in colunas
        )
        print(f"{cor}{texto}{RESET}")
    print("Acumulado = resultado - abs(drawdown). Maior acumulado vence.")


def _montar_resultado_par(
    nome_entrada: str,
    nome_saida: str,
    trades: list[dict],
    dias: list,
    entrada_titular: bool = False,
    saida_titular: bool = False,
) -> dict:
    resumo = _resumo(trades, len(dias))
    corte = dias[-min(cfg.LAB_DIAS_TESTE, max(1, len(dias) // 3))]
    longo = [t for t in trades if t["horario_rotulo"].date() < corte]
    curto = [t for t in trades if t["horario_rotulo"].date() >= corte]
    pf_longo = _profit_factor(longo)
    pf_curto = _profit_factor(curto)
    pf_minimo = (
        min(pf_longo, pf_curto)
        if not math.isnan(pf_longo) and not math.isnan(pf_curto)
        else float("nan")
    )
    score = _pontuacao(
        resumo["resultado"], resumo["capital_minimo"], pf_minimo, resumo["dias_operados"]
    )
    acumulado = resumo["resultado"] - abs(resumo["drawdown"])
    robustez = avaliar_robustez(trades, dias, cfg.LAB_JANELA_PREGOES, cfg.LAB_PASSO_JANELA)
    horizontes = avaliar_horizontes(trades, dias)
    return {
        "entrada": nome_entrada,
        "saida": nome_saida,
        "estrategia": nome_entrada,  # ranking só-entrada
        "estrategia_saida": nome_saida,  # ranking só-saída
        "titular": entrada_titular and saida_titular,
        "titular_entrada": entrada_titular,
        "titular_saida": saida_titular,
        **resumo,
        "pf_longo": pf_longo,
        "pf_curto": pf_curto,
        "acumulado": acumulado,
        "score_longo_raw": score,      # métrica multitemporal mantida para auditoria
        **horizontes,
        **robustez,
        "operacoes_n": len(trades),
    }


def _perguntar_modo_ranking() -> str:
    """
    Pergunta qual ranking rodar:
      E = só entradas (pareadas com saída titular)
      S = só saídas   (pareadas com entrada titular)
      C = cruzado     (todas as combinações — ranking principal)
    """
    while True:
        resp = input(
            "Qual ranking deseja? Entradas (E), Saídas (S) ou Cruzada (C): "
        ).strip().upper()
        if resp in ("E", "S", "C"):
            return resp
        print(f"Resposta '{resp}' não reconhecida — digite exatamente E, S ou C.")


def executar(caminho_csv: Optional[str] = None):
    caminho = Path(caminho_csv or cfg.CAMINHO_HISTORICO_INICIAL)
    if not caminho.exists():
        informado = input(
            f"CSV não encontrado em '{caminho}'. Informe o caminho completo: "
        ).strip().strip('"')
        caminho = Path(informado)

    inventario = listar_cartuchos_disco()
    imprimir_inventario_cartuchos(inventario)

    modo = _perguntar_modo_ranking()
    rotulos_modo = {
        "E": "ENTRADA (pareado com saída titular)",
        "S": "SAÍDA (pareado com entrada titular)",
        "C": "CRUZADO (todas as combinações entrada × saída)",
    }
    print(f"[MODO] Ranking escolhido: {modo} — {rotulos_modo[modo]}")

    candles_avaliacao = carregar_csv(caminho)
    dias = sorted({c.horario.date() for c in candles_avaliacao})
    dias_avaliacao = set(dias)
    candles, quantidade_aquecimento = preparar_aquecimento(candles_avaliacao)

    entradas, falhas_e = descobrir_entradas()
    saidas, falhas_s = descobrir_saidas()
    if not entradas:
        raise RuntimeError("Nenhuma entrada compatível foi encontrada.")
    if not saidas:
        raise RuntimeError("Nenhuma saída compatível foi encontrada.")

    entrada_titular = next(e for e in entradas if e.titular)
    saida_titular_carregada = next(s for s in saidas if s.titular)

    print("=" * 100)
    print(
        f"CLASSIFICAÇÃO [{VERSAO_CLASSIFICACAO}] — "
        f"ROBONILDO [{cfg.VERSAO}] ({rotulos_modo[modo]})"
    )
    print(
        f"Histórico: {candles_avaliacao[0].horario} até {candles_avaliacao[-1].horario} | "
        f"{len(candles_avaliacao)} candles | {len(dias)} pregões"
    )
    if quantidade_aquecimento:
        print(f"Aquecimento externo: {quantidade_aquecimento} candles (fora da pontuação)")
    print(f"Entrada titular: {entrada_titular.nome}.py")
    print(f"Saída titular  : {saida_titular_carregada.nome}.py")
    print(f"Entradas no ranking: {len(entradas)} | Saídas no ranking: {len(saidas)}")
    print("Multi = score ABSOLUTO individual (50/30/20) — sem percentil entre concorrentes.")
    print("=" * 100)

    print("[ETAPA 1/2] Calculando indicadores com o motor oficial...")
    rows = preparar_rows(candles)

    incompatíveis = list(falhas_e) + list(falhas_s)
    saidas_compativeis = []
    print("[CONTRATO] Validando proteção inicial dos cartuchos de saída...")
    for sai in saidas:
        compativel, motivo = validar_contrato_saida(sai, rows)
        if compativel:
            saidas_compativeis.append(sai)
            print(f"  {sai.nome}")
        else:
            incompatíveis.append((sai.nome, motivo))
            print(f"  {sai.nome} (INCOMPATIVEL)")

    if saida_titular_carregada not in saidas_compativeis:
        motivo = next(
            (erro for nome, erro in incompatíveis if nome == saida_titular_carregada.nome),
            "contrato V445 inválido",
        )
        raise RuntimeError(
            f"A saída titular {saida_titular_carregada.nome}.py está INCOMPATIVEL: {motivo}"
        )

    saidas = saidas_compativeis
    saida_titular = saida_titular_carregada

    # Só calcula o que o modo pede — evita produto cartesiano desnecessário
    # e impede que uma saída sem proteção inicial produza números enganosos.
    if modo == "E":
        pares_a_rodar = [(ent, saida_titular) for ent in entradas]
    elif modo == "S":
        pares_a_rodar = [(entrada_titular, sai) for sai in saidas]
    else:  # C
        pares_a_rodar = [(ent, sai) for ent in entradas for sai in saidas]

    print(
        f"[CONTRATO] Saídas compatíveis: {len(saidas)} | "
        f"Combinações a executar: {len(pares_a_rodar)}"
    )
    pares_ok = []  # list of dict resultados

    total = len(pares_a_rodar)
    print(f"[ETAPA 2/2] Executando {total} combinação(ões)...")
    n = 0
    for ent, sai in pares_a_rodar:
        n += 1
        rotulo = f"{ent.nome} × {sai.nome}"
        print(f"  [{n}/{total}] {rotulo}...", end="", flush=True)
        try:
            trades = executar_jogo(
                candles, rows, ent, dias_avaliacao, avaliar_saida=sai.avaliar_saida
            )
        except (KeyError, TypeError, ValueError, AttributeError) as erro:
            incompatíveis.append((rotulo, f"{type(erro).__name__}: {erro}"))
            print(" (INCOMPATIVEL)")
            continue
        res = _montar_resultado_par(
            ent.nome, sai.nome, trades, dias,
            entrada_titular=ent.titular, saida_titular=sai.titular,
        )
        pares_ok.append(res)
        print(f" ok | {len(trades)} ops | {_moeda(res['resultado'])}")

    rank_entrada: list[dict] = []
    rank_saida: list[dict] = []
    rank_cruzado: list[dict] = []
    disponibilidade = {"longo": False, "mensal": False, "diario": False, "confianca": "—"}

    # ----- Ranking ENTRADA (modo E) -----
    if modo == "E":
        for r in pares_ok:
            item = dict(r)
            item["estrategia"] = r["entrada"]
            item["titular"] = r["titular_entrada"]
            rank_entrada.append(item)
        disponibilidade = aplicar_pontuacao_multitemporal(rank_entrada, dias)
        for r in rank_entrada:
            if not disponibilidade["longo"]:
                r["nota_longo"] = float("nan")
            if not disponibilidade["mensal"]:
                r["nota_mensal"] = float("nan")
        rank_entrada.sort(
            key=lambda r: (
                r["acumulado"],
                r["resultado"],
                r["drawdown"],
                r["dias_operados"],
                -math.inf if math.isnan(r.get("pontuacao_robusta", float("nan"))) else r["pontuacao_robusta"],
            ),
            reverse=True,
        )
        for i, r in enumerate(rank_entrada, 1):
            r["pos"] = i
        titulo_entrada = (
            f"RANKING ENTRADA {VERSAO_CLASSIFICACAO} (motor {cfg.VERSAO}; "
            f"saída titular: {saida_titular.nome})"
        )
        with _capturar_e_imprimir() as _buf_entrada:
            _imprimir_ranking_simples(
                titulo_entrada,
                rank_entrada,
                chave_nome="estrategia",
            )
        _registrar_historico(titulo_entrada, _buf_entrada.getvalue())

    # ----- Ranking SAÍDA (modo S) -----
    if modo == "S":
        for r in pares_ok:
            item = dict(r)
            item["estrategia"] = r["saida"]
            item["titular"] = r["titular_saida"]
            rank_saida.append(item)
        disponibilidade = aplicar_pontuacao_multitemporal(rank_saida, dias)
        for r in rank_saida:
            if not disponibilidade["longo"]:
                r["nota_longo"] = float("nan")
            if not disponibilidade["mensal"]:
                r["nota_mensal"] = float("nan")
        rank_saida.sort(
            key=lambda r: (
                r["acumulado"],
                r["resultado"],
                r["drawdown"],
                r["dias_operados"],
                -math.inf if math.isnan(r.get("pontuacao_robusta", float("nan"))) else r["pontuacao_robusta"],
            ),
            reverse=True,
        )
        for i, r in enumerate(rank_saida, 1):
            r["pos"] = i
        titulo_saida = (
            f"RANKING SAÍDA {VERSAO_CLASSIFICACAO} (motor {cfg.VERSAO}; "
            f"entrada titular: {entrada_titular.nome})"
        )
        with _capturar_e_imprimir() as _buf_saida:
            _imprimir_ranking_simples(
                titulo_saida,
                rank_saida,
                chave_nome="estrategia",
            )
        _registrar_historico(titulo_saida, _buf_saida.getvalue())

    # ----- Ranking CRUZADO (modo C) -----
    if modo == "C":
        rank_cruzado = [dict(r) for r in pares_ok]
        rank_cruzado.sort(
            key=lambda r: (
                r["acumulado"],
                r["resultado"],
                r["drawdown"],
                r["dias_operados"],
            ),
            reverse=True,
        )
        for i, r in enumerate(rank_cruzado, 1):
            r["pos"] = i
        titulo_cruzado = f"RANKING CRUZADO {VERSAO_CLASSIFICACAO} (motor {cfg.VERSAO})"
        with _capturar_e_imprimir() as _buf_cruzado:
            _imprimir_ranking_cruzado(rank_cruzado, total_pregoes=len(dias))
        _registrar_historico(titulo_cruzado, _buf_cruzado.getvalue())

    if modo in ("E", "S"):
        ativos = [n for n in ("longo", "mensal", "diario") if disponibilidade.get(n)]
        rotulo_h = "entrada" if modo == "E" else "saída"
        print(f"\nHorizontes (ranking {rotulo_h}): {', '.join(ativos) or '—'} | "
              f"confiança: {disponibilidade['confianca']}")
        if disponibilidade["confianca"] in {"MUITO BAIXA", "BAIXA"}:
            print("Classificação provisória: histórico insuficiente para promover titular.")

    pasta_logs = Path(cfg.PASTA_LOGS_AUDITORIA)
    pasta_logs.mkdir(parents=True, exist_ok=True)

    def gravar(nome, linhas):
        if not linhas:
            return None
        saida = pasta_logs / (
            f"{nome}_{VERSAO_CLASSIFICACAO.lower()}_motor_{cfg.VERSAO.lower()}.csv"
        )
        campos = list(linhas[0].keys())
        with saida.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=campos, delimiter=";")
            w.writeheader()
            w.writerows(linhas)
        return saida

    relatorios = []
    if modo == "E":
        relatorios.append(gravar("classificacao_entrada", rank_entrada))
    elif modo == "S":
        relatorios.append(gravar("classificacao_saida", rank_saida))
    else:
        relatorios.append(gravar("classificacao_cruzada", rank_cruzado))
    print("\nRelatórios:")
    for p in relatorios:
        if p:
            print(f"  {p.resolve()}")
    print("Limitação: OHLC 15min não revela ordem intrabar nem preço exato das 18:20.")
    if incompatíveis:
        print("\nCartuchos/combinações INCOMPATIVEIS:")
        for nome, erro in incompatíveis:
            print(f"- {nome} (INCOMPATIVEL): {erro}")
    return {
        "modo": modo,
        "entrada": rank_entrada,
        "saida": rank_saida,
        "cruzado": rank_cruzado,
    }


if __name__ == "__main__":
    executar()

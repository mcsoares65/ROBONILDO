"""
ROBONILDO - principal.py
Versao exibida dinamicamente por configuracao.VERSAO

Loop principal do dia de pregao. Le preco continuamente (via leitor_dde, ainda a
construir), monta candles de 15min, aplica a regra MA_v2, gerencia risco e registra
tudo. ENVIAR_ORDENS = False nesta fase - nunca envia ordem real.
"""

import time
import csv
import random
import threading
import queue
import frases_narracao as frases
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

try:
    import colorama
    colorama.init()
    COR_ALTA = colorama.Fore.LIGHTGREEN_EX
    COR_BAIXA = colorama.Fore.RED
    COR_RESET = colorama.Style.RESET_ALL
    COR_PRONTO = colorama.Fore.LIGHTMAGENTA_EX   # dentro da faixa - sinal valido
    COR_QUENTE = colorama.Fore.LIGHTYELLOW_EX    # chegando perto
    COR_MORNO = colorama.Fore.LIGHTWHITE_EX      # distancia moderada
    COR_FRIO = colorama.Fore.LIGHTBLACK_EX       # ainda longe
    COR_NARRADOR = colorama.Fore.LIGHTCYAN_EX    # azul celeste/turquesa - texto do narrador
except ImportError:
    print("[AVISO] Biblioteca 'colorama' nao instalada (pip install colorama) - "
          "tendencia sera exibida sem cor.")
    COR_ALTA = COR_BAIXA = COR_RESET = ""
    COR_PRONTO = COR_QUENTE = COR_MORNO = COR_FRIO = COR_NARRADOR = ""


def cor_termometro(faltam: float) -> str:
    """
    'Termometro' visual para a distancia ate o gatilho de entrada:
      faltam <= 0   -> ja esta dentro da faixa (o proximo fechamento pode disparar)
      0 < faltam <= 20  -> quente, chegando perto
      20 < faltam <= 60 -> morno, distancia moderada
      faltam > 60   -> frio, ainda longe
    """
    if faltam <= 0:
        return COR_PRONTO
    elif faltam <= 20:
        return COR_QUENTE
    elif faltam <= 60:
        return COR_MORNO
    else:
        return COR_FRIO


def _quadro_proximidade(progresso: float, segundos_restantes: float,
                        duracao_total_segundos: float) -> str:
    """
    Radar de maturação da estratégia prioritária. A cor representa condições
    técnicas confirmadas, não apenas o tempo restante do candle: roxo em 0%,
    passando por magenta/amarelo/verde, até verde-limão em 100%.
    """
    quadrado = "■"
    if not COR_RESET:  # colorama indisponivel - fallback sem cor
        return quadrado

    paleta = [93, 129, 165, 201, 207, 220, 226, 154, 118, 82, 46]
    progresso = max(0.0, min(1.0, float(progresso)))
    indice = min(len(paleta) - 1, round(progresso * (len(paleta) - 1)))
    codigo_cor = paleta[indice]
    return f"\x1b[38;5;{codigo_cor}m{quadrado}{COR_RESET}"


def _resultado_liquido_reais(posicao, preco_atual: float) -> float:
    """
    Resultado em reais se a posicao fosse fechada AGORA, ja descontando o
    custo estimado da operacao - o MESMO valor que aparece no terminal
    ("Res:") e que motor.fechar_posicao() usa de verdade ao fechar.
    Fonte unica: cor do quadrado, narracao periodica e terminal usam esta
    mesma funcao, nunca recalculam o resultado cada um a sua maneira.
    """
    direcao = 1 if posicao.lado == "COMPRA" else -1
    resultado_pts = (preco_atual - posicao.entrada) * direcao
    return resultado_pts * cfg.VALOR_PONTO_REAIS - cfg.CUSTO_TOTAL_ESTIMADO_POR_OPERACAO_REAIS


def _progresso_posicao(posicao, preco_atual: float) -> float:
    """
    Progresso da posicao aberta, de -1.0 (no stop) a +1.0 (no alvo), em
    termos de RESULTADO LIQUIDO (ja descontado o custo) - nao de pontos
    brutos. Por isso 0.0 nao fica exatamente no preco de entrada; fica um
    pouco alem dele (o suficiente para cobrir o custo). Qualquer lucro
    liquido real (por menor que seja) ja da progresso > 0, e qualquer
    prejuizo liquido real ja da progresso < 0 - sem zona neutra artificial.
    """
    resultado_liquido = _resultado_liquido_reais(posicao, preco_atual)
    direcao = 1 if posicao.lado == "COMPRA" else -1

    # Regra 1 v10: o motor nao calcula mais stop/alvo - quem define e o
    # cartucho de saida titular, e ele pode legitimamente nunca definir um
    # dos dois (ou os dois). Sem o nivel de referencia, nao ha "caminho"
    # pra medir - devolve progresso neutro em vez de quebrar tentando
    # subtrair None.
    if resultado_liquido >= 0:
        if posicao.alvo is None:
            return 0.0
        resultado_liquido_no_alvo = (
            (posicao.alvo - posicao.entrada) * direcao * cfg.VALOR_PONTO_REAIS
            - cfg.CUSTO_TOTAL_ESTIMADO_POR_OPERACAO_REAIS
        )
        return min(1.0, resultado_liquido / resultado_liquido_no_alvo) if resultado_liquido_no_alvo > 0 else 0.0
    else:
        if posicao.stop is None:
            return 0.0
        resultado_liquido_no_stop = (
            (posicao.stop - posicao.entrada) * direcao * cfg.VALOR_PONTO_REAIS
            - cfg.CUSTO_TOTAL_ESTIMADO_POR_OPERACAO_REAIS
        )
        return -min(1.0, resultado_liquido / resultado_liquido_no_stop) if resultado_liquido_no_stop < 0 else 0.0


def _interpolar_cor(cor_a, cor_b, fracao: float):
    """Interpolacao linear continua entre duas cores RGB - sem degraus."""
    fracao = max(0.0, min(1.0, fracao))
    return tuple(round(a + (b - a) * fracao) for a, b in zip(cor_a, cor_b))


_BRANCO = (255, 255, 255)
_LIMA = (163, 255, 30)      # verde-limao, progresso = +1.0 (alvo)
_ROXO = (147, 51, 234)      # roxo, progresso = -1.0 (stop)


def _quadro_resultado(posicao, preco_atual: float) -> str:
    """
    Marcador da posicao: BRANCO (neutro) quando o resultado liquido esta em
    zero, e varia de forma CONTINUA (interpolacao RGB real, sem degraus de
    paleta) para roxo conforme o prejuizo liquido cresce em direcao ao stop,
    ou para verde-limao conforme o lucro liquido cresce em direcao ao alvo.
    """
    quadrado = "■"
    progresso = _progresso_posicao(posicao, preco_atual)

    if not COR_RESET:
        if progresso > 0:
            return "[+]"
        if progresso < 0:
            return "[-]"
        return "[0]"

    if progresso >= 0:
        r, g, b = _interpolar_cor(_BRANCO, _LIMA, progresso)
    else:
        r, g, b = _interpolar_cor(_BRANCO, _ROXO, abs(progresso))

    return f"\x1b[38;2;{r};{g};{b}m{quadrado}{COR_RESET}"


def _texto_indicadores(row) -> str:
    """Linha compacta com os indicadores usados pela estrategia titular."""
    if not row:
        return "Ind: aquecendo"

    def numero(nome, casas=1):
        valor = row.get(nome)
        if valor is None or valor != valor:
            return "-"
        return f"{valor:.{casas}f}"

    macd = row.get("macd")
    macd_signal = row.get("macd_signal")
    delta_macd = None
    if (macd is not None and macd == macd and macd_signal is not None
            and macd_signal == macd_signal):
        delta_macd = macd - macd_signal
    delta_texto = "-" if delta_macd is None else f"{delta_macd:.1f}"

    return (
        f"M21:{numero('MA21', 0)} M50:{numero('MA50', 0)} "
        f"D21:{numero('distancia_ma21', 0)} | RSI:{numero('rsi', 0)} "
        f"STO:{numero('stoch', 0)} ATR:{numero('atr_relativo', 2)} "
        f"MD:{delta_texto}"
    )


def _inicio_proximo_bloco(horario: datetime, minutos: int) -> datetime:
    """Horario de fechamento do candle atual (inicio do proximo bloco de N minutos)."""
    from datetime import timedelta
    bloco_atual = (horario.minute // minutos) * minutos
    inicio_atual = horario.replace(minute=bloco_atual, second=0, microsecond=0)
    return inicio_atual + timedelta(minutes=minutos)


def _tocar_beep():
    """Toca um beep sonoro de alerta - so funciona no Windows (winsound e nativo la)."""
    try:
        import winsound
        winsound.Beep(1200, 300)  # 1200 Hz, 300 ms
    except ImportError:
        print("\a", end="", flush=True)  # fallback: beep do proprio terminal (ASCII bell)


_narrador_local = threading.local()  # um objeto de voz POR THREAD - COM (usado pelo
                                      # SAPI) exige inicializacao por thread, e
                                      # compartilhar o mesmo objeto entre threads
                                      # diferentes (ex: a thread de noticias) e inseguro


def narrar(texto: str):
    """
    Fala em voz alta um fato JA CALCULADO pelo robo (ex: 'posicao aberta',
    'cinco', 'quatro'...) - usa o motor de texto-pra-fala nativo do Windows
    (SAPI), sem instalar nada novo.

    IMPORTANTE: isso NAO e o robo "interpretando o mercado" nem uma IA
    comentando - e so tornar audivel um dado que o codigo ja decidiu de forma
    deterministica. Diferente do modulo de narracao do projeto anterior
    (vozes de agentes de IA), que foi deliberadamente descartado por falta de
    confiabilidade.
    """
    print(f"{COR_NARRADOR}[NARRADOR] \"{texto}\"{COR_RESET}")
    try:
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()  # exige inicializacao POR THREAD - seguro
                                   # chamar de novo se a thread atual ja
                                   # inicializou (so incrementa um contador)
        if not hasattr(_narrador_local, "voz"):
            _narrador_local.voz = win32com.client.Dispatch("SAPI.SpVoice")
        SVSFlagAsync = 1  # nao bloqueia o robo esperando a fala terminar
        _narrador_local.voz.Speak(texto, SVSFlagAsync)
    except Exception as e:
        print(f"[NARRADOR] Falha ao falar '{texto}': {e}")


HEARTBEAT_SEGUNDOS = 5   # tick a tick, como estava antes do ajuste de poluicao visual.
                          # CONFIRMADO em teste (18/09/2026): a leitura real do DDE
                          # acontece a cada ~2s, normalmente - esse numero so controla
                          # o que aparece impresso na tela, nao a frequencia real de
                          # leitura nem a velocidade de reacao do robo.

import configuracao as cfg
print("=" * 60)
print(f"ROBONILDO [{cfg.VERSAO}]")
print("=" * 60)
import importlib
import importlib.util
from pathlib import Path as _Path
from motor import MotorRobonildo, Candle, media_movel
import motor as _motor_mod
print(f"[DIAGNOSTICO] motor.py carregado de: {_motor_mod.__file__}")
print(f"[DIAGNOSTICO] motor calcula RSI/ATR? "
      f"{'sim' if hasattr(_motor_mod, 'rsi_wilder') else 'NÃO - versão desatualizada!'}")

# Descobre sozinho qual é o cartucho oficial: o ÚNICO arquivo .py dentro de
# estrategia/. Não depende de configuração com nome de arquivo -
# trocar a estrategia e so trocar QUAL arquivo esta dentro dessa pasta.
# estrategia/entrada/ e estrategia/saida/. Nao depende de configuracao com
# nome de arquivo - trocar a estrategia e so trocar QUAL arquivo esta dentro
# de cada pasta. Os dois cartuchos sao independentes: a saida nunca sabe
# qual arquivo esta rodando do lado da entrada (decisao do conselho,
# rodada 3 - evita acoplamento oculto entre os dois).


def _descobrir_cartucho(nome_pasta: str, funcao_obrigatoria: str):
    """
    Acha exatamente 1 arquivo .py em estrategia/<nome_pasta>/titular/
    (ignora arquivos que comecam com "_"). Confirma a funcao obrigatoria.

    Estrutura V431:
      estrategia/entrada/titular/  → cartucho de entrada de producao
      estrategia/saida/titular/    → cartucho de saida de producao
    Candidatas de ranking ficam na raiz do slot (fora de titular/) e nao
    sao carregadas aqui — so no classificacao.py.
    """
    pasta = _Path(__file__).parent / "estrategia" / nome_pasta / "titular"
    candidatos = [a for a in sorted(pasta.glob("*.py")) if not a.stem.startswith("_")]
    if len(candidatos) != 1:
        raise RuntimeError(
            f"A pasta 'estrategia/{nome_pasta}/titular/' deve conter exatamente 1 "
            f"arquivo de cartucho; foram encontrados {len(candidatos)}: "
            f"{[a.name for a in candidatos]}"
        )
    nome = candidatos[0].stem
    # Import por caminho de arquivo — evita depender de estrategia/ ser pacote
    # com __init__ em todas as subpastas (titular/ pode ser so uma pasta de arquivos).
    spec = importlib.util.spec_from_file_location(
        f"robonildo_{nome_pasta}_titular_{nome}",
        candidatos[0],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Nao foi possivel importar {candidatos[0]}")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    if not callable(getattr(modulo, funcao_obrigatoria, None)):
        raise RuntimeError(
            f"'{nome}.py' (em estrategia/{nome_pasta}/titular/) nao fornece "
            f"{funcao_obrigatoria}(...); cartucho invalido."
        )
    return nome, modulo


_nome_estrategia, _modulo_estrategia = _descobrir_cartucho("entrada", "gerar_sinal")
diagnosticar_sinal = getattr(_modulo_estrategia, "diagnosticar_sinal", None)
diagnosticar_oportunidades = getattr(_modulo_estrategia, "diagnosticar_oportunidades", None)
print(f"Cartucho de entrada: {_nome_estrategia}.py  [estrategia/entrada/titular/]")

_nome_saida, _modulo_saida = _descobrir_cartucho("saida", "avaliar_saida")
diagnosticar_saida = getattr(_modulo_saida, "diagnosticar_saida", None)
print(f"Cartucho de saída: {_nome_saida}.py  [estrategia/saida/titular/]")

from construtor_candle import ConstrutorCandle
from registrador import Registrador
from auditor_execucao import AuditorExecucao
from leitor_dde import LeitorDDE
import leitor_dde as _leitor_dde_mod  # so para acessar PREFIXO_REPLAY (constante de config)

# Nome do ativo a buscar na coluna A da aba DDE - definido em __main__ (pergunta
# Replay/Normal) ANTES de rodar() ser chamado. Ver localizar_ativo() em leitor_dde.py.
_NOME_ATIVO_DDE = cfg.ATIVO  # valor padrao (modo Normal) ate __main__ perguntar
_MODO_REPLAY = False          # idem - definido em __main__ pela mesma resposta REPLAY/NORMAL,
                               # NAO confundir com cfg.MODO_TESTE_REPLAY (variavel diferente,
                               # sobre limpeza de historico acumulado - fixa em False)
from executor_ordem import ExecutorOrdem
import email_notificacao


def carregar_historico_inicial(caminho_csv: str, referencia_tempo: datetime) -> List[Candle]:
    """
    Carrega candles de 15min ja fechados. PRIMEIRO tenta o arquivo persistente
    (cfg.CAMINHO_HISTORICO_PERSISTENTE), que o proprio robo vai alimentando a
    cada candle que fecha - assim, a exportacao manual do Profit so e necessaria
    UMA VEZ, no primeiro uso, para "dar a partida". Nas execucoes seguintes, o
    robo carrega o que ele mesmo ja acumulou, mesmo apos dias sem rodar (o gap
    de tempo entre candles nao afeta o calculo da media movel).

    referencia_tempo: horario do MERCADO (nao o relogio do sistema) usado para
    calcular o gap - essencial em replay, onde o relogio real do computador e
    completamente diferente da data simulada.
    """
    caminho_persistente = Path(cfg.CAMINHO_HISTORICO_PERSISTENTE)
    if caminho_persistente.exists():
        candles = _ler_csv_candles(caminho_persistente)
        candles = _remover_candles_futuros(candles, referencia_tempo)
        descartado_por_gap = False
        if candles:
            gap = referencia_tempo - candles[-1].horario
            if gap.total_seconds() > cfg.GAP_MAXIMO_HORAS_HISTORICO * 3600:
                print(f"[AVISO] O ultimo candle salvo e de {candles[-1].horario} - "
                      f"gap de {gap.total_seconds()/3600:.1f}h, acima do limite de "
                      f"{cfg.GAP_MAXIMO_HORAS_HISTORICO}h. Descartando historico "
                      f"antigo: misturar candles de cenarios de mercado tao "
                      f"distantes geraria uma media sem significado real.")
                candles = []
                descartado_por_gap = True
        if candles:
            print(f"Historico persistente carregado: {len(candles)} candles de "
                  f"'{caminho_persistente}' (acumulado pelo proprio robo).")
            return candles
        if not descartado_por_gap:
            print(f"Historico persistente vazio em '{caminho_persistente}'.")
        print("Buscando carga inicial a partir da exportacao manual do Profit "
              "(historico persistente indisponivel ou descartado).")
    else:
        print(f"[AVISO] Nenhum historico persistente encontrado ainda em "
              f"'{caminho_persistente}'. Fazendo carga inicial (unica vez) a partir "
              f"da exportacao manual do Profit: '{caminho_csv}'.")

    caminho = Path(caminho_csv)
    if not caminho.exists():
        print(f"[AVISO] Arquivo de historico '{caminho_csv}' tambem nao encontrado. "
              f"O robo vai iniciar sem historico previo e pode demorar ~2 dias "
              f"de pregao ate conseguir calcular a MA50 e gerar sinais.")
        return []

    candles = _ler_csv_candles(caminho)
    candles = _remover_candles_futuros(candles, referencia_tempo)
    print(f"Carga inicial (unica vez): {len(candles)} candles de '{caminho_csv}'.")
    _salvar_historico_persistente(candles, sobrescrever=True)
    return candles


def _remover_candles_futuros(candles: List[Candle], referencia_tempo: datetime) -> List[Candle]:
    """
    Descarta qualquer candle mais recente que o horario atual do mercado (replay
    ou ao vivo). Protege contra o robo usar dado que, no momento simulado, ainda
    nao deveria existir - viés de "olhar para o futuro" que invalidaria qualquer
    teste, mesmo que o arquivo exportado va alem da data sendo testada.
    """
    # O horario do CSV e o INICIO do periodo. Por exemplo, o candle 14:15
    # somente esta fechado a partir de 14:30. A regra anterior comparava apenas
    # o inicio e podia carregar o OHLC completo de um candle ainda em formacao
    # quando um Replay era repetido.
    duracao = timedelta(minutes=cfg.TIMEFRAME_MINUTOS)
    filtrados = [c for c in candles if c.horario + duracao <= referencia_tempo]
    descartados = len(candles) - len(filtrados)
    if descartados > 0:
        print(f"[AVISO] {descartados} candle(s) do arquivo de historico sao "
              f"posteriores ao horario atual do mercado ({referencia_tempo}) e "
              f"foram descartados - o arquivo exportado provavelmente cobre um "
              f"periodo alem da data sendo usada agora.")
    return filtrados


def _ler_csv_candles(caminho: Path) -> List[Candle]:
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
            candles.append(Candle(
                horario=horario,
                abertura=float(abertura.replace(",", ".")),
                maxima=float(maxima.replace(",", ".")),
                minima=float(minima.replace(",", ".")),
                fechamento=float(fechamento.replace(",", ".")),
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


def _salvar_historico_persistente(candles: List[Candle], sobrescrever: bool = False):
    """
    UPSERT atomico por horario: o candle recebido substitui a ocorrencia
    anterior do mesmo horario, sem criar duplicatas. A escrita acontece num
    arquivo temporario e so depois substitui o original; uma interrupcao no
    meio da gravacao preserva o arquivo anterior.
    """
    caminho = Path(cfg.CAMINHO_HISTORICO_PERSISTENTE)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    existentes = [] if sobrescrever or not caminho.exists() else _ler_csv_candles(caminho)
    por_horario = {c.horario: c for c in existentes}
    for candle in candles:
        por_horario[candle.horario] = candle

    consolidados = sorted(por_horario.values(), key=lambda c: c.horario)
    temporario = caminho.with_name(f"{caminho.name}.tmp")
    _noticias = None
    try:
        with open(temporario, "w", encoding="latin1") as f:
            for c in consolidados:
                f.write(f"{cfg.ATIVO};{c.horario.strftime('%d/%m/%Y')};"
                        f"{c.horario.strftime('%H:%M:%S')};{c.abertura:.2f};"
                        f"{c.maxima:.2f};{c.minima:.2f};{c.fechamento:.2f};0;0\n")
            f.flush()
        temporario.replace(caminho)
    finally:
        if temporario.exists():
            try:
                temporario.unlink()
            except OSError:
                pass


def rodar():
    construtor = ConstrutorCandle(minutos=cfg.TIMEFRAME_MINUTOS)
    registrador = Registrador(pasta_logs=cfg.PASTA_LOGS_AUDITORIA)
    auditor = AuditorExecucao(
        pasta_logs=cfg.PASTA_LOGS_AUDITORIA,
        habilitado=cfg.AUDITORIA_EXECUCAO_ATIVA,
    )
    executor = ExecutorOrdem()
    fila_noticias = queue.Queue()

    # Noticias de mercado - so informativo, narrado quando surge algo novo e
    # relevante. NUNCA entra na decisao de entrada/saida (ver aviso no topo
    # de noticias.py) - falha silenciosamente se a rede/RSS der problema,
    # sem derrubar o robo.
    try:
        from noticias import NoticiasMercado
        _noticias = NoticiasMercado(callback_narracao=fila_noticias.put)
        _noticias.iniciar()
        print("[NOTICIAS] Monitoramento de noticias iniciado em segundo plano.")
    except Exception as e:
        print(f"[NOTICIAS] Nao foi possivel iniciar o modulo de noticias: {e}")

    if cfg.MODO_TESTE_REPLAY:
        caminho_persistente = Path(cfg.CAMINHO_HISTORICO_PERSISTENTE)
        if caminho_persistente.exists():
            caminho_persistente.unlink()
            print(f"[MODO_TESTE_REPLAY] Historico acumulado anterior apagado "
                  f"({caminho_persistente}) - comecando limpo para este teste.")
        # NAO apaga mais o estado_risco.json automaticamente aqui - isso
        # destruiria o rastro de uma posicao real ainda aberta se o script
        # precisasse reiniciar (queda de energia, erro, etc.), tanto em teste
        # quanto em operacao real. O motor ja sabe resetar sozinho
        # quando o dia de MERCADO muda (nao o relogio do computador) - isso
        # e suficiente e mais seguro que apagar tudo as cegas.

    leitor = LeitorDDE()
    leitor.conectar()
    leitor.localizar_ativo(_NOME_ATIVO_DDE)

    # pega uma primeira leitura do horario do MERCADO antes de criar o gestor de
    # risco e decidir sobre o historico - necessario para os dois calculos de
    # "que dia e hoje" fazerem sentido (comparar tempo de mercado com tempo de
    # mercado, nao com o relogio do computador)
    print("Aguardando primeira leitura valida do horario de mercado...")
    horario_inicial = None
    while horario_inicial is None:
        candidato = leitor.ler_horario_mercado()
        if candidato is not None:
            # sanidade: horario de pregao nunca e exatamente meia-noite - uma
            # leitura assim e quase certamente lixo (celula do DDE ainda nao
            # atualizada, resquicio de sessao anterior). Descartar e tentar de
            # novo, em vez de usar como referencia e corromper o carregamento
            # do historico (ja aconteceu: filtrou candles do proprio dia como
            # "futuro" por causa disso).
            if candidato.hour == 0 and candidato.minute == 0 and candidato.second == 0:
                print(f"[AVISO] Leitura inicial suspeita ({candidato}) - meia-noite "
                      f"nao e horario de pregao real. Descartando e tentando de novo.")
            else:
                horario_inicial = candidato
        if horario_inicial is None:
            time.sleep(1)
    print(f"Horario de mercado inicial: {horario_inicial}")

    gestor = MotorRobonildo(
        gerar_sinal=_modulo_estrategia.gerar_sinal,
        arquivo_estado=cfg.CAMINHO_ESTADO_RISCO,
        horario_mercado_inicial=horario_inicial,
        avaliar_saida=_modulo_saida.avaliar_saida,
        diagnosticar_oportunidades=diagnosticar_oportunidades,
    )
    if gestor.posicao_aberta:
        pos = gestor.posicao_aberta
        print(f"[AVISO] Posicao aberta RECUPERADA de uma sessao anterior (mesmo dia "
              f"de mercado): {pos.lado} @ {pos.entrada} | Stop: {pos.stop} | "
              f"Alvo: {pos.alvo} - retomando o monitoramento normalmente.")

    historico_candles: List[Candle] = carregar_historico_inicial(
        cfg.CAMINHO_HISTORICO_INICIAL, referencia_tempo=horario_inicial
    )

    # V458: a reconciliacao de OHLC no Replay foi REMOVIDA. Ela substituia o
    # OHLC amostrado pelo DDE pelo OHLC consolidado do arquivo - um artificio
    # que existia so no Replay e que, por isso, fazia o Replay produzir um
    # resultado que o mercado ao vivo nao pode reproduzir. Replay e o ensaio
    # geral da operacao real: agora ele usa exatamente a mesma fonte de preco
    # que a operacao real, candles amostrados do DDE a cada 2 segundos.
    # Ver conselho/2026-09-30-T.txt.

    if cfg.ENVIAR_ORDENS:
        aviso_ordens = "ORDENS REAIS SERAO ENVIADAS ao Profit (ALT+C/V/Z)."
    else:
        aviso_ordens = "Modo somente alerta/registro - nenhuma ordem sera enviada."
    print(f"ROBONILDO [{cfg.VERSAO}] iniciado. ENVIAR_ORDENS={cfg.ENVIAR_ORDENS} - {aviso_ordens}")

    ultimo_heartbeat = datetime.now()
    ultimo_candle_narracao_periodica = None  # evita repetir a narracao de acompanhamento no mesmo candle
    ultima_expectativa_narrada = None  # (candle, porta, lado), evita repetição da explicação
    ultima_expectativa_perdida = None  # evita repetir a perda da mesma expectativa
    ultima_prioridade_radar_narrada = None  # (candle, estratégia, lado, faixa de 10%)
    radar_100_chave = None       # oportunidade que permanece continuamente em 100%
    radar_100_desde = None       # relogio real; mede estabilidade sem depender do DDE
    ultima_saida_especulativa_narrada = None  # (candle, horario_entrada), evita repetir o
                                                # aviso de "saida se aproximando" no mesmo candle
    ultimo_candle_beep = None          # um único alerta sonoro perto do fechamento
    mercado_encerrado_avisado = None   # guarda a data (string) do dia ja avisado como encerrado
    aguardando_abertura_avisado = None  # guarda a data (string) do dia ja avisado como "bom dia,
                                         # aguardando abertura" - evita repetir a cada ciclo
    # Paridade com o motor: se uma posição for encerrada durante um candle,
    # o backtest não permite reentrada usando o fechamento desse mesmo candle.
    saida_desde_ultimo_fechamento = False

    while True:
        agora_real = datetime.now()
        preco = leitor.ler_preco()
        agora = leitor.ler_horario_mercado()  # hora do MERCADO (replay ou ao vivo),
                                               # nao do relogio do computador

        if preco is None or agora is None:
            time.sleep(2)
            continue  # instabilidade pontual do DDE - pula este ciclo, tenta de novo

        # ---------- DDE ainda nao atualizou para hoje (antes do leilao abrir) ----------
        # O campo de horario do DDE pode continuar mostrando o ultimo tick do
        # PREGAO ANTERIOR ate o leilao de abertura de hoje gerar o primeiro tick
        # novo. Comparar so a HORA (como o encerramento abaixo faz) confundiria
        # "18:24 de ontem" com "depois das 18:20 de hoje" - confirmado em
        # producao as 08:34 de 23/09/2026, o robo emitiu "Mercado encerrado por
        # hoje" usando um horario de mercado que na verdade era de ontem.
        # Comparando a DATA (nao so a hora) contra o relogio real do computador
        # detecta essa situacao e evita agir sobre dado velho.
        if not _MODO_REPLAY and agora.date() < agora_real.date():
            data_hoje_real = agora_real.strftime("%Y-%m-%d")
            if aguardando_abertura_avisado != data_hoje_real:
                print(f"[{agora_real.strftime('%H:%M:%S')}] Bom dia! Aguardando abertura "
                      f"do mercado (DDE ainda mostra o ultimo horario de ontem, "
                      f"{agora.strftime('%d/%m %H:%M:%S')}).")
                narrar("Bom dia! Aguardando abertura do mercado.")
                aguardando_abertura_avisado = data_hoje_real
            time.sleep(5)
            continue

        # ---------- Mercado encerrado: uma despedida e silencio total ----------
        # Mesma correcao do motor.verificar_corte_final: cfg.HORARIO_LIMITE_ABSOLUTO
        # tem segundos ("18:20:58") de proposito - comparar so por minuto atrasava
        # este aviso em quase 1 minuto e 2 segundos.
        if gestor.posicao_aberta is None and agora.strftime("%H:%M:%S") >= cfg.HORARIO_LIMITE_ABSOLUTO:
            data_hoje = agora.strftime("%Y-%m-%d")
            if mercado_encerrado_avisado != data_hoje:
                print(f"[{agora.strftime('%H:%M:%S')}] Mercado encerrado por hoje "
                      f"({cfg.HORARIO_LIMITE_ABSOLUTO}). Sem posição aberta.")
                narrar("Mercado encerrado por hoje. Até o próximo pregão.")
                if _noticias is not None:
                    _noticias.pausar()
                mercado_encerrado_avisado = data_hoje
            time.sleep(300)
            continue

        # Ao detectar um novo pregão, reativa o painel de notícias.
        if _noticias is not None:
            _noticias.retomar()

        # ---------- Prova real contra a tela do Profit ----------
        avisos_integridade = leitor.verificar_integridade(preco, agora, modo_replay=_MODO_REPLAY)
        for aviso in avisos_integridade:
            print(f"[{agora.strftime('%H:%M:%S')}] [INTEGRIDADE DDE] {aviso}")
            narrar(aviso)
        if leitor.checkpoint_devido():
            narrar(f"Checagem de rotina: preço lido é {preco:.0f}. Confira na tela do Profit.")
            leitor.marcar_checkpoint_feito()

        # ---------- Calculo de tendencia/faixa a cada iteracao (nao so no heartbeat) ----------
        # o beep de alerta precisa ser verificado com frequencia independente de
        # quao espacado esta o print do heartbeat (HEARTBEAT_SEGUNDOS pode ser
        # aumentado no futuro, e isso nao pode fazer o robo "pular" a janela do beep)
        # segundos_restantes e calculado SEMPRE (com ou sem posicao aberta) - e so
        # aritmetica de horario, nao depende de sinal - usado tanto para o beep de
        # entrada quanto para a narracao periodica (10s antes do fechamento)
        proximo_fechamento = _inicio_proximo_bloco(agora, cfg.TIMEFRAME_MINUTOS)
        segundos_restantes = (proximo_fechamento - agora).total_seconds()
        candle_horario_atual = proximo_fechamento - timedelta(minutes=cfg.TIMEFRAME_MINUTOS)

        dentro_da_faixa = False
        tendencia = None
        sinal_especulativo = None
        diagnostico = None
        radar = []
        oportunidade_prioritaria = None
        progresso_radar = 0.0
        candle_atual = construtor.candle_em_formacao()
        candles_para_ma = historico_candles + ([candle_atual] if candle_atual else [])
        ma21 = media_movel(candles_para_ma, cfg.MA_RAPIDA)
        ma50 = media_movel(candles_para_ma, cfg.MA_LENTA)
        row_indicadores = (gestor.construir_row(candles_para_ma)
                           if candle_atual is not None else None)
        radar = gestor.radar_oportunidades(row_indicadores)
        if radar:
            oportunidade_prioritaria = radar[0]
            progresso_radar = oportunidade_prioritaria["progresso"]
        if oportunidade_prioritaria and progresso_radar >= 1.0:
            chave_100_atual = (
                candle_atual.horario if candle_atual is not None else None,
                oportunidade_prioritaria.get("estrategia"),
                oportunidade_prioritaria.get("direcao"),
            )
            if radar_100_chave != chave_100_atual:
                radar_100_chave = chave_100_atual
                radar_100_desde = agora_real
        else:
            radar_100_chave = None
            radar_100_desde = None
        if ma21 is not None and ma50 is not None and candle_atual is not None:
            tendencia = "ALTA" if ma21 > ma50 else "BAIXA"

            if not gestor.posicao_aberta:
                # ---------- "Prestes a disparar": chama a estrategia REAL, de forma
                # especulativa, no candle ainda em formacao - GENERICO para qualquer
                # estrategia (nativa ou vinda do laboratorio via ponte), nao mais uma
                # reimplementacao hardcoded de "toque na MA21 + estocastico" (que so
                # cobria a Porta 1 da Manus_4_Portas_V11 - Portas 2/3/4 disparariam
                # sem NENHUM aviso sonoro antes, e o contador podia contar para um
                # sinal que a estrategia real nem ia aceitar). Chamar avaliar_candle()
                # de verdade garante que a narracao NUNCA diverge da decisao real,
                # para qualquer estrategia presente ou futura.
                sinal_especulativo = gestor.avaliar_candle(candles_para_ma)
                dentro_da_faixa = sinal_especulativo is not None
                if dentro_da_faixa:
                    tendencia = "ALTA" if sinal_especulativo.lado == "COMPRA" else "BAIXA"

                diagnostico = (diagnosticar_sinal(row_indicadores)
                               if diagnosticar_sinal is not None else None)
                if dentro_da_faixa:
                    porta = diagnostico.get("porta") if diagnostico else None
                    lado = sinal_especulativo.lado
                    chave_expectativa = (candle_atual.horario, porta, lado)
                    if ultima_expectativa_narrada != chave_expectativa:
                        explicacao = (
                            diagnostico["explicacao"] if diagnostico else
                            f"A estratégia identificou uma expectativa de "
                            f"{lado.lower()} no fechamento do candle em formação."
                        )
                        # Se a estrategia expuser total_portas (opcional), deixa
                        # explicito QUAL das portas foi - nao e um funil
                        # sequencial (so uma porta dispara por candle), so
                        # identifica a porta entre as possiveis.
                        total_portas = diagnostico.get("total_portas") if diagnostico else None
                        if porta and total_portas:
                            explicacao = f"{explicacao} (porta {porta} de {total_portas})"
                        # O candle em formacao fecha em horario + TIMEFRAME. Dizer
                        # so "no fechamento" gera leitura ambigua: logo apos um
                        # [CANDLE FECHADO] o operador le as duas frases em sequencia
                        # ("nenhum sinal confirmado" + "sera disparada no
                        # fechamento") e entende que a ordem deveria ter saido
                        # AGORA, quando ela se refere ao fechamento SEGUINTE.
                        # Nomear o horario elimina a ambiguidade.
                        fechamento_previsto = (
                            candle_atual.horario + timedelta(minutes=cfg.TIMEFRAME_MINUTOS)
                        ).strftime("%H:%M")
                        explicacao = (
                            f"{explicacao} Se confirmado no fechamento das "
                            f"{fechamento_previsto}, a ordem será disparada."
                        )
                        print(f"[CENÁRIO EM FORMAÇÃO] {explicacao}")
                        narrar(explicacao)
                        ultima_expectativa_narrada = chave_expectativa
                        ultima_expectativa_perdida = None
                elif (ultima_expectativa_narrada is not None
                      and ultima_expectativa_narrada[0] == candle_atual.horario
                      and ultima_expectativa_perdida != ultima_expectativa_narrada):
                    _, porta_anterior, lado_anterior = ultima_expectativa_narrada
                    origem = f"Porta {porta_anterior}" if porta_anterior else "estratégia"
                    frase_perdida = (
                        f"A expectativa de {lado_anterior.lower()} da {origem} perdeu "
                        "confirmação durante a formação do candle. Nenhuma ordem será "
                        "enviada neste momento."
                    )
                    print(f"[CENÁRIO EM FORMAÇÃO] {frase_perdida}")
                    narrar(frase_perdida)
                    ultima_expectativa_perdida = ultima_expectativa_narrada

                # O radar avisa antes da confirmação completa. Só narra a partir
                # de 70% para não transformar pequenas oscilações em promessa de
                # entrada nem poluir o áudio a cada leitura DDE.
                if (not dentro_da_faixa and oportunidade_prioritaria
                        and progresso_radar >= 0.70):
                    faixa = int(progresso_radar * 10)
                    chave_radar = (
                        candle_atual.horario,
                        oportunidade_prioritaria.get("estrategia"),
                        oportunidade_prioritaria.get("direcao"),
                        faixa,
                    )
                    if ultima_prioridade_radar_narrada != chave_radar:
                        faltantes = oportunidade_prioritaria.get("faltantes") or []
                        proxima = faltantes[0] if faltantes else "confirmação no fechamento"
                        explicacao = (
                            f"A estratégia {oportunidade_prioritaria['estrategia']} "
                            f"assumiu a prioridade para {oportunidade_prioritaria['direcao'].lower()}, "
                            f"com {oportunidade_prioritaria['confirmadas']} de "
                            f"{oportunidade_prioritaria['total']} condições. "
                            f"Ainda aguardamos {proxima}."
                        )
                        print(f"[RADAR] {explicacao}")
                        narrar(explicacao)
                        ultima_prioridade_radar_narrada = chave_radar
                        ultima_expectativa_perdida = None

                if (dentro_da_faixa and 0 < segundos_restantes <= cfg.BEEP_SEGUNDOS_ANTES
                        and ultimo_candle_beep != candle_atual.horario):
                    _tocar_beep()
                    ultimo_candle_beep = candle_atual.horario

            elif gestor.posicao_aberta:
                # ---------- "Saída se aproximando": mesma ideia da entrada, agora
                # do lado do cartucho de saida - chama avaliar_saida() de forma
                # especulativa, no candle ainda em formacao, usando o preco/hora
                # atuais. Se ela ja fecharia com o dado de agora, avisa ANTES do
                # candle fechar de verdade - mesmo espirito do "prestes a
                # disparar" da entrada: nunca diverge da decisao real, so
                # antecipa o aviso.
                posicao_atual = gestor.posicao_aberta
                direcao = 1 if posicao_atual.lado == "COMPRA" else -1
                resultado_especulativo = (row_indicadores["Fechamento"] - posicao_atual.entrada) * direcao
                posicao_especulativa = {
                    "lado": posicao_atual.lado,
                    "entrada": posicao_atual.entrada,
                    "candles_decorridos": posicao_atual.candles_decorridos + 1,
                    "maxima_desde_entrada": max(posicao_atual.maxima_desde_entrada, row_indicadores["Maximo"]),
                    "minima_desde_entrada": min(posicao_atual.minima_desde_entrada, row_indicadores["Minimo"]),
                    "resultado_flutuante_pts": resultado_especulativo,
                }
                try:
                    decisao_saida_especulativa = _modulo_saida.avaliar_saida(row_indicadores, posicao_especulativa)
                    # avaliar_saida() sempre retorna um dict (Regra 1 v10), mesmo
                    # quando não há fechamento (ex: {"fechar": False, ...}). Um dict
                    # não-vazio é truthy em Python, então bool(dict) daria sempre
                    # True aqui - o narrador avisaria "saída se aproximando" em
                    # TODO candle com posição aberta, e não só quando o cartucho
                    # realmente sinaliza fechamento. Por isso é obrigatório checar
                    # especificamente a chave "fechar".
                    saida_se_aproximando = (
                        isinstance(decisao_saida_especulativa, dict)
                        and bool(decisao_saida_especulativa.get("fechar", False))
                    )
                except Exception:
                    saida_se_aproximando = False

                chave_saida_especulativa = (candle_atual.horario, posicao_atual.horario_entrada)
                if saida_se_aproximando and ultima_saida_especulativa_narrada != chave_saida_especulativa:
                    explicacao_saida = None
                    if diagnosticar_saida is not None:
                        try:
                            explicacao_saida = diagnosticar_saida(row_indicadores, posicao_especulativa)
                        except Exception:
                            explicacao_saida = None
                    frase_saida = (
                        explicacao_saida if isinstance(explicacao_saida, str) else
                        "O cartucho de saída identificou uma condição de fechamento antecipado "
                        "se formando neste candle."
                    )
                    print(f"[CENÁRIO EM FORMAÇÃO] {frase_saida}")
                    narrar(frase_saida)
                    ultima_saida_especulativa_narrada = chave_saida_especulativa

        # ---------- Cenário visual antes do fechamento ----------
        # O candle ainda está em formação - o dado narrado aqui é uma leitura
        # do momento, não uma decisão (a decisão real só acontece no
        # fechamento do candle, via avaliar_candle/verificar_saida). A voz
        # relata o cenário como está agora, sabendo que pode mudar até o
        # fechamento.
        if (0 < segundos_restantes <= cfg.NARRACAO_ANTES_FECHAMENTO_SEGUNDOS
                and ultimo_candle_narracao_periodica != candle_horario_atual):
            if gestor.posicao_aberta:
                posicao = gestor.posicao_aberta
                resultado_reais = _resultado_liquido_reais(posicao, preco)
                lado_texto = "compra" if posicao.lado == "COMPRA" else "venda"

                # Regra 1 v10: o cartucho de saida pode legitimamente ainda
                # nao ter definido alvo (lucro) ou stop (prejuizo) - sem
                # nivel, nao ha "X% do caminho" pra narrar.
                if resultado_reais >= 0 and posicao.alvo is None:
                    frase = (
                        f"Posição de {lado_texto} aberta, com {abs(resultado_reais):.0f} "
                        "reais de lucro flutuante. O cartucho de saída ainda não "
                        "definiu um alvo para esta operação."
                    )
                elif resultado_reais < 0 and posicao.stop is None:
                    frase = (
                        f"Posição de {lado_texto} aberta, com {abs(resultado_reais):.0f} "
                        "reais de prejuízo flutuante. O cartucho de saída ainda não "
                        "definiu um stop para esta operação."
                    )
                else:
                    progresso = _progresso_posicao(posicao, preco)
                    if progresso >= 0:
                        percentual = progresso * 100
                        frase = (
                            f"Posição de {lado_texto} aberta, com {abs(resultado_reais):.0f} "
                            f"reais de lucro flutuante, {percentual:.0f} por cento do "
                            "caminho até o alvo."
                        )
                    else:
                        percentual = abs(progresso) * 100
                        frase = (
                            f"Posição de {lado_texto} aberta, com {abs(resultado_reais):.0f} "
                            f"reais de prejuízo flutuante, {percentual:.0f} por cento do "
                            "caminho até o stop."
                        )
                print(f"[CENÁRIO EM FORMAÇÃO] {frase}")
                narrar(frase)
            elif tendencia is not None and not radar:
                chave = (tendencia, "DENTRO" if dentro_da_faixa else "FORA")
                frase = frases.FRASES_PERIODICAS_SEM_POSICAO.get(chave)
                if frase:
                    print(f"[CENÁRIO EM FORMAÇÃO] {frase}")
                    narrar(frase)
            ultimo_candle_narracao_periodica = candle_horario_atual

        if (agora_real - ultimo_heartbeat).total_seconds() >= HEARTBEAT_SEGUNDOS:
            indicadores_texto = _texto_indicadores(row_indicadores)
            quadro = _quadro_proximidade(
                progresso_radar, segundos_restantes, cfg.TIMEFRAME_MINUTOS * 60
            )
            progresso_radar_pct = max(0.0, min(1.0, float(progresso_radar))) * 100
            if gestor.posicao_aberta:
                pos = gestor.posicao_aberta
                resultado_reais = _resultado_liquido_reais(pos, preco)
                if resultado_reais > 0:
                    cor_resultado = COR_ALTA
                elif resultado_reais < 0:
                    cor_resultado = COR_BAIXA
                else:
                    cor_resultado = ""
                resultado_colorido = (
                    f"{cor_resultado}{resultado_reais:+8.2f}{COR_RESET}"
                )
                if pos.lado == "COMPRA":
                    lado_colorido = f"\x1b[38;5;46m{'COMPRA':<6}{COR_RESET}"
                else:
                    lado_colorido = f"{COR_BAIXA}{'VENDA':<6}{COR_RESET}"
                quadro_posicao = _quadro_resultado(pos, preco)
                progresso_pct = abs(_progresso_posicao(pos, preco)) * 100
                alvo_txt = (f"Alvo {pos.alvo:6.0f} ({abs(pos.alvo - preco):4.0f})"
                            if pos.alvo is not None else "Alvo      - (   -)")
                stop_txt = (f"Stop {pos.stop:6.0f} ({abs(preco - pos.stop):4.0f})"
                            if pos.stop is not None else "Stop      - (   -)")
                print(f"[{agora.strftime('%H:%M:%S')}] {lado_colorido} | "
                      f"Ent {pos.entrada:6.0f} | Atual {preco:6.0f} | "
                      f"Res {resultado_colorido} | {alvo_txt} | {stop_txt} | "
                      f"{progresso_pct:3.0f}% {quadro_posicao}")
            else:
                if ma21 is not None and ma50 is not None and candle_atual is not None:
                    cor_tendencia = COR_ALTA if tendencia == "ALTA" else COR_BAIXA
                    tendencia_colorida = (
                        f"{cor_tendencia}{tendencia:<5}{COR_RESET}"
                    )
                    if oportunidade_prioritaria:
                        nome_radar = str(
                            oportunidade_prioritaria["estrategia"]
                        )
                        status_sinal = (
                            f"{COR_PRONTO}{nome_radar:<19}{COR_RESET}"
                        )
                        confirmacoes_radar = (
                            f"{oportunidade_prioritaria['confirmadas']}/"
                            f"{oportunidade_prioritaria['total']}"
                        )
                    else:
                        nome_radar = "EXPECTATIVA" if dentro_da_faixa else "espera"
                        status_sinal = (
                            f"{COR_PRONTO}{nome_radar:<19}{COR_RESET}"
                            if dentro_da_faixa else f"{nome_radar:<19}"
                        )
                        confirmacoes_radar = "-/-"

                    if oportunidade_prioritaria:
                        itens = oportunidade_prioritaria.get("faltantes") or []
                        faltante = str(itens[0]) if itens else "nenhuma"
                        detalhe_radar = str(
                            oportunidade_prioritaria.get("detalhe") or faltante
                        )
                    else:
                        faltante = "aguardando oportunidade"
                        detalhe_radar = faltante
                    if len(detalhe_radar) > 29:
                        detalhe_radar = detalhe_radar[:28] + "…"
                    sustentacao = ""
                    if radar_100_desde is not None and progresso_radar >= 1.0:
                        segundos_100 = max(0, int((agora_real - radar_100_desde).total_seconds()))
                        sustentacao = f" | há {segundos_100}s"
                    print(f"[{agora.strftime('%H:%M:%S')}] Preço {preco:6.0f} | "
                          f"{tendencia_colorida} | Radar {status_sinal} | "
                          f"{confirmacoes_radar:^3} | Falta {detalhe_radar:<29}"
                          f"{sustentacao}"
                          f" | {progresso_radar_pct:3.0f}% {quadro}")
                else:
                    print(f"[{agora.strftime('%H:%M:%S')}] Preço:{preco:.0f} | "
                          f"Aguardando indicadores")
            ultimo_heartbeat = agora_real


        # ---------- Checagem cruzada de posicao real (campo CAB) ----------
        # resolve o problema identificado no projeto anterior: "o controle de
        # posicao interno pode ficar diferente da posicao existente no Profit"
        contratos_reais = leitor.ler_contratos_abertos()
        estado_interno_tem_posicao = gestor.posicao_aberta is not None
        if contratos_reais is not None:
            estado_real_tem_posicao = contratos_reais != 0
            if estado_interno_tem_posicao != estado_real_tem_posicao:
                print(f"[{agora}] ALERTA CRITICO: divergencia entre estado interno "
                      f"(posicao={estado_interno_tem_posicao}) e posicao real via CAB "
                      f"(contratos={contratos_reais}). Intervencao manual necessaria.")
                # nao decide sozinho o que fazer - so alerta, dado o risco de piorar
                # a situacao agindo automaticamente sobre uma divergencia nao explicada

        candle_fechado = construtor.nova_leitura(preco, agora)

        # ---------- Gestao de posicao aberta (monitoramento continuo) ----------
        if gestor.posicao_aberta:
            # 1) stop/alvo verificados tick a tick - nao espera o candle fechar
            saida_continua = gestor.verificar_saida_continua(preco)
            if saida_continua:
                motivo, preco_saida = saida_continua
                posicao_antes = gestor.posicao_aberta
                ordem_ok = executor.encerrar_posicao()
                saida_teorica = (
                    posicao_antes.stop if motivo == "STOP"
                    else posicao_antes.alvo if motivo == "ALVO"
                    else preco_saida
                )
                auditor.registrar_saida(
                    horario=agora, posicao=posicao_antes, motivo=motivo,
                    saida_teorica=saida_teorica, saida_dde=preco,
                    ordem_enviada=(ordem_ok or not cfg.ENVIAR_ORDENS),
                    contratos_dde=contratos_reais,
                )
                if ordem_ok or not cfg.ENVIAR_ORDENS:
                    resultado_pts, msg = gestor.fechar_posicao(preco_saida, motivo)
                    leitor.escrever_banca_atual(gestor.banca_atual)
                    resultado_reais = resultado_pts * cfg.VALOR_PONTO_REAIS - cfg.CUSTO_TOTAL_ESTIMADO_POR_OPERACAO_REAIS
                    print(f"[{agora}] {msg}")
                    narrar(frases.FRASES_FECHAMENTO.get(motivo, frases.FRASE_FECHAMENTO_PADRAO_LUCRO if resultado_pts > 0 else frases.FRASE_FECHAMENTO_PADRAO_PREJUIZO))
                    registrador.registrar_operacao_fechada(
                        horario_entrada=datetime.fromisoformat(posicao_antes.horario_entrada),
                        horario_saida=agora, saida=preco_saida,
                        resultado_pts=resultado_pts, resultado_reais=resultado_reais,
                        motivo_saida=motivo,
                    )
                    email_notificacao.notificar_fechamento(
                        posicao_antes, motivo, preco_saida, resultado_pts, resultado_reais, agora
                    )
                    saida_desde_ultimo_fechamento = True
                else:
                    print(f"[{agora}] ALERTA CRITICO: saida {motivo} NAO enviada; "
                          "posicao interna mantida para nova tentativa.")

        # 2) corte de seguranca de horario (18:15-18:20), tambem continuo
        if gestor.posicao_aberta:
            corte = gestor.verificar_corte_final(preco, agora)
            if corte:
                motivo, preco_saida = corte
                posicao_antes = gestor.posicao_aberta
                ordem_ok = executor.encerrar_posicao()
                auditor.registrar_saida(
                    horario=agora, posicao=posicao_antes, motivo=motivo,
                    saida_teorica=preco_saida, saida_dde=preco,
                    ordem_enviada=(ordem_ok or not cfg.ENVIAR_ORDENS),
                    contratos_dde=contratos_reais,
                )
                if ordem_ok or not cfg.ENVIAR_ORDENS:
                    resultado_pts, msg = gestor.fechar_posicao(preco_saida, motivo)
                    leitor.escrever_banca_atual(gestor.banca_atual)
                    resultado_reais = resultado_pts * cfg.VALOR_PONTO_REAIS - cfg.CUSTO_TOTAL_ESTIMADO_POR_OPERACAO_REAIS
                    print(f"[{agora}] {msg}")
                    narrar(frases.FRASES_FECHAMENTO.get(motivo, frases.FRASE_FECHAMENTO_PADRAO_LUCRO if resultado_pts > 0 else frases.FRASE_FECHAMENTO_PADRAO_PREJUIZO))
                    registrador.registrar_operacao_fechada(
                        horario_entrada=datetime.fromisoformat(posicao_antes.horario_entrada),
                        horario_saida=agora, saida=preco_saida,
                        resultado_pts=resultado_pts, resultado_reais=resultado_reais,
                        motivo_saida=motivo,
                    )
                    email_notificacao.notificar_fechamento(
                        posicao_antes, motivo, preco_saida, resultado_pts, resultado_reais, agora
                    )
                    saida_desde_ultimo_fechamento = True
                else:
                    print(f"[{agora}] ALERTA CRITICO: corte final NAO enviado; "
                          "posicao interna mantida para nova tentativa.")

        # ---------- Ao fechar um candle: verifica stop/alvo e avalia novo sinal ----------
        if candle_fechado:
            # O motor do laboratório processa cada candle uma única vez. Quando
            # uma posição fecha dentro dele, o motor avança para o candle
            # seguinte sem procurar uma nova entrada na mesma linha. Guardamos
            # essa informação para reproduzir exatamente o mesmo comportamento.
            houve_saida_neste_candle = saida_desde_ultimo_fechamento
            saida_desde_ultimo_fechamento = False
            # ---------- Deteccao de salto no replay + preenchimento automatico ----------
            # Se o Profit for "arrastado"/pulado pra frente (em vez de acelerado de
            # forma continua) ENQUANTO o robo ja esta rodando, o ConstrutorCandle
            # fecharia o candle errado e abriria um buraco na sequencia - a MA21/RSI
            # ficariam calculadas com candles de antes E depois do buraco misturados,
            # sem sentido real. Se o ultimo candle conhecido esta mais de 1 candle
            # (TIMEFRAME_MINUTOS) atras do que acabou de fechar, tenta preencher o
            # buraco com dado REAL do arquivo historico (nao e "ver o futuro" - esse
            # trecho ja ficou para tras do horario atual, so nao tinha sido
            # incorporado ainda).
            if historico_candles:
                gap_minutos = (candle_fechado.horario - historico_candles[-1].horario).total_seconds() / 60
                if gap_minutos > cfg.TIMEFRAME_MINUTOS * 1.5:
                    print(f"[{agora}] [AVISO] Buraco de {gap_minutos:.0f} min detectado "
                          f"entre {historico_candles[-1].horario} e {candle_fechado.horario} "
                          f"(replay pulado/arrastado?) - tentando preencher com dado real "
                          f"do arquivo historico...")
                    try:
                        candles_arquivo = _ler_csv_candles(Path(cfg.CAMINHO_HISTORICO_INICIAL))
                    except (FileNotFoundError, OSError, ValueError) as e:
                        print(f"[{agora}] [AVISO] Nao foi possivel ler '{cfg.CAMINHO_HISTORICO_INICIAL}' "
                              f"para preencher o buraco: {e}")
                        candles_arquivo = []
                    preenchimento = [c for c in candles_arquivo
                                      if historico_candles[-1].horario < c.horario < candle_fechado.horario]
                    if preenchimento:
                        historico_candles.extend(preenchimento)
                        _salvar_historico_persistente(preenchimento)
                        print(f"[{agora}] [AVISO] Buraco preenchido com {len(preenchimento)} "
                              f"candle(s) reais do arquivo - MA21/RSI/ATR seguem validos.")
                    else:
                        print(f"[{agora}] [AVISO] Nao foi possivel preencher o buraco (arquivo "
                              f"historico nao cobre esse trecho) - MA21/RSI/ATR podem estar "
                              f"incorretos ate a media 'esquentar' de novo com candles novos.")

            # remove qualquer candle ja existente no mesmo horario (evita duplicar
            # quando o historico de bootstrap ja cobre parte do periodo que o
            # robo tambem esta reconstruindo ao vivo via DDE)
            historico_candles = [c for c in historico_candles if c.horario != candle_fechado.horario]
            historico_candles.append(candle_fechado)
            historico_candles.sort(key=lambda c: c.horario)
            _salvar_historico_persistente([candle_fechado])

            sinal_auditoria = None
            decisao_auditoria = "POSICAO_JA_ABERTA" if gestor.posicao_aberta else "SEM_SINAL"
            motivo_auditoria = ""

            if gestor.posicao_aberta:
                row_saida = gestor.construir_row(historico_candles)
                saida = gestor.verificar_saida(candle_fechado.maxima, candle_fechado.minima, agora,
                                                row=row_saida)
                if saida:
                    motivo, preco_saida = saida
                    posicao_antes = gestor.posicao_aberta
                    ordem_ok = executor.encerrar_posicao()
                    saida_teorica = (
                        posicao_antes.stop if motivo == "STOP"
                        else posicao_antes.alvo if motivo == "ALVO"
                        else preco_saida
                    )
                    auditor.registrar_saida(
                        horario=agora, posicao=posicao_antes, motivo=motivo,
                        saida_teorica=saida_teorica, saida_dde=preco,
                        ordem_enviada=(ordem_ok or not cfg.ENVIAR_ORDENS),
                        contratos_dde=contratos_reais,
                    )
                    if ordem_ok or not cfg.ENVIAR_ORDENS:
                        resultado_pts, msg = gestor.fechar_posicao(preco_saida, motivo)
                        leitor.escrever_banca_atual(gestor.banca_atual)
                        resultado_reais = resultado_pts * cfg.VALOR_PONTO_REAIS - cfg.CUSTO_TOTAL_ESTIMADO_POR_OPERACAO_REAIS
                        print(f"[{agora}] {msg}")
                        frase_fechamento = frases.FRASES_FECHAMENTO.get(
                            motivo, frases.FRASE_FECHAMENTO_PADRAO_LUCRO if resultado_pts > 0
                            else frases.FRASE_FECHAMENTO_PADRAO_PREJUIZO
                        )
                        if motivo == "SAIDA_CARTUCHO" and diagnosticar_saida is not None:
                            # explica o motivo REAL do cartucho, nao so a frase generica
                            # de lucro/prejuizo - mesmo espirito de diagnosticar_sinal()
                            # na entrada
                            posicao_final_publica = {
                                "lado": posicao_antes.lado,
                                "entrada": posicao_antes.entrada,
                                "candles_decorridos": posicao_antes.candles_decorridos,
                                "maxima_desde_entrada": posicao_antes.maxima_desde_entrada,
                                "minima_desde_entrada": posicao_antes.minima_desde_entrada,
                                "resultado_flutuante_pts": resultado_pts,
                            }
                            try:
                                explicacao_fechamento = diagnosticar_saida(row_saida, posicao_final_publica)
                            except Exception:
                                explicacao_fechamento = None
                            if isinstance(explicacao_fechamento, str):
                                frase_fechamento = explicacao_fechamento
                        narrar(frase_fechamento)
                        registrador.registrar_operacao_fechada(
                            horario_entrada=datetime.fromisoformat(posicao_antes.horario_entrada),
                            horario_saida=agora, saida=preco_saida,
                            resultado_pts=resultado_pts, resultado_reais=resultado_reais,
                            motivo_saida=motivo,
                        )
                        email_notificacao.notificar_fechamento(
                            posicao_antes, motivo, preco_saida, resultado_pts, resultado_reais, agora
                        )
                        houve_saida_neste_candle = True
                        decisao_auditoria = "SAIDA_SEM_REENTRADA"
                        motivo_auditoria = motivo
                    else:
                        print(f"[{agora}] ALERTA CRITICO: saida {motivo} NAO enviada; "
                              "posicao interna mantida para nova tentativa.")

            if not gestor.posicao_aberta and not houve_saida_neste_candle:
                ma21_fechamento = media_movel(historico_candles, cfg.MA_RAPIDA)
                ma50_fechamento = media_movel(historico_candles, cfg.MA_LENTA)
                tendencia_fechamento = None
                distancia_fechamento = None
                if ma21_fechamento is not None and ma50_fechamento is not None:
                    tendencia_fechamento = "ALTA" if ma21_fechamento > ma50_fechamento else "BAIXA"
                    distancia_fechamento = abs(candle_fechado.fechamento - ma21_fechamento)
                    print(f"[{agora}] [CANDLE FECHADO] Fechamento={candle_fechado.fechamento} "
                          f"MA21={ma21_fechamento:.2f} MA50={ma50_fechamento:.2f} "
                          f"Tendência={tendencia_fechamento} Distância={distancia_fechamento:.1f}pts "
                          f"(limite {cfg.TOLERANCIA_TOQUE_PONTOS})")

                sinal = gestor.avaliar_candle(historico_candles)
                sinal_auditoria = sinal
                if sinal:
                    row_fechamento = gestor.construir_row(historico_candles)
                    diagnostico_fechamento = (
                        diagnosticar_sinal(row_fechamento)
                        if diagnosticar_sinal is not None and row_fechamento is not None
                        else None
                    )
                    chave_fechamento = (
                        candle_fechado.horario,
                        diagnostico_fechamento.get("porta") if diagnostico_fechamento else None,
                        sinal.lado,
                    )
                    pode, motivo_bloqueio = gestor.pode_abrir_posicao(sinal.horario)
                    if pode:
                        origem_sinal = (
                            diagnostico_fechamento.get("estrategia")
                            if diagnostico_fechamento else "estratégia titular"
                        )
                        print(
                            f"\x1b[38;5;46m[{agora.strftime('%H:%M:%S')}] "
                            f"{origem_sinal} | SINAL {sinal.lado} CONFIRMADO"
                            f"{COR_RESET}"
                        )
                        if sinal.lado == "COMPRA":
                            ordem_ok = executor.comprar()
                        else:
                            ordem_ok = executor.vender()

                        auditor.registrar_entrada(
                            horario=agora, sinal=sinal, preco_dde=preco,
                            ordem_enviada=(ordem_ok or not cfg.ENVIAR_ORDENS),
                            contratos_dde=contratos_reais,
                            motivo="" if (ordem_ok or not cfg.ENVIAR_ORDENS)
                            else "Falha ao confirmar foco no Profit",
                        )

                        if ordem_ok or not cfg.ENVIAR_ORDENS:
                            # row=row_fechamento: o motor ORQUESTRA a abertura -
                            # ele mesmo consulta o cartucho de saída titular pelo
                            # stop/alvo iniciais no instante em que a posição
                            # abre (Regra 1 v10). Sem passar `row` aqui, a
                            # posição nasceria sem nível nenhum até o próximo
                            # candle fechar - o cartucho só "verifica a
                            # estratégia de saída", quem decide QUANDO chamá-lo
                            # é sempre o motor.
                            ok, msg = gestor.abrir_posicao(sinal, row=row_fechamento)
                            registrador.registrar_sinal(sinal, aceito=ok, motivo=msg if not ok else "")
                            if ok:
                                decisao_auditoria = "ENTRADA_ACEITA"
                                print(f"[{agora}] {msg}")
                                # gestor.posicao_aberta (não `sinal`): é a Posicao
                                # já com o stop/alvo reais que o cartucho definiu
                                # na abertura - `sinal` nunca carrega isso desde
                                # que o motor deixou de calcular nível nenhum.
                                registrador.registrar_operacao_aberta(gestor.posicao_aberta)
                                email_notificacao.notificar_abertura(gestor.posicao_aberta, agora)
                                narrar(
                                    f"A ordem de {sinal.lado.lower()} foi enviada após "
                                    "a confirmação do candle. A posição foi aberta."
                                )
                                if diagnostico_fechamento:
                                    narrar(diagnostico_fechamento["explicacao"])
                                    ultima_expectativa_narrada = chave_fechamento
                                if sinal.motivo:
                                    narrar(sinal.motivo)
                        else:
                            decisao_auditoria = "ENTRADA_NAO_ENVIADA"
                            motivo_auditoria = "Falha ao confirmar foco no Profit"
                            motivo_falha = "Ordem nao enviada: falha ao confirmar foco no Profit"
                            registrador.registrar_sinal(sinal, aceito=False, motivo=motivo_falha)
                            print(f"[{agora}] ALERTA CRITICO: {motivo_falha}. "
                                  "Posicao interna NAO foi aberta.")
                            narrar(
                                f"O sinal de {sinal.lado.lower()} foi confirmado, mas "
                                "a ordem não foi enviada ao Profit."
                            )
                    else:
                        decisao_auditoria = "SINAL_BLOQUEADO"
                        motivo_auditoria = motivo_bloqueio
                        registrador.registrar_sinal(sinal, aceito=False, motivo=motivo_bloqueio)
                        print(f"[{agora}] Sinal encontrado mas bloqueado: {motivo_bloqueio}")
                        if diagnostico_fechamento:
                            narrar(diagnostico_fechamento["explicacao"])
                            ultima_expectativa_narrada = chave_fechamento
                        narrar(
                            f"O sinal foi confirmado no fechamento do candle, mas a "
                            f"entrada foi bloqueada pela regra de risco: {motivo_bloqueio}."
                        )
                else:
                    if tendencia_fechamento is not None:
                        if candle_fechado.fechamento > candle_fechado.abertura:
                            direcao_candle = "alta"
                        elif candle_fechado.fechamento < candle_fechado.abertura:
                            direcao_candle = "baixa"
                        else:
                            direcao_candle = "estável"

                        tendencia_medias = tendencia_fechamento.lower()
                        if direcao_candle == "estável":
                            frase_candle = (
                                "O candle fechou estável e a tendência das médias "
                                f"permanece de {tendencia_medias}."
                            )
                        elif direcao_candle == tendencia_medias:
                            frase_candle = (
                                f"O candle fechou em {direcao_candle}, acompanhando a "
                                f"tendência de {tendencia_medias} das médias."
                            )
                        else:
                            frase_candle = (
                                f"O candle fechou em {direcao_candle}, mas a tendência "
                                f"das médias ainda é de {tendencia_medias}."
                            )
                        narrar(f"{frase_candle} Nenhum sinal de entrada foi confirmado.")
            elif not gestor.posicao_aberta and houve_saida_neste_candle:
                decisao_auditoria = "SAIDA_SEM_REENTRADA"
                motivo_auditoria = "Regra de paridade: não reutilizar o candle da saída"
                print(
                    f"[{agora}] [MOTOR] Nova entrada ignorada: "
                    f"uma posição foi encerrada neste mesmo candle."
                )

            auditor.registrar_candle(
                horario=agora,
                candle=candle_fechado,
                modo="REPLAY" if _MODO_REPLAY else "NORMAL",
                fonte_ohlc="DDE_AMOSTRADO",  # V458: unica fonte possivel, em
                                              # Replay e ao vivo (ver ata T)
                sinal=sinal_auditoria,
                decisao=decisao_auditoria,
                motivo=motivo_auditoria,
                contratos_dde=contratos_reais,
            )

        # Notícias entram em paralelo, mas só são apresentadas depois das
        # decisões e ordens deste ciclo. Nunca bloqueiam stop, alvo ou entrada.
        while True:
            try:
                texto_noticia = fila_noticias.get_nowait()
            except queue.Empty:
                break
            gestor.registrar_noticia(texto_noticia, horario=agora)
        for evento_noticia in gestor.consumir_noticias():
            narrar(evento_noticia["texto"])

        # Perto do fechamento, lê com mais frequência para reagir ao candle sem
        # atrasar a ordem; não há contagem regressiva falada na V412.
        intervalo = 1 if (dentro_da_faixa and segundos_restantes is not None
                           and segundos_restantes <= cfg.BEEP_SEGUNDOS_ANTES + 1) else 2
        time.sleep(intervalo)  # intervalo entre leituras do DDE


if __name__ == "__main__":
    print("=" * 60)
    while True:
        resposta_modo_dde = input(
            "Escolha REPLAY ou NORMAL (R/N): "
        ).strip().upper()
        if resposta_modo_dde in ("R", "N"):
            break
        print(f"Resposta '{resposta_modo_dde}' não reconhecida - digite exatamente "
              f"R ou N.")
    if resposta_modo_dde == "R":
        _MODO_REPLAY = True
        _NOME_ATIVO_DDE = f"{_leitor_dde_mod.PREFIXO_REPLAY}{cfg.ATIVO}"
        print(f"[MODO REPLAY] Buscando ativo '{_NOME_ATIVO_DDE}' na coluna A da aba DDE.")

        # V458: a REMOCAO dos limites diarios no Replay foi revogada. Ela
        # elevava os limites para 999, de modo que um Replay podia abrir dez
        # operacoes num dia em que a operacao real teria parado na segunda. Era
        # o artificio de maior impacto do robo: mudava a QUANTIDADE de posicoes,
        # nao um detalhe de preco. Replay agora respeita os mesmos limites da
        # operacao real. Para observar o comportamento sem limite, altere
        # MAX_PERDAS_DIA em configuracao.py de forma explicita e consciente.
        # Ver conselho/2026-09-30-T.txt.
        print(f"[AMBIENTE CONTROLADO] Sem capital real, mas o limite diario "
              f"da operacao real PERMANECE ativo "
              f"(MAX_PERDAS_DIA={cfg.MAX_PERDAS_DIA}) - o Replay precisa "
              f"reproduzir o que o mercado ao vivo faria.")
    else:  # resposta_modo_dde == "N" (unico valor restante possivel, garantido pelo loop acima)
        _MODO_REPLAY = False
        _NOME_ATIVO_DDE = cfg.ATIVO
        print(f"[MODO NORMAL] Buscando ativo '{_NOME_ATIVO_DDE}' na coluna A da aba DDE.")
        print("[AMBIENTE REAL] Limite diario validado permanece ativo "
              f"(MAX_PERDAS_DIA={cfg.MAX_PERDAS_DIA}; sem teto de contagem de "
              f"operacoes desde a V459).")
    print("=" * 60)

    if cfg.ENVIAR_ORDENS:
        print("ATENCAO: ENVIAR_ORDENS=True - ordens reais serao enviadas ao Profit.")
    else:
        print("Modo somente alerta/registro. Nenhuma ordem real sera enviada.")
    rodar()

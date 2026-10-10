"""
ROBONILDO - principal.py
Versao exibida dinamicamente por configuracao.VERSAO

Loop principal do dia de pregao. Le preco continuamente (via leitor_dde, ainda a
construir), monta candles de 15min, aplica a regra MA_v2, gerencia risco e registra
tudo. ENVIAR_ORDENS = False nesta fase - nunca envia ordem real.
"""

import time
import re
import csv
import random
import threading
import queue
import frases_narracao as frases
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

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


def _consenso_time(radar, lider):
    """V538: opiniao media do TIME de entrada sobre o cenario, de 0 a 1. Cada titular conta uma vez, com o
    seu melhor item do radar (mesmo que nao seja o escalado); quem aponta para o lado contrario ao da
    estrategia na frente conta 0. So painel: nao entra em nenhuma decisao."""
    if not radar:
        return 0.0
    direcao = lider.get("direcao") if lider else None
    melhores = {}
    for item in radar:
        chave = item.get("titular") or item.get("estrategia")
        valor = float(item.get("progresso", 0.0)) if item.get("direcao") == direcao else 0.0
        melhores[chave] = max(melhores.get(chave, 0.0), valor)
    return sum(melhores.values()) / len(melhores)


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
    return resultado_pts * cfg.valor_ponto_total() - cfg.custo_total_operacao()


_RISCO_INICIAL_PTS = {}   # horario_entrada -> distancia (pts) entre a entrada e o stop inicial (1R)


def _risco_inicial_pts(posicao):
    """V525: 1R da operacao = distancia da entrada ao stop INICIAL, memorizada na primeira vez que o
    stop aparece do lado do prejuizo (o stop do capitao trailing depois sobe e deixa de servir de
    referencia). None se ainda nao foi possivel medir."""
    chave = posicao.horario_entrada
    if chave not in _RISCO_INICIAL_PTS and posicao.stop is not None:
        direcao = 1 if posicao.lado == "COMPRA" else -1
        distancia = (posicao.entrada - posicao.stop) * direcao
        if distancia > 0:
            _RISCO_INICIAL_PTS[chave] = distancia
    return _RISCO_INICIAL_PTS.get(chave)


_TRAILING_AVISADO = {}   # horario_entrada -> {"armado": bool, "assumiu": bool}


def _estado_trailing(posicao, preco_atual: float):
    """V531: situacao do trailing do capitao numa posicao SEM alvo. Devolve None se nao da para saber
    (tem alvo, sem stop, ou o stop inicial nao foi medido). Senao: dict com
      stop_inicial, armado (o ganho maximo ja chegou a 1 R mas o stop ainda e o inicial: o stop so e
      atualizado no fechamento do candle) e assumiu (o stop ja passou do inicial, a favor da posicao)."""
    risco = _risco_inicial_pts(posicao)
    if posicao.alvo is not None or posicao.stop is None or risco is None:
        return None
    direcao = 1 if posicao.lado == "COMPRA" else -1
    stop_inicial = posicao.entrada - direcao * risco
    assumiu = (posicao.stop - stop_inicial) * direcao > 1e-9
    extremo = posicao.maxima_desde_entrada if direcao == 1 else posicao.minima_desde_entrada
    melhor = max((preco_atual - posicao.entrada) * direcao,
                 ((extremo - posicao.entrada) * direcao) if extremo else 0.0)
    return {"stop_inicial": stop_inicial, "risco": risco, "assumiu": assumiu,
            "armado": (not assumiu) and melhor >= risco}


def _frase_trailing(posicao, preco_atual: float, proximo_fechamento=None):
    """V531: frase a narrar UMA vez quando o trailing arma e UMA vez quando assume; None nos demais casos."""
    estado = _estado_trailing(posicao, preco_atual)
    if estado is None:
        return None
    avisado = _TRAILING_AVISADO.setdefault(posicao.horario_entrada, {"armado": False, "assumiu": False})
    if estado["assumiu"] and not avisado["assumiu"]:
        avisado["assumiu"] = avisado["armado"] = True
        direcao = 1 if posicao.lado == "COMPRA" else -1
        reais = (posicao.stop - posicao.entrada) * direcao * cfg.valor_ponto_total() \
            - cfg.custo_total_operacao()
        efeito = (f"protegendo {reais:.0f} reais de lucro" if reais >= 0
                  else f"reduzindo o prejuízo máximo para {abs(reais):.0f} reais")
        return f"O trailing assumiu. O stop passou a {posicao.stop:.0f}, {efeito}."
    if estado["armado"] and not avisado["armado"]:
        avisado["armado"] = True
        quando = (f"No fechamento do candle das {proximo_fechamento:%H:%M}" if proximo_fechamento
                  else "No fechamento deste candle")
        return (f"A saúde da operação chegou a 100%: o preço andou {estado['risco']:.0f} pontos a favor. "
                f"{quando}, o trailing passa a seguir o pico.")
    return None


def _progresso_posicao(posicao, preco_atual: float, risco_ref_pts=None) -> float:
    """
    Progresso da posicao aberta, de -1.0 (no stop) a +1.0 (no alvo), em
    termos de RESULTADO LIQUIDO (ja descontado o custo) - nao de pontos
    brutos. Por isso 0.0 nao fica exatamente no preco de entrada; fica um
    pouco alem dele (o suficiente para cobrir o custo). Qualquer lucro
    liquido real (por menor que seja) ja da progresso > 0, e qualquer
    prejuizo liquido real ja da progresso < 0 - sem zona neutra artificial.

    V525: sem alvo (capitao trailing) o lado do lucro nao tinha referencia e ficava em 0.0. Com
    `risco_ref_pts` (1R) o lado do lucro vai de 0 a +1.0 quando o lucro liquido chega a 1R.
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
            if not risco_ref_pts or risco_ref_pts <= 0:
                return 0.0
            lucro_1r = risco_ref_pts * cfg.valor_ponto_total() - cfg.custo_total_operacao()
            return min(1.0, resultado_liquido / lucro_1r) if lucro_1r > 0 else 0.0
        resultado_liquido_no_alvo = (
            (posicao.alvo - posicao.entrada) * direcao * cfg.valor_ponto_total()
            - cfg.custo_total_operacao()
        )
        return min(1.0, resultado_liquido / resultado_liquido_no_alvo) if resultado_liquido_no_alvo > 0 else 0.0
    else:
        if posicao.stop is None:
            return 0.0
        resultado_liquido_no_stop = (
            (posicao.stop - posicao.entrada) * direcao * cfg.valor_ponto_total()
            - cfg.custo_total_operacao()
        )
        return -min(1.0, resultado_liquido / resultado_liquido_no_stop) if resultado_liquido_no_stop < 0 else 0.0


def _interpolar_cor(cor_a, cor_b, fracao: float):
    """Interpolacao linear continua entre duas cores RGB - sem degraus."""
    fracao = max(0.0, min(1.0, fracao))
    return tuple(round(a + (b - a) * fracao) for a, b in zip(cor_a, cor_b))


_BRANCO = (255, 255, 255)
_LIMA = (163, 255, 30)      # verde-limao, progresso = +1.0 (alvo)
_ROXO = (147, 51, 234)      # roxo, progresso = -1.0 (stop)


def _saude_posicao(posicao, preco_atual: float):
    """V525/V530: saude do trade. Abre em 0% (branco, zero a zero liquido) e anda em direcao ao destino:
    verde no ganho (100% = alvo ou, sem alvo, lucro liquido de 1 R) ou roxo na perda (100% = stop). O
    percentual e a distancia percorrida (sempre >= 0); quem diz o lado e a cor. Devolve (percentual, quadrado)."""
    progresso = _progresso_posicao(posicao, preco_atual, _risco_inicial_pts(posicao))
    return abs(progresso) * 100.0, _quadro_resultado(posicao, preco_atual, progresso)


def _quadro_resultado(posicao, preco_atual: float, progresso=None) -> str:
    """
    Marcador da posicao: BRANCO (neutro) quando o resultado liquido esta em
    zero, e varia de forma CONTINUA (interpolacao RGB real, sem degraus de
    paleta) para roxo conforme o prejuizo liquido cresce em direcao ao stop,
    ou para verde-limao conforme o lucro liquido cresce em direcao ao alvo.
    """
    quadrado = "■"
    if progresso is None:
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
    """V514: toca BEEP_QUANTIDADE beeps seguidos de alerta (Windows: winsound). Roda numa thread
    para nao atrasar a leitura do DDE nem o fechamento do candle."""
    def _tocar():
        for i in range(cfg.BEEP_QUANTIDADE):
            try:
                import winsound
                winsound.Beep(1200, 300)  # 1200 Hz, 300 ms
            except ImportError:
                print("\a", end="", flush=True)  # fallback: beep do proprio terminal (ASCII bell)
            if i < cfg.BEEP_QUANTIDADE - 1:
                time.sleep(0.15)
    threading.Thread(target=_tocar, daemon=True).start()


_narrador_local = threading.local()  # um objeto de voz POR THREAD - COM (usado pelo
                                      # SAPI) exige inicializacao por thread, e
                                      # compartilhar o mesmo objeto entre threads
                                      # diferentes (ex: a thread de noticias) e inseguro


_RE_MA21 = re.compile(r"(?<![A-Za-z0-9])ma21(?![A-Za-z0-9])", re.IGNORECASE)


def _texto_para_voz(texto: str) -> str:
    """V537: pronuncia por extenso o que a voz leria mal. 'MA21' vira 'Média Móvel 21' (vale tambem para nomes de
    estrategia como entrada_retomada_ma21_v01). So troca palavra inteira; o resto do texto fica como veio."""
    return _RE_MA21.sub("Média Móvel 21", texto)


def narrar(texto: str, descartavel: bool = False):
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
    texto = _texto_para_voz(texto)
    print(f"{COR_NARRADOR}[NARRADOR] \"{texto}\"{COR_RESET}")
    try:
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()  # exige inicializacao POR THREAD - seguro
                                   # chamar de novo se a thread atual ja
                                   # inicializou (so incrementa um contador)
        if not hasattr(_narrador_local, "voz"):
            _narrador_local.voz = win32com.client.Dispatch("SAPI.SpVoice")
        if descartavel:
            # V486: aviso que perde o sentido se atrasar (integridade do DDE). Se a voz
            # ainda esta falando outra coisa, NAO entra na fila - o SAPI enfileira sem
            # limite e a voz ficava lendo avisos velhos horas depois.
            try:
                if _narrador_local.voz.Status.RunningState == 2:  # SRSEIsSpeaking
                    return
            except Exception:
                pass
        SVSFlagAsync = 1  # nao bloqueia o robo esperando a fala terminar
        _narrador_local.voz.Speak(texto, SVSFlagAsync)
    except Exception as e:
        print(f"[NARRADOR] Falha ao falar '{texto}': {e}")


_ultimo_aviso_integridade = {}  # V486: tipo de aviso -> quando foi emitido pela ultima vez

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
import shutil
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


def _importar_titular(nome_pasta: str, arquivo, funcao_obrigatoria: str, papel: str = "titular"):
    nome = arquivo.stem
    # Import por caminho de arquivo — evita depender de estrategia/ ser pacote
    # com __init__ em todas as subpastas (titular/ pode ser so uma pasta de arquivos).
    spec = importlib.util.spec_from_file_location(
        f"robonildo_{nome_pasta}_{papel}_{nome}",
        arquivo,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Nao foi possivel importar {arquivo}")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    if not callable(getattr(modulo, funcao_obrigatoria, None)):
        raise RuntimeError(
            f"'{nome}.py' (em estrategia/{nome_pasta}/, papel {papel}) nao fornece "
            f"{funcao_obrigatoria}(...); cartucho invalido."
        )
    return nome, modulo


def _arquivos_titulares(nome_pasta: str):
    pasta = _Path(__file__).parent / "estrategia" / nome_pasta / "titular"
    return [a for a in sorted(pasta.glob("*.py")) if not a.stem.startswith("_")]


def _descobrir_cartucho(nome_pasta: str, funcao_obrigatoria: str):
    """
    Acha exatamente 1 arquivo .py em estrategia/<nome_pasta>/titular/
    (ignora arquivos que comecam com "_"). Confirma a funcao obrigatoria.
    Mantida para compatibilidade; a SAIDA usa _descobrir_capitao_saida() desde a V520.

    Estrutura V520:
      estrategia/entrada/titular/          → cartuchos de entrada de producao (V497: 1 ou mais)
      estrategia/saida/titular/capitao/    → exatamente 1 cartucho: o capitao, UNICO que decide a saida
      estrategia/saida/titular/            → 0 ou mais cartuchos de exaustao: rodam ao vivo, so ALERTAM
    Candidatas de ranking ficam na raiz do slot (fora de titular/) e nao
    sao carregadas aqui — so no classificacao.py.
    """
    candidatos = _arquivos_titulares(nome_pasta)
    if len(candidatos) != 1:
        raise RuntimeError(
            f"A pasta 'estrategia/{nome_pasta}/titular/' deve conter exatamente 1 "
            f"arquivo de cartucho; foram encontrados {len(candidatos)}: "
            f"{[a.name for a in candidatos]}"
        )
    return _importar_titular(nome_pasta, candidatos[0], funcao_obrigatoria)


def _descobrir_capitao_saida():
    """V520: o capitao de saida e o UNICO arquivo .py em estrategia/saida/titular/capitao/.
    So ele decide fechar, stop e alvo da posicao (Regra 1). Trocar de capitao = mover
    arquivo, por merge de PR do dono."""
    pasta = _Path(__file__).parent / "estrategia" / "saida" / "titular" / "capitao"
    arquivos = [a for a in sorted(pasta.glob("*.py")) if not a.stem.startswith("_")]
    if len(arquivos) != 1:
        raise RuntimeError(
            "A pasta 'estrategia/saida/titular/capitao/' deve conter exatamente 1 "
            f"arquivo de cartucho; foram encontrados {len(arquivos)}: {[a.name for a in arquivos]}"
        )
    return _importar_titular("saida", arquivos[0], "avaliar_saida", papel="capitao")


def _descobrir_alertas_saida():
    """V520: titulares de saida que so ALERTAM. Ficam em estrategia/saida/titular/
    (fora de capitao/), 0 ou mais. Rodam em sombra no candle em formacao: se dizem
    "fechar", o robo narra e grava o alerta, mas NUNCA fecha a posicao por eles.
    Um alerta defeituoso e ignorado (nao derruba o robo)."""
    alertas = []
    for arquivo in _arquivos_titulares("saida"):
        try:
            alertas.append(_importar_titular("saida", arquivo, "avaliar_saida", papel="alerta"))
        except Exception as erro:
            print(f"[ALERTA DE SAÍDA] {arquivo.name} ignorado: {type(erro).__name__}: {erro}")
    return alertas


def _descobrir_titulares_entrada():
    """V497 (Regra 17): a pasta estrategia/entrada/titular/ aceita 1 ou mais
    cartuchos de entrada. Com 1, o cartucho opera sozinho (comportamento de
    sempre). Com 2 ou mais, escalacao.Escalacao os junta: consulta todos a cada
    candle e escala quem sinalizar (conflito de lados = nao entra)."""
    arquivos = _arquivos_titulares("entrada")
    if not arquivos:
        raise RuntimeError(
            "A pasta 'estrategia/entrada/titular/' deve conter pelo menos 1 arquivo de cartucho."
        )
    return [_importar_titular("entrada", a, "gerar_sinal") for a in arquivos]


_titulares_entrada = _descobrir_titulares_entrada()
if len(_titulares_entrada) == 1:
    _nome_estrategia, _modulo_estrategia = _titulares_entrada[0]
    _escalacao = None
else:
    from escalacao import Escalacao as _Escalacao, Membro as _Membro
    _escalacao = _Escalacao([_Membro(n, m) for n, m in _titulares_entrada])
    _nome_estrategia, _modulo_estrategia = _escalacao.nome, _escalacao
diagnosticar_sinal = getattr(_modulo_estrategia, "diagnosticar_sinal", None)
diagnosticar_oportunidades = getattr(_modulo_estrategia, "diagnosticar_oportunidades", None)
if _escalacao is None:
    print(f"Cartucho de entrada: {_nome_estrategia}.py  [estrategia/entrada/titular/]")
else:
    print(f"Escalação de entrada: {len(_titulares_entrada)} titulares  [estrategia/entrada/titular/]")
    for _n, _ in _titulares_entrada:
        print(f"  - {_n}.py")

_nome_saida, _modulo_saida = _descobrir_capitao_saida()
diagnosticar_saida = getattr(_modulo_saida, "diagnosticar_saida", None)
print(f"Capitão de saída: {_nome_saida}.py  [estrategia/saida/titular/capitao/]")
_alertas_saida = _descobrir_alertas_saida()
for _n, _ in _alertas_saida:
    print(f"  Alerta de saída (só avisa, não fecha): {_n}.py  [estrategia/saida/titular/]")

from construtor_candle import ConstrutorCandle, candles_faltando
import integridade_historico as _integridade
from historico_csv import ler_csv_candles as _ler_csv_candles
from historico_csv import resolver_csv_historico
from registrador import Registrador
from auditor_execucao import AuditorExecucao
from caminho_operacao import CaminhoOperacao
from alerta_saida import MonitorAlertasSaida, linha_posicao
from radar_estado import PublicadorRadar
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


_horarios_sinteticos = set()   # V498: candles APROXIMADOS (nao persistidos) presentes no historico


def _interpolar_e_registrar(historico_candles: List[Candle], referencia_tempo: datetime,
                            ja_vistos=(), preco_atual: Optional[float] = None) -> int:
    """V498: preenche por aproximacao (reta entre o preco antes e depois) os buracos de ate
    cfg.BURACO_MAX_CANDLES_PREENCHER candles. Os candles aproximados ficam so na memoria
    (nunca no arquivo persistente) e sao trocados pelos reais quando o export do Profit
    os cobrir. Devolve quantos candles criou."""
    base = list(historico_candles) + list(ja_vistos)
    analise = _integridade.analisar_historico(
        base, referencia_tempo, cfg.TIMEFRAME_MINUTOS,
        cfg.HORARIO_PRIMEIRO_CANDLE, cfg.HORARIO_ULTIMO_CANDLE, cfg.FERIADOS_B3,
        aquecimento=cfg.CANDLES_AQUECIMENTO_APOS_BURACO)
    if analise.integro:
        return 0
    novos = _integridade.interpolar_buracos(
        base, analise, preco_atual, cfg.TIMEFRAME_MINUTOS, cfg.HORARIO_PRIMEIRO_CANDLE,
        cfg.HORARIO_ULTIMO_CANDLE, cfg.FERIADOS_B3, cfg.BURACO_MAX_CANDLES_PREENCHER)
    if novos:
        historico_candles.extend(novos)
        historico_candles.sort(key=lambda c: c.horario)
        _horarios_sinteticos.update(c.horario for c in novos)
    return len(novos)


def _trocar_sinteticos_por_reais(historico_candles: List[Candle], referencia_tempo: datetime,
                                 recuperador, agora_real: datetime) -> int:
    """V498: se o export do Profit passou a cobrir candles aproximados, troca pelos reais."""
    if not _horarios_sinteticos or recuperador is None:
        return 0
    so_reais = [c for c in historico_candles if c.horario not in _horarios_sinteticos]
    novos = [c for c in recuperador.tentar(so_reais, referencia_tempo, agora_real,
                                           cfg.TIMEFRAME_MINUTOS)
             if c.horario in _horarios_sinteticos]
    if not novos:
        return 0
    trocados = {c.horario for c in novos}
    historico_candles[:] = sorted(
        [c for c in historico_candles if c.horario not in trocados] + novos,
        key=lambda c: c.horario)
    _horarios_sinteticos.difference_update(trocados)
    _salvar_historico_persistente(novos)
    return len(novos)


def _conferir_integridade_historico(historico_candles: List[Candle], referencia_tempo: datetime,
                                    recuperador, agora_real: datetime, forcar: bool = False,
                                    ja_vistos=(), preco_atual: Optional[float] = None):
    """V498: continuidade do historico contra o horario do mercado, nos dois caminhos de
    carga (arquivo persistente e CSV) e depois a cada tentativa de recuperacao.

    1) Se houver buraco de pregao, tenta preencher com o export mais recente do Profit
       (so insere candle que NAO existe; nunca troca o candle montado ao vivo).
    2) O que o export nao cobrir, ate BURACO_MAX_CANDLES_PREENCHER candles, e preenchido por
       aproximacao e as entradas seguem liberadas. Maior que isso, fica como buraco (bloqueia).
    Devolve (analise, n_do_export, n_aproximados). `historico_candles` e alterado no lugar.
    `ja_vistos`: candles que o robo ja tem mas ainda nao estao na lista (candle em formacao).
    Quem chama imprime/narra - esta funcao so decide e grava."""
    def _analisar():
        return _integridade.analisar_historico(
            list(historico_candles) + list(ja_vistos), referencia_tempo, cfg.TIMEFRAME_MINUTOS,
            cfg.HORARIO_PRIMEIRO_CANDLE, cfg.HORARIO_ULTIMO_CANDLE, cfg.FERIADOS_B3,
            aquecimento=cfg.CANDLES_AQUECIMENTO_APOS_BURACO)
    analise = _analisar()
    preenchidos = 0
    if analise.faltam_total > 0 and recuperador is not None:
        reais = [c for c in historico_candles if c.horario not in _horarios_sinteticos]
        novos = recuperador.tentar(reais + list(ja_vistos), referencia_tempo,
                                   agora_real, cfg.TIMEFRAME_MINUTOS, forcar=forcar)
        if novos:
            trocados = {c.horario for c in novos}
            historico_candles[:] = sorted(
                [c for c in historico_candles if c.horario not in trocados] + novos,
                key=lambda c: c.horario)
            _horarios_sinteticos.difference_update(trocados)
            _salvar_historico_persistente(novos)
            preenchidos = len(novos)
            analise = _analisar()
    aproximados = 0
    if analise.faltam_total > 0:
        aproximados = _interpolar_e_registrar(historico_candles, referencia_tempo,
                                              ja_vistos, preco_atual)
        if aproximados:
            analise = _analisar()
    return analise, preenchidos, aproximados


def _texto_buraco(analise) -> str:
    return _integridade.descrever_buracos(analise)


def _instrucao_liberar() -> str:
    return (f"Para liberar agora: exporte o histórico atualizado do Profit para a pasta de "
            f"'{_Path(cfg.CAMINHO_HISTORICO_INICIAL).parent}'. O robô confere a pasta a cada "
            f"30 segundos e libera sozinho, sem reiniciar.")


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
    # V499: o historico acumulado mudou de lugar (agora fora da pasta do robo). Na primeira
    # vez, copia o arquivo do local antigo, se existir; depois so o novo vale.
    legado = Path(cfg.CAMINHO_HISTORICO_PERSISTENTE_LEGADO)
    if not caminho_persistente.exists() and legado.exists() and legado != caminho_persistente:
        try:
            caminho_persistente.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(legado, caminho_persistente)
            print(f"[HISTORICO] Historico acumulado copiado do local antigo ({legado}) para "
                  f"o novo ({caminho_persistente}).")
        except OSError as e:
            print(f"[AVISO] Nao foi possivel copiar o historico acumulado antigo: {e}")
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

    caminho = resolver_csv_historico(caminho_csv, cfg.TIMEFRAME_MINUTOS)
    if not caminho.exists():
        print(f"[AVISO] Arquivo de historico '{caminho_csv}' tambem nao encontrado. "
              f"O robo vai iniciar sem historico previo e pode demorar ~2 dias "
              f"de pregao ate conseguir calcular a MA50 e gerar sinais.")
        return []

    candles = _ler_csv_candles(caminho)
    candles = _remover_candles_futuros(candles, referencia_tempo)
    print(f"Carga inicial (unica vez): {len(candles)} candles de '{caminho}'.")
    # V498: a conferencia de continuidade (V461) agora e feita por
    # _conferir_integridade_historico(), nos DOIS caminhos de carga, narrada.
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


def _salvar_historico_persistente(candles: List[Candle], sobrescrever: bool = False):
    """
    UPSERT atomico por horario: o candle recebido substitui a ocorrencia
    anterior do mesmo horario, sem criar duplicatas. A escrita acontece num
    arquivo temporario e so depois substitui o original; uma interrupcao no
    meio da gravacao preserva o arquivo anterior.

    V502: no REPLAY nao grava nada. O replay remonta candles de um dia que o
    arquivo ja tem (os do dia vem do export/ao vivo) e os substituiria por versoes
    montadas pela leitura do DDE, a comecar pelo primeiro candle, que o replay
    monta so a partir do momento em que e iniciado.
    """
    if _MODO_REPLAY:
        return
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
                quantidade = "" if c.quantidade is None else f"{c.quantidade:.12g}"
                f.write(f"{cfg.ATIVO};{c.horario.strftime('%d/%m/%Y')};"
                        f"{c.horario.strftime('%H:%M:%S')};{c.abertura:.2f};"
                        f"{c.maxima:.2f};{c.minima:.2f};{c.fechamento:.2f};0;{quantidade}\n")
            f.flush()
        temporario.replace(caminho)
    finally:
        if temporario.exists():
            try:
                temporario.unlink()
            except OSError:
                pass


def _migrar_logs_da_pasta_do_robo():
    """V506: os logs saíram da pasta do robô (<robo>\\logs) para cfg.PASTA_LOGS
    (D:\\DAYTRADE\\LOGS). Na partida, copia (nunca apaga nem sobrescreve) o que existir
    na pasta antiga e ainda não existir na nova, principalmente o estado_risco.json, que
    guarda posição aberta e banca. Depois disso só a pasta nova vale."""
    antiga, nova = Path(cfg.PASTA_LOGS_ANTIGA), Path(cfg.PASTA_LOGS)
    if not antiga.is_dir() or antiga.resolve() == nova.resolve():
        return
    copiados = 0
    try:
        nova.mkdir(parents=True, exist_ok=True)
        for origem in antiga.iterdir():
            destino = nova / origem.name
            if origem.is_file() and not destino.exists():
                shutil.copy2(origem, destino)
                copiados += 1
    except OSError as e:
        print(f"[LOGS] Nao foi possivel copiar os logs antigos de {antiga}: {e}")
        return
    if copiados:
        print(f"[LOGS] {copiados} arquivo(s) copiado(s) de {antiga} para {nova}.")


def rodar():
    _migrar_logs_da_pasta_do_robo()
    construtor = ConstrutorCandle(minutos=cfg.TIMEFRAME_MINUTOS)
    registrador = Registrador(pasta_logs=cfg.PASTA_LOGS_AUDITORIA)
    auditor = AuditorExecucao(
        pasta_logs=cfg.PASTA_LOGS_AUDITORIA,
        habilitado=cfg.AUDITORIA_EXECUCAO_ATIVA,
    )
    # V505: pico/vale/derrapagem/trilha de cada operacao real. No replay o relogio e o preco
    # sao simulados (derrapagem sem sentido e trilha duplicada do mesmo dia): nao grava.
    caminho = CaminhoOperacao(
        pasta_logs=cfg.PASTA_LOGS_AUDITORIA,
        habilitado=cfg.AUDITORIA_EXECUCAO_ATIVA and not _MODO_REPLAY,
    )
    # V520: titulares de alerta da saida (so avisam, nunca fecham). Replay nao grava log.
    monitor_alertas = MonitorAlertasSaida(
        _alertas_saida,
        pasta_logs=None if _MODO_REPLAY else cfg.PASTA_LOGS_AUDITORIA,
        intervalo_s=cfg.ALERTA_SAIDA_INTERVALO_SEGUNDOS,
        estabilidade_s=cfg.ALERTA_SAIDA_ESTABILIDADE_SEGUNDOS,
    )
    executor = ExecutorOrdem()
    fila_noticias = queue.Queue()

    # Noticias de mercado - so informativo, narrado quando surge algo novo e
    # relevante. NUNCA entra na decisao de entrada/saida (ver aviso no topo
    # de noticias.py) - falha silenciosamente se a rede/RSS der problema,
    # sem derrubar o robo.
    _noticias = None  # V498: sem isto, falha ao importar o modulo deixava a variavel indefinida
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
    # V460: coleta passiva de campos extras do DDE (so grava log; desligada se
    # leitor_dde.COLUNAS_EXTRAS_DDE estiver vazio)
    coleta = None
    try:
        from leitor_dde import COLUNAS_EXTRAS_DDE
        if COLUNAS_EXTRAS_DDE:
            from coleta_dde import ColetaDDE
            coleta = ColetaDDE(cfg.PASTA_LOGS_AUDITORIA, list(COLUNAS_EXTRAS_DDE))
            print(f"[COLETA_DDE] Coleta passiva ligada: {list(COLUNAS_EXTRAS_DDE)}")
    except Exception as e:
        print(f"[COLETA_DDE] indisponivel, seguindo sem coleta: {e}")
    leitor.localizar_ativo(_NOME_ATIVO_DDE)
    # V507: aba REGISTRO_OPERACOES da planilha (uma linha por operacao). Nunca no replay.
    registro_planilha = cfg.REGISTRO_PLANILHA_ATIVO and not _MODO_REPLAY
    if registro_planilha:
        registro_planilha = leitor.preparar_registro_operacoes()

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
    # V542: a banca atual vem da planilha (GESTAO_RISCO!B3, ver leitor_dde.CELULA_BANCA_ATUAL).
    # Le na partida e de novo antes de somar cada operacao (assim uma correcao manual na celula vale
    # na proxima saida); ao fechar, grava o valor atualizado. No replay a planilha nao e tocada.
    _banca_sem_gravar = [False]   # True se a ultima gravacao falhou: a memoria vale mais que a celula

    def _sincronizar_banca():
        if _MODO_REPLAY or _banca_sem_gravar[0]:
            return
        gestor.definir_banca(leitor.ler_banca_atual())

    def _fechar_posicao_e_gravar_banca(preco_saida, motivo):
        _sincronizar_banca()
        resultado_pts, msg = gestor.fechar_posicao(preco_saida, motivo)
        if not _MODO_REPLAY and gestor.banca_atual is not None:
            _banca_sem_gravar[0] = not leitor.escrever_banca_atual(gestor.banca_atual)
            if _banca_sem_gravar[0]:
                print("[ALERTA] Nao consegui gravar a banca na planilha; "
                      "vou usar o valor em memoria e tentar de novo na proxima saida.")
        return resultado_pts, msg

    _sincronizar_banca()
    if _MODO_REPLAY:
        print("[BANCA] Replay: a planilha nao e lida nem gravada.")
    elif gestor.banca_atual is None:
        print(f"[ALERTA] Banca atual ilegivel na planilha (aba GESTAO_RISCO, celula "
              f"{_leitor_dde_mod.CELULA_BANCA_ATUAL}). Preencha a celula com a banca; ate la o robo nao soma "
              f"o resultado das operacoes.")
    else:
        print(f"[BANCA] Banca atual lida da planilha: R${gestor.banca_atual:.2f}")

    # V546: estado do radar (radar/radar_estado.js). So desenho; nao decide nada.
    publicador_radar = None
    if cfg.RADAR_PUBLICA_ESTADO:
        publicador_radar = PublicadorRadar(
            cfg.CAMINHO_RADAR_ESTADO, "replay" if _MODO_REPLAY else "normal", envia_ordens=False)
        print(f"[RADAR] Publicando o estado em {cfg.CAMINHO_RADAR_ESTADO}")
    if cfg.RADAR_ENVIA_ORDENS:
        print("[RADAR] AVISO: RADAR_ENVIA_ORDENS=True, mas o radar ainda nao envia ordens; "
              "tratado como False (o robo continua sendo o unico que envia).")
    else:
        print("[RADAR] RADAR_ENVIA_ORDENS=False: o radar nao envia ordens ao Profit (fase de testes).")

    if gestor.posicao_aberta:
        pos = gestor.posicao_aberta
        print(f"[AVISO] Posicao aberta RECUPERADA de uma sessao anterior (mesmo dia "
              f"de mercado): {pos.lado} @ {pos.entrada} | Stop: {pos.stop} | "
              f"Alvo: {pos.alvo} - retomando o monitoramento normalmente.")

    historico_candles: List[Candle] = carregar_historico_inicial(
        cfg.CAMINHO_HISTORICO_INICIAL, referencia_tempo=horario_inicial
    )

    # ---------- V498: PRIMEIRA COISA - integridade da base de dados ----------
    # Em 06/10/2026 o robo so descobriu o buraco quando o sinal ja tinha disparado. Agora
    # a continuidade e conferida AQUI, na partida, nos dois caminhos de carga, e o
    # resultado e narrado em voz alta. Se houver buraco que o export do Profit nao
    # cubra, as novas entradas ja nascem bloqueadas e o robo diz isso agora.
    # O resolvedor imprime qual arquivo escolheu; na rechecagem a cada 30 s isso virava uma
    # linha repetida o dia todo. Aqui so repete a mensagem quando ela MUDA.
    _ultima_msg_resolvedor = [None]

    def _resolver_csv_silencioso():
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            caminho = resolver_csv_historico(cfg.CAMINHO_HISTORICO_INICIAL, cfg.TIMEFRAME_MINUTOS)
        texto = buf.getvalue().strip()
        if texto and texto != _ultima_msg_resolvedor[0]:
            print(texto)
        _ultima_msg_resolvedor[0] = texto
        return caminho

    recuperador_csv = _integridade.RecuperadorCSV(
        _resolver_csv_silencioso, _ler_csv_candles, intervalo_segundos=30.0)
    candles_aquecimento_restantes = 0
    narrar("Verificando a integridade da base de dados.")
    preco_inicial = leitor.ler_preco()
    analise_inicial, preenchidos, aproximados = _conferir_integridade_historico(
        historico_candles, horario_inicial, recuperador_csv, datetime.now(), forcar=True,
        preco_atual=preco_inicial)
    if preenchidos:
        msg = (f"Preenchi {preenchidos} candle(s) faltantes com o arquivo exportado do Profit.")
        print(f"[INTEGRIDADE] {msg}")
        narrar(msg)
    if aproximados:
        msg = (f"Havia buraco na base de dados. Preenchi {aproximados} candle(s) por aproximação, "
               f"uma reta entre o preço antes e depois. Entradas LIBERADAS. Os primeiros sinais "
               f"podem divergir um pouco; se exportar o histórico do Profit, troco pelos candles reais.")
        print(f"[INTEGRIDADE] {msg}")
        narrar(msg)
    if not historico_candles:
        msg = ("Não há histórico de candles. O robô vai calcular as médias só depois de "
               "acumular candles ao vivo; exporte o histórico do Profit para começar já.")
        print(f"[INTEGRIDADE] {msg}")
        narrar(msg)
    elif analise_inicial.integro:
        if not aproximados:
            print(f"[INTEGRIDADE] Base de dados íntegra: {analise_inicial.n_candles} candles, "
                  f"último em {analise_inicial.ultimo_candle}.")
            narrar("Base de dados íntegra. Histórico completo até o mercado agora.")
    else:
        candles_aquecimento_restantes = analise_inicial.restantes
        detalhe = _texto_buraco(analise_inicial)
        if candles_aquecimento_restantes > 0:
            msg = (f"ATENÇÃO. A base de dados tem um buraco grande demais para aproximar: "
                   f"{detalhe}. Novas entradas estão BLOQUEADAS por mais "
                   f"{candles_aquecimento_restantes} candles. {_instrucao_liberar()}")
        else:
            msg = (f"Aviso. Há buraco antigo na base de dados ({detalhe}), mas as médias "
                   f"já foram renovadas depois dele. Entradas liberadas.")
        print(f"[INTEGRIDADE] {msg}")
        narrar(msg)
        if candles_aquecimento_restantes > 0:
            try:
                email_notificacao.notificar("ROBONILDO: base de dados com buraco", msg)
            except Exception as e:
                print(f"[INTEGRIDADE] E-mail de aviso nao enviado: {e}")

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
    ultima_expectativa_narrada = None  # (candle, estratégia, lado), evita repetição da explicação
    ultima_expectativa_perdida = None  # evita repetir a perda da mesma expectativa
    radar_frente_chave = None  # V517: (estratégia, lado) hoje na frente do painel (histerese)
    radar_narrados = set()  # V516: (candle, estratégia, lado) já narrados; cada um é falado UMA vez por candle
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
    # V461/V498: candles que ainda precisam fechar antes de liberar NOVA entrada
    # depois de um buraco nao preenchido no historico (posicao aberta segue gerida).
    # Ja foi calculado na checagem de integridade da partida (acima).
    vigia_dde = _integridade.VigiaLeituraDDE()
    candles_perdidos_queda = 0   # candles inteiros perdidos na queda de leitura em andamento
    ultima_recuperacao_csv = datetime.now()
    ultimo_lembrete_bloqueio = datetime.now()
    ultimo_dia_candle_final = None   # data do dia cujo ultimo candle (18:15) ja foi fechado/salvo
    ultimo_candle_final_visto = None  # data do dia em que o robo acompanhou o candle 18:15 ao vivo
    ultima_hora_dde_vista = None     # (horario DDE, quando vimos) - detecta DDE parado no fim do dia

    while True:
        agora_real = datetime.now()
        preco = leitor.ler_preco()
        agora = leitor.ler_horario_mercado()  # hora do MERCADO (replay ou ao vivo),
                                               # nao do relogio do computador

        if preco is None or agora is None:
            # V498: antes era silencio total. Em 06/10/2026 a planilha ficou ~1 hora sem
            # leitura (outra planilha em uso) e o robo nao disse nada. Agora a falha vira
            # aviso falado (prazo curto se houver posicao aberta) e, com posicao aberta,
            # tambem e-mail.
            aviso_falha = vigia_dde.falha(
                agora_real, posicao_aberta=gestor.posicao_aberta is not None,
                erro=leitor.ultimo_erro_leitura)
            if aviso_falha:
                print(f"[{agora_real.strftime('%H:%M:%S')}] [FALHA DDE] {aviso_falha}")
                narrar(aviso_falha)
                if gestor.posicao_aberta is not None:
                    try:
                        email_notificacao.notificar("ROBONILDO: SEM LEITURA COM POSICAO ABERTA",
                                                    aviso_falha)
                    except Exception as e:
                        print(f"[FALHA DDE] E-mail de aviso nao enviado: {e}")
            # V498: BURACO sinalizado NO INSTANTE em que um candle inteiro se perde (ao vivo,
            # pelo relogio real), sem esperar a leitura voltar.
            if not _MODO_REPLAY and vigia_dde.inicio_queda is not None:
                perdidos = _integridade.candles_perdidos_na_queda(
                    vigia_dde.inicio_queda, agora_real, cfg.TIMEFRAME_MINUTOS,
                    cfg.HORARIO_PRIMEIRO_CANDLE, cfg.HORARIO_ULTIMO_CANDLE, cfg.FERIADOS_B3)
                if perdidos > candles_perdidos_queda:
                    primeiro_buraco = candles_perdidos_queda == 0
                    candles_perdidos_queda = perdidos
                    if primeiro_buraco:
                        msg = (f"BURACO NOS DADOS AGORA. Um candle inteiro se perdeu sem leitura do "
                               f"Profit. Assim que a leitura voltar eu preencho o buraco. "
                               f"Pare de mexer nas planilhas.")
                    else:
                        msg = f"Mais um candle perdido. Já são {perdidos} candles sem leitura."
                    print(f"[{agora_real.strftime('%H:%M:%S')}] [BURACO V498] {msg}")
                    narrar(msg)
                    if primeiro_buraco:
                        try:
                            email_notificacao.notificar("ROBONILDO: BURACO NOS DADOS (leitura caiu)", msg)
                        except Exception as e:
                            print(f"[BURACO] E-mail de aviso nao enviado: {e}")
            time.sleep(2)
            continue  # instabilidade pontual do DDE - pula este ciclo, tenta de novo
        aviso_volta = vigia_dde.sucesso(agora_real)
        candles_perdidos_queda = 0
        if aviso_volta:
            print(f"[{agora_real.strftime('%H:%M:%S')}] [FALHA DDE] {aviso_volta}")
            narrar(aviso_volta)
            # Conferencia IMEDIATA: nao espera o proximo candle fechar para descobrir o
            # buraco (em 06/10 o dono so soube na hora do sinal).
            em_formacao = construtor.candle_em_formacao()
            analise_volta, preenchidos, aproximados = _conferir_integridade_historico(
                historico_candles, agora, recuperador_csv, agora_real, forcar=True,
                ja_vistos=[em_formacao] if em_formacao is not None else (), preco_atual=preco)
            if preenchidos:
                narrar(f"Preenchi {preenchidos} candles faltantes com o export do Profit.")
            if aproximados:
                msg = (f"Buraco de {aproximados} candle(s) preenchido por aproximação, uma reta "
                       f"entre o preço de antes da queda e o de agora. Entradas LIBERADAS. "
                       f"Exporte o histórico do Profit para eu trocar pelos candles reais.")
                print(f"[{agora.strftime('%H:%M:%S')}] [INTEGRIDADE] {msg}")
                narrar(msg)
            if not analise_volta.integro and analise_volta.restantes > 0:
                candles_aquecimento_restantes = max(candles_aquecimento_restantes,
                                                    analise_volta.restantes)
                ultimo_lembrete_bloqueio = agora_real
                ultima_recuperacao_csv = agora_real
                msg = (f"BLOQUEIO. A queda de leitura abriu buraco grande demais para aproximar: "
                       f"{_texto_buraco(analise_volta)}. Novas entradas BLOQUEADAS por "
                       f"{candles_aquecimento_restantes} candles; posição aberta segue gerida. "
                       f"{_instrucao_liberar()}")
                print(f"[{agora.strftime('%H:%M:%S')}] [BLOQUEIO V498] {msg}")
                narrar(msg)
            elif analise_volta.integro and not aproximados:
                narrar("Conferi: nenhum candle foi perdido. Segue normal.")

        # ---------- V499/V498: buraco - troca aproximados por reais e tenta liberar bloqueio ----------
        # Roda ANTES dos desvios 'aguardando abertura' e 'mercado encerrado': o dono pode exportar
        # o historico de madrugada ou com o pregao fechado e ver a liberacao na hora.
        # A cada 30 s olha o export mais recente do Profit: candles reais substituem os
        # aproximados e fecham buraco grande. O lembrete falado a cada 5 min (so com bloqueio)
        # existe para o dono NUNCA descobrir o bloqueio so na hora do sinal.
        if candles_aquecimento_restantes > 0 or _horarios_sinteticos:
            if (agora_real - ultima_recuperacao_csv).total_seconds() >= 30:
                ultima_recuperacao_csv = agora_real
                trocados = _trocar_sinteticos_por_reais(historico_candles, agora, recuperador_csv,
                                                        agora_real)
                if trocados:
                    msg = (f"Troquei {trocados} candle(s) aproximados pelos candles reais do "
                           f"Profit. Base de dados mais precisa.")
                    print(f"[{agora.strftime('%H:%M:%S')}] [INTEGRIDADE] {msg}")
                    narrar(msg)
                if candles_aquecimento_restantes > 0:
                    analise_rec, preenchidos, aproximados = _conferir_integridade_historico(
                        historico_candles, agora, recuperador_csv, agora_real, preco_atual=preco)
                    if preenchidos or aproximados:
                        print(f"[{agora.strftime('%H:%M:%S')}] [INTEGRIDADE] {preenchidos} candle(s) "
                              f"do export e {aproximados} aproximados preencheram o buraco.")
                        if analise_rec.restantes < candles_aquecimento_restantes:
                            candles_aquecimento_restantes = analise_rec.restantes
                        if candles_aquecimento_restantes == 0:
                            msg = ("Base de dados corrigida. Entradas LIBERADAS.")
                            print(f"[{agora.strftime('%H:%M:%S')}] [INTEGRIDADE] {msg}")
                            narrar(msg)
                            ultimo_lembrete_bloqueio = agora_real
                        else:
                            narrar(f"Preenchi parte do buraco, mas ainda há buraco grande: "
                                   f"{_texto_buraco(analise_rec)}.")
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

            # V498: o ultimo candle do dia (18:15) NUNCA fechava: o construtor so fecha um
            # candle quando chega leitura de um periodo novo (18:30), e o robo parava de
            # ler as 18:20:58. Resultado: o candle 18:15 nao era salvo e a manha seguinte
            # abria com buraco falso (e 50 candles de bloqueio). Mantemos o construtor
            # alimentado (sem operar) ate o candle fechar - pelo relogio do DDE (>= 18:30)
            # ou, se o DDE parar de andar depois do encerramento, forcado.
            if ultimo_dia_candle_final != data_hoje and ultimo_candle_final_visto != data_hoje:
                # o robo nao acompanhou o ultimo candle ao vivo (iniciou depois das 18:15):
                # um candle montado so com leituras de depois do encerramento seria falso.
                ultimo_dia_candle_final = data_hoje
            if ultimo_dia_candle_final != data_hoje:
                candle_final = construtor.nova_leitura(preco, agora)
                if ultima_hora_dde_vista is None or ultima_hora_dde_vista[0] != agora:
                    ultima_hora_dde_vista = (agora, agora_real)
                elif candle_final is None and \
                        (agora_real - ultima_hora_dde_vista[1]).total_seconds() >= 60:
                    candle_final = construtor.fechar_em_formacao()
                if candle_final is not None:
                    ultimo_dia_candle_final = data_hoje
                    ultima_hora_dde_vista = None
                    if candle_final.horario.strftime("%H:%M") == cfg.HORARIO_ULTIMO_CANDLE and \
                            candle_final.horario.date() == agora.date():
                        historico_candles = [c for c in historico_candles
                                             if c.horario != candle_final.horario]
                        historico_candles.append(candle_final)
                        historico_candles.sort(key=lambda c: c.horario)
                        _salvar_historico_persistente([candle_final])
                        print(f"[HISTÓRICO] Candle de {candle_final.horario.strftime('%H:%M')} "
                              f"fechado e salvo no fim do pregão (evita buraco falso amanhã).")
                else:
                    time.sleep(5)
                    continue
            time.sleep(300)
            continue

        # Ao detectar um novo pregão, reativa o painel de notícias.
        if _noticias is not None:
            _noticias.retomar()

        # ---------- V498: lembrete falado do bloqueio (a recuperacao ja rodou acima) ----------
        if candles_aquecimento_restantes > 0:
            if candles_aquecimento_restantes > 0 and \
                    (agora_real - ultimo_lembrete_bloqueio).total_seconds() >= cfg.LEMBRETE_BLOQUEIO_SEGUNDOS:
                ultimo_lembrete_bloqueio = agora_real
                msg = (f"Lembrete: o robô NÃO vai entrar. Entradas BLOQUEADAS por buraco grande na "
                       f"base de dados, faltam {candles_aquecimento_restantes} candles. "
                       f"Exporte o histórico do Profit para liberar agora.")
                print(f"[{agora.strftime('%H:%M:%S')}] [INTEGRIDADE] {msg}")
                narrar(msg)


        # ---------- Prova real contra a tela do Profit ----------
        avisos_integridade = leitor.verificar_integridade(preco, agora, modo_replay=_MODO_REPLAY)
        for aviso in avisos_integridade:
            # V486: no maximo um aviso de cada TIPO a cada AVISO_INTEGRIDADE_REPETIR_SEGUNDOS
            # (o tipo e a primeira palavra: Salto / Preço / Horário).
            tipo_aviso = aviso.split(" ", 1)[0]
            ultimo_aviso = _ultimo_aviso_integridade.get(tipo_aviso)
            if (ultimo_aviso is not None and
                    (agora_real - ultimo_aviso).total_seconds() < _leitor_dde_mod.AVISO_INTEGRIDADE_REPETIR_SEGUNDOS):
                continue
            _ultimo_aviso_integridade[tipo_aviso] = agora_real
            print(f"[{agora.strftime('%H:%M:%S')}] [INTEGRIDADE DDE] {aviso}")
            narrar(aviso, descartavel=True)
        if leitor.checkpoint_devido():
            # V512: a narracao "Checagem de rotina: preco lido e X. Confira na tela do Profit." foi removida
            # a pedido do dono; o checkpoint continua sendo marcado (estado do leitor inalterado).
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
            # V517: histerese. Com o % fino as estratégias trocam de posição a cada leitura; a que já está na
            # frente só perde o lugar se outra passar na frente por mais de 5 pontos (ou se confirmar o sinal).
            if radar_frente_chave is not None and radar[0]["progresso"] < 1.0:
                for _item in radar:
                    if ((_item.get("estrategia"), _item.get("direcao")) == radar_frente_chave
                            and _item["progresso"] >= radar[0]["progresso"] - 0.05):
                        oportunidade_prioritaria = _item
                        break
            radar_frente_chave = (oportunidade_prioritaria.get("estrategia"),
                                  oportunidade_prioritaria.get("direcao"))
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
                if candles_aquecimento_restantes > 0:   # V498: nunca deixar o dono esperando em vao
                    msg = (f"Atenção: oportunidade de {oportunidade_prioritaria.get('estrategia')} "
                           f"em 100%, mas as entradas estão BLOQUEADAS por buraco na base de "
                           f"dados. O robô não vai entrar.")
                    print(f"[{agora.strftime('%H:%M:%S')}] [INTEGRIDADE] {msg}")
                    narrar(msg)
        else:
            radar_100_chave = None
            radar_100_desde = None
        if ma21 is not None and ma50 is not None and candle_atual is not None:
            tendencia = "ALTA" if ma21 > ma50 else "BAIXA"

            if not gestor.posicao_aberta:
                monitor_alertas.encerrar(agora_real)   # V520: fim da posicao -> resumo do log e zera
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
                    nome_estrategia = diagnostico.get("estrategia") if diagnostico else None
                    lado = sinal_especulativo.lado
                    chave_expectativa = (candle_atual.horario, nome_estrategia, lado)
                    if ultima_expectativa_narrada != chave_expectativa:
                        explicacao = (
                            diagnostico["explicacao"] if diagnostico else
                            f"A estratégia identificou uma expectativa de "
                            f"{lado.lower()} no fechamento do candle em formação."
                        )
                        # V509: a explicacao ja diz qual estrategia esta se aproximando
                        # (confirmacoes, proxima condicao); nao ha mais sufixo de "porta".
                        # O candle em formacao fecha em horario + TIMEFRAME. Dizer
                        # so "no fechamento" gera leitura ambigua: logo apos um
                        # [CANDLE FECHADO] o operador le as duas frases em sequencia
                        # ("nenhum sinal confirmado" + "sera disparada no
                        # fechamento") e entende que a ordem deveria ter saido
                        # AGORA, quando ela se refere ao fechamento SEGUINTE.
                        # Nomear o horario elimina a ambiguidade.
                        fechamento_previsto_dt = (
                            candle_atual.horario + timedelta(minutes=cfg.TIMEFRAME_MINUTOS)
                        )
                        fechamento_previsto = fechamento_previsto_dt.strftime("%H:%M")
                        # V488: a mesma porta que a entrada real usa (pode_abrir_posicao,
                        # avaliada no fechamento). Em 05/10/2026 as 18:15 o robo narrou
                        # "se confirmado no fechamento das 18:30, a ordem sera disparada",
                        # mas 18:30 e depois do horario limite (18:20): nao havia ordem
                        # possivel. Nao promete ordem que o gestor vai recusar.
                        pode_no_fechamento, motivo_no_fechamento = gestor.pode_abrir_posicao(
                            fechamento_previsto_dt)
                        if pode_no_fechamento:
                            explicacao = (
                                f"{explicacao} Se confirmado no fechamento das "
                                f"{fechamento_previsto}, a ordem será disparada."
                            )
                        else:
                            explicacao = (
                                f"{explicacao} Mas o fechamento previsto, {fechamento_previsto}, "
                                f"não permite ordem: {motivo_no_fechamento}."
                            )
                        narrar(explicacao)
                        ultima_expectativa_narrada = chave_expectativa
                        ultima_expectativa_perdida = None
                elif (ultima_expectativa_narrada is not None
                      and ultima_expectativa_narrada[0] == candle_atual.horario
                      and ultima_expectativa_perdida != ultima_expectativa_narrada):
                    _, estrategia_anterior, lado_anterior = ultima_expectativa_narrada
                    origem = f"da estratégia {estrategia_anterior}" if estrategia_anterior else "da estratégia"
                    frase_perdida = (
                        f"A expectativa de {lado_anterior.lower()} {origem} perdeu "
                        "confirmação durante a formação do candle."
                    )
                    narrar(frase_perdida)
                    ultima_expectativa_perdida = ultima_expectativa_narrada

                # O radar avisa antes da confirmação completa. Só narra a partir
                # de 70% para não transformar pequenas oscilações em promessa de
                # entrada nem poluir o áudio a cada leitura DDE.
                if (not dentro_da_faixa and oportunidade_prioritaria
                        and progresso_radar >= 0.70):
                    # V516: com o % fino a estratégia da frente e o valor oscilam a cada leitura; a chave
                    # não leva mais a faixa de %, e o conjunto lembra de tudo que já foi dito no candle
                    # (antes comparava só com a última fala e repetia ao alternar entre estratégias).
                    radar_narrados = {k for k in radar_narrados if k[0] == candle_atual.horario}
                    chave_radar = (
                        candle_atual.horario,
                        oportunidade_prioritaria.get("estrategia"),
                        oportunidade_prioritaria.get("direcao"),
                    )
                    if chave_radar not in radar_narrados:
                        faltantes = oportunidade_prioritaria.get("faltantes") or []
                        proxima = faltantes[0] if faltantes else "confirmação no fechamento"
                        explicacao = (
                            f"A estratégia {oportunidade_prioritaria['estrategia']} "
                            f"assumiu a prioridade para {oportunidade_prioritaria['direcao'].lower()}, "
                            f"com {oportunidade_prioritaria['confirmadas']} de "
                            f"{oportunidade_prioritaria['total']} condições. "
                            f"Ainda aguardamos {proxima}."
                        )
                        print(f"[ESCALA] {explicacao}")
                        narrar(explicacao)
                        radar_narrados.add(chave_radar)
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
                    narrar(frase_saida)
                    ultima_saida_especulativa_narrada = chave_saida_especulativa

                # ---------- V520: nivel de exaustao (titulares de alerta) ----------
                # So avisa e grava; quem decide a saida e o capitao. Mesmo contador de
                # relogio real da entrada ("ha Ns"): fala quando o nivel sobe e a cada
                # ALERTA_SAIDA_INTERVALO_SEGUNDOS enquanto ele se mantem.
                try:
                    pico_pts = ((posicao_especulativa["maxima_desde_entrada"] - posicao_atual.entrada)
                                if direcao == 1 else
                                (posicao_atual.entrada - posicao_especulativa["minima_desde_entrada"]))
                    fala_exaustao = monitor_alertas.avaliar(
                        row_indicadores, posicao_especulativa,
                        (candle_atual.horario, posicao_atual.horario_entrada), agora_real,
                        {
                            "horario_entrada": posicao_atual.horario_entrada,
                            "lado": posicao_atual.lado, "entrada": posicao_atual.entrada,
                            "preco": preco, "candle": candle_atual.horario.strftime("%H:%M"),
                            "lucro_pts": round(resultado_especulativo, 1), "pico_pts": round(pico_pts, 1),
                            "lucro_reais": _resultado_liquido_reais(posicao_atual, preco),
                        },
                    )
                except Exception:
                    fala_exaustao = None
                if fala_exaustao:
                    narrar(fala_exaustao)

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
                narrar(frase)
            elif tendencia is not None and not radar:
                chave = (tendencia, "DENTRO" if dentro_da_faixa else "FORA")
                frase = frases.FRASES_PERIODICAS_SEM_POSICAO.get(chave)
                if frase:
                    narrar(frase)
            ultimo_candle_narracao_periodica = candle_horario_atual

        if publicador_radar is not None:
            publicador_radar.publicar(
                radar, _consenso_time(radar, oportunidade_prioritaria), gestor.posicao_aberta)

        if (agora_real - ultimo_heartbeat).total_seconds() >= HEARTBEAT_SEGUNDOS:
            indicadores_texto = _texto_indicadores(row_indicadores)
            quadro = _quadro_proximidade(
                progresso_radar, segundos_restantes, cfg.TIMEFRAME_MINUTOS * 60
            )
            # V517: 100% só quando o sinal está confirmado; antes disso o painel trunca (99,6 vira 99, não 100)
            _p = max(0.0, min(1.0, float(progresso_radar)))
            progresso_radar_pct = 100.0 if _p >= 1.0 else float(min(99, int(_p * 100)))
            # V538: segunda coluna = consenso do time (media dos titulares), com a mesma cor/regra da primeira
            _c = max(0.0, min(1.0, _consenso_time(radar, oportunidade_prioritaria)))
            consenso_pct = 100.0 if _c >= 1.0 else float(min(99, int(_c * 100)))
            quadro_consenso = _quadro_proximidade(_c, segundos_restantes, cfg.TIMEFRAME_MINUTOS * 60)
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
                # V523: com posicao aberta e SEM alvo (o capitao trailing nunca define um) a linha segue o
                # padrao da Escala de entrada: alerta de exaustao na frente | n/N | Falta ... | % ■, e com
                # o alerta confirmado o lugar do "Falta" mostra o nivel e o "ha Ns". Resultado e stop
                # ficam no inicio, em colunas fixas. Largura: 120 colunas. Com alvo definido (ou sem
                # radar) vale a linha antiga, com a exaustao em forma curta.
                campos_exaustao = monitor_alertas.campos_painel(agora_real) if pos.alvo is None else None
                if campos_exaustao is not None:
                    resultado_curto = f"{cor_resultado}{resultado_reais:+7.2f}{COR_RESET}"
                    estado_trail = _estado_trailing(pos, preco)
                    rotulo_stop = "Trail" if (estado_trail and estado_trail["assumiu"]) else "Stop "
                    stop_curto = f"{rotulo_stop} {pos.stop:6.0f}" if pos.stop is not None else "Stop       -"
                    fala_trailing = _frase_trailing(pos, preco, proximo_fechamento)
                    if fala_trailing:
                        narrar(fala_trailing)
                    quadro_exaustao = _quadro_proximidade(
                        campos_exaustao["progresso"], segundos_restantes, cfg.TIMEFRAME_MINUTOS * 60
                    )
                    saude_pct, quadro_saude = _saude_posicao(pos, preco)
                    print(linha_posicao(agora.strftime('%H:%M:%S'), lado_colorido, preco, resultado_curto,
                                        stop_curto, campos_exaustao, quadro_exaustao,
                                        saude_pct, quadro_saude))
                else:
                    alvo_campo = (f"Alvo {pos.alvo:6.0f} ({abs(pos.alvo - preco):4.0f}) | "
                                  if pos.alvo is not None else "")
                    stop_txt = (f"Stop {pos.stop:6.0f} ({abs(preco - pos.stop):4.0f})"
                                if pos.stop is not None else "Stop      - (   -)")
                    print(f"[{agora.strftime('%H:%M:%S')}] {lado_colorido} | "
                          f"Ent {pos.entrada:6.0f} | Atual {preco:6.0f} | "
                          f"Res {resultado_colorido} | {alvo_campo}{stop_txt} | "
                          f"{progresso_pct:3.0f}% {quadro_posicao}"
                          f"{monitor_alertas.texto_painel(agora_real, compacto=True)}")
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
                        bloqueio_horario_radar = bool(
                            oportunidade_prioritaria.get("bloqueio_horario", False)
                        )
                    else:
                        faltante = "aguardando oportunidade"
                        detalhe_radar = faltante
                        bloqueio_horario_radar = False
                    largura_detalhe = 35 if bloqueio_horario_radar else 29
                    if len(detalhe_radar) > largura_detalhe:
                        detalhe_radar = detalhe_radar[:largura_detalhe - 1] + "…"
                    campo_detalhe = (
                        f"{detalhe_radar:<35}"
                        if bloqueio_horario_radar
                        else f"Falta {detalhe_radar:<29}"
                    )
                    if oportunidade_prioritaria and not itens:   # V540: nada falta -> "Falta nenhuma" se contradizia
                        campo_detalhe = f"{'Confirmada: aguarda o fechamento':<35}"
                    sustentacao = ""
                    if radar_100_desde is not None and progresso_radar >= 1.0:
                        segundos_100 = max(0, int((agora_real - radar_100_desde).total_seconds()))
                        sustentacao = f" | há {segundos_100}s"
                    # V522: avisos curtos (a explicacao completa ja foi narrada/impressa quando o buraco
                    # surgiu); antes passavam de 140 colunas e quebravam a linha do painel.
                    aviso_bloqueio = (
                        f" | {COR_BAIXA}BLOQ {candles_aquecimento_restantes}c"
                        f"{COR_RESET}" if candles_aquecimento_restantes > 0
                        else (" | aprox" if _horarios_sinteticos else "")
                    )
                    print(f"[{agora.strftime('%H:%M:%S')}] Preço {preco:6.0f} | "
                          f"{tendencia_colorida} | Escala {status_sinal} | "
                          f"{confirmacoes_radar:^3} | {campo_detalhe}"
                          f" | {progresso_radar_pct:3.0f}% {quadro}"
                          f" | {consenso_pct:3.0f}% {quadro_consenso}"
                          f"{sustentacao}{aviso_bloqueio}")   # V518: % e quadrado fixos; "há Ns" vai depois
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

        # Nenhuma coluna DDE de Quantidade incremental foi confirmada ainda.
        # Sem fonte auditada, os candles ao vivo mantêm quantidade=None;
        # nunca usar preço ou zero como substituto para volume Gabriel.
        if agora.strftime("%H:%M") >= cfg.HORARIO_ULTIMO_CANDLE:
            ultimo_candle_final_visto = agora.strftime("%Y-%m-%d")  # V498
        candle_fechado = construtor.nova_leitura(preco, agora)
        if coleta is not None:
            coleta.processar(agora, leitor.ler_extras(), candle_fechado)

        # ---------- Gestao de posicao aberta (monitoramento continuo) ----------
        if gestor.posicao_aberta:
            # V505: registra pico/vale/trilha desta leitura ANTES de qualquer decisao de saida
            caminho.atualizar(gestor.posicao_aberta, preco, agora)
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
                entrada_dde_op = auditor.entradas_dde.get(posicao_antes.horario_entrada)
                auditor.registrar_saida(
                    horario=agora, posicao=posicao_antes, motivo=motivo,
                    saida_teorica=saida_teorica, saida_dde=preco,
                    ordem_enviada=(ordem_ok or not cfg.ENVIAR_ORDENS),
                    contratos_dde=contratos_reais,
                )
                if ordem_ok or not cfg.ENVIAR_ORDENS:
                    resultado_pts, msg = _fechar_posicao_e_gravar_banca(preco_saida, motivo)
                    resultado_reais = resultado_pts * cfg.valor_ponto_total() - cfg.custo_total_operacao()
                    print(f"[{agora}] {msg}")
                    narrar(frases.FRASES_FECHAMENTO.get(motivo, frases.FRASE_FECHAMENTO_PADRAO_LUCRO if resultado_pts > 0 else frases.FRASE_FECHAMENTO_PADRAO_PREJUIZO))
                    registrador.registrar_operacao_fechada(
                        horario_entrada=datetime.fromisoformat(posicao_antes.horario_entrada),
                        horario_saida=agora, saida=preco_saida,
                        resultado_pts=resultado_pts, resultado_reais=resultado_reais,
                        motivo_saida=motivo,
                    )
                    linha_caminho = caminho.fechar(
                        posicao_antes, agora, motivo, saida_teorica, preco,
                        preco_saida, resultado_pts, resultado_reais, entrada_dde=entrada_dde_op,
                    )
                    if registro_planilha:
                        leitor.registrar_fechamento_planilha(
                            posicao_antes, agora, preco_saida, motivo, resultado_pts, resultado_reais,
                            pico_reais=(linha_caminho or {}).get('pico_reais'),
                            devolveu_reais=((linha_caminho or {}).get('devolucao_pts') or 0) * cfg.valor_ponto_total() if linha_caminho else None,
                            banca=gestor.banca_atual,
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
                entrada_dde_op = auditor.entradas_dde.get(posicao_antes.horario_entrada)
                auditor.registrar_saida(
                    horario=agora, posicao=posicao_antes, motivo=motivo,
                    saida_teorica=preco_saida, saida_dde=preco,
                    ordem_enviada=(ordem_ok or not cfg.ENVIAR_ORDENS),
                    contratos_dde=contratos_reais,
                )
                if ordem_ok or not cfg.ENVIAR_ORDENS:
                    resultado_pts, msg = _fechar_posicao_e_gravar_banca(preco_saida, motivo)
                    resultado_reais = resultado_pts * cfg.valor_ponto_total() - cfg.custo_total_operacao()
                    print(f"[{agora}] {msg}")
                    narrar(frases.FRASES_FECHAMENTO.get(motivo, frases.FRASE_FECHAMENTO_PADRAO_LUCRO if resultado_pts > 0 else frases.FRASE_FECHAMENTO_PADRAO_PREJUIZO))
                    registrador.registrar_operacao_fechada(
                        horario_entrada=datetime.fromisoformat(posicao_antes.horario_entrada),
                        horario_saida=agora, saida=preco_saida,
                        resultado_pts=resultado_pts, resultado_reais=resultado_reais,
                        motivo_saida=motivo,
                    )
                    linha_caminho = caminho.fechar(
                        posicao_antes, agora, motivo, preco_saida, preco,
                        preco_saida, resultado_pts, resultado_reais, entrada_dde=entrada_dde_op,
                    )
                    if registro_planilha:
                        leitor.registrar_fechamento_planilha(
                            posicao_antes, agora, preco_saida, motivo, resultado_pts, resultado_reais,
                            pico_reais=(linha_caminho or {}).get('pico_reais'),
                            devolveu_reais=((linha_caminho or {}).get('devolucao_pts') or 0) * cfg.valor_ponto_total() if linha_caminho else None,
                            banca=gestor.banca_atual,
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
                # V498: primeiro mede o que FALTA de pregao (fim de semana/feriado/noite nao
                # contam); so se faltar algo avisa, tenta preencher e bloqueia. Antes, todo
                # candle depois de uma noite "parecia" buraco por causa do gap em minutos.
                faltam = candles_faltando(
                    historico_candles[-1].horario, candle_fechado.horario,
                    cfg.TIMEFRAME_MINUTOS, cfg.HORARIO_PRIMEIRO_CANDLE,
                    cfg.HORARIO_ULTIMO_CANDLE, cfg.FERIADOS_B3)
                if faltam > 0:
                    ultimo_conhecido = historico_candles[-1].horario
                    ja_bloqueado = candles_aquecimento_restantes > 0   # ja avisado (queda do DDE)
                    print(f"[{agora}] [AVISO] Buraco de {faltam} candle(s) de pregao detectado "
                          f"entre {ultimo_conhecido} e {candle_fechado.horario} - tentando "
                          f"preencher com dado real do export do Profit...")
                    if not ja_bloqueado:
                        narrar(f"Atenção. Buraco nos dados: faltam {faltam} candles entre "
                               f"{ultimo_conhecido.strftime('%H:%M')} e "
                               f"{candle_fechado.horario.strftime('%H:%M')}. Vou preencher agora.")
                    novos_csv = recuperador_csv.tentar(
                        historico_candles + [candle_fechado], agora, agora_real,
                        cfg.TIMEFRAME_MINUTOS, forcar=True)
                    novos_csv = [c for c in novos_csv if c.horario < candle_fechado.horario]
                    if novos_csv:
                        historico_candles.extend(novos_csv)
                        historico_candles.sort(key=lambda c: c.horario)
                        _salvar_historico_persistente(novos_csv)
                        print(f"[{agora}] [AVISO] Buraco preenchido com {len(novos_csv)} "
                              f"candle(s) reais do arquivo.")
                    else:
                        print(f"[{agora}] [AVISO] Nao foi possivel preencher o buraco (export do "
                              f"Profit nao cobre esse trecho) - MA21/RSI/ATR podem estar "
                              f"incorretos ate a media 'esquentar' de novo com candles novos.")
                    # V498: o que o export nao cobriu e aproximado (ate BURACO_MAX_CANDLES_PREENCHER
                    # candles) e as entradas seguem liberadas. So buraco maior que isso bloqueia.
                    aproximados = _interpolar_e_registrar(historico_candles, agora,
                                                          ja_vistos=[candle_fechado])
                    if aproximados:
                        msg = (f"Buraco preenchido por aproximação: {aproximados} candle(s), uma "
                               f"reta entre o preço de antes e o de depois. Entradas LIBERADAS. "
                               f"Exporte o histórico do Profit para eu trocar pelos candles reais.")
                        print(f"[{agora}] [INTEGRIDADE] {msg}")
                        if not ja_bloqueado:
                            narrar(msg)
                    # V462 (achado C do Manus): a decisao de bloquear vem DEPOIS de qualquer
                    # tentativa, olhando o que AINDA falta - preenchimento parcial nao libera.
                    faltam = candles_faltando(
                        historico_candles[-1].horario, candle_fechado.horario,
                        cfg.TIMEFRAME_MINUTOS, cfg.HORARIO_PRIMEIRO_CANDLE,
                        cfg.HORARIO_ULTIMO_CANDLE, cfg.FERIADOS_B3)
                    if faltam > 0:
                        if candles_aquecimento_restantes == 0:   # V498: nao reinicia a contagem
                            candles_aquecimento_restantes = cfg.CANDLES_AQUECIMENTO_APOS_BURACO
                        ultimo_lembrete_bloqueio = agora_real
                        ultima_recuperacao_csv = agora_real
                        msg = (f"BLOQUEIO. Buraco de {faltam} candles, grande demais para aproximar. "
                               f"Novas entradas BLOQUEADAS por {candles_aquecimento_restantes} "
                               f"candles; posição aberta segue gerida. {_instrucao_liberar()}")
                        print(f"[{agora}] [BLOQUEIO V462] {msg}")
                        if not ja_bloqueado:
                            narrar(msg)
                            try:
                                email_notificacao.notificar("ROBONILDO: entradas bloqueadas por buraco", msg)
                            except Exception as e:
                                print(f"[BLOQUEIO] E-mail de aviso nao enviado: {e}")
                    elif novos_csv and not aproximados:
                        msg = "Buraco preenchido com dados reais. Entradas liberadas."
                        print(f"[{agora}] [INTEGRIDADE] {msg}")
                        narrar(msg)

            # remove qualquer candle ja existente no mesmo horario (evita duplicar
            # quando o historico de bootstrap ja cobre parte do periodo que o
            # robo tambem esta reconstruindo ao vivo via DDE)
            historico_candles = [c for c in historico_candles if c.horario != candle_fechado.horario]
            historico_candles.append(candle_fechado)
            historico_candles.sort(key=lambda c: c.horario)
            if _horarios_sinteticos:   # so conta aproximado dentro da janela dos indicadores
                _horarios_sinteticos.intersection_update(c.horario for c in historico_candles[-120:])
            if candles_aquecimento_restantes > 0:
                candles_aquecimento_restantes -= 1
                if candles_aquecimento_restantes == 0:
                    msg = "Aquecimento depois do buraco terminou. Novas entradas liberadas."
                    print(f"[{agora}] [INTEGRIDADE] {msg}")
                    narrar(msg)
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
                    entrada_dde_op = auditor.entradas_dde.get(posicao_antes.horario_entrada)
                    auditor.registrar_saida(
                        horario=agora, posicao=posicao_antes, motivo=motivo,
                        saida_teorica=saida_teorica, saida_dde=preco,
                        ordem_enviada=(ordem_ok or not cfg.ENVIAR_ORDENS),
                        contratos_dde=contratos_reais,
                    )
                    if ordem_ok or not cfg.ENVIAR_ORDENS:
                        resultado_pts, msg = _fechar_posicao_e_gravar_banca(preco_saida, motivo)
                        resultado_reais = resultado_pts * cfg.valor_ponto_total() - cfg.custo_total_operacao()
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
                        linha_caminho = caminho.fechar(
                            posicao_antes, agora, motivo, saida_teorica, preco,
                            preco_saida, resultado_pts, resultado_reais, entrada_dde=entrada_dde_op,
                        )
                        if registro_planilha:
                            leitor.registrar_fechamento_planilha(
                                posicao_antes, agora, preco_saida, motivo, resultado_pts, resultado_reais,
                                pico_reais=(linha_caminho or {}).get('pico_reais'),
                                devolveu_reais=((linha_caminho or {}).get('devolucao_pts') or 0) * cfg.valor_ponto_total() if linha_caminho else None,
                                banca=gestor.banca_atual,
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
                          f"Tendência={tendencia_fechamento} "
                          f"Fechamento a {distancia_fechamento:.0f} pts da MA21")   # V541: sem o "(limite 40)" antigo

                sinal = gestor.avaliar_candle(historico_candles)
                sinal_auditoria = sinal
                if sinal and _escalacao is not None and _escalacao.ultimo_titular:
                    print(f"[ESCALAÇÃO] A estratégia {_escalacao.ultimo_titular} foi escalada: {sinal.lado}.")
                if sinal:
                    row_fechamento = gestor.construir_row(historico_candles)
                    diagnostico_fechamento = (
                        diagnosticar_sinal(row_fechamento)
                        if diagnosticar_sinal is not None and row_fechamento is not None
                        else None
                    )
                    chave_fechamento = (
                        candle_fechado.horario,
                        diagnostico_fechamento.get("estrategia") if diagnostico_fechamento else None,
                        sinal.lado,
                    )
                    pode, motivo_bloqueio = gestor.pode_abrir_posicao(sinal.horario)
                    if pode and candles_aquecimento_restantes > 0:
                        pode = False
                        motivo_bloqueio = (f"BURACO NA BASE DE DADOS - entradas bloqueadas "
                                           f"({candles_aquecimento_restantes} candles restantes)")
                    if pode:
                        # V461: limite de risco por operacao ANTES de enviar ordem
                        pode, motivo_bloqueio = gestor.validar_risco_inicial(sinal, row_fechamento)
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
                                if publicador_radar is not None:
                                    publicador_radar.capturar(sinal.lado)   # V546: "Alvo capturado" no radar
                                registrador.registrar_operacao_aberta(gestor.posicao_aberta)
                                if registro_planilha:
                                    leitor.registrar_abertura_planilha(gestor.posicao_aberta)
                                email_notificacao.notificar_abertura(gestor.posicao_aberta, agora)
                                narrar(
                                    f"A ordem de {sinal.lado.lower()} foi enviada após "
                                    "a confirmação do candle. A posição foi aberta."
                                )
                                if _escalacao is not None and _escalacao.ultimo_titular:
                                    # V509: quem foi escalada e assumiu a posicao
                                    nome_escalada = (diagnostico_fechamento.get("estrategia")
                                                     if diagnostico_fechamento else None) or _escalacao.ultimo_titular
                                    narrar(f"A estratégia {nome_escalada} foi escalada e assumiu a posição.")
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
                        if candles_aquecimento_restantes > 0:
                            narrar(
                                f"O sinal de {sinal.lado.lower()} foi confirmado, mas a entrada "
                                f"está BLOQUEADA por buraco na base de dados, restam "
                                f"{candles_aquecimento_restantes} candles. {_instrucao_liberar()}"
                            )
                        else:
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
                        narrar(frase_candle)   # V513: sem a frase final "Nenhum sinal de entrada foi confirmado."
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
        print("[MODO REPLAY] O historico acumulado NAO sera gravado (so leitura); o arquivo real fica intacto.")

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

    # V543: numero de contratos da sessao. Multiplica valor do ponto e custo em todo o calculo
    # ao vivo (resultado da operacao, banca, painel, planilha). Enter = 1.
    while True:
        _contratos = cfg.interpretar_contratos(input("Com quantos contratos vai operar? [Enter = 1]: "))
        if _contratos is not None:
            break
        print(f"Resposta nao reconhecida - digite um numero inteiro de 1 a {cfg.CONTRATOS_MAXIMO}.")
    cfg.CONTRATOS = _contratos
    print(f"[CONTRATOS] {_contratos} contrato(s): R${cfg.valor_ponto_total():.2f} por ponto, "
          f"custo estimado de R${cfg.custo_total_operacao():.2f} por operacao.")
    if cfg.ENVIAR_ORDENS and not _MODO_REPLAY:
        print(f"[CONTRATOS] ATENCAO: o robo NAO altera a quantidade no Profit. Confira se a boleta "
              f"esta com {_contratos} contrato(s) antes de operar.")
    print("=" * 60)

    if cfg.ENVIAR_ORDENS:
        print("ATENCAO: ENVIAR_ORDENS=True - ordens reais serao enviadas ao Profit.")
    else:
        print("Modo somente alerta/registro. Nenhuma ordem real sera enviada.")
    rodar()

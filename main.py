# ARQUIVO: main.py
# ROBONILDO_102 — CONSENSO TÉCNICO + FLUXO (ANALÍTICO, SEM REGRAS DE HORÁRIO)

import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"  # remove "Hello from pygame..."

import time
import csv
import config
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from visao.pipeline import PipelineVisao
from ia.decisor_openai import DecisorOpenAI
from narracao.voz_seletor import VozSeletor
from narracao.narrador import Narrador

TZ = ZoneInfo("America/Sao_Paulo")

# >>> Você pode manter fixo aqui, ou depois ler do topo do gráfico (visão/OCR)
TIMEFRAME_ANALISE = "30M"

# Loop / ritmo
INTERVALO_CICLO = 6.0  # captura/IA a cada ~6s (ajuste fino)
INTERVALO_COMENTARIO_TECNICO = getattr(config, "INTERVALO_COMENTARIO_ANDAMENTO", 300)
INTERVALO_COMENTARIO_FLUXO = getattr(config, "INTERVALO_COMENTARIO_ANDAMENTO", 300)

# Consenso
MIN_CONF_PARA_OPERAR = 0.65         # só considera operar acima disso
MIN_CONF_PARA_FALAR_DECISAO = 0.55  # narrador pode falar decisão (sem operar) acima disso

# Log
PASTA_LOGS = Path("logs")
CAMINHO_LOG = PASTA_LOGS / "decisoes_102.csv"

OFFSET_GRAFICO = {
    "x": 80,
    "y": 120,
    "width": 1200,
    "height": 700
}


def _garantir_logs():
    PASTA_LOGS.mkdir(parents=True, exist_ok=True)
    if not CAMINHO_LOG.exists():
        with open(CAMINHO_LOG, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow([
                "timestamp",
                "timeframe",
                "acao_ia",
                "confianca",
                "market_status",
                "session_mode",
                "motivo_curto",
                "consenso_tecnico",
                "consenso_fluxo",
                "acao_final"
            ])


def _logar(decisao, acao_final: str, consenso_tecnico: bool, consenso_fluxo: bool):
    ts = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
    acao = str(getattr(decisao, "action", "AGUARDAR") or "AGUARDAR").upper()
    conf = float(getattr(decisao, "confidence", 0.0) or 0.0)
    motivo = str(getattr(decisao, "reason_short", "") or "")
    market_status = str(getattr(decisao, "market_status", "DESCONHECIDO") or "DESCONHECIDO").upper()
    session_mode = str(getattr(decisao, "session_mode", "DESCONHECIDO") or "DESCONHECIDO").upper()

    with open(CAMINHO_LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow([
            ts,
            TIMEFRAME_ANALISE,
            acao,
            round(conf, 3),
            market_status,
            session_mode,
            motivo,
            int(consenso_tecnico),
            int(consenso_fluxo),
            acao_final
        ])


def _is_replay(decisao) -> bool:
    # Detecção leve e objetiva (sem governança de horário agora)
    session_mode = str(getattr(decisao, "session_mode", "") or "").upper()
    if session_mode.startswith("REPLAY"):
        return True

    motivo = (str(getattr(decisao, "reason_short", "") or "") + " " +
              str(getattr(decisao, "notes", "") or "")).lower()
    return "replay" in motivo or "simul" in motivo


def _normalizar_acao(a: str) -> str:
    a = str(a or "").strip().upper()
    if a in ("BUY", "COMPRA"):
        return "COMPRAR"
    if a in ("SELL", "VENDA"):
        return "VENDER"
    if a in ("CLOSE", "ZERAR", "SAIR"):
        return "ENCERRAR"
    if a in ("AGUARDAR", "WAIT", "ESPERAR", ""):
        return "AGUARDAR"
    return "AGUARDAR"


def _normalizar_status(s: str) -> str:
    s = str(s or "").strip().upper()
    if s in ("LEILAO", "LEILÃO", "AUCTION"):
        return "LEILAO"
    if s in ("NORMAL", "ABERTO", "TRADING", "MERCADO", "OPEN"):
        return "NORMAL"
    return "DESCONHECIDO"


def _comentario_tecnico(decisao) -> str:
    """
    Comentário do 'grafista': regiões, gatilhos técnicos, timeframe.
    Aqui ele se baseia no motivo curto retornado pela IA e reforça disciplina.
    """
    acao = _normalizar_acao(getattr(decisao, "action", "AGUARDAR"))
    conf = float(getattr(decisao, "confidence", 0.0) or 0.0)
    motivo = str(getattr(decisao, "reason_short", "") or "").strip()

    if _is_replay(decisao):
        return f"No {TIMEFRAME_ANALISE}, estou em replay. Vou focar em regiões e estrutura, sem pressa. {motivo}".strip()

    if acao == "AGUARDAR":
        return f"No {TIMEFRAME_ANALISE}, ainda não vi gatilho limpo. Vou esperar preço entrar numa região melhor. {motivo}".strip()

    if conf < MIN_CONF_PARA_OPERAR:
        return f"Eu até vejo um cenário, mas falta convicção no {TIMEFRAME_ANALISE}. Melhor aguardar confirmação. {motivo}".strip()

    return f"Gatilho técnico no {TIMEFRAME_ANALISE} parece se formando. Se confirmar região, dá para {acao.lower()}. {motivo}".strip()


def _comentario_fluxo(decisao) -> str:
    """
    Comentário do 'tape reading' (por enquanto via tela/IA).
    Depois a gente evolui para BO/T&T por captura dedicada.
    """
    acao = _normalizar_acao(getattr(decisao, "action", "AGUARDAR"))
    conf = float(getattr(decisao, "confidence", 0.0) or 0.0)
    motivo = str(getattr(decisao, "reason_short", "") or "").strip()

    if _is_replay(decisao):
        return f"Fluxo em replay não valida execução. Vou só observar agressão/ritmo visual. {motivo}".strip()

    if acao == "AGUARDAR":
        return f"Fluxo ainda não está 'gritando'. Melhor segurar e esperar o mercado mostrar intenção. {motivo}".strip()

    if conf < MIN_CONF_PARA_OPERAR:
        return f"Não sinto pressão suficiente para executar agora. Falta intenção clara. {motivo}".strip()

    return f"Estou vendo intenção surgindo. Se o ritmo confirmar, dá para {acao.lower()} com disciplina. {motivo}".strip()


def _consenso_tecnico(decisao) -> bool:
    acao = _normalizar_acao(getattr(decisao, "action", "AGUARDAR"))
    conf = float(getattr(decisao, "confidence", 0.0) or 0.0)
    if _is_replay(decisao):
        return False
    if acao not in ("COMPRAR", "VENDER"):
        return False
    return conf >= MIN_CONF_PARA_OPERAR


def _consenso_fluxo(decisao) -> bool:
    # Por enquanto, como o "fluxo" ainda vem via IA/tela, usamos regra espelhada.
    # Depois que você colocar BO/T&T visível, a gente separa a leitura e o critério.
    acao = _normalizar_acao(getattr(decisao, "action", "AGUARDAR"))
    conf = float(getattr(decisao, "confidence", 0.0) or 0.0)
    if _is_replay(decisao):
        return False
    if acao not in ("COMPRAR", "VENDER"):
        return False
    return conf >= MIN_CONF_PARA_OPERAR


def main():
    print("ROBONILDO_102 iniciado (CONSENSO TÉCNICO + FLUXO)")
    print(f"Timeframe observado: {TIMEFRAME_ANALISE}\n")

    _garantir_logs()

    # =========================
    # VISÃO + IA
    # =========================
    visao = PipelineVisao(OFFSET_GRAFICO, nome_tela_profit=config.NOME_TELA_PROFIT)
    ia = DecisorOpenAI(modelo="gpt-5-mini")

    # =========================
    # VOZES (3 pessoas)
    # =========================

    # 1) NARRADOR PRINCIPAL (onyx)
    config.OPENAI_TTS_VOICE = "onyx"
    voz_narrador = VozSeletor()
    narrador = Narrador(voz_narrador, cooldown=2.0, nome="NARRADOR")

    # 2) COMENTARISTA TÉCNICO (shimmer)
    config.OPENAI_TTS_VOICE = "shimmer"
    voz_tecnico = VozSeletor()
    tecnico = Narrador(voz_tecnico, cooldown=INTERVALO_COMENTARIO_TECNICO, nome="TECNICO")

    # 3) COMENTARISTA DE FLUXO (sage) — você pode trocar por "cedar" se quiser mais grave
    config.OPENAI_TTS_VOICE = "sage"
    voz_fluxo = VozSeletor()
    fluxo = Narrador(voz_fluxo, cooldown=INTERVALO_COMENTARIO_FLUXO, nome="FLUXO")

    # fala inicial curta
    narrador.falar("Robonildo iniciado. Vou esperar o momento certo.", force=True)

    ultimo_tecnico = 0.0
    ultimo_fluxo = 0.0

    while True:
        inicio = time.time()
        try:
            frame, erro = visao.capturar_grafico()
            if erro:
                narrador.falar("Falha na captura do gráfico. Vou aguardar.", force=True)
                time.sleep(2)
                continue

            print("[IA] Consultando IA...")
            decisao = ia.decidir(frame_bgra=frame, timeframe=TIMEFRAME_ANALISE)

            acao = _normalizar_acao(getattr(decisao, "action", "AGUARDAR"))
            conf = float(getattr(decisao, "confidence", 0.0) or 0.0)
            motivo = str(getattr(decisao, "reason_short", "") or "").strip()

            market_status = _normalizar_status(getattr(decisao, "market_status", "DESCONHECIDO"))
            replay = _is_replay(decisao)

            print(f"[IA] {acao} | CONF={int(conf*100)}% | STATUS={market_status} | REPLAY={replay} | {motivo}")

            # Comentários pontuais (não spam)
            agora_ts = time.time()

            if (agora_ts - ultimo_tecnico) >= INTERVALO_COMENTARIO_TECNICO:
                tecnico.falar(_comentario_tecnico(decisao))
                ultimo_tecnico = agora_ts

            if (agora_ts - ultimo_fluxo) >= INTERVALO_COMENTARIO_FLUXO:
                fluxo.falar(_comentario_fluxo(decisao))
                ultimo_fluxo = agora_ts

            # Consenso para executar (sem horário; mas respeita REPLAY e LEILAO)
            consenso_tecnico = _consenso_tecnico(decisao)
            consenso_fluxo = _consenso_fluxo(decisao)

            acao_final = "AGUARDAR"

            if market_status == "LEILAO":
                acao_final = "AGUARDAR"
                # narrador só avisa se for algo relevante
                if conf >= MIN_CONF_PARA_FALAR_DECISAO:
                    narrador.falar("Mercado em leilão. Eu não opero agora.", force=True)

            elif replay:
                acao_final = "AGUARDAR"
                # sem falar toda hora em replay
                if conf >= 0.85:
                    narrador.falar("Replay detectado. Vou apenas observar e aprender o padrão.", force=True)

            else:
                if consenso_tecnico and consenso_fluxo and acao in ("COMPRAR", "VENDER"):
                    acao_final = acao
                    narrador.falar(f"CONSENSO fechado. {motivo}. Ação: {acao_final}.", force=True)

                    # Execução real (se você quiser)
                    if getattr(config, "ENVIAR_ORDENS", False):
                        try:
                            from operacao.executa_ordem import executar_ordem
                            _, msg = executar_ordem(acao_final)
                            print(f"[ORDENS] {msg}")
                        except Exception as e:
                            print(f"[ORDENS][ERRO] {repr(e)}")
                            narrador.falar("Tive erro ao enviar a ordem. Vou continuar monitorando.", force=True)
                    else:
                        print("[ORDENS] ENVIAR_ORDENS=False (simulação).")

                else:
                    acao_final = "AGUARDAR"
                    # narrador não fala sempre; só se a confiança estiver razoável e a IA tiver motivo relevante
                    if conf >= MIN_CONF_PARA_FALAR_DECISAO and acao in ("COMPRAR", "VENDER"):
                        narrador.falar(f"Quase. Falta consenso. {motivo}. Vou aguardar.", force=True)

            _logar(decisao, acao_final, consenso_tecnico, consenso_fluxo)

        except KeyboardInterrupt:
            print("\n[OK] Encerrado pelo usuário (Ctrl+C).")
            return
        except Exception as e:
            print("[ERRO]", repr(e))
            # fala curta, sem spam
            try:
                narrador.falar("Erro no ciclo. Continuando monitoramento.", force=True)
            except Exception:
                pass

        duracao = time.time() - inicio
        time.sleep(max(0.05, INTERVALO_CICLO - duracao))


if __name__ == "__main__":
    main()

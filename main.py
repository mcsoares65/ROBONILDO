# ARQUIVO: main.py
# PROJETO: ROBONILDO_102
# MODO: MONITORAMENTO com ESTADO + REGRAS DE PREGÃO + BLOQUEIO DE LEILÃO
# Fluxo: ver → IA decide → valida por regras → narração → log

import time
import csv
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from visao.pipeline import PipelineVisao
from ia.decisor_openai import DecisorOpenAI
from narracao.voz import Voz
from narracao.narrador import NarradorOficial

from operacao.estado_operacao import EstadoOperacao
from regras.pregao import RegrasPregao


# ==============================
# CONFIGURAÇÕES
# ==============================

TIMEFRAME_ANALISE = "30m"
TZ_LOCAL = ZoneInfo("America/Sao_Paulo")

OFFSET_GRAFICO = {
    "x": 80,
    "y": 120,
    "width": 1200,
    "height": 700
}

SMOKE_TEST = False
INTERVALO_CICLO = 6.0

# Narração
LIMIAR_FALA_CONFIANCA = 0.55

PASTA_LOGS = Path("logs")
CAMINHO_LOG = PASTA_LOGS / "decisoes_102.csv"

MODELO_OPENAI = "gpt-5-mini"


# ==============================
# LOG
# ==============================

def garantir_logs():
    PASTA_LOGS.mkdir(parents=True, exist_ok=True)


def registrar_decisao(decisao, acao_final: str, estado: EstadoOperacao, market_status: str):
    existe = CAMINHO_LOG.exists()

    with open(CAMINHO_LOG, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")

        if not existe:
            writer.writerow([
                "timestamp",
                "acao_ia",
                "acao_final",
                "posicao",
                "preco_entrada",
                "entrou_em",
                "preco_saida",
                "saiu_em",
                "confianca",
                "status",
                "motivo"
            ])

        entrou_em = estado.entrou_em.strftime("%Y-%m-%d %H:%M:%S") if estado.entrou_em else ""
        saiu_em = estado.saiu_em.strftime("%Y-%m-%d %H:%M:%S") if estado.saiu_em else ""

        writer.writerow([
            datetime.now(TZ_LOCAL).strftime("%Y-%m-%d %H:%M:%S"),
            getattr(decisao, "action", ""),
            acao_final,
            estado.posicao,
            estado.preco_entrada if estado.preco_entrada is not None else "",
            entrou_em,
            estado.preco_saida if estado.preco_saida is not None else "",
            saiu_em,
            round(decisao.confidence, 2),
            market_status,
            decisao.reason_short
        ])


# ==============================
# HELPERS
# ==============================

def tempo_para_falar(texto: str) -> float:
    return max(2.0, min(12.0, len(texto) / 14.0))


def normalizar_acao(acao: str) -> str:
    if not acao:
        return "AGUARDAR"
    a = str(acao).strip().upper()

    if a in ("AGUARDAR", "ESPERAR", "WAIT"):
        return "AGUARDAR"
    if a in ("COMPRAR", "COMPRA", "BUY"):
        return "COMPRAR"
    if a in ("VENDER", "VENDA", "SELL"):
        return "VENDER"
    if a in ("SAIR", "ENCERRAR", "ZERAR", "CLOSE"):
        return "ENCERRAR"

    return "AGUARDAR"


def normalizar_status(status: str) -> str:
    if not status:
        return "DESCONHECIDO"
    s = str(status).strip().upper()
    if s in ("LEILAO", "LEILÃO", "AUCTION"):
        return "LEILAO"
    if s in ("NORMAL", "ABERTO", "TRADING", "MERCADO"):
        return "NORMAL"
    return "DESCONHECIDO"


def normalizar_session_mode(session_mode: str) -> str:
    if not session_mode:
        return "DESCONHECIDO"
    s = str(session_mode).strip().upper()
    if s.startswith("REPLAY"):
        return "REPLAY"
    if s in ("AO_VIVO", "AOVIVO", "NORMAL", "LIVE"):
        return "AO_VIVO"
    return "DESCONHECIDO"


def decidir_acao_final(acao_norm: str, estado: EstadoOperacao) -> str:
    """
    Regra central:
    - se SEM_POSICAO: COMPRAR abre comprado; VENDER abre vendido; AGUARDAR espera
    - se VENDIDO: VENDER => MANTER; COMPRAR => ENCERRAR; AGUARDAR => MANTER
    - se COMPRADO: COMPRAR => MANTER; VENDER => ENCERRAR; AGUARDAR => MANTER
    """
    if estado.posicao == "SEM_POSICAO":
        if acao_norm in ("COMPRAR", "VENDER"):
            return acao_norm
        return "AGUARDAR"

    if estado.posicao == "VENDIDO":
        if acao_norm == "COMPRAR":
            return "ENCERRAR"
        return "MANTER"

    if estado.posicao == "COMPRADO":
        if acao_norm == "VENDER":
            return "ENCERRAR"
        return "MANTER"

    return "AGUARDAR"


def detectar_tarja_amarela_leilao(frame, altura=50, limiar_percentual=0.08) -> bool:
    """Detecta a tarja amarela de leilão no topo do ProfitPro."""
    try:
        import numpy as np
        import cv2
    except Exception:
        return False

    if frame is None:
        return False

    if frame.ndim == 3 and frame.shape[2] == 4:
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
    else:
        frame_bgr = frame

    topo = frame_bgr[:altura, :, :]
    if topo.size == 0:
        return False

    b, g, r = cv2.split(topo)
    mask_amarelo = (r > 200) & (g > 200) & (b < 170)
    proporcao = mask_amarelo.mean()
    return proporcao >= limiar_percentual


# ==============================
# MAIN
# ==============================

def main():
    modo = "SMOKE TEST" if SMOKE_TEST else "MONITORAMENTO"
    print(f"ROBONILDO_102 iniciado ({modo}).")
    print("Fluxo: ver → IA decide → valida regras → narração → log\n")

    garantir_logs()

    visao = PipelineVisao(OFFSET_GRAFICO)
    ia = DecisorOpenAI(modelo=MODELO_OPENAI)

    voz = Voz()
    narrador = NarradorOficial(voz, cooldown=1.0)

    estado = EstadoOperacao()
    pregao = RegrasPregao(hora_inicio=datetime.strptime("09:01", "%H:%M").time(),
                          hora_fim=datetime.strptime("18:20", "%H:%M").time(),
                          margem_zeragem_min=2)

    falou_fora_horario_ts = 0.0

    while True:
        ciclo_inicio = time.time()
        agora = datetime.now(TZ_LOCAL)

        try:
            # 1) Captura
            frame, erro = visao.capturar_grafico()
            if erro:
                print("[ERRO VISAO]", erro)
                narrador.falar("Falha ao capturar o gráfico. Vou aguardar.", force=True)
                time.sleep(3)
                if SMOKE_TEST:
                    return
                continue

            print("[OK] Captura realizada. Shape:", getattr(frame, "shape", None))

            # 2) IA decide (deve retornar também market_status)
            decisao = ia.decidir(frame_bgra=frame, timeframe=TIMEFRAME_ANALISE)

            acao_norm = normalizar_acao(getattr(decisao, "action", ""))
            market_status = normalizar_status(getattr(decisao, "market_status", "DESCONHECIDO"))
            session_mode = normalizar_session_mode(getattr(decisao, "session_mode", "DESCONHECIDO"))

            leilao_visual = detectar_tarja_amarela_leilao(frame)
            if leilao_visual:
                market_status = "LEILAO"

            em_replay = session_mode == "REPLAY"

            # 0) Regra de horário (valida apenas se não for replay)
            if not em_replay and not pregao.dentro_horario(agora):
                if estado.esta_aberto():
                    msg = "Fora do horário do pregão e há posição aberta. Encerrar imediatamente por segurança."
                    print("[HORARIO]", msg)
                    narrador.falar(msg, force=True)
                    time.sleep(tempo_para_falar(msg))
                    estado.aplicar_acao("ENCERRAR", agora, getattr(decisao, "price_now", None))
                    registrar_decisao(decisao, "ENCERRAR", estado, market_status)
                else:
                    if (time.time() - falou_fora_horario_ts) > 120:
                        narrador.falar("Fora do horário. Aguardando abertura do pregão.", force=True)
                        falou_fora_horario_ts = time.time()

                time.sleep(10)
                if SMOKE_TEST:
                    return
                continue

            # 0.1) Perto do encerramento: se tiver posição, encerrar
            if not em_replay and pregao.perto_de_encerrar(agora) and estado.esta_aberto():
                msg = "Pregão perto do encerramento. Vou encerrar a posição agora para evitar zeragem."
                print("[ENCERRAMENTO]", msg)
                narrador.falar(msg, force=True)
                time.sleep(tempo_para_falar(msg))
                estado.aplicar_acao("ENCERRAR", agora, getattr(decisao, "price_now", None))
                registrar_decisao(decisao, "ENCERRAR", estado, market_status)

                time.sleep(2)
                if SMOKE_TEST:
                    return
                continue

            # 2.1) Leilão: não faz nada
            if market_status == "LEILAO":
                msg = "Mercado em leilão. Não vou operar. Aguardando normalizar."
                print("[LEILAO]", msg)
                narrador.falar("Mercado em leilão.", force=True)
                registrar_decisao(decisao, "AGUARDAR", estado, market_status)

                time.sleep(5)
                if SMOKE_TEST:
                    return
                continue

            # 2.2) Posição aberta: restringe a IA para sair/manter
            if estado.posicao == "COMPRADO" and acao_norm == "COMPRAR":
                acao_norm = "AGUARDAR"
            if estado.posicao == "VENDIDO" and acao_norm == "VENDER":
                acao_norm = "AGUARDAR"

            # 3) Máquina de estados: ação final respeitando posição
            acao_final = decidir_acao_final(acao_norm, estado)

            print(
                f"[IA] AÇÃO={acao_norm} | FINAL={acao_final} | POS={estado.posicao} | "
                f"CONF={int(decisao.confidence * 100)}% | STATUS={market_status} | "
                f"MODO={session_mode} | MOTIVO={decisao.reason_short}"
            )

            # 4) Atualiza estado (simulado por enquanto — no futuro liga na execução real)
            estado.aplicar_acao(acao_final, agora, getattr(decisao, "price_now", None))

            # 5) Log
            registrar_decisao(decisao, acao_final, estado, market_status)
            print(f"[OK] Log gravado em: {CAMINHO_LOG}")

            # 6) Narração (sempre curta)
            # Regra: fala quando for abrir/encerrar; se for manter/aguardar só fala com confiança boa
            if acao_final in ("COMPRAR", "VENDER", "ENCERRAR"):
                texto_fala = f"{decisao.reason_short} Ação: {acao_final}."
                narrador.falar(texto_fala, force=True)
                time.sleep(tempo_para_falar(texto_fala))
            else:
                if decisao.confidence >= 0.70:
                    texto_fala = f"{decisao.reason_short} Ação: {acao_final}."
                    narrador.falar(texto_fala, force=True)
                    time.sleep(tempo_para_falar(texto_fala))

            # 7) Encerrar no smoke test
            if SMOKE_TEST:
                print("[OK] Smoke test finalizado (1 ciclo). Encerrando.")
                time.sleep(1)
                return

        except KeyboardInterrupt:
            print("\n[OK] Encerrado pelo usuário (Ctrl+C).")
            return

        except Exception as e:
            print("[ERRO GERAL] Exceção no ciclo:", repr(e))
            narrador.falar("Ocorreu um erro no ciclo. Vou me recuperar e continuar.", force=True)
            time.sleep(2)

        # Intervalo estável
        duracao = time.time() - ciclo_inicio
        espera = max(0.05, INTERVALO_CICLO - duracao)
        time.sleep(espera)


if __name__ == "__main__":
    main()

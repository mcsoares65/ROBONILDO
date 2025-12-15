# ARQUIVO: main.py
# PROJETO: ROBONILDO_102 (estável / monitoramento)
# Fluxo: ver → IA decide → valida regras → narração → log (loop)

import time
import csv
from datetime import datetime, time as dtime
from pathlib import Path

from visao.pipeline import PipelineVisao
from ia.decisor_openai import DecisorOpenAI
from narracao.voz import Voz
from narracao.narrador import NarradorOficial

from operacao.estado_operacao import EstadoOperacao, carregar_estado, salvar_estado
from regras.pregao import dentro_horario_pregao, esta_perto_do_fechamento
from visao.captura_janela import detectar_tarjas_status  # se você já tem; se não tiver, comente


# ==============================
# CONFIG
# ==============================

TIMEFRAME_ANALISE = "30m"

OFFSET_GRAFICO = {
    "x": 80,
    "y": 120,
    "width": 1200,
    "height": 700
}

INTERVALO_CICLO = 6.0

PASTA_LOGS = Path("logs")
CAMINHO_LOG = PASTA_LOGS / "decisoes_102.csv"

MODELO_OPENAI = "gpt-5-mini"

# Narração
COOLDOWN_FALA = 1.0
LIMIAR_FALA_CONFIANCA = 0.65   # fala se confiança >= isso
KEEPALIVE_FALA_SEG = 30.0      # fala pelo menos 1x a cada Xs mesmo em AGUARDAR
TEMPO_MINIMO_AUDIO = 2.5       # pra não truncar em encerramentos rápidos


# ==============================
# LOG
# ==============================

def garantir_logs():
    PASTA_LOGS.mkdir(parents=True, exist_ok=True)

def registrar_decisao(decisao, acao_final: str, estado: EstadoOperacao, market_status: str, modo: str):
    existe = CAMINHO_LOG.exists()

    with open(CAMINHO_LOG, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        if not existe:
            writer.writerow([
                "timestamp", "acao_ia", "acao_final", "posicao",
                "confianca", "status", "modo", "motivo"
            ])

        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            decisao.action,
            acao_final,
            estado.posicao,
            round(decisao.confidence, 2),
            market_status,
            modo,
            decisao.reason_short
        ])


# ==============================
# REGRAS DE AÇÃO FINAL
# ==============================

def decidir_acao_final(decisao_ia, estado: EstadoOperacao, market_status: str, modo: str) -> str:
    """
    Retorna: AGUARDAR | COMPRAR | VENDER | MANTER | ZERAR
    Regras:
      - Se market_status indicar LEILAO → AGUARDAR (nunca entra)
      - Se posição aberta:
          - COMPRAR/VENDER repetido → MANTER
          - decisão contrária pode virar ZERAR (se você quiser fechar e inverter depois)
      - Horário do pregão só vale quando modo != REPLAY
      - Perto do fechamento (modo != REPLAY): se tem posição → ZERAR
    """
    # 1) LEILÃO trava tudo
    if market_status == "LEILAO":
        return "AGUARDAR" if estado.posicao == "SEM_POSICAO" else "MANTER"

    # 2) Horário: só se NÃO for replay
    if modo != "REPLAY":
        if not dentro_horario_pregao():
            # fora do pregão
            if estado.posicao != "SEM_POSICAO":
                return "ZERAR"
            return "AGUARDAR"

        # 3) Perto do fechamento: zera se tiver posição
        if esta_perto_do_fechamento() and estado.posicao != "SEM_POSICAO":
            return "ZERAR"

    # 4) Gestão de posição
    if estado.posicao == "SEM_POSICAO":
        # sem posição: pode executar compra/venda
        if decisao_ia.action in ("COMPRAR", "VENDER"):
            return decisao_ia.action
        return "AGUARDAR"

    # com posição:
    if estado.posicao == "COMPRADO":
        # se IA mandar comprar de novo ou aguardar → manter
        if decisao_ia.action in ("COMPRAR", "AGUARDAR"):
            return "MANTER"
        # se IA mandar vender → aqui você escolhe: ZERAR ou inverter
        return "ZERAR"

    if estado.posicao == "VENDIDO":
        if decisao_ia.action in ("VENDER", "AGUARDAR"):
            return "MANTER"
        return "ZERAR"

    return "AGUARDAR"


# ==============================
# NARRAÇÃO (quando falar)
# ==============================

def deve_falar(decisao, acao_final: str, estado: EstadoOperacao,
              last_acao_final: str, last_pos: str,
              last_fala_ts: float) -> bool:
    mudou_acao = (acao_final != last_acao_final)
    mudou_pos = (estado.posicao != last_pos)
    conf_alta = (decisao.confidence >= LIMIAR_FALA_CONFIANCA)
    keepalive = ((time.time() - last_fala_ts) >= KEEPALIVE_FALA_SEG)
    # fala quando:
    return mudou_acao or mudou_pos or conf_alta or keepalive


# ==============================
# MAIN LOOP
# ==============================

def main():
    print("ROBONILDO_102 iniciado (MONITORAMENTO).")
    print("Fluxo: ver → IA decide → valida regras → narração → log\n")

    garantir_logs()

    visao = PipelineVisao(OFFSET_GRAFICO)
    ia = DecisorOpenAI(modelo=MODELO_OPENAI)

    voz = Voz()
    narrador = NarradorOficial(voz, cooldown=COOLDOWN_FALA)

    estado = carregar_estado()  # EstadoOperacao(posicao="SEM_POSICAO", ...)
    last_acao_final = ""
    last_pos = estado.posicao
    last_fala_ts = 0.0

    while True:
        # 1) Captura
        frame, erro = visao.capturar_grafico()
        if erro:
            print("[ERRO VISAO]", erro)
            narrador.falar("Falha ao capturar o gráfico. Vou aguardar.", force=True)
            time.sleep(TEMPO_MINIMO_AUDIO)
            time.sleep(INTERVALO_CICLO)
            continue

        print("[OK] Captura realizada. Shape:", getattr(frame, "shape", None))

        # 2) Detectar status (leilão / normal / etc.)
        market_status = "DESCONHECIDO"
        try:
            # Se você já detecta a tarja amarela aqui:
            market_status = detectar_tarjas_status(frame)  # "LEILAO" | "NORMAL" | "OUTRO" | ...
        except Exception:
            pass

        # 3) Modo (REPLAY ou AO_VIVO)
        # Se você já tinha essa detecção por leitura (tarja "Replay"), mantenha.
        # Aqui vou manter simples: se seu sistema já imprime MODO=REPLAY, então você já tem isso em algum lugar.
        # Como fallback: se aparecer "Replay" na tarja superior do Profit, você detecta no seu pipeline/leitura.
        modo = getattr(estado, "modo", "REPLAY")  # fallback; ideal: detectar via leitura real

        # 4) IA decide
        decisao = ia.decidir(frame_bgra=frame, timeframe=TIMEFRAME_ANALISE)

        # 5) Ação final pelas regras
        acao_final = decidir_acao_final(decisao, estado, market_status, modo)

        print(
            f"[IA] AÇÃO={decisao.action} | FINAL={acao_final} | POS={estado.posicao} | "
            f"CONF={int(decisao.confidence * 100)}% | STATUS={market_status} | MODO={modo} | "
            f"MOTIVO={decisao.reason_short}"
        )

        # 6) Aplicar ação final (somente simulação aqui; integração real você já tem)
        # Aqui você já está fazendo: se ENVIAR_ORDENS=False, apenas simula.
        # Se quiser, você pluga operacao/executa_ordem.py aqui.
        if acao_final in ("COMPRAR", "VENDER", "ZERAR"):
            # atualiza estado local (posição)
            estado.aplicar_acao(acao_final)
            salvar_estado(estado)

            if acao_final == "COMPRAR":
                print("[ORDENS] Simulação: ENVIAR_ORDENS=False. Ordem não enviada.")
            elif acao_final == "VENDER":
                print("[ORDENS] Simulação: ENVIAR_ORDENS=False. Ordem não enviada.")
            elif acao_final == "ZERAR":
                print("[ORDENS] Simulação: ENVIAR_ORDENS=False. Zeragem não enviada.")
        else:
            # MANTER/AGUARDAR: só persiste estado se quiser (geralmente não precisa)
            pass

        # 7) Falar (mais inteligente, sem ficar tagarelando)
        if deve_falar(decisao, acao_final, estado, last_acao_final, last_pos, last_fala_ts):
            texto_fala = f"{decisao.reason_short} Ação: {acao_final}."
            narrador.falar(texto_fala, force=True)

            # evita truncar
            tempo_estimado = max(TEMPO_MINIMO_AUDIO, min(12.0, len(texto_fala) / 14.0))
            time.sleep(tempo_estimado)

            last_fala_ts = time.time()
            last_acao_final = acao_final
            last_pos = estado.posicao

        # 8) Log
        registrar_decisao(decisao, acao_final, estado, market_status, modo)
        print(f"[OK] Log gravado em: {CAMINHO_LOG}")

        # 9) Sleep
        time.sleep(INTERVALO_CICLO)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[OK] Encerrado pelo usuário (Ctrl+C).")

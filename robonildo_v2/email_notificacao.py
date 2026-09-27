"""
ROBONILDO - email_notificacao.py

Envia um e-mail de resumo a cada abertura/fechamento de posicao real.

PRINCIPIO (mesmo da V416 para narracao e noticias): isto e puramente
informativo, e NUNCA pode atrasar nem bloquear a decisao/execucao de uma
ordem. O envio roda numa thread separada, com timeout curto, e qualquer
falha (rede fora, credencial errada, servidor fora do ar) e silenciosa -
so imprime um aviso no terminal, nunca derruba o robo nem impede a proxima
operacao.

Configuracao em configuracao.py (EMAIL_NOTIFICACAO_*). Se
EMAIL_NOTIFICACAO_ATIVO for False (padrao), este modulo nao faz nada.
"""

import smtplib
import ssl
import threading
from email.mime.text import MIMEText
from email.utils import formatdate

import configuracao as cfg


def _lista_destinatarios() -> list:
    """
    EMAIL_NOTIFICACAO_DESTINATARIO aceita 1 ou mais e-mails, separados por
    vírgula (ex: "voce@gmail.com, socio@gmail.com"). Espaços em volta de
    cada um são ignorados; entradas vazias (vírgula sobrando) também.
    """
    bruto = getattr(cfg, "EMAIL_NOTIFICACAO_DESTINATARIO", "") or ""
    return [e.strip() for e in bruto.split(",") if e.strip()]


def _enviar_smtp(assunto: str, corpo: str):
    """Roda na thread separada - qualquer excecao fica contida aqui."""
    try:
        destinatarios = _lista_destinatarios()
        if not destinatarios:
            print("[EMAIL] AVISO: notificação ativa, mas EMAIL_NOTIFICACAO_DESTINATARIO "
                  "está vazio. Envio ignorado.")
            return

        msg = MIMEText(corpo, "plain", "utf-8")
        msg["Subject"] = assunto
        msg["From"] = cfg.EMAIL_NOTIFICACAO_REMETENTE
        msg["To"] = ", ".join(destinatarios)
        msg["Date"] = formatdate(localtime=True)

        contexto = ssl.create_default_context()
        with smtplib.SMTP(cfg.EMAIL_NOTIFICACAO_SERVIDOR_SMTP,
                           cfg.EMAIL_NOTIFICACAO_PORTA_SMTP,
                           timeout=cfg.EMAIL_NOTIFICACAO_TIMEOUT_SEGUNDOS) as servidor:
            servidor.starttls(context=contexto)
            servidor.login(cfg.EMAIL_NOTIFICACAO_REMETENTE, cfg.EMAIL_NOTIFICACAO_SENHA_APP)
            servidor.sendmail(cfg.EMAIL_NOTIFICACAO_REMETENTE,
                               destinatarios, msg.as_string())
        print(f"[EMAIL] Notificação enviada para {len(destinatarios)} "
              f"destinatário(s): {assunto!r}")
    except Exception as e:
        print(f"[EMAIL] AVISO: falha ao enviar notificação ({type(e).__name__}: {e}) - "
              f"a operação em si NÃO foi afetada.")


def notificar(assunto: str, corpo: str):
    """
    Dispara o envio em segundo plano e retorna na hora - nunca espera a
    rede responder. Chamar logo apos abrir/fechar uma posicao real.
    """
    if not getattr(cfg, "EMAIL_NOTIFICACAO_ATIVO", False):
        return
    if not getattr(cfg, "EMAIL_NOTIFICACAO_SENHA_APP", ""):
        print("[EMAIL] AVISO: notificação ativa, mas a variável "
              "ROBONILDO_EMAIL_SENHA_APP não foi definida. Envio ignorado.")
        return
    threading.Thread(target=_enviar_smtp, args=(assunto, corpo), daemon=True).start()


def _fmt_nivel(valor) -> str:
    """Regra 1 v10: o motor nao calcula mais stop/alvo - quem define e o
    cartucho de saida titular, consultado na abertura da posicao. Se o
    cartucho nao tiver definido nada ainda nesse instante, o nivel e
    genuinamente None - nao e um erro, e o e-mail precisa dizer isso em
    vez de quebrar tentando formatar None como numero."""
    return f"{valor:.2f}" if valor is not None else "(ainda não definido pelo cartucho de saída)"


def notificar_abertura(posicao, agora):
    """Resumo de abertura de posição - `posicao` é o objeto Posicao já
    aberto pelo motor (gestor.posicao_aberta, logo após abrir_posicao),
    NÃO o Sinal: desde a Regra 1 v10, Sinal.stop/alvo são sempre None (o
    motor não calcula mais nada) - só a Posicao carrega o nível real que
    o cartucho de saída titular definiu na abertura."""
    assunto = f"ROBONILDO - Posição {posicao.lado} aberta @ {posicao.entrada:.0f}"
    corpo = (
        f"Posição aberta\n"
        f"------------------------------------------\n"
        f"Horário: {agora.strftime('%d/%m/%Y %H:%M:%S')}\n"
        f"Lado: {posicao.lado}\n"
        f"Entrada: {posicao.entrada:.2f}\n"
        f"Stop: {_fmt_nivel(posicao.stop)}\n"
        f"Alvo: {_fmt_nivel(posicao.alvo)}\n"
        f"Motivo: {posicao.motivo_entrada}\n"
    )
    notificar(assunto, corpo)


def notificar_fechamento(posicao, motivo, preco_saida, resultado_pts, resultado_reais, agora):
    """Resumo de fechamento de posicao - posicao e o objeto Posicao (gestor.posicao_aberta
    ANTES de fechar), motivo e a razao do fechamento (ALVO/STOP/CORTE_SEGURANCA_LIMITE)."""
    resultado_texto = "LUCRO" if resultado_pts >= 0 else "PREJUÍZO"
    assunto = (
        f"ROBONILDO - Posição {posicao.lado} fechada ({motivo}) - "
        f"{resultado_texto} R${resultado_reais:.2f}"
    )
    corpo = (
        f"Posição fechada\n"
        f"------------------------------------------\n"
        f"Horário: {agora.strftime('%d/%m/%Y %H:%M:%S')}\n"
        f"Lado: {posicao.lado}\n"
        f"Entrada: {posicao.entrada:.2f}\n"
        f"Saída: {preco_saida:.2f}\n"
        f"Motivo do fechamento: {motivo}\n"
        f"Resultado: {resultado_pts:.1f} pontos (R${resultado_reais:.2f})\n"
    )
    notificar(assunto, corpo)

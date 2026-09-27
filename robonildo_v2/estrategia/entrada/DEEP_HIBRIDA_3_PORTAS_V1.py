"""
DEEP_HIBRIDA_3_PORTAS_V1 — claude_hibrida_macd_livre_v1 com terceira porta.

Base: claude_hibrida_macd_livre_v1 (#1, 9136.19). Insight vencedor: as
portas de ROM PIMENTO DE MOMENTUM (MACD) nao devem compartilhar os
bloqueios de horario calibrados na porta de REVERSAO EM SUPORTE (MA21).

Essa versao aplica o mesmo principio a uma terceira porta, tambem de
natureza de momentum/rompimento: cruzamento do estocastico saindo de
zona extrema (stoch_cross_up_20 / stoch_cross_down_80). Igual a porta
MACD, fica livre dos bloqueios de quinta-feira, almoco e 15h-17h.

Hipotese: se liberar UMA porta de momentum rendeu +2000, liberar uma
segunda porta do mesmo tipo pode rende mais, sem mexer no que ja
funciona (porta MA21 continua com todos os bloqueios originais).

Risco declarado: pode piorar o drawdown e a sequencia de perdas, como
ja aconteceu em claude_hibrida_macd_livre_v1. Nao e vitoria garantida.

Autoria: gerado por IA (Claude, Anthropic) a pedido do usuario.
Revisao humana: obrigatoria antes de importar e rodar.
Status: candidata - NAO validada.

Contrato: gerar_sinal(row) -> 1 (compra), -1 (venda) ou 0 (sem operacao).
Colunas usadas: dt, trend, distancia_ma21, stoch, stoch_subindo,
stoch_descendo, stoch_cross_up_20, stoch_cross_down_80,
macd_cross_up, macd_cross_down.
"""

MAX_DISTANCIA_MA21 = 110.0
STOCH_MIN = 16.5
STOCH_MAX = 83.5


def _bloqueado_para_ma21(row) -> bool:
    ts = row['dt']
    if ts.weekday() == 3:  # quinta-feira
        return True
    hora = ts.strftime('%H:%M')
    if '12:00' <= hora <= '13:00':
        return True
    if '15:00' <= hora <= '16:59':
        return True
    return False


def gerar_sinal(row) -> int:
    trend = row['trend']
    if trend == 0:
        return 0

    # Porta 1: pullback na MA21 — bloqueios de horario completos.
    if not _bloqueado_para_ma21(row):
        if (
            row['distancia_ma21'] <= MAX_DISTANCIA_MA21
            and STOCH_MIN <= row['stoch'] <= STOCH_MAX
        ):
            if trend == 1 and row['stoch_subindo']:
                return 1
            if trend == -1 and row['stoch_descendo']:
                return -1

    # Porta 2: cruzamento do MACD — livre de bloqueios (rompimento).
    if trend == 1 and row['macd_cross_up']:
        return 1
    if trend == -1 and row['macd_cross_down']:
        return -1

    # Porta 3: cruzamento do estocastico saindo de extremo — livre
    # de bloqueios (tambem rompimento, nao reversao em suporte).
    if trend == 1 and row['stoch_cross_up_20']:
        return 1
    if trend == -1 and row['stoch_cross_down_80']:
        return -1

    return 0


__all__ = ['gerar_sinal']
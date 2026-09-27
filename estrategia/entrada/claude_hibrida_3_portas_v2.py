"""
laboratorio_estrategias/estrategias/claude_hibrida_3_portas_v2.py

CLAUDE_HIBRIDA_3_PORTAS_v2 - autoria: gerada por Claude (Anthropic), a
pedido do usuario, em resposta ao desafio de superar a
DEEP_HIBRIDA_3_PORTAS_V1. Revisao humana: obrigatoria antes de importar e
rodar. Status: candidata - numeros abaixo rodados no motor real antes
desta declaracao.

Origem transparente: mesma base de 3 portas da DEEP_HIBRIDA_3_PORTAS_V1
(porta 1: pullback na MA21 com bloqueios de horario; porta 2: cruzamento
do MACD, livre de bloqueios; porta 3: cruzamento do estocastico saindo de
extremo - stoch_cross_up_20/stoch_cross_down_80 -, tambem livre de
bloqueios). A UNICA mudanca: a porta 3 (a mais "crua" das tres, sem
nenhum filtro de qualidade proprio) passa a exigir o mesmo teto de corpo
de candle ja usado pela Manus_LPM_V7 (corpo <= 77.5% do range) - rejeita
candle de exaustao/marubozu no exato momento do cruzamento.

Confirmado antes de aplicar o filtro: a porta 3 e genuinamente
independente da porta MACD (so 3 candles de sobreposicao em 317 sinais
brutos) - nao e redundancia disfarçada.

Comparacao direta (12 meses, motor real):
    DEEP_HIBRIDA_3_PORTAS_V1: N=331  PF agr/trei/teste=1.72/1.73/1.70
                              Total R$10.699,42  DD -R$879,98  SeqPerdas=8
    Esta versao (v2):         N=314  PF agr/trei/teste=1.89/1.86/2.06
                              Total R$11.399,44  DD -R$638,82  SeqPerdas=7

Diferente da troca anterior (2 portas -> 3 portas, que trocou PF por
volume), esta e uma vitoria em TODOS os eixos ao mesmo tempo: mais lucro,
PF melhor nos tres recortes, drawdown menor, sequencia de perdas menor.
O filtro nao so cortou trades ruins da porta 3 como reduziu o risco
agregado da estrategia inteira.

Contrato: gerar_sinal(row) -> 1 (compra), -1 (venda) ou 0 (sem operacao).
Colunas usadas: dt, trend, distancia_ma21, stoch, stoch_subindo,
stoch_descendo, stoch_cross_up_20, stoch_cross_down_80, macd_cross_up,
macd_cross_down, Abertura, Fechamento, Maximo, Minimo - todas
documentadas em _template.py / indicadores.py.
"""

MAX_DISTANCIA_MA21 = 110.0
STOCH_MIN = 16.5
STOCH_MAX = 83.5
CORPO_MAXIMO_RELATIVO = 0.775


def _bloqueado_para_ma21(row) -> bool:
    """Bloqueios validados olhando so a porta MA21 (reversao em suporte) -
    nao se aplicam as portas de momentum/rompimento (MACD, estocastico)."""
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

    # Porta 1: pullback na MA21 - com bloqueios de horario completos.
    if not _bloqueado_para_ma21(row):
        if (
            row['distancia_ma21'] <= MAX_DISTANCIA_MA21
            and STOCH_MIN <= row['stoch'] <= STOCH_MAX
        ):
            if trend == 1 and row['stoch_subindo']:
                return 1
            if trend == -1 and row['stoch_descendo']:
                return -1

    # Porta 2: cruzamento do MACD - livre de bloqueios (rompimento).
    if trend == 1 and row['macd_cross_up']:
        return 1
    if trend == -1 and row['macd_cross_down']:
        return -1

    # Porta 3: cruzamento do estocastico saindo de extremo - livre de
    # bloqueios, mas agora exige candle sem corpo de exaustao.
    amplitude = row['Maximo'] - row['Minimo']
    if amplitude <= 0:
        return 0
    if abs(row['Fechamento'] - row['Abertura']) > CORPO_MAXIMO_RELATIVO * amplitude:
        return 0

    if trend == 1 and row['stoch_cross_up_20']:
        return 1
    if trend == -1 and row['stoch_cross_down_80']:
        return -1

    return 0


__all__ = ['gerar_sinal']

"""Saída Claude V6 — encerra no lucro quando o movimento reverte.

Candidata S001. NÃO é titular.

Autoria: Claude (Anthropic), a pedido do dono do laboratório em 30/09/2026.
Origem: ata `conselho/2026-09-30-O.txt`.

---------------------------------------------------------------------------
O QUE ESTA SAÍDA FAZ DE DIFERENTE
---------------------------------------------------------------------------
O laboratório já testou 59 variantes de proteção de lucro. Todas pertencem a
uma única família: **reposicionar um nível de preço** (breakeven, trailing
por distância, trailing estrutural, risco fixo em pontos, risco por ATR,
desistência por N candles, trava condicionada ao tamanho do risco). Nenhuma
delas melhorou o retorno ajustado ao risco, em nenhuma calibragem.

Esta saída pertence a outra família: **encerrar quando o movimento que
justificou a entrada acaba**. O motor já entrega os sinais de reversão no
`row` e o cartucho de entrada os utiliza — mas nenhuma saída em produção
jamais consultou qualquer um deles.

O gatilho escolhido é o estocástico saindo da zona extrema:

    COMPRA  -> row["stoch_cross_down_80"]   (estocástico cruzando 80 para baixo)
    VENDA   -> row["stoch_cross_up_20"]     (estocástico cruzando 20 para cima)

Só age **no lucro**. Reversão em prejuízo continua sendo trabalho do stop —
sair no vermelho por sinal de indicador é a armadilha que derrubou as 59
variantes anteriores.

---------------------------------------------------------------------------
O QUE FOI MEDIDO (motor oficial, dois períodos, par entrada_grok_3_v1)
---------------------------------------------------------------------------
Remedição em 01/10/2026, motor V459 (sem MAX_OPERACOES_DIA). Os números da
versão original (r/r 58,3 contra 53,5; dd -20%/-19%) foram medidos COM o teto
de 2 operações por dia e deixaram de valer quando ele foi removido (V459):

2026 (186 pregões operados):

    sem reversão (saida_chatgpt_v4) : R$ 17.013,59 | acerto 67,2% | dd -334 | r/r 50,9
    com este gatilho                : R$ 15.043,59 | acerto 70,2% | dd -301 | r/r 50,0

2023-2024:

    sem reversão (saida_chatgpt_v4) : R$   -292,89 | acerto 45,0% | dd -3.175
    com este gatilho                : R$   -234,34 | acerto 49,5% | dd -2.488

Leitura honesta: **custa resultado e compra risco, e a vantagem de retorno
ajustado ao risco desapareceu em 2026** (50,0 contra 50,9). Resta uma redução
de drawdown de -10% em 2026 e de -22% em 2023-2024, pagas com -R$ 1.970 em
2026. Não supera a base no total; quem quiser menos drawdown paga em resultado.

Nenhum parâmetro foi otimizado. O gatilho veio do que o motor já expõe, e as
constantes de stop/alvo/horário são as da `saida_chatgpt_v4`, copiadas sem
ajuste, para que a única diferença medida seja a saída por reversão.

---------------------------------------------------------------------------
CORREÇÃO HERDADA
---------------------------------------------------------------------------
A `saida_chatgpt_v4` tem uma inversão na regra das 18h: um `return` antecipado
pula a regra das 17:15, e com ATR acima de 550 pontos o limite das 18h fica
MAIS FROUXO que o anterior (com ATR 1.200: 600 contra 300). 33,1% dos candles
de 2026 estão nessa faixa. Aqui a proteção final usa sempre o limite mais
apertado entre as duas regras.

---------------------------------------------------------------------------
Regra 3 do compliance.md: este arquivo não importa nenhum módulo do projeto.
As constantes abaixo são cópias, não referências.
"""

from datetime import datetime
from math import isfinite

CONTRATO_SAIDA = "S001"
NOME = "saida_claude_v6"

# --- copiados da saida_chatgpt_v4, sem ajuste (Regra 3: cópia, não import) ---
SWING_LOOKBACK_CANDLES = 4
RELACAO_RISCO_RETORNO = 1.55
HORARIO_PROTECAO_V3 = "17:15"
HORARIO_PROTECAO_FINAL = "18:00"
PERDA_MINIMA_V3_PONTOS = 275.0
MULTIPLICADOR_V3_ATR = 0.25
PERDA_FINAL_ATR = 0.50


def _numero(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if isfinite(numero) else None


def _horario(row):
    valor = row.get("dt")
    if isinstance(valor, datetime) or hasattr(valor, "strftime"):
        try:
            return valor.strftime("%H:%M")
        except (TypeError, ValueError):
            return None
    return None


def _protecao_inicial(row, posicao):
    """Stop estrutural + alvo em RR fixo. Idêntico à v3/v4 — é o único
    componente do sistema que sobreviveu a todos os testes (platô chato entre
    swing 4-10 e RR 1,4-1,8)."""
    entrada = float(posicao["entrada"])
    lado = str(posicao["lado"]).upper()
    janela = (row.get("ohlc_recentes") or ())[-(SWING_LOOKBACK_CANDLES + 1):]
    if len(janela) < SWING_LOOKBACK_CANDLES + 1:
        raise ValueError("Histórico insuficiente para definir a proteção inicial.")

    if lado == "COMPRA":
        stop = min(float(c["Minimo"]) for c in janela)
        risco = entrada - stop
        alvo = entrada + RELACAO_RISCO_RETORNO * risco
    elif lado == "VENDA":
        stop = max(float(c["Maximo"]) for c in janela)
        risco = stop - entrada
        alvo = entrada - RELACAO_RISCO_RETORNO * risco
    else:
        raise ValueError(f"Lado inválido: {lado}")

    if risco <= 0 or not isfinite(stop) or not isfinite(alvo):
        raise ValueError(f"Proteção inicial inválida para {lado}.")
    return stop, alvo


def _reverteu(row, lado):
    """O movimento que justificou a entrada acabou?

    Estocástico saindo da zona extrema na direção contrária à posição.
    Devolve False quando o motor não expõe o campo (cartucho nunca quebra
    por indicador ausente)."""
    if lado == "COMPRA":
        return bool(row.get("stoch_cross_down_80"))
    return bool(row.get("stoch_cross_up_20"))


def _protecao_tardia(row, resultado):
    """Proteção de fim de pregão, com a inversão das 18h corrigida: usa sempre
    o limite MAIS APERTADO entre a regra das 17:15 e a das 18:00."""
    horario = _horario(row)
    atr = _numero(row.get("atr"))
    if horario is None or atr is None or atr <= 0:
        return None

    limite_v3 = max(PERDA_MINIMA_V3_PONTOS, MULTIPLICADOR_V3_ATR * atr)

    if horario >= HORARIO_PROTECAO_FINAL:
        limite = min(PERDA_FINAL_ATR * atr, limite_v3)
        if resultado <= -limite:
            return "PROTECAO_FINAL"
        return None

    if horario >= HORARIO_PROTECAO_V3:
        if resultado <= -limite_v3:
            return "PROTECAO_V3"
    return None


def _motivo(row, posicao):
    resultado = _numero(posicao.get("resultado_flutuante_pts"))
    if resultado is None:
        return None

    # Reversão só age NO LUCRO. No vermelho quem manda é o stop.
    if resultado > 0 and _reverteu(row, str(posicao["lado"]).upper()):
        return "REVERSAO_DO_MOVIMENTO"

    return _protecao_tardia(row, resultado)


def avaliar_saida(row: dict, posicao: dict) -> dict:
    if not isinstance(row, dict) or not isinstance(posicao, dict):
        raise TypeError("row e posicao precisam ser dicionários.")
    candles = _numero(posicao.get("candles_decorridos"))
    if candles is None:
        raise ValueError("candles_decorridos inválido.")
    if candles == 0:
        stop, alvo = _protecao_inicial(row, posicao)
        return {"fechar": False, "novo_stop": stop, "novo_alvo": alvo}
    return {"fechar": _motivo(row, posicao) is not None,
            "novo_stop": None, "novo_alvo": None}


def diagnosticar_saida(row, posicao):
    motivo = _motivo(row, posicao)
    resultado = _numero(posicao.get("resultado_flutuante_pts")) or 0.0
    if motivo == "REVERSAO_DO_MOVIMENTO":
        return ("O estocástico saiu da zona extrema contra a posição: o "
                f"movimento perdeu força com {abs(resultado):.0f} pontos de "
                "lucro. A posição foi encerrada para não devolver o ganho.")
    if motivo == "PROTECAO_FINAL":
        return ("A operação não apresentou continuidade até o período final "
                f"do pregão e atingiu {abs(resultado):.0f} pontos de perda. "
                "A posição foi encerrada para limitar a exposição.")
    if motivo == "PROTECAO_V3":
        return ("Proteção de fim de pregão acionada: a posição permaneceu "
                f"negativa e atingiu {abs(resultado):.0f} pontos de perda.")
    return None


__all__ = ["CONTRATO_SAIDA", "NOME", "avaliar_saida", "diagnosticar_saida"]

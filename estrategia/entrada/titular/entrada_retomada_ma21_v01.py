"""Entrada Retomada MA21 — Claude V1.

Autoria: Claude (Anthropic), em sessão operada por Marcio Soares; revisão
humana antes do teste oficial: pendente. A numeração v1 é a contagem própria
do autor, não a VERSAO do projeto.

Compra ou vende a favor da tendência quando o preço volta até perto da média
móvel de 21 candles (retomada) com o estocástico fora dos extremos e a favor.

Origem: Porta 1 de estrategia/entrada/titular/entrada_tres_portas_v01.py. Extração LITERAL: nenhum limiar, horário ou condição foi
alterado. Isola uma única ideia que hoje só existe combinada com outras num
agregador; não duplica nenhum arquivo existente (Regra 6) porque, sozinha, ela
produz sinais diferentes dos do agregador.
Variações testadas antes desta versão (Regra 11.2): nenhuma.
Sem dependência de data, evento ou preço absoluto (Regra 11.3).
Resultado financeiro: ainda não medido; rodar `classificacao.py` (Regra 12).

Contrato: gerar_sinal(row) -> 1, -1 ou 0 (opcional, V502: diagnosticar_oportunidades(row) -> radar,
sem efeito no sinal). Usa apenas dados fornecidos pelo
motor, não realiza I/O, não mantém estado e não importa módulos do projeto
(Regra 3).
"""

import math

MAX_DISTANCIA_MA21 = 90.0
STOCH_MIN = 16.5
STOCH_MAX = 83.5
ATR_RELATIVO_MAX = 1.40
SEPARACAO_FRACA_MIN = 75.0
SEPARACAO_FRACA_MAX = 175.0


def gerar_sinal(row) -> int:
    tendencia = row["trend"]
    if tendencia == 0:
        return 0
    hora = row["dt"].strftime("%H:%M")
    separacao = abs(row["MA21"] - row["MA50"])
    bloqueado = (
        row["dt"].weekday() == 3
        or "12:00" <= hora <= "13:15"
        or "15:00" <= hora <= "16:59"
    )
    if bloqueado or (SEPARACAO_FRACA_MIN <= separacao <= SEPARACAO_FRACA_MAX):
        return 0
    if row["atr_relativo"] > ATR_RELATIVO_MAX:
        return 0
    direcao_stoch = (row["stoch_subindo"] if tendencia == 1
                     else row["stoch_descendo"] if tendencia == -1 else False)
    if (row["distancia_ma21"] <= MAX_DISTANCIA_MA21
            and STOCH_MIN <= row["stoch"] <= STOCH_MAX
            and direcao_stoch):
        return 1 if tendencia == 1 else -1
    return 0


# ---------------------------------------------------------------------------
# Radar (V502). Mostra no terminal quantas condições já estão confirmadas e a
# próxima que falta. NÃO participa de gerar_sinal() e não altera nenhum limiar:
# é a cópia, para este arquivo, do radar que a porta tinha no titular antigo
# (entrada_tres_portas_v01). Sem I/O, sem estado, sem importar o projeto (Regra 3).
# ---------------------------------------------------------------------------


def _fino(ok, proximidade):
    """V515: 1.0 se a condicao esta atendida; senao a proximidade (0..0,99), para o % do painel
    andar ponto a ponto. Nunca chega a 1.0 sem a condicao atendida."""
    return 1.0 if ok else min(0.99, max(0.0, float(proximidade)))


def _prox_direcao_stoch(row, tendencia):
    """Proximidade da condicao 'estocastico na direcao da tendencia' (delta a favor > 0)."""
    delta = (row["stoch"] - row["stoch_prev"]) * tendencia
    return 1.0 / (1.0 + max(0.0, -delta) / 2.0)

def diagnosticar_oportunidades(row):
    tendencia = row["trend"]
    hora = row["dt"].strftime("%H:%M")
    separacao = abs(row["MA21"] - row["MA50"])
    quinta = row["dt"].weekday() == 3
    almoco = "12:00" <= hora <= "13:15"
    tarde = "15:00" <= hora <= "16:59"
    direcao_stoch = (row["stoch_subindo"] if tendencia == 1
                     else row["stoch_descendo"] if tendencia == -1 else False)
    elegibilidade = [
        (tendencia != 0, "definição de tendência"),
        (not (quinta or almoco or tarde), "horário permitido"),
        (not (SEPARACAO_FRACA_MIN <= separacao <= SEPARACAO_FRACA_MAX), "separação saudável das médias"),
        (not (row["atr_relativo"] > ATR_RELATIVO_MAX), "volatilidade aceitável"),
    ]
    # V541: quanto o preco ainda precisa se aproximar da MA21 (so texto de painel e voz; o sinal nao muda)
    falta_aproximar = max(1, int(math.ceil(row["distancia_ma21"] - MAX_DISTANCIA_MA21)))
    rotulo_aproximacao = (f"o preço chegar mais perto da MA21. Hoje está {falta_aproximar} "
                          f"{'ponto' if falta_aproximar == 1 else 'pontos'} acima do limite")
    condicoes = [
        (row["distancia_ma21"] <= MAX_DISTANCIA_MA21, rotulo_aproximacao),
        (STOCH_MIN <= row["stoch"] <= STOCH_MAX, "estocástico fora dos extremos"),
        (bool(direcao_stoch), "estocástico na direção da tendência"),
    ]
    elegivel = all(ok for ok, _ in elegibilidade)
    # V515: proximidade fina de cada condicao (so painel; gerar_sinal nao usa)
    dist = row["distancia_ma21"]
    fora_stoch = max(STOCH_MIN - row["stoch"], row["stoch"] - STOCH_MAX, 0.0)
    scores = [
        _fino(dist <= MAX_DISTANCIA_MA21, MAX_DISTANCIA_MA21 / dist if dist > 0 else 1.0),
        _fino(STOCH_MIN <= row["stoch"] <= STOCH_MAX, 1.0 - fora_stoch / STOCH_MIN),
        _fino(bool(direcao_stoch), _prox_direcao_stoch(row, tendencia)),
    ]
    confirmadas = sum(bool(ok) for ok, _ in condicoes) if elegivel else 0
    progresso_fino = sum(scores) / len(scores) if elegivel else 0.0
    faltantes = ([t for ok, t in condicoes if not ok] if elegivel
                 else [t for ok, t in elegibilidade if not ok])
    sinal = (1 if tendencia == 1 else -1) if elegivel and all(ok for ok, _ in condicoes) else 0
    faltante = faltantes[0] if faltantes else "nenhuma"
    detalhe = faltante
    bloqueio_horario = faltante == "horário permitido"
    if bloqueio_horario:
        detalhe = ("BLOQUEADA NESTA QUINTA" if quinta
                   else "BLOQUEADA ATÉ 13:30" if almoco else "BLOQUEADA ATÉ 17:00")
    elif faltante == rotulo_aproximacao:
        detalhe = f"aproximar {falta_aproximar} {'pt' if falta_aproximar == 1 else 'pts'} da MA21"   # V541 (antes: "dist. MA21 91 (máx. 90)")
    elif faltante == "estocástico na direção da tendência":
        detalhe = "estoc. a favor da tendência"   # V516: cabe na coluna do painel (29)
    elif faltante == "estocástico fora dos extremos":
        detalhe = f"estoc. {row['stoch']:.1f} (16,5-83,5)"
    return [{
        "estrategia": "Retomada MA21",
        "prioridade": 1,
        "direcao": "COMPRA" if tendencia == 1 else "VENDA" if tendencia == -1 else "NEUTRA",
        "sinal": sinal,
        "confirmadas": confirmadas,
        "total": len(condicoes),
        "progresso": progresso_fino,
        "faltantes": faltantes,
        "detalhe": detalhe,
        "bloqueio_horario": bloqueio_horario,
    }]

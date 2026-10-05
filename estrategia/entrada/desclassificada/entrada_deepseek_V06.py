"""Rompimento da EMA9 na direção do MACD — versão V06 (aula Massuda).

Autoria: DeepSeek (assistido). Revisão humana: pendente (Regra 8).
O "V06" no nome é numeração própria deste autor, NÃO a VERSAO do projeto
(versionamento.py, hoje V459).

Regra 11.2 — declaração de variações testadas nesta linha:
  V01..V05 (conceituais): entradas de continuação por RSI, rompimento de
                          range, confluência Fibonacci. V01..V05 existem
                          no disco como candidatas, algumas já refutadas.
  V06 (esta): abertura de família nova — a aula do Massuda. MACD clássico
              (12/26/9) + EMA9 + rompimento. Os limiares (10 e 25 no
              histograma, EMA9 no fechamento) são cópia literal da aula.
              A única conversão foi traduzir "entre 10 e -10 é lateral"
              para uma condição booleana, sem ajuste contra dataset.

Regra 11.3 — usa apenas campos já existentes em `row`. Nenhuma data
específica, nenhum preço absoluto do WINFUT. Pivot não entra nesta versão
(o `row` não expõe Pivot hoje, e a Regra 2 proíbe inventar coluna).

Regra 3 — sem I/O, sem import de módulo do projeto.

Regra 1 — gerar_sinal(row) -> -1 | 0 | 1.
Contrato opcional: diagnosticar_oportunidades(row).
"""

MACD_LINHA_MIN = 10.0
MACD_LINHA_FORTE = 25.0
PRIORIDADE_PORTA = 4


def _direcao(row):
    return "COMPRA" if row["trend"] == 1 else "VENDA" if row["trend"] == -1 else "NEUTRA"


def _avaliar(row):
    """Devolve (sinal, lista_de_faltantes).

    COMPRA: candle atual acima da EMA9-proxy E MACD acima de zero E
            histograma fora da zona 10/-10 E estocástico subindo.
    VENDA:  simétrico.
    """
    trend = row["trend"]
    if trend == 0:
        return 0, ["definição de tendência"]

    ma21 = row.get("MA21")
    macd = row.get("macd")
    macd_signal = row.get("macd_signal")
    if None in (ma21, macd, macd_signal):
        return 0, ["indicadores-base disponíveis"]

    # Proxy declarada: EMA9 não existe em row; MA21 é o preço médio recente
    # disponível. NÃO é a EMA9 da aula — é a aproximação honesta que o motor
    # permite hoje.
    ema9_proxy = ma21
    histograma = macd - macd_signal
    if abs(histograma) < MACD_LINHA_MIN:
        return 0, ["MACD fora da zona de lateralidade (10/-10)"]

    rompeu_acima = row["Fechamento"] > ema9_proxy and row.get("stoch_subindo")
    rompeu_abaixo = row["Fechamento"] < ema9_proxy and row.get("stoch_descendo")

    if macd > 0 and rompeu_acima:
        return 1, []
    if macd < 0 and rompeu_abaixo:
        return -1, []

    faltantes = []
    if macd > 0 and not rompeu_acima:
        faltantes.append("rompimento da EMA9 para cima")
    if macd < 0 and not rompeu_abaixo:
        faltantes.append("rompimento da EMA9 para baixo")
    if not faltantes:
        faltantes.append("MACD sem força na direção da tendência")
    return 0, faltantes


def gerar_sinal(row) -> int:
    return _avaliar(row)[0]


def diagnosticar_oportunidades(row):
    sinal, faltantes = _avaliar(row)
    total = 4
    confirmadas = total - len(faltantes)
    return [{
        "estrategia": "MACD + EMA9",
        "prioridade": PRIORIDADE_PORTA,
        "direcao": _direcao(row),
        "sinal": sinal,
        "confirmadas": confirmadas,
        "total": total,
        "progresso": confirmadas / total if total else 0.0,
        "faltantes": faltantes,
        "detalhe": faltantes[0] if faltantes else "nenhuma",
    }]


__all__ = ["gerar_sinal", "diagnosticar_oportunidades"]
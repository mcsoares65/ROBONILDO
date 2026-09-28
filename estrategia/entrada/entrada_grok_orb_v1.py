"""entrada_grok_orb_v1.py — candidata (não titular)

Autoria: Grok (xAI). Versão própria do autor: v1 (não é a VERSAO do projeto).

Pesquisa aplicada ao WIN 15min (sem VWAP — o motor não expoe VWAP no row):
  - Opening Range Breakout dos primeiros 30 minutos (09:00 e 09:15),
    literatura de day trade WIN/ES (Awake Trader, Veredicto Capital).
  - Pullback na MA21 só nas janelas nobres 09:30-11:30 e 14:00-14:59
    (volume/volatilidade concentrados no mini-índice).
  - Sem Porta 3 tardia (caso real 28/09/2026: COMPRA às 16:45 sem tempo
    útil até o corte 18:20).

Contrato: gerar_sinal(row) -> 1 / -1 / 0.
Sem I/O, sem estado global, sem imports do projeto.
Usa apenas row e row['ohlc_recentes'] (12 candles fechados, V444).

Declaração Regra 11.2: 4 variações internas da mesma ideia (ORB puro;
ORB+P1 o dia todo; ORB+P1 só manhã; ORB+P1 janelas nobres). Submetida
a última, por ser a mais restrita em horário. Nenhuma lógica de data
calendário (Regra 11.3). Não validada em classificacao.py — só após merge.
"""

ORB_FIM = "09:30"
ORB_LIMITE_SINAL = "11:00"
JANELAS_NOBRES = (("09:30", "11:30"), ("14:00", "14:59"))
MAX_DISTANCIA_MA21 = 90.0
STOCH_MIN = 16.5
STOCH_MAX = 83.5
ATR_RELATIVO_MAX = 1.40


def _hora(row):
    return row["dt"].strftime("%H:%M")


def _em_janela_nobre(hora):
    return any(inicio <= hora <= fim for inicio, fim in JANELAS_NOBRES)


def _range_abertura(row):
    """High/low dos candles 09:00 e 09:15 do mesmo dia (range de 30 min)."""
    dia = row["dt"].date()
    highs = []
    lows = []
    for c in row.get("ohlc_recentes") or ():
        dt = c.get("dt")
        if dt is None or not hasattr(dt, "date") or dt.date() != dia:
            continue
        hm = dt.strftime("%H:%M")
        if hm in ("09:00", "09:15"):
            highs.append(float(c["Maximo"]))
            lows.append(float(c["Minimo"]))
    if len(highs) < 2:
        return None, None
    return max(highs), min(lows)


def _sinal_orb(row):
    hora = _hora(row)
    if hora < ORB_FIM or hora > ORB_LIMITE_SINAL:
        return 0
    if row["trend"] == 0:
        return 0
    orb_high, orb_low = _range_abertura(row)
    if orb_high is None:
        return 0
    recentes = row.get("ohlc_recentes") or ()
    if len(recentes) < 2:
        return 0
    prev_close = float(recentes[-2]["Fechamento"])
    close = float(row["Fechamento"])
    # Sinal só no candle que CRUZA o range (sem estado global).
    if (
        row["trend"] == 1
        and close > orb_high
        and prev_close <= orb_high
        and row.get("atr_relativo", 1.0) <= ATR_RELATIVO_MAX
    ):
        return 1
    if (
        row["trend"] == -1
        and close < orb_low
        and prev_close >= orb_low
        and row.get("atr_relativo", 1.0) <= ATR_RELATIVO_MAX
    ):
        return -1
    return 0


def _sinal_pullback_ma21(row):
    hora = _hora(row)
    if not _em_janela_nobre(hora):
        return 0
    tendencia = row["trend"]
    if tendencia == 0:
        return 0
    if row["dt"].weekday() == 3:
        return 0
    separacao = abs(row["MA21"] - row["MA50"])
    if 75.0 <= separacao <= 175.0:
        return 0
    if row["atr_relativo"] > ATR_RELATIVO_MAX:
        return 0
    if row["distancia_ma21"] > MAX_DISTANCIA_MA21:
        return 0
    if not (STOCH_MIN <= row["stoch"] <= STOCH_MAX):
        return 0
    if tendencia == 1 and row["stoch_subindo"]:
        return 1
    if tendencia == -1 and row["stoch_descendo"]:
        return -1
    return 0


def gerar_sinal(row) -> int:
    orb = _sinal_orb(row)
    if orb in (-1, 1):
        return orb
    return _sinal_pullback_ma21(row)


def diagnosticar_sinal(row):
    orb = _sinal_orb(row)
    if orb in (-1, 1):
        return {
            "porta": 1,
            "total_portas": 2,
            "estrategia": "ORB 30min",
            "lado": "COMPRA" if orb == 1 else "VENDA",
            "explicacao": (
                "Rompimento do range de abertura (09:00-09:30) no sentido "
                "da tendência das médias."
            ),
        }
    pb = _sinal_pullback_ma21(row)
    if pb in (-1, 1):
        return {
            "porta": 2,
            "total_portas": 2,
            "estrategia": "Pullback MA21 (janela nobre)",
            "lado": "COMPRA" if pb == 1 else "VENDA",
            "explicacao": "Retomada da MA21 em horário de volume.",
        }
    return {
        "porta": 0,
        "total_portas": 2,
        "estrategia": "aguardando",
        "lado": "NEUTRA",
        "explicacao": "Nenhuma confirmação de ORB ou pullback na janela nobre.",
    }


__all__ = ["gerar_sinal", "diagnosticar_sinal"]

"""
saida_deepseek_v03.py — refinamento cirúrgico (DeepSeek, v03).

CONTEXTO:
    - Baseline (False sempre) = 18.875,98 | multi 1027,7 → teto conhecido.
    - ChatGPT V2 (só corta perda tardia ≥250pts após 16:30) é a referência
      cirúrgica: preserva a cauda positiva, ataca só perda tardia.
    - Meu v01 (agressivo) caiu para 9.528 — cortou winner demais.

FILOSOFIA v03:
    Mesma disciplina do ChatGPT V2, com 3 adições RARAS:
    1. Disaster real: primeiros 3 candles, perda ≥ 1,2 ATR + RSI extremo
       contra. Só fecha ordem que nasceu do lado errado do fluxo.
    2. Proteção tardia (herdada do ChatGPT V2): após 16:30, perda ≥ 250
       pts → fecha.
    3. Proteção final: após 17:00, perda ≥ 150 pts → fecha. Última hora
       tem liquidez pior; RR ruim para tentar recuperar.
    4. Giveback extremo: pico ≥ 2,0 ATR e devolveu até ≤ 0,15 ATR →
       fecha. Só dispara quando o trade já foi MUITO a favor e devolveu
       quase tudo. Não é pullback, é desmonte.

Tudo o mais: motor no comando. Nada de alvo, nada de RSI/estoc contra em
lucro, nada de MACD flip. Essas camadas matam winner — estão fora.

Contrato (Regras do Jogo, rodada 3):
    avaliar_saida(row, posicao) -> bool
    True  = fecha AGORA.
    False = motor segue no comando.
    Nunca afrouxa stop/alvo — só antecipa.
"""

from math import isfinite

__all__ = ['avaliar_saida', 'diagnosticar_saida']


# ---------------------------------------------------------------------------
# Parâmetros
# ---------------------------------------------------------------------------

HORARIO_TARDIO          = "16:30"
PERDA_TARDIA_PTS        = 250.0

HORARIO_FINAL           = "17:00"
PERDA_FINAL_PTS         = 150.0

CANDLES_DISASTER        = 3
MULT_ATR_DISASTER       = 1.2
RSI_DISASTER_CONTRA     = 30.0   # comprado: RSI <=; vendido: RSI >= 70

MULT_ATR_GIVEBACK       = 2.0
MULT_ATR_GIVEBACK_PISO  = 0.15


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get(d, *chaves, default=None):
    for k in chaves:
        if isinstance(d, dict) and k in d and d[k] is not None:
            return d[k]
    return default


def _num(x, default=0.0):
    try:
        n = float(x)
        return n if isfinite(n) else default
    except (TypeError, ValueError):
        return default


def _horario(row):
    v = row.get("dt") if isinstance(row, dict) else None
    if v is None:
        return None
    if hasattr(v, "strftime"):
        try:
            return v.strftime("%H:%M")
        except (TypeError, ValueError):
            return None
    return None


def _lado_comprado(lado):
    s = str(lado or '').strip().upper()
    return s in ('COMPRA', 'COMPRADO', 'LONG', 'C', 'BUY', 'B', '1')


# ---------------------------------------------------------------------------
# Motor de decisão
# ---------------------------------------------------------------------------

def avaliar_saida(row, posicao) -> bool:
    if not isinstance(row, dict) or not isinstance(posicao, dict):
        return False

    lado = posicao.get("lado")
    if lado is None:
        return False

    horario = _horario(row)
    flut    = _num(_get(posicao, 'resultado_flutuante_pts', 'flutuante', 'pnl_pts'), 0.0)
    candles = int(_num(_get(posicao, 'candles_decorridos', 'candles', 'barras'), 0))
    entrada = _num(_get(posicao, 'entrada', 'preco_entrada'), 0.0)
    maxima  = _num(_get(posicao, 'maxima_desde_entrada', 'maxima'), entrada)
    minima  = _num(_get(posicao, 'minima_desde_entrada', 'minima'), entrada)
    atr     = _num(_get(row, 'ATR', 'atr', 'atr_14'), 0.0)
    rsi     = _get(row, 'RSI', 'rsi', 'rsi_14')
    comprado = _lado_comprado(lado)

    # ---- Camada 2: proteção tardia (ideia ChatGPT V2) ------------------
    if horario is not None and horario >= HORARIO_TARDIO:
        if flut <= -PERDA_TARDIA_PTS:
            return True

    # ---- Camada 3: proteção final (última hora) ------------------------
    if horario is not None and horario >= HORARIO_FINAL:
        if flut <= -PERDA_FINAL_PTS:
            return True

    if atr <= 0.0 or entrada <= 0.0:
        return False

    # ---- Camada 1: disaster real ---------------------------------------
    if candles <= CANDLES_DISASTER and flut <= -MULT_ATR_DISASTER * atr:
        if rsi is not None:
            r = _num(rsi, 50.0)
            if comprado and r <= RSI_DISASTER_CONTRA:
                return True
            if (not comprado) and r >= (100.0 - RSI_DISASTER_CONTRA):
                return True

    # ---- Camada 4: giveback extremo ------------------------------------
    if comprado:
        pico = maxima - entrada if maxima > entrada else max(0.0, flut)
    else:
        pico = entrada - minima if minima < entrada else max(0.0, flut)

    if pico >= MULT_ATR_GIVEBACK * atr and 0.0 <= flut <= MULT_ATR_GIVEBACK_PISO * atr:
        return True

    return False


def diagnosticar_saida(row, posicao):
    try:
        if avaliar_saida(row, posicao):
            return {'cartucho': 'saida_deepseek_v03', 'decisao': 'fechar_agora'}
        return {'cartucho': 'saida_deepseek_v03', 'decisao': 'manter'}
    except Exception as exc:
        return {'cartucho': 'saida_deepseek_v03', 'erro': str(exc)}
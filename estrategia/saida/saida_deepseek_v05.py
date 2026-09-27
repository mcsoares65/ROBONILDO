"""
saida_deepseek_v05.py — corte tardio proporcional ao ATR (DeepSeek, v05).

DIAGNÓSTICO (rodadas anteriores):
    - v01 (6 camadas): 9.528 pts. Cortou winner. Reprovado.
    - v02 (3 camadas cirúrgicas): 16.671 pts. Ainda cortou winner.
    - v03 (disaster + giveback): 17.809 pts. Aproveit caiu 5,5 p.p.
      vs baseline. Ambas as camadas extras mataram trades que iam virar.
    - v04 (escada em pts fixos): não chegou a ser medido, mas parte da
      mesma premissa do v2, com o mesmo defeito: limiar absoluto.

APRENDIZADO DECISIVO:
    A ÚNICA coisa que comprovadamente paga é o corte tardio. Todas as
    camadas que agem antes das 16:30 (break-even, trailing, momentum,
    disaster, giveback) foram reprovadas em medição real.

    O ChatGPT v2 ganha +165,70 pts sobre baseline usando 250 pts fixos.
    Mas WINFUT tem dias de 200 pts e dias de 1.500 pts. Um limiar
    absoluto de 250 pts é brando em dia agitado e agressivo em dia morto.

ESTRATÉGIA v05:
    Mesma arquitetura do v2 — SÓ corte tardio, nada mais — mas expressa
    em fração de ATR. E com dois degraus em vez de um, porque o valor do
    corte cresce conforme o dia acaba:

        16:30  →  perda ≥ 0,70 × ATR   (fecha)
        17:00  →  perda ≥ 0,55 × ATR   (fecha)
        17:30  →  perda ≥ 0,40 × ATR   (fecha)
        17:45  →  perda ≥ 0,28 × ATR   (fecha)

    Calibração inicial: com ATR médio típico do WINFUT em 15 min
    (~180–220 pts), 0,70 × ATR ≈ 125–155 pts. Isso é mais conservador
    que o v2 em dia típico (250 pts fixos) — quer dizer, corta MENOS
    cedo e deixa o motor trabalhar mais. Em dia agitado (ATR ~ 400),
    0,70 × ATR ≈ 280 pts — parecido com o v2. Em dia morto (ATR ~ 100),
    ≈ 70 pts — corta muito cedo, o que é correto: nesse dia não há
    combustível para reverter 100 pts em 30 min.

    Nenhuma camada de momentum. Nenhum disaster cut. Nenhum giveback.
    Nenhuma exceção. Só corte tardio proporcional à volatilidade do dia.

Contrato (Regras do Jogo, rodada 3):
    avaliar_saida(row, posicao) -> bool
    True  = fecha AGORA.
    False = motor segue no comando.
    Nunca afrouxa stop/alvo — só antecipa.
"""

from math import isfinite

__all__ = ['avaliar_saida', 'diagnosticar_saida']


# (horário, fração de ATR) — avaliado do topo; primeiro horário
# satisfeito aplica seu limiar.
ESCADA_ATR = (
    ("16:30", 0.70),
    ("17:00", 0.55),
    ("17:30", 0.40),
    ("17:45", 0.28),
)

# Fallback quando ATR não está disponível: usa os mesmos valores do v2
# (limiar fixo) para garantir comportamento seguro em qualquer dataset.
PERDA_FALLBACK_PTS = 250.0


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


def _num(x, default=0.0):
    try:
        n = float(x)
        return n if isfinite(n) else default
    except (TypeError, ValueError):
        return default


def _get(d, *chaves, default=None):
    for k in chaves:
        if isinstance(d, dict) and k in d and d[k] is not None:
            return d[k]
    return default


def avaliar_saida(row, posicao) -> bool:
    if not isinstance(row, dict) or not isinstance(posicao, dict):
        return False

    horario = _horario(row)
    if horario is None:
        return False

    flut = _num(_get(posicao, 'resultado_flutuante_pts', 'flutuante', 'pnl_pts'), 0.0)
    atr  = _num(_get(row, 'ATR', 'atr', 'atr_14'), 0.0)

    for hora_limite, mult_atr in ESCADA_ATR:
        if horario >= hora_limite:
            limite_pts = mult_atr * atr if atr > 0.0 else PERDA_FALLBACK_PTS
            if flut <= -limite_pts:
                return True

    return False


def diagnosticar_saida(row, posicao):
    try:
        if avaliar_saida(row, posicao):
            horario = _horario(row)
            flut = _num(_get(posicao, 'resultado_flutuante_pts', 'flutuante', 'pnl_pts'), 0.0)
            atr = _num(_get(row, 'ATR', 'atr', 'atr_14'), 0.0)
            for hora_limite, mult in ESCADA_ATR:
                if horario and horario >= hora_limite and flut <= -mult * atr:
                    return {
                        'cartucho': 'saida_deepseek_v05',
                        'decisao': 'fechar_agora',
                        'motivo': f'corte tardio {hora_limite} ({mult:.2f}×ATR)',
                    }
        return {'cartucho': 'saida_deepseek_v05', 'decisao': 'manter'}
    except Exception as exc:
        return {'cartucho': 'saida_deepseek_v05', 'erro': str(exc)}
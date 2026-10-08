"""Entrada varredura de liquidez — Grok V1.

Autoria: Grok (xAI), em sessão operada por Marcio Soares, 08/10/2026;
revisão humana/conselho antes do teste oficial: pendente (Regra 12). A
numeração v01 é a versão da ideia, não a VERSAO do projeto.

Origem: artigo "Indicador SMC" da Central de Ajuda da Nelogica — "O Liquidity
Sweep ocorre quando o preço ultrapassa uma região de interesse, como um topo
ou fundo anterior, aciona ordens e, em seguida, retorna ao nível anterior."
O topo/fundo é o do artigo "Detectores de Topos e Fundos", período 2 (padrão
da tela de Propriedades, não ajustado). Uma ideia só (Regra 16): o evento é
furar o último extremo confirmado e fechar de volta para dentro. Não é o
playbook SMC de cinco etapas (BOS, CHoCH, order block, FVG).

Isto é o OPOSTO do Donchian (ata conselho/2026-10-05-AD.txt, hipótese P3):
lá a entrada era a favor do rompimento; aqui a entrada é a favor da falha
do rompimento. Não usa média, MACD, estocástico, Aroon, CCI, Keltner, HiLo,
ADX, SAR nem Bollinger.

Variações testadas antes desta versão (Regra 11.2): nenhuma. Período fixado
a priori no padrão da tela. Sem dependência de data, evento ou preço
absoluto (Regra 11.3): só compara o candle atual a um extremo já confirmado
na janela. Resultado financeiro: ainda não medido; é CANDIDATA, não titular.
Rodar `classificacao.py` depois do merge (Regra 12).

Contrato: gerar_sinal(row) -> 1, -1 ou 0. Usa apenas row["ohlc_recentes"],
não realiza I/O, não mantém estado e não importa módulos do projeto (Regra 3).
"""

PERIODO = 2


def _hl(candle):
    try:
        alta = float(candle["Maximo"])
        baixa = float(candle["Minimo"])
    except (KeyError, TypeError, ValueError):
        return None
    if alta != alta or baixa != baixa:
        return None
    if alta in (float("inf"), float("-inf")) or baixa in (float("inf"), float("-inf")):
        return None
    return alta, baixa


def detectar_topos_fundos(candles):
    """Detector do artigo Nelogica, período fixo.

    Topo: a referência é o último candle com a maior máxima; confirma quando
    PERIODO candles seguintes fecham com mínima menor que a mínima da
    referência (não precisam fazer escada entre si). Fundo: a referência é o
    último candle com a menor mínima; confirma quando PERIODO candles
    seguintes fecham com máxima maior que a máxima da referência. A
    confirmação só vale depois do candle que completa a contagem. Uma
    sequência de máximas iguais não zera a referência (o artigo atualiza
    para o último candle que tem a máxima mais alta).

    Devolve lista de ("topo"|"fundo", indice, preco) na ordem em que foram
    confirmados. preco é a máxima do topo ou a mínima do fundo.
    """
    serie = []
    for candle in candles:
        par = _hl(candle)
        if par is None:
            return []
        serie.append(par)
    n = len(serie)
    if n < PERIODO + 2:
        return []

    swings = []
    modo = "ambos"
    ref_topo = 0
    ref_fundo = 0
    streak_topo = 0
    streak_fundo = 0

    def _avanca_topo(i):
        nonlocal ref_topo, streak_topo
        alta, baixa = serie[i]
        if alta >= serie[ref_topo][0]:
            ref_topo = i
            streak_topo = 0
        elif baixa < serie[ref_topo][1]:
            streak_topo += 1
        else:
            streak_topo = 0

    def _avanca_fundo(i):
        nonlocal ref_fundo, streak_fundo
        alta, baixa = serie[i]
        if baixa <= serie[ref_fundo][1]:
            ref_fundo = i
            streak_fundo = 0
        elif alta > serie[ref_fundo][0]:
            streak_fundo += 1
        else:
            streak_fundo = 0

    def _confirma(qual, i):
        nonlocal modo, ref_topo, ref_fundo, streak_topo, streak_fundo
        if qual == "topo":
            swings.append(("topo", ref_topo, serie[ref_topo][0]))
            modo = "busca_fundo"
            ref_fundo = i
            streak_fundo = 0
        else:
            swings.append(("fundo", ref_fundo, serie[ref_fundo][1]))
            modo = "busca_topo"
            ref_topo = i
            streak_topo = 0

    for i in range(1, n):
        if modo in ("ambos", "busca_topo"):
            _avanca_topo(i)
        if modo in ("ambos", "busca_fundo"):
            _avanca_fundo(i)
        if modo == "busca_topo" and streak_topo >= PERIODO:
            _confirma("topo", i)
            continue
        if modo == "busca_fundo" and streak_fundo >= PERIODO:
            _confirma("fundo", i)
            continue
        if modo == "ambos" and (streak_topo >= PERIODO or streak_fundo >= PERIODO):
            if streak_topo >= PERIODO and streak_fundo >= PERIODO:
                if ref_topo == ref_fundo:
                    continue
                qual = "topo" if ref_topo < ref_fundo else "fundo"
            else:
                qual = "topo" if streak_topo >= PERIODO else "fundo"
            _confirma(qual, i)
    return swings


def _ultimo(swings, tipo):
    for item in reversed(swings):
        if item[0] == tipo:
            return item[2]
    return None


def gerar_sinal(row) -> int:
    janela = row.get("ohlc_recentes") or ()
    if len(janela) < PERIODO + 3:
        return 0
    atual = janela[-1]
    par = _hl(atual)
    if par is None:
        return 0
    try:
        fechamento = float(atual["Fechamento"])
    except (KeyError, TypeError, ValueError):
        return 0
    if fechamento != fechamento or fechamento in (float("inf"), float("-inf")):
        return 0

    # O candle atual não confirma o nível que ele próprio varre.
    swings = detectar_topos_fundos(janela[:-1])
    fundo = _ultimo(swings, "fundo")
    topo = _ultimo(swings, "topo")
    alta, baixa = par
    compra = fundo is not None and baixa < fundo and fechamento > fundo
    venda = topo is not None and alta > topo and fechamento < topo
    if compra and venda:
        return 0
    if compra:
        return 1
    if venda:
        return -1
    return 0

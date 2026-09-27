"""
baseline.py — cartucho de saída BASELINE (titular inicial), reescrito para
a Regra 1 v10.

Autoria: Claude (Anthropic), a pedido do dono do laboratório.

POR QUE ESTE ARQUIVO MUDOU (histórico): até a Regra 1 v9, `avaliar_saida`
sempre devolvia `False` porque o motor calculava sozinho um stop estrutural
(`SWING_LOOKBACK_CANDLES` candles) e um alvo em `RELACAO_RISCO_RETORNO` x o
risco, aplicando os dois como piso/teto duro — o baseline só precisava "não
atrapalhar" essa regra fixa do motor. A partir da Regra 1 v10, o motor NÃO
tem mais fórmula própria de saída nenhuma: quem define o stop e o alvo,
desde o primeiro instante da posição, é o arquivo de saída titular. Um
`avaliar_saida` que sempre devolve `False`, sob o motor v10, deixaria toda
posição sem NENHUMA proteção de preço — constatado empiricamente rodando
`classificacao.py`: o drawdown piorou de -309,19 para -498,39 no dataset
oficial só por causa dessa mudança silenciosa de comportamento, sem que o
arquivo em si tivesse sido tocado.

O QUE ESTE ARQUIVO FAZ AGORA: reproduz, dentro do próprio cartucho, a MESMA
fórmula que antes vivia no motor (stop estrutural + RR fixo) — migração 1:1
da regra existente para o cartucho, não uma estratégia nova. É calculada
UMA ÚNICA VEZ, no instante em que a posição abre (`candles_decorridos ==
0`, quando o motor consulta este arquivo pela primeira vez em
`abrir_posicao`) — nas chamadas seguintes o cartucho não propõe mais nenhum
`novo_stop`/`novo_alvo`, deixando intocado o valor já fixado na abertura,
exatamente como o motor fazia antes.

Como `avaliar_saida` não recebe a lista de candles (só `row` e `posicao`,
Regra 1), o stop estrutural é calculado a partir de `row["ohlc_recentes"]`
— janela de até 12 candles fechados que o motor expõe desde a V444,
suficiente para os `SWING_LOOKBACK_CANDLES(4) + 1 = 5` candles que a
fórmula usa. Os valores abaixo (4 candles / RR 1,55) são copiados
manualmente de `configuracao.py` em vez de importados de lá — Regra 3
proíbe o cartucho de importar módulos do projeto; são os mesmos valores de
sempre, documentados nos dois lugares.

Validado: rodando `classificacao.py` (ranking de saída, dataset oficial,
184 pregões) contra o motor v10, este arquivo reproduziu resultado e
drawdown idênticos aos medidos antes da mudança de contrato (quando a
fórmula ainda vivia no motor) — confirma que a migração é
comportamentalmente neutra, só muda ONDE a regra vive.

Contrato (Regra 1 v10):
    avaliar_saida(row, posicao) -> dict
        row: mesmo dict de sempre, agora incluindo row["ohlc_recentes"]
             (últimos 12 candles fechados, mais recente por último).
        posicao: lado, entrada, candles_decorridos, maxima_desde_entrada,
                 minima_desde_entrada, resultado_flutuante_pts.
        Retorna {"fechar": False, "novo_stop": ..., "novo_alvo": ...} na
        abertura (candles_decorridos == 0); nas chamadas seguintes devolve
        {"fechar": False, "novo_stop": None, "novo_alvo": None} — não
        redefine nada, mantém o nível já fixado na abertura.

Sem I/O, sem estado, sem imports do projeto.
"""

from __future__ import annotations

# Copiados de configuracao.py (SWING_LOOKBACK_CANDLES / RELACAO_RISCO_RETORNO)
# — não importados, por Regra 3. Se esses valores mudarem em configuracao.py,
# este arquivo precisa ser atualizado manualmente (documentado nos dois
# lugares).
SWING_LOOKBACK_CANDLES = 4
RELACAO_RISCO_RETORNO = 1.55


def avaliar_saida(row: dict, posicao: dict) -> dict:
    # Só define o nível na abertura da posição (candles_decorridos == 0,
    # a chamada síncrona que abrir_posicao faz). Nas chamadas seguintes,
    # não mexe em nada - o nível fixado na abertura vale até o fim da
    # operação, exatamente como a fórmula antiga do motor.
    if posicao["candles_decorridos"] != 0:
        return {"fechar": False, "novo_stop": None, "novo_alvo": None}

    ohlc = row.get("ohlc_recentes") or ()
    janela = ohlc[-(SWING_LOOKBACK_CANDLES + 1):]
    if len(janela) < SWING_LOOKBACK_CANDLES + 1:
        # Só pode acontecer bem no início do histórico (janela insuficiente).
        # Melhor nenhuma proteção declarada do que uma calculada sobre dado
        # incompleto.
        return {"fechar": False, "novo_stop": None, "novo_alvo": None}

    entrada = posicao["entrada"]
    lado = posicao["lado"]

    if lado == "COMPRA":
        stop = min(c["Minimo"] for c in janela)
        risco = entrada - stop
        if risco <= 0:
            return {"fechar": False, "novo_stop": None, "novo_alvo": None}
        alvo = entrada + RELACAO_RISCO_RETORNO * risco
    else:
        stop = max(c["Maximo"] for c in janela)
        risco = stop - entrada
        if risco <= 0:
            return {"fechar": False, "novo_stop": None, "novo_alvo": None}
        alvo = entrada - RELACAO_RISCO_RETORNO * risco

    return {"fechar": False, "novo_stop": stop, "novo_alvo": alvo}


def diagnosticar_saida(row, posicao):
    """Sem antecipação nesta versão - nada a narrar além do nível fixado
    na abertura (já visível no log de abertura da posição)."""
    return None


__all__ = ['avaliar_saida', 'diagnosticar_saida']

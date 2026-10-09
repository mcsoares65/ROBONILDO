"""Saída por Exaustão do Estocástico — Claude V1 (titular de ALERTA).

Autoria: Claude (Anthropic), em sessão operada por Marcio Soares; revisão humana
antes do teste oficial: pendente. A numeração v1 é a contagem própria do autor,
não a VERSAO do projeto.

Ideia única: o estocástico SAIR da zona de extremo (80 na compra, 20 na venda) com a posição no lucro mostra que o impulso que trouxe o ganho acabou. Tocar a zona não é o sinal (testado: pior); sair dela é.
Papel (V520): titular de ALERTA em estrategia/saida/titular/. Ao vivo roda em sombra: quando
devolve "fechar": True o robô narra e grava o alerta, mas quem fecha a posição é só o
capitão (estrategia/saida/titular/capitao/). Para o ranking do classificacao.py ele é um
cartucho de saída completo, com o mesmo stop inicial do capitão e do saida_baseline.

Regra de saída: a partir do 1º candle depois da entrada, se o lucro no fechamento do candle for
de pelo menos 0.5 R e a condição acima ocorrer, devolve "fechar": True (saída no fechamento).
Sem alvo fixo. Stop inicial: extremo dos 5 últimos candles do sinal (R = distância entrada-stop).

Variações testadas antes desta versão (Regra 11.2) — histórico 2020 a 02/10/2026, mesmas
1.739 entradas do time de 3 titulares, treino 2020-23 / teste 2024-26, saída no fechamento do candle
de 15 min, stop 1 R, sem alvo. Cerca de 70 variações: 20 regras de exaustão (rejeição de pavio
0,4/0,5/0,6; candle de reversão 0,5/0,8/1,0 ATR; MACD perdendo força 2 e 3 candles; esticado
2/3/4 ATR com candle contra ou com pavio; RSI virando em 70/80; falha em novo extremo; estocástico
saindo da zona 70/80) × lucro mínimo 0,5 R / 1,0 R. Referências no mesmo conjunto: saida_baseline
R$ 19.821; stop 1 R sem alvo e sem regra R$ 17.840; trailing de pico R$ 27.773 (simulação).
Melhor regra de exaustão: R$ 24.422 sozinha (2020-23 R$ 7.421; 2024-26 R$ 17.001; melhor que o baseline em 4 de 7 anos).
No motor completo (2020-2026): R$ 25.321.
Sozinha, nenhuma regra de exaustão superou o trailing; somada ao trailing (OU) a melhor
(estocástico saindo da zona 80) acrescentou só cerca de 2% (R$ 28.373 contra R$ 27.773).
Por isso entra como alerta, não como capitão. Resultado financeiro oficial: ainda não medido;
rodar `classificacao.py` (Regra 12). Sem dependência de data, evento ou preço absoluto (Regra 11.3).

Contrato S001: avaliar_saida(row, posicao) -> dict. Não realiza I/O, não mantém estado e não
importa módulos do projeto (Regra 3): as constantes e o cálculo do stop são cópias.
"""

from math import isfinite

CONTRATO_SAIDA = "S001"
NOME = "saida_exaustao_estocastico_v01"
SWING_LOOKBACK_CANDLES = 4
LUCRO_MIN_R = 0.5
ZONA = 80.0          # compra: estocástico estava >= 80 e agora < 80; venda: estava <= 20 e agora > 20


def _numero(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if isfinite(numero) else None


def _stop_inicial(row, posicao):
    """Stop do momento da entrada: extremo dos 5 candles que terminam no candle do sinal."""
    candles = row.get("ohlc_recentes") or ()
    decorridos = int(posicao["candles_decorridos"])
    fim = len(candles) - decorridos
    inicio = fim - (SWING_LOOKBACK_CANDLES + 1)
    if inicio < 0 or fim > len(candles):
        raise ValueError("Histórico insuficiente para recalcular o stop inicial.")
    janela = candles[inicio:fim]
    lado = str(posicao["lado"]).upper()
    if lado == "COMPRA":
        stop = min(float(c["Minimo"]) for c in janela)
    elif lado == "VENDA":
        stop = max(float(c["Maximo"]) for c in janela)
    else:
        raise ValueError(f"Lado inválido: {lado}")
    if not isfinite(stop):
        raise ValueError("Stop inicial inválido.")
    return stop


def _exaustao(row, direcao):
    atual = _numero(row.get("stoch"))
    anterior = _numero(row.get("stoch_prev"))
    if atual is None or anterior is None:
        return False
    if direcao == 1:
        return anterior >= ZONA and atual < ZONA
    return anterior <= 100.0 - ZONA and atual > 100.0 - ZONA


def avaliar_saida(row: dict, posicao: dict) -> dict:
    if not isinstance(row, dict) or not isinstance(posicao, dict):
        raise TypeError("row e posicao precisam ser dicionários.")
    entrada = _numero(posicao.get("entrada"))
    decorridos = _numero(posicao.get("candles_decorridos"))
    if entrada is None or decorridos is None:
        raise ValueError("entrada/candles_decorridos inválidos.")
    comprado = str(posicao["lado"]).upper() == "COMPRA"
    direcao = 1 if comprado else -1
    stop0 = _stop_inicial(row, posicao)
    risco = (entrada - stop0) if comprado else (stop0 - entrada)
    if risco <= 0:
        raise ValueError("Proteção inicial inválida (risco não positivo).")

    if decorridos == 0:
        return {"fechar": False, "novo_stop": stop0, "novo_alvo": None}

    fechamento = _numero(row.get("Fechamento"))
    if fechamento is None or (fechamento - entrada) * direcao < LUCRO_MIN_R * risco:
        return {"fechar": False, "novo_stop": None, "novo_alvo": None}
    return {"fechar": bool(_exaustao(row, direcao)), "novo_stop": None, "novo_alvo": None}


def diagnosticar_saida(row, posicao):
    return "O estocástico está saindo da zona de extremo com a posição no lucro: o impulso que trouxe o ganho está se esgotando."


__all__ = ["CONTRATO_SAIDA", "NOME", "avaliar_saida", "diagnosticar_saida"]

# -*- coding: utf-8 -*-
"""
ROBONILDO - frases_narracao.py

Cadastro de frases fixas, uma por cenário, sem sorteio. Cada situação
específica do robô dispara sempre a mesma frase, de forma previsível.

Para mudar o que é dito em algum cenário, edite somente o texto entre aspas
correspondente. Não é necessário alterar o principal.py.
"""

# ---------- Abertura de posição ----------
FRASE_COMPRA_ABERTA = "Posição de compra aberta."
FRASE_VENDA_ABERTA = "Posição de venda aberta."

# ---------- Fechamento de posição, por motivo específico ----------
FRASES_FECHAMENTO = {
    "ALVO": "Alvo atingido. Fechamos a operação com lucro.",
    "STOP": "Stop acionado. Fechamos a operação com prejuízo.",
    "CORTE_SEGURANCA_LIMITE": "Limite de horário atingido. Encerramento forçado.",
}

# Frases usadas somente se o motivo não estiver no dicionário acima.
FRASE_FECHAMENTO_PADRAO_LUCRO = "Posição encerrada com lucro."
FRASE_FECHAMENTO_PADRAO_PREJUIZO = "Posição encerrada com prejuízo."

# ---------- Narração periódica: estado atual ----------
FRASES_PERIODICAS_SEM_POSICAO = {
    ("ALTA", "FORA"): "A tendência é de alta. Ainda aguardamos o preço se aproximar.",
    ("ALTA", "DENTRO"): "A tendência é de alta, e o preço está dentro da faixa de entrada.",
    ("BAIXA", "FORA"): "A tendência é de baixa. Ainda aguardamos o preço se aproximar.",
    ("BAIXA", "DENTRO"): "A tendência é de baixa, e o preço está dentro da faixa de entrada.",
}

# A narração de posição aberta deixou de usar frase fixa (V413) - agora é
# construída dinamicamente em principal.py com o resultado real e o
# progresso até stop/alvo, usando a mesma _progresso_posicao() que colore
# o marcador visual. Texto fixo não fazia sentido para um estado que muda
# a cada segundo.

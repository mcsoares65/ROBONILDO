"""Auditoria de paridade entre a V19 teórica e a execução observada pelo DDE.

O arquivo é propositalmente append-only: uma falha posterior não apaga o rastro
da decisão anterior. Em ambiente real, o DDE informa o último preço observado e
a quantidade de contratos, mas não confirma o preço de execução da corretora.
Por isso os campos usam o nome ``*_dde`` e nunca afirmam ser o preço de fill.
"""

import csv
from datetime import datetime
from pathlib import Path

import configuracao as cfg


CAMPOS = [
    "evento", "id_operacao", "horario_mercado", "horario_sistema", "modo",
    "fonte_ohlc", "candle", "abertura", "maxima", "minima", "fechamento",
    "sinal_v19", "decisao", "motivo", "entrada_teorica", "entrada_dde",
    "diferenca_entrada_pts", "stop", "alvo", "ordem_enviada",
    "contratos_dde", "saida_teorica", "saida_dde", "diferenca_saida_pts",
    "resultado_teorico_reais", "resultado_dde_reais", "observacao",
]


class AuditorParidade:
    def __init__(self, pasta_logs="logs", habilitado=True):
        self.pasta = Path(pasta_logs)
        self.pasta.mkdir(parents=True, exist_ok=True)
        self.habilitado = habilitado
        self.entradas_dde = {}

    def _arquivo(self, horario):
        return self.pasta / f"auditoria_paridade_{horario.strftime('%Y-%m-%d')}.csv"

    @staticmethod
    def _valor(valor):
        if valor is None:
            return ""
        if isinstance(valor, float):
            return f"{valor:.4f}"
        return valor

    def _gravar(self, horario, **dados):
        if not self.habilitado:
            return
        arquivo = self._arquivo(horario)
        novo = not arquivo.exists()
        linha = {campo: "" for campo in CAMPOS}
        linha.update(dados)
        linha["horario_mercado"] = horario.isoformat()
        linha["horario_sistema"] = datetime.now().isoformat(timespec="milliseconds")
        with open(arquivo, "a", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=CAMPOS, delimiter=";")
            if novo:
                w.writeheader()
            w.writerow({k: self._valor(v) for k, v in linha.items()})

    def registrar_candle(self, horario, candle, modo, fonte_ohlc, sinal,
                         decisao, motivo="", contratos_dde=None):
        self._gravar(
            horario,
            evento="CANDLE_FECHADO",
            modo=modo,
            fonte_ohlc=fonte_ohlc,
            candle=candle.horario.isoformat(),
            abertura=candle.abertura,
            maxima=candle.maxima,
            minima=candle.minima,
            fechamento=candle.fechamento,
            sinal_v19=sinal.lado if sinal else "SEM_SINAL",
            decisao=decisao,
            motivo=motivo,
            entrada_teorica=sinal.entrada if sinal else None,
            stop=sinal.stop if sinal else None,
            alvo=sinal.alvo if sinal else None,
            contratos_dde=contratos_dde,
        )

    def registrar_entrada(self, horario, sinal, preco_dde, ordem_enviada,
                          contratos_dde=None, motivo=""):
        id_operacao = sinal.horario.isoformat()
        diferenca = preco_dde - sinal.entrada if preco_dde is not None else None
        if ordem_enviada:
            self.entradas_dde[id_operacao] = preco_dde
        self._gravar(
            horario,
            evento="ORDEM_ENTRADA",
            id_operacao=id_operacao,
            sinal_v19=sinal.lado,
            decisao="ENTRADA_ACEITA" if ordem_enviada else "ENTRADA_NAO_ENVIADA",
            motivo=motivo,
            entrada_teorica=sinal.entrada,
            entrada_dde=preco_dde,
            diferenca_entrada_pts=diferenca,
            stop=sinal.stop,
            alvo=sinal.alvo,
            ordem_enviada=ordem_enviada,
            contratos_dde=contratos_dde,
            observacao="Preço DDE observado no envio; não é confirmação do fill da corretora.",
        )

    def registrar_saida(self, horario, posicao, motivo, saida_teorica,
                        saida_dde, ordem_enviada, contratos_dde=None):
        id_operacao = posicao.horario_entrada
        entrada_dde = self.entradas_dde.pop(id_operacao, None)
        direcao = 1 if posicao.lado == "COMPRA" else -1
        resultado_teorico = (
            (saida_teorica - posicao.entrada) * direcao * cfg.VALOR_PONTO_REAIS
            - cfg.CUSTO_TOTAL_ESTIMADO_POR_OPERACAO_REAIS
            if saida_teorica is not None else None
        )
        resultado_dde = (
            (saida_dde - entrada_dde) * direcao * cfg.VALOR_PONTO_REAIS
            - cfg.CUSTO_TOTAL_ESTIMADO_POR_OPERACAO_REAIS
            if saida_dde is not None and entrada_dde is not None else None
        )
        diferenca = saida_dde - saida_teorica if saida_dde is not None and saida_teorica is not None else None
        self._gravar(
            horario,
            evento="ORDEM_SAIDA",
            id_operacao=id_operacao,
            sinal_v19=posicao.lado,
            decisao="SAIDA_ACEITA" if ordem_enviada else "SAIDA_NAO_ENVIADA",
            motivo=motivo,
            entrada_teorica=posicao.entrada,
            entrada_dde=entrada_dde,
            stop=posicao.stop,
            alvo=posicao.alvo,
            ordem_enviada=ordem_enviada,
            contratos_dde=contratos_dde,
            saida_teorica=saida_teorica,
            saida_dde=saida_dde,
            diferenca_saida_pts=diferenca,
            resultado_teorico_reais=resultado_teorico,
            resultado_dde_reais=resultado_dde,
            observacao="Resultado DDE é estimado; confirmação exata exige preço médio/fill fornecido pelo Profit.",
        )

"""
ROBONILDO - registrador.py

Grava cada sinal avaliado e cada operacao (aberta/fechada) em arquivos CSV,
um por dia, dentro de logs/.
"""

import csv
from pathlib import Path
from datetime import datetime
from typing import Optional

from motor import Sinal


class Registrador:
    def __init__(self, pasta_logs: str = "logs"):
        self.pasta = Path(pasta_logs)
        self.pasta.mkdir(parents=True, exist_ok=True)

    def _arquivo_sinais(self, data: datetime) -> Path:
        return self.pasta / f"sinais_{data.strftime('%Y-%m-%d')}.csv"

    def _arquivo_operacoes(self, data: datetime) -> Path:
        return self.pasta / f"operacoes_{data.strftime('%Y-%m-%d')}.csv"

    def registrar_sinal(self, sinal: Sinal, aceito: bool, motivo: str = ""):
        """Grava TODO sinal avaliado, aceito ou nao (util para auditoria - responder
        'por que ele operou' ou 'por que ele nao operou' depois)."""
        arquivo = self._arquivo_sinais(sinal.horario)
        novo = not arquivo.exists()
        with open(arquivo, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if novo:
                w.writerow(["horario", "lado", "entrada", "stop", "alvo",
                            "distancia_ma21", "aceito", "motivo_regra", "motivo_decisao"])
            w.writerow([sinal.horario.isoformat(), sinal.lado, sinal.entrada,
                        sinal.stop, sinal.alvo, f"{sinal.distancia_ma21:.1f}",
                        aceito, sinal.motivo, motivo])

    def registrar_operacao_aberta(self, posicao):
        """`posicao` e o objeto Posicao ja aberto pelo motor
        (gestor.posicao_aberta, logo apos abrir_posicao) - NAO o Sinal.

        Regra 1 v10: o motor nao calcula mais stop/alvo, entao Sinal.stop/
        alvo sao sempre None; quem tem os niveis REAIS definidos pelo
        cartucho de saida titular na abertura e a Posicao. Registrar o
        Sinal aqui gravaria stop/alvo vazios sempre, mesmo quando o
        cartucho definiu um nivel real."""
        horario_entrada = datetime.fromisoformat(posicao.horario_entrada)
        arquivo = self._arquivo_operacoes(horario_entrada)
        novo = not arquivo.exists()
        with open(arquivo, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if novo:
                w.writerow(["horario_entrada", "lado", "entrada", "stop", "alvo",
                            "horario_saida", "saida", "resultado_pts", "resultado_reais", "motivo_saida"])
            w.writerow([horario_entrada.isoformat(), posicao.lado, posicao.entrada,
                        posicao.stop, posicao.alvo, "", "", "", "", ""])

    def registrar_operacao_fechada(self, horario_entrada: datetime, horario_saida: datetime,
                                    saida: float, resultado_pts: float, resultado_reais: float,
                                    motivo_saida: str):
        """Atualiza a ultima linha em aberto (sem horario_saida) do dia da entrada."""
        arquivo = self._arquivo_operacoes(horario_entrada)
        if not arquivo.exists():
            return
        linhas = list(csv.reader(open(arquivo, encoding="utf-8")))
        cabecalho, dados = linhas[0], linhas[1:]
        for linha in reversed(dados):
            if linha[0] == horario_entrada.isoformat() and linha[5] == "":
                linha[5] = horario_saida.isoformat()
                linha[6] = str(saida)
                linha[7] = f"{resultado_pts:.1f}"
                linha[8] = f"{resultado_reais:.2f}"
                linha[9] = motivo_saida
                break
        with open(arquivo, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(cabecalho)
            w.writerows(dados)

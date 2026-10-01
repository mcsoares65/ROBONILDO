"""
ROBONILDO - coleta_dde.py (V460)

COLETA PASSIVA de campos extras do DDE (quantidade, negocios, volume, estocastico
do Profit). So GRAVA em logs/coleta_dde_AAAA-MM-DD.csv. NAO e lido por nenhum
modulo de decisao: motor, estrategias, gestor de risco e executor nao importam
este arquivo e nada aqui altera sinal, stop, alvo ou ordem. Qualquer erro e
engolido (best-effort) para nunca afetar o robo.

Para que serve: o CSV historico nao traz Negocios nem estocastico oficial, e o
volume por candle ao vivo nunca foi validado contra o historico. Acumulando dias
de dados reais, da para (1) validar Quantidade do DDE contra a Quantidade do CSV
exportado, (2) comparar o %K do Profit com o %K do motor (que usa maxima/minima
amostradas a cada 2s, sempre mais estreitas que as reais) e (3) so ENTAO decidir
se algum desses campos entra no motor (Regra 4: nada vale sem backtest).

Os campos do DDE de volume/quantidade/negocios sao ACUMULADOS NO DIA. O valor do
candle e a diferenca entre o acumulado no fim dele e no fim do anterior. O ultimo
valor "do candle" e o da amostra ANTERIOR a que fecha o candle (a amostra que
dispara o fechamento ja pertence ao candle seguinte).

Ligar: em leitor_dde.COLUNAS_EXTRAS_DDE, mapear nome -> coluna da planilha, p.ex.
    {"quantidade": "K", "negocios": "J", "volume": "L", "estoc_profit": "Q"}
Vazio (padrao) = desligado, comportamento identico ao da V459.
Regra 3 do compliance: este arquivo nao importa modulos do projeto.
"""

import csv
from pathlib import Path

_ACUMULADOS = ("quantidade", "negocios", "volume")


class ColetaDDE:
    def __init__(self, pasta_logs, nomes):
        self.pasta = Path(pasta_logs)
        self.nomes = [n for n in nomes]
        self._ultimo = {}          # extras da amostra mais recente
        self._base = {}            # acumulados no fim do candle anterior
        self._dia_base = None

    def processar(self, horario_mercado, extras, candle_fechado):
        """Chamar a cada amostra, depois de construtor.nova_leitura()."""
        try:
            if candle_fechado is not None and self._ultimo:
                self._gravar(candle_fechado)
            if extras:
                self._ultimo = dict(extras)
                self._ultimo["_dia"] = horario_mercado.date()
        except Exception as e:  # nunca afeta o robo
            print(f"[COLETA_DDE] erro ignorado: {e}")

    def _gravar(self, candle):
        fim = self._ultimo
        dia = fim.get("_dia")
        linha = {"horario_candle": candle.horario.strftime("%Y-%m-%d %H:%M"),
                 "fechamento": candle.fechamento}
        for nome in self.nomes:
            v = fim.get(nome)
            linha[f"{nome}_fim"] = "" if v is None else v
            if nome in _ACUMULADOS:
                base = self._base.get(nome) if self._dia_base == dia else None
                ok = v is not None and base is not None and v >= base
                linha[f"{nome}_candle"] = (v - base) if ok else ""
                if v is not None:
                    self._base[nome] = v
        self._dia_base = dia
        self.pasta.mkdir(parents=True, exist_ok=True)
        caminho = self.pasta / f"coleta_dde_{candle.horario.strftime('%Y-%m-%d')}.csv"
        novo = not caminho.exists()
        campos = list(linha.keys())
        with open(caminho, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=campos, delimiter=";")
            if novo:
                w.writeheader()
            w.writerow(linha)

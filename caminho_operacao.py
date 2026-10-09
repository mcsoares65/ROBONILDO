"""V505 - caminho de cada operacao: pico, vale, derrapagem e trilha de precos.

Pergunta do dono (07/10/2026): "o lucro de pico e devolvido antes da saida?". O backtest
so enxerga maxima/minima de candle de 15 min e diz que e raro (11 em 103); as operacoes
ao vivo de 06 e 07/10 mostraram o contrario. Este modulo grava, para cada operacao REAL,
o que aconteceu entre a entrada e a saida, com a leitura do DDE (nao e o fill da corretora):

  caminho_operacoes.csv        uma linha por operacao fechada (append-only, todos os dias)
  caminho_pontos_<dia>.csv     trilha de precos da operacao (horario, preco, resultado)
  caminho_aberto.json          estado da operacao em curso (sobrevive a reinicio do robo)

Nao decide nada: nao interfere em entrada, saida, ordem nem risco. Toda falha de gravacao
e engolida (com aviso), nunca derruba o robo. analisar_caminhos.py le estes arquivos e
simula regras de saida (ex.: "estopar quando cair X% do pico") sobre a trilha real.
"""

import csv
import json
from datetime import datetime
from pathlib import Path

import configuracao as cfg

ARQUIVO_RESUMO = "caminho_operacoes.csv"
ARQUIVO_ABERTO = "caminho_aberto.json"
INTERVALO_MIN_PONTO_S = 1.0   # no maximo 1 ponto por segundo na trilha (alem de pico/vale novos)

CAMPOS_RESUMO = [
    "data", "id_operacao", "lado", "entrada", "entrada_dde",
    "horario_entrada", "horario_saida", "duracao_min", "motivo",
    "stop", "alvo",
    "saida_teorica", "saida_dde", "derrapagem_pts", "saida_usada",
    "resultado_pts", "resultado_reais",
    "pico_pts", "pico_reais", "horario_pico", "min_ate_pico",
    "vale_pts", "vale_reais", "horario_vale",
    "devolucao_pts", "devolucao_pct_pico",
    "leituras", "maior_intervalo_s",
]
CAMPOS_PONTOS = ["id_operacao", "horario", "preco", "resultado_pts", "resultado_reais"]


def _direcao(lado):
    return 1 if lado == "COMPRA" else -1


class CaminhoOperacao:
    def __init__(self, pasta_logs="logs", habilitado=True):
        self.pasta = Path(pasta_logs)
        self.habilitado = habilitado
        self.estado = None          # dict da operacao em curso
        self._ultimo_ponto_dt = None
        if self.habilitado:
            try:
                self.pasta.mkdir(parents=True, exist_ok=True)
                self._carregar()
            except Exception as erro:
                print(f"[CAMINHO] Falha ao iniciar ({erro}); gravacao do caminho desligada.")
                self.habilitado = False

    # ---------- persistencia do estado em curso ----------
    @property
    def _arq_aberto(self):
        return self.pasta / ARQUIVO_ABERTO

    def _carregar(self):
        if self._arq_aberto.exists():
            try:
                self.estado = json.loads(self._arq_aberto.read_text(encoding="utf-8"))
            except Exception:
                self.estado = None

    def _salvar(self):
        try:
            if self.estado is None:
                if self._arq_aberto.exists():
                    self._arq_aberto.unlink()
            else:
                self._arq_aberto.write_text(json.dumps(self.estado, ensure_ascii=False), encoding="utf-8")
        except Exception as erro:
            print(f"[CAMINHO] Falha ao salvar estado: {erro}")

    # ---------- trilha ----------
    def _gravar_ponto(self, horario, preco, pts):
        arquivo = self.pasta / f"caminho_pontos_{horario.strftime('%Y-%m-%d')}.csv"
        novo = not arquivo.exists()
        with open(arquivo, "a", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            if novo:
                w.writerow(CAMPOS_PONTOS)
            w.writerow([self.estado["id"], horario.isoformat(), f"{preco:.2f}",
                        f"{pts:.2f}", f"{pts * cfg.valor_ponto_total():.2f}"])

    # ---------- chamado a cada leitura do DDE com posicao aberta ----------
    def atualizar(self, posicao, preco, horario):
        """Atualiza pico/vale/trilha. Chamar ANTES de qualquer checagem de saida."""
        if not self.habilitado or posicao is None or preco is None:
            return
        try:
            self._atualizar(posicao, float(preco), horario)
        except Exception as erro:
            print(f"[CAMINHO] Falha ao atualizar: {erro}")

    def _atualizar(self, posicao, preco, horario):
        id_op = posicao.horario_entrada
        iniciou = False
        if self.estado is None or self.estado.get("id") != id_op:
            # operacao nova (ou estado velho de outra operacao: descartado)
            self.estado = {
                "id": id_op, "lado": posicao.lado, "entrada": posicao.entrada,
                "pico_pts": 0.0, "horario_pico": id_op,
                "vale_pts": 0.0, "horario_vale": id_op,
                "leituras": 0, "maior_intervalo_s": 0.0, "ultima_leitura": None,
            }
            self._ultimo_ponto_dt = None
            iniciou = True
        e = self.estado
        pts = (preco - posicao.entrada) * _direcao(posicao.lado)

        novo_extremo = False
        if pts > e["pico_pts"]:
            e["pico_pts"], e["horario_pico"] = pts, horario.isoformat()
            novo_extremo = True
        if pts < e["vale_pts"]:
            e["vale_pts"], e["horario_vale"] = pts, horario.isoformat()
            novo_extremo = True

        if e["ultima_leitura"]:
            try:
                gap = (horario - datetime.fromisoformat(e["ultima_leitura"])).total_seconds()
                e["maior_intervalo_s"] = max(e["maior_intervalo_s"], gap)
            except ValueError:
                pass
        e["ultima_leitura"] = horario.isoformat()
        e["leituras"] += 1

        gravar = (self._ultimo_ponto_dt is None or novo_extremo or
                  (horario - self._ultimo_ponto_dt).total_seconds() >= INTERVALO_MIN_PONTO_S)
        if gravar:
            self._gravar_ponto(horario, preco, pts)
            self._ultimo_ponto_dt = horario
        if iniciou or novo_extremo or e["leituras"] % 30 == 0:
            self._salvar()

    # ---------- chamado depois do fechamento ----------
    def fechar(self, posicao, horario, motivo, saida_teorica, saida_dde,
               preco_saida, resultado_pts, resultado_reais, entrada_dde=None):
        if not self.habilitado:
            return None
        linha = None
        try:
            linha = self._fechar(posicao, horario, motivo, saida_teorica, saida_dde,
                                 preco_saida, resultado_pts, resultado_reais, entrada_dde)
        except Exception as erro:
            print(f"[CAMINHO] Falha ao gravar resumo: {erro}")
        finally:
            self.estado = None
            self._ultimo_ponto_dt = None
            self._salvar()
        return linha   # dict do resumo gravado (ou None); usado para a planilha (V507)

    def _fechar(self, posicao, horario, motivo, saida_teorica, saida_dde,
                preco_saida, resultado_pts, resultado_reais, entrada_dde):
        if self.estado is None or self.estado.get("id") != posicao.horario_entrada:
            # sem leituras registradas (ex.: operacao aberta e fechada no mesmo instante)
            self.estado = {
                "id": posicao.horario_entrada, "lado": posicao.lado, "entrada": posicao.entrada,
                "pico_pts": 0.0, "horario_pico": posicao.horario_entrada,
                "vale_pts": 0.0, "horario_vale": posicao.horario_entrada,
                "leituras": 0, "maior_intervalo_s": 0.0, "ultima_leitura": None,
            }
        e = self.estado
        d = _direcao(posicao.lado)
        # a leitura da saida tambem conta para pico/vale
        if saida_dde is not None:
            pts_saida = (float(saida_dde) - posicao.entrada) * d
            if pts_saida > e["pico_pts"]:
                e["pico_pts"], e["horario_pico"] = pts_saida, horario.isoformat()
            if pts_saida < e["vale_pts"]:
                e["vale_pts"], e["horario_vale"] = pts_saida, horario.isoformat()
        derrapagem = None
        if saida_dde is not None and saida_teorica is not None:
            # positivo = pior para o robo (comprado: saiu abaixo do nivel; vendido: acima)
            derrapagem = (float(saida_teorica) - float(saida_dde)) * d
        t_ent = datetime.fromisoformat(posicao.horario_entrada)
        t_pico = datetime.fromisoformat(e["horario_pico"])
        pico_reais = e["pico_pts"] * cfg.valor_ponto_total()
        devolucao = e["pico_pts"] - resultado_pts
        v = cfg.valor_ponto_total()
        linha = {
            "data": horario.strftime("%Y-%m-%d"), "id_operacao": posicao.horario_entrada,
            "lado": posicao.lado, "entrada": posicao.entrada, "entrada_dde": entrada_dde,
            "horario_entrada": posicao.horario_entrada, "horario_saida": horario.isoformat(),
            "duracao_min": round((horario - t_ent).total_seconds() / 60, 1), "motivo": motivo,
            "stop": posicao.stop, "alvo": posicao.alvo,
            "saida_teorica": saida_teorica, "saida_dde": saida_dde,
            "derrapagem_pts": derrapagem, "saida_usada": preco_saida,
            "resultado_pts": resultado_pts, "resultado_reais": resultado_reais,
            "pico_pts": e["pico_pts"], "pico_reais": pico_reais,
            "horario_pico": e["horario_pico"],
            "min_ate_pico": round((t_pico - t_ent).total_seconds() / 60, 1),
            "vale_pts": e["vale_pts"], "vale_reais": e["vale_pts"] * v,
            "horario_vale": e["horario_vale"],
            "devolucao_pts": devolucao,
            "devolucao_pct_pico": (devolucao / e["pico_pts"] * 100) if e["pico_pts"] > 0 else None,
            "leituras": e["leituras"], "maior_intervalo_s": round(e["maior_intervalo_s"], 1),
        }
        arquivo = self.pasta / ARQUIVO_RESUMO
        novo = not arquivo.exists()
        with open(arquivo, "a", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=CAMPOS_RESUMO, delimiter=";")
            if novo:
                w.writeheader()
            w.writerow({k: ("" if x is None else (f"{x + 0.0:.2f}" if isinstance(x, float) else x))
                        for k, x in linha.items()})
        return linha

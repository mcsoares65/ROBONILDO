"""V520 - alertas de exaustao da saida: nivel de confianca, contador de sustentacao e log.

Os titulares de ALERTA (estrategia/saida/titular/*.py, fora de capitao/) rodam em sombra no
candle ainda em formacao. Cada um que devolve "fechar": True e um voto de exaustao. O NIVEL
e quantos votos existem agora (1..total). Como o contador "ha Ns" da entrada, o monitor mede
em relogio real ha quantos segundos o nivel atual se mantem; se o nivel muda, o contador
recomeca; se o candle fecha ou a posicao muda, tudo recomeca.

NAO decide nada: nao fecha posicao, nao mexe em stop/alvo, nao interfere em ordem nem risco.
So quem fecha e o capitao (estrategia/saida/titular/capitao/). Qualquer falha (cartucho de
alerta com erro, disco cheio) e engolida, nunca derruba o robo.

Log (append-only, um arquivo por dia) em <pasta_logs>/alertas_saida_AAAA-MM-DD.csv:
  evento: SUBIU (nivel aumentou), CAIU (diminuiu mas segue > 0), DESFEZ (voltou a 0), SUSTENTA (cada INTERVALO s com nivel>0),
          RESUMO (uma linha ao fim da posicao: nivel maximo e maior sustentacao).
O resultado final da operacao fica em caminho_operacoes.csv (mesmo horario_entrada); juntar
as duas tabelas e o que permite medir, depois de algumas semanas, se "nivel N ha S segundos"
antecipa de fato a devolucao do lucro.
"""

import csv
from datetime import datetime
from pathlib import Path

INTERVALO_NARRACAO_S = 10

CAMPOS_LOG = [
    "horario", "evento", "horario_entrada", "lado", "entrada", "preco", "candle",
    "nivel", "total", "alertas", "segundos", "lucro_pts", "pico_pts",
    "nivel_max", "sustentacao_max_s",
]


class MonitorAlertasSaida:
    def __init__(self, alertas, pasta_logs=None, intervalo_s=INTERVALO_NARRACAO_S, habilitado=True):
        """alertas: lista de (nome, modulo) com avaliar_saida e (opcional) diagnosticar_saida."""
        self.alertas = list(alertas)
        self.total = len(self.alertas)
        self.pasta = Path(pasta_logs) if pasta_logs else None
        self.intervalo_s = intervalo_s
        self.habilitado = habilitado and self.total > 0
        self._zerar()

    # ---------- estado ----------
    def _zerar(self):
        self.chave = None            # (candle, horario_entrada)
        self.horario_entrada = None
        self.nivel = 0
        self.nomes = []
        self.desde = None            # relogio real em que o nivel atual comecou
        self.ultima_fala = None      # relogio real da ultima narracao
        self.nivel_max = 0
        self.sustentacao_max_s = 0
        self._ctx = None

    def segundos(self, agora_real):
        if self.nivel <= 0 or self.desde is None:
            return 0
        return max(0, int((agora_real - self.desde).total_seconds()))

    def texto_painel(self, agora_real):
        """Trecho para a linha da posicao no painel ('' se nao ha titulares de alerta)."""
        if not self.habilitado:
            return ""
        if self.nivel <= 0:
            return f" | Exaustão 0/{self.total}"
        return f" | Exaustão {self.nivel}/{self.total} há {self.segundos(agora_real)}s"

    # ---------- avaliacao ----------
    def avaliar(self, row, posicao_especulativa, chave, agora_real, contexto):
        """Chamado a cada leitura com posicao aberta. `contexto` e um dict com horario_entrada,
        lado, entrada, preco, candle, lucro_pts, pico_pts, lucro_reais (so para log/frase).

        Devolve a frase a narrar (str) ou None."""
        if not self.habilitado:
            return None
        try:
            return self._avaliar(row, posicao_especulativa, chave, agora_real, contexto)
        except Exception as erro:   # nunca derruba o robo
            print(f"[ALERTA DE SAÍDA] falha ignorada: {type(erro).__name__}: {erro}")
            return None

    def _avaliar(self, row, posicao_especulativa, chave, agora_real, contexto):
        if self.chave is not None and chave != self.chave:
            # candle novo (ou posicao nova): comeca do zero. A posicao so muda de verdade em encerrar().
            if self.chave[1] == chave[1]:
                nivel_max, sust_max = self.nivel_max, self.sustentacao_max_s
                self._zerar()
                self.nivel_max, self.sustentacao_max_s = nivel_max, sust_max
            else:
                self.encerrar(agora_real)
        self.chave = chave
        self.horario_entrada = contexto.get("horario_entrada")
        self._ctx = contexto

        votos = []
        for nome, modulo in self.alertas:
            try:
                resposta = modulo.avaliar_saida(row, posicao_especulativa)
            except Exception:
                continue
            if isinstance(resposta, dict) and bool(resposta.get("fechar", False)):
                votos.append((nome, modulo))
        nivel = len(votos)
        nomes = [n for n, _ in votos]

        fala = None
        if nivel != self.nivel:
            anterior = self.nivel
            self.nivel, self.nomes = nivel, nomes
            self.desde = agora_real if nivel > 0 else None
            if nivel > anterior:
                self.nivel_max = max(self.nivel_max, nivel)
                self._gravar("SUBIU", agora_real)
                fala = self._frase_subiu(votos, row, posicao_especulativa, contexto)
                self.ultima_fala = agora_real
            elif nivel == 0:
                self._gravar("DESFEZ", agora_real)
                fala = "A exaustão se desfez."
                self.ultima_fala = None
            else:  # caiu mas ainda ha votos
                self._gravar("CAIU", agora_real)
                self.ultima_fala = agora_real
        elif nivel > 0:
            self.nomes = nomes
            seg = self.segundos(agora_real)
            self.sustentacao_max_s = max(self.sustentacao_max_s, seg)
            if self.ultima_fala is None or (agora_real - self.ultima_fala).total_seconds() >= self.intervalo_s:
                self._gravar("SUSTENTA", agora_real)
                fala = self._frase_sustenta(seg, contexto)
                self.ultima_fala = agora_real
        return fala

    def encerrar(self, agora_real):
        """Fim da posicao (ou troca): grava o RESUMO se houve algum alerta e zera o estado."""
        if self.habilitado and self.nivel_max > 0 and self._ctx is not None:
            self._gravar("RESUMO", agora_real)
        self._zerar()

    # ---------- frases (sem termos de futebol; numeros ja calculados pelo robo) ----------
    def _frase_subiu(self, votos, row, posicao_especulativa, contexto):
        partes = []
        for _, modulo in votos:
            diag = getattr(modulo, "diagnosticar_saida", None)
            if callable(diag):
                try:
                    texto = diag(row, posicao_especulativa)
                except Exception:
                    texto = None
                if isinstance(texto, str):
                    partes.append(texto.rstrip("."))
        base = f"Exaustão nível {self.nivel} de {self.total}."
        if partes:
            base += " " + ". ".join(partes) + "."
        return base + self._sufixo_lucro(contexto)

    def _frase_sustenta(self, segundos, contexto):
        return (f"Exaustão nível {self.nivel} de {self.total}, sustentada há {segundos} segundos."
                + self._sufixo_lucro(contexto))

    @staticmethod
    def _sufixo_lucro(contexto):
        reais = contexto.get("lucro_reais")
        if reais is None:
            return ""
        return f" Resultado atual de {f'{reais:.2f}'.replace('.', ',')} reais."

    # ---------- log ----------
    def _gravar(self, evento, agora_real):
        if self.pasta is None:
            return
        ctx = self._ctx or {}
        try:
            self.pasta.mkdir(parents=True, exist_ok=True)
            arquivo = self.pasta / f"alertas_saida_{agora_real.strftime('%Y-%m-%d')}.csv"
            novo = not arquivo.exists()
            with arquivo.open("a", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=CAMPOS_LOG, delimiter=";")
                if novo:
                    w.writeheader()
                w.writerow({
                    "horario": agora_real.strftime("%H:%M:%S"),
                    "evento": evento,
                    "horario_entrada": ctx.get("horario_entrada", ""),
                    "lado": ctx.get("lado", ""),
                    "entrada": ctx.get("entrada", ""),
                    "preco": ctx.get("preco", ""),
                    "candle": ctx.get("candle", ""),
                    "nivel": self.nivel,
                    "total": self.total,
                    "alertas": "|".join(self.nomes),
                    "segundos": self.segundos(agora_real),
                    "lucro_pts": ctx.get("lucro_pts", ""),
                    "pico_pts": ctx.get("pico_pts", ""),
                    "nivel_max": self.nivel_max,
                    "sustentacao_max_s": self.sustentacao_max_s,
                })
        except Exception as erro:
            print(f"[ALERTA DE SAÍDA] falha ao gravar o log ({erro}); seguindo sem gravar.")

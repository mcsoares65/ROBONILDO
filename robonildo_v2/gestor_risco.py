"""
ROBONILDO - gestor_risco.py
Versao: V200 (primeira integracao com padroes reaproveitados do ROBONILDO_109)

Reaproveita do projeto anterior (operacao/gestao_risco.py):
  - Persistencia de estado em JSON (sobrevive a reinicio do processo)
  - Reset automatico diario
  - Circuit breaker (pausa apos sequencia de perdas)
  - Ciclo de vida da posicao (abrir / verificar / fechar)

Substitui do projeto anterior:
  - calculo de stop/alvo: agora usa a regra MA_v2 (stop estrutural do estrategia.py),
    nao mais stop fixo em pontos/percentual
  - margem de zeragem: 17:45 (nao 18:18 - muito apertado, ver regras_pregao.py)
"""

from dataclasses import dataclass, asdict
from typing import Optional, Tuple
from datetime import datetime, date
from pathlib import Path
import json

import configuracao as cfg
from estrategia._nucleo import Sinal


@dataclass
class Posicao:
    lado: str  # COMPRA ou VENDA
    entrada: float
    stop: float
    alvo: float
    horario_entrada: str  # isoformat
    motivo_entrada: str


class GestorRisco:
    """
    Controla quantas operacoes ja aconteceram no dia, se ja existe posicao aberta,
    e decide se um novo Sinal pode virar operacao real (ou so registro de referencia).

    NAO envia ordem nenhuma - isso e responsabilidade de outro modulo, quando
    ENVIAR_ORDENS estiver habilitado no futuro.
    """

    def __init__(self, arquivo_estado: str = "logs/estado_risco.json", horario_mercado_inicial: Optional[datetime] = None):
        self.arquivo_estado = Path(arquivo_estado)
        self.arquivo_estado.parent.mkdir(parents=True, exist_ok=True)

        self.posicao_aberta: Optional[Posicao] = None
        self.operacoes_hoje: int = 0
        self.perdas_hoje: int = 0
        # IMPORTANTE: usa o horario do MERCADO (replay ou ao vivo), nao o relogio
        # real do computador - senao, testar dois dias de mercado diferentes no
        # mesmo dia real faz o robo achar que ainda e "o mesmo dia" e carregar
        # contadores (ex: perdas_hoje) de um teste anterior sem querer.
        self.data_atual: date = (horario_mercado_inicial or datetime.now()).date()
        self.banca_atual: float = cfg.BANCA_ATUAL_REAIS  # NAO reseta diariamente -
                                                          # acumula o resultado real
                                                          # de todas as operacoes

        self._carregar_estado()

    # ---------- Persistencia ----------
    def _carregar_estado(self):
        if not self.arquivo_estado.exists():
            return
        try:
            estado = json.loads(self.arquivo_estado.read_text(encoding="utf-8"))
            # banca_atual e carregada SEMPRE, independente de mudanca de dia -
            # ela e cumulativa, nao reseta como operacoes_hoje/perdas_hoje
            self.banca_atual = estado.get("banca_atual", cfg.BANCA_ATUAL_REAIS)

            data_salva = date.fromisoformat(estado["data"])
            if data_salva != self.data_atual:
                self._resetar_dia()
                return
            self.operacoes_hoje = estado.get("operacoes_hoje", 0)
            self.perdas_hoje = estado.get("perdas_hoje", 0)
            if estado.get("posicao"):
                self.posicao_aberta = Posicao(**estado["posicao"])
        except Exception as e:
            print(f"[GESTOR_RISCO] Erro ao carregar estado, iniciando limpo: {e}")

    def _salvar_estado(self):
        estado = {
            "data": self.data_atual.isoformat(),
            "operacoes_hoje": self.operacoes_hoje,
            "perdas_hoje": self.perdas_hoje,
            "posicao": asdict(self.posicao_aberta) if self.posicao_aberta else None,
            "banca_atual": self.banca_atual,
        }
        self.arquivo_estado.write_text(
            json.dumps(estado, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def _resetar_dia(self):
        self.operacoes_hoje = 0
        self.perdas_hoje = 0
        self.posicao_aberta = None
        # banca_atual NAO e resetada aqui - continua acumulando entre dias
        self._salvar_estado()

    def _checar_novo_dia(self, horario_mercado: datetime):
        dia_mercado = horario_mercado.date()
        if dia_mercado != self.data_atual:
            self.data_atual = dia_mercado
            self._resetar_dia()

    # ---------- Regras ----------
    def pode_abrir_posicao(self, horario: datetime) -> Tuple[bool, str]:
        self._checar_novo_dia(horario)

        if self.posicao_aberta is not None:
            return False, "Ja existe posicao aberta"
        if self.operacoes_hoje >= cfg.MAX_OPERACOES_DIA:
            return False, f"Limite diario de operacoes atingido ({cfg.MAX_OPERACOES_DIA})"
        if self.perdas_hoje >= cfg.MAX_PERDAS_DIA:
            return False, f"Limite diario de perdas atingido ({cfg.MAX_PERDAS_DIA})"
        if horario.strftime("%H:%M") >= cfg.HORARIO_BLOQUEIO_NOVAS_ENTRADAS:
            return False, f"Apos horario limite para novas entradas ({cfg.HORARIO_BLOQUEIO_NOVAS_ENTRADAS})"
        return True, ""

    def abrir_posicao(self, sinal: Sinal) -> Tuple[bool, str]:
        pode, motivo = self.pode_abrir_posicao(sinal.horario)
        if not pode:
            return False, motivo

        self.posicao_aberta = Posicao(
            lado=sinal.lado,
            entrada=sinal.entrada,
            stop=sinal.stop,
            alvo=sinal.alvo,
            horario_entrada=sinal.horario.isoformat(),
            motivo_entrada=sinal.motivo,
        )
        self.operacoes_hoje += 1
        self._salvar_estado()
        return True, f"Posicao aberta: {sinal.lado} @ {sinal.entrada}"

    def verificar_saida_continua(self, preco_atual: float) -> Optional[Tuple[str, float]]:
        """
        Verifica stop/alvo usando o preco TICK A TICK (nao esperando o candle
        de 15min fechar). Um stop/alvo real na corretora executaria no instante
        em que o preco tocasse o nivel - esperar o fechamento do candle atrasaria
        a reacao em ate 15 minutos, o que e inaceitavel com capital real.

        Retorna (motivo, preco_atual) se bateu, None caso contrario.
        """
        if self.posicao_aberta is None:
            return None

        pos = self.posicao_aberta
        if pos.lado == "COMPRA":
            if preco_atual <= pos.stop:
                return "STOP", preco_atual
            if preco_atual >= pos.alvo:
                return "ALVO", preco_atual
        else:
            if preco_atual >= pos.stop:
                return "STOP", preco_atual
            if preco_atual <= pos.alvo:
                return "ALVO", preco_atual
        return None

    def verificar_saida(self, maxima_candle: float, minima_candle: float, horario: datetime) -> Optional[Tuple[str, float]]:
        """
        Verifica se o candle atual (maxima/minima) bateu o stop ou o alvo.
        Retorna (motivo, preco_saida) ou None.

        NAO fecha mais por horario aqui - isso passou a ser responsabilidade de
        verificar_corte_final(), que monitora em tempo real (nao por candle) e
        forca o fechamento apenas em HORARIO_LIMITE_ABSOLUTO (18:20), no lucro
        ou no prejuizo - sem trava antecipada.
        """
        if self.posicao_aberta is None:
            return None

        pos = self.posicao_aberta
        if pos.lado == "COMPRA":
            if minima_candle <= pos.stop:
                return "STOP", pos.stop
            if maxima_candle >= pos.alvo:
                return "ALVO", pos.alvo
        else:
            if maxima_candle >= pos.stop:
                return "STOP", pos.stop
            if minima_candle <= pos.alvo:
                return "ALVO", pos.alvo

        return None

    def resultado_flutuante(self, preco_atual: float) -> float:
        """Resultado em pontos se a posicao fosse fechada agora, ao preco_atual."""
        if self.posicao_aberta is None:
            return 0.0
        pos = self.posicao_aberta
        sinal_direcao = 1 if pos.lado == "COMPRA" else -1
        return (preco_atual - pos.entrada) * sinal_direcao

    def verificar_corte_final(self, preco_atual: float, horario: datetime) -> Optional[Tuple[str, float]]:
        """
        Chamado em modo continuo (nao por candle), enquanto a posicao estiver
        aberta. Regra unica: a posicao fica aberta ate HORARIO_LIMITE_ABSOLUTO
        (18:20), esteja no lucro ou no prejuizo - so ai fecha forcadamente, de
        qualquer forma, para nunca ultrapassar o limite real da corretora e
        cair na taxa de zeragem.
        """
        if self.posicao_aberta is None:
            return None

        hm = horario.strftime("%H:%M")
        if hm >= cfg.HORARIO_LIMITE_ABSOLUTO:
            return "CORTE_SEGURANCA_LIMITE", preco_atual

        return None  # ainda dentro do horario, continua monitorando normalmente

    def fechar_posicao(self, preco_saida: float, motivo: str) -> Tuple[float, str]:
        if self.posicao_aberta is None:
            return 0.0, "Nenhuma posicao aberta para fechar"

        pos = self.posicao_aberta
        sinal_direcao = 1 if pos.lado == "COMPRA" else -1
        resultado_pontos = (preco_saida - pos.entrada) * sinal_direcao
        resultado_reais = resultado_pontos * cfg.VALOR_PONTO_REAIS - cfg.CUSTO_TOTAL_ESTIMADO_POR_OPERACAO_REAIS

        if resultado_pontos < 0:
            self.perdas_hoje += 1

        self.banca_atual += resultado_reais

        msg = (f"Posicao fechada: {pos.lado} | Entrada={pos.entrada} Saida={preco_saida} | "
               f"Resultado={resultado_pontos:.1f}pts (R${resultado_reais:.2f}) | Motivo={motivo} | "
               f"Banca atual: R${self.banca_atual:.2f}")

        self.posicao_aberta = None
        self._salvar_estado()
        return resultado_pontos, msg

    def status(self, horario_mercado: datetime) -> dict:
        self._checar_novo_dia(horario_mercado)
        return {
            "posicao_aberta": self.posicao_aberta is not None,
            "operacoes_hoje": self.operacoes_hoje,
            "perdas_hoje": self.perdas_hoje,
            "pode_operar": self.pode_abrir_posicao(horario_mercado)[0],
        }

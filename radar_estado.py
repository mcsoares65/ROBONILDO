"""V546 - estado do radar: o que o robo publica para a tela radar/radar.html desenhar.

A pagina le radar/radar_estado.js (window.RADAR_ESTADO = {...}) a cada segundo. O arquivo traz
SO o que a tela precisa para desenhar: por estrategia do time um rumo estavel (id), o lado
(+1 compra, -1 venda) e a confianca (0 a 1); o consenso do time; se ha posicao; e o evento de
captura (contador que sobe a cada entrada aceita). V547: tambem o cabecalho de mercado (ativo,
horario do mercado, preco atual e tamanho do candle), que e dado publico. Nunca grava nome de
estrategia, condicao, limite nem preco de entrada/stop: quem receber o arquivo nao deduz as regras.

NAO decide nada. Qualquer falha (disco, permissao, pagina lendo o arquivo) e engolida; nunca
derruba o robo.
"""

import json
import os
import time
from pathlib import Path
from typing import Optional

from versionamento import VERSAO


def _lado(direcao) -> int:
    texto = str(direcao or "").upper()
    return 1 if texto == "COMPRA" else -1 if texto == "VENDA" else 0


class PublicadorRadar:
    def __init__(self, caminho, modo: str, envia_ordens: bool = False, intervalo_s: float = 1.0):
        self.caminho = Path(caminho)
        self.modo = modo                      # "replay" ou "normal"
        self.envia_ordens = bool(envia_ordens)
        self.intervalo_s = intervalo_s
        self._ids: dict = {}                  # titular -> indice estavel (ordem de aparicao)
        self._n = 0                           # numero da atualizacao (a pagina usa para saber se esta viva)
        self._captura_seq = 0
        self._captura_lado = 0
        self._ultimo = None                   # relogio monotonico da ultima gravacao
        self._forcar = False

    def capturar(self, lado) -> None:
        """Chamado quando o robo ABRE uma posicao (ordem enviada no fechamento do candle)."""
        self._captura_seq += 1
        self._captura_lado = _lado(lado)
        self._forcar = True

    @staticmethod
    def _mercado(mercado) -> Optional[dict]:
        if not mercado:
            return None
        horario = mercado.get("horario")
        preco = mercado.get("preco")
        return {
            "ativo": str(mercado.get("ativo") or ""),
            "horario": horario.isoformat(timespec="seconds") if hasattr(horario, "isoformat") else None,
            "preco": float(preco) if isinstance(preco, (int, float)) else None,
            "timeframe_min": int(mercado.get("timeframe_min") or 15),
        }

    def montar(self, radar, consenso: float, posicao_aberta, mercado=None) -> dict:
        melhores: dict = {}
        for item in radar or []:
            chave = item.get("titular") or item.get("estrategia")
            if chave is None:
                continue
            if chave not in self._ids:
                self._ids[chave] = len(self._ids)
            conf = max(0.0, min(1.0, float(item.get("progresso", 0.0) or 0.0)))
            atual = melhores.get(chave)
            if atual is None or conf > atual["conf"]:
                melhores[chave] = {"dir": _lado(item.get("direcao")), "conf": conf}
        estrategias = []
        for chave, indice in sorted(self._ids.items(), key=lambda kv: kv[1]):
            m = melhores.get(chave, {"dir": 0, "conf": 0.0})
            estrategias.append({"id": indice, "dir": m["dir"], "conf": round(m["conf"], 4)})
        return {
            "n": self._n,
            "versao": VERSAO,
            "modo": self.modo,
            "radar_envia_ordens": self.envia_ordens,
            "estrategias": estrategias,
            "consenso": round(max(0.0, min(1.0, float(consenso or 0.0))), 4),
            "posicao": _lado(getattr(posicao_aberta, "lado", None)) if posicao_aberta is not None else None,
            "captura": {"seq": self._captura_seq, "dir": self._captura_lado},
            "mercado": self._mercado(mercado),
        }

    def publicar(self, radar, consenso: float, posicao_aberta, agora: Optional[float] = None, mercado=None) -> bool:
        """Grava o estado se ja passou o intervalo (ou se houve captura). Devolve True se gravou."""
        try:
            agora = time.monotonic() if agora is None else agora
            if (not self._forcar and self._ultimo is not None
                    and agora - self._ultimo < self.intervalo_s):
                return False
            self._n += 1
            estado = self.montar(radar, consenso, posicao_aberta, mercado)
            texto = "window.RADAR_ESTADO = " + json.dumps(estado, ensure_ascii=False) + ";\n"
            self.caminho.parent.mkdir(parents=True, exist_ok=True)
            temp = self.caminho.with_suffix(".tmp")
            temp.write_text(texto, encoding="utf-8")
            os.replace(temp, self.caminho)
            self._ultimo = agora
            self._forcar = False
            return True
        except Exception:
            self._ultimo = agora if agora is not None else self._ultimo
            return False

"""Escalação dos titulares de entrada (o "radar" que escala quem entra em campo).

A pasta estrategia/entrada/titular/ aceita VÁRIOS cartuchos, cada um uma ideia só
(Regra 16). Esta peça junta os titulares e se apresenta ao motor como se fosse um
cartucho único: `gerar_sinal(row)` e `diagnosticar_oportunidades(row)`. Assim o
robô ao vivo (principal.py) e o juiz (classificacao.py) usam exatamente a mesma
lógica de escalação (Regra de paridade replay/ao vivo).

Regras da escalação (Regra 17):
- A cada candle fechado todos os titulares são consultados.
- Se nenhum sinaliza: sem sinal.
- Se sinalizam só para um lado: o titular de maior prioridade entra em campo.
  Prioridade = atributo opcional PRIORIDADE_ESCALACAO do cartucho (menor vence);
  empate ou ausência: ordem alfabética do nome do arquivo.
- Se há sinais em lados opostos no mesmo candle: não entra (o motor fica de fora)
  e o conflito fica registrado em `ultimo_conflito`.
- O motor continua com uma posição por vez e com todas as regras de risco de hoje.
- Um cartucho que lance exceção NÃO é silenciado: o erro sobe, como acontece hoje
  com um titular único.

A escalação NÃO é um cartucho e NÃO concorre no ranking: é um agendador do motor
(como o próprio motor). O juiz a mede como uma linha de comparação contra os
titulares individuais, para provar que o time vale mais que o melhor jogador.
"""

from __future__ import annotations

from typing import Callable, Optional

PRIORIDADE_PADRAO = 999


class Membro:
    """Um titular de entrada: nome (arquivo) + funções do cartucho."""

    def __init__(self, nome: str, modulo=None, *, gerar_sinal: Optional[Callable] = None):
        self.nome = nome
        self.gerar_sinal = gerar_sinal or getattr(modulo, "gerar_sinal", None)
        if not callable(self.gerar_sinal):
            raise TypeError(f"O titular '{nome}' precisa fornecer gerar_sinal(row).")
        self.diagnosticar_oportunidades = getattr(modulo, "diagnosticar_oportunidades", None)
        self.diagnosticar_sinal = getattr(modulo, "diagnosticar_sinal", None)
        prioridade = getattr(modulo, "PRIORIDADE_ESCALACAO", PRIORIDADE_PADRAO)
        self.prioridade = int(prioridade)


def _direcao_texto(sinal: int, row: dict) -> str:
    if sinal == 1:
        return "COMPRA"
    if sinal == -1:
        return "VENDA"
    tendencia = row.get("trend")
    return "COMPRA" if tendencia == 1 else "VENDA" if tendencia == -1 else "NEUTRA"


class Escalacao:
    def __init__(self, membros: list[Membro]):
        if not membros:
            raise ValueError("A escalação precisa de pelo menos um titular de entrada.")
        nomes = [m.nome.casefold() for m in membros]
        if len(set(nomes)) != len(nomes):
            raise ValueError("Titulares repetidos na escalação (Regra 7).")
        self.membros = sorted(membros, key=lambda m: (m.prioridade, m.nome.casefold()))
        self.ultimo_titular: Optional[str] = None     # quem entrou em campo no último sinal
        self.ultimo_conflito: Optional[dict] = None   # {nome: sinal} se houve lados opostos
        self.nome = "TIME(" + "+".join(m.nome for m in self.membros) + ")"

    # ---------- sinal ----------
    def _sinais(self, row: dict) -> dict:
        sinais = {}
        for membro in self.membros:
            bruto = membro.gerar_sinal(row)
            if bruto not in (-1, 0, 1):
                raise ValueError(
                    f"Direção de sinal inválida em {membro.nome}: {bruto!r}. Esperado 1, -1 ou 0."
                )
            if bruto:
                sinais[membro.nome] = bruto
        return sinais

    def gerar_sinal(self, row: dict) -> int:
        self.ultimo_titular = None
        self.ultimo_conflito = None
        sinais = self._sinais(row)
        if not sinais:
            return 0
        if len(set(sinais.values())) > 1:
            self.ultimo_conflito = dict(sinais)
            return 0
        escalado = next(m for m in self.membros if m.nome in sinais)
        self.ultimo_titular = escalado.nome
        return sinais[escalado.nome]

    # ---------- radar ----------
    def diagnosticar_oportunidades(self, row: dict) -> list[dict]:
        """Radar de todos os titulares. Cada item traz o campo `titular` (arquivo).
        Titular sem radar próprio vira uma oportunidade única: 100% se sinaliza."""
        itens = []
        for ordem, membro in enumerate(self.membros):
            if callable(membro.diagnosticar_oportunidades):
                for item in membro.diagnosticar_oportunidades(row):
                    novo = dict(item)
                    novo["titular"] = membro.nome
                    novo["prioridade"] = ordem * 100 + int(novo.get("prioridade", 99))
                    itens.append(novo)
                continue
            sinal = membro.gerar_sinal(row)
            itens.append({
                "titular": membro.nome,
                "estrategia": membro.nome,
                "prioridade": ordem * 100,
                "direcao": _direcao_texto(sinal, row),
                "sinal": sinal,
                "confirmadas": 1 if sinal else 0,
                "total": 1,
                "progresso": 1.0 if sinal else 0.0,
                "faltantes": [] if sinal else ["condições da estratégia"],
                "detalhe": "" if sinal else "aguardando condições",
                "bloqueio_horario": False,
            })
        return sorted(itens, key=lambda i: (-float(i.get("progresso", 0.0)), i["prioridade"]))

    def diagnosticar_sinal(self, row: dict) -> dict:
        """Diagnóstico para a narração: o titular escalado, ou o mais próximo de disparar."""
        radar = self.diagnosticar_oportunidades(row)
        confirmadas = [i for i in radar if i.get("sinal") in (-1, 1)]
        item = min(confirmadas, key=lambda i: i["prioridade"]) if confirmadas else radar[0]
        faltantes = item.get("faltantes") or []
        proxima = faltantes[0] if faltantes else "nenhuma"
        return {
            "porta": self.membros.index(
                next(m for m in self.membros if m.nome == item["titular"])) + 1,
            "total_portas": len(self.membros),
            "estrategia": item.get("estrategia", item["titular"]),
            "lado": item.get("direcao", "NEUTRA"),
            "progresso": item.get("progresso", 0.0),
            "confirmadas": item.get("confirmadas", 0),
            "total": item.get("total", 0),
            "faltantes": faltantes,
            "explicacao": (
                f"A estratégia {item.get('estrategia', item['titular'])} está com "
                f"{item.get('confirmadas', 0)} de {item.get('total', 0)} confirmações. "
                f"Próxima condição: {proxima}."
            ),
        }


__all__ = ["Escalacao", "Membro", "PRIORIDADE_PADRAO"]

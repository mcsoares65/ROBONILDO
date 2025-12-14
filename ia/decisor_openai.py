from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class DecisaoIA:
    action: str
    confidence: Optional[float]
    reason_short: str
    reason_long: Optional[str] = None
    timestamp: Optional[str] = None


class DecisorOpenAI:
    def __init__(self) -> None:
        self.nome_modelo = "openai-vision"

    def decidir(self) -> DecisaoIA:
        """
        Placeholder de decisão automática. A implementação real deve usar
        o modelo de visão da OpenAI para analisar o contexto atual.
        """
        return DecisaoIA(
            action="AGUARDAR",
            confidence=None,
            reason_short="Aguardando sinal; IA simulada.",
            reason_long=None,
            timestamp=datetime.utcnow().isoformat(),
        )

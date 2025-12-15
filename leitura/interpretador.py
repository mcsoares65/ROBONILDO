# ARQUIVO: leitura/interpretador.py
# ROBONILDO_101 — Interpretador de cenário (texto curto e narrável)

class InterpretadorCenario:
    def interpretar(self, estado: dict) -> str:
        """
        estado esperado (exemplo):
        {
            "tendencia": "alta" | "baixa" | "lateral",
            "volatilidade": "baixa" | "media" | "alta",
            "regiao": "topo" | "fundo" | "meio",
            "debug": {...}  # opcional
        }
        """

        tendencia = estado.get("tendencia")
        volatilidade = estado.get("volatilidade")
        regiao = estado.get("regiao")

        # 1) Fala ultra curta baseada em volatilidade (prioridade alta)
        if volatilidade == "alta":
            return "Mercado acelerado. Cautela total."
        if volatilidade == "media":
            return "Mercado ativo. Vou observar."
        if volatilidade == "baixa":
            return "Mercado frio. Paciência."

        # 2) Regras de contexto (fallback)
        if tendencia == "lateral":
            return "Mercado lateral. Sem pressa."
        if tendencia == "alta" and regiao == "fundo":
            return "Tendência de alta. Região interessante."
        if tendencia == "baixa" and regiao == "topo":
            return "Mercado pressionado. Cuidado com venda."

        # 3) Fallback final
        return "Cenário indefinido. Vou observar."

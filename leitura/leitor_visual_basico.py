# ARQUIVO: leitura/leitor_visual_basico.py
# ROBONILDO_101 — Leitura visual mínima do frame (sem OCR): atividade/contraste/energia

import numpy as np


class LeitorVisualBasico:
    def analisar(self, frame_bgra: np.ndarray) -> dict:
        """
        frame_bgra: numpy array (H, W, 4) em BGRA (do MSS)
        Retorna um estado simples para o InterpretadorCenario.
        """

        if frame_bgra is None or frame_bgra.size == 0:
            return {"tendencia": "lateral", "volatilidade": "baixa", "regiao": "meio"}

        # BGRA -> BGR
        bgr = frame_bgra[:, :, :3].astype(np.int16)
        b = bgr[:, :, 0]
        g = bgr[:, :, 1]
        r = bgr[:, :, 2]

        # Métricas baratas
        brilho = (r + g + b) / 3.0
        contraste = float(brilho.std())          # “energia visual”
        media = float(brilho.mean())

        # “atividade” aproximada: quanto o frame tem de áreas bem verdes ou bem vermelhas
        # (isso pega candles/indicadores coloridos, sem saber o que são)
        verdes = np.sum((g - r) > 35)
        vermelhos = np.sum((r - g) > 35)
        total = frame_bgra.shape[0] * frame_bgra.shape[1]
        taxa_cor = float((verdes + vermelhos) / max(total, 1))

        # Classificação simples
        if contraste > 40 or taxa_cor > 0.08:
            volatilidade = "alta"
        elif contraste > 25 or taxa_cor > 0.04:
            volatilidade = "media"
        else:
            volatilidade = "baixa"

        # Tendência aqui ainda é “neutra” (sem OCR / sem candle real)
        tendencia = "lateral"

        # Região (só pra preencher a estrutura)
        regiao = "meio"

        return {
            "tendencia": tendencia,
            "volatilidade": volatilidade,
            "regiao": regiao,
            "debug": {
                "media_brilho": round(media, 2),
                "contraste": round(contraste, 2),
                "taxa_cor": round(taxa_cor, 4),
                "verdes": int(verdes),
                "vermelhos": int(vermelhos),
            }
        }

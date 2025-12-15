# ARQUIVO: ia/decisor_openai.py
# PROJETO: ROBONILDO_103
# FUNÇÃO: manda print → recebe JSON (AGUARDAR/COMPRAR/VENDER) + contexto (REPLAY/LEILAO/preço/níveis)
#
# ✅ Continuação direta da sua versão 102 (mesma estrutura, mais campos sem engessar).
# ✅ Mantém compatibilidade: action/confidence/reason_short/notes continuam existindo.
# ✅ Adiciona: session_mode (REPLAY/AO_VIVO/DESCONHECIDO) e market_status (NORMAL/LEILAO/DESCONHECIDO)
# ✅ Campos "inteligentes" são opcionais e podem vir vazios sem quebrar.

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Optional, Tuple, Any, Dict, List

from openai import OpenAI


# ==============================
# MODELO DE SAÍDA
# ==============================

@dataclass
class DecisaoIA:
    # Compatível com v102
    action: str            # AGUARDAR | COMPRAR | VENDER
    confidence: float      # 0.0..1.0
    reason_short: str      # narrável (1 frase)
    notes: str = ""        # opcional (curto)

    # Novos campos v103 (opcionais / seguros)
    session_mode: str = "DESCONHECIDO"     # REPLAY | AO_VIVO | DESCONHECIDO
    market_status: str = "DESCONHECIDO"    # NORMAL | LEILAO | DESCONHECIDO

    # Extras (se a IA conseguir inferir com evidência visual)
    price_now: Optional[float] = None
    key_levels: Optional[List[Dict[str, Any]]] = None
    flow_bias: str = "DESCONHECIDO"        # COMPRADOR | VENDEDOR | NEUTRO | DESCONHECIDO


# ==============================
# DECISOR OPENAI (VISION)
# ==============================

class DecisorOpenAI:
    """
    v103:
    - recebe print (frame BGRA)
    - chama OpenAI Vision
    - retorna DecisaoIA
    - NÃO engessa estratégia (sem IF de trade aqui)
    - SÓ pede para classificar REPLAY e LEILAO quando houver evidência visual
    """

    def __init__(self, modelo: str = "gpt-5-mini"):
        self.client = OpenAI()
        self.model = modelo

    # --------------------------
    # helpers
    # --------------------------

    @staticmethod
    def _to_data_url_png(frame_bgra) -> str:
        import numpy as np
        import cv2

        if frame_bgra is None:
            raise ValueError("frame_bgra is None")

        if frame_bgra.dtype != np.uint8:
            frame_bgra = frame_bgra.astype(np.uint8)

        # Profit vindo BGRA (mss) → converter para BGR e encodar em PNG
        if frame_bgra.ndim == 3 and frame_bgra.shape[2] == 4:
            bgr = cv2.cvtColor(frame_bgra, cv2.COLOR_BGRA2BGR)
        else:
            # Se já vier BGR, tenta encodar direto
            bgr = frame_bgra

        ok, buf = cv2.imencode(".png", bgr)
        if not ok:
            raise RuntimeError("Falha ao encodar PNG")

        b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
        return f"data:image/png;base64,{b64}"

    @staticmethod
    def _parse_json_only(text: str) -> Tuple[Optional[dict], str]:
        if not text:
            return None, "Resposta vazia"

        try:
            obj = json.loads(text)
            if isinstance(obj, dict):
                return obj, ""
        except Exception:
            pass

        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            candidate = text[start:end + 1]
            try:
                obj = json.loads(candidate)
                if isinstance(obj, dict):
                    return obj, ""
            except Exception as e:
                return None, f"JSON inválido: {e}"

        return None, "Não achei JSON na resposta"

    @staticmethod
    def _norm_action(v: Any) -> str:
        s = str(v or "").strip().upper()
        if s in ("COMPRAR", "COMPRA", "BUY"):
            return "COMPRAR"
        if s in ("VENDER", "VENDA", "SELL"):
            return "VENDER"
        return "AGUARDAR"

    @staticmethod
    def _norm_session_mode(v: Any) -> str:
        s = str(v or "").strip().upper()
        if s in ("REPLAY", "REPLAY_DE_MERCADO", "REPLAY_MERCADO"):
            return "REPLAY"
        if s in ("AO_VIVO", "AOVIVO", "LIVE", "NORMAL"):
            return "AO_VIVO"
        return "DESCONHECIDO"

    @staticmethod
    def _norm_market_status(v: Any) -> str:
        s = str(v or "").strip().upper()
        if s in ("LEILAO", "LEILÃO", "AUCTION"):
            return "LEILAO"
        if s in ("NORMAL", "ABERTO", "MERCADO"):
            return "NORMAL"
        return "DESCONHECIDO"

    @staticmethod
    def _clamp01(v: Any, default: float = 0.55) -> float:
        try:
            x = float(v)
        except Exception:
            x = float(default)
        if x < 0.0:
            return 0.0
        if x > 1.0:
            return 1.0
        return x

    @staticmethod
    def _safe_float(v: Any) -> Optional[float]:
        if v is None:
            return None
        try:
            return float(v)
        except Exception:
            return None

    # --------------------------
    # decisão
    # --------------------------

    def decidir(self, frame_bgra, timeframe: str = "30m") -> DecisaoIA:
        img_url = self._to_data_url_png(frame_bgra)

        system = (
            "Você é o ROBONILDO_103, assistente de decisão para day trade no mini índice (WIN) baseado em visão.\n"
            "Você recebe um print do ProfitPro e deve retornar SOMENTE um JSON válido (sem markdown, sem texto extra).\n"
            "Importante:\n"
            "- Seja conservador: se não estiver MUITO claro, responda AGUARDAR.\n"
            "- Não invente dados (preço, níveis, indicadores, leilão, replay) se não estiver visível.\n"
            "- Se você enxergar evidência clara de 'Replay', marque session_mode=REPLAY.\n"
            "- Se você enxergar evidência clara de 'Leilão', marque market_status=LEILAO.\n"
            "- reason_short deve ser UMA frase curta em português, narrável.\n"
        )

        # Prompt simples: deixa o modelo “pensar” livremente, mas devolver estrutura.
        user = f"""
Analise o print do gráfico do WIN no ProfitPro (timeframe {timeframe}) e decida UMA ação: AGUARDAR, COMPRAR ou VENDER.

Regras:
- Conservador por padrão.
- Se estiver confuso ou incompleto, AGUARDAR.
- Não invente o que não estiver visível.
- Se aparecer "Replay" (ou evidência clara), session_mode deve ser REPLAY.
- Se aparecer "Leilão" (ou evidência clara), market_status deve ser LEILAO.

Retorne EXATAMENTE neste formato (JSON):
{{
  "action": "AGUARDAR|COMPRAR|VENDER",
  "confidence": 0.0,
  "reason_short": "frase curta",
  "notes": "opcional, curto",
  "session_mode": "REPLAY|AO_VIVO|DESCONHECIDO",
  "market_status": "NORMAL|LEILAO|DESCONHECIDO",
  "price_now": null,
  "key_levels": null,
  "flow_bias": "COMPRADOR|VENDEDOR|NEUTRO|DESCONHECIDO"
}}
"""

        # Se a sua SDK suportar response_format com json_schema, ajuda MUITO a evitar texto extra.
        # Se não suportar, o parser abaixo ainda tenta extrair JSON.
        try:
            resp = self.client.responses.create(
                model=self.model,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "robonildo_103_decisao",
                        "schema": {
                            "type": "object",
                            "additionalProperties": True,
                            "properties": {
                                "action": {"type": "string", "enum": ["AGUARDAR", "COMPRAR", "VENDER"]},
                                "confidence": {"type": "number"},
                                "reason_short": {"type": "string"},
                                "notes": {"type": "string"},
                                "session_mode": {"type": "string", "enum": ["REPLAY", "AO_VIVO", "DESCONHECIDO"]},
                                "market_status": {"type": "string", "enum": ["NORMAL", "LEILAO", "DESCONHECIDO"]},
                                "price_now": {"type": ["number", "null"]},
                                "key_levels": {"type": ["array", "null"], "items": {"type": "object"}},
                                "flow_bias": {"type": "string"},
                            },
                            "required": ["action", "confidence", "reason_short", "session_mode", "market_status"],
                        },
                    },
                },
                input=[
                    {"role": "system", "content": [{"type": "input_text", "text": system}]},
                    {"role": "user", "content": [
                        {"type": "input_text", "text": user},
                        {"type": "input_image", "image_url": img_url},
                    ]},
                ],
            )
        except TypeError:
            # fallback caso sua SDK não aceite response_format
            resp = self.client.responses.create(
                model=self.model,
                input=[
                    {"role": "system", "content": [{"type": "input_text", "text": system}]},
                    {"role": "user", "content": [
                        {"type": "input_text", "text": user},
                        {"type": "input_image", "image_url": img_url},
                    ]},
                ],
            )

        # Extrair texto do output (Responses API)
        out_text = ""
        try:
            # caminho comum nas SDKs atuais
            if hasattr(resp, "output_text") and resp.output_text:
                out_text = resp.output_text
            else:
                for item in resp.output:
                    if getattr(item, "type", "") == "message":
                        for c in getattr(item, "content", []):
                            if getattr(c, "type", "") in ("output_text", "text"):
                                out_text += getattr(c, "text", "")
        except Exception:
            out_text = ""

        data, err = self._parse_json_only(out_text)
        if err or not data:
            return DecisaoIA(
                action="AGUARDAR",
                confidence=0.51,
                reason_short="Não consegui ler o cenário com segurança. Vou aguardar.",
                notes=f"parse_error={err}",
                session_mode="DESCONHECIDO",
                market_status="DESCONHECIDO",
                price_now=None,
                key_levels=None,
                flow_bias="DESCONHECIDO",
            )

        action = self._norm_action(data.get("action", "AGUARDAR"))
        conf = self._clamp01(data.get("confidence", 0.55), default=0.55)

        reason = str(data.get("reason_short", "")).strip() or "Vou aguardar."
        # Proteção para não “explodir” narração com textão
        if len(reason) > 240:
            reason = reason[:240].rsplit(" ", 1)[0] + "..."

        notes = str(data.get("notes", "")).strip()
        if len(notes) > 240:
            notes = notes[:240].rsplit(" ", 1)[0] + "..."

        session_mode = self._norm_session_mode(data.get("session_mode", "DESCONHECIDO"))
        market_status = self._norm_market_status(data.get("market_status", "DESCONHECIDO"))

        price_now = self._safe_float(data.get("price_now", None))

        key_levels = data.get("key_levels", None)
        if not isinstance(key_levels, list):
            key_levels = None

        flow_bias = str(data.get("flow_bias", "DESCONHECIDO")).strip().upper()
        if flow_bias not in ("COMPRADOR", "VENDEDOR", "NEUTRO", "DESCONHECIDO"):
            flow_bias = "DESCONHECIDO"

        return DecisaoIA(
            action=action,
            confidence=conf,
            reason_short=reason,
            notes=notes,
            session_mode=session_mode,
            market_status=market_status,
            price_now=price_now,
            key_levels=key_levels,
            flow_bias=flow_bias,
        )

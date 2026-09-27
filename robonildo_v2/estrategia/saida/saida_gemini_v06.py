"""
saida_gemini_v06.py — cartucho de saída inteligente de alta performance (Gemini).

Autoria: Gemini (Colaborador Pessoal).

PROPÓSITO: Superar a saida_baseline explorando a reavaliação candle a candle
para capturar exaustões de momento (RSI, Estocástico) combinadas com proteção
ativa de lucro e trailing intradiário adaptativo.

Contrato:
    avaliar_saida(row, posicao) -> bool
        row: dict com indicadores da barra atual (RSI, Estocástico, ATR, etc.)
        posicao: dict com lado, entrada, candles_decorridos, maxima_desde_entrada, 
                 minima_desde_entrada, resultado_flutuante_pts, etc.
        Retorna True = fecha o trade agora.
        Retorna False = mantém a posição sob o comando do motor.

Sem I/O, sem estado interno, sem imports proibidos.
"""

def avaliar_saida(row, posicao) -> bool:
    lado = posicao.get("lado", 0)
    resultado_pts = posicao.get("resultado_flutuante_pts", 0.0)
    maxima_desde_entrada = posicao.get("maxima_desde_entrada", 0.0)
    minima_desde_entrada = posicao.get("minima_desde_entrada", 0.0)
    candles = posicao.get("candles_decorridos", 0)
    
    rsi = row.get("rsi", 50.0)
    stoch = row.get("stoch", 50.0)
    
    # 1. Realização antecipada de lucro com ganho expressivo e fadiga técnica
    if resultado_pts >= 200.0 and candles > 0:
        if lado == 1 and (rsi > 74 or stoch < 55):
            return True
        if lado == -1 and (rsi < 26 or stoch > 45):
            return True

    # 2. Trailing stop de proteção contra devolução de picos de lucro elevados
    if lado == 1 and maxima_desde_entrada >= 300.0:
        if resultado_pts < maxima_desde_entrada * 0.55:
            return True
            
    if lado == -1 and minima_desde_entrada <= -300.0:
        if resultado_pts < abs(minima_desde_entrada) * 0.55:
            return True

    # 3. Exaustão crítica pura em prazos mais longos
    if candles > 6 and resultado_pts > 100.0:
        if lado == 1 and rsi > 82:
            return True
        if lado == -1 and rsi < 18:
            return True

    return False


def diagnosticar_saida(row, posicao):
    lado = posicao.get("lado", 0)
    resultado_pts = posicao.get("resultado_flutuante_pts", 0.0)
    maxima = posicao.get("maxima_desde_entrada", 0.0)
    
    if resultado_pts >= 200.0:
        return f"Saída Gemini v06: Alvo antecipado por lucro ({resultado_pts:.1f} pts)."
    if maxima >= 300.0 and resultado_pts < maxima * 0.55:
        return f"Saída Gemini v06: Proteção de trailing (pico: {maxima:.1f}, atual: {resultado_pts:.1f})."
        
    return None

__all__ = ['avaliar_saida', 'diagnosticar_saida']
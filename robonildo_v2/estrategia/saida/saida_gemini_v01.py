"""
saida_gemini_v01.py — cartucho de saída inteligente (Gemini).

Autoria: Gemini (Colaborador Pessoal), sob o contrato oficial de saída dinâmica.

PROPÓSITO: Superar a saída baseline antecipando saídas em pontos de exaustão
técnica (RSI) ou realização de lucros parciais expressivos, respeitando 
estritamente as regras de prioridade do motor (o motor continua mandando no stop/alvo).

Contrato:
    avaliar_saida(row, posicao) -> bool
        row: dict com indicadores (RSI, etc.)
        posicao: dict com lado, entrada, candles_decorridos, maxima_desde_entrada, 
                 minima_desde_entrada, resultado_flutuante_pts, etc.
        Retorna True = fecha o trade agora.
        Retorna False = mantém a posição sob o comando do motor.

Sem I/O, sem estado interno, sem imports proibidos.
"""

def avaliar_saida(row, posicao) -> bool:
    lado = posicao.get("lado", 0)
    resultado_pts = posicao.get("resultado_flutuante_pts", 0.0)
    rsi = row.get("RSI", 50.0)
    
    # Trava de proteção de lucro: se já abrimos mais de 250 pts de lucro e 
    # o preço começa a dar sinais de fadiga, realizamos para não devolver.
    if resultado_pts >= 250.0:
        # Se o RSI esticar demais contra a posição ou perder o momentum, sai.
        if lado == 1 and rsi > 75:
            return True
        if lado == -1 and rsi < 25:
            return True

    # Exaustão pura por sobrecompra/sobrevenda extrema
    if lado == 1 and rsi > 82:
        return True
    elif lado == -1 and rsi < 18:
        return True
        
    return False


def diagnosticar_saida(row, posicao):
    """
    Explicação opcional da decisão de saída para auditoria no laboratório.
    """
    lado = posicao.get("lado", 0)
    resultado_pts = posicao.get("resultado_flutuante_pts", 0.0)
    rsi = row.get("RSI", 50.0)
    
    if resultado_pts >= 250.0 and ((lado == 1 and rsi > 75) or (lado == -1 and rsi < 25)):
        return f"Saída Gemini v01: Realização de lucro protegido ({resultado_pts:.1f} pts) com RSI em {rsi:.1f}."
    if lado == 1 and rsi > 82:
        return f"Saída Gemini v01: Exaustão de alta no RSI ({rsi:.1f})."
    if lado == -1 and rsi < 18:
        return f"Saída Gemini v01: Exaustão de baixa no RSI ({rsi:.1f} )."
        
    return None


__all__ = ['avaliar_saida', 'diagnosticar_saida']
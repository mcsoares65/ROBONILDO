"""
Cartucho de Saída: saida_gemini_v1
Foco: Proteção Dinâmica de MFE + Fuga por Reversão
"""

def avaliar_saida(row: dict, posicao: dict) -> bool:
    lado = posicao["lado"]
    resultado = posicao["resultado_flutuante_pts"]
    atr = row.get("atr", 0.0)
    
    if not atr or atr <= 0:
        return False

    # 1. Cálculo da Excursão Máxima a Favor (MFE)
    if lado == "COMPRA":
        mfe_pts = posicao["maxima_desde_entrada"] - posicao["entrada"]
    else:
        mfe_pts = posicao["entrada"] - posicao["minima_desde_entrada"]

    # 2. Trailing Stop Baseado em MFE vs ATR
    # Só arma após andar 1,5 ATR a nosso favor. Se armado, não permite devolver
    # mais que 0,75 ATR do topo alcançado.
    if mfe_pts > 1.5 * atr:
        drawdown_do_topo = mfe_pts - resultado
        if drawdown_do_topo > 0.75 * atr:
            return True

    # 3. Fuga por Reversão Técnica (Apenas no Lucro)
    # Se já garantimos > 0,5 ATR, abandonamos o trade se os indicadores virarem.
    if resultado > 0.5 * atr:
        rsi = row.get("rsi")
        
        if lado == "COMPRA":
            rsi_sobrecomprado_caindo = (rsi is not None and rsi > 70 and row.get("rsi_descendo"))
            if row.get("stoch_cross_down_80") or row.get("macd_cross_down") or rsi_sobrecomprado_caindo:
                return True
        else:
            rsi_sobrevendido_subindo = (rsi is not None and rsi < 30 and row.get("rsi_subindo"))
            if row.get("stoch_cross_up_20") or row.get("macd_cross_up") or rsi_sobrevendido_subindo:
                return True

    # 4. Limpeza de Fim de Pregão
    # Corta o risco após as 17:45 se estiver no azul, evitando a loteria do fim do dia.
    hora = row["dt"].strftime("%H:%M")
    if hora >= "17:45" and resultado > 0:
        return True

    return False
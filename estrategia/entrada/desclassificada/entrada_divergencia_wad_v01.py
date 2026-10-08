"""Entrada de divergência de extremos com Williams A/D (variante sem volume).

Autoria: Manus (IA), proposta em 08/10/2026. Revisão humana: pendente.
Origem: seção "Acumulação/Distribuição Williams" do PDF da Nelogica
"indicadores_completo.pdf", pp. 6–10; fórmula sem volume documentada em
https://help.tc2000.com/m/69445/l/755887-williams-accumulation-distribution
O motor fornece row['wad_preco_recentes']; o cartucho NÃO calcula o indicador.
Este WAD usa apenas OHLC: não é fluxo de negócios, volume ou agressão DDE.

Hipótese distinta das entradas titulares: o preço faz um novo extremo, mas o
WAD não o confirma; entra só após rompimento do extremo oposto do candle de
preparação. Não consulta MA21/MA50, MACD, estocástico ou portas do time.

Variações relevantes testadas: uma (esta formulação pré-registrada);
nenhum limiar ajustado por resultados. Referência
nos 16 candles [-22:-6]; preparação no candle [-2]; confirmação no [-1].
Compra se mínima da preparação < mínimo da referência, WAD da preparação >
WAD no candle desse mínimo e fechamento atual > máxima da preparação.
Venda simétrica. Com empate de extremo na referência, usa o mais recente.
Sem datas, níveis absolutos, estado global, I/O ou imports do projeto.
Resultado financeiro não validado; não é cartucho titular.
Contrato: gerar_sinal(row) -> 1 | 0 | -1.
"""

NOME = "entrada_divergencia_wad_v01"
JANELA_REFERENCIA = 16
INICIO_REFERENCIA = 22
FIM_REFERENCIA = 6


def gerar_sinal(row: dict) -> int:
    barras = row.get("ohlc_recentes") or ()
    wad = row.get("wad_preco_recentes") or ()
    if len(barras) < INICIO_REFERENCIA or len(wad) != len(barras):
        return 0
    referencia = barras[-INICIO_REFERENCIA:-FIM_REFERENCIA]
    if len(referencia) != JANELA_REFERENCIA:
        return 0

    # Índices relativos à série completa: não há leitura de candles futuros.
    inicio = len(barras) - INICIO_REFERENCIA
    indice_fundo = max(range(JANELA_REFERENCIA),
                       key=lambda i: (-float(referencia[i]["Minimo"]), i))
    indice_topo = max(range(JANELA_REFERENCIA),
                      key=lambda i: (float(referencia[i]["Maximo"]), i))
    preparacao = barras[-2]
    atual = barras[-1]

    compra = (float(preparacao["Minimo"]) < float(referencia[indice_fundo]["Minimo"])
              and wad[-2] > wad[inicio + indice_fundo]
              and float(atual["Fechamento"]) > float(preparacao["Maximo"]))
    venda = (float(preparacao["Maximo"]) > float(referencia[indice_topo]["Maximo"])
             and wad[-2] < wad[inicio + indice_topo]
             and float(atual["Fechamento"]) < float(preparacao["Minimo"]))
    return 1 if compra and not venda else (-1 if venda and not compra else 0)


__all__ = ["NOME", "gerar_sinal"]

"""
analise.py — roda as estratégias TITULARES (entrada + saída) contra o
histórico oficial e exporta a movimentação dia-a-dia (uma linha por
operação fechada) em .xlsx, no mesmo formato do relatório manual já
usado no laboratório (Data | Hora de entrada | Hora de saída | Tipo da
operação | Resultado (R$) | Total acumulado (R$) | Motivo).

Não duplica lógica de backtest nem de descoberta de cartuchos: importa
classificacao.py e motor.py e usa exatamente as mesmas funções que já
rodam oficialmente (carregar_csv, descobrir_entradas/descobrir_saidas,
executar_jogo) — as operações que saem aqui são as mesmas que sairiam do
motor oficial para o mesmo histórico e os mesmos titulares. classificacao.py
não é alterado, só importado.

Diferença para o `classificacao.py`: aquele responde "qual estratégia é
melhor" (ranking entrada × saída). Este responde "o que aconteceu, dia a
dia, rodando só os titulares atuais" — é o extrato de operações, não um
ranking.

Uso (executar de dentro da pasta do projeto, ao lado de classificacao.py):

    python analise.py
    python analise.py "D:\\DAYTRADE\\HISTORICO\\WINFUT_F_0_15min.csv"
    python analise.py --inicio 2026-09-01 --fim 2026-09-25
    python analise.py --saida-dir "D:\\DAYTRADE\\ANALISES" --nome extrato_setembro

Parâmetros:
    caminho             (posicional, opcional) CSV do histórico oficial, ou
                         pasta que o contém (pega o .csv mais recente).
                         Padrão: cfg.CAMINHO_HISTORICO_INICIAL (mesmo padrão
                         de classificacao.py).
    --inicio AAAA-MM-DD  Primeiro dia a incluir no relatório (padrão: o
                         primeiro dia disponível no histórico, após o
                         aquecimento de 65 candles dos indicadores).
    --fim AAAA-MM-DD    Último dia a incluir (padrão: o último dia do
                         histórico).
    --saida-dir PASTA   Pasta onde a planilha será salva.
                        Padrão: D:\\DAYTRADE\\ANALISES
    --nome NOME         Nome base do arquivo (sem extensão).
                        Padrão: extrato_titulares_<AAAAMMDD>_<AAAAMMDD>
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# Reaproveita a engine oficial - zero lógica de backtest duplicada aqui.
import classificacao as cl
import configuracao as cfg

try:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
except ImportError:
    sys.exit(
        "Pacote 'openpyxl' não encontrado. Instale com:\n"
        "    pip install openpyxl"
    )


CABECALHO_FILL = PatternFill(start_color="FF17365D", end_color="FF17365D", fill_type="solid")
CABECALHO_FONTE = Font(name="Arial", bold=True, color="FFFFFFFF")
TITULO_FONTE = Font(name="Arial", bold=True, size=14)
ROTULO_FONTE = Font(name="Arial", bold=True, size=10)
FONTE_PADRAO = Font(name="Arial", size=10)
FORMATO_MOEDA = '"R$ "#,##0.00;[Red]"(R$ "#,##0.00\\);\\-'
FORMATO_DATA = "dd/mm/yyyy"


def _resolver_caminho_historico(informado: str) -> Path:
    caminho = Path(informado)
    if caminho.is_dir():
        candidatos = sorted(
            caminho.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True
        )
        if not candidatos:
            raise SystemExit(f"Nenhum .csv encontrado em '{caminho}'.")
        escolhido = candidatos[0]
        print(f"[HISTÓRICO] Pasta informada; usando o CSV mais recente: {escolhido.name}")
        return escolhido
    if not caminho.exists():
        from historico_csv import resolver_csv_historico
        import configuracao as _cfg
        achado = Path(resolver_csv_historico(str(caminho), _cfg.TIMEFRAME_MINUTOS))
        if achado.exists():
            print(f"[HISTÓRICO] '{caminho.name}' não existe; usando '{achado.name}'.")
            return achado
        raise SystemExit(f"Caminho não encontrado: '{caminho}'.")
    return caminho


def _data(informado: str | None) -> date | None:
    if not informado:
        return None
    return datetime.strptime(informado, "%Y-%m-%d").date()


def _gerar_extrato(caminho_csv: Path, inicio: date | None, fim: date | None) -> dict:
    candles_avaliacao = cl.carregar_csv(caminho_csv)
    todos_dias = sorted({c.horario.date() for c in candles_avaliacao})
    candles, _ = cl.preparar_aquecimento(candles_avaliacao)

    dias_avaliacao = {
        d for d in todos_dias
        if (inicio is None or d >= inicio) and (fim is None or d <= fim)
    }
    if not dias_avaliacao:
        raise SystemExit("Nenhum pregão no histórico cai dentro do período informado.")

    entradas, _ = cl.descobrir_entradas()
    saidas, _ = cl.descobrir_saidas()
    entrada_titular = next((e for e in entradas if e.titular), None)
    saida_titular = next((s for s in saidas if s.titular), None)
    if entrada_titular is None:
        raise SystemExit("Nenhuma entrada titular encontrada em estrategia/entrada/titular/.")
    if saida_titular is None:
        raise SystemExit("Nenhuma saída titular encontrada em estrategia/saida/titular/.")

    print(f"Entrada titular: {entrada_titular.nome}.py")
    print(f"Saída titular  : {saida_titular.nome}.py")
    print(f"Período do relatório: {min(dias_avaliacao)} a {max(dias_avaliacao)} "
          f"({len(dias_avaliacao)} pregões)")

    rows = cl.preparar_rows(candles)
    trades = cl.executar_jogo(
        candles, rows, entrada_titular, dias_avaliacao,
        avaliar_saida=saida_titular.avaliar_saida,
    )
    trades = sorted(trades, key=lambda t: t["horario_execucao"])

    return {
        "entrada_titular": entrada_titular.nome,
        "saida_titular": saida_titular.nome,
        "periodo_inicio": min(dias_avaliacao),
        "periodo_fim": max(dias_avaliacao),
        "historico_inicio": candles_avaliacao[0].horario,
        "historico_fim": candles_avaliacao[-1].horario,
        "n_candles_historico": len(candles_avaliacao),
        "trades": trades,
    }


def _autofit(ws, larguras: dict) -> None:
    for indice, largura in larguras.items():
        ws.column_dimensions[get_column_letter(indice)].width = largura


def _planilha_operacoes(wb, resultado: dict) -> None:
    ws = wb.active
    ws.title = "Operações"
    trades = resultado["trades"]
    resultado_liquido = sum(t["resultado_reais"] for t in trades)

    ws.cell(row=2, column=2,
            value=f"Operações dos titulares — {resultado['periodo_inicio']:%d/%m/%Y} "
                  f"a {resultado['periodo_fim']:%d/%m/%Y}").font = TITULO_FONTE

    ws.cell(row=5, column=2, value="Período").font = ROTULO_FONTE
    ws.cell(row=5, column=3, value="Operações").font = ROTULO_FONTE
    ws.cell(row=5, column=5, value="Resultado líquido").font = ROTULO_FONTE
    ws.cell(row=5, column=6, value="Entrada").font = ROTULO_FONTE
    ws.cell(row=5, column=7, value="Saída").font = ROTULO_FONTE

    ws.cell(row=6, column=2,
            value=f"{resultado['periodo_inicio']:%d/%m} a {resultado['periodo_fim']:%d/%m/%Y}").font = FONTE_PADRAO
    ws.cell(row=6, column=3, value=len(trades)).font = FONTE_PADRAO
    cel_res = ws.cell(row=6, column=5, value=resultado_liquido)
    cel_res.font = FONTE_PADRAO
    cel_res.number_format = FORMATO_MOEDA
    ws.cell(row=6, column=6, value=resultado["entrada_titular"]).font = FONTE_PADRAO
    ws.cell(row=6, column=7, value=resultado["saida_titular"]).font = FONTE_PADRAO

    linha_cabecalho = 9
    colunas = [
        ("dia_semana", "Dia"),
        ("data", "Data"),
        ("hora_entrada", "Hora de entrada"),
        ("hora_saida", "Hora de saída"),
        ("tipo", "Tipo da operação"),
        ("resultado", "Resultado (R$)"),
        ("acumulado", "Total acumulado (R$)"),
        ("motivo", "Motivo"),
    ]
    for c, (_, rotulo) in enumerate(colunas, 1):
        cel = ws.cell(row=linha_cabecalho, column=c, value=rotulo)
        cel.font = CABECALHO_FONTE
        cel.fill = CABECALHO_FILL
        cel.alignment = Alignment(horizontal="center", vertical="center")
    ws.freeze_panes = f"A{linha_cabecalho + 1}"

    for i, trade in enumerate(trades):
        linha = linha_cabecalho + 1 + i
        data_entrada = trade["horario_rotulo"].date()
        hora_entrada = trade["horario_execucao"].strftime("%H:%M")
        saida_fim = trade["saida_dt"]
        saida_inicio = saida_fim - timedelta(minutes=cfg.TIMEFRAME_MINUTOS)
        hora_saida = f"{saida_inicio:%H:%M}-{saida_fim:%H:%M}"

        cel_data = ws.cell(row=linha, column=2, value=data_entrada)
        cel_data.number_format = FORMATO_DATA
        cel_data.font = FONTE_PADRAO
        ws.cell(row=linha, column=1,
                value=f'=TEXT(B{linha},"dddd")').font = FONTE_PADRAO
        ws.cell(row=linha, column=3, value=hora_entrada).font = FONTE_PADRAO
        ws.cell(row=linha, column=4, value=hora_saida).font = FONTE_PADRAO
        ws.cell(row=linha, column=5, value=trade["lado"]).font = FONTE_PADRAO
        cel_result = ws.cell(row=linha, column=6, value=round(trade["resultado_reais"], 2))
        cel_result.font = FONTE_PADRAO
        cel_result.number_format = FORMATO_MOEDA
        if i == 0:
            formula_acumulado = f"=F{linha}"
        else:
            formula_acumulado = f"=G{linha - 1}+F{linha}"
        cel_acum = ws.cell(row=linha, column=7, value=formula_acumulado)
        cel_acum.font = FONTE_PADRAO
        cel_acum.number_format = FORMATO_MOEDA
        motivo = trade["motivo"]
        if trade.get("intrabar_ambiguo"):
            motivo += " (ambíguo)"
        ws.cell(row=linha, column=8, value=motivo).font = FONTE_PADRAO

    _autofit(ws, {1: 12, 2: 12, 3: 14, 4: 15, 5: 16, 6: 16, 7: 18, 8: 22})


def _planilha_metodologia(wb, resultado: dict, caminho_csv: Path) -> None:
    ws = wb.create_sheet("Metodologia")
    ws.cell(row=1, column=1, value="Metodologia e critérios").font = TITULO_FONTE
    ws.cell(row=3, column=1, value="Item").font = CABECALHO_FONTE
    ws.cell(row=3, column=1).fill = CABECALHO_FILL
    ws.cell(row=3, column=2, value="Critério aplicado").font = CABECALHO_FONTE
    ws.cell(row=3, column=2).fill = CABECALHO_FILL

    janelas = " e ".join(f"{ini}–{fim}" for ini, fim in cfg.JANELAS_BLOQUEADAS)
    itens = [
        ("Estratégia de entrada",
         f"{resultado['entrada_titular']}.py (titular em estrategia/entrada/titular/ no "
         "momento da geração). Ver docstring do arquivo para a lógica de cada porta."),
        ("Estratégia de saída",
         f"{resultado['saida_titular']}.py (titular em estrategia/saida/titular/ no "
         "momento da geração). Ver docstring do arquivo para os critérios de antecipação."),
        ("Histórico utilizado",
         f"{caminho_csv.name}, de {resultado['historico_inicio']:%d/%m/%Y} a "
         f"{resultado['historico_fim']:%d/%m/%Y} ({resultado['n_candles_historico']} candles, "
         f"timeframe {cfg.TIMEFRAME_MINUTOS} min). Candles anteriores ao período do relatório "
         "são usados só para aquecer os indicadores, não aparecem na tabela."),
        ("Período do relatório",
         f"{resultado['periodo_inicio']:%d/%m/%Y} a {resultado['periodo_fim']:%d/%m/%Y}"),
        ("Motor",
         f"Motor oficial do laboratório: não calcula stop nem alvo (Regra 1, "
         f"compliance.md v8) — quem define os dois, desde a abertura da posição, é "
         f"{resultado['saida_titular']}.py; custo de R$ "
         f"{cfg.CUSTO_TOTAL_ESTIMADO_POR_OPERACAO_REAIS:.2f} por operação (R$ "
         f"{cfg.VALOR_PONTO_REAIS:.2f} por ponto de WIN)."),
        ("Limites",
         f"Máximo de {cfg.MAX_PERDAS_DIA} perdas por dia (sem teto de contagem "
         f"de operações desde a V459); janela(s) {janelas} bloqueada(s)."),
        ("Hora de entrada",
         "Momento executável: fechamento do candle de sinal, isto é, rótulo do candle "
         f"acrescido de {cfg.TIMEFRAME_MINUTOS} minutos."),
        ("Hora de saída",
         "Intervalo do candle em que stop, alvo, saída do cartucho ou encerramento ocorreu. "
         "O OHLC de 15 minutos não informa o segundo exato."),
        ("Resultado",
         f"Valor líquido para 1 contrato de WIN, a R$ {cfg.VALOR_PONTO_REAIS:.2f} por ponto, "
         f"já descontado o custo de R$ {cfg.CUSTO_TOTAL_ESTIMADO_POR_OPERACAO_REAIS:.2f}."),
        ("Total acumulado", "Fórmula que soma os resultados em ordem cronológica."),
        ("Paridade",
         "As operações vêm diretamente do registro interno do motor oficial "
         "(motor.operacoes_fechadas), o mesmo usado em produção e no laboratório — não há "
         "caminho de cálculo paralelo."),
        ("Limitação", "Backtest histórico não garante resultado futuro."),
    ]
    for i, (campo, valor) in enumerate(itens, start=4):
        ws.cell(row=i, column=1, value=campo).font = ROTULO_FONTE
        cel = ws.cell(row=i, column=2, value=valor)
        cel.font = FONTE_PADRAO
        cel.alignment = Alignment(wrap_text=True, vertical="top")
    _autofit(ws, {1: 24, 2: 100})


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Roda as estratégias TITULARES (entrada + saída) contra o histórico oficial "
            "e exporta o extrato de operações dia a dia em .xlsx."
        )
    )
    parser.add_argument(
        "caminho", nargs="?", default=None,
        help=(
            "CSV do histórico oficial, ou pasta que o contém. Se omitido, usa "
            "cfg.CAMINHO_HISTORICO_INICIAL (mesmo padrão do classificacao.py)."
        ),
    )
    parser.add_argument("--inicio", default=None, help="Primeiro dia (AAAA-MM-DD).")
    parser.add_argument("--fim", default=None, help="Último dia (AAAA-MM-DD).")
    parser.add_argument("--saida-dir", default=r"D:\DAYTRADE\ANALISES",
                         help=r"Pasta de saída (padrão: D:\DAYTRADE\ANALISES).")
    parser.add_argument("--nome", default=None, help="Nome base do arquivo, sem extensão.")
    args = parser.parse_args()

    caminho_informado = args.caminho or cfg.CAMINHO_HISTORICO_INICIAL
    caminho_csv = _resolver_caminho_historico(caminho_informado)
    inicio = _data(args.inicio)
    fim = _data(args.fim)

    resultado = _gerar_extrato(caminho_csv, inicio, fim)

    wb = Workbook()
    _planilha_operacoes(wb, resultado)
    _planilha_metodologia(wb, resultado, caminho_csv)

    pasta_saida = Path(args.saida_dir)
    pasta_saida.mkdir(parents=True, exist_ok=True)
    nome = args.nome or (
        f"extrato_titulares_{resultado['periodo_inicio']:%Y%m%d}_"
        f"{resultado['periodo_fim']:%Y%m%d}"
    )
    caminho_saida = pasta_saida / f"{nome}.xlsx"
    wb.save(caminho_saida)

    total = sum(t["resultado_reais"] for t in resultado["trades"])
    print(f"\n[OK] {len(resultado['trades'])} operações | resultado líquido: R$ {total:,.2f}")
    print(f"[OK] Planilha salva em: {caminho_saida.resolve()}")


if __name__ == "__main__":
    main()

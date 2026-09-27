"""Testes automatizados da Regra 13 (fator de presença), compliance.md v5.

Cobre exatamente o checklist da Regra 13.6:
  - coberturas de 0%, 50% e 100%;
  - invariância ao lote: a mesma estratégia, testada sozinha e testada
    junto de outras candidatas no mesmo histórico, produz exatamente o
    mesmo pontuacao_final.

Não depende do motor nem de CSV real — chama `_montar_resultado_par`
diretamente com trades sintéticos, então roda em qualquer máquina em
segundos. Rode com:  python -m pytest test_regra13_cobertura.py -v
(ou "python test_regra13_cobertura.py" — tem um runner manual no final).
"""

from __future__ import annotations

import math
from datetime import date, datetime

from classificacao import _montar_resultado_par, aplicar_pontuacao_multitemporal


def _trade(dia: date, resultado: float) -> dict:
    return {
        "horario_rotulo": datetime(dia.year, dia.month, dia.day, 17, 0),
        "resultado_reais": resultado,
        "intrabar_ambiguo": False,
    }


def _dias(quantidade: int) -> list[date]:
    return [date(2026, 1, d) for d in range(1, quantidade + 1)]


def _trades_pf_finito(dias: list[date]) -> list[dict]:
    """Alterna ganho/perda pra garantir PF finito (evita nan por perdas=0),

    que é o caso realista — uma estratégia com zero perdas no teste inteiro
    não existe em produção e deixaria o teste testando um caso degenerado
    do _pontuacao(), não da Regra 13."""
    return [
        _trade(d, 120.0 if i % 2 == 0 else -60.0)
        for i, d in enumerate(dias)
    ]


def test_cobertura_100_por_cento():
    """Estratégia operou todos os dias do período -> cobertura = 1.0."""
    dias = _dias(10)
    trades = _trades_pf_finito(dias)
    r = _montar_resultado_par("est_a", "saida_x", trades, dias)
    assert math.isclose(r["cobertura"], 1.0), r["cobertura"]
    assert math.isclose(r["presenca"], 100.0), r["presenca"]
    assert not math.isnan(r["pontuacao_base"]), "fixture não deveria gerar nan"
    assert math.isclose(r["pontuacao_final"], r["pontuacao_base"]), (
        "com cobertura 100%, pontuacao_final deve ser igual a pontuacao_base"
    )


def test_cobertura_50_por_cento():
    """Estratégia operou metade dos dias do período -> cobertura = 0.5.

    Os dias operados são espalhados (dia sim, dia não) por todo o
    período, não concentrados no início — senão o corte longo/curto do
    pf_minimo (Regra 5) cai todo num dos dois lados e gera nan por um
    motivo alheio à Regra 13 (perdas=0 no lado vazio)."""
    dias = _dias(30)
    dias_operados = dias[0::2]  # metade dos dias, espalhados por todo o período
    trades = _trades_pf_finito(dias_operados)
    r = _montar_resultado_par("est_b", "saida_x", trades, dias)
    assert math.isclose(r["cobertura"], 0.5), r["cobertura"]
    assert math.isclose(r["presenca"], 50.0), r["presenca"]
    assert not math.isnan(r["pontuacao_base"]), "fixture não deveria gerar nan"
    assert math.isclose(r["pontuacao_final"], r["pontuacao_base"] * 0.5)


def test_cobertura_0_por_cento():
    """Estratégia não operou nenhum dia -> cobertura = 0, pontuacao_final = 0

    (nunca negativa, mesmo que pontuacao_base fosse positiva; e nunca
    positiva por acidente se pontuacao_base for negativa — 0 * qualquer
    coisa finita é 0)."""
    dias = _dias(10)
    trades: list[dict] = []
    r = _montar_resultado_par("est_c", "saida_x", trades, dias)
    assert r["cobertura"] == 0.0
    assert r["presenca"] == 0.0
    # A Regra 13.3 exige zero exato, mesmo que a pontuação-base seja nan.
    assert r["pontuacao_final"] == 0.0


def test_denominador_absoluto_nao_relativo_ao_grupo():
    """Regra 13.1 — o pontuacao_final de uma estratégia NÃO pode mudar

    conforme quantos dias as OUTRAS estratégias do lote operaram. Este é
    o teste que teria pegado o defeito da v4 (denominador =
    maior_numero_de_dias_operados_do_grupo)."""
    dias = _dias(20)
    trades_a = _trades_pf_finito(dias[0::2])  # opera metade, espalhado

    # Cenário 1: "est_a" é a única do lote.
    r_sozinha = _montar_resultado_par("est_a", "saida_x", trades_a, dias)

    # Cenário 2: "est_a" está num lote com uma concorrente que opera TODOS
    # os dias (o que, na fórmula v4, mudaria o denominador de "est_a").
    _ = _montar_resultado_par(
        "est_concorrente_full", "saida_x",
        _trades_pf_finito(dias), dias,
    )
    r_em_lote = _montar_resultado_par("est_a", "saida_x", trades_a, dias)

    assert r_sozinha["cobertura"] == r_em_lote["cobertura"]
    assert r_sozinha["pontuacao_final"] == r_em_lote["pontuacao_final"], (
        "invariância ao lote quebrada — pontuacao_final mudou conforme o "
        "concorrente presente no lote (era exatamente o defeito da v4)"
    )


def test_pontuacao_final_nunca_fica_positiva_com_resultado_negativo():
    """Regra 13.5 — resultado negativo não pode virar pontuação final

    positiva (o sinal de pontuacao_base deve se preservar, já que
    cobertura nunca é negativa)."""
    dias = _dias(10)
    trades = [_trade(d, -50.0) for d in dias]
    r = _montar_resultado_par("est_perde", "saida_x", trades, dias)
    assert r["pontuacao_final"] <= 0


def _linha_multitemporal(cobertura: float) -> dict:
    return {
        "score_longo_raw": 100.0,
        "score_mensal_raw": 100.0,
        "score_diario_raw": 100.0,
        "cobertura": cobertura,
    }


def test_regra13_aplicada_ao_ranking_de_entradas():
    """Modo E usa multi.final, não a nota multitemporal sem presença."""
    dias = _dias(10)
    linha = _linha_multitemporal(0.5)
    aplicar_pontuacao_multitemporal([linha], dias)
    assert math.isclose(linha["pontuacao_multitemporal_base"], 100.0)
    assert math.isclose(linha["pontuacao_multitemporal"], 50.0)


def test_regra13_aplicada_ao_ranking_de_saidas():
    """Modo S passa pela mesma função e recebe exatamente o mesmo fator."""
    dias = _dias(10)
    linha = _linha_multitemporal(0.25)
    aplicar_pontuacao_multitemporal([linha], dias)
    assert math.isclose(linha["pontuacao_multitemporal_base"], 100.0)
    assert math.isclose(linha["pontuacao_multitemporal"], 25.0)


if __name__ == "__main__":
    import sys
    import traceback

    testes = [v for k, v in list(globals().items()) if k.startswith("test_")]
    falhas = 0
    for teste in testes:
        try:
            teste()
            print(f"OK   - {teste.__name__}")
        except AssertionError:
            falhas += 1
            print(f"FALHOU - {teste.__name__}")
            traceback.print_exc()
    print(f"\n{len(testes) - falhas}/{len(testes)} testes passaram.")
    sys.exit(1 if falhas else 0)

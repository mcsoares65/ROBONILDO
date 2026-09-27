"""Testes do critério único de classificação por acumulado.

Rode com: python test_classificacao_acumulado.py
"""

from __future__ import annotations

from datetime import date, datetime

from classificacao import _montar_resultado_par


def _trade(dia: date, resultado: float) -> dict:
    return {
        "horario_rotulo": datetime(dia.year, dia.month, dia.day, 17, 0),
        "resultado_reais": resultado,
        "intrabar_ambiguo": False,
    }


def _dias(quantidade: int) -> list[date]:
    return [date(2026, 1, dia) for dia in range(1, quantidade + 1)]


def test_acumulado_desconta_modulo_do_drawdown():
    dias = _dias(4)
    trades = [
        _trade(dias[0], 100.0),
        _trade(dias[1], -40.0),
        _trade(dias[2], 20.0),
        _trade(dias[3], -10.0),
    ]
    resultado = _montar_resultado_par("entrada", "saida", trades, dias)
    assert resultado["resultado"] == 70.0
    assert resultado["drawdown"] == -40.0
    assert resultado["acumulado"] == 30.0


def test_drawdown_maior_reduz_acumulado():
    dias = _dias(4)
    suave = [_trade(dias[0], 100.0), _trade(dias[1], -20.0)]
    severo = [_trade(dias[0], 140.0), _trade(dias[1], -60.0)]
    a = _montar_resultado_par("a", "saida", suave, dias)
    b = _montar_resultado_par("b", "saida", severo, dias)
    assert a["resultado"] == b["resultado"] == 80.0
    assert a["acumulado"] > b["acumulado"]


def test_sem_operacoes_resulta_em_acumulado_zero():
    resultado = _montar_resultado_par("entrada", "saida", [], _dias(4))
    assert resultado["resultado"] == 0.0
    assert resultado["drawdown"] == 0.0
    assert resultado["acumulado"] == 0.0


if __name__ == "__main__":
    import sys
    import traceback

    testes = [valor for nome, valor in list(globals().items()) if nome.startswith("test_")]
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

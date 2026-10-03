"""Diagnóstico de cenários: como cada entrada e cada saída se sai em cada cenário.

Só leitura: não altera motor, cartuchos nem ranking. Cada operação é marcada com
o cenário (cenario.py) do candle que gerou o sinal; depois agrega por
estratégia x cenário. Também mede o quanto o reconhecedor acerta contra o
gabarito de regimes do simulador (modo 'regimes').

Uso:
  python diagnostico_cenarios.py [csv] [--periodo ...] [--simular reamostragem|regimes ...]

As funções diagnosticar() e matriz_confusao() recebem candles/rows já prontos,
para reaproveitar caches em análises longas.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Optional

import cenario
import classificacao as cl
import configuracao as cfg

MIN_OPS_CONFIAVEL = 20     # abaixo disso a célula é só indício


def diagnosticar(candles, rows, dias, entradas, saidas, entrada_titular, saida_titular) -> list[dict]:
    """Linhas: tipo ('entrada'|'saida'), estrategia, cenario, ops, resultado, vitorias."""
    row_por_hora = {c.horario: r for c, r in zip(candles, rows)}
    saidas_ok = [s for s in saidas if cl.validar_contrato_saida(s, rows)[0]]
    pares = [("entrada", e.nome, e, saida_titular) for e in entradas]
    pares += [("saida", s.nome, entrada_titular, s) for s in saidas_ok]

    celulas = defaultdict(lambda: [0, 0.0, 0])
    for tipo, nome, ent, sai in pares:
        try:
            trades = cl.executar_jogo(candles, rows, ent, dias, avaliar_saida=sai.avaliar_saida)
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
        for t in trades:
            cen = cenario.classificar(row_por_hora.get(t["horario_rotulo"]))
            c = celulas[(tipo, nome, cen)]
            c[0] += 1
            c[1] += t["resultado_reais"]
            c[2] += 1 if t["resultado_reais"] > 0 else 0
    return [
        {"tipo": k[0], "estrategia": k[1], "cenario": k[2], "ops": v[0],
         "resultado": round(v[1], 2), "vitorias": v[2]}
        for k, v in sorted(celulas.items())
    ]


def distribuicao(rows) -> dict:
    cont = defaultdict(int)
    for r in rows:
        if r is not None:
            cont[cenario.classificar(r)] += 1
    return dict(cont)


# Regime verdadeiro do simulador -> cenários aceitos como acerto.
ACERTOS = {
    "tendencia_alta": {"tendencia", "esticado"},
    "tendencia_baixa": {"tendencia", "esticado"},
    "lateral": {"lateral"},
    "volatil": {"volatil", "esticado"},
}


def matriz_confusao(candles, rows, rotulos: dict) -> dict:
    """Gabarito (regime do simulador) x cenário reconhecido. Candles de abertura
    e fim de tarde são separados do resto, pois dependem do relógio, não do regime."""
    m = defaultdict(lambda: defaultdict(int))
    for c, r in zip(candles, rows):
        if r is None or c.horario not in rotulos:
            continue
        m[rotulos[c.horario]][cenario.classificar(r)] += 1
    return {k: dict(v) for k, v in m.items()}


def acerto_geral(matriz: dict) -> float:
    ok = tot = 0
    for regime, cols in matriz.items():
        for cen, n in cols.items():
            if cen in ("abertura", "fim_de_tarde", cenario.INDEFINIDO):
                continue
            tot += n
            if cen in ACERTOS.get(regime, set()):
                ok += n
    return ok / tot if tot else float("nan")


LARGURA_NOME = 36
LARGURA_CEL = 11           # 36 + 7*11 = 113 colunas: cabe no console do Windows (120)


def imprimir_distribuicao(dist: dict) -> None:
    total = sum(dist.values()) or 1
    print("\nCandles por cenario:")
    for nome in cenario.NOMES:
        n = dist.get(nome, 0)
        print(f"  {nome:14s}{n:>7d}  {100 * n / total:>4.0f}%")


def imprimir_confusao(matriz: dict) -> None:
    cols = list(cenario.NOMES)
    print("\nGabarito do simulador (linhas) x cenario reconhecido (colunas), % da linha:")
    print(f"  {'gabarito':17s}" + "".join(f"{c[:9]:>10s}" for c in cols))
    for regime, v in matriz.items():
        tot = sum(v.values()) or 1
        print(f"  {regime:17s}" + "".join(f"{100 * v.get(c, 0) / tot:>9.0f}%" for c in cols))


def imprimir(linhas: list[dict], titulo: str = "") -> None:
    if titulo:
        print(f"\n===== {titulo} =====")
    rotulos = {"abertura": "abertura", "fim_de_tarde": "fim_tarde", "volatil": "volatil",
               "esticado": "esticado", "tendencia": "tendencia", "lateral": "lateral",
               cenario.INDEFINIDO: "indefinido"}
    for tipo in ("entrada", "saida"):
        sub = [l for l in linhas if l["tipo"] == tipo]
        if not sub:
            continue
        nomes = sorted({l["estrategia"] for l in sub})
        cols = list(cenario.NOMES)
        print(f"\n-- {tipo.upper()}: R$ (ops) por cenario; * = menos de {MIN_OPS_CONFIAVEL} ops --")
        print(f"{'estrategia':{LARGURA_NOME}s}" + "".join(f"{rotulos[c]:>{LARGURA_CEL}s}" for c in cols))
        for n in nomes:
            partes = []
            for c in cols:
                cel = next((l for l in sub if l["estrategia"] == n and l["cenario"] == c), None)
                if cel is None:
                    partes.append(f"{'-':>{LARGURA_CEL}s}")
                else:
                    marca = "*" if cel["ops"] < MIN_OPS_CONFIAVEL else " "
                    partes.append(f"{cel['resultado']:>{LARGURA_CEL - 1}.0f}({cel['ops']})".rjust(LARGURA_CEL - 1) + marca)
            print(f"{n[:LARGURA_NOME]:{LARGURA_NOME}s}" + "".join(partes))


MIN_OPS_METADE = 10        # operações mínimas por metade para a célula contar


def consistencia(linhas_a: list[dict], linhas_b: list[dict], nome_titular_entrada: str,
                 nome_titular_saida: str) -> list[dict]:
    """Compara duas metades (do período que o usuário escolheu) e devolve as células
    em que a estratégia fica melhor (ou pior) que a titular NO MESMO SENTIDO nas
    duas metades. Só conta célula com >= MIN_OPS_METADE operações em ambas as
    metades, na estratégia e na titular. Ordena pelo menor efeito entre as metades.
    Não define período nenhum: as metades vêm dos dias que foram apurados."""
    def indexa(linhas):
        return {(l["tipo"], l["estrategia"], l["cenario"]): l for l in linhas}

    a, b = indexa(linhas_a), indexa(linhas_b)
    saida = []
    for (tipo, nome, cen), la in a.items():
        titular = nome_titular_entrada if tipo == "entrada" else nome_titular_saida
        if nome == titular or (tipo, nome, cen) not in b:
            continue
        ta, tb = a.get((tipo, titular, cen)), b.get((tipo, titular, cen))
        lb = b[(tipo, nome, cen)]
        if None in (ta, tb):
            continue
        if min(la["ops"], lb["ops"], ta["ops"], tb["ops"]) < MIN_OPS_METADE:
            continue
        da, db = la["resultado"] - ta["resultado"], lb["resultado"] - tb["resultado"]
        if da * db > 0:
            saida.append({"tipo": tipo, "estrategia": nome, "cenario": cen,
                          "delta_metade_1": round(da, 2), "delta_metade_2": round(db, 2),
                          "efeito_minimo": round(min(abs(da), abs(db)) * (1 if da > 0 else -1), 2)})
    return sorted(saida, key=lambda x: -abs(x["efeito_minimo"]))


def gravar_csv(linhas: list[dict], caminho: Path) -> Path:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["tipo", "estrategia", "cenario", "ops", "resultado", "vitorias"],
                           delimiter=";")
        w.writeheader()
        w.writerows(linhas)
    return caminho


def main(argv=None):
    ap = argparse.ArgumentParser(description="Diagnóstico estratégia x cenário (só leitura).")
    ap.add_argument("csv", nargs="?")
    ap.add_argument("--periodo")
    ap.add_argument("--simular", choices=["reamostragem", "regimes"])
    ap.add_argument("--dias-sim", type=int, default=120)
    ap.add_argument("--semente", type=int)
    ap.add_argument("--metades", action="store_true",
                    help="divide os dias apurados ao meio e mostra o que se repete nas duas metades")
    a = ap.parse_args(argv)

    caminho = Path(a.csv or cfg.CAMINHO_HISTORICO_INICIAL)
    if not caminho.exists():
        from historico_csv import resolver_csv_historico
        caminho = Path(resolver_csv_historico(str(caminho), cfg.TIMEFRAME_MINUTOS))
    reais = cl.carregar_csv(caminho)
    rotulos = None
    if a.simular:
        import simulador_mercado as sim
        candles, rotulos, semente = sim.gerar_candles(reais, a.dias_sim, a.semente, a.simular)
        dias = sorted({c.horario.date() for c in candles})
        titulo = f"SIMULADO {a.simular} semente {semente}"
    else:
        todos = sorted({c.horario.date() for c in reais})
        dias, rot = cl.interpretar_periodo(a.periodo, todos)
        candles, titulo = reais, f"periodo {rot}"
    dias_av = set(dias)
    rows = cl.preparar_rows(candles, dias_av)
    entradas, _ = cl.descobrir_entradas()
    saidas, _ = cl.descobrir_saidas()
    et = next(e for e in entradas if e.titular)
    st = next(s for s in saidas if s.titular)

    imprimir_distribuicao(distribuicao(rows))
    if rotulos:
        mc = matriz_confusao(candles, rows, rotulos)
        imprimir_confusao(mc)
        print(f"Acerto (fora abertura/fim de tarde): {acerto_geral(mc):.1%}")
    linhas = diagnosticar(candles, rows, dias_av, entradas, saidas, et, st)
    imprimir(linhas, titulo)
    if a.metades:
        meio = len(dias) // 2
        d1, d2 = set(dias[:meio]), set(dias[meio:])
        l1 = diagnosticar(candles, rows, d1, entradas, saidas, et, st)
        l2 = diagnosticar(candles, rows, d2, entradas, saidas, et, st)
        rep = consistencia(l1, l2, et.nome, st.nome)
        print(f"\n-- REPETE NAS DUAS METADES ({dias[0]}..{dias[meio-1]} | {dias[meio]}..{dias[-1]}) "
              f"vs titular; min {MIN_OPS_METADE} ops por metade --")
        for r in rep[:25]:
            print(f"{r['tipo']:8s}{r['estrategia'][:40]:42s}{r['cenario']:14s}"
                  f"{r['delta_metade_1']:>10.0f}{r['delta_metade_2']:>10.0f}")
        if not rep:
            print("nenhuma célula se repete nas duas metades")
        print("Muitas células são testadas: um padrão que repete ainda pode ser acaso; trate como hipótese.")
    saida_csv = gravar_csv(linhas, Path(cfg.PASTA_LOGS_AUDITORIA) / "diagnostico_cenarios.csv")
    print(f"\nRelatorio: {saida_csv.resolve()}")


if __name__ == "__main__":
    main()

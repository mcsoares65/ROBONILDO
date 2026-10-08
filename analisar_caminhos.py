"""V505 - le os arquivos de caminho_operacao.py e responde a pergunta do giveback.

Uso:  python analisar_caminhos.py [pasta_logs] [ativacao_reais]

1) Resumo: quantas operacoes chegaram a lucro, quanto devolveram, derrapagem na saida,
   buracos de leitura do DDE (maior_intervalo_s).
2) Simulacao "estopar quando o lucro cair X% do pico" sobre a TRILHA REAL de cada operacao
   (a regra so liga depois que o lucro bruto passa de `ativacao_reais`, padrao R$ 100).
   Compara o total real com o total que cada X teria dado. Com poucas operacoes e so um
   indicio; cada linha mostra quantas operacoes a regra chegou a acionar.
So le arquivos; nao altera nada.
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

CUSTO_REAIS = 0.50
VALOR_PONTO = 0.2


def _f(v):
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None


def carregar(pasta):
    pasta = Path(pasta)
    resumo = []
    arq = pasta / "caminho_operacoes.csv"
    if arq.exists():
        with open(arq, newline="", encoding="utf-8-sig") as f:
            resumo = list(csv.DictReader(f, delimiter=";"))
    trilhas = defaultdict(list)
    for arq in sorted(pasta.glob("caminho_pontos_*.csv")):
        with open(arq, newline="", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f, delimiter=";"):
                v = _f(r["resultado_reais"])
                if v is not None:
                    trilhas[r["id_operacao"]].append(v)
    return resumo, trilhas


def simular(trilha, pct, ativacao, resultado_real):
    """Retorna (resultado_liquido, acionou). Trilha em R$ brutos, em ordem."""
    pico = None
    for v in trilha:
        if pico is None or v > pico:
            pico = v
        if pico >= ativacao and v <= pico * (1 - pct):
            return v - CUSTO_REAIS, True
    return resultado_real, False


def main(pasta="logs", ativacao=100.0):
    resumo, trilhas = carregar(pasta)
    if not resumo:
        print(f"Nenhuma operacao em {Path(pasta) / 'caminho_operacoes.csv'} ainda.")
        return
    print(f"{len(resumo)} operacao(oes) com caminho gravado.\n")
    print(f"{'data':10} {'lado':6} {'motivo':22} {'res R$':>8} {'pico R$':>8} {'devolveu R$':>11} "
          f"{'deriv.pts':>9} {'gap max s':>9}")
    for r in resumo:
        dev = (_f(r["devolucao_pts"]) or 0) * VALOR_PONTO
        print(f"{r['data']:10} {r['lado']:6} {r['motivo'][:22]:22} {_f(r['resultado_reais']) or 0:8.2f} "
              f"{_f(r['pico_reais']) or 0:8.2f} {dev:11.2f} "
              f"{(_f(r['derrapagem_pts']) if _f(r['derrapagem_pts']) is not None else float('nan')):9.1f} "
              f"{_f(r['maior_intervalo_s']) or 0:9.1f}")
    picos = [_f(r["pico_reais"]) or 0 for r in resumo]
    ganhou_e_devolveu = [r for r in resumo if (_f(r["pico_reais"]) or 0) >= ativacao
                         and (_f(r["resultado_reais"]) or 0) < (_f(r["pico_reais"]) or 0) * 0.5]
    print(f"\nChegaram a +R$ {ativacao:.0f}: {sum(p >= ativacao for p in picos)} | "
          f"destas, terminaram abaixo de 50% do pico: {len(ganhou_e_devolveu)}")
    der = [x for x in (_f(r["derrapagem_pts"]) for r in resumo) if x is not None]
    if der:
        print(f"Derrapagem na saida (pts, + = pior): media {sum(der) / len(der):.1f} | max {max(der):.1f}")

    com_trilha = [r for r in resumo if trilhas.get(r["id_operacao"])]
    print(f"\nSimulacao 'estopar com X% de queda do pico' (liga acima de R$ {ativacao:.0f}) "
          f"em {len(com_trilha)} operacao(oes) com trilha:")
    real = sum(_f(r["resultado_reais"]) or 0 for r in com_trilha)
    print(f"  real (como o robo fez)      : R$ {real:9.2f}")
    for pct in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9):
        tot, acionou = 0.0, 0
        for r in com_trilha:
            res, ac = simular(trilhas[r["id_operacao"]], pct, ativacao, _f(r["resultado_reais"]) or 0)
            tot += res
            acionou += ac
        print(f"  queda de {int(pct * 100):2d}% do pico      : R$ {tot:9.2f}  "
              f"(acionou em {acionou}; {tot - real:+.2f} vs real)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "logs",
         float(sys.argv[2]) if len(sys.argv) > 2 else 100.0)

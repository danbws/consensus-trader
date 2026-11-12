r"""
Simulacao de aportes e juros compostos para a carteira de consenso (12/11/2026).

Pergunta: o que pesa mais no resultado, a regra ser um pouco melhor ou o quanto se aplica e por quanto tempo?
Premissas (tudo em dolar, convertido a um cambio fixo para ler em reais; o cambio de verdade varia):
  - comeca com o que existe hoje na carteira de papel (US$ 1.000);
  - retorno: 6%, 8% e 10% ao ano (a faixa da revisao de 11/11), mais o S&P de 2018-2026 (~13,8%) so como teto historico;
  - "vantagem da regra": o consenso rendeu de 0,4 a 1,5 ponto acima do indice; aqui, 1 ponto;
  - imposto: 15% sobre o ganho, cobrado so no fim (a regra troca pouco; o contador confirma como fica);
  - cenario ruim: queda de 30% no 2o ano, depois volta ao ritmo normal.
Nao e previsao nem recomendacao: e conta de juros compostos com as premissas acima.

Uso: .\.venv\Scripts\python.exe scripts\simula_aportes.py
"""
import json
from pathlib import Path

CAMBIO = 5.40          # R$ por US$, fixo so para leitura
INICIAL = 1000.0       # US$
IMPOSTO = 0.15
RAIZ = Path(__file__).resolve().parent.parent


def simular(anos: int, taxa: float, aporte_reais: float, queda_ano2: bool = False) -> tuple[float, float]:
    """Valor final (US$) e total aplicado (US$), aporte mensal em reais convertido no cambio fixo."""
    saldo, aplicado = INICIAL, INICIAL
    aporte = aporte_reais / CAMBIO
    mensal = (1 + taxa) ** (1 / 12) - 1
    for mes in range(anos * 12):
        r = mensal
        if queda_ano2 and 12 <= mes < 24:
            r = (1 - 0.30) ** (1 / 12) - 1
        saldo = saldo * (1 + r) + aporte
        aplicado += aporte
    return saldo, aplicado


def liquido(saldo, aplicado):
    return saldo - max(saldo - aplicado, 0) * IMPOSTO


def brl(us):
    s = f"{us * CAMBIO:,.0f}".replace(",", ".")
    return f"R$ {s}"


def main():
    aportes = (0, 500, 1000, 2000)
    prazos = (5, 10, 20)
    tabelas = {}
    for taxa in (0.06, 0.08, 0.10, 0.138):
        print(f"\nRetorno de {taxa * 100:.1f}% ao ano em dolar (valor no fim, ja com 15% de imposto sobre o ganho)")
        print(f"  {'aporte por mes':>16} | " + " | ".join(f"{p:>2} anos: final / aplicado".rjust(34) for p in prazos))
        for a in aportes:
            cel = []
            for p in prazos:
                s, ap = simular(p, taxa, a)
                cel.append(f"{brl(liquido(s, ap)):>14} / {brl(ap):>13}")
                tabelas[f"{taxa}|{a}|{p}"] = [round(liquido(s, ap) * CAMBIO), round(ap * CAMBIO)]
            print(f"  {('R$ ' + str(a)):>16} | " + " | ".join(c.rjust(34) for c in cel))

    print("\nO que vale mais: 1 ponto a mais de retorno (7% -> 8%) ou o aporte?  (10 anos, ja com imposto)")
    for a in aportes:
        s7, ap = simular(10, 0.07, a)
        s8, _ = simular(10, 0.08, a)
        print(f"  aporte R$ {a:>5}/mes: a 7% {brl(liquido(s7, ap)):>12} | a 8% {brl(liquido(s8, ap)):>12} | "
              f"o 1 ponto vale {brl(liquido(s8, ap) - liquido(s7, ap)):>11}")

    print("\nCenario ruim: queda de 30% no 2o ano, 8% ao ano no resto (10 anos, com imposto)")
    for a in aportes:
        s_ok, ap = simular(10, 0.08, a)
        s_ruim, _ = simular(10, 0.08, a, queda_ano2=True)
        print(f"  aporte R$ {a:>5}/mes: sem queda {brl(liquido(s_ok, ap)):>12} | com queda {brl(liquido(s_ruim, ap)):>12} "
              f"| aplicado {brl(ap):>12}")
    destino = RAIZ / "user_data" / "simula_aportes.json"
    destino.write_text(json.dumps({"cambio": CAMBIO, "tabelas": tabelas}, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()

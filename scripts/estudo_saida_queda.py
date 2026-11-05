r"""
Hipotese (05/11/2026): a carteira de consenso caiu 2,4% num dia (ganho de R$ 305 para R$ 169). Sair quando cai
e voltar depois teria rendido mais do que ficar parado?

Base: a carteira de consenso diaria do estudo (scripts/estudo_consenso_robustez.py, top 10, corte 3%,
2 gestores, custo 0,2%), de 16/02/2018 a 29/10/2026. Por cima dela, regras de "tirar e colocar":
  A) queda de um dia: se a carteira cai X% ou mais num dia, sai e so volta depois de K pregoes;
       X em (1,5; 2; 3) e K em (5, 10, 20)
  B) queda desde o topo: sai quando a carteira esta X% abaixo do maior valor ja visto, volta quando ela
       fecha acima da propria media de N dias; X em (5, 10, 15, 20) e N em (20, 50)
  C) media movel: so fica dentro com a carteira acima da propria media de N dias; N em (50, 100, 200)
  20 regras. Decisao no fechamento do dia, vale a partir do dia seguinte. Custo de 0,2% por saida ou volta.
  Fora do mercado o dinheiro rende como titulo curto (BIL, precos de user_data/estudo_cot).

Protocolo de sempre: escolher em 2018-2021, conferir em 2022-2026, vizinhos, sorteio do mesmo tempo fora.
Uso: .\.venv\Scripts\python.exe scripts\estudo_saida_queda.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estudo_consenso_robustez as rb  # noqa: E402  (ao importar, imprime a tabela de robustez)

RAIZ = Path(__file__).resolve().parent.parent
CUSTO = 0.002
P1 = ("2018-02-16", "2022-02-15")
P2 = ("2022-02-16", "2026-10-29")


def regras():
    for x in (1.5, 2.0, 3.0):
        for k in (5, 10, 20):
            yield f"A queda de 1 dia >= {x}%, volta em {k} pregoes", ("A", x, k)
    for x in (5, 10, 15, 20):
        for n in (20, 50):
            yield f"B {x}% abaixo do topo, volta acima da media {n}", ("B", x, n)
    for n in (50, 100, 200):
        yield f"C so acima da media de {n} dias", ("C", n, None)


def posicao(v: pd.Series, regra) -> pd.Series:
    """1 = na carteira, 0 = no caixa, decidido no fechamento do dia."""
    tipo, a, b = regra
    r = v.pct_change()
    if tipo == "C":
        return (v > v.rolling(a, min_periods=a).mean()).astype(float).where(lambda s: v.rolling(a).mean().notna(), 1.0)
    pos, estado, espera = [], 1.0, 0
    media = v.rolling(b, min_periods=1).mean() if tipo == "B" else None
    topo = v.cummax()
    for i in range(len(v)):
        if tipo == "A":
            if espera > 0:
                espera -= 1
                if espera == 0:
                    estado = 1.0
            elif r.iloc[i] <= -a / 100:
                estado, espera = 0.0, b
        else:
            if estado == 1.0 and v.iloc[i] <= topo.iloc[i] * (1 - a / 100):
                estado = 0.0
            elif estado == 0.0 and v.iloc[i] > media.iloc[i]:
                estado = 1.0
        pos.append(estado)
    return pd.Series(pos, index=v.index)


def rodar(v, caixa, pos, ini, fim):
    m = (v.index >= ini) & (v.index <= fim)
    rv, rc = v.pct_change()[m].fillna(0), caixa.pct_change()[m].fillna(0)
    p = pos.shift(1)[m].fillna(1.0)
    trocas = p.diff().abs().fillna(0)
    r = p * rv + (1 - p) * rc - trocas * CUSTO
    cur = (1 + r).cumprod()
    anos = (v.index[m][-1] - v.index[m][0]).days / 365.25
    return ((cur.iloc[-1] ** (1 / anos) - 1) * 100, ((cur / cur.cummax()).min() - 1) * 100,
            (1 - p.mean()) * 100, int(trocas.sum()))


def sorteio(v, caixa, pos, ini, fim, vezes=1000):
    m = (pos.index >= ini) & (pos.index <= fim)
    p = pos[m]
    blocos, atual, n = [], p.iloc[0], 0
    for x in p:
        if x == atual:
            n += 1
        else:
            blocos.append((atual, n))
            atual, n = x, 1
    blocos.append((atual, n))
    rng, res = np.random.default_rng(42), []
    for _ in range(vezes):
        ordem = rng.permutation(len(blocos))
        s = pd.Series(np.concatenate([[blocos[i][0]] * blocos[i][1] for i in ordem]), index=p.index)
        res.append(rodar(v, caixa, s.reindex(pos.index).fillna(1.0), ini, fim)[0])
    return np.array(res)


def main():
    v = rb.rodar(pd.Timestamp(P1[0]), pd.Timestamp(P2[1]))
    caixa = pd.read_parquet(RAIZ / "user_data" / "estudo_cot" / "precos.parquet")["BIL"].reindex(v.index).ffill()

    r = v.pct_change().dropna()
    print("\nO que vem depois de um dia de queda forte na carteira (2018-2026):")
    for x in (2.0, 3.0):
        dias = r[r <= -x / 100].index
        for k in (5, 20):
            depois = [v.iloc[v.index.get_loc(d) + k] / v.loc[d] - 1 for d in dias if v.index.get_loc(d) + k < len(v)]
            normal = (v.shift(-k) / v - 1).dropna()
            print(f"  queda >= {x}% num dia ({len(dias)} vezes): {k} pregoes depois, media {np.mean(depois) * 100:+5.2f}% "
                  f"(subiu em {np.mean(np.array(depois) > 0) * 100:3.0f}% das vezes); qualquer dia: {normal.mean() * 100:+5.2f}%")

    bh = [rodar(v, caixa, pd.Series(1.0, index=v.index), *p) for p in (P1, P2)]
    print(f"\nFicar parado (a regra de hoje): 2018-21 {bh[0][0]:5.1f}% ao ano, queda max {bh[0][1]:5.1f}% | "
          f"2022-26 {bh[1][0]:5.1f}%, queda max {bh[1][1]:5.1f}%\n")
    linhas = []
    for nome, regra in regras():
        pos = posicao(v, regra)
        a, b = rodar(v, caixa, pos, *P1), rodar(v, caixa, pos, *P2)
        linhas.append((nome, regra, a, b))
        marca = "GANHA NOS DOIS" if a[0] > bh[0][0] and b[0] > bh[1][0] else ""
        print(f"  {nome:46} 18-21 {a[0]:5.1f}% (queda {a[1]:5.1f}%, fora {a[2]:3.0f}%)  "
              f"22-26 {b[0]:5.1f}% (queda {b[1]:5.1f}%, fora {b[2]:3.0f}%, {b[3]:3d} trocas) {marca}")
    ganha = sum(1 for _, _, a, b in linhas if a[0] > bh[0][0] and b[0] > bh[1][0])
    print(f"\nRegras que ganham de ficar parado nos dois periodos: {ganha} de {len(linhas)}")
    nome, regra, a, b = max(linhas, key=lambda x: x[2][0])
    s = sorteio(v, caixa, posicao(v, regra), *P2)
    print(f"Melhor de 2018-21: {nome}: {a[0]:.1f}% -> 2022-26 {b[0]:.1f}% (parado {bh[1][0]:.1f}%); "
          f"ganha de {(s < b[0]).mean() * 100:.0f}% dos sorteios com o mesmo tempo fora")


if __name__ == "__main__":
    main()

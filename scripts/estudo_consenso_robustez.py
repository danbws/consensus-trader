r"""
Robustez do estudo de consenso (scripts/estudo_consenso.py): vizinhos dos parametros e checagem de
vies de sobrevivencia (acoes do consenso sem preco, que teriam ficado de fora sem querer).
Uso: .\.venv\Scripts\python.exe scripts\estudo_consenso_robustez.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estudo_consenso as ec  # noqa: E402

px = pd.read_parquet(ec.CACHE / "precos.parquet").sort_index()
rel = ec.carregar13f()
dias = px.index
datas = []
for ano in range(2017, 2027):
    for mes in (2, 5, 8, 11):
        prox = dias[dias >= pd.Timestamp(ano, mes, 16)]
        if len(prox) and prox[0] < dias[-1]:
            datas.append(prox[0])

sem_preco_total, com_preco_total = {}, 0


def carteira(dia, top, minimo, min_gestores, conta_faltas=False):
    global com_preco_total
    ultimos = {}
    for r in rel:
        if pd.Timestamp(r["entregue"]) <= dia and (r["cik"] not in ultimos or r["periodo"] > ultimos[r["cik"]]["periodo"]):
            ultimos[r["cik"]] = r
    cont, pesos = {}, {}
    for r in ultimos.values():
        for t, p in ec.apostas_por_empresa(r, minimo).items():
            cont[t] = cont.get(t, 0) + 1
            pesos.setdefault(t, []).append(p)
    todos = sorted([t for t, n in cont.items() if n >= min_gestores], key=lambda t: (-cont[t], -np.mean(pesos[t])))[:top]
    if conta_faltas:
        for t in todos:
            if t not in px.columns or pd.isna(px.at[dia, t]):
                sem_preco_total[t] = sem_preco_total.get(t, 0) + 1
            else:
                com_preco_total += 1
    validos = [t for t, n in cont.items() if n >= min_gestores and t in px.columns and pd.notna(px.at[dia, t])]
    validos.sort(key=lambda t: (-cont[t], -np.mean(pesos[t])))
    return validos[:top]


def rodar(ini, fim, top=10, minimo=3.0, min_gestores=2, atraso=0, conta_faltas=False):
    valor, atual, serie = 1.0, [], []
    rebal = [d for d in datas if ini <= d < fim]
    for i, d in enumerate(rebal):
        entra = dias[min(dias.get_loc(d) + atraso, len(dias) - 1)]
        ate = rebal[i + 1] if i + 1 < len(rebal) else min(fim, dias[-1])
        nova = carteira(d, top, minimo, min_gestores, conta_faltas)
        giro = len(set(nova) ^ set(atual)) / max(len(nova) + len(atual), 1)
        valor *= 1 - 0.002 * giro
        trecho = px.loc[entra:ate]
        ret = (trecho[nova].ffill() / trecho[nova].iloc[0]).mean(axis=1) if nova else pd.Series(1.0, index=trecho.index)
        serie.append(valor * ret)
        valor *= float(ret.iloc[-1])
        atual = nova
    s = pd.concat(serie)
    return s[~s.index.duplicated(keep="last")]


def ao_ano(s):
    anos = (s.index[-1] - s.index[0]).days / 365.25
    return ((s.iloc[-1] / s.iloc[0]) ** (1 / anos) - 1) * 100


P = {"2018-21": (pd.Timestamp("2018-02-16"), pd.Timestamp("2022-02-15")),
     "2022-26": (pd.Timestamp("2022-02-16"), pd.Timestamp("2026-10-29"))}
spy = {k: ao_ano(px.loc[a:b, "SPY"].dropna()) for k, (a, b) in P.items()}
print(f"{'variante':38} {'2018-21':>8} {'2022-26':>8}   (S&P 500: {spy['2018-21']:.1f}% e {spy['2022-26']:.1f}% ao ano)")
variantes = {"base: top10, corte 3%, 2 gestores": {}, "corte 2%": {"minimo": 2.0}, "corte 5%": {"minimo": 5.0},
             "3 gestores ou mais": {"min_gestores": 3}, "top 8": {"top": 8}, "top 12": {"top": 12}, "top 15": {"top": 15},
             "entra 5 dias depois": {"atraso": 5}, "entra 20 dias depois": {"atraso": 20}}
for nome, p in variantes.items():
    r = [ao_ano(rodar(*P[k], **p)) for k in P]
    marca = "  vence nos 2" if r[0] > spy["2018-21"] and r[1] > spy["2022-26"] else ""
    print(f"{nome:38} {r[0]:7.1f}% {r[1]:7.1f}%{marca}")

rodar(P["2018-21"][0], P["2022-26"][1], conta_faltas=True)
print(f"\nSobrevivencia: {sum(sem_preco_total.values())} escolhas sem preco contra {com_preco_total} com preco")
print("Sem preco:", sorted(sem_preco_total.items(), key=lambda x: -x[1])[:15])

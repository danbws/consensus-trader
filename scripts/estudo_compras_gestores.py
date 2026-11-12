r"""
Hipotese (12/11/2026): em vez de seguir o que os gestores JA TEM (a carteira de consenso), seguir o que eles
ACABARAM DE COMPRAR ou aumentar no trimestre rende mais?

Base: os mesmos 16 gestores e 596 relatorios 13F do estudo de consenso (scripts/estudo_consenso.py), precos da Alpaca.
O 13F guardado traz o peso de cada acao na carteira do gestor, nao a quantidade; "comprou" e medido pelo peso:
  - posicao NOVA: a empresa nao estava no relatorio anterior do gestor e entrou com peso >= X%;
  - AUMENTO: o peso subiu Y pontos ou mais de um relatorio para o outro (inclui as novas).
  (o peso tambem muda quando o preco muda; por isso os cortes sao altos, e a versao "so novas" nao tem esse problema)
Regras testadas, sempre 10 acoes em partes iguais, troca no dia 16 de fev/mai/ago/nov (depois do prazo do 13F), custo 0,2%:
  1) so novas: empresas que mais gestores abriram no ultimo relatorio (desempate: maior peso de entrada)
  2) aumentos: empresas que mais gestores aumentaram (desempate: maior aumento)
  3) consenso + compra: a carteira de consenso, mas ordenada primeiro pelas que algum gestor aumentou
Protocolo de sempre: escolher em 2018-2021, conferir em 2022-2026, vizinhos, comparar com o consenso e com o S&P.

Uso: .\.venv\Scripts\python.exe scripts\estudo_compras_gestores.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estudo_consenso as ec  # noqa: E402

px = pd.read_parquet(ec.CACHE / "precos.parquet").sort_index()
dias = px.index
P = {"2018-21": (pd.Timestamp("2018-02-16"), pd.Timestamp("2022-02-15")),
     "2022-26": (pd.Timestamp("2022-02-16"), pd.Timestamp("2026-10-29"))}

# relatorios por gestor, em ordem, com o peso por empresa e o anterior ao lado
por_gestor = {}
for r in ec.carregar13f():
    por_gestor.setdefault(r["cik"], []).append(r)
pares = []  # (entregue, cik, pesos_agora, pesos_antes)
for cik, lista in por_gestor.items():
    lista.sort(key=lambda r: r["periodo"])
    for antes, agora in zip(lista, lista[1:]):
        pares.append((pd.Timestamp(agora["entregue"]), cik, ec.apostas_por_empresa(agora, 0.0),
                      ec.apostas_por_empresa(antes, 0.0)))

datas = []
for ano in range(2017, 2027):
    for mes in (2, 5, 8, 11):
        prox = dias[dias >= pd.Timestamp(ano, mes, 16)]
        if len(prox) and prox[0] < dias[-1]:
            datas.append(prox[0])


def ultimos_pares(dia):
    u = {}
    for p in pares:
        if p[0] <= dia and (p[1] not in u or p[0] > u[p[1]][0]):
            u[p[1]] = p
    return u.values()


def tem_preco(t, dia):
    return t in px.columns and pd.notna(px.at[dia, t])


def escolher(dia, regra, top=10, novo=3.0, aumento=2.0, corte=3.0, min_gestores=1):
    cont, forca = {}, {}
    if regra in ("novas", "aumentos"):
        for _, _, agora, antes in ultimos_pares(dia):
            for t, p in agora.items():
                if regra == "novas":
                    ok, f = (t not in antes and p >= novo), p
                else:
                    ok, f = (p - antes.get(t, 0.0) >= aumento), p - antes.get(t, 0.0)
                if ok:
                    cont[t] = cont.get(t, 0) + 1
                    forca[t] = forca.get(t, 0) + f
        lista = [t for t in cont if cont[t] >= min_gestores and tem_preco(t, dia)]
        lista.sort(key=lambda t: (-cont[t], -forca[t]))
        return lista[:top]
    # consenso + compra
    comprou = {}
    for _, _, agora, antes in ultimos_pares(dia):
        for t, p in agora.items():
            if p >= corte and p - antes.get(t, 0.0) >= aumento:
                comprou[t] = comprou.get(t, 0) + 1
            if p >= corte:
                cont[t] = cont.get(t, 0) + 1
                forca.setdefault(t, []).append(p)
    lista = [t for t in cont if cont[t] >= 2 and tem_preco(t, dia)]
    if regra == "consenso":
        lista.sort(key=lambda t: (-cont[t], -np.mean(forca[t])))
    else:
        lista.sort(key=lambda t: (-min(comprou.get(t, 0), 1), -cont[t], -np.mean(forca[t])))
    return lista[:top]


def rodar(ini, fim, regra, **kw):
    valor, atual, serie = 1.0, [], []
    rebal = [d for d in datas if ini <= d < fim]
    for i, d in enumerate(rebal):
        ate = rebal[i + 1] if i + 1 < len(rebal) else min(fim, dias[-1])
        nova = escolher(d, regra, **kw)
        giro = len(set(nova) ^ set(atual)) / max(len(nova) + len(atual), 1)
        valor *= 1 - 0.002 * giro
        trecho = px.loc[d:ate]
        ret = (trecho[nova].ffill() / trecho[nova].iloc[0]).mean(axis=1) if nova else pd.Series(1.0, index=trecho.index)
        serie.append(valor * ret)
        valor *= float(ret.iloc[-1])
        atual = nova
    s = pd.concat(serie)
    return s[~s.index.duplicated(keep="last")]


def medir(s):
    anos = (s.index[-1] - s.index[0]).days / 365.25
    return ((s.iloc[-1] / s.iloc[0]) ** (1 / anos) - 1) * 100, ((s / s.cummax()).min() - 1) * 100


def main():
    spy = {k: medir(px.loc[a:b, "SPY"].dropna()) for k, (a, b) in P.items()}
    base = {k: medir(rodar(*P[k], "consenso")) for k in P}
    print(f"S&P 500:            2018-21 {spy['2018-21'][0]:5.1f}% (queda {spy['2018-21'][1]:5.1f}%) | "
          f"2022-26 {spy['2022-26'][0]:5.1f}% (queda {spy['2022-26'][1]:5.1f}%)")
    print(f"Consenso (hoje):    2018-21 {base['2018-21'][0]:5.1f}% (queda {base['2018-21'][1]:5.1f}%) | "
          f"2022-26 {base['2022-26'][0]:5.1f}% (queda {base['2022-26'][1]:5.1f}%)\n")
    variantes = {}
    for novo in (2.0, 3.0, 5.0):
        for mg in (1, 2):
            variantes[f"so novas, peso >= {novo:.0f}%, {mg}+ gestor(es)"] = ("novas", {"novo": novo, "min_gestores": mg})
    for aum in (1.0, 2.0, 3.0):
        for mg in (1, 2):
            variantes[f"aumentos >= {aum:.0f} ponto(s), {mg}+ gestor(es)"] = ("aumentos", {"aumento": aum, "min_gestores": mg})
    for aum in (1.0, 2.0):
        variantes[f"consenso, primeiro as aumentadas >= {aum:.0f} pt"] = ("consenso_compra", {"aumento": aum})
    linhas = []
    for nome, (regra, kw) in variantes.items():
        a, b = medir(rodar(*P["2018-21"], regra, **kw)), medir(rodar(*P["2022-26"], regra, **kw))
        vs_spy = a[0] > spy["2018-21"][0] and b[0] > spy["2022-26"][0]
        vs_cons = a[0] > base["2018-21"][0] and b[0] > base["2022-26"][0]
        linhas.append((nome, a, b, vs_spy, vs_cons))
        print(f"  {nome:44} 2018-21 {a[0]:5.1f}% (queda {a[1]:5.1f}%) | 2022-26 {b[0]:5.1f}% (queda {b[1]:5.1f}%)"
              f"{'  > S&P nos 2' if vs_spy else ''}{'  > CONSENSO nos 2' if vs_cons else ''}")
    print(f"\nGanham do S&P nos dois periodos: {sum(x[3] for x in linhas)} de {len(linhas)}; "
          f"ganham do consenso nos dois: {sum(x[4] for x in linhas)} de {len(linhas)}")
    m = max(linhas, key=lambda x: x[1][0])
    print(f"Melhor de 2018-21: {m[0]}: {m[1][0]:.1f}% -> 2022-26 {m[2][0]:.1f}% "
          f"(consenso {base['2022-26'][0]:.1f}%, S&P {spy['2022-26'][0]:.1f}%)")
    d = datas[-1]
    print(f"\nLista da ultima troca do estudo ({d.date()}) na melhor de 2018-21:", escolher(d, *variantes[m[0]][:1], **variantes[m[0]][1]))


if __name__ == "__main__":
    main()

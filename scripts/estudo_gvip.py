r"""
Comparacao (13/11/2026): o nosso consenso contra o GVIP, o fundo do Goldman Sachs que segue a lista "VIP dos hedge
funds" (as acoes que mais aparecem entre as maiores apostas dos 13F dos fundos). E a versao profissional da mesma
ideia; se o nosso consenso nao ganhar dele, a versao pronta existe e da menos trabalho.

Base: as carteiras do estudo com a leitura corrigida dos 13F (scripts/estudo_mais_gestores.py): 16 gestores, 2+
(a regra de hoje) e 37 gestores, 3+ (a candidata). GVIP e SPY: preco diario da Alpaca ajustado por dividendos.
O GVIP ja desconta a taxa do fundo (0,45% ao ano); o consenso desconta 0,2% por troca e nao tem taxa.

Uso: .\.venv\Scripts\python.exe scripts\estudo_gvip.py
"""
import json
import sys
from pathlib import Path

import httpx
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import estudo_consenso as ec  # noqa: E402
import estudo_mais_gestores as mg  # noqa: E402
import estudo_sobrevivencia as es  # noqa: E402


def gvip(fim: str) -> pd.Series:
    chaves = json.loads((ec.RAIZ / "user_data" / "alpaca.json").read_text(encoding="utf-8"))
    cab = {"APCA-API-KEY-ID": chaves["key"], "APCA-API-SECRET-KEY": chaves["secret"]}
    d = httpx.get("https://data.alpaca.markets/v2/stocks/GVIP/bars", headers=cab, timeout=60,
                  params={"timeframe": "1Day", "start": "2016-06-01", "end": fim, "adjustment": "all",
                          "feed": "sip", "limit": 10000}).json()
    return pd.Series({pd.Timestamp(b["t"][:10]): b["c"] for b in d["bars"]})


def main():
    originais, novos = ec.carregar13f(), mg.carregar_novos()
    px = pd.read_parquet(ec.CACHE / "precos.parquet").sort_index()
    extra = es.baixar_precos(originais + novos, px)
    extra = pd.DataFrame({t: es.cortar(extra[t]) for t in extra.columns})
    px = pd.concat([px, extra.reindex(px.index)], axis=1)
    px["GVIP"] = gvip(str(px.index.max().date())).reindex(px.index).ffill()
    dias = px.index
    datas = []
    for ano in range(2017, 2027):
        for mes in (2, 5, 8, 11):
            prox = dias[dias >= pd.Timestamp(ano, mes, 16)]
            if len(prox) and prox[0] < dias[-1]:
                datas.append(prox[0])

    series = {}
    for nome, rel, kw in (("16 gestores, 2+ (regra de hoje)", originais, {}),
                          ("37 gestores, 3+ (candidata)", originais + novos, {"min_gestores": 3})):
        partes = [mg.rodar(px, rel, datas, a, b, **kw)[0] for a, b in mg.P.values()]
        s = partes[0]
        s2 = partes[1] * s.iloc[-1] / partes[1].iloc[0]
        series[nome] = pd.concat([s, s2[s2.index > s.index[-1]]])
    for t in ("GVIP", "SPY"):
        series[t] = px[t].loc[mg.P["2018-21"][0]:mg.P["2022-26"][1]].dropna()

    print(f"  {'':34} {'2018-2021':>22} {'2022-2026':>22}")
    for nome, s in series.items():
        a = mg.medir(s.loc[slice(*mg.P["2018-21"])])
        b = mg.medir(s.loc[slice(*mg.P["2022-26"])])
        print(f"  {nome:34} {a[0]:6.1f}% (queda {a[1]:6.1f}%) {b[0]:6.1f}% (queda {b[1]:6.1f}%)")

    print("\nAno a ano:")
    print("  ano " + "".join(f"{n.split(' (')[0]:>18}" for n in series))
    for ano in range(2018, 2027):
        linha = f"  {ano}"
        for s in series.values():
            x = s[s.index.year == ano]
            linha += f"{(x.iloc[-1] / x.iloc[0] - 1) * 100:17.1f}%"
        print(linha)

    r = pd.DataFrame({n: s.pct_change() for n, s in series.items()}).dropna()
    print("\nCorrelacao dos retornos diarios com o GVIP:",
          ", ".join(f"{n.split(' (')[0]} {r[n].corr(r['GVIP']):.2f}" for n in r.columns if n != "GVIP"))
    gv = series["GVIP"]
    for nome in list(series)[:2]:
        s = series[nome].reindex(gv.index).ffill()
        ganhou = [s.iloc[i + 252] / s.iloc[i] > gv.iloc[i + 252] / gv.iloc[i] for i in range(0, len(gv) - 252, 5)]
        print(f"Janelas de 1 ano em que {nome.split(' (')[0]} rendeu mais que o GVIP: {np.mean(ganhou) * 100:.0f}%")


if __name__ == "__main__":
    main()

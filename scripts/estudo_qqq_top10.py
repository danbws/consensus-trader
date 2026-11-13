r"""
Comparacao (13/11/2026): o consenso e so "big tech com outro nome"? As listas do consenso quase sempre tem GOOGL,
AMZN, META, MSFT, TSM e V. Se as 10 maiores do S&P em partes iguais, ou o Nasdaq 100 (QQQ), renderem o mesmo, existe
uma regra bem mais simples, sem 13F nenhum.

Top 10: as 10 maiores empresas do S&P 500 por valor de mercado no comeco de cada ano (lista fixa por ano, montada com
o ranking publicado na virada de cada ano; aproximada nas ultimas posicoes, onde a diferenca entre a 9a e a 12a e
pequena). Partes iguais, troca nas mesmas datas do consenso (dia 16 de fev/mai/ago/nov) usando a lista do ano, custo
0,2% sobre o que troca. QQQ e SPY: preco diario da Alpaca ajustado por dividendos.

Uso: .\.venv\Scripts\python.exe scripts\estudo_qqq_top10.py
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

TOP10 = {
    2017: ["AAPL", "GOOGL", "MSFT", "BRK.B", "XOM", "AMZN", "META", "JNJ", "JPM", "GE"],
    2018: ["AAPL", "GOOGL", "MSFT", "AMZN", "META", "BRK.B", "JNJ", "JPM", "XOM", "BAC"],
    2019: ["MSFT", "AAPL", "AMZN", "GOOGL", "BRK.B", "META", "JNJ", "JPM", "XOM", "V"],
    2020: ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "BRK.B", "JPM", "JNJ", "V", "WMT"],
    2021: ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "BRK.B", "JNJ", "JPM", "V"],
    2022: ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "BRK.B", "UNH", "JPM"],
    2023: ["AAPL", "MSFT", "GOOGL", "AMZN", "BRK.B", "UNH", "JNJ", "XOM", "V", "JPM"],
    2024: ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B", "LLY", "AVGO"],
    2025: ["AAPL", "NVDA", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "AVGO", "BRK.B", "JPM"],
    2026: ["NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "AVGO", "TSLA", "BRK.B", "JPM"],
}


def baixar(simbolos: list[str], fim: str) -> pd.DataFrame:
    chaves = json.loads((ec.RAIZ / "user_data" / "alpaca.json").read_text(encoding="utf-8"))
    cab = {"APCA-API-KEY-ID": chaves["key"], "APCA-API-SECRET-KEY": chaves["secret"]}
    col = {}
    for t in simbolos:
        d = httpx.get(f"https://data.alpaca.markets/v2/stocks/{t}/bars", headers=cab, timeout=60,
                      params={"timeframe": "1Day", "start": "2016-06-01", "end": fim, "adjustment": "all",
                              "feed": "sip", "limit": 10000}).json()
        col[t] = pd.Series({pd.Timestamp(b["t"][:10]): b["c"] for b in d.get("bars") or []})
    return pd.DataFrame(col)


def carteira_igual(px: pd.DataFrame, datas: list, ini: str, fim: str, lista) -> pd.Series:
    """Partes iguais, troca nas datas, 0,2% sobre o que entra e sai."""
    datas = [d for d in datas if pd.Timestamp(ini) <= d <= pd.Timestamp(fim)]
    valor, partes, atual = 1.0, [], set()
    for i, d in enumerate(datas):
        ate = datas[i + 1] if i + 1 < len(datas) else pd.Timestamp(fim)
        nomes = [t for t in lista(d) if t in px.columns and not np.isnan(px.at[d, t])]
        troca = len(set(nomes) ^ atual) / max(len(nomes), 1) / 2
        valor *= 1 - 0.002 * 2 * troca
        atual = set(nomes)
        trecho = px.loc[d:ate, nomes].ffill()
        s = (trecho / trecho.iloc[0]).mean(axis=1) * valor
        partes.append(s if not partes else s.iloc[1:])
        valor = s.iloc[-1]
    return pd.concat(partes)


def main():
    originais, novos = ec.carregar13f(), mg.carregar_novos()
    px = pd.read_parquet(ec.CACHE / "precos.parquet").sort_index()
    extra = es.baixar_precos(originais + novos, px)
    extra = pd.DataFrame({t: es.cortar(extra[t]) for t in extra.columns})
    px = pd.concat([px, extra.reindex(px.index)], axis=1)
    fim = str(px.index.max().date())
    falta = sorted({t for l in TOP10.values() for t in l} - set(px.columns)) + ["QQQ"]
    novos_px = baixar([t for t in falta if t not in px.columns], fim)
    px = pd.concat([px, novos_px.reindex(px.index).ffill(limit=5)], axis=1)
    px = px.loc[:, ~px.columns.duplicated()]

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
    partes = [carteira_igual(px, datas, a, b, lambda d: TOP10[d.year]) for a, b in mg.P.values()]
    series["Top 10 S&P (partes iguais)"] = pd.concat([partes[0], (partes[1] * partes[0].iloc[-1] / partes[1].iloc[0])
                                                      .loc[lambda s: s.index > partes[0].index[-1]]])
    for t in ("QQQ", "SPY"):
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
    print("\nCorrelacao dos retornos diarios:")
    for n in list(series)[:2]:
        print(f"  {n.split(' (')[0]}: top 10 {r[n].corr(r['Top 10 S&P (partes iguais)']):.2f}, "
              f"QQQ {r[n].corr(r['QQQ']):.2f}, SPY {r[n].corr(r['SPY']):.2f}")
    for ref in ("Top 10 S&P (partes iguais)", "QQQ"):
        rf = series[ref]
        for nome in list(series)[:2]:
            s = series[nome].reindex(rf.index).ffill()
            ganhou = [s.iloc[i + 252] / s.iloc[i] > rf.iloc[i + 252] / rf.iloc[i] for i in range(0, len(rf) - 252, 5)]
            print(f"Janelas de 1 ano em que {nome.split(' (')[0]} rendeu mais que {ref.split(' (')[0]}: "
                  f"{np.mean(ganhou) * 100:.0f}%")


if __name__ == "__main__":
    main()

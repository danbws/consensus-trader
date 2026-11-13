r"""
Hipotese (12/11/2026): a carteira de consenso fica melhor com MAIS gestores na lista (16 -> 37)?
Com mais gente, a contagem "quantos gestores tem esta acao como maior aposta" depende menos de poucos nomes.

Base: os 16 gestores do estudo de consenso (scripts/estudo_consenso.py) + 21 gestores conhecidos por carteiras
concentradas e de longo prazo, 13F de 2016 a 2026 (guardados a parte, em user_data/estudo_mais_gestores/13f, para
nao mexer na lista que o robo usa). Mesma regra: top 10 empresas, corte 3%, troca no dia 16 depois do prazo do 13F,
custo 0,2%. Testa 2 e 3 gestores minimos (com mais gente, 2 pode ficar facil demais).
Vies conhecido: a lista foi escolhida hoje, entre gestores que ficaram famosos (o mesmo vale para os 16 originais).

Uso: .\.venv\Scripts\python.exe scripts\estudo_mais_gestores.py   (baixa o que faltar na 1a vez; demora)
"""
import json
import sys
import time
from pathlib import Path

import httpx
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estudo_consenso as ec  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / "user_data" / "estudo_mais_gestores"
PASTA_13F = PASTA / "13f"
NOVOS = {
    "1569205": "Terry Smith (Fundsmith)", "1536411": "Druckenmiller (Duquesne)", "1647251": "Chris Hohn (TCI)",
    "1553733": "Glenn Greenberg (Brave Warrior)", "1641864": "Rochon (Giverny)", "915191": "Prem Watsa (Fairfax)",
    "883965": "Wally Weitz", "1036325": "Chris Davis (Davis Advisers)", "1056831": "Berkowitz (Fairholme)",
    "807985": "Mason Hawkins (Southeastern)", "1697868": "Kantesaria (Valley Forge)", "1345471": "Nelson Peltz (Trian)",
    "1034524": "Polen Capital", "1671657": "Pat Dorsey (Dorsey AM)", "1631014": "Altarock Partners",
    "921669": "Carl Icahn", "728014": "Ruane Cunniff (Sequoia)", "905567": "Yacktman",
    "859804": "Wedgewood Partners", "1115373": "Semper Augustus", "1279936": "Cantillon",
}
P = {"2018-21": (pd.Timestamp("2018-02-16"), pd.Timestamp("2022-02-15")),
     "2022-26": (pd.Timestamp("2022-02-16"), pd.Timestamp("2026-10-29"))}


def baixar13f():
    PASTA_13F.mkdir(parents=True, exist_ok=True)
    for cik, nome in NOVOS.items():
        try:
            filings = ec.ferramenta("filings", cik, "--limit", "60")["filings"]
        except Exception as erro:
            print(f"{nome}: sem lista ({erro})", flush=True)
            continue
        por_periodo = {}
        for f in sorted(filings, key=lambda f: f["filed"]):
            if f["form"] == "13F-HR" and f["period"] >= ec.INICIO and f["period"] not in por_periodo:
                por_periodo[f["period"]] = f
        for periodo, f in sorted(por_periodo.items()):
            destino = PASTA_13F / f"{cik}_{periodo}.json"
            if destino.exists() and '"cusip"' in destino.read_text(encoding="utf-8"):
                continue  # relatorio guardado no formato antigo (sem CUSIP) e baixado de novo
            try:
                h = ec.ferramenta("holdings", cik, "--accession", f["accession"])
                posicoes = [{"ticker": p.get("ticker"), "pct": p.get("pct_of_13f"), "put_call": p.get("put_call"),
                             "cusip": p.get("cusip"), "nome": p.get("name") or p.get("issuer")}
                            for p in h.get("positions", [])]
                destino.write_text(json.dumps({"cik": cik, "periodo": periodo, "entregue": f["filed"],
                                               "posicoes": posicoes}), encoding="utf-8")
            except Exception as erro:
                print(f"{nome} {periodo}: erro ({erro})", flush=True)
            time.sleep(0.3)
        print(f"{nome}: {len(por_periodo)} relatorios", flush=True)
    ec.tk.mapear_cusips(carregar_novos())


def carregar_novos() -> list[dict]:
    return ec.tk.resolver([json.loads(a.read_text(encoding="utf-8")) for a in sorted(PASTA_13F.glob("*.json"))])


def baixar_precos(relatorios: list[dict]):
    """Precos das acoes que os novos gestores tem com peso >= 3% e que ainda nao estao no arquivo do consenso."""
    arq = ec.CACHE / "precos.parquet"
    px = pd.read_parquet(arq)
    precisa = set()
    for r in relatorios:
        precisa |= set(ec.apostas_por_empresa(r, 3.0))
    falta = sorted(t for t in precisa if t and t.replace(".", "").isalpha() and t not in px.columns)
    print(f"{len(falta)} acoes novas para baixar preco", flush=True)
    if not falta:
        return
    chaves = json.loads((RAIZ / "user_data" / "alpaca.json").read_text(encoding="utf-8"))
    cab = {"APCA-API-KEY-ID": chaves["key"], "APCA-API-SECRET-KEY": chaves["secret"]}
    colunas = {}
    for i in range(0, len(falta), 50):
        lote, token, linhas = falta[i:i + 50], None, []
        while True:
            params = {"symbols": ",".join(lote), "timeframe": "1Day", "start": "2016-06-01",
                      "end": str(px.index.max().date()), "adjustment": "all", "feed": "sip", "limit": 10000}
            if token:
                params["page_token"] = token
            r = httpx.get("https://data.alpaca.markets/v2/stocks/bars", params=params, headers=cab, timeout=90)
            r.raise_for_status()
            d = r.json()
            for sym, bs in (d.get("bars") or {}).items():
                linhas += [(sym, b["t"][:10], b["c"]) for b in bs]
            token = d.get("next_page_token")
            if not token:
                break
        x = pd.DataFrame(linhas, columns=["sym", "dia", "fecha"])
        colunas.update({s: g.set_index("dia")["fecha"] for s, g in x.groupby("sym")})
    novo = pd.DataFrame(colunas)
    novo.index = pd.to_datetime(novo.index)
    pd.concat([px, novo], axis=1).sort_index().to_parquet(arq)


def rodar(px, rel, datas, ini, fim, top=10, minimo=3.0, min_gestores=2):
    dias = px.index

    def carteira(dia):
        ultimos = {}
        for r in rel:
            if pd.Timestamp(r["entregue"]) <= dia and (r["cik"] not in ultimos or r["periodo"] > ultimos[r["cik"]]["periodo"]):
                ultimos[r["cik"]] = r
        cont, pesos = {}, {}
        for r in ultimos.values():
            for t, p in ec.apostas_por_empresa(r, minimo).items():
                cont[t] = cont.get(t, 0) + 1
                pesos.setdefault(t, []).append(p)
        validos = [t for t, n in cont.items() if n >= min_gestores and t in px.columns and pd.notna(px.at[dia, t])]
        validos.sort(key=lambda t: (-cont[t], -np.mean(pesos[t])))
        return validos[:top]

    valor, atual, serie = 1.0, [], []
    rebal = [d for d in datas if ini <= d < fim]
    for i, d in enumerate(rebal):
        ate = rebal[i + 1] if i + 1 < len(rebal) else min(fim, dias[-1])
        nova = carteira(d)
        giro = len(set(nova) ^ set(atual)) / max(len(nova) + len(atual), 1)
        valor *= 1 - 0.002 * giro
        trecho = px.loc[d:ate]
        ret = (trecho[nova].ffill() / trecho[nova].iloc[0]).mean(axis=1) if nova else pd.Series(1.0, index=trecho.index)
        serie.append(valor * ret)
        valor *= float(ret.iloc[-1])
        atual = nova
    s = pd.concat(serie)
    return s[~s.index.duplicated(keep="last")], carteira


def medir(s):
    anos = (s.index[-1] - s.index[0]).days / 365.25
    return ((s.iloc[-1] / s.iloc[0]) ** (1 / anos) - 1) * 100, ((s / s.cummax()).min() - 1) * 100


def main():
    if "--sem-baixar" not in sys.argv:
        baixar13f()
    originais, novos = ec.carregar13f(), carregar_novos()
    print(f"\n{len(originais)} relatorios dos 16 originais + {len(novos)} dos novos "
          f"({len({r['cik'] for r in novos})} gestores com dados)")
    px = pd.read_parquet(ec.CACHE / "precos.parquet").sort_index()
    # acoes que so aparecem com a leitura corrigida (13/11): preco a parte, cortado se o ticker foi reaproveitado
    import estudo_sobrevivencia as es
    extra = es.baixar_precos(originais + novos, px)
    extra = pd.DataFrame({t: es.cortar(extra[t]) for t in extra.columns})
    px = pd.concat([px, extra.reindex(px.index)], axis=1)
    dias = px.index
    datas = []
    for ano in range(2017, 2027):
        for mes in (2, 5, 8, 11):
            prox = dias[dias >= pd.Timestamp(ano, mes, 16)]
            if len(prox) and prox[0] < dias[-1]:
                datas.append(prox[0])
    spy = {k: medir(px.loc[a:b, "SPY"].dropna()) for k, (a, b) in P.items()}
    print(f"  {'S&P 500':46} 2018-21 {spy['2018-21'][0]:5.1f}% (queda {spy['2018-21'][1]:5.1f}%) | "
          f"2022-26 {spy['2022-26'][0]:5.1f}% (queda {spy['2022-26'][1]:5.1f}%)")
    versoes = {
        "16 gestores, 2+ (a regra de hoje)": (originais, {}),
        "16 gestores, 3+": (originais, {"min_gestores": 3}),
        "37 gestores, 2+": (originais + novos, {}),
        "37 gestores, 3+": (originais + novos, {"min_gestores": 3}),
        "37 gestores, 4+": (originais + novos, {"min_gestores": 4}),
        "37 gestores, 3+, top 8": (originais + novos, {"min_gestores": 3, "top": 8}),
        "37 gestores, 3+, top 12": (originais + novos, {"min_gestores": 3, "top": 12}),
        "37 gestores, 3+, corte 5%": (originais + novos, {"min_gestores": 3, "minimo": 5.0}),
        "so os 21 novos, 2+": (novos, {}),
    }
    res = {}
    for nome, (rel, kw) in versoes.items():
        a = medir(rodar(px, rel, datas, *P["2018-21"], **kw)[0])
        b = medir(rodar(px, rel, datas, *P["2022-26"], **kw)[0])
        res[nome] = (a, b)
        marca = "  > S&P nos 2" if a[0] > spy["2018-21"][0] and b[0] > spy["2022-26"][0] else ""
        print(f"  {nome:46} 2018-21 {a[0]:5.1f}% (queda {a[1]:5.1f}%) | 2022-26 {b[0]:5.1f}% (queda {b[1]:5.1f}%){marca}")
    base = res["16 gestores, 2+ (a regra de hoje)"]
    melhores = [n for n, (a, b) in res.items() if n.startswith("37") and a[0] > base[0][0] and b[0] > base[1][0]]
    print(f"\nVersoes com 37 gestores que ganham da regra de hoje nos dois periodos: {len(melhores)} de 6"
          + (f" ({', '.join(melhores)})" if melhores else ""))
    _, carteira = rodar(px, originais + novos, datas, *P["2022-26"], min_gestores=3)
    print(f"Lista da ultima troca do estudo ({datas[-1].date()}), 37 gestores 3+: {carteira(datas[-1])}")


if __name__ == "__main__":
    main()

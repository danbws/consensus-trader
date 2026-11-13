r"""
Hipotese (12/11/2026): o resultado do estudo de consenso (15,3% ao ano) esta inflado por vies de sobrevivencia?

O que se achou antes de rodar: nos 13F guardados, parte das posicoes vem SEM ticker (a ferramenta nao achou o
CUSIP na lista de hoje). Em 2017-18 isso era ~30% do peso das carteiras; em 2026, ~8%. As que somem sao de dois
tipos: empresas que deixaram a bolsa (Activision, Celgene, Twitter...) e empresas vivas que trocaram de nome ou
codigo (Facebook -> META). O estudo original simplesmente nao via essas posicoes.

Correcao: baixa de novo os mesmos 13F guardando CUSIP e nome, acha o ticker pelo CUSIP na OpenFIGI (publica, sem
chave), baixa o preco historico na Alpaca (ela guarda as que sairam da bolsa) e roda a MESMA regra (top 10, corte 3%,
2+ gestores, troca no dia 16 depois do prazo do 13F, custo 0,2%). Ticker reaproveitado por outra empresa: a serie e
cortada no primeiro buraco de 20 dias ou no primeiro trecho de 10 fechamentos iguais (acao parada depois de comprada).
Limite conhecido: empresa que quebrou fica com o ultimo preco negociado (a perda real foi maior).

Uso: .\.venv\Scripts\python.exe scripts\estudo_sobrevivencia.py   (1a vez baixa tudo; demora uns 20 min)
"""
import json
import sys
import time
from pathlib import Path

import httpx
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import estudo_consenso as ec  # noqa: E402
import estudo_mais_gestores as mg  # noqa: E402
import tickers_13f as tk  # noqa: E402

PASTA = ec.RAIZ / "user_data" / "estudo_sobrevivencia"
PASTA_13F = PASTA / "13f"
ANTIGO = PASTA / "13f_antigo"  # copia da leitura de antes da correcao (13/11/2026), para comparar
PRECOS = PASTA / "precos_extra.parquet"


def baixar13f():
    PASTA_13F.mkdir(parents=True, exist_ok=True)
    for cik, nome in ec.GESTORES.items():
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
            if destino.exists():
                continue
            try:
                h = ec.ferramenta("holdings", cik, "--accession", f["accession"])
                posicoes = [{"ticker": p.get("ticker"), "pct": p.get("pct_of_13f"), "put_call": p.get("put_call"),
                             "cusip": p.get("cusip"), "nome": p.get("name") or p.get("issuer")}
                            for p in h.get("positions", [])]
                destino.write_text(json.dumps({"cik": cik, "periodo": periodo, "entregue": f["filed"],
                                               "posicoes": posicoes}), encoding="utf-8")
            except Exception as erro:
                print(f"{nome} {periodo}: erro ({erro})", flush=True)
        print(f"{nome}: {len(por_periodo)} relatorios", flush=True)


def carregar() -> list[dict]:
    return [json.loads(a.read_text(encoding="utf-8")) for a in sorted(PASTA_13F.glob("*.json"))]


def aplicar_mapa(relatorios: list[dict], _mapa=None):
    tk.resolver(relatorios)


def cortar(s: pd.Series) -> pd.Series:
    """Fica so com o primeiro trecho continuo da serie (ticker reaproveitado ou acao parada vira outro trecho)."""
    s = s.dropna()
    if len(s) < 2:
        return s
    buraco = np.where(np.diff(s.index.values).astype("timedelta64[D]").astype(int) > 20)[0]
    fim = len(s) if not len(buraco) else buraco[0] + 1
    iguais = (s.diff() == 0).astype(int)
    corrida = iguais.groupby((iguais == 0).cumsum()).cumsum()
    parada = np.where(corrida.values >= 10)[0]
    if len(parada):
        fim = min(fim, parada[0] - 9)
    return s.iloc[:fim]


def baixar_precos(relatorios: list[dict], px: pd.DataFrame) -> pd.DataFrame:
    extra = pd.read_parquet(PRECOS) if PRECOS.exists() else pd.DataFrame()
    precisa = set()
    for r in relatorios:
        precisa |= set(ec.apostas_por_empresa(r, 3.0))
    falta = sorted(t for t in precisa if t and t.replace(".", "").isalpha()
                   and t not in px.columns and t not in extra.columns)
    print(f"{len(falta)} acoes novas para baixar preco", flush=True)
    chaves = json.loads((ec.RAIZ / "user_data" / "alpaca.json").read_text(encoding="utf-8"))
    cab = {"APCA-API-KEY-ID": chaves["key"], "APCA-API-SECRET-KEY": chaves["secret"]}
    colunas = {}
    for t in falta:
        linhas, token = [], None
        while True:
            params = {"timeframe": "1Day", "start": "2016-06-01", "end": str(px.index.max().date()),
                      "adjustment": "all", "feed": "sip", "limit": 10000}
            if token:
                params["page_token"] = token
            d = httpx.get(f"https://data.alpaca.markets/v2/stocks/{t}/bars", params=params, headers=cab,
                          timeout=90).json()
            linhas += [(b["t"][:10], b["c"]) for b in d.get("bars") or []]
            token = d.get("next_page_token")
            if not token:
                break
        if linhas:
            colunas[t] = pd.Series({pd.Timestamp(a): c for a, c in linhas})
        else:
            colunas[t] = pd.Series(dtype=float)
    if colunas:
        novo = pd.DataFrame(colunas)
        extra = pd.concat([extra, novo], axis=1)
        extra.to_parquet(PRECOS)
    return extra


def main():
    if "--sem-baixar" not in sys.argv:
        baixar13f()
    novos = carregar()
    originais = [json.loads(a.read_text(encoding="utf-8")) for a in sorted(ANTIGO.glob("*.json"))]
    peso_sem = lambda rs: np.mean([sum((p["pct"] or 0) for p in r["posicoes"] if not p["ticker"] and not p["put_call"])
                                   for r in rs])
    print(f"\n{len(novos)} relatorios (original: {len(originais)}). Peso medio sem ticker antes: {peso_sem(novos):.1f}%")
    tk.mapear_cusips(novos)
    aplicar_mapa(novos)
    print(f"Peso medio sem ticker depois da OpenFIGI: {peso_sem(novos):.1f}%")

    px = pd.read_parquet(ec.CACHE / "precos.parquet").sort_index()
    extra = baixar_precos(novos, px)
    extra = pd.DataFrame({t: cortar(extra[t]) for t in extra.columns})
    px2 = pd.concat([px, extra.reindex(px.index)], axis=1)

    dias = px.index
    datas = []
    for ano in range(2017, 2027):
        for mes in (2, 5, 8, 11):
            prox = dias[dias >= pd.Timestamp(ano, mes, 16)]
            if len(prox) and prox[0] < dias[-1]:
                datas.append(prox[0])

    spy = {k: mg.medir(px.loc[a:b, "SPY"].dropna()) for k, (a, b) in mg.P.items()}
    print(f"\n  {'S&P 500':40} 2018-21 {spy['2018-21'][0]:5.1f}% | 2022-26 {spy['2022-26'][0]:5.1f}%")
    resultado = {}
    for nome, rel, tabela in (("original (leitura antes de 13/11)", originais, px),
                              ("corrigido (com as que sumiram)", novos, px2)):
        linha = {}
        for k, (a, b) in mg.P.items():
            s, carteira = mg.rodar(tabela, rel, datas, a, b)
            linha[k] = mg.medir(s)
        resultado[nome] = linha
        print(f"  {nome:40} 2018-21 {linha['2018-21'][0]:5.1f}% (queda {linha['2018-21'][1]:5.1f}%) | "
              f"2022-26 {linha['2022-26'][0]:5.1f}% (queda {linha['2022-26'][1]:5.1f}%)")

    # quais acoes entraram na carteira corrigida e nao estavam na original, e quantas sairam da bolsa durante a posse
    _, cart_o = mg.rodar(px, originais, datas, *mg.P["2018-21"])
    _, cart_n = mg.rodar(px2, novos, datas, *mg.P["2018-21"])
    entraram, morreram = {}, set()
    for i, d in enumerate(datas):
        o, n = set(cart_o(d)), set(cart_n(d))
        for t in n - o:
            entraram[t] = entraram.get(t, 0) + 1
        ate = datas[i + 1] if i + 1 < len(datas) else dias[-1]
        for t in n:
            if t in px2.columns and px2[t].loc[d:ate].isna().any() and px2[t].loc[ate:].dropna().empty:
                morreram.add(t)
    print("\nAcoes que a correcao poe na carteira (trimestres):",
          ", ".join(f"{t} {q}" for t, q in sorted(entraram.items(), key=lambda x: -x[1])))
    print("Sairam da bolsa enquanto estavam na carteira corrigida:", ", ".join(sorted(morreram)) or "nenhuma")

    # efeito na lista de HOJE (a ultima troca)
    print(f"\nLista da ultima troca ({datas[-1].date()}): original {cart_o(datas[-1])}")
    print(f"                                  corrigida {cart_n(datas[-1])}")
    ultimos = {}
    for r in novos:
        if r["cik"] not in ultimos or r["periodo"] > ultimos[r["cik"]]["periodo"]:
            ultimos[r["cik"]] = r
    sem = [(ec.GESTORES[r["cik"]], p["nome"], p["pct"]) for r in ultimos.values() for p in r["posicoes"]
           if not p["ticker"] and not p["put_call"] and (p["pct"] or 0) >= 3]
    print("Posicoes >=3% ainda sem ticker no ultimo 13F de cada gestor:", sem or "nenhuma")
    (PASTA / "resultado.json").write_text(json.dumps(resultado, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()

r"""
Estudo: comprar o CONSENSO dos grandes investidores (13F) + tendencia da bolsa. (aula 12, 30/10/2026)

Regras definidas ANTES de olhar resultado:
  - Cada 13F so vale a partir da data em que foi ENTREGUE (nada de informacao do futuro).
  - Rebalanceio no 1o dia util apos 15/fev, 15/mai, 15/ago e 15/nov (prazo do 13F: 45 dias).
  - "Maior aposta" = acao (nao opcao) com 3% ou mais da carteira do gestor, no ultimo 13F entregue.
  - Consenso = maiores apostas de pelo menos 2 gestores. Ranking: n de gestores, depois peso medio.
  - Compra as TOP N em partes iguais e segura ate o proximo rebalanceio. Custo: 0,1% por operacao.
  Variantes: (A) consenso puro; (B) so acoes acima da media de 200 dias; (C) B + so investe com o
  S&P 500 (SPY) acima da media de 200 dias (senao fica em caixa); (D) A com 20 acoes.
  Comparacao: segurar SPY; copiar so o Buffett (top 10).
  Periodos: 2018-2021 (escolha) e 2022-2026 (fora da amostra).

Uso (na pasta do projeto):
  .\.venv\Scripts\python.exe scripts\estudo_consenso.py baixar13f   (SEC, demora; guarda em cache)
  .\.venv\Scripts\python.exe scripts\estudo_consenso.py precos      (Alpaca, conta de papel)
  .\.venv\Scripts\python.exe scripts\estudo_consenso.py simular
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CACHE = RAIZ / "user_data" / "estudo_consenso"
CACHE_13F = CACHE / "13f"
FERRAMENTA = Path(__file__).resolve().parent.parent / "third_party" / "edgar13f" / "edgar13f.py"
PASTA_ACOES = RAIZ / "acoes-eua"

GESTORES = {
    "1067983": "Buffett (Berkshire)", "1061768": "Klarman (Baupost)", "1709323": "Li Lu (Himalaya)",
    "1336528": "Ackman (Pershing)", "1649339": "Burry (Scion)", "1656456": "Tepper (Appaloosa)",
    "1040273": "Loeb (Third Point)", "1061165": "Lone Pine", "1112520": "Akre", "1549575": "Pabrai (Dalal Street)",
    "1167483": "Tiger Global", "949509": "Marks (Oaktree)", "1096343": "Gayner (Markel)",
    "1079114": "Einhorn (Greenlight)", "1103804": "Viking Global", "860643": "Gardner Russo",
}
INICIO = "2016-12-31"


def ferramenta(*args) -> dict:
    r = subprocess.run([sys.executable, str(FERRAMENTA), *args, "--json"], cwd=PASTA_ACOES,
                       capture_output=True, timeout=600, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout or "erro").strip().splitlines()[-1])
    return json.loads(r.stdout)


# ------------------------------------------------------------------ etapa 1: 13F
def baixar13f():
    CACHE_13F.mkdir(parents=True, exist_ok=True)
    for cik, nome in GESTORES.items():
        try:
            filings = ferramenta("filings", cik, "--limit", "60")["filings"]
        except Exception as erro:
            print(f"{nome}: sem lista ({erro})", flush=True)
            continue
        # um relatorio por trimestre: o primeiro 13F-HR entregue (emendas /A sao ignoradas)
        por_periodo = {}
        for f in sorted(filings, key=lambda f: f["filed"]):
            if f["form"] == "13F-HR" and f["period"] >= INICIO and f["period"] not in por_periodo:
                por_periodo[f["period"]] = f
        for periodo, f in sorted(por_periodo.items()):
            destino = CACHE_13F / f"{cik}_{periodo}.json"
            if destino.exists():
                continue
            try:
                h = ferramenta("holdings", cik, "--accession", f["accession"])
                posicoes = [{"ticker": p.get("ticker"), "pct": p.get("pct_of_13f"), "put_call": p.get("put_call")}
                            for p in h.get("positions", [])]
                destino.write_text(json.dumps({"cik": cik, "periodo": periodo, "entregue": f["filed"],
                                               "posicoes": posicoes}), encoding="utf-8")
                print(f"{nome} {periodo}: {len(posicoes)} posicoes", flush=True)
            except Exception as erro:
                print(f"{nome} {periodo}: erro ({erro})", flush=True)
            time.sleep(0.3)
    print("fim 13F", flush=True)


def carregar13f() -> list[dict]:
    return [json.loads(a.read_text(encoding="utf-8")) for a in sorted(CACHE_13F.glob("*.json"))]


def maiores_apostas(relatorio: dict, minimo: float = 3.0) -> dict:
    return {p["ticker"]: p["pct"] for p in relatorio["posicoes"]
            if p["ticker"] and not p["put_call"] and (p["pct"] or 0) >= minimo}


# classes da mesma empresa contam como uma so (a primeira e a que a carteira compra)
MESMA_EMPRESA = {"BRK.A": "BRK.B", "GOOG": "GOOGL", "LEN.B": "LEN", "FOX": "FOXA", "NWS": "NWSA",
                 "LBTYK": "LBTYA", "LBTYB": "LBTYA", "LLYVK": "LLYVA", "FWONK": "FWONA", "BATRK": "BATRA",
                 "UA": "UAA", "HEI.A": "HEI"}


def apostas_por_empresa(relatorio: dict, minimo: float = 3.0) -> dict:
    """Peso de cada EMPRESA na carteira do gestor (somando as classes de acao) e corte de minimo%."""
    soma = {}
    for p in relatorio["posicoes"]:
        if p["ticker"] and not p["put_call"]:
            t = MESMA_EMPRESA.get(p["ticker"], p["ticker"])
            soma[t] = soma.get(t, 0) + (p["pct"] or 0)
    return {t: v for t, v in soma.items() if v >= minimo}


# ------------------------------------------------------------------ etapa 2: precos
def precos():
    import httpx
    import pandas as pd

    chaves = json.loads((RAIZ / "user_data" / "alpaca.json").read_text(encoding="utf-8"))
    cab = {"APCA-API-KEY-ID": chaves["key"], "APCA-API-SECRET-KEY": chaves["secret"]}
    tickers = {"SPY"}
    for r in carregar13f():
        tickers |= set(maiores_apostas(r, 1.0))
    tickers = sorted(t for t in tickers if t and t.replace(".", "").isalpha())
    print(f"{len(tickers)} acoes", flush=True)
    destino = CACHE / "precos.parquet"
    feitos = pd.read_parquet(destino) if destino.exists() else pd.DataFrame()
    ja = set(feitos.columns) if len(feitos) else set()
    colunas = {}
    for i in range(0, len(tickers), 50):
        lote = [t for t in tickers[i:i + 50] if t not in ja]
        if not lote:
            continue
        token, linhas = None, []
        while True:
            params = {"symbols": ",".join(lote), "timeframe": "1Day", "start": "2016-06-01", "end": "2026-10-29",
                      "adjustment": "all", "feed": "sip", "limit": 10000}
            if token:
                params["page_token"] = token
            r = httpx.get("https://data.alpaca.markets/v2/stocks/bars", params=params, headers=cab, timeout=60)
            r.raise_for_status()
            d = r.json()
            for sym, barras in (d.get("bars") or {}).items():
                linhas += [(sym, b["t"][:10], b["c"]) for b in barras]
            token = d.get("next_page_token")
            if not token:
                break
        df = pd.DataFrame(linhas, columns=["sym", "dia", "fecha"])
        if len(df):
            colunas.update({s: g.set_index("dia")["fecha"] for s, g in df.groupby("sym")})
        print(f"lote {i // 50 + 1}: {len(lote)} acoes", flush=True)
    novo = pd.DataFrame(colunas)
    tudo = pd.concat([feitos, novo], axis=1) if len(feitos) else novo
    tudo.index = pd.to_datetime(tudo.index)
    tudo.sort_index().to_parquet(destino)
    print(f"fim precos: {tudo.shape}", flush=True)


# ------------------------------------------------------------------ etapa 3: simular
def simular():
    import numpy as np
    import pandas as pd

    px = pd.read_parquet(CACHE / "precos.parquet").sort_index()
    relatorios = carregar13f()
    ma200 = px.rolling(200, min_periods=150).mean()
    dias = px.index
    datas = []
    for ano in range(2017, 2027):
        for mes in (2, 5, 8, 11):
            d = pd.Timestamp(ano, mes, 16)
            prox = dias[dias >= d]
            if len(prox) and prox[0] < dias[-1]:
                datas.append(prox[0])

    def carteira_no_dia(dia, top, tendencia, so_buffett=False):
        ultimos = {}
        for r in relatorios:
            if pd.Timestamp(r["entregue"]) <= dia and (not so_buffett or r["cik"] == "1067983"):
                if r["cik"] not in ultimos or r["periodo"] > ultimos[r["cik"]]["periodo"]:
                    ultimos[r["cik"]] = r
        if so_buffett:
            r = ultimos.get("1067983")
            if not r:
                return []
            pos = sorted(maiores_apostas(r, 0.0).items(), key=lambda x: -x[1])
            return [t for t, _ in pos if t in px.columns and pd.notna(px.at[dia, t])][:top]
        contagem, pesos = {}, {}
        for r in ultimos.values():
            for t, pct in maiores_apostas(r).items():
                contagem[t] = contagem.get(t, 0) + 1
                pesos.setdefault(t, []).append(pct)
        cand = [t for t, n in contagem.items() if n >= 2 and t in px.columns and pd.notna(px.at[dia, t])]
        if tendencia:
            cand = [t for t in cand if pd.notna(ma200.at[dia, t]) and px.at[dia, t] > ma200.at[dia, t]]
        cand.sort(key=lambda t: (-contagem[t], -np.mean(pesos[t])))
        return cand[:top]

    def rodar(inicio, fim, top=10, tendencia=False, filtro_spy=False, so_buffett=False):
        valor, atual, serie = 1.0, [], []
        rebal = [d for d in datas if inicio <= d < fim]
        for i, d in enumerate(rebal):
            ate = rebal[i + 1] if i + 1 < len(rebal) else min(fim, dias[-1])
            nova = [] if (filtro_spy and px.at[d, "SPY"] < ma200.at[d, "SPY"]) else carteira_no_dia(d, top, tendencia, so_buffett)
            giro = len(set(nova) ^ set(atual)) / max(len(nova) + len(atual), 1)
            valor *= 1 - 0.001 * 2 * giro
            trecho = px.loc[d:ate]
            if nova:
                ret = (trecho[nova].ffill() / trecho[nova].iloc[0]).mean(axis=1)
            else:
                ret = pd.Series(1.0, index=trecho.index)
            serie.append(valor * ret)
            valor *= float(ret.iloc[-1])
            atual = nova
        s = pd.concat(serie)
        s = s[~s.index.duplicated(keep="last")]
        return s

    def metr(s):
        anos = (s.index[-1] - s.index[0]).days / 365.25
        return {"total": (s.iloc[-1] / s.iloc[0] - 1) * 100, "ao_ano": ((s.iloc[-1] / s.iloc[0]) ** (1 / anos) - 1) * 100,
                "queda_max": (s / s.cummax() - 1).min() * 100}

    periodos = {"2018-2021 (escolha)": (pd.Timestamp("2018-02-16"), pd.Timestamp("2022-02-15")),
                "2022-2026 (fora)": (pd.Timestamp("2022-02-16"), pd.Timestamp("2026-10-29")),
                "2018-2026 (tudo)": (pd.Timestamp("2018-02-16"), pd.Timestamp("2026-10-29"))}
    variantes = {"A consenso top10": dict(top=10), "B consenso + tendencia": dict(top=10, tendencia=True),
                 "C B + filtro SPY": dict(top=10, tendencia=True, filtro_spy=True), "D consenso top20": dict(top=20),
                 "Copiar Buffett top10": dict(top=10, so_buffett=True)}
    resultado = {}
    for pnome, (ini, fim) in periodos.items():
        print(f"\n=== {pnome} ===")
        spy = px.loc[ini:fim, "SPY"].dropna()
        m = metr(spy / spy.iloc[0])
        resultado.setdefault(pnome, {})["Segurar SPY (S&P 500)"] = m
        print(f"  {'Segurar SPY (S&P 500)':28} total {m['total']:7.1f}%  ao ano {m['ao_ano']:5.1f}%  queda max {m['queda_max']:6.1f}%")
        for vnome, p in variantes.items():
            m = metr(rodar(ini, fim, **p))
            resultado[pnome][vnome] = m
            print(f"  {vnome:28} total {m['total']:7.1f}%  ao ano {m['ao_ano']:5.1f}%  queda max {m['queda_max']:6.1f}%")
    hoje = carteira_no_dia(dias[-1], 10, True)
    print("\nCarteira de consenso + tendencia hoje:", hoje)
    (CACHE / "resultado.json").write_text(json.dumps({"resultado": resultado, "carteira_hoje": hoje}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    {"baixar13f": baixar13f, "precos": precos, "simular": simular}[sys.argv[1]]()

r"""
Hipotese (04/11/2026): o relatorio COT da CFTC (quem esta comprado e vendido nos futuros) avisa para onde o
ativo vai? Testado nos ETFs que representam os futuros: SPY (S&P 500), GLD (ouro), SLV (prata),
TLT (titulo longo do Tesouro) e FXE (euro).

Indice COT (o classico de Larry Williams): posicao liquida do grupo (comprados - vendidos) colocada numa escala
0-100 entre a minima e a maxima das ultimas N semanas.
  - seguir os COMERCIAIS (produtores e bancos que se protegem; a ideia e que eles compram barato): comprado
    quando o indice deles >= T, sai quando <= 100-T;
  - seguir os ESPECULADORES (fundos, "nao comerciais"; a ideia e acompanhar a tendencia): a mesma regra
    com o indice deles.
  Grade: 2 grupos x N em (26, 52, 156) semanas x T em (50, 65, 80) = 18 regras por ativo.
  Fora do mercado, o dinheiro fica no BIL (titulo de 1 a 3 meses), nao parado.

Sem olhar o futuro:
  - a posicao e de terca, mas sai na sexta a tarde; a regra so vale a partir do fechamento da segunda
    seguinte (terca + 6 dias, ou o proximo pregao);
  - nas paralisacoes do governo (dez/2018-jan/2019 e out/2025-jan/2026) a CFTC parou de publicar e soltou
    tudo depois: os relatorios desse intervalo so valem a partir da data em que sairam (aproximada para cima).
Custo por troca: 0,1% (diferenca de preco e escorregao; corretora sem comissao).

Protocolo (docs/hipoteses-testadas.md): escolher no periodo 1, confirmar no periodo 2, conferir os vizinhos,
comparar com comprar e segurar e com sorteios do mesmo tempo fora do mercado.
Regra marcada ANTES de rodar, para nao escolher olhando: comerciais, 156 semanas, T=80 (a de Williams).

Dados: CFTC, relatorio "legacy" so futuros (deacotAAAA.zip, publico); precos diarios ajustados da Alpaca.
Uso: .\.venv\Scripts\python.exe scripts\estudo_cot.py
"""
import io
import json
import zipfile
from pathlib import Path

import httpx
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / "user_data" / "estudo_cot"
CUSTO = 0.001
P1 = ("2016-07-01", "2021-06-30")
P2 = ("2021-07-01", "2026-10-30")
ANOS = range(2012, 2027)
# ETF -> codigo do contrato na CFTC (o codigo nao muda quando a bolsa renomeia o contrato)
ATIVOS = {"SPY": "13874A", "GLD": "088691", "SLV": "084691", "TLT": "020601", "FXE": "099741"}
CAIXA = "BIL"
PARALISACOES = [("2018-12-18", "2019-01-29", "2019-03-11"), ("2025-09-30", "2026-01-20", "2026-02-02")]
GRADE = [(g, n, t) for g in ("comerciais", "especuladores") for n in (26, 52, 156) for t in (50, 65, 80)]
MARCADA = ("comerciais", 156, 80)


def baixar_cot() -> pd.DataFrame:
    arq = PASTA / "cot_legacy.parquet"
    if arq.exists():
        return pd.read_parquet(arq)
    PASTA.mkdir(parents=True, exist_ok=True)
    partes = []
    for ano in ANOS:
        r = httpx.get(f"https://www.cftc.gov/files/dea/history/deacot{ano}.zip", timeout=120,
                      headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True)
        r.raise_for_status()
        z = zipfile.ZipFile(io.BytesIO(r.content))
        df = pd.read_csv(z.open(z.namelist()[0]), low_memory=False)
        df.columns = [c.strip() for c in df.columns]
        partes.append(df)
        print(f"COT {ano}: {len(df)} linhas", flush=True)
    df = pd.concat(partes).copy()
    df["codigo"] = df["CFTC Contract Market Code"].astype(str).str.strip()
    df = df[df["codigo"].isin(ATIVOS.values())]
    df = pd.DataFrame({
        "codigo": df["codigo"],
        "data": pd.to_datetime(df["As of Date in Form YYYY-MM-DD"]),
        "com": df["Commercial Positions-Long (All)"] - df["Commercial Positions-Short (All)"],
        "esp": df["Noncommercial Positions-Long (All)"] - df["Noncommercial Positions-Short (All)"],
    }).drop_duplicates(["codigo", "data"]).sort_values("data")
    df.to_parquet(arq)
    return df


def baixar_precos() -> pd.DataFrame:
    arq = PASTA / "precos.parquet"
    if arq.exists():
        return pd.read_parquet(arq)
    chaves = json.loads((RAIZ / "user_data" / "alpaca.json").read_text(encoding="utf-8"))
    cab = {"APCA-API-KEY-ID": chaves["key"], "APCA-API-SECRET-KEY": chaves["secret"]}
    token, linhas = None, []
    while True:
        params = {"symbols": ",".join([*ATIVOS, CAIXA]), "timeframe": "1Day", "start": "2016-01-01",
                  "end": "2026-11-03", "adjustment": "all", "feed": "sip", "limit": 10000}
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
    px = pd.DataFrame(linhas, columns=["sym", "dia", "fecha"]).pivot(index="dia", columns="sym", values="fecha")
    px.index = pd.to_datetime(px.index)
    px = px.sort_index()
    px.to_parquet(arq)
    return px


def disponivel_em(data: pd.Timestamp) -> pd.Timestamp:
    for ini, fim, saiu in PARALISACOES:
        if pd.Timestamp(ini) <= data <= pd.Timestamp(fim):
            return pd.Timestamp(saiu)
    return data + pd.Timedelta(days=6)


def indice(serie: pd.Series, n: int) -> pd.Series:
    mn, mx = serie.rolling(n, min_periods=n).min(), serie.rolling(n, min_periods=n).max()
    return ((serie - mn) / (mx - mn).replace(0, np.nan) * 100)


def posicao(cot: pd.DataFrame, codigo: str, dias: pd.DatetimeIndex, grupo: str, n: int, t: int) -> pd.Series:
    """1 = no ativo, 0 = no caixa, a partir do fechamento do dia (vale para o retorno do dia seguinte)."""
    c = cot[cot["codigo"] == codigo].set_index("data").sort_index()
    idx = indice(c["com" if grupo == "comerciais" else "esp"], n).dropna()
    estado, sinais = 0, {}
    for data, v in idx.items():
        if v >= t:
            estado = 1
        elif v <= 100 - t:
            estado = 0
        sinais[disponivel_em(data)] = estado
    s = pd.Series(sinais).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    return s.reindex(dias.union(s.index)).ffill().reindex(dias).fillna(0)


def rodar(px: pd.Series, caixa: pd.Series, pos: pd.Series, ini: str, fim: str):
    """Retorno anual %, queda maxima %, % do tempo no ativo, trocas."""
    m = (px.index >= ini) & (px.index <= fim)
    r_at, r_cx = px.pct_change()[m], caixa.pct_change()[m]
    p = pos.shift(1)[m].fillna(0)  # posicao decidida no fechamento de ontem
    trocas = p.diff().abs().fillna(p.iloc[0])
    r = p * r_at + (1 - p) * r_cx - trocas * CUSTO
    cur = (1 + r.fillna(0)).cumprod()
    anos = (px.index[m][-1] - px.index[m][0]).days / 365.25
    return ((cur.iloc[-1] ** (1 / anos) - 1) * 100, ((cur / cur.cummax()).min() - 1) * 100,
            p.mean() * 100, int(trocas.sum()))


def sorteio(px, caixa, pos, ini, fim, vezes=1000) -> np.ndarray:
    """Mesmos blocos de dentro/fora da regra, em ordem aleatoria: mesmo tempo fora, mesmas trocas."""
    m = (pos.index >= ini) & (pos.index <= fim)
    p = pos[m]
    blocos, atual, n = [], p.iloc[0], 0
    for v in p:
        if v == atual:
            n += 1
        else:
            blocos.append((atual, n))
            atual, n = v, 1
    blocos.append((atual, n))
    rng, res = np.random.default_rng(42), []
    for _ in range(vezes):
        ordem = rng.permutation(len(blocos))
        s = pd.Series(np.concatenate([[blocos[i][0]] * blocos[i][1] for i in ordem]), index=p.index)
        res.append(rodar(px, caixa, s.reindex(pos.index).fillna(0), ini, fim)[0])
    return np.array(res)


def main():
    cot, px = baixar_cot(), baixar_precos()
    for sym, cod in ATIVOS.items():
        datas = cot[cot["codigo"] == cod]["data"]
        print(f"{sym}: {len(datas)} relatorios COT ({datas.min().date()} a {datas.max().date()}), "
              f"{px[sym].notna().sum()} dias de preco")
    caixa = px[CAIXA].ffill()
    linhas = []
    for sym, cod in ATIVOS.items():
        a = px[sym].ffill()
        bh1 = rodar(a, caixa, pd.Series(1.0, index=a.index), *P1)
        bh2 = rodar(a, caixa, pd.Series(1.0, index=a.index), *P2)
        for g, n, t in GRADE:
            pos = posicao(cot, cod, a.index, g, n, t)
            r1, r2 = rodar(a, caixa, pos, *P1), rodar(a, caixa, pos, *P2)
            linhas.append(dict(ativo=sym, grupo=g, semanas=n, T=t, p1=r1[0], p1_queda=r1[1], p1_dentro=r1[2],
                               p2=r2[0], p2_queda=r2[1], p2_dentro=r2[2], trocas=r1[3] + r2[3],
                               bh1=bh1[0], bh1_queda=bh1[1], bh2=bh2[0], bh2_queda=bh2[1]))
    df = pd.DataFrame(linhas)
    df["ganha1"], df["ganha2"] = df.p1 > df.bh1, df.p2 > df.bh2
    df.round(2).to_csv(PASTA / "resultado.csv", index=False)

    print("\nComprar e segurar (% ao ano | queda maxima):")
    for sym in ATIVOS:
        b = df[df.ativo == sym].iloc[0]
        print(f"  {sym}: P1 {b.bh1:5.1f}% | {b.bh1_queda:5.1f}%    P2 {b.bh2:5.1f}% | {b.bh2_queda:5.1f}%")

    print("\nRegra marcada antes (comerciais, 156 semanas, T=80):")
    for sym in ATIVOS:
        x = df[(df.ativo == sym) & (df.grupo == MARCADA[0]) & (df.semanas == MARCADA[1]) & (df["T"] == MARCADA[2])].iloc[0]
        print(f"  {sym}: P1 {x.p1:5.1f}% (no ativo {x.p1_dentro:3.0f}%)  P2 {x.p2:5.1f}% (no ativo {x.p2_dentro:3.0f}%)"
              f"  ganha nos dois: {'sim' if x.ganha1 and x.ganha2 else 'nao'}")

    print("\nMelhor regra do P1 em cada ativo, conferida no P2:")
    for sym, cod in ATIVOS.items():
        d = df[df.ativo == sym]
        x = d.loc[d.p1.idxmax()]
        a = px[sym].ffill()
        pos = posicao(cot, cod, a.index, x.grupo, int(x.semanas), int(x["T"]))
        s2 = sorteio(a, caixa, pos, *P2)
        print(f"  {sym}: {x.grupo} {int(x.semanas)} sem T={int(x['T'])}: P1 {x.p1:5.1f}% (indice {x.bh1:5.1f}%) -> "
              f"P2 {x.p2:5.1f}% (indice {x.bh2:5.1f}%), queda {x.p2_queda:5.1f}% vs {x.bh2_queda:5.1f}%; "
              f"no P2 ganha de {(s2 < x.p2).mean() * 100:3.0f}% dos sorteios")

    print("\nQuantas das 18 regras ganham do comprar e segurar nos dois periodos:")
    for sym in ATIVOS:
        d = df[df.ativo == sym]
        print(f"  {sym}: {int((d.ganha1 & d.ganha2).sum())} de 18  (P1: {int(d.ganha1.sum())}, P2: {int(d.ganha2.sum())})")
    print(f"  total: {int((df.ganha1 & df.ganha2).sum())} de {len(df)}")
    for g in ("comerciais", "especuladores"):
        d = df[df.grupo == g]
        print(f"  seguindo os {g}: {int((d.ganha1 & d.ganha2).sum())} de {len(d)}")


if __name__ == "__main__":
    main()

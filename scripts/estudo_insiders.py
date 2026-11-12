r"""
Hipotese (12/11/2026): quando VARIOS diretores de uma empresa compram acoes dela com o proprio dinheiro, em poucos dias,
a acao sobe mais que o mercado nos meses seguintes? (compras "em grupo" de insiders, formulario 4 da SEC)

Dados:
  - compras: conjuntos trimestrais de formularios 3/4/5 da SEC (2016 a 2026), so compra a mercado (codigo P),
    so diretor ou executivo (fundo dono de 10% fica de fora), preco >= US$ 2;
  - o sinal so vale a partir do dia da ENTREGA do formulario que completa o grupo (o que se sabia na hora);
  - precos diarios da Alpaca (ajustados), entrada no fechamento do 1o pregao depois da entrega.
Regra: "grupo" = N diretores diferentes comprando em ate 30 dias, somando pelo menos V dolares; segura H pregoes.
  Carteira com partes iguais entre os sinais abertos; sem sinal aberto, fica em caixa. Custo 0,2% (ida e volta).
Protocolo de sempre: escolher em 2017-2021, conferir em 2022-2026, vizinhos, sorteio (mesmas acoes, datas sorteadas).
Vies conhecido: empresa que quebrou ou mudou de codigo pode nao ter preco na Alpaca (a cobertura e impressa).

Uso (na pasta do projeto):
  .\.venv\Scripts\python.exe scripts\estudo_insiders.py baixar    (SEC + precos; demora, guarda em cache)
  .\.venv\Scripts\python.exe scripts\estudo_insiders.py
"""
import io
import json
import re
import sys
import time
import zipfile
from pathlib import Path

import httpx
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
CACHE = RAIZ / "user_data" / "estudo_insiders"
PAGINA = "https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets"
P1 = ("2017-01-01", "2021-12-31")
P2 = ("2022-01-01", "2026-10-31")
CUSTO = 0.002
JANELA = 30


def cabecalho_sec() -> dict:
    cfg = json.loads((RAIZ / "acoes-eua" / "trader" / "config.json").read_text(encoding="utf-8"))
    return {"User-Agent": cfg["sec_user_agent"]}


def ler_tsv(z: zipfile.ZipFile, nome: str, colunas: list[str]) -> pd.DataFrame:
    arq = next(n for n in z.namelist() if n.upper().endswith(nome))
    with z.open(arq) as f:
        return pd.read_csv(f, sep="\t", usecols=colunas, dtype=str, quoting=3, on_bad_lines="skip")


def baixar_compras():
    (CACHE / "trimestres").mkdir(parents=True, exist_ok=True)
    cab = cabecalho_sec()
    html = httpx.get(PAGINA, headers=cab, follow_redirects=True, timeout=60).text
    links = sorted(set(re.findall(r'href="([^"]+?(\d{4})q(\d)_form345\.zip)"', html)), key=lambda x: (x[1], x[2]))
    for link, ano, tri in links:
        if int(ano) < 2016:
            continue
        destino = CACHE / "trimestres" / f"{ano}q{tri}.parquet"
        if destino.exists():
            continue
        r = httpx.get("https://www.sec.gov" + link, headers=cab, follow_redirects=True, timeout=300)
        r.raise_for_status()
        z = zipfile.ZipFile(io.BytesIO(r.content))
        sub = ler_tsv(z, "SUBMISSION.TSV", ["ACCESSION_NUMBER", "FILING_DATE", "ISSUERCIK", "ISSUERTRADINGSYMBOL"])
        dono = ler_tsv(z, "REPORTINGOWNER.TSV", ["ACCESSION_NUMBER", "RPTOWNERCIK", "RPTOWNER_RELATIONSHIP"])
        tr = ler_tsv(z, "NONDERIV_TRANS.TSV", ["ACCESSION_NUMBER", "TRANS_CODE", "TRANS_DATE", "TRANS_SHARES",
                                              "TRANS_PRICEPERSHARE", "TRANS_ACQUIRED_DISP_CD"])
        tr = tr[(tr["TRANS_CODE"] == "P") & (tr["TRANS_ACQUIRED_DISP_CD"] == "A")].copy()
        tr["valor"] = pd.to_numeric(tr["TRANS_SHARES"], errors="coerce") * pd.to_numeric(tr["TRANS_PRICEPERSHARE"], errors="coerce")
        tr["preco"] = pd.to_numeric(tr["TRANS_PRICEPERSHARE"], errors="coerce")
        tr = tr[(tr["preco"] >= 2) & (tr["valor"] > 0)]
        # so diretor ou executivo: fundo que e so "dono de 10%" nao e insider de gestao
        rel = dono["RPTOWNER_RELATIONSHIP"].fillna("")
        dono = dono[rel.str.contains("Director|Officer", case=False)]
        dono = dono.drop_duplicates("ACCESSION_NUMBER")
        g = (tr.groupby("ACCESSION_NUMBER").agg(valor=("valor", "sum"), dia_compra=("TRANS_DATE", "max")).reset_index()
             .merge(sub, on="ACCESSION_NUMBER").merge(dono[["ACCESSION_NUMBER", "RPTOWNERCIK"]], on="ACCESSION_NUMBER"))
        g["entregue"] = pd.to_datetime(g["FILING_DATE"], format="%d-%b-%Y", errors="coerce")
        g["dia_compra"] = pd.to_datetime(g["dia_compra"], format="%d-%b-%Y", errors="coerce")
        g = g.rename(columns={"ISSUERCIK": "empresa", "ISSUERTRADINGSYMBOL": "acao", "RPTOWNERCIK": "quem"})
        g[["empresa", "acao", "quem", "valor", "dia_compra", "entregue"]].to_parquet(destino)
        print(f"{ano}q{tri}: {len(g)} formularios de compra", flush=True)
        time.sleep(0.5)


def carregar_compras() -> pd.DataFrame:
    df = pd.concat([pd.read_parquet(a) for a in sorted((CACHE / "trimestres").glob("*.parquet"))], ignore_index=True)
    df = df.dropna(subset=["entregue", "dia_compra", "acao"])
    df["acao"] = df["acao"].str.strip().str.upper().str.replace("-", ".", regex=False)
    df = df[df["acao"].str.fullmatch(r"[A-Z]{1,5}(\.[A-Z])?")]
    df = df[(df["dia_compra"] <= df["entregue"]) & (df["entregue"] - df["dia_compra"] <= pd.Timedelta(days=60))]
    return df.sort_values("entregue").reset_index(drop=True)


def sinais(df: pd.DataFrame, n: int, minimo: float) -> pd.DataFrame:
    """Primeiro dia (entrega) em que N diretores diferentes compraram em 30 dias somando `minimo`;
    depois de um sinal, a mesma empresa so da outro 90 dias depois."""
    saida = []
    for empresa, g in df.groupby("empresa", sort=False):
        if g["quem"].nunique() < n:
            continue
        ultimo = None
        for dia in g["entregue"].unique():
            if ultimo is not None and dia - ultimo < pd.Timedelta(days=90):
                continue
            janela = g[(g["entregue"] <= dia) & (g["dia_compra"] >= dia - pd.Timedelta(days=JANELA))]
            if janela["quem"].nunique() >= n and janela["valor"].sum() >= minimo:
                saida.append((empresa, janela["acao"].iloc[-1], pd.Timestamp(dia), janela["valor"].sum()))
                ultimo = dia
    return pd.DataFrame(saida, columns=["empresa", "acao", "dia", "valor"])


def baixar_precos():
    df = carregar_compras()
    s = sinais(df, 2, 25_000)
    tickers = sorted(set(s["acao"]) | {"SPY"})
    chaves = json.loads((RAIZ / "user_data" / "alpaca.json").read_text(encoding="utf-8"))
    cab = {"APCA-API-KEY-ID": chaves["key"], "APCA-API-SECRET-KEY": chaves["secret"]}
    destino = CACHE / "precos.parquet"
    feitos = pd.read_parquet(destino) if destino.exists() else pd.DataFrame()
    falta = [t for t in tickers if t not in set(feitos.columns)]
    print(f"{len(tickers)} acoes com sinal, {len(falta)} a baixar", flush=True)
    colunas = {}
    for i in range(0, len(falta), 50):
        lote, token, linhas = falta[i:i + 50], None, []
        while True:
            params = {"symbols": ",".join(lote), "timeframe": "1Day", "start": "2016-06-01", "end": "2026-11-11",
                      "adjustment": "all", "feed": "sip", "limit": 10000}
            if token:
                params["page_token"] = token
            r = httpx.get("https://data.alpaca.markets/v2/stocks/bars", params=params, headers=cab, timeout=90)
            if r.status_code == 429:
                time.sleep(20)
                continue
            r.raise_for_status()
            d = r.json()
            for sym, barras in (d.get("bars") or {}).items():
                linhas += [(sym, b["t"][:10], b["c"]) for b in barras]
            token = d.get("next_page_token")
            if not token:
                break
        x = pd.DataFrame(linhas, columns=["sym", "dia", "fecha"])
        colunas.update({sy: g.set_index("dia")["fecha"] for sy, g in x.groupby("sym")})
        if (i // 50) % 10 == 0:
            print(f"precos: {i + len(lote)}/{len(falta)}", flush=True)
    novo = pd.DataFrame(colunas)
    novo.index = pd.to_datetime(novo.index)
    tudo = pd.concat([feitos, novo], axis=1) if len(feitos) else novo
    tudo.sort_index().to_parquet(destino)
    print(f"fim precos: {tudo.shape}", flush=True)


# ------------------------------------------------------------------ simulacao
def entradas(s: pd.DataFrame, px: pd.DataFrame) -> list[tuple[str, int]]:
    """(acao, posicao do dia de entrada no indice) para cada sinal com preco; entrada no 1o pregao depois da entrega."""
    dias = px.index
    out = []
    for acao, dia in zip(s["acao"], s["dia"]):
        if acao not in px.columns:
            continue
        i = dias.searchsorted(dia, side="right")
        if i < len(dias) and not np.isnan(px[acao].iat[i]):
            out.append((acao, i))
    return out


def carteira(ent, ret: pd.DataFrame, h: int) -> pd.Series:
    """Retorno diario da carteira: partes iguais entre os sinais abertos; sem sinal, caixa (zero)."""
    soma = np.zeros(len(ret))
    conta = np.zeros(len(ret))
    for acao, i in ent:
        fim = min(i + h, len(ret) - 1)
        r = ret[acao].values[i + 1:fim + 1].copy()
        r = np.nan_to_num(r)
        if len(r) == 0:
            continue
        r[0] -= CUSTO / 2
        r[-1] -= CUSTO / 2
        soma[i + 1:fim + 1] += r
        conta[i + 1:fim + 1] += 1
    return pd.Series(np.where(conta > 0, soma / np.maximum(conta, 1), 0.0), index=ret.index), conta


def medir(serie: pd.Series, ini: str, fim: str):
    r = serie[(serie.index >= ini) & (serie.index <= fim)]
    cur = (1 + r).cumprod()
    anos = (r.index[-1] - r.index[0]).days / 365.25
    return (cur.iloc[-1] ** (1 / anos) - 1) * 100, ((cur / cur.cummax()).min() - 1) * 100


def excesso(ent, px: pd.DataFrame, h: int, ini: str, fim: str) -> tuple[float, int]:
    """Media de (retorno da acao - retorno do SPY) nos H pregoes depois da entrada, em pontos %."""
    v = []
    for acao, i in ent:
        if not (ini <= str(px.index[i].date()) <= fim) or i + h >= len(px):
            continue
        a = px[acao].iat[i + h] / px[acao].iat[i] - 1
        m = px["SPY"].iat[i + h] / px["SPY"].iat[i] - 1
        if np.isfinite(a):
            v.append(a - m - CUSTO)
    return (np.mean(v) * 100 if v else np.nan), len(v)


def sorteio(ent, px, h, ini, fim, vezes=300):
    """Mesmas acoes, data de entrada sorteada no mesmo ano (com preco): mede se o MOMENTO da compra importa."""
    rng = np.random.default_rng(42)
    anos = px.index.year
    res = []
    for _ in range(vezes):
        nova = []
        for acao, i in ent:
            ok = np.where((anos == anos[i]) & px[acao].notna().values)[0]
            if len(ok):
                nova.append((acao, int(rng.choice(ok))))
        res.append(excesso(nova, px, h, ini, fim)[0])
    return np.array(res)


def main():
    if "baixar" in sys.argv:
        baixar_compras()
        baixar_precos()
        return
    df = carregar_compras()
    px = pd.read_parquet(CACHE / "precos.parquet").sort_index()
    px = px[px.index >= "2016-06-01"]
    ret = px.pct_change(fill_method=None)
    spy = ret["SPY"].fillna(0)
    print(f"{len(df)} formularios de compra de diretores, {df['empresa'].nunique()} empresas")
    b1, b2 = medir(spy, *P1), medir(spy, *P2)
    print(f"S&P 500 (SPY): 2017-21 {b1[0]:5.1f}% ao ano (queda {b1[1]:5.1f}%) | 2022-26 {b2[0]:5.1f}% (queda {b2[1]:5.1f}%)\n")

    linhas = []
    for n in (2, 3, 4):
        for minimo in (100_000, 500_000):
            s = sinais(df, n, minimo)
            ent = entradas(s, px)
            for h in (21, 63, 126):
                cart, conta = carteira(ent, ret, h)
                a, b = medir(cart, *P1), medir(cart, *P2)
                e1, q1 = excesso(ent, px, h, *P1)
                e2, q2 = excesso(ent, px, h, *P2)
                vazio = (conta[(px.index >= P2[0])] == 0).mean() * 100
                linhas.append(dict(n=n, minimo=minimo, h=h, sinais=len(s), com_preco=len(ent), a=a, b=b,
                                   e1=e1, e2=e2, q1=q1, q2=q2, vazio=vazio, ent=ent))
                marca = "GANHA NOS DOIS" if a[0] > b1[0] and b[0] > b2[0] else ""
                print(f"  {n} diretores, US$ {minimo / 1000:>3.0f} mil, {h:3d} preg | sinais {len(s):4d} "
                      f"(preco {len(ent) / max(len(s), 1) * 100:3.0f}%) | 17-21 {a[0]:5.1f}% q{a[1]:6.1f}% exc {e1:+5.2f} "
                      f"| 22-26 {b[0]:5.1f}% q{b[1]:6.1f}% exc {e2:+5.2f} (caixa {vazio:3.0f}%) {marca}")
    ganha = sum(1 for x in linhas if x["a"][0] > b1[0] and x["b"][0] > b2[0])
    exc = sum(1 for x in linhas if x["e1"] > 0 and x["e2"] > 0)
    print(f"\nVersoes que ganham do S&P nos dois periodos (carteira): {ganha} de {len(linhas)}")
    print(f"Versoes com excesso medio por sinal positivo nos dois periodos: {exc} de {len(linhas)}")
    m = max(linhas, key=lambda x: x["e1"])
    s = sorteio(m["ent"], px, m["h"], *P2)
    print(f"Melhor de 2017-21 (excesso por sinal): {m['n']} diretores, US$ {m['minimo'] / 1000:.0f} mil, {m['h']} pregoes: "
          f"{m['e1']:+.2f} -> 2022-26 {m['e2']:+.2f} pontos por sinal ({m['q2']} sinais); "
          f"ganha de {(s < m['e2']).mean() * 100:.0f}% dos sorteios de data (media dos sorteios {np.nanmean(s):+.2f})")
    res = pd.DataFrame([{k: v for k, v in x.items() if k != "ent"} for x in linhas])
    res.to_csv(CACHE / "resultado.csv", index=False)


if __name__ == "__main__":
    main()

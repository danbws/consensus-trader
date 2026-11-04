r"""
Hipotese (04/11/2026): o dinheiro entrando ou saindo dos ETFs de bitcoin dos EUA (o "dinheiro grande") avisa
para onde o bitcoin vai nos dias seguintes? Se sim, ficar comprado so quando o fluxo e positivo ganharia de
"comprar e segurar".

Dados
  - fluxo liquido diario somado dos ETFs (US$ milhoes), Farside Investors, 11/01/2024 a 03/11/2026:
    user_data/estudo_etf_btc/fluxos_farside.csv (copiado da pagina publica; conferido: 722 dias, soma 56.533,9)
  - preco diario do BTC/USDT na Binance (fechamento 00:00 UTC), API publica de candles.

Sem olhar o futuro: o fluxo do pregao de NY do dia t so e conhecido depois do fechamento (sai a noite).
Entao a decisao vale a partir do fechamento do dia t+1 (ATRASO=1) ou t+2 (ATRASO=2, mais conservador).
Custo por troca (compra ou venda): 0,15% (taxa 0,1% + diferenca de preco 0,05%).

Protocolo (o mesmo de docs/hipoteses-testadas.md): escolher no periodo 1, confirmar no periodo 2, conferir
vizinhos e comparar com comprar e segurar.
Uso: .\.venv\Scripts\python.exe scripts\estudo_etf_btc.py
"""
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / "user_data" / "estudo_etf_btc"
CUSTO = 0.0015
P1 = ("2024-01-15", "2025-06-30")
P2 = ("2025-07-01", "2026-11-03")


def fluxos() -> pd.Series:
    v = lambda s: -float(s[1:-1].replace(",", "")) if s.startswith("(") else float(s.replace(",", ""))
    linhas = list(csv.reader(open(PASTA / "fluxos_farside.csv", encoding="utf-8"), delimiter=";"))[1:]
    s = pd.Series({pd.Timestamp(datetime.strptime(d, "%d %b %Y")): v(x) for d, x in linhas}).sort_index()
    return s


def precos_btc() -> pd.Series:
    arq = PASTA / "btc_diario.json"
    if not arq.exists():
        velas, ini = [], int(datetime(2023, 12, 1, tzinfo=timezone.utc).timestamp() * 1000)
        while True:
            r = httpx.get("https://api.binance.com/api/v3/klines", timeout=30,
                          params={"symbol": "BTCUSDT", "interval": "1d", "startTime": ini, "limit": 1000}).json()
            velas += r
            if len(r) < 1000:
                break
            ini = r[-1][0] + 1
        arq.write_text(json.dumps([[k[0], float(k[4])] for k in velas]))
    dados = json.loads(arq.read_text())
    # vela do dia D fecha as 00:00 UTC de D+1: o preco "do fim do dia D"
    return pd.Series({pd.Timestamp(datetime.fromtimestamp(t / 1000, timezone.utc).date()): c for t, c in dados}).sort_index()


def sinal(fl: pd.Series, dias: pd.DatetimeIndex, janela: int, limite: float, tipo: str) -> pd.Series:
    """1 = comprado, 0 = fora. Fluxo do dia de pregao t; dias sem pregao repetem o ultimo valor conhecido."""
    soma = fl.rolling(janela).sum()
    if tipo == "positivo":         # comprado quando a soma da janela esta acima do limite
        s = (soma > limite).astype(float)
    else:                          # "evitar saidas": so sai quando a soma da janela fica abaixo de -limite
        s = (soma >= -limite).astype(float)
    return s.reindex(dias, method="ffill").fillna(0.0)


def rodar(px: pd.Series, posicao: pd.Series, ini: str, fim: str, atraso: int):
    ret = px.pct_change().fillna(0.0)
    pos = posicao.shift(atraso + 1).fillna(0.0)  # +1: a posicao decidida no fim do dia t rende no dia t+1
    trecho = (ret.index >= ini) & (ret.index <= fim)
    r, p = ret[trecho], pos[trecho]
    trocas = p.diff().abs().fillna(p.iloc[0])
    curva = (1 + r * p - trocas * CUSTO).cumprod()
    anos = (r.index[-1] - r.index[0]).days / 365.25
    ao_ano = (curva.iloc[-1] ** (1 / anos) - 1) * 100
    queda = ((curva / curva.cummax()) - 1).min() * 100
    return ao_ano, queda, p.mean() * 100, int(trocas.sum())


def segurar(px: pd.Series, ini: str, fim: str):
    s = px[(px.index >= ini) & (px.index <= fim)]
    anos = (s.index[-1] - s.index[0]).days / 365.25
    return ((s.iloc[-1] / s.iloc[0]) ** (1 / anos) - 1) * 100, ((s / s.cummax()) - 1).min() * 100


def main():
    fl, px = fluxos(), precos_btc()
    dias = px.index[px.index >= "2024-01-11"]
    px = px[dias]
    bh = {k: segurar(px, *p) for k, p in (("P1", P1), ("P2", P2))}
    print(f"Comprar e segurar BTC:  P1 {bh['P1'][0]:6.1f}%/ano (pior queda {bh['P1'][1]:.0f}%)   "
          f"P2 {bh['P2'][0]:6.1f}%/ano (pior queda {bh['P2'][1]:.0f}%)\n")

    # correlacao simples: fluxo de hoje x retorno do BTC amanha (sem regra nenhuma)
    ret = px.pct_change()
    f = fl.reindex(dias).fillna(0.0)
    for atraso in (0, 1, 2):
        c = np.corrcoef(f[:-(atraso + 1)], ret.shift(-(atraso + 1)).dropna()[:len(f) - atraso - 1])[0, 1]
        print(f"Correlacao fluxo do dia x retorno {atraso + 1} dia(s) depois: {c:+.3f}")
    c0 = np.corrcoef(f[1:], ret[1:])[0, 1]
    print(f"(no MESMO dia: {c0:+.3f}  -> isso e o preco puxando o fluxo, nao da para usar)\n")

    resultados = []
    for tipo in ("positivo", "evitar_saidas"):
        for janela in (1, 3, 5, 10, 20):
            for limite in (0, 250, 500, 1000):
                if tipo == "evitar_saidas" and limite == 0:
                    continue
                pos = sinal(fl, dias, janela, limite, tipo)
                for atraso in (1, 2):
                    r1 = rodar(px, pos, *P1, atraso)
                    r2 = rodar(px, pos, *P2, atraso)
                    resultados.append({"tipo": tipo, "janela": janela, "limite": limite, "atraso": atraso,
                                       "p1": r1[0], "p1_queda": r1[1], "p1_dentro": r1[2], "p1_trocas": r1[3],
                                       "p2": r2[0], "p2_queda": r2[1], "p2_dentro": r2[2], "p2_trocas": r2[3]})
    df = pd.DataFrame(resultados)
    df["vence_p1"] = df.p1 > bh["P1"][0]
    df["vence_p2"] = df.p2 > bh["P2"][0]
    df["vence_os_2"] = df.vence_p1 & df.vence_p2
    pd.set_option("display.width", 200)
    print(f"{len(df)} variantes. Vencem comprar-e-segurar no P1: {df.vence_p1.sum()}, no P2: {df.vence_p2.sum()}, "
          f"nos dois: {df.vence_os_2.sum()}\n")

    # protocolo: escolhe a melhor do P1 (atraso 1) e olha como ela foi no P2
    melhor = df[df.atraso == 1].sort_values("p1", ascending=False).head(5)
    print("Top 5 escolhidas no periodo 1 (atraso 1) e o que fizeram no periodo 2:")
    print(melhor[["tipo", "janela", "limite", "p1", "p1_queda", "p1_dentro", "p2", "p2_queda", "p2_dentro", "p2_trocas"]]
          .round(1).to_string(index=False))
    e = melhor.iloc[0]
    viz = df[(df.tipo == e.tipo) & (df.atraso == 1) & (df.janela.isin([e.janela, *[j for j in (1, 3, 5, 10, 20) if abs(np.log(j / e.janela)) < 1.2]]))]
    print(f"\nVizinhas da escolhida ({e.tipo}, janela {e.janela}, limite {e.limite}): "
          f"{viz.vence_os_2.sum()} de {len(viz)} vencem nos dois periodos")
    # menor queda com retorno parecido? (o fluxo pode servir de "freio" mesmo sem ganhar mais)
    df["p2_ret_por_queda"] = df.p2 / df.p2_queda.abs()
    bh_rq = bh["P2"][0] / abs(bh["P2"][1])
    print(f"\nRetorno/pior queda no P2: comprar e segurar {bh_rq:.2f}; variantes melhores que isso: "
          f"{(df.p2_ret_por_queda > bh_rq).sum()} de {len(df)}")
    df.round(2).to_csv(PASTA / "resultado.csv", index=False, sep=";")
    print(f"\nTabela completa: {PASTA / 'resultado.csv'}")


if __name__ == "__main__":
    main()

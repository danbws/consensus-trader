r"""
Hipotese (12/11/2026): uma fatia FIXA de bitcoin dentro da carteira de consenso, so comprada e mantida (sem robo de
trade), melhora o resultado? E quanto ela aumenta as quedas?

Base: a carteira de consenso diaria do estudo (scripts/estudo_consenso_robustez.py, top 10, corte 3%, 2 gestores,
custo 0,2%), de 16/02/2018 a 29/10/2026, e o BTC/USDT diario da Binance (API publica) no mesmo periodo.
Regra: X% em bitcoin e o resto no consenso; X em 0, 2,5, 5, 10 e 20%. A fatia volta ao peso a cada 3 meses
(ou nunca, na versao "sem reequilibrar"). Custo de 0,2% sobre o que se troca no reequilibrio.
Nada se escolhe olhando o resultado: todas as fatias sao mostradas nos dois periodos e ano a ano.

Uso: .\.venv\Scripts\python.exe scripts\estudo_fatia_btc.py
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estudo_consenso_robustez as rb  # noqa: E402  (ao importar, imprime a tabela de robustez)

RAIZ = Path(__file__).resolve().parent.parent
ARQ = RAIZ / "user_data" / "estudo_etf_btc" / "btc_diario_2017.json"
P1 = ("2018-02-16", "2022-02-15")
P2 = ("2022-02-16", "2026-10-29")
CUSTO = 0.002


def precos_btc() -> pd.Series:
    if not ARQ.exists():
        velas, ini = [], int(datetime(2017, 9, 1, tzinfo=timezone.utc).timestamp() * 1000)
        while True:
            r = httpx.get("https://api.binance.com/api/v3/klines", timeout=30,
                          params={"symbol": "BTCUSDT", "interval": "1d", "startTime": ini, "limit": 1000}).json()
            velas += r
            if len(r) < 1000:
                break
            ini = r[-1][0] + 1
        ARQ.write_text(json.dumps([[k[0], float(k[4])] for k in velas]))
    dados = json.loads(ARQ.read_text())
    return pd.Series({pd.Timestamp(datetime.fromtimestamp(t / 1000, timezone.utc).date()): c for t, c in dados}).sort_index()


def misturar(cons: pd.Series, btc: pd.Series, fatia: float, reequilibrar: bool) -> pd.Series:
    """Valor diario de uma carteira com `fatia` em BTC e o resto no consenso."""
    rc, rb_ = cons.pct_change().fillna(0).values, btc.pct_change().fillna(0).values
    vc, vb = 1 - fatia, fatia
    saida, trimestre = [], cons.index[0].quarter
    for i, dia in enumerate(cons.index):
        vc *= 1 + rc[i]
        vb *= 1 + rb_[i]
        total = vc + vb
        if reequilibrar and fatia > 0 and dia.quarter != trimestre:
            troca = abs(vb - total * fatia)
            total -= troca * CUSTO
            vc, vb = total * (1 - fatia), total * fatia
            trimestre = dia.quarter
        saida.append(total)
    return pd.Series(saida, index=cons.index)


def medir(s: pd.Series, ini: str, fim: str):
    s = s[(s.index >= ini) & (s.index <= fim)]
    anos = (s.index[-1] - s.index[0]).days / 365.25
    r = s.pct_change().dropna()
    return ((s.iloc[-1] / s.iloc[0]) ** (1 / anos) - 1) * 100, ((s / s.cummax()).min() - 1) * 100, \
        r.std() * np.sqrt(252) * 100


def main():
    cons = rb.rodar(pd.Timestamp(P1[0]), pd.Timestamp(P2[1]))
    btc = precos_btc().reindex(cons.index, method="ffill")
    print("\nFatia de bitcoin dentro da carteira de consenso (ao ano | pior queda | oscilacao anual)")
    print(f"  {'versao':34} {'2018-2021':>30} {'2022-2026':>30}")
    series = {}
    for reeq in (True, False):
        for fatia in (0.0, 0.025, 0.05, 0.10, 0.20):
            if fatia == 0 and not reeq:
                continue
            nome = f"{fatia * 100:4.1f}% BTC" + ("" if reeq else ", sem reequilibrar")
            s = misturar(cons, btc, fatia, reeq)
            series[nome] = s
            a, b = medir(s, *P1), medir(s, *P2)
            print(f"  {nome:34} {a[0]:6.1f}% | {a[1]:6.1f}% | {a[2]:5.1f}%     {b[0]:6.1f}% | {b[1]:6.1f}% | {b[2]:5.1f}%")
    a, b = medir(btc, *P1), medir(btc, *P2)
    print(f"  {'so bitcoin (comparacao)':34} {a[0]:6.1f}% | {a[1]:6.1f}% | {a[2]:5.1f}%     {b[0]:6.1f}% | {b[1]:6.1f}% | {b[2]:5.1f}%")

    print("\nAno a ano (reequilibrando a cada 3 meses):")
    nomes = [n for n in series if "sem" not in n]
    print("  ano  " + "".join(f"{n.strip():>13}" for n in nomes) + f"{'bitcoin':>10}")
    for ano in range(2018, 2027):
        linha = f"  {ano} "
        for n in nomes:
            s = series[n][series[n].index.year == ano]
            linha += f"{(s.iloc[-1] / s.iloc[0] - 1) * 100:12.1f}%"
        b = btc[btc.index.year == ano]
        print(linha + f"{(b.iloc[-1] / b.iloc[0] - 1) * 100:9.1f}%")

    # quanto a fatia ajudou em cada janela de 3 anos (todas as datas de inicio): mede se depende do ponto de partida
    print("\nJanelas de 3 anos (todas as datas de inicio): em quantas a fatia rendeu mais que 0% de BTC")
    base = series[nomes[0]]
    for n in nomes[1:]:
        s = series[n]
        ganhou, pior = [], []
        for i in range(0, len(s) - 756, 5):
            ganhou.append(s.iloc[i + 756] / s.iloc[i] > base.iloc[i + 756] / base.iloc[i])
            q = s.iloc[i:i + 757]
            pior.append(((q / q.cummax()).min() - 1) * 100)
        print(f"  {n.strip():12} rendeu mais em {np.mean(ganhou) * 100:3.0f}% das janelas")


if __name__ == "__main__":
    main()

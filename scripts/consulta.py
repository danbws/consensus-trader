r"""
Consulta: "o robo compraria isto agora?" para qualquer par spot da Binance.

Aplica as mesmas regras da RoboTendenciaBTC (docs/aulas/03-a-estrategia.md) sobre o preco
real de agora e explica cada uma. Nao e previsao nem recomendacao: e o que as regras dizem.

Uso:  .\.venv\Scripts\python.exe scripts\consulta.py USDT/BRL [--json]
"""
import json
import sys
from datetime import datetime, timezone

import ccxt
import pandas as pd
import requests
import talib

FNG_MAX = 80


def velas(ex, par, tf, n):
    df = pd.DataFrame(ex.fetch_ohlcv(par, tf, limit=n), columns=["t", "o", "h", "l", "c", "v"])
    return df.iloc[:-1]  # so velas fechadas, como o robo


def tendencia(df):
    c = df["c"]
    e50, e200 = talib.EMA(c, 50).iloc[-1], talib.EMA(c, 200).iloc[-1]
    return {"preco": float(c.iloc[-1]), "ema50": float(e50), "ema200": float(e200),
            "alta": bool(c.iloc[-1] > e200 and e50 > e200)}


def consultar(par: str) -> dict:
    ex = ccxt.binance()
    ex.load_markets()
    if par not in ex.markets:
        raise SystemExit(f"Par {par} nao existe na Binance spot.")
    h1 = tendencia(velas(ex, par, "1h", 300))
    m15 = velas(ex, par, "15m", 120)
    rsi = talib.RSI(m15["c"], 14)
    _, _, bb_inf = talib.BBANDS(m15["c"], 20, 2, 2)
    respirada = bool(rsi.iloc[-2] < 35 <= rsi.iloc[-1])
    perto_banda = bool(m15["l"].tail(3).min() <= bb_inf.iloc[-1] * 1.005)
    volume_ok = bool(m15["v"].iloc[-1] > m15["v"].tail(30).mean())
    btc = tendencia(velas(ex, "BTC/BRL", "1h", 300))
    try:
        fng = int(requests.get("https://api.alternative.me/fng/", timeout=10).json()["data"][0]["value"])
    except Exception:
        fng = None
    diario = velas(ex, par, "1d", 400)["c"]

    regras = [
        ("Tendência de 1 hora em alta", h1["alta"],
         f"preço {h1['preco']:.6g}, média 50 {h1['ema50']:.6g}, média 200 {h1['ema200']:.6g}"),
        ("Bitcoin em alta (mercado geral)", btc["alta"],
         f"BTC {btc['preco']:,.0f}".replace(",", ".") + f"; média 200 {btc['ema200']:,.0f}".replace(",", ".")),
        ("RSI saindo de baixo de 35 (respirada)", respirada, f"RSI 15 min agora {float(rsi.iloc[-1]):.1f}"),
        ("Preço perto da banda de baixo", perto_banda, f"banda {float(bb_inf.iloc[-1]):.6g}"),
        ("Volume acima da média", volume_ok, "última vela de 15 min contra as 30 anteriores"),
        ("Mercado sem euforia", fng is None or fng < FNG_MAX, f"Fear & Greed {fng if fng is not None else 'sem dado'}"),
    ]
    compraria = all(ok for _, ok, _ in regras)
    variacao = {f"{n}d": round(float(diario.iloc[-1] / diario.iloc[-1 - n] - 1) * 100, 2)
                for n in (7, 30, 90, 365) if len(diario) > n}
    return {
        "par": par, "consultado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "preco": h1["preco"], "variacao": variacao, "compraria": compraria,
        "regras": [{"regra": n, "ok": ok, "detalhe": d} for n, ok, d in regras],
        "aviso": "É o que as regras do robô dizem agora, não uma previsão nem recomendação.",
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    r = consultar(sys.argv[1].upper())
    if "--json" in sys.argv:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(f"{r['par']}  preço {r['preco']:.6g}  variação {r['variacao']}")
        for x in r["regras"]:
            print(f"  [{'OK' if x['ok'] else '--'}] {x['regra']}: {x['detalhe']}")
        print(f"\nO robô {'COMPRARIA' if r['compraria'] else 'NÃO compraria'} agora. {r['aviso']}")

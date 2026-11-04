r"""
Qualidade da execucao: o teste ao vivo compra e vende no preco que o backtest supoe?
(alerta de 29/10/2026 em docs/hipoteses-testadas.md)

Para cada operacao do teste ao vivo (tradesv3.dryrun.sqlite):
  - compra: compara o preco pago com a ABERTURA da vela de 15 min em que a ordem foi feita
    (o backtest compra exatamente nesse preco);
  - venda: compara com o preco da vela no momento da venda (para stop, o preco do stop).
  Diferenca positiva = o teste ao vivo pagou MAIS caro (compra) ou vendeu MAIS barato (venda).
E mede o spread agora (melhor oferta de venda / melhor oferta de compra) nos pares do robo.

Uso: .\.venv\Scripts\python.exe scripts\qualidade_execucao.py [--json]
"""
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import ccxt
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
CONFIG = json.loads((RAIZ / "user_data" / "config.json").read_text(encoding="utf-8"))


def vela_15m(ex, par, quando: datetime):
    inicio = int(quando.replace(minute=quando.minute - quando.minute % 15, second=0, microsecond=0).timestamp() * 1000)
    k = ex.fetch_ohlcv(par, "15m", since=inicio, limit=1)
    return k[0] if k else None


def operacoes(ex):
    banco = RAIZ / "tradesv3.dryrun.sqlite"
    if not banco.exists():
        return []
    con = sqlite3.connect(f"file:{banco}?mode=ro", uri=True)
    linhas = con.execute("select pair, open_date, open_rate, close_date, close_rate, exit_reason, stop_loss "
                         "from trades order by open_date").fetchall()
    saida = []
    for par, abre, p_compra, fecha, p_venda, motivo, stop in linhas:
        d_abre = pd.Timestamp(abre, tz="UTC").to_pydatetime()
        v = vela_15m(ex, par, d_abre)
        item = {"par": par, "compra_em": abre[:16], "preco_compra": p_compra,
                "abertura_vela": v[1] if v else None,
                "dif_compra_pct": round((p_compra / v[1] - 1) * 100, 3) if v else None}
        if fecha and p_venda:
            d_fecha = pd.Timestamp(fecha, tz="UTC").to_pydatetime()
            vf = vela_15m(ex, par, d_fecha)
            ref = stop if motivo and "stop" in motivo and stop else (vf[4] if vf else None)
            item.update({"venda_em": fecha[:16], "preco_venda": p_venda, "saida": motivo, "referencia_venda": ref,
                         "dif_venda_pct": round((ref / p_venda - 1) * 100, 3) if ref else None})
        saida.append(item)
    return saida


def spreads(ex):
    r = {}
    for par in CONFIG["exchange"]["pair_whitelist"]:
        try:
            ob = ex.fetch_order_book(par, 5)
            r[par] = round((ob["asks"][0][0] / ob["bids"][0][0] - 1) * 100, 3)
        except Exception:
            r[par] = None
    return r


if __name__ == "__main__":
    ex = ccxt.binance()
    ops, spr = operacoes(ex), spreads(ex)
    resultado = {"medido_em": datetime.now(timezone.utc).isoformat(timespec="seconds"), "operacoes": ops, "spread_pct": spr}
    compras = [o["dif_compra_pct"] for o in ops if o.get("dif_compra_pct") is not None]
    vendas = [o["dif_venda_pct"] for o in ops if o.get("dif_venda_pct") is not None]
    resultado["media_dif_compra_pct"] = round(sum(compras) / len(compras), 3) if compras else None
    resultado["media_dif_venda_pct"] = round(sum(vendas) / len(vendas), 3) if vendas else None
    validos = [v for v in spr.values() if v is not None]
    resultado["spread_medio_pct"] = round(sum(validos) / len(validos), 3) if validos else None
    if "--json" in sys.argv:
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
    else:
        for o in ops:
            print(f"{o['par']:9} compra {o['compra_em']} dif {o['dif_compra_pct']:+.3f}%"
                  + (f" | venda {o['venda_em']} ({o['saida']}) dif {o['dif_venda_pct']:+.3f}%" if o.get("dif_venda_pct") is not None else ""))
        print(f"\nMedia: compra {resultado['media_dif_compra_pct']}% | venda {resultado['media_dif_venda_pct']}% "
              f"(positivo = pior que o backtest)")
        print("Spread agora (%):", {k.split('/')[0]: v for k, v in spr.items()}, "| medio", resultado["spread_medio_pct"])

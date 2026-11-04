# -*- coding: utf-8 -*-
r"""Radar de moedas - API publica da Binance (sem chave). So leitura.

Nota de momento (0 a 100):
  40% rank do retorno 30d + 30% rank do retorno 90d   (forca recente)
  +15 se preco acima da media de 200 dias (tendencia de alta)
  +10 se volume medio 7d > volume medio 30d (interesse crescendo)
  -ate 20 de penalidade se volatilidade 30d (anualizada) passa de 100%
Uso: .\.venv\Scripts\python.exe scripts\radar_moedas.py
"""
import json, os, re, sys, time, math
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import ccxt

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(RAIZ, "user_data", "radar_moedas.json")
STABLES = {"USDT","USDC","BUSD","FDUSD","TUSD","USDP","DAI","USDD","EUR","EURI","AEUR","GBP","TRY","BRL",
           "BFUSD","USD1","XUSD","RLUSD","PYUSD","UST","USTC","USDE","SUSD","PAXG","XAUT","BKRW","IDRT","VAI","U"}
# acoes/ETFs tokenizados (sufixo B) - nao sao cripto
TOKENIZADOS = {"MSTRB","TSLAB","SPCXB","CRCLB","NVDAB","INTCB","SNDKB","SKHYB","SOXLB","COINB","AAPLB","GOOGLB","AMZNB","METAB","QQQB","SPYB"}
DIAS = 220

def eh_alavancado(base):
    return bool(re.search(r"(UP|DOWN|BULL|BEAR)$", base)) and base not in ("JUP","SUP")

def candidatos(ex):
    ex.load_markets()
    tk = ex.fetch_tickers()
    brl, usdt = [], []
    for sym, m in ex.markets.items():
        if not (m.get("spot") and m.get("active")):
            continue
        base, quote = m["base"], m["quote"]
        if base in STABLES or base in TOKENIZADOS or (len(base) >= 5 and base.endswith("B")) or eh_alavancado(base):
            continue
        t = tk.get(sym) or {}
        qv = t.get("quoteVolume") or 0
        if quote == "BRL" and qv >= 50_000:
            brl.append((sym, base, qv))
        elif quote == "USDT" and qv >= 1_000_000:
            usdt.append((sym, base, qv))
    usdt.sort(key=lambda x: -x[2])
    return brl, usdt[:60]

def media(v): return sum(v) / len(v) if v else 0.0

def metricas(ex, sym):
    o = ex.fetch_ohlcv(sym, "1d", limit=DIAS)
    if len(o) < 95:
        raise ValueError("poucos candles (%d)" % len(o))
    c = [x[4] for x in o]; v = [x[5] * x[4] for x in o]  # volume em moeda de cotacao
    c0 = c[-1]
    ret = lambda n: (c0 / c[-1 - n] - 1) * 100
    ma200 = media(c[-200:]) if len(c) >= 200 else None
    ma50 = media(c[-50:])
    rets = [math.log(c[i] / c[i-1]) for i in range(len(c) - 30, len(c))]
    mu = media(rets)
    vol30 = math.sqrt(sum((r - mu) ** 2 for r in rets) / (len(rets) - 1)) * math.sqrt(365) * 100
    topo = max(x[2] for x in o[-90:])
    v7, v30 = media(v[-7:]), media(v[-30:])
    return dict(preco=c0, ret_7d=ret(7), ret_30d=ret(30), ret_90d=ret(90),
                vol_cresc=(v7 / v30 - 1) * 100 if v30 else 0.0,
                acima_ma200=(c0 > ma200) if ma200 else None, acima_ma50=c0 > ma50,
                volat_30d=vol30, queda_topo_90d=(c0 / topo - 1) * 100)

def rank_pct(valores):
    ordem = sorted(range(len(valores)), key=lambda i: valores[i])
    r = [0.0] * len(valores)
    for pos, i in enumerate(ordem):
        r[i] = pos / max(len(valores) - 1, 1)
    return r

def main():
    t0 = time.time()
    ex = ccxt.binance({"enableRateLimit": True, "timeout": 15000})
    brl, usdt = candidatos(ex)
    bases_brl = {b for _, b, _ in brl}
    alvos = {}
    for sym, base, qv in usdt:
        alvos[base] = sym  # preferir USDT (mais liquido e historico longo)
    for sym, base, qv in brl:
        alvos.setdefault(base, sym)
    print("Pares a analisar: %d (BRL liquidos: %d, USDT top: %d)" % (len(alvos), len(brl), len(usdt)))

    def tarefa(item):
        base, sym = item
        for tent in range(2):
            try:
                m = metricas(ex, sym); m.update(par=sym, base=base); return m
            except Exception as e:
                err = str(e)[:80]; time.sleep(1)
        print("  falhou %s: %s" % (sym, err)); return None
    with ThreadPoolExecutor(max_workers=4) as pool:
        res = [r for r in pool.map(tarefa, alvos.items()) if r]

    r30 = rank_pct([r["ret_30d"] for r in res]); r90 = rank_pct([r["ret_90d"] for r in res])
    agora = datetime.now(timezone.utc).isoformat()
    saida = []
    for r, a, b in zip(res, r30, r90):
        nota = 40 * a + 30 * b
        nota += 15 if r["acima_ma200"] else 0
        nota += 10 if r["vol_cresc"] > 0 else 0
        nota -= min(20, max(0, (r["volat_30d"] - 100) / 5))
        saida.append(dict(par=r["par"], preco=round(r["preco"], 8), ret_7d=round(r["ret_7d"], 2),
            ret_30d=round(r["ret_30d"], 2), ret_90d=round(r["ret_90d"], 2), vol_cresc=round(r["vol_cresc"], 1),
            acima_ma200=r["acima_ma200"], acima_ma50=bool(r["acima_ma50"]), volat_30d=round(r["volat_30d"], 1),
            queda_topo_90d=round(r["queda_topo_90d"], 2), nota=round(max(0, min(100, nota)), 1),
            tem_par_brl=r["base"] in bases_brl, gerado_em=agora))
    saida.sort(key=lambda x: -x["nota"])
    with open(SAIDA, "w", encoding="utf-8") as f:
        json.dump(saida, f, ensure_ascii=False, indent=1)
    print("%-12s %6s %8s %8s %8s %8s %5s %5s %7s %7s %s" % ("par","nota","7d%","30d%","90d%","volCr%","MA200","MA50","vol30","queda","BRL"))
    for s in saida:
        print("%-12s %6.1f %8.1f %8.1f %8.1f %8.1f %5s %5s %7.0f %7.1f %s" % (s["par"], s["nota"], s["ret_7d"], s["ret_30d"],
            s["ret_90d"], s["vol_cresc"], "sim" if s["acima_ma200"] else "nao", "sim" if s["acima_ma50"] else "nao",
            s["volat_30d"], s["queda_topo_90d"], "sim" if s["tem_par_brl"] else "-"))
    print("\n%d moedas, %.0fs, gravado em %s" % (len(saida), time.time() - t0, SAIDA))

if __name__ == "__main__":
    main()

r"""
Simulador da estrategia de ROTACAO com PROTECAO DE CAPITAL (docs/aulas/07-rotacao-e-protecao.md).

Regra, decidida so com o que se sabia no dia (executa na abertura do dia seguinte):
  - a cada N dias, nota de momento das moedas = media do ranking de alta de 30 e 90 dias;
    so entram moedas acima da propria media de 200 dias (tendencia);
  - filtro de mercado opcional: com o BTC abaixo da media de 200 dias, fica em real;
  - compra as TOP moedas, partes iguais;
  - stop movel por moeda: caiu X% do topo desde a compra -> vende e fica em real ate a proxima troca;
  - protecao de capital (CPPI): piso = P% do capital inicial; exposicao = M x (saldo - piso) / saldo.
    Se o saldo encosta no piso, vende tudo.
Taxa 0,1% + 0,1% de escorregamento por ordem.

Testa a regra comecando em cada data possivel (de 5 em 5 dias) e compara com segurar
as 12 moedas e com segurar so BTC, comecando no mesmo dia.

Uso: .\.venv\Scripts\python.exe scripts\simula_rotacao.py
"""
import itertools
import json
from pathlib import Path

import ccxt
import numpy as np
import pandas as pd

PARES = ["BTC/BRL", "ETH/BRL", "SOL/BRL", "XRP/BRL", "BNB/BRL", "ADA/BRL", "LINK/BRL",
         "AVAX/BRL", "NEAR/BRL", "SUI/BRL", "LTC/BRL", "PEPE/BRL"]
CUSTO = 0.002          # taxa + escorregamento por ordem
CAPITAL = 30.0
INICIO_DADOS = "2024-08-01"
PRIMEIRA_PARTIDA = "2025-04-01"
CACHE = Path(__file__).resolve().parent.parent / "user_data" / "diario_brl.parquet"


def carregar() -> tuple[pd.DataFrame, pd.DataFrame]:
    if CACHE.exists() and (pd.Timestamp.now() - pd.Timestamp(CACHE.stat().st_mtime, unit="s")).total_seconds() < 6 * 3600:
        tudo = pd.read_parquet(CACHE)
    else:
        ex = ccxt.binance()
        partes = []
        for par in PARES:
            since = int(pd.Timestamp(INICIO_DADOS, tz="UTC").timestamp() * 1000)
            linhas = []
            while True:
                lote = ex.fetch_ohlcv(par, "1d", since=since, limit=1000)
                if not lote:
                    break
                linhas += lote
                since = lote[-1][0] + 86400000
                if len(lote) < 1000:
                    break
            d = pd.DataFrame(linhas, columns=["t", "o", "h", "l", "c", "v"])
            d["par"] = par
            partes.append(d)
        tudo = pd.concat(partes)
        tudo["t"] = pd.to_datetime(tudo["t"], unit="ms", utc=True).dt.normalize()
        tudo.to_parquet(CACHE)
    abre = tudo.pivot(index="t", columns="par", values="o").sort_index()
    fecha = tudo.pivot(index="t", columns="par", values="c").sort_index()
    fecha = fecha.iloc[:-1]  # o dia de hoje ainda nao fechou
    return abre.loc[fecha.index], fecha


def simular(abre, fecha, inicio, top=3, troca=7, filtro_btc=True, stop=0.15, piso=0.9, mult=4.0):
    ma200 = fecha.rolling(200, min_periods=200).mean()
    r30, r90 = fecha / fecha.shift(30) - 1, fecha / fecha.shift(90) - 1
    dias = fecha.index[fecha.index >= inicio]
    caixa, qtd, topo = CAPITAL, {}, {}
    piso_rs = CAPITAL * piso if piso else 0.0
    saldos, ultimo_rebal, ordens, travado = [], None, 0, False
    pendente = None  # (alvos {par: valor}) a executar na abertura seguinte

    for i, dia in enumerate(dias):
        px_ab = abre.loc[dia]
        # 1) executa a decisao de ontem na abertura de hoje
        if pendente is not None:
            saldo_ab = caixa + sum(q * px_ab[p] for p, q in qtd.items())
            for p in list(qtd):
                alvo = pendente.get(p, 0.0)
                atual = qtd[p] * px_ab[p]
                if alvo < atual * 0.9:  # vende o excesso
                    vender = atual - alvo
                    caixa += vender * (1 - CUSTO); qtd[p] -= vender / px_ab[p]; ordens += 1
                    if qtd[p] * px_ab[p] < 0.5:
                        caixa += qtd[p] * px_ab[p] * (1 - CUSTO); del qtd[p]; topo.pop(p, None)
            for p, alvo in pendente.items():
                atual = qtd.get(p, 0.0) * px_ab[p]
                if alvo > atual * 1.1 + 0.5 and caixa > 1:
                    comprar = min(alvo - atual, caixa)
                    qtd[p] = qtd.get(p, 0.0) + comprar * (1 - CUSTO) / px_ab[p]; caixa -= comprar; ordens += 1
                    topo[p] = max(topo.get(p, 0), px_ab[p])
            pendente = None

        # 2) fecha o dia: saldo, stops, protecao
        px = fecha.loc[dia]
        for p in qtd:
            topo[p] = max(topo.get(p, px[p]), px[p])
        saldo = caixa + sum(q * px[p] for p, q in qtd.items())
        saldos.append(saldo)
        alvos = {p: q * px[p] for p, q in qtd.items()}
        mudou = False
        if stop:
            for p in list(alvos):
                if px[p] < topo[p] * (1 - stop):
                    alvos[p] = 0.0; mudou = True
        if piso and saldo <= piso_rs * 1.02 and qtd:
            alvos = {p: 0.0 for p in alvos}; mudou = True; travado = True

        # 3) troca periodica
        if ultimo_rebal is None or (dia - ultimo_rebal).days >= troca:
            ultimo_rebal = dia
            mercado_ok = (not filtro_btc) or (px["BTC/BRL"] > ma200.loc[dia, "BTC/BRL"])
            exposicao = 1.0
            if piso:
                exposicao = float(np.clip(mult * (saldo - piso_rs) / saldo, 0, 1))
            elegiveis = [p for p in PARES if pd.notna(ma200.loc[dia, p]) and px[p] > ma200.loc[dia, p]
                         and pd.notna(r90.loc[dia, p])]
            alvos = {p: 0.0 for p in qtd}
            if mercado_ok and elegiveis and exposicao > 0.05:
                nota = (r30.loc[dia, elegiveis].rank() + r90.loc[dia, elegiveis].rank()) / 2
                escolhidas = list(nota.sort_values(ascending=False).index[:top])
                for p in escolhidas:
                    alvos[p] = saldo * exposicao / len(escolhidas)
            mudou = True
        if mudou and i + 1 < len(dias):
            pendente = alvos

    s = pd.Series(saldos, index=dias)
    return {"final": float(s.iloc[-1]), "minimo": float(s.min()),
            "queda_max": float((s / s.cummax() - 1).min() * 100), "ordens": ordens, "serie": s}


def segurar(fecha, abre, inicio, pares):
    d0 = fecha.index[fecha.index >= inicio][0]
    rel = fecha.loc[d0:, pares] / abre.loc[d0, pares]
    s = CAPITAL * (1 - CUSTO) ** 2 * rel.mean(axis=1)
    return {"final": float(s.iloc[-1]), "minimo": float(s.min()),
            "queda_max": float((s / s.cummax() - 1).min() * 100)}


def avaliar(abre, fecha, **param):
    partidas = fecha.index[(fecha.index >= PRIMEIRA_PARTIDA) & (fecha.index <= fecha.index[-30])][::5]
    finais, minimos, quedas = [], [], []
    for d in partidas:
        r = simular(abre, fecha, d, **param)
        finais.append(r["final"]); minimos.append(r["minimo"]); quedas.append(r["queda_max"])
    f = np.array(finais)
    return {"partidas": len(f), "mediana": float(np.median(f)), "pior": float(f.min()), "melhor": float(f.max()),
            "perdeu_pct": float((f < CAPITAL).mean() * 100),
            "abaixo_capital_pct": float((np.array(minimos) < CAPITAL * 0.97).mean() * 100),
            "pior_minimo": float(min(minimos)), "queda_max_mediana": float(np.median(quedas))}


if __name__ == "__main__":
    abre, fecha = carregar()
    print(f"Dados: {fecha.index[0].date()} a {fecha.index[-1].date()}")

    # referencias: segurar, comecando em cada data
    partidas = fecha.index[(fecha.index >= PRIMEIRA_PARTIDA) & (fecha.index <= fecha.index[-30])][::5]
    for nome, pares in (("Segurar as 12", PARES), ("Segurar BTC", ["BTC/BRL"])):
        r = [segurar(fecha, abre, d, pares) for d in partidas]
        f = np.array([x["final"] for x in r])
        print(f"{nome:42} mediana R$ {np.median(f):6.2f} | pior R$ {f.min():6.2f} | melhor R$ {f.max():6.2f} | "
              f"perdeu em {(f < CAPITAL).mean()*100:4.0f}% das partidas | pior saldo no caminho R$ {min(x['minimo'] for x in r):6.2f}")

    variantes = {
        "A) radar puro (top3, mensal, sem protecao)": dict(top=3, troca=30, filtro_btc=False, stop=None, piso=None),
        "B) radar semanal + stop 15%": dict(top=3, troca=7, filtro_btc=False, stop=0.15, piso=None),
        "C) B + filtro BTC": dict(top=3, troca=7, filtro_btc=True, stop=0.15, piso=None),
        "D) C + piso 90% (mult 4)": dict(top=3, troca=7, filtro_btc=True, stop=0.15, piso=0.90, mult=4),
        "E) C + piso 85% (mult 4)": dict(top=3, troca=7, filtro_btc=True, stop=0.15, piso=0.85, mult=4),
        "F) B + piso 90% (mult 5), sem filtro BTC": dict(top=3, troca=7, filtro_btc=False, stop=0.15, piso=0.90, mult=5),
        "G) top2 semanal + stop 12% + piso 90%": dict(top=2, troca=7, filtro_btc=True, stop=0.12, piso=0.90, mult=4),
    }
    resultados = {}
    for nome, p in variantes.items():
        r = avaliar(abre, fecha, **p)
        resultados[nome] = r
        print(f"{nome:42} mediana R$ {r['mediana']:6.2f} | pior R$ {r['pior']:6.2f} | melhor R$ {r['melhor']:6.2f} | "
              f"perdeu em {r['perdeu_pct']:4.0f}% das partidas | pior saldo no caminho R$ {r['pior_minimo']:6.2f}")

    print("\nComecando em 01/06/2026:")
    for nome, p in variantes.items():
        r = simular(abre, fecha, pd.Timestamp("2026-06-01", tz="UTC"), **p)
        print(f"  {nome:42} R$ 30 -> R$ {r['final']:6.2f} (pior momento R$ {r['minimo']:.2f}, {r['ordens']} ordens)")
    for nome, pares in (("Segurar as 12", PARES), ("Segurar BTC", ["BTC/BRL"])):
        r = segurar(fecha, abre, pd.Timestamp("2026-06-01", tz="UTC"), pares)
        print(f"  {nome:42} R$ 30 -> R$ {r['final']:6.2f} (pior momento R$ {r['minimo']:.2f})")

    saida = Path(__file__).resolve().parent.parent / "user_data" / "simulacao_rotacao.json"
    saida.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")

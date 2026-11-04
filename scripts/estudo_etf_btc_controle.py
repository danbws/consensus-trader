r"""
Controle do estudo dos ETFs de bitcoin (scripts/estudo_etf_btc.py): a regra escolhida ganhou no periodo 2
porque o fluxo avisa algo, ou so porque ficou fora do mercado parte do tempo numa queda?
  - sorteio: mesmo tempo fora do mercado, mesmo numero de trocas, dias ao acaso (1.000 sorteios);
  - regra so de preco: comprado quando o BTC fecha acima da media de 50 dias (nao usa fluxo nenhum).
Uso: .\.venv\Scripts\python.exe scripts\estudo_etf_btc_controle.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estudo_etf_btc as e  # noqa: E402

fl, px = e.fluxos(), e.precos_btc()
dias = px.index[px.index >= "2024-01-11"]
px = px[dias]
ESCOLHIDA = dict(janela=10, limite=1000, tipo="evitar_saidas")
pos = e.sinal(fl, dias, ESCOLHIDA["janela"], ESCOLHIDA["limite"], ESCOLHIDA["tipo"])

for nome, (ini, fim) in (("P1", e.P1), ("P2", e.P2)):
    real = e.rodar(px, pos, ini, fim, 1)
    p = pos.shift(2).fillna(0)[(pos.index >= ini) & (pos.index <= fim)]
    # sorteio de blocos: mesmos tamanhos de periodos dentro/fora, em ordem aleatoria (mantem tempo e trocas)
    blocos, atual, n = [], p.iloc[0], 0
    for v in p:
        if v == atual:
            n += 1
        else:
            blocos.append((atual, n))
            atual, n = v, 1
    blocos.append((atual, n))
    rng = np.random.default_rng(42)
    sorteios = []
    for _ in range(1000):
        ordem = rng.permutation(len(blocos))
        serie = np.concatenate([[blocos[i][0]] * blocos[i][1] for i in ordem])
        s = pd.Series(serie, index=p.index).reindex(pos.index).fillna(0).shift(-2).fillna(0)
        sorteios.append(e.rodar(px, s, ini, fim, 1)[0])
    sorteios = np.array(sorteios)
    media50 = (px > px.rolling(50).mean()).astype(float)
    m50 = e.rodar(px, media50, ini, fim, 1)
    bh = e.segurar(px, ini, fim)
    print(f"{nome}: regra do fluxo {real[0]:6.1f}%/ano (fora {100 - real[2]:.0f}% do tempo) | "
          f"sorteio com o mesmo tempo fora: mediana {np.median(sorteios):6.1f}%, a regra ganha de "
          f"{(sorteios < real[0]).mean() * 100:.0f}% dos sorteios | media de 50 dias {m50[0]:6.1f}% | "
          f"comprar e segurar {bh[0]:6.1f}%")

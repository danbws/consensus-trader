r"""
Duas listas lado a lado (12/11/2026, pedido do Daniel): a carteira de consenso de hoje (16 gestores, acao em 2 ou mais)
contra a candidata do estudo (37 gestores, acao em 3 ou mais; scripts/estudo_mais_gestores.py).
As duas sao SIMULADAS aqui, sem ordem nenhuma: US$ 1.000 cada, a partir do mesmo dia, com a mesma regra do robo
(10 acoes em partes iguais, 5% de caixa, troca quando a lista muda e volta ao peso a cada 90 dias, custo 0,2%).
So dados novos contam: o que acontecer daqui para frente nenhum estudo viu. A rotina de aprendizado chama 1x por dia.

Uso: .\.venv\Scripts\python.exe scripts\listas_lado_a_lado.py   (atualiza e mostra o placar)
"""
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aprendizado_diario as ad  # noqa: E402
import estudo_consenso as ec  # noqa: E402
import estudo_mais_gestores as mg  # noqa: E402

ARQ = ad.PASTA / "lado_a_lado.json"
INICIAL, CAIXA_PCT, DIAS_EQUILIBRIO, CUSTO_LADO = 1000.0, 0.05, 90, 0.001
VERSOES = {"16": "16 gestores (a regra de hoje)", "37": "37 gestores (candidata)"}


def candidatas(relatorios: list[dict], min_gestores: int) -> list[str]:
    ultimos = {}
    for r in relatorios:
        if r["cik"] not in ultimos or r["periodo"] > ultimos[r["cik"]]["periodo"]:
            ultimos[r["cik"]] = r
    cont, pesos = {}, {}
    for r in ultimos.values():
        for t, p in ec.apostas_por_empresa(r, 3.0).items():
            cont[t] = cont.get(t, 0) + 1
            pesos.setdefault(t, []).append(p)
    lista = [t for t, n in cont.items() if n >= min_gestores]
    return sorted(lista, key=lambda t: (-cont[t], -np.mean(pesos[t])))


def ultimos_precos(simbolos: list[str]) -> dict:
    df = ad.barras(simbolos, str(date.today() - timedelta(days=12)))
    return {s: float(df[s].dropna().iloc[-1]) for s in df.columns if df[s].notna().any()}


def valor(c: dict, px: dict) -> float:
    return c["caixa"] + sum(q * px.get(s, c["ultimo_preco"].get(s, 0.0)) for s, q in c["acoes"].items())


def reequilibrar(c: dict, lista: list[str], px: dict, hoje: str):
    total = valor(c, px)
    alvo = total * (1 - CAIXA_PCT) / len(lista)
    antes = {s: q * px.get(s, 0.0) for s, q in c["acoes"].items()}
    depois = {s: alvo for s in lista}
    giro = sum(abs(depois.get(s, 0.0) - antes.get(s, 0.0)) for s in set(antes) | set(depois))
    total -= giro * CUSTO_LADO
    alvo = total * (1 - CAIXA_PCT) / len(lista)
    c["acoes"] = {s: alvo / px[s] for s in lista}
    c["caixa"] = total - alvo * len(lista)
    c["lista"], c["equilibrado_em"] = lista, hoje


def atualizar() -> dict:
    """Atualiza as duas carteiras simuladas; devolve o placar e as trocas do dia."""
    hoje = str(date.today())
    estado = ad.ler(ARQ, None)
    try:
        mg.baixar13f()  # so baixa relatorio novo dos 21 gestores a mais (os outros ja estao guardados)
    except Exception:
        pass
    originais, novos = ec.carregar13f(), mg.carregar_novos()
    cand = {"16": candidatas(originais, 2), "37": candidatas(originais + novos, 3)}
    px = ultimos_precos(sorted(set(cand["16"][:25]) | set(cand["37"][:25]) | {"SPY"} |
                               {s for c in (estado or {}).get("carteiras", {}).values() for s in c["acoes"]}))
    listas = {k: [t for t in v if t in px][:10] for k, v in cand.items()}
    trocas = {}
    if estado is None:
        estado = {"inicio": hoje, "spy_inicio": px["SPY"], "carteiras": {}, "historico": {}}
        for k in VERSOES:
            c = {"caixa": INICIAL, "acoes": {}, "lista": [], "ultimo_preco": {}}
            reequilibrar(c, listas[k], px, hoje)
            estado["carteiras"][k] = c
            trocas[k] = {"entrou": listas[k], "saiu": []}
    else:
        for k, c in estado["carteiras"].items():
            mudou = set(listas[k]) != set(c["lista"])
            dias = (date.today() - date.fromisoformat(c["equilibrado_em"])).days
            if mudou or dias >= DIAS_EQUILIBRIO:
                if mudou:
                    trocas[k] = {"entrou": sorted(set(listas[k]) - set(c["lista"])),
                                 "saiu": sorted(set(c["lista"]) - set(listas[k]))}
                reequilibrar(c, listas[k], px, hoje)
    for c in estado["carteiras"].values():
        c["ultimo_preco"].update({s: px[s] for s in c["acoes"] if s in px})
    placar = {k: round(valor(c, px), 2) for k, c in estado["carteiras"].items()}
    placar["spy"] = round(INICIAL * px["SPY"] / estado["spy_inicio"], 2)
    estado["historico"][hoje] = placar
    ad.gravar(ARQ, estado)
    return {"inicio": estado["inicio"], "placar": placar, "trocas": trocas,
            "listas": {k: c["lista"] for k, c in estado["carteiras"].items()}}


def texto(r: dict) -> str:
    p = r["placar"]
    ini = date.fromisoformat(r["inicio"]).strftime("%d/%m/%Y")
    linhas = [f"⚖️ <b>Listas lado a lado</b> (simuladas desde {ini}, US$ 1.000 cada)"]
    for k, nome in VERSOES.items():
        linhas.append(f"{nome}: US$ {p[k]:,.2f} ({(p[k] / INICIAL - 1) * 100:+.2f}%)")
    linhas.append(f"S&P 500: US$ {p['spy']:,.2f} ({(p['spy'] / INICIAL - 1) * 100:+.2f}%)")
    for k, t in r["trocas"].items():
        if t["saiu"]:
            linhas.append(f"Troca na lista de {k}: saiu {', '.join(t['saiu'])}; entrou {', '.join(t['entrou'])}")
    return "\n".join(linhas)


if __name__ == "__main__":
    ad.ENVIAR = False
    r = atualizar()
    print(texto(r))
    print({k: v for k, v in r["listas"].items()})

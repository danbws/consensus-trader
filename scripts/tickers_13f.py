r"""
Ticker de cada posicao do 13F (13/11/2026, scripts/estudo_sobrevivencia.py).

A ferramenta do 13F so acha o ticker pelo CUSIP na lista de empresas de HOJE. O que ela nao acha vinha sem ticker e
o robo ignorava: ~30% do peso das carteiras em 2017-18 e ~8% em 2026, incluindo empresas vivas grandes (Bank of
America, Brookfield). Aqui o que vier sem ticker e resolvido:
  1. pelo CUSIP na OpenFIGI (publica, sem chave), guardado em user_data/estudo_consenso/cusip_ticker.json;
  2. pelo nome, para as empresas que a OpenFIGI nao devolve com codigo americano (POR_NOME).
Posicao que continuar sem ticker (acao estrangeira, posicao pequena) segue ignorada, como antes.
"""
import json
import time
from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parent.parent
ARQ = RAIZ / "user_data" / "estudo_consenso" / "cusip_ticker.json"

# Empresas que chegaram a ter 2+ gestores com 3% ou mais no mesmo trimestre e que a OpenFIGI nao devolve
# (sairam da bolsa ou trocaram de nome). Codigo conferido com o historico de preco da Alpaca.
POR_NOME = {"ALLERGAN": "AGN", "ALTABA": "AABA", "UNITED TECHNOL": "UTX", "FIAT CHRYSLER": "FCAU",
            "DOWDUPONT": "DWDP", "TWENTY FIRST C": "FOXA", "PRICELINE": "BKNG", "FLEETCOR": "CPAY",
            "WALGREENS BOOT": "WBA", "QORVO": "QRVO", "TWITTER": "TWTR", "CONSOL ENERGY": "CEIX",
            "WARNER BROS DI": "WBD", "ELECTRONIC ARTS": "EA", "SEAGATE TECHNOL": "STX", "CANADIAN PAC": "CP",
            "ACTIVISION": "ATVI"}


def _mapa() -> dict:
    return json.loads(ARQ.read_text(encoding="utf-8")) if ARQ.exists() else {}


def resolver(relatorios: list[dict]) -> list[dict]:
    """Preenche o ticker que falta (sem rede). Relatorio no formato antigo, sem CUSIP, passa como esta."""
    mapa = _mapa()
    for r in relatorios:
        for p in r["posicoes"]:
            if p.get("ticker") or p.get("put_call"):
                continue
            p["ticker"] = mapa.get(p.get("cusip") or "")
            if not p["ticker"]:
                nome = (p.get("nome") or "").upper()
                p["ticker"] = next((t for k, t in POR_NOME.items() if nome.startswith(k)), None)
    return relatorios


def mapear_cusips(relatorios: list[dict]):
    """Procura na OpenFIGI os CUSIPs ainda sem ticker (10 por pedido, 25 pedidos por minuto sem chave)."""
    mapa = _mapa()
    falta = sorted({p["cusip"] for r in relatorios for p in r["posicoes"]
                    if not p.get("ticker") and not p.get("put_call") and p.get("cusip")
                    and (p.get("pct") or 0) >= 0.5} - set(mapa))
    for i in range(0, len(falta), 10):
        lote = falta[i:i + 10]
        for _ in range(5):
            r = httpx.post("https://api.openfigi.com/v3/mapping", timeout=60,
                           json=[{"idType": "ID_CUSIP", "idValue": c, "exchCode": "US"} for c in lote])
            if r.status_code != 429:
                break
            time.sleep(30)
        r.raise_for_status()
        for c, resp in zip(lote, r.json()):
            dados = resp.get("data") or []
            acoes = [d for d in dados if d.get("marketSector") == "Equity"] or dados
            mapa[c] = acoes[0]["ticker"].replace("/", ".") if acoes else None
        ARQ.parent.mkdir(parents=True, exist_ok=True)
        ARQ.write_text(json.dumps(mapa), encoding="utf-8")
        time.sleep(2.6)
    return len(falta)

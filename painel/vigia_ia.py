"""
De olho na Anthropic e na OpenAI na bolsa (19/11/2026, pedido do Daniel). So avisa; nao compra nada e nao muda a
carteira de consenso (ela so pega uma acao quando os gestores dos 13F tiverem; o 1o 13F depois da estreia da
Anthropic sai ate 15/02/2027).

Avisa no Telegram:
  - quando a empresa aparece na corretora (a OpenAI ainda nao abriu capital; ETFs com o nome dela nao contam);
  - no 1o negocio (estreia), comparando com o preco da oferta;
  - quando a acao sobe ou cai 5% ou mais no dia (uma vez por dia em cada direcao).
Preco: Alpaca, feed IEX (o gratuito, quase em tempo real).
"""
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

EMPRESAS = {
    "Anthropic": {"busca": "anthropic", "ipo": 83.0},  # oferta precificada em 18/11/2026 a US$ 83
    "OpenAI": {"busca": "openai", "ipo": None},        # pedido confidencial de abertura; estreia esperada em 2027
}
MOVIMENTO = 5.0      # % no dia que vale aviso
BUSCA_LISTA_S = 6 * 3600
NOVA_YORK = ZoneInfo("America/New_York")


def _cab(pasta: Path) -> dict | None:
    try:
        ch = json.loads((pasta / "alpaca.json").read_text(encoding="utf-8"))
        return {"APCA-API-KEY-ID": ch["key"], "APCA-API-SECRET-KEY": ch["secret"]}
    except Exception:
        return None


def achar_tickers(cab: dict, est: dict, agora: float) -> list[str]:
    """Procura na lista de acoes da corretora as empresas que ainda nao tem codigo. Devolve as novas."""
    faltam = [n for n in EMPRESAS if not est.get(n, {}).get("ticker")]
    if not faltam or agora - float(est.get("_lista_em") or 0) < BUSCA_LISTA_S:
        return []
    est["_lista_em"] = agora
    ativos = httpx.get("https://paper-api.alpaca.markets/v2/assets", headers=cab, timeout=90,
                       params={"status": "active", "asset_class": "us_equity"}).json()
    novas = []
    for n in faltam:
        b = EMPRESAS[n]["busca"]
        for a in ativos:
            nome = (a.get("name") or "").lower()
            if b in nome and "etf" not in nome and a.get("tradable"):
                est.setdefault(n, {}).update(ticker=a["symbol"], nome=a["name"], bolsa=a.get("exchange"))
                novas.append(n)
                break
    return novas


def cotacao(cab: dict, ticker: str) -> dict | None:
    d = httpx.get(f"https://data.alpaca.markets/v2/stocks/{ticker}/snapshot", headers=cab, timeout=30,
                  params={"feed": "iex"}).json()
    preco = ((d.get("latestTrade") or {}).get("p")) or ((d.get("dailyBar") or {}).get("c"))
    if not preco:
        return None
    return {"preco": float(preco), "anterior": float((d.get("prevDailyBar") or {}).get("c") or 0) or None,
            "dia": ((d.get("latestTrade") or {}).get("t") or "")[:10]}


def rodada(pasta: Path, est: dict, agora: float, usd, pct, e) -> list[str]:
    """Uma conferencia; `est` e o pedaco do estado do bot para este vigia. usd/pct/e: formatadores do bot."""
    cab = _cab(pasta)
    if not cab:
        return []
    msgs = []
    for n in achar_tickers(cab, est, agora):
        x = est[n]
        ipo = EMPRESAS[n]["ipo"]
        msgs.append(f"🆕 <b>{e(n)} está na bolsa</b>: {e(x['nome'])}, código <b>{e(x['ticker'])}</b> ({e(x.get('bolsa'))})"
                    + (f"\nPreço da oferta: {usd(ipo)}" if ipo else "")
                    + "\nO robô não compra: a carteira só muda quando os gestores dos 13F tiverem a ação.")
    hoje = datetime.now(NOVA_YORK).strftime("%Y-%m-%d")
    for n, cfg in EMPRESAS.items():
        x = est.get(n) or {}
        if not x.get("ticker"):
            continue
        try:
            c = cotacao(cab, x["ticker"])
        except Exception:
            continue
        if not c:
            continue
        x["ultimo"], x["ultimo_dia"] = c["preco"], c["dia"]
        if not x.get("estreia") and cfg["ipo"]:
            x["estreia"] = c["preco"]
            x["estreia_dia"] = c["dia"]
            msgs.append(f"🔔 <b>{e(n)} ({e(x['ticker'])}) estreou</b>\n1º preço: {usd(c['preco'])} · "
                        f"oferta {usd(cfg['ipo'])} ({pct((c['preco'] / cfg['ipo'] - 1) * 100)})\n"
                        "<i>Estreia costuma oscilar muito nos primeiros dias.</i>")
        base = c["anterior"] if c["anterior"] and c["dia"] != x.get("estreia_dia") else cfg["ipo"]
        if not base:
            continue
        mov = (c["preco"] / base - 1) * 100
        lado = "sobe" if mov > 0 else "cai"
        if abs(mov) >= MOVIMENTO and x.get(f"avisou_{lado}") != hoje:
            x[f"avisou_{lado}"] = hoje
            ref = "fechamento de ontem" if base == c["anterior"] else "preço da oferta"
            msgs.append(f"{'🚀' if mov > 0 else '📉'} <b>{e(n)} ({e(x['ticker'])}) {pct(mov)} hoje</b>\n"
                        f"Agora {usd(c['preco'])} · {ref} {usd(base)}"
                        + (f" · oferta {usd(cfg['ipo'])} ({pct((c['preco'] / cfg['ipo'] - 1) * 100)})" if cfg["ipo"] else ""))
        est[n] = x
    return msgs


def linhas_tela(est: dict, usd, pct, e) -> list[str]:
    """Bloco "De olho" da tela de Acoes EUA."""
    linhas = []
    for n, cfg in EMPRESAS.items():
        x = est.get(n) or {}
        if not x.get("ticker"):
            linhas.append(f"👀 {e(n)}: ainda fora da bolsa")
        elif not x.get("ultimo"):
            linhas.append(f"👀 {e(n)} ({e(x['ticker'])}): ainda sem negócio")
        else:
            ipo = f" · oferta {usd(cfg['ipo'])} ({pct((x['ultimo'] / cfg['ipo'] - 1) * 100)})" if cfg["ipo"] else ""
            linhas.append(f"👀 {e(n)} ({e(x['ticker'])}): {usd(x['ultimo'])}{ipo}")
    return linhas

r"""
Historico do patrimonio por tipo de investimento, para a visao "quanto ganhei" de qualquer periodo.

Um ponto por dia (o ultimo valor do dia vale), gravado de hora em hora pelo painel e ao abrir a tela:
  user_data/historico_patrimonio.json
    cripto            {"inicio", "capital", "dias": {data: valor em R$}}
    acoes[corretora]  {"inicio", "capital", "fora", "dias": {data: valor em US$}}  (uma serie por corretora)
    dolar             {data: PTAX de venda do Banco Central}
  user_data/aportes.json (opcional; preencha quando colocar dinheiro novo)
    [{"data": "2027-02-10", "tipo": "acoes", "valor": 500.0}]   valor na moeda do tipo

Ganho do periodo = valor no fim - valor no inicio - aportes no periodo. O capital inicial conta como aporte no
dia do inicio, entao "desde o inicio" = valor de hoje - tudo o que foi colocado.
O total junta tudo em reais pelo dolar de cada dia (inclui o efeito do cambio nas acoes).
"""
import json
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corretoras  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
USER_DATA = RAIZ / "user_data"
ARQ = USER_DATA / "historico_patrimonio.json"
ARQ_APORTES = USER_DATA / "aportes.json"
INICIO_CRIPTO, CAPITAL_CRIPTO = "2026-10-21", 50.0   # robo no simulado desde 21/10 com R$ 50
CAPITAL_ACOES = 1000.0                               # carteira de consenso (consenso_automatico.TAMANHO_INICIAL)
NOVA_YORK = ZoneInfo("America/New_York")


def ler(arq: Path, padrao):
    try:
        return json.loads(arq.read_text(encoding="utf-8"))
    except Exception:
        return padrao


def hoje() -> str:
    return date.today().isoformat()


# ------------------------------------------------------------------ dolar
def dolar(h: dict, dia: str) -> float:
    """PTAX de venda do dia (ou do ultimo dia util antes); busca no Banco Central o que faltar."""
    tab = h.setdefault("dolar", {})
    d = date.fromisoformat(dia)
    for i in range(10):
        k = (d - timedelta(days=i)).isoformat()
        if k in tab:
            return tab[k]
    ini = d - timedelta(days=15)
    url = ("https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarPeriodo("
           "dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)"
           f"?@dataInicial='{ini:%m-%d-%Y}'&@dataFinalCotacao='{d:%m-%d-%Y}'&$format=json")
    for v in httpx.get(url, timeout=30).json()["value"]:
        tab[v["dataHoraCotacao"][:10]] = float(v["cotacaoVenda"])
    for i in range(10):
        k = (d - timedelta(days=i)).isoformat()
        if k in tab:
            return tab[k]
    raise RuntimeError(f"Sem dólar PTAX perto de {dia}")


# ------------------------------------------------------------------ valores de hoje
def valor_cripto_hoje() -> float | None:
    g = ler(USER_DATA / "guarda_status.json", {})
    return float(g["patrimonio"]) if g.get("patrimonio") is not None else None


def valor_acoes_hoje(serie: dict, c) -> float | None:
    """Carteira de consenso = patrimonio da conta - o que esta fora dela (o saldo ficticio da conta de papel)."""
    conta = c.conta()
    if serie.get("fora") is None:
        cons = ler(corretoras.arq_estado_consenso(c.nome), {})
        if cons.get("caixa") is None:
            return None
        vale = sum(p["market_value"] for p in c.posicoes())
        serie["fora"] = round(conta["equity"] - vale - float(cons["caixa"]), 2)
    return round(conta["equity"] - serie["fora"], 2)


# ------------------------------------------------------------------ montar o passado (uma vez)
def reconstruir_cripto() -> dict:
    """Valor de cada dia = capital + lucro das operacoes fechadas ate aquele dia (banco do robo, so leitura)."""
    serie = {"inicio": INICIO_CRIPTO, "capital": CAPITAL_CRIPTO, "dias": {INICIO_CRIPTO: CAPITAL_CRIPTO}}
    real, sim = RAIZ / "tradesv3.sqlite", RAIZ / "tradesv3.dryrun.sqlite"
    banco = real if real.exists() and real.stat().st_size else sim
    lucro_dia = {}
    if banco.exists():
        con = sqlite3.connect(f"file:{banco.as_posix()}?mode=ro", uri=True)
        for fechou, lucro in con.execute("select close_date, close_profit_abs from trades where is_open = 0"):
            d = (datetime.fromisoformat(fechou) - timedelta(hours=3)).date().isoformat()
            lucro_dia[d] = lucro_dia.get(d, 0.0) + float(lucro or 0)
        con.close()
    d, acumulado = date.fromisoformat(INICIO_CRIPTO), 0.0
    while d.isoformat() < hoje():
        acumulado += lucro_dia.get(d.isoformat(), 0.0)
        serie["dias"][d.isoformat()] = round(CAPITAL_CRIPTO + acumulado, 2)
        d += timedelta(days=1)
    return serie


def reconstruir_acoes(c) -> dict:
    cons = ler(corretoras.arq_estado_consenso(c.nome), {})
    inicio = (cons.get("ligado_em") or hoje())[:10]
    serie = {"inicio": inicio, "capital": CAPITAL_ACOES, "fora": None, "dias": {inicio: CAPITAL_ACOES}}
    valor_acoes_hoje(serie, c)
    if c.nome == "alpaca" and serie["fora"] is not None:  # a Alpaca guarda o patrimonio de cada dia
        hist = c._req("GET", "/account/portfolio/history", params={"period": "3M", "timeframe": "1D"})
        for ts, eq in zip(hist.get("timestamp", []), hist.get("equity", [])):
            # a Alpaca carimba cada dia as 20h de Nova York do proprio pregao
            d = datetime.fromtimestamp(ts, NOVA_YORK).date().isoformat()
            if eq and inicio <= d < hoje():
                serie["dias"][d] = round(float(eq) - serie["fora"], 2)
    return serie


# ------------------------------------------------------------------ registrar
def registrar() -> dict:
    """Grava o ponto de hoje de cada tipo (e monta o passado na primeira vez). Devolve o historico."""
    h = ler(ARQ, {})
    if "cripto" not in h:
        h["cripto"] = reconstruir_cripto()
    v = valor_cripto_hoje()
    if v is not None:
        h["cripto"]["dias"][hoje()] = round(v, 2)
    c = corretoras.corretora_acoes("painel")
    try:
        if c.configurada():
            series = h.setdefault("acoes", {})
            if c.nome not in series:
                series[c.nome] = reconstruir_acoes(c)
            v = valor_acoes_hoje(series[c.nome], c)
            if v is not None:
                series[c.nome]["dias"][hoje()] = v
        h["acoes_em_uso"] = c.nome
    except Exception as erro:  # corretora fora do ar: fica o ultimo ponto gravado
        h["erro_acoes"] = str(erro)[:200]
    finally:
        c.fechar()
    try:
        dolar(h, hoje())
    except Exception:
        pass
    h["atualizado_em"] = datetime.now().isoformat(timespec="seconds")
    ARQ.write_text(json.dumps(h, ensure_ascii=False, indent=1), encoding="utf-8")
    return h


# ------------------------------------------------------------------ ganhos de um periodo
def _valor_ate(dias: dict, dia: str) -> float:
    """Ultimo valor ate o dia (inclusive); antes do inicio, 0."""
    ks = [k for k in dias if k <= dia]
    return dias[max(ks)] if ks else 0.0


def periodo(nome: str | None, de: str | None = None, ate: str | None = None) -> tuple[str, str]:
    h = date.today()
    if de and ate:
        return de, ate
    inicio = {"7d": h - timedelta(days=6), "30d": h - timedelta(days=29), "mes": h.replace(day=1),
              "ano": h.replace(month=1, day=1)}.get(nome or "tudo", date(2000, 1, 1))
    return inicio.isoformat(), h.isoformat()


def ganhos(h: dict, de: str, ate: str) -> dict:
    aportes = ler(ARQ_APORTES, [])
    serie_acoes = (h.get("acoes") or {}).get(h.get("acoes_em_uso", "alpaca"))
    tipos, entradas_brl, base_brl0 = [], [], 0.0  # para a curva de ganho acumulado
    vespera = (date.fromisoformat(de) - timedelta(days=1)).isoformat()
    for tipo, s, moeda, nome in (("cripto", h.get("cripto"), "BRL", "Cripto (simulado)"),
                                 ("acoes", serie_acoes, "USD", "Ações EUA (conta de papel)")):
        if not s:
            continue
        entrou = [{"data": s["inicio"], "valor": s["capital"]}] + [a for a in aportes if a.get("tipo") == tipo]
        no_periodo = [a for a in entrou if de <= a["data"] <= ate]
        ini, fim = _valor_ate(s["dias"], vespera), _valor_ate(s["dias"], ate)
        colocado = sum(a["valor"] for a in no_periodo)
        base = ini + colocado
        ganho = fim - ini - colocado
        cambio = (lambda d: dolar(h, d)) if moeda == "USD" else (lambda d: 1.0)
        ganho_brl = fim * cambio(ate) - ini * cambio(vespera) - sum(a["valor"] * cambio(a["data"]) for a in no_periodo)
        # parte do ganho em reais que veio so do dolar subir ou cair (o resto e das acoes)
        efeito_dolar = ganho_brl - ganho * cambio(ate)
        base_brl0 += ini * cambio(vespera)
        entradas_brl += [(a["data"], a["valor"] * cambio(a["data"])) for a in no_periodo]
        tipos.append({"tipo": tipo, "nome": nome, "moeda": moeda, "inicio_serie": s["inicio"],
                      "valor_inicio": round(ini, 2), "valor_fim": round(fim, 2), "aportes": round(colocado, 2),
                      "ganho": round(ganho, 2), "ganho_pct": round(ganho / base * 100, 2) if base else 0.0,
                      "valor_fim_brl": round(fim * cambio(ate), 2), "ganho_brl": round(ganho_brl, 2),
                      "efeito_dolar_brl": round(efeito_dolar, 2)})
    base_brl = sum(t["valor_fim_brl"] - t["ganho_brl"] for t in tipos)
    total = {"valor_fim_brl": round(sum(t["valor_fim_brl"] for t in tipos), 2),
             "ganho_brl": round(sum(t["ganho_brl"] for t in tipos), 2)}
    total["ganho_pct"] = round(total["ganho_brl"] / base_brl * 100, 2) if base_brl else 0.0
    # serie diaria para o grafico: patrimonio e ganho acumulado no periodo (o dinheiro colocado nao conta como ganho)
    dias = sorted({d for t in (h.get("cripto"), serie_acoes) if t for d in t["dias"] if de <= d <= ate})
    serie = []
    for d in dias:
        cr = _valor_ate(h["cripto"]["dias"], d) if h.get("cripto") else 0.0
        ac = _valor_ate(serie_acoes["dias"], d) if serie_acoes else 0.0
        total_d = cr + ac * (dolar(h, d) if ac else 1)
        colocado_d = sum(v for dt, v in entradas_brl if dt <= d)
        serie.append({"dia": d, "cripto": round(cr, 2), "acoes_usd": round(ac, 2), "total_brl": round(total_d, 2),
                      "ganho_brl": round(total_d - base_brl0 - colocado_d, 2)})
    return {"de": de, "ate": ate, "tipos": tipos, "total": total, "serie": serie,
            "dolar_hoje": h.get("dolar", {}).get(max(h.get("dolar", {"": 0}))) if h.get("dolar") else None,
            "atualizado_em": h.get("atualizado_em"), "simulado": True}


if __name__ == "__main__":
    hist = registrar()
    for p in ("7d", "30d", "tudo"):
        r = ganhos(hist, *periodo(p))
        print(p, json.dumps({"total": r["total"], "tipos": [(t["tipo"], t["ganho"], t["ganho_pct"], t["ganho_brl"]) for t in r["tipos"]]},
                            ensure_ascii=False))

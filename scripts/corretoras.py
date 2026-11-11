r"""
Corretoras de acoes do robo (planejamento-dinheiro-real.md, secoes 3 e 7): a mesma interface para a Alpaca
(conta de papel, onde o teste comecou) e a Interactive Brokers (onde o dinheiro real vai ficar).

Qual esta em uso: user_data/corretora.json  {"acoes": "alpaca" | "ibkr", "ibkr": {"porta": 4002}}
(gravado pela tela Configuracoes; sem o arquivo, Alpaca).

IBKR
  - O robo fala com o IB Gateway (ou o TWS) aberto NESTE computador, logado pelo dono da conta. Nenhuma senha da
    IBKR passa pelo robo: o login e o 2 fatores acontecem no proprio Gateway.
  - TRAVA: so conta de PAPEL. Aceita apenas as portas de papel (4002 Gateway, 7497 TWS) e confere que todas as
    contas do login comecam com "DU" (o prefixo das contas de papel da IBKR). Conta real e recusada e desconecta.
  - Cada execucao do robo e gravada em acoes-eua/trader/state/ibkr_execucoes.json (com a comissao), que e a fonte
    das vendas no relatorio de imposto. Dividendos e imposto retido vem do Flex Query, se configurado
    (user_data/ibkr_flex.json, token e numero da consulta, colados na tela Configuracoes).
"""
import asyncio
import json
import math
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

RAIZ = Path(__file__).resolve().parent.parent
USER_DATA = RAIZ / "user_data"
STATE = RAIZ / "acoes-eua" / "trader" / "state"
ARQ_CONFIG = USER_DATA / "corretora.json"

PORTAS_PAPEL_IBKR = {4002: "IB Gateway (papel)", 7497: "TWS (papel)"}
CLIENTE_IBKR = {"painel": 41, "consenso": 42, "imposto": 43, "teste": 44}
FLEX = "https://ndcdyn.interactivebrokers.com/AccountManagement/FlexWebService"


def ler_json(arq: Path, padrao=None):
    try:
        return json.loads(arq.read_text(encoding="utf-8"))
    except Exception:
        return padrao


def config() -> dict:
    c = ler_json(ARQ_CONFIG, {}) or {}
    return {"acoes": c.get("acoes", "alpaca"), "ibkr": {"porta": 4002, **(c.get("ibkr") or {})}}


def corretora_acoes(uso: str = "painel"):
    c = config()
    if c["acoes"] == "ibkr":
        return Ibkr(porta=int(c["ibkr"]["porta"]), uso=uso)
    return Alpaca()


def arq_estado_consenso(nome: str) -> Path:
    """Cada corretora tem a sua carteira de consenso (caixa e historico nao se misturam)."""
    return STATE / ("consenso.json" if nome == "alpaca" else f"consenso_{nome}.json")


# ===================================================================== Alpaca (papel)
class Alpaca:
    nome, nome_exibir = "alpaca", "Alpaca"
    URL = "https://paper-api.alpaca.markets/v2"  # so o endereco de papel: chave real nao funciona aqui

    def __init__(self, chaves: dict | None = None):
        self.chaves = chaves or ler_json(USER_DATA / "alpaca.json")

    def configurada(self) -> bool:
        return bool(self.chaves)

    def _req(self, metodo: str, rota: str, **kw):
        r = httpx.request(metodo, self.URL + rota, timeout=20, headers={
            "APCA-API-KEY-ID": self.chaves["key"], "APCA-API-SECRET-KEY": self.chaves["secret"]}, **kw)
        if r.status_code >= 400:
            raise RuntimeError(f"Alpaca {r.status_code}: {r.text[:200]}")
        return r.json() if r.text else {}

    def fechar(self):
        pass

    def conta(self) -> dict:
        c = self._req("GET", "/account")
        return {"equity": float(c["equity"]), "cash": float(c["cash"]), "moeda": c.get("currency", "USD"),
                "papel": True, "id": self.chaves["key"][-4:]}

    def posicoes(self) -> list[dict]:
        return [{"symbol": p["symbol"], "qty": float(p["qty"]), "avg_entry_price": float(p["avg_entry_price"]),
                 "current_price": float(p["current_price"]), "market_value": float(p["market_value"]),
                 "unrealized_pl": float(p["unrealized_pl"]), "unrealized_plpc": float(p["unrealized_plpc"]),
                 "change_today": float(p["change_today"]) if p.get("change_today") is not None else None}
                for p in self._req("GET", "/positions")]

    def ordens(self, limite: int = 20) -> list[dict]:
        return [{c: o.get(c) for c in ("symbol", "side", "type", "qty", "notional", "filled_qty", "filled_avg_price",
                                       "status", "submitted_at")}
                for o in self._req("GET", "/orders", params={"status": "all", "limit": limite, "direction": "desc"})]

    def bolsa_aberta(self) -> bool:
        return bool(self._req("GET", "/clock").get("is_open"))

    def negociavel(self, simbolo: str) -> bool:
        try:
            a = self._req("GET", f"/assets/{simbolo}")
            return bool(a.get("tradable") and a.get("fractionable"))
        except Exception:
            return False

    def vender_tudo(self, simbolo: str) -> dict:
        p = next((x for x in self.posicoes() if x["symbol"] == simbolo), None)
        self._req("DELETE", f"/positions/{simbolo}")
        for _ in range(30):  # espera executar
            time.sleep(2)
            if not any(x["symbol"] == simbolo for x in self.posicoes()):
                break
        return {"acao": simbolo, "lado": "venda", "valor": round(p["market_value"], 2) if p else 0.0}

    def vender_valor(self, simbolo: str, valor: float) -> dict:
        """Vende parte da posicao, em dolares (fracao): usado para devolver a acao ao peso igual."""
        self._req("POST", "/orders", json={"symbol": simbolo, "side": "sell", "notional": f"{valor:.2f}",
                                           "type": "market", "time_in_force": "day"})
        for _ in range(30):  # espera executar, para o dinheiro estar livre antes das compras
            time.sleep(2)
            if not any(o["symbol"] == simbolo and o["side"] == "sell" for o in self._req("GET", "/orders", params={"status": "open"})):
                break
        return {"acao": simbolo, "lado": "venda", "valor": round(valor, 2)}

    def comprar_valor(self, simbolo: str, valor: float) -> dict:
        self._req("POST", "/orders", json={"symbol": simbolo, "side": "buy", "notional": f"{valor:.2f}",
                                           "type": "market", "time_in_force": "day"})
        return {"acao": simbolo, "lado": "compra", "valor": round(valor, 2)}

    def atividades(self) -> list[dict]:
        """Compras, vendas e dividendos, no formato das 'activities' da Alpaca (o relatorio de imposto usa esse)."""
        todas, token = [], None
        while True:
            p = {"activity_types": "FILL,DIV,DIVNRA", "page_size": 100, "direction": "asc"}
            if token:
                p["page_token"] = token
            pagina = self._req("GET", "/account/activities", params=p)
            todas += pagina
            if len(pagina) < 100:
                return todas
            token = pagina[-1]["id"]


# ===================================================================== Interactive Brokers (papel)
def simbolo_ibkr(s: str) -> str:
    return s.replace(".", " ")  # BRK.B -> "BRK B"


def simbolo_nosso(s: str) -> str:
    return s.replace(" ", ".")


def mercado_aberto(liquid_hours: str, fuso: str, agora: datetime | None = None) -> bool:
    """liquidHours da IBKR: '20261030:0930-20261030:1600;20261031:CLOSED;...' no fuso do contrato."""
    tz = ZoneInfo({"US/Eastern": "America/New_York"}.get(fuso, fuso or "America/New_York"))
    agora = (agora or datetime.now(timezone.utc)).astimezone(tz)
    for trecho in (liquid_hours or "").split(";"):
        if "-" not in trecho or "CLOSED" in trecho:
            continue
        ini, fim = trecho.split("-")
        a = datetime.strptime(ini, "%Y%m%d:%H%M").replace(tzinfo=tz)
        b = datetime.strptime(fim, "%Y%m%d:%H%M").replace(tzinfo=tz)
        if a <= agora < b:
            return True
    return False


def quantidade_fracionada(valor: float, preco: float) -> float:
    """Quantidade para gastar ate `valor`, arredondada PARA BAIXO em 4 casas (nunca gasta mais que o combinado)."""
    if preco <= 0:
        return 0.0
    return math.floor(valor / preco * 10_000) / 10_000


def recusou_fracao(mensagens: list[str]) -> bool:
    t = " ".join(mensagens).lower()
    return "fraction" in t or "10243" in t


class ContaRealRecusada(RuntimeError):
    pass


class Ibkr:
    nome, nome_exibir = "ibkr", "Interactive Brokers"

    def __init__(self, porta: int = 4002, uso: str = "painel", ib=None, arq_execucoes: Path | None = None):
        if porta not in PORTAS_PAPEL_IBKR:
            raise ContaRealRecusada(f"Porta {porta} não é de conta de papel. Use 4002 (IB Gateway) ou 7497 (TWS).")
        self.porta, self.cliente = porta, CLIENTE_IBKR.get(uso, 49)
        self.ib = ib  # um IB() de teste pode ser injetado
        self.arq_execucoes = arq_execucoes or STATE / "ibkr_execucoes.json"

    # ------------------------------------------------------------- conexao
    def configurada(self) -> bool:
        return True

    def conectar(self):
        if self.ib is not None and self.ib.isConnected():
            return self.ib
        try:
            asyncio.get_event_loop()
        except RuntimeError:  # linha de execucao sem loop (painel): cria um
            asyncio.set_event_loop(asyncio.new_event_loop())
        if self.ib is None:
            from ib_async import IB
            self.ib = IB()
        try:
            self.ib.connect("127.0.0.1", self.porta, clientId=self.cliente, timeout=8)
        except Exception:
            raise RuntimeError(f"Não achei o {PORTAS_PAPEL_IBKR[self.porta]} aberto e logado neste computador. "
                               f"Abra o programa, faça o login em Paper Trading e confira a porta {self.porta} "
                               "em Configure > Settings > API.")
        contas = list(self.ib.managedAccounts())
        if not contas or not all(c.upper().startswith("DU") for c in contas):
            self.ib.disconnect()
            raise ContaRealRecusada("O login aberto no Gateway é de conta REAL. Este robô só opera a conta de "
                                    "papel da IBKR por enquanto: faça o login escolhendo Paper Trading.")
        self.conta_id = contas[0]
        return self.ib

    def fechar(self):
        if self.ib is not None and self.ib.isConnected():
            self.ib.disconnect()

    def _acao(self, simbolo: str):
        from ib_async import Stock
        return Stock(simbolo_ibkr(simbolo), "SMART", "USD")

    # ------------------------------------------------------------- leitura
    def conta(self) -> dict:
        ib = self.conectar()
        caixa = sum(float(v.value) for v in ib.accountValues()
                    if v.tag == "CashBalance" and v.currency == "USD" and v.account == self.conta_id)
        acoes = sum(p["market_value"] for p in self.posicoes())
        # patrimonio em dolar = acoes + caixa em dolar (a moeda base da conta pode ser real)
        return {"equity": round(caixa + acoes, 2), "cash": round(caixa, 2), "moeda": "USD", "papel": True,
                "id": self.conta_id[-4:]}

    def posicoes(self) -> list[dict]:
        ib = self.conectar()
        saida = []
        for p in ib.portfolio():
            if p.contract.secType != "STK" or not p.position:
                continue
            custo = p.averageCost * p.position
            saida.append({"symbol": simbolo_nosso(p.contract.symbol), "qty": float(p.position),
                          "avg_entry_price": float(p.averageCost), "current_price": float(p.marketPrice),
                          "market_value": float(p.marketValue), "unrealized_pl": float(p.unrealizedPNL),
                          "unrealized_plpc": float(p.unrealizedPNL) / custo if custo else 0.0, "change_today": None})
        return saida

    def ordens(self, limite: int = 20) -> list[dict]:
        execs = ler_json(self.arq_execucoes, []) or []
        return [{"symbol": e["symbol"], "side": e["side"], "type": "market", "qty": e["qty"], "notional": None,
                 "filled_qty": e["qty"], "filled_avg_price": e["price"], "status": "filled", "submitted_at": e["time"]}
                for e in reversed(execs[-limite:])]

    def bolsa_aberta(self) -> bool:
        ib = self.conectar()
        det = ib.reqContractDetails(self._acao("SPY"))
        return bool(det) and mercado_aberto(det[0].liquidHours, det[0].timeZoneId)

    def negociavel(self, simbolo: str) -> bool:
        try:
            return bool(self.conectar().qualifyContracts(self._acao(simbolo)))
        except Exception:
            return False

    def preco(self, simbolo: str) -> float:
        ib = self.conectar()
        c = self._acao(simbolo)
        ib.qualifyContracts(c)
        ib.reqMarketDataType(3)  # sem assinatura de cotacao, usa a atrasada (15 min): serve para dividir o valor
        t = ib.reqMktData(c, "", snapshot=True)
        for _ in range(20):
            ib.sleep(0.5)
            p = t.marketPrice()
            if p and p == p and p > 0:  # p == p descarta NaN
                return float(p)
        barras = ib.reqHistoricalData(c, "", "2 D", "1 day", "TRADES", True)
        if barras:
            return float(barras[-1].close)
        raise RuntimeError(f"Sem preço para {simbolo} na IBKR.")

    # ------------------------------------------------------------- ordens
    def _executar(self, simbolo: str, lado: str, qtd: float):
        from ib_async import MarketOrder
        ib = self.conectar()
        c = self._acao(simbolo)
        ib.qualifyContracts(c)
        trade = ib.placeOrder(c, MarketOrder(lado, qtd, tif="DAY"))
        for _ in range(60):
            ib.sleep(1)
            if trade.isDone():
                break
        ib.sleep(2)  # a comissao chega logo depois da execucao
        return trade, [f"{x.errorCode} {x.message}" for x in trade.log if x.message or x.errorCode]

    def _gravar(self, simbolo: str, trade) -> tuple[float, float]:
        execs = ler_json(self.arq_execucoes, []) or []
        qtd = valor = 0.0
        for f in trade.fills:
            com = abs(float(f.commissionReport.commission or 0)) if f.commissionReport else 0.0
            execs.append({"exec_id": f.execution.execId, "order_id": str(trade.order.orderId), "symbol": simbolo,
                          "side": "buy" if f.execution.side == "BOT" else "sell", "qty": float(f.execution.shares),
                          "price": float(f.execution.price), "comissao": com,
                          "time": f.execution.time.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")})
            qtd += float(f.execution.shares)
            valor += float(f.execution.shares) * float(f.execution.price)
        self.arq_execucoes.parent.mkdir(parents=True, exist_ok=True)
        self.arq_execucoes.write_text(json.dumps(execs, indent=1), encoding="utf-8")
        return qtd, valor

    def vender_tudo(self, simbolo: str) -> dict:
        p = next((x for x in self.posicoes() if x["symbol"] == simbolo), None)
        if not p:
            return {"acao": simbolo, "lado": "venda", "valor": 0.0}
        trade, erros = self._executar(simbolo, "SELL", p["qty"])
        _, valor = self._gravar(simbolo, trade)
        if trade.orderStatus.status != "Filled":
            raise RuntimeError(f"Venda de {simbolo} não executou ({trade.orderStatus.status}): {' | '.join(erros)[:300]}")
        return {"acao": simbolo, "lado": "venda", "valor": round(valor, 2)}

    def vender_valor(self, simbolo: str, valor: float) -> dict:
        """Vende parte da posicao (o valor em dolares, nunca mais do que tem); sem fracao na API, acoes inteiras."""
        p = next((x for x in self.posicoes() if x["symbol"] == simbolo), None)
        if not p:
            return {"acao": simbolo, "lado": "venda", "valor": 0.0}
        preco = self.preco(simbolo)
        qtd = min(quantidade_fracionada(valor, preco), float(p["qty"]))
        trade, erros = self._executar(simbolo, "SELL", qtd) if qtd > 0 else (None, [])
        aviso = None
        if trade is not None and trade.orderStatus.status != "Filled" and recusou_fracao(erros):
            inteiras = min(math.floor(valor / preco), math.floor(float(p["qty"])))
            aviso = f"{simbolo}: a IBKR recusou fração; vendi {inteiras} ação(ões) inteira(s)."
            trade, erros = self._executar(simbolo, "SELL", inteiras) if inteiras else (None, [])
        if trade is None:
            return {"acao": simbolo, "lado": "venda", "valor": 0.0,
                    "aviso": aviso or f"{simbolo}: ajuste de US$ {valor:.2f} pequeno demais para vender."}
        _, recebido = self._gravar(simbolo, trade)
        if trade.orderStatus.status != "Filled":
            raise RuntimeError(f"Venda de {simbolo} não executou ({trade.orderStatus.status}): {' | '.join(erros)[:300]}")
        return {"acao": simbolo, "lado": "venda", "valor": round(recebido, 2), **({"aviso": aviso} if aviso else {})}

    def comprar_valor(self, simbolo: str, valor: float) -> dict:
        preco = self.preco(simbolo)
        qtd = quantidade_fracionada(valor, preco)
        trade, erros = self._executar(simbolo, "BUY", qtd) if qtd > 0 else (None, [])
        aviso = None
        if trade is not None and trade.orderStatus.status != "Filled" and recusou_fracao(erros):
            # a conta nao aceitou fracao pela API: compra em acoes inteiras e o resto fica em caixa
            inteiras = math.floor(valor / preco)
            aviso = f"{simbolo}: a IBKR recusou fração; comprei {inteiras} ação(ões) inteira(s)."
            trade, erros = self._executar(simbolo, "BUY", inteiras) if inteiras else (None, [])
            if trade is None:
                return {"acao": simbolo, "lado": "compra", "valor": 0.0,
                        "aviso": f"{simbolo}: sem fração na API e US$ {valor:.2f} não paga 1 ação (US$ {preco:.2f})."}
        if trade is None:
            return {"acao": simbolo, "lado": "compra", "valor": 0.0, "aviso": f"{simbolo}: valor pequeno demais."}
        _, gasto = self._gravar(simbolo, trade)
        if trade.orderStatus.status != "Filled":
            raise RuntimeError(f"Compra de {simbolo} não executou ({trade.orderStatus.status}): {' | '.join(erros)[:300]}")
        return {"acao": simbolo, "lado": "compra", "valor": round(gasto, 2), **({"aviso": aviso} if aviso else {})}

    # ------------------------------------------------------------- imposto
    def atividades(self) -> list[dict]:
        """No formato das 'activities' da Alpaca: execucoes do robo (com comissao) + dividendos do Flex Query."""
        saida = [{"activity_type": "FILL", "transaction_time": e["time"], "symbol": e["symbol"], "side": e["side"],
                  "qty": e["qty"], "price": e["price"], "order_id": e["order_id"], "comissao": e.get("comissao", 0.0)}
                 for e in ler_json(self.arq_execucoes, []) or []]
        flex = ler_json(USER_DATA / "ibkr_flex.json")
        if flex:
            saida += dividendos_flex(baixar_flex(flex["token"], flex["query"]))
        return sorted(saida, key=lambda a: a.get("transaction_time") or a.get("date", ""))


# ===================================================================== Flex Query (dividendos)
def xml_seguro(texto: str) -> ET.Element:
    """O XML vem da IBKR, mas mesmo assim: sem DOCTYPE/ENTITY (bloqueia entidade externa e 'bomba' de entidades)."""
    if "<!DOCTYPE" in texto.upper() or "<!ENTITY" in texto.upper():
        raise RuntimeError("Resposta do Flex com DOCTYPE/ENTITY: recusada.")
    return ET.fromstring(texto)


def baixar_flex(token: str, consulta: str) -> str:
    r = httpx.get(f"{FLEX}/SendRequest", params={"t": token, "q": consulta, "v": 3}, timeout=60)
    raiz = xml_seguro(r.text)
    if raiz.findtext("Status") != "Success":
        raise RuntimeError(f"Flex Query recusado: {raiz.findtext('ErrorCode')} {raiz.findtext('ErrorMessage')}")
    ref = raiz.findtext("ReferenceCode")
    for _ in range(12):
        time.sleep(5)
        r = httpx.get(f"{FLEX}/GetStatement", params={"t": token, "q": ref, "v": 3}, timeout=60)
        if "<FlexQueryResponse" in r.text:
            return r.text
    raise RuntimeError("O Flex Query não ficou pronto em 1 minuto. Tente de novo mais tarde.")


def _data_flex(v: str) -> str:
    """'20261030', '20261030;101500' ou '2026-10-30' -> '2026-10-30'."""
    v = (v or "").split(";")[0].split(",")[0].strip()
    return v[:10] if "-" in v else f"{v[:4]}-{v[4:6]}-{v[6:8]}"


def dividendos_flex(xml: str) -> list[dict]:
    """CashTransactions do Flex: 'Dividends' -> DIV, 'Withholding Tax' -> DIVNRA (valor negativo)."""
    saida = []
    for ct in xml_seguro(xml).iter("CashTransaction"):
        tipo = (ct.get("type") or "").lower()
        if ct.get("currency", "USD") != "USD" or not ("dividend" in tipo or "withholding" in tipo):
            continue
        if (ct.get("levelOfDetail") or "DETAIL").upper() not in ("DETAIL", ""):
            continue  # o Flex pode trazer totais; so as linhas de detalhe contam
        saida.append({"activity_type": "DIVNRA" if "withholding" in tipo else "DIV",
                      "date": _data_flex(ct.get("dateTime") or ct.get("settleDate") or ct.get("reportDate") or ""),
                      "symbol": simbolo_nosso(ct.get("symbol") or ""), "net_amount": float(ct.get("amount") or 0)})
    return saida

r"""
Teste da camada de corretoras (scripts/corretoras.py) sem IBKR de verdade: um IB Gateway falso responde
como o ib_async. Confere as travas de conta de papel, a compra fracionada e o plano B (acoes inteiras),
o registro das execucoes, o horario da bolsa, o Flex Query e o custo com comissao no relatorio de imposto.
Uso: .\.venv\Scripts\python.exe scripts\teste_corretoras.py
"""
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corretoras as cr  # noqa: E402
import relatorio_imposto as ri  # noqa: E402

falhas = 0


def conferir(nome, cond):
    global falhas
    print(("ok    " if cond else "FALHA ") + nome)
    falhas += 0 if cond else 1


class TradeFalso:
    def __init__(self, ordem, sym, preco, executa=True, erro=None):
        self.order = NS(orderId=ordem.orderId)
        self.orderStatus = NS(status="Filled" if executa else "Cancelled")
        self.log = [NS(errorCode=10243 if erro else 0, message=erro or "Filled")]
        lado = "BOT" if ordem.action == "BUY" else "SLD"
        self.fills = [NS(execution=NS(execId=f"e{ordem.orderId}", side=lado, shares=ordem.totalQuantity, price=preco,
                                      time=datetime(2026, 11, 16, 15, 0, tzinfo=timezone.utc)),
                         commissionReport=NS(commission=-0.35))] if executa else []

    def isDone(self):
        return True


class IBFalso:
    def __init__(self, contas=("DU1234567",), aceita_fracao=True):
        self.contas, self.aceita_fracao, self.ligado, self.ordens = list(contas), aceita_fracao, False, []
        self.carteira = [NS(contract=NS(secType="STK", symbol="BRK B"), position=0.5, averageCost=500.0,
                            marketPrice=520.0, marketValue=260.0, unrealizedPNL=10.0)]

    def isConnected(self):
        return self.ligado

    def connect(self, *a, **k):
        self.ligado = True

    def disconnect(self):
        self.ligado = False

    def managedAccounts(self):
        return self.contas

    def accountValues(self):
        return [NS(tag="CashBalance", currency="USD", value="740.00", account=self.contas[0]),
                NS(tag="CashBalance", currency="BRL", value="9999", account=self.contas[0])]

    def portfolio(self):
        return self.carteira

    def qualifyContracts(self, c):
        return [c] if c.symbol != "XXXX" else []

    def reqContractDetails(self, c):
        return [NS(liquidHours="20261116:0930-20261116:1600;20261117:CLOSED", timeZoneId="US/Eastern")]

    def reqMarketDataType(self, t):
        pass

    def reqMktData(self, c, *a, **k):
        return NS(marketPrice=lambda: 400.0)

    def sleep(self, s):
        pass

    def reqHistoricalData(self, *a, **k):
        return []

    def placeOrder(self, c, ordem):
        ordem.orderId = len(self.ordens) + 1
        self.ordens.append((c.symbol, ordem.action, ordem.totalQuantity))
        fracao = ordem.totalQuantity != int(ordem.totalQuantity)
        if fracao and not self.aceita_fracao:
            return TradeFalso(ordem, c.symbol, 400.0, executa=False, erro="Fractional-sized order cannot be placed via API")
        return TradeFalso(ordem, c.symbol, 400.0)


pasta = Path(tempfile.mkdtemp())

# ---- travas de conta de papel
try:
    cr.Ibkr(porta=4001)
    conferir("porta 4001 (Gateway REAL) recusada", False)
except cr.ContaRealRecusada:
    conferir("porta 4001 (Gateway REAL) recusada", True)
try:
    cr.Ibkr(porta=7496)
    conferir("porta 7496 (TWS REAL) recusada", False)
except cr.ContaRealRecusada:
    conferir("porta 7496 (TWS REAL) recusada", True)
real = IBFalso(contas=("U7654321",))
try:
    cr.Ibkr(ib=real, arq_execucoes=pasta / "x.json").conta()
    conferir("login de conta real (U...) recusado", False)
except cr.ContaRealRecusada:
    conferir("login de conta real (U...) recusado e desconectado", not real.ligado)
misto = IBFalso(contas=("DU1", "U2"))
try:
    cr.Ibkr(ib=misto, arq_execucoes=pasta / "x.json").conta()
    conferir("login com uma conta real no meio recusado", False)
except cr.ContaRealRecusada:
    conferir("login com uma conta real no meio recusado", True)

# ---- leitura
ib = IBFalso()
k = cr.Ibkr(ib=ib, arq_execucoes=pasta / "execs.json")
pos = k.posicoes()
conferir("posicao BRK B vira BRK.B", pos[0]["symbol"] == "BRK.B" and pos[0]["qty"] == 0.5)
conta = k.conta()
conferir("patrimonio em dolar = caixa USD + acoes (ignora o caixa em real)", conta["equity"] == 1000.0 and conta["cash"] == 740.0)
conferir("negociavel: acao que existe", k.negociavel("MSFT") and not k.negociavel("XXXX"))

# ---- bolsa
aberta = cr.mercado_aberto("20261116:0930-20261116:1600;20261117:CLOSED", "US/Eastern",
                           datetime(2026, 11, 16, 15, 0, tzinfo=timezone.utc))  # 10h em NY
fechada = cr.mercado_aberto("20261116:0930-20261116:1600;20261117:CLOSED", "US/Eastern",
                            datetime(2026, 11, 16, 22, 0, tzinfo=timezone.utc))  # 17h em NY
feriado = cr.mercado_aberto("20261116:0930-20261116:1600;20261117:CLOSED", "US/Eastern",
                            datetime(2026, 11, 17, 15, 0, tzinfo=timezone.utc))
conferir("bolsa: aberta as 10h de NY, fechada as 17h e no dia CLOSED", aberta and not fechada and not feriado)

# ---- compras
conferir("quantidade fracionada arredonda para baixo", cr.quantidade_fracionada(87.35, 400.0) == 0.2183)
f = k.comprar_valor("MSFT", 87.35)
conferir("compra fracionada: 0,2183 acao", ib.ordens[-1] == ("MSFT", "BUY", 0.2183) and abs(f["valor"] - 87.32) < 0.01)
ib2 = IBFalso(aceita_fracao=False)
k2 = cr.Ibkr(ib=ib2, arq_execucoes=pasta / "execs2.json")
f2 = k2.comprar_valor("MSFT", 900.0)
conferir("sem fracao na API: plano B compra 2 acoes inteiras e avisa",
         ib2.ordens[-1] == ("MSFT", "BUY", 2) and f2["valor"] == 800.0 and "inteira" in f2.get("aviso", ""))
f3 = k2.comprar_valor("MSFT", 87.35)
conferir("sem fracao e valor menor que 1 acao: nao compra e avisa", f3["valor"] == 0 and "não paga 1 ação" in f3["aviso"])
v = k.vender_tudo("BRK.B")
conferir("venda de tudo usa a quantidade da posicao", ib.ordens[-1] == ("BRK B", "SELL", 0.5) and v["valor"] == 200.0)

# ---- execucoes -> relatorio de imposto (com comissao)
ativ = k.atividades()
conferir("execucoes gravadas com comissao", len(ativ) == 2 and all(a["comissao"] == 0.35 for a in ativ))
ptax = NS(em=lambda d: 5.0)
compra = {"activity_type": "FILL", "transaction_time": "2026-11-16T15:00:00Z", "symbol": "MSFT", "side": "buy",
          "qty": 1, "price": 400.0, "order_id": "1", "comissao": 1.0}
venda = {**compra, "side": "sell", "price": 450.0, "order_id": "2", "transaction_time": "2026-11-20T15:00:00Z"}
vendas, _, carteira = ri.acoes(2026, ptax, [compra, venda])
conferir("lucro em reais desconta a comissao da compra e da venda", abs(vendas[0]["lucro_brl"] - (449 - 401) * 5.0) < 1e-6)

# ---- Flex Query
xml = """<FlexQueryResponse><FlexStatements><FlexStatement><CashTransactions>
<CashTransaction currency="USD" type="Dividends" symbol="MSFT" amount="2.50" dateTime="20261210;202000" levelOfDetail="DETAIL"/>
<CashTransaction currency="USD" type="Withholding Tax" symbol="MSFT" amount="-0.75" dateTime="20261210" levelOfDetail="DETAIL"/>
<CashTransaction currency="USD" type="Deposits/Withdrawals" amount="1000" dateTime="20261201"/>
<CashTransaction currency="USD" type="Dividends" amount="2.50" levelOfDetail="SUMMARY"/>
</CashTransactions></FlexStatement></FlexStatements></FlexQueryResponse>"""
d = cr.dividendos_flex(xml)
conferir("Flex: dividendo e imposto retido, sem deposito nem total",
         [(x["activity_type"], x["date"], x["net_amount"]) for x in d] == [("DIV", "2026-12-10", 2.5), ("DIVNRA", "2026-12-10", -0.75)])
try:
    cr.dividendos_flex('<!DOCTYPE x [<!ENTITY a "b">]><x/>')
    conferir("Flex com DOCTYPE/ENTITY recusado", False)
except RuntimeError:
    conferir("Flex com DOCTYPE/ENTITY recusado", True)

# ---- escolha da corretora
conferir("sem arquivo de configuracao: Alpaca", cr.config()["acoes"] in ("alpaca", "ibkr"))
conferir("estado do consenso separado por corretora",
         cr.arq_estado_consenso("alpaca").name == "consenso.json" and cr.arq_estado_consenso("ibkr").name == "consenso_ibkr.json")

print(f"\n{falhas} falha(s)")
sys.exit(1 if falhas else 0)

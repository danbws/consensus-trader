r"""
Relatorio anual para o contador (planejamento-dinheiro-real.md, secao 5): tudo o que foi vendido no ano, com
lucro ou prejuizo em reais, dividendos e o que sobrou em carteira em 31/12 (ficha "Bens e Direitos").

Fontes:
  - acoes: a corretora em uso (scripts/corretoras.py). Alpaca: atividades da conta. IBKR: execucoes gravadas pelo
           robo (com comissao) + dividendos e imposto retido pelo Flex Query.
           Custo pelo metodo PEPS (a primeira compra e a primeira a sair), comissao incluida;
  - cripto: banco do Freqtrade (tradesv3*.sqlite), lido so para leitura; os pares sao em reais.
Conversao: dolar PTAX do Banco Central na data de cada compra e de cada venda (cotacao de VENDA, ver COTACAO).
           Se o contador indicar outra regra, troca-se so a constante.

Enquanto a conta for de papel e o robo estiver no simulado, o relatorio sai marcado SIMULADO: serve para
conferir o formato com o contador antes do dinheiro real.

Uso (na pasta do projeto):
  .\.venv\Scripts\python.exe scripts\relatorio_imposto.py            (ano atual)
  .\.venv\Scripts\python.exe scripts\relatorio_imposto.py --ano 2026
Gera docs/impostos/AAAA.md e docs/impostos/AAAA-vendas.csv.
"""
import csv
import sqlite3
import sys
from collections import defaultdict, deque
from datetime import date, datetime, timedelta
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from corretoras import corretora_acoes  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / "docs" / "impostos"
COTACAO = "cotacaoVenda"  # Lei 14.754/2023: dolar de venda do BCB na data; confirmar com o contador
ALIQUOTA = 0.15
FUSO_BR = timedelta(hours=-3)


# ------------------------------------------------------------------ dolar PTAX
class Ptax:
    def __init__(self, inicio: date, fim: date):
        url = ("https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarPeriodo("
               "dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)"
               f"?@dataInicial='{inicio - timedelta(days=10):%m-%d-%Y}'&@dataFinalCotacao='{fim:%m-%d-%Y}'&$format=json")
        self.dia = {}
        for v in httpx.get(url, timeout=60).json()["value"]:
            self.dia[v["dataHoraCotacao"][:10]] = float(v[COTACAO])  # a ultima do dia prevalece

    def em(self, d: date) -> float:
        """Cotacao do dia; em fim de semana e feriado, a do ultimo dia util antes."""
        for i in range(10):
            k = (d - timedelta(days=i)).isoformat()
            if k in self.dia:
                return self.dia[k]
        raise RuntimeError(f"Sem PTAX perto de {d}")


def dia_br(iso: str) -> date:
    return (datetime.fromisoformat(iso.replace("Z", "+00:00")).replace(tzinfo=None) + FUSO_BR).date()


# ------------------------------------------------------------------ acoes (corretora em uso)
def acoes(ano: int, ptax: Ptax, atividades: list[dict]):
    lotes = defaultdict(deque)  # symbol -> [qtd, preco_usd, dolar_da_compra, dia]
    vendas, dividendos = [], []
    for a in atividades:
        tipo = a["activity_type"]
        if tipo == "FILL":
            d, s, q, px = dia_br(a["transaction_time"]), a["symbol"], float(a["qty"]), float(a["price"])
            comissao = float(a.get("comissao") or 0)  # IBKR cobra; entra no custo da compra e sai do valor da venda
            if a["side"] == "buy":
                lotes[s].append([q, px + comissao / q, ptax.em(d), d])
                continue
            px -= comissao / q
            falta, custo_usd, custo_brl, primeira = q, 0.0, 0.0, None
            while falta > 1e-9 and lotes[s]:
                lote = lotes[s][0]
                usa = min(falta, lote[0])
                custo_usd += usa * lote[1]
                custo_brl += usa * lote[1] * lote[2]
                primeira = primeira or lote[3]
                lote[0] -= usa
                falta -= usa
                if lote[0] <= 1e-9:
                    lotes[s].popleft()
            if d.year == ano:
                dolar = ptax.em(d)
                linha = {"tipo": "acao", "ativo": s, "data": d.isoformat(), "comprado_em": str(primeira or ""),
                         "quantidade": q, "venda_usd": q * px, "custo_usd": custo_usd, "dolar_venda": dolar,
                         "venda_brl": q * px * dolar, "custo_brl": custo_brl,
                         "lucro_brl": q * px * dolar - custo_brl, "sem_custo": falta > 1e-9, "ordem": a.get("order_id")}
                ant = vendas[-1] if vendas else None
                if ant and ant["ordem"] == linha["ordem"] and ant["data"] == linha["data"]:  # execucao parcial: uma linha por ordem
                    for k in ("quantidade", "venda_usd", "custo_usd", "venda_brl", "custo_brl", "lucro_brl"):
                        ant[k] += linha[k]
                    ant["sem_custo"] = ant["sem_custo"] or linha["sem_custo"]
                    ant["comprado_em"] = min(ant["comprado_em"], linha["comprado_em"]) or linha["comprado_em"]
                else:
                    vendas.append(linha)
        elif tipo in ("DIV", "DIVNRA"):
            d = date.fromisoformat(a["date"][:10])
            if d.year == ano:
                valor = float(a.get("net_amount") or 0)
                dividendos.append({"ativo": a.get("symbol"), "data": d.isoformat(), "tipo": tipo,
                                   "usd": valor, "brl": valor * ptax.em(d)})
    carteira = []
    for s, ls in lotes.items():
        q = sum(l[0] for l in ls)
        if q > 1e-9:
            carteira.append({"ativo": s, "quantidade": q, "custo_usd": sum(l[0] * l[1] for l in ls),
                             "custo_brl": sum(l[0] * l[1] * l[2] for l in ls)})
    return vendas, dividendos, carteira


# ------------------------------------------------------------------ cripto (Freqtrade)
def cripto(ano: int):
    """Com dinheiro real usa so o banco real; antes disso, o do simulado (marcado SIMULADO)."""
    real, sim = RAIZ / "tradesv3.sqlite", RAIZ / "tradesv3.dryrun.sqlite"
    banco, simulado = (real, False) if real.exists() and real.stat().st_size else (sim, True)
    vendas, carteira = [], []
    if not banco.exists():
        return vendas, carteira, simulado
    con = sqlite3.connect(f"file:{banco.as_posix()}?mode=ro", uri=True)  # so leitura: nao mexe no banco do robo
    for pair, aberta, abriu, fechou, qtd, p_ent, p_sai, lucro, stake in con.execute(
            "select pair, is_open, open_date, close_date, amount, open_rate, close_rate, close_profit_abs, stake_amount "
            "from trades order by close_date"):
        if aberta:
            carteira.append({"ativo": pair.split("/")[0], "quantidade": qtd, "custo_brl": stake})
            continue
        d = dia_br(fechou)
        if d.year == ano:
            vendas.append({"tipo": "cripto", "ativo": pair.split("/")[0], "data": d.isoformat(),
                           "comprado_em": dia_br(abriu).isoformat(), "quantidade": qtd,
                           "venda_brl": qtd * p_sai, "custo_brl": qtd * p_ent, "lucro_brl": lucro})
    con.close()
    return vendas, carteira, simulado


# ------------------------------------------------------------------ saida
def brl(v: float) -> str:
    return ("-" if v < 0 else "") + "R$ " + f"{abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def usd(v: float) -> str:
    return ("-" if v < 0 else "") + "US$ " + f"{abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def num(v: float) -> str:
    return f"{v:.8g}".replace(".", ",")


def main():
    ano = int(sys.argv[sys.argv.index("--ano") + 1]) if "--ano" in sys.argv else date.today().year
    fim = min(date(ano, 12, 31), date.today())
    corretora = corretora_acoes("imposto")
    try:
        atividades = corretora.atividades() if corretora.configurada() else []
        conta_papel = corretora.conta()["papel"] if atividades else True
    finally:
        corretora.fechar()
    inicio = min([dia_br(a["transaction_time"]) for a in atividades if a.get("transaction_time")] + [date(ano, 1, 1)])
    ptax = Ptax(inicio, fim)
    v_acoes, dividendos, cart_acoes = acoes(ano, ptax, atividades)
    v_cripto, cart_cripto, cripto_simulada = cripto(ano)
    acoes_papel = conta_papel

    lucro_acoes = sum(v["lucro_brl"] for v in v_acoes)
    lucro_cripto = sum(v["lucro_brl"] for v in v_cripto)
    div_bruto = sum(d["brl"] for d in dividendos if d["tipo"] == "DIV")
    div_retido = -sum(d["brl"] for d in dividendos if d["tipo"] == "DIVNRA")
    base = lucro_acoes + lucro_cripto + div_bruto

    PASTA.mkdir(parents=True, exist_ok=True)
    with open(PASTA / f"{ano}-vendas.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["tipo", "ativo", "data_venda", "primeira_compra", "quantidade", "venda_usd", "custo_usd",
                    "dolar_ptax_venda", "venda_brl", "custo_brl", "lucro_brl"])
        for v in sorted(v_acoes + v_cripto, key=lambda x: x["data"]):
            em_usd = v["tipo"] == "acao"
            w.writerow([v["tipo"], v["ativo"], v["data"], v["comprado_em"], num(v["quantidade"]),
                        num(round(v["venda_usd"], 2)) if em_usd else "", num(round(v["custo_usd"], 2)) if em_usd else "",
                        num(v["dolar_venda"]) if em_usd else "", num(round(v["venda_brl"], 2)), num(round(v["custo_brl"], 2)),
                        num(round(v["lucro_brl"], 2))])

    aviso = []
    if acoes_papel:
        aviso.append(f"as ações são da **conta de papel** da {corretora.nome_exibir} (dinheiro fictício)")
    if cripto_simulada:
        aviso.append("as criptos são do **robô no simulado**")
    L = [f"# Relatório de imposto · {ano}", "",
         f"Gerado em {datetime.now():%d/%m/%Y %H:%M} · período 01/01/{ano} a {fim:%d/%m/%Y}", ""]
    if aviso:
        L += [f"> **SIMULADO:** {' e '.join(aviso)}. Nada aqui é imposto de verdade; serve para conferir o formato com o contador.", ""]
    L += ["> Regra usada (Lei 14.754/2023, a confirmar com o contador): ganho em reais = valor da venda no dólar PTAX de venda",
          "> do dia da venda − custo no dólar PTAX do dia de cada compra; custo pelo PEPS (primeira compra sai primeiro).", "",
          "## 1. Resumo", "",
          "| | Valor |", "|---|---:|",
          f"| Lucro/prejuízo com ações no exterior | {brl(lucro_acoes)} |",
          f"| Lucro/prejuízo com cripto (Binance, exterior) | {brl(lucro_cripto)} |",
          f"| Dividendos recebidos (bruto) | {brl(div_bruto)} |",
          f"| Imposto já retido nos EUA sobre dividendos | {brl(div_retido)} |",
          f"| **Resultado do ano** | **{brl(base)}** |",
          f"| Estimativa de 15% sobre o resultado positivo (antes de compensar o retido nos EUA) | {brl(max(base, 0) * ALIQUOTA)} |",
          "", "Prejuízo do ano: a lei permite compensar com ganhos de aplicações no exterior; o contador confirma como.", ""]

    L += ["## 2. Vendas de ações", ""]
    if v_acoes:
        L += ["| Data | Ação | Qtde | Venda US$ | Custo US$ | Dólar | Venda R$ | Custo R$ | Lucro R$ |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
        for v in v_acoes:
            marca = " ⚠️ sem compra registrada" if v["sem_custo"] else ""
            L.append(f"| {v['data']} | {v['ativo']}{marca} | {num(v['quantidade'])} | {usd(v['venda_usd'])} | {usd(v['custo_usd'])} | "
                     f"{num(v['dolar_venda'])} | {brl(v['venda_brl'])} | {brl(v['custo_brl'])} | {brl(v['lucro_brl'])} |")
    else:
        L.append("Nenhuma venda no ano.")

    L += ["", "## 3. Vendas de cripto", ""]
    if v_cripto:
        por_mes = defaultdict(float)
        for v in v_cripto:
            por_mes[v["data"][:7]] += v["venda_brl"]
        L += ["| Data | Moeda | Comprada em | Qtde | Venda R$ | Custo R$ | Lucro R$ (já com taxas) |",
              "|---|---|---|---:|---:|---:|---:|"]
        for v in v_cripto:
            L.append(f"| {v['data']} | {v['ativo']} | {v['comprado_em']} | {num(v['quantidade'])} | {brl(v['venda_brl'])} | "
                     f"{brl(v['custo_brl'])} | {brl(v['lucro_brl'])} |")
        L += ["", "Total vendido por mês (o contador usa para ver obrigação de informar a Receita):", ""]
        L += [f"- {m}: {brl(t)}" for m, t in sorted(por_mes.items())]
    else:
        L.append("Nenhuma venda no ano.")

    L += ["", "## 4. Dividendos", ""]
    if dividendos:
        L += ["| Data | Ação | Tipo | US$ | R$ |", "|---|---|---|---:|---:|"]
        for d in dividendos:
            tipo = "dividendo" if d["tipo"] == "DIV" else "imposto retido nos EUA"
            L.append(f"| {d['data']} | {d['ativo']} | {tipo} | {usd(d['usd'])} | {brl(d['brl'])} |")
    else:
        L.append("Nenhum dividendo no ano.")

    L += ["", f"## 5. Bens e Direitos em {fim:%d/%m/%Y} (pelo custo, não pelo valor de mercado)", ""]
    if cart_acoes or cart_cripto:
        L += ["| Ativo | Onde | Qtde | Custo US$ | Custo R$ |", "|---|---|---:|---:|---:|"]
        for c in sorted(cart_acoes, key=lambda x: x["ativo"]):
            L.append(f"| {c['ativo']} | {corretora.nome_exibir} (EUA) | {num(c['quantidade'])} | {usd(c['custo_usd'])} | {brl(c['custo_brl'])} |")
        for c in cart_cripto:
            L.append(f"| {c['ativo']} | Binance | {num(c['quantidade'])} | - | {brl(c['custo_brl'])} |")
    else:
        L.append("Nada em carteira.")
    L += ["", f"Detalhe venda a venda, para o contador abrir no Excel: `docs/impostos/{ano}-vendas.csv`.", ""]
    (PASTA / f"{ano}.md").write_text("\n".join(L), encoding="utf-8")
    print(f"Gerado docs/impostos/{ano}.md: acoes {brl(lucro_acoes)}, cripto {brl(lucro_cripto)}, "
          f"dividendos {brl(div_bruto)}, {len(v_acoes)} vendas de acoes, {len(v_cripto)} de cripto")


if __name__ == "__main__":
    main()

r"""
Carteira de CONSENSO automatica em conta de PAPEL (aula 12; estudo em docs/hipoteses-testadas.md).
A corretora (Alpaca ou Interactive Brokers) vem de user_data/corretora.json: ver scripts/corretoras.py.

Regra (a mesma testada em scripts/estudo_consenso.py):
  - as 10 EMPRESAS que mais gestores da lista tem como "maior aposta" (3% ou mais da carteira, somando
    as classes de acao, ex.: GOOG+GOOGL, BRK.A+BRK.B) no ultimo 13F entregue; empate: maior peso medio;
  - partes iguais, 5% em caixa; troca SO quando a lista muda (relatorios novos, 1x por trimestre).
Seguranca:
  - so conta de PAPEL: na Alpaca, o endereco de papel; na IBKR, porta de papel e conta "DU" (corretoras.py);
  - nenhuma compra acima de 20% da carteira; nada de opcao; so com a bolsa aberta;
  - tudo registrado em acoes-eua/trader/state/consenso.json (IBKR: consenso_ibkr.json) e avisado no Telegram.

Uso (na pasta do projeto):
  .\.venv\Scripts\python.exe scripts\consenso_automatico.py --simular    (mostra o plano, nao envia nada)
  .\.venv\Scripts\python.exe scripts\consenso_automatico.py              (executa, se a bolsa estiver aberta)
  --atualizar13f  baixa antes os relatorios novos da SEC
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import httpx
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estudo_consenso as ec  # noqa: E402
from corretoras import arq_estado_consenso, corretora_acoes  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
TAMANHO_INICIAL = 1000.0
CAIXA_PCT = 0.05
MAX_ORDEM_PCT = 0.20
TOP, CORTE, MIN_GESTORES = 10, 3.0, 2


def telegram(texto: str):
    try:
        t = json.loads((RAIZ / "user_data" / "telegram_painel.json").read_text(encoding="utf-8"))
        httpx.post(f"https://api.telegram.org/bot{t['token']}/sendMessage", timeout=15,
                   json={"chat_id": t["chat_id"], "text": texto, "parse_mode": "HTML"})
    except Exception:
        pass


def consenso_hoje(corretora) -> tuple[list[str], dict]:
    """A lista alvo com o que se sabe hoje (ultimo 13F entregue de cada gestor)."""
    ultimos = {}
    for r in ec.carregar13f():
        if r["cik"] not in ultimos or r["periodo"] > ultimos[r["cik"]]["periodo"]:
            ultimos[r["cik"]] = r
    cont, pesos, quem = {}, {}, {}
    for r in ultimos.values():
        for t, p in ec.apostas_por_empresa(r, CORTE).items():
            cont[t] = cont.get(t, 0) + 1
            pesos.setdefault(t, []).append(p)
            quem.setdefault(t, []).append(ec.GESTORES.get(r["cik"], r["cik"]))
    lista = sorted([t for t, n in cont.items() if n >= MIN_GESTORES], key=lambda t: (-cont[t], -np.mean(pesos[t])))
    # so acoes que a corretora negocia (na Alpaca, tambem em fracao)
    alvo = []
    for t in lista:
        if corretora.negociavel(t):
            alvo.append(t)
        if len(alvo) == TOP:
            break
    return alvo, {t: {"gestores": len(quem[t]), "quem": quem[t]} for t in alvo}


def ler_estado(arq: Path) -> dict:
    try:
        return json.loads(arq.read_text(encoding="utf-8"))
    except Exception:
        return {"ligado_em": None, "caixa": None, "alvo": [], "historico": []}


def main():
    simular = "--simular" in sys.argv
    if "--atualizar13f" in sys.argv:
        ec.baixar13f()
    corretora = corretora_acoes("consenso")
    if not corretora.configurada():
        print("Nenhuma corretora de ações configurada.")
        return
    try:
        rodar(corretora, simular)
    finally:
        corretora.fechar()


def rodar(corretora, simular: bool):
    arq_estado = arq_estado_consenso(corretora.nome)
    estado = ler_estado(arq_estado)
    alvo, detalhes = consenso_hoje(corretora)
    posicoes = {p["symbol"]: p for p in corretora.posicoes()}
    vale = sum(float(p["market_value"]) for p in posicoes.values())
    pago = sum(float(p["qty"]) * float(p["avg_entry_price"]) for p in posicoes.values())
    if estado.get("caixa") is None:  # primeira vez: a carteira de teste vale US$ 1.000 contando o que ja foi pago
        estado["caixa"] = round(TAMANHO_INICIAL - pago, 2)
    carteira = vale + estado["caixa"]

    vender = [s for s in posicoes if s not in alvo]
    comprar = [s for s in alvo if s not in posicoes]
    plano = {"corretora": corretora.nome, "alvo": alvo, "vender": vender, "comprar": comprar,
             "carteira": round(carteira, 2), "caixa": estado["caixa"]}
    print(json.dumps({**plano, "detalhes": detalhes}, ensure_ascii=False, indent=2))
    if not vender and not comprar:
        print("Nada a trocar: a carteira ja e o consenso.")
        return
    if simular:
        print("SIMULACAO: nada foi enviado.")
        return
    if not corretora.bolsa_aberta():
        print("Bolsa fechada: troca fica para a proxima conferencia com a bolsa aberta.")
        return

    feitos = []
    for s in vender:  # 1) vende o que saiu da lista (cada corretora espera a venda executar)
        feitos.append(corretora.vender_tudo(s))
    if vender:  # soma o dinheiro das vendas ao caixa da carteira
        estado["caixa"] = round(estado["caixa"] + sum(f["valor"] for f in feitos), 2)

    if comprar:  # 2) compra o que entrou, em partes iguais, guardando 5% de caixa
        mantidas = sum(float(p["market_value"]) for s, p in posicoes.items() if s in alvo)
        total = mantidas + estado["caixa"]
        por_acao = min((total * (1 - CAIXA_PCT) - mantidas) / len(comprar), total * MAX_ORDEM_PCT)
        por_acao = round(max(0.0, por_acao), 2)
        for s in comprar:
            if por_acao < 1:
                break
            f = corretora.comprar_valor(s, por_acao)  # devolve o valor realmente gasto
            estado["caixa"] = round(estado["caixa"] - f["valor"], 2)
            feitos.append(f)

    agora = datetime.now().isoformat(timespec="seconds")
    estado.update(ligado_em=estado.get("ligado_em") or agora, alvo=alvo, ultima_troca=agora)
    estado["historico"] = ([{"em": agora, "ordens": feitos, "alvo": alvo}] + estado.get("historico", []))[:50]
    arq_estado.parent.mkdir(parents=True, exist_ok=True)
    arq_estado.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")

    linhas = [f"🔄 <b>Carteira de consenso: troca feita</b> ({corretora.nome_exibir}, conta de papel)", ""]
    vendas = [f for f in feitos if f["lado"] == "venda"]
    compras = [f for f in feitos if f["lado"] == "compra"]
    if vendas:
        linhas.append("Vendeu: " + ", ".join(f"{f['acao']} (US$ {f['valor']:.2f})" for f in vendas))
    if compras:
        linhas.append("Comprou: " + ", ".join(f"{f['acao']} (US$ {f['valor']:.2f})" for f in compras))
    linhas += [f"⚠️ {f['aviso']}" for f in feitos if f.get("aviso")]
    linhas += ["", f"Caixa da carteira: US$ {estado['caixa']:.2f}", "Motivo: são as ações que mais gestores têm entre as maiores apostas."]
    telegram("\n".join(linhas))
    print("FEITO:", json.dumps(feitos, ensure_ascii=False))


if __name__ == "__main__":
    main()

r"""
Teste do peso igual da carteira de consenso (scripts/consenso_automatico.py), sem corretora de verdade:
o plano de vendas e compras e uma execucao completa com uma corretora falsa.
Uso: .\.venv\Scripts\python.exe scripts\teste_pesos.py
"""
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import consenso_automatico as ca  # noqa: E402

falhas = 0


def conferir(nome, cond):
    global falhas
    print(("ok    " if cond else "FALHA ") + nome)
    falhas += 0 if cond else 1


# ---- plano
alvo = ["A", "B", "C", "D"]
plano = ca.planejar(alvo, {"A": 395.0, "B": 195.0, "C": 200.0, "D": 160.0}, 50.0, equilibrar=True)
conferir("peso alvo = 95% da carteira dividido pelas acoes, com teto de 20%",
         plano["carteira"] == 1000.0 and plano["por_acao"] == 200.0)
conferir("reduz a que passou do peso e completa a que ficou abaixo",
         plano["reduzir"] == {"A": 195.0} and plano["aumentar"] == {"D": 40.0})
conferir("diferenca menor que 1% da carteira nao vira ordem", "B" not in plano["aumentar"] and "C" not in plano["reduzir"])
sem = ca.planejar(alvo, {"A": 400.0, "B": 190.0, "C": 200.0, "D": 160.0}, 50.0, equilibrar=False)
conferir("sem troca na lista e antes de 90 dias: nao mexe nos pesos", not any(sem[k] for k in ("vender", "comprar", "reduzir", "aumentar")))
troca = ca.planejar(["A", "B", "E"], {"A": 400.0, "B": 300.0, "X": 250.0}, 50.0, equilibrar=False)
conferir("troca na lista sempre equilibra junto",
         troca["vender"] == ["X"] and troca["comprar"] == ["E"] and "A" in troca["reduzir"] and "B" in troca["reduzir"])
agora = datetime(2026, 11, 11)
conferir("equilibra se nunca equilibrou ou depois de 90 dias",
         ca.vence_equilibrio({}, agora) and ca.vence_equilibrio({"equilibrado_em": (agora - timedelta(days=90)).isoformat()}, agora)
         and not ca.vence_equilibrio({"equilibrado_em": (agora - timedelta(days=30)).isoformat()}, agora))


# ---- execucao completa com corretora falsa
class Falsa:
    nome, nome_exibir = "teste", "Teste"

    def __init__(self):
        self.pos = {"A": 395.0, "B": 195.0, "C": 200.0, "D": 160.0}
        self.ordens = []

    def posicoes(self):
        return [{"symbol": s, "market_value": v, "qty": 1, "avg_entry_price": 100.0} for s, v in self.pos.items()]

    def bolsa_aberta(self):
        return True

    def vender_tudo(self, s):
        self.ordens.append(("vende tudo", s))
        return {"acao": s, "lado": "venda", "valor": self.pos.pop(s)}

    def vender_valor(self, s, v):
        self.ordens.append(("vende", s, v))
        self.pos[s] -= v
        return {"acao": s, "lado": "venda", "valor": v}

    def comprar_valor(self, s, v):
        self.ordens.append(("compra", s, v))
        self.pos[s] = self.pos.get(s, 0.0) + v
        return {"acao": s, "lado": "compra", "valor": v}


pasta = Path(tempfile.mkdtemp())
enviados = []
ca.consenso_hoje = lambda c: (alvo, {})
ca.arq_estado_consenso = lambda nome: pasta / "consenso.json"
ca.telegram = enviados.append
(pasta / "consenso.json").write_text('{"caixa": 50.0, "alvo": ["A", "B", "C", "D"], "historico": []}', encoding="utf-8")
f = Falsa()
ca.rodar(f, simular=False)
conferir("vende antes de comprar", f.ordens[0] == ("vende", "A", 195.0) and f.ordens[-1] == ("compra", "D", 40.0))
conferir("depois do ajuste, as quatro ficam perto de US$ 200", all(abs(v - 200.0) <= 10.0 for v in f.pos.values()))
estado = ca.ler_estado(pasta / "consenso.json")
conferir("com 4 acoes o teto de 20% por acao deixa o resto no caixa, e grava a data do equilibrio",
         abs(estado["caixa"] - 205.0) < 0.01 and estado.get("equilibrado_em"))
conferir("aviso no Telegram diz que ajustou o peso", enviados and "Ajustou o peso" in enviados[0] and "mesmo peso" in enviados[0])
f.ordens.clear()
ca.rodar(f, simular=False)
conferir("rodando de novo logo depois: nada a fazer", f.ordens == [])

print(f"\n{falhas} falha(s)")
sys.exit(1 if falhas else 0)

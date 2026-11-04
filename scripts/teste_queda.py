r"""
Teste do aviso de queda das acoes (painel/telegram_bot.avaliar_queda).
Uso: .\.venv\Scripts\python.exe scripts\teste_queda.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "painel"))
from telegram_bot import avaliar_queda  # noqa: E402

falhas = 0


def conferir(nome, cond):
    global falhas
    print(("ok    " if cond else "FALHA ") + nome)
    falhas += 0 if cond else 1


est = {}
conferir("sobe: sem aviso", avaliar_queda(1000, est) is None and avaliar_queda(1200, est) is None)
conferir("topo guardado", est["acoes_pico"] == 1200)
conferir("-15%: sem aviso", avaliar_queda(1020, est) is None)
conferir("-21% 1a leitura: espera confirmar", avaliar_queda(948, est) is None)
msg = avaliar_queda(948, est)
conferir("-21% 2a leitura: avisa", msg is not None and "não vende" in msg)
conferir("-21% de novo: nao repete", avaliar_queda(940, est) is None and avaliar_queda(940, est) is None)
avaliar_queda(830, est)
conferir("-31% confirmado: avisa nivel novo", avaliar_queda(830, est) is not None)
conferir("leitura isolada a -45%: espera", avaliar_queda(660, est) is None)
conferir("voltou a -35%: cancela a espera", avaliar_queda(780, est) is None and est["acoes_abaixo"] is None)
conferir("-12%: ainda nao rearma", avaliar_queda(1056, est) is None and est["acoes_nivel"] == -30.0)
conferir("-5%: rearma", avaliar_queda(1140, est) is None and est["acoes_nivel"] == 0)
avaliar_queda(950, est)
conferir("caiu de novo -21%: avisa outra vez", avaliar_queda(950, est) is not None)
est2 = {}
avaliar_queda(1000, est2)
avaliar_queda(500, est2)
m = avaliar_queda(500, est2)
conferir("tombo de -50%: um aviso so, no nivel mais fundo", m is not None and est2["acoes_nivel"] == -40.0
         and avaliar_queda(500, est2) is None)

print(f"\n{falhas} falha(s)")
sys.exit(1 if falhas else 0)

r"""
Teste do aviso de concentracao por setor (painel/setores.py e painel/telegram_bot.avaliar_concentracao).
Uso: .\.venv\Scripts\python.exe scripts\teste_concentracao.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "painel"))
from setores import SEM_SETOR, TECNOLOGIA, concentracao  # noqa: E402
from telegram_bot import avaliar_concentracao  # noqa: E402

falhas = 0


def conferir(nome, cond):
    global falhas
    print(("ok    " if cond else "FALHA ") + nome)
    falhas += 0 if cond else 1


def pos(**kw):
    return [{"symbol": s.replace("_", "."), "market_value": str(v)} for s, v in kw.items()]


# carteira de 17/11/2026: 6 de tecnologia e internet, 3 financeiras, 1 sem cadastro, caixa de 5%
cart = pos(NVDA=95, TSM=95, MSFT=95, GOOGL=95, META=95, AMZN=95, V=95, BRK_B=95, BN=95, ZZZZ=95)
s = concentracao(cart, caixa=50)
conferir("maior setor = tecnologia, 57% (o caixa conta no total)", s[0][0] == TECNOLOGIA and round(s[0][1]) == 57)
conferir("acao sem cadastro aparece separada", any(x[0] == SEM_SETOR and x[2] == ["ZZZZ"] for x in s))
conferir("soma dos setores + caixa = 100%", round(sum(x[1] for x in s) + 50 / 1000 * 100) == 100)
conferir("carteira vazia: nada", concentracao([], 0) == [])

est = {}
conferir("1a leitura acima de 50%: espera confirmar", avaliar_concentracao(s, est) is None)
msg = avaliar_concentracao(s, est)
conferir("2a leitura: avisa", msg is not None and "57%" in msg and "não muda nada sozinho" in msg)
conferir("mesmo nivel: nao repete", avaliar_concentracao(s, est) is None and avaliar_concentracao(s, est) is None)
s65 = [(TECNOLOGIA, 65.0, ["NVDA"])]
avaliar_concentracao(s65, est)
conferir("passou de 60%: avisa de novo", avaliar_concentracao(s65, est) is not None and est["conc_nivel"] == 60.0)
conferir("caiu para 48%: nao avisa nem rearma", avaliar_concentracao([(TECNOLOGIA, 48.0, [])], est) is None
         and est["conc_nivel"] == 60.0)
avaliar_concentracao([(TECNOLOGIA, 40.0, [])], est)
conferir("abaixo de 45%: rearma", est["conc_nivel"] == 0)
pulo = [(TECNOLOGIA, 75.0, [])]
avaliar_concentracao(pulo, est)
conferir("pulo direto para 75%: um aviso so, no nivel 70", avaliar_concentracao(pulo, est) is not None
         and est["conc_nivel"] == 70.0 and avaliar_concentracao(pulo, est) is None)

print(f"\n{falhas} falha(s)")
sys.exit(1 if falhas else 0)

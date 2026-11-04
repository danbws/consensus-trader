r"""
Teste do porteiro do painel (painel/acesso.py): computador, celular pelo Tailscale e Wi-Fi de casa.
Usa um arquivo de senha temporario; nao toca na senha real.

Uso: .\.venv\Scripts\python.exe scripts\teste_acesso.py
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "painel"))
from fastapi.testclient import TestClient  # noqa: E402

import servidor  # noqa: E402
from acesso import Acesso  # noqa: E402

tmp = Path(tempfile.mkdtemp()) / "acesso.json"
servidor.acesso.__init__(tmp, servidor.PAGINAS)  # troca o arquivo de senha pelo temporario
H = {"X-Painel": "sim"}
falhas = []


def confere(nome, cond):
    print(("OK   " if cond else "FALHA") + " " + nome)
    if not cond:
        falhas.append(nome)


pc = TestClient(servidor.app, client=("127.0.0.1", 5000))
cel = TestClient(servidor.app, client=("100.101.102.103", 5000), follow_redirects=False)
wifi = TestClient(servidor.app, client=("192.168.0.50", 5000), follow_redirects=False)

confere("origem: computador", Acesso.origem("127.0.0.1") == "computador")
confere("origem: ::1", Acesso.origem("::1") == "computador")
confere("origem: tailscale", Acesso.origem("100.64.0.1") == "celular")
confere("origem: wifi recusado", Acesso.origem("192.168.0.50") == "fora")
confere("origem: internet recusada", Acesso.origem("8.8.8.8") == "fora")

confere("computador abre o terminal sem senha", pc.get("/terminal").status_code == 200)
confere("computador abre a Conta", pc.get("/conta").status_code == 200)
confere("wifi de casa recusado", wifi.get("/terminal").status_code == 403)
confere("wifi nao chega na API", wifi.get("/api/resumo").status_code == 403)

confere("celular sem senha vai para /entrar", cel.get("/terminal").status_code == 303)
confere("celular sem senha nao le a API", cel.get("/api/resumo").status_code == 401)
confere("celular nunca abre a Conta", cel.get("/conta").status_code == 403)
confere("celular nunca le a chave", cel.get("/api/conta").status_code == 403)
confere("celular nao cadastra chave da Alpaca", cel.post("/api/alpaca/chave", json={"key": "x" * 20, "secret": "y" * 40}, headers=H).status_code == 403)
confere("celular nao apaga chave da Alpaca", cel.delete("/api/alpaca/chave", headers=H).status_code == 403)
confere("celular nao liga o Telegram", cel.post("/api/telegram", json={"token": "1:" + "x" * 40}, headers=H).status_code == 403)
confere("celular nao desliga o Telegram", cel.delete("/api/telegram", headers=H).status_code == 403)
confere("celular nao cria senha", cel.post("/api/senha", json={"senha": "12345678"}, headers=H).status_code == 403)
confere("entrar sem senha criada avisa", cel.post("/api/entrar", json={"senha": "x"}, headers=H).status_code == 400)

confere("computador cria senha", pc.post("/api/senha", json={"senha": "teste-senha-1"}, headers=H).status_code == 200)
confere("senha curta recusada", pc.post("/api/senha", json={"senha": "123"}, headers=H).status_code == 400)
confere("senha errada recusada", cel.post("/api/entrar", json={"senha": "errada"}, headers=H).status_code == 401)
confere("entrar exige o cabecalho do painel", cel.post("/api/entrar", json={"senha": "teste-senha-1"}).status_code == 403)
r = cel.post("/api/entrar", json={"senha": "teste-senha-1"}, headers=H)
confere("senha certa entra", r.status_code == 200 and servidor.COOKIE in r.cookies)
confere("celular logado abre o terminal", cel.get("/terminal").status_code == 200)
confere("celular logado le o resumo", cel.get("/api/resumo").status_code == 200)
confere("celular logado continua sem a Conta", cel.get("/api/conta").status_code == 403)
confere("senha nao fica em texto no arquivo", "teste-senha-1" not in tmp.read_text())

for _ in range(5):
    cel.post("/api/entrar", json={"senha": "errada"}, headers=H)
confere("5 erros bloqueiam novas tentativas", cel.post("/api/entrar", json={"senha": "teste-senha-1"}, headers=H).status_code == 429)

cel.post("/api/sair", headers=H)
confere("depois de sair volta a pedir senha", cel.get("/api/resumo").status_code == 401)

print(f"\n{len(falhas)} falha(s)")
sys.exit(1 if falhas else 0)

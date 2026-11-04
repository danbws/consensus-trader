"""
Quem pode abrir o painel (docs/aulas/10-celular.md).

  - Este computador (127.0.0.1 / ::1): tudo liberado, sem senha.
  - Celular pela rede particular do Tailscale (100.64.0.0/10 e fd7a:115c:a1e0::/48): precisa entrar
    com a senha do painel. A tela Conta (chave da Binance) e a troca de senha NUNCA abrem por aqui.
  - Qualquer outro endereco (Wi-Fi de casa, internet): recusado.

A senha e criada no proprio computador (/senha). Fica guardada so como hash PBKDF2
em user_data/painel_acesso.json; as sessoes do celular duram 30 dias.
"""
import hashlib
import hmac
import ipaddress
import json
import secrets
import time
from pathlib import Path

from fastapi import Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

REDES_TAILSCALE = [ipaddress.ip_network("100.64.0.0/10"), ipaddress.ip_network("fd7a:115c:a1e0::/48")]
SO_NO_COMPUTADOR = ("/conta", "/api/conta", "/senha", "/api/senha", "/api/alpaca/chave", "/api/telegram",
                    "/api/corretora", "/api/ibkr")
LIVRES_NO_CELULAR = ("/entrar", "/api/entrar", "/manifest.json", "/icone.png", "/icone-180.png", "/estilo.css", "/casca.js")
COOKIE = "painel_sessao"
DURACAO_SESSAO = 30 * 86400
ITERACOES = 240_000


class Acesso:
    def __init__(self, arquivo: Path, pasta_paginas: Path):
        self.arquivo = arquivo
        self.paginas = pasta_paginas
        self._tentativas: dict[str, list[float]] = {}

    # ------------------------------------------------------------ dados
    def _ler(self) -> dict:
        try:
            return json.loads(self.arquivo.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _gravar(self, dados: dict) -> None:
        self.arquivo.write_text(json.dumps(dados), encoding="utf-8")

    def tem_senha(self) -> bool:
        return "hash" in self._ler()

    def definir_senha(self, senha: str) -> None:
        sal = secrets.token_bytes(16)
        hash_ = hashlib.pbkdf2_hmac("sha256", senha.encode(), sal, ITERACOES)
        # trocar a senha derruba as sessoes abertas no celular
        self._gravar({"sal": sal.hex(), "hash": hash_.hex(), "sessoes": {}})

    def conferir_senha(self, senha: str) -> bool:
        d = self._ler()
        if "hash" not in d:
            return False
        calc = hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(d["sal"]), ITERACOES)
        return hmac.compare_digest(calc.hex(), d["hash"])

    def nova_sessao(self) -> str:
        d = self._ler()
        agora = time.time()
        sessoes = {k: v for k, v in d.get("sessoes", {}).items() if v > agora}
        token = secrets.token_urlsafe(32)
        sessoes[hashlib.sha256(token.encode()).hexdigest()] = agora + DURACAO_SESSAO
        d["sessoes"] = sessoes
        self._gravar(d)
        return token

    def sessao_valida(self, token: str | None) -> bool:
        if not token:
            return False
        validade = self._ler().get("sessoes", {}).get(hashlib.sha256(token.encode()).hexdigest())
        return bool(validade and validade > time.time())

    def encerrar_sessao(self, token: str | None) -> None:
        if not token:
            return
        d = self._ler()
        d.get("sessoes", {}).pop(hashlib.sha256(token.encode()).hexdigest(), None)
        self._gravar(d)

    def pode_tentar(self, ip: str) -> bool:
        """No maximo 5 senhas erradas a cada 15 minutos por aparelho."""
        agora = time.time()
        lista = [t for t in self._tentativas.get(ip, []) if agora - t < 900]
        self._tentativas[ip] = lista
        return len(lista) < 5

    def registrar_erro(self, ip: str) -> None:
        self._tentativas.setdefault(ip, []).append(time.time())

    # ------------------------------------------------------------ origem
    @staticmethod
    def origem(ip: str) -> str:
        try:
            endereco = ipaddress.ip_address(ip)
        except ValueError:
            return "fora"
        if getattr(endereco, "ipv4_mapped", None):
            endereco = endereco.ipv4_mapped
        if endereco.is_loopback:
            return "computador"
        if any(endereco in rede for rede in REDES_TAILSCALE):
            return "celular"
        return "fora"

    # ------------------------------------------------------------ porteiro
    async def porteiro(self, request: Request, call_next):
        ip = request.client.host if request.client else ""
        origem = self.origem(ip)
        caminho = request.url.path
        request.state.origem = origem
        if origem == "computador":
            return await call_next(request)
        if origem == "fora":
            return JSONResponse({"detail": "Acesso recusado."}, status_code=403)
        # celular pelo Tailscale
        if caminho.startswith(SO_NO_COMPUTADOR):
            if caminho.startswith("/api"):
                return JSONResponse({"detail": "Esta tela só abre no computador."}, status_code=403)
            return FileResponse(self.paginas / "so-no-computador.html", status_code=403)
        if caminho in LIVRES_NO_CELULAR or self.sessao_valida(request.cookies.get(COOKIE)):
            return await call_next(request)
        if caminho.startswith("/api"):
            return JSONResponse({"detail": "Entre com a senha do painel."}, status_code=401)
        return RedirectResponse("/entrar?volta=" + caminho, status_code=303)

r"""
Painel do robo-trade: http://127.0.0.1:8090

Le os dados do robo (API do Freqtrade, 127.0.0.1:8080) e mostra numa tela simples.
A senha da API fica so aqui no servidor; o navegador nunca a ve.

Ligar:  .\.venv\Scripts\python.exe painel\servidor.py
"""
import json
import sys
import threading
from datetime import datetime
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from acesso import COOKIE, DURACAO_SESSAO, Acesso

RAIZ = Path(__file__).resolve().parent.parent
USER_DATA = RAIZ / "user_data"
ARQ_PAUSA = USER_DATA / "PAUSAR"
CONFIG = json.loads((USER_DATA / "config.json").read_text(encoding="utf-8"))
API = CONFIG["api_server"]
BASE = f"http://{API['listen_ip_address']}:{API['listen_port']}/api/v1"
AUTH = (API["username"], API["password"])
PAGINAS = Path(__file__).parent

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
acesso = Acesso(USER_DATA / "painel_acesso.json", PAGINAS)
app.middleware("http")(acesso.porteiro)


@app.middleware("http")
async def sem_cache(request: Request, call_next):
    """Telas, estilo e scripts sempre na versao nova (o painel muda com frequencia; o iPhone guardava a velha)."""
    resposta = await call_next(request)
    tipo = resposta.headers.get("content-type", "")
    if tipo.startswith(("text/html", "text/css", "application/javascript", "text/javascript")):
        resposta.headers["Cache-Control"] = "no-cache"
    return resposta


# ---------------------------------------------------------------- acesso pelo celular (Tailscale)
@app.get("/entrar")
def pagina_entrar():
    return FileResponse(PAGINAS / "entrar.html")


@app.post("/api/entrar")
def entrar(corpo: dict, request: Request, x_painel: str | None = Header(default=None)):
    _exigir_painel(x_painel)
    ip = request.client.host if request.client else ""
    if not acesso.tem_senha():
        raise HTTPException(400, "A senha do painel ainda não foi criada. Crie no computador, em /senha.")
    if not acesso.pode_tentar(ip):
        raise HTTPException(429, "Muitas tentativas erradas. Espere 15 minutos.")
    if not acesso.conferir_senha(str(corpo.get("senha", ""))):
        acesso.registrar_erro(ip)
        raise HTTPException(401, "Senha errada.")
    resposta = JSONResponse({"ok": True})
    resposta.set_cookie(COOKIE, acesso.nova_sessao(), max_age=DURACAO_SESSAO, httponly=True, samesite="strict")
    return resposta


@app.post("/api/sair")
def sair(request: Request, x_painel: str | None = Header(default=None)):
    _exigir_painel(x_painel)
    acesso.encerrar_sessao(request.cookies.get(COOKIE))
    resposta = JSONResponse({"ok": True})
    resposta.delete_cookie(COOKIE)
    return resposta


@app.get("/senha")
def pagina_senha():
    return FileResponse(PAGINAS / "senha.html")


@app.get("/api/senha")
def status_senha():
    return {"tem_senha": acesso.tem_senha()}


@app.post("/api/senha")
def criar_senha(corpo: dict, x_painel: str | None = Header(default=None)):
    """So chega aqui pelo computador (o porteiro bloqueia o celular)."""
    _exigir_painel(x_painel)
    senha = str(corpo.get("senha", ""))
    if len(senha) < 8:
        raise HTTPException(400, "Use pelo menos 8 caracteres.")
    acesso.definir_senha(senha)
    return {"ok": True, "mensagem": "Senha do painel salva. Os celulares conectados vão precisar entrar de novo."}


@app.get("/manifest.json")
def manifesto():
    return JSONResponse({
        "name": "Robô de Trade", "short_name": "Robô", "start_url": "/terminal", "display": "standalone",
        "background_color": "#0D1117", "theme_color": "#0D1117", "lang": "pt-BR",
        "icons": [{"src": "/icone-180.png", "sizes": "180x180", "type": "image/png"},
                  {"src": "/icone.png", "sizes": "256x256", "type": "image/png"}],
    }, media_type="application/manifest+json")


@app.get("/icone-180.png")
def icone_180():
    return FileResponse(PAGINAS / "robo-180.png")


def _ler_json(caminho: Path):
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except Exception:
        return None


def _robo(cliente: httpx.Client, metodo: str, rota: str, **kw):
    r = cliente.request(metodo, BASE + rota, auth=AUTH, timeout=8, **kw)
    r.raise_for_status()
    return r.json()


def _exigir_painel(x_painel: str | None):
    # cabecalho proprio: outro site aberto no navegador nao consegue disparar as acoes
    if x_painel != "sim":
        raise HTTPException(403, "Acao permitida so pelo painel.")


@app.get("/")
def pagina():
    return FileResponse(Path(__file__).parent / "index.html")


@app.get("/terminal")
def terminal():
    return FileResponse(Path(__file__).parent / "terminal.html")


@app.get("/investidores")
def pagina_investidores():
    return FileResponse(Path(__file__).parent / "investidores.html")


@app.get("/estilo.css")
def estilo_css():
    return FileResponse(Path(__file__).parent / "estilo.css", media_type="text/css")


@app.get("/casca.js")
def casca_js():
    return FileResponse(Path(__file__).parent / "casca.js", media_type="text/javascript")


BINANCE = "https://api.binance.com/api/v3"
PARES = CONFIG["exchange"]["pair_whitelist"]
TEMPOS = {"1m", "5m", "15m", "1h", "4h", "1d"}
INDICADORES = ["ema50_1h", "ema200_1h", "bb_inferior", "rsi"]
_cache_mercado: dict = {"em": 0.0, "dados": None}


@app.get("/api/mercado")
def mercado():
    """Preco, variacao e volume de 24 h dos pares que o robo observa (cache de 5 s)."""
    import time

    if _cache_mercado["dados"] and time.time() - _cache_mercado["em"] < 5:
        return _cache_mercado["dados"]
    simbolos = json.dumps([p.replace("/", "") for p in PARES], separators=(",", ":"))
    r = httpx.get(f"{BINANCE}/ticker/24hr", params={"symbols": simbolos}, timeout=8)
    r.raise_for_status()
    por_simbolo = {t["symbol"]: t for t in r.json()}
    dados = []
    for par in PARES:
        t = por_simbolo.get(par.replace("/", ""))
        if t:
            dados.append({
                "par": par, "simbolo": t["symbol"], "preco": float(t["lastPrice"]),
                "var_24h": float(t["priceChangePercent"]), "max_24h": float(t["highPrice"]),
                "min_24h": float(t["lowPrice"]), "volume_brl": float(t["quoteVolume"]),
            })
    _cache_mercado.update(em=time.time(), dados=dados)
    return dados


@app.get("/api/candles")
def candles(par: str, tf: str = "15m", limite: int = 300):
    """Velas da Binance + (no 15m) os indicadores e sinais que o robo calculou."""
    if par not in PARES or tf not in TEMPOS:
        raise HTTPException(400, "Par ou tempo grafico invalido.")
    limite = max(50, min(limite, 1000))
    r = httpx.get(f"{BINANCE}/klines",
                  params={"symbol": par.replace("/", ""), "interval": tf, "limit": limite}, timeout=8)
    r.raise_for_status()
    velas = [{"t": k[0] // 1000, "o": float(k[1]), "h": float(k[2]), "l": float(k[3]),
              "c": float(k[4]), "v": float(k[7])} for k in r.json()]

    indicadores, sinais = {}, []
    if tf == "15m":
        try:
            with httpx.Client() as c:
                df = _robo(c, "GET", "/pair_candles", params={"pair": par, "timeframe": tf, "limit": limite})
            col = {nome: i for i, nome in enumerate(df["columns"])}
            ts = col.get("__date_ts")
            for nome in INDICADORES:
                if nome in col and ts is not None:
                    indicadores[nome] = [
                        {"t": linha[ts] // 1000, "v": linha[col[nome]]}
                        for linha in df["data"] if linha[col[nome]] is not None
                    ]
            for nome, tipo in (("enter_long", "compra"), ("exit_long", "venda")):
                if nome in col and ts is not None:
                    sinais += [{"t": linha[ts] // 1000, "tipo": tipo}
                               for linha in df["data"] if linha[col[nome]] == 1]
        except Exception:
            pass  # robo desligado: mostra so as velas
    return {"velas": velas, "indicadores": indicadores, "sinais": sorted(sinais, key=lambda s: s["t"])}


@app.get("/api/resumo")
def resumo():
    dados = {
        "robo_ligado": False,
        "guarda": _ler_json(USER_DATA / "guarda_status.json"),
        "pausa_arquivo": ARQ_PAUSA.read_text(encoding="utf-8").strip() if ARQ_PAUSA.exists() else None,
        "radar": _ler_json(USER_DATA / "radar_moedas.json"),
        "saldo_inicial": _modo().get("available_capital") or CONFIG.get("dry_run_wallet"),
        "saldo_minimo": (_modo().get("guarda") or CONFIG.get("guarda", {})).get("saldo_minimo"),
        "max_operacoes": CONFIG.get("max_open_trades"),
    }
    try:
        with httpx.Client() as c:
            cfg = _robo(c, "GET", "/show_config")
            dados.update(
                robo_ligado=True,
                estado=cfg.get("state"),
                dry_run=cfg.get("dry_run"),
                estrategia=cfg.get("strategy"),
                stoploss=cfg.get("stoploss"),
                saldo=_robo(c, "GET", "/balance"),
                abertas=_robo(c, "GET", "/status"),
                lucro=_robo(c, "GET", "/profit"),
                operacoes=_robo(c, "GET", "/trades", params={"limit": 30})["trades"],
                travas=_robo(c, "GET", "/locks")["locks"],
                diario=_robo(c, "GET", "/daily", params={"timescale": 14})["data"],
            )
    except Exception as erro:
        dados["erro_robo"] = str(erro)
    return dados


@app.post("/api/pausar")
def pausar(x_painel: str | None = Header(default=None)):
    _exigir_painel(x_painel)
    ARQ_PAUSA.write_text(
        f"Pausado no painel em {datetime.now():%d/%m %H:%M}.", encoding="utf-8"
    )
    return {"ok": True, "mensagem": "Compras pausadas. As moedas abertas continuam protegidas pelo stop."}


@app.post("/api/retomar")
def retomar(x_painel: str | None = Header(default=None)):
    _exigir_painel(x_painel)
    ARQ_PAUSA.unlink(missing_ok=True)
    try:
        with httpx.Client() as c:
            if _robo(c, "GET", "/show_config").get("state") != "running":
                _robo(c, "POST", "/start")
    except Exception:
        return {"ok": True, "mensagem": "Pausa retirada, mas o robo esta desligado. Ligue o iniciar-robo.ps1."}
    guarda = _ler_json(USER_DATA / "guarda_status.json") or {}
    if guarda.get("patrimonio") is not None and guarda["patrimonio"] < (guarda.get("saldo_minimo") or 0):
        return {
            "ok": True,
            "mensagem": "Retomado, mas o saldo ainda esta abaixo do piso: o robo vai pausar de novo. "
            "Aumente o piso no config ou revise a estrategia.",
        }
    return {"ok": True, "mensagem": "Compras retomadas."}


@app.post("/api/vender-tudo")
def vender_tudo(x_painel: str | None = Header(default=None)):
    _exigir_painel(x_painel)
    ARQ_PAUSA.write_text(
        f"Tudo vendido e pausado no painel em {datetime.now():%d/%m %H:%M}.", encoding="utf-8"
    )
    try:
        with httpx.Client() as c:
            _robo(c, "POST", "/forceexit", json={"tradeid": "all"})
    except Exception as erro:
        raise HTTPException(502, f"Compras pausadas, mas a venda falhou: {erro}")
    return {"ok": True, "mensagem": "Ordens de venda enviadas para todas as moedas. Compras pausadas."}


PASTA_RELATORIOS = RAIZ / "docs" / "relatorios"


@app.get("/relatorios")
def pagina_relatorios():
    return FileResponse(Path(__file__).parent / "relatorios.html")


@app.get("/api/relatorios")
def relatorios():
    """Datas dos relatorios diarios, do mais novo para o mais velho."""
    import re

    if not PASTA_RELATORIOS.exists():
        return []
    datas = [a.stem for a in PASTA_RELATORIOS.glob("*.md") if re.fullmatch(r"\d{4}-\d{2}-\d{2}", a.stem)]
    return sorted(datas, reverse=True)


@app.get("/api/relatorios/{data}")
def relatorio(data: str):
    import re

    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", data):
        raise HTTPException(400, "Data inválida.")
    arquivo = PASTA_RELATORIOS / f"{data}.md"
    if not arquivo.exists():
        raise HTTPException(404, "Relatório não encontrado.")
    return {"data": data, "texto": arquivo.read_text(encoding="utf-8")}


@app.get("/api/consulta")
def consulta(par: str):
    """As regras do robo aplicadas agora ao par (scripts/consulta.py)."""
    import sys

    if par not in PARES:
        raise HTTPException(400, "Par fora da lista do robô.")
    sys.path.insert(0, str(RAIZ / "scripts"))
    from consulta import consultar

    return consultar(par)


# ---------------------------------------------------------------- acoes EUA (Alpaca, conta de PAPEL)
ARQ_ALPACA = USER_DATA / "alpaca.json"          # chaves da Alpaca; so nesta maquina (fora do git)
ALPACA_PAPEL = "https://paper-api.alpaca.markets/v2"   # so o endereco de papel: chave real nao funciona aqui


def _alpaca(rota: str, chaves: dict, **params):
    r = httpx.get(ALPACA_PAPEL + rota, params=params or None, timeout=10, headers={
        "APCA-API-KEY-ID": chaves["key"], "APCA-API-SECRET-KEY": chaves["secret"]})
    if r.status_code in (401, 403):
        raise HTTPException(400, "A Alpaca recusou a chave. Ela precisa ser de conta de PAPEL (Paper Trading).")
    r.raise_for_status()
    return r.json()


@app.get("/acoes")
def pagina_acoes():
    return FileResponse(PAGINAS / "acoes.html")


@app.get("/api/alpaca")
def alpaca():
    chaves = _ler_json(ARQ_ALPACA)
    carteira_buffett = _ler_json(RAIZ / "acoes-eua" / "trader" / "targets.json")
    base = {"conectada": False, "referencia": carteira_buffett}
    if not chaves:
        return base
    try:
        conta = _alpaca("/account", chaves)
        posicoes = _alpaca("/positions", chaves)
        ordens = _alpaca("/orders", chaves, status="all", limit=20, direction="desc")
    except HTTPException as erro:
        return {**base, "erro": erro.detail}
    except Exception as erro:
        return {**base, "erro": f"Não foi possível falar com a Alpaca agora: {erro}"}
    campos = ("status", "currency", "equity", "last_equity", "cash", "buying_power", "portfolio_value")
    return {
        **base, "conectada": True, "papel": True, "final_chave": chaves["key"][-4:],
        "conta": {c: conta.get(c) for c in campos},
        "posicoes": [{c: p.get(c) for c in ("symbol", "qty", "avg_entry_price", "current_price", "market_value",
                                              "unrealized_pl", "unrealized_plpc", "change_today")} for p in posicoes],
        "ordens": [{c: o.get(c) for c in ("symbol", "side", "type", "qty", "notional", "filled_qty",
                                            "filled_avg_price", "status", "submitted_at")} for o in ordens],
    }


@app.get("/api/acoes")
def acoes_corretora_ativa():
    """A carteira de acoes na corretora em uso (Alpaca ou IBKR), no mesmo formato da /api/alpaca.
    E o que a tela Acoes EUA, a tela inicial e o Telegram leem."""
    sys.path.insert(0, str(RAIZ / "scripts"))
    import corretoras

    cfg = corretoras.config()
    if cfg["acoes"] != "ibkr":
        return {**alpaca(), "corretora": "alpaca", "corretora_nome": "Alpaca"}
    return _ibkr_cache()


_IBKR_TRAVA = threading.Lock()
_IBKR_ULTIMO: dict = {"em": 0.0, "dados": None}


def _ibkr_cache() -> dict:
    """Uma conexao por vez com o IB Gateway e resposta guardada por 20 s (o Telegram consulta a cada 30 s)."""
    import time as _t

    with _IBKR_TRAVA:
        if _IBKR_ULTIMO["dados"] and _t.time() - _IBKR_ULTIMO["em"] < 20:
            return _IBKR_ULTIMO["dados"]
        import corretoras

        base = {"conectada": False, "corretora": "ibkr", "corretora_nome": "Interactive Brokers",
                "referencia": _ler_json(RAIZ / "acoes-eua" / "trader" / "targets.json")}
        c = corretoras.corretora_acoes("painel")
        try:
            conta = c.conta()
            dados = {**base, "conectada": True, "papel": True, "final_chave": conta["id"],
                     "conta": {"status": "ACTIVE", "currency": "USD", "equity": str(conta["equity"]),
                               "cash": str(conta["cash"]), "portfolio_value": str(conta["equity"])},
                     "posicoes": [{k: (str(v) if isinstance(v, float) else v) for k, v in p.items()} for p in c.posicoes()],
                     "ordens": c.ordens()}
        except Exception as erro:
            dados = {**base, "erro": str(erro)}
        finally:
            c.fechar()
        _IBKR_ULTIMO.update(em=_t.time(), dados=dados)
        return dados


def _registrar_historico(forcar: bool = False) -> dict:
    """Ponto de hoje de cada tipo (scripts/historico.py). Na mesma trava da IBKR: uma conexao por vez."""
    sys.path.insert(0, str(RAIZ / "scripts"))
    import historico

    h = historico.ler(historico.ARQ, {})
    em = h.get("atualizado_em")
    velho = not em or (datetime.now() - datetime.fromisoformat(em)).total_seconds() > 600
    if forcar or velho:
        with _IBKR_TRAVA:
            h = historico.registrar()
    return h


@app.get("/api/ganhos")
def ver_ganhos(periodo: str = "tudo", de: str | None = None, ate: str | None = None):
    """Quanto ganhou por tipo de investimento e no total, num periodo (7d, 30d, mes, ano, tudo ou de/ate)."""
    import historico

    h = _registrar_historico()
    try:
        inicio, fim = historico.periodo(periodo, de, ate)
        datetime.fromisoformat(inicio), datetime.fromisoformat(fim)
    except ValueError:
        raise HTTPException(400, "Datas inválidas.")
    if inicio > fim:
        raise HTTPException(400, "A data inicial é depois da final.")
    return {**historico.ganhos(h, inicio, fim), "periodo": periodo if not (de and ate) else "personalizado"}


@app.get("/api/corretora")
def ver_corretora():
    sys.path.insert(0, str(RAIZ / "scripts"))
    import corretoras

    return {**corretoras.config(), "flex": (USER_DATA / "ibkr_flex.json").exists()}


@app.post("/api/corretora")
def trocar_corretora(corpo: dict, x_painel: str | None = Header(default=None)):
    """So pelo computador. Trocar para a IBKR so grava depois de conectar de verdade na conta de PAPEL."""
    _exigir_painel(x_painel)
    sys.path.insert(0, str(RAIZ / "scripts"))
    import corretoras

    acoes = corpo.get("acoes")
    if acoes not in ("alpaca", "ibkr"):
        raise HTTPException(400, "Escolha Alpaca ou Interactive Brokers.")
    porta = int(corpo.get("porta") or 4002)
    if acoes == "ibkr":
        if porta not in corretoras.PORTAS_PAPEL_IBKR:
            raise HTTPException(400, "Só as portas de papel: 4002 (IB Gateway) ou 7497 (TWS).")
        with _IBKR_TRAVA:
            c = corretoras.Ibkr(porta=porta, uso="teste")
            try:
                conta = c.conta()
            except Exception as erro:
                raise HTTPException(400, str(erro))
            finally:
                c.fechar()
        msg = (f"Conectado na conta de papel da IBKR (final {conta['id']}). Caixa em dólar: US$ {conta['cash']:,.2f}. "
               "A carteira de consenso passa a ser montada lá na próxima conferência com a bolsa aberta.")
    else:
        msg = "Ações de volta na Alpaca (conta de papel)."
    corretoras.ARQ_CONFIG.write_text(json.dumps({"acoes": acoes, "ibkr": {"porta": porta}}), encoding="utf-8")
    _IBKR_ULTIMO.update(em=0.0, dados=None)
    return {"ok": True, "mensagem": msg}


@app.post("/api/ibkr/flex")
def salvar_flex(corpo: dict, x_painel: str | None = Header(default=None)):
    """Token e numero do Flex Query (dividendos para o relatorio de imposto). So pelo computador."""
    _exigir_painel(x_painel)
    token, consulta = str(corpo.get("token", "")).strip(), str(corpo.get("query", "")).strip()
    if len(token) < 10 or not consulta.isdigit():
        raise HTTPException(400, "Cole o token inteiro e o número da consulta (Query ID, só números).")
    (USER_DATA / "ibkr_flex.json").write_text(json.dumps({"token": token, "query": consulta}), encoding="utf-8")
    return {"ok": True, "mensagem": "Flex Query salvo neste computador. O relatório de imposto vai buscar os dividendos nele."}


@app.delete("/api/ibkr/flex")
def apagar_flex(x_painel: str | None = Header(default=None)):
    _exigir_painel(x_painel)
    (USER_DATA / "ibkr_flex.json").unlink(missing_ok=True)
    return {"ok": True, "mensagem": "Flex Query apagado deste computador."}


PASTA_TRADER = RAIZ / "acoes-eua" / "trader"
ARQ_ENVIOS = PASTA_TRADER / "state" / "painel_envios.json"
CAMPOS_SIMPLES = ("symbol", "side", "qty", "notional", "type", "time_in_force", "limit_price", "stop_price",
                  "extended_hours")
CAMPOS_ALPACA = CAMPOS_SIMPLES + ("trail_price", "trail_percent", "client_order_id", "order_class",
                                  "take_profit_limit_price", "stop_loss_stop_price", "stop_loss_limit_price",
                                  "advanced_instructions")


def _impressao(ordem: dict) -> str:
    """A mesma 'impressao digital' da trader-risk (check.py): prova que a ordem e a que foi checada."""
    import hashlib

    nucleo = {k: ordem[k] for k in CAMPOS_ALPACA if k in ordem and ordem[k] is not None}
    texto = json.dumps(nucleo, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()[:16]


def _propostas() -> list[dict]:
    ordens = (_ler_json(PASTA_TRADER / "orders.json") or {}).get("orders", [])
    risco = _ler_json(PASTA_TRADER / "state" / "risk.json") or {}
    risco_hoje = risco.get("date") == datetime.now().date().isoformat()
    vereditos = {r["fingerprint"]: r for r in risco.get("results", [])} if risco_hoje else {}
    enviadas = _ler_json(ARQ_ENVIOS) or {}
    lista = []
    for i, o in enumerate(ordens, start=1):
        impressao = _impressao(o)
        v = vereditos.get(impressao)
        envio = enviadas.get(impressao)
        if envio:
            estado = "enviada"
        elif not v:
            estado = "sem_checagem"
        elif v["verdict"] != "PASS":
            estado = "bloqueada"
        elif any(k not in CAMPOS_SIMPLES for k in o if k in CAMPOS_ALPACA and o[k] is not None):
            estado = "avancada"
        else:
            estado = "pronta"
        lista.append({"indice": i, "impressao": impressao, "estado": estado, "ordem": {k: o.get(k) for k in CAMPOS_SIMPLES if o.get(k) is not None},
                      "motivo": o.get("why"), "risco": (v or {}).get("reasons", []), "envio": envio})
    return lista


@app.get("/api/alpaca/propostas")
def propostas():
    return {"ordens": _propostas(), "fonte": (_ler_json(PASTA_TRADER / "orders.json") or {}).get("source")}


@app.post("/api/alpaca/enviar")
def enviar_ordem(corpo: dict, x_painel: str | None = Header(default=None)):
    """Envia UMA ordem aprovada para a conta de PAPEL, so quando o dono clica (o 'sim' dele)."""
    _exigir_painel(x_painel)
    chaves = _ler_json(ARQ_ALPACA)
    if not chaves:
        raise HTTPException(400, "Conecte a conta de papel da Alpaca primeiro.")
    alvo = next((p for p in _propostas() if p["impressao"] == corpo.get("impressao")), None)
    if not alvo:
        raise HTTPException(400, "Essa ordem mudou ou não existe mais. Atualize a tela.")
    if alvo["estado"] != "pronta":
        raise HTTPException(400, {"enviada": "Essa ordem já foi enviada.",
                                  "sem_checagem": "A checagem de risco de hoje ainda não passou por essa ordem.",
                                  "bloqueada": "A checagem de risco bloqueou essa ordem.",
                                  "avancada": "Ordem avançada: envie direto pela corretora."}[alvo["estado"]])
    r = httpx.post(ALPACA_PAPEL + "/orders", json=alvo["ordem"], timeout=15, headers={
        "APCA-API-KEY-ID": chaves["key"], "APCA-API-SECRET-KEY": chaves["secret"]})
    if r.status_code >= 400:
        raise HTTPException(400, f"A Alpaca recusou a ordem: {r.json().get('message', r.text)}")
    resposta = r.json()
    enviadas = _ler_json(ARQ_ENVIOS) or {}
    enviadas[alvo["impressao"]] = {"em": datetime.now().isoformat(timespec="seconds"), "id": resposta.get("id"),
                                   "status": resposta.get("status"), "ordem": alvo["ordem"], "conta": "papel"}
    ARQ_ENVIOS.parent.mkdir(parents=True, exist_ok=True)
    ARQ_ENVIOS.write_text(json.dumps(enviadas, indent=2), encoding="utf-8")
    o = alvo["ordem"]
    valor = f"US$ {o['notional']}" if o.get("notional") else f"{o.get('qty')} ações"
    return {"ok": True, "mensagem": f"Enviada para a conta de papel: {'compra' if o['side'] == 'buy' else 'venda'} de {valor} de {o['symbol']}."}


# ---------------------------------------------------------------- Telegram (avisos e comandos do robo)
# O bot e do PAINEL (painel/telegram_bot.py: menu com botoes, avisos em portugues). O Telegram do
# Freqtrade fica desligado: dois programas nao podem ler o mesmo bot ao mesmo tempo.
ARQ_TELEGRAM = USER_DATA / "telegram.json"                 # lido pelo Freqtrade: sempre desligado
ARQ_TELEGRAM_PAINEL = USER_DATA / "telegram_painel.json"   # codigo do bot, conversa e nome (so o painel le)
DESLIGADO_FREQTRADE = {"telegram": {"enabled": False, "token": "", "chat_id": ""}}


def _migrar_telegram():
    """Quem ligou o Telegram antes do bot do painel: o codigo passa para o painel e o Freqtrade desliga."""
    t = (_ler_json(ARQ_TELEGRAM) or {}).get("telegram", {})
    if t.get("enabled") and t.get("token"):
        if not ARQ_TELEGRAM_PAINEL.exists():
            info = _ler_json(USER_DATA / "telegram_info.json") or {}
            ARQ_TELEGRAM_PAINEL.write_text(json.dumps({"token": t["token"], "chat_id": str(t["chat_id"]),
                                                       "bot": info.get("bot"), "conectado_em": info.get("conectado_em")}),
                                           encoding="utf-8")
        ARQ_TELEGRAM.write_text(json.dumps(DESLIGADO_FREQTRADE), encoding="utf-8")
        _recarregar_robo()


@app.get("/api/telegram")
def status_telegram():
    t = _ler_json(ARQ_TELEGRAM_PAINEL) or {}
    return {"ligado": bool(t.get("token")), "bot": t.get("bot"), "conectado_em": t.get("conectado_em")}


@app.post("/api/telegram")
def ligar_telegram(corpo: dict, x_painel: str | None = Header(default=None)):
    """So pelo computador. Confere o codigo do bot, acha a conversa do dono e manda uma mensagem de teste."""
    _exigir_painel(x_painel)
    token = str(corpo.get("token", "")).strip()
    if ":" not in token or len(token) < 30:
        raise HTTPException(400, "Cole o código completo que o BotFather mandou (tem dois-pontos no meio).")
    api = f"https://api.telegram.org/bot{token}"
    eu = httpx.get(f"{api}/getMe", timeout=10).json()
    if not eu.get("ok"):
        raise HTTPException(400, "O Telegram recusou esse código. Confira se copiou inteiro.")
    conversas = [u["message"]["chat"] for u in httpx.get(f"{api}/getUpdates", timeout=10).json().get("result", [])
                 if u.get("message", {}).get("chat", {}).get("type") == "private"]
    if not conversas:
        raise HTTPException(400, f"Abra o seu bot @{eu['result']['username']} no Telegram, toque em Iniciar "
                                 "(ou mande /start) e depois clique em Ligar de novo.")
    chat = conversas[-1]
    teste = httpx.post(f"{api}/sendMessage", timeout=10, json={
        "chat_id": chat["id"], "text": "Robô de Trade conectado. Mande /menu a qualquer momento para abrir os botões."}).json()
    if not teste.get("ok"):
        raise HTTPException(400, "Não consegui mandar a mensagem de teste. Mande /start para o bot e tente de novo.")
    ARQ_TELEGRAM_PAINEL.write_text(json.dumps({"token": token, "chat_id": str(chat["id"]), "bot": eu["result"]["username"],
                                               "conectado_em": datetime.now().isoformat(timespec="seconds")}), encoding="utf-8")
    ARQ_TELEGRAM.write_text(json.dumps(DESLIGADO_FREQTRADE), encoding="utf-8")
    _recarregar_robo()
    return {"ok": True, "mensagem": f"Telegram ligado no bot @{eu['result']['username']}, conversa de {chat.get('first_name', 'você')}."}


@app.delete("/api/telegram")
def desligar_telegram(x_painel: str | None = Header(default=None)):
    _exigir_painel(x_painel)
    ARQ_TELEGRAM_PAINEL.unlink(missing_ok=True)
    (USER_DATA / "telegram_info.json").unlink(missing_ok=True)
    ARQ_TELEGRAM.write_text(json.dumps(DESLIGADO_FREQTRADE), encoding="utf-8")
    _recarregar_robo()
    return {"ok": True, "mensagem": "Telegram desligado e código apagado deste computador."}


@app.get("/api/investidores")
def investidores():
    """O que o vigia (scripts/vigia_investidores.py) viu: ultimo 13F de cada investidor e as novidades."""
    estado = _ler_json(USER_DATA / "investidores_estado.json") or {}
    return {"investidores": list(estado.values()), "novidades": (_ler_json(USER_DATA / "investidores_novidades.json") or [])[:10]}


def _vigia_em_segundo_plano():
    """Confere a SEC a cada 6 h enquanto o painel estiver ligado (13F sai 1x por trimestre)."""
    import subprocess
    import sys
    import threading
    import time

    def laco():
        time.sleep(60)  # deixa o painel subir primeiro
        while True:
            try:
                subprocess.run([sys.executable, str(RAIZ / "scripts" / "vigia_investidores.py")], cwd=RAIZ,
                               capture_output=True, timeout=1800)
            except Exception:
                pass
            time.sleep(6 * 3600)

    threading.Thread(target=laco, daemon=True, name="vigia-investidores").start()

    def consenso():
        """Carteira de consenso (conta de papel): confere de hora em hora; so troca quando a lista muda.
        Uma vez por dia baixa antes os 13F novos da SEC."""
        ultima_sec = 0.0
        time.sleep(120)
        while True:
            usa_ibkr = (_ler_json(USER_DATA / "corretora.json") or {}).get("acoes") == "ibkr"
            if usa_ibkr or (USER_DATA / "alpaca.json").exists():
                args = [sys.executable, str(RAIZ / "scripts" / "consenso_automatico.py")]
                if time.time() - ultima_sec > 20 * 3600:
                    args.append("--atualizar13f")
                    ultima_sec = time.time()
                try:
                    r = subprocess.run(args, cwd=RAIZ, capture_output=True, timeout=1800, encoding="utf-8")
                    (USER_DATA / "logs" / "consenso.log").open("a", encoding="utf-8").write(
                        f"\n== {time.strftime('%d/%m %H:%M')}\n" + (r.stdout or "")[-1500:] + (r.stderr or "")[-800:])
                except Exception:
                    pass
            time.sleep(3600)

    threading.Thread(target=consenso, daemon=True, name="carteira-consenso").start()

    def historico_horario():
        """Um ponto por hora do patrimonio de cada tipo (o grafico de ganhos usa o ultimo de cada dia)."""
        time.sleep(90)
        while True:
            try:
                _registrar_historico(forcar=True)
            except Exception:
                pass
            time.sleep(3600)

    threading.Thread(target=historico_horario, daemon=True, name="historico").start()


@app.post("/api/alpaca/chave")
def salvar_alpaca(corpo: dict, x_painel: str | None = Header(default=None)):
    """So pelo computador (o porteiro bloqueia o celular)."""
    _exigir_painel(x_painel)
    chaves = {"key": str(corpo.get("key", "")).strip(), "secret": str(corpo.get("secret", "")).strip()}
    if len(chaves["key"]) < 10 or len(chaves["secret"]) < 20:
        raise HTTPException(400, "Cole a API Key ID e a Secret Key completas.")
    conta = _alpaca("/account", chaves)  # recusa chave de conta real: ela nao funciona no endereco de papel
    ARQ_ALPACA.write_text(json.dumps({**chaves, "salva_em": datetime.now().isoformat(timespec="seconds")}),
                          encoding="utf-8")
    return {"ok": True, "mensagem": f"Conta de papel conectada. Patrimônio fictício: US$ {float(conta['equity']):,.2f}."}


@app.delete("/api/alpaca/chave")
def apagar_alpaca(x_painel: str | None = Header(default=None)):
    _exigir_painel(x_painel)
    ARQ_ALPACA.unlink(missing_ok=True)
    return {"ok": True, "mensagem": "Chaves da Alpaca apagadas deste computador."}


# ---------------------------------------------------------------- conta (dinheiro real)
ARQ_CONTA = USER_DATA / "conta.json"   # chave da Binance; fica so nesta maquina (fora do git)
ARQ_MODO = USER_DATA / "modo.json"     # {"dry_run": true} ou o modo real com o valor liberado
FRASE_REAL = "QUERO USAR DINHEIRO REAL"
DIAS_MINIMOS_TESTE = 21
VALOR_MINIMO_REAL = 30


def _modo() -> dict:
    return _ler_json(ARQ_MODO) or {"dry_run": True}


def _validar_chave(key: str, secret: str) -> dict:
    import ccxt

    ex = ccxt.binance({"apiKey": key, "secret": secret, "enableRateLimit": True})
    try:
        saldo = ex.fetch_balance()
        restr = ex.sapi_get_account_apirestrictions()
    except ccxt.AuthenticationError:
        raise HTTPException(400, "A Binance recusou a chave. Confira se copiou a chave e o segredo inteiros.")
    except ccxt.PermissionDenied:
        raise HTTPException(400, "A chave não tem permissão de leitura, ou o IP desta máquina não está liberado nela.")
    except Exception as erro:
        raise HTTPException(502, f"Não foi possível falar com a Binance agora: {erro}")
    ativos = {k: v for k, v in (saldo.get("total") or {}).items() if v}
    return {
        "permite_saque": bool(restr.get("enableWithdrawals")),
        "permite_trade": bool(restr.get("enableSpotAndMarginTrading")),
        "ip_restrito": bool(restr.get("ipRestrict")),
        "saldo_brl": float(ativos.get("BRL", 0)),
        "ativos": ativos,
    }


def _teste() -> dict:
    """Ha quantos dias o teste roda e como esta o resultado dele (banco do dry-run)."""
    import sqlite3
    import time

    banco = USER_DATA.parent / "tradesv3.dryrun.sqlite"
    if not banco.exists():
        return {"dias": 0, "operacoes": 0, "resultado": 0.0}
    info = banco.stat()
    dias = (time.time() - getattr(info, "st_birthtime", info.st_ctime)) / 86400
    with sqlite3.connect(f"file:{banco}?mode=ro", uri=True) as con:
        n, lucro = con.execute(
            "SELECT COUNT(*), COALESCE(SUM(close_profit_abs), 0) FROM trades WHERE is_open = 0"
        ).fetchone()
    return {"dias": round(dias, 1), "operacoes": n, "resultado": round(lucro, 2)}


def _recarregar_robo() -> bool:
    try:
        with httpx.Client() as c:
            _robo(c, "POST", "/reload_config")
        return True
    except Exception:
        return False


@app.get("/conta")
def pagina_conta():
    return FileResponse(Path(__file__).parent / "conta.html")


@app.get("/icone.png")
def icone():
    return FileResponse(Path(__file__).parent / "robo.png")


@app.get("/api/conta")
def conta():
    dados = _ler_json(ARQ_CONTA)
    modo = _modo()
    resposta = {
        "modo": "teste" if modo.get("dry_run", True) else "real",
        "valor_liberado": modo.get("available_capital"),
        "chave": None,
        "teste": _teste(),
        "dias_minimos": DIAS_MINIMOS_TESTE,
        "valor_minimo": VALOR_MINIMO_REAL,
        "frase": FRASE_REAL,
    }
    if dados:
        resposta["chave"] = {"final": dados["key"][-4:], "validada_em": dados.get("validada_em")}
        try:
            resposta["chave"].update(_validar_chave(dados["key"], dados["secret"]))
        except HTTPException as erro:
            resposta["chave"]["erro"] = erro.detail
    return resposta


@app.post("/api/conta/chave")
def salvar_chave(corpo: dict, x_painel: str | None = Header(default=None)):
    _exigir_painel(x_painel)
    key, secret = str(corpo.get("key", "")).strip(), str(corpo.get("secret", "")).strip()
    if len(key) < 20 or len(secret) < 20:
        raise HTTPException(400, "Cole a chave (API Key) e o segredo (Secret Key) completos.")
    info = _validar_chave(key, secret)
    if info["permite_saque"]:
        raise HTTPException(400, "Essa chave permite SAQUE. Por segurança ela não foi salva. "
                                 "Na Binance, desmarque \"Permitir saques\" (ou crie outra chave) e tente de novo.")
    if not info["permite_trade"]:
        raise HTTPException(400, "Essa chave não permite negociar. Na Binance, marque "
                                 "\"Permitir negociação spot e de margem\" e tente de novo.")
    ARQ_CONTA.write_text(json.dumps(
        {"key": key, "secret": secret, "validada_em": datetime.now().isoformat(timespec="seconds")}
    ), encoding="utf-8")
    return {"ok": True, "mensagem": "Chave conferida e salva só neste computador.", **info}


@app.delete("/api/conta/chave")
def apagar_chave(x_painel: str | None = Header(default=None)):
    _exigir_painel(x_painel)
    if not _modo().get("dry_run", True):
        raise HTTPException(400, "Volte para o modo de teste antes de apagar a chave.")
    ARQ_CONTA.unlink(missing_ok=True)
    return {"ok": True, "mensagem": "Chave apagada deste computador."}


@app.post("/api/conta/modo")
def trocar_modo(corpo: dict, x_painel: str | None = Header(default=None)):
    _exigir_painel(x_painel)
    if corpo.get("modo") == "teste":
        ARQ_MODO.write_text(json.dumps({"dry_run": True}), encoding="utf-8")
        ok = _recarregar_robo()
        return {"ok": True, "mensagem": "Voltou para o teste com saldo fictício." if ok
                else "Modo de teste gravado. Abra o robô pelo ícone para valer."}

    # ligar com dinheiro real: todas as travas abaixo precisam passar
    dados = _ler_json(ARQ_CONTA)
    if not dados:
        raise HTTPException(400, "Cadastre e confira a chave da Binance primeiro.")
    info = _validar_chave(dados["key"], dados["secret"])
    teste = _teste()
    problemas = []
    if info["permite_saque"]:
        problemas.append("a chave passou a permitir saque")
    if not info["permite_trade"]:
        problemas.append("a chave não permite negociar")
    if teste["dias"] < DIAS_MINIMOS_TESTE:
        problemas.append(f"o teste roda há {teste['dias']:.0f} dias (o mínimo é {DIAS_MINIMOS_TESTE})")
    try:
        valor = float(corpo.get("valor", 0))
    except (TypeError, ValueError):
        valor = 0
    if valor < VALOR_MINIMO_REAL:
        problemas.append(f"o valor liberado precisa ser de pelo menos R$ {VALOR_MINIMO_REAL}")
    if valor > info["saldo_brl"]:
        problemas.append(f"o saldo em real na Binance é R$ {info['saldo_brl']:.2f}, menor que o valor liberado")
    if not (corpo.get("li_aula") and corpo.get("aceito_perder")):
        problemas.append("faltam as duas confirmações")
    if str(corpo.get("frase", "")).strip().upper() != FRASE_REAL:
        problemas.append("a frase de confirmação não confere")
    if problemas:
        raise HTTPException(400, "Ainda não dá para ligar: " + "; ".join(problemas) + ".")

    ARQ_MODO.write_text(json.dumps({
        "dry_run": False,
        "available_capital": round(valor, 2),
        "guarda": {"saldo_minimo": round(valor * 2 / 3, 2)},
        "exchange": {"key": dados["key"], "secret": dados["secret"]},
    }), encoding="utf-8")
    ok = _recarregar_robo()
    return {"ok": True, "mensagem": (
        f"Robô ligado com dinheiro real, usando até R$ {valor:.2f}. "
        f"Ele pausa sozinho se esse valor cair abaixo de R$ {valor * 2 / 3:.2f}."
    ) if ok else "Modo real gravado. Feche e abra o robô pelo ícone para valer."}


if __name__ == "__main__":
    import sys

    if sys.stdout is None or sys.stderr is None:  # pythonw (oculto): sem console, o log vai para arquivo
        (USER_DATA / "logs").mkdir(exist_ok=True)
        sys.stdout = sys.stderr = open(USER_DATA / "logs" / "painel.log", "a", encoding="utf-8", buffering=1)
    _vigia_em_segundo_plano()
    _migrar_telegram()
    from telegram_bot import BotTelegram

    BotTelegram(USER_DATA).iniciar()
    # 0.0.0.0 para o celular chegar pelo Tailscale; o porteiro (acesso.py) recusa qualquer outra origem
    uvicorn.run(app, host="0.0.0.0", port=8090, log_level="warning")

"""
Bot do Telegram do robo-trade (aula 10): menu com botoes, avisos em portugues e confirmacao para
o que mexe em dinheiro. Roda dentro do painel, em duas linhas de execucao:
  - "escuta": recebe botoes e comandos (getUpdates), so da conversa do dono;
  - "avisos": a cada 30 s olha o painel (/api/...) e manda so as novidades escolhidas em "Avisos".
Fala com o resto do sistema pelas rotas do proprio painel (127.0.0.1:8090), como a tela faz.

Arquivos (user_data/, fora do git):
  telegram_painel.json  codigo do bot e conversa (gravado pela tela Conta)
  telegram_avisos.json  quais avisos ligados
  telegram_estado.json  o que ja foi avisado (para nao repetir depois de reiniciar)
"""
import html
import json
import threading
import time
from datetime import datetime
from pathlib import Path

import httpx

PAINEL = "http://127.0.0.1:8090"
CAB = {"X-Painel": "sim"}
AVISOS_PADRAO = {"operacoes": True, "travas": True, "investidores": True, "acoes": True, "queda_acoes": True,
                 "resumo_diario": True}
NOMES_AVISOS = {"operacoes": "Compras e vendas (cripto)", "travas": "Travas e pausas", "investidores": "Relatório novo de investidor",
                "acoes": "Ordens de ações executadas", "queda_acoes": "Queda forte das ações (−20%)",
                "resumo_diario": "Resumo do dia às 20h"}
# Queda da carteira de acoes a partir do maior valor (planejamento-dinheiro-real.md, secao 6): avisa, nao vende.
QUEDA_NIVEIS = (-20.0, -30.0, -40.0)
QUEDA_REARMA = -10.0  # voltou para menos de 10% abaixo do topo: os avisos valem de novo
SAIDAS = {"roi": "alvo de lucro", "stop_loss": "stop", "trailing_stop_loss": "stop móvel", "exit_signal": "sinal de saída",
          "rsi_esticado": "sinal de saída", "force_exit": "venda manual", "emergency_exit": "emergência"}
CONFIRMA_SEG = 300


def brl(v) -> str:
    return "R$ " + f"{float(v or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def usd(v) -> str:
    return "US$ " + f"{float(v or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(v) -> str:
    v = float(v or 0)
    return ("+" if v > 0 else "") + f"{v:.2f}".replace(".", ",") + "%"


def e(t) -> str:
    return html.escape(str(t if t is not None else ""))


def avaliar_queda(valor: float, est: dict) -> str | None:
    """Atualiza o topo da carteira em `est` e devolve o aviso quando a queda passa de um nivel novo.
    So avisa na 2a leitura seguida abaixo do nivel (uma cotacao errada isolada nao dispara)."""
    pico = max(float(est.get("acoes_pico") or 0), valor)
    est["acoes_pico"] = pico
    queda = (valor / pico - 1) * 100 if pico else 0.0
    nivel = float(est.get("acoes_nivel") or 0)
    if queda > QUEDA_REARMA:
        est["acoes_nivel"], est["acoes_abaixo"] = 0, None
        return None
    novo = min([n for n in QUEDA_NIVEIS if queda <= n and n < nivel], default=None)
    if novo is None:
        est["acoes_abaixo"] = None
        return None
    if est.get("acoes_abaixo") != novo:  # 1a leitura abaixo: espera confirmar
        est["acoes_abaixo"] = novo
        return None
    est["acoes_nivel"], est["acoes_abaixo"] = novo, None
    return (f"📉 <b>Ações EUA caíram {pct(queda)} desde o topo</b>\n"
            f"Topo: {usd(pico)} · agora: {usd(valor)}\n\n"
            "O robô <b>não vende</b> por causa disso: queda assim acontece em ano ruim de bolsa e vender no fundo "
            "transforma a queda em perda. Combine a revisão: a regra continua valendo ou o mundo mudou?\n"
            "<i>Planejamento, seção 6.</i>")


class BotTelegram:
    def __init__(self, pasta: Path):
        self.pasta = pasta
        self.arq_conf = pasta / "telegram_painel.json"
        self.arq_avisos = pasta / "telegram_avisos.json"
        self.arq_estado = pasta / "telegram_estado.json"
        self.pendentes: dict[str, float] = {}   # confirmacoes: acao -> validade
        self._parar = threading.Event()

    # ---------------------------------------------------------------- arquivos
    def _ler(self, arq: Path, padrao):
        try:
            return json.loads(arq.read_text(encoding="utf-8"))
        except Exception:
            return padrao

    def conf(self) -> dict:
        return self._ler(self.arq_conf, {})

    def avisos(self) -> dict:
        return {**AVISOS_PADRAO, **self._ler(self.arq_avisos, {})}

    # ---------------------------------------------------------------- telegram
    def api(self, metodo: str, **dados):
        c = self.conf()
        if not c.get("token"):
            return None
        dados = {k: v for k, v in dados.items() if v is not None}
        try:
            r = httpx.post(f"https://api.telegram.org/bot{c['token']}/{metodo}", json=dados, timeout=45)
            return r.json()
        except Exception:
            return None

    def mandar(self, texto: str, botoes=None):
        c = self.conf()
        if c.get("chat_id"):
            self.api("sendMessage", chat_id=c["chat_id"], text=texto, parse_mode="HTML",
                     disable_web_page_preview=True, reply_markup={"inline_keyboard": botoes} if botoes else None)

    def editar(self, msg: dict, texto: str, botoes):
        r = self.api("editMessageText", chat_id=msg["chat"]["id"], message_id=msg["message_id"], text=texto,
                     parse_mode="HTML", disable_web_page_preview=True, reply_markup={"inline_keyboard": botoes})
        if not (r or {}).get("ok") and "not modified" not in str((r or {}).get("description", "")):
            self.mandar(texto, botoes)

    # ---------------------------------------------------------------- painel
    def get(self, rota: str):
        try:
            return httpx.get(PAINEL + rota, timeout=60).json()
        except Exception:
            return None

    def post(self, rota: str):
        try:
            r = httpx.post(PAINEL + rota, headers=CAB, timeout=60)
            return r.json().get("mensagem") or r.json().get("detail") or "Feito."
        except Exception as erro:
            return f"Não consegui falar com o painel ({erro})."

    def valor_carteira_acoes(self, a: dict, est: dict) -> float | None:
        """Valor da carteira de consenso = patrimonio da conta menos o que esta fora dela.
        Na conta de papel, "fora" sao os US$ 99 mil ficticios; calculado uma vez (acoes + caixa do consenso)
        e guardado. Pelo patrimonio total, a troca de acoes (venda e depois compra) nao parece queda."""
        try:
            equity = float(a["conta"]["equity"])
        except Exception:
            return None
        corretora = a.get("corretora", "alpaca")
        if est.get("acoes_corretora", "alpaca") != corretora:  # outra conta: topo e "fora" comecam do zero
            est.update(acoes_corretora=corretora, acoes_fora=None, acoes_pico=None, acoes_nivel=0, acoes_abaixo=None)
        if est.get("acoes_fora") is None:
            nome = "consenso.json" if corretora == "alpaca" else f"consenso_{corretora}.json"
            cons = self._ler(self.pasta.parent / "acoes-eua" / "trader" / "state" / nome, {})
            if cons.get("caixa") is None or not a.get("posicoes"):
                return None
            vale = sum(float(p["market_value"]) for p in a["posicoes"])
            est["acoes_fora"] = round(equity - vale - float(cons["caixa"]), 2)
        return equity - float(est["acoes_fora"])

    # ---------------------------------------------------------------- telas
    @staticmethod
    def b(texto, dado):
        return {"text": texto, "callback_data": dado}

    def tela_menu(self):
        r = self.get("/api/resumo") or {}
        pausado = bool(r.get("pausa_arquivo") or (r.get("guarda") or {}).get("pausa"))
        pausa = self.b("▶️ Retomar compras", "retomar") if pausado else self.b("⏸ Pausar compras", "pausar")
        texto = "🤖 <b>Robô de Trade</b> · o que você quer ver?"
        return texto, [[self.b("📈 Ganhos", "ganhos"), self.b("📊 Resumo", "resumo")],
                       [self.b("🪙 Cripto", "cripto")],
                       [self.b("🇺🇸 Ações EUA", "acoes"), self.b("🧑‍💼 Investidores", "investidores")],
                       [pausa, self.b("🛑 Vender tudo", "vender")],
                       [self.b("🔔 Avisos", "avisos"), self.b("📄 Relatório do dia", "relatorio")]]

    def rodape(self, atual):
        return [[self.b("🔄 Atualizar", atual), self.b("⬅️ Menu", "menu")]]

    def tela_resumo(self):
        r = self.get("/api/resumo") or {}
        a = self.get("/api/acoes") or {}
        g = r.get("guarda") or {}
        ini, pat = g.get("saldo_inicial") or r.get("saldo_inicial") or 0, g.get("patrimonio") or 0
        if not r.get("robo_ligado"):
            modo = "robô desligado ou reiniciando"
        else:
            estado = "pausado" if (r.get("pausa_arquivo") or g.get("pausa")) else "operando"
            modo = f"{'teste' if r.get('dry_run') is True else 'DINHEIRO REAL' if r.get('dry_run') is False else '?'}, {estado}"
        linhas = ["📊 <b>Resumo</b>", "",
                  f"🪙 <b>Cripto</b> ({modo})",
                  f"Saldo {brl(pat)} · resultado {brl(pat - ini)} ({pct((pat / ini - 1) * 100 if ini else 0)})",
                  f"Moedas compradas: {len([x for x in (r.get('abertas') or []) if x])} · pausa em {brl(g.get('saldo_minimo'))}",
                  f"Fear &amp; Greed: {e(g.get('fear_greed', '-'))}"]
        if a.get("conectada"):
            c = a["conta"]
            dia = float(c["equity"]) - float(c["last_equity"])
            pago = sum(float(p["qty"]) * float(p["avg_entry_price"]) for p in a.get("posicoes", []))
            vale = sum(float(p["market_value"]) for p in a.get("posicoes", []))
            linhas += ["", "🇺🇸 <b>Ações EUA</b> (conta de papel)",
                       f"Pago {usd(pago)} · vale agora {usd(vale)}",
                       f"Resultado {usd(vale - pago)} ({pct((vale / pago - 1) * 100 if pago else 0)}) · hoje {usd(dia)}"]
        linhas += ["", f"🕒 Atualizado em {datetime.now():%d/%m/%Y às %H:%M}"]
        return "\n".join(linhas), self.rodape("resumo")

    def tela_cripto(self):
        r = self.get("/api/resumo") or {}
        if not r.get("robo_ligado"):
            return "🪙 <b>Cripto</b>\n\nO robô está desligado ou reiniciando. Tente de novo em 1 minuto.", self.rodape("cripto")
        g = r.get("guarda") or {}
        inicio = float(g.get("saldo_inicial") or r.get("saldo_inicial") or 0)
        agora = float(g.get("patrimonio") or 0)
        dif = agora - inicio
        teste = "teste, dinheiro fictício" if r.get("dry_run") else "DINHEIRO REAL"
        linhas = [f"🪙 <b>Cripto</b> ({teste})", "",
                  f"Você começou com:  <b>{brl(inicio)}</b>",
                  f"Tem agora:  <b>{brl(agora)}</b>",
                  f"{'✅ Ganho' if dif >= 0 else '🔻 Perda'}:  <b>{brl(abs(dif))}</b> ({pct((agora / inicio - 1) * 100 if inicio else 0)})"]

        abertas = [x for x in (r.get("abertas") or []) if x]
        linhas += ["", "<b>Moedas compradas agora</b>"]
        if abertas:
            for t in sorted(abertas, key=lambda t: -float(t.get("profit_abs") or 0)):
                gan = float(t.get("profit_abs") or 0)
                bola = "🟢" if gan > 0 else "🔴" if gan < 0 else "⚪"
                pago = float(t["stake_amount"])
                linhas.append(f"{bola} <b>{e(t['pair'].split('/')[0])}</b>  {'+' if gan >= 0 else '−'}{brl(abs(gan))} ({pct(t['profit_pct'])})")
                linhas.append(f"      pagou {brl(pago)} · vale {brl(pago + gan)}")
        else:
            linhas.append("Nenhuma: o saldo está todo em real, esperando um sinal de compra.")

        fech = [t for t in (r.get("operacoes") or []) if not t.get("is_open")]
        if fech:
            ganhos = [t for t in fech if float(t.get("profit_abs") or 0) > 0]
            linhas += ["", f"<b>Operações já fechadas: {len(fech)}</b> ({len(ganhos)} com lucro, {len(fech) - len(ganhos)} com prejuízo)"]
            for t in fech[-5:][::-1]:
                gan = float(t.get("profit_abs") or 0)
                bola = "🟢" if gan > 0 else "🔴" if gan < 0 else "⚪"
                dia = str(t.get("close_date") or "")[8:10] + "/" + str(t.get("close_date") or "")[5:7]
                linhas.append(f"{bola} {e(t['pair'].split('/')[0])}  {'+' if gan >= 0 else '−'}{brl(abs(gan))} ({pct(t['profit_pct'])}) · "
                              f"{e(SAIDAS.get(t.get('exit_reason'), t.get('exit_reason')))} · {e(dia)}")

        travas = [t for t in (r.get("travas") or []) if t.get("active")]
        pausa = r.get("pausa_arquivo") or g.get("pausa")
        linhas += ["", f"🛡 Pausa automática se o saldo cair a {brl(g.get('saldo_minimo'))}."]
        if pausa:
            linhas.append(f"⏸ Compras pausadas: {e(pausa)}")
        if travas:
            linhas.append("🔒 Travas ativas: " + ", ".join(e(t["pair"].split("/")[0]) for t in travas[:6]))
        return "\n".join(linhas), self.rodape("cripto")

    def tela_acoes(self):
        a = self.get("/api/acoes") or {}
        if not a.get("conectada"):
            motivo = e(a.get("erro") or f"Conta da {a.get('corretora_nome', 'corretora')} não conectada.")
            return f"🇺🇸 <b>Ações EUA</b>\n\n{motivo}\nConfira em Configurações, no computador.", self.rodape("acoes")
        posicoes = a.get("posicoes", [])
        if not posicoes:
            return "🇺🇸 <b>Ações EUA</b> (conta de papel)\n\nNenhuma ação na carteira.", self.rodape("acoes")
        nomes = {w["ticker"]: w["name"] for w in ((a.get("referencia") or {}).get("weights") or [])}
        itens = []
        for p in posicoes:
            pago = float(p["qty"]) * float(p["avg_entry_price"])
            vale = float(p["market_value"])
            itens.append((vale - pago, pago, vale, p["symbol"]))
        pago_total = sum(i[1] for i in itens)
        vale_total = sum(i[2] for i in itens)
        ganho = vale_total - pago_total
        icone = "✅" if ganho >= 0 else "🔻"
        linhas = [f"🇺🇸 <b>Ações EUA</b> · {e(a.get('corretora_nome', 'Alpaca'))} (conta de papel, dinheiro fictício)", "",
                  f"Você pagou:  <b>{usd(pago_total)}</b>",
                  f"Vale agora:  <b>{usd(vale_total)}</b>",
                  f"{icone} {'Ganho' if ganho >= 0 else 'Perda'}:  <b>{usd(abs(ganho))}</b> ({pct((vale_total / pago_total - 1) * 100 if pago_total else 0)})",
                  "", "<b>Por ação</b> (da que mais ganhou para a que menos)"]
        for g, pago, vale, sym in sorted(itens, reverse=True):
            bola = "🟢" if g > 0 else "🔴" if g < 0 else "⚪"
            nome = f"{e(nomes.get(sym, sym))} ({e(sym)})" if sym in nomes else e(sym)
            linhas.append(f"{bola} <b>{nome}</b>  {'+' if g >= 0 else '−'}{usd(abs(g))} ({pct((vale / pago - 1) * 100 if pago else 0)})")
            linhas.append(f"      pagou {usd(pago)} · vale {usd(vale)}")
        est = self._ler(self.arq_estado, {})
        if (est.get("acoes_pico") and est.get("acoes_fora") is not None
                and est.get("acoes_corretora", "alpaca") == a.get("corretora", "alpaca")):
            valor = float(a["conta"]["equity"]) - float(est["acoes_fora"])
            linhas += ["", f"📈 Topo da carteira: {usd(est['acoes_pico'])} · agora {pct((valor / est['acoes_pico'] - 1) * 100)} do topo",
                       "<i>Aviso automático se cair 20% do topo (não vende sozinho).</i>"]
        if a.get("corretora", "alpaca") == "alpaca":  # propostas de ordens so existem na Alpaca
            prop = self.get("/api/alpaca/propostas") or {}
            prontas = [p for p in prop.get("ordens", []) if p["estado"] == "pronta"]
            if prontas:
                linhas += ["", f"📝 {len(prontas)} ordem(ns) esperando a sua aprovação no painel."]
        linhas += ["", "<i>O resto do saldo da conta de papel é dinheiro fictício parado: não entra no ganho.</i>"]
        return "\n".join(linhas), self.rodape("acoes")

    def tela_ganhos(self):
        """Quanto ganhou por tipo e no total: 7 dias, 30 dias e desde o inicio (painel /api/ganhos)."""
        linhas = ["📈 <b>Seus ganhos</b> (tudo simulado)"]
        for chave, nome in (("7d", "Últimos 7 dias"), ("30d", "Últimos 30 dias"), ("tudo", "Desde o início")):
            g = self.get(f"/api/ganhos?periodo={chave}")
            if not g or "total" not in g:
                return "📈 Não consegui calcular os ganhos agora.", self.rodape("ganhos")
            t = g["total"]
            linhas += ["", f"<b>{nome}</b>", f"{'✅' if t['ganho_brl'] >= 0 else '🔻'} Total: <b>{brl(t['ganho_brl'])}</b> ({pct(t['ganho_pct'])})"]
            for x in g["tipos"]:
                valor = brl(x["ganho"]) if x["moeda"] == "BRL" else f"{usd(x['ganho'])} ≈ {brl(x['ganho_brl'])}"
                linhas.append(f"   {'🪙' if x['tipo'] == 'cripto' else '🇺🇸'} {e(x['nome'].split(' (')[0])}: {valor} ({pct(x['ganho_pct'])})")
        linhas += ["", "<i>O valor em reais das ações inclui a variação do dólar. Datas à sua escolha: painel, Visão geral.</i>",
                   "", f"🕒 Atualizado em {datetime.now():%d/%m/%Y às %H:%M}"]
        return "\n".join(linhas), self.rodape("ganhos")

    def tela_investidores(self):
        d = self.get("/api/investidores") or {}
        linhas = ["🧑‍💼 <b>Investidores que acompanhamos</b>", ""]
        for i in d.get("investidores", []):
            m = i.get("mudancas") or {}
            novas = ", ".join((m.get("comprou (nova)") or [])[:4]) or "-"
            linhas.append(f"<b>{e(i['nome'])}</b> · trimestre {e(i.get('periodo'))}")
            linhas.append(f"   novas: {e(novas)}")
            if i.get("aviso"):
                linhas.append(f"   ⚠️ {e(i['aviso'])}")
        return "\n".join(linhas) or "Sem dados ainda.", self.rodape("investidores")

    def tela_avisos(self):
        av = self.avisos()
        botoes = [[self.b(("✅ " if av[k] else "⬜ ") + nome, f"aviso:{k}")] for k, nome in NOMES_AVISOS.items()]
        return "🔔 <b>Avisos</b> · toque para ligar ou desligar", botoes + [[self.b("⬅️ Menu", "menu")]]

    def tela_relatorio(self):
        datas = self.get("/api/relatorios") or []
        if not datas:
            return "📄 Ainda não há relatório diário.", self.rodape("relatorio")
        r = self.get(f"/api/relatorios/{datas[0]}") or {}
        texto = r.get("texto", "")
        trecho = texto.split("## ", 2)
        resumo = ("## " + trecho[1]) if len(trecho) > 1 else texto[:1500]
        resumo = resumo.replace("## ", "").replace("**", "")[:1500]
        return f"📄 <b>Relatório de {e(datas[0])}</b>\n\n{e(resumo)}\n\n<i>O relatório completo está no painel, em Relatórios.</i>", self.rodape("relatorio")

    def tela_confirma(self, acao: str):
        textos = {"pausar": "Pausar as compras do robô de cripto? Ele continua cuidando das moedas que já tem.",
                  "retomar": "Retomar as compras do robô de cripto?",
                  "vender": "Vender AGORA todas as moedas do robô de cripto, pelo preço do momento, e pausar as compras?"}
        self.pendentes[acao] = time.time() + CONFIRMA_SEG
        return (f"❓ <b>Confirma?</b>\n{e(textos[acao])}\n\n<i>Vale por 5 min.</i>",
                [[self.b("✅ Confirmar", f"ok:{acao}"), self.b("❌ Cancelar", "menu")]])

    def executar(self, acao: str):
        if self.pendentes.pop(acao, 0) < time.time():
            return "⌛ A confirmação expirou. Peça de novo pelo menu.", [[self.b("⬅️ Menu", "menu")]]
        rota = {"pausar": "/api/pausar", "retomar": "/api/retomar", "vender": "/api/vender-tudo"}[acao]
        return f"✅ {e(self.post(rota))}", [[self.b("⬅️ Menu", "menu")]]

    # ---------------------------------------------------------------- escuta
    def tratar(self, upd: dict):
        c = self.conf()
        chat_ok = str(c.get("chat_id", ""))
        if "callback_query" in upd:
            q = upd["callback_query"]
            if str(q["message"]["chat"]["id"]) != chat_ok:
                return
            self.api("answerCallbackQuery", callback_query_id=q["id"])
            d = q.get("data", "")
            if d.startswith("aviso:"):
                av = self.avisos()
                k = d.split(":", 1)[1]
                if k in av:
                    av[k] = not av[k]
                    self.arq_avisos.write_text(json.dumps(av), encoding="utf-8")
                texto, botoes = self.tela_avisos()
            elif d.startswith("ok:"):
                texto, botoes = self.executar(d.split(":", 1)[1])
            elif d in ("pausar", "retomar", "vender"):
                texto, botoes = self.tela_confirma(d)
            else:
                tela = {"menu": self.tela_menu, "resumo": self.tela_resumo, "cripto": self.tela_cripto, "ganhos": self.tela_ganhos,
                        "acoes": self.tela_acoes, "investidores": self.tela_investidores,
                        "avisos": self.tela_avisos, "relatorio": self.tela_relatorio}.get(d, self.tela_menu)
                texto, botoes = tela()
            self.editar(q["message"], texto, botoes)
        elif "message" in upd:
            m = upd["message"]
            if str(m["chat"]["id"]) != chat_ok:
                return  # qualquer outra conversa e ignorada
            texto, botoes = self.tela_menu()
            self.mandar(texto, botoes)

    def escuta(self):
        deslocamento = None
        while not self._parar.is_set():
            if not self.conf().get("token"):
                time.sleep(10)
                continue
            try:
                r = self.api("getUpdates", timeout=30, offset=deslocamento,
                             allowed_updates=["message", "callback_query"]) or {}
                for upd in r.get("result", []):
                    deslocamento = upd["update_id"] + 1
                    try:
                        self.tratar(upd)
                    except Exception:
                        pass
            except Exception:
                time.sleep(5)

    # ---------------------------------------------------------------- avisos
    def avisar(self):
        primeira = True
        while not self._parar.is_set():
            try:
                if self.conf().get("token"):
                    self._rodada_avisos(silenciosa=primeira and not self.arq_estado.exists())
                    primeira = False
            except Exception:
                pass
            time.sleep(30)

    def _rodada_avisos(self, silenciosa: bool):
        av = self.avisos()
        est = self._ler(self.arq_estado, {"abertas": [], "fechadas": [], "pausa": None, "travas": [],
                                          "investidores": [], "ordens": [], "resumo_dia": ""})
        msgs = []
        r = self.get("/api/resumo") or {}
        if r.get("robo_ligado"):
            abertas = {str(t["trade_id"]): t for t in (r.get("abertas") or []) if t}
            fechadas = {str(t["trade_id"]): t for t in (r.get("operacoes") or []) if not t.get("is_open")}
            if av["operacoes"]:
                for i, t in abertas.items():
                    if i not in est["abertas"]:
                        stop = f"\nStop: {t['stop_loss_abs']:.6g}" if t.get("stop_loss_abs") else ""
                        msgs.append(f"🟢 <b>Compra</b> · {e(t['pair'])}\n{brl(t['stake_amount'])} a {t['open_rate']:.6g}{stop}")
                for i, t in fechadas.items():
                    if i not in est["fechadas"]:
                        icone = "✅" if float(t.get("profit_abs") or 0) >= 0 else "🔻"
                        msgs.append(f"{icone} <b>Venda</b> · {e(t['pair'])}\n{pct(t['profit_pct'])} ({brl(t['profit_abs'])}) · "
                                    f"{e(SAIDAS.get(t.get('exit_reason'), t.get('exit_reason')))}")
            est["abertas"], est["fechadas"] = list(abertas), list(fechadas)[-200:]
            pausa = r.get("pausa_arquivo") or (r.get("guarda") or {}).get("pausa")
            travas = sorted(f"{t['pair']}|{t['lock_end_time']}" for t in (r.get("travas") or []) if t.get("active") and t["pair"] == "*")
            if av["travas"]:
                if pausa and pausa != est["pausa"]:
                    msgs.append(f"⏸ <b>Compras pausadas</b>\n{e(pausa)}")
                if not pausa and est["pausa"]:
                    msgs.append("▶️ <b>Compras retomadas</b>")
                for t in travas:
                    if t not in est["travas"]:
                        msgs.append(f"🔒 <b>Trava de proteção</b> até {e(t.split('|')[1][11:16])}: o robô parou de comprar por um tempo.")
            est["pausa"], est["travas"] = pausa, travas
        inv = self.get("/api/investidores") or {}
        chaves_inv = [f"{n['cik']}|{n['accession']}" for n in inv.get("novidades", [])]
        if av["investidores"]:
            for n, ch in zip(inv.get("novidades", []), chaves_inv):
                if ch not in est["investidores"]:
                    m = n.get("mudancas") or {}
                    partes = [f"{k}: {', '.join(v[:6])}" for k, v in m.items() if v]
                    msgs.append(f"🧑‍💼 <b>{e(n['nome'])}</b> entregou o trimestre de {e(n['trimestre'])}\n" + e("\n".join(partes)))
        est["investidores"] = chaves_inv
        a = self.get("/api/acoes") or {}
        if a.get("conectada"):
            executadas = {o["submitted_at"] + o["symbol"]: o for o in a.get("ordens", []) if o.get("status") == "filled"}
            if av["acoes"]:
                novas = [o for ch, o in executadas.items() if ch not in est["ordens"]]
                if novas:  # uma mensagem so, mesmo quando a carteira troca varias acoes de uma vez
                    linhas = [f"🇺🇸 <b>{len(novas)} ordem(ns) executada(s)</b> (conta de papel)"]
                    for o in novas:
                        valor = usd(o["notional"]) if o.get("notional") else f"{float(o.get('filled_qty') or o.get('qty') or 0):.4g} ações"
                        linhas.append(f"{'🟢 Compra' if o['side'] == 'buy' else '🔵 Venda'} {e(o['symbol'])}: {valor} a {usd(o['filled_avg_price'])}")
                    msgs.append("\n".join(linhas))
            est["ordens"] = list(executadas)[-200:]
            valor = self.valor_carteira_acoes(a, est)
            if valor:
                aviso = avaliar_queda(valor, est)
                if aviso and av["queda_acoes"]:
                    msgs.append(aviso)
        hoje = datetime.now().strftime("%Y-%m-%d")
        if av["resumo_diario"] and datetime.now().hour >= 20 and est.get("resumo_dia") != hoje:
            texto, _ = self.tela_resumo()
            msgs.append(texto.replace("📊 <b>Resumo</b>", "🌙 <b>Resumo do dia</b>"))
            est["resumo_dia"] = hoje
        self.arq_estado.write_text(json.dumps(est), encoding="utf-8")
        if not silenciosa:
            for m in msgs[:10]:
                self.mandar(m, [[self.b("📋 Menu", "menu")]])

    def iniciar(self):
        threading.Thread(target=self.escuta, daemon=True, name="telegram-escuta").start()
        threading.Thread(target=self.avisar, daemon=True, name="telegram-avisos").start()

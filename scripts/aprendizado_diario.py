r"""
Rotina de aprendizado (12/11/2026): o robo estuda todo dia, mas NAO muda a propria regra.
Mudanca de regra so entra depois de passar no protocolo e com o OK do Daniel (docs/hipoteses-testadas.md).

  - todo dia (depois do fechamento da bolsa): a carteira de papel esta rendendo o que o estudo previa?
    Compara o consenso de papel com o S&P 500 desde o inicio e avisa no Telegram se a diferenca sair do normal
    (mais de 2 desvios da diferenca que o estudo mostrou entre o consenso e o indice);
  - toda semana (sabado): roda o proximo estudo da fila (user_data/aprendizado/fila.json) e manda o resumo;
    estudo sem script fica esperando na fila;
  - todo mes (dia 1o ou depois): atualiza os precos, refaz o consenso ate hoje e confere se a vantagem continua
    (ultimos 12 meses e desde o fim do estudo, 29/10/2026).
Tudo fica em user_data/aprendizado/ (estado.json, diario.json, resultados/). O painel chama este script 1x por dia.

Uso: .\.venv\Scripts\python.exe scripts\aprendizado_diario.py [--semanal] [--mensal] [--sem-telegram]
"""
import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import httpx
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / "user_data" / "aprendizado"
ESTADO = PASTA / "estado.json"
FILA = PASTA / "fila.json"
FIM_ESTUDO = "2026-10-29"
DESVIO_PADRAO = 0.08  # diferenca anual tipica consenso x S&P, ate o 1o calculo mensal
FILA_INICIAL = [
    {"id": "mais_gestores", "nome": "Mais gestores na lista do consenso (16 -> 30)",
     "script": "scripts/estudo_mais_gestores.py"},
]
ENVIAR = "--sem-telegram" not in sys.argv
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def ler(arq: Path, padrao):
    try:
        return json.loads(arq.read_text(encoding="utf-8"))
    except Exception:
        return padrao


def gravar(arq: Path, dados):
    arq.parent.mkdir(parents=True, exist_ok=True)
    arq.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")


def telegram(texto: str):
    print(texto)
    if not ENVIAR:
        return
    try:
        t = json.loads((RAIZ / "user_data" / "telegram_painel.json").read_text(encoding="utf-8"))
        httpx.post(f"https://api.telegram.org/bot{t['token']}/sendMessage", timeout=15,
                   json={"chat_id": t["chat_id"], "text": texto, "parse_mode": "HTML"})
    except Exception:
        pass


def barras(simbolos: list[str], inicio: str) -> pd.DataFrame:
    """Fechamentos diarios ajustados da Alpaca (so leitura de dados de mercado)."""
    chaves = json.loads((RAIZ / "user_data" / "alpaca.json").read_text(encoding="utf-8"))
    cab = {"APCA-API-KEY-ID": chaves["key"], "APCA-API-SECRET-KEY": chaves["secret"]}
    colunas = {}
    for i in range(0, len(simbolos), 50):
        lote, token, linhas = simbolos[i:i + 50], None, []
        while True:
            params = {"symbols": ",".join(lote), "timeframe": "1Day", "start": inicio, "adjustment": "all",
                      "feed": "sip", "limit": 10000}
            if token:
                params["page_token"] = token
            r = httpx.get("https://data.alpaca.markets/v2/stocks/bars", params=params, headers=cab, timeout=90)
            r.raise_for_status()
            d = r.json()
            for sym, bs in (d.get("bars") or {}).items():
                linhas += [(sym, b["t"][:10], b["c"]) for b in bs]
            token = d.get("next_page_token")
            if not token:
                break
        x = pd.DataFrame(linhas, columns=["sym", "dia", "fecha"])
        colunas.update({s: g.set_index("dia")["fecha"] for s, g in x.groupby("sym")})
    df = pd.DataFrame(colunas)
    df.index = pd.to_datetime(df.index)
    return df.sort_index()


# ------------------------------------------------------------------ todo dia
def conferir_carteira(estado: dict) -> dict:
    hist = ler(RAIZ / "user_data" / "historico_patrimonio.json", {})
    corretora = hist.get("acoes_em_uso") or "alpaca"
    dias = ((hist.get("acoes") or {}).get(corretora) or {}).get("dias") or {}
    if len(dias) < 2:
        return {"ok": True, "texto": "carteira de papel sem historico ainda"}
    serie = pd.Series(dias, dtype=float)
    serie.index = pd.to_datetime(serie.index)
    serie = serie.sort_index()
    spy = barras(["SPY"], str(serie.index[0].date() - timedelta(days=5)))["SPY"]
    spy = spy.reindex(serie.index, method="ffill")
    r_cart = serie.iloc[-1] / serie.iloc[0] - 1
    r_spy = spy.iloc[-1] / spy.iloc[0] - 1
    dif = r_cart - r_spy
    pregoes = max(len(serie) - 1, 1)
    sigma = estado.get("desvio_anual", DESVIO_PADRAO) * np.sqrt(pregoes / 252)
    fora = abs(dif) > 2 * sigma
    return {"ok": not fora, "dias": pregoes, "carteira": round(r_cart * 100, 2), "sp500": round(r_spy * 100, 2),
            "diferenca": round(dif * 100, 2), "normal_ate": round(2 * sigma * 100, 2)}


# ------------------------------------------------------------------ toda semana
def proximo_estudo() -> dict:
    fila = ler(FILA, None)
    if fila is None:
        fila = [dict(x, estado="na fila") for x in FILA_INICIAL]
        gravar(FILA, fila)
    for item in fila:
        if item.get("estado") != "na fila":
            continue
        script = RAIZ / item["script"]
        if not script.exists():
            return {"nome": item["nome"], "texto": "esperando o script do estudo ser escrito", "rodou": False}
        r = subprocess.run([sys.executable, str(script)], cwd=RAIZ, capture_output=True, timeout=3 * 3600,
                           encoding="utf-8")
        saida = (r.stdout or "") + (r.stderr or "")
        arq = PASTA / "resultados" / f"{date.today()}_{item['id']}.txt"
        arq.parent.mkdir(parents=True, exist_ok=True)
        arq.write_text(saida, encoding="utf-8")
        item.update(estado="rodou" if r.returncode == 0 else "erro", em=str(date.today()), resultado=str(arq.name))
        gravar(FILA, fila)
        fim = [l for l in saida.strip().splitlines() if l.strip()][-6:]
        return {"nome": item["nome"], "texto": "\n".join(fim), "rodou": r.returncode == 0}
    return {"nome": None, "texto": "fila vazia: mande ideias para testar", "rodou": False}


# ------------------------------------------------------------------ todo mes
def atualizar_precos_consenso():
    arq = RAIZ / "user_data" / "estudo_consenso" / "precos.parquet"
    px = pd.read_parquet(arq).sort_index()
    inicio = str((px.index[-1] + timedelta(days=1)).date())
    if inicio >= str(date.today()):
        return px
    novo = barras(list(px.columns), inicio)
    if len(novo):
        px = pd.concat([px, novo[[c for c in novo.columns if c in px.columns]]]).sort_index()
        px = px[~px.index.duplicated(keep="last")]
        px.to_parquet(arq)
    return px


def conferir_vantagem(estado: dict) -> dict:
    px = atualizar_precos_consenso()
    sys.path.insert(0, str(RAIZ / "scripts"))
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):  # o estudo imprime a tabela de robustez ao importar
        import estudo_consenso_robustez as rb
    fim = px.index[-1]
    cons = rb.rodar(pd.Timestamp("2018-02-16"), fim)
    spy = px["SPY"].reindex(cons.index).ffill()
    d = cons.pct_change() - spy.pct_change()
    estado["desvio_anual"] = round(float(d.std() * np.sqrt(252)), 4)

    def janela(ini):
        c, s = cons[cons.index >= ini], spy[spy.index >= ini]
        return round((c.iloc[-1] / c.iloc[0] - 1) * 100, 2), round((s.iloc[-1] / s.iloc[0] - 1) * 100, 2)

    doze = janela(fim - pd.Timedelta(days=365))
    depois = janela(pd.Timestamp(FIM_ESTUDO)) if fim > pd.Timestamp(FIM_ESTUDO) + pd.Timedelta(days=7) else None
    return {"ate": str(fim.date()), "doze_meses": doze, "depois_do_estudo": depois,
            "desvio_anual": estado["desvio_anual"]}


# ------------------------------------------------------------------
def main():
    PASTA.mkdir(parents=True, exist_ok=True)
    estado = ler(ESTADO, {})
    hoje = date.today()
    registro: dict = {"dia": str(hoje)}
    linhas = []

    c = conferir_carteira(estado)
    registro["carteira"] = c
    # avisa so quando entra (ou troca de lado) fora do normal, nao todo dia
    lado = None if c.get("ok") else ("acima" if c["diferenca"] > 0 else "abaixo")
    if lado and lado != estado.get("alerta"):
        explica = ("Pode ser sorte de poucas ações; o estudo não promete isso." if lado == "acima"
                   else "Pode ser fase ruim passageira; se durar meses, a regra precisa ser revista.")
        linhas.append(f"{'📈' if lado == 'acima' else '⚠️'} A carteira de consenso está {lado} do normal: "
                      f"{c['carteira']:+.2f}% contra {c['sp500']:+.2f}% do S&P em {c['dias']} pregões "
                      f"(diferença {c['diferenca']:+.2f} pontos; normal até ±{c['normal_ate']:.2f}). {explica}")
    estado["alerta"] = lado

    semanal = "--semanal" in sys.argv or (hoje.weekday() == 5 and estado.get("ultima_semanal") != str(hoje))
    if semanal:
        e = proximo_estudo()
        registro["estudo"] = e
        estado["ultima_semanal"] = str(hoje)
        if e["nome"]:
            linhas.append(f"🔬 <b>Estudo da semana</b>: {e['nome']}\n{e['texto']}")
        else:
            linhas.append(f"🔬 Estudo da semana: {e['texto']}")
        if "dias" in c:
            linhas.append(f"📊 Consenso desde o início: {c['carteira']:+.2f}% | S&P 500: {c['sp500']:+.2f}% "
                          f"({c['dias']} pregões; diferença dentro do normal: {'sim' if c['ok'] else 'não'})")

    mes = hoje.strftime("%Y-%m")
    if "--mensal" in sys.argv or estado.get("ultimo_mensal") != mes:
        v = conferir_vantagem(estado)
        registro["vantagem"] = v
        estado["ultimo_mensal"] = mes
        t = (f"📅 <b>Conferência do mês</b> (dados até {v['ate']})\n"
             f"Consenso nos últimos 12 meses: {v['doze_meses'][0]:+.1f}% | S&P 500: {v['doze_meses'][1]:+.1f}%")
        if v["depois_do_estudo"]:
            t += (f"\nDesde o fim do estudo (29/10/2026): {v['depois_do_estudo'][0]:+.1f}% | "
                  f"S&P 500: {v['depois_do_estudo'][1]:+.1f}%")
        linhas.append(t)

    estado["ultimo_dia"] = str(hoje)
    gravar(ESTADO, estado)
    diario = ler(PASTA / "diario.json", [])
    gravar(PASTA / "diario.json", ([registro] + [x for x in diario if x.get("dia") != str(hoje)])[:400])
    if linhas:
        telegram("🧠 <b>Aprendizado do robô</b>\n\n" + "\n\n".join(linhas) +
                 "\n\nNada na regra muda sem o seu OK.")
    else:
        print("Dia conferido, nada fora do normal:", json.dumps(c, ensure_ascii=False))


if __name__ == "__main__":
    main()

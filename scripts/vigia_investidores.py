r"""
Vigia de investidores: avisa quando um investidor da lista entrega um 13F novo na SEC e resume
o que ele comprou, vendeu, aumentou e diminuiu em relacao ao trimestre anterior.

Usa third_party/edgar13f/edgar13f.py (de Jakeschincariol/trader-skill, MIT) e a
identificacao da SEC de acoes-eua/trader/config.json.

  Lista de investidores: user_data/investidores.json (criada na primeira vez; edite a vontade).
  Estado (ultimo relatorio visto de cada um): user_data/investidores_estado.json
  Novidades (para o painel e o Telegram): user_data/investidores_novidades.json

Uso:  .\.venv\Scripts\python.exe scripts\vigia_investidores.py           (so o que e novo)
      .\.venv\Scripts\python.exe scripts\vigia_investidores.py --todos   (resume todos, novo ou nao)
"""
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PASTA_ACOES = RAIZ / "acoes-eua"
FERRAMENTA = Path(__file__).resolve().parent.parent / "third_party" / "edgar13f" / "edgar13f.py"
ARQ_LISTA = RAIZ / "user_data" / "investidores.json"
ARQ_ESTADO = RAIZ / "user_data" / "investidores_estado.json"
ARQ_NOVIDADES = RAIZ / "user_data" / "investidores_novidades.json"

LISTA_INICIAL = [
    {"cik": "1067983", "nome": "Warren Buffett (Berkshire Hathaway)"},
    {"cik": "1649339", "nome": "Michael Burry (Scion Asset Management)"},
    {"cik": "1336528", "nome": "Bill Ackman (Pershing Square)"},
    {"cik": "1709323", "nome": "Li Lu (Himalaya Capital)"},
    {"cik": "1061768", "nome": "Seth Klarman (Baupost)"},
]


def ler(caminho: Path, padrao):
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except Exception:
        return padrao


def ferramenta(*args) -> dict:
    r = subprocess.run([sys.executable, str(FERRAMENTA), *args, "--json"], cwd=PASTA_ACOES,
                       capture_output=True, timeout=300, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip().splitlines()[-1] if (r.stderr or r.stdout) else "erro")
    return json.loads(r.stdout)


def resumir(diff: dict) -> dict:
    """Junta o diff da ferramenta num resumo curto em portugues."""
    grupos = {"NEW": "comprou (nova)", "SOLD": "vendeu tudo", "ADDED": "aumentou", "TRIMMED": "diminuiu"}
    resumo = {rotulo: [] for rotulo in grupos.values()}
    # maiores mudancas primeiro (em valor)
    mudancas = sorted(diff.get("changes", []), key=lambda c: -abs((c.get("value_after") or 0) - (c.get("value_before") or 0)))
    for c in mudancas:
        rotulo = grupos.get(str(c.get("status", "")).upper().replace("SOLD OUT", "SOLD"))
        if not rotulo:
            continue
        nome = c.get("ticker") or c.get("issuer")
        if c.get("put_call"):
            nome += f" ({'aposta na queda' if c['put_call'].upper() == 'PUT' else 'opção de compra'})"
        if len(resumo[rotulo]) < 15:
            resumo[rotulo].append(nome)
    return resumo


def main():
    if not ARQ_LISTA.exists():
        ARQ_LISTA.write_text(json.dumps(LISTA_INICIAL, ensure_ascii=False, indent=2), encoding="utf-8")
    lista = ler(ARQ_LISTA, LISTA_INICIAL)
    estado = ler(ARQ_ESTADO, {})
    novidades = ler(ARQ_NOVIDADES, [])
    todos = "--todos" in sys.argv
    saida = []
    for inv in lista:
        cik, nome = inv["cik"], inv["nome"]
        try:
            filings = [f for f in ferramenta("filings", cik)["filings"] if f["form"].startswith("13F-HR")]
        except Exception as erro:
            saida.append({"nome": nome, "erro": str(erro)})
            continue
        if not filings:
            continue
        ultimo = filings[0]
        visto = estado.get(cik, {}).get("accession")
        novo = visto is not None and visto != ultimo["accession"]
        primeira_vez = visto is None
        dias_sem = (datetime.now() - datetime.fromisoformat(ultimo["filed"])).days
        item = {"cik": cik, "nome": nome, "trimestre": ultimo["period"], "entregue_em": ultimo["filed"],
                "accession": ultimo["accession"], "novo": novo, "dias_desde_o_ultimo": dias_sem}
        if dias_sem > 140:
            item["aviso"] = f"Sem relatório novo há {dias_sem} dias: o investidor pode ter parado de entregar."
        if novo or todos or primeira_vez:
            try:
                item["mudancas"] = resumir(ferramenta("diff", cik, "--accession", ultimo["accession"]))
            except Exception as erro:
                item["erro_diff"] = str(erro)
        if novo:
            novidades.insert(0, {**item, "visto_em": datetime.now().isoformat(timespec="seconds")})
        anterior = estado.get(cik, {})
        estado[cik] = {"accession": ultimo["accession"], "periodo": ultimo["period"], "nome": nome,
                       "entregue_em": ultimo["filed"], "aviso": item.get("aviso"),
                       "mudancas": item.get("mudancas") or anterior.get("mudancas"),
                       "conferido_em": datetime.now().isoformat(timespec="seconds")}
        saida.append(item)
    ARQ_ESTADO.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")
    ARQ_NOVIDADES.write_text(json.dumps(novidades[:50], ensure_ascii=False, indent=2), encoding="utf-8")
    if "--json" in sys.argv:
        print(json.dumps(saida, ensure_ascii=False, indent=2))
        return
    for i in saida:
        if "erro" in i:
            print(f"{i['nome']}: erro ao consultar ({i['erro']})")
            continue
        marca = "NOVO! " if i["novo"] else ""
        print(f"{marca}{i['nome']}: trimestre {i['trimestre']}, entregue em {i['entregue_em']}")
        if i.get("aviso"):
            print(f"   {i['aviso']}")
        for rotulo, tickers in (i.get("mudancas") or {}).items():
            if tickers:
                print(f"   {rotulo}: {', '.join(t for t in tickers if t)}")


if __name__ == "__main__":
    main()

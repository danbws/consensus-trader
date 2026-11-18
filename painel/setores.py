"""
Setor de cada acao da carteira de consenso, para o aviso de concentracao no Telegram (18/11/2026).

Os grupos sao pensados pelo jeito que as acoes andam juntas, nao pela classificacao oficial (GICS). Na oficial,
Google e Meta sao "Comunicacao" e Amazon e "Consumo", mas na correcao dos chips de novembro de 2026 as tres cairam
junto com Nvidia e Microsoft. Por isso ficam todas em "Tecnologia e internet".

Acao que nao esta aqui aparece como "Sem setor cadastrado" na tela; e so acrescentar na lista.
"""

TECNOLOGIA = "Tecnologia e internet"
FINANCEIRO = "Bancos, cartões e seguros"
CONSUMO = "Consumo e varejo"
SAUDE = "Saúde"
ENERGIA = "Energia e materiais"
INDUSTRIA = "Indústria e transporte"
IMOVEIS = "Imóveis e infraestrutura"
SEM_SETOR = "Sem setor cadastrado"

SETORES = {
    # tecnologia e internet (inclui chips, software, nuvem e plataformas)
    "NVDA": TECNOLOGIA, "TSM": TECNOLOGIA, "MSFT": TECNOLOGIA, "AAPL": TECNOLOGIA, "GOOGL": TECNOLOGIA,
    "GOOG": TECNOLOGIA, "META": TECNOLOGIA, "AMZN": TECNOLOGIA, "AVGO": TECNOLOGIA, "AMD": TECNOLOGIA,
    "ASML": TECNOLOGIA, "ORCL": TECNOLOGIA, "CRM": TECNOLOGIA, "ADBE": TECNOLOGIA, "NFLX": TECNOLOGIA,
    "NOW": TECNOLOGIA, "INTU": TECNOLOGIA, "SHOP": TECNOLOGIA, "SE": TECNOLOGIA, "MELI": TECNOLOGIA,
    "BABA": TECNOLOGIA, "PDD": TECNOLOGIA, "TSLA": TECNOLOGIA, "PLTR": TECNOLOGIA, "SNOW": TECNOLOGIA,
    "CRWD": TECNOLOGIA, "PANW": TECNOLOGIA, "MU": TECNOLOGIA, "QCOM": TECNOLOGIA, "TXN": TECNOLOGIA,
    "LRCX": TECNOLOGIA, "AMAT": TECNOLOGIA, "KLAC": TECNOLOGIA, "QRVO": TECNOLOGIA, "STX": TECNOLOGIA,
    "EA": TECNOLOGIA, "ATVI": TECNOLOGIA, "TTWO": TECNOLOGIA, "SPOT": TECNOLOGIA, "TWTR": TECNOLOGIA,
    "IAC": TECNOLOGIA, "BKNG": TECNOLOGIA, "UBER": TECNOLOGIA, "WDAY": TECNOLOGIA, "DDOG": TECNOLOGIA,
    "AABA": TECNOLOGIA, "FOXA": TECNOLOGIA, "WBD": TECNOLOGIA, "DIS": TECNOLOGIA, "CHTR": TECNOLOGIA,
    "CMCSA": TECNOLOGIA, "LBRDK": TECNOLOGIA,
    # bancos, cartoes e seguros
    "V": FINANCEIRO, "MA": FINANCEIRO, "AXP": FINANCEIRO, "BRK.B": FINANCEIRO, "BRK.A": FINANCEIRO,
    "BN": FINANCEIRO, "BAC": FINANCEIRO, "JPM": FINANCEIRO, "WFC": FINANCEIRO, "C": FINANCEIRO,
    "GS": FINANCEIRO, "MS": FINANCEIRO, "SCHW": FINANCEIRO, "BK": FINANCEIRO, "USB": FINANCEIRO,
    "MCO": FINANCEIRO, "SPGI": FINANCEIRO, "MKL": FINANCEIRO, "CB": FINANCEIRO, "AIG": FINANCEIRO,
    "PYPL": FINANCEIRO, "FI": FINANCEIRO, "FISV": FINANCEIRO, "CPAY": FINANCEIRO, "KKR": FINANCEIRO,
    "BX": FINANCEIRO, "APO": FINANCEIRO, "COF": FINANCEIRO, "ALLY": FINANCEIRO, "KMX": FINANCEIRO,
    "BAM": FINANCEIRO, "ICE": FINANCEIRO, "CME": FINANCEIRO, "MSCI": FINANCEIRO,
    # consumo e varejo
    "KO": CONSUMO, "PEP": CONSUMO, "PG": CONSUMO, "WMT": CONSUMO, "COST": CONSUMO, "MCD": CONSUMO,
    "QSR": CONSUMO, "CMG": CONSUMO, "SBUX": CONSUMO, "NKE": CONSUMO, "HD": CONSUMO, "LOW": CONSUMO,
    "PM": CONSUMO, "MO": CONSUMO, "KHC": CONSUMO, "DEO": CONSUMO, "BUD": CONSUMO, "HLT": CONSUMO,
    "MAR": CONSUMO, "LULU": CONSUMO, "TGT": CONSUMO, "WBA": CONSUMO, "FCAU": CONSUMO, "GM": CONSUMO,
    "F": CONSUMO, "LVS": CONSUMO, "ORLY": CONSUMO, "AZO": CONSUMO, "NVR": CONSUMO, "LEN": CONSUMO,
    "DHI": CONSUMO, "CPNG": CONSUMO, "HHH": CONSUMO,
    # saude
    "UNH": SAUDE, "JNJ": SAUDE, "LLY": SAUDE, "ABBV": SAUDE, "PFE": SAUDE, "MRK": SAUDE, "AGN": SAUDE,
    "CELG": SAUDE, "BMY": SAUDE, "AMGN": SAUDE, "GILD": SAUDE, "TMO": SAUDE, "DHR": SAUDE, "CVS": SAUDE,
    "CI": SAUDE, "HUM": SAUDE, "ELV": SAUDE, "ISRG": SAUDE, "MCK": SAUDE, "VRTX": SAUDE, "REGN": SAUDE,
    "NVO": SAUDE, "TEVA": SAUDE,
    # energia e materiais
    "XOM": ENERGIA, "CVX": ENERGIA, "OXY": ENERGIA, "COP": ENERGIA, "CEIX": ENERGIA, "EOG": ENERGIA,
    "SLB": ENERGIA, "FCX": ENERGIA, "DWDP": ENERGIA, "DOW": ENERGIA, "LIN": ENERGIA, "NUE": ENERGIA,
    "TECK": ENERGIA, "CNQ": ENERGIA, "VST": ENERGIA, "CEG": ENERGIA,
    # industria e transporte
    "GE": INDUSTRIA, "UTX": INDUSTRIA, "RTX": INDUSTRIA, "HON": INDUSTRIA, "BA": INDUSTRIA, "CAT": INDUSTRIA,
    "DE": INDUSTRIA, "UNP": INDUSTRIA, "CSX": INDUSTRIA, "NSC": INDUSTRIA, "CP": INDUSTRIA, "CNI": INDUSTRIA,
    "UPS": INDUSTRIA, "FDX": INDUSTRIA, "DAL": INDUSTRIA, "UAL": INDUSTRIA, "AAL": INDUSTRIA, "LUV": INDUSTRIA,
    "GD": INDUSTRIA, "LMT": INDUSTRIA, "NOC": INDUSTRIA, "HWM": INDUSTRIA, "FERG": INDUSTRIA, "WAB": INDUSTRIA,
    "ETN": INDUSTRIA, "TDG": INDUSTRIA,
    # imoveis e infraestrutura
    "AMT": IMOVEIS, "PLD": IMOVEIS, "EQIX": IMOVEIS, "CCI": IMOVEIS, "BIP": IMOVEIS, "BEP": IMOVEIS,
    "NEE": IMOVEIS, "HHC": IMOVEIS,
}


def setor(ticker: str) -> str:
    return SETORES.get((ticker or "").upper(), SEM_SETOR)


def concentracao(posicoes: list[dict], caixa: float = 0.0) -> list[tuple[str, float, list[str]]]:
    """[(setor, % da carteira, acoes)] do maior para o menor. posicoes: as da corretora (symbol, market_value).
    O caixa conta no total (e parte da carteira), mas nao vira setor."""
    total = sum(float(p["market_value"]) for p in posicoes) + max(caixa, 0.0)
    if total <= 0:
        return []
    grupos: dict[str, list] = {}
    for p in posicoes:
        g = grupos.setdefault(setor(p["symbol"]), [0.0, []])
        g[0] += float(p["market_value"])
        g[1].append(p["symbol"])
    return sorted(((s, v / total * 100, sorted(t)) for s, (v, t) in grupos.items()), key=lambda x: -x[1])

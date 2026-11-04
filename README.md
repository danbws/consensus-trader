# consensus-trader

[Leia em português](README.pt-BR.md)

A personal trading lab that runs on one Windows PC. It has three parts:

- a **US stock portfolio** that holds the companies most often found among the top positions of well-known value investors, taken from their SEC 13F filings;
- a **crypto bot** built on [Freqtrade](https://github.com/freqtrade/freqtrade), trading BRL pairs on Binance;
- a **web panel** and a **Telegram bot** to follow both, from the desktop or a phone.

All of it runs on paper money today. I built it to answer one question: can a small, careful bot do better than simply buying and holding? I kept a log of every idea I tested, including the ones that failed. That log is the most useful part of the repository.

## What I found

**Stocks: the 13F consensus has a small edge.** Take 16 managers (Buffett, Klarman, Li Lu, Ackman, Burry, Tepper, Pabrai, Marks and others), look at each one's latest 13F filing, and buy the 10 companies that the most managers hold at 3% or more of their portfolio. Rebalance when new filings change the list, about once a quarter. Each filing counts only from the date it was filed, so the backtest never sees the future.

| Daily prices, 0.2% cost per trade | 2018-2021 (rule chosen here) | 2022-2026 (out of sample) |
|---|---|---|
| S&P 500, buy and hold | 14.9% a year | 13.8% a year |
| Consensus, top 10 | **15.3% a year** | **15.3% a year** |

6 of the 9 nearby variants (other cut-offs, top 8, entering 5 or 20 days later) also beat the index in both periods. The edge is real but small, and the drawdowns look like the index's. The portfolio has been running on paper (Alpaca) since 30 Oct 2026.

**Crypto: I did not find an edge.** More than 40 rules, Freqtrade's FreqAI and well-known community strategies went through the same protocol: choose on one period, confirm on another, check nearby parameters, charge realistic fees and spread. None passed all four. The early gains on BRL pairs most likely came from thin order books, and they disappeared once spread was charged. The live dry-run matched the backtest: about flat.

**Bitcoin ETF flows do not predict the next day.** The correlation between today's net flow into the US spot ETFs and tomorrow's return was +0.04. Large outflows act as a brake in falling markets but cost you in rising ones, and only one exact parameter set beat buy-and-hold in both periods.

The full log, in Portuguese, is in [docs/hipoteses-testadas.md](docs/hipoteses-testadas.md).

## What is inside

| Path | What it is |
|---|---|
| `scripts/estudo_consenso.py`, `estudo_consenso_robustez.py` | 13F download, the consensus backtest and the robustness checks |
| `scripts/consenso_automatico.py` | Runs the consensus portfolio: checks hourly, trades only when the list changes |
| `scripts/corretoras.py` | One interface for Alpaca and Interactive Brokers (IB Gateway via `ib_async`), paper accounts only |
| `scripts/vigia_investidores.py` | Watches for new 13F filings and summarises what each investor bought and sold |
| `scripts/relatorio_imposto.py` | Yearly report for a Brazilian accountant: every sale in BRL at the central bank rate (PTAX), FIFO cost, dividends |
| `scripts/historico.py` | Daily value per asset type, so the panel can show gains for any period |
| `scripts/estudo_etf_btc*.py` | The bitcoin ETF flow study |
| `user_data/strategies/` | The Freqtrade strategies that were tested (`RoboSaidas.py` is the one running) |
| `painel/` | FastAPI panel (charts, gains, settings) and the Telegram bot |
| `third_party/edgar13f/` | SEC 13F parser by Jake Schincariol, MIT |
| `docs/aulas/` | Ten short lessons, in Portuguese, for someone new to trading |

## Safety

- **Paper only.** Alpaca is reached only through its paper endpoint. Interactive Brokers is refused unless the port is a paper port (4002 or 7497) and every account in the login starts with `DU`. Real money for crypto needs a key without withdrawal rights, 21 days of testing and a typed confirmation.
- **The panel listens on your machine.** Other devices get in only through Tailscale, with a password, and the settings pages never open from a phone.
- **The Telegram bot answers one chat.** Anything that moves money asks for confirmation, valid for 5 minutes.
- **Keys stay out of git.** `.gitignore` works as an allow list: only code and docs are tracked.
- **Stops and alerts.** The crypto bot pauses itself if the balance falls by a third. The stock portfolio never sells on a drop; it sends a Telegram alert at -20%, -30% and -40% from its peak, because selling at the bottom turns a drawdown into a loss.

## Running it

You need Windows 10 or 11 and Python 3.11 or newer (developed on 3.14).

```powershell
git clone https://github.com/danbws/consensus-trader.git
cd consensus-trader
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy user_data\config.example.json user_data\config.json
copy acoes-eua\trader\config.example.json acoes-eua\trader\config.json
```

Edit both files. In `user_data\config.json`, change the `api_server` user, password and secrets. In `acoes-eua\trader\config.json`, put your name and e-mail in `sec_user_agent`; the SEC asks for it on every download.

```powershell
.\abrir-robo.ps1
```

This starts the bot and the panel in the background and opens <http://127.0.0.1:8090>. Under **Configurações** you connect the Alpaca paper keys, Telegram and, later, the IB Gateway. `parar-robo.ps1` stops everything.

The tests need no broker: `scripts\teste_corretoras.py`, `teste_queda.py` and `teste_acesso.py`.

## Not financial advice

This is a study project. It shows data and the results of rules, and it can be wrong. Past results do not promise future ones. Do your own research before putting real money anywhere.

## License

[GPL-3.0](LICENSE), the same as Freqtrade. `third_party/edgar13f` keeps its own MIT license.

Made by **Daniel Bichof** ([@danbws](https://github.com/danbws)), Brazil.

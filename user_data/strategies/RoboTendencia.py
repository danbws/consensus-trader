"""
RoboTendencia - estrategia de teste do robo-trade.

Ideia (explicada na docs/aulas/03-a-estrategia.md):
  1. Onde: so opera moedas em alta no grafico de 1 hora (preco acima da media de 200
     e media de 50 acima da de 200).
  2. Quando entrar: no grafico de 15 minutos, espera uma "respirada" (RSI saindo de
     baixo de 35) perto da banda de baixo de Bollinger, com volume acima do normal.
  3. Sentimento: le o indice Fear & Greed (medo e ganancia do mercado cripto) e nao
     compra quando o mercado esta em euforia (>= 80).
  4. Quando sair: alvo de lucro que diminui com o tempo (minimal_roi), stop de 4%,
     stop que acompanha o lucro (trailing) e saida quando o RSI fica esticado (> 72).

Seguranca (docs/aulas/06-seguranca.md), herdada por todas as versoes:
  - piso de saldo: se o patrimonio cair abaixo de "guarda.saldo_minimo" do config,
    o robo para de comprar (pausa) ate alguem retomar no painel;
  - pausa manual: existindo o arquivo user_data/PAUSAR, nao compra nada;
  - protecoes do Freqtrade: esfriamento por moeda, trava apos varios stops seguidos,
    trava apos queda forte do saldo em 48 h, e trava da moeda que so da prejuizo.
"""
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
import talib.abstract as ta
from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy, informative
from pandas import DataFrame

logger = logging.getLogger(__name__)

URL_FEAR_GREED = "https://api.alternative.me/fng/?limit=0&format=json"
CANDLES_POR_HORA = 4  # timeframe de 15 min


class RoboTendencia(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "15m"
    can_short = False
    startup_candle_count = 220

    # alvo de lucro por tempo de operacao (minutos -> lucro minimo para vender)
    minimal_roi = {"0": 0.04, "60": 0.025, "240": 0.015, "720": 0.005}
    stoploss = -0.04
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02
    trailing_only_offset_is_reached = True

    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False

    # sentimento: nao compra com o mercado em euforia
    fng_max_entrada = 80

    _fng: pd.DataFrame | None = None
    _fng_lido_em = 0.0
    _ultimo_status = 0.0

    # ------------------------------------------------------------------ seguranca
    @property
    def protections(self):
        h = CANDLES_POR_HORA
        return [
            # depois de vender uma moeda, espera 30 min antes de comprar a mesma de novo
            {"method": "CooldownPeriod", "stop_duration_candles": 2},
            # 3 stops em 6 h (qualquer moeda): para de comprar por 6 h
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 6 * h,
                "trade_limit": 3,
                "stop_duration_candles": 6 * h,
                "only_per_pair": False,
            },
            # perdeu 10% do saldo em 48 h: para de comprar por 24 h
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 48 * h,
                "trade_limit": 3,
                "stop_duration_candles": 24 * h,
                "max_allowed_drawdown": 0.10,
            },
            # moeda que deu prejuizo nas 2 ultimas em 24 h: fica 12 h de castigo
            {
                "method": "LowProfitPairs",
                "lookback_period_candles": 24 * h,
                "trade_limit": 2,
                "stop_duration_candles": 12 * h,
                "required_profit": -0.02,
            },
        ]

    def _saldo_inicial(self) -> float:
        # o Freqtrade separa 1% de reserva (tradable_balance_ratio); aqui vale o saldo inteiro
        if not self.wallets:
            return 0.0
        if self.config.get("available_capital"):  # dinheiro real: so o valor liberado na tela Conta
            return float(self.config["available_capital"])
        return self.wallets.get_starting_balance() / self.config.get("tradable_balance_ratio", 1.0)

    def _saldo_minimo(self) -> float:
        guarda = self.config.get("guarda", {})
        return float(guarda.get("saldo_minimo", self._saldo_inicial() * 2 / 3))

    def _patrimonio(self) -> float:
        """Saldo inicial + lucro das operacoes fechadas + lucro (ou perda) das abertas."""
        total = self._saldo_inicial() + Trade.get_total_closed_profit()
        for trade in Trade.get_trades_proxy(is_open=True):
            df, _ = self.dp.get_analyzed_dataframe(trade.pair, self.timeframe)
            if len(df):
                total += trade.calc_profit(float(df["close"].iloc[-1]))
        return float(total)

    def _arquivo_pausa(self) -> Path:
        return Path(self.config["user_data_dir"]) / "PAUSAR"

    def _ao_vivo(self) -> bool:
        return self.dp.runmode.value in ("dry_run", "live")

    def _motivo_pausa(self) -> str | None:
        # o arquivo de pausa so vale para o robo ligado; o backtest nao le nem grava
        ao_vivo = self._ao_vivo()
        if ao_vivo and self._arquivo_pausa().exists():
            motivo = self._arquivo_pausa().read_text(encoding="utf-8").strip()
            return motivo or "Pausado manualmente no painel."
        if self.wallets and self._patrimonio() < self._saldo_minimo():
            motivo = (
                f"Saldo abaixo do piso de seguranca (R$ {self._saldo_minimo():.2f}). "
                "Revise a estrategia antes de retomar."
            )
            if ao_vivo:
                # a pausa continua mesmo se o saldo voltar ou o robo reiniciar
                self._arquivo_pausa().write_text(motivo, encoding="utf-8")
                logger.warning("GUARDA: %s", motivo)
            return motivo
        return None

    def bot_loop_start(self, current_time: datetime, **kwargs) -> None:
        """A cada 30 s grava user_data/guarda_status.json para o painel."""
        if not self._ao_vivo():
            return
        if time.time() - self._ultimo_status < 30:
            return
        self._ultimo_status = time.time()
        try:
            fng = self._carregar_fear_greed()
            status = {
                "atualizado_em": datetime.now(timezone.utc).isoformat(),
                "patrimonio": round(self._patrimonio(), 2),
                "saldo_inicial": round(self._saldo_inicial(), 2),
                "saldo_minimo": round(self._saldo_minimo(), 2),
                "pausa": self._motivo_pausa(),
                "fear_greed": int(fng["fng"].iloc[-1]) if fng is not None else None,
                "fng_max_entrada": self.fng_max_entrada,
            }
            destino = Path(self.config["user_data_dir"]) / "guarda_status.json"
            destino.write_text(json.dumps(status, ensure_ascii=False), encoding="utf-8")
        except Exception as erro:
            logger.warning("GUARDA: nao gravou status (%s)", erro)

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                            time_in_force: str, current_time: datetime, entry_tag: str | None,
                            side: str, **kwargs) -> bool:
        motivo = self._motivo_pausa()
        if motivo:
            logger.info("GUARDA: compra de %s bloqueada - %s", pair, motivo)
            return False
        return True

    # ------------------------------------------------------------------ sentimento
    def _carregar_fear_greed(self) -> pd.DataFrame | None:
        """Historico diario do Fear & Greed; relido no maximo 1x por hora."""
        if self._fng is not None and time.time() - self._fng_lido_em < 3600:
            return self._fng
        try:
            dados = requests.get(URL_FEAR_GREED, timeout=10).json()["data"]
            fng = pd.DataFrame(dados)
            fng["date"] = pd.to_datetime(fng["timestamp"].astype(int), unit="s", utc=True)
            fng["fng"] = fng["value"].astype(int)
            self._fng = fng[["date", "fng"]].sort_values("date").reset_index(drop=True)
            self._fng_lido_em = time.time()
        except Exception as erro:  # sem internet / API fora: segue sem o filtro
            logger.warning("Fear & Greed indisponivel (%s); filtro desligado.", erro)
        return self._fng

    # ------------------------------------------------------------------ indicadores
    @informative("1h")
    def populate_indicators_1h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        bb = ta.BBANDS(dataframe, timeperiod=20, nbdevup=2.0, nbdevdn=2.0)
        dataframe["bb_inferior"] = bb["lowerband"]
        dataframe["volume_medio"] = dataframe["volume"].rolling(30).mean()

        fng = self._carregar_fear_greed()
        if fng is not None and not dataframe.empty:
            fng = fng.assign(date=fng["date"].astype(dataframe["date"].dtype))
            unido = pd.merge_asof(
                dataframe[["date"]].sort_values("date"), fng, on="date", direction="backward"
            )
            dataframe["fng"] = unido["fng"].values
        else:
            dataframe["fng"] = 50  # neutro
        dataframe["fng"] = dataframe["fng"].fillna(50)
        return dataframe

    # ------------------------------------------------------------------ entrada
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        tendencia_alta = (dataframe["close_1h"] > dataframe["ema200_1h"]) & (
            dataframe["ema50_1h"] > dataframe["ema200_1h"]
        )
        respirada = (dataframe["rsi"].shift(1) < 35) & (dataframe["rsi"] >= 35)
        perto_banda = dataframe["low"].rolling(3).min() <= dataframe["bb_inferior"] * 1.005
        volume_ok = dataframe["volume"] > dataframe["volume_medio"]
        sem_euforia = dataframe["fng"] < self.fng_max_entrada

        dataframe.loc[
            tendencia_alta & respirada & perto_banda & volume_ok & sem_euforia,
            ["enter_long", "enter_tag"],
        ] = (1, "pullback_tendencia")
        return dataframe

    # ------------------------------------------------------------------ saida
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["rsi"] > 72, ["exit_long", "exit_tag"]] = (1, "rsi_esticado")
        return dataframe

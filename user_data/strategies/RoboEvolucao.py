"""
Evolucoes da RoboTendenciaBTC (relatorio de 20/10/2026, docs/aulas/08-evolucao.md).

  RoboAdaptativo   15 min; o filtro do Bitcoin so bloqueia quando o BTC esta em baixa
                   no grafico de 1 h E no diario (abaixo da media de 50 dias).
  RoboTendencia1h  1 h; tendencia lida no grafico de 4 h; alvos e stop maiores.
  RoboAdaptativo1h 1 h + o filtro flexivel do Bitcoin.

Todas herdam a guarda da RoboTendencia (piso de saldo, pausa, protecoes).
"""
import talib.abstract as ta
from freqtrade.strategy import informative, merge_informative_pair
from pandas import DataFrame

from RoboTendencia import RoboTendencia
from RoboTendenciaBTC import RoboTendenciaBTC


def _tendencia(df: DataFrame) -> DataFrame:
    df["ema50"] = ta.EMA(df, timeperiod=50)
    df["ema200"] = ta.EMA(df, timeperiod=200)
    return df


def _juntar_btc(estrategia, dataframe: DataFrame, tempo: str, sufixo: str) -> DataFrame:
    btc = _tendencia(estrategia.dp.get_pair_dataframe("BTC/BRL", tempo).copy())
    btc = btc[["date", "close", "ema50", "ema200"]]
    return merge_informative_pair(dataframe, btc, estrategia.timeframe, tempo, ffill=True,
                                  append_timeframe=False, suffix=sufixo)


class RoboAdaptativo(RoboTendenciaBTC):
    def informative_pairs(self):
        return [("BTC/BRL", "1h"), ("BTC/BRL", "1d")]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        return _juntar_btc(self, dataframe, "1d", "btcd")

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = RoboTendencia.populate_entry_trend(self, dataframe, metadata)
        btc_1h_baixa = (dataframe["close_btc"] < dataframe["ema200_btc"]) | (
            dataframe["ema50_btc"] < dataframe["ema200_btc"])
        btc_diario_baixa = dataframe["close_btcd"] < dataframe["ema50_btcd"]
        dataframe.loc[btc_1h_baixa & btc_diario_baixa, "enter_long"] = 0
        return dataframe


class RoboTendencia1h(RoboTendencia):
    timeframe = "1h"
    startup_candle_count = 220
    minimal_roi = {"0": 0.08, "360": 0.05, "1440": 0.03, "2880": 0.015}
    stoploss = -0.05
    trailing_stop_positive = 0.015
    trailing_stop_positive_offset = 0.03
    filtro_btc_flexivel = False

    @property
    def protections(self):
        return [
            {"method": "CooldownPeriod", "stop_duration_candles": 1},
            {"method": "StoplossGuard", "lookback_period_candles": 12, "trade_limit": 3,
             "stop_duration_candles": 12, "only_per_pair": False},
            {"method": "MaxDrawdown", "lookback_period_candles": 48, "trade_limit": 3,
             "stop_duration_candles": 24, "max_allowed_drawdown": 0.10},
            {"method": "LowProfitPairs", "lookback_period_candles": 24, "trade_limit": 2,
             "stop_duration_candles": 12, "required_profit": -0.02},
        ]

    def populate_indicators_1h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe  # sem o informativo de 1 h do pai: aqui 1 h ja e o tempo principal

    @informative("4h")
    def populate_indicators_4h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return _tendencia(dataframe)

    def informative_pairs(self):
        return [("BTC/BRL", "4h"), ("BTC/BRL", "1d")]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe = _juntar_btc(self, dataframe, "4h", "btc")
        return _juntar_btc(self, dataframe, "1d", "btcd")

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        tendencia_alta = (dataframe["close_4h"] > dataframe["ema200_4h"]) & (
            dataframe["ema50_4h"] > dataframe["ema200_4h"])
        respirada = (dataframe["rsi"].shift(1) < 35) & (dataframe["rsi"] >= 35)
        perto_banda = dataframe["low"].rolling(3).min() <= dataframe["bb_inferior"] * 1.005
        volume_ok = dataframe["volume"] > dataframe["volume_medio"]
        sem_euforia = dataframe["fng"] < self.fng_max_entrada
        btc_baixa = (dataframe["close_btc"] < dataframe["ema200_btc"]) | (
            dataframe["ema50_btc"] < dataframe["ema200_btc"])
        if self.filtro_btc_flexivel:
            btc_baixa = btc_baixa & (dataframe["close_btcd"] < dataframe["ema50_btcd"])
        dataframe.loc[
            tendencia_alta & respirada & perto_banda & volume_ok & sem_euforia & ~btc_baixa,
            ["enter_long", "enter_tag"],
        ] = (1, "pullback_tendencia_1h")
        return dataframe


class RoboAdaptativo1h(RoboTendencia1h):
    filtro_btc_flexivel = True

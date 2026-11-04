"""
Seguidor de tendencia de prazo longo (simulacao de 29/10/2026, docs/aulas/11-prazo-longo.md).

A ideia e o oposto do robo atual: em vez de ganhos de 1% a 3% (onde taxa e spread pesam muito),
buscar os movimentos grandes de 10% a 50% e ficar dentro enquanto a tendencia durar.

  Entrada (vela de 4 h):
    - a moeda esta em tendencia de alta no diario (media de 50 dias acima da de 200, preco acima da de 50);
    - o BTC/USDT tambem esta acima da media de 50 dias (mercado geral);
    - o preco rompe a maxima das ultimas 20 velas de 4 h (~3 dias), com volume acima da media;
    - sem euforia no Fear & Greed.
  Saida:
    - fecha abaixo da minima das ultimas 10 velas (o "canal" virou);
    - stop movel largo (liga em +12%, segura 6%) e stop de 10% para quando der errado logo.
Herda a guarda da RoboTendencia (piso de saldo, pausa).
"""
import talib.abstract as ta
from freqtrade.strategy import informative, merge_informative_pair
from pandas import DataFrame

from RoboTendencia import RoboTendencia


class RoboTendenciaLonga(RoboTendencia):
    timeframe = "4h"
    startup_candle_count = 1250       # ~208 dias: a media de 200 dias precisa de historico
    minimal_roi = {"0": 100}           # sem alvo fixo: quem vende e o canal ou o stop movel
    stoploss = -0.10
    trailing_stop = True
    trailing_stop_positive = 0.06
    trailing_stop_positive_offset = 0.12
    trailing_only_offset_is_reached = True
    use_exit_signal = True
    par_btc = "BTC/USDT"
    janela_entrada = 20
    janela_saida = 10

    @property
    def protections(self):
        return [
            {"method": "CooldownPeriod", "stop_duration_candles": 1},
            {"method": "StoplossGuard", "lookback_period_candles": 6, "trade_limit": 3,
             "stop_duration_candles": 6, "only_per_pair": False},
            {"method": "MaxDrawdown", "lookback_period_candles": 12, "trade_limit": 3,
             "stop_duration_candles": 6, "max_allowed_drawdown": 0.15},
        ]

    def populate_indicators_1h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe  # o informativo de 1 h do pai nao serve no tempo de 4 h

    @informative("1d")
    def populate_indicators_1d(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)
        return dataframe

    def informative_pairs(self):
        return [(self.par_btc, "1d")]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)  # rsi, volume medio, Fear & Greed
        dataframe["maxima"] = dataframe["high"].shift(1).rolling(self.janela_entrada).max()
        dataframe["minima"] = dataframe["low"].shift(1).rolling(self.janela_saida).min()
        btc = self.dp.get_pair_dataframe(self.par_btc, "1d").copy()
        btc["ema50"] = ta.EMA(btc, timeperiod=50)
        btc = btc[["date", "close", "ema50"]]
        return merge_informative_pair(dataframe, btc, self.timeframe, "1d", ffill=True,
                                      append_timeframe=False, suffix="btcd")

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        tendencia = (dataframe["ema50_1d"] > dataframe["ema200_1d"]) & (dataframe["close"] > dataframe["ema50_1d"])
        mercado = dataframe["close_btcd"] > dataframe["ema50_btcd"]
        rompe = dataframe["close"] > dataframe["maxima"]
        volume = dataframe["volume"] > dataframe["volume_medio"]
        sem_euforia = dataframe["fng"] < self.fng_max_entrada
        dataframe.loc[tendencia & mercado & rompe & volume & sem_euforia,
                      ["enter_long", "enter_tag"]] = (1, "rompimento_tendencia")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["close"] < dataframe["minima"], ["exit_long", "exit_tag"]] = (1, "canal_virou")
        return dataframe


class RoboTendenciaLongaSemBtc(RoboTendenciaLonga):
    """Sem o filtro do BTC: so a tendencia da propria moeda."""

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        tendencia = (dataframe["ema50_1d"] > dataframe["ema200_1d"]) & (dataframe["close"] > dataframe["ema50_1d"])
        rompe = dataframe["close"] > dataframe["maxima"]
        volume = dataframe["volume"] > dataframe["volume_medio"]
        dataframe.loc[tendencia & rompe & volume & (dataframe["fng"] < self.fng_max_entrada),
                      ["enter_long", "enter_tag"]] = (1, "rompimento_tendencia")
        return dataframe


class RoboTendenciaLongaLenta(RoboTendenciaLonga):
    """Canal mais longo: entra no rompimento de ~7 dias, sai na minima de ~3 dias."""
    janela_entrada = 42
    janela_saida = 20


# vizinhos da Lenta (robustez: se so o 42/20 exato funciona, e sorte)
class RoboLenta36_15(RoboTendenciaLonga):
    janela_entrada = 36
    janela_saida = 15


class RoboLenta48_24(RoboTendenciaLonga):
    janela_entrada = 48
    janela_saida = 24


class RoboLenta60_30(RoboTendenciaLonga):
    janela_entrada = 60
    janela_saida = 30

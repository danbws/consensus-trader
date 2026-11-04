"""
Simulacoes de 29/10/2026 (docs/hipoteses-testadas.md), so backtest:

  RoboMovelUSDT   a RoboSaidaMovel em pares contra o dolar (USDT), com o BTC/USDT como termometro
  RoboAdx20       RoboSaidaMovel que so compra com tendencia forte (ADX de 1 h acima de 20):
  RoboAdx25       fica de fora quando o mercado esta de lado
  RoboAdx20USDT   as duas coisas juntas
"""
import talib.abstract as ta
from freqtrade.strategy import informative, merge_informative_pair
from pandas import DataFrame

from RoboSaidas import RoboSaidaMovel


class RoboMovelUSDT(RoboSaidaMovel):
    par_btc = "BTC/USDT"

    def informative_pairs(self):
        return [(self.par_btc, "1h")]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # pula o populate_indicators da RoboTendenciaBTC (que le BTC/BRL) e refaz com o BTC/USDT
        from RoboTendencia import RoboTendencia
        dataframe = RoboTendencia.populate_indicators(self, dataframe, metadata)
        btc = self.dp.get_pair_dataframe(self.par_btc, "1h").copy()
        btc["ema50"] = ta.EMA(btc, timeperiod=50)
        btc["ema200"] = ta.EMA(btc, timeperiod=200)
        btc = btc[["date", "close", "ema50", "ema200"]]
        return merge_informative_pair(dataframe, btc, self.timeframe, "1h", ffill=True,
                                      append_timeframe=False, suffix="btc")


class _FiltroAdx:
    adx_minimo = 20

    @informative("1h")
    def populate_indicators_1h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        dataframe.loc[dataframe["adx_1h"] < self.adx_minimo, "enter_long"] = 0
        return dataframe


class RoboAdx20(_FiltroAdx, RoboSaidaMovel):
    adx_minimo = 20


class RoboAdx25(_FiltroAdx, RoboSaidaMovel):
    adx_minimo = 25


class RoboAdx20USDT(_FiltroAdx, RoboMovelUSDT):
    adx_minimo = 20

"""
RoboTendenciaBTC - variacao da RoboTendencia (aula 04: comparar versoes).

Muda duas coisas:
  - so compra quando o proprio Bitcoin esta em alta no grafico de 1 hora
    (em cripto, quando o BTC cai, quase tudo cai junto);
  - stop mais curto (2,5%) e alvos de lucro um pouco maiores, para a perda media
    nao ser maior que o ganho medio.
"""
from freqtrade.strategy import merge_informative_pair
from pandas import DataFrame
import talib.abstract as ta

from RoboTendencia import RoboTendencia


class RoboTendenciaBTC(RoboTendencia):
    minimal_roi = {"0": 0.05, "120": 0.03, "480": 0.02, "1440": 0.01}
    stoploss = -0.025

    def informative_pairs(self):
        return [("BTC/BRL", "1h")]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        btc = self.dp.get_pair_dataframe("BTC/BRL", "1h").copy()
        btc["ema50"] = ta.EMA(btc, timeperiod=50)
        btc["ema200"] = ta.EMA(btc, timeperiod=200)
        btc = btc[["date", "close", "ema50", "ema200"]]
        return merge_informative_pair(
            dataframe, btc, self.timeframe, "1h", ffill=True, append_timeframe=False, suffix="btc"
        )

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        btc_em_baixa = (dataframe["close_btc"] < dataframe["ema200_btc"]) | (
            dataframe["ema50_btc"] < dataframe["ema200_btc"]
        )
        dataframe.loc[btc_em_baixa, "enter_long"] = 0
        return dataframe


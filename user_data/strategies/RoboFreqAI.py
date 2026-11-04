"""
RoboFreqAI - estrategia com inteligencia artificial (FreqAI + LightGBM), so compra (spot).

Adaptada da FreqaiExampleStrategy que vem com o Freqtrade:
  - sem short (so compra e vende);
  - modelo preve a variacao media do preco nas proximas horas (alvo "&-s_close");
  - compra quando o modelo preve alta acima do limite (ENTRADA_MIN) e a previsao e confiavel (do_predict);
  - vende quando o modelo preve queda, ou pelo ROI/stop.
Uso: freqtrade backtesting -c user_data/configs_teste/config_freqai.json --strategy RoboFreqAI --freqaimodel LightGBMRegressor
"""
import logging
from functools import reduce

import talib.abstract as ta
from pandas import DataFrame
from technical import qtpylib

from freqtrade.strategy import IStrategy

logger = logging.getLogger(__name__)


class RoboFreqAI(IStrategy):
    INTERFACE_VERSION = 3
    can_short = False
    timeframe = "15m"

    # alvo de lucro e limite de tempo: sai em 8h no maximo
    minimal_roi = {"0": 0.05, "480": -1}
    stoploss = -0.04
    use_exit_signal = True
    process_only_new_candles = True
    startup_candle_count: int = 40

    # a previsao precisa passar de 0,6% (cobre as taxas de ~0,2% ida e volta com folga)
    ENTRADA_MIN = 0.006

    def feature_engineering_expand_all(self, dataframe: DataFrame, period: int, metadata: dict, **kwargs) -> DataFrame:
        dataframe["%-rsi-period"] = ta.RSI(dataframe, timeperiod=period)
        dataframe["%-mfi-period"] = ta.MFI(dataframe, timeperiod=period)
        dataframe["%-adx-period"] = ta.ADX(dataframe, timeperiod=period)
        dataframe["%-sma-period"] = ta.SMA(dataframe, timeperiod=period)
        dataframe["%-ema-period"] = ta.EMA(dataframe, timeperiod=period)

        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=period, stds=2.2)
        dataframe["bb_lowerband-period"] = bollinger["lower"]
        dataframe["bb_middleband-period"] = bollinger["mid"]
        dataframe["bb_upperband-period"] = bollinger["upper"]
        dataframe["%-bb_width-period"] = (
            dataframe["bb_upperband-period"] - dataframe["bb_lowerband-period"]
        ) / dataframe["bb_middleband-period"]
        dataframe["%-close-bb_lower-period"] = dataframe["close"] / dataframe["bb_lowerband-period"]
        dataframe["%-roc-period"] = ta.ROC(dataframe, timeperiod=period)
        dataframe["%-relative_volume-period"] = dataframe["volume"] / dataframe["volume"].rolling(period).mean()
        return dataframe

    def feature_engineering_expand_basic(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        dataframe["%-pct-change"] = dataframe["close"].pct_change()
        return dataframe

    def feature_engineering_standard(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        dataframe["%-day_of_week"] = dataframe["date"].dt.dayofweek
        dataframe["%-hour_of_day"] = dataframe["date"].dt.hour
        return dataframe

    def set_freqai_targets(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        n = self.freqai_info["feature_parameters"]["label_period_candles"]
        dataframe["&-s_close"] = dataframe["close"].shift(-n).rolling(n).mean() / dataframe["close"] - 1
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = self.freqai.start(dataframe, metadata, self)
        return dataframe

    def populate_entry_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        cond = [df["do_predict"] == 1, df["&-s_close"] > self.ENTRADA_MIN]
        df.loc[reduce(lambda x, y: x & y, cond), ["enter_long", "enter_tag"]] = (1, "ia_alta")
        return df

    def populate_exit_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        cond = [df["do_predict"] == 1, df["&-s_close"] < 0]
        df.loc[reduce(lambda x, y: x & y, cond), "exit_long"] = 1
        return df

    def confirm_trade_entry(self, pair, order_type, amount, rate, time_in_force, current_time, entry_tag, side, **kwargs) -> bool:
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = df.iloc[-1].squeeze()
        if rate > (last_candle["close"] * (1 + 0.0025)):
            return False
        return True
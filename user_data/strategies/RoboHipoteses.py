"""
Hipoteses do relatorio diario de 21/10/2026 (docs/relatorios/2026-10-21.md), so para backtest.

  RoboRsi40     respirada com RSI saindo de baixo de 40 (em vez de 35)
  RoboSemVolume sem a exigencia de volume acima da media
  RoboRsi40SemVolume as duas juntas
"""
from pandas import DataFrame

from RoboTendenciaBTC import RoboTendenciaBTC


class RoboRsi40(RoboTendenciaBTC):
    rsi_entrada = 40
    exigir_volume = True

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        tendencia_alta = (dataframe["close_1h"] > dataframe["ema200_1h"]) & (
            dataframe["ema50_1h"] > dataframe["ema200_1h"])
        respirada = (dataframe["rsi"].shift(1) < self.rsi_entrada) & (dataframe["rsi"] >= self.rsi_entrada)
        perto_banda = dataframe["low"].rolling(3).min() <= dataframe["bb_inferior"] * 1.005
        volume_ok = dataframe["volume"] > dataframe["volume_medio"] if self.exigir_volume else True
        sem_euforia = dataframe["fng"] < self.fng_max_entrada
        btc_alta = (dataframe["close_btc"] > dataframe["ema200_btc"]) & (
            dataframe["ema50_btc"] > dataframe["ema200_btc"])
        dataframe.loc[tendencia_alta & respirada & perto_banda & volume_ok & sem_euforia & btc_alta,
                      ["enter_long", "enter_tag"]] = (1, "pullback_tendencia")
        return dataframe


class RoboSemVolume(RoboRsi40):
    rsi_entrada = 35
    exigir_volume = False


class RoboRsi40SemVolume(RoboRsi40):
    exigir_volume = False

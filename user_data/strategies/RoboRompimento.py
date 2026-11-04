"""
RoboRompimento - RoboTendenciaBTC + uma segunda forma de entrar: o ROMPIMENTO (aula 09).

A entrada original compra na queda (respirada). Quando o mercado sobe sem respirar, ela fica
de fora. O rompimento compra quando a moeda, ja em tendencia de alta e com o BTC em alta:
  - fecha acima da maxima das ultimas N velas de 15 min (12 h na versao padrao);
  - com volume pelo menos 1,5 x a media;
  - com RSI entre 55 e 75 (forca, mas sem estar esticado demais);
  - sem euforia no Fear & Greed.
Saidas, stop e toda a guarda sao os mesmos da RoboTendenciaBTC.
"""
from pandas import DataFrame

from RoboTendenciaBTC import RoboTendenciaBTC


class RoboRompimento(RoboTendenciaBTC):
    janela_rompimento = 48      # velas de 15 min = 12 h
    volume_minimo = 1.5
    rsi_min, rsi_max = 55, 75

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)  # entrada da queda + filtro BTC
        tendencia_alta = (dataframe["close_1h"] > dataframe["ema200_1h"]) & (
            dataframe["ema50_1h"] > dataframe["ema200_1h"])
        btc_alta = (dataframe["close_btc"] > dataframe["ema200_btc"]) & (
            dataframe["ema50_btc"] > dataframe["ema200_btc"])
        maxima = dataframe["high"].shift(1).rolling(self.janela_rompimento).max()
        rompeu = dataframe["close"] > maxima
        volume_forte = dataframe["volume"] > dataframe["volume_medio"] * self.volume_minimo
        rsi_ok = dataframe["rsi"].between(self.rsi_min, self.rsi_max)
        sem_euforia = dataframe["fng"] < self.fng_max_entrada
        sinal = tendencia_alta & btc_alta & rompeu & volume_forte & rsi_ok & sem_euforia
        sinal &= dataframe["enter_long"].fillna(0) != 1
        dataframe.loc[sinal, ["enter_long", "enter_tag"]] = (1, "rompimento")
        return dataframe


class RoboRompimento24h(RoboRompimento):
    janela_rompimento = 96      # maxima de 24 h: menos sinais, mais fortes


class RoboRompimentoForte(RoboRompimento):
    janela_rompimento = 96
    volume_minimo = 2.0
    rsi_min, rsi_max = 60, 72

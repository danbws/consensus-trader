"""
Variacoes de SAIDA da RoboTendenciaBTC (docs/hipoteses-testadas.md, 21/10/2026). Entrada igual.

  RoboSaidaLonga     alvos maiores (8% -> 1,5% em 24 h), mesmo stop
  RoboSaidaMovel     quase sem alvo fixo: quem vende e o stop movel (liga em +2,5%, segura 1,5%)
  RoboSaidaCurta     alvos menores (2,5% -> 0,8%) e stop de 2%
  RoboSemSinalSaida  sem a venda por RSI acima de 72 (so alvo e stop)
  RoboStopLargo      stop de 4% (mais espaco para a moeda oscilar)
"""
from RoboTendenciaBTC import RoboTendenciaBTC


class RoboSaidaLonga(RoboTendenciaBTC):
    minimal_roi = {"0": 0.08, "240": 0.05, "720": 0.03, "1440": 0.015}


class RoboSaidaMovel(RoboTendenciaBTC):
    minimal_roi = {"0": 0.12, "2880": 0.01}
    stoploss = -0.03
    trailing_stop_positive = 0.015
    trailing_stop_positive_offset = 0.025


class RoboSaidaCurta(RoboTendenciaBTC):
    minimal_roi = {"0": 0.025, "60": 0.015, "240": 0.008}
    stoploss = -0.02
    trailing_stop_positive = 0.006
    trailing_stop_positive_offset = 0.012


class RoboSemSinalSaida(RoboTendenciaBTC):
    use_exit_signal = False


class RoboStopLargo(RoboTendenciaBTC):
    stoploss = -0.04

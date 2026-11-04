"""
Teste de robustez da RoboSaidaMovel: parametros vizinhos (se so o valor exato funciona, e sorte).
"""
from RoboSaidas import RoboSaidaMovel


class RoboMovel_1_2(RoboSaidaMovel):      # liga em +2%, segura 1%
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02


class RoboMovel_2_3(RoboSaidaMovel):      # liga em +3%, segura 2%
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.03


class RoboMovelStop25(RoboSaidaMovel):    # stop de 2,5% em vez de 3%
    stoploss = -0.025


class RoboMovelStop4(RoboSaidaMovel):     # stop de 4%
    stoploss = -0.04

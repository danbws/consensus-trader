"""
Hipotese do diario ao vivo de 29/10/2026: o alvo de 1% so depois de 48 h segura moedas paradas.
Variacoes da RoboSaidaMovel mudando so o tempo do alvo minimo.
"""
from RoboSaidas import RoboSaidaMovel


class RoboAlvo24h(RoboSaidaMovel):
    minimal_roi = {"0": 0.12, "1440": 0.01}


class RoboAlvo12h(RoboSaidaMovel):
    minimal_roi = {"0": 0.12, "720": 0.01}


class RoboAlvo24hMeio(RoboSaidaMovel):
    minimal_roi = {"0": 0.12, "1440": 0.005}

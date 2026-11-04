# Aula 8: testar antes de mudar (evoluções de 20/10/2026)

Estratégias em `user_data/strategies/RoboEvolucao.py`, saldo de R$ 50, proteções ligadas.

| Versão | Out/25 a mar/26 (mercado −58%) | Abr a out/26 (mercado +37%) | Último ano (mercado −34%) |
|---|---|---|---|
| **RoboTendenciaBTC (ligada)** | **−0,4%** | −7,9% | **−13,2%** |
| RoboAdaptativo (filtro do BTC flexível) | −4,5% | −16,8% | −22,6% |
| RoboTendencia1h (tempo de 1 h) | −22,1% | **−1,9%** | −18,6% |
| RoboAdaptativo1h (1 h + filtro flexível) | −21,5% | −9,1% | −26,8% |

**Conclusão:** afrouxar as regras fez o robô operar mais e perder mais. A versão ligada continua
a melhor no conjunto. A de 1 h foi melhor só no período de alta e muito pior na queda.

## Simulação com R$ 1.000 (robô ligado, reinvestindo tudo)
| Começo | Robô ligado | Proteção de capital (Aula 7) | Segurar as 12 | Segurar BTC |
|---|---|---|---|---|
| 01/06/2026 | R$ 999,66 (pior R$ 941) | R$ 949,35 (pior R$ 945) | R$ 1.199,01 (pior R$ 782) | R$ 1.105,31 (pior R$ 822) |
| 20/10/2025 (1 ano) | R$ 863,97 (pior R$ 813) | R$ 927,37 (pior R$ 925) | R$ 650,81 (pior R$ 405) | R$ 698,56 (pior R$ 520) |

Reinvestir não muda a porcentagem: o robô já usa o saldo inteiro em cada nova compra.
Com R$ 1.000 em vez de R$ 30, o resultado em % é praticamente o mesmo; muda só o tamanho em reais.

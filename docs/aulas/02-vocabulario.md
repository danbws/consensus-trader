# Aula 2: vocabulário mínimo

| Termo | O que é | No nosso robô |
|---|---|---|
| **Par** | As duas moedas da troca. Em `BTC/BRL` você compra bitcoin pagando em real | 12 pares em BRL |
| **Exchange / corretora** | Onde as ordens acontecem | Binance |
| **Candle (vela)** | Resumo de um período: abertura, máxima, mínima e fechamento | — |
| **Timeframe** | O tamanho de cada candle | 15 min (decisão) e 1 h (tendência) |
| **Ordem a mercado / limitada** | A mercado executa já, no preço que tiver. A limitada só executa no preço que você definir | Limitada, no melhor preço do livro |
| **Livro de ofertas** | A fila de quem quer comprar e de quem quer vender | Lido a cada ordem |
| **Spread** | A diferença entre o melhor preço de compra e o de venda: um custo escondido | Maior nos pares pequenos |
| **Taxa** | O que a corretora cobra por ordem | ~0,1% na entrada e 0,1% na saída |
| **Mínimo por ordem** | O menor valor que a corretora aceita | **R$ 10** nos pares em BRL |
| **Stake** | Quanto o robô coloca em cada operação | O saldo dividido por 2 (~R$ 15) |
| **ROI (alvo)** | O lucro em que o robô vende | 5% logo de cara, caindo para 1% depois de 1 dia |
| **Stop loss** | A perda máxima: vende para não perder mais | 2,5% |
| **Trailing stop** | Um stop que sobe junto com o lucro | Liga depois de +2% e protege +1% |
| **Drawdown** | A maior queda do saldo do topo até o fundo. Mede quanto dói | 19,6% no backtest |
| **Win rate** | Quantas operações deram lucro | 60%. Sozinho, não quer dizer nada! |
| **Profit factor** | Lucro total dividido pela perda total. Acima de 1 ganha, abaixo de 1 perde | 0,9 (perde) |
| **Backtest** | A regra rodando sobre o passado | Aula 4 |
| **Dry-run (paper)** | Preço real ao vivo, ordem simulada | Modo atual |
| **Overfitting** | Ajustar a regra até ela "acertar" o passado. No futuro ela quebra | O maior risco de quem otimiza |

## A conta das taxas (por que R$ 10 é pouco)
Cada operação completa (comprar e vender) custa cerca de **0,2%**, mais o spread.
O robô faz em média ~0,7 operação por dia.

- 250 operações por ano × 0,2% ≈ **50% do valor da operação pago em taxa ao longo do ano**.
- Ou seja: a estratégia precisa ganhar bem mais que isso só para empatar.

E o mínimo de R$ 10 cria uma armadilha: se você compra com R$ 10 e a moeda cai 2%, a sua
posição vale R$ 9,80 e **não pode ser vendida** (fica abaixo do mínimo). Por isso o teste usa
R$ 30, em operações de cerca de R$ 15.

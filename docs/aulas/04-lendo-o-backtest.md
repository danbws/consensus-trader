# Aula 4: lendo um backtest (com os nossos números reais)

Período: 01/10/2025 a 20/10/2026, preço real da Binance, R$ 30 fictícios, taxas incluídas.

| | RoboTendencia | RoboTendenciaBTC |
|---|---|---|
| Operações | 276 | 261 |
| Acerto (win rate) | **66%** | 60% |
| Resultado | **−42,7%** | **−7,7%** |
| Maior queda (drawdown) | 44,7% | 19,6% |
| Mercado (média das 12 moedas) | −41,7% | −41,7% |

## Lição 1: acertar muito não é ganhar
A primeira versão acerta 2 de cada 3 operações e mesmo assim perdeu quase metade do dinheiro.
Os ganhos eram pequenos (alvo de 0,5% a 4%) e as perdas iam até 4% mais taxa. Uma perda
apagava 3 ou 4 ganhos. O número que importa é o **profit factor** (lucro total ÷ perda total)
e a **expectativa** (quanto ganha em média por operação), não o acerto.

## Lição 2: compare com o mercado
O mercado caiu 41,7% no período. Um robô que só compra (não aposta na queda) sofre num ano de
queda. A segunda versão perdeu 7,7%: **protegeu muito melhor que segurar as moedas**, mas
ainda perdeu. Isso é melhor que comprar e segurar, e ainda não serve para dinheiro.

## Lição 3: o drawdown é o que você vai sentir
Num drawdown de 44,7%, os R$ 30 viram R$ 16,50 em algum momento. Pergunte a si mesmo se
aguentaria ver isso sem desligar o robô. Se não, a estratégia não é para você, mesmo que
termine positiva.

## Lição 4: cuidado com o overfitting
Seria fácil mexer nos números (RSI 33 em vez de 35, stop 2,3%...) até o backtest ficar verde.
O Freqtrade até tem uma ferramenta para isso (`hyperopt`). O problema é que você acaba
decorando o passado. A forma honesta de fazer:
1. otimizar num pedaço do histórico (ex.: out/2025 a abr/2026);
2. testar **sem mexer** no pedaço que ficou de fora (mai a out/2026);
3. confirmar no dry-run ao vivo, que é o "futuro" que ninguém viu.

## Lição 5: o backtest é otimista
No passado, toda ordem é executada no preço do candle. Ao vivo tem spread, ordem que não
executa e atraso. Espere um resultado ao vivo **pior** que o do backtest. Por isso o dry-run
existe.

## Exercício
Rode de novo, mudando só o período, e veja se a conclusão se mantém:
```powershell
.\.venv\Scripts\freqtrade.exe backtesting --config user_data/config.json --strategy-list RoboTendencia RoboTendenciaBTC --timerange 20260401- --breakdown month
```

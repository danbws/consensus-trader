# Aula 9: comprar mais vezes piorou; vender melhor ajudou (21/10/2026)

Tudo comparado com a versão que estava ligada (RoboTendenciaBTC), R$ 50, travas ligadas.
Tabela completa em `docs/hipoteses-testadas.md`.

## 1. Comprar mais vezes: todas pioraram
Rompimento da máxima, RSI 40 em vez de 35, sem exigir volume: o robô operou mais e perdeu mais
(de −5% a −35% no último ano, contra −13% da versão ligada). Cada operação custa ~0,2% em taxa;
compra que não é seletiva paga a taxa e perde.

## 2. Vender melhor: o stop móvel
A versão antiga vendia cedo, em alvos pequenos (1% a 5%), e perdia o resto da subida. A nova
(**RoboSaidaMovel**, ligada desde 21/10) quase não tem alvo fixo:
- quando a moeda sobe **2,5%**, liga o stop móvel;
- ele acompanha o topo e vende quando a moeda **devolve 1,5%** do ponto mais alto;
- se der errado desde o início, o stop vende com **3%** de perda.

| Período | Versão antiga | Stop móvel |
|---|---|---|
| Out/25 a mar/26 (usado para escolher) | −0,4% | +4,1% |
| Abr/26 em diante (fora da escolha) | −7,9% | +5,1% |
| Desde 01/06 | +0,2% | +6,5% |
| Último ano | −13,2% | +1,2% |
| Maior queda | 13% a 19% | ~9% |

## 3. Por que escolher num período e conferir no outro
Testando muitas versões, alguma sempre sai bonita por sorte. A defesa é escolher olhando **só um
período** e conferir num período que ficou de fora. A ideia de tirar as moedas que perderam no
1º período parecia ótima e piorou no 2º: era sorte do passado.

## 4. Ainda não é dinheiro real
A cada R$ 1 perdido, a versão nova ganha ~R$ 1,07 a R$ 1,11. O combinado para dinheiro real é
pelo menos R$ 1,20, mais 3 semanas ao vivo parecidas com o backtest.

# Aula 6: os mecanismos de segurança e como acompanhar

Um robô sem trava pode perder tudo numa sequência ruim. O nosso tem duas camadas: a de
**cada operação** e a do **robô inteiro**.

## Em cada operação
| Trava | O que faz |
|---|---|
| Stop de 3% | Se a moeda cair 3% abaixo do preço de compra, o robô vende |
| Stop móvel | Depois de +2,5%, se a moeda devolver 1,5% do topo, o robô vende e guarda o lucro. Desde 21/10 é ele quem faz quase todas as vendas (aula 9) |
| Até 2 operações | O saldo é dividido em duas partes. Uma moeda ruim não leva tudo |
| Mínimo de R$ 10 | Regra da Binance. Por isso o saldo do teste é R$ 50, não R$ 10 |

## No robô inteiro (ele para de comprar, mas continua cuidando do que já tem)
| Trava | Quando dispara | Quanto tempo |
|---|---|---|
| **Piso de saldo** | Saldo abaixo de R$ 33, um terço abaixo dos R$ 50 (configurável em `guarda.saldo_minimo`) | Até você clicar em **Retomar** |
| Sequência de stops | 3 stops em 6 horas | 6 horas |
| Queda forte | Saldo caiu 10% em 48 horas | 24 horas |
| Moeda de castigo | A moeda deu prejuízo nas 2 últimas vezes em 24 h | 12 horas, só aquela moeda |
| Esfriamento | Logo depois de vender uma moeda | 30 minutos, só aquela moeda |
| Euforia | Fear & Greed em 80 ou mais | Enquanto durar |

**Por que pausar e não vender tudo quando o saldo cai?** Vender no pânico costuma realizar a
pior perda. A pausa impede *novas* perdas e deixa as operações abertas terminarem no alvo ou
no stop. Se você quiser sair de tudo, o botão **Vender tudo** faz isso na hora.

**Por que a pausa do piso não volta sozinha?** Se o saldo caiu um terço, alguma coisa na
estratégia não está funcionando no mercado atual. Uma pessoa precisa olhar antes de continuar.

## Onde acompanhar
| Tela | Endereço | Para quê |
|---|---|---|
| Painel simples | <http://127.0.0.1:8090> | Saldo, distância até o piso, posições, travas, radar |
| Terminal de gráficos | <http://127.0.0.1:8090/terminal> | Velas ao vivo, indicadores do robô, setas de compra e venda, linha de stop |
| FreqUI (do Freqtrade) | <http://127.0.0.1:8080> | Tela técnica completa, em inglês |

## Como ler o terminal
- **Velas:** verde, a vela fechou acima de onde abriu; vermelha, abaixo. Cada vela é um período (escolha 1 min a 1 dia).
- **Linhas laranja:** as médias de 50 e 200 horas. O robô só compra quando a de 50 está acima da de 200.
- **Linha tracejada cinza:** a banda de baixo de Bollinger. O robô procura compras perto dela.
- **RSI (embaixo):** a compra acontece quando ele sobe de volta acima de 35. Acima de 72, o robô vende.
- **Setas:** cada compra (laranja) e venda (verde se lucro, vermelha se prejuízo) do robô.
- **Linhas no preço:** quando há uma moeda comprada, aparecem o preço de compra e o stop.

Os indicadores aparecem no tempo de 15 min, que é o que o robô usa para decidir.

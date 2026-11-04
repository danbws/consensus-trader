# Aula 3: a estratégia, peça por peça

Arquivos: `user_data/strategies/RoboTendencia.py` e `RoboTendenciaBTC.py` (a que está ligada).

A ideia se chama **pullback a favor da tendência**: compra uma moeda que está subindo, no
momento em que ela dá uma "respirada" (cai um pouco), apostando que a subida continua.

## 1. Onde investir: filtro de tendência (gráfico de 1 h)
- **Média móvel exponencial (EMA)** é a média dos últimos N preços, com mais peso nos recentes.
- A EMA de 200 horas é a tendência longa. A EMA de 50 horas é a tendência média.
- Regra: **o preço acima da EMA 200 e a EMA 50 acima da EMA 200** quer dizer que a moeda está em alta.
- Moeda que não passa nesse filtro é ignorada. É assim que o robô "escolhe onde investir"
  entre as 12.

## 2. O mercado como um todo: o Bitcoin (só na versão BTC)
Em cripto, quando o Bitcoin cai, quase tudo cai junto. Então, se o próprio BTC não está em
alta pelo mesmo critério, **o robô não compra nada**. Foi esse filtro que tirou o resultado de
−42,7% para −7,7% (Aula 4).

## 3. Quando entrar: a respirada (gráfico de 15 min)
- **RSI** (0 a 100) mede a força das últimas altas contra as quedas. Abaixo de 30–35 quer dizer
  que caiu demais e rápido.
- **Bandas de Bollinger** são uma faixa em volta da média que se abre e fecha com a volatilidade.
  Tocar a banda de baixo significa um preço "esticado para baixo".
- Regra de entrada:
  1. o RSI **estava abaixo de 35 e voltou para cima de 35** (a queda perdeu força);
  2. o preço tocou a banda de baixo nos últimos 3 candles;
  3. o volume está acima da média dos últimos 30 candles (tem gente negociando de verdade).

## 4. A "pesquisa": sentimento do mercado
- O **Fear & Greed Index** (alternative.me) é um número diário de 0 (pânico) a 100 (euforia),
  calculado a partir de volatilidade, volume, redes sociais e dominância do BTC.
- O robô relê o índice a cada hora e **não compra quando ele está em 80 ou mais**: na euforia,
  o risco de comprar no topo é maior.
- Se a API do índice cair, o robô segue sem esse filtro e registra um aviso no log.

## 5. Quando sair
| Saída | Regra |
|---|---|
| Alvo (ROI) | 5% na hora; depois de 2 h, 3%; depois de 8 h, 2%; depois de 24 h, 1% |
| Stop | −2,5% |
| Trailing | depois de +2%, se devolver mais que 1% do topo, vende |
| Sinal | RSI acima de 72 (subiu rápido demais): realiza o lucro |

## Para treinar o olho
Abra o painel, vá em **Chart**, escolha um par e adicione `ema50_1h`, `ema200_1h`,
`bb_inferior` e `rsi`. As setas verdes e vermelhas são as entradas e saídas. Compare com as
regras acima.

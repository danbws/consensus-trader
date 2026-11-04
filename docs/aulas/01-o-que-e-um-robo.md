# Aula 1: o que é um robô de trade (e o que ele não é)

## A ideia em uma frase
Um robô de trade é um programa que olha o preço, aplica **regras fixas** e manda ordens de
compra e venda para a corretora sozinho, 24 horas por dia.

## O que ele faz bem
- **Não cansa e não dorme.** Cripto negocia 24 horas, 7 dias por semana, inclusive feriado.
- **Não tem emoção.** Não segura uma perda "esperando voltar" e não compra por empolgação.
- **É testável.** Dá para rodar a mesma regra sobre um ano de preço real (backtest) e ver o
  que teria acontecido antes de arriscar um centavo.

## O que ele NÃO faz
- **Não adivinha o futuro.** Ele reage a padrões do passado. Quando o mercado muda de
  comportamento, uma regra que funcionava para de funcionar.
- **Não garante lucro.** A maioria dos robôs perde dinheiro, principalmente por causa das taxas.
  O nosso primeiro teste perdeu 42,7% num ano (Aula 4).
- **Não "pesquisa" como uma pessoa.** "Estar antenado" para um robô é ler números: preço,
  volume, indicadores e índices de sentimento. Ele não lê notícia nem entende contexto, a não
  ser que a gente programe isso. Veja "Próximos passos" na Aula 5.

## Como o nosso robô funciona, de ponta a ponta

```
Binance (preço real)  ──>  Freqtrade a cada ~10 s
                               │
                               ├─ a cada 15 min fecha um "candle" e recalcula os indicadores
                               ├─ a cada 1 h relê o índice Fear & Greed (sentimento)
                               ├─ escolhe, entre 12 moedas, a que deu sinal de compra
                               ├─ compra (simulado) com o saldo livre
                               └─ vende no alvo de lucro, no stop ou no sinal de saída
                                         │
                                  Painel  http://127.0.0.1:8080
```

## As 3 fases do nosso teste
1. **Backtest:** a regra sobre 12 meses de preço real. ✔ feito.
2. **Dry-run:** preço real ao vivo, dinheiro fictício, por 2 a 4 semanas. ← estamos aqui.
3. **Dinheiro real e pequeno:** só se as fases 1 e 2 forem boas (checklist na Aula 5).

> Por que não o "dinheiro de teste" (testnet) da Binance? Na testnet o preço e o volume são
> artificiais, com pouca gente negociando. O dry-run usa o mercado **real**, só que finge as
> ordens. Por isso ele é um teste melhor da estratégia.

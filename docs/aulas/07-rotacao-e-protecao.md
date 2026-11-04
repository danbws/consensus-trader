# Aula 7: rotação de moedas e proteção de capital (simulação de 20/10/2026)

Script: `scripts/simula_rotacao.py`. Dados diários reais da Binance (pares em BRL), taxa e
escorregamento de 0,2% por ordem, decisões tomadas só com o que se sabia no dia e executadas
na abertura do dia seguinte.

## A pergunta certa: "funciona começando em qualquer dia?"
Uma data só engana: a regra pode ter dado sorte. Por isso cada versão foi testada começando
em ~90 datas diferentes, de 5 em 5 dias, de abril/2025 a setembro/2026, sempre até hoje,
com R$ 30.

| Versão | Mediana final | Pior final | Melhor final | Pior saldo no caminho |
|---|---|---|---|---|
| Segurar as 12 moedas | R$ 27,03 | R$ 15,71 | R$ 44,72 | **R$ 9,91** |
| Segurar só BTC | R$ 25,65 | R$ 18,45 | R$ 39,25 | R$ 13,73 |
| A) Radar puro: 3 mais fortes, troca mensal | R$ 24,84 | R$ 8,74 | R$ 44,10 | R$ 6,26 |
| C) Radar semanal + stop 15% + filtro BTC | R$ 28,60 | R$ 16,61 | R$ 40,21 | R$ 16,61 |
| **D) C + proteção de capital (piso 90%)** | **R$ 28,50** | **R$ 27,22** | R$ 31,69 | **R$ 27,22** |
| E) C + piso 85% | R$ 27,85 | R$ 25,73 | R$ 34,48 | R$ 25,73 |

Começando em 01/06/2026: segurar as 12 daria R$ 35,97; a versão D, R$ 28,50; o radar puro, R$ 22,20.

## O que isso ensina
1. **O período foi de queda.** De abril/2025 a outubro/2026 o mercado cripto caiu na maior parte
   do tempo. Nenhuma regra ganhou na maioria das datas. Quem segurou chegou a ver R$ 30 virar R$ 9,91.
2. **A proteção de capital funciona como prometido:** em nenhuma das ~90 datas a versão D ficou
   abaixo de R$ 27,22. Ela troca o ganho grande pela perda pequena.
3. **Rotação perde a moeda que dispara depois de cair.** A NEAR caiu 20% em julho, saiu do topo
   do radar em agosto e subiu 130% em setembro. Regra de momento chega atrasada nas viradas.
4. **Proteger 100% do capital só com cripto é impossível.** Com piso de 100%, o robô nunca
   compraria nada. O piso de 90% significa: "aceito perder no máximo ~10%".

## Como funciona a proteção (CPPI)
- Piso = 90% do capital (R$ 27). Colchão = saldo - piso (R$ 3 no começo).
- O robô investe no máximo **4 x o colchão** (R$ 12 no começo; o resto fica em real).
- Se ganha, o colchão cresce e ele investe mais. Se perde, investe menos. Encostou no piso, vende tudo.
- Risco que sobra: uma queda brusca entre duas checagens pode furar o piso um pouco.

## Proteger o capital de verdade: arriscar só o rendimento
A forma clássica de "não perder o capital inicial" não está dentro da cripto: é deixar o
capital numa aplicação de baixo risco (renda fixa) e mandar para o robô **só o rendimento**.
Se o robô perder tudo, o capital continua lá. Se ganhar, soma.

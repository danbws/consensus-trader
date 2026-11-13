# Hipóteses já testadas

Antes de sugerir uma mudança no robô, confira aqui. Todas comparadas com a RoboTendenciaBTC (ligada),
R$ 50, proteções ligadas. Resultado em % do saldo.

| Data | Hipótese | Out/25 a mar/26 | Abr/26 em diante | Último ano | Veredito | Arquivo |
|---|---|---|---|---|---|---|
| 20/10 | Referência: RoboTendenciaBTC | −0,4% | −7,9% | −13,2% | ligada | RoboTendenciaBTC.py |
| 20/10 | Filtro do BTC flexível (só bloqueia com BTC diário em baixa) | −4,5% | −16,8% | −22,6% | pior | RoboEvolucao.py |
| 20/10 | Tempo de 1 h, tendência de 4 h | −22,1% | −1,9% | −18,6% | pior | RoboEvolucao.py |
| 20/10 | 1 h + filtro flexível | −21,5% | −9,1% | −26,8% | pior | RoboEvolucao.py |
| 21/10 | Entrada extra por rompimento da máxima de 12 h | −15,4% | −11,7% | −26,5% | pior | RoboRompimento.py |
| 21/10 | Rompimento da máxima de 24 h | −6,1% | −13,5% | −21,9% | pior | RoboRompimento.py |
| 21/10 | Rompimento de 24 h com volume 2x e RSI 60-72 | −4,5% | −15,7% | −23,2% | pior | RoboRompimento.py |
| 21/10 | RSI 40 em vez de 35 (relatório de 21/10) | −14,8% | −25,6% | −34,1% | pior | RoboHipoteses.py |
| 21/10 | Sem exigir volume (relatório de 21/10) | −4,9% | −33,3% | −34,7% | pior | RoboHipoteses.py |
| 21/10 | RSI 40 e sem volume | −21,7% | −23,3% | −34,5% | pior | RoboHipoteses.py |
| 21/10 | Alvos maiores (8% -> 1,5%) | −1,5% | −6,3% | −13,4% | igual/pior | RoboSaidas.py |
| 21/10 | Alvos menores (2,5%) e stop 2% | −11,5% | −17,6% | −27,6% | pior | RoboSaidas.py |
| 21/10 | Sem venda por RSI > 72 | +3,8% | −5,6% | −7,4% | melhor no 1º, perde no 2º | RoboSaidas.py |
| 21/10 | Stop de 4% | −5,9% | +3,8% | −8,1% | instável | RoboSaidas.py |
| 21/10 | **Stop móvel vende (liga em +2,5%, segura 1,5%), stop 3%, quase sem alvo fixo** | **+4,1%** | **+5,1%** | **+1,2%** | **melhor em todos; desde 01/06: +6,5%; PF 1,11 e 1,07** | RoboSaidas.py (RoboSaidaMovel) |
| 21/10 | Vizinhos do stop móvel (1%/2%, 2%/3%, stop 2,5% e 4%) | −2,4% a +6,0% | −7,0% a +5,3% | | 2%/3% parecido; stop 2,5% instável | RoboSaidasVizinhas.py |
| 21/10 | Tirar as 5 moedas que perderam no 1º período (SUI, AVAX, LTC, SOL, XRP) | escolhido aqui | −5,8% (Movel) / −14,2% (atual) | | **pior fora da amostra: não escolher moeda pelo passado** | config de 7 pares |
| 29/10 | Alvo de 1% depois de 24 h em vez de 48 h (diário ao vivo) | +7,0% | +1,4% | −1,3% | melhor no 1º, pior no 2º: **fica 48 h** | RoboTempoAlvo.py |
| 29/10 | Alvo de 1% depois de 12 h | −0,6% | −1,0% | −6,4% | pior | RoboTempoAlvo.py |
| 29/10 | Alvo de 0,5% depois de 24 h | +5,8% | +0,6% | −2,6% | pior no 2º | RoboTempoAlvo.py |
| 29/10 | **Taxa com desconto do BNB (0,075% em vez de 0,1% por ordem)**, mesma estratégia | **+6,1%** | **+9,6%** | **+7,0%** | **melhor em todos; vale só no dinheiro real, pagando a taxa em BNB** | --fee 0.00075 |
| 29/10 | Só comprar com tendência forte (ADX 1 h > 20) | +1,2% | +3,4% | −0,7% | pior | RoboRegime.py |
| 29/10 | Só comprar com ADX 1 h > 25 | −2,7% | +3,6% | −2,4% | pior | RoboRegime.py |
| 29/10 | Mesma estratégia em 20 pares contra o dólar (USDT) | −27,5% | −19,6% | −34,1% | **muito pior** | RoboRegime.py, config_usdt20 |
| 29/10 | Mesmas 12 moedas, contra o dólar (USDT) | −21,3% | −23,3% | −34,7% | **muito pior: o ganho depende dos pares em real** | config_usdt12 |
| 29/10 | Pares em real cobrando +0,05% por ordem (spread) | −1,6% | −1,3% | −9,5% | **o lucro some** | --fee 0.0015 |
| 29/10 | Pares em real cobrando +0,1% por ordem (spread) | −2,5% | −10,7% | −18,9% | **perde** | --fee 0.002 |
| 29/10 | Robô atual só nas 6 moedas líquidas em real (BTC ETH SOL XRP BNB LTC; escolhidas pelo spread, não pelo resultado) | −1,0% | +3,4% | 0,0% | **sem vantagem: o lucro vinha das moedas de spread alto** | config_brl_liquidos |
| 29/10 | Prazo longo, 20 moedas em USDT, vela de 4 h, rompimento de ~3 dias / saída ~1,5 dia (custo 0,12%) | −1,9% | −2,4% | −2,4% | pior | RoboTendenciaLonga.py |
| 29/10 | Prazo longo "Lenta" (rompimento ~7 dias / saída ~3 dias) | −1,4% | +9,7% | +9,7% | parecia boa... | RoboTendenciaLonga.py |
| 29/10 | Lenta e vizinhos, 4 anos (ago/22 a out/26, ano a ano): +1,7% / **−34,3%** (mercado +142%) / −1,5% / +3,2%; vizinhos de −36% a +31% | | | | **não robusta: o +9,7% foi sorte do período** | RoboTendenciaLonga.py |
| 20/10 | 13 estratégias da comunidade, NostalgiaForInfinity e FreqAI | ver docs/resultados-estrategias.md | | | nenhuma consistente | |
| 20/10 | Rotação de moedas com proteção de capital (piso 90%) | ver docs/aulas/07-rotacao-e-protecao.md | | | protege, não lucra | simula_rotacao.py |

## O que o conjunto mostra
Todas as mudanças que fazem o robô **comprar mais vezes** pioraram o resultado. Neste mercado e com
taxa de 0,2% por operação, a entrada "na respirada" da versão ligada só se paga quando é seletiva.
Mexer em **quando sair** funcionou: deixar o stop móvel vender (RoboSaidaMovel) foi a primeira
versão positiva nos dois períodos separados, com queda máxima menor (9% contra 13% a 19%).
O profit factor (1,07 a 1,11) ainda fica abaixo do 1,2 combinado para dinheiro real.
Escolher **quais moedas** pelo resultado passado não funcionou fora da amostra.

## Alerta de 29/10: o ganho pode ser ilusão do mercado em real
A mesma estratégia, nas mesmas moedas, perde ~35% ao ano contra o dólar e só ganha nos pares em real,
que têm pouco volume. E o ganho em real some quando o teste cobra um spread realista (0,05% por ordem).
Hipótese mais provável: a estratégia "ganha" comprando as tremidas de um livro de ofertas fino, e na vida
real essas tremidas custam o spread. O backtest não cobra spread; o teste ao vivo usa ordens limitadas e
pode estar sendo otimista também. **Antes de qualquer dinheiro real, medir no teste ao vivo se as compras e
vendas saem no preço que o backtest supõe** (preço da ordem contra o preço da vela).
**Medição de 29/10 (scripts/qualidade_execucao.py):** as 4 operações do teste ao vivo saíram até 0,06% melhores que
o backtest supõe, mas o teste ao vivo não sabe se a ordem seria aceita num livro fino. Spread medido: BTC, ETH, SOL,
XRP, BNB e LTC perto de zero; ADA 0,37%, AVAX 0,48%, PEPE 0,42%, SUI 0,20%, LINK 0,14%.

## Balanço de 29/10 (cerca de 40 hipóteses)
Nenhuma estratégia de trade testada mostrou vantagem que resista a: dois períodos separados, ajustes vizinhos,
custo realista (taxa + spread) e moedas líquidas. A versão ligada continua no teste ao vivo para medir, mas hoje
não há base para dinheiro real.
## Ações EUA: consenso dos grandes investidores (30/10, scripts/estudo_consenso.py e estudo_consenso_robustez.py)
16 gestores, 595 relatórios 13F (2016 a 2026), preços diários da Alpaca. Cada relatório só vale a partir da data de entrega.
Regra: comprar as 10 ações que mais gestores têm como "maior aposta" (3% ou mais da carteira), trocar a cada trimestre.

| Versão | 2018-2021 (escolha) | 2022-2026 (fora) | Último ponto |
|---|---|---|---|
| S&P 500 (segurar o índice) | 14,9% ao ano | 13,8% ao ano | queda máx. 33,8% |
| **Consenso top 10** (corrigido: cada empresa conta uma vez por gestor) | **15,3%** | **15,3%** | |
| Consenso top 10, primeira conta (Google e Berkshire contados duas vezes) | 17,4% | 16,5% | queda máx. 28,9% |
| Consenso + tendência | 13,7% | 16,2% | |
| Consenso + tendência + filtro do S&P | 8,5% | 13,4% | filtro atrapalha |
| Consenso top 20 | 14,1% | 12,7% | diluir atrapalha |
| Copiar só o Buffett (top 10) | 9,0% | 8,4% | perde do índice |

Vizinhos, já com a correção (custo 0,2%, classes de ação somadas por empresa): 6 de 9 ganham do índice nos dois períodos
(base, corte 2%, 3 gestores, top 8, entrar 5 ou 20 dias depois). Perdem no 2º período: corte 5%, top 12 e top 15. Viés de sobrevivência: 10 escolhas sem preço contra 340 com preço.
**Veredito: primeira regra com vantagem que resiste aos testes, mas pequena (0,4 a 1,5 ponto por ano acima do índice, na versão corrigida)
e com quedas parecidas com as do índice.** Candidata a rodar na conta de papel.
## Cripto: seguir o dinheiro dos ETFs de bitcoin (04/11, scripts/estudo_etf_btc.py e estudo_etf_btc_controle.py)

Pergunta: o fluxo diário dos ETFs de bitcoin dos EUA (o "dinheiro grande", dados da Farside, 11/01/2024 a 03/11/2026) avisa para onde o BTC vai?
Sem olhar o futuro (o fluxo do dia só é usado a partir do fim do dia seguinte), custo de 0,15% por troca, P1 = jan/2024 a jun/2025 (BTC +88,6% ao ano), P2 = jul/2025 a nov/2026 (BTC −20,7% ao ano).

- **Fluxo de hoje × preço de amanhã: correlação +0,04 (praticamente zero).** No mesmo dia é +0,38, mas aí é o preço puxando o fluxo, e não dá para usar.
- **70 variantes** (comprado quando o fluxo é positivo, ou "só sai quando a saída dos últimos N dias passa de X"): 5 vencem comprar-e-segurar no P1, 62 no P2, **3 nos dois**.
- A melhor do P1 ("sai quando a saída de 10 dias passa de US$ 1 bilhão"): **+102% no P1 (BTC +89%) e +4,3% no P2 (BTC −20,7%)**, com 13 trocas no P2. Ela ganha de 88% e 95% dos sorteios que ficam fora do mercado o mesmo tempo, então tem algo de real ali.
- **Mas é frágil: das 18 vizinhas, só ela mesma vence nos dois períodos.** O padrão de todas é o de um **freio**: perde na alta (P1) e segura parte da queda (P2). Uma regra boba de preço (média de 50 dias) faz parecido no P2 (−1,9%).
- Menos de 3 anos de dados e poucos episódios de saída forte (2 ou 3 no P1).

**Veredito:** o fluxo dos ETFs não prevê o preço do dia seguinte. Grandes saídas seguidas funcionam como freio em queda, mas custam na alta, e a escolha exata dos números importa demais. **Não muda a decisão de 04/11: cripto continua sem dinheiro real.** Dá para reavaliar quando houver mais dados (fim de 2027), com a regra congelada hoje (10 dias, US$ 1 bilhão) para não escolher de novo olhando o resultado.

## Seguir o relatório COT da CFTC (04/11, scripts/estudo_cot.py)

Pergunta: o relatório semanal de quem está comprado e vendido nos futuros (COT, a base de painéis pagos de "posicionamento institucional") avisa para onde o ativo vai?
Testado nos ETFs dos futuros: SPY (S&P 500), GLD (ouro), SLV (prata), TLT (título longo) e FXE (euro). Índice COT clássico (posição líquida na escala 0-100 das últimas N semanas), seguindo os comerciais ou os especuladores, N em 26/52/156 semanas, limite em 50/65/80: 18 regras por ativo, 90 no total.
Sem olhar o futuro: posição de terça só vale a partir da segunda seguinte. Nas paralisações do governo (2018-19 e 2025-26), só depois que a CFTC publicou. Fora do mercado o dinheiro fica no BIL. Custo de 0,1% por troca. P1 = jul/2016 a jun/2021, P2 = jul/2021 a out/2026.

- **A regra clássica de Larry Williams (comerciais, 3 anos, limite 80), marcada antes de rodar, perde de comprar e segurar nos 5 ativos e nos dois períodos.** No S&P 500: 16,4% e 8,5% ao ano, contra 17,4% e 12,7%.
- **S&P 500 e ouro: nenhuma das 36 regras vence nos dois períodos.** A melhor do P1 no S&P rende 6,0% ao ano no P2 (índice 12,7%) e empata com o sorteio (50%). No ouro, 5,8% contra 15,4%.
- **16 das 90 regras vencem nos dois períodos, quase todas no título longo e no euro.** Esses dois ficaram parados ou caíram no P2 (TLT −7,0% ao ano), enquanto o caixa rendia 3,5%. Qualquer tempo fora do mercado já ganhava: no TLT, as 18 regras vencem no P2. A melhor do euro rende 3,4% no P2, o mesmo que o caixa.
- Seguir os especuladores (tendência) foi um pouco melhor que seguir os comerciais (13 contra 3 de 45), mas pelo mesmo motivo do caixa.

**Veredito:** o COT não dá vantagem nos ativos que interessam (ações e ouro). Onde parece funcionar, é o caixa rendendo enquanto o ativo caía. Não entra no robô. Um painel que vende nota a partir do COT precisaria mostrar um resultado medido melhor que este para valer a assinatura.

## Ações EUA: tirar quando cai e colocar depois (05/11, scripts/estudo_saida_queda.py)

Pergunta: a carteira de consenso caiu 2,4% num dia (ganho de R$ 305 para R$ 169). Sair nas quedas e voltar depois rende mais que ficar parado?
Base: a carteira de consenso diária de 2018 a 2026 (custo 0,2%). Por cima dela, 20 regras: sair depois de um dia de queda de 1,5%, 2% ou 3% e voltar em 5, 10 ou 20 pregões; sair a 5, 10, 15 ou 20% abaixo do topo e voltar acima da média de 20 ou 50 dias; ficar só acima da média de 50, 100 ou 200 dias. Decisão no fechamento, vale no dia seguinte; 0,2% por saída ou volta; fora do mercado rende como título curto.

- **Depois de um dia de queda de 2% ou mais (128 vezes), a carteira subiu em média 2,0% nos 20 pregões seguintes, mais que num dia qualquer (1,3%).** Depois de quedas de 3% (47 vezes), subiu 2,6%. Os dias de alta forte costumam vir logo depois dos de queda; quem sai perde justamente eles.
- **Nenhuma das 20 regras ganha de ficar parado nos dois períodos** (parado: 15,3% e 15,4% ao ano). As que saem rápido (queda de 1,5% ou 5% do topo) rendem entre −7% e +6% ao ano.
- A melhor de 2018-2021 (sair depois de queda de 3%, voltar em 10 pregões) rende 13,6% em 2022-2026, contra 15,4% parado, e perde para 64% dos sorteios.
- Algumas regras diminuem a queda máxima (média de 200 dias: −17% contra −27%), mas pagam com 2 a 10 pontos a menos por ano.

**Veredito:** para esta carteira, tirar na queda e colocar depois custa dinheiro. A regra continua: não vende porque caiu; só avisa em −20%, −30% e −40%.

## Ações EUA: compras em grupo dos diretores (12/11, scripts/estudo_insiders.py)

Pergunta: quando vários diretores ou executivos de uma empresa compram ações dela com o próprio dinheiro em poucos dias, a ação sobe mais que o mercado nos meses seguintes?
Base: formulários 4 da SEC de 2016 a 2026 (110.877 compras a mercado de diretores e executivos, 6.510 empresas; fundo que é só "dono de 10%" fica de fora). O sinal só vale a partir da entrega do formulário que completa o grupo; entrada no fechamento do pregão seguinte; custo 0,2%. Grupo de 2, 3 ou 4 diretores em até 30 dias, somando US$ 100 mil ou US$ 500 mil; segurar 21, 63 ou 126 pregões (18 versões). 93% dos sinais têm preço na Alpaca.

- **Nenhuma das 18 versões ganha do S&P 500 nos dois períodos** (S&P: 18,3% ao ano em 2017-2021 e 11,6% em 2022-2026). Em 2022-2026 as carteiras rendem de 0,6% a 6,4% ao ano, com quedas de 31% a 39%.
- Por sinal, a ação sobe mais que o S&P em só 43% a 45% das vezes; o resultado mediano é 2 a 3 pontos abaixo do índice em 3 meses, nos dois períodos.
- A melhor de 2017-2021 (4 diretores, US$ 500 mil, 3 meses: +2,5 pontos por sinal) vira −1,2 ponto em 2022-2026.
- O efeito que estudos antigos encontraram (com dados dos anos 80 e 90) não aparece nestes 10 anos; a informação fica pública no dia da entrega do formulário.
- Vieses: empresa que quebrou ou trocou de código pode não ter preço (7% dos sinais), o que deixaria o resultado ainda pior.

**Veredito:** seguir as compras dos diretores não dá vantagem e piora a queda. Não entra no robô.

## Ações EUA: seguir o que os gestores compraram no trimestre (12/11, scripts/estudo_compras_gestores.py)

Pergunta: em vez de seguir o que os gestores já têm (o consenso), seguir o que eles acabaram de comprar ou aumentar rende mais?
Base: os mesmos 16 gestores e 596 relatórios 13F do consenso. O 13F guardado traz o peso de cada ação, não a quantidade: "nova" é a empresa que não estava no relatório anterior e entrou com peso de 2%, 3% ou 5%; "aumento" é o peso subir 1, 2 ou 3 pontos. Sempre 10 ações em partes iguais, troca no dia 16 depois do prazo do 13F, custo 0,2%. 14 versões.

| Versão | 2018-2021 | 2022-2026 |
|---|---|---|
| S&P 500 | 14,9% ao ano | 13,8% ao ano |
| Consenso (a regra de hoje) | 15,0% | 15,3% |
| Só as posições novas (6 versões) | −7,8% a 12,6% | −5,7% a 12,6% |
| Só os aumentos (6 versões) | −11,8% a 11,5% | −0,5% a 11,2% |
| Consenso, com as que algum gestor aumentou na frente (2 versões) | 15,4% e 16,9% | 15,0% e 15,0% |

- **Seguir só as compras do trimestre perde do S&P e do consenso** nas 12 versões, com quedas de até 78%.
- Pôr na frente do consenso as ações que algum gestor aumentou ganha do S&P nos dois períodos, mas não do consenso simples em 2022-2026 (15,0% contra 15,3%). A melhora de 2018-2021 não se repete fora da amostra.

**Veredito:** o consenso continua como está. Seguir as compras do trimestre não entra no robô.

## Ações EUA + uma fatia fixa de bitcoin (12/11, scripts/estudo_fatia_btc.py)

Pergunta: uma fatia fixa de bitcoin dentro da carteira de consenso, só comprada e mantida (sem robô de trade), melhora o resultado? Quanto aumenta as quedas?
Base: a carteira de consenso diária de 2018 a 2026 e o BTC/USDT diário da Binance. Fatias de 0%, 2,5%, 5%, 10% e 20%, voltando ao peso a cada 3 meses ou nunca. Custo de 0,2% sobre o que se troca.

| Fatia de BTC (volta ao peso a cada 3 meses) | 2018-2021 | 2022-2026 | Pior queda 2022-2026 |
|---|---|---|---|
| 0% (a regra de hoje) | 15,3% ao ano | 15,3% | −27,0% |
| 2,5% | 17,3% | 15,7% | −28,0% |
| 5% | 19,2% | 16,0% | −29,1% |
| 10% | 22,8% | 16,6% | −31,1% |
| 20% | 29,2% | 17,5% | −35,2% |

- Com a volta ao peso a cada 3 meses, toda fatia rendeu mais nos dois períodos e em quase todas as janelas de 3 anos. Sem a volta ao peso, a fatia cresce sozinha e em 2022-2026 rende menos que 0% de BTC, com quedas maiores (até −42%).
- O ganho vem quase todo de 2019, 2020, 2023 e 2024, anos em que o bitcoin subiu de 86% a 315%. Em 2025 e 2026 a fatia tirou rendimento (o bitcoin caiu 10% e 13%).
- É um único ativo num período em que ele multiplicou de valor; o teste não diz se isso se repete. Diferente das regras de trade, aqui não há o que "escolher" no passado, mas há a aposta de que o bitcoin continue subindo mais que as ações.

**Veredito:** uma fatia pequena, com volta ao peso a cada 3 meses, foi a única forma de bitcoin que melhorou a carteira nestes testes, ao custo de quedas um pouco maiores. Fica como opção de decisão do Daniel, não como regra do robô; não muda a conclusão de que o robô de trade de cripto não tem vantagem.

## Ações EUA: consenso com mais gestores, 16 -> 37 (12/11, scripts/estudo_mais_gestores.py)

Pergunta: com mais gestores na lista, a contagem do consenso depende menos de poucos nomes. Rende mais?
Base: os 16 gestores de hoje + 21 conhecidos por carteiras concentradas e de longo prazo (Fundsmith, Duquesne, TCI, Brave Warrior, Giverny, Fairfax, Weitz, Davis, Fairholme, Southeastern, Valley Forge, Trian, Polen, Dorsey, Altarock, Icahn, Ruane Cunniff, Yacktman, Wedgewood, Semper Augustus, Cantillon). 1.384 relatórios 13F. Mesma regra (top 10, corte 3%, troca no dia 16, custo 0,2%). Os 13F novos ficam à parte (user_data/estudo_mais_gestores); a lista do robô não mudou.

| Versão | 2018-2021 | 2022-2026 | Pior queda 2022-2026 |
|---|---|---|---|
| S&P 500 | 14,9% ao ano | 13,8% | −22,1% |
| **16 gestores, 2+ (a regra de hoje)** | **15,3%** | **15,3%** | −27,0% |
| 37 gestores, 3+ | 19,8% | 15,8% | −29,3% |
| 37 gestores, 4+ | 20,0% | 17,4% | −28,7% |
| 37 gestores, 3+, top 8 | 18,8% | 18,5% | −30,2% |
| 37 gestores, 3+, top 12 | 19,1% | 13,8% | −28,3% |
| 37 gestores, 3+, corte 5% | 19,3% | 16,1% | −31,6% |
| Só os 21 novos | 18,9% | 13,6% | −29,3% |

- 5 das 6 versões com 37 gestores ganham da regra de hoje nos dois períodos. A melhora é grande em 2018-2021 (+4 a +5 pontos) e pequena em 2022-2026 (+0,5 a +3 pontos; top 12 perde).
- Tirando um gestor novo de cada vez (37 gestores, 3+), 2022-2026 fica entre 14,7% e 17,1%: em 18 de 21 casos acima da regra de hoje. A melhora não depende de um nome só.
- Os 21 novos sozinhos não ganham do S&P em 2022-2026: o que ajuda é a contagem maior, não os nomes novos.
- Só 4 de 390 escolhas ficaram sem preço.
- **Viés:** os 21 foram escolhidos hoje, entre gestores que ficaram famosos. O mesmo vale para os 16 originais, mas aqui a escolha foi feita depois de ver 2018-2026. Parte da melhora pode vir disso.

**Veredito:** candidata a mudança (37 gestores, 3 ou mais), com melhora pequena e viés de escolha. Não muda o robô sem o OK do Daniel; se aprovar, vale acompanhar as duas listas lado a lado por alguns trimestres antes de trocar.

## Ações EUA: viés de sobrevivência e posições sem ticker (12/11, scripts/estudo_sobrevivencia.py)

Pergunta: o resultado do consenso está inflado porque os preços só têm empresas que sobreviveram?
O que se achou antes: parte das posições dos 13F vem **sem ticker**, porque a ferramenta não acha o CUSIP na lista de hoje. Eram ~30% do peso em 2017-18 e ~8% em 2026, e o estudo e o robô simplesmente ignoram essas posições. Não são só empresas mortas (Allergan, Altaba, United Technologies, Twitter): há empresas vivas grandes, como Bank of America (a do Buffett), Brookfield (BN; aparece como BKPA, que a corretora não negocia) e Facebook antes de virar META.
Correção: os mesmos 596 relatórios baixados de novo com CUSIP e nome; ticker pela OpenFIGI e, para as 17 que ela não acha, pelo nome; preço histórico da Alpaca, que guarda as que saíram da bolsa. Peso sem ticker caiu de 20,4% para 6,8% (o que sobra é ação estrangeira e posição pequena). Mesma regra de antes.

| Versão | 2018-2021 | 2022-2026 |
|---|---|---|
| S&P 500 | 14,9% ao ano | 13,8% |
| Original (como o robô lê hoje) | 15,3% | 15,3% |
| **Corrigido (com o que faltava)** | **18,3%** | **13,0%** |

- Viés de sobrevivência clássico: pequeno. Só duas empresas saíram da bolsa enquanto estavam na carteira corrigida (Allergan e CONSOL), as duas compradas por outra empresa, sem quebra.
- O que muda o resultado é o buraco no ticker: em 2022-2026 a carteira corrigida troca 1 a 3 nomes por trimestre (entram BAC e BN; saem V, AAPL, MSFT), e isso basta para tirar 2,3 pontos por ano.
- **Em 2022-2026, com os dados completos, o consenso fica abaixo do S&P** (13,0% contra 13,8%). A vantagem que parecia confirmada no 2º período não se sustenta.
- Lista de hoje: com os dados completos, entra BN e sai QSR. O resto é igual.
- O estudo de 37 gestores e as listas lado a lado usam a mesma leitura e têm o mesmo buraco.

**Veredito:** a leitura dos 13F tem um erro que o robô carrega para a lista real e precisa ser corrigido; isso é conserto de dado, não ajuste de resultado. A conclusão muda: com dado completo, o consenso não mostrou vantagem sobre o S&P no período de confirmação. Não muda o robô sem o OK do Daniel.

**Corrigido no robô em 13/11** (pedido do Daniel): `scripts/tickers_13f.py` resolve o ticker que falta (OpenFIGI pelo CUSIP e, se não achar, pelo nome) e os 13F passam a ser guardados com CUSIP e nome. Vale para o robô, para as listas lado a lado e para os estudos. A leitura antiga ficou em `user_data/estudo_sobrevivencia/13f_antigo` para comparação. Efeito na lista real: sai QSR, entra BN.

## Ações EUA: 37 gestores refeito com os dados corrigidos (13/11, scripts/estudo_mais_gestores.py)

Mesmo estudo de 12/11, agora com a leitura corrigida dos 13F (os 790 relatórios dos 21 gestores novos baixados de novo com CUSIP) e com os preços das empresas que saíram da bolsa.

| Versão | 2018-2021 | 2022-2026 | Pior queda 2022-2026 |
|---|---|---|---|
| S&P 500 | 14,9% ao ano | 13,8% | −22,1% |
| **16 gestores, 2+ (a regra de hoje)** | **18,3%** | **13,0%** | −28,9% |
| 16 gestores, 3+ | 18,5% | 14,0% | −32,0% |
| 37 gestores, 3+ | 18,0% | 15,5% | −29,5% |
| 37 gestores, 4+ | 18,0% | 16,7% | −30,0% |
| 37 gestores, 3+, top 8 | 19,1% | 18,5% | −30,2% |
| 37 gestores, 3+, top 12 | 16,2% | 13,6% | −29,7% |
| 37 gestores, 3+, corte 5% | 18,4% | 15,4% | −31,6% |
| Só os 21 novos | 18,8% | 13,6% | −32,1% |

- Com 37 gestores, 2+ e 3+ dão a mesma carteira: sempre há 10 ou mais ações com 3 gestores, e a contagem vem primeiro.
- Com dado completo, a vantagem de 2018-2021 sobre a regra de hoje sumiu (18,0% contra 18,3%). Em 2022-2026 ficou: 15,5% contra 13,0%.
- 37 gestores, 3+ é a única versão comparável que ganha do S&P nos dois períodos; a regra de hoje perde em 2022-2026.
- Tirando um gestor novo de cada vez, 2022-2026 fica entre 14,1% e 16,3%: nos 21 casos acima do S&P e da regra de hoje.
- Top 8 é o melhor número, mas é um ajuste escolhido olhando o resultado; não vale como regra.
- Custo: quedas maiores que as do S&P (−29,5% contra −22,1%).
- **Viés:** continua o mesmo de antes (os 21 foram escolhidos hoje, entre gestores famosos).

**Veredito:** com os dados certos, a candidata de 37 gestores ficou mais forte em relação à regra de hoje, porque a regra de hoje piorou e a de 37 se manteve. A vantagem sobre o S&P é pequena (cerca de 1,7 ponto por ano em 2022-2026) e vem com quedas maiores. Continua candidata: decisão do Daniel, com as listas lado a lado como prova com dados novos.

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

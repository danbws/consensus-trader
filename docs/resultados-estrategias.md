# Resultados: estrategias da comunidade, NostalgiaForInfinity e FreqAI

Data dos testes: 20/10/2026. Tudo foi feito em backtest (simulacao com precos do passado) e em copias de teste. O robo que roda ao vivo (porta 8080, `config.json`, `RoboTendencia.py`, `RoboTendenciaBTC.py`) nao foi tocado.

## Como ler os numeros

- **Backtest** = "e se o robo tivesse operado de 01/10/2025 ate hoje". Ele e sempre mais otimista que o mundo real: nao sente atraso, ordem que nao executa, preco que pula, taxa maior, nem o fato de a estrategia ter sido escolhida olhando o passado.
- **Resultado %** = quanto os R$ 30 iniciais viraram. **Saldo final** = quanto sobrou dos R$ 30.
- **Drawdown** = a maior queda do saldo entre um pico e o fundo seguinte (quanto maior, mais doloroso).
- **Profit factor (PF)** = quanto ganhou para cada R$ 1 que perdeu. Abaixo de 1 = perde dinheiro. Acima de 1,3 comeca a ser interessante.
- **Win rate** = porcentagem de operacoes que fecharam no lucro. Atencao: win rate alto engana (varias vitorias pequenas e uma perda enorme).

## Condicoes dos testes

| Item | Valor |
|---|---|
| Corretora / moeda | Binance spot, BRL |
| Saldo inicial | R$ 30 (stake "unlimited", maximo 2 operacoes abertas ao mesmo tempo) |
| Pares | os mesmos 12 do robo: BTC, ETH, SOL, XRP, BNB, ADA, LINK, AVAX, NEAR, SUI, LTC, PEPE (em BRL) |
| Periodo 1 (principal) | 01/10/2025 ate 20/10/2026. O mercado caiu em media 41,7% nesse periodo (BTC -31,9%). |
| Periodo 2 (checagem) | 01/04/2026 ate 20/10/2026. Nesse periodo o mercado SUBIU em media 36,8% (BTC +17,1%). |
| Taxa | 0,1% por ordem (a pior taxa da Binance) |
| Referencia | RoboTendenciaBTC (a que ja esta no robo ao vivo) |

Importante: os dois periodos sao de mercados opostos (queda e alta). Uma estrategia boa de verdade precisa aguentar os dois.

## Tabela 1 - Periodo principal (01/10/2025 a 20/10/2026, mercado -41,7%)

| Estrategia | Tempo grafico | Operacoes | Resultado % | Saldo final (R$) | Drawdown max % | Profit factor | Win rate % |
|---|---|---|---|---|---|---|---|
| **MultiMa** | 4h | 333 | **+24,47** | 37,34 | 22,40 | 1,15 | 31,5 |
| Strategy002 | 5m | 158 | -5,84 | 28,25 | 16,07 | 0,90 | 91,1 |
| RoboTendenciaBTC (referencia, ao vivo) | 15m | 261 | -7,69 | 27,69 | 19,63 | 0,93 | 60,2 |
| UniversalMACD | 5m | 126 | -22,03 | 23,39 | 40,32 | 0,56 | 78,6 |
| Strategy003 | 5m | 208 | -33,12 | 20,07 | 43,54 | 0,69 | 87,0 |
| SwingHighToSky | 15m | 86 | -33,48 | 19,96 | 42,52 | 0,32 | 69,8 |
| Strategy004 | 5m | 193 | -37,13 | 18,86 | 45,62 | 0,61 | 87,6 |
| Strategy005 | 5m | 111 | -43,12 | 17,07 | 47,11 | 0,61 | 76,6 |
| Strategy001 | 5m | 80 | -43,69 | 16,89 | 46,65 | 0,38 | 77,5 |
| Bandtastic | 15m | 312 | -44,29 | 16,71 | 47,32 | 0,59 | 57,4 |
| Supertrend | 1h | 343 | -42,83 | 17,15 | 47,28 | 0,72 | 29,4 |
| Diamond | 5m | 71 | -46,68 | 16,00 | 52,77 | 0,37 | 83,1 |
| CustomStoplossWithPSAR | 1h | 6 | -48,33 | 15,50 | 48,33 | 0,00 | 0,0 |
| NostalgiaForInfinityX8 (USDT, carteira 100 USDT, 6 operacoes) | 5m | 97 | -22,19 | 77,81 USDT | 36,61 | 0,54 | 86,6 |
| NostalgiaForInfinityX8 (USDT, carteira 6 USDT = R$ 30, 1 operacao) | 5m | 13 | -35,64 | 3,86 USDT | 38,97 | 0,25 | 69,2 |
| RoboFreqAI (FreqAI + LightGBM, so 4 pares) | 15m | 422 | -43,01 | 17,10 | 44,27 | 0,62 | 46,9 |

Para comparar: comprar e segurar os 12 pares nesse periodo daria cerca de -41,7%.

## Tabela 2 - Segundo periodo, isolado (01/04/2026 a 20/10/2026, mercado +36,8%)

Rodado nas 3 melhores do periodo principal (MultiMa, Strategy002, UniversalMACD), mais a Strategy003 e a referencia.

| Estrategia | Operacoes | Resultado % | Saldo final (R$) | Drawdown max % | Profit factor | Win rate % |
|---|---|---|---|---|---|---|
| MultiMa | 210 | +19,49 | 35,85 | 19,35 | 1,20 | 33,8 |
| Strategy002 | 79 | +6,89 | 32,07 | 8,82 | 1,28 | 93,7 |
| UniversalMACD | 82 | +41,09 | 42,33 | 0,02 (*) | 274 (*) | 82,9 |
| Strategy003 | 135 | +22,88 | 36,87 | 10,04 | 1,53 | 94,1 |
| RoboTendenciaBTC (referencia) | 177 | -8,84 | 27,35 | 13,77 | 0,88 | 60,5 |
| RoboFreqAI | 444 | -26,27 | 22,12 | 26,97 | 0,71 | 46,8 |

(*) O drawdown e o profit factor da UniversalMACD sao enganosos: houve quase nenhuma perda fechada nesse trecho, mas ela perdeu 22% no periodo todo. Ela so ganha quando o mercado inteiro sobe. Nao e um sinal de qualidade, e sorte de periodo.

Referencia extra: RoboTendenciaBTC de 01/01/2026 a 20/10/2026 deu -9,59% (213 operacoes, PF 0,89).

## O que foi feito, passo a passo

### Estrategias da comunidade
- Repositorio `freqtrade/freqtrade-strategies` clonado (raso) em `externos\freqtrade-strategies`. O codigo de cada estrategia foi lido antes de copiar; nada do repositorio foi executado fora do Freqtrade.
- Escolhidas 12 estrategias spot (so compra, sem short, sem futuros) e copiadas para `user_data\strategies\comunidade\`: Strategy001 a Strategy005, Bandtastic, SwingHighToSky, Supertrend, Diamond, CustomStoplossWithPSAR, UniversalMACD, MultiMa. Sem nenhuma adaptacao no codigo: rodaram do jeito que vieram.
- Baixados dados novos de 5m, 4h e 1d (de 01/09/2025) para os 12 pares em BRL. Os tempos de 15m e 1h ja existiam.
- Descartadas (nao testadas): Heracles e GodStra (precisam da biblioteca `ta`, que nao esta instalada e e pouco usada), TrendRiderStrategy (feita para futuros, usa BTC/USDT:USDT), e as pastas `futures` e `lookahead_bias` do repositorio.
- Cada estrategia rodou sozinha, com o mesmo saldo, pares e periodo. Configs de teste em `user_data\configs_teste\` (a copia do config real, com a API desligada e outra porta).

### Verificacao de "trapaca" (lookahead)
Rodei a ferramenta `lookahead-analysis` do Freqtrade (que detecta estrategia que "enxerga o futuro") nas tres melhores: MultiMa, UniversalMACD e Strategy002. As tres passaram sem vies. Entao o bom resultado delas nao vem de trapaca tecnica no codigo.

### NostalgiaForInfinity (NFI)
- Clonada em `externos\NostalgiaForInfinity` e copiada so a estrategia `NostalgiaForInfinityX8.py` para `user_data\strategies\nfi\` (o arquivo foi verificado: nao faz chamadas de rede nem executa comandos, so le/grava um arquivo de cache).
- **Nao deu para rodar em BRL**: a NFI usa o par BTC/USDT como referencia de mercado e so reconhece moedas estaveis em dolar/euro como "stake". Por isso foi rodada com os 12 pares equivalentes em **USDT** (dados de 5m, 15m, 1h, 4h e 1d baixados para eles), em modo spot.
- Duas rodadas, as duas claramente em USDT e nao em BRL:
  1. Carteira de 6 USDT (cerca de R$ 30), 1 operacao por vez: -35,64%, so 13 operacoes. Com 6 USDT a NFI nao consegue fazer o que a torna especial (varias entradas e recompras com a carteira cheia, e a Binance exige minimo de ~5 USDT por ordem), entao este teste e pouco representativo.
  2. Carteira de 100 USDT, ate 6 operacoes: -22,19% (mercado -41,7%), 97 operacoes, 86,6% de acerto mas profit factor 0,54 e drawdown de 36,6%. Perde menos que o mercado, mas perde.
- A NFI e um projeto enorme e pensado para carteiras maiores, muitos pares e configuracao propria. Nao encaixa nos R$ 30.

### FreqAI (inteligencia artificial)
- Instalados no venv: `lightgbm`, `scikit-learn`, `datasieve` e `xgboost` (este ultimo porque o Freqtrade 2026.9 importa o xgboost junto com os modelos mesmo usando so o LightGBM). Sem pytorch / aprendizado por reforco. Nenhum pacote existente foi atualizado.
- Estrategia: `user_data\strategies\RoboFreqAI.py`, adaptada da `FreqaiExampleStrategy` que vem com o Freqtrade: sem short, so compra; o modelo prediz a variacao media do preco nas proximas 6 horas (24 velas de 15m); compra se a previsao passar de +0,6% e for considerada confiavel; vende se a previsao ficar negativa, ou por alvo de 5% / limite de 8 horas / stop de 4%.
- Config: `user_data\configs_teste\config_freqai.json`. Modelo LightGBMRegressor, 15m (com 1h como apoio), 4 pares (BTC, ETH, SOL, XRP em BRL), treino com 30 dias, re-treino a cada 7 dias. Cada backtest levou de 4 a 6 minutos (bem abaixo do limite de 25).
- Resultados: 01/01/2026 a 19/10/2026 = **-19,94%** (633 operacoes, PF 0,86); 01/10/2025 a 19/10/2026 = **-43,01%** (422 operacoes, PF 0,62); 01/04/2026 a 19/10/2026 = **-26,27%** (444 operacoes, PF 0,71). Perdeu ate no periodo em que o mercado subiu. O FreqAI exige data final no backtest, por isso terminam em 19/10.
- Nota: foi o primeiro modelo, sem ajuste fino. Mexer em parametros ate dar lucro neste mesmo periodo seria overfitting. Mesmo assim, o resultado em duas janelas diferentes sugere que o modelo nao encontrou um padrao previsivel nos precos.

## Quais falharam e por que

| Estrategia | Motivo |
|---|---|
| Strategy001, 004, 005, Bandtastic, Supertrend, Diamond, SwingHighToSky | Perderam 33% a 47%, ou seja, praticamente o mesmo que o mercado: nenhuma protecao. Stops muito largos (a maioria tem stop entre -10% e -34%) deixam a perda correr. |
| CustomStoplossWithPSAR | So 6 operacoes no ano, todas perdidas (PF 0). Nao serve para esses pares em BRL. |
| Strategy003 | Win rate 87% mas PF 0,69: muitas vitorias pequenas e poucas perdas enormes. Ganhou 22,9% so quando o mercado subiu 36,8%. |
| UniversalMACD | -22% no ano, +41% so no trecho de alta. Depende da direcao do mercado. |
| NFI | Nao suporta BRL; em USDT perdeu 22% a 36%. |
| RoboFreqAI | Perdeu nos tres periodos testados, inclusive na alta. |

## Conclusao honesta

1. **Nenhuma estrategia testada e comprovadamente boa.** Das 12 da comunidade, 11 perderam dinheiro no periodo principal, a maioria tanto quanto simplesmente segurar as moedas.
2. **A unica que ficou positiva nos dois periodos foi a MultiMa** (+24,5% com o mercado em -41,7%, e +19,5% com o mercado em +36,8%; profit factor 1,15 e 1,20; passou no teste de lookahead). E uma estrategia de tendencia no grafico de 4 horas, entra em poucos casos e sai quando as medias se invertem.
3. **Mas ha um alerta forte de concentracao:** a NEAR/BRL sozinha rendeu +12,9 R$ no periodo 1 (o total da estrategia foi +7,3 R$) e +9,3 R$ no periodo 2 (total +5,9 R$). Sem a NEAR a MultiMa teria perdido dinheiro nos dois periodos. Ou seja, o resultado depende de uma unica moeda ter feito uma tendencia longa: pode nao se repetir. Win rate de 31% significa que ela erra 2 de cada 3 vezes e depende de poucos acertos grandes.
   Outro alerta: o stop da MultiMa e de -34,5% (uma unica operacao ruim pode custar mais de um terco da posicao). Se for ao dry-run, vale testar tambem uma copia com stop mais curto, sabendo que isso muda o resultado.
4. **Strategy002** foi a segunda menos ruim (-5,8% na queda, +6,9% na alta), mas com PF abaixo de 1,3 e 91% a 94% de acerto: o perfil classico de "pega moedas por centavos e arrisca uma perda grande" (stop de -10%). Pior que a MultiMa em robustez.
5. **Overfitting e otimismo:** as estrategias da comunidade vieram otimizadas pelos autores com dados de outros anos (nao otimizei nada nelas, o que e bom). Ainda assim, escolher a "melhor" entre 13 testadas ja e uma forma de vies: com tantas tentativas, uma sempre se sai bem por sorte. Dois periodos nao sao prova. O backtest nao inclui derrapagem, atraso de ordem, mercado ilíquido (PEPE, SUI) nem o comportamento diferente ao vivo.
6. **IA (FreqAI) e NFI nao valem o esforco para R$ 30**: perderam em todos os periodos testados.

### O que vale levar ao dry-run ao vivo
**MultiMa**, apenas como **dry-run paralelo (dinheiro de mentira)** para observar por pelo menos 4 a 8 semanas ao lado da RoboTendenciaBTC, e so tirar conclusao com varias dezenas de operacoes reais simuladas. Nao e recomendacao de usar dinheiro real: os numeros acima nao justificam isso, e um robo que perde menos que o mercado ainda pode perder dinheiro. Criterios para considerar mais adiante: PF acima de 1,2 e saldo positivo em dry-run, sem depender de uma unica moeda.

## Comandos exatos (rodar na pasta do projeto)

Backtest da candidata (nao interfere no robo ao vivo):

```powershell
.\.venv\Scripts\freqtrade.exe backtesting -c user_data\configs_teste\config_base.json --recursive-strategy-search --strategy MultiMa --timerange 20251001-
```

Dry-run paralelo (dinheiro de mentira) em OUTRO banco e OUTRA porta, para nao colidir com o robo atual. Antes, crie `user_data\configs_teste\config_dry_multima.json` copiando `config_base.json` e mudando `"bot_name"` e `"listen_port"` (por exemplo 8092). A API fica desligada em `config_base.json`; ligue-a nessa copia se quiser ver pelo painel. Depois:

```powershell
.\.venv\Scripts\freqtrade.exe trade -c user_data\configs_teste\config_dry_multima.json --strategy MultiMa --recursive-strategy-search --db-url sqlite:///user_data/tradesv3.dryrun.multima.sqlite
```

(Arquivo `user_data\strategies\comunidade\MultiMa.py`, classe `MultiMa`.) Cuidado: esse comando inicia um segundo robo.

Para repetir qualquer outro teste: `.\.venv\Scripts\freqtrade.exe backtesting -c user_data\configs_teste\config_base.json --recursive-strategy-search --strategy <Classe> --timerange 20251001-`. FreqAI: `... backtesting -c user_data\configs_teste\config_freqai.json --strategy RoboFreqAI --freqaimodel LightGBMRegressor --timerange 20260101-20261019`. NFI: `... backtesting -c user_data\configs_teste\config_usdt100.json --recursive-strategy-search --strategy NostalgiaForInfinityX8 --timerange 20251001-`.

## Arquivos criados

- `externos\freqtrade-strategies\` e `externos\NostalgiaForInfinity\` (clones; nao sao carregados pelo robo)
- `user_data\strategies\comunidade\` (12 estrategias), `user_data\strategies\nfi\NostalgiaForInfinityX8.py`, `user_data\strategies\RoboFreqAI.py`
- `user_data\configs_teste\` (configs `config_base.json`, `config_usdt.json`, `config_usdt100.json`, `config_freqai.json`, logs dos testes e scripts `roda.ps1` / `resumo.py`)
- Dados novos em `user_data\data\binance\` (5m, 4h, 1d em BRL; 5m, 15m, 1h, 4h, 1d em USDT)

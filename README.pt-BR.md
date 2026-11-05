# consensus-trader

[Read in English](README.md)

Um laboratório pessoal de investimentos que roda num computador com Windows. São três partes:

- uma **carteira de ações dos EUA** com as empresas que mais aparecem entre as maiores posições de investidores conhecidos, tiradas dos relatórios 13F que eles entregam à SEC;
- um **robô de cripto** feito com o [Freqtrade](https://github.com/freqtrade/freqtrade), negociando pares em real na Binance;
- um **painel web** e um **bot do Telegram** para acompanhar as duas coisas, no computador ou no celular.

Hoje tudo roda com dinheiro fictício. Eu montei isso para responder uma pergunta: um robô pequeno e cuidadoso consegue render mais do que simplesmente comprar e segurar? Anotei cada ideia testada, inclusive as que deram errado. Esse caderno é a parte mais útil do repositório.

## O que eu descobri

**Ações: o consenso dos 13F tem uma vantagem pequena.** Pegue 16 gestores (Buffett, Klarman, Li Lu, Ackman, Burry, Tepper, Pabrai, Marks e outros), olhe o último 13F de cada um e compre as 10 empresas que mais gestores têm com 3% ou mais da carteira. Troque quando os relatórios novos mudarem a lista, mais ou menos uma vez por trimestre. Cada relatório só vale a partir da data em que foi entregue, então o teste nunca enxerga o futuro.

| Preços diários, custo de 0,2% por operação | 2018-2021 (regra escolhida aqui) | 2022-2026 (fora da amostra) |
|---|---|---|
| S&P 500, comprar e segurar | 14,9% ao ano | 13,8% ao ano |
| Consenso, top 10 | **15,3% ao ano** | **15,3% ao ano** |

6 das 9 variações próximas (outros cortes, top 8, entrar 5 ou 20 dias depois) também ganham do índice nos dois períodos. A vantagem existe, mas é pequena, e as quedas são parecidas com as do índice. A carteira roda na conta de papel da Alpaca desde 30/10/2026.

**Cripto: não achei vantagem.** Mais de 40 regras, o FreqAI do Freqtrade e estratégias conhecidas da comunidade passaram pelo mesmo protocolo: escolher num período, confirmar em outro, conferir os parâmetros vizinhos e cobrar taxa e spread de verdade. Nenhuma passou nas quatro. O ganho inicial nos pares em real provavelmente vinha de livros de ofertas com pouca gente, e sumiu quando o spread entrou na conta. O teste ao vivo bateu com o backtest: perto de zero.

**O dinheiro dos ETFs de bitcoin não prevê o dia seguinte.** A correlação entre o fluxo de hoje nos ETFs americanos e o retorno de amanhã foi de +0,04. Saídas grandes funcionam como freio na queda, mas custam na alta, e só uma combinação exata de números ganhou de comprar e segurar nos dois períodos.

**O relatório COT não ganha de comprar e segurar em ações nem em ouro.** A regra clássica de Larry Williams perdeu nos cinco ativos testados, e nenhuma das 36 regras no S&P 500 e no ouro venceu nos dois períodos.

O caderno completo está em [docs/hipoteses-testadas.md](docs/hipoteses-testadas.md).

## O que tem aqui

| Caminho | O que é |
|---|---|
| `scripts/estudo_consenso.py`, `estudo_consenso_robustez.py` | Download dos 13F, o backtest do consenso e os testes de robustez |
| `scripts/consenso_automatico.py` | Toca a carteira de consenso: confere de hora em hora e só negocia quando a lista muda |
| `scripts/corretoras.py` | A mesma interface para Alpaca e Interactive Brokers (IB Gateway pelo `ib_async`), só conta de papel |
| `scripts/vigia_investidores.py` | Avisa quando sai um 13F novo e resume o que cada investidor comprou e vendeu |
| `scripts/relatorio_imposto.py` | Relatório anual para o contador: cada venda em reais pelo dólar PTAX, custo pelo PEPS, dividendos |
| `scripts/historico.py` | Valor diário por tipo de investimento, para o painel mostrar o ganho de qualquer período |
| `scripts/estudo_etf_btc*.py` | O estudo dos fluxos dos ETFs de bitcoin |
| `scripts/estudo_saida_queda.py` | Tirar na queda e colocar depois: 20 regras de saída sobre a carteira de consenso |
| `scripts/estudo_cot.py` | O estudo do relatório COT da CFTC (S&P 500, ouro, prata, títulos, euro) |
| `user_data/strategies/` | As estratégias do Freqtrade que foram testadas (`RoboSaidas.py` é a que está ligada) |
| `painel/` | Painel em FastAPI (gráficos, ganhos, configurações) e o bot do Telegram |
| `third_party/edgar13f/` | Leitor de 13F da SEC, de Jake Schincariol, licença MIT |
| `docs/aulas/` | Dez aulas curtas para quem está começando |

## Segurança

- **Só papel.** A Alpaca é acessada só pelo endereço da conta de papel. A Interactive Brokers é recusada se a porta não for de papel (4002 ou 7497) ou se alguma conta do login não começar com `DU`. Dinheiro real na cripto exige chave sem permissão de saque, 21 dias de teste e uma frase digitada.
- **O painel escuta no seu computador.** Outros aparelhos só entram pelo Tailscale, com senha, e as telas de configuração nunca abrem pelo celular.
- **O bot do Telegram atende uma conversa só.** Tudo que mexe em dinheiro pede confirmação, que vale 5 minutos.
- **Chave nenhuma vai para o git.** O `.gitignore` funciona como lista do que pode entrar: só código e documentação.
- **Travas e avisos.** O robô de cripto pausa sozinho se o saldo cair um terço. A carteira de ações nunca vende porque caiu; ela avisa no Telegram em -20%, -30% e -40% a partir do topo, porque vender no fundo transforma a queda em perda.

## Como rodar

Precisa de Windows 10 ou 11 e Python 3.11 ou mais novo (desenvolvido no 3.14).

```powershell
git clone https://github.com/danbws/consensus-trader.git
cd consensus-trader
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy user_data\config.example.json user_data\config.json
copy acoes-eua\trader\config.example.json acoes-eua\trader\config.json
```

Edite os dois arquivos. No `user_data\config.json`, troque usuário, senha e segredos do bloco `api_server`. No `acoes-eua\trader\config.json`, coloque seu nome e e-mail em `sec_user_agent`; a SEC pede isso em todo download.

```powershell
.\abrir-robo.ps1
```

Isso liga o robô e o painel escondidos e abre <http://127.0.0.1:8090>. Em **Configurações** você conecta as chaves de papel da Alpaca, o Telegram e, depois, o IB Gateway. O `parar-robo.ps1` desliga tudo.

Os testes não precisam de corretora: `scripts\teste_corretoras.py`, `teste_queda.py` e `teste_acesso.py`.

## Não é recomendação de investimento

É um projeto de estudo. Ele mostra dados e o resultado de regras, e pode estar errado. Resultado passado não garante resultado futuro. Pesquise por conta própria antes de colocar dinheiro de verdade em qualquer lugar.

## Licença

[GPL-3.0](LICENSE), a mesma do Freqtrade. A pasta `third_party/edgar13f` mantém a licença MIT dela.

Feito por **Daniel Bichof** ([@danbws](https://github.com/danbws)), Brasil.

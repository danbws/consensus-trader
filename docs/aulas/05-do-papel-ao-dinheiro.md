# Aula 5: do papel para o dinheiro de verdade

## Checklist antes de colocar 1 real
Todos os itens precisam estar ✔:
- [ ] Backtest **positivo** em pelo menos 2 períodos diferentes, com profit factor acima de 1,2
- [ ] Teste no pedaço do histórico que não foi usado para ajustar a regra (Aula 4, lição 4)
- [ ] Pelo menos **3 semanas de dry-run** ao vivo com resultado parecido com o do backtest
- [ ] Drawdown que você aguenta ver sem desligar
- [ ] Um valor que você aceita perder **inteiro**

Hoje nenhuma das duas versões passa no primeiro item.

## Ligando com dinheiro real (quando chegar a hora)
Essa parte é sua. Eu não crio conta, não digito chave e não movo dinheiro.
1. Na Binance, crie uma **chave de API** só com a permissão **"Ativar Spot e Margin Trading"**.
   **Nunca marque "Permitir saques".** Se alguém roubar a chave, não consegue tirar o dinheiro.
2. Restrinja a chave ao IP da máquina onde o robô roda.
3. Deposite por Pix um valor pequeno (R$ 30 a R$ 60, por causa do mínimo de R$ 10 por ordem).
4. No `user_data/config.json`: `"dry_run": false`, a chave e o segredo em `exchange`, e um
   `"dry_run_wallet"` que você ignora.
5. Ligue um alerta no **Telegram** (o Freqtrade manda cada compra e venda para o celular).

## Rodar 24 horas
- **No seu PC:** ele precisa ficar ligado, sem hibernar, com internet. Serve para o teste.
- **Em servidor (VPS):** Linux com 1 GB de RAM (~US$ 5/mês) roda o Freqtrade em Docker. Ele
  fica no ar mesmo com o seu PC desligado, e o painel abre pelo celular. É o caminho para
  depois do dry-run.

## Imposto e regra
Ganho com cripto entra no Imposto de Renda, e a regra muda conforme a corretora seja nacional
ou estrangeira e conforme o volume vendido por mês. Com R$ 30 o valor é irrisório, mas a
movimentação é declarável. Confirme com o contador quando passar para dinheiro real.

## Próximos passos possíveis (onde nos espelhar)
| Caminho | O que é | Esforço |
|---|---|---|
| **freqtrade-strategies** (github.com/freqtrade/freqtrade-strategies) | Estratégias de exemplo da comunidade: rodar no nosso backtest e comparar | Baixo |
| **NostalgiaForInfinity** (github.com/iterativv/NostalgiaForInfinity) | A estratégia mais usada da comunidade, muito mais complexa | Baixo para testar |
| **FreqAI** (já vem no Freqtrade) | Um modelo de machine learning treinado no histórico, que retreina sozinho de tempos em tempos. É o "treinar o bot" | Médio |
| **Notícias e sentimento** | Ler manchetes ou redes e transformar em nota de humor por moeda | Alto |
| **Hummingbot / Jesse** | Outros robôs abertos (market making, outros estilos) | Para comparar |

A ordem que eu sugiro: rodar as estratégias da comunidade no backtest, depois o FreqAI, e só
então notícias. Cada passo passa pelo mesmo checklist.

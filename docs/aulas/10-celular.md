# Aula 10: o robô no iPhone, pelo Tailscale

## Como funciona
O Tailscale cria uma rede particular só entre os seus aparelhos (computador e iPhone). O celular
abre o painel como se estivesse em casa, de qualquer lugar (4G, outro Wi-Fi), e ninguém mais na
internet enxerga o painel. O computador precisa estar ligado, com o robô rodando.

| Quem abre | O que acontece |
|---|---|
| Este computador | Tudo, sem senha, como sempre |
| iPhone pelo Tailscale | Pede a senha do painel; gráficos, painel simples, relatórios e os botões Pausar e Vender |
| iPhone pelo Tailscale, tela Conta ou troca de senha | **Nunca** abre (chave da Binance) |
| Qualquer outro aparelho (até no Wi-Fi de casa) | Recusado |

Proteções: senha guardada só como hash; 5 senhas erradas bloqueiam por 15 minutos; a sessão do
celular dura 30 dias; trocar a senha desconecta os celulares. Teste: `scripts\teste_acesso.py`.

## Passo a passo (uma vez só)
1. **No computador**, abra <http://127.0.0.1:8090/senha> e crie a senha do painel (mínimo 8 caracteres).
2. **No computador**, instale o Tailscale (<https://tailscale.com/download>) e entre com a sua conta
   (Google, Microsoft ou Apple).
3. **No iPhone**, instale o app **Tailscale** da App Store e entre com **a mesma conta**. Ligue a chave dele.
4. No app do Tailscale (no PC ou no iPhone), veja o **nome** ou o endereço **100.x.x.x** do computador.
5. **No Safari do iPhone**, abra `http://NOME-DO-PC:8090` (ou `http://100.x.x.x:8090`) e entre com a senha.
6. Em **Compartilhar > Adicionar à Tela de Início**: vira o ícone "Robô", que abre direto nos gráficos.

Se o Windows perguntar se o "Python" pode usar a rede, permita. Se o iPhone não abrir o painel,
é quase sempre o Firewall do Windows bloqueando a porta 8090.

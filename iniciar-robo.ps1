# Liga o robo em modo de teste (dry-run: preco real da Binance, saldo ficticio).
# Se o robo cair (internet, erro), ele espera 30 segundos e liga de novo.
# Painel: http://127.0.0.1:8080  (usuario e senha em user_data\config.json, bloco api_server)
# Para parar: Ctrl+C nesta janela.

$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot
# Chama pelo python.exe: desde 13/11/2026 o Smart App Control do Windows bloqueia o freqtrade.exe
# (lancador sem assinatura); o python.exe da venv e liberado.
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
New-Item -ItemType Directory -Force (Join-Path $PSScriptRoot "user_data\logs") | Out-Null

# modo.json: teste (padrao) ou dinheiro real. Quem troca e a tela Conta do painel.
$modo = Join-Path $PSScriptRoot "user_data\modo.json"
if (-not (Test-Path $modo)) { [IO.File]::WriteAllText($modo, '{"dry_run": true}') }
# telegram.json: avisos e comandos pelo Telegram. Quem liga e a tela Conta do painel.
$telegram = Join-Path $PSScriptRoot "user_data\telegram.json"
if (-not (Test-Path $telegram)) { [IO.File]::WriteAllText($telegram, '{"telegram": {"enabled": false, "token": "", "chat_id": ""}}') }

while ($true) {
    Write-Host "$(Get-Date -Format 'dd/MM HH:mm:ss')  ligando o robo..."
    & $python -m freqtrade trade --config user_data/config.json --config user_data/modo.json --config user_data/telegram.json --logfile user_data/logs/robo.log
    Write-Host "$(Get-Date -Format 'dd/MM HH:mm:ss')  robo parou; religando em 30 s (Ctrl+C para sair)"
    Start-Sleep -Seconds 30
}

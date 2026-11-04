# Atalho "Robô de Trade": liga o que estiver desligado, sem janela, e abre o terminal de graficos.
#   - robo (Freqtrade, porta 8080) e painel (porta 8090) rodam OCULTOS: nao aparecem na barra de tarefas
#   - para desligar: atalho "Desligar Robô de Trade" (parar-robo.ps1)
#   -SemNavegador: so liga, sem abrir o navegador (usado pelo relatorio diario)
param([switch]$SemNavegador)

$raiz = $PSScriptRoot
function Responde($url) {
    try { Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 2 | Out-Null; return $true } catch { return $false }
}
function Rodando($padrao) {
    [bool](Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match $padrao })
}

# o robo pode estar subindo (ainda sem responder): so liga se nao houver o processo
if (-not (Responde "http://127.0.0.1:8080/api/v1/ping") -and -not (Rodando 'iniciar-robo\.ps1|trade --config')) {
    Start-Process powershell -WindowStyle Hidden -WorkingDirectory $raiz `
        -ArgumentList "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$raiz\iniciar-robo.ps1`""
}
if (-not (Responde "http://127.0.0.1:8090/api/resumo") -and -not (Rodando 'painel\\servidor\.py')) {
    Start-Process "$raiz\.venv\Scripts\pythonw.exe" -WorkingDirectory $raiz -ArgumentList "`"$raiz\painel\servidor.py`""
}

if (-not $SemNavegador) {
    for ($i = 0; $i -lt 40 -and -not (Responde "http://127.0.0.1:8090/api/resumo"); $i++) { Start-Sleep -Milliseconds 500 }
    Start-Process "http://127.0.0.1:8090/terminal"
}

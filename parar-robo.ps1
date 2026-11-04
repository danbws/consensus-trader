# Atalho "Desligar Robô de Trade": desliga o robo e o painel que rodam ocultos.
# As posicoes abertas continuam registradas e o robo retoma de onde parou quando for ligado de novo.

Add-Type -AssemblyName PresentationFramework
$resp = [System.Windows.MessageBox]::Show(
    "Desligar o robô de trade e o painel?`n`nEnquanto estiver desligado ele não compra nem vende, nem usa o stop. Para ligar de novo, use o ícone Robô de Trade.",
    "Robô de Trade", "YesNo", "Question")
if ($resp -ne "Yes") { exit }

# primeiro o laco que religa o robo, depois o robo e o painel
foreach ($padrao in 'iniciar-robo\.ps1', 'trade --config', 'painel\\servidor\.py') {
    Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match $padrao } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
}
[System.Windows.MessageBox]::Show("Robô e painel desligados.", "Robô de Trade") | Out-Null

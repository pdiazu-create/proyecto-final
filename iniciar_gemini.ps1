# La clave se introduce localmente y no se escribe en archivos.
Set-Location -LiteralPath $PSScriptRoot
$sondaGrace = New-Object System.Net.Sockets.TcpClient
$servidorOcupado = $false
try { $sondaGrace.Connect('127.0.0.1', 8000); $servidorOcupado = $true }
catch { }
finally { $sondaGrace.Dispose() }
if ($servidorOcupado) {
    Write-Host 'Ya hay un servidor en el puerto 8000. Cierra la instancia anterior con Ctrl+C antes de iniciar Gemini.'
    exit 1
}
$variablesGrace = @('GRACE_IA', 'GRACE_IA_PROVEEDOR', 'GRACE_IA_MODEL', 'GRACE_IA_KEY', 'GRACE_IA_TIMEOUT')
$entornoAnterior = @{}
foreach ($nombreGrace in $variablesGrace) {
    $entornoAnterior[$nombreGrace] = [Environment]::GetEnvironmentVariable($nombreGrace, 'Process')
}
$secretoGrace = Read-Host 'Introduce tu clave de Gemini (entrada oculta; no se guarda)' -AsSecureString
$punteroGrace = [IntPtr]::Zero
try {
    $punteroGrace = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secretoGrace)
    $env:GRACE_IA_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($punteroGrace)
    $env:GRACE_IA = 'api'
    $env:GRACE_IA_PROVEEDOR = 'gemini'
    $env:GRACE_IA_MODEL = 'gemini-3.5-flash-lite'
    $env:GRACE_IA_TIMEOUT = '30'
    Write-Host 'Modelo rapido: gemini-3.5-flash-lite. El diagnostico comprobara si tu cuenta permite utilizarlo.'
    python diagnostico_ia.py
    Write-Host 'Grace con Gemini: http://127.0.0.1:8000'
    python app.py
}
finally {
    if ($punteroGrace -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($punteroGrace)
    }
    foreach ($nombreGrace in $variablesGrace) {
        [Environment]::SetEnvironmentVariable($nombreGrace, $entornoAnterior[$nombreGrace], 'Process')
    }
    $secretoGrace.Dispose()
}

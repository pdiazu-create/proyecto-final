# Inicio privado: la clave solo se mantiene en memoria durante el servidor.
Set-Location -LiteralPath $PSScriptRoot
if (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue) {
    Write-Host 'El puerto 8000 ya tiene un servidor. Cierra Grace con Ctrl+C en su terminal antes de iniciar otra instancia.'
    exit 1
}
$claveSegura = Read-Host 'Introduce tu clave API (entrada oculta; no se guarda)' -AsSecureString
$punteroClave = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($claveSegura)
try {
    $env:GRACE_IA_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($punteroClave)
    $env:GRACE_IA = 'api'
    $env:GRACE_IA_PROVEEDOR = 'openai'
    if (-not $env:GRACE_IA_MODEL) { $env:GRACE_IA_MODEL = 'gpt-4o-mini' }
    Write-Host 'Grace inicia con API opcional. Abre http://127.0.0.1:8000'
    python app.py
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($punteroClave)
    Remove-Item Env:GRACE_IA_KEY -ErrorAction SilentlyContinue
    $claveSegura.Dispose()
}

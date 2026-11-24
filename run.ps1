# Arranca el MVP en Windows: .\run.ps1   (opcional: .\run.ps1 -Port 9000)
param([int]$Port = 8080)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$py = if (Get-Command python -ErrorAction SilentlyContinue) { "python" } elseif (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { throw "Instala Python 3.11+ desde python.org" }
if (-not (Test-Path .venv)) { & $py -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install -q -r requirements.txt
$env:APP_PORT = "$Port"
Start-Job { Start-Sleep 2; Start-Process "http://localhost:$using:Port" } | Out-Null
Write-Host "CrediScore en http://localhost:$Port  (Ctrl+C para salir)"
& .\.venv\Scripts\python.exe -m src.main

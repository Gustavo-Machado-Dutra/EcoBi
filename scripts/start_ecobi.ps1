<#
.SYNOPSIS
    Script de inicialização do EcoBI Intelligence para PowerShell no Windows.
.DESCRIPTION
    Configura variáveis de ambiente locais, valida diretórios e inicia o EcoBI Launcher.
.PARAMETER Host
    Endereço IP de escuta (padrão: 127.0.0.1).
.PARAMETER Port
    Porta HTTP do servidor (padrão: 8000).
.PARAMETER NoBrowser
    Desativa abertura automática do navegador.
.PARAMETER CheckOnly
    Apenas valida o ambiente e encerra sem subir o servidor.
#>

param (
    [string]$Host = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$NoBrowser,
    [switch]$CheckOnly
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = (Resolve-Path "$ScriptDir\..").Path
Set-Location $RootDir

Write-Host "=======================================================" -ForegroundColor DarkGreen
Write-Host " EcoBI Intelligence — Release Piloto Windows" -ForegroundColor Green
Write-Host " Raiz do Projeto: $RootDir" -ForegroundColor Gray
Write-Host "=======================================================" -ForegroundColor DarkGreen

$VenvPython = "$RootDir\.venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    $PythonExe = $VenvPython
} else {
    $PythonExe = "python"
}

Write-Host "Runtime Python detectado: $PythonExe" -ForegroundColor Cyan

$ArgsList = @("scripts\ecobi_launcher.py", "--host", $Host, "--port", $Port)
if ($NoBrowser) { $ArgsList += "--no-browser" }
if ($CheckOnly) { $ArgsList += "--check-only" }

& $PythonExe $ArgsList

param (
    [string]$ModelName = 'qwen3.5:4b',
    [switch]$CheckOnly,
    [switch]$DefineOnly
)

function Test-EcoBILoopbackListenerAddresses {
    [CmdletBinding()]
    param ([scriptblock]$GetListenerAddresses)

    try {
        foreach ($address in @(& $GetListenerAddresses)) {
            $parsedAddress = [System.Net.IPAddress]::Parse([string]$address)
            if (-not [System.Net.IPAddress]::IsLoopback($parsedAddress)) { return $false }
        }
        return $true
    }
    catch {
        return $false
    }
}

function Initialize-EcoBIOllama {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory = $true)]
        [string]$ModelName,
        [switch]$CheckOnly,
        [string]$InstallDirectory = (Join-Path $env:LOCALAPPDATA 'Programs\Ollama'),
        [string]$TempDirectory = (Join-Path $env:TEMP 'EcoBI'),
        [scriptblock]$ResolveExecutable = {
            param($InstallPath)
            $command = Get-Command ollama -ErrorAction SilentlyContinue
            if ($command -and $command.CommandType -eq 'Application' -and $command.Source -like '*.exe') { return $command.Source }
            $candidate = Join-Path $InstallPath 'ollama.exe'
            if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
            return $null
        },
        [scriptblock]$DownloadInstaller = {
            param($Uri, $Destination)
            Invoke-WebRequest -Uri $Uri -OutFile $Destination -UseBasicParsing
        },
        [scriptblock]$VerifySignature = {
            param($Path)
            $signature = Get-AuthenticodeSignature -FilePath $Path
            return ($signature.Status -eq 'Valid' -and $signature.SignerCertificate.Subject -match '(^|, )O=Ollama Inc\.(,|$)')
        },
        [scriptblock]$InstallAction = {
            param($Path, $InstallPath)
            $arguments = "/VERYSILENT /NORESTART /SUPPRESSMSGBOXES /DIR=`"$InstallPath`""
            $process = Start-Process -FilePath $Path -ArgumentList $arguments -PassThru
            $process.WaitForExit()
            return $process.ExitCode
        },
        [scriptblock]$GetListenerAddresses = {
            Get-NetTCPConnection -State Listen -LocalPort 11434 -ErrorAction Stop |
                Select-Object -ExpandProperty LocalAddress
        },
        [scriptblock]$RunCli = {
            param($Executable, [string[]]$Arguments)
            if ($Arguments[0] -eq 'list') {
                $output = & $Executable @Arguments 2>&1 | Out-String
                return @{ ExitCode = $LASTEXITCODE; Output = $output }
            }
            & $Executable @Arguments
            return @{ ExitCode = $LASTEXITCODE; Output = '' }
        },
        [scriptblock]$StartServer = {
            param($Executable)
            Start-Process -FilePath $Executable -ArgumentList 'serve' -WindowStyle Hidden | Out-Null
        },
        [scriptblock]$Sleep = { Start-Sleep -Seconds 1 },
        [scriptblock]$ConfirmSetup = {
            param($Message)
            Write-Host $Message
            try { return ((Read-Host 'Continue? [y/N]') -match '^(?i:y)$') } catch { return $false }
        }
    )

    if ($ModelName -notmatch '^[A-Za-z0-9][A-Za-z0-9._:/-]*$') {
        Write-Warning 'The configured Ollama model name is invalid; EcoBI will use its deterministic local fallback.'
        return $false
    }

    $ollama = & $ResolveExecutable $InstallDirectory
    if ($ollama -and -not (& $VerifySignature $ollama)) {
        Write-Warning 'The local Ollama executable does not have a valid Ollama Inc. signature; EcoBI will use its deterministic local fallback.'
        return $false
    }
    if (-not $ollama -and -not $CheckOnly) {
        if (-not (& $ConfirmSetup 'First-run setup downloads the official Ollama installer (at least 4 GB of disk space) and a local model may require additional storage.')) {
            Write-Warning 'Ollama setup was declined; EcoBI will use its deterministic local fallback. External AI remains blocked.'
            return $false
        }
        $installerPath = Join-Path $TempDirectory 'OllamaSetup.exe'
        try {
            New-Item -ItemType Directory -Path $TempDirectory -Force | Out-Null
            & $DownloadInstaller 'https://ollama.com/download/OllamaSetup.exe' $installerPath
            if (-not (Test-Path -LiteralPath $installerPath -PathType Leaf) -or -not (& $VerifySignature $installerPath)) {
                throw 'The downloaded Ollama installer has no valid Ollama Inc. Authenticode signature.'
            }
            $exitCode = & $InstallAction $installerPath $InstallDirectory
            if ($exitCode -ne 0) { throw "The per-user Ollama installer exited with code $exitCode." }
            $ollama = & $ResolveExecutable $InstallDirectory
            if (-not $ollama) { throw 'Ollama installation completed but its executable was not found in the user install directory.' }
            if (-not (& $VerifySignature $ollama)) { throw 'The installed Ollama executable does not have a valid Ollama Inc. signature.' }
            if (($env:PATH -split ';') -notcontains $InstallDirectory) { $env:PATH = "$InstallDirectory;$env:PATH" }
        }
        catch {
            Write-Warning "Ollama setup failed; EcoBI will use deterministic local fallback. External AI remains blocked. $($_.Exception.Message)"
            return $false
        }
        finally {
            Remove-Item -LiteralPath $installerPath -Force -ErrorAction SilentlyContinue
        }
    }

    if (-not $ollama) {
        Write-Warning 'Ollama is unavailable; EcoBI will use its deterministic local fallback. External AI remains blocked.'
        return $false
    }

    $originalOllamaHost = $env:OLLAMA_HOST
    $env:OLLAMA_HOST = '127.0.0.1:11434'
    try {
        if (-not (Test-EcoBILoopbackListenerAddresses -GetListenerAddresses $GetListenerAddresses)) {
            Write-Warning 'The Ollama listener could not be verified as loopback-only; deterministic fallback remains active and external AI remains blocked.'
            return $false
        }
        $listing = & $RunCli $ollama @('list')
        if ($listing.ExitCode -ne 0 -and -not $CheckOnly) {
            try { & $StartServer $ollama } catch { }
            for ($attempt = 0; $attempt -lt 20 -and $listing.ExitCode -ne 0; $attempt++) {
                & $Sleep
                if (-not (Test-EcoBILoopbackListenerAddresses -GetListenerAddresses $GetListenerAddresses)) {
                    Write-Warning 'The Ollama listener could not be verified as loopback-only; deterministic fallback remains active and external AI remains blocked.'
                    return $false
                }
                $listing = & $RunCli $ollama @('list')
            }
        }
        if ($listing.ExitCode -ne 0) {
            Write-Warning 'The local Ollama service is unavailable; EcoBI will use its deterministic local fallback. External AI remains blocked.'
            return $false
        }

        if (-not (Test-EcoBILoopbackListenerAddresses -GetListenerAddresses $GetListenerAddresses)) {
            Write-Warning 'The Ollama listener is not verifiably loopback-only; deterministic fallback remains active and external AI remains blocked.'
            return $false
        }
        $modelPresent = ($listing.Output -split '\r?\n' | Select-Object -Skip 1 | Where-Object {
            $columns = $_.Trim() -split '\s+'
            $columns.Count -gt 0 -and $columns[0] -eq $ModelName
        } | Measure-Object).Count -gt 0
        if (-not $modelPresent -and $CheckOnly) {
            Write-Warning "Configured local model '$ModelName' is not installed; no download occurs in check-only mode."
            return $false
        }
        if (-not $modelPresent) {
            if (-not (& $ConfirmSetup "The configured model '$ModelName' is missing. Downloading it can require substantial disk space.")) {
                Write-Warning 'The model download was declined; EcoBI will use its deterministic local fallback. External AI remains blocked.'
                return $false
            }
            if (-not (Test-EcoBILoopbackListenerAddresses -GetListenerAddresses $GetListenerAddresses)) {
                Write-Warning 'The Ollama listener is not verifiably loopback-only; deterministic fallback remains active and external AI remains blocked.'
                return $false
            }
            $pull = & $RunCli $ollama @('pull', $ModelName)
            if ($pull.ExitCode -ne 0) {
                Write-Warning "Model '$ModelName' could not be downloaded from the local Ollama service; deterministic fallback remains available and external AI remains blocked."
                return $false
            }
            $listing = & $RunCli $ollama @('list')
            $modelPresent = $listing.ExitCode -eq 0 -and (($listing.Output -split '\r?\n' | Select-Object -Skip 1 | Where-Object {
                $columns = $_.Trim() -split '\s+'
                $columns.Count -gt 0 -and $columns[0] -eq $ModelName
            } | Measure-Object).Count -gt 0)
        }
        if (-not $modelPresent) {
            Write-Warning "Configured local model '$ModelName' is still unavailable; deterministic fallback remains active."
            return $false
        }
        Write-Host "Local Ollama and model '$ModelName' are ready."
        return $true
    }
    catch {
        Write-Warning "Local Ollama readiness failed; deterministic fallback remains available and external AI remains blocked. $($_.Exception.Message)"
        return $false
    }
    finally {
        if ($null -eq $originalOllamaHost) { Remove-Item Env:OLLAMA_HOST -ErrorAction SilentlyContinue }
        else { $env:OLLAMA_HOST = $originalOllamaHost }
    }
}

if (-not $DefineOnly) { Initialize-EcoBIOllama -ModelName $ModelName -CheckOnly:$CheckOnly | Out-Null }

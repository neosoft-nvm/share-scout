$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
function Install-Dependency($id, $description) {
    if (!(Get-Command winget -ErrorAction SilentlyContinue)) { throw "Install $description manually, then reopen this launcher. winget is unavailable." }
    Write-Host "Setting up $description. Windows may ask for administrator approval."
    winget install --id $id --exact --source winget --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -ne 0) { throw "Installation failed for $description." }
    $env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
}
try {
    if (!(Get-Command py -ErrorAction SilentlyContinue) -and !(Get-Command python -ErrorAction SilentlyContinue)) { Install-Dependency 'Python.Python.3.13' 'Python 3' }
    if (!(Get-Command rclone -ErrorAction SilentlyContinue)) { Install-Dependency 'Rclone.Rclone' 'rclone' }
    $winfsp = (Test-Path "${env:ProgramFiles(x86)}\WinFsp") -or (Test-Path "$env:ProgramFiles\WinFsp")
    if (!$winfsp) { Install-Dependency 'WinFsp.WinFsp' 'WinFsp cloud drive support' }
    $appDir = Join-Path $env:LOCALAPPDATA 'ResourceMapperApp'
    New-Item -ItemType Directory -Force -Path $appDir | Out-Null
    if ($PSScriptRoot -ne $appDir) {
        Get-ChildItem -LiteralPath $PSScriptRoot -Filter '*.py' | Copy-Item -Destination $appDir -Force
        Copy-Item -LiteralPath "$PSScriptRoot\Launch-Windows.cmd", "$PSScriptRoot\Setup-Windows.ps1" -Destination $appDir -Force
        Copy-Item -LiteralPath "$PSScriptRoot\sharescout.png", "$PSScriptRoot\sharescout.ico", "$PSScriptRoot\sharescout.svg" -Destination $appDir -Force
        Get-ChildItem -LiteralPath $PSScriptRoot -Filter 'icon_*.png' | Copy-Item -Destination $appDir -Force
        if (Test-Path "$PSScriptRoot\vendor") {
            Copy-Item -Recurse -LiteralPath "$PSScriptRoot\vendor" -Destination "$appDir\vendor" -Force
        }
    }
    $pythonArgs = ''
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $pythonGui = Join-Path (Split-Path (Get-Command py).Source) 'pyw.exe'
        $pythonArgs = '-3 '
    } else {
        $pythonGui = Join-Path (Split-Path (Get-Command python).Source) 'pythonw.exe'
    }
    if (!(Test-Path $pythonGui)) { throw 'Python was installed, but its desktop launcher was not found. Reopen the setup launcher.' }
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Programs')) 'ShareScout.lnk'))
    $shortcut.TargetPath = $pythonGui
    $shortcut.Arguments = $pythonArgs + '"' + $appDir + '\resource_mapper.py"'
    $shortcut.WorkingDirectory = $appDir
    $shortcut.Description = 'Find computers and connect shared folders'
    $shortcut.IconLocation = "$appDir\sharescout.ico"
    $shortcut.Save()
    Start-Process -FilePath $pythonGui -ArgumentList $shortcut.Arguments -WorkingDirectory $appDir
    exit 0
} catch { Write-Host $_ -ForegroundColor Red; exit 1 }

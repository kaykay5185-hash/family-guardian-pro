$ErrorActionPreference = 'Stop'
$serverDir = Join-Path $PSScriptRoot '..\server' | Resolve-Path
$venvPython = Join-Path $serverDir '.venv\Scripts\python.exe'
$venvPip = Join-Path $serverDir '.venv\Scripts\pip.exe'
$pythonLauncher = Get-Command py -ErrorAction SilentlyContinue
if (-not (Test-Path $venvPython)) {
    if (-not $pythonLauncher) { throw 'Python 3.10 or later is required. Install it from python.org, then run this launcher again.' }
    & py -3 -m venv (Join-Path $serverDir '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment.' }
}
if (-not (Test-Path $venvPip)) { throw 'The Python environment is incomplete. Remove server\.venv and retry.' }
Write-Host 'Installing or checking Family Guardian PC dependencies...' -ForegroundColor Yellow
& $venvPip install -r (Join-Path $serverDir 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Check your internet connection and retry.' }
$username = Read-Host 'Choose a parent dashboard username'
if ([string]::IsNullOrWhiteSpace($username)) { throw 'A username is required.' }
$securePassword = Read-Host 'Choose a parent dashboard password' -AsSecureString
$password = [System.Net.NetworkCredential]::new('', $securePassword).Password
if ($password.Length -lt 12) { throw 'Use a password with at least 12 characters.' }
$passwordHash = $password | & $venvPython -c "import sys; from werkzeug.security import generate_password_hash; print(generate_password_hash(sys.stdin.read().rstrip()))"
if (-not $passwordHash) { throw 'Could not prepare the password hash.' }
$password = $null
$securePassword.Dispose()
$env:PARENT_USERNAME = $username
$env:PARENT_PASSWORD_HASH = $passwordHash.Trim()
$randomBytes = New-Object byte[] 48
$randomGenerator = [Security.Cryptography.RandomNumberGenerator]::Create()
try { $randomGenerator.GetBytes($randomBytes) } finally { $randomGenerator.Dispose() }
$env:SESSION_SECRET = [Convert]::ToBase64String($randomBytes)
$env:DATABASE_PATH = Join-Path $serverDir 'family_guardian.sqlite3'
$env:HOST = '0.0.0.0'
$env:PORT = '5000'
$localUrl = 'http://127.0.0.1:5000'
$lanAddress = Get-NetIPAddress -AddressFamily IPv4 -AddressState Preferred -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -ne '127.0.0.1' -and $_.IPAddress -notlike '169.254.*' -and $_.InterfaceAlias -notmatch 'Loopback' } |
    Select-Object -First 1 -ExpandProperty IPAddress
if ($lanAddress) { $phoneUrl = "http://${lanAddress}:5000" }
Write-Host "Starting Family Guardian Pro on this PC at $localUrl" -ForegroundColor Green
if ($phoneUrl) { Write-Host "On a phone connected to the same Wi-Fi, open $phoneUrl" -ForegroundColor Cyan }
else { Write-Host 'Could not detect the PC Wi-Fi address. On the PC, run ipconfig and use its IPv4 Address on your phone, followed by :5000.' -ForegroundColor Yellow }
Write-Host 'This local session ends when you close this window. Press Ctrl+C to stop.'
$stdoutLog = Join-Path $serverDir 'pc-server.log'
$stderrLog = Join-Path $serverDir 'pc-server-error.log'
$server = Start-Process -FilePath $venvPython -ArgumentList 'app.py' -WorkingDirectory $serverDir -WindowStyle Hidden -PassThru -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog
try {
    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        if ($server.HasExited) { throw "The local server exited. See $stderrLog" }
        try { Invoke-WebRequest -Uri "$localUrl/login" -UseBasicParsing -TimeoutSec 1 | Out-Null; $ready = $true; break } catch { Start-Sleep -Milliseconds 500 }
    }
    if (-not $ready) { throw "The local server did not become ready. See $stderrLog" }
    Start-Process $localUrl
    while (-not $server.HasExited) { Start-Sleep -Seconds 1 }
} finally {
    if (-not $server.HasExited) { Stop-Process -Id $server.Id -Force }
}

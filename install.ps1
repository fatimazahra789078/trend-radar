# Trend Radar installer. Double-click INSTALL.cmd (or: powershell -ExecutionPolicy Bypass -File install.ps1)
# Everything is per-user (no admin needed): a scheduled task, a notification name, trendradar:// links, a desktop icon.
$ErrorActionPreference = 'Stop'
$root   = Split-Path -Parent $MyInvocation.MyCommand.Path
$script = Join-Path $root 'trend_radar.py'

Write-Host "== Trend Radar install ==" -ForegroundColor Cyan

# 1. Python (standard library only, nothing to pip install)
$py = $null
foreach ($cmd in @('py', 'python')) {
    try {
        $p = & $cmd -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $p) { $py = "$p".Trim(); break }
    } catch {}
}
if (-not $py) { Write-Host "Python not found. Install Python 3 from https://www.python.org first." -ForegroundColor Red; exit 1 }
$pyw = Join-Path (Split-Path $py) 'pythonw.exe'
if (-not (Test-Path $pyw)) { $pyw = $py }
Write-Host "Python: $pyw"

# 2. Icon
& $py $script --make-icon

# 3. Notification sender name "Trend Radar"
$k = 'HKCU:\Software\Classes\AppUserModelId\TrendRadar.Notifier'
New-Item -Path $k -Force | Out-Null
New-ItemProperty -Path $k -Name DisplayName -Value 'Trend Radar' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $k -Name IconUri -Value (Join-Path $root 'icon.png') -PropertyType String -Force | Out-Null
New-ItemProperty -Path $k -Name ShowInSettings -Value 1 -PropertyType DWord -Force | Out-Null

# 4. trendradar:// links (the "Dashboard" button inside notifications)
$p = 'HKCU:\Software\Classes\trendradar'
New-Item -Path "$p\shell\open\command" -Force | Out-Null
Set-ItemProperty -Path $p -Name '(default)' -Value 'URL:Trend Radar'
New-ItemProperty -Path $p -Name 'URL Protocol' -Value '' -PropertyType String -Force | Out-Null
Set-ItemProperty -Path "$p\shell\open\command" -Name '(default)' -Value "`"$pyw`" `"$script`" --handle `"%1`""

# 5. Scheduled task: check every N minutes while you are logged in
$cfg = Get-Content (Join-Path $root 'config.json') -Raw | ConvertFrom-Json
$every = [int]$cfg.check_every_minutes
if ($every -lt 5) { $every = 15 }
$action = New-ScheduledTaskAction -Execute $pyw -Argument "`"$script`"" -WorkingDirectory $root
$repeat = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) -RepetitionInterval (New-TimeSpan -Minutes $every)
$logon  = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$logon.Delay = 'PT2M'   # give Wi-Fi 2 minutes after switching on, then the catch-up summary comes
$set = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 10) -MultipleInstances IgnoreNew
$who = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
$desc = 'Trend Radar: trends and breaking news notifications (USA, Germany, Europe)'
try {
    Register-ScheduledTask -TaskName 'TrendRadar' -Action $action -Trigger @($repeat, $logon) -Settings $set `
        -Principal $who -Description $desc -Force | Out-Null
} catch {
    Write-Host "Logon trigger not allowed without admin - using the repeating trigger only."
    Register-ScheduledTask -TaskName 'TrendRadar' -Action $action -Trigger $repeat -Settings $set `
        -Principal $who -Description $desc -Force | Out-Null
}
Write-Host "Scheduled task 'TrendRadar' every $every minutes."

# 6. Desktop icon: check now + open dashboard
$ws = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'Trend Radar.lnk'))
$lnk.TargetPath = $pyw
$lnk.Arguments = "`"$script`" --open"
$lnk.WorkingDirectory = $root
$lnk.IconLocation = (Join-Path $root 'icon.ico')
$lnk.Description = 'Check trends now and open the dashboard'
$lnk.Save()
Write-Host "Desktop icon 'Trend Radar' created."

# 7. Test notification + first check
& $py $script --test
Write-Host "Running the first check..."
& $py $script --open
Write-Host "Done. You will get notifications automatically." -ForegroundColor Green

# Removes Trend Radar's scheduled task, notification name, trendradar:// links and desktop icon.
# Your files in this folder stay (delete the folder yourself if you want).
$ErrorActionPreference = 'SilentlyContinue'
Unregister-ScheduledTask -TaskName 'TrendRadar' -Confirm:$false
Remove-Item -Path 'HKCU:\Software\Classes\AppUserModelId\TrendRadar.Notifier' -Recurse -Force
Remove-Item -Path 'HKCU:\Software\Classes\trendradar' -Recurse -Force
Remove-Item -Path (Join-Path ([Environment]::GetFolderPath('Desktop')) 'Trend Radar.lnk') -Force
Write-Host "Trend Radar removed."

# Removes Agent Composer: the app, its shortcuts, its FL scripts and its Apps list entry.
# Your chats, MIDI, takes and Mini Brain in Documents\Agent Composer are left alone,
# and so are uv and loopMIDI (other apps may use them).
$dest = Join-Path $env:LOCALAPPDATA "Programs\Agent Composer"
try { & (Join-Path $dest "install.ps1") -Uninstall | Out-Null } catch {}
foreach ($dir in @([Environment]::GetFolderPath("Programs"), [Environment]::GetFolderPath("Desktop"))) {
    Remove-Item (Join-Path $dir "Agent Composer.lnk") -ErrorAction SilentlyContinue
}
Remove-Item "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\AgentComposer" -Recurse -ErrorAction SilentlyContinue
Set-Location $env:TEMP
Remove-Item $dest -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "Agent Composer is removed. Your files in Documents\Agent Composer are still there."
Start-Sleep 3

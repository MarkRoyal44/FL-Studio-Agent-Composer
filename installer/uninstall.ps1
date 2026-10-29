# Removes Agent Composer: the app, its shortcuts, its FL scripts and its Apps list entry.
# Your chats, MIDI, takes and Mini Brain in Documents\Agent Composer are left alone,
# and so are uv and loopMIDI (other apps may use them).
$dest = Join-Path $env:LOCALAPPDATA "Programs\Agent Composer"
try { & (Join-Path $dest "install.ps1") -Uninstall | Out-Null } catch {}
foreach ($dir in @([Environment]::GetFolderPath("Programs"), [Environment]::GetFolderPath("Desktop"))) {
    Remove-Item (Join-Path $dir "Agent Composer.lnk") -ErrorAction SilentlyContinue
}
# The plugin, its Add menu entry and FL's search folder for it
$clapDir = Join-Path $env:LOCALAPPDATA "Programs\Common\CLAP"
Remove-Item (Join-Path $clapDir "Agent Composer.clap") -ErrorAction SilentlyContinue
$db = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "Image-Line\FL Studio\Presets\Plugin database\Generators"
Remove-Item (Join-Path $db "Agent Composer.*") -ErrorAction SilentlyContinue
if (-not (Get-ChildItem $clapDir -ErrorAction SilentlyContinue)) {
    Get-ChildItem "HKCU:\Software\Image-Line\Shared\Plugin search paths\List" -ErrorAction SilentlyContinue |
        Where-Object { (Get-ItemProperty $_.PSPath).path -eq "$clapDir\" } | Remove-Item -Recurse
}
Remove-Item "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\AgentComposer" -Recurse -ErrorAction SilentlyContinue
Set-Location $env:TEMP
Remove-Item $dest -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "Agent Composer is removed. Your files in Documents\Agent Composer are still there."
Start-Sleep 3

# Agent Composer installer (Windows). Copies two scripts into FL Studio's settings folder,
# makes the Agent Composer folders, and checks the tools it needs. Installs no software.
#   Run:   powershell -ExecutionPolicy Bypass -File install.ps1
#   Undo:  powershell -ExecutionPolicy Bypass -File install.ps1 -Uninstall
param([switch]$Uninstall)
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$fl = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "Image-Line\FL Studio\Settings"
$hw = Join-Path $fl "Hardware\AgentComposer"
$pr = Join-Path $fl "Piano roll scripts"
$prScript = Join-Path $pr "Agent Composer.pyscript"

if ($Uninstall) {
    if (Test-Path $hw) { Remove-Item -Recurse -Force $hw; "Removed $hw" }
    if (Test-Path $prScript) { Remove-Item -Force $prScript; "Removed $prScript" }
    "Your MIDI files and takes in Documents\Agent Composer were left alone."
    exit 0
}

if (-not (Test-Path $fl)) { throw "FL Studio's settings folder wasn't found at $fl. Open FL Studio once, then run this again." }
New-Item -ItemType Directory -Force (Join-Path $hw "bridge"), $pr | Out-Null
Copy-Item (Join-Path $repo "fl\device_AgentComposer.py"), (Join-Path $repo "fl\LICENSE-fl-studio-mcp") $hw -Force
Copy-Item (Join-Path $repo "fl\Agent Composer.pyscript") $pr -Force
$home_ = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "Agent Composer"
New-Item -ItemType Directory -Force (Join-Path $home_ "Takes"), (Join-Path $home_ "MIDI") | Out-Null
"Copied the FL script to      $hw"
"Copied the piano roll script $prScript"
"Your takes and MIDI live in  $home_"
""
$need = @{
    "claude" = "Claude Code  -> https://docs.claude.com/en/docs/claude-code (then run 'claude' once to sign in)";
    "uv"     = "uv           -> https://docs.astral.sh/uv/";
    "python" = "Python 3.10+ -> https://www.python.org/downloads/";
}
$missing = $need.Keys | Where-Object { -not (Get-Command $_ -ErrorAction SilentlyContinue) }
if ($missing) { "Still needed:"; $missing | ForEach-Object { "  " + $need[$_] } } else { "Claude Code, uv and Python are all here." }
""
"Last step inside FL Studio: Options > MIDI settings, pick your virtual MIDI port (loopMIDI on Windows),"
"set Controller type to 'Agent Composer', and enable it. Then run start.bat."

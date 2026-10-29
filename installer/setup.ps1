# Agent Composer setup (Windows). This is what AgentComposerSetup.exe runs.
# It puts the app in %LOCALAPPDATA%\Programs\Agent Composer, gets the free helpers it needs
# (uv, which brings its own Python, and loopMIDI, which gives FL a port to load the script on),
# copies the FL scripts, and adds Start menu and desktop shortcuts. No admin needed, except
# loopMIDI's own installer, which Windows asks about.
#   Run from a checkout:  powershell -ExecutionPolicy Bypass -File installer\setup.ps1
#   Undo:                 Settings > Apps > Agent Composer > Uninstall
param([switch]$Quiet)
$ErrorActionPreference = "Stop"
# Native tools write progress to stderr; that isn't an error.
$PSNativeCommandUseErrorActionPreference = $false
$Host.UI.RawUI.WindowTitle = "Agent Composer setup"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$dest = Join-Path $env:LOCALAPPDATA "Programs\Agent Composer"

function Say($t, $c = "Gray") { Write-Host $t -ForegroundColor $c }
function Ask($q) {
    if ($Quiet) { return $true }
    $a = Read-Host "$q [Y/n]"
    return ($a -eq "" -or $a -match "^[yY]")
}

Say ""
Say "  Agent Composer for FL Studio" Red
Say "  Chat with an AI agent that works inside your open FL project."
Say ""

# 1. The app itself
Say "[1/5] Copying Agent Composer to $dest"
$payload = Join-Path $here "payload.zip"
$stage = Join-Path $env:TEMP ("ac-setup-" + [guid]::NewGuid().ToString("N"))
if (Test-Path $payload) {
    Expand-Archive -Path $payload -DestinationPath $stage -Force
    $src = $stage
} else {
    $src = Split-Path -Parent $here  # running from a checkout
}
New-Item -ItemType Directory -Force $dest | Out-Null
# Replace the app files, keep nothing else there: your own stuff lives in Documents\Agent Composer.
Get-ChildItem $dest -Force | Remove-Item -Recurse -Force
Get-ChildItem $src -Force | Where-Object { $_.Name -notin @(".git", "__pycache__", "dist") } |
    Copy-Item -Destination $dest -Recurse -Force
if (Test-Path $stage) { Remove-Item -Recurse -Force $stage }

# 2. uv (brings Python with it)
Say "[2/5] Checking uv, the tool that runs Agent Composer"
$env:PATH = "$env:USERPROFILE\.local\bin;$env:PATH"
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Say "      Installing uv for this user (free, from astral.sh)..."
    powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    $env:PATH = "$env:USERPROFILE\.local\bin;$env:PATH"
}
if (Get-Command uv -ErrorAction SilentlyContinue) {
    Say "      Getting Python through uv (first time only)..."
    cmd /c "uv python install 3.12 >nul 2>&1"
    cmd /c "uv sync --script `"$dest\mcp_server.py`" >nul 2>&1"
    Say "      uv is ready." Green
} else {
    Say "      uv didn't install. Get it from https://docs.astral.sh/uv/ and run setup again." Yellow
}

# 3. loopMIDI (the port FL loads the script on)
Say "[3/5] Checking loopMIDI, the virtual MIDI port FL talks through"
$lm = "${env:ProgramFiles(x86)}\Tobias Erichsen\loopMIDI\loopMIDI.exe"
if (-not (Test-Path $lm)) {
    if ((Get-Command winget -ErrorAction SilentlyContinue) -and (Ask "      loopMIDI isn't installed. Install it now (free)?")) {
        cmd /c "winget install --id TobiasErichsen.loopMIDI -e --silent --accept-package-agreements --accept-source-agreements >nul 2>&1"
    }
}
if (Test-Path $lm) {
    # A port called "loopMIDI Port" is what the FL script looks for.
    $ports = "HKCU:\Software\Tobias Erichsen\loopMIDI\Ports"
    New-Item -Force $ports -ErrorAction SilentlyContinue | Out-Null
    if ($null -eq (Get-ItemProperty $ports -Name "loopMIDI Port" -ErrorAction SilentlyContinue)) {
        New-ItemProperty $ports -Name "loopMIDI Port" -Value 1 -PropertyType DWord -Force | Out-Null
    }
    $run = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
    if ($null -eq (Get-ItemProperty $run -Name "loopMIDI" -ErrorAction SilentlyContinue)) {
        New-ItemProperty $run -Name "loopMIDI" -Value $lm -PropertyType String -Force | Out-Null
    }
    if (-not (Get-Process loopMIDI -ErrorAction SilentlyContinue)) { Start-Process $lm }
    Say "      loopMIDI is ready, with a port called 'loopMIDI Port'." Green
} else {
    Say "      Skipped. Get it from https://www.tobias-erichsen.de/software/loopmidi.html" Yellow
}

# 4. FL scripts
Say "[4/5] Copying the scripts into FL Studio"
try {
    & (Join-Path $dest "install.ps1") | Out-Null
    Say "      Done. FL picks it up on its own the next time it opens." Green
} catch {
    Say "      $($_.Exception.Message)" Yellow
}

# 5. Shortcuts and the Apps list entry
Say "[5/5] Adding shortcuts"
$ws = New-Object -ComObject WScript.Shell
$icon = Join-Path $dest "app\ui\icon.ico"
foreach ($dir in @([Environment]::GetFolderPath("Programs"), [Environment]::GetFolderPath("Desktop"))) {
    $l = $ws.CreateShortcut((Join-Path $dir "Agent Composer.lnk"))
    $l.TargetPath = Join-Path $dest "start.bat"
    $l.WorkingDirectory = $dest
    $l.IconLocation = $icon
    $l.WindowStyle = 7  # the console starts minimized
    $l.Description = "Agent Composer for FL Studio"
    $l.Save()
}
$un = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\AgentComposer"
New-Item -Force $un | Out-Null
$ver = (Select-String -Path (Join-Path $dest "app\server.py") -Pattern '^VERSION = "(.+)"').Matches[0].Groups[1].Value
@{ DisplayName = "Agent Composer for FL Studio"; DisplayVersion = $ver; Publisher = "Tech-Ants LLC";
   DisplayIcon = $icon; InstallLocation = $dest; NoModify = 1; NoRepair = 1;
   UninstallString = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$dest\installer\uninstall.ps1`"" }.GetEnumerator() |
    ForEach-Object {
        $t = if ($_.Value -is [int]) { "DWord" } else { "String" }
        New-ItemProperty $un -Name $_.Key -Value $_.Value -PropertyType $t -Force | Out-Null
    }

Say ""
Say "  All set. Agent Composer $ver is installed." Green
Say "  Open FL Studio, then open Agent Composer from the desktop or Start menu."
Say "  The 'Start here' tab walks you through the rest."
Say ""
if (-not $Quiet -and (Ask "  Open Agent Composer now?")) { Start-Process (Join-Path $dest "start.bat") -WorkingDirectory $dest -WindowStyle Minimized }

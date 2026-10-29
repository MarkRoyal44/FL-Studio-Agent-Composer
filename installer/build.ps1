# Builds dist\AgentComposerSetup.exe from the committed code, using IExpress (built into Windows).
#   powershell -ExecutionPolicy Bypass -File installer\build.ps1
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$work = Join-Path $repo "dist\build"
$exe = Join-Path $repo "dist\AgentComposerSetup.exe"
Remove-Item $work -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $work | Out-Null

# Only what's committed goes in, so nothing private can slip into the exe.
git -C $repo archive --format=zip -o (Join-Path $work "payload.zip") HEAD
Copy-Item (Join-Path $repo "installer\setup.ps1") $work
Set-Content (Join-Path $work "run.cmd") "@powershell -NoProfile -ExecutionPolicy Bypass -File setup.ps1" -Encoding ascii

$sed = @"
[Version]
Class=IEXPRESS
SEDVersion=3
[Options]
PackagePurpose=InstallApp
ShowInstallProgramWindow=0
HideExtractAnimation=1
UseLongFileName=1
InsideCompressed=0
CAB_FixedSize=0
CAB_ResvCodeSigning=0
RebootMode=N
InstallPrompt=
DisplayLicense=
FinishMessage=
TargetName=$exe
FriendlyName=Agent Composer setup
AppLaunched=cmd /c run.cmd
PostInstallCmd=<None>
AdminQuietInstCmd=
UserQuietInstCmd=
SourceFiles=SourceFiles
[Strings]
FILE0="payload.zip"
FILE1="setup.ps1"
FILE2="run.cmd"
[SourceFiles]
SourceFiles0=$work\
[SourceFiles0]
%FILE0%=
%FILE1%=
%FILE2%=
"@
$sedPath = Join-Path $work "setup.sed"
Set-Content $sedPath $sed -Encoding ascii
Remove-Item $exe -ErrorAction SilentlyContinue
Start-Process "$env:WINDIR\System32\iexpress.exe" -ArgumentList "/N", "/Q", $sedPath -Wait -NoNewWindow
if (-not (Test-Path $exe)) { throw "IExpress didn't make the exe." }
Remove-Item $work -Recurse -Force
"Built $exe ({0:N0} KB)" -f ((Get-Item $exe).Length / 1KB)

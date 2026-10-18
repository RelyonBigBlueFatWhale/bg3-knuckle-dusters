# Knuckle Dusters probe -- compile + pack + deploy
# ASCII only (Windows PowerShell 5.1 reads BOM-less files as ANSI).
# Usage: powershell -NoProfile -File D:\DSH\knuckle_tools\build.ps1
$ErrorActionPreference = 'Continue'

$ROOT   = 'D:\DSH\knuckle_mod'
$MOD    = 'KnuckleDusters'
$DIVINE = 'D:\Tools\LSLib\Divine.exe'
$LOCAPY = 'D:\DSH\bg3-ascendant\tools\loca.py'
$DIST   = 'D:\DSH\knuckle_pak'
$GAMEMODS = Join-Path $env:LOCALAPPDATA "Larian Studios\Baldur's Gate 3\Mods"

function Invoke-Native {
    param([string]$Exe, [string[]]$Arguments, [string]$Expect)
    $out = & $Exe @Arguments 2>&1
    $code = $LASTEXITCODE
    foreach ($line in $out) {
        if ("$line" -match 'Wrote|INFO|FATAL|rror|entries') { Write-Host "    $line" }
    }
    if ($Expect -and -not [System.IO.File]::Exists($Expect)) { throw "step failed (exit $code): expected $Expect" }
}

$rt = Join-Path $ROOT "Public\$MOD\RootTemplates"

Write-Host '--- 0/5 UI: TextureBank lsx -> lsf ---' -ForegroundColor Cyan
$tbLsx = Join-Path $ROOT "Public\$MOD\Content\UI\[PAK]_UI\_merged.lsx"
if ([System.IO.File]::Exists($tbLsx)) {
    $tbLsf = Join-Path $ROOT "Public\$MOD\Content\UI\[PAK]_UI\_merged.lsf"
    if (Test-Path -LiteralPath $tbLsf) { Remove-Item -LiteralPath $tbLsf -Force }
    Invoke-Native $DIVINE @('-g','bg3','-a','convert-resource','-s',$tbLsx,'-d',$tbLsf) $tbLsf
} else {
    Write-Host '    (no TextureBank to compile)' -ForegroundColor DarkGray
}

Write-Host '--- 1/4 root templates: lsx -> lsf ---' -ForegroundColor Cyan
$lsf = Join-Path $rt '_merged.lsf'
if (Test-Path $lsf) { Remove-Item $lsf -Force }
Invoke-Native $DIVINE @('-g','bg3','-a','convert-resource','-s',(Join-Path $rt '_merged.lsx'),'-d',$lsf) $lsf

Write-Host '--- 2/4 localization: xml -> loca ---' -ForegroundColor Cyan
foreach ($base in @((Join-Path $ROOT "Public\$MOD\Localization"), (Join-Path $ROOT 'Localization'))) {
    foreach ($lang in @('Chinese', 'English')) {
        $xml  = Join-Path $base "$lang\$MOD.xml"
        $loca = Join-Path $base "$lang\$MOD.loca"
        if (Test-Path $loca) { Remove-Item $loca -Force }
        Invoke-Native 'python' @($LOCAPY,'build',$xml,$loca) $loca
        Invoke-Native 'python' @($LOCAPY,'verify',$loca)
    }
}

Write-Host '--- 2b/4 visual bank: lsx -> lsf ---' -ForegroundColor Cyan
$vbank = Join-Path $ROOT 'Public\Shared\Content\Assets\Weapons\[PAK]_Humans\_merged.lsx'
if ([System.IO.File]::Exists($vbank)) {
  $vbankOut = [System.IO.Path]::ChangeExtension($vbank, '.lsf')
  # Divine may silently keep a stale .lsf when the target already exists
  if (Test-Path -LiteralPath $vbankOut) { Remove-Item -LiteralPath $vbankOut -Force }
  Invoke-Native $divine @('-g','bg3','-a','convert-resource','-s',$vbank,'-d',$vbankOut) $vbankOut
} else { throw "missing visual bank: $vbank" }

Write-Host '--- 3/4 create-package ---' -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $DIST | Out-Null
$pak = Join-Path $DIST "$MOD.pak"
if (Test-Path $pak) { Remove-Item $pak -Force }
Invoke-Native $DIVINE @('-g','bg3','-a','create-package','-s',$ROOT,'-d',$pak) $pak
Write-Host ("    wrote {0}  ({1:N0} B)" -f $pak, (Get-Item $pak).Length) -ForegroundColor Green

Write-Host '--- 4/4 read back ---' -ForegroundColor Cyan
& $DIVINE -g bg3 -a list-package -s $pak 2>&1 | ForEach-Object { ($_ -split "`t")[0] } |
    Where-Object { $_ -match '\S' } | ForEach-Object { "    $_" }

Write-Host ''
Write-Host '--- deploy: copy to game Mods ---' -ForegroundColor Cyan
$deployed = Join-Path $GAMEMODS "$MOD.pak"
try {
    Copy-Item $pak $deployed -Force -ErrorAction Stop
} catch {
    Write-Host "    [LOCKED] game is running, pak is in use - close the game and rerun" -ForegroundColor Red
    throw
}
# read-back check: a silent copy failure looks like a successful deploy (hit this before)
$h1 = (Get-FileHash $pak -Algorithm MD5).Hash
$h2 = (Get-FileHash $deployed -Algorithm MD5).Hash
if ($h1 -ne $h2) { throw "deploy mismatch: pak=$h1 deployed=$h2" }
Write-Host ("    -> {0}  ({1:N0} B, md5 {2} verified)" -f $deployed, (Get-Item $deployed).Length, $h2.Substring(0,12).ToLower()) -ForegroundColor Green
$lib = 'D:\Tools\BG3Mods'
if (Test-Path $lib) {
    Copy-Item $pak (Join-Path $lib "$MOD.pak") -Force -ErrorAction SilentlyContinue
    Write-Host "    -> BG3MM library synced" -ForegroundColor DarkGray
}

# Package all three knuckles (each with its OWN reference, geometry and texture set).
#
#   1. pack_gr2.py    OBJ -> DAE on a real vanilla weapon skeleton
#   2. divine         DAE -> GR2   (rigid mesh, header e5 9b 49 5e)
#   3. Decompress     verify the seven joints and that no LOD leaked in
#   4. wire_visuals   VisualBank + MaterialBank(3) + TextureBank(12)
#   5. build.ps1      create-package + deploy + md5 read-back
#   6. register       modsettings sync
#
# Textures are produced separately:
#   make_textures.py --style <style> --ao bake_out/<name>_ao.png
#   texconv -> <name>_{BM,NM,PM}.DDS in the Resources folder
#
# ASCII only (Windows PowerShell 5.1 parses BOM-less files as ANSI).
$ErrorActionPreference = 'Stop'

$DIVINE = 'D:\Tools\LSLib\Divine.exe'
$PP     = 'E:\SteamLibrary\steamapps\common\Baldurs Gate 3 Toolkit\preprocessor.exe'
$PY     = 'C:\Users\16084\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
$TOOLS  = 'D:\DSH\knuckle_tools'
$MODEL  = Join-Path $TOOLS 'model_out'
$WORK   = Join-Path $TOOLS 'gr2_convert\v7'
$RES    = 'D:\DSH\knuckle_mod\Generated\Public\KnuckleDusters\Assets\Weapons\Humans\KD_Knuckles_Unsharpened\Resources'
$NAMES  = @('KD_Knuckles_SteelSpike', 'KD_Knuckles_BoneChill', 'KD_Knuckles_Unsharpened')

New-Item -ItemType Directory -Force -Path $WORK, $RES | Out-Null
$env:PYTHONIOENCODING = 'utf-8'

$fail = 0
foreach ($name in $NAMES) {
    Write-Host ("=== {0} ===" -f $name) -ForegroundColor Cyan
    $obj = Join-Path $MODEL "$name.obj"
    if (-not (Test-Path -LiteralPath $obj)) { Write-Host '    FAIL: no OBJ' -ForegroundColor Red; $fail++; continue }

    & $PY -X utf8 (Join-Path $TOOLS 'pack_gr2.py') $name $obj 2>&1 |
        Select-String '\[pack\]' | ForEach-Object { Write-Host ('    ' + $_.Line) }
    $dae = Join-Path $WORK "$name.dae"
    $gr2 = Join-Path $WORK "$name.gr2"
    if (-not (Test-Path -LiteralPath $dae)) { Write-Host '    FAIL: no DAE' -ForegroundColor Red; $fail++; continue }
    if (Test-Path -LiteralPath $gr2) { Remove-Item -LiteralPath $gr2 -Force }

    & $DIVINE -g bg3 -a convert-model -s $dae -d $gr2 -i dae -o gr2 2>&1 |
        Select-String 'FATAL|rror' | Select-Object -First 2 | ForEach-Object { Write-Host ('    ! ' + $_.Line.Trim()) -ForegroundColor Red }
    if (-not (Test-Path -LiteralPath $gr2)) { Write-Host '    FAIL: convert-model produced nothing' -ForegroundColor Red; $fail++; continue }

    $dec = [System.IO.Path]::ChangeExtension($gr2, '.dec.gr2')
    if (Test-Path -LiteralPath $dec) { Remove-Item -LiteralPath $dec -Force }
    & $PP Decompress $gr2 -output $dec 2>&1 | Out-Null
    $txt = [System.Text.Encoding]::ASCII.GetString([System.IO.File]::ReadAllBytes($dec))
    Remove-Item -LiteralPath $dec -Force
    $want = @("Dummy_$name", 'Dummy_Sheath', 'Dummy_Attachment', "${name}_Mesh")
    $miss = $want | Where-Object { $txt -notmatch [regex]::Escape($_) }
    if ($miss) { Write-Host ("    FAIL: missing joints {0}" -f ($miss -join ',')) -ForegroundColor Red; $fail++ }
    else { Write-Host '    joints OK' -ForegroundColor Green }
    if ($txt -match "${name}_Mesh_LOD1") { Write-Host '    FAIL: LOD leaked' -ForegroundColor Red; $fail++ }

    $dst = Join-Path $RES "$name.gr2"
    Copy-Item -LiteralPath $gr2 -Destination $dst -Force
    $b = [System.IO.File]::ReadAllBytes($dst)
    Write-Host ("    installed {0,9:N0} B  head {1}" -f $b.Length, (($b[0..7] | ForEach-Object { $_.ToString('x2') }) -join ' '))
}

if ($fail -gt 0) { throw "$fail weapon(s) failed" }

Write-Host ''
Write-Host '[banks] visual + 3 materials + 12 textures' -ForegroundColor Cyan
& $PY -X utf8 (Join-Path $TOOLS 'wire_visuals.py') 2>&1 | Select-String 'visual |wrote|转换|OK' | ForEach-Object { Write-Host ('    ' + $_.Line) }

Write-Host '[pak] create-package + deploy' -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $TOOLS 'build.ps1') 2>&1 |
    Select-String 'wrote D:\\DSH\\knuckle_pak|-> C:|BG3MM|FATAL|LOCKED' | ForEach-Object { Write-Host ('    ' + $_.Line.Trim()) }
& $PY -X utf8 (Join-Path $TOOLS 'register_knuckles.py') 2>&1 | Select-String 'md5|BG3MM' | ForEach-Object { Write-Host ('    ' + $_.Line.Trim()) }
Write-Host 'done' -ForegroundColor Green

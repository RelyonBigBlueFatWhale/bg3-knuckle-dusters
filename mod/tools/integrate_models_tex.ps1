# Integrate the rebuilt models + the new look-dev textures into the pak.
#
#   model_out\*.obj              (multi-view rebuild, 8.7k-10k tris, centred at origin)
#   bake_out\*_ao.png            (1024^2, Cycles CPU)
#   weapon_tex\<style>_{BM,NM,PM}.png   (new look-dev sets from the texture pass)
#        -> texconv BC7_UNORM + DX10 header into Resources as KD_Knuckles_<name>_{BM,NM,PM}.DDS
#        -> pack_all.ps1  (GR2 from the new OBJs, install, banks, pak, deploy)
#
# The DDS *filenames* stay exactly what wire_visuals.py already points at, so the
# MaterialBank/TextureBank need no change: only the pixels move.
#
# Style -> weapon mapping is the look-dev pass's naming.
# ASCII only: Windows PowerShell 5.1 parses BOM-less files as ANSI.

$ErrorActionPreference = 'Stop'

$TOOLS = 'D:\DSH\knuckle_tools'
$TEX   = Join-Path $TOOLS 'weapon_tex'
$RES   = 'D:\DSH\knuckle_mod\Generated\Public\KnuckleDusters\Assets\Weapons\Humans\KD_Knuckles_Unsharpened\Resources'
$TC    = 'E:\SteamLibrary\steamapps\common\Baldurs Gate 3 Toolkit\texconv.exe'

$MAP = @(
    @{ Name = 'KD_Knuckles_SteelSpike';   Style = 'steel_runeglow' },
    @{ Name = 'KD_Knuckles_BoneChill';    Style = 'frost_icevein'  },
    @{ Name = 'KD_Knuckles_Unsharpened';  Style = 'brass_scroll'   }
)

Write-Host '--- 1/3 resolve texture styles ---' -ForegroundColor Cyan
$missing = @()
foreach ($m in $MAP) {
    foreach ($c in @('BM','NM','PM','GLOW')) {
        $p = Join-Path $TEX ('{0}_{1}.png' -f $m.Style, $c)
        if (-not (Test-Path -LiteralPath $p)) { $missing += $p }
    }
}
if ($missing.Count -gt 0) {
    Write-Host '  MISSING textures:' -ForegroundColor Red
    $missing | ForEach-Object { Write-Host ('    ' + $_) }
    throw 'texture sets incomplete - run the look-dev pass first'
}
foreach ($m in $MAP) { Write-Host ('  ' + $m.Name + '  <-  ' + $m.Style) -ForegroundColor Gray }

Write-Host '--- 2/3 convert to BC7 DDS (BM/NM/PM + GLOW) ---' -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $RES | Out-Null
foreach ($m in $MAP) {
    foreach ($c in @('BM','NM','PM','GLOW')) {
        $src = Join-Path $TEX ('{0}_{1}.png' -f $m.Style, $c)
        $tmp = Join-Path $TEX ('integ_' + $m.Style + '_' + $c)
        New-Item -ItemType Directory -Force -Path $tmp | Out-Null
        & $TC -f BC7_UNORM -m 1 -y -nologo -o $tmp -ft dds -dx10 $src | Out-Null
        $prod = Join-Path $tmp ('{0}_{1}.dds' -f $m.Style, $c)
        if (-not (Test-Path -LiteralPath $prod)) { throw ('texconv produced nothing for ' + $src) }
        $dst = Join-Path $RES ('{0}_{1}.DDS' -f $m.Name, $c)
        Copy-Item -LiteralPath $prod -Destination $dst -Force
        Write-Host ('  ' + (Split-Path $dst -Leaf) + '  ' + (Get-Item $dst).Length + ' B') -ForegroundColor Gray
    }
}

Write-Host '--- 3/3 pack: GR2 + banks + pak + deploy ---' -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $TOOLS 'pack_all.ps1')

Write-Host ''
Write-Host 'done. verify in game: model shape, texture colour, rune glow.' -ForegroundColor Green

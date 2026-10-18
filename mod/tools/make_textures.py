# -*- coding: utf-8 -*-
"""Compose the three BG3 texture maps from (baked AO) x (procedural filigree).

Division of labour -- this is the part that makes the ornament survive a game
pipeline:

  * baked AO      carries the FORM (holes, collars, coil bar, crown, lobes)
  * filigree      is a TILEABLE sheet (gen_ornament.py): scrolls + bezel + studs.
                  A tileable sheet lines up with ANY UV layout, so it does not
                  matter that the decimated mesh's islands are scattered.
  * both are sampled in the same UV space, so the colour grooves and the normal
    grooves land on the same texels.

Outputs (per style):
  <style>_BM.png  base colour  -- brass/steel/frost tint, grooves darkened, AO
                                 multiplied into the crevices
  <style>_NM.png  normal map   -- the filigree sheet (repeats across the UVs)
  <style>_PM.png  physical map -- R roughness (grooves rougher), G metallic,
                                 B cavity/AO for the shader

Run:
  python make_textures.py --style brass_filigree --res 1024
"""
import argparse
import os

import numpy as np
from PIL import Image

ORN = r"D:\DSH\knuckle_tools\ornament"
BAKE = r"D:\DSH\knuckle_tools\bake_out"
OUT = r"D:\DSH\knuckle_tools\weapon_tex"

# style -> (base brass/steel colour, accent on high points, metallic, base roughness)
# how much the highlight end is allowed to lift the base colour (1.0 = old behaviour)
ACCENT_WEIGHT = {
    "steel_dark": 0.28,      # black iron: highlights must stay dark
    "frost_silver": 0.62,
}

PALETTE = {
    "brass_filigree": ((0.66, 0.44, 0.14), (0.93, 0.76, 0.38), 1.0, 0.30),
    "frost_ribs":     ((0.13, 0.30, 0.50), (0.55, 0.78, 0.95), 1.0, 0.24),
    "spike_studs":    ((0.17, 0.17, 0.19), (0.62, 0.63, 0.66), 1.0, 0.35),
    # 钢刺：黑铁 + 蓝色符文辉光（参考图 钢刺.png）
    "steel_dark":     ((0.006, 0.007, 0.009), (0.042, 0.085, 0.175), 1.0, 0.46),
    # 寒霜：银白 + 冰蓝雕纹（参考图 寒霜.png）
    "frost_silver":   ((0.38, 0.44, 0.54), (0.88, 0.95, 1.00), 1.0, 0.20),
}


def load(path, mode="RGB"):
    if not os.path.isfile(path):
        raise SystemExit("missing %s" % path)
    return np.array(Image.open(path).convert(mode), dtype=np.float32) / 255.0


def resize(a, res):
    if a.shape[0] == res and a.shape[1] == res:
        return a
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    im = im.resize((res, res), Image.LANCZOS)
    return np.array(im, dtype=np.float32) / 255.0


def blur(a, passes=2):
    out = a.copy()
    for _ in range(passes):
        out[1:-1, 1:-1] = (out[1:-1, 1:-1] * 0.36
                           + out[:-2, 1:-1] * 0.16 + out[2:, 1:-1] * 0.16
                           + out[1:-1, :-2] * 0.16 + out[1:-1, 2:] * 0.16)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--style", default="brass_filigree")
    ap.add_argument("--res", type=int, default=1024)
    ap.add_argument("--ao", default=None, help="override baked AO path")
    ap.add_argument("--pattern", default=None, help="ornament pattern to reuse (default: same as style)")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    base, accent, metallic, rough = PALETTE[a.style]
    accent_w = ACCENT_WEIGHT.get(a.style, 0.55)

    pat = a.pattern or a.style
    h_path = os.path.join(ORN, "%s_height.png" % pat)
    H = resize(load(h_path, "L"), a.res)
    H = blur(H, 1)                                  # engraving, not stencil

    ao_path = a.ao or os.path.join(BAKE, "%s_ao.png" % a.style)
    AO = resize(load(ao_path, "L"), a.res) if os.path.isfile(ao_path) else np.ones_like(H)
    AO = np.clip((AO - AO.min()) / max(1e-6, AO.max() - AO.min()), 0, 1)
    AO = 0.35 + 0.65 * AO                           # never fully black

    # grooves come from the BAKED AO (a geometric quantity -> coherent under any UV),
    # a light filigree component only breaks up the flat areas
    fil = np.clip(1.0 - H, 0, 1) ** 1.6
    groove = np.clip(0.55 * (1.0 - AO) + 0.45 * fil, 0, 1)
    groove = blur(groove, 1)

    # ---- base colour: brass with darker grooves and cavity shading
    bm = np.zeros((a.res, a.res, 3), dtype=np.float32)
    for c in range(3):
        hi = accent[c]
        lo = base[c]
        val = lo * (1.0 - accent_w * groove) + hi * (accent_w * (1.0 - groove))
        bm[:, :, c] = np.clip(val * (0.45 + 0.55 * AO), 0, 1)
    # a hint of polish on the very high points
    polish = np.clip((H - 0.72) / 0.28, 0, 1) * 0.35
    for c in range(3):
        bm[:, :, c] = np.clip(bm[:, :, c] + polish * accent[c], 0, 1)

    # ---- EDGE WEAR -----------------------------------------------------------
    # Exposed surface = high ambient occlusion (nothing is blocking it). Real metal
    # rubs bright and smooth exactly there while the recesses stay dark and rough,
    # and it is cheap to derive because the AO is already geometric truth. This is
    # what stops the part from reading as uniformly cast polystyrene.
    wear = np.clip((AO - 0.72) / 0.28, 0, 1) ** 1.4
    wear = blur(wear, 1)
    for c in range(3):
        # lift the exposed edges toward a cool metallic highlight
        bm[:, :, c] = np.clip(bm[:, :, c] * (1.0 + 0.55 * wear) + 0.05 * wear, 0, 1)

    # ---- normal: the tileable filigree sheet
    # normal: the tileable filigree, blended 55% toward flat so it reads as surface
    # richness instead of noise once the UV islands scatter it
    nm_path = os.path.join(ORN, "%s_normal.png" % pat)
    NM = resize(load(nm_path, "RGB"), a.res)
    NM = 0.82 * NM + 0.18 * np.array([0.5, 0.5, 1.0], dtype=np.float32)

    # ---- physical: R roughness, G metallic, B cavity -------------------------
    pm = np.zeros((a.res, a.res, 3), dtype=np.float32)
    pm[:, :, 0] = np.clip(rough * 0.65 + groove * 0.42, 0, 1)   # grooves rougher
    pm[:, :, 0] = np.clip(pm[:, :, 0] * (1.0 - 0.62 * wear), 0.04, 1)   # worn = polished
    pm[:, :, 1] = metallic
    pm[:, :, 2] = np.clip(1.0 - AO, 0, 1)                       # cavity mask

    for name, arr, mode in (("BM", bm, "RGB"), ("NM", NM, "RGB"), ("PM", pm, "RGB")):
        p = os.path.join(OUT, "%s_%s.png" % (a.style, name))
        Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8), mode).save(p)
        print("  %-42s %8d B" % (os.path.basename(p), os.path.getsize(p)))

    print("style=%s res=%d  H[%.3f..%.3f] AO[%.3f..%.3f] groove_mean=%.3f" % (
        a.style, a.res, H.min(), H.max(), AO.min(), AO.max(), float(groove.mean())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

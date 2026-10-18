# -*- coding: utf-8 -*-
"""Flatten the baked lighting out of the look-dev textures.

The icon-driven generator samples the reference PNG per texel, and a reference render
carries its own specular streaks and shading gradients. Baked into BM/NM those read as
"brushed streaks" and "melted waves" on the in-game surface -- exactly what showed up on
brass_scroll (long horizontal streaks) and frost_icevein (washed grey, speckled edges).

Fix, per texture:

  BM  -- divide out the low-frequency luminance (gaussian sigma 48) with strength k.
         That removes the studio lighting gradient while keeping every fine detail
         (scroll lines, rune marks, edge wear).
  NM  -- low-pass the tangent tilt and mix the smooth part back toward flat, so the
         big waviness disappears but the fine embossing survives. Renormalised.
  GLOW -- untouched.

Per-style strength lives in STYLE below. Originals are backed up to *.prepolish.png
so this is reversible with one copy.

Run: python polish_textures.py            (all three)
     python polish_textures.py --style brass_scroll
"""
import argparse
import io
import os
import shutil

import numpy as np
from PIL import Image

TEX = r"D:\DSH\knuckle_tools\weapon_tex"

STYLE = {
    #            flat  nm_flat  sat   (flat/nm_flat are 0..1; sat multiplies chroma)
    "brass_scroll":  (0.88, 0.38, 1.00),
    "frost_icevein": (0.72, 0.30, 1.35),
    "steel_runeglow": (0.55, 0.24, 1.15),
}


def gauss(a, sigma):
    if sigma <= 0:
        return a
    r = max(1, int(round(2.2 * sigma)))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / float(sigma)) ** 2)
    k /= k.sum()
    out = a
    for axis in (0, 1):
        out = np.apply_along_axis(lambda m: np.convolve(m, k, mode="same"), axis, out)
    return out


def flatten_bm(rgb, k, sat):
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722])
    low = gauss(lum, 48.0)
    keep = low.mean()
    # divide out the low-frequency illumination ...
    gain = (keep / np.maximum(low, 1e-4)) ** k
    out = rgb * gain[..., None]
    # ... then restore the ORIGINAL overall level (dividing alone darkens everything,
    # because the icon's specular streaks are the bright part)
    for c in range(3):
        m0 = rgb[..., c]
        m1 = out[..., c]
        scale = float(m0.mean() / max(m1.mean(), 1e-5))
        out[..., c] = m1 * scale
    if sat != 1.0:
        g = out @ np.array([0.2126, 0.7152, 0.0722])
        out = g[..., None] + (out - g[..., None]) * sat
    return np.clip(out, 0.0, 1.0)


def flatten_nm(rgb, k):
    sm = np.stack([gauss(rgb[:, :, i], 24.0) for i in range(3)], axis=2)
    out = rgb * (1.0 - k) + sm * k
    # push ONLY the low-frequency part back toward the neutral normal (0.5, 0.5)
    a = 0.5 * k
    out[:, :, 0] = out[:, :, 0] * (1.0 - a) + 0.5 * a
    out[:, :, 1] = out[:, :, 1] * (1.0 - a) + 0.5 * a
    # rebuild Z from X,Y so the normal stays unit length
    vx = out[:, :, 0] * 2.0 - 1.0
    vy = out[:, :, 1] * 2.0 - 1.0
    vz = np.sqrt(np.clip(1.0 - vx ** 2 - vy ** 2, 0.0, 1.0))
    out[:, :, 2] = (vz + 1.0) * 0.5
    return np.clip(out, 0.0, 1.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--style", default=None)
    a = ap.parse_args()
    styles = [a.style] if a.style else list(STYLE)

    for st in styles:
        flat, nm_flat, sat = STYLE[st]
        for ch, fn in (("BM", lambda x: flatten_bm(x, flat, sat)),
                       ("NM", lambda x: flatten_nm(x, nm_flat))):
            p = os.path.join(TEX, "%s_%s.png" % (st, ch))
            if not os.path.isfile(p):
                print("  missing", p)
                continue
            bak = p + ".prepolish.png"
            if not os.path.isfile(bak):
                shutil.copyfile(p, bak)
            src = bak if os.path.isfile(bak) else p
            im = Image.open(src).convert("RGB")
            arr = np.asarray(im).astype(np.float32) / 255.0
            out = fn(arr)
            Image.fromarray((out * 255.0 + 0.5).astype(np.uint8), "RGB").save(p)
            lum = (out @ np.array([0.2126, 0.7152, 0.0722]))
            print("  %-32s mean=%.3f  p10=%.3f p90=%.3f" % (
                os.path.basename(p), lum.mean(), np.percentile(lum, 10), np.percentile(lum, 90)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
"""icon_texgen.py -- icon-driven knuckle texture generator (new file; does not touch make_textures.py)

WHY A SECOND GENERATOR
----------------------
make_textures.py composites "one base colour x bake AO x tileable scroll sheet".
That sheet has no relation to the model, so the whole part ends up one flat
grey/gold and the normal map carries a scroll pattern that belongs to no part.

This one uses the concept art as texture truth: every texel is projected back
into the icon, so the blue runes / ice tracery / brass scrollwork land exactly
where the reference puts them, and the normal map's relief is derived from the
same icon pixels (dark engraved line = groove). The base colour and the relief
therefore share one coordinate system.

COORDINATE CHAIN
----------------
texel --(UV rasteriser)--> 3D pos P / normal N --(fitted front projection)--> icon pixel

The projection is fitted by rendering the model's front silhouette (x,z) and
maximising IoU against the icon's object mask over rotation / scale / translation
/ mirror. Worst case ~2 s; it is deterministic.

OUTPUTS (4 maps per style, 1024^2)
----------------------------------
<style>_BM.png    base colour (sRGB)
<style>_NM.png    tangent-space normal (geometry normal + icon relief gradient)
<style>_PM.png    R = roughness, G = metallic, B = cavity
                  (R and B are DERIVED quantities, not authored inputs: B is the
                   bake AO inverted, R is a heuristical mix -- see comments)
<style>_GLOW.png  emissive mask (grayscale) -- feeds BG3 CHAR_BASE_GM's Glowmap slot

USAGE
-----
python icon_texgen.py --style steel_runeglow [--res 1024]
python icon_texgen.py --all
"""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image

ROOT = r"D:\DSH\knuckle_tools"
MODEL_DIR = os.path.join(ROOT, "model_out")
BAKE_DIR = os.path.join(ROOT, "bake_out")
ICON_DIR = os.path.join(ROOT, "icons_src")
TEX_OUT = os.path.join(ROOT, "weapon_tex")
PREV_OUT = os.path.join(ROOT, "preview", "lookdev")

# Style table. Colours are linear (engine BaseColor semantics).
#   base/wear : metal F0 and the bare metal exposed at worn edges
#   glow      : rune / ice-vein emission colour (Glowmap path, also baked partially
#               into BM as the degraded fallback when no emissive is available)
#   rough     : (base, worn edge, engraved groove)
STYLES = {
    "steel_runeglow": dict(
        obj="KD_Knuckles_SteelSpike",
        icon="KD_Item_Knuckle_Steel_Spike.png",
        base=(0.0135, 0.0145, 0.0170),      # near-black iron
        wear=(0.28, 0.29, 0.31),
        glow=(0.030, 0.180, 0.850),          # blue rune glow
        rough=(0.70, 0.40, 0.74),
        metallic=1.0, glow_metal=0.12, glow_rough=0.16,
        glow_amt=1.00, relief=0.00055, relief_rune=0.00170, normal_strength=1.00,
        glow_thr=0.038, glow_k=0.055, glow_hp=-0.020, glow_lummax=0.62,
        note="black iron + blue rune engraving (emissive via Glowmap)",
    ),
    "frost_icevein": dict(
        obj="KD_Knuckles_BoneChill",
        icon="KD_Item_Knuckle_Bone_Chill.png",
        base=(0.285, 0.375, 0.560),          # cold silver-blue
        wear=(0.90, 0.96, 1.00),
        glow=(0.030, 0.190, 0.950),          # ice blue, stronger
        rough=(0.30, 0.14, 0.42),
        metallic=1.0, glow_metal=0.25, glow_rough=0.12,
        glow_amt=1.00, relief=0.00070, relief_rune=0.00155, normal_strength=1.20,
        glow_thr=0.026, glow_k=0.060, glow_hp=-0.020, glow_lummax=0.95,
        note="silver metal + ice-blue tracery (frost highlights on rims and spikes)",
    ),
    "brass_scroll": dict(
        obj="KD_Knuckles_Unsharpened",
        icon="KD_Item_Knuckle_Unsharpened.png",
        base=(0.620, 0.375, 0.085),          # saturated brass
        wear=(1.000, 0.820, 0.450),
        glow=(0.0, 0.0, 0.0),                # no emission
        rough=(0.34, 0.22, 0.48),
        metallic=1.0, glow_metal=1.0, glow_rough=0.36,
        glow_amt=0.0, relief=0.00062, relief_rune=0.0, normal_strength=1.28,
        cord_suppress=0.92,
        glow_thr=9.0, glow_k=1.0, glow_hp=9.0, glow_lummax=0.0,
        note="brass/dark gold + scroll relief (recesses dark, ridges bright)",
    ),
}


def log(m):
    print("[lookdev] %s" % m)
    sys.stdout.flush()


# ---------------------------------------------------------------- OBJ / normals
def load_obj(path):
    verts, uvs, vns, faces, fuv, fnm = [], [], [], [], [], []
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            if line.startswith("v "):
                verts.append([float(x) for x in line.split()[1:4]])
            elif line.startswith("vt "):
                uvs.append([float(x) for x in line.split()[1:3]])
            elif line.startswith("vn "):
                vns.append([float(x) for x in line.split()[1:4]])
            elif line.startswith("f "):
                vi, ti, ni = [], [], []
                for p in line.split()[1:]:
                    c = p.split("/")
                    vi.append(int(c[0]) - 1)
                    ti.append(int(c[1]) - 1 if len(c) > 1 and c[1] else -1)
                    ni.append(int(c[2]) - 1 if len(c) > 2 and c[2] else -1)
                for k in range(1, len(vi) - 1):
                    faces.append([vi[0], vi[k], vi[k + 1]])
                    fuv.append([ti[0], ti[k], ti[k + 1]])
                    fnm.append([ni[0], ni[k], ni[k + 1]])
    V = np.asarray(verts, np.float64)
    UV = np.asarray(uvs, np.float64) if uvs else np.zeros((len(V), 2))
    Nv = np.asarray(vns, np.float64) if vns else None
    FN = np.asarray(fnm, np.int32) if vns else None
    return V, UV, Nv, np.asarray(faces, np.int32), np.asarray(fuv, np.int32), FN


def vertex_normals(V, F):
    N = np.zeros_like(V)
    n = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    for k in range(3):
        np.add.at(N, F[:, k], n)
    return N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)


# ------------------------------------------------------------- UV rasterisation
def raster_uv(V, UV, TUV, F, Nv, FN, res):
    """Rasterise the UV layout. Returns world pos, normal, dPdu, dPdv, coverage."""
    P = np.zeros((res, res, 3))
    N = np.zeros((res, res, 3))
    U = np.zeros((res, res, 3))
    W = np.zeros((res, res, 3))
    cov = np.zeros((res, res), bool)
    yy, xx = np.mgrid[0:res, 0:res]
    for t in range(len(TUV)):
        iuv = TUV[t]
        if (iuv < 0).any():
            continue
        tuv = UV[iuv]
        px = tuv[:, 0] * res
        py = (1.0 - tuv[:, 1]) * res
        x0 = max(int(np.floor(px.min())) - 1, 0)
        x1 = min(int(np.ceil(px.max())) + 1, res - 1)
        y0 = max(int(np.floor(py.min())) - 1, 0)
        y1 = min(int(np.ceil(py.max())) + 1, res - 1)
        if x1 < x0 or y1 < y0:
            continue
        den = (px[1] - px[0]) * (py[2] - py[0]) - (px[2] - px[0]) * (py[1] - py[0])
        if abs(den) < 1e-12:
            continue
        inv = 1.0 / den
        xs = xx[y0:y1 + 1, x0:x1 + 1] + 0.5
        ys = yy[y0:y1 + 1, x0:x1 + 1] + 0.5
        b1 = ((xs - px[0]) * (py[2] - py[0]) - (px[2] - px[0]) * (ys - py[0])) * inv
        b2 = ((px[1] - px[0]) * (ys - py[0]) - (xs - px[0]) * (py[1] - py[0])) * inv
        b0 = 1.0 - b1 - b2
        m = (b0 >= -1e-6) & (b1 >= -1e-6) & (b2 >= -1e-6)
        if not m.any():
            continue
        b0, b1, b2 = b0[m], b1[m], b2[m]
        sl = (slice(y0, y1 + 1), slice(x0, x1 + 1))
        pos = b0[:, None] * V[F[t, 0]] + b1[:, None] * V[F[t, 1]] + b2[:, None] * V[F[t, 2]]
        if FN is not None and (FN[t] >= 0).all():
            nn = (b0[:, None] * Nv[FN[t, 0]] + b1[:, None] * Nv[FN[t, 1]]
                  + b2[:, None] * Nv[FN[t, 2]])
        else:
            nv = vertex_normals(V, np.asarray([F[t]]))
            nn = b0[:, None] * nv[0] + b1[:, None] * nv[1] + b2[:, None] * nv[2]
        nn /= np.maximum(np.linalg.norm(nn, axis=1, keepdims=True), 1e-12)
        du1, du2 = tuv[1] - tuv[0], tuv[2] - tuv[0]
        dw1 = V[F[t, 1]] - V[F[t, 0]]
        dw2 = V[F[t, 2]] - V[F[t, 0]]
        det2 = du1[0] * du2[1] - du2[0] * du1[1]
        if abs(det2) < 1e-14:
            continue
        P[sl][m] = pos
        N[sl][m] = nn
        U[sl][m] = (dw1 * du2[1] - dw2 * du1[1]) / det2
        W[sl][m] = (dw2 * du1[0] - dw1 * du2[0]) / det2
        cv = cov[sl]
        cv[m] = True
        cov[sl] = cv
    return P, N, U, W, cov


def raster_mask_2d(pts2, tris, res, bbox=(0, 1, 0, 1)):
    """Binary silhouette of the mesh in a 2D plane (used for the alignment fit)."""
    x0b, x1b, y0b, y1b = bbox
    sx = (res - 1) / max(1e-9, x1b - x0b)
    sy = (res - 1) / max(1e-9, y1b - y0b)
    p = np.stack([(pts2[:, 0] - x0b) * sx, (y1b - pts2[:, 1]) * sy], 1)
    M = np.zeros((res, res), bool)
    yy, xx = np.mgrid[0:res, 0:res]
    for tri in tris:
        a, b, c = p[tri[0]], p[tri[1]], p[tri[2]]
        den = (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])
        if abs(den) < 1e-12:
            continue
        xa = max(int(np.floor(min(a[0], b[0], c[0]))), 0)
        xb = min(int(np.ceil(max(a[0], b[0], c[0]))) + 1, res - 1)
        ya = max(int(np.floor(min(a[1], b[1], c[1]))), 0)
        yb = min(int(np.ceil(max(a[1], b[1], c[1]))) + 1, res - 1)
        if xb < xa or yb < ya:
            continue
        xs = xx[ya:yb + 1, xa:xb + 1] + 0.5
        ys = yy[ya:yb + 1, xa:xb + 1] + 0.5
        inv = 1.0 / den
        b1 = ((xs - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (ys - a[1])) * inv
        b2 = ((b[0] - a[0]) * (ys - a[1]) - (xs - a[0]) * (b[1] - a[1])) * inv
        M[ya:yb + 1, xa:xb + 1] |= (1.0 - b1 - b2 >= 0) & (b1 >= 0) & (b2 >= 0)
    return M


# ---------------------------------------------------------------- small helpers
def bilinear(img, x, y):
    H, W = img.shape[:2]
    x = np.clip(x, 0, W - 1.001)
    y = np.clip(y, 0, H - 1.001)
    x0 = np.floor(x).astype(np.int32)
    y0 = np.floor(y).astype(np.int32)
    fx = x - x0
    fy = y - y0
    if img.ndim == 3:
        fx, fy = fx[..., None], fy[..., None]
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy)
            + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)


def gauss(a, sigma):
    """Separable Gaussian (edge padded). Cheap enough for 1k maps."""
    if sigma <= 0:
        return a
    r = max(1, int(round(2.2 * sigma)))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / max(1e-6, sigma)) ** 2)
    k /= k.sum()
    out = a
    for axis in (0, 1):
        pad = [(0, 0)] * out.ndim
        pad[axis] = (r, r)
        p = np.pad(out, pad, mode="edge")
        acc = np.zeros_like(out)
        for i, w in enumerate(k):
            sl = [slice(None)] * out.ndim
            sl[axis] = slice(i, i + out.shape[axis])
            acc += w * p[tuple(sl)]
        out = acc
    return out


def dilate_fill(rgb, mask, passes=10):
    """Fill outside the icon mask by nearest-neighbour diffusion (no white bleed)."""
    out = rgb.copy()
    m = mask.copy()
    for _ in range(passes):
        if m.all():
            break
        acc = np.zeros_like(out)
        cnt = np.zeros(m.shape)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            sp = np.roll(m, (dy, dx), (0, 1)).astype(np.float64)
            acc += np.roll(out, (dy, dx), (0, 1)) * (sp[..., None] if out.ndim == 3 else sp)
            cnt += sp
        new = (~m) & (cnt > 0)
        out[new] = acc[new] / cnt[new][:, None]
        m = m | new
    return out


# ---------------------------------------------------------------------- the icon
def load_icon(path, work=1024):
    """Crop the icon to its object, work at `work` px, build colour/relief/blue mask."""
    a = np.array(Image.open(path).convert("RGBA"), np.float64) / 255.0
    rgb, alpha = a[..., :3], a[..., 3]
    if alpha.min() < 0.99:
        mask = alpha > 0.5
    else:
        lum = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
        chroma = rgb.max(axis=2) - rgb.min(axis=2)
        mask = (lum < 0.955) | (chroma > 0.055)
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        raise SystemExit("icon mask empty: %s" % path)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    pad = int(0.04 * max(x1 - x0, y1 - y0))
    x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
    x1 = min(rgb.shape[1] - 1, x1 + pad)
    y1 = min(rgb.shape[0] - 1, y1 + pad)
    rgb, mask = rgb[y0:y1 + 1, x0:x1 + 1], mask[y0:y1 + 1, x0:x1 + 1]
    h, w = rgb.shape[:2]
    sc = work / max(h, w)
    nw, nh = max(2, int(round(w * sc))), max(2, int(round(h * sc)))
    rgb = np.array(Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8))
                   .resize((nw, nh), Image.LANCZOS), np.float64) / 255.0
    mask = np.array(Image.fromarray((mask * 255).astype(np.uint8))
                    .resize((nw, nh), Image.BILINEAR), np.float64) > 127
    filled = gauss(dilate_fill(rgb, mask, passes=12), 1.2)
    lum = 0.2126 * filled[..., 0] + 0.7152 * filled[..., 1] + 0.0722 * filled[..., 2]
    # Relief: dark engraved line = groove. Two high-pass bands, coarse block + fine
    # line. The fine band is pre-smoothed (sigma 0.8 px) because the icons carry
    # compression/paracord weave noise which would otherwise become foil wrinkles
    # once the gradient is scaled by the icon->world derivative.
    fine = gauss(lum, 0.8) - gauss(lum, 3.0)
    med = gauss(lum, 3.0) - gauss(lum, 9.0)
    # Unsharp the source first: the brass icon is only 380 px and gets upscaled
    # ~2.7x here, which otherwise turns every scroll into a soft blob.
    sharp = lum + 0.75 * (lum - gauss(lum, 1.6))
    hgt = -((gauss(sharp, 0.8) - gauss(sharp, 3.0)) * 1.30 + med * 0.45)
    inside = gauss(mask.astype(np.float64), 2.0)
    hgt = hgt * np.clip(inside * 1.4, 0, 1)
    nz = np.percentile(np.abs(hgt[mask]), 97) if mask.any() else 1.0
    hgt = np.clip(hgt / max(nz, 1e-6), -1.6, 1.6)
    blueness = filled[..., 2] - 0.5 * (filled[..., 0] + 0.6 * filled[..., 1])
    # Thin blue veins read as the *local* blue excess, not the absolute blue level:
    # the dark iron body is already slightly blue, so an absolute threshold floods
    # the part. High-passing the blue channel isolates the drawn lines.
    blue_hp = blueness - gauss(blueness, 7.0)
    # The drawn rune lines are ~1.5 texels wide at 1024/31% UV occupancy, so they
    # alias into dashes. A 1 px max-filter thickens them enough to survive the UV
    # down-sample as continuous veins (0.53 mm line -> ~2.5 texels).
    b = blue_hp
    for dy, dx in ((0, 1), (1, 0)):
        b = np.maximum(b, np.roll(np.roll(blue_hp, dy, 0), dx, 1))
    blue_hp = gauss(b, 0.55)
    # Engraved rune/vein groove field: the blue tracery is cut IN, so it gets its
    # own (deeper) groove so the relief reads even where luminance contrast is low.
    rune = np.clip(blue_hp / 0.075, 0, 1) * np.clip(inside * 1.5, 0, 1)
    rune = gauss(rune, 0.9)
    # Paracord detector (brass icon): the wrap is a desaturated, mid-dark band while
    # the brass body is strongly chromatic. The model's grip is a short coil, not a
    # full wrap, so projecting the wrap's weave as relief reads as melted rope --
    # the brass style suppresses relief there (colour is kept for continuity).
    mx_ = filled.max(axis=2)
    sat = np.where(mx_ > 1e-4, (mx_ - filled.min(axis=2)) / np.maximum(mx_, 1e-4), 0)
    cord = (sat < 0.42) & (lum < 0.58) & mask
    cord = gauss(cord.astype(np.float64), 2.5)
    cord = np.clip(cord * 1.6, 0, 1)
    return dict(rgb=filled, mask=mask, lum=lum, height=hgt, blueness=blueness,
                blue_hp=blue_hp, rune=rune, cord=cord, hp=lum - gauss(lum, 18.0),
                size=(nw, nh))


# --------------------------------------------------------------------- alignment
def fit_align(model_mask, icon_mask, verbose=True):
    """2x3 affine [mx,my] -> [ix,iy] (image array coords of both masks) by IoU.

    model_mask: 512^2 silhouette covering the model x-z box, aspect preserved
    """
    S = 256
    SS = 128                     # scoring resolution (soft masks = smoother objective)
    HSRC = float(model_mask.shape[0])
    icon_s = np.array(Image.fromarray((icon_mask * 255).astype(np.uint8))
                      .resize((S, S), Image.BILINEAR), np.float64) > 127
    icon_soft = np.array(Image.fromarray((icon_s * 255).astype(np.uint8))
                         .resize((SS, SS), Image.BILINEAR), np.float64) / 255.0
    src = Image.fromarray((model_mask * 255).astype(np.uint8))
    ys, xs = np.nonzero(icon_s)
    ib = (xs.min(), xs.max(), ys.min(), ys.max())
    ys2, xs2 = np.nonzero(model_mask)
    mw = (xs2.max() - xs2.min()) * S / HSRC
    mh = (ys2.max() - ys2.min()) * S / HSRC
    s0 = min((ib[1] - ib[0]) / max(mw, 1.0), (ib[3] - ib[2]) / max(mh, 1.0))

    def score_of(s, th, tx, ty, mir):
        """Binary silhouette IoU at S. (A soft L1 objective was tried and drifts to
        a smaller fit: it rewards shrinking away from the parts the icon does not
        have, e.g. the extra ice spikes on the frost icon.)"""
        c, sn = np.cos(th), np.sin(th)
        a, b, d, e = c * s, -sn * s, sn * s, c * s
        if mir:
            a, d = -a, -d
        det = a * e - b * d
        if abs(det) < 1e-9:
            return 0.0
        ia, ib_, id_, ie = e / det, -b / det, -d / det, a / det
        icx, icy = -(ia * tx + ib_ * ty), -(id_ * tx + ie * ty)
        k = HSRC / S
        out = src.transform((S, S), Image.AFFINE,
                            (ia * k, ib_ * k, icx * k, id_ * k, ie * k, icy * k),
                            resample=Image.BILINEAR)
        o = np.array(out, np.float64) / 255.0 > 0.5
        return np.logical_and(o, icon_s).sum() / max(np.logical_or(o, icon_s).sum(), 1)

    cx_i, cy_i = 0.5 * (ib[0] + ib[1]) / S, 0.5 * (ib[2] + ib[3]) / S
    best, best_mirror = (0.0, s0, 0.0, 0.0, 0.0), False
    # The icons are front views of these very parts, so the in-plane roll is small.
    # Search +-40deg only: a full 360 search happily locks onto a rotated blob that
    # covers the same area (found rot=-87deg for the brass icon, which is nonsense).
    angles = np.radians(np.arange(-40, 41, 5))
    for mir in (False, True):
        for s in [s0 * f for f in (0.84, 0.92, 1.0, 1.06, 1.13, 1.22)]:
            for th in angles:
                c, sn = np.cos(th), np.sin(th)
                a, b, d, e = c * s, -sn * s, sn * s, c * s
                if mir:
                    a, d = -a, -d
                for dx in (-0.05, 0.0, 0.05):
                    for dy in (-0.05, 0.0, 0.05):
                        tx = cx_i + dx - (a * 0.5 + b * 0.5)
                        ty = cy_i + dy - (d * 0.5 + e * 0.5)
                        v = score_of(s, th, tx, ty, mir)
                        if v > best[0]:
                            best, best_mirror = (v, s, th, tx, ty), mir
    sc, s, th, tx, ty = best
    for step in (0.02, 0.008):
        moved = True
        while moved:
            moved = False
            for ds, dth, dtx, dty in ((step, 0, 0, 0), (-step, 0, 0, 0), (0, step, 0, 0),
                                      (0, -step, 0, 0), (0, 0, step, 0), (0, 0, -step, 0),
                                      (0, 0, 0, step), (0, 0, 0, -step)):
                v = score_of(s + ds, th + dth, tx + dtx, ty + dty, best_mirror)
                if v > sc + 1e-5:
                    sc, s, th, tx, ty = v, s + ds, th + dth, tx + dtx, ty + dty
                    moved = True

    def iou_at(s, th, tx, ty, mir):
        c, sn = np.cos(th), np.sin(th)
        a, b, d, e = c * s, -sn * s, sn * s, c * s
        if mir:
            a, d = -a, -d
        det = a * e - b * d
        ia, ib_, id_, ie = e / det, -b / det, -d / det, a / det
        icx, icy = -(ia * tx + ib_ * ty), -(id_ * tx + ie * ty)
        k = HSRC / S
        out = src.transform((S, S), Image.AFFINE,
                            (ia * k, ib_ * k, icx * k, id_ * k, ie * k, icy * k),
                            resample=Image.BILINEAR)
        o = np.array(out, np.float64) / 255.0 > 0.5
        return np.logical_and(o, icon_s).sum() / max(np.logical_or(o, icon_s).sum(), 1)

    iou = iou_at(s, th, tx, ty, best_mirror)
    c, sn = np.cos(th), np.sin(th)
    a, b, d, e = c * s, -sn * s, sn * s, c * s
    if best_mirror:
        a, d = -a, -d
    if verbose:
        log("    align IoU=%.3f scale=%.3f rot=%.1fdeg mirror=%s" % (
            iou, s, np.degrees(th), best_mirror))
    return np.array([[a, b, tx], [d, e, ty]]), iou, dict(
        scale=float(s), rot_deg=float(np.degrees(th)), mirror=bool(best_mirror), iou=float(iou))


# ------------------------------------------------------------------------- build
def build(style, res=1024, use_icon=True, verbose=True):
    cfg = STYLES[style]
    obj, icon_name = cfg["obj"], cfg["icon"]
    V, UV, Nv, F, TUV, FN = load_obj(os.path.join(MODEL_DIR, obj + ".obj"))
    if verbose:
        log("== %s  -- %s" % (style, cfg["note"]))
        log("   %s  V=%d F=%d VT=%d" % (obj, len(V), len(F), len(UV)))

    P, N, dPdu, dPdv, cov = raster_uv(V, UV, TUV, F, Nv, FN, res)
    if verbose:
        log("   uv coverage %.1f%%" % (100.0 * cov.mean()))
    if not cov.any():
        raise SystemExit("UV raster empty")

    # ---- bake AO -> cavity -------------------------------------------------
    ao_path = os.path.join(BAKE_DIR, obj + "_ao.png")
    if os.path.isfile(ao_path):
        ao = np.array(Image.open(ao_path).convert("L").resize((res, res), Image.LANCZOS),
                      np.float64) / 255.0
        ao = gauss(ao, 1.5)
        lo, hi = np.percentile(ao[cov], 2), np.percentile(ao[cov], 98)
        ao = np.clip((ao - lo) / max(1e-6, hi - lo), 0, 1)
    else:
        ao = np.ones((res, res))
    # The baked AO is noisy at texel scale (low-sample bake). Wide blur feeds the
    # "bare metal on exposed edges" term; the sharper one only feeds cavity.
    ao_soft = gauss(ao, 7.0)
    ao_soft = np.clip(ao_soft / max(1e-6, np.percentile(ao_soft[cov], 90)) * 0.9, 0, 1)
    ao_s = np.clip(0.18 + 0.82 * ao, 0, 1)
    ao_s_soft = np.clip(0.18 + 0.82 * ao_soft, 0, 1)

    # ---- icon fit ----------------------------------------------------------
    icon, A, iou = None, None, 0.0
    if use_icon and os.path.isfile(os.path.join(ICON_DIR, icon_name)):
        icon = load_icon(os.path.join(ICON_DIR, icon_name), work=1024)
        IW, IH = icon["size"]
        x, z = V[:, 0], V[:, 2]
        S = max(x.max() - x.min(), z.max() - z.min())
        cx3, cz3 = 0.5 * (x.max() + x.min()), 0.5 * (z.max() + z.min())
        pts = np.stack([(x - cx3) / S + 0.5, (z - cz3) / S + 0.5], 1)
        front = raster_mask_2d(pts, F, 512)
        A, iou, _fit = fit_align(front, icon["mask"], verbose=verbose)
        icon["SZ"] = (S, cx3, cz3)
        icon["IJW"] = (IW, IH)
        icon["A"] = A
        # J = d(icon px, icon py) / d(world x, world z)
        #   mx = (x-cx)/S+0.5 , my = 0.5-(z-cz)/S
        J = np.array([[IW * A[0, 0] / S, -IW * A[0, 1] / S],
                      [IH * A[1, 0] / S, -IH * A[1, 1] / S]])
    else:
        log("   !! icon missing -- falling back to procedural")

    # ---- per-texel icon sampling ------------------------------------------
    col = np.zeros((res, res, 3))
    det = np.zeros((res, res))
    gxw = np.zeros((res, res))       # d(height)/dx  [m per m]
    gzw = np.zeros((res, res))
    glow = np.zeros((res, res))
    if icon is not None:
        S, cx3, cz3 = icon["SZ"]
        IW, IH = icon["IJW"]
        h = icon["height"]
        gpx, gpy = np.gradient(h, axis=1), np.gradient(h, axis=0)
        rn = icon["rune"]
        rpx, rpy = np.gradient(-rn, axis=1), np.gradient(-rn, axis=0)   # groove = down
        x, z = P[..., 0], P[..., 2]
        wf = np.clip(-N[..., 1], 0, 1)
        wb = np.clip(N[..., 1], 0, 1)
        ws = np.maximum(wf + wb, 1e-6)
        wf, wb = wf / ws, wb / ws

        def proj(xx, zz, mirror):
            mx = (xx - cx3) / S + 0.5
            if mirror:
                mx = 1.0 - mx
            my = 0.5 - (zz - cz3) / S
            return ((A[0, 0] * mx + A[0, 1] * my + A[0, 2]) * IW,
                    (A[1, 0] * mx + A[1, 1] * my + A[1, 2]) * IH)

        for mirror, w in ((False, wf), (True, wb)):
            if w.max() < 1e-4:
                continue
            qx, qy = proj(x, z, mirror)
            col += bilinear(icon["rgb"], qx, qy) * w[..., None]
            cm = bilinear(icon["cord"], qx, qy) * cfg.get("cord_suppress", 0.0)
            det += bilinear(h, qx, qy) * w * (1 - cm)
            gx_p, gy_p = bilinear(gpx, qx, qy), bilinear(gpy, qx, qy)
            if cm.any():
                gx_p = gx_p * (1 - cm)
                gy_p = gy_p * (1 - cm)
            sx = -1.0 if mirror else 1.0
            gxw += (gx_p * J[0, 0] + gy_p * J[1, 0]) * sx * w
            gzw += (gx_p * J[0, 1] + gy_p * J[1, 1]) * w
            # extra engraved rune groove (deeper than the luminance relief)
            rx_p = bilinear(rpx, qx, qy)
            ry_p = bilinear(rpy, qx, qy)
            gxw += (rx_p * J[0, 0] + ry_p * J[1, 0]) * sx * w * cfg["relief_rune"]
            gzw += (rx_p * J[0, 1] + ry_p * J[1, 1]) * w * cfg["relief_rune"]
            # rune / ice-vein mask: blue excess, on a fine bright line, not a blown
            # highlight. Thresholds come from measuring the icons (see report).
            bl = bilinear(icon["blue_hp"], qx, qy)
            hp = bilinear(icon["hp"], qx, qy)
            lm = bilinear(icon["lum"], qx, qy)
            g = np.clip((bl - cfg["glow_thr"]) / cfg["glow_k"], 0, 1)
            g *= np.clip((hp - cfg["glow_hp"]) / 0.04, 0, 1)
            g *= np.clip((cfg["glow_lummax"] - lm) / 0.12, 0, 1)
            glow += g * w
        det = np.clip(det, -2, 2)
        glow = np.clip(gauss(np.clip((glow - 0.15) / 0.70, 0, 1), 0.6), 0, 1)
        gxw *= cfg["relief"]
        gzw *= cfg["relief"]
    else:
        rng = np.random.default_rng(7)
        nz = gauss(rng.normal(size=(res, res)), 3.0)
        det = np.clip(nz / max(1e-6, np.abs(nz).max()), -1, 1)
        col[:] = np.array(cfg["base"])
        gxw = np.gradient(det * cfg["relief"], axis=1) * res
        gzw = np.gradient(det * cfg["relief"], axis=0) * res

    # ---- world-space normal perturbation ----------------------------------
    # Soft-clamp the slope: decimated UV islands are locally stretched, and a few
    # texels would otherwise carry 60-80 deg slopes that read as melted wax.
    gmag = np.sqrt(gxw * gxw + gzw * gzw)
    damp = 1.0 / (1.0 + (gmag / 1.60) ** 2)
    gxw *= damp
    gzw *= damp
    tang = np.stack([gxw, np.zeros_like(gxw), gzw], -1)
    tang -= (tang * N).sum(-1)[..., None] * N
    Np = N - cfg["normal_strength"] * tang
    Np /= np.maximum(np.linalg.norm(Np, axis=2, keepdims=True), 1e-12)

    # ---- tangent space -----------------------------------------------------
    T = dPdu - (dPdu * N).sum(-1)[..., None] * N
    T /= np.maximum(np.linalg.norm(T, axis=2, keepdims=True), 1e-12)
    Bc = np.cross(N, T) * np.sign((dPdv * np.cross(N, T)).sum(-1))[..., None]
    ts = np.stack([(Np * T).sum(-1), (Np * Bc).sum(-1), (Np * N).sum(-1)], -1)
    NM = np.clip(ts * 0.5 + 0.5, 0, 1)

    # ---- base colour -------------------------------------------------------
    lum_icon = 0.2126 * col[..., 0] + 0.7152 * col[..., 1] + 0.0722 * col[..., 2]
    lum_lf = gauss(lum_icon, 26.0)
    lum_lf /= max(1e-6, np.percentile(lum_lf[cov], 75))
    tone = np.clip((lum_lf - 0.55) * 0.18, -0.15, 0.16)
    detail = np.clip(lum_icon - gauss(lum_icon, 3.0), -1, 1)
    icon_hi = np.clip((lum_icon - 0.62) / 0.28, 0, 1)        # icon's bare-metal highlights

    # Exposed = convex, unoccluded metal that rubbed bright. Driven by the WIDE
    # AO only, so bake speckle does not turn into noise in the albedo.
    exposed = np.clip((ao_s_soft - 0.66) / 0.34, 0, 1) ** 1.7
    wearmask = np.clip(0.55 * exposed + 0.22 * icon_hi, 0, 1)
    cavity = 1.0 - ao_s
    groove = np.clip(-det, 0, 1) ** 0.85                     # icon dark line = groove
    ridge = np.clip(det, 0, 1)

    base, wear = np.array(cfg["base"]), np.array(cfg["wear"])
    glowc = np.array(cfg["glow"])
    alb = np.empty((res, res, 3))
    for c in range(3):
        v = base[c] * (1.0 + 0.35 * tone)
        v = v * (0.86 + 0.22 * detail)
        v = v * (1.0 - 0.45 * groove)
        v = v + (wear[c] - v) * (0.90 * wearmask)
        alb[..., c] = np.clip(v, 0, 1)
    gmix = (glow * cfg["glow_amt"])[..., None]
    alb = alb * (1 - gmix) + (glowc[None, None, :] * (0.55 + 0.9 * glow[..., None])) * gmix
    # soft cavity shading (AO), but never crush the runes
    alb *= (0.62 + 0.38 * ao_s_soft)[..., None] ** (1.0 - 0.65 * glow[..., None])
    alb = np.clip(alb, 0, 1)

    # ---- physical map: R roughness / G metallic / B cavity -----------------
    r_base = cfg["rough"][0]
    rough = np.full((res, res), r_base)
    rough = rough + 0.16 * groove - 0.30 * exposed * (r_base - 0.05) + 0.10 * cavity + 0.06 * detail
    rough = rough * (1 - glow) + cfg["glow_rough"] * glow
    rough = np.clip(rough, 0.04, 0.98)
    metal = cfg["metallic"] * (1 - glow) + cfg["glow_metal"] * glow
    PM = np.stack([rough, np.clip(metal, 0, 1), cavity], -1)

    # ---- gutter padding (UV islands grown 6 px) ---------------------------
    def pad(img, val):
        m = cov.copy()
        out = img.copy()
        for _ in range(6):
            if m.all():
                break
            acc = np.zeros_like(out)
            cnt = np.zeros((res, res))
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                sp = np.roll(m, (dy, dx), (0, 1))
                acc += np.roll(out, (dy, dx), (0, 1)) * (sp[..., None] if out.ndim == 3 else sp)
                cnt += sp
            new = (~m) & (cnt > 0)
            if out.ndim == 3:
                out[new] = acc[new] / cnt[new][:, None]
            else:
                out[new] = acc[new] / cnt[new]
            m = m | new
        out[~m] = np.asarray(val, np.float64)
        return out

    BM = pad(alb, 0.0)
    NM = pad(NM, np.array([0.5, 0.5, 1.0]))
    PM = pad(PM, np.array([0.5, 1.0, 0.0]))
    GLOW = pad(glow, 0.0)

    os.makedirs(TEX_OUT, exist_ok=True)
    out = {}
    for name, arr in (("BM", BM), ("NM", NM), ("PM", PM),
                      ("GLOW", np.repeat(GLOW[..., None], 3, 2))):
        p = os.path.join(TEX_OUT, "%s_%s.png" % (style, name))
        Image.fromarray((np.clip(arr, 0, 1) * 255).round().astype(np.uint8), "RGB").save(p)
        out[name] = p

    # ---- stats (valid texels only) ---------------------------------------
    m = cov
    lum_bm = 0.2126 * BM[..., 0] + 0.7152 * BM[..., 1] + 0.0722 * BM[..., 2]
    nstrength = np.linalg.norm(NM[..., :2][m] - 0.5, axis=-1) * 2.0
    stats = dict(
        style=style, res=res, triangles=int(len(F)), uv_coverage=round(float(m.mean()), 4),
        bm_mean=[round(float(BM[..., c][m].mean()), 4) for c in range(3)],
        bm_lum_mean=round(float(lum_bm[m].mean()), 4),
        bm_lum_p10=round(float(np.percentile(lum_bm[m], 10)), 4),
        bm_lum_p50=round(float(np.percentile(lum_bm[m], 50)), 4),
        bm_lum_p90=round(float(np.percentile(lum_bm[m], 90)), 4),
        nm_mean=[round(float(NM[..., c][m].mean()), 4) for c in range(3)],
        nm_strength_mean=round(float(nstrength.mean()), 4),
        nm_strength_p95=round(float(np.percentile(nstrength, 95)), 4),
        rough_min=round(float(np.percentile(PM[..., 0][m], 2)), 4),
        rough_max=round(float(np.percentile(PM[..., 0][m], 98)), 4),
        rough_mean=round(float(PM[..., 0][m].mean()), 4),
        metal_mean=round(float(PM[..., 1][m].mean()), 4),
        cavity_mean=round(float(PM[..., 2][m].mean()), 4),
        glow_coverage=round(float((glow[m] > 0.25).mean()), 4),
        relief_mm=round(cfg["relief"] * 1000, 3),
        align_iou=round(float(iou), 4),
    )
    if verbose:
        log("   BM mean=%s  lum p10/p50/p90=%.3f/%.3f/%.3f  NM str=%.3f  rough %.2f..%.2f  glow=%.2f%%"
            % (stats["bm_mean"], stats["bm_lum_p10"], stats["bm_lum_p50"], stats["bm_lum_p90"],
               stats["nm_strength_mean"], stats["rough_min"], stats["rough_max"],
               100 * stats["glow_coverage"]))
    data = dict(icon=icon, P=P, cov=cov, glow=glow, BM=BM, NM=NM, PM=PM, A=A, V=V)
    return out, stats, data


def contact_sheet(style, data, out_dir=PREV_OUT):
    """BM|NM|PM|GLOW strip plus an icon-projection QA image."""
    os.makedirs(out_dir, exist_ok=True)
    BM, NM, PM, glow = data["BM"], data["NM"], data["PM"], data["glow"]
    strip = np.concatenate([(np.clip(a, 0, 1) * 255).astype(np.uint8) for a in
                            (BM, NM, PM, np.repeat(glow[..., None], 3, 2))], axis=1)
    Image.fromarray(strip).save(os.path.join(out_dir, "%s_tex.png" % style))
    icon = data["icon"]
    if icon is None:
        return
    res = BM.shape[0]
    P, cov, A = data["P"], data["cov"], data["A"]
    S, cx3, cz3 = icon["SZ"]
    IW, IH = icon["IJW"]
    x, z = P[..., 0], P[..., 2]
    mx = (x - cx3) / S + 0.5
    my = 0.5 - (z - cz3) / S
    sx = np.round(mx * (res - 1)).astype(np.int32)
    sy = np.round(my * (res - 1)).astype(np.int32)
    ok = cov & (sx >= 0) & (sx < res) & (sy >= 0) & (sy < res)
    cc = bilinear(icon["rgb"], (A[0, 0] * mx + A[0, 1] * my + A[0, 2]) * IW,
                  (A[1, 0] * mx + A[1, 1] * my + A[1, 2]) * IH)
    front = np.zeros((res, res, 3))
    front[sy[ok], sx[ok]] = cc[ok]
    ic = np.array(Image.fromarray((np.clip(icon["rgb"], 0, 1) * 255).astype(np.uint8))
                  .resize((res, res), Image.LANCZOS), np.float64) / 255.0
    Image.fromarray((np.concatenate([front, ic], 1) * 255).astype(np.uint8)).save(
        os.path.join(out_dir, "%s_proj.png" % style))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--style", default="steel_runeglow")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--res", type=int, default=1024)
    ap.add_argument("--no-icon", action="store_true")
    ap.add_argument("--stats", default=os.path.join(PREV_OUT, "stats.json"))
    a = ap.parse_args()
    styles = list(STYLES) if a.all else [a.style]
    all_stats = {}
    for st in styles:
        if st not in STYLES:
            raise SystemExit("unknown style %s (have %s)" % (st, list(STYLES)))
        paths, stats, data = build(st, a.res, use_icon=not a.no_icon)
        contact_sheet(st, data)
        all_stats[st] = stats
        log("   wrote " + ", ".join(os.path.basename(p) for p in paths.values()))
    os.makedirs(os.path.dirname(a.stats), exist_ok=True)
    old = {}
    if os.path.isfile(a.stats):
        try:
            old = json.load(open(a.stats, "r", encoding="utf-8"))
        except Exception:
            old = {}
    old.update(all_stats)
    with open(a.stats, "w", encoding="utf-8") as fh:
        json.dump(old, fh, indent=2, ensure_ascii=False)
    print(json.dumps(all_stats, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

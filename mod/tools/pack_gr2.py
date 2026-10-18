# -*- coding: utf-8 -*-
"""Turn one of our meshes into a weapon GR2 by REUSING a vanilla weapon's DAE.

Why this exists (2026-10-17 evening, measured not guessed):
  A working vanilla weapon is a RIGID mesh.  `preprocessor Decompress` +
  `divine convert-model -i gr2 -o dae` on `WPN_HUM_Dagger_Bhaalist_A.GR2` shows:
      * no <library_controllers> / <skin> / <vertex_weights> at all
      * <instance_geometry> (not <instance_controller>)
      * bone tree  Dummy_<stem> -> Dummy_Sheath -> Dummy_Attachment -> Dummy_FX*,
        plus one extra JOINT named <stem>_Mesh that the geometry binds to
      * bone offsets  Sheath (0, .01878, -.05030)  Attachment local (0,0,.11830)
        => attachment world (0, .01878, .06800) -- which sits right in the middle
        of the dagger's 3.4 cm x 1.7 cm handle.  So Dummy_Attachment IS the grip.
  Our earlier model was a SKINNED mesh with every bone at identity, so the plate
  centre landed on the hand and the fist swallowed it.

So: keep the vanilla DAE's skeleton / rigid binding / materials verbatim, rename
the elements to ours, and drop our geometry into the LOD0 slot.

Coordinate mapping (verified by importing the vanilla DAE into Blender, where
Collada (x,y,z) arrives as Blender (x,-z,y)):
      collada = (Xb, Zb, -Yb) * SCALE + OFFSET
  with OFFSET = the attachment world position, so our grip ends up in the hand.
"""
import io
import math
import os
import re
import sys

TEMPLATE = r"D:\DSH\knuckle_tools\skeleton\dagger.dae"
TEMPLATE_STEM = "WPN_HUM_Dagger_Bhaalist_A"
OUT_DIR = r"D:\DSH\knuckle_tools\gr2_convert\v7"

# the vanilla dagger's attachment world position == the grip point
ATTACH_WORLD = (0.0, 0.018776, 0.068001)
SCALE = 1.0

# Fine position tuning without editing this file:
#     KD_OFF_X / KD_OFF_Y / KD_OFF_Z   metres, applied in GAME space after the map.
# Evidence for the rule itself (research_grip.py): measured on the vanilla dagger by
# cross-section roundness, the handle centre sits at z = +0.0710 while
# Dummy_Attachment is at +0.0680 -- 3 mm apart. So "grip centre == attachment" is
# the vanilla convention. A fist weapon's equivalent of the grip is the row of
# finger bores, which can legitimately sit a centimetre or two forward of the palm
# centre, hence these knobs.
OFF = tuple(float(os.environ.get("KD_OFF_" + ax, "0")) for ax in ("X", "Y", "Z"))


def log(m):
    print("[pack] %s" % m)
    sys.stdout.flush()


# --------------------------------------------------------------------------- obj
def read_obj(path):
    """Return (positions, normals, uvs) as per-corner lists (unwelded)."""
    verts, norms, texs = [], [], []
    corners = []          # (v_idx, vt_idx, vn_idx) per corner
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith("v "):
                verts.append(tuple(float(x) for x in line.split()[1:4]))
            elif line.startswith("vn "):
                norms.append(tuple(float(x) for x in line.split()[1:4]))
            elif line.startswith("vt "):
                parts = line.split()
                texs.append((float(parts[1]), float(parts[2])))
            elif line.startswith("f "):
                idx = []
                for tok in line.split()[1:]:
                    bits = tok.split("/")
                    vi = int(bits[0]) - 1
                    ti = int(bits[1]) - 1 if len(bits) > 1 and bits[1] else None
                    ni = int(bits[2]) - 1 if len(bits) > 2 and bits[2] else None
                    idx.append((vi, ti, ni))
                for k in range(1, len(idx) - 1):        # fan triangulation
                    corners.append(idx[0])
                    corners.append(idx[k])
                    corners.append(idx[k + 1])
    if not verts or not corners:
        raise SystemExit("empty obj: %s" % path)
    return verts, norms, texs, corners


def _rot_mode(name):
    """Which proper rotation to map the mesh with.

    The correct in-hand orientation of a fist weapon cannot be read out of the data
    (see D:\\DSH\\指虎-持握与骨骼绑定调研.md): the pose is not data-driven, so the only
    way to settle it is to see it on the character. To spend one game session instead
    of three, each weapon can be given a different candidate rotation:

        A  collada = (-z,  x, -y)   bore axis -> -Z   (the original baseline)
        B  collada = ( x,  z, -y)   same bore axis, plate turned a quarter turn
        C  collada = (-x, -z, -y)   bore axis flipped, plate turned the other way

    All three are proper rotations (det +1). Select with KD_ROT (applies to all) or
    KD_ROT_<SHORT> per weapon, where SHORT is STEEL / CHILL / GOLD. The default keeps
    the three-way test assignment so a single build answers the question.
    """
    short = ("STEEL" if "SteelSpike" in name
             else "CHILL" if "BoneChill" in name
             else "GOLD")
    mode = os.environ.get("KD_ROT_" + short) or os.environ.get("KD_ROT")
    if mode:
        return mode.upper()
    return "E"


def _tune(name):
    """Per-weapon fine tuning: (tilt degrees, drop metres, shift fraction of width).

    In-game feedback 2026-10-18: the gold weapon's tilt direction was right, so that
    sign is now used for all three and pushed 17 deg further (-42). After the roll the
    part also has to slide along its own GRIP -> STRIKING-END axis by 30% of its width,
    which is what finally puts the four bores on the fingers.

    knuckle width is the model's X span; the shift is applied in model space so it
    follows the roll instead of fighting it.
    """
    short = ("STEEL" if "SteelSpike" in name
             else "CHILL" if "BoneChill" in name
             else "GOLD")
    tilt = float(os.environ.get("KD_TILT_" + short) or os.environ.get("KD_TILT") or "-42")
    drop = float(os.environ.get("KD_DROP_" + short) or os.environ.get("KD_DROP") or "0.012")
    shift = float(os.environ.get("KD_SHIFT_" + short) or os.environ.get("KD_SHIFT") or "0.30")
    return tilt, drop, shift


def map_pos(p, mode="A", tilt=0.0, drop=0.0, shift=0.0):
    """Blender (X=hole row, Y=thickness/bore axis, Z=height) -> game space.

    Mode E was confirmed in game (2026-10-18): with it the four bores sit across the
    fingers and the part reads as worn rather than stuck into the palm. D turned out to
    be exactly 180 deg off E, so E is now the base for every weapon.

    tilt  -- degrees about the PALM-BAR axis, i.e. the line running along the row of
             bores (model X). In game space after mode E that axis is collada Z (the
             forward / blade direction), so the rotation is a roll of the part around
             the punch direction -- it changes which phalanx the four bores land on.
             An earlier build rotated about the BORE axis (collada Y) instead, which
             only spins the plate face and was invisible at 12 deg.
    drop  -- metres down (game -Z).
    """
    x, y, z = p
    # slide along the part's own grip -> striking-end axis BEFORE the roll,
    # so the offset follows the rotation instead of fighting it
    z += shift
    if mode == "D":
        cx, cy, cz = z, y, -x
    elif mode == "E":
        cx, cy, cz = -z, y, x
    elif mode == "B":
        cx, cy, cz = x, z, -y
    else:
        cx, cy, cz = -z, x, -y

    if tilt:
        a = math.radians(tilt)
        ca, sa = math.cos(a), math.sin(a)
        # rotate about collada Z (the palm-bar / bore-row axis in game space)
        cx, cy = cx * ca - cy * sa, cx * sa + cy * ca

    return (cx * SCALE + ATTACH_WORLD[0] + OFF[0],
            cy * SCALE + ATTACH_WORLD[1] + OFF[1],
            cz * SCALE + ATTACH_WORLD[2] + OFF[2] - drop)


def map_dir(d, mode="A"):
    x, y, z = d
    n = math.sqrt(x * x + y * y + z * z) or 1.0
    if mode == "D":
        cx, cy, cz = z, y, -x
    elif mode == "E":
        cx, cy, cz = -z, y, x
    elif mode == "B":
        cx, cy, cz = x, z, -y
    else:
        cx, cy, cz = -z, x, -y
    return (cx / n, cy / n, cz / n)


def build_arrays(obj_path, mode="A", tilt=0.0, drop=0.0, shift=0.0):
    verts, norms, texs, corners = read_obj(obj_path)
    pos, nor, tan, bit, uv = [], [], [], [], []
    tris = 0
    for c in range(0, len(corners), 3):
        tri = corners[c:c + 3]
        tris += 1
        # tangent / binormal from the UV derivatives of this triangle
        p0 = verts[tri[0][0]]
        p1 = verts[tri[1][0]]
        p2 = verts[tri[2][0]]
        uv0 = texs[tri[0][1]] if tri[0][1] is not None else (0.0, 0.0)
        uv1 = texs[tri[1][1]] if tri[1][1] is not None else (0.0, 0.0)
        uv2 = texs[tri[2][1]] if tri[2][1] is not None else (0.0, 0.0)
        e1 = [p1[i] - p0[i] for i in range(3)]
        e2 = [p2[i] - p0[i] for i in range(3)]
        d1 = (uv1[0] - uv0[0], uv1[1] - uv0[1])
        d2 = (uv2[0] - uv0[0], uv2[1] - uv0[1])
        det = d1[0] * d2[1] - d2[0] * d1[1]
        if abs(det) < 1e-12:
            t = (1.0, 0.0, 0.0)
        else:
            r = 1.0 / det
            t = tuple((e1[i] * d2[1] - e2[i] * d1[1]) * r for i in range(3))
        for (vi, vti, vni) in tri:
            pos.append(map_pos(verts[vi], mode, tilt, drop, shift))
            n = map_dir(norms[vni], mode) if (vni is not None and vni < len(norms)) else (0.0, 1.0, 0.0)
            nor.append(n)
            tv = map_dir(t, mode)
            # orthogonalise the tangent against the normal
            dot = sum(tv[i] * n[i] for i in range(3))
            tv = tuple(tv[i] - n[i] * dot for i in range(3))
            ln = math.sqrt(sum(x * x for x in tv)) or 1.0
            tv = tuple(x / ln for x in tv)
            tan.append(tv)
            b = (n[1] * tv[2] - n[2] * tv[1],
                 n[2] * tv[0] - n[0] * tv[2],
                 n[0] * tv[1] - n[1] * tv[0])
            bit.append(b)
            uv.append(texs[vti] if (vti is not None and vti < len(texs)) else (0.0, 0.0))
    return pos, nor, tan, bit, uv, tris


# ------------------------------------------------------------------ dae surgery
def flatten(values):
    return " ".join("%.6f" % v for v in values)


def replace_array(text, stem, suffix, count, body):
    """Replace <float_array id="<stem>-<suffix>-array" count="N"> ... </float_array>."""
    pat = re.compile(
        r'(<float_array id="%s-%s-array" count=")\d+(">)(.*?)(</float_array>)' % (re.escape(stem), suffix),
        re.S)
    new, n = pat.subn(lambda m: "%s%d%s%s%s" % (m.group(1), count, m.group(2), body, m.group(4)), text)
    if n != 1:
        raise SystemExit("could not patch %s array (%d matches)" % (suffix, n))
    return new


def replace_accessor_count(text, stem, suffix, count):
    pat = re.compile(r'(<accessor count=")\d+(" source="#%s-%s-array")' % (re.escape(stem), suffix))
    new, n = pat.subn(lambda m: "%s%d%s" % (m.group(1), count, m.group(2)), text)
    if n != 1:
        raise SystemExit("could not patch %s accessor (%d matches)" % (suffix, n))
    return new


def replace_triangles(text, tri_count, p_body):
    """Rewrite <triangles count="N" ...><input/><p>...</p> in one pass."""
    pat = re.compile(r'(<triangles count=")\d+("[^>]*>\s*(?:<input[^>]*/>\s*)*<p>)(.*?)(</p>)', re.S)
    new, n = pat.subn(lambda m: "%s%d%s%s%s" % (m.group(1), tri_count, m.group(2), p_body, m.group(4)),
                      text, count=1)
    if n != 1:
        raise SystemExit("could not patch <triangles> (%d matches)" % n)
    return new


def strip_lods(text):
    """Drop LOD1..LOD3 completely.

    The template's ids are '<stem>_Mesh_LOD1', '<stem>_Mesh_LOD1-geom',
    'Bone_<stem>_Mesh_LOD1' -- forgetting the '_Mesh' here silently leaves the
    DAGGER's LOD geometry in the file, and the game happily switches to it.
    """
    base = TEMPLATE_STEM + "_Mesh"
    for lod in ("_LOD1", "_LOD2", "_LOD3"):
        text = re.sub(r'\s*<geometry id="%s%s-geom".*?</geometry>' % (re.escape(base), lod),
                      "", text, flags=re.S)
        text = re.sub(r'\s*<node id="Bone_%s%s".*?</node>' % (re.escape(base), lod),
                      "", text, flags=re.S)
        text = re.sub(r'\s*<node id="%s%s".*?</node>' % (re.escape(base), lod),
                      "", text, flags=re.S)
    # the LOD extras that described the now-missing levels
    text = re.sub(r'\s*<LODDistance xmlns="">[^<]*</LODDistance>', "", text)
    text = re.sub(r'\s*<LOD xmlns="">[^<]*</LOD>', "", text)
    return text


def build_weapon(name, obj_path, out_dae):
    text = io.open(TEMPLATE, encoding="utf-8-sig").read()
    text = strip_lods(text)

    _tilt, _drop, _shift_frac = _tune(name)
    _verts = read_obj(obj_path)[0]
    _w = max(v[0] for v in _verts) - min(v[0] for v in _verts)
    _shift = _shift_frac * _w
    pos, nor, tan, bit, uv, tris = build_arrays(obj_path, _rot_mode(name), _tilt, _drop, _shift)
    log("%-26s %6d tris / %6d corners" % (name, tris, len(pos)))

    # rename every element of the template to ours
    text = text.replace(TEMPLATE_STEM, name)

    # geometry sources are named "<stem>_Mesh-positions" etc.
    mesh_stem = name + "_Mesh"

    # swap the LOD0 geometry payload (all arrays are per-corner / unwelded).
    # NOTE float_array@count counts FLOATS, accessor@count counts ITEMS.
    text = replace_array(text, mesh_stem, "positions", len(pos) * 3, flatten([c for p in pos for c in p]))
    text = replace_array(text, mesh_stem, "normals", len(nor) * 3, flatten([c for p in nor for c in p]))
    text = replace_array(text, mesh_stem, "tangents", len(tan) * 3, flatten([c for p in tan for c in p]))
    text = replace_array(text, mesh_stem, "binormals", len(bit) * 3, flatten([c for p in bit for c in p]))
    text = replace_array(text, mesh_stem, "uvs0", len(uv) * 2, flatten([c for p in uv for c in p]))
    for suffix, cnt in (("positions", len(pos)), ("normals", len(nor)), ("tangents", len(tan)),
                        ("binormals", len(bit)), ("uvs0", len(uv))):
        text = replace_accessor_count(text, mesh_stem, suffix, cnt)

    # <p>: every source is per-corner, so corner c uses index c in all five
    p_body = " ".join("%d %d %d %d %d" % (c, c, c, c, c) for c in range(len(pos)))
    text = replace_triangles(text, len(pos) // 3, p_body)

    io.open(out_dae, "w", encoding="utf-8", newline="\n").write(text)
    log("wrote %s  %d B" % (os.path.basename(out_dae), os.path.getsize(out_dae)))


def main():
    argv = sys.argv[1:]
    os.makedirs(OUT_DIR, exist_ok=True)
    targets = []
    if argv and argv[0] == "--all":
        targets = [
            ("KD_Knuckles_SteelSpike", os.path.join(r"D:\DSH\knuckle_tools\model_out", "KD_Knuckles_SteelSpike.obj")),
            ("KD_Knuckles_BoneChill", os.path.join(r"D:\DSH\knuckle_tools\model_out", "KD_Knuckles_BoneChill.obj")),
            ("KD_Knuckles_Unsharpened", os.path.join(r"D:\DSH\knuckle_tools\model_out", "KD_Knuckles_Unsharpened.obj")),
        ]
    elif len(argv) >= 2:
        targets = [(argv[0], argv[1])]
    else:
        raise SystemExit("usage: pack_gr2.py <name> <obj> | --all")

    for name, obj in targets:
        if not os.path.isfile(obj):
            raise SystemExit("missing obj: %s" % obj)
        build_weapon(name, obj, os.path.join(OUT_DIR, name + ".dae"))


if __name__ == "__main__":
    main()

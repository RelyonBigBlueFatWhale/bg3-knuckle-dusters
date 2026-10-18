# -*- coding: utf-8 -*-
"""Add an off-hand twin for each knuckle so both fists show one.

Why a second item instead of one two-handed item: the engine attaches ONE visual per
equipped weapon to the hand bone. A `Twohanded` weapon therefore shows one knuckle
gripped by both hands. The only way to see one on each fist is two items, which is also
how vanilla dual-wielded weapons work.

Chirality: a knuckle duster is not symmetric -- the palm bar must face the palm and the
striking face must point outward. Worn on the left hand the same mesh would have the bar
outward, so the twin is a MIRRORED copy (model X negated, winding flipped).

This script only writes NEW files / ADDITIVE dict entries; the in-service geometry and
the three existing weapons are untouched.

Run: python add_offhand_pair.py
"""
import io
import os
import re
import shutil
import uuid

TOOLS = r"D:\DSH\knuckle_tools"
MODEL = os.path.join(TOOLS, "model_out")
RES = (r"D:\DSH\knuckle_mod\Generated\Public\KnuckleDusters\Assets\Weapons\Humans"
       r"\KD_Knuckles_Unsharpened\Resources")
WV = os.path.join(TOOLS, "wire_visuals.py")
ROOT = r"D:\DSH\knuckle_mod\Public\KnuckleDusters\RootTemplates\_merged.lsx"
WEP = r"D:\DSH\knuckle_mod\Public\KnuckleDusters\Stats\Generated\Data\KD_1_Weapons.txt"
LUA = r"D:\DSH\knuckle_mod\Mods\KnuckleDusters\ScriptExtender\Lua\BootstrapServer.lua"

PAIRS = [
    # (gr2 stem, main stats name, off stats name, main template uuid)
    ("KD_Knuckles_SteelSpike", "KD_SteelSpikeFist", "KD_SteelSpikeFist_Off",
     "d6476755-6fb1-4752-91e4-a51ada4747da"),
    ("KD_Knuckles_BoneChill", "KD_BoneChill", "KD_BoneChill_Off",
     "94187658-a74c-4e44-a709-b3526ef1fbfd"),
    ("KD_Knuckles_Unsharpened", "KD_Unsharpened", "KD_Unsharpened_Off",
     "7e69ee66-6202-42b3-8e17-b587fd9a0276"),
]


def mirror_obj(src, dst):
    """Mirror across model X and flip winding so normals stay outward."""
    out = []
    for line in io.open(src, encoding="utf-8", errors="replace"):
        if line.startswith("v "):
            p = line.split()
            out.append("v %s %s %s\n" % (-float(p[1]), p[2], p[3]))
        elif line.startswith("vn "):
            p = line.split()
            out.append("vn %s %s %s\n" % (-float(p[1]), p[2], p[3]))
        elif line.startswith("f "):
            parts = line.split()[1:]
            out.append("f " + " ".join(reversed(parts)) + "\n")
        else:
            out.append(line)
    io.open(dst, "w", encoding="utf-8", newline="\n").write("".join(out))


def main():
    # 1) mirrored OBJs + duplicated DDS (the off visual gets its own material entry,
    #    so its texture resources point at *_Off.DDS copies)
    for stem, main_name, off_name, _ in PAIRS:
        src = os.path.join(MODEL, stem + ".obj")
        dst = os.path.join(MODEL, off_name.replace("KD_", "KD_Knuckles_", 1).replace(
            "_Off", "_Off") + ".obj")
        # stat names differ from the gr2 stems; derive the gr2 off stem explicitly
        off_stem = stem + "_Off"
        dst = os.path.join(MODEL, off_stem + ".obj")
        mirror_obj(src, dst)
        print("  mirrored -> %s (%d B)" % (os.path.basename(dst), os.path.getsize(dst)))
        for ch in ("BM", "NM", "PM", "GLOW"):
            s = os.path.join(RES, "%s_%s.DDS" % (stem, ch))
            d = os.path.join(RES, "%s_%s.DDS" % (off_stem, ch))
            if os.path.isfile(s):
                shutil.copyfile(s, d)

    # 2) wire_visuals: additive MATERIALS / VISUALS / BOUNDS entries
    s = io.open(WV, encoding="utf-8").read()
    if "KD_Knuckles_SteelSpike_Off" in s:
        print("  wire_visuals already carries the off entries, skipping")
    else:
        blocks = []
        for i, (stem, _, _, _) in enumerate(PAIRS, start=1):
            off = stem + "_Off"
            base = "f1f0a1b2-%02d" % i
            blocks.append(
                '    "%s": (\n'
                '        "%s01-4c3d-8e9f-bb0000000%d01",\n'
                '        ("%s02-4c3d-8e9f-bb0000000%d02", "%s03-4c3d-8e9f-bb0000000%d03",\n'
                '         "%s04-4c3d-8e9f-bb0000000%d04", "%s05-4c3d-8e9f-bb0000000%d05")),\n'
                % (off, base, i, base, i, base, i, base, i, base, i))
        s = s.replace("MATERIALS = {\n", "MATERIALS = {\n" + "".join(blocks), 1)

        vblocks, bblocks = [], []
        for i, (stem, main_name, off_name, _) in enumerate(PAIRS, start=1):
            off = stem + "_Off"
            vid = "a1f3c2e4-5b6d-4e7f-8a90-1b2c3d4e5f%02d" % (60 + i)
            vblocks.append('    "WPN_%s": ("%s", "%s"),\n' % (off_name, vid, off))
            bblocks.append('    "%s":   ((-0.15, -0.15, -0.15), (0.15, 0.15, 0.15)),\n' % off)
        s = s.replace("VISUALS = {\n", "VISUALS = {\n" + "".join(vblocks), 1)
        s = s.replace('    "KD_Knuckles_Unsharpened":  ((-0.14, -0.14, -0.14), (0.14, 0.14, 0.14)),\n',
                      '    "KD_Knuckles_Unsharpened":  ((-0.14, -0.14, -0.14), (0.14, 0.14, 0.14)),\n'
                      + "".join(bblocks), 1)
        io.open(WV, "w", encoding="utf-8", newline="\n").write(s)
        print("  wire_visuals: +3 MATERIALS, +3 VISUALS, +3 BOUNDS")

    # 3) root templates: one new GameObjects node per off weapon
    t = io.open(ROOT, encoding="utf-8-sig").read()
    if "_Off" in t:
        print("  root templates already carry the off entries, skipping")
    else:
        add = []
        for i, (stem, main_name, off_name, tmpl) in enumerate(PAIRS, start=1):
            vid = "a1f3c2e4-5b6d-4e7f-8a90-1b2c3d4e5f%02d" % (60 + i)
            mapkey = str(uuid.uuid5(uuid.NAMESPACE_DNS, off_name))
            add.append(
                '\t\t\t\t<node id="GameObjects">\n'
                '\t\t\t\t\t<attribute id="Description" type="TranslatedString" handle="hab8c030age971g4073gb037g1fc3c972dc60" version="1" />\n'
                '\t\t\t\t\t<attribute id="DisplayName" type="TranslatedString" handle="h5922721bg9243g4caegb9a1gdfe3ba0c0ad6" version="1" />\n'
                '\t\t\t\t\t<attribute id="EquipmentTypeID" type="guid" value="2d85d633-d496-44a1-a643-0e95ef879a6d" />\n'
                '\t\t\t\t\t<attribute id="Icon" type="FixedString" value="%s" />\n'
                '\t\t\t\t\t<attribute id="LevelName" type="FixedString" value="" />\n'
                '\t\t\t\t\t<attribute id="MapKey" type="FixedString" value="%s" />\n'
                '\t\t\t\t\t<attribute id="Name" type="LSString" value="%s" />\n'
                '\t\t\t\t\t<attribute id="ParentTemplateId" type="FixedString" value="569b0f3d-abcd-4b01-aaf0-979091288163" />\n'
                '\t\t\t\t\t<attribute id="PhysicsTemplate" type="FixedString" value="76fd694e-35c8-9109-0d8c-78bf8e107c76" />\n'
                '\t\t\t\t\t<attribute id="Stats" type="FixedString" value="%s" />\n'
                '\t\t\t\t\t<attribute id="Type" type="FixedString" value="item" />\n'
                '\t\t\t\t\t<attribute id="VisualTemplate" type="FixedString" value="%s" />\n'
                '\t\t\t\t</node>\n'
                % (os.path.basename(stem).replace("KD_Knuckles_", "KD_Item_Knuckle_") if False else
                   {"KD_Knuckles_SteelSpike": "KD_Item_Knuckle_Steel_Spike",
                    "KD_Knuckles_BoneChill": "KD_Item_Knuckle_Bone_Chill",
                    "KD_Knuckles_Unsharpened": "KD_Item_Knuckle_Unsharpened"}[stem],
                   mapkey, off_name, off_name, vid))
        t = t.replace("\t\t\t</children>", "".join(add) + "\t\t\t</children>", 1)
        io.open(ROOT, "w", encoding="utf-8", newline="\n").write(t)
        print("  root templates: +3 off entries")

    # 4) weapon stats: add the off twins, and drop NoDualWield so the pair can be worn
    w = io.open(WEP, encoding="utf-8").read()
    w = w.replace(";NoDualWield", "")
    if "_Off" not in w:
        add = []
        for stem, main_name, off_name, tmpl in PAIRS:
            m = re.search(r'(?ms)^new entry "%s"\r?\n(.*?)(?=\r?\nnew entry "|\Z)' % re.escape(main_name), w)
            if not m:
                print("  !! main stat not found:", main_name)
                continue
            body = m.group(1).rstrip()
            offbody = re.sub(r'(?m)^data "RootTemplate" "[^"]*"',
                             'data "RootTemplate" "%s"' % str(uuid.uuid5(uuid.NAMESPACE_DNS, off_name)), body)
            add.append('\nnew entry "%s"\n%s\n' % (off_name, offbody))
        w = w.rstrip() + "\n" + "".join(add)
        io.open(WEP, "w", encoding="utf-8", newline="\n").write(w)
        print("  weapon stats: +3 off entries, NoDualWield removed")

    # 5) console grant: give a pair
    lua = io.open(LUA, encoding="utf-8").read()
    if "_Off" not in lua:
        lua = lua.replace(
            '    { name = "KD_Unsharpened",    uuid = "7e69ee66-6202-42b3-8e17-b587fd9a0276",  label = "无锋 (Legendary)" },',
            '    { name = "KD_Unsharpened",    uuid = "7e69ee66-6202-42b3-8e17-b587fd9a0276",  label = "无锋 (Legendary)" },\n'
            '    { name = "KD_SteelSpikeFist_Off", uuid = "d6476755-6fb1-4752-91e4-a51ada4747da", label = "钢刺之拳·左手" },\n'
            '    { name = "KD_BoneChill_Off",  uuid = "94187658-a74c-4e44-a709-b3526ef1fbfd", label = "彻骨之寒·左手" },\n'
            '    { name = "KD_Unsharpened_Off", uuid = "7e69ee66-6202-42b3-8e17-b587fd9a0276", label = "无锋·左手" },')
        io.open(LUA, "w", encoding="utf-8", newline="\n").write(lua)
        print("  !kd now grants a pair")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

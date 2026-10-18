# -*- coding: utf-8 -*-
"""Wire the emissive material for the three knuckles.

Evidence (from the look-dev pass, which unpacked Materials.pak and checked all 244
templates for IsEmissiveMaterial):

  * CHAR_BASE.lsf      -> IsEmissiveMaterial=False, slots are only basecolor /
                          normalmap / physicalmap / MSKColor  => cannot glow.
  * CHAR_BASE_GM.lsf   -> IsEmissiveMaterial=True, same slots PLUS
                          Glowmap (texture), GlowMultiplier (scalar), GlowColor (fvec3).
  * Vanilla proves the wiring: WPN_HUM_Longbow_A_1_GM_Lightning's MaterialBank points at
    Base_GradientMapping_2G_GM_VT.lsf and carries GlowIntensity / glowmap.

So the change is: point SourceFile at CHAR_BASE_GM.lsf, add the three parameter
overrides, and register a GLOW texture per weapon. MaterialType goes 13 -> 4 to match
vanilla weapon materials (4 is what WPN_HUM_Glaive_A_2_Poison uses).

Per-weapon glow colour: steel = rune blue, frost = icy blue, gold = warm (its GLOW map
is fully black, so it simply does not emit).

Run: python wire_emissive_material.py
"""
import io
import re

P = r"D:\DSH\knuckle_tools\wire_visuals.py"

GLOW_IDS = {
    "KD_Knuckles_SteelSpike":   "d1f0a1b2-0106-4c3d-8e9f-aa0000000106",
    "KD_Knuckles_BoneChill":    "d1f0a1b2-0206-4c3d-8e9f-aa0000000206",
    "KD_Knuckles_Unsharpened":  "d1f0a1b2-0306-4c3d-8e9f-aa0000000306",
}
GLOW_RGB = {
    "KD_Knuckles_SteelSpike":   "0.10 0.38 1.00",
    "KD_Knuckles_BoneChill":    "0.45 0.80 1.00",
    "KD_Knuckles_Unsharpened":  "1.00 0.62 0.18",
}
MULT = "2.0"


def param_texture(pid, pname):
    return ('\t\t\t\t<node id="Texture2DParameters">\n'
            '\t\t\t\t\t<attribute id="Enabled" type="bool" value="True" />\n'
            '\t\t\t\t\t<attribute id="ExportAsPreset" type="bool" value="True" />\n'
            '\t\t\t\t\t<attribute id="GroupName" type="FixedString" value="01 Texture Map" />\n'
            '\t\t\t\t\t<attribute id="ID" type="FixedString" value="%s" />\n'
            '\t\t\t\t\t<attribute id="ParameterName" type="FixedString" value="%s" />\n'
            '\t\t\t\t\t<attribute id="UniformName" type="FixedString" value="Texture2DParameter_%s" />\n'
            '\t\t\t\t</node>\n' % (pid, pname, pname))


def param_scalar(pname, value):
    return ('\t\t\t\t<node id="ScalarParameters">\n'
            '\t\t\t\t\t<attribute id="BaseValue" type="float" value="1" />\n'
            '\t\t\t\t\t<attribute id="Enabled" type="bool" value="True" />\n'
            '\t\t\t\t\t<attribute id="ExportAsPreset" type="bool" value="True" />\n'
            '\t\t\t\t\t<attribute id="GroupName" type="FixedString" value="" />\n'
            '\t\t\t\t\t<attribute id="ParameterName" type="FixedString" value="%s" />\n'
            '\t\t\t\t\t<attribute id="Value" type="float" value="%s" />\n'
            '\t\t\t\t\t<attribute id="UniformName" type="FixedString" value="ScalarParameter_%s" />\n'
            '\t\t\t\t</node>\n' % (pname, value, pname))


def param_vec3(pname, rgb):
    return ('\t\t\t\t<node id="Vector3Parameters">\n'
            '\t\t\t\t\t<attribute id="BaseValue" type="fvec3" value="%s" />\n'
            '\t\t\t\t\t<attribute id="Enabled" type="bool" value="True" />\n'
            '\t\t\t\t\t<attribute id="ExportAsPreset" type="bool" value="True" />\n'
            '\t\t\t\t\t<attribute id="GroupName" type="FixedString" value="02 Colour" />\n'
            '\t\t\t\t\t<attribute id="IsColor" type="bool" value="True" />\n'
            '\t\t\t\t\t<attribute id="ParameterName" type="FixedString" value="%s" />\n'
            '\t\t\t\t\t<attribute id="Value" type="fvec3" value="%s" />\n'
            '\t\t\t\t\t<attribute id="UniformName" type="FixedString" value="Vector3Parameter_%s" />\n'
            '\t\t\t\t</node>\n' % (rgb, pname, rgb, pname))


def main():
    s = io.open(P, encoding="utf-8").read()

    # --- 1) GLOW ids into the MATERIALS table -----------------------------
    if "GLOW_IDS" not in s:
        s = s.replace(
            "TEX_DIR = ",
            "GLOW_IDS = " + repr(GLOW_IDS) + "\n"
            "GLOW_RGB = " + repr(GLOW_RGB) + "\n"
            "GLOW_MULT = %r\n\nTEX_DIR = " % MULT)

    # --- 2) material region: GM template + glow params ---------------------
    old_mat = re.search(r'(?ms)def _material_region\(\):.*?return "".join\(t\)\n', s).group(0)
    new_mat = '''def _material_region():
    """Emissive material: CHAR_BASE cannot glow, CHAR_BASE_GM can.

    CHAR_BASE_GM adds three parameters on top of the normal four texture slots:
    Glowmap (texture), GlowMultiplier (scalar), GlowColor (fvec3). Vanilla magic
    weapons wire exactly this (WPN_HUM_Longbow_A_1_GM_Lightning). MaterialType 4 is
    what vanilla weapon materials use.
    """
    t = ['<region id="MaterialBank">\\n', '\\t<node id="MaterialBank">\\n', '\\t\\t<children>\\n']
    for stem, (mid, tids) in MATERIALS.items():
        glow_id = GLOW_IDS[stem]
        t += ['\\t\\t\\t<node id="Resource">\\n',
              '\\t\\t\\t\\t<attribute id="DiffusionProfileUUID" type="FixedString" value="" />\\n',
              '\\t\\t\\t\\t<attribute id="ID" type="FixedString" value="%s" />\\n' % mid,
              '\\t\\t\\t\\t<attribute id="MaterialType" type="uint8" value="4" />\\n',
              '\\t\\t\\t\\t<attribute id="Name" type="LSString" value="%s_Material" />\\n' % stem,
              '\\t\\t\\t\\t<attribute id="SourceFile" type="LSString" value="Public/Shared/Assets/Materials/Characters/CHAR_BASE_GM.lsf" />\\n',
              '\\t\\t\\t\\t<children>\\n']
        for pid, pname in zip(tids, ("basecolor", "normalmap", "physicalmap", "MSKColor")):
            t.append(_tex_param(pid, pname))
        t.append(param_texture(glow_id, "Glowmap"))
        t.append(param_scalar("GlowMultiplier", GLOW_MULT))
        t.append(param_vec3("GlowColor", GLOW_RGB[stem]))
        t += ['\\t\\t\\t\\t</children>\\n', '\\t\\t\\t</node>\\n']
    t += ['\\t\\t</children>\\n', '\\t</node>\\n', '</region>\\n']
    return "".join(t)
'''
    s = s.replace(old_mat, new_mat)

    # --- 3) texture region: add the GLOW resource -------------------------
    s = s.replace(
        '        t.append(_tex_res(msk, "%s_MSK" % stem, "%s_BM.DDS" % stem, False))',
        '        t.append(_tex_res(msk, "%s_MSK" % stem, "%s_BM.DDS" % stem, False))\n'
        '        # glow map: black everywhere except the runes; SRGB False (it is a mask)\n'
        '        t.append(_tex_res(GLOW_IDS[stem], "%s_GLOW" % stem, "%s_GLOW.DDS" % stem, False))')

    io.open(P, "w", encoding="utf-8", newline="\n").write(s)
    import ast
    ast.parse(s)
    print("wire_visuals.py patched: GM template + Glowmap/GlowMultiplier/GlowColor + GLOW texture row")
    print("glow ids:", GLOW_IDS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

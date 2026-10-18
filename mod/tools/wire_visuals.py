# -*- coding: utf-8 -*-
"""把三套指虎网格接进 BG3 的武器视觉库（VisualBank）。

照抄的原版样本（Shared.pak: Public/Shared/Content/Assets/Weapons/[PAK]_Humans/_merged.lsf 的 VisualBank 区）：
    Resource{ ID, Name, SourceFile=<GR2>, Template=<无扩展名>.Dummy_<GR2名>.0,
              MaterialType=0, Slot=Unassigned, Radius, BoundsMin/Max/Center,
              Objects[{LOD, MaterialID, ObjectID=<GR2名>.<GR2名>_Mesh.0}] }
材质先用原版匕首的 MaterialID（必定可解析）—— 先保"看得见"，再谈换金属。

本脚本做四件事：
  1) 写 Public/KnuckleDusters/Content/Assets/Weapons/[PAK]_Humans/_merged.lsx
  2) 给 gen_knuckles.py 打补丁：视觉模板从"单一匕首 UUID"改为"按武器映射"
  3) 跑 gen_knuckles.py 重新生成 stats / 根模板
  4) 给 build.ps1 插入一步：打包前把这张 bank 的 lsx 转成 lsf
"""
import io
import os
import re
import subprocess
import sys

KNUCKLE = r"D:\DSH\knuckle_mod"
PUB = os.path.join(KNUCKLE, "Public", "KnuckleDusters")
TOOLS = r"D:\DSH\knuckle_tools"
DIVINE = r"D:\Tools\LSLib\Divine.exe"

# 网格对象名后缀。2026-10-17 晚用 `preprocessor Decompress` 读通了两组对照：
#   原版 WPN_HUM_Dagger_Bhaalist_A.GR2 / WPN_HUM_Sun_Mace_A.GR2 内部是
#       Dummy_<stem>  ->  Dummy_Sheath  ->  Dummy_Attachment  ->  [Dummy_FX*, 网格]
#       网格名 = <stem>_Mesh（LOD 依次 _Mesh_LOD1/_Mesh_LOD2）
#   而我们旧产物只有 Root + Dummy_Attachment（缺 Dummy_<stem> 与 Dummy_Sheath），
#   于是 Template / ObjectID 指向了**根本不存在的节点** —— 装备上、姿势对、手上空。
# ⇒ build_v4.py 现在按原版结构建骨骼，网格命名也对齐 <stem>_Mesh。
OBJ_SUFFIX = os.environ.get("KD_OBJ_SUFFIX", "_Mesh")

# 三件武器各有自己的材质与四张贴图（黑铁符文 / 银白冰纹 / 黄铜浮雕）。
# 2026-10-17 实证：VisualTemplate 指向能显示的 GR2 并配这套材质 → 手上出现模型，
# 说明材质库/贴图库/路径/UUID 解析全部有效。
# 现在三表由本脚本一起生成 —— 历史上只写 VisualBank 会把手加的另两张表整片冲掉。
MATERIALS = {
    # GR2 stem: (material uuid, (BM, NM, PM, MSK) uuids)
    "KD_Knuckles_SteelSpike": (
        "d1f0a1b2-0101-4c3d-8e9f-aa0000000101",
        ("d1f0a1b2-0102-4c3d-8e9f-aa0000000102", "d1f0a1b2-0103-4c3d-8e9f-aa0000000103",
         "d1f0a1b2-0104-4c3d-8e9f-aa0000000104", "d1f0a1b2-0105-4c3d-8e9f-aa0000000105")),
    "KD_Knuckles_BoneChill": (
        "d1f0a1b2-0201-4c3d-8e9f-aa0000000201",
        ("d1f0a1b2-0202-4c3d-8e9f-aa0000000202", "d1f0a1b2-0203-4c3d-8e9f-aa0000000203",
         "d1f0a1b2-0204-4c3d-8e9f-aa0000000204", "d1f0a1b2-0205-4c3d-8e9f-aa0000000205")),
    "KD_Knuckles_Unsharpened": (
        "d1f0a1b2-0301-4c3d-8e9f-aa0000000301",
        ("d1f0a1b2-0302-4c3d-8e9f-aa0000000302", "d1f0a1b2-0303-4c3d-8e9f-aa0000000303",
         "d1f0a1b2-0304-4c3d-8e9f-aa0000000304", "d1f0a1b2-0305-4c3d-8e9f-aa0000000305")),
    # left-hand twins: mirrored meshes with their own material + their own DDS copies,
    # so the whole pipeline stays identical to the right-hand entries.
    "KD_Knuckles_SteelSpike_Off": (
        "f1f0a1b2-0101-4c3d-8e9f-bb0000000101",
        ("f1f0a1b2-0102-4c3d-8e9f-bb0000000102", "f1f0a1b2-0103-4c3d-8e9f-bb0000000103",
         "f1f0a1b2-0104-4c3d-8e9f-bb0000000104", "f1f0a1b2-0105-4c3d-8e9f-bb0000000105")),
    "KD_Knuckles_BoneChill_Off": (
        "f1f0a1b2-0201-4c3d-8e9f-bb0000000201",
        ("f1f0a1b2-0202-4c3d-8e9f-bb0000000202", "f1f0a1b2-0203-4c3d-8e9f-bb0000000203",
         "f1f0a1b2-0204-4c3d-8e9f-bb0000000204", "f1f0a1b2-0205-4c3d-8e9f-bb0000000205")),
    "KD_Knuckles_Unsharpened_Off": (
        "f1f0a1b2-0301-4c3d-8e9f-bb0000000301",
        ("f1f0a1b2-0302-4c3d-8e9f-bb0000000302", "f1f0a1b2-0303-4c3d-8e9f-bb0000000303",
         "f1f0a1b2-0304-4c3d-8e9f-bb0000000304", "f1f0a1b2-0305-4c3d-8e9f-bb0000000305")),
}
GLOW_IDS = {'KD_Knuckles_SteelSpike': 'd1f0a1b2-0106-4c3d-8e9f-aa0000000106', 'KD_Knuckles_BoneChill': 'd1f0a1b2-0206-4c3d-8e9f-aa0000000206', 'KD_Knuckles_Unsharpened': 'd1f0a1b2-0306-4c3d-8e9f-aa0000000306',
            'KD_Knuckles_SteelSpike_Off': 'f1f0a1b2-0106-4c3d-8e9f-bb0000000106', 'KD_Knuckles_BoneChill_Off': 'f1f0a1b2-0206-4c3d-8e9f-bb0000000206', 'KD_Knuckles_Unsharpened_Off': 'f1f0a1b2-0306-4c3d-8e9f-bb0000000306'}
GLOW_RGB = {'KD_Knuckles_SteelSpike': '0.10 0.38 1.00', 'KD_Knuckles_BoneChill': '0.45 0.80 1.00', 'KD_Knuckles_Unsharpened': '1.00 0.62 0.18',
            'KD_Knuckles_SteelSpike_Off': '0.10 0.38 1.00', 'KD_Knuckles_BoneChill_Off': '0.45 0.80 1.00', 'KD_Knuckles_Unsharpened_Off': '1.00 0.62 0.18'}
GLOW_MULT = '2.0'

TEX_DIR = "Generated/Public/KnuckleDusters/Assets/Weapons/Humans/KD_Knuckles_Unsharpened/Resources"

ORIG_FILE_VERSION = "144115203108241409"

MODELS_DIR = "Generated/Public/KnuckleDusters/Assets/Weapons/Humans/KD_Knuckles_Unsharpened/Resources"

# 物品名 -> (视觉 UUID, GR2 基名)
VISUALS = {
    "WPN_KD_SteelSpikeFist": ("a1f3c2e4-5b6d-4e7f-8a90-1b2c3d4e5f60", "KD_Knuckles_SteelSpike"),
    "WPN_KD_BoneChill":      ("b2e4d3f5-6c7e-4f80-9ab1-2c3d4e5f6071", "KD_Knuckles_BoneChill"),
    "WPN_KD_Unsharpened":    ("c3f5e406-7d8f-4081-abc2-3d4e5f607182", "KD_Knuckles_Unsharpened"),
    "WPN_KD_SteelSpikeFist_Off": ("a1f3c2e4-5b6d-4e7f-8a90-1b2c3d4e5f61", "KD_Knuckles_SteelSpike_Off"),
    "WPN_KD_BoneChill_Off":      ("a1f3c2e4-5b6d-4e7f-8a90-1b2c3d4e5f62", "KD_Knuckles_BoneChill_Off"),
    "WPN_KD_Unsharpened_Off":    ("a1f3c2e4-5b6d-4e7f-8a90-1b2c3d4e5f63", "KD_Knuckles_Unsharpened_Off"),
}

# 网格实际尺寸（米，Blender 里建的就是这个尺寸）：0.12 x 0.026 x 0.075
# 包围体给足余量，避免被视锥剔除；真进了游戏再按观感微调。
BOUNDS = {
    "KD_Knuckles_SteelSpike":   ((-0.15, -0.15, -0.15), (0.15, 0.15, 0.15)),
    "KD_Knuckles_BoneChill":    ((-0.15, -0.15, -0.15), (0.15, 0.15, 0.15)),
    "KD_Knuckles_Unsharpened":  ((-0.14, -0.14, -0.14), (0.14, 0.14, 0.14)),
    "KD_Knuckles_SteelSpike_Off":   ((-0.15, -0.15, -0.15), (0.15, 0.15, 0.15)),
    "KD_Knuckles_BoneChill_Off":    ((-0.15, -0.15, -0.15), (0.15, 0.15, 0.15)),
    "KD_Knuckles_Unsharpened_Off":  ((-0.15, -0.15, -0.15), (0.15, 0.15, 0.15)),
}

HEADER = '<?xml version="1.0" encoding="utf-8"?>\n<save>\n' \
         '\t<version major="4" minor="0" revision="6" build="5" lslib_meta="v1,bswap_guids" />\n'


def log(m):
    print(m)
    sys.stdout.flush()


def write(path, text):
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    io.open(path, "w", encoding="utf-8", newline="\n").write(text)
    log("  wrote %-72s %6d B" % (os.path.relpath(path, KNUCKLE), len(text.encode("utf-8"))))


def build_bank():
    t = [HEADER, '\t<region id="VisualBank">\n', '\t\t<node id="VisualBank">\n', '\t\t\t<children>\n']
    for item, (uuid, gr2) in VISUALS.items():
        src = "%s/%s.gr2" % (MODELS_DIR, gr2)
        # Template = <SourceFile 去扩展名>.Dummy_<stem>.0
        #   原版两条互证：...WPN_HUM_Cannon_A.Dummy_WPN_HUM_Cannon_A.0、匕首同构
        #   → 必须指向 GR2 骨骼树的根节点 Dummy_<stem>，而不是网格名
        templ = "%s.Dummy_%s.0" % (src[:-4], gr2)
        bmin, bmax = BOUNDS[gr2]
        radius = round(max(abs(v) for v in list(bmin) + list(bmax)), 4)
        t.append('\t\t\t\t<node id="Resource">\n')
        for k, v in (("AttachBone", ""), ("AttachmentSkeletonResource", ""),
                     ("BlueprintInstanceResourceID", "")):
            t.append('\t\t\t\t\t<attribute id="%s" type="FixedString" value="%s" />\n' % (k, v))
        t.append('\t\t\t\t\t<attribute id="BoundsMax" type="fvec3" value="%s" />\n' % " ".join(str(x) for x in bmax))
        t.append('\t\t\t\t\t<attribute id="BoundsMin" type="fvec3" value="%s" />\n' % " ".join(str(x) for x in bmin))
        t.append('\t\t\t\t\t<attribute id="Center" type="fvec3" value="0 0 0" />\n')
        t.append('\t\t\t\t\t<attribute id="ClothColliderResourceID" type="FixedString" value="" />\n')
        t.append('\t\t\t\t\t<attribute id="HairPresetResourceId" type="FixedString" value="" />\n')
        t.append('\t\t\t\t\t<attribute id="HairType" type="uint8" value="0" />\n')
        t.append('\t\t\t\t\t<attribute id="ID" type="FixedString" value="%s" />\n' % uuid)
        t.append('\t\t\t\t\t<attribute id="Initialized" type="bool" value="True" />\n')
        t.append('\t\t\t\t\t<attribute id="Localized" type="bool" value="False" />\n')
        # vanilla weapon visuals use MaterialType=4 (read out of Shared.pak's
        # [PAK]_Humans bank, record WPN_HUM_Glaive_A_2_Poison); 0 was our guess
        t.append('\t\t\t\t\t<attribute id="MaterialType" type="uint8" value="4" />\n')
        t.append('\t\t\t\t\t<attribute id="Name" type="LSString" value="%s" />\n' % gr2)
        t.append('\t\t\t\t\t<attribute id="NeedsSkeletonRemap" type="bool" value="False" />\n')
        t.append('\t\t\t\t\t<attribute id="Radius" type="float" value="%s" />\n' % radius)
        t.append('\t\t\t\t\t<attribute id="ScalpMaterialId" type="FixedString" value="" />\n')
        t.append('\t\t\t\t\t<attribute id="SkeletonResource" type="FixedString" value="" />\n')
        t.append('\t\t\t\t\t<attribute id="SkeletonSlot" type="FixedString" value="" />\n')
        t.append('\t\t\t\t\t<attribute id="Slot" type="FixedString" value="Unassigned" />\n')
        t.append('\t\t\t\t\t<attribute id="SoftbodyResourceID" type="FixedString" value="" />\n')
        t.append('\t\t\t\t\t<attribute id="SourceFile" type="LSString" value="%s" />\n' % src)
        t.append('\t\t\t\t\t<attribute id="SupportsVertexColorMask" type="bool" value="False" />\n')
        t.append('\t\t\t\t\t<attribute id="Template" type="FixedString" value="%s" />\n' % templ)
        t.append('\t\t\t\t\t<attribute id="_OriginalFileVersion_" type="int64" value="%s" />\n' % ORIG_FILE_VERSION)
        t.append('\t\t\t\t\t<children>\n')
        t.append('\t\t\t\t\t\t<node id="AnimationWaterfall">\n'
                 '\t\t\t\t\t\t\t<attribute id="Object" type="FixedString" value="" />\n'
                 '\t\t\t\t\t\t</node>\n')
        t.append('\t\t\t\t\t\t<node id="Base" />\n')
        t.append('\t\t\t\t\t\t<node id="Objects">\n')
        t.append('\t\t\t\t\t\t\t<attribute id="LOD" type="uint8" value="0" />\n')
        t.append('\t\t\t\t\t\t\t<attribute id="MaterialID" type="FixedString" value="%s" />\n'
                 % MATERIALS.get(gr2, ("", []))[0])
        t.append('\t\t\t\t\t\t\t<attribute id="ObjectID" type="FixedString" value="%s.%s%s.0" />\n'
                 % (gr2, gr2, OBJ_SUFFIX))
        t.append('\t\t\t\t\t\t\t<attribute id="Physics" type="FixedString" value="" />\n')
        t.append('\t\t\t\t\t\t\t<attribute id="Slot" type="FixedString" value="" />\n')
        t.append('\t\t\t\t\t\t</node>\n')
        t.append('\t\t\t\t\t</children>\n')
        t.append('\t\t\t\t</node>\n')
        log("  visual %-28s -> %s  (%s)" % (item, uuid, gr2))
    t += ['\t\t\t</children>\n', '\t\t</node>\n', '\t</region>\n']
    t.append(_material_region())
    t.append(_texture_region())
    t.append('</save>\n')
    write(os.path.join(KNUCKLE, "Public", "Shared", "Content", "Assets", "Weapons", "[PAK]_Humans", "_merged.lsx"), "".join(t))


def param_texture(pid, pname):
    """Texture slot for the emissive template (Glowmap uses the bare uniform name)."""
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


def _tex_param(pid, pname):
    return ('\t\t\t\t<node id="Texture2DParameters">\n'
            '\t\t\t\t\t<attribute id="Enabled" type="bool" value="True" />\n'
            '\t\t\t\t\t<attribute id="ExportAsPreset" type="bool" value="True" />\n'
            '\t\t\t\t\t<attribute id="GroupName" type="FixedString" value="01 Texture Map" />\n'
            '\t\t\t\t\t<attribute id="ID" type="FixedString" value="%s" />\n'
            '\t\t\t\t\t<attribute id="ParameterName" type="FixedString" value="%s" />\n'
            '\t\t\t\t\t<attribute id="UniformName" type="FixedString" value="Texture2DParameter_%s_DefaultWrapSampler" />\n'
            '\t\t\t\t</node>\n' % (pid, pname, pname))


def _tex_res(tid, name, dds, srgb):
    return ('\t\t\t\t<node id="Resource">\n'
            '\t\t\t\t\t<attribute id="Name" type="LSString" value="%s" />\n'
            '\t\t\t\t\t<attribute id="ID" type="FixedString" value="%s" />\n'
            '\t\t\t\t\t<attribute id="SourceFile" type="LSString" value="%s/%s" />\n'
            '\t\t\t\t\t<attribute id="Format" type="uint32" value="64" />\n'
            '\t\t\t\t\t<attribute id="Width" type="int32" value="1024" />\n'
            '\t\t\t\t\t<attribute id="Height" type="int32" value="1024" />\n'
            '\t\t\t\t\t<attribute id="Depth" type="int32" value="1" />\n'
            '\t\t\t\t\t<attribute id="Localized" type="bool" value="False" />\n'
            '\t\t\t\t\t<attribute id="SRGB" type="bool" value="%s" />\n'
            '\t\t\t\t\t<attribute id="Streaming" type="bool" value="True" />\n'
            '\t\t\t\t\t<attribute id="Template" type="FixedString" value="" />\n'
            '\t\t\t\t\t<attribute id="Type" type="int32" value="1" />\n'
            '\t\t\t\t</node>\n' % (name, tid, TEX_DIR, dds, "True" if srgb else "False"))


def _material_region():
    """Emissive material: CHAR_BASE cannot glow, CHAR_BASE_GM can.

    CHAR_BASE_GM adds three parameters on top of the normal four texture slots:
    Glowmap (texture), GlowMultiplier (scalar), GlowColor (fvec3). Vanilla magic
    weapons wire exactly this (WPN_HUM_Longbow_A_1_GM_Lightning). MaterialType 4 is
    what vanilla weapon materials use.
    """
    t = ['<region id="MaterialBank">\n', '\t<node id="MaterialBank">\n', '\t\t<children>\n']
    for stem, (mid, tids) in MATERIALS.items():
        glow_id = GLOW_IDS[stem]
        t += ['\t\t\t<node id="Resource">\n',
              '\t\t\t\t<attribute id="DiffusionProfileUUID" type="FixedString" value="" />\n',
              '\t\t\t\t<attribute id="ID" type="FixedString" value="%s" />\n' % mid,
              '\t\t\t\t<attribute id="MaterialType" type="uint8" value="4" />\n',
              '\t\t\t\t<attribute id="Name" type="LSString" value="%s_Material" />\n' % stem,
              '\t\t\t\t<attribute id="SourceFile" type="LSString" value="Public/Shared/Assets/Materials/Characters/CHAR_BASE_GM.lsf" />\n',
              '\t\t\t\t<children>\n']
        for pid, pname in zip(tids, ("basecolor", "normalmap", "physicalmap", "MSKColor")):
            t.append(_tex_param(pid, pname))
        t.append(param_texture(glow_id, "Glowmap"))
        t.append(param_scalar("GlowMultiplier", GLOW_MULT))
        t.append(param_vec3("GlowColor", GLOW_RGB[stem]))
        t += ['\t\t\t\t</children>\n', '\t\t\t</node>\n']
    t += ['\t\t</children>\n', '\t</node>\n', '</region>\n']
    return "".join(t)


def _texture_region():
    t = ['<region id="TextureBank">\n', '\t<node id="TextureBank">\n', '\t\t<children>\n']
    for stem, (mid, tids) in MATERIALS.items():
        bm, nm, pm, msk = tids
        t.append(_tex_res(bm, "%s_BM" % stem, "%s_BM.DDS" % stem, True))
        t.append(_tex_res(nm, "%s_NM" % stem, "%s_NM.DDS" % stem, False))
        t.append(_tex_res(pm, "%s_PM" % stem, "%s_PM.DDS" % stem, False))
        t.append(_tex_res(msk, "%s_MSK" % stem, "%s_BM.DDS" % stem, False))
        # glow map: black everywhere except the runes; SRGB False (it is a mask)
        t.append(_tex_res(GLOW_IDS[stem], "%s_GLOW" % stem, "%s_GLOW.DDS" % stem, False))
    t += ['\t\t</children>\n', '\t</node>\n', '</region>\n']
    return "".join(t)



def patch_generator():
    """视觉模板改成按武器映射（原来是三件共用一个匕首 UUID）。"""
    p = os.path.join(TOOLS, "gen_knuckles.py")
    src = io.open(p, encoding="utf-8").read()
    if "VISUAL_TMPL_BY_ITEM" in src:
        log("  gen_knuckles.py 已打过补丁，跳过")
        return
    anchor = 'VISUAL_TMPL = "cb8ea426-fecc-de0f-ffb2-be1596ae68c0"\n'
    if anchor not in src:
        log("  !! 找不到 VISUAL_TMPL 锚点，补丁失败")
        return
    block = anchor + (
        "# 我们自己生成的武器视觉（Content/Assets/Weapons/[PAK]_Humans/_merged.lsx 里的 VisualBank ID）\n"
        "VISUAL_TMPL_BY_ITEM = {\n"
        '    "WPN_KD_SteelSpikeFist": "a1f3c2e4-5b6d-4e7f-8a90-1b2c3d4e5f60",\n'
        '    "WPN_KD_BoneChill": "b2e4d3f5-6c7e-4f80-9ab1-2c3d4e5f6071",\n'
        '    "WPN_KD_Unsharpened": "c3f5e406-7d8f-4081-abc2-3d4e5f607182",\n'
        "}\n")
    src = src.replace(anchor, block, 1)
    old_use = '% (VISUAL_TMPL if VISUAL_MODE == "dagger" else ""))'
    new_use = '% (VISUAL_TMPL_BY_ITEM.get(name, VISUAL_TMPL) if VISUAL_MODE == "dagger" else ""))'
    if old_use not in src:
        log("  !! 找不到 VisualTemplate 使用处，补丁失败")
        return
    src = src.replace(old_use, new_use, 1)
    io.open(p, "w", encoding="utf-8", newline="\n").write(src)
    log("  已给 gen_knuckles.py 打补丁：按武器映射视觉 UUID")


def patch_build_ps1():
    """build.ps1 的视觉库转换步骤现在是手工维护的（2b/4 段）。
    历史上这个自动打补丁拿 `--- 3/4 create-package ---` 当锚点，而那串正好在
    一个 Write-Host 单引号字符串里 —— 插入后单引号被切断，生成两段互相覆盖的
    死代码（PS 静默跑完，只打出两行乱码）。所以现在只校验、不再自动改。"""
    p = os.path.join(TOOLS, "build.ps1")
    src = io.open(p, encoding="utf-8").read()
    if "PAK]_Humans\\_merged.lsx" in src:
        log("  build.ps1 已含视觉库转换步骤，跳过")
        return
    log("  !! build.ps1 缺少视觉库转换步骤（2b/4 段）—— 请手工补：")
    log("     $vbank = Join-Path $ROOT 'Public\\Shared\\Content\\Assets\\Weapons\\[PAK]_Humans\\_merged.lsx'")
    log("     先删 .lsf 再 divine convert-resource，最后才 create-package")


def convert_bank():
    lsx = os.path.join(KNUCKLE, "Public", "Shared", "Content", "Assets", "Weapons", "[PAK]_Humans", "_merged.lsx")
    lsf = os.path.splitext(lsx)[0] + ".lsf"
    if os.path.isfile(lsf):
        os.remove(lsf)
    r = subprocess.run([DIVINE, "-g", "bg3", "-a", "convert-resource", "-s", lsx, "-d", lsf],
                       capture_output=True, text=True)
    ok = os.path.isfile(lsf)
    log("  转换视觉库 -> %s  %s (%d B)" % (os.path.basename(lsf), "OK" if ok else "失败",
                                        os.path.getsize(lsf) if ok else 0))
    if not ok:
        log(r.stdout[-500:] + r.stderr[-500:])
    return ok


def main():
    log("① 写视觉库 lsx")
    build_bank()
    log("② 打补丁")
    patch_generator()
    patch_build_ps1()
    # ③ 曾经在这里无条件重跑 gen_knuckles.py —— 那是**从头重新生成** KD_1~KD_4 的脚本，
    # 每次出包都会把手工维护的 stat（武器属性、武僧武器被动、剥壳被动、攻击法术的
    # UseCosts/MeleeWeaponAttack/伤害链）整片覆盖回模板原样。
    # 2026-10-18 实测踩到一次：出包后 KD_1/KD_2 回到 2,006 / 2,632 B（= 模板原样）。
    # 现在 stat 由人手维护，**默认不再重新生成**；确实需要重建骨架时用 KD_REGEN_STATS=1 显式打开。
    if os.environ.get("KD_REGEN_STATS") == "1":
        log("③ 显式要求：重新生成 stats 与根模板（会覆盖手工修改！）")
        r = subprocess.run([sys.executable, os.path.join(TOOLS, "gen_knuckles.py")],
                           capture_output=True, text=True)
        log("   " + (r.stdout.strip().splitlines() or ["(no output)"])[-1])
        if r.returncode != 0:
            log(r.stderr[-800:])
            return 1
    else:
        log("③ 跳过 stats 重建（手工维护中；需要重建请设 KD_REGEN_STATS=1）")
    log("④ 转换视觉库为 lsf")
    return 0 if convert_bank() else 1


if __name__ == "__main__":
    sys.exit(main())

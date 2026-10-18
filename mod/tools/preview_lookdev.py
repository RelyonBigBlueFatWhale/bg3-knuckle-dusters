# -*- coding: utf-8 -*-
"""preview_lookdev.py -- render a knuckle with the real BM/NM/PM (+GLOW) maps.

Look-dev sibling of preview_v6.py: same mesh, same camera framing convention
(center + (0.80,-1.95,0.85)*size, 72 mm), but a neutral grey studio instead of a
blown-white transparent background, and the GLOW map wired into Emission the
way CHAR_BASE_GM's Glowmap x GlowColor x GlowMultiplier would be in game.

Renders per style:
  <style>_look.png   3/4 view, 1000x800, grey studio (the v6 camera)
  <style>_front.png  front orthographic, 1024x1024, alpha (for icon comparison)

Run: blender --background --factory-startup --python preview_lookdev.py -- <style>
"""
import math
import os
import sys

import bpy
from mathutils import Vector

MODEL_DIR = r"D:\DSH\knuckle_tools\model_out"
TEX_DIR = r"D:\DSH\knuckle_tools\weapon_tex"
OUT = r"D:\DSH\knuckle_tools\preview\lookdev"

STYLES = {
    "steel_runeglow": dict(obj="KD_Knuckles_SteelSpike", glow_color=(0.10, 0.38, 1.0), glow_strength=3.4),
    "frost_icevein": dict(obj="KD_Knuckles_BoneChill", glow_color=(0.18, 0.45, 1.0), glow_strength=1.1),
    "brass_scroll": dict(obj="KD_Knuckles_Unsharpened", glow_color=(0.0, 0.0, 0.0), glow_strength=0.0),
}


def log(m):
    print("[lookdev-prev] %s" % m)
    sys.stdout.flush()


def img_node(nt, path, x, y, non_color=False):
    n = nt.nodes.new("ShaderNodeTexImage")
    n.location = (x, y)
    n.image = bpy.data.images.load(path)
    if non_color:
        n.image.colorspace_settings.name = "Non-Color"
    return n


def build_material(style, cfg):
    mat = bpy.data.materials.new("M_" + style)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    n = nt.nodes
    out = n.new("ShaderNodeOutputMaterial")
    out.location = (900, 0)
    bsdf = n.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (560, 0)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    bm = os.path.join(TEX_DIR, "%s_BM.png" % style)
    if os.path.isfile(bm):
        t = img_node(nt, bm, -620, 260)
        nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
    nm = os.path.join(TEX_DIR, "%s_NM.png" % style)
    if os.path.isfile(nm):
        t = img_node(nt, nm, -620, -40, non_color=True)
        nmap = n.new("ShaderNodeNormalMap")
        nmap.location = (-300, -40)
        nmap.inputs["Strength"].default_value = 1.0
        nt.links.new(t.outputs["Color"], nmap.inputs["Color"])
        nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    pm = os.path.join(TEX_DIR, "%s_PM.png" % style)
    if os.path.isfile(pm):
        t = img_node(nt, pm, -620, -360, non_color=True)
        sep = n.new("ShaderNodeSeparateColor")
        sep.location = (-300, -360)
        nt.links.new(t.outputs["Color"], sep.inputs["Color"])
        nt.links.new(sep.outputs["Red"], bsdf.inputs["Roughness"])
        nt.links.new(sep.outputs["Green"], bsdf.inputs["Metallic"])
        # PM.B (cavity) is not a Principled input; it is baked into BM/PM by the
        # generator and left unwired here on purpose.
    glw = os.path.join(TEX_DIR, "%s_GLOW.png" % style)
    if os.path.isfile(glw) and cfg["glow_strength"] > 0:
        t = img_node(nt, glw, -620, -660, non_color=True)
        bw = n.new("ShaderNodeRGBToBW")
        bw.location = (-340, -660)
        mul = n.new("ShaderNodeMixRGB") if hasattr(bpy.types, "ShaderNodeMixRGB") else n.new("ShaderNodeMix")
        mul.location = (-140, -600)
        try:
            mul.blend_type = "MULTIPLY"
            mul.inputs["Fac"].default_value = 1.0
            mul.inputs[2].default_value = (*cfg["glow_color"], 1.0)
        except Exception:
            pass
        nt.links.new(t.outputs["Color"], bw.inputs["Color"])
        nt.links.new(bw.outputs["Val"], mul.inputs[1])
        nt.links.new(mul.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = cfg["glow_strength"]
    return mat


def build_world():
    w = bpy.data.worlds.new("W")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 0.85
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.30
    ramp.color_ramp.elements[0].color = (0.055, 0.058, 0.062, 1)
    ramp.color_ramp.elements[1].position = 0.85
    ramp.color_ramp.elements[1].color = (0.42, 0.45, 0.50, 1)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    tex = nt.nodes.new("ShaderNodeTexCoord")
    nt.links.new(tex.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])


def area(center, size, loc, rot, energy, sz, color=(1, 1, 1)):
    d = bpy.data.lights.new("L", type="AREA")
    d.energy = energy
    d.size = sz
    d.color = color
    o = bpy.data.objects.new("L", d)
    o.location = center + Vector(loc) * size
    o.rotation_euler = tuple(math.radians(a) for a in rot)
    bpy.context.collection.objects.link(o)
    return o


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["steel_runeglow"]
    style = argv[0]
    cfg = STYLES[style]
    obj_path = os.path.join(MODEL_DIR, cfg["obj"] + ".obj")
    if not os.path.isfile(obj_path):
        raise SystemExit("missing %s" % obj_path)
    os.makedirs(OUT, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.obj_import(filepath=obj_path, up_axis="Z", forward_axis="NEGATIVE_Y")
    ob = [o for o in bpy.context.scene.objects if o.type == "MESH"][0]
    ob.data.materials.clear()
    ob.data.materials.append(build_material(style, cfg))
    for p in ob.data.polygons:
        p.use_smooth = True

    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    center = (mn + mx) / 2.0
    size = max((mx - mn).x, (mx - mn).y, (mx - mn).z)

    build_world()
    # Soft 3-point rig scaled to the part; big sources so the plate, the bore rims
    # and the relief all stay readable (light size ~ part size => soft falloff).
    area(center, size, (-1.25, -1.45, 1.30), (46, 0, -40), 2.2, 1.65 * size, (1.0, 0.97, 0.92))
    area(center, size, (1.45, -1.05, 0.30), (86, 0, 58), 0.9, 2.00 * size, (0.78, 0.85, 1.0))
    area(center, size, (0.50, 1.55, 1.00), (118, 0, 166), 2.6, 1.10 * size, (1.0, 0.90, 0.78))
    area(center, size, (0.0, -0.40, 2.10), (12, 0, 0), 1.2, 1.30 * size, (0.95, 0.97, 1.0))

    cam_d = bpy.data.cameras.new("Cam")
    cam = bpy.data.objects.new("Cam", cam_d)
    bpy.context.collection.objects.link(cam)
    cam.location = center + Vector((0.80, -1.95, 0.85)) * size
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam_d.lens = 72
    bpy.context.scene.camera = cam

    s = bpy.context.scene
    s.render.engine = "CYCLES"
    s.cycles.device = "CPU"
    s.cycles.samples = int(os.environ.get("QC_SAMPLES", "110"))
    s.cycles.use_denoising = True
    s.view_settings.view_transform = "AgX"
    s.view_settings.look = "AgX - Medium High Contrast"
    s.render.film_transparent = False
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_mode = "RGBA"
    qs = float(os.environ.get("QC_SCALE", "1.0"))
    s.render.resolution_x = int(1000 * qs)
    s.render.resolution_y = int(800 * qs)
    look_png = os.path.join(OUT, "%s_look.png" % style)
    s.render.filepath = look_png
    bpy.ops.render.render(write_still=True)
    log("look -> %s" % look_png)

    # front orthographic (icon-comparable), transparent so the compositor can
    # drop it on the same card as the icon
    cam2_d = bpy.data.cameras.new("CamFront")
    cam2 = bpy.data.objects.new("CamFront", cam2_d)
    bpy.context.collection.objects.link(cam2)
    cam2_d.type = "ORTHO"
    cam2_d.ortho_scale = 1.12 * max((mx - mn).x, (mx - mn).z)
    cam2.location = center + Vector((0.0, -3.0, 0.0)) * size
    cam2.rotation_euler = (center - cam2.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam2
    s.render.film_transparent = True
    s.render.resolution_x = int(1024 * qs)
    s.render.resolution_y = int(1024 * qs)
    front_png = os.path.join(OUT, "%s_front.png" % style)
    s.render.filepath = front_png
    bpy.ops.render.render(write_still=True)
    log("front -> %s" % front_png)


if __name__ == "__main__":
    main()

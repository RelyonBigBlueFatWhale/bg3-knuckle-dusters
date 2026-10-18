# -*- coding: utf-8 -*-
"""Render a v6 mesh with its BAKED normal + AO maps applied -- the real "does it
look like the reference art" check.

Run: blender --background --factory-startup --python preview_v6.py -- <name> [<style>]
Out: D:\\DSH\\knuckle_tools\\preview\\v6\\<name>.png
"""
import math
import os
import sys

import bpy
from mathutils import Vector

MODEL_DIR = r"D:\DSH\knuckle_tools\model_out"
BAKE_OUT = r"D:\DSH\knuckle_tools\bake_out"
OUT = r"D:\DSH\knuckle_tools\preview\v6"

STYLE_TINT = {
    "brass_filigree": ((0.72, 0.50, 0.18, 1.0), 0.30),
    "frost_ribs": ((0.16, 0.34, 0.55, 1.0), 0.24),
    "spike_studs": ((0.19, 0.19, 0.21, 1.0), 0.34),
}


def log(m):
    print("[prev6] %s" % m)
    sys.stdout.flush()


def build_material(style):
    """Exactly the three maps the game will get: BM / NM / PM."""
    texdir = r"D:\DSH\knuckle_tools\weapon_tex"
    mat = bpy.data.materials.new("M_" + style)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    n = nt.nodes
    out = n.new("ShaderNodeOutputMaterial"); out.location = (760, 0)
    bsdf = n.new("ShaderNodeBsdfPrincipled"); bsdf.location = (440, 0)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Metallic"].default_value = 1.0

    bm = os.path.join(texdir, "%s_BM.png" % style)
    if os.path.isfile(bm):
        img = n.new("ShaderNodeTexImage"); img.location = (-520, 180)
        img.image = bpy.data.images.load(bm)
        nt.links.new(img.outputs["Color"], bsdf.inputs["Base Color"])
    nm = os.path.join(texdir, "%s_NM.png" % style)
    if os.path.isfile(nm):
        t2 = n.new("ShaderNodeTexImage"); t2.location = (-520, -220)
        t2.image = bpy.data.images.load(nm)
        t2.image.colorspace_settings.name = "Non-Color"
        nmap = n.new("ShaderNodeNormalMap"); nmap.location = (-220, -220)
        nmap.inputs["Strength"].default_value = 1.0
        nt.links.new(t2.outputs["Color"], nmap.inputs["Color"])
        nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    pm = os.path.join(texdir, "%s_PM.png" % style)
    if os.path.isfile(pm):
        t3 = n.new("ShaderNodeTexImage"); t3.location = (-520, -520)
        t3.image = bpy.data.images.load(pm)
        t3.image.colorspace_settings.name = "Non-Color"
        sep = n.new("ShaderNodeSeparateColor"); sep.location = (-220, -520)
        nt.links.new(t3.outputs["Color"], sep.inputs["Color"])
        nt.links.new(sep.outputs["Red"], bsdf.inputs["Roughness"])
        nt.links.new(sep.outputs["Green"], bsdf.inputs["Metallic"])
    return mat

def setup(center, size):
    world = bpy.data.worlds.new("W")
    bpy.context.scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.34, 0.37, 0.44, 1.0)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.22

    def area(name, loc, rot, energy, sz, color=(1, 1, 1)):
        d = bpy.data.lights.new(name, type="AREA")
        d.energy = energy; d.size = sz; d.color = color
        o = bpy.data.objects.new(name, d)
        o.location = center + Vector(loc) * size
        o.rotation_euler = tuple(math.radians(a) for a in rot)
        bpy.context.collection.objects.link(o)

    area("Key", (-0.9, -1.3, 1.1), (52, 0, -36), 3.2, 0.55, (1.0, 0.98, 0.94))
    area("Fill", (1.2, -0.9, 0.1), (84, 0, 56), 0.9, 0.8, (0.80, 0.86, 1.0))
    area("Rim", (0.3, 1.2, 0.8), (120, 0, 165), 2.0, 0.5, (1.0, 0.92, 0.82))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["KD_Knuckles_Unsharpened"]
    name = argv[0]
    style = argv[1] if len(argv) > 1 else "brass_filigree"
    os.makedirs(OUT, exist_ok=True)

    obj = os.path.join(MODEL_DIR, name + ".obj")
    if not os.path.isfile(obj):
        raise SystemExit("missing %s" % obj)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.obj_import(filepath=obj, up_axis="Z", forward_axis="NEGATIVE_Y")
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    ob = meshes[0]
    ob.data.materials.clear()
    ob.data.materials.append(build_material(style))
    for p in ob.data.polygons:
        p.use_smooth = True

    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    center = (mn + mx) / 2.0
    size = max((mx - mn).x, (mx - mn).y, (mx - mn).z)
    setup(center, size)

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
    s.cycles.samples = 128
    s.cycles.use_denoising = True
    s.render.resolution_x = 900
    s.render.resolution_y = 720
    s.render.film_transparent = True
    s.view_settings.view_transform = "Standard"
    png = os.path.join(OUT, name + ".png")
    s.render.filepath = png
    bpy.ops.render.render(write_still=True)
    log("%s  %d tris  %.3f x %.3f x %.3f m -> %s" % (
        name, sum(len(p.vertices) - 2 for p in ob.data.polygons),
        mx.x - mn.x, mx.y - mn.y, mx.z - mn.z, os.path.basename(png)))


if __name__ == "__main__":
    main()

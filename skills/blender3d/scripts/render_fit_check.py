"""Render exploded and cut-away views of a multi-part model to check how parts fit.

Usage:
    /Applications/Blender.app/Contents/MacOS/Blender -b <file.blend> --factory-startup \
        -P skills/blender3d/scripts/render_fit_check.py -- <out_dir> [<prefix>]

Writes:
    <prefix>_exploded.png  child objects pulled down below their parent, 3/4 view
    <prefix>_section.png   every mesh cut in half at Y = 0, framed on the child parts
Each object gets its own flat color. Prints non-manifold edge counts per object
(0 = watertight). Nothing is saved back to the .blend.
"""

import os
import sys

import bmesh
import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if not argv:
    sys.exit("usage: ... -P render_fit_check.py -- <out_dir> [<prefix>]")
out_dir = os.path.abspath(argv[0])
prefix = argv[1] if len(argv) > 1 else os.path.splitext(os.path.basename(bpy.data.filepath))[0]
os.makedirs(out_dir, exist_ok=True)

scene = bpy.context.scene
meshes = sorted((o for o in scene.objects if o.type == "MESH"), key=lambda o: o.name)
children = [o for o in meshes if o.parent is not None]
if not children:
    sys.exit("no parented parts to check")

for o in meshes:
    bm = bmesh.new()
    bm.from_mesh(o.data)
    print(f"[fit] {o.name}: non-manifold edges = {sum(not e.is_manifold for e in bm.edges)}")
    bm.free()

palette = [(0.55, 0.55, 0.6, 1), (0.85, 0.45, 0.15, 1), (0.2, 0.5, 0.85, 1),
           (0.3, 0.7, 0.35, 1), (0.75, 0.3, 0.6, 1), (0.9, 0.8, 0.2, 1)]
for i, o in enumerate(meshes):
    o.color = palette[i % len(palette)]

scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "OBJECT"
scene.display.shading.show_cavity = True

cam = bpy.data.objects.new("FitCam", bpy.data.cameras.new("FitCam"))
scene.collection.objects.link(cam)
scene.camera = cam
cam.data.type = "ORTHO"


def bounds(objs):
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    lo = Vector(tuple(min(p[i] for p in pts) for i in range(3)))
    hi = Vector(tuple(max(p[i] for p in pts) for i in range(3)))
    return lo, hi


def shoot(path, lo, hi, direction, res):
    w, h = res
    scene.render.resolution_x, scene.render.resolution_y = res
    center = (lo + hi) / 2
    size = hi - lo
    cam.location = center + Vector(direction).normalized() * (size.length * 2 + 1)
    cam.data.clip_end = size.length * 10 + 10
    rot = (center - cam.location).to_track_quat("-Z", "Y")
    cam.rotation_euler = rot.to_euler()
    # Fit the box corners as seen by the camera; ortho_scale spans the larger render side
    inv = rot.inverted()
    corners = [inv @ (Vector((x, y, z)) - center) for x in (lo.x, hi.x) for y in (lo.y, hi.y) for z in (lo.z, hi.z)]
    span_x = max(c.x for c in corners) - min(c.x for c in corners)
    span_y = max(c.y for c in corners) - min(c.y for c in corners)
    scale = max(span_x, span_y * w / h) if w >= h else max(span_y, span_x * h / w)
    cam.data.ortho_scale = scale * 1.1
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


# Exploded: lower parts move further down, gap = 15% of assembly height
lo, hi = bounds(meshes)
gap = (hi.z - lo.z) * 0.15
ordered = sorted(children, key=lambda o: -bounds([o])[0].z)
saved = {o: o.matrix_world.copy() for o in ordered}
for k, o in enumerate(ordered):
    o.matrix_world.translation.z -= gap * (k + 1)
lo_e, hi_e = bounds(meshes)
shoot(os.path.join(out_dir, f"{prefix}_exploded.png"), lo_e, hi_e, (0.6, -1, 0.35), (900, 1400))
for o, mw in saved.items():
    o.matrix_world = mw

# Section: cut away Y < 0 and frame on the parts (full assembly width)
lo, hi = bounds(meshes)
size = (hi - lo).length
cutter = bpy.data.objects.new("FitCutter", bpy.data.meshes.new("FitCutter"))
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=size * 2)
bmesh.ops.translate(bm, verts=bm.verts, vec=(0, -size, 0))
bm.to_mesh(cutter.data)
bm.free()
scene.collection.objects.link(cutter)
cutter.hide_render = True
for o in meshes:
    mod = o.modifiers.new("FitCut", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.use_self = True          # bodies built from overlapping shells
    mod.use_hole_tolerant = True
    mod.object = cutter
plo, phi = bounds(children)
frame_lo = Vector((lo.x, lo.y, plo.z))
frame_hi = Vector((hi.x, hi.y, phi.z))
shoot(os.path.join(out_dir, f"{prefix}_section.png"), frame_lo, frame_hi, (0, -1, 0.12), (1400, 900))

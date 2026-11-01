"""Render Workbench preview images of every mesh object in a .blend.

Usage:
    /Applications/Blender.app/Contents/MacOS/Blender -b <file.blend> --factory-startup \
        -P .claude/skills/blender3d/scripts/render_preview.py -- <out_dir> [<prefix>]

Writes <out_dir>/<prefix>_front.png (near eye level) and <out_dir>/<prefix>_top.png
(elevated, shows the top surface), both framing all mesh objects. <prefix> defaults
to the .blend file name. Workbench is used because it renders reliably headless;
nothing is saved back to the .blend.
"""

import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if not argv:
    sys.exit("usage: ... -P render_preview.py -- <out_dir> [<prefix>]")
out_dir = os.path.abspath(argv[0])
prefix = argv[1] if len(argv) > 1 else os.path.splitext(os.path.basename(bpy.data.filepath))[0]
os.makedirs(out_dir, exist_ok=True)

scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "MATERIAL"
scene.display.shading.show_cavity = True
scene.render.resolution_x, scene.render.resolution_y = 1400, 900

meshes = sorted((o for o in scene.objects if o.type == "MESH"), key=lambda o: o.name)
if not meshes:
    sys.exit("no mesh objects to render")


def bounds(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


cam_data = bpy.data.cameras.new("PreviewCam")
cam = bpy.data.objects.new("PreviewCam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam


def shoot(objs, path, direction, lens=50.0):
    lo, hi = bounds(objs)
    center = (lo + hi) / 2
    size = (hi - lo).length
    # Distance so the bounding box diagonal fits the short side of the frame, plus margin
    rx, ry = scene.render.resolution_x, scene.render.resolution_y
    cam_data.sensor_fit = "HORIZONTAL"
    short_side_mm = cam_data.sensor_width * min(rx, ry) / rx
    dist = size * lens / short_side_mm * 1.1
    direction = Vector(direction).normalized()
    cam.location = center + direction * dist
    cam_data.lens = lens
    cam_data.clip_end = dist * 10
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


shoot(meshes, os.path.join(out_dir, f"{prefix}_front.png"), (0.35, -1.0, 0.15))
shoot(meshes, os.path.join(out_dir, f"{prefix}_top.png"), (0.5, -1.0, 0.9))

"""Render one object as a studio "showcase" image on a pure white background.

Usage:
    /Applications/Blender.app/Contents/MacOS/Blender -b <file.blend> --factory-startup \
        -P .claude/skills/blender3d/scripts/render_showcase.py -- \
        <object name> <out.png> [width height samples azimuth_deg elevation_deg]

Defaults: 2000 x 1500 (4:3), 128 samples, azimuth -35, elevation 38 (a high three-quarter
view from the front-left that looks down into open-topped parts).

What it does, in this session only (nothing is saved back to the .blend):
  - hides every other object, unparents the chosen one and puts it at the world origin
    in print orientation (origin on the floor, Z up)
  - gives it a charcoal ABS-like material so details read on white
  - Cycles (CPU, denoised), three soft area lights, a shadow-catcher floor, and a
    compositor step that lays the result over pure white (255, 255, 255)
  - Standard view transform, so white really is white
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if len(argv) < 2:
    sys.exit("usage: ... -P render_showcase.py -- <object name> <out.png> "
             "[width height samples azimuth_deg elevation_deg]")
obj_name, out_path = argv[0], os.path.abspath(argv[1])
width = int(argv[2]) if len(argv) > 2 else 2000
height = int(argv[3]) if len(argv) > 3 else 1500
samples = int(argv[4]) if len(argv) > 4 else 128
azimuth = math.radians(float(argv[5])) if len(argv) > 5 else math.radians(-35.0)
elevation = math.radians(float(argv[6])) if len(argv) > 6 else math.radians(38.0)
os.makedirs(os.path.dirname(out_path), exist_ok=True)

scene = bpy.context.scene
obj = bpy.data.objects[obj_name]

# Isolate the object in print orientation
for o in scene.objects:
    if o is not obj:
        o.hide_render = True
        o.hide_viewport = True
obj.parent = None
obj.matrix_world = Matrix.Identity(4)
bpy.context.view_layer.update()

# Material: charcoal ABS (the model's own black is too dark to show detail on white)
mat = bpy.data.materials.new("Showcase_ABS")
mat.use_nodes = True
bsdf = mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.055, 0.055, 0.06, 1.0)
bsdf.inputs["Roughness"].default_value = 0.32
for i in range(len(obj.material_slots)):
    obj.material_slots[i].material = mat
if not obj.material_slots:
    obj.data.materials.append(mat)

# Bounds
pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
lo = Vector(tuple(min(p[i] for p in pts) for i in range(3)))
hi = Vector(tuple(max(p[i] for p in pts) for i in range(3)))
center = (lo + hi) / 2
size = hi - lo
radius = size.length / 2

# Render settings
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = samples
scene.cycles.use_adaptive_sampling = True
scene.cycles.use_denoising = True
scene.cycles.denoiser = "OPENIMAGEDENOISE"
scene.cycles.max_bounces = 8
scene.render.resolution_x, scene.render.resolution_y = width, height
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
scene.render.image_settings.compression = 15
scene.render.filepath = out_path

# World: white ambient light
world = bpy.data.worlds.new("ShowcaseWorld")
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
bg.inputs["Strength"].default_value = 0.4
scene.world = world

# Floor that only catches the contact shadow
floor_mesh = bpy.data.meshes.new("ShowcaseFloor")
s = radius * 40
floor_mesh.from_pydata([(-s, -s, lo.z), (s, -s, lo.z), (s, s, lo.z), (-s, s, lo.z)], [], [(0, 1, 2, 3)])
floor = bpy.data.objects.new("ShowcaseFloor", floor_mesh)
scene.collection.objects.link(floor)
floor.is_shadow_catcher = True

# Camera
cam_data = bpy.data.cameras.new("ShowcaseCam")
cam_data.lens = 85.0
cam_data.sensor_fit = "HORIZONTAL"
cam = bpy.data.objects.new("ShowcaseCam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
fill_fraction = 0.5  # how much of the frame width the part's widest extent covers
fov = 2 * math.atan(cam_data.sensor_width / (2 * cam_data.lens))
dist = (max(size.x, size.y) / fill_fraction / 2) / math.tan(fov / 2)
direction = Vector((math.sin(azimuth) * math.cos(elevation),
                    -math.cos(azimuth) * math.cos(elevation),
                    math.sin(elevation)))
cam.location = center + direction * dist
cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
cam_data.clip_start = dist * 0.05
cam_data.clip_end = dist * 20


def area_light(name, offset, power, light_size):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = power
    data.size = light_size
    light = bpy.data.objects.new(name, data)
    scene.collection.objects.link(light)
    light.location = center + Vector(offset) * radius
    light.rotation_euler = (center - light.location).to_track_quat("-Z", "Y").to_euler()
    return light


# Soft key from the front-left above, fill from the right, rim from behind.
# Lights sit a fixed number of radii away, so power scales with radius squared; the base
# values below are for a part with a ~44 mm bounding radius (the Glosola plug).
power_scale = (radius / 0.0445) ** 2
area_light("Key", (-4.0, -4.5, 5.5), 0.7 * power_scale, radius * 6)
area_light("Fill", (5.0, -3.0, 2.5), 0.25 * power_scale, radius * 6)
area_light("Rim", (1.5, 5.0, 3.5), 0.35 * power_scale, radius * 4)

# Compositor: lay the (transparent-background) render over pure white
scene.use_nodes = True
tree = scene.node_tree
tree.nodes.clear()
render_layers = tree.nodes.new("CompositorNodeRLayers")
white = tree.nodes.new("CompositorNodeRGB")
white.outputs[0].default_value = (1.0, 1.0, 1.0, 1.0)
alpha_over = tree.nodes.new("CompositorNodeAlphaOver")
# The floor shadow fades out slowly and can leave the far corners at 251-253; a tiny
# exposure lift (about 4%) clips those to pure white and hardly touches the part.
exposure = tree.nodes.new("CompositorNodeExposure")
exposure.inputs["Exposure"].default_value = 0.06
composite = tree.nodes.new("CompositorNodeComposite")
tree.links.new(white.outputs[0], alpha_over.inputs[1])
tree.links.new(render_layers.outputs["Image"], alpha_over.inputs[2])
tree.links.new(alpha_over.outputs[0], exposure.inputs["Image"])
tree.links.new(exposure.outputs[0], composite.inputs["Image"])

bpy.ops.render.render(write_still=True)
print(f"[showcase] {obj_name} -> {out_path} ({width}x{height}, {samples} samples)")

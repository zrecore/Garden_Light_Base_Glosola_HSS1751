"""Export one object for 3D printing with Blender's 3D Print Toolbox extension.

Run (WITHOUT --factory-startup, so the user's installed 3D Print Toolbox loads):
    /Applications/Blender.app/Contents/MacOS/Blender -b models/Glosola_HSS1751.6PK.blend \
        -P scripts/export_print3d.py -- Glosola_HSS1751.6PK_Base models/print OBJ

Does what the toolbox's sidebar panel does: selects the object, runs "Check All"
and prints the report, then runs "Export" (io.print3d_export). The file is named
by the toolbox: <out_dir>/<blend name>-<object name>.<ext>.

Before checking and exporting, the object is unparented and moved to the world
origin with no rotation, so its own origin (bottom center) sits on Z = 0 in print
orientation, and its mesh is triangulated (n-gons can be split wrongly by slicers).

The toolbox's "Zero Faces/Edges" check uses one threshold (0.0001 Blender units) for
both areas and lengths. In this meter-scale scene that flags any face under 100 mm²,
so the script also prints its own degenerate-geometry counts in mm.

Orientation: the toolbox exports OBJ with Blender's OBJ defaults (Y-up, i.e. file
(X, Y, Z) = Blender (x, z, -y)), which Z-up slicers show lying on its side. For OBJ
the object is rotated +90 degrees about X after the checks and just before export,
so the file comes out Z-up: flange at Z = 0, height along +Z. STL and PLY are
already exported Z-up and are left alone.

Scale: the model is true size in Blender meters, while slicers read OBJ/STL/PLY
coordinates as millimeters. The toolbox multiplies by the scene's unit scale when
"Scene Scale" is on, so this script sets unit scale to 1000 for the export only.
Nothing is saved back to the .blend.
"""

import os
import sys

import math

import bmesh
import bpy
from mathutils import Matrix

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if len(argv) < 2:
    sys.exit("usage: ... -P export_print3d.py -- <object name> <out dir> [OBJ|STL|PLY]")
obj_name, out_dir = argv[0], os.path.abspath(argv[1])
fmt = argv[2].upper() if len(argv) > 2 else "OBJ"

if not hasattr(bpy.ops.io, "print3d_export"):
    sys.exit("3D Print Toolbox is not enabled (install it from Edit > Preferences > Get Extensions, "
             "and run Blender without --factory-startup)")
from bl_ext.blender_org.print3d_toolbox import report  # noqa: E402

scene = bpy.context.scene
obj = bpy.data.objects[obj_name]

# Print orientation: unparent and put the object's origin at the world origin
obj.parent = None
obj.matrix_world.identity()
bpy.context.view_layer.update()

# Triangulate (export session only)
bm = bmesh.new()
bm.from_mesh(obj.data)
bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="BEAUTY", ngon_method="BEAUTY")
bm.to_mesh(obj.data)
bm.free()

# Select only this object and make it active (the toolbox works on the selection)
for o in bpy.context.view_layer.objects:
    o.select_set(False)
obj.select_set(True)
bpy.context.view_layer.objects.active = obj

# 3D Print Toolbox > Analyze > Check All
bpy.ops.mesh.print3d_check_all()
print(f"[print3d] Check All for {obj.name}:")
for text, _data in report.info():
    print(f"[print3d]   {text}")

bm = bmesh.new()
bm.from_mesh(obj.data)
short = sum(e.calc_length() * 1000 <= 0.001 for e in bm.edges)
tiny = sum(f.calc_area() * 1e6 <= 0.0001 for f in bm.faces)
down = [f for f in bm.faces if f.normal.z < -0.7]
on_bed = sum(abs(f.calc_center_median().z) < 1e-9 for f in down)
print(f"[print3d] mm check: {len(bm.faces)} triangles, edges <= 0.001 mm: {short}, "
      f"faces <= 0.0001 mm^2: {tiny}, downward faces: {len(down)} ({on_bed} on the bed at Z = 0)")
bm.free()

# Make the OBJ Z-up (see docstring): Blender up (+Z) -> -Y, which the OBJ writer maps to file +Z
if fmt == "OBJ":
    obj.matrix_world = Matrix.Rotation(math.radians(90.0), 4, "X")
    bpy.context.view_layer.update()

# 3D Print Toolbox > Export
props = scene.print_3d
props.export_path = out_dir + os.sep
props.export_format = fmt
props.use_scene_scale = True
scene.unit_settings.scale_length = 1000.0  # meters -> millimeters in the exported file
result = bpy.ops.io.print3d_export()
print(f"[print3d] export {fmt}: {result}")

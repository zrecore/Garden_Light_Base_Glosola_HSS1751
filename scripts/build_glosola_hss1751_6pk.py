"""Build one Glosola HSS1751 solar pathway light in Blender.

Run headless:
    /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup -P scripts/build_glosola_hss1751_6pk.py

Source: https://www.amazon.com/dp/B0FQ2WP9CV
    "Measurements" Size : 17.3" tall (incl. stake) x 3.15" lamp head
    "Product Detail & Size" image: 3.15in wide cylinder, 17.3in tall incl. stake
    -> 8.001 cm diameter, 43.942 cm tall (assembled)
    Customer photo by RReig (https://m.media-amazon.com/images/I/81PO2jFwByL.jpg):
    a broken unit showing the one-piece spike and the cup-shaped base plug, whose
    center socket has snapped off (the small loose ring in the photo).

The light is a straight cylinder, top to bottom: black cap with a recessed round
solar panel, clear fluted acrylic lens, hollow black stainless pipe. The bottom of
the pipe is closed by a separate ABS base plug: a flange the pipe rests on (flush
with the pipe's outside) and a cup that goes up inside the pipe. Six wedge ribs on
the cup's outside, each with a sloped lead-in at the open end, grip the pipe wall.
The plug has a molded center socket, braced to the cup wall by six radial support
ribs on the floor, and the spike's round collar slides up into the socket.

Part heights of the body and the exposed stake length were measured from the size
diagram (3.15in = 126 px, 17.3in = 693 px). Plug flange, cup height and wedge
ribs were measured from the user's side photo of a plug (IMG_8570); socket and spike
proportions were scaled from the customer photo against the plug diameter. Wall
thicknesses and fit clearances are estimates.

Objects (all in collection Glosola_HSS1751.6PK, each origin at its bottom center):
    Glosola_HSS1751.6PK         light body; origin on the base mating plane
    Glosola_HSS1751.6PK_Base    child of body
    Glosola_HSS1751.6PK_Spike   child of body; origin at the spike tip

The scene uses metric units displayed in millimeters (scale_length = 1.0, so the
geometry is true-to-size on export). Constants below are written in cm (CM converts
them to Blender meters); sizes are reported in mm to match the scene units.
"""

import math
import os

import bmesh
import bpy
from mathutils import Matrix, Vector

NAME = "Glosola_HSS1751.6PK"
CM = 0.01  # cm -> Blender meters
MM_PER_CM = 10.0

# Listing dimensions (cm)
TOTAL_H = 17.3 * 2.54       # 43.942
BODY_D = 3.15 * 2.54        # 8.001

# Assembled heights measured from the size diagram, bottom (spike tip, z = 0) to top
SPIKE_TAPER_Z = 4.6         # spike narrows to the tip below this
MATING_Z = 13.0             # bottom face of the base plug (spike shows 13 cm below it)
LENS_Z0 = 31.8              # top of pipe / bottom of acrylic lens
CAP_Z0 = 40.2               # top of lens / bottom of solar cap

# Body details
PIPE_WALL = 0.1
PIPE_ID = BODY_D - 2 * PIPE_WALL   # 7.801 estimated; replace with a caliper measurement
LENS_WALL = 0.25
LENS_FLUTES, LENS_FLUTE_DEPTH = 24, 0.12
PANEL_RIM, PANEL_RECESS = 0.35, 0.08

# Base plug: flange (OD = body, flush with the pipe outside) + cup inside the pipe.
# Wedge rib tips sit RIB_CLEARANCE (diametral) inside the pipe's inside wall so the
# printed plug slides in; the cup wall sits RIB_H inside the rib tips.
# Test prints: 0.6 mm was still too big to go in; the user asked for the outer wall
# radius 2 mm smaller (ribs move in with it), i.e. 4 mm more across.
# Then 1 mm too loose: outer wall and ribs back out 1 mm in radius.
# Then still loose: rib tips 0.5 mm further out in radius with the cup wall unchanged
# (the wall is derived as tip - RIB_H, so RIB_CLEARANCE -1.0 mm and RIB_H +0.5 mm together).
# Then tips at 76.41 mm across were too big for the pipe (75.41 was too loose): set midway,
# 75.91 mm across (RIB_CLEARANCE 0.16 -> 0.21; RIB_H unchanged, so the cup wall moves in 0.25 mm).
# The pipe is slightly out of round and can't be measured; PIPE_ID is only a reference.
# Then 75.91 (and 76.41) were still too big. Reference print: tips 73.41 mm across with 2.5 mm
# ribs was almost right, only 0.5 mm (diameter) loose -> tips 73.91 mm across, ribs back to 2.5 mm
# (RIB_CLEARANCE 0.41, RIB_H 0.25, so the cup wall is 68.91 mm across).
# Then almost perfect but a little loose: tips another 0.3 mm across -> 74.21 mm
# (RIB_CLEARANCE 0.38; the cup wall follows, 69.21 mm across).
# Then still a hair loose: tips another 0.2 mm across -> 74.41 mm (RIB_CLEARANCE 0.36;
# the cup wall follows, 69.41 mm across).
# Then almost perfect but a touch loose: tips another 0.2 mm across -> 74.61 mm
# (RIB_CLEARANCE 0.34; the cup wall follows, 69.61 mm across).
# Then still a little loose: tips another 0.2 mm across -> 74.81 mm (RIB_CLEARANCE 0.32;
# the cup wall follows, 69.81 mm across).
RIB_CLEARANCE = 0.32        # 3.2 mm across under PIPE_ID -> rib tips 74.81 mm across
BASE_FLANGE_H = 0.3
BASE_CUP_H = 3.6            # cup height above the flange
BASE_CUP_WALL = 0.15
BASE_FLOOR_H = 0.5          # floor thickness, measured from the plug's bottom face
RIB_COUNT = 6                # evenly spaced (confirmed by the user)
RIB_H, RIB_T = 0.25, 0.2    # radial height, tangential thickness
RIB_LEAD = 0.4              # sloped lead-in length at the open end of the cup
INNER_RIB_COUNT = 6         # support ribs from the socket to the cup wall, on the floor
INNER_RIB_T = 0.2
INNER_RIB_OFFSET = 30.0     # degrees; 30 puts each one midway between two wedge ribs
# Socket: the hole the spike's collar goes into. The hole is set directly by BORE_D, and the
# socket's outside by SOCKET_OD, so changing either never moves the other: the wall
# ((SOCKET_OD - BORE_D) / 2) is only a result. Not derived from the modeled collar.
# Test prints, bore diameter: 24.9 -> 28.9 -> 26.9 -> 24.1 -> 25.5 mm (too small for the stake).
# Reference print: 28.9 mm was almost right, only needed 0.5 mm less -> 28.4 mm.
# Then almost perfect but the stake was a little loose: 0.3 mm smaller -> 28.1 mm.
# Then the stake still had a bit of play: 0.3 mm smaller again -> 27.8 mm.
# Then still a little loose: 0.2 mm smaller again -> 27.6 mm.
# Then almost perfect but a touch loose: 0.2 mm smaller again -> 27.4 mm.
# Then still loose: 0.3 mm smaller again -> 27.1 mm.
BORE_D = 2.71
SOCKET_OD = 3.49            # as in the 28.9 reference print, so the wall is 3.9 mm
SOCKET_H = 2.6

# Spike: cross fins with a round collar that slides into the plug's socket
# The modeled collar is an old estimate (not measured). The spike is deliberately left
# unmodified, so it is now larger than BORE_D; only the plug's hole follows test prints.
COLLAR_D = 2.64
COLLAR_H = SOCKET_H
SOCKET_ID = BORE_D
FIN_SPAN, FIN_T, FIN_TIP_SPAN = 2.2, 0.3, 0.3

# Layout: parts are stacked along Z in assembly order (spike, plug, light) with this
# gap between one part's top and the next part's bottom. 0 = assembled.
EXPLODE_GAP = 20.0

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    us = scene.unit_settings
    us.system = "METRIC"
    us.scale_length = 1.0
    us.length_unit = "MILLIMETERS"
    return scene


def material(name, color, metallic=0.0, roughness=0.5, transmission=0.0, ior=1.45, emission=None, strength=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Transmission Weight"].default_value = transmission
    bsdf.inputs["IOR"].default_value = ior
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1.0)
        bsdf.inputs["Emission Strength"].default_value = strength
    mat.diffuse_color = (*color, 1.0)  # viewport / workbench color
    return mat


def new_faces(bm, before):
    return [f for f in bm.faces if f not in before]


def add_cylinder(bm, mat_index, z0, z1, r0, r1=None, segments=64):
    """Add a capped cylinder/cone between z0 and z1 (cm) with flat caps and smooth sides."""
    r1 = r0 if r1 is None else r1
    depth = z1 - z0
    verts = bmesh.ops.create_cone(
        bm, cap_ends=True, cap_tris=False, segments=segments,
        radius1=r0 * CM, radius2=r1 * CM, depth=depth * CM,
        matrix=Matrix.Translation((0, 0, (z0 + depth / 2) * CM)),
    )["verts"]
    faces = {f for v in verts for f in v.link_faces}
    for f in faces:
        f.material_index = mat_index
        f.smooth = len(f.verts) == 4  # sides smooth, n-gon caps flat
    return faces


def add_tube(bm, mat_index, z0, z1, outer_r, inner_r, segments=64):
    """Add a closed tube between z0 and z1 (cm). outer_r is a radius or a function of angle."""
    outer = outer_r if callable(outer_r) else (lambda a: outer_r)
    rings = []
    for z in (z0, z1):
        for r_at in (outer, lambda a: inner_r):
            rings.append([
                bm.verts.new((r_at(a) * math.cos(a) * CM, r_at(a) * math.sin(a) * CM, z * CM))
                for a in (2 * math.pi * i / segments for i in range(segments))
            ])
    ob, ib, ot, it = rings
    walls, ends = [], []
    for i in range(segments):
        j = (i + 1) % segments
        walls.append(bm.faces.new((ob[i], ob[j], ot[j], ot[i])))
        walls.append(bm.faces.new((ib[i], it[i], it[j], ib[j])))
        ends.append(bm.faces.new((ot[i], ot[j], it[j], it[i])))
        ends.append(bm.faces.new((ob[i], ib[i], ib[j], ob[j])))
    for f in walls + ends:
        f.material_index = mat_index
        f.smooth = f in walls
    bmesh.ops.recalc_face_normals(bm, faces=walls + ends)


def add_lathe(bm, mat_index, profile, segments=64):
    """Revolve a closed (r, z) profile in cm around Z into a watertight solid."""
    before = set(bm.faces)
    verts = [bm.verts.new((r * CM, 0.0, z * CM)) for r, z in profile]
    edges = [bm.edges.new((verts[i], verts[(i + 1) % len(verts)])) for i in range(len(verts))]
    bmesh.ops.spin(bm, geom=verts + edges, cent=(0, 0, 0), axis=(0, 0, 1),
                   angle=2 * math.pi, steps=segments, use_merge=True)
    faces = new_faces(bm, before)
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    for f in faces:
        f.material_index = mat_index
        f.smooth = abs(f.normal.z) < 0.5  # walls smooth, flat rings/floors flat


def add_cross_loft(bm, mat_index, levels, thickness):
    """Loft a '+' cross section through (z, span) levels in cm into a capped solid."""
    t = thickness / 2
    rings = []
    for z, span in levels:
        a = span / 2
        outline = [(t, a), (-t, a), (-t, t), (-a, t), (-a, -t), (-t, -t),
                   (-t, -a), (t, -a), (t, -t), (a, -t), (a, t), (t, t)]
        rings.append([bm.verts.new((x * CM, y * CM, z * CM)) for x, y in outline])
    faces = [bm.faces.new(rings[0][::-1]), bm.faces.new(rings[-1])]
    for lo, hi in zip(rings, rings[1:]):
        n = len(lo)
        faces += [bm.faces.new((lo[i], lo[(i + 1) % n], hi[(i + 1) % n], hi[i])) for i in range(n)]
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    for f in faces:
        f.material_index = mat_index
        f.smooth = False


def add_wedge_ribs(bm, mat_index, count, r_root, r_surface, r_tip, z0, z1, lead, thickness):
    """Add axial ribs on a cylinder wall: full height r_tip from z0, sloping back to the
    wall surface over the last `lead` cm before z1. r_root sits inside the wall so the
    ribs overlap it for a boolean union. Rib corners lie exactly on each radius (the
    flat outer face doesn't poke past r_tip)."""
    profile = [(r_root, z0), (r_tip, z0), (r_tip, z1 - lead), (r_surface, z1), (r_root, z1)]
    faces = []
    for k in range(count):
        a = 2 * math.pi * k / count
        ca, sa = math.cos(a), math.sin(a)
        sides = [[bm.verts.new(((math.sqrt(r * r - t * t) * ca - t * sa) * CM,
                                (math.sqrt(r * r - t * t) * sa + t * ca) * CM, z * CM)) for r, z in profile]
                 for t in (-thickness / 2, thickness / 2)]
        n = len(profile)
        faces += [bm.faces.new(sides[0][::-1]), bm.faces.new(sides[1])]
        faces += [bm.faces.new((sides[0][i], sides[0][(i + 1) % n], sides[1][(i + 1) % n], sides[1][i]))
                  for i in range(n)]
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    for f in faces:
        f.material_index = mat_index
        f.smooth = False


def add_radial_ribs(bm, mat_index, count, r0, r1, z0, z1, thickness, offset_deg=0.0):
    """Add flat radial ribs (boxes) spanning r0..r1 and z0..z1 (cm), evenly spaced."""
    faces = []
    t = thickness / 2
    for k in range(count):
        a = math.radians(offset_deg) + 2 * math.pi * k / count
        ca, sa = math.cos(a), math.sin(a)
        v = [bm.verts.new(((r * ca - w * sa) * CM, (r * sa + w * ca) * CM, z * CM))
             for z in (z0, z1) for r in (r0, r1) for w in (-t, t)]
        # v index = z*4 + r*2 + w
        quads = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
        faces += [bm.faces.new([v[i] for i in q]) for q in quads]
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    for f in faces:
        f.material_index = mat_index
        f.smooth = False


def mesh_from_bmesh(bm, name, mats):
    bm.normal_update()
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for mat in mats:
        mesh.materials.append(mat)
    return mesh


def build_body_mesh(mats):
    """Cap, lens, LED/solar modules and hollow pipe. Built in assembly coordinates."""
    m = {mat.name: i for i, mat in enumerate(mats)}
    bm = bmesh.new()
    r = BODY_D / 2

    # Hollow stainless pipe, resting on the base plug's flange
    add_tube(bm, m["Glosola_Steel_Black"], MATING_Z + BASE_FLANGE_H, LENS_Z0, r, PIPE_ID / 2)

    # LED module on top of the pipe, inside the lens
    inner_r = r - LENS_WALL
    add_cylinder(bm, m["Glosola_Module_White"], LENS_Z0, LENS_Z0 + 0.3, inner_r)
    add_cylinder(bm, m["Glosola_LED_3000K"], LENS_Z0 + 0.3, LENS_Z0 + 0.5, 0.5, segments=24)

    # Fluted acrylic lens: rounded vertical ribs, peaks on the body radius
    def fluted(a):
        return r - LENS_FLUTE_DEPTH * math.sin(LENS_FLUTES * a / 2) ** 2
    add_tube(bm, m["Glosola_Acrylic_Clear"], LENS_Z0, CAP_Z0, fluted, inner_r, segments=LENS_FLUTES * 8)

    # Solar cap: white PCB underside, black body, recessed round panel on top
    add_cylinder(bm, m["Glosola_Module_White"], CAP_Z0, CAP_Z0 + 0.3, inner_r)
    cap = add_cylinder(bm, m["Glosola_ABS_Black"], CAP_Z0 + 0.3, TOTAL_H, r)
    top = next(f for f in cap if len(f.verts) > 4 and f.normal.z > 0.5)
    bmesh.ops.inset_region(bm, faces=[top], thickness=PANEL_RIM * CM, depth=-PANEL_RECESS * CM)
    top.material_index = m["Glosola_Solar_Panel"]

    mesh = mesh_from_bmesh(bm, NAME, mats)
    mesh.transform(Matrix.Translation((0, 0, -MATING_Z * CM)))  # origin on the mating plane
    return mesh


def union_bmeshes(scene, name, mat, bm_a, bm_b):
    """Boolean-union two bmeshes (EXACT solver) into one watertight mesh datablock."""
    a = bpy.data.objects.new("_union_a", mesh_from_bmesh(bm_a, "_union_a", [mat]))
    b = bpy.data.objects.new("_union_b", mesh_from_bmesh(bm_b, "_union_b", [mat]))
    scene.collection.objects.link(a)
    scene.collection.objects.link(b)
    union = a.modifiers.new("Union", "BOOLEAN")
    union.operation = "UNION"
    union.solver = "EXACT"
    union.object = b
    mesh = bpy.data.meshes.new_from_object(a.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    mesh.name = name
    # The union leaves a few zero-length edges / zero-area slivers where faces meet;
    # dissolve anything under 0.001 mm so the part checks clean for 3D printing
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.dissolve_degenerate(bm, dist=0.001 * 0.1 * CM, edges=bm.edges[:])
    bm.to_mesh(mesh)
    bm.free()
    for tmp in (a, b):
        tmp_mesh = tmp.data
        bpy.data.objects.remove(tmp)
        bpy.data.meshes.remove(tmp_mesh)
    return mesh


def build_base_mesh(mat, scene):
    """Flanged cup plug with a molded center socket and wedge ribs, as one watertight mesh."""
    r = BODY_D / 2
    rib_tip = (PIPE_ID - RIB_CLEARANCE) / 2
    wall_or = rib_tip - RIB_H
    wall_ir = wall_or - BASE_CUP_WALL
    top = BASE_FLANGE_H + BASE_CUP_H
    sock_ir, sock_or = SOCKET_ID / 2, SOCKET_OD / 2
    profile = [
        (sock_ir, 0.0), (r, 0.0), (r, BASE_FLANGE_H), (wall_or, BASE_FLANGE_H), (wall_or, top),
        (wall_ir, top), (wall_ir, BASE_FLOOR_H), (sock_or, BASE_FLOOR_H), (sock_or, SOCKET_H), (sock_ir, SOCKET_H),
    ]
    cup_bm = bmesh.new()
    add_lathe(cup_bm, 0, profile)
    ribs_bm = bmesh.new()
    # Lead-ins end 0.05 mm inside the wall: the wall is a 64-gon, so ending exactly on the
    # true radius would leave hair-thin flaps between its corners
    add_wedge_ribs(ribs_bm, 0, RIB_COUNT, wall_or - BASE_CUP_WALL / 2, wall_or - 0.005, rib_tip,
                   BASE_FLANGE_H - 0.05, top, RIB_LEAD, RIB_T)
    # Support ribs: overlap halfway into the socket wall and cup wall so they union, but
    # never reach the socket bore (sock_ir), which stays clear for the spike collar
    add_radial_ribs(ribs_bm, 0, INNER_RIB_COUNT, (sock_ir + sock_or) / 2, wall_ir + BASE_CUP_WALL / 2,
                    BASE_FLOOR_H - 0.05, SOCKET_H, INNER_RIB_T, INNER_RIB_OFFSET)
    return union_bmeshes(scene, f"{NAME}_Base", mat, cup_bm, ribs_bm)


def build_spike_mesh(mat, scene):
    """Cross-finned spike with a round collar on top, unioned into one watertight mesh."""
    exposed = MATING_Z  # length below the base plug
    fins_bm = bmesh.new()
    add_cross_loft(fins_bm, 0, [(0.0, FIN_TIP_SPAN), (SPIKE_TAPER_Z, FIN_SPAN), (exposed + COLLAR_H / 2, FIN_SPAN)], FIN_T)
    collar_bm = bmesh.new()
    add_cylinder(collar_bm, 0, exposed, exposed + COLLAR_H, COLLAR_D / 2, segments=48)
    return union_bmeshes(scene, f"{NAME}_Spike", mat, fins_bm, collar_bm)


def world_bounds(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    lo = Vector(tuple(min(p[i] for p in pts) for i in range(3)))
    hi = Vector(tuple(max(p[i] for p in pts) for i in range(3)))
    return (hi - lo) / CM


def z_range(obj):
    zs = [(obj.matrix_world @ Vector(c)).z / CM for c in obj.bound_box]
    return min(zs), max(zs)


def explode_along_z(objs, gap):
    """Move each object up so it sits `gap` cm above the top of the one below it.
    Objects keep their assembly order; shifts are applied parents first."""
    ordered = sorted(objs, key=lambda o: z_range(o)[0])
    assembled = {o: o.matrix_world.copy() for o in objs}
    shifts, prev_top = {}, None
    for o in ordered:
        lo, hi = z_range(o)
        shifts[o] = 0.0 if prev_top is None else prev_top + gap - lo
        prev_top = hi + shifts[o]
    for o in sorted(objs, key=lambda o: o.parent is not None):
        mw = assembled[o].copy()
        mw.translation.z += shifts[o] * CM
        o.matrix_world = mw
        bpy.context.view_layer.update()


def main():
    scene = reset_scene()

    mats = [
        material("Glosola_Steel_Black", (0.025, 0.025, 0.025), metallic=0.6, roughness=0.45),
        material("Glosola_ABS_Black", (0.02, 0.02, 0.02), roughness=0.5),
        material("Glosola_Acrylic_Clear", (0.95, 0.95, 0.95), roughness=0.05, transmission=1.0, ior=1.49),
        material("Glosola_Solar_Panel", (0.02, 0.03, 0.06), metallic=0.3, roughness=0.12),
        material("Glosola_Module_White", (0.85, 0.85, 0.85), roughness=0.4),
        material("Glosola_LED_3000K", (1.0, 0.75, 0.45), emission=(1.0, 0.71, 0.42), strength=8.0),
    ]
    abs_black = mats[1]

    coll = bpy.data.collections.new(NAME)
    scene.collection.children.link(coll)

    body = bpy.data.objects.new(NAME, build_body_mesh(mats))
    body.location = (0, 0, MATING_Z * CM)
    coll.objects.link(body)  # no Bevel modifier: it lowers the narrow rim around the panel recess

    # Separate parts, parented to the body at their assembled positions (local offsets)
    parts = [
        (f"{NAME}_Base", build_base_mesh(abs_black, scene), 0.0),
        (f"{NAME}_Spike", build_spike_mesh(abs_black, scene), -MATING_Z),
    ]
    objs = [body]
    for name, mesh, z in parts:
        obj = bpy.data.objects.new(name, mesh)
        obj.parent = body
        obj.location = (0, 0, z * CM)
        coll.objects.link(obj)
        objs.append(obj)

    bpy.context.view_layer.update()
    for obj in objs:
        d = obj.dimensions / CM * MM_PER_CM
        print(f"[{NAME}] {obj.name} dimensions (mm): X={d.x:.2f} Y={d.y:.2f} Z={d.z:.2f}")
    d = world_bounds(objs) * MM_PER_CM
    print(f"[{NAME}] assembled dimensions (mm): X={d.x:.2f} Y={d.y:.2f} Z={d.z:.2f}")

    if EXPLODE_GAP > 0:
        explode_along_z(objs, EXPLODE_GAP)
        ordered = sorted(objs, key=lambda o: z_range(o)[0])
        for below, above in zip(ordered, ordered[1:]):
            print(f"[{NAME}] gap {below.name} -> {above.name}: {(z_range(above)[0] - z_range(below)[1]) * MM_PER_CM:.2f} mm")
        for o in ordered:
            lo, hi = z_range(o)
            print(f"[{NAME}] layout {o.name}: z {lo * MM_PER_CM:.2f} to {hi * MM_PER_CM:.2f} mm")

    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"{NAME}.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print(f"[{NAME}] saved {path}")


if __name__ == "__main__":
    main()

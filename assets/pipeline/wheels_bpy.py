"""Assemble wheels (SDF rim + caliper, modelled tyre and drilled disc) in bpy."""
import bpy, bmesh, numpy as np, math
from mathutils import Matrix, Vector
import studio, sdf, wheel, meshio

def tyre_mesh(name, R=0.340, W=0.255, seat=0.258, segs=384):
    hw = W / 2
    # profile (r, a) from inboard bead over the tread to outboard bead
    prof = []
    side = [(seat, -hw + 0.010), (seat + 0.008, -hw - 0.002), (seat + 0.03, -hw - 0.005), (R - 0.035, -hw - 0.004),
            (R - 0.014, -hw + 0.003), (R - 0.004, -hw + 0.014)]
    prof += side
    # tread with 3 circumferential grooves
    grooves = [-0.065 * W / 0.255, 0.0, 0.060 * W / 0.255]
    a_vals = np.linspace(-hw + 0.022, hw - 0.022, 60)
    for a in a_vals:
        r = R - 0.002 * (2 * a / W) ** 2
        for g in grooves:
            if abs(a - g) < 0.0055: r = R - 0.007
        prof.append((r, a))
    prof += [(r, -a) for (r, a) in side[::-1]]
    bm = bmesh.new()
    ring0 = [bm.verts.new((r, 0.0, a)) for (r, a) in prof]
    rings = [ring0]
    for i in range(1, segs):
        t = 2 * math.pi * i / segs
        c, s = math.cos(t), math.sin(t)
        rings.append([bm.verts.new((r * c, r * s, a)) for (r, a) in prof])
    n = len(prof)
    for i in range(segs):
        A, B = rings[i], rings[(i + 1) % segs]
        for j in range(n - 1):
            bm.faces.new([A[j], A[j + 1], B[j + 1], B[j]])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    return ob

def disc_mesh(name, R=0.205, r_in=0.120, T=0.036, a0=-0.050):
    # vented disc: two friction plates + vanes, cross-drilled holes via boolean
    bpy.ops.mesh.primitive_cylinder_add(vertices=256, radius=R, depth=T, location=(0, 0, a0))
    d = bpy.context.object; d.name = name
    bpy.ops.mesh.primitive_cylinder_add(vertices=128, radius=r_in, depth=T + 0.01, location=(0, 0, a0))
    hole = bpy.context.object
    m = d.modifiers.new('bore', 'BOOLEAN'); m.object = hole; m.operation = 'DIFFERENCE'
    bpy.context.view_layer.objects.active = d; bpy.ops.object.modifier_apply(modifier='bore')
    bpy.data.objects.remove(hole)
    # vent slot ring (dark gap visible at the disc edge)
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=0.0001, location=(0, 0, a0))
    bpy.data.objects.remove(bpy.context.object)
    # cross-drilled holes: 3 rows x 24, staggered
    holes = []
    for row, rr in enumerate([0.145, 0.165, 0.185]):
        for k in range(24):
            t = 2 * math.pi * (k + row / 3) / 24
            bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.0035, depth=T + 0.02, location=(rr * math.cos(t), rr * math.sin(t), a0))
            holes.append(bpy.context.object)
    bpy.ops.object.select_all(action='DESELECT')
    for h in holes: h.select_set(True)
    bpy.context.view_layer.objects.active = holes[0]; bpy.ops.object.join()
    H = bpy.context.object
    m = d.modifiers.new('drill', 'BOOLEAN'); m.object = H; m.operation = 'DIFFERENCE'; m.solver = 'EXACT'
    bpy.context.view_layer.objects.active = d; bpy.ops.object.modifier_apply(modifier='drill')
    bpy.data.objects.remove(H)
    bv = d.modifiers.new('bev', 'BEVEL'); bv.width = 0.0008; bv.segments = 2; bv.limit_method = 'ANGLE'
    # aluminium bell (hat)
    bpy.ops.mesh.primitive_cylinder_add(vertices=128, radius=0.122, depth=0.060, location=(0, 0, a0 + 0.035))
    hat = bpy.context.object; hat.name = name + '_hat'
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.105, depth=0.07, location=(0, 0, a0 + 0.030))
    inner = bpy.context.object
    m = hat.modifiers.new('cut', 'BOOLEAN'); m.object = inner; m.operation = 'DIFFERENCE'
    bpy.context.view_layer.objects.active = hat; bpy.ops.object.modifier_apply(modifier='cut')
    bpy.data.objects.remove(inner)
    return d, hat

_cache = {}
def sdf_part(key, fn, bounds, vox):
    if key not in _cache:
        V, F = sdf.mesh_sdf(fn, bounds, vox=vox, block=96, band=4, label=key)
        N, F = meshio.orient(V, F, fn)
        _cache[key] = (V, F, N)
    return _cache[key]

def materials():
    M = {}
    M['rim'] = studio.mat('rim_forged', (0.06, 0.062, 0.066), metallic=1.0, rough=0.38, coat=0.5, coat_rough=0.12)
    M['tyre'] = studio.mat('tyre', (0.022, 0.022, 0.022), rough=0.88)
    M['disc'] = studio.mat('disc_ccm', (0.10, 0.10, 0.10), metallic=0.4, rough=0.55)
    M['hat'] = studio.mat('disc_hat', (0.55, 0.56, 0.58), metallic=1.0, rough=0.35)
    M['caliper'] = studio.mat('caliper', (0.75, 0.03, 0.02), rough=0.35, coat=1.0)
    return M

def place(objs, x, y, z, side, scale_a=1.0, spin=0.0):
    """Local wheel frame (u,v,a) -> world. Left (side=+1): a -> +y. Right: mirrored."""
    # map u->x, v->z, a->y*side
    M = Matrix(((1, 0, 0, 0), (0, 0, side * scale_a, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
    T = Matrix.Translation((x, y, z))
    S = Matrix.Rotation(spin, 4, 'Z')
    for o in objs:
        o.matrix_world = T @ M @ S
        if side < 0:  # mirrored transform flips winding: fix normals by flipping mesh once
            pass

_shared = {}
def _link(src, name):
    o = bpy.data.objects.new(name, src.data); bpy.context.scene.collection.objects.link(o)
    return o

def build_wheels(XF, XR, RF, RR, TF, TR, M):
    rimV = sdf_part('rim', wheel.rim, ((-0.27,0.27),(-0.27,0.27),(-0.13,0.125)), 0.0015)
    calV = sdf_part('cal', wheel.caliper, ((-0.05,0.25),(-0.05,0.25),(-0.10,0.0)), 0.0015)
    out = []
    for (x, R, T, W, sa) in [(XF, RF, TF, 0.255, 1.0), (XR, RR, TR, 0.305, 1.12)]:
        for side in (1, -1):
            tag = f"{'F' if x > 0 else 'R'}{'L' if side > 0 else 'R'}"
            if 'rim' not in _shared: _shared['rim'] = studio.mesh_from_arrays('rim_' + tag, *rimV[:2], rimV[2], mats=[M['rim']])
            rim = _shared['rim'] if _shared['rim'].name == 'rim_' + tag else _link(_shared['rim'], 'rim_' + tag)
            ty = tyre_mesh('tyre_' + tag, R=R, W=W, seat=0.258)
            ty.data.materials.append(M['tyre'])
            disc, hat = disc_mesh('disc_' + tag)
            disc.data.materials.clear(); hat.data.materials.clear()
            disc.data.materials.append(M['disc']); hat.data.materials.append(M['hat'])
            # caliper sits behind the axle: rotate so it faces rearward/up
            if 'cal' not in _shared: _shared['cal'] = studio.mesh_from_arrays('cal_' + tag, *calV[:2], calV[2], mats=[M['caliper']])
            cal = _shared['cal'] if _shared['cal'].name == 'cal_' + tag else _link(_shared['cal'], 'cal_' + tag)
            # caliper angle: front axle -> toward rear (u negative). caliper modelled at +35deg; rotate by 110deg about axis
            place([rim, ty, disc, hat], x, side * T, R, side, sa, spin=0.0)
            place([cal], x, side * T, R, side, sa, spin=math.radians(110 if side > 0 else 110))
            out += [rim, ty, disc, hat, cal]
    # flip normals on mirrored objects (negative determinant)
    for o in out:
        if o.matrix_world.determinant() < 0 and o.data.users == 1:
            bm = bmesh.new(); bm.from_mesh(o.data)
            bmesh.ops.reverse_faces(bm, faces=bm.faces); bm.to_mesh(o.data); bm.free()
            if o.data.has_custom_normals:
                pass
    return out

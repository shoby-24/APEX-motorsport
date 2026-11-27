"""Import the McLaren P1 GTR 2015 FBX (user-supplied, see assets/LICENSES.json) and normalise it to the GLB asset contract.

Raw file: length along Blender -Y (front at -Y), ~2x scale, ground at z=-1.14, Russian material names.
Output: <OUT>/p1_full.blend with root `mclaren_p1_gtr_2015`, body, wheel_*/caliper_* (origin at hub), part_* under socket_* empties.
"""
import bpy, sys, os, math, mathutils
FBX = os.environ['FBX']; OUT = os.environ.get('OUT', os.path.join(os.environ.get('APEX_WORK', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'build')), 'p1')); os.makedirs(OUT, exist_ok=True)
TEX = os.environ.get('TEX', '')
ROOT = 'mclaren_p1_gtr_2015'

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=FBX)
if TEX:  # relink textures that the FBX references by bare name
    for im in bpy.data.images:
        for f in os.listdir(TEX):
            if os.path.splitext(f)[0].startswith(os.path.splitext(os.path.basename(im.filepath or im.name))[0][:20]):
                im.filepath = os.path.join(TEX, f); break
for o in list(bpy.data.objects):
    if o.name.startswith('Референс'): bpy.data.objects.remove(o)

# bake hierarchy transforms into mesh data, drop empties
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
for o in meshes:
    mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
for o in list(bpy.data.objects):
    if o.type != 'MESH': bpy.data.objects.remove(o)
for o in meshes:
    if o.data.users > 1: o.data = o.data.copy()
    o.data.transform(o.matrix_world); o.matrix_world = mathutils.Matrix.Identity(4)

# raw-space wheel centres from the tyres (Object_35*)
def bbox(o):
    xs = [v.co for v in o.data.vertices]
    return mathutils.Vector([min(v[i] for v in xs) for i in range(3)]), mathutils.Vector([max(v[i] for v in xs) for i in range(3)])
tyres = [o for o in meshes if o.name.startswith('Object_35')]
ground = min(bbox(o)[0].z for o in tyres)
cent = {o.name: (bbox(o)[0] + bbox(o)[1]) / 2 for o in tyres}
S = float(os.environ.get('SCALE', '0.5'))
ymid = (min(c.y for c in cent.values()) + max(c.y for c in cent.values())) / 2
# raw (x, y, z) -> car (x fwd, y left, z up): front is raw -Y, so x = -(y - ymid); raw +X is the car's left? -> y = x
M = mathutils.Matrix(((0, -S, 0, S * ymid), (S, 0, 0, 0), (0, 0, S, -S * ground), (0, 0, 0, 1)))
for o in meshes:
    o.data.transform(M)
    if M.determinant() < 0: o.data.flip_normals()
def corner(c):
    p = M @ c
    return ('f' if p.x > 0 else 'r') + ('l' if p.y > 0 else 'r'), p
hubs = {}
for n, c in cent.items():
    k, p = corner(c); hubs[k] = p
print('HUBS', {k: tuple(round(a, 3) for a in v) for k, v in hubs.items()})

def which_corner(o):
    lo, hi = bbox(o); c = (lo + hi) / 2
    return min(hubs, key=lambda k: (hubs[k].x - c.x) ** 2 + (hubs[k].y - c.y) ** 2)

# ---- materials -> contract slots ----
SLOT = {
    # purple livery panels
    **{n: 'paint_body' for n in ['Материал.005', 'Материал.008', 'Материал.014', 'Материал.016', 'Материал.024', 'Материал.038', 'Материал.040']},
    # black panels are the P1 GTR's second livery colour
    **{n: 'paint_accent' for n in ['Материал', 'Материал.001', 'Материал.002', 'Материал.003', 'Материал.006', 'Материал.007', 'Материал.009',
                                   'Материал.012', 'Материал.013', 'Материал.020', 'Материал.022', 'Материал.023', 'Материал.029', 'Материал.035', 'Материал.037']},
    'Материал.017': 'carbon', 'Материал.036': 'carbon',
    'Материал.010': 'trim_black', 'Материал.034': 'trim_black', 'Материал.032': 'lamp_housing',
    'Материал.011': 'glass', 'Материал.018': 'glass', 'Материал.004': 'lens_clear',
    'Материал.031': 'emissive_drl', 'Материал.033': 'lens_clear', 'Материал.030': 'lens_red', 'Материал.039': 'emissive_tail',
    'Материал.041': 'mirror_glass', 'Материал.026': 'titanium', 'Материал.027': 'trim_black', 'Материал.028': 'titanium',
    'Материал.015': 'rim', 'Материал.021': 'disc', 'Материал.019': 'titanium',
    'Material.005': 'tyre', 'Material.006': 'tyre', 'Material.007': 'tyre',
    'CRBN_JANTE.002': 'rim', 'Material.012': 'rim', 'Material.013': 'rim', 'Material.014': 'rim',
}
SLOT.update(dict(kv.split('=') for kv in os.environ.get('SLOT_OVERRIDE', '').split(',') if kv))
slot_mats = {}
def slot_mat(s):
    if s not in slot_mats:
        m = bpy.data.materials.new(s); m.use_nodes = True; slot_mats[s] = m
    return slot_mats[s]
for o in meshes:
    for i, ms in enumerate(o.material_slots):
        n = ms.material.name if ms.material else ''
        s = SLOT.get(n)
        # Vert.006 carries the tyre-named grey on the body: treat as paint
        if n == 'Material.005' and not o.name.startswith('Object_35'): s = 'paint_body'
        if s is None: print('UNMAPPED', o.name, n); s = 'trim_black'
        keep = ms.material if (ms.material and ms.material.use_nodes and any(nd.type == 'TEX_IMAGE' for nd in ms.material.node_tree.nodes)) else None
        if keep is not None and s in ('tyre', 'rim', 'carbon'):
            o.material_slots[i].material = None; o.data.materials[i] = slot_mat(s)
            slot_mats[s]['src_tex'] = [nd.image.filepath for nd in keep.node_tree.nodes if nd.type == 'TEX_IMAGE' and nd.image][0]
        else:
            o.data.materials[i] = slot_mat(s)

# ---- grouping ----

# ---- calipers: the FBX has none, so fit our own six-piston caliper (assets/pipeline wheel.py, cal.npz) to each disc ----
import numpy as np
CAL = os.environ['CAL_NPZ']
cd = np.load(CAL); CV, CF = cd['V'], cd['F']
for o in meshes:
    if o.name in ['Окружность'] + ['Окружность.%03d' % i for i in range(1, 8)] and o.data.materials[0].name == 'disc':
        k = which_corner(o); h = hubs[k]; side = 1 if k[1] == 'l' else -1
        lo, hi = bbox(o); R = (hi.z - lo.z) / 2; ay = (lo.y + hi.y) / 2
        sc = R / 0.205; spin = math.radians(110)
        u, v, a = CV[:, 0], CV[:, 1], CV[:, 2]
        u2 = (u * math.cos(spin) - v * math.sin(spin)) * sc; v2 = (u * math.sin(spin) + v * math.cos(spin)) * sc
        X = np.stack([h.x + u2, ay + side * (a + 0.05) * sc, h.z + v2], 1).astype(np.float32)
        F = CF[:, ::-1] if side < 0 else CF
        me = bpy.data.meshes.new('caliper_' + k); me.from_pydata(X.tolist(), [], F.tolist()); me.shade_smooth()
        me.materials.append(slot_mat('caliper'))
        c = bpy.data.objects.new('caliper_' + k, me); bpy.context.scene.collection.objects.link(c); meshes.append(c)
        print('CALIPER', k, 'R=%.3f' % R, 'axial=%.3f' % ay)

# ---- PBR values per slot (glTF-friendly: factors + the model's own image textures) ----
PBR = {  # base colour (linear), metallic, roughness, coat, transmission, emission
    'paint_body': ((0.11, 0.0, 0.42), 0.6, 0.30, 1.0, 0, None), 'paint_accent': ((0.012, 0.012, 0.014), 0.3, 0.28, 1.0, 0, None),
    'carbon': ((0.02, 0.02, 0.022), 0.0, 0.3, 1.0, 0, None), 'trim_black': ((0.012, 0.012, 0.012), 0.0, 0.45, 0.3, 0, None),
    'lamp_housing': ((0.08, 0.08, 0.085), 1.0, 0.18, 0, 0, None), 'glass': ((0.05, 0.055, 0.06), 0.0, 0.02, 0, 0.0, None),
    'lens_clear': ((0.9, 0.9, 0.9), 0.0, 0.02, 0, 1.0, None), 'lens_red': ((0.5, 0.01, 0.01), 0.0, 0.05, 0, 0.9, None),
    'emissive_drl': ((0.9, 0.9, 0.95), 0.0, 0.2, 0, 0, ((0.85, 0.9, 1.0), 6.0)), 'emissive_tail': ((0.5, 0.0, 0.0), 0.0, 0.2, 0, 0, ((1.0, 0.02, 0.01), 4.0)),
    'mirror_glass': ((0.9, 0.9, 0.9), 1.0, 0.02, 0, 0, None), 'titanium': ((0.45, 0.42, 0.40), 1.0, 0.3, 0, 0, None),
    'disc': ((0.10, 0.10, 0.10), 0.4, 0.55, 0, 0, None), 'caliper': ((0.75, 0.42, 0.01), 0.0, 0.35, 1.0, 0, None),
    'tyre': ((0.025, 0.025, 0.025), 0.0, 0.85, 0, 0, None), 'rim': ((0.05, 0.05, 0.055), 1.0, 0.35, 0.5, 0, None),
}
for s, m in slot_mats.items():
    c, met, r, coat, tr, em = PBR[s]
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*c, 1); b.inputs['Metallic'].default_value = met; b.inputs['Roughness'].default_value = r
    b.inputs['Coat Weight'].default_value = coat; b.inputs['Transmission Weight'].default_value = tr
    if em: b.inputs['Emission Color'].default_value = (*em[0], 1); b.inputs['Emission Strength'].default_value = em[1]
    if s == 'glass': b.inputs['Alpha'].default_value = 0.35; m.surface_render_method = 'BLENDED'
    if 'src_tex' in m and s in ('rim', 'carbon'):
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(m['src_tex'], check_existing=True)
        nt.links.new(t.outputs['Color'], b.inputs['Base Color'])

def group_of(o):
    n = o.name; m0 = o.data.materials[0].name if o.data.materials else ''
    if n.startswith('Object_35') or n.startswith('Object_37') or n in ('Цилиндр', 'Цилиндр.001', 'Цилиндр.002', 'Цилиндр.003') \
       or n in ['Окружность'] + ['Окружность.%03d' % i for i in range(1, 8)]:
        return 'wheel_' + which_corner(o)
    if n.startswith('caliper_'): return n
    if n in ('Плоскость', 'Куб'): return 'part_wing_p1_gtr'
    if n == 'Vert.025': return 'part_splitter_p1_gtr'
    if n in ('Окружность.008', 'Окружность.009', 'Цилиндр.004'): return 'part_exhaust_p1_gtr'
    if n == 'Vert.029': return 'part_mirrors_p1_gtr'
    return 'body'
groups = {}
for o in meshes: groups.setdefault(group_of(o), []).append(o)
print('GROUPS', {k: [o.name for o in v] for k, v in groups.items()})
def join(objs, name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1: bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active; o.name = name; o.data.name = name
    return o
J = {k: join(v, k) for k, v in groups.items()}
for k, o in J.items():
    if k.startswith('caliper_'):
        m = o.modifiers.new('dec', 'DECIMATE'); m.ratio = 0.13
        bpy.context.view_layer.objects.active = o; bpy.ops.object.modifier_apply(modifier='dec')
for o in J.values():
    o.data.shade_smooth() if hasattr(o.data, 'shade_smooth') else None
    bpy.context.view_layer.objects.active = o
    try: bpy.ops.object.shade_auto_smooth(angle=math.radians(35))
    except Exception as e: print('autosmooth', e)

def bounds_all(objs):
    lo = [min(bbox(o)[0][i] for o in objs) for i in range(3)]; hi = [max(bbox(o)[1][i] for o in objs) for i in range(3)]
    return lo, hi
SOCK = {'socket_wheel_' + k: tuple(v) for k, v in hubs.items()}
for k, part in (('socket_wing', 'part_wing_p1_gtr'), ('socket_splitter', 'part_splitter_p1_gtr'),
                ('socket_exhaust', 'part_exhaust_p1_gtr'), ('socket_mirrors', 'part_mirrors_p1_gtr')):
    lo, hi = bounds_all([J[part]]); SOCK[k] = ((lo[0] + hi[0]) / 2, 0.0, lo[2])
for k, o in J.items():
    if k.startswith(('wheel_', 'caliper_')):
        bpy.context.scene.cursor.location = hubs[k.split('_')[1]]
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
root = bpy.data.objects.new(ROOT, None); bpy.context.scene.collection.objects.link(root)
bpy.context.view_layer.update()
for s, loc in SOCK.items():
    e = bpy.data.objects.new(s, None); e.location = loc; bpy.context.scene.collection.objects.link(e); e.parent = root
for k, o in J.items():
    sock = {'part_wing_p1_gtr': 'socket_wing', 'part_splitter_p1_gtr': 'socket_splitter', 'part_exhaust_p1_gtr': 'socket_exhaust',
            'part_mirrors_p1_gtr': 'socket_mirrors'}.get(k)
    o.parent = bpy.data.objects[sock] if sock else root
    if sock: o.matrix_parent_inverse = mathutils.Matrix.Translation(-mathutils.Vector(SOCK[sock]))
lo, hi = bounds_all(list(J.values()))
print('DIMS L=%.3f W=%.3f H=%.3f WB=%.3f' % (hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2], hubs['fl'].x - hubs['rl'].x),
      'TRACK_F=%.3f TRACK_R=%.3f R=%.3f' % (hubs['fl'].y - hubs['fr'].y, hubs['rl'].y - hubs['rr'].y, hubs['fl'].z))
print('TRIS', {k: sum(len(p.vertices) - 2 for p in o.data.polygons) for k, o in J.items()})
bpy.ops.wm.save_as_mainfile(filepath=OUT + '/p1_full.blend')

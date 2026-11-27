"""Build the car without the studio, simplify into 3 LODs and export GLBs that follow docs/asset-contract.md.
Usage: python export_glb.py  (env: NPZ, OUT)"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, numpy as np, math, json
import studio, meshio, wheels_bpy, parts, interior, sdf
import body3 as body
NPZ = os.environ.get('NPZ', 'body.npz'); OUT = os.environ.get('OUT', '../build/glb')
os.makedirs(OUT, exist_ok=True)

SLOT_RENAME = {'rim_forged': 'rim', 'disc_ccm': 'disc', 'disc_hat': 'disc_hat', 'seat_fabric': 'interior_seat', 'alcantara': 'interior_alcantara',
               'led_white': 'emissive_drl', 'led_red': 'emissive_tail', 'amber': 'emissive_indicator', 'strap_red': 'strap', 'mirror': 'mirror_glass'}
TARGET = {'lod0': 450_000, 'lod1': 70_000, 'lod2': 14_000}

def build():
    studio.reset()
    d = np.load(NPZ); V, F = d['V'], d['F']
    N, F = meshio.orient(V, F, body.outer)
    lab = body.labels(V[F].mean(1))
    M = {k: studio.mat(k, c, metallic=m, rough=r, coat=cc) for k, c, m, r, cc in [
        ('paint_body', (0.72, 0.73, 0.75), 0.8, 0.30, 1.0), ('trim_black', (0.012,)*3, 0, 0.25, 0.6), ('carbon', (0.02,)*3, 0, 0.32, 1.0),
        ('lamp_housing', (0.08,)*3, 1, 0.18, 0), ('interior_trim', (0.03,)*3, 0, 0.7, 0), ('grille', (0.01,)*3, 0, 0.6, 0)]}
    studio.mesh_from_arrays('body', V, F, N, mats=[M[k] for k in body.SLOTS], mat_index=lab)
    for name, fn, bounds, mat in [('glass', body.glass, ((-2.0,0.2),(-0.85,0.85),(0.8,1.25)), studio.mat('glass', (0.6,0.65,0.65), rough=0.0, transmission=1.0, ior=1.5)),
                                  ('head_lens', body.head_lens, ((1.6,2.45),(-1.0,1.0),(0.3,0.9)), studio.mat('lens_clear', (1,1,1), rough=0.0, transmission=1.0)),
                                  ('tail_lens', body.tail_lens, ((-2.45,-1.9),(-1.05,1.05),(0.8,1.0)), studio.mat('lens_red', (0.6,0.02,0.02), rough=0.05, transmission=1.0))]:
        v, f = sdf.mesh_sdf(fn, bounds, vox=0.004, block=96, band=4, label=name)
        n, f = meshio.orient(v, f, fn); studio.mesh_from_arrays(name, v, f, n, mats=[mat])
    WM = wheels_bpy.materials()
    wheels_bpy.build_wheels(body.XF, body.XR, body.RF, body.RR, body.TF, body.TR, WM)
    parts.build(body, M)
    interior.build(body, M)

def apply_all():
    for o in list(bpy.data.objects):
        if o.type == 'CURVE':
            bpy.context.view_layer.objects.active = o; o.select_set(True)
            bpy.ops.object.convert(target='MESH'); o.select_set(False)
    for o in bpy.data.objects:
        if o.type == 'MESH':
            for m in list(o.modifiers):
                bpy.context.view_layer.objects.active = o
                bpy.ops.object.modifier_apply(modifier=m.name)

def flatten_materials():
    """glTF only carries factors + images: replace procedural graphs with their factor values; rename to slot names."""
    for m in bpy.data.materials:
        if not m.use_nodes: continue
        b = m.node_tree.nodes.get('Principled BSDF')
        for l in list(m.node_tree.links):
            if l.to_node == b and l.to_socket.name in ('Base Color', 'Normal', 'Metallic'):
                m.node_tree.links.remove(l)
        if m.name in SLOT_RENAME: m.name = SLOT_RENAME[m.name]

def group(name_of):
    """Return {group_name: [objects]} for wheels, calipers, parts, interior and body."""
    g = {}
    for o in bpy.data.objects:
        if o.type != 'MESH': continue
        g.setdefault(name_of(o), []).append(o)
    return g

def classify(o):
    n = o.name
    for t in ('FL', 'FR', 'RL', 'RR'):
        if n.endswith('_' + t) or n.endswith('_' + t + '_hat'):
            return ('caliper_' if n.startswith('cal_') else 'wheel_') + t.lower()
    if n.startswith(('seat', 'wheel_sw', 'dash', 'floor', 'cage', 'harness', 'btn', 'Cylinder', 'Plane')) or 'cage' in n or 'harness' in n:
        return 'interior'
    for p in ('splitter', 'canards'): 
        if n.startswith(p): return 'part_splitter_gt3'
    if n.startswith('wing'): return 'part_wing_swan_gt3'
    if n.startswith('exhaust'): return 'part_exhaust_side_twin'
    if n.startswith(('mirrors', 'mirror_glass')): return 'part_mirrors_race'
    return 'body'

def join(objs, name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1: bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active; o.name = name; o.data.name = name
    return o

def tri_count(o): return sum(len(p.vertices) - 2 for p in o.data.polygons)

def decimate(o, target):
    for _ in range(4):                      # collapse can undershoot on meshes with many islands: repeat
        t = tri_count(o)
        if t <= target * 1.1: break
        m = o.modifiers.new('dec', 'DECIMATE'); m.ratio = max(target / t, 0.002); m.use_collapse_triangulate = True
        bpy.context.view_layer.objects.active = o; bpy.ops.object.modifier_apply(modifier='dec')

SOCKETS = {'socket_wing': (-2.06, 0, 1.0), 'socket_splitter': (2.30, 0, 0.07), 'socket_exhaust': (-0.86, 0.985, 0.175),
           'socket_mirrors': (0.0, 0.9, 0.9), 'socket_wheel_fl': (body.XF, body.TF, body.RF), 'socket_wheel_fr': (body.XF, -body.TF, body.RF),
           'socket_wheel_rl': (body.XR, body.TR, body.RR), 'socket_wheel_rr': (body.XR, -body.TR, body.RR)}

def main():
    budget_share = {'body': 0.42, 'interior': 0.16, 'part_wing_swan_gt3': 0.05, 'part_splitter_gt3': 0.05, 'part_exhaust_side_twin': 0.01, 'part_mirrors_race': 0.01}
    if not (os.environ.get('REUSE') and os.path.exists(OUT + '/vanta_full.blend')):
        build(); apply_all(); flatten_materials()
        groups = {k: join(v, k) for k, v in group(classify).items()}
        # wheel pivots: move origin of each wheel/caliper to its hub centre so games can spin and steer them
        for k, o in groups.items():
            if k.startswith(('wheel_', 'caliper_')):
                c = SOCKETS['socket_wheel_' + k.split('_')[1]]
                bpy.context.scene.cursor.location = c
                bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
                bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        root = bpy.data.objects.new('aurion_vanta_gt3', None); bpy.context.scene.collection.objects.link(root)
        for s, loc in SOCKETS.items():
            e = bpy.data.objects.new(s, None); e.location = loc; bpy.context.scene.collection.objects.link(e); e.parent = root
        for k, o in groups.items():
            sock = {'part_wing_swan_gt3': 'socket_wing', 'part_splitter_gt3': 'socket_splitter', 'part_exhaust_side_twin': 'socket_exhaust',
                    'part_mirrors_race': 'socket_mirrors'}.get(k)
            o.parent = bpy.data.objects[sock] if sock else root
            if sock: o.matrix_parent_inverse = bpy.data.objects[sock].matrix_world.inverted()
        bpy.ops.wm.save_as_mainfile(filepath=OUT + '/vanta_full.blend')
    report = {}
    for lod, target in TARGET.items():
        if lod not in os.environ.get('LODS', 'lod0,lod1,lod2').split(','): continue
        bpy.ops.wm.open_mainfile(filepath=OUT + '/vanta_full.blend')
        for o in list(bpy.data.objects):
            if o.type != 'MESH': continue
            share = budget_share.get(o.name, 0.30 / 8)
            if lod != 'lod0' and o.name == 'interior':
                if lod == 'lod2': bpy.data.objects.remove(o); continue
                share = 0.06
            decimate(o, int(target * share))
        tris = {o.name: tri_count(o) for o in bpy.data.objects if o.type == 'MESH'}
        report[lod] = {'triangles': sum(tris.values()), 'objects': tris}
        path = f'{OUT}/{lod}.glb'
        bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', export_apply=True, export_yup=True,
                                  export_materials='EXPORT', export_normals=True)
        report[lod]['bytes'] = os.path.getsize(path)
    old = json.load(open(OUT + '/report.json')) if os.path.exists(OUT + '/report.json') else {}
    old.update(report); json.dump(old, open(OUT + '/report.json', 'w'), indent=1)
    print(json.dumps({k: (v['triangles'], v['bytes']) for k, v in report.items()}))

main()

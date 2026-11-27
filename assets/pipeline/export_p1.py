"""Export LOD0/1/2 GLBs of the imported P1 GTR (run import_p1.py first). One LOD per process: env LODS=lod0 etc."""
import bpy, os, json
OUT = os.environ.get('OUT', os.path.join(os.environ.get('APEX_WORK', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'build')), 'p1')); BLEND = OUT + '/p1_full.blend'
TARGET = {'lod0': 450000, 'lod1': 70000, 'lod2': 14000}
SHARE = {'body': 0.55, 'part_splitter_p1_gtr': 0.04, 'part_wing_p1_gtr': 0.03, 'part_mirrors_p1_gtr': 0.01, 'part_exhaust_p1_gtr': 0.01}
def tri(o): return sum(len(p.vertices) - 2 for p in o.data.polygons)
def decimate(o, target):
    for _ in range(4):
        t = tri(o)
        if t <= target * 1.1: break
        m = o.modifiers.new('dec', 'DECIMATE'); m.ratio = max(target / t, 0.002); m.use_collapse_triangulate = True
        bpy.context.view_layer.objects.active = o; bpy.ops.object.modifier_apply(modifier='dec')
report = {}
for lod in os.environ.get('LODS', 'lod0,lod1,lod2').split(','):
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    if lod != 'lod0':
        for o in bpy.data.objects:
            if o.type == 'MESH':
                share = SHARE.get(o.name, 0.06 if o.name.startswith('wheel_') else 0.0075)
                decimate(o, int(TARGET[lod] * share))
    tris = {o.name: tri(o) for o in bpy.data.objects if o.type == 'MESH'}
    path = f'{OUT}/{lod}.glb'
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', export_apply=True, export_yup=True, export_materials='EXPORT', export_normals=True)
    report[lod] = {'triangles': sum(tris.values()), 'objects': tris, 'bytes': os.path.getsize(path), 'budget': TARGET[lod]}
old = json.load(open(OUT + '/report.json')) if os.path.exists(OUT + '/report.json') else {}
old.update(report); json.dump(old, open(OUT + '/report.json', 'w'), indent=1)
print('REPORT', json.dumps({k: (v['triangles'], v['bytes']) for k, v in report.items()}))

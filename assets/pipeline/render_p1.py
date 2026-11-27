"""Studio renders of the imported P1 GTR (p1_full.blend). Env: BLEND, OUT, VIEWS, RES, SAMPLES, PAINT (linear rgb)."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, studio
BLEND = os.environ['BLEND']; OUT = os.environ['OUT']
VIEWS = os.environ.get('VIEWS', '34,side,rear,front').split(','); RES = [int(v) for v in os.environ.get('RES', '1280x720').split('x')]
SAMPLES = int(os.environ.get('SAMPLES', '48')); os.makedirs(OUT, exist_ok=True)
studio.reset(); studio.studio()
with bpy.data.libraries.load(BLEND, link=False) as (src, dst): dst.objects = src.objects
for o in dst.objects: bpy.context.scene.collection.objects.link(o)
if os.environ.get('PAINT'):
    c = tuple(float(v) for v in os.environ['PAINT'].split(','))
    bpy.data.materials['paint_body'].node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*c, 1)
# render-only flake on the paints (the GLB keeps plain factors)
for n in ('paint_body', 'paint_accent'):
    m = bpy.data.materials.get(n)
    if m: b = m.node_tree.nodes['Principled BSDF']; studio.car_paint(n, tuple(b.inputs['Base Color'].default_value[:3]), metallic=b.inputs['Metallic'].default_value, rough=b.inputs['Roughness'].default_value)
g = bpy.data.materials.get('glass')
if g:
    b = g.node_tree.nodes['Principled BSDF']; b.inputs['Alpha'].default_value = 1.0; b.inputs['Transmission Weight'].default_value = 1.0
    b.inputs['Base Color'].default_value = (0.55, 0.58, 0.6, 1); b.inputs['Roughness'].default_value = 0.0
views = {'34': ((5.6, 3.9, 1.05), (0.25, 0, 0.5), 45), 'side': ((0.0, 7.6, 0.70), (0, 0, 0.55), 40),
         'rear': ((-5.0, 3.9, 1.45), (-0.4, 0, 0.55), 45), 'front': ((5.8, -1.4, 0.95), (0.6, 0, 0.45), 45),
         'wheel': ((2.5, 2.05, 0.55), (1.31, 0.75, 0.33), 50), 'top': ((1.5, 2.2, 3.4), (0, 0, 0.6), 35),
         'cockpit': ((-0.6, 1.9, 1.35), (-0.3, 0.2, 0.7), 30)}
for k in VIEWS:
    loc, tgt, lens = views[k]; studio.camera(loc, tgt, lens); studio.render(f'{OUT}/{k}.png', RES[0], RES[1], samples=SAMPLES)

import sys, os, importlib; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, numpy as np, math
import studio, sdf, meshio, wheels_bpy
BODY = os.environ.get('BODY', 'body3'); NPZ = os.environ.get('NPZ', 'body.npz')
OUT = os.environ.get('OUT', '../build/renders'); VIEWS = os.environ.get('VIEWS', '34,side,rear,front').split(',')
RES = [int(v) for v in os.environ.get('RES', '1280x720').split('x')]; SAMPLES = int(os.environ.get('SAMPLES', '40'))
PARTS = os.environ.get('PARTS', '')
body = importlib.import_module(BODY)
os.makedirs(OUT, exist_ok=True)
d = np.load(NPZ); V, F = d['V'], d['F']
N, F = meshio.orient(V, F, body.outer)
lab = body.labels(V[F].mean(1))
s = studio.reset(); studio.studio()
PAINT = tuple(float(c) for c in os.environ.get('PAINT', '0.38,0.40,0.42').split(','))
M = {
 'paint_body': studio.car_paint('paint_body', PAINT),
 'trim_black': studio.mat('trim_black', (0.012,0.012,0.012), rough=0.25, coat=0.6),
 'carbon': studio.mat('carbon', (0.02,0.02,0.022), rough=0.35, coat=1.0),
 'lamp_housing': studio.mat('lamp_housing', (0.08,0.08,0.085), metallic=1, rough=0.18),
 'interior_trim': studio.mat('interior_trim', (0.03,0.03,0.03), rough=0.7),
 'grille': studio.mat('grille', (0.01,0.01,0.01), rough=0.6),
}
if os.environ.get('CARBON_TEX'):
    import materials; materials.upgrade(M)
studio.mesh_from_arrays('body', V, F, N, mats=[M[k] for k in body.SLOTS], mat_index=lab)
if os.environ.get('NO_GLOSSY_LIGHTS'):
    pass
for name, fn, bounds, m in [
    ('glass', body.glass, ((-2.0,0.2),(-0.85,0.85),(0.8,1.25)), studio.mat('glass', (0.6,0.65,0.65), rough=0.0, transmission=1.0, ior=1.5)),
    ('head_lens', body.head_lens, ((1.6,2.45),(-1.0,1.0),(0.3,0.9)), studio.mat('lens_clear', (1,1,1), rough=0.0, transmission=1.0, ior=1.5)),
    ('tail_lens', body.tail_lens, ((-2.45,-1.9),(-1.05,1.05),(0.8,1.0)), studio.mat('lens_red', (0.6,0.02,0.02), rough=0.05, transmission=1.0, ior=1.5))]:
    cache = f'{sdf.WORK}/cache_{BODY}_{name}.npz'
    if os.path.exists(cache) and os.path.getmtime(cache) > os.path.getmtime(NPZ):
        c = np.load(cache); v, f, n = c['V'], c['F'], c['N']
    else:
        v, f = sdf.mesh_sdf(fn, bounds, vox=0.0025, block=96, band=4, label=name)
        n, f = meshio.orient(v, f, fn); np.savez(cache, V=v, F=f, N=n)
    if len(v): studio.mesh_from_arrays(name, v, f, n, mats=[m])
WM = wheels_bpy.materials()
wheels_bpy.build_wheels(body.XF, body.XR, body.RF, body.RR, body.TF, body.TR, WM)
if PARTS:
    import parts; parts.build(body, M)
if os.environ.get('INTERIOR'):
    import interior; interior.build(body, M)
bpy.ops.wm.save_as_mainfile(filepath=OUT + '/scene.blend')
views = {'34': ((5.6, 3.9, 1.05), (0.25, 0, 0.55), 45), 'side': ((0.0, 7.6, 0.70), (0, 0, 0.58), 40),
         'rear': ((-5.0, 3.9, 1.45), (-0.4, 0, 0.6), 45), 'front': ((5.8, -1.4, 0.95), (0.6, 0, 0.5), 45),
         'wheel': ((XFw:=body.XF) + 1.25, body.TF + 1.35, 0.55, ) if False else ((body.XF + 1.2, body.TF + 1.3, 0.55), (body.XF, body.TF, 0.36), 50),
         'top': ((1.5, 2.2, 3.4), (0, 0, 0.6), 35), 'cockpit': ((-0.6, 1.9, 1.35), (-0.7, 0.2, 0.75), 30)}
for k in VIEWS:
    loc, tgt, lens = views[k]
    studio.camera(loc, tgt, lens)
    studio.render(f'{OUT}/{k}.png', RES[0], RES[1], samples=SAMPLES)

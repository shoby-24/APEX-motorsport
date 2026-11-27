"""GT3 aero + detail parts for the Vanta (SDF meshes + small bpy primitives)."""
import os, numpy as np, math, bpy
from sdf import Field2D, smin, smax, spline, interp
import sdf, meshio, studio

F2 = lambda pts, res=0.0015: Field2D.polygon(np.asarray(pts, float), res=res)
def sym(half):
    half = np.asarray(half); return np.vstack([half, half[::-1] * [1, -1]])
def capsule(P, a, b, r):
    a = np.asarray(a, np.float32); b = np.asarray(b, np.float32)
    pa = P - a; ba = b - a
    h = np.clip((pa @ ba) / (ba @ ba), 0, 1)
    return np.linalg.norm(pa - h[:, None] * ba, axis=1) - r

# ---------------- splitter + end plates + rods
SPLIT = F2(sym(spline([(2.60,0.0),(2.59,0.40),(2.55,0.72),(2.46,0.92),(2.32,1.00),(2.10,1.005),(2.00,0.98),(2.00,0.0)], 10)))
def splitter(P):
    x, y, z = P[:,0], P[:,1], P[:,2]; ay = np.abs(y)
    lift = 0.012 * np.clip((x - 2.45) / 0.15, 0, 1) ** 2
    plate = smax(SPLIT(x, y), np.abs(z - 0.064 - lift) - 0.010, 0.004)
    fin = smax(smax(np.abs(ay - 0.985) - 0.004, np.abs(x - 2.25) - 0.22, 0.0), np.abs(z - 0.15) - 0.09, 0.006)
    fin = smax(fin, (z - 0.06) - (2.47 - x) * 0.9, 0.01)      # swept leading edge
    d = smin(plate, fin, 0.006)
    for yy in (0.35, 0.72):
        for s in (1, -1):
            d = np.minimum(d, capsule(P, (2.50, s*yy, 0.07), (2.40, s*yy, 0.25), 0.0045))
    return d

# ---------------- canards (two per side)
CAN = F2(np.array([(0.0,0.0),(0.20,0.0),(0.17,0.085),(0.02,0.06)]))   # plan outline in (dx, outward)
def canards(P):
    x, y, z = P[:,0], P[:,1], P[:,2]; ay = np.abs(y)
    d = None
    for (x0, y0, z0, tilt) in [(2.18, 0.90, 0.30, 0.20), (2.10, 0.95, 0.40, 0.14)]:
        dx = x0 + 0.20 - x; dy = ay - y0
        zc = z0 + tilt * (0.20 - dx) * 0.5
        c = smax(CAN(dx, dy), np.abs(z - zc - 0.10 * dy) - 0.003, 0.0015)
        d = c if d is None else np.minimum(d, c)
    return d

# ---------------- side skirts
SKIRT_SEC = F2(np.array([(0.90,0.065),(1.045,0.065),(1.050,0.080),(1.000,0.095),(0.98,0.150),(0.90,0.150)]))
def skirts(P):
    x, y, z = P[:,0], P[:,1], P[:,2]; ay = np.abs(y)
    sec = SKIRT_SEC(ay, z)
    taper = np.maximum(x - 0.98, -0.98 - x)
    return smax(sec + 0.04 * np.maximum(taper + 0.06, 0) * 8, taper, 0.02)

# ---------------- rear diffuser
def diffuser(P):
    x, y, z = P[:,0], P[:,1], P[:,2]; ay = np.abs(y)
    ramp = interp(x, [-2.48, -2.35, -1.65, -1.40], [0.32, 0.30, 0.10, 0.075])
    plate = smax(smax(np.abs(z - ramp) - 0.006, ay - 0.86, 0.0), np.maximum(x + 1.40, -2.46 - x), 0.004)
    d = plate
    for yy in (0.0, 0.24, 0.48, 0.74):
        fin = smax(smax(np.abs(ay - yy) - 0.004, z - ramp, 0.0), np.maximum(0.075 - z, np.maximum(x + 1.65, -2.47 - x)), 0.003)
        fin = smax(fin, (0.075 + (-1.65 - x) * 0.30) - z, 0.0)   # fin lower edge rises
        d = np.minimum(d, fin)
    return d

# ---------------- swan-neck rear wing
def airfoil(c=0.30, camber=0.08, t=0.11, n=60):
    xs = (1 - np.cos(np.linspace(0, np.pi, n))) / 2
    yt = 5 * t * (0.2969*np.sqrt(xs) - 0.1260*xs - 0.3516*xs**2 + 0.2843*xs**3 - 0.1036*xs**4)
    p = 0.4
    yc = np.where(xs < p, camber/p**2*(2*p*xs - xs**2), camber/(1-p)**2*((1-2*p) + 2*p*xs - xs**2))
    up = np.c_[xs, yc + yt]; lo = np.c_[xs, yc - yt]
    pts = np.vstack([up, lo[::-1][1:-1]]) * c
    return pts
_af = airfoil()
# inverted (downforce) + angle: in (x, z) with x pointing forward -> flip chord direction
_ang = math.radians(9.0)
_A = np.array([[-1.0, 0.0], [0.0, -1.0]]) @ np.array([[math.cos(_ang), -math.sin(_ang)], [math.sin(_ang), math.cos(_ang)]])
WING2 = F2((_af @ _A.T) + np.array([-2.06, 1.335]), res=0.0008)
NECK = F2(spline([(-2.03,1.0),(-2.06,1.12),(-2.10,1.26),(-2.16,1.37),(-2.24,1.395),(-2.30,1.375),(-2.29,1.345),
                  (-2.22,1.355),(-2.16,1.33),(-2.12,1.24),(-2.09,1.12),(-2.08,1.0)], 8), res=0.001)
ENDP = F2(spline([(-2.00,1.24),(-2.02,1.40),(-2.12,1.43),(-2.42,1.43),(-2.46,1.36),(-2.44,1.20),(-2.30,1.17),(-2.10,1.17)], 8), res=0.001)
def wing(P):
    x, y, z = P[:,0], P[:,1], P[:,2]; ay = np.abs(y)
    main = smax(WING2(x, z), ay - 0.925, 0.004)
    gurney = smax(smax(np.abs(x + 2.355) - 0.002, np.abs(z - 1.400) - 0.012, 0.0), ay - 0.925, 0.0)
    endp = smax(ENDP(x, z), np.abs(ay - 0.931) - 0.003, 0.002)
    neck = smax(NECK(x, z), np.abs(ay - 0.32) - 0.007, 0.003)
    return np.minimum(np.minimum(smin(main, gurney, 0.003), endp), neck)

# ---------------- race mirrors
def mirrors(P):
    x, y, z = P[:,0], P[:,1], P[:,2]; ay = np.abs(y)
    # teardrop housing: ellipsoid blended with a tail cone
    q = np.c_[(x + 0.02) / 0.090, (ay - 1.03) / 0.075, (z - 0.985) / 0.045]
    ell = (np.linalg.norm(q, axis=1) - 1.0) * 0.045
    cut = -(x + 0.035)     # flat rear face where the glass sits
    house = smax(ell, -cut * -1, 0.004) if False else smax(ell, -(x + 0.045) * -1 * -1, 0.0)
    house = smax(ell, (-0.050 - x), 0.004)      # truncated at the back
    stalk = capsule(np.c_[x, ay, z], (0.02, 0.90, 0.895), (-0.01, 0.99, 0.975), 0.010)
    stalk2 = capsule(np.c_[x, ay, z], (0.10, 0.90, 0.895), (0.01, 0.99, 0.975), 0.008)
    return smin(house, np.minimum(stalk, stalk2), 0.008)
def mirror_glass(P):
    x, y, z = P[:,0], P[:,1], P[:,2]; ay = np.abs(y)
    q = np.c_[(ay - 1.03) / 0.068, (z - 0.985) / 0.039]
    return smax(np.linalg.norm(q, axis=1) * 0.039 - 0.039, np.abs(x + 0.052) - 0.002, 0.0)

# ---------------- side exhaust (twin), tow straps
def exhaust(P):
    x, y, z = P[:,0], P[:,1], P[:,2]; ay = np.abs(y)
    d = None
    for x0 in (-0.80, -0.92):
        r = np.hypot(x - x0, z - 0.175)
        tube = smax(np.abs(r - 0.040) - 0.0025, np.abs(ay - 0.985) - 0.055, 0.0015)
        d = tube if d is None else np.minimum(d, tube)
    return d
def straps(P):
    x, y, z = P[:,0], P[:,1], P[:,2]
    d = None
    for (x0, y0, z0, s) in [(2.47, -0.55, 0.20, 1), (-2.40, 0.55, 0.40, -1)]:
        loop = smax(smax(np.abs(np.hypot((x - x0 - s*0.045) / 1.6, z - z0) - 0.030) - 0.003, np.abs(y - y0) - 0.016, 0.0), 0.0, 0.0)
        d = loop if d is None else np.minimum(d, loop)
    return d

PARTS = [
    ('splitter', splitter, ((1.95,2.65),(-1.05,1.05),(0.04,0.33)), 0.0025, 'carbon'),
    ('canards', canards, ((2.0,2.45),(-1.08,1.08),(0.25,0.50)), 0.0015, 'carbon'),
    ('skirts', skirts, ((-1.10,1.10),(-1.08,1.08),(0.05,0.17)), 0.0025, 'carbon'),
    ('diffuser', diffuser, ((-2.50,-1.35),(-0.90,0.90),(0.06,0.36)), 0.0025, 'carbon'),
    ('wing', wing, ((-2.50,-1.98),(-0.96,0.96),(0.98,1.45)), 0.0018, 'carbon'),
    ('mirrors', mirrors, ((-0.08,0.12),(-1.12,1.12),(0.87,1.04)), 0.0015, 'paint_body'),
    ('mirror_glass', mirror_glass, ((-0.06,-0.04),(-1.11,1.11),(0.94,1.03)), 0.001, 'mirror'),
    ('exhaust', exhaust, ((-0.98,-0.74),(-1.05,1.05),(0.12,0.23)), 0.0012, 'titanium'),
    ('straps', straps, ((-2.50,2.56),(-0.6,0.6),(0.14,0.46)), 0.0012, 'strap'),
]

def build(body, M):
    M['mirror'] = studio.mat('mirror', (0.9,0.9,0.9), metallic=1.0, rough=0.02)
    M['titanium'] = studio.mat('titanium', (0.42,0.36,0.40), metallic=1.0, rough=0.25)
    M['strap'] = studio.mat('strap_red', (0.6,0.02,0.02), rough=0.6)
    for name, fn, bounds, vox, mname in PARTS:
        cache = f'{sdf.WORK}/cache_part_{name}.npz'
        src = os.path.getmtime(__file__)
        if os.path.exists(cache) and os.path.getmtime(cache) > src:
            c = np.load(cache); V, F, N = c['V'], c['F'], c['N']
        else:
            V, F = sdf.mesh_sdf(fn, bounds, vox=vox, block=96, band=4, label=name)
            if not len(V): print('EMPTY', name); continue
            N, F = meshio.orient(V, F, fn); np.savez(cache, V=V, F=F, N=N)
        studio.mesh_from_arrays(name, V, F, N, mats=[M[mname]])
    lights(body, M)
    # bonnet pins, antenna, wiper as primitives
    def surf_z(x, y):
        z = np.linspace(0.3, 1.3, 400).astype(np.float32)
        d = body.shell(np.c_[np.full_like(z, x), np.full_like(z, y), z])
        return float(z[np.where(d < 0)[0].max()])
    for (px, py) in body.PINS:
        for s in (1, -1):
            zz = surf_z(px, s * py)
            bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.014, depth=0.006, location=(px, s*py, zz + 0.002))
            bpy.context.object.data.materials.append(M['titanium'])
            bpy.ops.mesh.primitive_torus_add(major_radius=0.016, minor_radius=0.0018, location=(px + 0.03, s*py, zz + 0.003))
            bpy.context.object.data.materials.append(M['strap'])
    zr = surf_z(-1.05, 0.0)
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.0025, depth=0.20, location=(-1.05, 0, zr + 0.10))
    bpy.context.object.data.materials.append(M['trim_black'])
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.012, depth=0.012, location=(-1.05, 0, zr + 0.006))
    bpy.context.object.data.materials.append(M['trim_black'])
    # single centre wiper parked at the base of the screen
    zw = surf_z(0.02, 0.0)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0.0, 0.05, zw + 0.012), rotation=(0, math.radians(-25), math.radians(8)))
    w = bpy.context.object; w.scale = (0.012, 0.62, 0.010); w.data.materials.append(M['trim_black'])

def _surface_z(body, x, y, z0=0.3, z1=1.3):
    z = np.linspace(z0, z1, 800).astype(np.float32)
    d = body.shell(np.c_[np.full_like(z, x), np.full_like(z, y), z])
    i = np.where(d < 0)[0]
    return float(z[i.max()]) if len(i) else None

def _surface_x_rear(body, y, z):
    x = np.linspace(-2.5, -1.8, 700).astype(np.float32)
    d = body.shell(np.c_[x, np.full_like(x, y), np.full_like(x, z)])
    i = np.where(d < 0)[0]
    return float(x[i.min()])

def _tube(name, pts, r, mat):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    for p, q in zip(sp.points, pts): p.co = (*q, 1)
    cu.bevel_depth = r; cu.bevel_resolution = 4; cu.use_fill_caps = True
    ob = bpy.data.objects.new(name, cu); bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(mat)
    return ob

def lights(body, M):
    M['drl'] = studio.mat('led_white', (1,1,1), rough=0.3, emission=(0.85,0.92,1.0), estrength=12.0)
    M['tail_led'] = studio.mat('led_red', (0.5,0.0,0.0), rough=0.3, emission=(1.0,0.02,0.01), estrength=10.0)
    M['chrome'] = studio.mat('chrome', (0.9,0.9,0.92), metallic=1.0, rough=0.06)
    M['proj_lens'] = studio.mat('proj_lens', (0.9,0.95,1.0), rough=0.0, transmission=1.0, ior=1.5)
    for s in (1, -1):
        # DRL strip along the outer edge of the lamp
        pts = []
        for (x, ay) in [(2.305,0.50),(2.26,0.62),(2.17,0.75),(2.03,0.860),(1.90,0.905)]:
            z = _surface_z(body, x, s * ay)
            pts.append((x, s * ay, z - 0.012))
        _tube(f'drl_{s}', np.array(pts), 0.0045, M['drl'])
        # two projector modules: chrome bezel cup + glass lens
        for (x, ay, r) in [(2.215, 0.610, 0.030), (2.105, 0.735, 0.026)]:
            z = _surface_z(body, x, s * ay) - 0.020
            bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=r * 1.25, depth=0.012, location=(x, s * ay, z - 0.004))
            bpy.context.object.data.materials.append(M['chrome'])
            bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=r, location=(x, s * ay, z - 0.012))
            o = bpy.context.object; o.scale = (1, 1, 0.55); o.data.materials.append(M['proj_lens'])
            bpy.ops.object.shade_smooth()
        # amber indicator sliver at the inner end
        pts = []
        for (x, ay) in [(1.96,0.865),(1.89,0.890)]:
            z = _surface_z(body, x, s * ay); pts.append((x, s * ay, z - 0.010))
        _tube(f'ind_{s}', np.array(pts), 0.0035, studio.mat('amber', (1.0,0.35,0.0), rough=0.3, emission=(1.0,0.4,0.0), estrength=1.5))
    # tail light: full-width LED bar + vertical light blades at each end
    pts = []
    for yy in np.linspace(-0.95, 0.95, 41):
        zc = 0.893 + (0.012 if abs(yy) > 0.85 else 0.0) * (abs(yy) - 0.85) / 0.1
        x = _surface_x_rear(body, yy, zc)
        pts.append((x + 0.010, yy, zc))
    _tube('tail_bar', np.array(pts), 0.005, M['tail_led'])
    # rain light (FIA style) in the diffuser centre
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-2.43, 0.0, 0.33))
    o = bpy.context.object; o.scale = (0.03, 0.10, 0.04); o.data.materials.append(M['tail_led'])

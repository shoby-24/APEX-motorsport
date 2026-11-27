"""GT3 race interior: roll cage, bucket seat + harness, race wheel, dash, switch panel, extinguisher. LHD driver at +y."""
import os, numpy as np, math, bpy
from sdf import Field2D, smin, smax, spline, interp
import sdf, meshio, studio
from parts import _tube, capsule

DY = 0.385                      # driver seat centreline
def rbox(P, c, h, r):
    q = np.abs(P - np.asarray(c, np.float32)) - (np.asarray(h, np.float32) - r)
    return np.linalg.norm(np.maximum(q, 0), axis=1) + np.minimum(q.max(1), 0) - r

def rot_y(P, c, ang):
    """rotate points about the y axis through c (for tilting parts)."""
    c = np.asarray(c, np.float32); Q = P - c
    ca, sa = math.cos(ang), math.sin(ang)
    return np.c_[Q[:,0]*ca - Q[:,2]*sa, Q[:,1], Q[:,0]*sa + Q[:,2]*ca] + c

def seat(P):
    # local: seat centred at (x=-1.10, y=DY); back reclined 18 deg
    base = rbox(P, (-1.02, DY, 0.215), (0.24, 0.23, 0.07), 0.05)
    Pb = rot_y(P, (-1.28, DY, 0.24), math.radians(-18))
    back = rbox(Pb, (-1.28, DY, 0.60), (0.06, 0.235, 0.36), 0.05)
    shell_ = smin(base, back, 0.06)
    # hollow: carve the occupant space leaving bolsters
    occ = smin(rbox(P, (-0.98, DY, 0.33), (0.26, 0.165, 0.10), 0.06), rbox(Pb, (-1.20, DY, 0.66), (0.08, 0.17, 0.36), 0.06), 0.05)
    d = smax(shell_, -occ, 0.02)
    # head restraint wings
    wing = rbox(Pb, (-1.25, DY, 0.92), (0.10, 0.20, 0.08), 0.04)
    wing = smax(wing, -rbox(Pb, (-1.17, DY, 0.92), (0.10, 0.12, 0.10), 0.03), 0.01)
    # harness slots in the back
    for yy in (DY - 0.07, DY + 0.07):
        d = smax(d, -rbox(Pb, (-1.28, yy, 0.86), (0.08, 0.022, 0.012), 0.004), 0.002)
    return smin(d, wing, 0.03)

def steering(P):
    c = np.array([-0.60, DY, 0.735], np.float32); tilt = math.radians(68)
    Q = rot_y(P, c, -(math.pi / 2 - tilt)) - c        # wheel plane = local (y, z)
    u, v, w = Q[:,1], Q[:,2], Q[:,0]
    # rounded-rectangle rim with flat top and bottom (race wheel)
    hu, hv, rr = 0.150, 0.110, 0.06
    qu = np.abs(u) - hu + rr; qv = np.abs(v) - hv + rr
    ring = np.hypot(np.maximum(qu, 0), np.maximum(qv, 0)) + np.minimum(np.maximum(qu, qv), 0) - rr
    rim = np.hypot(ring, w) - 0.016
    # centre body with display
    body = rbox(np.c_[u, v, w], (0, -0.005, -0.012), (0.105, 0.080, 0.020), 0.012)
    grips = rbox(np.c_[np.abs(u), v, w], (0.125, 0.0, -0.004), (0.030, 0.070, 0.022), 0.012)
    d = smin(smin(rim, body, 0.01), grips, 0.008)
    paddles = rbox(np.c_[np.abs(u), v, w], (0.090, 0.04, -0.050), (0.06, 0.035, 0.003), 0.002)
    col = capsule(P, (-0.60, DY, 0.735), (-0.30, DY, 0.62), 0.028)
    return np.minimum(np.minimum(d, paddles), col)

def dash(P):
    x, y, z = P[:,0], P[:,1], P[:,2]
    top = rbox(P, (-0.15, 0.0, 0.80), (0.20, 0.80, 0.06), 0.03)
    binnacle = rbox(P, (-0.38, DY, 0.86), (0.08, 0.16, 0.05), 0.02)
    console = rbox(P, (-0.55, 0.0, 0.45), (0.34, 0.09, 0.30), 0.03)
    tunnel = rbox(P, (-1.05, 0.0, 0.26), (0.45, 0.11, 0.12), 0.04)
    return smin(smin(top, binnacle, 0.03), smin(console, tunnel, 0.05), 0.03)

def floor(P):
    return rbox(P, (-0.90, 0.0, 0.135), (0.95, 0.85, 0.012), 0.005)

PARTS = [('seat', seat, ((-1.50,-0.70),(DY-0.30,DY+0.30),(0.12,1.08)), 0.0025, 'seat'),
         ('wheel_sw', steering, ((-0.72,-0.25),(DY-0.20,DY+0.20),(0.55,0.88)), 0.0015, 'alcantara'),
         ('dash', dash, ((-1.55,0.10),(-0.85,0.85),(0.10,0.92)), 0.003, 'carbon'),
         ('floor', floor, ((-1.90,0.10),(-0.90,0.90),(0.11,0.16)), 0.004, 'carbon')]

def cage_points(body, x, n=9):
    """Points 45 mm inside the cabin skin around a section at x, from floor (left) over the roof to floor (right)."""
    pts = []
    for a in np.linspace(math.radians(-80), math.radians(80), n):
        dirv = np.array([0.0, math.sin(a), math.cos(a)]); o = np.array([x, 0.0, 0.55])
        ts = np.linspace(0.05, 1.2, 600)
        P = (o + ts[:, None] * dirv).astype(np.float32)
        d = body.shell(P)
        i = np.where(d < -0.045)[0]
        if len(i): pts.append(P[i.max()])
    return np.array(pts)

def build(body, M):
    M['seat'] = studio.mat('seat_fabric', (0.03, 0.03, 0.032), rough=0.85)
    M['alcantara'] = studio.mat('alcantara', (0.025, 0.025, 0.025), rough=0.9)
    M['cage'] = studio.mat('cage', (0.55, 0.03, 0.03), rough=0.35, coat=0.8)
    M['harness'] = studio.mat('harness', (0.70, 0.04, 0.03), rough=0.7)
    M['screen'] = studio.mat('screen', (0.02,0.02,0.02), rough=0.2, emission=(0.2,0.6,1.0), estrength=1.5)
    M['extinguisher'] = studio.mat('extinguisher', (0.7, 0.05, 0.04), rough=0.3, coat=1.0)
    for name, fn, bounds, vox, mname in PARTS:
        cache = f'{sdf.WORK}/cache_int_{name}.npz'
        if os.path.exists(cache) and os.path.getmtime(cache) > os.path.getmtime(__file__):
            c = np.load(cache); V, F, N = c['V'], c['F'], c['N']
        else:
            V, F = sdf.mesh_sdf(fn, bounds, vox=vox, block=96, band=4, label=name)
            N, F = meshio.orient(V, F, fn); np.savez(cache, V=V, F=F, N=N)
        studio.mesh_from_arrays(name, V, F, N, mats=[M[mname]])
    # roll cage: main hoop, front hoop (A-pillars), roof rails, door X-bars, rear stays, diagonal
    main = cage_points(body, -1.30, 11); front = cage_points(body, -0.45, 11)
    R = 0.021
    _tube('cage_main', main, R, M['cage']); _tube('cage_front', front, R, M['cage'])
    for i in (3, 7):
        _tube(f'cage_roof{i}', np.array([front[i], main[i]]), R, M['cage'])
    for s, (a, b) in [(1, (9, 10)), (-1, (0, 1))]:
        f0, m0 = front[b], main[b]; f1, m1 = front[a], main[a]
        _tube(f'cage_doorX1_{s}', np.array([f0, m1]), R * 0.9, M['cage'])
        _tube(f'cage_doorX2_{s}', np.array([f1 * [1,1,1] - [0,0,0.25], m0 + [0,0,0.25]]), R * 0.9, M['cage'])
    _tube('cage_diag', np.array([main[1], main[9]]), R, M['cage'])
    for i in (2, 8):
        _tube(f'cage_stay{i}', np.array([main[i], main[i] + [-0.75, 0, -0.30]]), R * 0.9, M['cage'])
    # 6-point harness: shoulder straps from the hoop over the seat back, lap belts
    for yy in (DY - 0.07, DY + 0.07):
        _tube(f'harness_s{yy:.2f}', np.array([(-1.42, yy, 0.98), (-1.30, yy, 0.93), (-1.14, yy, 0.78), (-0.98, yy * 0.98 + DY * 0.02, 0.52), (-0.88, DY, 0.36)]), 0.006, M['harness'])
    for yy in (DY - 0.19, DY + 0.19):
        _tube(f'harness_l{yy:.2f}', np.array([(-1.10, yy, 0.26), (-0.96, yy * 0.6 + DY * 0.4, 0.36), (-0.88, DY, 0.36)]), 0.006, M['harness'])
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.03, depth=0.012, location=(-0.88, DY, 0.365))
    bpy.context.object.data.materials.append(M['chrome'] if 'chrome' in M else M['cage'])
    # display screens
    bpy.ops.mesh.primitive_plane_add(size=1, location=(-0.335, DY, 0.885), rotation=(0, math.radians(-62), 0))
    o = bpy.context.object; o.scale = (0.08, 0.13, 1); o.data.materials.append(M['screen'])
    c = np.array([-0.60, DY, 0.735]); n = np.array([math.cos(math.radians(68)) * -1, 0, math.sin(math.radians(68)) * 0])
    bpy.ops.mesh.primitive_plane_add(size=1, location=(-0.578, DY, 0.73), rotation=(0, math.radians(-22), 0))
    o = bpy.context.object; o.scale = (0.035, 0.06, 1); o.data.materials.append(M['screen'])
    # switch panel buttons on the console
    cols = [(0.8,0.05,0.03),(0.05,0.5,0.1),(0.9,0.6,0.02),(0.05,0.2,0.8)]
    for i in range(4):
        for j in range(3):
            bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=0.009, depth=0.012, location=(-0.42 - 0.05 * j, -0.06 + 0.04 * i, 0.755), rotation=(0, math.radians(30), 0))
            bpy.context.object.data.materials.append(studio.mat(f'btn{i}', cols[i], rough=0.4))
    # fire extinguisher bottle on the passenger floor
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.055, depth=0.38, location=(-0.85, -0.42, 0.21), rotation=(0, math.radians(90), 0))
    bpy.context.object.data.materials.append(M['extinguisher']); bpy.ops.object.shade_smooth()

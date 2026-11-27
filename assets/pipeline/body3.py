"""Aurion Vanta GT3 body v3: fictional FRONT-engine GT3 race coupe. m; x fwd, y left, z up; origin ground, mid-wheelbase."""
import numpy as np
from sdf import Field2D, smin, smax, spline, interp

WB = 2.72; XF, XR = WB/2, -WB/2
RF, RR = 0.340, 0.355
TF, TR = 0.855, 0.850
F2 = lambda pts, res=0.002: Field2D.polygon(np.asarray(pts, float), res=res)
def sym(half):  # mirror a half outline (u, +v) to a closed symmetric polygon
    half = np.asarray(half); return np.vstack([half, half[::-1] * [1, -1]])
def rbox2(u, v, cu, cv, hu, hv, r):
    qu = np.abs(u - cu) - hu + r; qv = np.abs(v - cv) - hv + r
    return np.hypot(np.maximum(qu, 0), np.maximum(qv, 0)) + np.minimum(np.maximum(qu, qv), 0) - r

# ------------------------------------------------------------------ main volumes
side_top = spline([(2.43,0.30),(2.42,0.40),(2.37,0.50),(2.24,0.60),(2.02,0.700),(1.72,0.800),(1.42,0.862),(1.16,0.882),
                   (0.80,0.886),(0.40,0.884),(0.00,0.888),(-0.50,0.900),(-1.00,0.928),(-1.40,0.955),(-1.80,0.966),
                   (-2.10,0.980),(-2.25,0.998),(-2.31,0.994)], 16)
side_bot = spline([(-2.325,0.95),(-2.335,0.76),(-2.31,0.56),(-2.23,0.39),(-2.09,0.26),(-1.86,0.155),(-1.60,0.11),
                   (0.0,0.100),(1.80,0.105),(2.20,0.130),(2.39,0.180),(2.43,0.24)], 16)
SIDE = F2(np.vstack([side_top, side_bot]))
plan_half = spline([(2.44,0.0),(2.43,0.30),(2.39,0.55),(2.31,0.745),(2.16,0.895),(1.96,0.982),(1.70,1.018),(1.36,1.028),
                    (1.05,1.012),(0.85,0.975),(0.50,0.945),(0.00,0.935),(-0.50,0.942),(-0.80,0.968),(-1.05,1.012),
                    (-1.36,1.032),(-1.75,1.022),(-2.05,0.988),(-2.22,0.915),(-2.31,0.76),(-2.34,0.45),(-2.345,0.0)], 16)
PLAN = F2(sym(plan_half))
_ph = plan_half[np.argsort(plan_half[:,0])]
def half_width(x): return interp(x, _ph[:,0], _ph[:,1])
SEC = F2(sym(spline([(0.0,0.06),(0.80,0.06),(0.95,0.13),(1.03,0.28),(1.055,0.50),(1.04,0.74),(0.97,0.95),(0.0,1.05)], 12)[:, ::-1][:, ::-1]))
# note: SEC is in (y, z) with y symmetric -> build explicitly
_sec = spline([(0.0,0.06),(0.80,0.06),(0.95,0.13),(1.03,0.28),(1.055,0.50),(1.04,0.74),(0.97,0.95),(0.0,1.05)], 12)
SEC = F2(np.vstack([_sec, _sec[::-1] * [-1, 1]]))

cab_top = spline([(0.14,0.82),(0.06,0.875),(-0.20,0.990),(-0.50,1.130),(-0.75,1.200),(-1.00,1.212),(-1.25,1.190),
                  (-1.55,1.120),(-1.85,1.050),(-2.10,1.005),(-2.24,0.995)], 16)
CAB_SIDE = F2(np.vstack([cab_top, [(-2.24,0.60),(0.14,0.60)]]))
cab_plan = spline([(0.16,0.0),(0.14,0.45),(0.05,0.685),(-0.40,0.725),(-0.90,0.732),(-1.30,0.712),(-1.70,0.650),
                   (-2.05,0.560),(-2.22,0.45),(-2.25,0.0)], 16)
CAB_PLAN = F2(sym(cab_plan))
_cs = spline([(0.0,0.55),(0.82,0.55),(0.82,0.86),(0.74,1.02),(0.60,1.16),(0.36,1.225),(0.0,1.232)], 12)
CAB_SEC = F2(np.vstack([_cs, _cs[::-1] * [-1, 1]]))

def head_zmin(x): return interp(x, [1.8, 2.0, 2.2, 2.36, 2.5], [0.70, 0.63, 0.55, 0.42, 0.36])
def bonnet_h(x): return interp(x, [0.0,0.20,0.70,1.36,1.90,2.30,2.50], [0.90,0.872,0.860,0.815,0.718,0.585,0.50])
def deck_h(x):   return interp(x, [-2.50,-2.25,-1.90,-1.60], [1.0,0.985,0.95,1.02])

# ------------------------------------------------------------------ 2D feature outlines
FRONT_C = F2(spline([(-0.1,0.165),(0.52,0.165),(0.60,0.21),(0.585,0.36),(0.50,0.445),(0.30,0.468),(-0.1,0.470)], 8))
FRONT_S = F2(spline([(0.68,0.170),(0.93,0.175),(0.985,0.24),(0.95,0.34),(0.80,0.335),(0.69,0.26)], 8))
HEAD = F2(spline([(2.355,0.47),(2.30,0.64),(2.18,0.80),(2.00,0.915),(1.87,0.945),(1.845,0.905),(1.98,0.83),(2.14,0.70),(2.24,0.55),(2.29,0.46)], 10))
TAIL = F2(np.vstack([spline([(-0.97,0.905),(-0.90,0.880),(-0.55,0.872),(0.55,0.872),(0.90,0.880),(0.97,0.905)], 8),
                     spline([(0.97,0.935),(0.90,0.918),(0.55,0.910),(-0.55,0.910),(-0.90,0.918),(-0.97,0.935)], 8)]))
SIDEWIN = F2(spline([(0.02,0.905),(-0.30,1.035),(-0.62,1.150),(-0.95,1.170),(-1.30,1.140),(-1.58,1.060),(-1.70,0.985),
                     (-1.60,0.935),(-1.10,0.915),(-0.40,0.905)], 12))
WSCREEN = F2(np.vstack([spline([(0.08,0.0),(0.07,0.42),(0.02,0.600),(-0.30,0.640),(-0.62,0.635),(-0.68,0.45),(-0.69,0.0)], 10),
                        spline([(-0.69,0.0),(-0.68,-0.45),(-0.62,-0.635),(-0.30,-0.640),(0.02,-0.600),(0.07,-0.42),(0.08,0.0)], 10)]))
REARWIN = F2(sym(spline([(-1.22,0.0),(-1.22,0.42),(-1.35,0.52),(-1.70,0.50),(-1.90,0.40),(-1.92,0.0)], 10)))
FVENT = F2(spline([(0.98,0.80),(0.80,0.79),(0.66,0.70),(0.62,0.48),(0.70,0.36),(0.86,0.38),(0.96,0.55)], 10))   # fender vent (side view)
BVENT = F2(spline([(1.88,0.22),(1.90,0.50),(1.80,0.58),(1.45,0.56),(1.38,0.42),(1.42,0.24)], 10))             # bonnet vent (plan, |y|)
SIDE_LINES = Field2D.polylines([
    spline([(0.06,0.150),(0.10,0.40),(0.08,0.70),(0.03,0.89)], 10),               # door front
    spline([(-1.12,0.150),(-1.12,0.45),(-1.08,0.70),(-1.02,0.92)], 10),           # door rear
    [(0.06,0.150),(-1.12,0.150)],                                                 # door bottom
    spline([(2.18,0.56),(2.04,0.46),(1.86,0.42),(1.73,0.44)], 10),                # bumper / fender
    spline([(-1.80,0.62),(-1.98,0.64),(-2.20,0.66),(-2.33,0.68)], 10),            # rear bumper
], (-2.6, 2.6, -0.1, 1.4), res=0.001)
TOP_LINES = Field2D.polylines([
    spline([(0.18,0.62),(0.9,0.62),(1.70,0.58),(2.22,0.46),(2.30,0.25),(2.32,0.0),(2.30,-0.25),(2.22,-0.46),(1.70,-0.58),(0.9,-0.62),(0.18,-0.62)], 12),
    [(0.18,0.62),(0.18,-0.62)],                                                   # bonnet rear edge
    spline([(-2.00,0.52),(-2.24,0.50),(-2.30,0.25),(-2.31,0.0),(-2.30,-0.25),(-2.24,-0.50),(-2.00,-0.52)], 10),  # boot lid
    [(-2.00,0.52),(-2.00,-0.52)],
], (-2.6, 2.6, -1.1, 1.1), res=0.001)
FUEL = (-1.62, 1.00)     # quick-fill cap on the left C-pillar (x, z), side view
PINS = [(2.12, 0.42), (0.40, 0.55)]   # bonnet pins (x, |y|)

# ------------------------------------------------------------------ volumes
def lower_body(x, y, z):
    ay = np.abs(y)
    d = smax(smax(SIDE(x, z), PLAN(x, y), 0.10), SEC(y, z), 0.06)
    v = smax((bonnet_h(x) + 0.075 * np.minimum(ay / 0.70, 1.35) ** 2 - z) * 0.95, -0.10 - x, 0.05)
    d = smax(d, -v, 0.06)
    r = smax((deck_h(x) + 0.03 * np.minimum(ay / 0.62, 1.3) ** 2 - z) * 0.95, x + 1.85, 0.05)
    d = smax(d, -r, 0.05)
    return d

def cabin(x, y, z):
    return smax(smax(CAB_SIDE(x, z), CAB_PLAN(x, y), 0.07), CAB_SEC(y, z), 0.05)

def arch(x, y, z, xc, zc, R, inner=0.52):
    return smax(np.hypot(x - xc, z - zc) - R, inner - np.abs(y), 0.02)

def shell(P):
    x, y, z = P[:,0], P[:,1], P[:,2]; ay = np.abs(y)
    d = smin(lower_body(x, y, z), cabin(x, y, z), 0.07)
    # crisp horizontal character line: shallow step along the door at z~0.55 (subtle undercut below)
    under = smax(smax(z - 0.52, 0.16 - z, 0.06), (half_width(x) - 0.018) - ay, 0.02)
    under = smax(under, np.maximum(x - 0.90, -0.95 - x) * 1.0, 0.25)
    d = smax(d, -under, 0.03)
    d = smax(d, -arch(x, y, z, XF, RF, RF + 0.045), 0.008)
    d = smax(d, -arch(x, y, z, XR, RR, RR + 0.050), 0.008)
    return d

_T = {}
def ztop(x, ay):
    if 'z' not in _T:
        from sdf import extent_table
        _T['z'] = extent_table(lambda P: shell(P), 2, np.arange(-2.5, 2.51, 0.01), np.arange(0.0, 1.11, 0.01), 0.0, 1.4, 'ztop3')
    return _T['z'](x, ay)
def yside(x, z):
    if 'y' not in _T:
        from sdf import extent_table
        _T['y'] = extent_table(lambda P: shell(P), 1, np.arange(-2.5, 2.51, 0.01), np.arange(0.0, 1.31, 0.01), 0.0, 1.15, 'yside3')
    return _T['y'](x, z)

def slats(coord, pitch, thick):
    t = (coord / pitch) % 1.0
    return (np.abs(t - 0.5) * pitch) - thick / 2   # negative within the slat plates (centred at half pitch)

def features(P, d0):
    x, y, z = P[:,0], P[:,1], P[:,2]; ay = np.abs(y)
    d = d0
    # grille mouth with horizontal vanes
    mouth = smax(FRONT_C(ay, z), 2.24 - x, 0.012)
    d = smax(d, -mouth, 0.008)
    vanes = smax(smax(FRONT_C(ay, z) + 0.015, -(slats(z, 0.034, 0.005)) * -1 if False else slats(z - 0.017, 0.034, 0.004), 0.0),
                 np.abs(x - 2.30) - 0.045, 0.002)
    d = smin(d, vanes, 0.0)
    s = smax(FRONT_S(ay, z), 2.16 - x, 0.01)
    d = smax(d, -s, 0.008)
    # fender vents behind the front wheels with 5 vertical blades
    fv = smax(FVENT(x, z), (yside(x, z) - 0.14) - ay, 0.006)
    d = smax(d, -fv, 0.005)
    blades = smax(smax(FVENT(x, z) + 0.008, slats(x - 0.62, 0.072, 0.010), 0.0), np.abs(ay - (yside(x, z) - 0.030)) - 0.022, 0.002)
    d = smin(d, blades, 0.0)
    # bonnet extractor vents with louvres
    bv = smax(BVENT(x, ay), -(d0 + 0.045), 0.0)
    bv = smax(bv, (ztop(x, ay) - 0.06) - z, 0.0)
    d = smax(d, -bv, 0.006)
    louv = smax(smax(BVENT(x, ay) + 0.006, slats(x - 1.38 + 0.008 * (z - 0.8) * 0, 0.045, 0.006), 0.0), np.abs(d0 + 0.020) - 0.017, 0.002)
    louv = smax(louv, (ztop(x, ay) - 0.06) - z, 0.0)
    d = smin(d, louv, 0.0)
    # rear diffuser cavity + exhaust side pipes are separate parts
    dif = smax(rbox2(y, z, 0, 0.21, 0.78, 0.12, 0.03), x + 2.20, 0.01)
    d = smax(d, -dif, 0.008)
    # lamp recesses
    lamp = smax(smax(HEAD(x, ay), -(d0 + 0.028), 0.004), np.maximum(1.6 - x, (ztop(x, ay) - 0.045) - z), 0.0)
    d = smax(d, -lamp, 0.004)
    tail = smax(smax(TAIL(y, z), -(d0 + 0.022), 0.003), x + 1.9, 0.0)
    d = smax(d, -tail, 0.003)
    # windows
    d = smax(d, -smax(windows(x, y, z), -(d0 + 0.05), 0.0), 0.004)
    # panel gaps
    g1 = smax(SIDE_LINES(x, z) - 0.0022, (yside(x, z) - 0.012) - ay, 0.0)
    zref = np.where(x > 0, bonnet_h(x), deck_h(x))
    g2 = smax(TOP_LINES(x, y) - 0.0022, (ztop(x, ay) - 0.012) - z, 0.0)
    fuel = smax(np.abs(np.hypot(x - FUEL[0], z - FUEL[1]) - 0.048) - 0.0018, 0.45 - y, 0.0)
    g = np.minimum(np.minimum(g1, g2), fuel)
    d = smax(d, -smax(g, -(d0 + 0.006), 0.0), 0.0012)
    return d

def windows(x, y, z):
    ay = np.abs(y)
    sw = smax(SIDEWIN(x, z), 0.40 - ay, 0.0)
    ws = smax(WSCREEN(x, y), 0.80 - z, 0.0)
    rw = smax(REARWIN(x, y), 0.95 - z, 0.0)
    return np.minimum(np.minimum(sw, ws), rw)

def interior_cavity(P, d0):
    x, y, z = P[:,0], P[:,1], P[:,2]
    box = smax(smax(np.abs(x + 0.95) - 1.05, np.abs(y) - 0.90, 0.04), np.abs(z - 0.70) - 0.56, 0.04)
    return smax(d0 + 0.012, box, 0.02)

def outer(P):
    d0 = shell(P)
    d = features(P, d0)
    return smax(d, -interior_cavity(P, d0), 0.006)

def glass(P):
    x, y, z = P[:,0], P[:,1], P[:,2]
    d0 = shell(P)
    return smax(np.abs(d0 + 0.006) - 0.0025, windows(x, y, z) - 0.010, 0.0)

def head_lens(P):
    x, y, z = P[:,0], P[:,1], P[:,2]
    d0 = shell(P)
    return smax(smax(np.abs(d0 + 0.0035) - 0.0025, HEAD(x, np.abs(y)) + 0.0005, 0.0), np.maximum(1.6 - x, (ztop(x, np.abs(y)) - 0.045) - z), 0.0)

def tail_lens(P):
    x, y, z = P[:,0], P[:,1], P[:,2]
    d0 = shell(P)
    return smax(smax(np.abs(d0 + 0.003) - 0.002, TAIL(y, z) + 0.0005, 0.0), x + 1.9, 0.0)

SLOTS = ['paint_body', 'trim_black', 'carbon', 'lamp_housing', 'interior_trim', 'grille']
def labels(P):
    x, y, z = P[:,0], P[:,1], P[:,2]; ay = np.abs(y)
    d0 = shell(P)
    lab = np.zeros(len(P), np.int32)
    lab[(d0 < -0.004) & ~((z > ztop(x, ay) - 0.05) & (HEAD(x, ay) < 0.002) & (x > 1.6))] = 5
    lab[(z < 0.150) & (x < 2.30) & (x > -2.05)] = 2
    lab[(x < -2.10) & (z < 0.42)] = 2
    lab[(x > 2.22) & (z < 0.20)] = 2
    lab[(FVENT(x, z) < 0.004) & (ay > yside(x, z) - 0.16)] = 2          # fender vent blades carbon
    lab[(BVENT(x, ay) < 0.004) & (z > ztop(x, ay) - 0.07)] = 2          # bonnet louvres carbon
    lab[(FRONT_C(ay, z) < 0.0) & (x > 2.2)] = 5
    near_top = z > ztop(x, ay) - 0.02; near_side = ay > yside(x, z) - 0.02
    sw = smax(SIDEWIN(x, z), 0.40 - ay, 0.0); ws = np.minimum(smax(WSCREEN(x, y), 0.80 - z, 0.0), smax(REARWIN(x, y), 0.95 - z, 0.0))
    lab[(sw < 0.022) & (d0 > -0.006) & near_side & (z > 0.8)] = 1
    lab[(ws < 0.022) & (d0 > -0.006) & near_top] = 1
    lab[(HEAD(x, ay) < 0.0) & (x > 1.6) & (d0 < -0.002) & (z > ztop(x, ay) - 0.05)] = 3
    lab[(TAIL(y, z) < 0.0) & (x < -1.9) & (d0 < -0.002)] = 3
    lab[d0 < -0.010] = 4
    lab[(d0 < -0.010) & ((x < -2.0) | (x > 0.12))] = 5
    return lab

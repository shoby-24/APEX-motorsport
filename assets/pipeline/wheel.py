"""Forged 5x2-spoke centre-lock wheel + caliper as SDFs. Local frame: a = axial (+ = outboard), wheel axis through origin.
Points are given as (u, v, a): u,v in the wheel face plane."""
import numpy as np
from sdf import Field2D, smin, smax, spline, interp

RIM_R = 0.254          # 20 in bead seat radius
RIM_W = 0.24
A_FACE = 0.105         # outboard face of the rim lip

# Y spoke template along +u (polygon in face plane)
_sp = np.array([(0.055,0.0125),(0.150,0.0105),(0.236,0.0088),(0.246,0.0120),(0.255,0.0170),
                (0.255,-0.0170),(0.246,-0.0120),(0.236,-0.0088),(0.150,-0.0105),(0.055,-0.0125)])
NSPOKE = 12
SPOKE = Field2D.polygon(_sp, pad=0.05, res=0.0005)
# barrel profile in (r, a): closed polygon, lip on both sides
_bp = [(0.236,-0.125),(0.258,-0.125),(0.262,-0.118),(0.250,-0.110),(0.242,-0.105),(0.240,-0.040),(0.232,-0.020),
       (0.232,0.080),(0.240,0.095),(0.252,0.100),(0.262,0.105),(0.264,0.112),(0.258,0.117),(0.236,0.117),(0.228,0.100),
       (0.224,0.080),(0.224,-0.020),(0.230,-0.045),(0.230,-0.118)]
BARREL = Field2D.polygon(_bp, pad=0.03, res=0.0005)

def face_a(r):   # front surface of the spokes (concave dish)
    t = np.clip((r - 0.06) / 0.18, 0, 1)
    return 0.030 + 0.080 * t ** 1.6

def rim(P):
    u, v, a = P[:,0], P[:,1], P[:,2]
    r = np.hypot(u, v); th = np.arctan2(v, u)
    d = BARREL(r, a)
    # spokes: 5 rotated copies
    seg = 2 * np.pi / NSPOKE
    t = (th + seg / 2) % seg - seg / 2
    sp = SPOKE(r * np.cos(t), r * np.sin(t))
    fa = face_a(r)
    thick = interp(r, [0.06, 0.15, 0.24], [0.040, 0.030, 0.024])
    spk = smax(sp, np.abs(a - (fa - thick / 2)) - thick / 2, 0.004)
    # pocket milled into each spoke face
    # centre ridge chamfers on each spoke face: shallow V groove
    ridge = smax(np.abs(r * np.sin(t)) - 0.0012, np.abs(a - fa) - 0.0015, 0.0008)
    ridge = smax(ridge, np.maximum(0.095 - r, r - 0.228), 0.002)
    spk = smax(spk, -ridge, 0.0008)
    # hub
    hub = smax(r - 0.092, np.abs(a - 0.012) - 0.030, 0.008)
    d = smin(d, smin(spk, hub, 0.012), 0.008)
    # centre bore + centre-lock nut with 12 notches
    d = smax(d, -(r - 0.040), 0.002)
    nut = smax(r - 0.054, np.abs(a - 0.052) - 0.014, 0.003)
    hexn = smax(np.max(np.abs(np.stack([u*np.cos(k*np.pi/3)+v*np.sin(k*np.pi/3) for k in range(3)])),0) - 0.046, np.abs(a - 0.070) - 0.006, 0.002)
    nut = smin(nut, hexn, 0.002)
    notch = np.abs(((th * 12 / (2 * np.pi)) % 1.0) - 0.5) * (2 * np.pi * r / 12) - 0.004
    nut = smax(nut, -smax(notch, np.maximum(0.040 - r, a - 0.064), 0.0), 0.001)
    nut = smax(nut, -(r - 0.018), 0.001)
    d = smin(d, nut, 0.0)
    return d

def caliper(P, disc_r=0.205, ang=np.radians(35)):
    """Six-piston monoblock wrapped around the disc edge, centred at angle `ang` in the face plane."""
    u, v, a = P[:,0], P[:,1], P[:,2]
    r = np.hypot(u, v); th = np.arctan2(v, u) - ang
    th = (th + np.pi) % (2 * np.pi) - np.pi
    arc = r * th
    body = smax(smax(np.abs(r - 0.188) - 0.034, np.abs(arc) - 0.135 * (1 - 0.15 * np.clip((r - 0.17) / 0.05, 0, 1)), 0.014),
                np.abs(a + 0.050) - 0.042, 0.010)
    slot = smax(np.abs(a + 0.050) - 0.022, 0.168 - r, 0.004)
    body = smax(body, -slot, 0.003)
    # bridge window on the outer face
    win = smax(smax(np.abs(r - 0.196) - 0.010, np.abs(arc) - 0.070, 0.004), np.abs(a + 0.050) - 0.050, 0.0)
    body = smax(body, -smax(win, -(a + 0.020), 0.0), 0.002)
    return body

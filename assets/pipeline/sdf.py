"""Small SDF modelling kernel: 2D raster fields + smooth booleans + blockwise marching cubes."""
import numpy as np
from scipy import ndimage
from skimage import measure
from matplotlib.path import Path

def smin(a, b, k):
    if k <= 0: return np.minimum(a, b)
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)

def smax(a, b, k):
    return -smin(-a, -b, k)

class Field2D:
    """Signed (polygon) or unsigned (polyline) 2D distance field sampled bilinearly."""
    def __init__(self, umin, umax, vmin, vmax, res=0.002):
        self.u0, self.v0, self.res = umin, vmin, res
        self.nu = int(np.ceil((umax - umin) / res)) + 1
        self.nv = int(np.ceil((vmax - vmin) / res)) + 1
        self.d = None
    def _grid(self):
        u = self.u0 + np.arange(self.nu) * self.res
        v = self.v0 + np.arange(self.nv) * self.res
        U, V = np.meshgrid(u, v, indexing='ij')
        return U, V
    @classmethod
    def polygon(cls, pts, pad=0.3, res=0.002):
        pts = np.asarray(pts, float)
        key = _key('poly', pts, pad, res)
        hit = _load(key)
        if hit is not None: return hit
        f = cls(pts[:,0].min()-pad, pts[:,0].max()+pad, pts[:,1].min()-pad, pts[:,1].max()+pad, res)
        U, V = f._grid()
        inside = Path(pts).contains_points(np.c_[U.ravel(), V.ravel()]).reshape(U.shape)
        dist = _dist_to_polyline(np.vstack([pts, pts[:1]]), U, V)
        f.d = np.where(inside, -dist, dist).astype(np.float32)
        f._prep(); _save(key, f)
        return f
    def _prep(self):
        self.c = ndimage.spline_filter(self.d.astype(np.float64), order=3)
    @classmethod
    def polylines(cls, lines, bounds, res=0.001):
        key = _key('lines', *[np.asarray(l, float) for l in lines], np.asarray(bounds), res)
        hit = _load(key)
        if hit is not None: return hit
        f = cls(*bounds, res=res)
        mask = np.zeros((f.nu, f.nv), bool)
        for ln in lines:
            ln = np.asarray(ln, float)
            for a, b in zip(ln[:-1], ln[1:]):
                n = int(np.ceil(np.linalg.norm(b - a) / (res * 0.5))) + 1
                t = np.linspace(0, 1, n)[:, None]
                p = a + (b - a) * t
                iu = np.round((p[:,0] - f.u0) / res).astype(int)
                iv = np.round((p[:,1] - f.v0) / res).astype(int)
                ok = (iu >= 0) & (iu < f.nu) & (iv >= 0) & (iv < f.nv)
                mask[iu[ok], iv[ok]] = True
        f.d = np.full(mask.shape, 9.0, np.float32)
        f.d = np.minimum(f.d, 9.0)
        dd = None
        for ln in lines:
            dl = _dist_to_polyline(np.asarray(ln, float), *f._grid())
            dd = dl if dd is None else np.minimum(dd, dl)
        f.d = dd.astype(np.float32)
        f._prep(); _save(key, f)
        return f
    def __call__(self, u, v):
        iu = (np.asarray(u) - self.u0) / self.res
        iv = (np.asarray(v) - self.v0) / self.res
        out = ndimage.map_coordinates(self.c, [iu.ravel(), iv.ravel()], order=3, mode='nearest', prefilter=False).reshape(np.shape(u))
        # outside the raster, grow distance linearly
        du = np.maximum(np.maximum(-iu, iu - (self.nu - 1)), 0) * self.res
        dv = np.maximum(np.maximum(-iv, iv - (self.nv - 1)), 0) * self.res
        return out + np.hypot(du, dv)

import hashlib, pickle, os
WORK = os.environ.get('APEX_WORK') or os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'build', 'cache')
CACHE = os.path.join(WORK, 'fieldcache')
def _key(*parts):
    h = hashlib.sha1()
    for p in parts: h.update(np.asarray(p).tobytes() if not isinstance(p, str) else p.encode())
    return h.hexdigest()
def _load(k):
    p = os.path.join(CACHE, k + '.pkl')
    if os.path.exists(p):
        with open(p, 'rb') as fh: return pickle.load(fh)
def _save(k, f):
    os.makedirs(CACHE, exist_ok=True)
    with open(os.path.join(CACHE, k + '.pkl'), 'wb') as fh: pickle.dump(f, fh, protocol=4)

def _dist_to_polyline(poly, U, V, step=0.0004):
    from scipy.spatial import cKDTree
    pts = []
    for a, b in zip(poly[:-1], poly[1:]):
        n = max(2, int(np.ceil(np.linalg.norm(b - a) / step)) + 1)
        pts.append(a + (b - a) * np.linspace(0, 1, n)[:, None])
    tree = cKDTree(np.vstack(pts))
    d, _ = tree.query(np.c_[U.ravel(), V.ravel()], workers=-1)
    return d.reshape(U.shape)

def spline(pts, n=24, closed=False):
    """Catmull-Rom through points -> dense polyline."""
    P = np.asarray(pts, float)
    if closed: P = np.vstack([P[-1], P, P[0], P[1]])
    else: P = np.vstack([P[0], P, P[-1]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i-1], P[i], P[i+1], P[i+2]
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t*t, t*t*t
            out.append(0.5*((2*p1) + (-p0+p2)*t + (2*p0-5*p1+4*p2-p3)*t2 + (-p0+3*p1-3*p2+p3)*t3))
    if not closed: out.append(P[-2])
    return np.array(out)

def interp(x, xs, ys):
    return np.interp(x, xs, ys).astype(np.float32)

def mesh_sdf(fn, bounds, vox=0.0025, block=96, band=4, label=""):
    """Blockwise narrow-band marching cubes of fn(P[N,3])->d.
    Each block is first sampled every `band` voxels; exact values are computed only near the surface."""
    import time; t0 = time.time()
    (x0, x1), (y0, y1), (z0, z1) = bounds
    n = [int(np.ceil((b - a) / vox)) + 1 for a, b in bounds]
    B = block - block % band
    verts, faces, nv, nevals = [], [], 0, 0
    for bi in range(0, n[0] - 1, B):
        for bj in range(0, n[1] - 1, B):
            for bk in range(0, n[2] - 1, B):
                rng = [np.arange(s0, min(s0 + B + 1, nn)) for s0, nn in zip((bi, bj, bk), n)]
                if min(len(r) for r in rng) < 2: continue
                org = np.array([x0, y0, z0]) + vox * np.array([r[0] for r in rng])
                shp = [len(r) for r in rng]
                # coarse lattice (includes last index)
                cidx = [np.unique(np.r_[np.arange(0, s, band), s - 1]) for s in shp]
                C = np.stack(np.meshgrid(*[org[a] + cidx[a] * vox for a in range(3)], indexing='ij'), -1)
                Dc = fn(C.reshape(-1, 3).astype(np.float32)).reshape(C.shape[:3]); nevals += Dc.size
                cell = band * vox * 1.8
                if Dc.min() > cell or Dc.max() < -cell: continue
                from scipy.interpolate import RegularGridInterpolator
                it = RegularGridInterpolator([c.astype(float) for c in cidx], Dc)
                F = np.stack(np.meshgrid(*[np.arange(s) for s in shp], indexing='ij'), -1).reshape(-1, 3)
                D = it(F).astype(np.float32)
                near = np.abs(D) < cell
                P = (org + F[near] * vox).astype(np.float32)
                D[near] = fn(P); nevals += len(P)
                D = D.reshape(shp)
                if D.min() > 0 or D.max() < 0: continue
                v, f, _, _ = measure.marching_cubes(D, 0.0, spacing=(vox, vox, vox))
                v += org
                verts.append(v.astype(np.float32)); faces.append(f + nv); nv += len(v)
    if not verts: return np.zeros((0,3),np.float32), np.zeros((0,3),np.int64)
    V = np.concatenate(verts); F = np.concatenate(faces)
    key = np.round(V / (vox * 0.01)).astype(np.int64)
    _, idx, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    V = V[idx]; F = inv.reshape(-1)[F]
    F = F[(F[:,0]!=F[:,1]) & (F[:,1]!=F[:,2]) & (F[:,0]!=F[:,2])]
    print(f"[mesh {label}] {len(V)} verts {len(F)} tris, {nevals/1e6:.1f}M evals, {time.time()-t0:.1f}s", flush=True)
    return V, F

def grad(fn, P, h=0.002):
    e = np.eye(3, dtype=np.float32) * h
    g = np.stack([fn(P + e[i]) - fn(P - e[i]) for i in range(3)], -1)
    n = np.linalg.norm(g, axis=1, keepdims=True) + 1e-12
    return g / n

class Grid2D:
    """Regular-grid scalar table with bilinear lookup (e.g. top-surface height z(x, |y|))."""
    def __init__(self, u0, v0, du, dv, data):
        self.u0, self.v0, self.du, self.dv, self.d = u0, v0, du, dv, data.astype(np.float32)
    def __call__(self, u, v):
        iu = (np.asarray(u) - self.u0) / self.du; iv = (np.asarray(v) - self.v0) / self.dv
        return ndimage.map_coordinates(self.d, [np.ravel(iu), np.ravel(iv)], order=1, mode='nearest').reshape(np.shape(u))

def extent_table(fn, axis, ua, va, lo, hi, key, coarse=80, iters=14, fill=-1.0):
    """For each (u, v) column find the largest t in [lo, hi] along `axis` with fn < 0. Cached."""
    k = _key('ext' + key, np.asarray(ua), np.asarray(va), np.asarray([lo, hi, axis]))
    hit = _load(k)
    if hit is not None: return hit
    U, Vv = np.meshgrid(ua, va, indexing='ij'); n = U.size
    def P(t):
        cols = [None, None, None]
        others = [a for a in range(3) if a != axis]
        cols[others[0]] = U.ravel(); cols[others[1]] = Vv.ravel(); cols[axis] = t
        return np.stack(cols, 1).astype(np.float32)
    ts = np.linspace(hi, lo, coarse)
    best = np.full(n, np.nan); found = np.zeros(n, bool)
    prev = np.full(n, hi)
    for t in ts:
        inside = fn(P(np.full(n, t))) < 0
        new = inside & ~found
        best[new] = t; found |= inside
        prev = np.where(found, prev, t)
    # refine between best (inside) and best + step (outside)
    step = (hi - lo) / (coarse - 1)
    a = np.where(found, best, lo); b = np.where(found, best + step, lo)
    for _ in range(iters):
        m = (a + b) / 2
        ins = fn(P(m)) < 0
        a = np.where(ins, m, a); b = np.where(ins, b, m)
    out = np.where(found, a, fill).reshape(U.shape)
    g = Grid2D(ua[0], va[0], ua[1] - ua[0], va[1] - va[0], out)
    _save(k, g)
    return g

def relax(V, F, fn, iters=3, lam=0.6):
    """Tangential Laplacian relaxation + projection back onto the zero set (removes MC terracing in triangle normals)."""
    from scipy import sparse
    n = len(V)
    I = np.concatenate([F[:,0], F[:,1], F[:,2], F[:,1], F[:,2], F[:,0]])
    J = np.concatenate([F[:,1], F[:,2], F[:,0], F[:,0], F[:,1], F[:,2]])
    A = sparse.csr_matrix((np.ones(len(I), np.float32), (I, J)), shape=(n, n))
    A.data[:] = 1.0
    deg = np.asarray(A.sum(1)).ravel(); deg[deg == 0] = 1
    V = V.astype(np.float32).copy()
    for _ in range(iters):
        N = grad(fn, V)
        L = (A @ V) / deg[:, None] - V
        L -= (L * N).sum(1, keepdims=True) * N
        V += lam * L
        for _ in range(2):
            d = fn(V); N = grad(fn, V)
            V -= d[:, None] * N
    return V

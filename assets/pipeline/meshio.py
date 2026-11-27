import numpy as np, sdf
def orient(V, F, fn):
    N = sdf.grad(fn, V)
    fnrm = np.cross(V[F[:,1]] - V[F[:,0]], V[F[:,2]] - V[F[:,0]])
    flip = (fnrm * N[F].mean(1)).sum(1) < 0
    F = F.copy(); F[flip] = F[flip][:, ::-1]
    return N, F

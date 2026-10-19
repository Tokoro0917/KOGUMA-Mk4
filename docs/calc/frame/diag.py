"""初めの形(v3)のどこがたわんでいるかを見る"""
import numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
import fem, design as dz, analyze as an
from scipy.sparse.linalg import eigsh
g = dz.build()
mesh = fem.make_mesh(g['domain'], g['pc'], 0.6, 0.3)
M = fem.Model(mesh, g['pc'], g['clamps'])
K = M.K_bend(); D = M.clamp_dofs_bend()
FA = M.load_patch(45, 0, 1.0, 3.0)
(w,), _ = fem.solve_multi(K, [FA], D)
wv = w[M.bb.nodal_dofs[0]]
vx, vy = mesh.p
for x in (0, 7, 23, 30, 38, 45):
    sel = (np.abs(vx - x) < 0.8) & (np.abs(vy) < 1.5)
    print(f'x={x:3d}: 中心線のたわみ {np.abs(wv[sel]).max():.3f} mm')
fig, ax = plt.subplots(1, 2, figsize=(13, 4.5))
tp = ax[0].tripcolor(vx, vy, mesh.t.T, np.abs(wv), shading='gouraud', cmap='viridis')
fig.colorbar(tp, ax=ax[0]); ax[0].set_aspect('equal'); ax[0].set_title('LC-A: front skid 3N, |w| [mm]')
# 座屈のモード(正面衝突)
Ki = M.K_in(); Di = M.clamp_dofs_inplane()
FD, _ = M.load_edge(lambda x, y: (x > dz.XE - 0.05) & (np.abs(y) < 15), (-50, 0))
(u,), _ = fem.solve_multi(Ki, [FD], Di)
sx, sy, sxy = M.inplane_stress_qp(u)
KG = M.K_geo(sx, sy, sxy)
I = np.setdiff1d(np.arange(K.shape[0]), D)
vals, vecs = eigsh(K[I][:, I].tocsc(), k=1, M=(-KG[I][:, I]).tocsc(), sigma=1e-2, which='LM', mode='buckling')
phi = np.zeros(K.shape[0]); phi[I] = vecs[:, 0]
pv = phi[M.bb.nodal_dofs[0]]
tp = ax[1].tripcolor(vx, vy, mesh.t.T, np.abs(pv) / np.abs(pv).max(), shading='gouraud', cmap='magma')
ax[1].set_aspect('equal'); ax[1].set_title(f'LC-D buckling mode (lambda={vals[0]:.2f})')
for a in ax:
    for c in g['clamps']:
        a.plot(*c.exterior.xy, 'w-', lw=1)
fig.tight_layout(); fig.savefig('diag_v3.png', dpi=110)

"""基板(FR4)の固有振動。柱で留め、部品・電池・壁センサを質量で載せる(2026-10-28)
使い方(リポジトリの一番上で): python3 mechanical/vehicle/pcb_modes.py 厚さ [stiff]
  stiff: 電池の所は曲がらないとみなす。holders: 壁センサのホルダの所でフレームに支えられる(ホルダ v3、2026-10-31。固く支えるとした上限)"""
import sys, numpy as np
sys.path.insert(0, 'docs/calc/frame'); sys.path.insert(0, 'mechanical/vehicle')
import fem
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from shapely import affinity
from skfem import Basis, BilinearForm, asm, ElementTriMorley
from skfem.helpers import dd
from scipy.sparse.linalg import eigsh
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt

T_PCB = float(sys.argv[1]) if len(sys.argv) > 1 else 0.6
BAT_STIFF = "stiff" in sys.argv
import pcb_shape as ps
pcb = ps.outline()
FAN = ps.FAN
POSTS = [(-17.0, 22.0), (-17.0, -22.0), (8.0, 22.0), (8.0, -22.0)] + ([(20.0, 22.0), (20.0, -22.0)] if "post20" in sys.argv else [])
mesh = fem.make_mesh(pcb, [], 1.0, 0.8)
E, nu, rho = 22000.0, 0.15, 1.85e-9          # FR4
cent = mesh.p[:, mesh.t].mean(axis=1)
p, t = mesh.p, mesh.t
a_ = p[:, t[1]] - p[:, t[0]]; b_ = p[:, t[2]] - p[:, t[0]]
area = np.abs(a_[0] * b_[1] - a_[1] * b_[0]) / 2
bat = (cent[0] >= ps.BAT[0]) & (cent[0] <= ps.BAT[1]) & (np.abs(cent[1]) <= ps.BAT[2])
D = E * T_PCB**3 / (12 * (1 - nu**2)) * np.ones(t.shape[1])
if BAT_STIFF:                                 # 電池を両面テープで貼り、電池の所は曲がらないとみなす(上限)
    D[bat] *= 1000
rt = rho * T_PCB * np.ones(t.shape[1])
rt += 2.5e-6 / area.sum()                     # 部品 2.5g を全体に広げる
rt[bat] += 14.5e-6 / area[bat].sum()          # 電池 14.5g
SENS = {k: ps.holder(k).centroid.coords[0] for k in ps.SENS}   # ホルダの真ん中(v6 までは寝かせたセンサの位置)
for (x0, y0) in SENS.values():                # 壁センサ 0.39g(発光 + 受光 0.2g、ホルダ 0.19g。基板 v7 から。ホルダは基板の裏)
    k = (cent[0] - x0)**2 + (cent[1] - y0)**2 <= 2.0**2
    rt[k] += 0.39e-6 / area[k].sum()
bb = Basis(mesh, ElementTriMorley(), intorder=4)
nq = bb.X.shape[1]
ef = lambda a: np.repeat(a[:, None], nq, axis=1)
@BilinearForm
def kf(u, v, w):
    U, V = dd(u), dd(v)
    return w.D * (U[0, 0] * V[0, 0] + U[1, 1] * V[1, 1] + nu * (U[0, 0] * V[1, 1] + U[1, 1] * V[0, 0]) + 2 * (1 - nu) * U[0, 1] * V[0, 1])
@BilinearForm
def mf(u, v, w):
    return w.rt * u * v
K = asm(kf, bb, D=ef(D)); M = asm(mf, bb, rt=ef(rt))
# 柱(ねじの頭 φ3.5 で押さえる)の所は固定
clampel = np.zeros(t.shape[1], bool)
for (x0, y0) in POSTS:
    clampel |= (cent[0] - x0)**2 + (cent[1] - y0)**2 <= 1.9**2
if 'holders' in sys.argv:   # ホルダの足元(上から見た形)をフレームで支える
    from shapely import contains_xy
    for k in ps.SENS:
        clampel |= contains_xy(ps.holder(k), cent[0], cent[1])
Dofs = np.unique(bb.element_dofs[:, clampel])
I = np.setdiff1d(np.arange(K.shape[0]), Dofs)
vals, vecs = eigsh(K[I][:, I], k=6, M=M[I][:, I], sigma=0, which='LM')
f = np.sqrt(np.abs(vals)) / (2 * np.pi)
print(f'基板 {T_PCB}mm、電池 {"固い" if BAT_STIFF else "質量だけ"}、基板+部品+電池+センサ {rt @ area * 1e6:.1f} g')
fig, axs = plt.subplots(2, 3, figsize=(17, 7.5))
nodal = bb.nodal_dofs[0]
for i in range(6):
    w = np.zeros(K.shape[0]); w[I] = vecs[:, i]; wn = w[nodal]; wn /= np.abs(wn).max()
    sens = {k: wn[np.argmin((p[0] - x)**2 + (p[1] - y)**2)] for k, (x, y) in SENS.items()}
    print(f'  {i+1}次 {f[i]:7.0f} Hz  センサの所の揺れ(最大を1): ' + ', '.join(f'{k} {abs(v):.2f}' for k, v in sens.items()))
    ax = axs.flat[i]; ax.tripcolor(p[0], p[1], t.T, wn, cmap='RdBu_r', shading='gouraud', vmin=-1, vmax=1)
    for (x0, y0) in POSTS: ax.plot(x0, y0, 'k^')
    for (x0, y0) in SENS.values(): ax.plot(x0, y0, 'ms', ms=5)
    ax.set_aspect('equal'); ax.set_title(f'mode {i+1}: {f[i]:.0f} Hz'); ax.set_xlim(-50, 48); ax.set_ylim(-36, 36)
fig.suptitle(f'PCB FR4 {T_PCB} mm, posts (black), wall sensors (magenta); battery {"bonded (stiff)" if BAT_STIFF else "mass only"}')
fig.tight_layout(); fig.savefig(f'docs/img/vehicle/pcb_modes_{ps.VER}_{T_PCB}_{"post20_" if "post20" in sys.argv else ""}{"holders_" if "holders" in sys.argv else ""}{"stiff" if BAT_STIFF else "mass"}.png', dpi=90)

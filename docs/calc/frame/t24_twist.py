"""frame t24v9 と main のねじれの硬さと、揺れ方(固有振動数の上から5つ)。使い方(このディレクトリで): python3 t24_twist.py t24 / python3 t24_twist.py main
マウントのねじの所を固定(マウントと基板は硬いとみる)。前・後ろの角 (±49.2, ±22) に上下逆の力 ±0.5N をかけて、左右の角の高さの差からねじれの角度を出す(2026-11-23)"""
import json, sys, numpy as np
sys.path.insert(0, '.')
which = sys.argv[1]
if which == 't24':
    import t24; t24.set_suction('w2')
    import design as dz
    P = dict(json.load(open('results/t24v9_params.json')))
else:
    import design as dz
    P = dict(json.load(open('results/final_params.json')))
P.pop('base', None)
import fem, analyze as an
from scipy.sparse.linalg import eigsh
g = dz.build(**P)
mesh = fem.make_mesh(g['domain'], g['pc'], 0.45, 0.15)
M = fem.Model(mesh, g['pc'], g['clamps'], ribs=g['vribs'])
K = M.K_bend(); D = M.clamp_dofs_bend()
vx, vy = mesh.p
idx = M.bb.nodal_dofs[0]
def at(w, x0, y0):
    k = np.argmin((vx - x0)**2 + (vy - y0)**2); return w[idx][k]
yc = 22.0; xf = 49.2; xr = -(dz.XE - 0.8)
for name, x0 in (('前', xf), ('後ろ', xr)):
    F = M.load_patch(x0, yc, 1.0, 0.5) - M.load_patch(x0, -yc, 1.0, 0.5)
    w = fem.solve_multi(K, [F], D)[0][0]
    ang = (at(w, x0, yc) - at(w, x0, -yc)) / (2 * yc)
    T = 0.5 * 2 * yc
    print(f'{name}のねじれ: 1 N·mm で {np.degrees(ang / T) * 1000:.2f} m°、ねじれの硬さ {T / np.degrees(ang):.0f} N·mm/°、角の上下 ±0.5N で {at(w, x0, yc):.3f}mm')
# 片方の前の角だけ 1.5N(B_corner)のときの、左右の角の高さ
F = M.load_patch(xf, yc, 1.0, 1.5)
w = fem.solve_multi(K, [F], D)[0][0]
print(f'前の角に 1.5N: 押した角 {at(w, xf, yc):.3f}mm、反対の角 {at(w, xf, -yc):.3f}mm、前の真ん中 {at(w, 45, 0):.3f}mm')
Mm = M.M_bend(an.MASSES)
I = np.setdiff1d(np.arange(K.shape[0]), D)
lam, vec = eigsh(K[I][:, I], k=5, M=Mm[I][:, I], sigma=0, which='LM')
o = np.argsort(lam)
for j in o:
    u = np.zeros(K.shape[0]); u[I] = vec[:, j]; w = u[idx]
    # 左右の対称・反対称、前後のどちらが大きく動くか
    k2 = np.array([np.argmin((vx - a)**2 + (vy + b)**2) for a, b in zip(vx, vy)])
    sym = np.abs(w + w[k2]).max() / np.abs(w).max() / 2
    kind = 'ねじれ(左右が逆)' if sym < 0.2 else ('曲げ(左右が同じ)' if sym > 0.8 else '混ざり')
    fr = np.abs(w[vx > 30]).max(); re = np.abs(w[vx < -30]).max(); mid = np.abs(w[np.abs(vx) < 25]).max()
    k = np.argmax(np.abs(w))
    print(f'{np.sqrt(lam[j]) / 2 / np.pi:.0f}Hz {kind}、一番動く所 ({vx[k]:.0f}, {vy[k]:.0f})、前 {fr / np.abs(w).max():.2f} 後ろ {re / np.abs(w).max():.2f} 真ん中 {mid / np.abs(w).max():.2f}')

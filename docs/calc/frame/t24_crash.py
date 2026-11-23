"""frame t24v7 の衝突で割れる力・座屈する力と、割れやすい所(2026-11-23)。使い方(このディレクトリで): python3 t24_crash.py
正面(30mm・柱 12mm・端寄り)、前の角に柱(45°)、横。力 1N で解いて、Tsai-Hill が 1 になる力を出す。図は docs/img/frame/t24v6_crash_spots.png(手で印を付けた)"""
import json, sys, numpy as np
sys.path.insert(0, '.')
import t24, design as dz, fem
from scipy.sparse.linalg import eigsh
P = dict(json.load(open('results/t24v7_params.json'))); t24.set_suction('w2')
g = dz.build(**P)
mesh = fem.make_mesh(g['domain'], g['pc'], 0.45, 0.15)
M = fem.Model(mesh, g['pc'], g['clamps'], ribs=g['vribs'])
Ki = M.K_in(); Di = M.clamp_dofs_inplane(); K = M.K_bend(); D = M.clamp_dofs_bend()
XE, YE = dz.XE, dz.YE
c = np.sqrt(0.5)
cases = {
 '正面(前の辺の真ん中 30mm)': (lambda x, y: (x > XE - 0.05) & (np.abs(y) < 15), (-1, 0)),
 '柱に正面(前の辺の真ん中 12mm)': (lambda x, y: (x > XE - 0.05) & (np.abs(y) < 6), (-1, 0)),
 '柱に正面(前の辺の端寄り y 12〜24)': (lambda x, y: (x > XE - 0.05) & (y > 12) & (y < 24), (-1, 0)),
 '柱に前の角(斜め 45°)': (lambda x, y: (x > XE - 6) & (y > YE - 6), (-c, -c)),
 '横(切り欠きの前後の辺)': (lambda x, y: (y > dz.YB - 0.05) & (np.abs(x) > dz.SLOT_L / 2) & (np.abs(x) < dz.XB), (0, -1)),
}
X = M.bi.global_coordinates().value    # (2, nel, nqp)
mask = M.ef(M.ispc).astype(bool)
for name, (sel, F) in cases.items():
    Fv, L = M.load_edge(sel, F)
    u = fem.solve_multi(Ki, [Fv], Di)[0][0]
    sx, sy, sxy = M.inplane_stress_qp(u)
    fi = fem.tsai_hill(sx, sy, sxy, mask)
    idx = np.unravel_index(np.argmax(fi), fi.shape)
    Ffail = 1 / np.sqrt(fi.max())
    # 割れる所の上位(離れた所)
    flat = np.argsort(fi.ravel())[::-1]
    pts = []
    for k in flat[:4000]:
        e, q = np.unravel_index(k, fi.shape)
        p = (X[0, e, q], X[1, e, q])
        if all(np.hypot(p[0] - a, p[1] - b) > 4 for a, b, _ in pts):
            pts.append((p[0], p[1], 1 / np.sqrt(fi[e, q])))
        if len(pts) == 4: break
    bk = fem.buckling(K, M.K_geo(sx, sy, sxy), D)
    print(f'{name}: 割れる力 {Ffail:.0f}N、座屈する力 {bk:.0f}N。割れやすい所 ' + '、'.join(f'({a:.1f}, {b:.1f}) {f:.0f}N' for a, b, f in pts))

"""吸引する面の窓をカーボンで埋め、塩ビのシートをなくした案(2026-11-23、ユーザー「ねじの上に塩ビを貼るのが嫌、0.8mm にして埋めたい」)。
使い方(このディレクトリで): python3 t24_solid.py
t24v9 の形のまま、(1) 今(1.0mm + 塩ビ 0.2mm)、(2) 1.0mm で埋める、(3) 0.8mm で埋める、を同じ荷重で比べる。
吸引する面の外の窓はそのまま。たわみ・座屈・割れる力は t24.run と同じ計算"""
import json, sys, numpy as np
sys.path.insert(0, '.')
import t24, design as dz, fem, analyze as an
from scipy.sparse.linalg import eigsh

t24.set_suction('w2')
P0 = dict(json.load(open('results/t24v9_params.json')))
P0.pop('base', None)
L = an.LOADS
SKIRT_X, SKIRT_Y = 40.0, 21.3


def run(t_mm, solid):
    """板の厚さ t_mm、solid なら吸引する面の窓を埋める。結果を dict で返す"""
    g = dz.build(**dict(P0, _t=t_mm, _solid=solid))     # 厚さと窓を埋めるかは t24.build_t24 が受け取る
    mc, mp, iz = dz.mass_iz(g)
    mesh = fem.make_mesh(g['domain'], g['pc'], 0.45, 0.15)
    M = fem.Model(mesh, g['pc'], g['clamps'], ribs=g['vribs'])
    r = dict(m_carbon=mc, m_pc=mp)
    K = M.K_bend()
    D = M.clamp_dofs_bend()
    FA = M.load_patch(45, 0, 1.0, L['A_front'])
    FB = M.load_patch(49.2, 22.0, 1.0, L['B_corner'])
    FC, area = M.load_pressure(g['suction'], 1.0)
    ws, _ = fem.solve_multi(K, [FA, FB, FC * (5.9 / area)], D)
    vx, vy = mesh.p
    wv = [w[M.bb.nodal_dofs[0]] for w in ws]
    near = lambda x0, y0, rr: (vx - x0)**2 + (vy - y0)**2 <= rr**2
    r['dA'] = np.abs(wv[0][near(45, 0, 1.0)]).max()
    r['dB'] = np.abs(wv[1][near(49.2, 22, 1.0)]).max()
    front = (np.abs(vx - SKIRT_X) < 0.6) & (np.abs(vy) <= SKIRT_Y)
    side = (np.abs(np.abs(vy) - SKIRT_Y) < 0.6) & (np.abs(vx) <= SKIRT_X)
    inside = (np.abs(vx) <= SKIRT_X) & (np.abs(vy) <= SKIRT_Y)
    r['skirt_front'] = np.abs(wv[2][front]).max()
    r['skirt_side'] = np.abs(wv[2][side]).max()
    r['suction_max'] = np.abs(wv[2][inside]).max()
    sf = []
    for w in ws:
        sx, sy, sxy = M.bend_stress(w)
        fi = max(fem.tsai_hill(sx, sy, sxy, M.ispc).max(), fem.tsai_hill(-sx, -sy, -sxy, M.ispc).max())
        sf.append(1 / np.sqrt(fi))
    r['SF_bend'] = min(sf)
    Mm = M.M_bend(an.MASSES)
    I = np.setdiff1d(np.arange(K.shape[0]), D)
    lam = eigsh(K[I][:, I], k=3, M=Mm[I][:, I], sigma=0, which='LM', return_eigenvectors=False)
    r['f1'] = np.sqrt(np.sort(lam)[0]) / 2 / np.pi
    Ki = M.K_in()
    Di = M.clamp_dofs_inplane()
    c = np.sqrt(0.5)
    FD, _ = M.load_edge(lambda x, y: (x > dz.XE - 0.05) & (np.abs(y) < 15), (-1.0, 0))
    FE, _ = M.load_edge(lambda x, y: (x > dz.XE - 6) & (y > dz.YE - 6), (-c, -c))
    FF, _ = M.load_edge(lambda x, y: (y > dz.YB - 0.05) & (np.abs(x) > dz.SLOT_L / 2) & (np.abs(x) < dz.XB), (0, -1.0))
    us, _ = fem.solve_multi(Ki, [FD, FE, FF], Di)
    for name, u in zip(('D', 'E', 'F'), us):
        sx, sy, sxy = M.inplane_stress_qp(u)
        r[f'break_{name}'] = 1 / np.sqrt(fem.tsai_hill(sx, sy, sxy, M.ef(M.ispc).astype(bool)).max())
        r[f'buckle_{name}'] = fem.buckling(K, M.K_geo(sx, sy, sxy), D)
    return r


CASES = [('今 t24v9(1.0mm + 塩ビ 0.2mm)', 1.0, False),
         ('1.0mm で埋める', 1.0, True),
         ('0.8mm で埋める', 0.8, True),
         ('0.8mm + 塩ビ(参考)', 0.8, False)]
rows = {}
for name, t_mm, solid in CASES:
    r = run(t_mm, solid)
    rows[name] = r
    print(f"{name}: カーボン {r['m_carbon']:.2f}g + 塩ビ {r['m_pc']:.2f}g = {r['m_carbon'] + r['m_pc']:.2f}g、"
          f"吸引600g スカート前 {r['skirt_front']:.3f} 横 {r['skirt_side']:.3f} 面の中 {r['suction_max']:.3f}mm、"
          f"前の滑り板 {r['dA']:.2f}mm 角 {r['dB']:.2f}mm、{r['f1']:.0f}Hz、"
          f"座屈 正面 {r['buckle_D']:.0f} 角 {r['buckle_E']:.0f} 横 {r['buckle_F']:.0f}N、"
          f"割れる 正面 {r['break_D']:.0f} 角 {r['break_E']:.0f} 横 {r['break_F']:.0f}N、曲げの安全率 {r['SF_bend']:.1f}", flush=True)
json.dump(rows, open('results/t24_solid.json', 'w'), indent=1, ensure_ascii=False, default=float)

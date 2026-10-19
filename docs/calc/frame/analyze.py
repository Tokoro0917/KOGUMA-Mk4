"""1つの形について、荷重のケースをすべて計算する"""
import time, numpy as np
from shapely.geometry import box, Point
from scipy.sparse.linalg import eigsh
import fem, design as dz
CF_X = min(fem.CF['Xt'], fem.CF['Xc'])

LOADS = dict(
    A_front=3.0,      # 前の滑り板に下向き 3N(急な減速での前のめり、落とした時)
    A_rear=3.0,       # 後ろの滑り板に下向き 3N
    B_corner=1.5,     # 前の角に下向き 1.5N(角を柱や床に引っ掛けた時)
    C_suction=5.9,    # 吸引 600g(設計値)。吸引する面に均一の圧力
    D_front=50.0,     # 正面から壁に衝突 50N(前の辺の真ん中30mmで受ける)
    E_corner=30.0,    # 前の角が柱に斜め45°で衝突 30N
    F_side=30.0,      # 横から壁に衝突 30N(タイヤの外の張り出し)
)
MASSES = [(49.2, 8, 1.0, 0.4), (49.2, -8, 1.0, 0.4), (49.2, 17, 1.0, 0.35), (49.2, -17, 1.0, 0.35),
          (45, 0, 1.0, 0.3), (-45, 0, 1.0, 0.3)]     # 壁センサ 1.5g、前後の滑り板 0.3g ずつ

def run(params, max_area=0.15, h=0.45, do_buckling=True, hook=None):
    """hook(M, g): Model を作った直後に呼ぶ(要素ごとの厚さを変えるときなど)。dict を返すと結果に足す"""
    params = dict(params); params.pop('base', None)
    t0 = time.time()
    g = dz.build(**params)
    mc, mp, iz = dz.mass_iz(g)
    mesh = fem.make_mesh(g['domain'], g['pc'], h, max_area)
    M = fem.Model(mesh, g['pc'], g['clamps'], ribs=g['vribs'])
    res = dict(m_carbon=mc, m_pc=mp, iz=iz, nel=mesh.t.shape[1])
    if hook is not None:
        res.update(hook(M, g) or {})
    # ---- 面外(曲げ) ----
    K = M.K_bend(); D = M.clamp_dofs_bend()
    FA = M.load_patch(45, 0, 1.0, LOADS['A_front'])
    FR = M.load_patch(-45, 0, 1.0, LOADS['A_rear'])
    FB = M.load_patch(49.2, 22.0, 1.0, LOADS['B_corner'])
    FC, area = M.load_pressure(g['suction'], 1.0)
    p = LOADS['C_suction'] / area
    ws, _ = fem.solve_multi(K, [FA, FR, FB, FC * p], D)
    vx, vy = mesh.p
    wv = [w[M.bb.nodal_dofs[0]] for w in ws]
    near = lambda x0, y0, r: (vx - x0)**2 + (vy - y0)**2 <= r**2
    res['dA'] = np.abs(wv[0][near(45, 0, 1.0)]).max()
    res['dA_rear'] = np.abs(wv[1][near(-45, 0, 1.0)]).max()
    res['dB'] = np.abs(wv[2][near(49.2, 22, 1.0)]).max()
    land = (np.abs(vx) <= dz.SX) & (np.abs(vy) <= dz.SY) & ((np.abs(vx) >= dz.SX - 3.0) | (np.abs(vy) >= dz.SY - 3.0))
    res['dC_skirt'] = np.abs(wv[3][land]).max()
    pcv = np.zeros(mesh.p.shape[1], bool); pcv[np.unique(mesh.t[:, M.ispc])] = True
    res['dC_pc'] = np.abs(wv[3][pcv]).max() if pcv.any() else 0
    for name, w in zip(('A', 'A_rear', 'B', 'C'), ws):
        sx, sy, sxy = M.bend_stress(w)
        fi = max(fem.tsai_hill(sx, sy, sxy, M.ispc).max(), fem.tsai_hill(-sx, -sy, -sxy, M.ispc).max())
        res[f'SF_{name}'] = 1 / np.sqrt(fi)
        if M.rib_info:
            res[f'SF_rib_{name}'] = CF_X / max(M.rib_stress(w), 1e-9)
    # ---- 振動 ----
    Mm = M.M_bend(MASSES)
    I = np.setdiff1d(np.arange(K.shape[0]), D)
    lam = eigsh(K[I][:, I], k=3, M=Mm[I][:, I], sigma=0, which='LM', return_eigenvectors=False)
    res['f1'] = np.sqrt(np.sort(lam)[0]) / 2 / np.pi
    # ---- 面内(衝突) ----
    Ki = M.K_in(); Di = M.clamp_dofs_inplane()
    FD, _ = M.load_edge(lambda x, y: (x > dz.XE - 0.05) & (np.abs(y) < 15), (-LOADS['D_front'], 0))
    c = np.sqrt(0.5)
    FE, _ = M.load_edge(lambda x, y: (x > dz.XE - 6) & (y > dz.YE - 6), (-LOADS['E_corner'] * c, -LOADS['E_corner'] * c))
    FF, _ = M.load_edge(lambda x, y: (y > dz.YB - 0.05) & (np.abs(x) < 8), (0, -LOADS['F_side']))
    us, _ = fem.solve_multi(Ki, [FD, FE, FF], Di)
    for name, u in zip(('D', 'E', 'F'), us):
        sx, sy, sxy = M.inplane_stress_qp(u)
        fi = fem.tsai_hill(sx, sy, sxy, M.ef(M.ispc).astype(bool)).max()
        res[f'SF_{name}'] = 1 / np.sqrt(fi)
        ux, uy = u[M.bi.nodal_dofs[0]], u[M.bi.nodal_dofs[1]]
        res[f'd{name}'] = np.sqrt(ux**2 + uy**2).max()
        if do_buckling:
            KG = M.K_geo(sx, sy, sxy)
            res[f'BK_{name}'] = fem.buckling(K, KG, D)
    res['time'] = time.time() - t0
    return res

if __name__ == '__main__':
    import json, sys
    r = run({}, max_area=float(sys.argv[1]) if len(sys.argv) > 1 else 0.15)
    print(json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}, indent=1))

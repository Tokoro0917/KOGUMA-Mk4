"""タイヤ24mm 用のフレーム(t24、2026-11-21、ブランチ claude/trusting-dirac-1tdt54)。
frame v6.9 のパラメータ(results/v6_9_params.json)のまま、design.py の定数だけをタイヤ24mm の並びに変えて作り、FEM で計算する。
  - タイヤ・71T の所は外へ開いた切り欠き(|y| > 22.3、前後 SLOT_L)。フレームの外側の帯はなくす(spec「車輪の並びとフレームの幅」)
  - モーターマウント t24v2 のねじ (8, ±19.5)・(-21, ±19.5)、ファンの台の継ぎ目 (14, ±20.3)
  - 横からの衝突(F)は、切り欠きの前後のフレームの横の辺(|y| = 35、9 < |x| < 16.7)で受ける(v6.9 はタイヤの外の帯 |x| < 8)
使い方(このディレクトリで): python3 t24.py [max_area(既定 0.15)] [案の名前 ...]
  → results/t24_<案>_result.json、params.json。案は下の VARIANTS"""
import json, os, sys, time
import numpy as np
from scipy.sparse.linalg import eigsh
import design as dz

# ---- タイヤ24mm の並び(右側の値を正の y で) ----
dz.SLOT_L, dz.SLOT_Y0, dz.SLOT_Y1 = 18.0, 22.3, 40.0   # 切り欠き: 前後18mm(z 3.0 でタイヤの前後 ±7.94、すき間約1mm)、71T の内の面 22.8 から 0.5mm
dz.MOUNT_SCREWS = [(-21.0, 19.5), (8.0, 19.5)]
dz.FAN_JOINTS = [(14.0, 20.3), (14.0, -20.3)]
dz.G_REAR = (-25.5, 19.0)                               # 骨G の始まり(後ろの耳のすぐ後ろ)
dz.MOUNT_PAD = (-25.0, 12.5, dz.SY, dz.SLOT_Y0 + 0.5)    # マウントが載る所(窓を開けない)
dz.ENC_BOARD = (-3.0, 3.0, 16.9, 17.5)                  # エンコーダ基板はフレームまで来ないが、窓の計算の都合で残す所

MOUTH_R = 1.5                                           # 切り欠きの口の角(フレームの外側の角)を丸める半径
_build = dz.build
def build_t24(**kw):
    """design.build の形から、切り欠きの口の角 (±SLOT_L/2, ±YB) を半径 MOUTH_R で丸める(壁に引っかからないように)"""
    from shapely.geometry import box, Point
    from shapely.ops import unary_union
    g = _build(**kw)
    x0, y0, r = dz.SLOT_L / 2, dz.YB, MOUTH_R
    cuts = []
    for sx in (1, -1):
        for sy in (1, -1):
            sq = box(min(sx * x0, sx * (x0 + r)), min(sy * y0, sy * (y0 - r)), max(sx * x0, sx * (x0 + r)), max(sy * y0, sy * (y0 - r)))
            cuts.append(sq.difference(Point(sx * (x0 + r), sy * (y0 - r)).buffer(r, 64)))
    c = unary_union(cuts)
    g['domain'], g['carbon'] = g['domain'].difference(c), g['carbon'].difference(c)
    return g
dz.build = build_t24

import fem, analyze as an

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = json.load(open(os.path.join(HERE, 'results/v6_9_params.json')))
VARIANTS = {
    'a': dict(BASE),                                             # v6.9 そのまま(マウントの下・切り欠きの前後の横の帯に窓)
    'b': dict(BASE, mount_windows=['pad2']),                     # 切り欠きの前後の横の帯には窓を開けない
    'c': dict(BASE, mount_windows=[]),                           # マウントの下にも窓を開けない
}

def run(params, max_area=0.15, h=0.45):
    """analyze.run と同じ。ただし横からの衝突 F は切り欠きの前後の横の辺で受ける"""
    params = dict(params); params.pop('base', None)
    t0 = time.time()
    g = dz.build(**params)
    mc, mp, iz = dz.mass_iz(g)
    mesh = fem.make_mesh(g['domain'], g['pc'], h, max_area)
    M = fem.Model(mesh, g['pc'], g['clamps'], ribs=g['vribs'])
    res = dict(m_carbon=mc, m_pc=mp, iz=iz, nel=mesh.t.shape[1])
    L = an.LOADS
    K = M.K_bend(); D = M.clamp_dofs_bend()
    FA = M.load_patch(45, 0, 1.0, L['A_front']); FR = M.load_patch(-45, 0, 1.0, L['A_rear'])
    FB = M.load_patch(49.2, 22.0, 1.0, L['B_corner'])
    FC, area = M.load_pressure(g['suction'], 1.0)
    ws, _ = fem.solve_multi(K, [FA, FR, FB, FC * (L['C_suction'] / area)], D)
    vx, vy = mesh.p
    wv = [w[M.bb.nodal_dofs[0]] for w in ws]
    near = lambda x0, y0, r: (vx - x0)**2 + (vy - y0)**2 <= r**2
    res['dA'] = np.abs(wv[0][near(45, 0, 1.0)]).max()
    res['dA_rear'] = np.abs(wv[1][near(-45, 0, 1.0)]).max()
    res['dB'] = np.abs(wv[2][near(49.2, 22, 1.0)]).max()
    for name, w in zip(('A', 'A_rear', 'B', 'C'), ws):
        sx, sy, sxy = M.bend_stress(w)
        fi = max(fem.tsai_hill(sx, sy, sxy, M.ispc).max(), fem.tsai_hill(-sx, -sy, -sxy, M.ispc).max())
        res[f'SF_{name}'] = 1 / np.sqrt(fi)
    Mm = M.M_bend(an.MASSES)
    I = np.setdiff1d(np.arange(K.shape[0]), D)
    lam = eigsh(K[I][:, I], k=3, M=Mm[I][:, I], sigma=0, which='LM', return_eigenvectors=False)
    res['f1'] = np.sqrt(np.sort(lam)[0]) / 2 / np.pi
    Ki = M.K_in(); Di = M.clamp_dofs_inplane()
    FD, _ = M.load_edge(lambda x, y: (x > dz.XE - 0.05) & (np.abs(y) < 15), (-L['D_front'], 0))
    c = np.sqrt(0.5)
    FE, _ = M.load_edge(lambda x, y: (x > dz.XE - 6) & (y > dz.YE - 6), (-L['E_corner'] * c, -L['E_corner'] * c))
    FF, nF = M.load_edge(lambda x, y: (y > dz.YB - 0.05) & (np.abs(x) > dz.SLOT_L / 2) & (np.abs(x) < dz.XB), (0, -L['F_side']))
    us, _ = fem.solve_multi(Ki, [FD, FE, FF], Di)
    for name, u in zip(('D', 'E', 'F'), us):
        sx, sy, sxy = M.inplane_stress_qp(u)
        res[f'SF_{name}'] = 1 / np.sqrt(fem.tsai_hill(sx, sy, sxy, M.ef(M.ispc).astype(bool)).max())
        ux, uy = u[M.bi.nodal_dofs[0]], u[M.bi.nodal_dofs[1]]
        res[f'd{name}'] = np.sqrt(ux**2 + uy**2).max()
        res[f'BK_{name}'] = fem.buckling(K, M.K_geo(sx, sy, sxy), D)
    res['time'] = time.time() - t0
    return res, g

if __name__ == '__main__':
    ma = float(sys.argv[1]) if len(sys.argv) > 1 else 0.15
    names = sys.argv[2:] or list(VARIANTS)
    for nm in names:
        r, g = run(VARIANTS[nm], max_area=ma)
        r = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}
        json.dump(r, open(f'results/t24_{nm}_result.json', 'w'), indent=1)
        json.dump(VARIANTS[nm], open(f'results/t24_{nm}_params.json', 'w'), ensure_ascii=False)
        print(nm, f"カーボン {r['m_carbon']:.2f}g、前 {r['dA']:.2f}mm、後ろ {r['dA_rear']:.2f}mm、角 {r['dB']:.2f}mm、{r['f1']:.0f}Hz、"
              f"座屈 正面 {r['BK_D'] * an.LOADS['D_front']:.0f} / 角 {r['BK_E'] * an.LOADS['E_corner']:.0f} / 横 {r['BK_F'] * an.LOADS['F_side']:.0f}N、安全率 "
              + ' '.join(f"{k[3:]}{r[k]:.1f}" for k in r if k.startswith('SF_')) + f"、{r['time']:.0f}s", flush=True)

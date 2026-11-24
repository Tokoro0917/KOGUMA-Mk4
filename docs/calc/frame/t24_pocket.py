"""1mm の板で、吸引する面の窓(t24v9 で塩ビを貼っていた所)を上から掘ってカーボンの底を残す案(ポケット加工、2026-11-24、ユーザー「それか 1mm でポケット加工」)。
使い方(このディレクトリで): python3 t24_pocket.py → 数字と results/t24_pocket.json
形は frame t24v9(案 w2lXf15se、1mm)。窓の所を底の厚さ tf のカーボンにする(塩ビなし)。
片面から掘ると底は板の真ん中からずれるので、底の曲げ剛性は次の2つの間になる(pocket.py と同じ考え方):
  下限: 底だけの板(tf³/12)。ポケットが広いと、真ん中のあたりはこれに近い
  上限: 底が板の真ん中の面のまわりで曲がる(tf³/12 + tf·e²、e = (1 − tf)/2)。ポケットの縁の近くはこれに近い
比べるもの: t24v9(1mm + 塩ビ)、t24v10(0.8mm で埋める)"""
import json, sys, numpy as np
sys.path.insert(0, '.')
import t24, design as dz, fem, analyze as an
from scipy.sparse.linalg import eigsh

t24.set_suction('w2')
P9 = dict(json.load(open('results/t24v9_params.json')))
P9.pop('base', None)
L = an.LOADS
SKIRT_X, SKIRT_Y = 40.0, 21.3


def make_model(tf, bound):
    """ポケットの底の厚さ tf、bound は 'low'(下限)か 'high'(上限)。(g, mesh, M, 底の要素, 表面までの距離) を返す"""
    g = dz.build(**P9)
    mesh = fem.make_mesh(g['domain'], g['pc'], 0.45, 0.15)
    M = fem.Model(mesh, g['pc'], g['clamps'], ribs=g['vribs'])
    pocket = M.ispc.copy()                       # 窓の所の要素 = ポケット
    full = fem.CF['t']
    e = (full - tf) / 2
    if bound == 'low':
        d_eff = tf**3 / 12
        z_far = tf / 2                           # 曲げの応力を見る、中立の面から表面までの距離
    else:
        d_eff = tf**3 / 12 + tf * e**2
        z_far = e + tf / 2
    t = np.where(pocket, tf, full)
    M.t = t
    M.Q = [np.full(mesh.t.shape[1], q) for q in fem.Q_CF]
    M.D = [q * np.where(pocket, d_eff, full**3 / 12) for q in M.Q]
    M.rhot = fem.CF['rho'] * t
    M.ispc = np.zeros(mesh.t.shape[1], bool)     # 底もカーボンなので、壊れるかどうかを調べる
    zf = np.where(pocket, z_far, full / 2)
    return g, mesh, M, pocket, zf


def bend_fi(M, w, zf):
    """曲げの表面の Tsai-Hill の指数(要素ごと)"""
    H = M.bb.interpolate(w).hess.mean(axis=-1)
    kx, ky, kxy = H[0, 0], H[1, 1], H[0, 1]
    q11, q12, q22, q66 = M.Q
    sx = -(q11 * kx + q12 * ky) * zf
    sy = -(q12 * kx + q22 * ky) * zf
    sxy = -2 * q66 * kxy * zf
    return max(fem.tsai_hill(sx, sy, sxy).max(), fem.tsai_hill(-sx, -sy, -sxy).max())


def run(tf, bound):
    g, mesh, M, pocket, zf = make_model(tf, bound)
    mc, mp, iz = dz.mass_iz(g)                   # mc: 窓を抜いた 1mm のカーボン
    pocket_area = sum(p.area for p in g['pc'])
    r = dict(tf=tf, bound=bound, m=mc + pocket_area * tf * 1.55e-3, pocket_area=pocket_area)
    K = M.K_bend()
    D = M.clamp_dofs_bend()
    FA = M.load_patch(45, 0, 1.0, L['A_front'])
    FB = M.load_patch(49.2, 22.0, 1.0, L['B_corner'])
    FC, area = M.load_pressure(g['suction'], 1.0)
    ws, _ = fem.solve_multi(K, [FA, FB, FC * (5.9 / area)], D)
    vx, vy = mesh.p
    wv = [w[M.bb.nodal_dofs[0]] for w in ws]
    near = lambda x0, y0, rr: (vx - x0)**2 + (vy - y0)**2 <= rr**2
    front = (np.abs(vx - SKIRT_X) < 0.6) & (np.abs(vy) <= SKIRT_Y)
    side = (np.abs(np.abs(vy) - SKIRT_Y) < 0.6) & (np.abs(vx) <= SKIRT_X)
    inside = (np.abs(vx) <= SKIRT_X) & (np.abs(vy) <= SKIRT_Y)
    r['dA'] = np.abs(wv[0][near(45, 0, 1.0)]).max()
    r['dB'] = np.abs(wv[1][near(49.2, 22, 1.0)]).max()
    r['skirt_front'] = np.abs(wv[2][front]).max()
    r['skirt_side'] = np.abs(wv[2][side]).max()
    r['suction_max'] = np.abs(wv[2][inside]).max()
    r['SF_bend'] = 1 / np.sqrt(max(bend_fi(M, w, zf) for w in ws))
    r['SF_suction'] = 1 / np.sqrt(bend_fi(M, ws[2], zf))
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
        r[f'break_{name}'] = 1 / np.sqrt(fem.tsai_hill(sx, sy, sxy).max())
        r[f'buckle_{name}'] = fem.buckling(K, M.K_geo(sx, sy, sxy), D)
    return r


rows = []
for tf in (0.3, 0.4, 0.5):
    for bound in ('low', 'high'):
        r = run(tf, bound)
        rows.append(r)
        nm = {'low': '下限', 'high': '上限'}[bound]
        print(f"底 {tf}mm({nm}): カーボン {r['m']:.2f}g、吸引600g スカート前 {r['skirt_front']:.3f} 横 {r['skirt_side']:.3f} 面の中 {r['suction_max']:.3f}mm(安全率 {r['SF_suction']:.1f})、"
              f"前の滑り板 {r['dA']:.2f}mm 角 {r['dB']:.2f}mm、{r['f1']:.0f}Hz、"
              f"座屈 正面 {r['buckle_D']:.0f} 角 {r['buckle_E']:.0f} 横 {r['buckle_F']:.0f}N、"
              f"割れる 正面 {r['break_D']:.0f} 角 {r['break_E']:.0f} 横 {r['break_F']:.0f}N、曲げの安全率 {r['SF_bend']:.1f}", flush=True)
print('ポケットの面積', round(rows[0]['pocket_area']), 'mm²')
json.dump(rows, open('results/t24_pocket.json', 'w'), indent=1, ensure_ascii=False, default=float)

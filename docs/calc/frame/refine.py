"""フレームの見直し(2026-10-19): どこを細くでき、どこを強くすべきか
  map : 今の形(final_params.json)の要素ごとの働きの図
        左: 硬さへの効き(曲げのひずみエネルギーの密度。前・後ろの滑り板、前の角、1次の振動、正面・角の座屈の形の最大。平均 = 1)
        右: 材料の使い方(破壊の指数 sqrt(Tsai-Hill)。曲げ A/A後ろ/B/C と面内 D/E/F の最大。1 で壊れる)
  sens: 部材の幅を1つずつ変えたときの重さと性能の変化(粗いメッシュ、results/refine_sens.json)
  try : 見直した案をいくつか計算する(粗いメッシュ、results/refine_try.json)
使い方: python3 refine.py map 図.png | sens | try
"""
import sys, json
import numpy as np
from multiprocessing import Pool
from scipy.sparse.linalg import eigsh
import fem, design as dz, analyze as an

P0 = json.load(open('results/final_params.json'))

def element_maps(P, max_area=0.15, h=0.45):
    g = dz.build(**P)
    mesh = fem.make_mesh(g['domain'], g['pc'], h, max_area)
    M = fem.Model(mesh, g['pc'], g['clamps'], ribs=g['vribs'])
    K = M.K_bend(); D = M.clamp_dofs_bend()
    F = [M.load_patch(45, 0, 1.0, an.LOADS['A_front']), M.load_patch(-45, 0, 1.0, an.LOADS['A_rear']),
         M.load_patch(49.2, 22.0, 1.0, an.LOADS['B_corner'])]
    FC, area = M.load_pressure(g['suction'], 1.0)
    ws, _ = fem.solve_multi(K, F + [FC * an.LOADS['C_suction'] / area], D)
    I = np.setdiff1d(np.arange(K.shape[0]), D)
    Mm = M.M_bend(an.MASSES)
    lam, vec = eigsh(K[I][:, I], k=1, M=Mm[I][:, I], sigma=0, which='LM')
    mode = np.zeros(K.shape[0]); mode[I] = vec[:, 0]
    # 面内(衝突)と座屈の形
    Ki = M.K_in(); Di = M.clamp_dofs_inplane()
    FD, _ = M.load_edge(lambda x, y: (x > dz.XE - 0.05) & (np.abs(y) < 15), (-an.LOADS['D_front'], 0))
    c = np.sqrt(0.5)
    FE, _ = M.load_edge(lambda x, y: (x > dz.XE - 6) & (y > dz.YE - 6), (-an.LOADS['E_corner'] * c, -an.LOADS['E_corner'] * c))
    FF, _ = M.load_edge(lambda x, y: (y > dz.YB - 0.05) & (np.abs(x) < 8), (0, -an.LOADS['F_side']))
    us, _ = fem.solve_multi(Ki, [FD, FE, FF], Di)
    bk = []
    for u in us[:2]:
        sx, sy, sxy = M.inplane_stress_qp(u)
        KG = M.K_geo(sx, sy, sxy)
        vals, vecs = eigsh(K[I][:, I].tocsc(), k=1, M=(-KG[I][:, I]).tocsc(), sigma=1e-2, which='LM', mode='buckling')
        phi = np.zeros(K.shape[0]); phi[I] = vecs[:, 0]
        bk.append(phi)
    area_e = M.elem_area(); d11, d12, d22, d66 = M.D
    cf = ~M.ispc
    sed = []
    for w in ws[:3] + [mode] + bk:
        H = M.bb.interpolate(w).hess.mean(axis=-1)
        kx, ky, kxy = H[0, 0], H[1, 1], H[0, 1]
        e = 0.5 * (d11 * kx**2 + 2 * d12 * kx * ky + d22 * ky**2 + 4 * d66 * kxy**2)
        e = np.where(cf, e, 0)
        sed.append(e * area_e[cf].sum() / (e * area_e).sum())
    fi = np.zeros(mesh.t.shape[1])
    for w, load in zip(ws, (1, 1, 1, 1)):
        sx, sy, sxy = M.bend_stress(w)
        fi = np.maximum(fi, np.maximum(fem.tsai_hill(sx, sy, sxy, M.ispc), fem.tsai_hill(-sx, -sy, -sxy, M.ispc)))
    for u in us:
        sx, sy, sxy = M.inplane_stress_qp(u)
        fi = np.maximum(fi, fem.tsai_hill(sx, sy, sxy, M.ef(M.ispc).astype(bool)).max(axis=1))
    return g, mesh, M, np.max(sed, axis=0), np.sqrt(fi)

def draw_map(fn):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm
    g, mesh, M, sed, fi = element_maps(P0)
    vx, vy = mesh.p
    fig, axs = plt.subplots(1, 2, figsize=(18, 6.6))
    for ax, val, title, kw in ((axs[0], np.clip(sed, 0.02, 50), 'stiffness use: strain energy density (mean = 1), log', dict(norm=LogNorm(0.05, 20), cmap='viridis')),
                               (axs[1], fi, 'strength use: sqrt(Tsai-Hill), worst of A/Ar/B/C/D/E/F (1 = break)', dict(cmap='inferno', vmin=0, vmax=0.12))):
        v = np.where(M.ispc, np.nan, val)
        tp = ax.tripcolor(vx, vy, mesh.t.T, facecolors=v, **kw)
        plt.colorbar(tp, ax=ax, fraction=0.03)
        for p in g['pc']:
            ax.fill(*p.exterior.xy, color='#cfe3f0')
        for c in g['clamps']:
            ax.plot(*c.exterior.xy, color='r', lw=0.8)
        ax.set_aspect('equal'); ax.set_xlim(-53, 53); ax.set_ylim(-38, 38); ax.set_title(title, fontsize=10)
    fig.tight_layout(); fig.savefig(fn, dpi=100)
    # 部分ごとの平均(重さあたりの働き)
    cx, cy = M.cent
    a = M.elem_area(); cf = ~M.ispc
    regions = {
        '前の辺(x > 47)': (cx > dz.XE - 3.5),
        '後ろの辺(x < -47)': (cx < -dz.XE + 3.5),
        '外周の枠(前の斜め)': (cx > dz.XB) & (np.abs(cy) > dz.YE + 0.5) & (cx < dz.XE - 3.5),
        '外周の枠(後ろの斜め)': (cx < -dz.XB) & (np.abs(cy) > dz.YE + 0.5) & (cx > -dz.XE + 3.5),
        '横の帯(|x| < 16.7、|y| > 26)': (np.abs(cx) < dz.XB) & (np.abs(cy) > 26.3),
        'マウントの下(|y| 15.25〜26.3)': (cx > -22) & (cx < 12.5) & (np.abs(cy) > dz.SY) & (np.abs(cy) < 26.3),
        '吸引する面の中(カーボン)': (np.abs(cx) < dz.SX) & (np.abs(cy) < dz.SY),
        '前の背骨(x 30〜47)': (cx > dz.SX) & (cx < dz.XE - 3.5) & (np.abs(cy) < 2.5),
        '後ろの背骨': (cx < -dz.SX) & (cx > -dz.XE + 3.5) & (np.abs(cy) < 2.5),
    }
    out = {}
    for k, sel in regions.items():
        sel = sel & cf
        if sel.sum() == 0:
            continue
        out[k] = dict(mass=round(float(a[sel].sum() * 1.55e-3), 3), sed=round(float((sed[sel] * a[sel]).sum() / a[sel].sum()), 2),
                      fi_max=round(float(fi[sel].max()), 3))
    json.dump(out, open('results/refine_map.json', 'w'), ensure_ascii=False, indent=1)
    for k, v in out.items():
        print(f"{k:28s} {v['mass']:.2f}g  働き(平均1) {v['sed']:6.2f}  破壊の指数(最大) {v['fi_max']:.3f}")

SENS = {
    'base': {},
    '外周の枠 2.0': dict(rim=2.0), '外周の枠 3.0': dict(rim=3.0),
    '前後の辺 2.5': dict(end_edge=2.5), '前後の辺 4.0': dict(end_edge=4.0),
    '背骨 3': dict(spine_root=3, spine_tip=3), '背骨 5': dict(spine_root=5, spine_tip=5),
    '骨G 2.5': dict(brace_w=2.5), '骨G 4.5': dict(brace_w=4.5),
    '筋交いA 1.5': dict(brace_w_each={'A': 1.5}), '筋交いA 3.0': dict(brace_w_each={'A': 3.0}),
    '吸引の縁 2.5': dict(land=2.5), '吸引の縁 4.0': dict(land=4.0),
    '吸引の中の背骨 3': dict(inner_spine=3.0), '吸引の中の背骨 5': dict(inner_spine=5.0),
    'ファンのまわり 2.5': dict(fan_ring=2.5), 'ファンのまわり 4.5': dict(fan_ring=4.5),
    'マウントの下の窓なし': dict(mount_windows=[]),
    '窓の角 R3': dict(fillet=3.0),
}

def job(item):
    name, over = item
    p = dict(P0, **over)
    try:
        r = an.run(p, max_area=0.3, h=0.6)
    except Exception as e:
        r = dict(error=str(e))
    r['name'] = name; r['over'] = over
    return r

def table(rows, base):
    keys = (('dA', -1), ('dA_rear', -1), ('dB', -1), ('f1', 1), ('BK_D', 1), ('BK_E', 1), ('BK_F', 1))
    print(f"{'案':22s} {'重さ':>7s} {'前滑り':>7s} {'後滑り':>7s} {'前の角':>7s} {'振動':>6s} {'正面座屈':>7s} {'角座屈':>7s} {'横座屈':>7s} {'安全率':>6s} {'総合/g':>7s}")
    for r in rows:
        if 'error' in r:
            print(r['name'], r['error']); continue
        dm = r['m_carbon'] - base['m_carbon']
        rel = [s * (r[k] / base[k] - 1) for k, s in keys]
        score = 100 * np.mean(rel)
        sf = min(v for k, v in r.items() if k.startswith('SF_'))
        eff = score / dm if abs(dm) > 0.005 else float('nan')
        r['score'] = score; r['dm'] = dm; r['eff'] = eff
        print(f"{r['name']:22s} {dm:+7.3f} " + ' '.join(f"{100 * s * (r[k] / base[k] - 1):+7.1f}" for k, s in keys)
              + f" {sf:6.1f} {eff:+7.1f}")

if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'map':
        draw_map(sys.argv[2])
    elif mode == 'sens':
        with Pool(4) as pool:
            rows = pool.map(job, list(SENS.items()), chunksize=1)
        json.dump(rows, open('results/refine_sens.json', 'w'), ensure_ascii=False, indent=1, default=float)
        table(rows, rows[0])
    elif mode == 'try':
        cands = json.loads(open(sys.argv[2]).read())
        with Pool(4) as pool:
            rows = pool.map(job, [('base', {})] + list(cands.items()), chunksize=1)
        json.dump(rows, open('results/refine_try.json', 'w'), ensure_ascii=False, indent=1, default=float)
        table(rows, rows[0])

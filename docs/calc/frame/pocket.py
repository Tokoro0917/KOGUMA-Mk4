"""ポケット加工(片面から掘って薄くする)で軽くできるかを調べる(2026-10-18)
  1. frame_v4.2 の曲げのひずみエネルギーの密度(前・後ろの滑り板、前の角、1次の振動)から、働いていない所を探す
  2. 縁・穴・ねじ・滑り板・吸引する面の縁から離れた所だけを、加工できる形(半径1mmの刃物が通る)にしてポケットにする
  3. ポケットの底の厚さ tf で計算し直す。片面から掘ると底は板の真ん中からずれるので、曲げ剛性は
       下限: 底の厚さだけの板(tf³/12)
       上限: 底が板の真ん中の面のまわりで曲がる(tf³/12 + tf·e²、e = (t − tf)/2)
     の間になる。両方を計算する
  4. 比べるもの: 板の厚さ0.8mm(全体を薄くする)
使い方: python3 pocket.py [tf=0.5]      ポケット
        python3 pocket.py 0.5 win        同じ所を貫通の窓にしたとき(先に上を実行)
        python3 pocket.py 0.5 plot 図.png  ポケットの場所の図
"""
import sys, json
import numpy as np
from multiprocessing import Pool
from scipy import ndimage
from scipy.sparse.linalg import eigsh
import shapely
from shapely.geometry import Point
import fem, design as dz, analyze as an

P = json.load(open('results/final_params.json'))
TF = float(sys.argv[1]) if len(sys.argv) > 1 else 0.5
MA, H = 0.3, 0.6              # 比べるだけなので、粗いメッシュ(sweep と同じ)
MARGIN = 1.5                  # 縁・窓・穴から残す肉(全厚)
TOOL_R = 1.0                  # ポケットの角の丸み(刃物の半径)
GRID = 0.2

def utilization(M, g):
    """要素ごとの曲げのひずみエネルギーの密度(荷重ごとに平均 = 1 にして、最大をとる)"""
    K = M.K_bend(); D = M.clamp_dofs_bend()
    FA = M.load_patch(45, 0, 1.0, an.LOADS['A_front'])
    FR = M.load_patch(-45, 0, 1.0, an.LOADS['A_rear'])
    FB = M.load_patch(49.2, 22.0, 1.0, an.LOADS['B_corner'])
    ws, _ = fem.solve_multi(K, [FA, FR, FB], D)
    Mm = M.M_bend(an.MASSES)
    I = np.setdiff1d(np.arange(K.shape[0]), D)
    lam, vec = eigsh(K[I][:, I], k=1, M=Mm[I][:, I], sigma=0, which='LM')
    phi = np.zeros(K.shape[0]); phi[I] = vec[:, 0]
    area = M.elem_area(); d11, d12, d22, d66 = M.D
    out = []
    for w in ws + [phi]:
        Hs = M.bb.interpolate(w).hess.mean(axis=-1)
        kx, ky, kxy = Hs[0, 0], Hs[1, 1], Hs[0, 1]
        e = 0.5 * (d11 * kx**2 + 2 * d12 * kx * ky + d22 * ky**2 + 4 * d66 * kxy**2)
        e = np.where(M.ispc, 0, e)
        out.append(e * area[~M.ispc].sum() / (e * area).sum())
    return np.max(out, axis=0)

def candidates(g):
    """ポケットにしてよい所(ラスター、GRID mm)"""
    xs = np.arange(-dz.XE, dz.XE + GRID, GRID); ys = np.arange(-dz.YB, dz.YB + GRID, GRID)
    X, Y = np.meshgrid(xs, ys)
    keep_full = g['carbon'].boundary.buffer(MARGIN)                       # 縁・窓・穴のまわり
    for (x, y) in dz.MOUNT_SCREWS:
        for sy in (1, -1):
            keep_full = keep_full.union(Point(x, sy * y).buffer(dz.BOSS_R + 0.8))   # ねじの頭・ナット・マウントの耳
    for x in (45, -45):
        keep_full = keep_full.union(Point(x, 0).buffer(3.0))              # 滑り板
    keep_full = keep_full.union(g['suction'].boundary.buffer(3.0))        # 吸引する面の縁(スカート)
    ok = shapely.contains_xy(g['carbon'].difference(keep_full), X, Y)
    return X, Y, ok

def pocket_mask(M, util, X, Y, ok, q):
    """util が下から q の割合の所を、刃物が通る形にして、要素の印にする"""
    # 要素の値をラスターへ(一番近い要素の重心)
    from scipy.spatial import cKDTree
    tree = cKDTree(M.cent.T)
    _, idx = tree.query(np.c_[X.ravel(), Y.ravel()])
    U = util[idx].reshape(X.shape)
    thr = np.quantile(U[ok], q) if q < 1 else np.inf
    B = ok & (U <= thr)
    r = int(round(TOOL_R / GRID))
    disk = (np.add.outer(np.arange(-r, r + 1)**2, np.arange(-r, r + 1)**2) <= r * r)
    B = ndimage.binary_opening(B, structure=disk)                 # 刃物が入れない細い所を消す
    lab, n = ndimage.label(B)
    sizes = ndimage.sum(B, lab, range(1, n + 1)) * GRID**2
    B = np.isin(lab, 1 + np.flatnonzero(sizes >= 6.0))             # 6mm² より小さいポケットは作らない
    # 要素の重心がポケットの中か
    ix = np.clip(np.round((M.cent[0] - X[0, 0]) / GRID).astype(int), 0, X.shape[1] - 1)
    iy = np.clip(np.round((M.cent[1] - Y[0, 0]) / GRID).astype(int), 0, X.shape[0] - 1)
    return B[iy, ix] & ~M.ispc, B

def make_hook(mask_fn, tf, upper):
    def hook(M, g):
        mask = mask_fn(M, g)
        t0 = fem.CF['t']
        e = (t0 - tf) / 2
        fac = (tf**3 / 12 + (tf * e**2 if upper else 0)) / (t0**3 / 12)
        M.D = [np.where(mask, d * fac, d) for d in M.D]
        M.t = np.where(mask, tf, M.t)                          # 面内の剛性・座屈の幾何剛性・応力
        M.rhot = np.where(mask, fem.CF['rho'] * tf, M.rhot)
        a = M.elem_area()[mask]
        cx, cy = M.cent[:, mask]
        dm = fem.CF['rho'] * 1e6 * (t0 - tf) * a                # 減る質量 [g](rho は t/mm³)
        return dict(pocket_area=a.sum(), pocket_dm=dm.sum(), pocket_diz=(dm * (cx**2 + cy**2)).sum() / 100)
    return hook

def job(args):
    name, q, tf, upper, t_plate = args
    import fem as f2
    f2.CF['t'] = t_plate
    g = dz.build(**P)
    def mask_fn(M, g):
        if q is None:
            return np.zeros(M.m.t.shape[1], bool)
        util = utilization(M, g)
        X, Y, ok = candidates(g)
        mask, B = pocket_mask(M, util, X, Y, ok, q)
        np.save(f'results/pocket_{name}.npy', B)
        return mask
    r = an.run(P, max_area=MA, h=H, hook=make_hook(mask_fn, tf, upper))
    r['name'] = name
    return r

def raster_poly(B, X, Y):
    """ラスターの印をポリゴンにする"""
    from shapely.geometry import box
    from shapely.ops import unary_union
    iy, ix = np.nonzero(B)
    h = GRID / 2 + 1e-3                     # 隣のセルと少し重ねて、すき間なくつなぐ
    cells = [box(X[0, i] - h, Y[j, 0] - h, X[0, i] + h, Y[j, 0] + h) for j, i in zip(iy, ix)]
    return unary_union(cells).buffer(-1e-3).simplify(0.12)

def win_job(name):
    """ポケットと同じ所を、貫通の窓にする(比べるため)"""
    B = np.load(f'results/pocket_{name}.npy')
    g0 = dz.build(**P)
    X, Y, ok = candidates(g0)
    W = raster_poly(B, X, Y)
    build0 = dz.build
    def build_w(**kw):
        g = build0(**kw)
        g['domain'] = g['domain'].difference(W)
        g['carbon'] = g['carbon'].difference(W)
        return g
    dz.build = build_w
    r = an.run(P, max_area=MA, h=H)
    dz.build = build0
    r['name'] = 'win_' + name
    return r

def plot(fn):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    g = dz.build(**P)
    X, Y, ok = candidates(g)
    fig, axs = plt.subplots(1, 3, figsize=(18, 5.2))
    for ax, (nm, title) in zip(axs, (('q0.3_lo', 'lowest-use 30% (269 mm2)'), ('q0.6_lo', 'lowest-use 60% (486 mm2)'),
                                     ('q1.0_lo', 'all allowed (760 mm2)'))):
        B = np.load(f'results/pocket_{nm}.npy')
        for p in getattr(g['carbon'], 'geoms', [g['carbon']]):
            ax.fill(*p.exterior.xy, color='#5f5a50')
            for r in p.interiors:
                ax.fill(*r.xy, color='w')
        for p in g['pc']:
            ax.fill(*p.exterior.xy, color='#9ecae1')
        ax.contourf(X, Y, ok.astype(float), levels=[0.5, 1.5], colors=['#fdd0a2'], alpha=0.5)
        ax.contourf(X, Y, B.astype(float), levels=[0.5, 1.5], colors=['#e6550d'])
        ax.set_aspect('equal'); ax.set_xlim(-53, 53); ax.set_ylim(-38, 38); ax.set_title(title)
    fig.suptitle('frame v4.2: pocket (or window) area = orange, allowed area = light orange (1.5 mm from edges, screws, skids, skirt land)')
    fig.tight_layout(); fig.savefig(fn, dpi=90)

if __name__ == '__main__' and len(sys.argv) > 2 and sys.argv[2] == 'plot':
    plot(sys.argv[3])
elif __name__ == '__main__' and len(sys.argv) > 2 and sys.argv[2] == 'win':
    with Pool(3) as pool:
        out = pool.map(win_job, ['q0.3_lo', 'q0.6_lo', 'q1.0_lo'], chunksize=1)
    json.dump(out, open('results/pocket_windows.json', 'w'), ensure_ascii=False, indent=1, default=float)
    for r in out:
        print(r['name'], {k: round(float(v), 4) for k, v in r.items() if k != 'name'})
elif __name__ == '__main__':
    cases = [('base', None, 1.0, False, 1.0), ('plate0.8', None, 0.8, False, 0.8)]
    for q in (0.3, 0.6, 1.0):
        for up in (False, True):
            cases.append((f'q{q}_{"hi" if up else "lo"}', q, TF, up, 1.0))
    with Pool(4) as pool:
        out = pool.map(job, cases, chunksize=1)
    json.dump(out, open(f'results/pocket_tf{TF}.json', 'w'), ensure_ascii=False, indent=1, default=float)
    for r in out:
        print(r['name'], {k: round(float(v), 4) for k, v in r.items() if k != 'name'})

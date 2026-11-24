"""モーターマウント(t24)の肉の厚さを調べる(2026-11-24、ユーザー「すごい薄いところとかあるけど大丈夫?」)。
使い方(このフォルダで): python3 thickness_t24.py → 薄い所の一覧と mount_t24v6_thickness.png
やり方:
  1. マウントの形を細かい三角形にし、0.06mm の立方体(ボクセル)の集まりにする(y 方向に線を通し、面を通った回数で中か外かを決める)
  2. 各ボクセルの「肉の厚さ」= そのボクセルを含む、形の中に入る一番大きな球の直径(局所の厚さ)
  3. 厚さが 0.8mm(JLC Temp Resin のすすめる最小の壁)より薄い所を、つながった塊に分ける。
     角の近くの細い帯(どの角にもできる)は除くため、板や壁のように 2 方向に広がった所だけを残す"""
import numpy as np
from scipy import ndimage
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mount as mm
import mount_t24 as mt

plt.rcParams['font.family'] = 'IPAGothic'
H = 0.06                 # ボクセルの大きさ [mm]
WALL_MIN = 0.8           # JLC Temp Resin のすすめる最小の壁 [mm]
RADII = [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5]   # 調べる球の半径(厚さは 2 倍)


def voxelize(solid):
    """形をボクセルにする。(中かどうかの 3D 配列 [x, y, z], 原点, 大きさ)"""
    verts, tris = solid.tessellate(0.005, 0.1)
    V = np.array([(v.x, v.y, v.z) for v in verts])
    T = np.array(tris)
    bb = solid.BoundingBox()
    x0, y0, z0 = bb.xmin - 2 * H, bb.ymin - 2 * H, bb.zmin - 2 * H
    nx = int((bb.xmax - x0) / H) + 3
    ny = int((bb.ymax - y0) / H) + 3
    nz = int((bb.zmax - z0) / H) + 3
    xs = x0 + (np.arange(nx) + 0.5) * H
    zs = z0 + (np.arange(nz) + 0.5) * H
    hits = [[[] for _ in range(nz)] for _ in range(nx)]
    # 三角形ごとに、xz 面に写した三角形の中にある線 (x, z) を探し、そこで面を通る y を記録する
    for a, b, c in T:
        A, B, C = V[a], V[b], V[c]
        xmin, xmax = min(A[0], B[0], C[0]), max(A[0], B[0], C[0])
        zmin, zmax = min(A[2], B[2], C[2]), max(A[2], B[2], C[2])
        i0 = max(int(np.ceil((xmin - x0) / H - 0.5)), 0)
        i1 = min(int(np.floor((xmax - x0) / H - 0.5)), nx - 1)
        k0 = max(int(np.ceil((zmin - z0) / H - 0.5)), 0)
        k1 = min(int(np.floor((zmax - z0) / H - 0.5)), nz - 1)
        if i1 < i0 or k1 < k0:
            continue
        det = (B[0] - A[0]) * (C[2] - A[2]) - (C[0] - A[0]) * (B[2] - A[2])
        if abs(det) < 1e-12:
            continue
        for i in range(i0, i1 + 1):
            for k in range(k0, k1 + 1):
                px, pz = xs[i], zs[k]
                # 重心座標で、三角形の中か(辺の上は片側だけ数える)
                l1 = ((B[0] - px) * (C[2] - pz) - (C[0] - px) * (B[2] - pz)) / det
                l2 = ((C[0] - px) * (A[2] - pz) - (A[0] - px) * (C[2] - pz)) / det
                l3 = 1 - l1 - l2
                if l1 < 0 or l2 < 0 or l3 < 0:
                    continue
                hits[i][k].append(l1 * A[1] + l2 * B[1] + l3 * C[1])
    vox = np.zeros((nx, ny, nz), bool)
    ys = y0 + (np.arange(ny) + 0.5) * H
    for i in range(nx):
        for k in range(nz):
            h = sorted(hits[i][k])
            # 同じ所を2回数えたもの(辺の上)を除く
            hh = []
            for y in h:
                if not hh or abs(y - hh[-1]) > 1e-6:
                    hh.append(y)
            for j in range(0, len(hh) - 1, 2):
                vox[i, (ys > hh[j]) & (ys < hh[j + 1]), k] = True
    return vox, (x0, y0, z0)


def local_thickness(vox):
    """各ボクセルの局所の厚さ [mm](RADII の段階で)"""
    dt = ndimage.distance_transform_edt(vox) * H
    lt = np.zeros(vox.shape, np.float32)
    for r in RADII:
        core = dt >= r
        if not core.any():
            break
        covered = ndimage.distance_transform_edt(~core) * H <= r + H / 2
        lt[covered & vox] = 2 * r
    lt[vox & (lt == 0)] = 2 * RADII[0] * 0.5
    return lt


def thin_regions(vox, lt, origin, limit):
    """厚さ limit 未満の塊(2 方向に 0.6mm 以上広がるもの)の一覧"""
    thin = vox & (lt < limit)
    # 角の近くの細い帯(線のような形)を除き、板や壁のような形(2 方向に広がる)だけを残す:
    # 5 × 5 × 1 の板を 3 つの向きで当てはめ(オープニング)、どれかの板が入る所だけ残す
    plate = np.zeros(thin.shape, bool)
    for shape in ((5, 5, 1), (5, 1, 5), (1, 5, 5)):
        plate |= ndimage.binary_opening(thin, structure=np.ones(shape, bool))
    thin = plate
    lab, n = ndimage.label(thin, structure=np.ones((3, 3, 3)))
    out = []
    keep = np.zeros(vox.shape, bool)
    for idx in range(1, n + 1):
        pts = np.argwhere(lab == idx)
        if len(pts) < 30:
            continue
        xyz = pts * H + np.array(origin) + H / 2
        ext = np.sort(np.ptp(xyz, axis=0))
        keep[lab == idx] = True
        tmin = lt[tuple(pts.T)].min()
        tmed = np.median(lt[tuple(pts.T)])
        out.append(dict(center=xyz.mean(axis=0), lo=xyz.min(axis=0), hi=xyz.max(axis=0), vol=len(pts) * H**3, tmin=tmin, tmed=tmed))
    return out, keep


if __name__ == '__main__':
    solid = mm.build(mt.P).val()
    vox, origin = voxelize(solid)
    vol = vox.sum() * H**3
    print(f'ボクセル {vox.shape}、体積 {vol:.0f} mm³(CAD {solid.Volume():.0f} mm³)')
    lt = local_thickness(vox)
    regions, keep = thin_regions(vox, lt, origin, WALL_MIN)
    regions.sort(key=lambda r: -r['vol'])
    print(f'厚さ {WALL_MIN}mm 未満の所(壁・板のような塊): {len(regions)} か所')
    for no, r in enumerate(regions, 1):
        c, lo, hi = r['center'], r['lo'], r['hi']
        print(f"  {no}. 中心 ({c[0]:.1f}, {c[1]:.1f}, {c[2]:.1f})、x {lo[0]:.1f}〜{hi[0]:.1f}、y {lo[1]:.1f}〜{hi[1]:.1f}、z {lo[2]:.1f}〜{hi[2]:.1f}、"
              f"体積 {r['vol']:.2f} mm³、厚さ 一番薄い {r['tmin']:.1f}mm・真ん中 {r['tmed']:.1f}mm")
    # 図: 3 方向から見た、薄い所(色)と形(灰色)
    x0, y0, z0 = origin
    nx, ny, nz = vox.shape
    ext = {'xz': [x0, x0 + nx * H, z0, z0 + nz * H], 'xy': [x0, x0 + nx * H, y0, y0 + ny * H], 'yz': [y0, y0 + ny * H, z0, z0 + nz * H]}
    thin_t = np.where(keep, lt, np.inf)
    fig, axes = plt.subplots(1, 3, figsize=(18, 5.5), gridspec_kw=dict(width_ratios=[3, 3, 1.2]))
    views = (('外から見る(xz)', 1, 'xz', 'x [mm]', 'z [mm]'), ('上から見る(xy)', 2, 'xy', 'x [mm]', 'y [mm]'), ('前から見る(yz)', 0, 'yz', 'y [mm]', 'z [mm]'))
    for ax, (title, axis, key, xl, yl) in zip(axes, views):
        sil = vox.any(axis=axis)
        tmin = thin_t.min(axis=axis)
        if key == 'yz':
            sil, tmin = sil, tmin
        ax.imshow(np.where(sil, 0.85, 1.0).T, origin='lower', extent=ext[key], cmap='gray', vmin=0, vmax=1, aspect='equal')
        m = np.ma.masked_invalid(np.where(np.isfinite(tmin), tmin, np.nan))
        im = ax.imshow(m.T, origin='lower', extent=ext[key], cmap='autumn', vmin=0.2, vmax=WALL_MIN, aspect='equal')
        for no, r in enumerate(regions, 1):      # 塊の番号(一覧の順)
            c = r['center']
            u, v = {'xz': (c[0], c[2]), 'xy': (c[0], c[1]), 'yz': (c[1], c[2])}[key]
            ax.text(u, v, str(no), fontsize=9, color='b', fontweight='bold', ha='center', va='center',
                    bbox=dict(boxstyle='circle,pad=0.15', fc='w', ec='b', lw=0.8, alpha=0.85))
        ax.set_title(title)
        ax.set_xlabel(xl)
        ax.set_ylabel(yl)
    fig.colorbar(im, ax=axes, label='肉の厚さ [mm](色の所が 0.8mm 未満)', shrink=0.8)
    fig.suptitle(f'モーターマウント 右 {mt.VER} の肉の薄い所(JLC Temp Resin のすすめる最小の壁 {WALL_MIN}mm 未満。灰色は形の影)')
    fig.savefig(f'mount_{mt.VER}_thickness.png', dpi=110, bbox_inches='tight')
    print('図', f'mount_{mt.VER}_thickness.png')

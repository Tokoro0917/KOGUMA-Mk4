"""吸引ファンの流体の計算の結果を、軸を通る縦の断面(y = 0 の近くのセル)で図にする(2026-11-24)。
使い方: python3 docs/calc/fan_cfd/flow_fig.py <出す図> <計算のフォルダ>[@回] ...(フォルダごとに 1 列: 上が圧力、下が速さ)
出す図の名前が _en.png で終わるときは、英語の図にする(報告の PDF 用)"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import post

plt.rcParams['font.family'] = 'IPAGothic'
NAMES = {'A': 'A 今', 'B': 'B xfa273 さん', 'C': 'C 組み合わせ', 'D': 'D 壁なし'}
NAMES_EN = {'A': 'A current', 'B': 'B xfa273 type', 'C': 'C combined', 'D': 'D no walls'}


def slice_data(arg):
    t = None
    case = arg
    if '@' in arg:
        case, t = arg.split('@')
    pts, faces, owner, neigh, patches = post.read_mesh(case)
    ncell = max(owner.max(), neigh.max()) + 1
    cf, sf = post.face_geometry(pts, faces)
    vol, cc = post.cell_geometry(cf, sf, owner, neigh, ncell)
    if t is None:
        t = post.latest_time(case)
    p, _ = post.read_field(case, t, 'p', ncell)
    U, _ = post.read_field(case, t, 'U', ncell)
    h = np.cbrt(vol)
    sel = np.abs(cc[:, 1]) < h * 0.6                 # y = 0 の面を通るセル
    return case, cc[sel], h[sel], p[sel] * post.RHO, np.linalg.norm(U[sel], axis=1)


out = sys.argv[1]
args = sys.argv[2:]
EN = out.endswith('_en.png')
LABEL_P = '圧力 [Pa]'
LABEL_U = '速さ [m/s]'
TITLE = '軸を通る縦の断面(y = 0)。灰色は壁・羽根(35,000rpm)'
if EN:
    NAMES = NAMES_EN
    LABEL_P = 'pressure [Pa]'
    LABEL_U = 'speed [m/s]'
    TITLE = 'Vertical section through the axis (y = 0). Grey = walls and impeller (35,000 rpm)'
fig, axes = plt.subplots(2, len(args), figsize=(6.2 * len(args), 7.5), squeeze=False)
for k, arg in enumerate(args):
    case, c, h, p, u = slice_data(arg)
    name = os.path.basename(case.split('@')[0].rstrip('/'))[0]
    for row, (val, cmap, vmin, vmax, lab) in enumerate(((p, 'coolwarm', -2500, 1000, LABEL_P), (u, 'viridis', 0, 60, LABEL_U))):
        ax = axes[row, k]
        order = np.argsort(-h)                         # 大きいセルから描き、小さいセルを上に重ねる
        sc = ax.scatter(c[order, 0] * 1000, c[order, 2] * 1000, c=val[order], s=(h[order] * 1000 * 9)**2, marker='s', cmap=cmap, vmin=vmin, vmax=vmax, linewidths=0)
        ax.set_xlim(-30, 30)
        ax.set_ylim(-6, 20)
        ax.set_aspect('equal')
        ax.set_facecolor('#444444')
        ax.set_title(f'{NAMES.get(name, name)}: {lab}', fontsize=10)
        fig.colorbar(sc, ax=ax, shrink=0.7)
fig.suptitle(TITLE, fontsize=11)
fig.tight_layout()
fig.savefig(out, dpi=100)
print(out)

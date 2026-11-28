"""3 つのファンの形(make_case.py の A・B・C)の、軸を通る縦の断面の図(2026-11-24)。
使い方(リポジトリの一番上から): python3 docs/calc/fan_cfd/section_fig.py → docs/img/tire24/fan_cfd_shapes.png
英語の図(報告の PDF 用): python3 docs/calc/fan_cfd/section_fig.py --en → docs/img/tire24/fan_cfd_shapes_en.png"""
import importlib
import os
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

plt.rcParams['font.family'] = 'IPAGothic'
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
EN = '--en' in sys.argv            # 英語の図にする(draw の中で sys.argv を書きかえるので、先に見ておく)
TITLES = {'A': 'A 今の MK4(止まった輪の中で回る)', 'B': 'B xfa273 さんの形(外の壁も回る、下から出す)', 'C': 'C 組み合わせ(B + 止まった輪、上へ出す)'}
# 図の中の言葉(日本語 → 英語)
WORDS_EN = {
    'A 今の MK4(止まった輪の中で回る)': 'A: current MK4 (open impeller inside a fixed ring)',
    'B xfa273 さんの形(外の壁も回る、下から出す)': 'B: xfa273 type (rotating shroud, exhaust at the bottom)',
    'C 組み合わせ(B + 止まった輪、上へ出す)': 'C: combined (B + fixed ring, exhaust upward)',
    '回る羽根': 'rotating impeller',
    'フレームと機体の下の部屋': 'frame and chamber under the robot',
    'メイン基板': 'main PCB',
    'モーター': 'motor',
    '止まった輪': 'fixed ring',
    '回る座標で解く範囲(MRF)': 'rotating zone (MRF)',
    'x [mm](ファンの中心から)': 'x [mm] (from fan axis)',
    'z [mm](床から)': 'z [mm] (from floor)',
    '流体の計算で比べる 3 つの形(y = 0 の縦の断面。下の部屋の下の小さな穴が、スカートと床のすき間 0.15mm の漏れ)':
        'Three geometries compared by CFD (section at y = 0; the small hole below the chamber models the 0.15 mm skirt-floor leak)',
}


def word(text):
    """英語の図のときは英語に置きかえる"""
    if EN:
        return WORDS_EN[text]
    return text


def draw(ax, case):
    sys.argv = ['x', case, '/tmp/unused']
    mc = importlib.import_module('make_case')
    mc = importlib.reload(mc)
    parts = [(mc.impeller(), '#d95f5f', word('回る羽根')), (mc.base(), '#5f5a50', word('フレームと機体の下の部屋')), (mc.pcb(), '#2e8b57', word('メイン基板')),
             (mc.motor(), '#b0b0b0', word('モーター'))]
    if mc.RING:
        parts.append((mc.ring_solid(mc.RING[0], mc.RING[1], mc.Z_FRAME - 0.1, 10.0), '#f0d060', word('止まった輪')))
    import cadquery as cq
    slab = cq.Workplane('XY').box(200, 0.01, 60).translate((0, 0, 5))
    for wp, color, label in parts:
        cut = wp.intersect(slab)
        first = True
        for face in cut.faces().vals():
            if abs(face.normalAt().y) < 0.99 or face.Center().y > 0:
                continue
            w = face.outerWire()
            pts = []
            for k in range(600):
                v = w.positionAt(k / 600)          # 輪の線の上を、長さで等分した点
                pts.append((v.x, v.z))
            ax.add_patch(Polygon(pts, closed=True, fc=color, ec='k', lw=0.4, label=label if first else None))
            first = False
    ax.add_patch(plt.Rectangle((-mc.R_ZONE, mc.Z_ZONE0), 2 * mc.R_ZONE, mc.Z_ZONE1 - mc.Z_ZONE0, fill=False, ec='b', ls='--', lw=0.8,
                               label=word('回る座標で解く範囲(MRF)')))
    ax.set_xlim(-30, 30)
    ax.set_ylim(-6, 20)
    ax.set_aspect('equal')
    ax.set_title(word(TITLES[case]), fontsize=10)
    ax.set_xlabel(word('x [mm](ファンの中心から)'))
    ax.set_ylabel(word('z [mm](床から)'))


fig, axes = plt.subplots(1, 3, figsize=(18, 4.6))
for ax, case in zip(axes, 'ABC'):
    draw(ax, case)
h, l = axes[2].get_legend_handles_labels()
fig.legend(h, l, loc='lower center', ncol=6, fontsize=9)
fig.suptitle(word('流体の計算で比べる 3 つの形(y = 0 の縦の断面。下の部屋の下の小さな穴が、スカートと床のすき間 0.15mm の漏れ)'), fontsize=11)
fig.tight_layout(rect=(0, 0.07, 1, 0.94))
out = os.path.join(HERE, '../../img/tire24/fan_cfd_shapes.png')
if EN:
    out = os.path.join(HERE, '../../img/tire24/fan_cfd_shapes_en.png')
fig.savefig(out, dpi=100)
print(out)

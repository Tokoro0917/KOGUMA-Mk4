"""3 つのファンの形(make_case.py の A・B・C)の、軸を通る縦の断面の図(2026-11-24)。
使い方(リポジトリの一番上から): python3 docs/calc/fan_cfd/section_fig.py → docs/img/tire24/fan_cfd_shapes.png"""
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
TITLES = {'A': 'A 今の MK4(止まった輪の中で回る)', 'B': 'B xfa273 さんの形(外の壁も回る、下から出す)', 'C': 'C 組み合わせ(B + 止まった輪、上へ出す)'}


def draw(ax, case):
    sys.argv = ['x', case, '/tmp/unused']
    mc = importlib.import_module('make_case')
    mc = importlib.reload(mc)
    parts = [(mc.impeller(), '#d95f5f', '回る羽根'), (mc.base(), '#5f5a50', 'フレームと機体の下の部屋'), (mc.pcb(), '#2e8b57', 'メイン基板'),
             (mc.motor(), '#b0b0b0', 'モーター')]
    if mc.RING:
        parts.append((mc.ring_solid(mc.RING[0], mc.RING[1], mc.Z_FRAME - 0.1, 10.0), '#f0d060', '止まった輪'))
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
                               label='回る座標で解く範囲(MRF)'))
    ax.set_xlim(-30, 30)
    ax.set_ylim(-6, 20)
    ax.set_aspect('equal')
    ax.set_title(TITLES[case], fontsize=10)
    ax.set_xlabel('x [mm](ファンの中心から)')
    ax.set_ylabel('z [mm](床から)')


fig, axes = plt.subplots(1, 3, figsize=(18, 4.6))
for ax, case in zip(axes, 'ABC'):
    draw(ax, case)
h, l = axes[2].get_legend_handles_labels()
fig.legend(h, l, loc='lower center', ncol=6, fontsize=9)
fig.suptitle('流体の計算で比べる 3 つの形(y = 0 の縦の断面。下の部屋の下の小さな穴が、スカートと床のすき間 0.15mm の漏れ)', fontsize=11)
fig.tight_layout(rect=(0, 0.07, 1, 0.94))
out = os.path.join(HERE, '../../img/tire24/fan_cfd_shapes.png')
fig.savefig(out, dpi=100)
print(out)

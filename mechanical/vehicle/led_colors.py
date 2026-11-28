"""基板の表示用 LED の色を変えたときの見た目を比べる図(2026-11-27、ユーザー「LED は何色がいいと思いますか」「デザインの問題」「どんな感じになるかみせて」)。
使い方(リポジトリの一番上で):
  1. T24_TMP=<一時フォルダ> python3 mechanical/vehicle/t24_mass.py   (色の図の三角と色を <一時フォルダ>/vehicle_t24_colors.npz に書き出す)
  2. T24_TMP=<一時フォルダ> python3 mechanical/vehicle/led_colors.py → mechanical/vehicle/led_colors_t24.png
LED の位置は KiCad の基板(hardware/kicad/KOGUMA-Mk4_t24/KOGUMA-Mk4_t24.kicad_pcb)の D2・D90〜D96・D98 から読んだ値を書き写した。
KiCad の座標 (X, Y) → 機体の座標 (x, y) = (X − 150, 100 − Y)(マウントのねじ H1〜H4 で合わせた)。
光っている感じは、LED の上に、白い基板に広がる光の丸(半透明)を重ねて表す"""
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgba
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

HERE = os.path.dirname(os.path.abspath(__file__))
SCRATCH = os.environ.get('T24_TMP', '/tmp')
Z_PCB_TOP = 14.2
# KiCad の位置 (X, Y)
LEDS_KICAD = {'D2': (130.25, 113.75), 'D90': (130.4, 101.78), 'D91': (130.9, 99.91), 'D92': (130.4, 97.98),
              'D93': (121.85, 114.39), 'D94': (122.15, 112.46), 'D95': (122.15, 87.63), 'D96': (121.85, 85.71),
              'D98': (185.2, 100.0)}
COLORS = [('オレンジ(今の LED)', '#ff8a1f'), ('青', '#2f7bff'), ('白', '#ffffff'), ('赤', '#ff2a2a')]


def box_tris(x, y, z, lx, ly, lz):
    """直方体の三角(12 枚)"""
    v = np.array([[x - lx / 2, y - ly / 2, z], [x + lx / 2, y - ly / 2, z], [x + lx / 2, y + ly / 2, z], [x - lx / 2, y + ly / 2, z],
                  [x - lx / 2, y - ly / 2, z + lz], [x + lx / 2, y - ly / 2, z + lz], [x + lx / 2, y + ly / 2, z + lz], [x - lx / 2, y + ly / 2, z + lz]])
    faces = [(0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    return [v[list(f)] for f in faces]


def glow_tris(x, y, z, r, n=24):
    """光の丸(基板の上に置く平らな円)"""
    out = []
    for i in range(n):
        a0 = 2 * np.pi * i / n
        a1 = 2 * np.pi * (i + 1) / n
        out.append(np.array([[x, y, z], [x + r * np.cos(a0), y + r * np.sin(a0), z], [x + r * np.cos(a1), y + r * np.sin(a1), z]]))
    return out


data = np.load(os.path.join(SCRATCH, 'vehicle_t24_colors.npz'))
base_tris = list(data['tris'])
base_cols = []
for c in data['colors']:
    c = tuple(c)
    if np.allclose(c[:3], to_rgba('#9aa0a6')[:3]):      # 電池は半分すかす(下の LED が見えるように)
        c = (c[0], c[1], c[2], 0.3)
    base_cols.append(c)

plt.rcParams['font.family'] = 'IPAPGothic'
fig = plt.figure(figsize=(16, 12), facecolor='#dfe5ea')
for i in range(len(COLORS)):
    name, color = COLORS[i]
    tris = list(base_tris)
    cols = list(base_cols)
    for X, Y in LEDS_KICAD.values():
        x = X - 150.0
        y = 100.0 - Y
        for t in glow_tris(x, y, Z_PCB_TOP + 0.02, 2.6):
            tris.append(t)
            cols.append(to_rgba(color, 0.35))
        for t in glow_tris(x, y, Z_PCB_TOP + 0.03, 1.4):
            tris.append(t)
            cols.append(to_rgba(color, 0.55))
        for t in box_tris(x, y, Z_PCB_TOP, 1.6, 0.8, 0.95):
            tris.append(t)
            cols.append(to_rgba(color, 1.0))
    ax = fig.add_subplot(2, 2, i + 1, projection='3d')
    ax.set_facecolor('#dfe5ea')
    ax.add_collection3d(Poly3DCollection(np.array(tris), facecolors=cols, edgecolor='none'))
    ax.set_xlim(-52, 52)
    ax.set_ylim(-40, 40)
    ax.set_zlim(0, 35)
    ax.set_box_aspect((104, 80, 35), zoom=1.3)
    ax.view_init(42, 160)         # 斜め後ろ(左)の上から(LED は後ろに多い)
    ax.set_axis_off()
    ax.set_title(name, fontsize=14)
fig.suptitle('表示用 LED の色の比べ(白い基板、斜め後ろの上から、電池はすかして描く。LED 9 個: 後ろの角に 2 個ずつ・後ろの真ん中 3 個・電源・前)', fontsize=12)
fig.tight_layout(rect=(0, 0, 1, 0.95))
out = os.path.join(HERE, 'led_colors_t24.png')
fig.savefig(out, dpi=100, facecolor=fig.get_facecolor())
print(out)

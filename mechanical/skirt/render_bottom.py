"""機体を裏(床の側)から見た図に、一次スカート(t24v3)と二次スカート(青い袋)を重ねる(2026-11-27、ユーザー「裏側見せて」)。
使い方(リポジトリの一番上で): python3 mechanical/skirt/render_bottom.py → mechanical/skirt/bottom_view_t24.png
機体は mechanical/vehicle/mk4_vehicle_t24.step(部品の名前がないので、色は外形の位置で決める)。
機体のモデルに入っている仮のスカート(吸引する面のふちのフィルム、z 0.5〜2.0)は描かない。
二次スカート(袋 t24v3)は、枠の下の面に貼った平らな 1 枚(厚さ 0.05mm)で表す。実物は枠から外がやわらかく床の方へたれる"""
import os
import sys
import numpy as np
import cadquery as cq
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

HERE = os.path.dirname(os.path.abspath(__file__))
VEHICLE = os.path.join(HERE, '..', 'vehicle', 'mk4_vehicle_t24.step')
SKIRT = os.path.join(HERE, 'skirt_t24v3.step')
X_OUT, Y_OUT, W = 40.0, 16.2, 2.5     # 枠(skirt_t24.py の t24v3)
FILM_T = 0.05
Z_SKIRT_BOTTOM = 1.0


def color_of(bb):
    """外形の位置から部品の色を決める"""
    if bb.zmin > 1.9 and bb.zmax < 2.9 and bb.xmax - bb.xmin > 90:
        return '#4a463f'     # フレーム
    if bb.zmax <= 2.01 and bb.zmin >= 0.49 and abs(bb.xmax - 40) < 0.1:
        return None          # 機体のモデルの仮のスカート(描かない)
    if bb.zmin < 0.6 and bb.zmax <= 2.01 and bb.xmax - bb.xmin < 6:
        return '#f0f0f0'     # 滑り板
    if bb.zmin < 0 + 0.5 and bb.zmax > 20:
        return '#262626'     # タイヤ
    if bb.zmin < 1.0 and bb.zmax - bb.zmin > 5 and bb.xmax - bb.xmin < 4.5:
        return '#666666'     # ねじ
    return '#c8c8c8'


def tris(shape):
    verts, faces = shape.tessellate(0.05, 0.3)
    v = np.array([(p.x, p.y, p.z) for p in verts])
    if len(faces) == 0:
        return np.zeros((0, 3, 3))
    return v[np.array(faces)]


TT = []
CC = []
veh = cq.importers.importStep(VEHICLE).val()
for s in veh.Solids():
    c = color_of(s.BoundingBox())
    if c is None:
        continue
    T = tris(s)
    TT.append(T)
    CC += [c] * len(T)
skirt = cq.importers.importStep(SKIRT).val()
T = tris(skirt)
TT.append(T)
CC += ['#f28e2b'] * len(T)
# 二次スカート(袋 t24v3): film_t24.py の形を、枠の下の面(両面テープの下)に平らに置く
sys.path.insert(0, HERE)
import film_t24
z_film = Z_SKIRT_BOTTOM - 0.15 - FILM_T
film2d = film_t24.film_outline()
film_wp = cq.Workplane('XY').workplane(offset=z_film).polyline(list(film2d.exterior.coords)[:-1]).close().extrude(FILM_T)
for hole in film2d.interiors:
    film_wp = film_wp.cut(cq.Workplane('XY').workplane(offset=z_film - 0.1).polyline(list(hole.coords)[:-1]).close().extrude(FILM_T + 0.2))
flat = film_wp
T = tris(flat.val())
TT.append(T)
CC += ['#3a7bd5'] * len(T)
TT = np.concatenate(TT)

plt.rcParams['font.family'] = 'IPAPGothic'
from matplotlib.patches import Polygon as MplPolygon
fig = plt.figure(figsize=(16, 7.5))
# 左: 真下から見た図
ax = fig.add_subplot(1, 2, 1, projection='3d')
ax.add_collection3d(Poly3DCollection(TT, facecolors=CC, edgecolor='none'))
ax.set_xlim(-52, 52)
ax.set_ylim(-40, 40)
ax.set_zlim(0, 35)
ax.set_box_aspect((104, 80, 35), zoom=1.25)
ax.view_init(-90, -90)
ax.set_axis_off()
ax.set_title('真下から(床から見上げる。右が前、ファンの穴が見える)', fontsize=12)

# 右: マウントの後ろのねじ(x = -21)を通る断面の、右の横の所の拡大(横から見る)
ax2 = fig.add_subplot(1, 2, 2)
X_CUT = -21.0
slab = cq.Solid.makeBox(0.02, 80, 40, cq.Vector(X_CUT - 0.01, -40, -2))
shapes = []
for s in veh.Solids():
    c = color_of(s.BoundingBox())
    if c is not None:
        shapes.append((s, c))
shapes.append((skirt, '#f28e2b'))
shapes.append((flat.val(), '#3a7bd5'))
for s, c in shapes:
    bb = s.BoundingBox()
    if bb.xmin > X_CUT or bb.xmax < X_CUT:
        continue
    sec = s.intersect(slab)
    for f in sec.Faces():
        if abs(f.normalAt().x) < 0.5:
            continue
        verts, faces = f.tessellate(0.005, 0.1)
        for t in faces:
            ax2.add_patch(MplPolygon([(-verts[n].y, verts[n].z) for n in t], closed=True, fc=c, ec=c, lw=0.2))
ax2.axhline(0, color='#888888', lw=1)
ax2.text(24.2, 0.15, '床', fontsize=10, color='#555555')
ax2.annotate('フレーム(z 2.0〜2.8)', xy=(20, 2.4), xytext=(20.5, 3.7), fontsize=9, arrowprops=dict(arrowstyle='->', lw=0.6))
ax2.annotate('一次スカート(z 1.0〜1.85)\n上に両面テープ 0.15mm', xy=(14.8, 1.4), xytext=(9.3, 3.4), fontsize=9, arrowprops=dict(arrowstyle='->', lw=0.6))
ax2.annotate('二次スカート(青い袋 t24v3)\n枠の下に貼る。枠から外はたれて床へ', xy=(19.0, 0.8), xytext=(9.3, -1.3), fontsize=9, arrowprops=dict(arrowstyle='->', lw=0.6))
ax2.annotate('マウントのねじの頭\n(z 0.9〜2.0)', xy=(18.4, 1.0), xytext=(19.5, -1.3), fontsize=9, arrowprops=dict(arrowstyle='->', lw=0.6))
ax2.set_xlim(9, 26)
ax2.set_ylim(-1.8, 4.6)
ax2.set_aspect('equal')
ax2.set_xlabel('中心から右への距離 [mm](−y)')
ax2.set_ylabel('z [mm](床から)')
ax2.set_title(f'右の横の断面(x = {X_CUT:g}、ねじの所。前から見る)', fontsize=12)
fig.suptitle('機体の裏: 一次スカート t24v3(橙、枠 80 × 32.4mm・幅 2.5mm)と二次スカート(青、Digi-Key の袋 t24v3、96 × 49mm)', fontsize=12)
fig.tight_layout(rect=(0, 0, 1, 0.95))
out = os.path.join(HERE, 'bottom_view_t24.png')
fig.savefig(out, dpi=110)
print(out)

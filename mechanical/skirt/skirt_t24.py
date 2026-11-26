"""タイヤ24mm の機体の一次スカート(2026-11-26、ユーザー「一次スカートを作ろうと」)。
t24v2(2026-11-26、ユーザー「それは吸着できない。ネジの内側に入れて」): 枠の横をマウントのねじの頭より内側に入れた。
  t24v1 は吸引する面(80 × 42.6mm)のふちに沿い、ねじの頭(床から 0.9mm、枠より低い)が囲む面の中に入っていた。
t24v1: 吸引する面のふちに沿った枠。
吸引する面(フレームの下、80 × 42.6mm)のまわりを囲む平らな枠。自分の 3D プリンタ(FDM)で印刷し、両面テープでフレームの下に貼る。
下に二次スカート(フィルム)を貼って床に近づける前提。
考え方は KOGUMA.MK3 の「一次スカート」(底板の下に貼る四角い枠、外 23 × 49.6mm・内 15 × 41.6mm・厚さ 1mm)と、
ToraNeko.Mk3 のスカート枠(mechanical/skirt_slider/、両面テープの厚さの分だけ低く作る)。
使い方(リポジトリの一番上で): python3 mechanical/skirt/skirt_t24.py
  → mechanical/skirt/skirt_t24v1.stl(印刷の向き: フレームに貼る面が下)
     mechanical/skirt/skirt_t24v1.step・mechanical/order_t24/14_skirt_t24v1.step(機体の座標)
     mechanical/skirt/skirt_t24v1.png(フレーム・ねじの頭・滑り板と重ねた図)

寸法の決め方(座標は機体と同じ。原点は車軸の真ん中の床、+x 前、+y 左、mm):
  - 高さ: 下の端を床から 1.0mm(ユーザー)。フレームの下の面は z 2.0 なので、両面テープ(厚さ TAPE_T)の分だけ低く作る(ToraNeko と同じ)
  - 枠の横(t24v2): マウントのねじの頭(鉄 低頭 M2、頭 φ3.8、(6.8, ±18.4)・(−21, ±18.4)、|y| 16.5〜20.3)の内側。
    外のふち |y| 16.2(ねじの頭と 0.3mm)、内のふち |y| 16.2 − W
  - 枠の前後: 外のふち x ±40(吸引する面のふち。そのすぐ外にフレームの窓がかかるので広げない)。内のふちは x ±(40 − W)
  - 前後の滑り板(カグスベール φ5、(±45, 0))のまわりは 0.5mm あける
  - 機体が加減速で 0.64° 傾いて滑り板が床に着いても、枠の前後の端(x ±40)は床から 0.56mm 残る(床に当たらない)"""
import os
import cadquery as cq
from shapely.geometry import box, Point, Polygon
from shapely.ops import unary_union
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

VER = 't24v2'
HERE = os.path.dirname(os.path.abspath(__file__))
FRAME_STEP = os.path.join(HERE, '..', 'order_t24', '01_frame_t24v10.step')

SUCTION_X = 40.0          # 吸引する面の半分(前後)
SUCTION_Y = 21.3          # 吸引する面の半分(左右)
W = 2.0                   # 枠の幅(0.4mm のノズルで 5 周。両面テープを貼りやすい幅)
X_OUT = 40.0              # 枠の前後の外のふち(吸引する面のふち x ±40。その外はフレームの窓がかかるので広げない)
Y_OUT = 16.2              # 枠の横の外のふち(t24v2: ねじの頭 |y| 16.5 の 0.3mm 内)
Z_FRAME_BOTTOM = 2.0      # フレームの下の面
Z_BOTTOM = 1.0            # 枠の下の端(床から、ユーザー)
TAPE_T = 0.15             # 両面テープの厚さ(パッケージの厚さに合わせて変える)
THICK = Z_FRAME_BOTTOM - Z_BOTTOM - TAPE_T   # 印刷する厚さ(0.85mm)
SCREWS = [(6.8, 18.4), (6.8, -18.4), (-21.0, 18.4), (-21.0, -18.4)]
SCREW_HEAD_R = 1.9        # 低頭 M2 の頭 φ3.8
SCREW_CLEAR = 0.3
SKIDS = [(45.0, 0.0), (-45.0, 0.0)]
SKID_R = 2.5
SKID_CLEAR = 0.5
CORNER_R = 1.0            # 外の角の丸み


def frame_bottom_outline():
    """フレームの下の面(z 2.0)で、カーボンがある所の形(shapely)"""
    frame = cq.importers.importStep(FRAME_STEP).val()
    cut = frame.intersect(cq.Solid.makeBox(200, 200, 0.02, cq.Vector(-100, -100, Z_FRAME_BOTTOM + 0.1)))
    # 切り口の面を三角に分けて、三角を全部つなげる(面のふちをたどると、辺の向きがそろわず形がゆがむため)
    polys = []
    for face in cut.Faces():
        if abs(face.normalAt().z) < 0.5:
            continue
        verts, tris = face.tessellate(0.01, 0.1)
        for t in tris:
            polys.append(Polygon([(verts[n].x, verts[n].y) for n in t]))
    return unary_union(polys).buffer(0.001).buffer(-0.001)


def skirt_outline(carbon):
    """枠の形(上から見た形、shapely)"""
    outer = box(-X_OUT, -Y_OUT, X_OUT, Y_OUT).intersection(carbon)
    inner = box(-X_OUT + W, -Y_OUT + W, X_OUT - W, Y_OUT - W)
    ring = outer.difference(inner)
    for x, y in SCREWS:      # ねじの頭とは重ならないはず(t24v2 では枠の外)
        assert ring.distance(Point(x, y).buffer(SCREW_HEAD_R, 64)) >= SCREW_CLEAR - 1e-6, 'ねじの頭に近すぎる'
    for x, y in SKIDS:
        ring = ring.difference(Point(x, y).buffer(SKID_R + SKID_CLEAR, 64))
    # 外の角を丸める(引っかかりにくく、印刷のはがれも減る)。小さな切れ端は捨てる
    ring = ring.buffer(-CORNER_R / 2, join_style=1).buffer(CORNER_R / 2, join_style=1)
    if ring.geom_type == 'MultiPolygon':
        ring = max(ring.geoms, key=lambda g: g.area)
    return ring


def min_width(ring):
    """枠の一番細い所の幅のおおよその値(内へ少しずつ削って、切れるまでの量 × 2)"""
    w = 0.0
    while True:
        test = ring.buffer(-(w + 0.05))
        if test.is_empty or test.geom_type == 'MultiPolygon' or len(test.interiors) == 0:
            return 2 * (w + 0.05)
        w += 0.05


carbon = frame_bottom_outline()
ring = skirt_outline(carbon)
print(f'枠 {VER}: 面積 {ring.area:.0f} mm²、厚さ {THICK:.2f}mm、体積 {ring.area * THICK:.0f} mm³、'
      f'重さ {ring.area * THICK * 1.27 / 1000:.2f} g(PETG 1.27 g/cm³)、一番細い所 約 {min_width(ring):.1f}mm')
inner_area = Polygon(ring.interiors[0]).area
print(f'囲む面積 {inner_area:.0f} mm²(フレームの吸引する面 80 × 42.6 = 3,408mm²。t24v1 は 3,035mm²)')

# 立体: 機体の座標(枠は z 1.0〜1.85。上にテープ 0.15mm)
pts = list(ring.exterior.coords)[:-1]
solid = cq.Workplane('XY').workplane(offset=Z_BOTTOM).polyline(pts).close().extrude(THICK)
for hole in ring.interiors:
    h = cq.Workplane('XY').workplane(offset=Z_BOTTOM - 0.1).polyline(list(hole.coords)[:-1]).close().extrude(THICK + 0.2)
    solid = solid.cut(h)
assert solid.val().isValid()
cq.exporters.export(solid, os.path.join(HERE, f'skirt_{VER}.step'))
cq.exporters.export(solid, os.path.join(HERE, '..', 'order_t24', f'14_skirt_{VER}.step'))
# 印刷の向き: フレームに貼る面(上の面)を下にする(裏返して、下の面を z 0 に)
printed = solid.rotate((0, 0, 0), (1, 0, 0), 180).translate((0, 0, Z_BOTTOM + THICK))
cq.exporters.export(printed, os.path.join(HERE, f'skirt_{VER}.stl'), tolerance=0.01, angularTolerance=0.1)

# 図: 上から見た図(フレーム・ねじの頭・滑り板・ファンの穴と重ねる)
plt.rcParams['font.family'] = 'IPAPGothic'
fig, ax = plt.subplots(figsize=(11, 8))
from matplotlib.path import Path
from matplotlib.patches import PathPatch


def fill(geom, color, alpha, label=None):
    """穴のある形を、穴を抜いて塗る"""
    geoms = [geom] if geom.geom_type == 'Polygon' else list(geom.geoms)
    for k, g in enumerate(geoms):
        verts = []
        codes = []
        for ringline in [g.exterior] + list(g.interiors):
            xy = list(ringline.coords)
            verts += xy
            codes += [Path.MOVETO] + [Path.LINETO] * (len(xy) - 2) + [Path.CLOSEPOLY]
        ax.add_patch(PathPatch(Path(verts, codes), fc=color, ec='none', alpha=alpha, label=label if k == 0 else None))


fill(carbon, '#4a463f', 0.35, 'フレーム(上から見た向き)')
fill(ring, '#f28e2b', 0.95, f'一次スカート {VER}')
sx, sy = box(-SUCTION_X, -SUCTION_Y, SUCTION_X, SUCTION_Y).exterior.xy
ax.plot(sx, sy, color='#257de0', lw=1, ls='--', label='フレームの吸引する面(80 × 42.6mm、カーボンで埋めた所)')
for k, (x, y) in enumerate(SCREWS):
    ax.add_patch(plt.Circle((x, y), SCREW_HEAD_R, color='#666666', label='マウントのねじの頭(低頭 M2)' if k == 0 else None))
for k, (x, y) in enumerate(SKIDS):
    ax.add_patch(plt.Circle((x, y), SKID_R, color='#9ecae1', label='滑り板(カグスベール φ5)' if k == 0 else None))
ax.set_aspect('equal')
ax.set_xlim(-52, 52)
ax.set_ylim(-37, 37)
ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.08), ncol=2, frameon=False, fontsize=9)
ax.set_title(f'一次スカート {VER}(上から見た図。厚さ {THICK:.2f}mm + 両面テープ {TAPE_T}mm、下の端は床から {Z_BOTTOM}mm)', fontsize=12)
ax.set_xlabel('x [mm](前が +)')
ax.set_ylabel('y [mm](左が +)')
fig.tight_layout()
fig.savefig(os.path.join(HERE, f'skirt_{VER}.png'), dpi=120)
print('書き出した')

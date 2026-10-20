"""カーボン板の注文用ファイルを作る(カーボンラボ.jp の入稿ルールに合わせる)
  - DXF: 上から見た外形の実線だけ、1:1、文字・寸法線なし、部品の間は 5mm 以上、ファイル名は半角英数字 20 文字以内
  - フレーム1枚(リブがあるときは、リブも同じ DXF に並べる。リブは繊維の向き 0°= X 方向に寝かせる)
  - ポリカーボネートの板は別の DXF と、1:1 で印刷する型紙(PDF)
使い方: python3 make_order.py [出力のフォルダ]
"""
import os, sys, json
import numpy as np, ezdxf
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
from shapely import affinity
import design as dz, ribparts as rp, dxf_arcs as dxa

VER = '64'          # frame v6.4(ファンの台の左右の穴をなくし、ねじの穴 5つに、2026-10-20)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '../../../mechanical/frame')   # 製作用のファイルは mechanical/frame に置く
os.makedirs(OUT, exist_ok=True)
P = json.load(open(os.path.join(HERE, 'results/final_params.json')))
g = dz.build(**P)
ribs = g['vribs']
slots = [s for (l, h, w) in ribs for s in rp.slots_for(l)]
plate = g['carbon'].difference(unary_union(slots))
holes = dz.holes()

# リブの部品をフレームの下に並べる
parts = []
y = -dz.YB - 6.0
for (l, h, w) in ribs:
    part = rp.rib_part(l.length, h)                  # (u, v)、つめは v < 0
    b = part.bounds
    y_top = y
    part = affinity.translate(part, -b[0] - 50.0, y_top - b[3])
    parts.append(part)
    y = y_top - (b[3] - b[1]) - 5.5

def check_min(poly, name, wmin=1.5):
    """幅 wmin より狭い所(穴・溝・材料)がないか"""
    bad = []
    for i, r in enumerate(poly.interiors):
        if Polygon(r).buffer(-wmin / 2 + 0.01).is_empty:
            bad.append(f'{name}: 穴・溝 {i} が {wmin}mm より狭い')
    thin = poly.difference(poly.buffer(-wmin / 2 + 0.01).buffer(wmin / 2 - 0.01))
    # 尖った角(出っ張った角)が丸くなる分(1か所 0.3mm² 未満)は問題にしない
    for t in getattr(thin, 'geoms', [thin]):
        if t.area > 0.3:
            c = t.centroid
            bad.append(f'{name}: 幅 {wmin}mm より細い材料 ({c.x:.1f}, {c.y:.1f}) 付近 {t.area:.2f} mm²')
    return bad

msgs = []
for p in getattr(plate, 'geoms', [plate]):
    msgs += check_min(p, 'フレーム')
for i, p in enumerate(parts):
    msgs += check_min(p, f'リブ{i + 1}')

doc = ezdxf.new(units=4)
msp = doc.modelspace()
def add(poly):      # 直線と本当の円弧で書く(dxf_arcs.py)
    dxa.add_polygon(msp, poly)
add(plate)
for (x, yy) in holes:
    msp.add_circle((x, yy), dz.HOLE_D / 2)
for p in parts:
    add(p)
fn = os.path.join(OUT, f'MK4FRAME{VER}_T1.dxf')
doc.saveas(fn)

# ポリカーボネート
sheet = g['suction'].difference(Point(dz.FAN_X, 0).buffer(dz.FAN_R, 128))
doc2 = ezdxf.new(units=4); m2 = doc2.modelspace()
dxa.add_polygon(m2, sheet)
doc2.saveas(os.path.join(OUT, f'MK4PC{VER}_T02.dxf'))

# 1:1 の型紙(A4、印刷は「実際のサイズ」で)
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
W, H = 210 / 25.4, 297 / 25.4
fig = plt.figure(figsize=(W, H))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 210); ax.set_ylim(0, 297); ax.axis('off')
ox, oy = 105, 200
xs, ys = sheet.exterior.xy
ax.plot(np.array(xs) + ox, np.array(ys) + oy, 'k-', lw=0.5)
for r in sheet.interiors:
    xs, ys = r.xy; ax.plot(np.array(xs) + ox, np.array(ys) + oy, 'k-', lw=0.5)
ax.plot([30, 80], [60, 60], 'k-', lw=0.8); ax.text(30, 63, '50 mm (check scale)', fontsize=8)
ax.plot([30, 30], [60, 110], 'k-', lw=0.8)
ax.text(20, 280, f'MK4 PVC sheet 0.2mm  (frame v{VER[0]}.{VER[1:]}, suction area {2 * dz.SX:g} x {2 * dz.SY:g}, fan hole dia.{2 * dz.FAN_R:g})', fontsize=9)
ax.text(20, 272, 'print at 100% (actual size). +x (front) = right. glue on TOP of carbon.', fontsize=8)
ax.annotate('FRONT ->', (ox + 25, oy + 18), fontsize=8)
fig.savefig(os.path.join(OUT, f'MK4PC{VER}_template_A4_1to1.pdf'))

print('書き出し:', os.listdir(OUT))
print('最小の幅の確認:', 'OK' if not msgs else msgs)
bb = unary_union([plate] + parts).bounds
print(f'全体の大きさ {bb[2] - bb[0]:.1f} × {bb[3] - bb[1]:.1f} mm、カーボン {(plate.area + sum(p.area for p in parts)) * 1.55e-3:.2f} g(1mm)')

"""基板の外形を DXF に書き出す(形は pcb_shape.py。vehicle.py と同じ)
使い方(リポジトリの一番上で): python3 mechanical/vehicle/pcb_dxf.py
レイヤー: OUTLINE(外形と、壁センサのホルダのほぞの穴)、HOLES(M2 の通し穴 φ2.2)、REF(参考: 壁センサのホルダと足の穴と光、UI の LED、
        ファンの輪とハブ、電池、マウントの柱、ファンの台のねじ、エンコーダ基板)。同じ名前の PNG も書く"""
import math, os, sys
import numpy as np
import ezdxf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcb_shape as ps
sys.path.insert(0, 'docs/calc/frame')
import design as dz, dxf_arcs as dxa

outline = ps.outline()
doc = ezdxf.new('R2010', setup=True); doc.units = ezdxf.units.MM
for nm, col in (('OUTLINE', 7), ('HOLES', 1), ('REF', 8)):
    doc.layers.add(nm, color=col)
msp = doc.modelspace()
dxa.add_polygon(msp, outline, dict(layer='OUTLINE'))
for (x, y) in ps.SCREWS:
    msp.add_circle((x, y), ps.HOLE / 2, dxfattribs=dict(layer='HOLES'))
ref = dict(layer='REF')
msp.add_circle(ps.FAN, 17.5, dxfattribs=ref)                                         # ファンの輪の外側(基板の下、上 z 10.0)
msp.add_circle(ps.FAN, 5.35, dxfattribs=ref)                                         # ファンのハブ(z 16.0 まで基板を抜ける)
for (x, y) in dz.FAN_JOINTS:
    msp.add_circle((x, y), 2.0, dxfattribs=ref)                                      # ファンの台のねじの頭(基板の下、頭の上 z 12.4)
for (x, y) in ps.SCREWS:
    msp.add_circle((x, y), 3.1, dxfattribs=ref)                                      # マウントの柱
msp.add_lwpolyline([(-21.25, -16), (1.25, -16), (1.25, 16), (-21.25, 16)], close=True, dxfattribs=ref)   # 電池(基板の上)
for i, (x, y) in enumerate(ps.LEDS + [ps.LED_FRONT]):                                # UI の LED と前の LED(1608 で 1.6 × 0.8、長い方が y)
    msp.add_lwpolyline([(x - 0.4, y - 0.8), (x + 0.4, y - 0.8), (x + 0.4, y + 0.8), (x - 0.4, y + 0.8)], close=True, dxfattribs=ref)
for (x0, x1, y0, y1) in ps.ENC:                                                      # エンコーダ基板を立てる所(基板の裏)
    msp.add_lwpolyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], close=True, dxfattribs=ref)
    msp.add_text('ENC', height=1.2, dxfattribs=ref).set_placement((x0, y1 + 0.5 if y0 > 0 else y0 - 1.7))
msp.add_text('LED x7', height=1.0, dxfattribs=ref).set_placement((-27.0, -1.0))
for nm, ((sx, sy), ang) in ps.SENS.items():                                        # 壁センサ: ホルダ、ほぞの穴(切り抜く)、足の穴、光
    a = math.radians(ang); u = np.array([math.cos(a), math.sin(a)])
    dxa.add_polygon(msp, ps.slot(nm), dict(layer='OUTLINE'))
    msp.add_lwpolyline(list(ps.holder(nm).exterior.coords), close=True, dxfattribs=ref)
    for (px, py) in ps.pads(nm):
        msp.add_circle((px, py), 0.45, dxfattribs=ref); msp.add_circle((px, py), ps.PAD_D / 2, dxfattribs=ref)
    msp.add_line((sx, sy), tuple(np.array([sx, sy]) + u * 12), dxfattribs=ref)
    msp.add_text(nm, height=1.5, dxfattribs=ref).set_placement(tuple(np.array([sx, sy]) + u * 3 + np.array([-u[1], u[0]]) * 3.5))
os.makedirs('mechanical/pcb', exist_ok=True)
out = f'mechanical/pcb/pcb_outline_{ps.VER}.dxf'
doc.saveas(out)
print(f'{out}: 面積 {ps.board().area:.0f} mm²(穴を除く)、外形 {[round(v, 2) for v in outline.bounds]}')

# ---- 図 ----
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(12, 8.6)); ax.set_facecolor('#20262e')
def draw(g, **k):
    for gg in getattr(g, 'geoms', [g]):
        ax.plot(*gg.exterior.xy, **k)
        for i in gg.interiors: ax.plot(*i.xy, **k)
draw(dz.outline(0), color='#777', lw=1)
bd = ps.board()
for gg in getattr(bd, 'geoms', [bd]):
    ax.fill(*gg.exterior.xy, color='#2f6b3a')
    for i in gg.interiors: ax.fill(*i.xy, color='#20262e')
draw(bd, color='w', lw=1.2)
for (x, y) in ps.SCREWS:
    ax.add_patch(plt.Circle((x, y), 3.1, fill=False, ec='#aaa', lw=0.5))
ax.add_patch(plt.Circle(ps.FAN, 17.5, fill=False, ec='#aaa', lw=0.5, ls='--'))
ax.add_patch(plt.Rectangle((-21.25, -16), 22.5, 32, fill=False, ec='#aaa', lw=0.5, ls='--')); ax.text(-20.5, 13.5, 'battery', color='#aaa', fontsize=8)
for (x0, x1, y0, y1) in ps.ENC: ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, ec='#ddd', lw=0.8))
for (x, y) in ps.LEDS + [ps.LED_FRONT]: ax.add_patch(plt.Rectangle((x - 0.4, y - 0.8), 0.8, 1.6, fc='#ddd'))
for nm, ((sx, sy), ang) in ps.SENS.items():
    a = math.radians(ang); u = np.array([math.cos(a), math.sin(a)]); n = np.array([-u[1], u[0]])
    draw(ps.holder(nm), color='#5aa0ff', lw=1.0)
    for (px, py) in ps.pads(nm): ax.add_patch(plt.Circle((px, py), ps.PAD_D / 2, fill=False, ec='orange', lw=0.6))
    e = np.array([sx, sy]) + u * 20; ax.plot([sx, e[0]], [sy, e[1]], color='#f66', lw=0.7)
    ax.text(*(np.array([sx, sy]) + u * 2 + n * 4.5), nm, color='w', fontsize=9, ha='center', va='center')
ax.set_aspect('equal'); ax.set_xlim(-53, 53); ax.set_ylim(-38, 38); ax.grid(True, color='#444', lw=0.3)
ax.set_title(f'PCB {ps.VER} (green) on frame (gray). Blue: wall sensor holders, orange: lead holes, red: beams. '
             f'{bd.area:.0f} mm2', fontsize=10)
fig.savefig(out.replace('.dxf', '.png'), dpi=90, bbox_inches='tight')

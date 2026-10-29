"""基板の外形を DXF に書き出す(形は pcb_shape.py。vehicle.py と同じ)
使い方(リポジトリの一番上で): python3 mechanical/vehicle/pcb_dxf.py
レイヤー: OUTLINE(外形)、HOLES(M2 の通し穴 φ2.2)、REF(参考: 壁センサ、UI の LED、ファンの輪とハブ、電池、マウントの柱、ファンの台のねじ)"""
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
for i, (x, y) in enumerate(ps.LEDS):                                                 # UI の LED(1608 として 1.6 × 0.8)
    msp.add_lwpolyline([(x - 0.4, y - 0.8), (x + 0.4, y - 0.8), (x + 0.4, y + 0.8), (x - 0.4, y + 0.8)], close=True, dxfattribs=ref)
for (x0, x1, y0, y1) in ps.ENC:                                                      # エンコーダ基板を立てる所(基板の裏)
    msp.add_lwpolyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], close=True, dxfattribs=ref)
    msp.add_text('ENC', height=1.2, dxfattribs=ref).set_placement((x0, y1 + 0.5 if y0 > 0 else y0 - 1.7))
msp.add_text('LED x7', height=1.5, dxfattribs=ref).set_placement((ps.REAR + 4.0, -15.0))
for nm, ((sx, sy), ang) in ps.SENS.items():
    a = math.radians(ang); u = np.array([math.cos(a), math.sin(a)]); n = np.array([-u[1], u[0]])
    for off in (2.0, -2.0):                                                           # 発光・受光 φ3 × 4.5 を寝かせる
        c = np.array([sx, sy]) + n * off
        pts = [c + n * 1.5, c + n * 1.5 + u * 4.5, c - n * 1.5 + u * 4.5, c - n * 1.5]
        msp.add_lwpolyline([tuple(p) for p in pts], close=True, dxfattribs=ref)
    msp.add_line((sx, sy), tuple(np.array([sx, sy]) + u * 12), dxfattribs=ref)
    msp.add_text(nm, height=1.5, dxfattribs=ref).set_placement((sx + 1, sy + 1))
os.makedirs('mechanical/pcb', exist_ok=True)
out = f'mechanical/pcb/pcb_outline_{ps.VER}.dxf'
doc.saveas(out)
print(f'{out}: 面積 {ps.board().area:.0f} mm²(穴を除く)、外形 {[round(v, 2) for v in outline.bounds]}')

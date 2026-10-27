"""機体の案 v4 の基板(U字)の外形を DXF に書き出す(2026-10-27)。形は vehicle.py の「基板」と同じ
使い方(リポジトリの一番上で): python3 mechanical/vehicle/pcb_dxf.py
レイヤー: OUTLINE(外形)、HOLES(M2 の通し穴 φ2.2)、REF(参考: 壁センサ、ファンの輪、電池、マウントの柱、ファンの台のねじ)"""
import math, os, sys
import numpy as np
import ezdxf
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from shapely import affinity
sys.path.insert(0, 'docs/calc/frame')
import design as dz, dxf_arcs as dxa

FAN = (dz.FAN_X, 0.0)
HOLE = 2.2
_half = Polygon([(-19.0, 0.0), (-19.0, 26.0), (-8.0, 26.0), (-8.0, 25.0), (7.0, 25.0), (8.5, 28.0), (9.0, 33.0),
                 (16.0, 33.5), (24.0, 31.0), (34.0, 28.5), (40.0, 27.5), (44.5, 25.0), (45.0, 22.0), (42.0, 19.5), (34.0, 17.5), (14.2, 17.5), (14.2, 0.0)])
outline = unary_union([_half, affinity.scale(_half, 1, -1, origin=(0, 0))]).difference(Point(FAN).buffer(17.5, 64))
outline = outline.buffer(-1.5, join_style=1).buffer(1.5, join_style=1).buffer(1.0, join_style=1).buffer(-1.0, join_style=1)
holes = [(x, sy * y) for (x, y) in dz.MOUNT_SCREWS for sy in (1, -1)]            # マウントの前後の柱(z 13.6、柱にねじ山)
SENS = {'FL': ((12.0, 30.0), 5.0), 'FR': ((12.0, -30.0), -5.0), 'R': ((41.0, 24.0), -75.0), 'L': ((41.0, -24.0), 75.0)}

doc = ezdxf.new('R2010', setup=True); doc.units = ezdxf.units.MM
for nm, col in (('OUTLINE', 7), ('HOLES', 1), ('REF', 8)):
    doc.layers.add(nm, color=col)
msp = doc.modelspace()
dxa.add_polygon(msp, outline, dict(layer='OUTLINE'))
for (x, y) in holes:
    msp.add_circle((x, y), HOLE / 2, dxfattribs=dict(layer='HOLES'))
# 参考
ref = dict(layer='REF')
msp.add_circle(FAN, 17.5, dxfattribs=ref)                                            # ファンの輪の外側
for (x, y) in dz.FAN_JOINTS:
    msp.add_circle((x, y), 2.0, dxfattribs=ref)                                      # ファンの台のねじの頭(基板の下、頭の上 z 12.4)
for (x, y) in holes:
    msp.add_circle((x, y), 3.1, dxfattribs=ref)                                      # マウントの柱
msp.add_lwpolyline([(-21.25, -16), (1.25, -16), (1.25, 16), (-21.25, 16)], close=True, dxfattribs=ref)   # 電池(基板の上)
for nm, ((sx, sy), ang) in SENS.items():
    a = math.radians(ang); u = np.array([math.cos(a), math.sin(a)]); n = np.array([-u[1], u[0]])
    for off in (2.0, -2.0):                                                           # 発光・受光 φ3 × 4.5 を寝かせる
        c = np.array([sx, sy]) + n * off
        pts = [c + n * 1.5, c + n * 1.5 + u * 4.5, c - n * 1.5 + u * 4.5, c - n * 1.5]
        msp.add_lwpolyline([tuple(p) for p in pts], close=True, dxfattribs=ref)
    msp.add_line((sx, sy), tuple(np.array([sx, sy]) + u * 12), dxfattribs=ref)       # 向き
    msp.add_text(nm, height=1.5, dxfattribs=dict(layer='REF')).set_placement((sx + 1, sy + 1))
out = 'mechanical/pcb/pcb_outline_v4.dxf'
doc.saveas(out)
print(f'{out}: 面積 {outline.area:.0f} mm²、外形 {[round(v, 2) for v in outline.bounds]}、穴 {holes}')

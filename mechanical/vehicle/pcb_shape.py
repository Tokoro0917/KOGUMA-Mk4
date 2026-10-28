"""基板の外形(vehicle.py と pcb_dxf.py・pcb_modes.py で共通)。座標は機体と同じ(原点は車軸の中心、+x が前、mm)
v5(2026-10-28): ファンの上は覆い、モーターのハブのまわり(半径 HUB_HOLE)だけ開ける。前の腕どうしもつなげる。
                後ろはフレームの後ろの端の近く(x −46)まで広げ、UI の LED 7個を並べる"""
import os, sys
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from shapely import affinity
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../docs/calc/frame'))
import design as dz

VER = 'v5'
FAN = (dz.FAN_X, 0.0)
HUB_HOLE = 7.0          # ファンのハブ(半径5.35、z 16.0 まで)とモーターを通す穴の半径
HOLE = 2.2              # M2 の通し穴
# 右半分(y ≥ 0)。41T の上(|x| ≤ 8)は |y| ≤ 25。後ろの角はフレームの角(x −46 で y 26.5)より内側
_HALF = [(-46.0, 0.0), (-46.0, 22.5), (-43.0, 25.5), (-8.0, 26.0), (-8.0, 25.0), (7.0, 25.0), (8.5, 28.0), (9.0, 33.0),
         (16.0, 33.5), (24.0, 31.0), (34.0, 28.5), (40.0, 27.5), (44.5, 25.0), (45.0, 22.0), (45.0, 0.0)]
SCREWS = [(x, sy * y) for (x, y) in dz.MOUNT_SCREWS for sy in (1, -1)]       # マウントの前後の柱
SENS = {'FL': ((12.0, 30.0), 5.0), 'FR': ((12.0, -30.0), -5.0), 'R': ((41.0, 24.0), -75.0), 'L': ((41.0, -24.0), 75.0)}
LEDS = [(-43.5, 4.0 * k) for k in range(-3, 4)]                                # UI の LED 7個(後ろの縁、4mm おき)

def outline():
    half = Polygon(_HALF)
    o = unary_union([half, affinity.scale(half, 1, -1, origin=(0, 0))])
    o = o.buffer(-1.5, join_style=1).buffer(1.5, join_style=1).buffer(1.0, join_style=1).buffer(-1.0, join_style=1)
    return o.difference(Point(FAN).buffer(HUB_HOLE, 64))

def board():
    """外形からねじの穴を抜いたもの"""
    return outline().difference(unary_union([Point(p).buffer(HOLE / 2, 24) for p in SCREWS]))

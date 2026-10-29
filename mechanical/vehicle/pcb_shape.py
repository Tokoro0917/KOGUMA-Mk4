"""基板の外形(vehicle.py と pcb_dxf.py・pcb_modes.py で共通)。座標は機体と同じ(原点は車軸の中心、+x が前、mm)
v5(2026-10-28): ファンの上は覆い、モーターのハブのまわり(半径 HUB_HOLE)だけ開ける。前の腕どうしもつなげる。
                後ろはフレームの後ろの端の近く(x −46)まで広げ、UI の LED 7個を並べる
v6(2026-10-29): 大きすぎたので、前はクワガタの形(左右の腕の間を x NOTCH_X より前で開ける)に戻し、後ろは x REAR まで"""
import os, sys
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union
from shapely import affinity
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../docs/calc/frame'))
import design as dz

VER = 'v6'
FAN = (dz.FAN_X, 0.0)
HUB_HOLE = 7.0          # ファンのハブ(半径5.35、z 16.0 まで)とモーターを通す穴の半径
HOLE = 2.2              # M2 の通し穴
REAR = -30.0            # 後ろの縁(電池の後ろの端 −21.25 から約9mm。LED を並べる)
NOTCH_X, NOTCH_Y = 32.0, 17.5   # 前の切り欠き(クワガタの腕の間): x ≥ NOTCH_X、|y| ≤ NOTCH_Y(ファンの輪の前の端は x 31.7)
# 右半分(y ≥ 0)。41T の上(|x| ≤ 8)は |y| ≤ 25
_HALF = [(REAR, 0.0), (REAR, 23.0), (REAR + 3.0, 26.0), (-8.0, 26.0), (-8.0, 25.0), (7.0, 25.0), (8.5, 28.0), (9.0, 33.0),
         (16.0, 33.5), (24.0, 31.0), (34.0, 28.5), (40.0, 27.5), (44.5, 25.0), (45.0, 22.0), (45.0, 0.0)]
SCREWS = [(x, sy * y) for (x, y) in dz.MOUNT_SCREWS for sy in (1, -1)]       # マウントの前後の柱
SENS = {'FL': ((12.0, 30.0), 5.0), 'FR': ((12.0, -30.0), -5.0), 'R': ((41.0, 24.0), -75.0), 'L': ((41.0, -24.0), 75.0)}
ENC = [(-2.6, 5.2, -21.0, -20.4), (-2.6, 5.2, 20.4, 21.0)]   # エンコーダ基板を立てる所(x0, x1, y0, y1)。基板の裏にはんだ付けし、z 3.3 まで下ろす
LEDS = [(REAR + 2.5, 4.0 * k) for k in range(-3, 4)]                                # UI の LED 7個(後ろの縁、4mm おき)

def outline():
    half = Polygon(_HALF)
    o = unary_union([half, affinity.scale(half, 1, -1, origin=(0, 0))])
    o = o.difference(box(NOTCH_X, -NOTCH_Y, 60.0, NOTCH_Y))                    # クワガタの腕の間
    o = o.buffer(2.0, join_style=1).buffer(-2.0, join_style=1)                  # 切り欠きの奥の角を R2 に
    o = o.buffer(-1.5, join_style=1).buffer(1.5, join_style=1).buffer(1.0, join_style=1).buffer(-1.0, join_style=1)
    return o.difference(Point(FAN).buffer(HUB_HOLE, 64))

def board():
    """外形からねじの穴を抜いたもの"""
    return outline().difference(unary_union([Point(p).buffer(HOLE / 2, 24) for p in SCREWS]))

"""基板の外形(vehicle.py と pcb_dxf.py・pcb_modes.py で共通)。座標は機体と同じ(原点は車軸の中心、+x が前、mm)
v5(2026-10-28): ファンの上は覆い、モーターのハブのまわり(半径 HUB_HOLE)だけ開ける。前の腕どうしもつなげる。
                後ろはフレームの後ろの端の近く(x −46)まで広げ、UI の LED 7個を並べる
v6(2026-10-29): 大きすぎたので、前はクワガタの形(左右の腕の間を x NOTCH_X より前で開ける)に戻し、後ろは x REAR まで
v7(2026-10-30): 形をすっきりさせ、壁センサをホルダ(ToraNeko.Mk3 と同じ形、`mechanical/sensor_holder/`)に入れる。
                後ろは長方形、前は「後ろの長方形 + 4つのセンサ(ホルダと足の穴)」を囲む凸の形を、フレームの 1mm 内側で切る。
                車輪(41T・タイヤ)の所と、前の腕の間だけをへこませる。角は R3"""
import os, sys, math
import numpy as np
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union
from shapely import affinity
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../docs/calc/frame'))
import design as dz

VER = 'v7'
FAN = (dz.FAN_X, 0.0)
HUB_HOLE = 7.0          # ファンのハブ(半径5.35、z 16.0 まで)とモーターを通す穴の半径
HOLE = 2.2              # M2 の通し穴
REAR = -30.0            # 後ろの縁(電池の後ろの端 −21.25 から約9mm。LED を並べる)
NOTCH_X, NOTCH_Y = 32.0, 17.5   # 前の切り欠き(クワガタの腕の間): x ≥ NOTCH_X、|y| ≤ NOTCH_Y(ファンの輪の前の端は x 31.7)
REAR_Y = 26.0           # 後ろの長方形の半幅
WHEEL_CUT = (-8.0, 8.5, 25.0)   # 41T・タイヤの所は基板を置かない: x0 ≤ x ≤ x1 で |y| > y0(41T の一番上は z 13.95)
FRAME_MARGIN = 1.0      # 基板はフレームの外形から 1mm 内側
R_CORNER = 3.0          # 角の丸み(出っ張った角もへこんだ角も)
SCREWS = [(x, sy * y) for (x, y) in dz.MOUNT_SCREWS for sy in (1, -1)]       # マウントの前後の柱
ENC = [(-2.65, 2.65, -21.0, -20.4), (-2.65, 2.65, 20.4, 21.0)]   # エンコーダ基板が通る所(x0, x1, y0, y1)。穴は ENC_Base_Slot(NPTH 1.0 × 5.9mm)
LEDS = [(REAR + 2.5, 4.0 * k) for k in range(-3, 4)]                                # UI の LED 7個(後ろの縁、4mm おき)

# ---- 壁センサ(2026-10-30 からホルダに入れる)。(x, y) はホルダの前の面(光が出る所)の真ん中、角度は光の向き(+x から反時計回り) ----
# 前の2本はタイヤの前の耳で外へ5°、横の2本は前の腕から反対側の壁へ75°(左右で交差)。v6 までは (12, ±30)・(41, ±24) に寝かせていた
SENS = {'FL': ((18.0, 29.0), 5.0), 'FR': ((18.0, -29.0), -5.0), 'R': ((41.0, 18.5), -75.0), 'L': ((41.0, -18.5), 75.0)}
# ホルダ(sensor_holder.py の P と同じ値): 幅、奥行き、ほぞ(幅、奥行き、後ろの面からのずれ)、ほぞの穴のすき間と角の丸み
HOLDER_W, HOLDER_D = 6.0, 4.04
PEG_W, PEG_D, PEG_BACK = 3.0, 3.0, 0.0
SLOT_CLR, SLOT_R = 0.1, 0.5
# 足の穴(φ0.9、パッド φ1.6、ピッチ 2.54)。前の面からの距離: 受光(下の穴)は後ろの面の 0.85mm 後ろ、発光(上の穴)は 3.0mm 後ろ
# (ToraNeko は 0.85・2.8mm で φ1.8。パッドどうしを 0.2mm 以上離すため、発光を少し後ろにし、パッドを φ1.6 にした)
LEAD_ROWS = {'recv': HOLDER_D + 0.85, 'emit': HOLDER_D + 3.0}
LEAD_PITCH, PAD_D = 2.54, 1.6

def _frame(nm):
    (x, y), a = SENS[nm]; a = math.radians(a)
    u = np.array([math.cos(a), math.sin(a)]); n = np.array([-u[1], u[0]])
    return np.array([x, y]), u, n
def _poly(nm, pts):
    o, u, n = _frame(nm)
    return Polygon([tuple(o + u * a + n * b) for a, b in pts])
def holder(nm):
    """ホルダの足元(上から見た形)"""
    w, d = HOLDER_W, HOLDER_D
    return _poly(nm, [(0, -w / 2), (0, w / 2), (-d, w / 2), (-d, -w / 2)])
def slot(nm):
    """ほぞの穴(基板を切り抜く)"""
    c = SLOT_CLR; a0 = -HOLDER_D + PEG_BACK
    p = _poly(nm, [(a0 + PEG_D + c, -PEG_W / 2 - c), (a0 + PEG_D + c, PEG_W / 2 + c), (a0 - c, PEG_W / 2 + c), (a0 - c, -PEG_W / 2 - c)])
    return p.buffer(-SLOT_R, join_style=2).buffer(SLOT_R)
def pads(nm, part=None):
    """足の穴の中心: part = 'emit' / 'recv' / None(両方)"""
    o, u, n = _frame(nm)
    return [tuple(o - u * LEAD_ROWS[k] + n * s * LEAD_PITCH / 2) for k in (['recv', 'emit'] if part is None else [part]) for s in (-1, 1)]
def footprint(nm, m=1.0):
    """基板が要る所: ホルダと足のパッドを囲んで m だけ広げる"""
    return unary_union([holder(nm)] + [Point(p).buffer(PAD_D / 2) for p in pads(nm)]).convex_hull.buffer(m, join_style=1)

def outline():
    x0, x1, y0 = WHEEL_CUT
    rear = box(REAR, -REAR_Y, x1, REAR_Y)
    front = unary_union([box(x0, -REAR_Y, x1, REAR_Y)] + [footprint(k) for k in SENS]
                        + [Point(47.0, sy * 24.0).buffer(0.5) for sy in (1, -1)]).convex_hull     # 前の腕の先(x 47.5)
    o = unary_union([rear, front]).intersection(dz.outline(0).buffer(-FRAME_MARGIN, join_style=2))
    o = o.difference(box(x0, y0, x1, 60)).difference(box(x0, -60, x1, -y0))                    # 41T・タイヤ
    o = o.difference(box(NOTCH_X, -NOTCH_Y, 80.0, NOTCH_Y))                                    # クワガタの腕の間
    o = o.buffer(R_CORNER, join_style=1).buffer(-R_CORNER, join_style=1)                       # へこんだ角
    o = o.buffer(-R_CORNER, join_style=1).buffer(R_CORNER, join_style=1)                       # 出っ張った角
    o = o.difference(box(x0, y0, x1 - 0.5, 60)).difference(box(x0, -60, x1 - 0.5, -y0))        # 丸めで 41T の上にはみ出た分を戻す
    return o.difference(Point(FAN).buffer(HUB_HOLE, 64))

def board():
    """外形からねじの穴とホルダのほぞの穴を抜いたもの"""
    return outline().difference(unary_union([Point(p).buffer(HOLE / 2, 24) for p in SCREWS] + [slot(k) for k in SENS]))

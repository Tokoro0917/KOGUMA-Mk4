"""基板の外形(vehicle.py と pcb_dxf.py・pcb_modes.py で共通)。座標は機体と同じ(原点は車軸の中心、+x が前、mm)
v5(2026-10-28): ファンの上は覆い、モーターのハブのまわり(半径 HUB_HOLE)だけ開ける。前の腕どうしもつなげる。
                後ろはフレームの後ろの端の近く(x −46)まで広げ、UI の LED 7個を並べる
v6(2026-10-29): 大きすぎたので、前はクワガタの形(左右の腕の間を x NOTCH_X より前で開ける)に戻し、後ろは x REAR まで
v7(2026-10-30): 形をすっきりさせ、壁センサをホルダ(ToraNeko.Mk3 と同じ形、`mechanical/sensor_holder/`)に入れる。
                後ろは長方形、前は「後ろの長方形 + 4つのセンサ(ホルダと足の穴)」を囲む凸の形を、フレームの 1mm 内側で切る。
                車輪(41T・タイヤ)の所と、前の腕の間だけをへこませる。角は R3
v8(2026-10-30): v7 の形がよくないので作り直した(4つの案から選んだ)。外形はフレームと平行な八角形(フレームの 1.5mm 内側)、
                前の切り欠きは大きな円弧(中心 (51, 0)、半径 19。ToraNeko.Mk3 の前後の円弧と同じ考え方)、車輪の所は四角く切る。
                へこんだ角 R3、出っ張った角 R5。横の壁センサを (41, ±18.5) から (40, ±18) へ
v9(2026-10-30): もっと削った。フレームから 3mm 内側、前の円弧を半径 20 に、後ろの横は |y| 26.5 でまっすぐ(車輪の所まで)。
                約 450mm² 減(−0.5g)。壁センサを形に収まる所へ: 前 (18, ±29) → (21, ±27)、横 (40, ±18) → (37.5, ±17.5)
v10(2026-10-30): 前の腕(クワガタ)を、壁センサのホルダの所だけ残す角にした。後ろの長方形とファンのまわりの円(半径 14)を芯にし、
                 4つのセンサ(ホルダと足の穴を 1mm 広げた形)を、ファンの中心へ向かう幅 9mm の首で芯につなぎ、R7 で丸める。
                 横の壁センサを (37.5, ±17.5) → (37.5, ±14) へ内側に(光はファンの輪の外側から 2mm 以上離す)。v9 から約 210mm² 減
v11(2026-10-30): 振動対策。v10 の角は先のセンサ(0.39g)が重く、1次が 136Hz(基板 0.6mm)。面積を増やしてよいので、
                 左右それぞれ前のセンサ(FL・FR)と横のセンサ(R・L)の間を埋め(横の縁はまっすぐ)、前の切り欠きは小さな円弧
                 (中心 (55, 0)、半径 18)にした。1次 160Hz、約 3790mm²(v10 は 3233mm²、+0.6g)。前の切り欠きも埋めると
                 先が重くなって 145Hz に下がる
v12(2026-10-30): 軽くするため中をくり抜いた(4つの案から選んだ)。電池の下に窓(x −18.25〜−1.75、|y| ≤ 13、角 R3)、
                 前と横のセンサの間にポケット(縁・ファンのまわり・センサのまわりに 4.5mm 残す、角 R2)。
                 約 3020mm²(v11 から −770mm²、−0.85g)、1次 145Hz(v11 は 160Hz、v10 は 136Hz)。電池の下は抜いても振動はほぼ変わらない。
                 前は縁を 2.5mm にすると 80Hz、ファンからセンサへの梁(トラス)だけ残すと 137Hz
v13(2026-10-30): 電池の下にはマイコンを置くので、電池の下の窓はやめた(前と横のセンサの間のポケットだけ)
v14(2026-10-30): 後ろも前と同じように削った(3つの案から選んだ)。x < 4 は、電池の下(マイコン、|y| ≤ 17)、後ろの LED の列(|y| ≤ 15)、
                 柱のまわり(半径 4 の耳)、エンコーダ基板の穴のまわり(2mm)だけ残し、へこんだ角 R3。
                 約 3050mm²(v13 から −0.44g)。1次 147Hz は変わらない(前のセンサで決まる)。3次(電池)は 303 → 280Hz"""
import os, sys, math
import numpy as np
from shapely.geometry import Polygon, Point, box, LineString
from shapely.ops import unary_union
from shapely import affinity
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../docs/calc/frame'))
import design as dz

VER = 'v14'
FAN = (dz.FAN_X, 0.0)
HUB_HOLE = 7.0          # ファンのハブ(半径5.35、z 16.0 まで)とモーターを通す穴の半径
HOLE = 2.2              # M2 の通し穴
REAR, FRONT = -30.0, 47.5        # 後ろの縁(電池の後ろの端 −21.25 から約9mm。LED を並べる)、前の縁
FRAME_MARGIN = 3.0      # 外形はフレームの外形と平行に 3mm 内側(v8 は 1.5mm)
NOTCH_C, NOTCH_R = (51.0, 0.0), 20.0   # 前の切り欠き(クワガタの腕の間)の円弧。x 31 まで(ファンの輪の前の端は x 31.7。v8 は半径 19)
REAR_Y = 26.5           # 後ろ(車輪より後ろ)の横の縁 |y|
WHEEL_CUT = (-8.0, 8.5, 25.0)   # 41T・タイヤの所は基板を置かない: x0 ≤ x ≤ x1 で |y| > y0(41T の一番上は z 13.95)
R_IN, R_OUT = 3.0, 5.0  # へこんだ角、出っ張った角の丸み(v8・v9)
CORE_FAN_R = 14.0       # v10: 芯にするファンのまわりの円の半径
NECK_W, R_HORN = 9.0, 7.0   # v10: センサと芯をつなぐ首の幅、角のつけ根の丸み(v11 も R_HORN でへこんだ角を丸める)
NOTCH11_C, NOTCH11_R = (55.0, 0.0), 18.0   # v11: 前の切り欠きの円弧
BAT = (-21.25, 1.25, 16.0)    # 電池(x0, x1, |y|)
BAT_WIN_M, BAT_WIN_R = 3.0, 3.0           # v12: 電池の下の窓(電池の縁から内側へ 3mm、角 R3)
BAT_WIN = False                           # v13: 電池の下にはマイコンを置くので窓は開けない
REAR_SIDE, REAR_LED, POST_BOSS, ENC_RIM, R_REAR, REAR_X = 17.0, 15.0, 4.0, 2.0, 3.0, 4.0   # v14: 後ろ(x < REAR_X)に残す所: 電池の下 |y|、LED の列 |y|、柱の耳の半径、エンコーダの穴のまわり、へこんだ角
POCKET_RIM, POCKET_R = 4.5, 2.0           # v12: 前と横のセンサの間のポケット(縁などに残す幅、角の丸み)
SCREWS = [(x, sy * y) for (x, y) in dz.MOUNT_SCREWS for sy in (1, -1)]       # マウントの前後の柱
ENC = [(-2.65, 2.65, -21.0, -20.4), (-2.65, 2.65, 20.4, 21.0)]   # エンコーダ基板が通る所(x0, x1, y0, y1)。穴は ENC_Base_Slot(NPTH 1.0 × 5.9mm)
LEDS = [(REAR + 2.5, 4.0 * k) for k in range(-3, 4)]                                # UI の LED 7個(後ろの縁、4mm おき)

# ---- 壁センサ(2026-10-30 からホルダに入れ、基板の裏(下)に付ける)。(x, y) はホルダの前の面(光が出る所)の真ん中、角度は光の向き(+x から反時計回り) ----
# ホルダは sensor_holder.py(v2、高さ 9.9mm)。基板の下面 z 13.6 から下の端 z 3.7。光の高さは受光 z 10.4、発光 z 6.0
HOLDER_SIDE = 'bottom'
# 前の2本はタイヤの前の耳の一番外で外へ7°(斜めのとき柱にかかる)、横の2本は前の角から反対側へ63.0°(左右で交差。区画の中心で柱の前半分を見る。2026-10-30 までは 75° で横の壁を見ていた)。v6 までは (12, ±30)・(41, ±24) に寝かせていた
SENS = {'FL': ((17.0, 30.75), 7.0), 'FR': ((17.0, -30.75), -7.0), 'R': ((42.0, 16.0), -63.0), 'L': ((42.0, -16.0), 63.0)}   # v10。前はフレームから出さずに一番外((17, ±30.75)、ホルダの外の角はフレームの 0.5mm 内側)、外へ 7°(斜めの直線の 82% の位置で柱にかかる。MK3 は (22, ±27) 10° で 76%。2026-10-30)。横は区画の中心で柱の中心より前(柱の前半分の真ん中 x 93)を見る。角度を小さくするため前へ出して (42, ±16)、真横から 27.0°(前から 63.0°。(37.5, ±14) では 29.5°)。前の壁があれば前の壁の y ∓66 に当たる(2026-10-30。それまでは横の壁を見る 75°)。v9 は R・L が (37.5, ±17.5)。前は (18, ±28) だとマウントの腕(ファンの台の継ぎ目)と 0.17mm なので前へ。v8 は (18, ±29)・(40, ±18)、v7 は R・L が (41, ±18.5)
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

def outline_v9():
    """v9 の形(フレームと平行な八角形、前は円弧、後ろの横はまっすぐ)"""
    x0, x1, y0 = WHEEL_CUT
    o = dz.outline(0).buffer(-FRAME_MARGIN, join_style=2).intersection(box(REAR, -50, FRONT, 50))   # フレームと平行な八角形
    o = o.difference(box(-50, REAR_Y, x0, 60)).difference(box(-50, -60, x0, -REAR_Y))             # 後ろの横をまっすぐに
    o = o.difference(Point(NOTCH_C).buffer(NOTCH_R, 256))                                         # 前の円弧の切り欠き
    o = o.difference(box(x0, y0, x1, 60)).difference(box(x0, -60, x1, -y0))                    # 41T・タイヤ
    o = o.buffer(R_IN, join_style=1).buffer(-R_IN, join_style=1)                               # へこんだ角
    o = o.buffer(-R_OUT, join_style=1).buffer(R_OUT, join_style=1)                             # 出っ張った角
    o = o.difference(box(x0, y0, x1 - 0.3, 60)).difference(box(x0, -60, x1 - 0.3, -y0))        # 丸めで 41T の上にはみ出た分を戻す
    return o.difference(Point(FAN).buffer(HUB_HOLE, 64))

def outline_v10():
    """v10: 芯(後ろの長方形 + ファンのまわりの円)に、4つのセンサの所を首でつなぐ(クワガタの角)"""
    x0, x1, y0 = WHEEL_CUT
    lim = dz.outline(0).buffer(-FRAME_MARGIN, join_style=2)
    core = unary_union([box(REAR, -REAR_Y, x0, REAR_Y), box(x0, -y0, 12.5, y0), Point(FAN).buffer(CORE_FAN_R, 128)])
    pods = [footprint(k, 1.0) for k in SENS]
    necks = [LineString([tuple(holder(k).centroid.coords[0]), FAN]).buffer(NECK_W / 2) for k in SENS]
    o = unary_union([core] + pods + necks).intersection(lim)
    o = o.buffer(R_HORN, join_style=1).buffer(-R_HORN, join_style=1)                           # 角のつけ根(へこんだ角)
    o = o.buffer(-2.0, join_style=1).buffer(2.0, join_style=1)                                 # 出っ張った角
    o = unary_union([o] + [p.intersection(dz.outline(0).buffer(-0.3, join_style=2)) for p in pods])     # センサの所はフレームの 0.3mm 内側まで
    o = o.buffer(1.0, join_style=1).buffer(-1.0, join_style=1)
    o = o.difference(box(x0, y0, x1 - 0.3, 60)).difference(box(x0, -60, x1 - 0.3, -y0))        # 41T・タイヤ
    return o.difference(Point(FAN).buffer(HUB_HOLE, 64))

def outline_v11():
    """v11: 芯(後ろの長方形 + ファンのまわりの円)と、左右それぞれ前と横のセンサを囲む形。前は小さな円弧で切る"""
    x0, x1, y0 = WHEEL_CUT
    lim = dz.outline(0).buffer(-FRAME_MARGIN, join_style=2)
    core = unary_union([box(REAR, -REAR_Y, x0, REAR_Y), box(x0, -y0, 12.5, y0), Point(FAN).buffer(CORE_FAN_R, 128)])
    pods = [footprint(k, 1.0) for k in SENS]
    fan = Point(FAN).buffer(CORE_FAN_R)
    sides = [unary_union([footprint(a, 1.0), footprint(b, 1.0), fan]).convex_hull.intersection(box(0, 0, 60, 60) if a == 'FL' else box(0, -60, 60, 0))
             for a, b in (('FL', 'R'), ('FR', 'L'))]                                              # 前と横のセンサの間を埋める
    front = unary_union([footprint('R', 1.0), footprint('L', 1.0)]).convex_hull.difference(Point(NOTCH11_C).buffer(NOTCH11_R, 128))
    o = unary_union([core, front] + sides).intersection(lim)
    o = o.buffer(R_HORN, join_style=1).buffer(-R_HORN, join_style=1)                           # へこんだ角
    o = o.buffer(-2.0, join_style=1).buffer(2.0, join_style=1)                                 # 出っ張った角
    o = unary_union([o] + [p.intersection(dz.outline(0).buffer(-0.3, join_style=2)) for p in pods])     # センサの所はフレームの 0.3mm 内側まで
    o = o.buffer(1.0, join_style=1).buffer(-1.0, join_style=1)
    o = o.difference(box(x0, y0, x1 - 0.3, 60)).difference(box(x0, -60, x1 - 0.3, -y0))        # 41T・タイヤ
    return o.difference(Point(FAN).buffer(HUB_HOLE, 64))

def pockets(o, bat_win=None):
    """くり抜き: 前と横のセンサの間のポケットと、bat_win なら電池の下の窓(v12)"""
    m, r, w = BAT_WIN_M, BAT_WIN_R, POCKET_RIM
    win = box(BAT[0] + m, -BAT[2] + m, BAT[1] - m, BAT[2] - m).buffer(-r).buffer(r)
    keep = unary_union([Point(FAN).buffer(CORE_FAN_R + w), box(-60, -60, 12.5 + w, 60)] + [footprint(k, w) for k in SENS])
    h = o.buffer(-w).difference(keep).buffer(-POCKET_R, join_style=1).buffer(POCKET_R, join_style=1)
    return unary_union(([win] if (BAT_WIN if bat_win is None else bat_win) else []) + [g for g in getattr(h, 'geoms', [h]) if g.area > 15])

def outline_v12():
    """v12: v11 の形から、電池の下の窓と前と横のセンサの間のポケットをくり抜く"""
    o = outline_v11()
    return o.difference(pockets(o, True))

def outline_v13():
    """v13: v11 の形から、前と横のセンサの間のポケットをくり抜く(電池の下は抜かない)"""
    o = outline_v11()
    return o.difference(pockets(o))

def outline():
    """v14: v13 の後ろ(x < REAR_X)を、電池の下・LED の列・柱の耳・エンコーダの穴のまわりだけ残して削る"""
    x0, x1, y0 = WHEEL_CUT
    v11 = outline_v11()
    keep = unary_union([box(BAT[0] - 1, -REAR_SIDE, BAT[1] + 1, REAR_SIDE), box(REAR, -REAR_LED, BAT[0] + 1.25, REAR_LED)]
                       + [Point(p).buffer(POST_BOSS) for p in SCREWS]
                       + [box(a - ENC_RIM, c - ENC_RIM, b + ENC_RIM, d + ENC_RIM) for a, b, c, d in ENC])
    o = unary_union([v11.difference(box(-60, -60, REAR_X, 60)), keep.intersection(v11)])
    o = o.buffer(R_REAR, join_style=1).buffer(-R_REAR, join_style=1).buffer(-2.0, join_style=1).buffer(2.0, join_style=1)
    o = o.difference(box(x0, y0, x1 - 0.3, 60)).difference(box(x0, -60, x1 - 0.3, -y0))        # 41T・タイヤ
    return o.difference(pockets(o)).difference(Point(FAN).buffer(HUB_HOLE, 64))

def board():
    """外形からねじの穴とホルダのほぞの穴を抜いたもの"""
    return outline().difference(unary_union([Point(p).buffer(HOLE / 2, 24) for p in SCREWS] + [slot(k) for k in SENS]))

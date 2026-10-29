"""MK4 の機体全体(仮の案 v0、2026-10-18)
フレーム v4.4、モーターマウント(後ろの耳に基板を受ける柱を足した案)、足回り(ToraNeko.Mk3 の部品)、
吸引ファン(ケース・羽根・モーター・押さえ)、基板、電池、壁センサ、滑り板、スカート、ねじを並べ、
ぶつかり・質量・重心・慣性モーメントを計算して、STEP と図を出す。
座標 [mm]: x 前(+)、y 左(+)、z 上(床 = 0)。車軸 (0, y, 7.5)。
使い方: python3 vehicle.py [出力のフォルダ(既定はこのフォルダ)] [版(v0 / v1、既定は v1)]
  v0: 最初の案(基板0.8mm、鉄のねじ6組、ファンの押さえあり)
  v1: 軽くした案(基板0.6mm、フレームの下の4本だけ鉄の低頭、ほかはナイロン、ファンのケースを薄く、押さえなし)
"""
import os, sys, json, math, itertools
import numpy as np
import cadquery as cq
from shapely.geometry import Point, Polygon, box as sbox
from shapely.ops import unary_union
from shapely import affinity
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '../../docs/calc/frame'))
sys.path.insert(0, os.path.join(HERE, '../motor_mount'))
import design as dz
import mount as mm

OUT = sys.argv[1] if len(sys.argv) > 1 else HERE
V = sys.argv[2] if len(sys.argv) > 2 else 'v4'
# ねじの寸法 [mm]: d 径、dk/k 頭の径・高さ(なべ。フレームの下の M3 は低頭)、s/m ナットの二面幅・厚さ、
# hole 穴、boss 柱・耳の半径(ナットのまわりに0.8mm)、pocket/depth ナットの穴の二面幅・深さ、Lp 基板を留めるねじの長さ
SPEC = {'M3':   dict(d=3.0, dk=5.5, k=1.5, s=5.5, m=2.4, hole=3.2, boss=3.7, pocket=5.7, depth=2.5, Lp=5.0),
        'M2':   dict(d=2.0, dk=3.8, k=1.1, s=4.0, m=1.6, hole=2.2, boss=3.1, pocket=4.2, depth=1.7, Lp=4.0, tap=1.6),   # 2026-10-20: 通し穴 2.3 → 2.2、タップの下穴 1.6
        'M1.6': dict(d=1.6, dk=3.2, k=1.3, s=3.2, m=1.3, hole=1.8, boss=2.7, pocket=3.4, depth=1.4, Lp=3.0),
        'M1.4': dict(d=1.4, dk=2.5, k=0.9, s=3.0, m=1.2, hole=1.7, boss=2.6, pocket=3.2, depth=1.3, Lp=3.0)}
CFG = dict(v0=dict(pcb_t=0.8, wall=0.8, top=0.8, clamp=True, screws='steel', boss_r=3.0, size='M3'),
           v1=dict(pcb_t=0.6, wall=0.6, top=0.6, clamp=False, screws='mixed', boss_r=3.4, size='M3'),
           v2=dict(pcb_t=0.6, wall=0.6, top=0.6, clamp=False, screws='m2mix', size='M2'),
           v3=dict(pcb_t=0.6, wall=0.6, top=0.6, clamp=False, screws='m2mix', size='M2', fan='volute'),
           v4=dict(pcb_t=0.6, wall=0.6, top=0.6, clamp=False, screws='m2mix', size='M2', fan='spider', tap=True),   # tap: 印刷の部品にねじ山を切る(ナットなし、2026-10-20)
           v2_m14=dict(pcb_t=0.6, wall=0.6, top=0.6, clamp=False, screws='small', size='M1.4'),
           v2_m16=dict(pcb_t=0.6, wall=0.6, top=0.6, clamp=False, screws='small', size='M1.6'),
           v2_m2=dict(pcb_t=0.6, wall=0.6, top=0.6, clamp=False, screws='small', size='M2'))[V]
SC = SPEC[CFG['size']]
if CFG['screws'] in ('small', 'm2mix'):
    CFG['boss_r'] = SC['boss']
TAP = CFG.get('tap', False)
FAST = os.environ.get('FAST') == '1'      # 重さだけ計算する(ぶつかり・STEP・図を省く)

# ---------------- 高さ(床から) ----------------
Z_FB, Z_FT = 2.0, 3.0        # フレームの下面・上面
Z_PC = 3.2                   # 吸引する面のシート(塩ビ 0.2mm、2026-10-19 にポリカーボネート 0.2mm から)の上面
Z_PCB = 13.6                 # 基板の下面(マウントのモーターの筒の上 13.36 から 0.24)
T_PCB = CFG['pcb_t']         # 基板の厚さ
Z_PCBT = Z_PCB + T_PCB
FAN = (dz.FAN_X, 0.0)        # ファンの中心
BAT = dict(x=-10.0 if CFG.get('fan') == 'spider' else -5.0, lx=22.5, ly=32.0, lz=14.0)   # 電池: 1S 180mAh(7.5 × 32 × 14)× 3 を立てて並べる(MK3 の STEP の寸法)。v4 はファンの上の穴を避けて 5mm 後ろへ

# ---------------- 質量・密度 ----------------
RHO = dict(carbon=1.55e-3, pc=1.4e-3, resin=1.2e-3, fr4=1.85e-3, steel=7.85e-3, ndfeb=7.5e-3, rubber=1.2e-3,
           pom=1.42e-3, brass=8.5e-3, ptfe=2.2e-3, film=1.4e-3, nylon=1.14e-3,
           titanium=4.43e-3, aluminum=2.8e-3, pa12=1.01e-3, skid=0.6e-3)   # g/mm³(skid: カグスベール。樹脂0.5mm + コルク1mm の平均の見積もり)
FIXED = dict(motor=5.3, fan_motor=5.3, battery=14.5, pcb_parts=2.5, sensor=0.1, wiring=0.6)   # g

def ycyl(r, y0, y1, x, z):
    return mm.ycyl(r, y0, y1, x, z)

SKID_R, SKID_T = 2.5, 1.5     # 滑り板(カグスベール)の半径、厚さ [mm]

def zcyl(r, z0, z1, x=0.0, y=0.0):
    return cq.Workplane().center(x, y).circle(r).extrude(z1 - z0).translate((0, 0, z0))

def poly_solid(poly, z0, z1):
    out = []
    for p in getattr(poly, 'geoms', [poly]):
        if p.area < 0.5:
            continue
        wp = cq.Workplane().polyline(list(p.exterior.coords)[:-1]).close().extrude(z1 - z0)
        for r in p.interiors:
            wp = wp.cut(cq.Workplane().polyline(list(r.coords)[:-1]).close().extrude(z1 - z0))
        out.append(wp.translate((0, 0, z0)).val())
    return out[0] if len(out) == 1 else cq.Compound.makeCompound(out)

def mirror(s):
    return s.mirror('XZ')

parts = {}      # 名前 -> (形, 材料 or 固定の質量の名前)
def add(name, shape, mat):
    if isinstance(shape, cq.Workplane):
        shape = shape.val()
    parts[name] = (shape, mat)

# ---------------- フレーム ----------------
FP = json.load(open(os.path.join(HERE, '../../docs/calc/frame/results/final_params.json')))
g = dz.build(**FP)
screws_mount = dz.holes() if CFG.get('fan') in ('volute', 'spider') else [(x, sy * y) for (x, y) in dz.MOUNT_SCREWS for sy in (1, -1)]
plate = g['carbon'].difference(unary_union([Point(c).buffer(SC['hole'] / 2, 32) for c in screws_mount]))
add('frame', poly_solid(plate, Z_FB, Z_FT), 'carbon')
sheet = g['suction'].difference(Point(dz.FAN_X, 0).buffer(dz.FAN_R, 64))
add('pc_sheet', poly_solid(sheet, Z_FT, Z_PC), 'pc')
skirt = g['suction'].difference(g['suction'].buffer(-0.1, join_style=2))           # 0.1mm のフィルム、床から 0.5mm
add('skirt', poly_solid(skirt, 0.5, Z_FB), 'film')
for sx in (1, -1):
    # 滑り板: カグスベール(フリーサイズ、約1.5mm = フッ素加工の樹脂0.5 + コルク1.0)をフレームの下面に直接貼る(2026-10-19)。
    # φ5 に切る。床とのすき間は 2.0 − 1.5 = 0.5mm。加速・減速で機体が0.64°傾いて片方が床に着く(スカートの端は床から0.17mm)
    dome = zcyl(SKID_R, Z_FB - SKID_T, Z_FB, sx * 45.0, 0.0)
    add(f'skid_{"F" if sx > 0 else "R"}', dome, 'skid')

# ---------------- 足回り(右を作って左に写す) ----------------
P2 = (dict(mm.P_V1, pcb_post=Z_PCB) if CFG['screws'] == 'steel' else dict(mm.P_V1, pcb_post=Z_PCB, post_r=3.7, post_nut=True)
      if CFG['size'] == 'M3' else
      dict(mm.P_V1, pcb_post=Z_PCB, post_r=SC['boss'], post_nut=True, boss_r=SC['boss'], nut_af=SC['pocket'],
           nut_depth=SC['depth'], hole_d=SC['hole']))
if TAP:
    P2 = dict(P2, hole_d=SC['tap'], tap=True)
if CFG.get('fan') == 'spider':      # 2026-10-20: 前の耳から腕を伸ばしてファンの台を持ち、前の耳の上にも基板の柱(mount.py v5)
    _jx, _jy = dz.FAN_JOINTS[0]
    P2 = dict(P2, fan_joint=(_jx, -abs(_jy)), joint_r=mm.P['joint_r'], joint_z=mm.P['joint_z'], arm_w=mm.P['arm_w'], pcb_post_front=True)
(xr_, yr_), (xf_, yf_) = dz.MOUNT_SCREWS
P2 = dict(P2, screw_front=(xf_, -yf_), screw_rear=(xr_, -yr_))     # ねじの位置はフレームに合わせる(右側なので y は負)
mx, mz = mm.motor_center(P2)
right = {}
right['mount'] = (mm.build(P2).val(), 'resin')
tn = cq.importers.importStep(os.path.join(HERE, '../motor_mount/tn_drive_mk4_right.step')).val().Solids()
for s in tn:
    bb = s.BoundingBox()
    if abs(bb.zmax - 14.5) < 0.05:              # ToraNeko のタイヤ(φ14)は使わない
        continue
    if bb.ymin > -21.1 and bb.ymax < -20.4:
        right['enc_board'] = (s.translate(cq.Vector(0, 0, 0.11)), 'fr4'); continue
    if bb.ymin > -22.3 and bb.ymax < -20.9:
        right['as5047p'] = (s.translate(cq.Vector(0, 0, 0.11)), 'resin'); continue
    if abs(bb.zmax - 13.25) < 0.05:
        right['wheel'] = (s, 'resin'); continue
    if abs(bb.zmax - 13.95) < 0.05:
        right['spur41'] = (s, 'pom'); continue
    if abs(bb.ymax + 23.7) < 0.05 and abs(bb.ymin + 29.7) < 0.05:
        right['pin'] = (s, 'steel'); continue
    if abs(bb.ymin + 23.7) < 0.05:
        right['magnet'] = (s, 'ndfeb'); continue
    if abs((bb.xmax - bb.xmin) - 7.2) < 0.05:
        right['brg_out' if bb.ymin < -26 else 'brg_in'] = (s, 'steel'); continue
right['tire'] = (ycyl(7.5, -31.8, -28.3, 0, 7.5).cut(ycyl(5.75, -31.9, -28.2, 0, 7.5)).val(), 'rubber')
right['motor'] = (ycyl(4.3, P2['motor_face'], P2['motor_face'] + 20.0, mx, mz).union(
    ycyl(1.2, P2['motor_face'] - 0.3, P2['motor_face'], mx, mz)).val(), 'motor')
right['shaft'] = (ycyl(0.6, P2['motor_face'] - 0.3, -27.9, mx, mz).val(), 'steel')
right['pinion'] = (ycyl(2.25, -25.9, -27.9, mx, mz).cut(ycyl(0.6, -25.8, -28.0, mx, mz)).val(), 'brass')
for k, (s, m) in right.items():
    add(k + '_R', s, m)
    add(k + '_L', mirror(s), m)

# ---------------- 吸引ファン ----------------
fx, fy = FAN
VOLUTE = CFG.get('fan') == 'volute'
SPIDER = CFG.get('fan') == 'spider'
FRAME_FAN = VOLUTE or SPIDER          # ファンをフレームにねじで留める(v3、v4)
if not FRAME_FAN:          # v0〜v2: 丸いケース(左右に窓)、ポリカーボネートに接着
    R_OUT = 16.0; R_IN = R_OUT - CFG['wall']   # ケースの壁
    Z_TOP1 = 9.6; Z_TOP0 = Z_TOP1 - CFG['top']   # ケースの天井(この上にモーターの前の面が載る)
    BOSS_Y, BOSS_R = 12.5, CFG['boss_r']   # 基板(と押さえ)のねじの柱
    case = zcyl(R_OUT, Z_PC, Z_TOP1, fx, fy).cut(zcyl(R_IN, Z_PC - 0.1, Z_TOP0, fx, fy))
    case = case.union(zcyl(R_IN, Z_PC, Z_PC + 0.6, fx, fy).cut(zcyl(13.0, Z_PC - 0.1, Z_PC + 0.7, fx, fy)))   # 接着の面(内側のつば)
    for ang in (90, -90):             # 吐き出しの窓(左右)
        a = math.radians(ang)
        win = (cq.Workplane().box(8.0, 4.0, 4.0).translate((fx + 15.6 * math.cos(a), fy + 15.6 * math.sin(a), 5.9))
               .rotate((fx + 15.6 * math.cos(a), fy + 15.6 * math.sin(a), 0), (fx + 15.6 * math.cos(a), fy + 15.6 * math.sin(a), 1), ang - 90))
        case = case.cut(win)
    case = case.union(zcyl(4.35 + CFG['wall'], Z_TOP1, Z_PCB, fx, fy))       # モーターの筒(v1 はモーターを接着)
    for sy in (1, -1):
        case = case.union(zcyl(BOSS_R, Z_TOP1, Z_PCB, fx, sy * BOSS_Y))      # 押さえのねじの柱
    case = case.cut(zcyl(4.35, Z_TOP1, Z_PCB + 1, fx, fy))                  # モーターの穴
    case = case.cut(zcyl(1.5, Z_TOP0 - 0.1, Z_TOP1 + 0.1, fx, fy))          # 軸と軸受けの出っ張りの穴
    for sy in (1, -1):
        case = case.cut(zcyl(SC['hole'] / 2, Z_TOP0 - 0.1, Z_PCB + 1, fx, sy * BOSS_Y))
        nut = (cq.Workplane().center(fx, sy * BOSS_Y).polygon(6, SC['pocket'] / math.cos(math.pi / 6)).extrude(SC['depth'])
               .translate((0, 0, Z_PCB - SC['depth'])))
        slot = cq.Workplane().box(4.0, SC['pocket'], SC['depth'], centered=(False, True, False)).translate((fx, sy * BOSS_Y, Z_PCB - SC['depth']))
        case = case.cut(nut).cut(slot)                                       # ナットは横から入れる
    add('fan_case', case, 'resin')
    PCB_FAN_POSTS = [(fx, sy * BOSS_Y) for sy in (1, -1)]
elif SPIDER:            # v4: 羽根を輪で囲い、腕でモーターを真ん中に持つ(2026-10-19。2026-10-20 から、ハブと輪を斜め45°の4本の腕でつなぎ、輪から耳を出してマウントの腕に留める)。フレームにねじ3本で留める。上へ吐き出す
    BOSS_R = CFG['boss_r']
    W = 1.0                                   # 輪の壁(2026-10-20 に 0.6 から。前の耳のねじをやめた分、輪を太くして台を硬くする)
    R_RING, Z_RING = 16.5, 10.0               # 輪の内側の半径(囲いの内径 φ33、羽根 φ32 とのすき間 0.5mm。2026-10-20)、輪の上
    Z_ARM0, Z_ARM1, ARM_W = 8.8, 10.8, 3.0    # 腕(羽根の上 8.0 から 0.8 上)
    Z_TOP1 = 9.4; Z_TOP0 = Z_ARM0             # モーターの前の面を受けるハブの底
    Z_COL = 16.0                              # ハブの上(2026-10-20: 圧入にして 13.2 から伸ばした。モーターを 6.6mm つかむ)
    BORE_D = 8.6                              # モーターの穴(モーター φ8.6 を圧入。モーターマウントの軸受の穴と同じ考え方で寸法どおり)
    # 基板はモーターマウントの前後の耳の上の柱で受ける(2026-10-20。ファンの台の左右の柱はやめた)
    PCB_FAN_POSTS = [(dz.MOUNT_SCREWS[1][0], sy * dz.MOUNT_SCREWS[1][1]) for sy in (1, -1)]
    case = zcyl(R_RING + W, Z_PC, Z_RING, fx, fy).cut(zcyl(R_RING, Z_PC - 0.1, Z_RING + 0.1, fx, fy))   # 輪(囲い)
    ring_foot = Point(fx, fy).buffer(R_RING + W, 128).difference(Point(fx, fy).buffer(R_RING, 128)).difference(g['suction'])
    if ring_foot.area > 0.05:            # 塩ビのない所(吸引する面の外)は、輪をフレームの上面(3.0)まで下げてすき間をふさぐ
        case = case.union(cq.Workplane().add(poly_solid(ring_foot, Z_FT, Z_PC + 0.05)))
    for ang in (45, 135, 225, 315):      # モーターの受け(ハブ)を輪につなぐ腕4本、斜め45°で均等(2026-10-20。それまではハブから継ぎ目へ2本と前へ1本)
        case = case.union(cq.Workplane().box(R_RING + W / 2, ARM_W, Z_ARM1 - Z_ARM0, centered=(False, True, False))
                          .rotate((0, 0, 0), (0, 0, 1), ang).translate((fx, fy, Z_ARM0)))
    case = case.union(zcyl(5.35, Z_TOP0, Z_COL, fx, fy))                                              # ハブ
    for (px, py) in dz.FAN_JOINTS:       # マウントの腕に載せる耳(上から M2 で留める)。輪から耳へ短い腕を出す(2026-10-20)
        L = math.hypot(px - fx, py - fy); ang = math.degrees(math.atan2(py - fy, px - fx))
        case = case.union(cq.Workplane().box(L - R_RING, ARM_W, Z_ARM1 - Z_ARM0, centered=(False, True, False))
                          .translate((R_RING, 0, 0)).rotate((0, 0, 0), (0, 0, 1), ang).translate((fx, fy, Z_ARM0)))
        case = case.union(zcyl(mm.P['joint_r'], Z_ARM0, Z_ARM1, px, py))
        case = case.cut(zcyl(SC['hole'] / 2, Z_ARM0 - 0.1, Z_ARM1 + 0.1, px, py))
    for (px, py) in dz.FAN_SCREWS:
        L = math.hypot(px - fx, py - fy); ang = math.degrees(math.atan2(py - fy, px - fx))
        arm = (cq.Workplane().box(L, ARM_W, Z_ARM1 - Z_ARM0, centered=(False, True, False))
               .rotate((0, 0, 0), (0, 0, 1), ang).translate((fx, fy, Z_ARM0)))
        case = case.union(arm)
        top = Z_PCB if (px, py) in PCB_FAN_POSTS else Z_ARM1
        case = case.union(zcyl(BOSS_R, Z_PC, top, px, py))
        foot = Point(px, py).buffer(BOSS_R, 48).difference(g['suction'])
        if foot.area > 0.5:
            case = case.union(cq.Workplane().add(poly_solid(foot, Z_FT, Z_PC + 0.05)))
    # モーターの筒: 上から圧入し、前の面をハブの底に当てる(2026-10-20。それまでは割りを入れて横のねじで締めていた)
    case = case.cut(zcyl(BORE_D / 2, Z_TOP1, Z_COL + 1, fx, fy))
    case = case.cut(zcyl(1.5, Z_TOP0 - 0.1, Z_TOP1 + 0.1, fx, fy))
    def nut_pocket(px, py, z_top, out):
        hexp = cq.Workplane().center(px, py).polygon(6, SC['pocket'] / math.cos(math.pi / 6)).extrude(SC['depth']).translate((0, 0, z_top - SC['depth']))
        ux, uy = out
        slot = cq.Workplane().box(5.0 if ux else SC['pocket'], 5.0 if uy else SC['pocket'], SC['depth'], centered=(True, True, False)) \
            .translate((px + 2.5 * ux, py + 2.5 * uy, z_top - SC['depth']))
        return hexp.union(slot)
    for (px, py) in dz.FAN_SCREWS:
        case = case.cut(zcyl((SC['tap'] if TAP else SC['hole']) / 2, Z_FT - 0.2, Z_PCB + 1, px, py))
        if TAP:
            continue          # ねじ山を切る(下からフレームのねじ、柱の上から基板のねじ)
        out = (1, 0) if abs(py) <= 1 else (0, 1 if py > 0 else -1)
        case = case.cut(nut_pocket(px, py, P2['ear_top'] + 0.01, out))
        if (px, py) in PCB_FAN_POSTS:
            case = case.cut(nut_pocket(px, py, Z_PCB + 0.01, out))
    assert case.val().isValid() and case.val().Volume() > 500, 'ファンの台の形が壊れた'
    add('fan_case', case, 'resin')
else:                   # v3: 渦巻きのケース(ボリュート)。フレームにねじ3本で留める。基板はケースの柱に載せるだけ(2026-10-19)
    from shapely.geometry import Polygon as SPoly
    BOSS_R = CFG['boss_r']
    Z_TOP1 = 9.4; Z_TOP0 = Z_TOP1 - CFG['top']
    W = CFG['wall']
    R0, R1, Y_OUT = 10.6, 13.6, 15.5          # 渦巻きの内側の半径(舌 → 出口)、出口の端(左)
    tt = np.linspace(0, 1, 181)
    pts = [(fx + (R0 + (R1 - R0) * t) * math.cos(2 * math.pi * t), fy + (R0 + (R1 - R0) * t) * math.sin(2 * math.pi * t)) for t in tt]
    pts += [(fx + R1, fy + Y_OUT), (fx + R0, fy + Y_OUT)]
    inner = SPoly(pts).buffer(0)
    outer = inner.buffer(W, join_style=2)
    exit_cut = sbox(fx + R0 - 0.01, fy + Y_OUT - 0.01, fx + R1 + 0.01, fy + Y_OUT + W + 0.5)
    PCB_FAN_POSTS = [p for p in dz.FAN_SCREWS if abs(p[1]) > 1]     # 基板も載せる柱(左右)
    FRONT_EAR = [p for p in dz.FAN_SCREWS if abs(p[1]) <= 1][0]
    webs = []
    for (px, py) in dz.FAN_SCREWS:                                   # 柱・耳とケースをつなぐ
        q = outer.exterior.interpolate(outer.exterior.project(Point(px, py)))
        webs.append(Point(px, py).buffer(BOSS_R, 32).union(q.buffer(1.5)).convex_hull)
    wall2d = outer.union(unary_union(webs)).difference(inner).difference(exit_cut)
    case = cq.Workplane().add(poly_solid(wall2d, Z_PC, Z_TOP1))
    case = case.union(cq.Workplane().add(poly_solid(outer, Z_TOP0, Z_TOP1)))   # 天井
    for (px, py) in dz.FAN_SCREWS:
        top = Z_PCB if (px, py) in PCB_FAN_POSTS else Z_TOP1
        case = case.union(zcyl(BOSS_R, Z_PC, top, px, py))
        foot = Point(px, py).buffer(BOSS_R, 48).difference(g['suction'])     # ポリカーボネートのない所は、フレームの上面(3.0)まで下げる
        if foot.area > 0.5:
            case = case.union(cq.Workplane().add(poly_solid(foot, Z_FT, Z_PC + 0.05)))
    # モーターの筒(割りを入れて、横のねじで締める)
    Z_COL = 13.2
    col = zcyl(5.15, Z_TOP1, Z_COL, fx, fy).union(
        cq.Workplane().box(2.8, 5.6, 3.0, centered=False).translate((fx - 7.4, fy - 2.8, 10.0)))
    case = case.union(col)
    case = case.cut(cq.Workplane().box(3.6, 0.8, Z_COL - Z_TOP1, centered=False).translate((fx - 7.5, fy - 0.4, Z_TOP1 + 0.3)))
    case = case.cut(zcyl(4.35, Z_TOP1, Z_COL + 1, fx, fy))
    case = case.cut(ycyl(SC['hole'] / 2, -3.0, 3.0, fx - 6.1, 11.5))
    case = case.cut(zcyl(1.5, Z_TOP0 - 0.1, Z_TOP1 + 0.1, fx, fy))           # 軸の穴
    def nut_pocket(px, py, z_top, out):
        hexp = cq.Workplane().center(px, py).polygon(6, SC['pocket'] / math.cos(math.pi / 6)).extrude(SC['depth']).translate((0, 0, z_top - SC['depth']))
        ux, uy = out
        slot = cq.Workplane().box(5.0 if ux else SC['pocket'], 5.0 if uy else SC['pocket'], SC['depth'], centered=(True, True, False)) \
            .translate((px + 2.5 * ux, py + 2.5 * uy, z_top - SC['depth']))
        return hexp.union(slot)
    for (px, py) in dz.FAN_SCREWS:
        case = case.cut(zcyl(SC['hole'] / 2, Z_FT - 0.2, Z_PCB + 1, px, py))
        out = (1, 0) if abs(py) <= 1 else (0, 1 if py > 0 else -1)
        case = case.cut(nut_pocket(px, py, P2['ear_top'] + 0.01, out))        # フレームのねじのナット(横から)
        if (px, py) in PCB_FAN_POSTS:
            case = case.cut(nut_pocket(px, py, Z_PCB + 0.01, out))            # 基板のねじのナット(横から)
    assert case.val().isValid() and case.val().Volume() > 500, 'ファンのケースの形が壊れた'
    add('fan_case', case, 'resin')
R_IMP = 16.0 if SPIDER else 10.0      # 羽根の半径(2026-10-20: φ32)
imp = zcyl(R_IMP, 7.4, 8.0, fx, fy).union(zcyl(1.5, 4.5, 8.0, fx, fy))
for i in range(8):
    imp = imp.union(cq.Workplane().box(R_IMP - 4.0, 0.5, 3.6).translate((fx + (R_IMP + 4.0) / 2, fy, 5.6))
                    .rotate((fx, fy, 0), (fx, fy, 1), i * 45))
imp = imp.cut(zcyl(0.6, 4.4, 8.1, fx, fy))
add('impeller', imp, 'resin')
add('fan_motor', zcyl(4.3, Z_TOP1, Z_TOP1 + 20.0, fx, fy).union(zcyl(1.2, Z_TOP1 - 0.3, Z_TOP1, fx, fy)), 'fan_motor')
add('fan_shaft', zcyl(0.6, Z_TOP1 - 5.1, Z_TOP1 - 0.3, fx, fy), 'steel')
Z_CL = Z_PCBT + 2.0 if CFG['clamp'] else Z_PCBT    # 押さえの上面(押さえがなければ、ねじの頭は基板の上)
if CFG['clamp']:
    clamp = zcyl(5.6, Z_PCBT, Z_CL, fx, fy)
    for sy in (1, -1):
        bar = cq.Workplane().box(3.0, BOSS_Y, Z_CL - Z_PCBT, centered=(True, False, False)).translate((fx, 0 if sy > 0 else -BOSS_Y, Z_PCBT))
        clamp = clamp.union(zcyl(BOSS_R, Z_PCBT, Z_CL, fx, sy * BOSS_Y)).union(bar)
    clamp = clamp.cut(zcyl(4.35, Z_PCBT - 0.1, Z_CL + 0.1, fx, fy))
    for sy in (1, -1):
        clamp = clamp.cut(zcyl(1.6, Z_PCBT - 0.1, Z_CL + 0.1, fx, sy * BOSS_Y))
    add('fan_clamp', clamp, 'resin')

# ---------------- 基板 ----------------
if SPIDER:      # 2026-10-19: U字。2026-10-28(基板 v5): ファンの上はハブのまわりだけ開け、後ろは x −46 まで広げる(pcb_shape.py)
    import pcb_shape
    pcb_outline = pcb_shape.outline()
else:
    pcb_outline = unary_union([
        sbox(-21.0, -25.5, -9.0, 25.5),     # 後ろ(マウントの柱の上)
        sbox(-9.0, -25.0, 9.0, 25.0),       # 車輪の間(41T の上は z 13.95 なので |y| 25.8 より内側)
        sbox(9.0, -21.0, 25.0 if FRAME_FAN else 22.0, 21.0),       # ファンのまわり(v3 はケースの柱まで)
        sbox(22.0, -12.0, 40.0, 12.0),      # 首
        sbox(40.0, -23.0, 47.5, 23.0),      # 壁センサの板(フレームの前の辺より内側)
    ]).buffer(-2.0, join_style=1).buffer(2.0, join_style=1)
pcb_holes = ([] if SPIDER else [Point(FAN).buffer(4.6, 64)]) + [Point(p).buffer(SC['hole'] / 2, 24) for p in PCB_FAN_POSTS] \
    + [Point(dz.MOUNT_SCREWS[0][0], sy * dz.MOUNT_SCREWS[0][1]).buffer(SC['hole'] / 2, 24) for sy in (1, -1)]
pcb_poly = pcb_outline.difference(unary_union(pcb_holes))
add('pcb', poly_solid(pcb_poly, Z_PCB, Z_PCBT), 'fr4')

# ---------------- 電池 ----------------
b = BAT
add('battery', cq.Workplane().box(b['lx'], b['ly'], b['lz']).translate((b['x'], 0, Z_PCBT + b['lz'] / 2)), 'battery')

# ---------------- 壁センサ(発光 OPV332・受光 SFH 229 FA、φ3 × 4.5 を基板の上に寝かせる) ----------------
# 2026-10-19: 前の2本はタイヤの前の耳 (12, ±30) で外へ5°、横の2本は前の角 (41, ±24) から反対側の壁へ 75°(左右で交差)
SENS = {'FL': ((12.0, 30.0), 5.0), 'FR': ((12.0, -30.0), -5.0), 'R': ((41.0, 24.0), -75.0), 'L': ((41.0, -24.0), 75.0)}
for nm, ((sx_, sy_), ang) in SENS.items():
    a = math.radians(ang)
    u = np.array([math.cos(a), math.sin(a)]); n = np.array([-u[1], u[0]])
    for k, off in (('led', 2.0), ('pd', -2.0)):
        c = np.array([sx_, sy_]) + n * off
        body = (cq.Workplane('YZ').circle(1.5).extrude(4.5).translate((0, 0, Z_PCBT + 1.6))
                .rotate((0, 0, 0), (0, 0, 1), ang).translate((c[0], c[1], 0)))
        add(f'sensor_{nm}_{k}', body, 'sensor')

# ---------------- ねじ・ナット ----------------
def screw(x, y, z_head_bottom, L, up=True, head_h=None, head_r=None, d=None):
    """小ねじ。up=True なら頭が下で軸が上へ"""
    head_h = SC['k'] if head_h is None else head_h
    head_r = SC['dk'] / 2 if head_r is None else head_r
    r = (SC['d'] if d is None else d) / 2
    if up:
        return zcyl(head_r, z_head_bottom - head_h, z_head_bottom, x, y).union(zcyl(r, z_head_bottom, z_head_bottom + L, x, y))
    return zcyl(head_r, z_head_bottom, z_head_bottom + head_h, x, y).union(zcyl(r, z_head_bottom - L, z_head_bottom, x, y))
def nut(x, y, z0):
    return (cq.Workplane().center(x, y).polygon(6, SC['s'] / math.cos(math.pi / 6)).extrude(SC['m'])
            .cut(cq.Workplane().center(x, y).circle(SC['d'] / 2).extrude(SC['m'])).translate((0, 0, z0)))
xr, xf = dz.MOUNT_SCREWS[0][0], dz.MOUNT_SCREWS[1][0]      # MOUNT_SCREWS = [後ろ, 前]
for sy, side in ((1, 'L'), (-1, 'R')):
    y = sy * dz.MOUNT_SCREWS[0][1]
    if CFG['screws'] == 'steel':     # v0: 鉄 6組
        add(f'screw_mountF_{side}', screw(xf, y, Z_FB, 5.0), 'steel')                       # 前の耳: L5、ナットは耳の上
        add(f'nut_mountF_{side}', nut(xf, y, P2['ear_top'] - P2['nut_depth']), 'steel')
        add(f'screw_post_{side}', screw(xr, y, Z_FB, 15.0), 'steel')                        # 後ろの耳: L15 でフレーム・柱・基板
        add(f'nut_post_{side}', nut(xr, y, Z_PCBT), 'steel')
        add(f'screw_fan_{side}', screw(fx, sy * BOSS_Y, Z_CL, 5.0, up=False), 'steel')      # ファンの押さえ: L5、ナットはケースの柱
        add(f'nut_fan_{side}', nut(fx, sy * BOSS_Y, Z_PCB - 2.45), 'steel')
    elif CFG['screws'] == 'm2mix':   # v2: M2。フレームの下は鉄の低頭 L5 + ナイロンのナット、基板はナイロンのなべ L4 + ナイロンのナット
        for nm_, x_ in (('mountF', xf), ('mountR', xr)):
            add(f'screw_{nm_}_{side}', screw(x_, y, Z_FB, 5.0), 'steel')
            if not TAP:
                add(f'nut_{nm_}_{side}', nut(x_, y, P2['ear_top'] - P2['nut_depth']), 'nylon')
        add(f'screw_post_{side}', screw(xr, y, Z_PCBT, SC['Lp'], up=False, head_h=1.6, head_r=2.0), 'nylon')
        if not TAP:
            add(f'nut_post_{side}', nut(xr, y, Z_PCB - SC['depth'] + 0.05), 'nylon')
        fpx, fpy = PCB_FAN_POSTS[0 if sy > 0 else 1]
        add(f'screw_fan_{side}', screw(fpx, fpy, Z_CL, SC['Lp'], up=False, head_h=1.6, head_r=2.0), 'nylon')
        if not TAP:
            add(f'nut_fan_{side}', nut(fpx, fpy, Z_PCB - SC['depth'] + 0.05), 'nylon')
    elif CFG['screws'] == 'small':   # 細いねじ(鉄)8組。基板のねじは短く
        for nm_, x_ in (('mountF', xf), ('mountR', xr)):
            add(f'screw_{nm_}_{side}', screw(x_, y, Z_FB, 5.0), 'steel')
            add(f'nut_{nm_}_{side}', nut(x_, y, P2['ear_top'] - P2['nut_depth']), 'steel')
        add(f'screw_post_{side}', screw(xr, y, Z_PCBT, SC['Lp'], up=False), 'steel')
        add(f'nut_post_{side}', nut(xr, y, Z_PCB - SC['depth'] + 0.05), 'steel')
        add(f'screw_fan_{side}', screw(fx, sy * BOSS_Y, Z_CL, SC['Lp'], up=False), 'steel')
        add(f'nut_fan_{side}', nut(fx, sy * BOSS_Y, Z_PCB - SC['depth'] + 0.05), 'steel')
    else:                            # v1: フレームの下は頭の低い鉄(床まで0.5mm)、ナットと基板のねじはナイロン
        for nm_, x_ in (('mountF', xf), ('mountR', xr)):
            add(f'screw_{nm_}_{side}', screw(x_, y, Z_FB, 5.0), 'steel')                    # 低頭 L5、ナットは耳(後ろは横から入れる)
            add(f'nut_{nm_}_{side}', nut(x_, y, P2['ear_top'] - P2['nut_depth']), 'nylon')
        add(f'screw_post_{side}', screw(xr, y, Z_PCBT, 5.0, up=False, head_h=2.1, head_r=2.75), 'nylon')  # なべ L5、柱の上のナット
        add(f'nut_post_{side}', nut(xr, y, Z_PCB - 2.45), 'nylon')
        add(f'screw_fan_{side}', screw(fx, sy * BOSS_Y, Z_CL, 5.0, up=False, head_h=2.1, head_r=2.75), 'nylon')
        add(f'nut_fan_{side}', nut(fx, sy * BOSS_Y, Z_PCB - 2.45), 'nylon')

if FRAME_FAN:   # ファンのケースをフレームに留めるねじ(下から鉄の低頭 L5)と、モーターの筒を締めるねじ(ナイロン、横)
    for i, (px, py) in enumerate(dz.FAN_SCREWS):
        add(f'screw_fanframe_{i}', screw(px, py, Z_FB, 5.0), 'steel')
        if not TAP:
            add(f'nut_fanframe_{i}', nut(px, py, P2['ear_top'] - P2['nut_depth'] + 0.05), 'nylon')
    if SPIDER:
        for i, (px, py) in enumerate(dz.FAN_JOINTS):   # ファンの台をマウントの腕に留める(ナイロンのなべ L6、上から)
            add(f'screw_fanjoint_{i}', screw(px, py, 10.8, 6.0, up=False, head_h=1.6, head_r=2.0), 'nylon')
    if not SPIDER:      # v3: モーターの筒を横のねじで締める(v4 は圧入)
        add('screw_fanclamp', ycyl(1.0, -2.8, 5.2, fx - 6.1, 11.5).union(ycyl(2.0, -4.4, -2.8, fx - 6.1, 11.5)), 'nylon')
        add('nut_fanclamp', ycyl(2.3, 2.8, 4.4, fx - 6.1, 11.5).cut(ycyl(1.0, 2.7, 4.5, fx - 6.1, 11.5)), 'nylon')

# ---------------- 質量 ----------------
def props(shape):
    gp = GProp_GProps(); BRepGProp.VolumeProperties_s(shape.wrapped, gp)
    c = gp.CentreOfMass(); I = gp.MatrixOfInertia()
    return gp.Mass(), np.array([c.X(), c.Y(), c.Z()]), np.array([[I.Value(i, j) for j in (1, 2, 3)] for i in (1, 2, 3)])

rows = []
for name, (shape, mat) in parts.items():
    v, c, I = props(shape)
    if mat in FIXED:
        m = FIXED[mat]; rho = m / v
    else:
        rho = RHO[mat]; m = v * rho
    rows.append(dict(name=name, mat=mat, vol=v, m=m, c=c, I=I * rho))
# 形のないもの: 基板の部品(基板の面に広げる)、配線
pcb_c = np.array([pcb_poly.centroid.x, pcb_poly.centroid.y, Z_PCBT + 0.5])
for r in rows:
    if r['name'] == 'pcb':
        scale = (r['m'] + FIXED['pcb_parts']) / r['m']
        r['m'] *= scale; r['I'] = r['I'] * scale; r['mat'] = 'fr4 + 部品2.5g'
rows.append(dict(name='wiring', mat='配線(仮)', vol=0, m=FIXED['wiring'], c=np.array([0.0, 0.0, 12.0]), I=np.zeros((3, 3))))
M = sum(r['m'] for r in rows)
CG = sum(r['m'] * r['c'] for r in rows) / M
Izz = sum(r['I'][2, 2] + r['m'] * ((r['c'][0] - CG[0])**2 + (r['c'][1] - CG[1])**2) for r in rows) / 100   # g·cm²

GROUP = [('フレーム・ポリカーボネート・スカート・滑り板', ('frame', 'pc_sheet', 'skirt', 'skid')),
         ('モーターマウント × 2', ('mount_',)),
         ('走行用モーター × 2', ('motor_',)),
         ('車輪・タイヤ・41T・ピニオン・軸・軸受・磁石・エンコーダ', ('wheel', 'tire', 'spur41', 'pinion', 'pin_', 'shaft_', 'brg_', 'magnet', 'enc_board', 'as5047p')),
         ('吸引ファン(モーター・ケース・羽根' + ('・押さえ' if CFG['clamp'] else '') + ')', ('fan_', 'impeller')),
         (f'基板({T_PCB}mm)+ 部品', ('pcb',)),
         ('電池(3S 180mAh)', ('battery',)),
         ('壁センサ × 4', ('sensor_',)),
         ('ねじ・ナット', ('screw_', 'nut_')),
         ('配線', ('wiring',))]
grp = []
for gname, keys in GROUP:
    sel = [r for r in rows if any(r['name'].startswith(k) for k in keys)]
    m = sum(r['m'] for r in sel)
    iz = sum(r['I'][2, 2] + r['m'] * ((r['c'][0] - CG[0])**2 + (r['c'][1] - CG[1])**2) for r in sel) / 100
    grp.append(dict(group=gname, m=round(m, 2), iz=round(iz, 1), n=len(sel)))
assert sum(x['n'] for x in grp) == len(rows), [r['name'] for r in rows if not any(any(r['name'].startswith(k) for k in ks) for _, ks in GROUP)]

# もしも(部品の重さを何倍にするか)
def whatif(factors):
    m_tot, iz_tot = 0.0, 0.0
    for r in rows:
        k = 1.0
        for pre, f in factors.items():
            if r['name'].startswith(pre):
                k = f(r) if callable(f) else f
        m_tot += r['m'] * k
        iz_tot += k * (r['I'][2, 2] + r['m'] * ((r['c'][0] - CG[0])**2 + (r['c'][1] - CG[1])**2))
    return dict(m=round(m_tot, 2), iz=round(iz_tot / 100, 1))
def pcb_t(t):
    def f(r):
        bare = r['m'] - FIXED['pcb_parts']
        return (bare * t / T_PCB + FIXED['pcb_parts']) / r['m']
    return f
if V == 'v0':
    ny = RHO['nylon'] / RHO['steel']
    WHATIF = {'ねじ・ナットをナイロンに': whatif({'screw_': ny, 'nut_': ny}), '基板を0.6mmに': whatif({'pcb': pcb_t(0.6)}),
              '両方': whatif({'screw_': ny, 'nut_': ny, 'pcb': pcb_t(0.6)})}
else:   # 2026-10-19: ファン(モーター・羽根)と電池は変えない。ほかで軽くする案
    ny, ti = RHO['nylon'] / RHO['steel'], RHO['titanium'] / RHO['steel']
    al, pa = RHO['aluminum'] / RHO['steel'], RHO['pa12'] / RHO['resin']
    fanscr = {'screw_fanframe_': ny}
    mscr_ti, mscr_al = {'screw_mount': ti}, {'screw_mount': al}
    pa12 = {'mount_': pa, 'fan_case': pa, 'wheel': pa}
    pcb4 = {'pcb': pcb_t(0.4)}
    WHATIF = {'ファンの台のねじ3本をナイロンに': whatif(fanscr),
              'マウントのねじ4本をチタンに': whatif(mscr_ti), 'マウントのねじ4本をアルミに': whatif(mscr_al),
              '印刷する部品をPA12に(マウント・ファンの台・ホイール)': whatif(pa12),
              '基板を0.4mmに': whatif(pcb4),
              'ねじ(ナイロン + チタン)+ PA12': whatif({**fanscr, **mscr_ti, **pa12}),
              'ねじ(ナイロン + アルミ)+ PA12': whatif({**fanscr, **mscr_al, **pa12}),
              'ねじ(ナイロン + チタン)+ PA12 + 基板0.4mm': whatif({**fanscr, **mscr_ti, **pa12, **pcb4})}
print('もしも:', WHATIF)

if FAST:
    print(f"{V}: 合計 {M:.2f} g、重心 ({CG[0]:.2f}, {CG[1]:.2f}, {CG[2]:.2f}) mm、慣性モーメント {Izz:.0f} g·cm²")
    for x in grp:
        print(f"  {x['group']:42s} {x['m']:6.2f} g  {x['iz']:6.1f} g·cm²")
    json.dump(dict(mass=round(M, 2), cg=[round(c, 2) for c in CG], iz=round(Izz, 1), groups=grp, whatif=WHATIF,
                   parts=[dict(name=r['name'], mat=r['mat'], m=round(r['m'], 3)) for r in rows]),
              open(os.path.join(OUT, f'vehicle_{V}_mass.json'), 'w'), ensure_ascii=False, indent=1)
    sys.exit(0)

# ---------------- ぶつかり ----------------
IGN = [('pinion', 'spur41'), ('pin_', 'wheel'), ('pin_', 'brg_'), ('magnet', 'brg_in'), ('brg_out', 'spur41'), ('spur41', 'wheel'),
       ('tire', 'wheel'), ('shaft_', 'pinion'), ('motor_', 'shaft_'), ('enc_board', 'as5047p'), ('magnet', 'pin_'), ('brg_in', 'brg_out'),
       ('mount', 'brg_'), ('mount', 'motor_'), ('mount', 'frame'), ('mount', 'enc_board'), ('enc_board', 'frame'),
       ('screw_', 'nut_'), ('screw_', 'frame'), ('screw_', 'mount'), ('screw_', 'pcb'), ('screw_', 'fan_'), ('nut_', 'mount'), ('nut_', 'pcb'),
       ('nut_', 'fan_case'), ('nut_', 'fan_clamp'), ('fan_case', 'pc_sheet'), ('fan_case', 'fan_motor'), ('fan_motor', 'fan_shaft'),
       ('impeller', 'fan_shaft'), ('fan_case', 'pcb'), ('fan_clamp', 'pcb'), ('fan_clamp', 'fan_motor'), ('pcb', 'battery'),
       ('pcb', 'sensor_'), ('pcb', 'mount'), ('frame', 'pc_sheet'), ('frame', 'skirt'), ('frame', 'skid'), ('pc_sheet', 'skirt'),
       ('fan_case', 'frame'), ('pcb', 'fan_motor'), ('sensor_', 'sensor_'), ('impeller', 'fan_case'), ('spur41', 'tire')]
def ignored(a, b):
    for p, q in IGN:
        if (a.startswith(p) and b.startswith(q)) or (a.startswith(q) and b.startswith(p)):
            return True
    return False
def bbgap(a, b):
    A, B = a.BoundingBox(), b.BoundingBox()
    dx = max(0, max(A.xmin, B.xmin) - min(A.xmax, B.xmax))
    dy = max(0, max(A.ymin, B.ymin) - min(A.ymax, B.ymax))
    dz_ = max(0, max(A.zmin, B.zmin) - min(A.zmax, B.zmax))
    return math.sqrt(dx * dx + dy * dy + dz_ * dz_)
clear = []
names = list(parts)
for a, b2 in itertools.combinations(names, 2):
    if ignored(a, b2):
        continue
    sa, sb = parts[a][0], parts[b2][0]
    if bbgap(sa, sb) > 1.0:
        continue
    d = BRepExtrema_DistShapeShape(sa.wrapped, sb.wrapped); d.Perform()
    v = d.Value()
    if v < 1.0:
        ov = 0.0
        if v < 1e-6:
            try:
                ov = sa.intersect(sb).Volume()
            except Exception:
                ov = -1
        clear.append(dict(a=a, b=b2, gap=round(v, 3), overlap=round(ov, 3)))
clear.sort(key=lambda r: r['gap'])


res = dict(whatif=WHATIF, mass=round(M, 2), cg=[round(c, 2) for c in CG], iz=round(Izz, 1), groups=grp, clearances=clear,
           parts=[dict(name=r['name'], mat=r['mat'], m=round(r['m'], 3), c=[round(c, 2) for c in r['c']]) for r in rows],
           height=round(max(s.BoundingBox().zmax for s, _ in parts.values()), 2))
json.dump(res, open(os.path.join(OUT, f'vehicle_{V}_result.json'), 'w'), ensure_ascii=False, indent=1)
print(f"合計 {M:.2f} g、重心 ({CG[0]:.2f}, {CG[1]:.2f}, {CG[2]:.2f}) mm、慣性モーメント(重心まわり) {Izz:.0f} g·cm²、高さ {res['height']} mm")
for x in grp:
    print(f"  {x['group']:42s} {x['m']:6.2f} g  {x['iz']:6.1f} g·cm²")
print('すき間 1mm 未満:')
for r in clear:
    print(f"  {r['a']:18s} - {r['b']:18s} {r['gap']:6.3f} mm  重なり {r['overlap']} mm³")

# ---------------- STEP(部品ごとに名前と色) ----------------
COL = dict(nylon=(0.95, 0.95, 0.9), carbon=(0.25, 0.24, 0.22), pc=(0.62, 0.79, 0.88), film=(0.9, 0.9, 0.6), ptfe=(0.95, 0.95, 0.95), skid=(0.95, 0.95, 0.95), resin=(0.95, 0.56, 0.17),
           steel=(0.3, 0.3, 0.32), ndfeb=(0.7, 0.7, 0.75), rubber=(0.1, 0.1, 0.1), pom=(0.9, 0.9, 0.85), brass=(0.8, 0.65, 0.2),
           fr4=(0.1, 0.45, 0.2), motor=(0.65, 0.65, 0.68), fan_motor=(0.65, 0.65, 0.68), battery=(0.2, 0.35, 0.75), sensor=(0.85, 0.2, 0.2))
asm = cq.Assembly(name=f'MK4_vehicle_{V}')
for name, (shape, mat) in parts.items():
    asm.add(shape, name=name, color=cq.Color(*COL[mat]))
asm.save(os.path.join(OUT, f'mk4_vehicle_{V}.step'))

# ---------------- 図 ----------------
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
tri = {}
for name, (shape, mat) in parts.items():
    v, t = shape.tessellate(0.06, 0.35)
    v = np.array([(p.x, p.y, p.z) for p in v])
    tri[name] = (v[np.array(t)] if len(t) else np.zeros((0, 3, 3)), mat)
ALL_T = np.concatenate([T for T, _ in tri.values() if len(T)])
ALL_C = np.concatenate([np.tile(list(COL[mat]) + [0.4 if mat in ('pc', 'film') else 1.0], (len(T), 1)) for T, mat in tri.values() if len(T)])
def draw3d(ax, elev, azim, title):
    # 1つのまとまりにして描く(部品をまたいで奥から順に塗られる)
    ax.add_collection3d(Poly3DCollection(ALL_T, facecolors=ALL_C, linewidths=0, shade=True))
    ax.set_xlim(-52, 52); ax.set_ylim(-37, 37); ax.set_zlim(0, 32)
    ax.set_box_aspect((104, 74, 32), zoom=1.15); ax.view_init(elev, azim); ax.set_axis_off(); ax.set_title(title, fontsize=10)
fig = plt.figure(figsize=(16, 7.5))
draw3d(fig.add_subplot(1, 2, 1, projection='3d'), 28, -60, f'MK4 vehicle {V} (provisional) from front-left')
draw3d(fig.add_subplot(1, 2, 2, projection='3d'), 28, -125, 'from rear-left')
fig.tight_layout(); fig.savefig(os.path.join(OUT, f'vehicle_{V}_3d.png'), dpi=110)

# 上から・横から(輪郭)
from matplotlib.patches import Polygon as MPoly
fig, axs = plt.subplots(2, 1, figsize=(11, 12), gridspec_kw=dict(height_ratios=[74, 40]))
order = sorted(parts, key=lambda n: parts[n][0].BoundingBox().zmax)
for ax, (i, j), lim in ((axs[0], (0, 1), (-40, 40)), (axs[1], (0, 2), (-1, 33))):
    seq = order if j == 1 else sorted(parts, key=lambda n: -parts[n][0].BoundingBox().ymin)
    for name in seq:
        T, mat = tri[name]
        if not len(T):
            continue
        a = 0.3 if mat in ('pc', 'film') else (0.8 if mat == 'battery' else 1.0)
        for t in T[::1]:
            ax.add_patch(MPoly(t[:, [i, j]], closed=True, fc=COL[mat], ec='none', alpha=a))
    ax.set_xlim(-55, 55); ax.set_ylim(*lim); ax.set_aspect('equal'); ax.grid(alpha=.3)
axs[0].set_title('top view (x forward, y left) [mm]'); axs[1].set_title('side view from the right (x forward, z up) [mm]')
axs[1].axhline(0, color='k', lw=1)
fig.tight_layout(); fig.savefig(os.path.join(OUT, f'vehicle_{V}_views.png'), dpi=100)

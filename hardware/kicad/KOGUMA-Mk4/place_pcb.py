"""メイン基板の部品を、配置の案(docs/img/pcb_zone_plan.png、2026-10-31)どおりに置く(最初の配置)
- 部品はすべて表。電池(x −21.25〜1.25、|y| ≤ 16)は部品の上に載せるので、その下には高さ 1.1mm 以下の部品だけ
- IC・コネクタ・スイッチなどは、まとまりごとに位置を決めて置く(ANCHOR)
- 抵抗・コンデンサは、つながる IC のパッドのそばの空いている所を探して置く(NEAR)
- 裏は壁センサのホルダの足だけ。ねじの頭(上)、エンコーダの穴とパッド、ファンの穴を避ける
座標は機体の座標(原点は車軸の中心、+x 前、+y 左)、角度は上から見て反時計回り(KiCad と同じ向き)
使い方(このフォルダで): python3 place_pcb.py   → KOGUMA-Mk4.kicad_pcb の部品を置き直す(線は引かない)"""
import os, sys, math
import pcbnew
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union
from shapely import affinity
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '../../../mechanical/vehicle'))
import pcb_shape as ps

OX, OY = 150.0, 100.0
mm = pcbnew.FromMM
P = lambda x, y: pcbnew.VECTOR2I(mm(OX + x), mm(OY - y))
back = lambda v: (pcbnew.ToMM(v.x) - OX, OY - pcbnew.ToMM(v.y))
PCB = os.path.join(HERE, 'KOGUMA-Mk4.kicad_pcb')
board = pcbnew.LoadBoard(PCB)
FP = {f.GetReference(): f for f in board.GetFootprints()}

BAT = box(-21.25, -16.0, 1.25, 16.0)
LOW = 1.1                                    # 電池の下に置ける高さ
TALL = ('C_0805', 'C_1206', 'R_1206', 'SOIC', 'CP_EIA', 'SolderWire', 'PinHeader', 'Buzzer', 'SW_Push', 'SW_Slide', 'D_SMF', 'D_SOD-123')
OUTLINE = ps.outline()
AREA = Polygon(OUTLINE.exterior).buffer(-0.25)
for r in OUTLINE.interiors:
    AREA = AREA.difference(Polygon(r).buffer(0.25))
KEEP = [Point(p).buffer(2.4) for p in ps.SCREWS]                       # ねじの頭(φ3.8)
KEEP += [box(x0 - 3.0, y0 - 3.0 if y0 < 0 else y0 - 2.6, x1 + 3.0, y1 + 2.6 if y0 > 0 else y1 + 3.0) for x0, x1, y0, y1 in ps.ENC]  # エンコーダの穴とパッド

def crt(fp):
    """courtyard(表か裏)を機体の座標の shapely に"""
    for lay in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
        sp = fp.GetCourtyard(lay)
        if sp.OutlineCount():
            polys = []
            for k in range(sp.OutlineCount()):
                o = sp.Outline(k)
                polys.append(Polygon([back(o.CPoint(i)) for i in range(o.PointCount())]).buffer(0.05))
            return unary_union(polys)
    bb = fp.GetBoundingBox(False)
    (x0, y0), (x1, y1) = back(bb.GetOrigin()), back(bb.GetEnd())
    return box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))

placed = {}
FAILED = []
FIXED = ['D70', 'D71', 'D72', 'D73', 'D74', 'D75', 'D76', 'D77', 'J5', 'J6', 'D90', 'D91', 'D92', 'D93', 'D94', 'D95', 'D96', 'D98', 'H1', 'H2', 'H3', 'H4']
for r in FIXED:
    placed[r] = crt(FP[r]) if not FP[r].IsFlipped() else None        # 裏のホルダは表の部品とはぶつからない(足の穴は KEEP に入れる)
for nm in ps.SENS:
    KEEP.append(unary_union([Point(p).buffer(ps.PAD_D / 2 + 0.3) for p in ps.pads(nm)]))
    KEEP.append(ps.slot(nm).buffer(0.3))

def is_tall(fp):
    n = fp.GetFPID().GetLibItemName().wx_str()
    return any(t in n for t in TALL)

def legal(ref, poly):
    if not AREA.contains(poly):
        return False
    if any(poly.intersects(k) for k in KEEP):
        return False
    if is_tall(FP[ref]) and poly.intersects(BAT):
        return False
    return not any(q is not None and poly.intersects(q) for r, q in placed.items() if r != ref)

def put(ref, x, y, a=0.0, force=False):
    fp = FP[ref]
    fp.SetOrientationDegrees(a % 360); fp.SetPosition(P(x, y))
    poly = crt(fp)
    if not force and not legal(ref, poly):
        return False
    placed[ref] = poly
    return True

def pad_xy(ref, net):
    for p in FP[ref].Pads():
        if p.GetNetname() == net:
            return back(p.GetPosition())
    return None

def near(ref, tx, ty, angles=(0, 90), rmax=12.0):
    """(tx, ty) にいちばん近い、置ける所に置く"""
    best = None
    r = 0.0
    while r <= rmax and best is None:
        n = max(1, int(2 * math.pi * r / 0.4)) if r > 0 else 1
        for i in range(n):
            th = 2 * math.pi * i / n
            x, y = tx + r * math.cos(th), ty + r * math.sin(th)
            for a in angles:
                if put(ref, x, y, a):
                    best = (x, y, a); break
                placed.pop(ref, None)
            if best: break
        r += 0.2
    if best is None:
        FAILED.append((ref, tx, ty)); print(f'{ref}: 置ける所がない(目標 {tx:.1f}, {ty:.1f})')
        return None
    put(ref, *best, force=True)
    return best

def near_pad(ref, ic, net=None, out=1.6, **kw):
    """IC のパッド(net。省略すると、この部品の GND 以外のネット)のそばに、IC の外へ out だけ出して置く"""
    if net is None:
        nets = [p.GetNetname() for p in FP[ref].Pads() if p.GetNetname() not in ('GND', '')]
        cands = [(n, pad_xy(ic, n)) for n in nets if pad_xy(ic, n)]
        net = cands[0][0]
    px, py = pad_xy(ic, net)
    cx, cy = back(FP[ic].GetPosition())
    d = math.hypot(px - cx, py - cy) or 1.0
    return near(ref, px + (px - cx) / d * out, py + (py - cy) / d * out, **kw)

# ================= まとまりごとの置き方 =================
# 1. MCU(電池の下)。上の辺(左 +y)に IMU・UART・ファン・ブザー、右の辺(前)にモーターの PWM・エンコーダの SPI、
#    下の辺(右 −y)に ADC、左の辺(後ろ)に発振子・SMPS
put('U4', -11.0, 0.5, 0, force=True)
put('U76', -0.9, 0.0, 90, force=True)                                   # 2. IMU: 車軸の真上のすぐ後ろ。SPI の辺を MCU に向ける
# 4. ドライバとモーターの線(電池のすぐ前。モーターの端子は裏の (−8.5, ±5))
near('J2', 3.4, 4.9, angles=(90,)); near('J3', 3.4, -4.9, angles=(90,))
near('U2', 5.0, 10.6, angles=(0, 90)); near('U3', 5.0, -10.6, angles=(0, 90))
# 5. 電源の入口(ファンの穴の左): 大きい部品から
near('C4', 12.5, 16.0, angles=(90, 0, 60))
near('Q1', 9.5, 12.0, angles=(0, 90))
near('J1', 4.0, 16.5, angles=(0, 90))
# 6. 3.3V の DC-DC(ファンの穴の右)
near('U1', 11.6, -13.8, angles=(0, 90))
# 7. ファン(ファンの穴の前)
near('J4', 24.5, 0.0, angles=(90,))
near('Q40', 25.6, 4.4, angles=(0, 90)); near('R43', 25.6, -4.4, angles=(90, 0))
# 8. 受光のアンプ(FL・R は左、L・FR は右。それぞれ2つのセンサの間の縁)
near('U74', 27.0, 27.0, angles=(-30, -20, -40, 60, 70)); near('U75', 27.0, -27.0, angles=(30, 20, 40, -60, -70))
# 9. 発光のドライバ(それぞれのホルダのそば)
near('U70', 12.0, 25.5, angles=(0, 90)); near('U73', 12.0, -25.5, angles=(0, 90))
near('U72', 35.0, 21.0, angles=(-27, 63)); near('U71', 35.0, -21.0, angles=(27, -63))
# 10. 押しボタン・デバッグ端子(電池の左右)、ブザー
near('SW2', -8.0, 19.5, angles=(90, 0))
near('J7', -11.0, -19.5, angles=(0, 90))
near('BZ1', 30.4, 0.0, angles=(0,))                                    # ブザーは電池の横に入らないので前の真ん中(音の出る穴を前へ)

# SW1: V 字の斜めの縁(y 5〜11 でほぼまっすぐ)に、本体の前の辺を縁の 0.1mm 内側にそろえる
from shapely.geometry import LineString
e = [(LineString([(-40, y), (-10, y)]).intersection(OUTLINE).bounds[0], y) for y in (5.0, 11.0)]
ux, uy = e[1][0] - e[0][0], e[1][1] - e[0][1]; L = math.hypot(ux, uy); ux, uy = ux / L, uy / L
nx, ny = uy, -ux                                      # 縁から基板の中への向き
if nx < 0: nx, ny = -nx, -ny
mx, my = (e[0][0] + e[1][0]) / 2, (e[0][1] + e[1][1]) / 2
# フットプリント: つまみは +y(KiCad の下)、本体の前の辺は原点から 1.3mm。機体の座標では、つまみの向きを (−nx, −ny) に向ける
ang = math.degrees(math.atan2(-ny, -nx)) + 90         # ローカルの +y(KiCad)= 機体の −y を (−nx, −ny) へ
put('SW1', mx + nx * 1.4, my + ny * 1.4, round(ang), force=True)

# ---- 抵抗・コンデンサ ----
# MCU のパスコンと周り
for r in ('C55', 'C56', 'C57', 'C58', 'C59', 'C60', 'C61', 'C64'):
    near_pad(r, 'U4', out=1.5)
near_pad('L1', 'U4', net='Net-(U4-VLXSMPS)', out=2.2)
near_pad('C53', 'U4', net='Net-(U4-VLXSMPS)', out=2.0)
near_pad('C54', 'U4', net='/MCU/VCORE', out=2.5)
near_pad('Y1', 'U4', net='/MCU/OSC_IN', out=1.8)
near_pad('FB1', 'U4', net='Net-(U4-VDDA)', out=2.0)
near_pad('C51', 'U4', net='Net-(U4-VDDA)', out=1.5); near_pad('C52', 'U4', net='Net-(U4-VDDA)', out=1.5)
near_pad('C63', 'U4', net='NRST', out=1.5)
near_pad('R50', 'U4', net='/MCU/BOOT0', out=1.5)
near('C50', -11.0, -6.5); near('C62', -11.0, 7.0)
# IMU
near_pad('C81', 'U76', net='+3V3', out=1.3); near_pad('C82', 'U76', net='+3V3', out=1.3)
# LED の抵抗(MCU と後ろの LED の間)
for r, t in (('R90', (-18.0, -2.0)), ('R91', (-18.0, -4.0)), ('R92', (-18.0, 2.5)), ('R93', (-18.0, -11.0)), ('R94', (-18.0, -13.0)),
             ('R95', (-18.0, 11.0)), ('R96', (-18.0, 13.0)), ('R99', (-4.0, 6.0))):
    near(r, *t)
# ドライバ
for drv, cs in (('U2', ('C21', 'C22', 'C23', 'C24', 'R21', 'R22', 'R23', 'R24', 'R25')), ('U3', ('C31', 'C32', 'C33', 'C34', 'R31', 'R32', 'R33', 'R34', 'R35'))):
    for r in cs:
        near_pad(r, drv, out=1.3)
near('R40', 0.0, 8.5)
# 電源
for r in ('C2', 'C3', 'C5', 'C6', 'D1'):
    near_pad(r, 'Q1', net='VBAT', out=2.0)
for r in ('R1', 'R2', 'C1'):
    near_pad(r, 'Q1', net='/電源/GATE', out=1.5)
near('R4', 9.0, 7.5); near('R5', 9.0, 5.8); near('C9', 9.0, 4.3)
near('D2', 18.0, 9.0); near('R6', 18.0, 7.5)
for r in ('C7', 'C8'):
    near_pad(r, 'U1', net='+3V3', out=1.6)
near_pad('R3', 'U1', net='Net-(U1-FB(11))', out=1.5)
# ファン
near_pad('D40', 'Q40', net='Net-(D40-A)', out=1.5)
for r in ('R41', 'R42'):
    near_pad(r, 'Q40', net='Net-(Q40-G)', out=1.3)
near_pad('R44', 'R43', net='Net-(Q40-S)', out=1.2); near('C40', 27.5, -1.5)
# 壁センサ: 発光のドライバの抵抗とパスコン、アンプの帰還とパスコン、PD_BIAS(前の真ん中)
for u, rs, c in (('U70', 'R70', 'C70'), ('U71', 'R71', 'C71'), ('U72', 'R72', 'C72'), ('U73', 'R73', 'C73')):
    near_pad(rs, u, out=1.2); near_pad(c, u, net='+3V3', out=1.2)
for u, items in (('U74', ('R74', 'C74', 'R75', 'C75')), ('U75', ('R76', 'C76', 'R77', 'C77'))):
    for r in items:
        near_pad(r, u, out=1.3, rmax=8.0)
for u, items in (('U74', ('C83', 'C78')), ('U75', ('C84', 'C79'))):          # アンプの電源(100nF + 10µF)
    for r in items:
        near_pad(r, u, net='+3V3', out=1.3, rmax=14.0)
near('R78', 22.5, 9.0); near('R79', 22.5, 7.4); near('C80', 22.5, 5.6)
# 表示・通信
near('R98', -2.0, 19.0); near('C90', -2.0, 17.4)
near_pad('Q90', 'BZ1', net='Net-(BZ1--)', out=2.0); near_pad('D97', 'BZ1', net='Net-(BZ1--)', out=2.0); near_pad('R97', 'Q90', net='BUZZER', out=1.5)
near('TP1', -16.0, -17.5)

# 図(確かめ用): 置いた部品の courtyard、置けない所
if os.environ.get('PLOT'):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(16, 14)); ax.set_facecolor('#1b1f24')
    ax.fill(*OUTLINE.exterior.xy, color='#2a5a37'); ax.plot(*OUTLINE.exterior.xy, 'w', lw=0.8)
    for r_ in OUTLINE.interiors: ax.fill(*r_.xy, color='#1b1f24')
    ax.plot(*BAT.exterior.xy, color='#ffd23f', ls='--')
    for k in KEEP:
        for g in getattr(k, 'geoms', [k]): ax.fill(*g.exterior.xy, color='#c33', alpha=0.4)
    for r_, q in placed.items():
        if q is None: continue
        for g in getattr(q, 'geoms', [q]): ax.plot(*g.exterior.xy, color='#9cf', lw=0.7)
        c = q.centroid; ax.text(c.x, c.y, r_, fontsize=5.5, color='w', ha='center', va='center')
    for r_, x, y in FAILED: ax.plot(x, y, 'mx'); ax.text(x, y, r_, color='m', fontsize=7)
    ax.set_aspect('equal'); ax.set_xlim(-32, 47); ax.set_ylim(-36, 36); ax.grid(True, color='#444', lw=0.3)
    fig.tight_layout(); fig.savefig(os.environ['PLOT'], dpi=90)
# 部品番号: シルクに残すのはコネクタ・スイッチだけ。ほかは Fab に(小さい部品が混んでいて重なるため)
for r_, f in FP.items():
    t = f.Reference()
    if r_[:2] in ('J1', 'J2', 'J3', 'J4', 'J7', 'SW', 'TP') and not r_.startswith(('J5', 'J6')):
        t.SetLayer(pcbnew.F_SilkS); t.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8))); t.SetTextThickness(mm(0.12))
    else:
        t.SetLayer(pcbnew.B_Fab if f.IsFlipped() else pcbnew.F_Fab)
left = [r for r in FP if r not in placed]
print('置いていない:', left)
board.Save(PCB)
print('置いた', len(placed))

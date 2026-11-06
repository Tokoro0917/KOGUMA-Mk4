"""IC のまわりにコンデンサ(と、ノイズに効く小さな部品)を置き、IC ごとのグループにする(2026-11-06)
基板に部品を載せる前の準備。グループは基板の外(前の側)に並べるので、KiCad でグループごと基板に動かせる。

置き方の決まり:
- コンデンサは、つなぐ IC のピンのパッドの外に置き、そのピンのネットのパッドを IC に向ける(線を最短に)。
  もう一方(GND・PGND)のパッドは外を向くので、そこに GND のビアを打つ(ループが小さくなる)
- 小さい値(100nF など、高い周波数用)を先に、ピンのいちばん近くに置く。大きい値(10µF など)はその外か横
- 部品の外形(コートヤード)は重ねない。IC のピンの真正面から、外へ・横へずらして空いている所を探す
- 受光アンプの帰還(820k・0.5pF)は、出力と − 入力のピンの間に、辺に沿って置く(高インピーダンスの線を最短に)
- 発振子 Y1 は PH0・PH1 のピンの外に、辺に沿って置く。SMPS のインダクタ L1 は VLXSMPS のピンの外
- DC-DC の出力のコンデンサ C7 の GND のパッドのとなりに NT1(PGND と GND の1点)を置く
- エンコーダ基板のパスコン C86・C87 は、基板の上の J5・J6 の 3.3V のパッドの内側に置く(J5・J6 は位置が決まっているため)
使い方(このフォルダで): python3 place_caps.py  (gen_pcb.py で作った、部品を置く前の基板に対して使う)
"""
import os, sys, math
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, 'KOGUMA-Mk4.kicad_pcb')
mm, MM = pcbnew.FromMM, pcbnew.ToMM
board = pcbnew.LoadBoard(PCB)
FP = {f.GetReference(): f for f in board.GetFootprints()}
OX, OY = 150.0, 100.0          # 機体の (x, y) → KiCad の (OX + x, OY − y)

def pad(ref, num):
    return [p for p in FP[ref].Pads() if p.GetNumber() == num][0]

def xy(p):
    return MM(p.GetPosition().x), MM(p.GetPosition().y)

def box(ref):
    """コートヤードの箱(KiCad の座標、mm)。コートヤードのない部品はパッドの箱 + 0.25"""
    f = FP[ref]
    f.BuildCourtyardCaches()
    cy = f.GetCourtyard(pcbnew.F_CrtYd)
    if cy.OutlineCount():
        bb = cy.BBox()
        return (MM(bb.GetLeft()), MM(bb.GetTop()), MM(bb.GetRight()), MM(bb.GetBottom()))
    xs, ys = [], []
    for p in f.Pads():
        bb = p.GetBoundingBox()
        xs += [MM(bb.GetLeft()), MM(bb.GetRight())]; ys += [MM(bb.GetTop()), MM(bb.GetBottom())]
    return (min(xs) - 0.25, min(ys) - 0.25, max(xs) + 0.25, max(ys) + 0.25)

def overlap(a, b, gap=0.0):
    return a[0] < b[2] + gap and b[0] < a[2] + gap and a[1] < b[3] + gap and b[1] < a[3] + gap

def side_normal(ic, p):
    """IC の中心からパッドへの向きを、辺の外向きの単位ベクトルにする"""
    cx, cy = MM(FP[ic].GetPosition().x), MM(FP[ic].GetPosition().y)
    x, y = xy(p)
    b = box(ic); hw, hh = (b[2] - b[0]) / 2, (b[3] - b[1]) / 2
    dx, dy = (x - cx) / hw, (y - cy) / hh
    return ((1 if dx > 0 else -1), 0) if abs(dx) >= abs(dy) else (0, (1 if dy > 0 else -1))

def face(ref, num, d):
    """部品 ref のパッド num が、向き d(単位ベクトル)の側に来るように回す。2端子・3端子の部品"""
    f = FP[ref]
    for ang in (0, 90, 180, 270):
        f.SetOrientationDegrees(ang)
        ps = [xy(p) for p in f.Pads()]
        c = (sum(p[0] for p in ps) / len(ps), sum(p[1] for p in ps) / len(ps))   # パッドの中心(原点がパッドの上の部品もある)
        x, y = xy(pad(ref, num))
        v = (x - c[0], y - c[1]); L = math.hypot(*v) or 1
        if v[0] / L * d[0] + v[1] / L * d[1] > 0.99:
            return ang
    raise RuntimeError((ref, num, d))

def try_place(ref, x, y, placed):
    FP[ref].SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    b = box(ref)
    return b if not any(overlap(b, o) for o in placed.values()) else None

def place_at(ref, anchor, apin, placed, my_pin=None, mode='radial', pin2=None, gap=0.15, wlat=1.0):
    """anchor のパッド apin の外に ref を置く。my_pin は anchor のピンに向けるパッド(省略すると同じネットのパッド)
    mode: 'radial' = 辺に直角(パッドの1つをピンに向ける)、'tangent' = 辺に沿う(apin と pin2 の間)"""
    ap = pad(anchor, apin); n = side_normal(anchor, ap)
    if my_pin is None:
        my_pin = [p.GetNumber() for p in FP[ref].Pads() if p.GetNetCode() == ap.GetNetCode()][0]
    px, py = xy(ap)
    if pin2:
        qx, qy = xy(pad(anchor, pin2)); px, py = (px + qx) / 2, (py + qy) / 2
    t = (-n[1], n[0])                                   # 辺に沿う向き
    if mode == 'radial':
        face(ref, my_pin, (-n[0], -n[1]))
    else:
        tv = (qx - xy(ap)[0], qy - xy(ap)[1]); L = math.hypot(*tv); tv = (tv[0] / L, tv[1] / L)
        face(ref, my_pin, (-tv[0], -tv[1]))            # my_pin を apin の側に
    # IC のコートヤードの外から、外へ・横へずらして探す
    b0 = box(anchor)
    edge = {(1, 0): b0[2], (-1, 0): b0[0], (0, 1): b0[3], (0, -1): b0[1]}[n]
    FP[ref].SetPosition(pcbnew.VECTOR2I(0, 0)); bb = box(ref)
    half_n = (bb[2] - bb[0]) / 2 if n[0] else (bb[3] - bb[1]) / 2
    base = edge + (half_n + gap) * (n[0] + n[1])
    best = None
    for k in range(0, 60):                      # 外へ 0.25mm ずつ
        r = k * 0.25
        for j in sorted(range(-32, 33), key=abs):    # 横へ 0.25mm ずつ
            lat = j * 0.25
            cost = r + wlat * abs(lat)
            if best and cost >= best[0]:
                continue
            if n[0]:
                x, y = base + r * n[0], py + lat
            else:
                x, y = px + lat, base + r * n[1]
            b = try_place(ref, x, y, placed)
            if b:
                best = (cost, x, y, b)
        if best and best[0] <= r:
            break
    cost, x, y, b = best
    FP[ref].SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    placed[ref] = b
    return b

def cluster(name, ic, items):
    placed = {ic: box(ic)}
    for it in items:
        ref, anchor, apin = it[:3]
        kw = it[3] if len(it) > 3 else {}
        place_at(ref, anchor, apin, placed, **kw)
    return name, list(placed)

GROUPS = []
# ---------------- MCU(U4) ----------------
mcu = [
    # 置く順 = 優先の順(左の辺の 1〜17 番は混むので、ノイズに効くものから近くに置く)
    ('Y1', 'U4', '10', dict(mode='tangent', pin2='11', my_pin='1')),   # 発振子(PH0・PH1)。線を最短に
    ('C53', 'U4', '5'),                                   # VLXSMPS 220pF
    ('L1', 'U4', '5'),                                    # SMPS のインダクタ(VLXSMPS → VFBSMPS)
    ('C50', 'U4', '6'),                                   # VDDSMPS 10µF
    ('C54', 'U4', '7'),                                   # VFBSMPS 10µF
    ('C57', 'U4', '9'),                                   # VDD 100nF(ピンのとなりの VSS へ GND のビア)
    ('C52', 'U4', '16'),                                  # VDDA 100nF
    ('C58', 'U4', '22'), ('C59', 'U4', '35'), ('C60', 'U4', '51'), ('C61', 'U4', '68'),   # ほかの VDD
    ('C55', 'U4', '33'), ('C56', 'U4', '49'),            # VCAP 100nF × 2
    ('C51', 'U4', '16'),                                  # VDDA 4.7µF
    ('FB1', 'U4', '16'), ('R51', 'FB1', '2'),             # VDDA のフィルタ
    ('C64', 'U4', '1'),                                   # VBAT(VDD につなぐ。電流は小さい)
    ('C63', 'U4', '12'),                                  # NRST
    ('C62', 'U4', '68'),                                  # VDD のまとめの 4.7µF
]
# ADC のフィルタのコンデンサ(レビュー: MCU のそばに)
adc = {}
u4 = FP['U4']
for c in ('C9', 'C40', 'C23', 'C24', 'C33', 'C34'):
    net = [p for p in FP[c].Pads() if p.GetNetname() not in ('GND',)][0].GetNetCode()
    pin = [p.GetNumber() for p in u4.Pads() if p.GetNetCode() == net][0]
    mcu.append((c, 'U4', pin))
GROUPS.append(cluster('U4 MCU', 'U4', mcu))

# ---------------- 3.3V の DC-DC(U1)----------------
GROUPS.append(cluster('U1 DC-DC', 'U1', [
    ('C6', 'U1', '4'), ('C5', 'U1', '4'),                 # 入力 100nF、10µF
    ('C7', 'U1', '8'), ('C8', 'U1', '8'),                 # 出力 22µF × 2
    ('R3', 'U1', '11'),                                   # RFB
    ('NT1', 'C7', '2', dict(my_pin='1')),                 # PGND と GND の1点: C7 の GND のパッドのとなり
]))

# ---------------- モータードライバ(U2・U3)----------------
for u, c100, c10, rsr in (('U2', 'C21', 'C22', 'R21'), ('U3', 'C31', 'C32', 'R31')):
    GROUPS.append(cluster(f'{u} MP6551', u, [(c100, u, '2'), (c10, u, '2'), (rsr, u, '6')]))

# ---------------- 受光アンプ(U74・U75)----------------
def tia(u, pairs, c100, c10, extra=()):
    items = [(c100, u, '8'), (c10, u, '8')]
    for (r, c, out, inn) in pairs:                       # 帰還: 出力と − 入力の間に、辺に沿って
        items += [(r, u, out, dict(mode='tangent', pin2=inn)), (c, u, out, dict(mode='tangent', pin2=inn))]
    return items + list(extra)
def tia_pairs(u):
    out = []
    for out_pin, in_pin in (('1', '2'), ('7', '6')):
        n_in = pad(u, in_pin).GetNetCode()
        r = [f.GetReference() for f in FP.values() if f.GetReference().startswith('R7') and any(p.GetNetCode() == n_in for p in f.Pads())][0]
        c = [f.GetReference() for f in FP.values() if f.GetReference().startswith('C7') and any(p.GetNetCode() == n_in for p in f.Pads())][0]
        out.append((r, c, out_pin, in_pin))
    return out
GROUPS.append(cluster('U74 受光アンプ FL・R', 'U74', tia('U74', tia_pairs('U74'), 'C83', 'C78',
                                                        extra=[('C80', 'U74', '3'), ('R79', 'U74', '3'), ('R78', 'U74', '3')])))
GROUPS.append(cluster('U75 受光アンプ FR・L', 'U75', tia('U75', tia_pairs('U75'), 'C84', 'C79')))

# ---------------- 発光の定電流ドライバ(U70〜U73)----------------
for i in range(4):
    u = f'U7{i}'
    GROUPS.append(cluster(f'{u} NJU6080', u, [(f'C7{i}', u, '6'), (f'R7{i}', u, '3')]))

# ---------------- IMU(U76)----------------
GROUPS.append(cluster('U76 IMU', 'U76', [('C81', 'U76', '5'), ('C82', 'U76', '8')]))

# ---------------- 電源スイッチ(Q1)----------------
GROUPS.append(cluster('Q1 電源スイッチ', 'Q1', [
    ('C1', 'Q1', '4'), ('C10', 'Q1', '4'), ('R1', 'Q1', '4'), ('R2', 'Q1', '4'),
    ('D1', 'Q1', '6', dict(my_pin='1')), ('C2', 'Q1', '6'), ('C3', 'Q1', '7'), ('C4', 'Q1', '8'),
]))

# ---------------- ファン(Q40)----------------
GROUPS.append(cluster('Q40 ファン', 'Q40', [
    ('R43', 'Q40', '2'), ('R42', 'Q40', '1', dict(my_pin='1')), ('R41', 'Q40', '1'),
    ('D40', 'Q40', '3'), ('J4', 'D40', '1', dict(my_pin='1')),
    ('C42', 'J4', '1'), ('C41', 'J4', '1'),
]))

# ---------------- ブザー(BZ1)・スイッチ ----------------
GROUPS.append(cluster('BZ1 ブザー', 'BZ1', [('C91', 'BZ1', '1'), ('D97', 'BZ1', '2'), ('Q90', 'BZ1', '2', dict(my_pin='3'))]))
sw = [f.GetReference() for f in FP.values() if f.GetReference().startswith('SW') and any(p.GetNetname() == 'SW' for p in f.Pads())][0]
GROUPS.append(cluster(f'{sw} スイッチ', sw, [('C90', sw, [p.GetNumber() for p in FP[sw].Pads() if p.GetNetname() == 'SW'][0])]))

# ---------------- エンコーダ基板のパスコン(基板の上、J5・J6 の 3.3V のパッドの内側)----------------
# J5・J6 のパッドは裏(エンコーダ基板の内側と外側に2列)。内側の列の 3.3V(1番)と GND(7番)の真上に、横向きに置き、
# それぞれのパッドの上からビアで裏へ。機体の |y| 18.6(電池のホルダの壁 |y| 16.3〜17.3 から 0.57mm 離れる)
for c, j in (('C86', 'J5'), ('C87', 'J6')):
    p1 = min((p for p in FP[j].Pads() if p.GetNumber() == '1'), key=lambda p: abs(xy(p)[1] - OY))   # 内側の列
    p7 = min((p for p in FP[j].Pads() if p.GetNumber() == '7'), key=lambda p: abs(xy(p)[1] - OY))
    (x1, y1), (x7, _) = xy(p1), xy(p7)
    yc = OY - 18.6 if y1 < OY else OY + 18.6
    f = FP[c]; f.SetPosition(pcbnew.VECTOR2I(mm((x1 + x7) / 2), mm(yc)))
    face(c, '1', (1 if x1 > x7 else -1, 0))              # 3.3V のパッドを 1番の側に
    f.SetPosition(pcbnew.VECTOR2I(mm((x1 + x7) / 2), mm(yc)))

# ---------------- グループにして、基板の外(前)に並べる ----------------
for g in list(board.Groups()):
    board.Remove(g)
x0, ytop = OX + 60.0, OY - 45.0
col_x, y, wmax = x0, ytop, 0.0
for name, refs in GROUPS:
    bs = [box(r) for r in refs]
    gx0, gy0, gx1, gy1 = min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs)
    w, h = gx1 - gx0, gy1 - gy0
    if y + h > OY + 60:
        col_x += wmax + 4; y = ytop; wmax = 0
    dx, dy = col_x - gx0, y - gy0
    for r in refs:
        FP[r].Move(pcbnew.VECTOR2I(mm(dx), mm(dy)))
    g = pcbnew.PCB_GROUP(board); g.SetName(name)
    for r in refs:
        g.AddItem(FP[r])
    board.Add(g)
    y += h + 3; wmax = max(wmax, w)
# グループに入らない、まだ置かない部品: グループの右に並べる
grouped = {r for _, refs in GROUPS for r in refs}
fixed_x = (OX - 40, OX + 50)                            # 基板の上の部品(位置が決まっている)はそのまま
loose = [r for r, f in FP.items() if r not in grouped and r not in ('C86', 'C87') and not (fixed_x[0] < MM(f.GetPosition().x) < fixed_x[1])]
col_x += wmax + 6; y = ytop; wmax = 0
for r in sorted(loose):
    b = box(r); w, h = b[2] - b[0], b[3] - b[1]
    if y + h > OY + 60:
        col_x += wmax + 2; y = ytop; wmax = 0
    FP[r].Move(pcbnew.VECTOR2I(mm(col_x - b[0]), mm(y - b[1])))
    y += h + 1.0; wmax = max(wmax, w)
board.Save(PCB)
print('グループ', len(GROUPS), '部品', len(grouped), 'まだ置かない', len(loose))
for name, refs in GROUPS:
    print(' ', name, ':', ' '.join(r for r in refs[1:]))

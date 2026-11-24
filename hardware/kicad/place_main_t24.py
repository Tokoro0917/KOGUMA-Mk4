"""タイヤ24mm 用のメイン基板(KOGUMA-Mk4_t24)の部品を基板に置く(仮の配置、2026-11-23、ブランチ claude/trusting-dirac-1tdt54)
使い方(リポジトリの一番上で。KiCad 9 の Python 3.12 に shapely・numpy・scipy・matplotlib が要る):
  1. /usr/bin/python3.12 hardware/kicad/make_main_t24.py          … 基板の土台(機構で決まる部品だけ置く)
  2. (cd hardware/kicad/KOGUMA-Mk4 && /usr/bin/python3.12 place_caps.py t24)   … IC ごとにコンデンサ・抵抗を近くに並べたグループ(基板の外)
  3. /usr/bin/python3.12 hardware/kicad/place_main_t24.py         … グループと残りの部品を基板に置き、基板のファイルに書く(place.json・floorplan.png も)
決め方:
  - グループ(place_caps.py の IC ごとの塊)は、中の並びを変えずに塊のまま動かす(回すのは 90° おき、上の面だけ)
  - 要の部品・グループは FIXED に手で置く(下の説明)。ほかのグループと部品は、つながる先の近くへ1つずつ置く(グループから、つながりの多いものから)。
    置く所の値 = 各パッドから同じネットのもう置いた部品のパッドまでの距離の和(GND は小さい重み。電源のネットは同じシートの IC・コネクタのパッドだけを相手にする)。裏の面は少し損にする
  - 置いてよい所: 外形の中(コートヤードが外形の中)。上の面の電池の下(x -16.25〜6.25、y ±16)は高さ 1.2mm 以下の部品だけ。
    裏の面はモーター・マウント・ファンの囲い・壁センサのホルダの所に置かない。ファンのモーターの穴・柱・エンコーダのパッド・壁センサの足の穴をよける
座標は機体の座標(x 前、y 左)。KiCad の X = 150 + x、Y = 100 − y"""
import os, sys, json, math, subprocess
import numpy as np
import shapely
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union
from shapely.prepared import prep
from shapely import affinity

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(ROOT, '../..')
DST = os.path.join(ROOT, 'KOGUMA-Mk4_t24')
PCB = os.path.join(DST, 'KOGUMA-Mk4_t24.kicad_pcb')
PY = '/usr/bin/python3.12'
sys.path.insert(0, os.path.join(REPO, 'mechanical/vehicle')); sys.path.insert(0, os.path.join(REPO, 'docs/calc/frame'))
cwd = os.getcwd(); os.chdir(REPO)
import pcb_t24, pcb_shape as ps
os.chdir(cwd)

# ---- 手で置く部品・グループ: ref(グループならその IC)→ (x, y, 回転[°] の list か None, 面 'T'/'B', 探す半径[mm], 縁に付けるか) ----
# (x, y) は、ひとつの部品ならコートヤードの外の四角の真ん中、グループなら IC のコートヤードの真ん中。
# 半径 > 0 なら、その近くで空いている所を探す(値 = 4 × 目当てからの距離 + 0.25 × つなぐ先までの長さ)。回転が None なら 4つの向きから。
# 縁に付ける('SW1')なら、つまみ(フットプリントの +Y、0° で機体の -y)の側がコートヤードから 0.8mm 外で外形の外になる所だけ(つまみを外に出す)
# 2026-11-24 に置き直した(ユーザー: MK3 では吸引のノイズが壁センサにのったので、電池の電圧(大きい電流)は基板の後ろに集める。
# 定電流の NJU6080 はそれぞれの発光の LED の近く。全体を左右(y → −y)で線対称に)。
# 後ろの左 = 電池の入口と 3.3V の DC-DC、後ろの右 = ファン(線のパッド J4 も後ろ。ファンのモーターの線は電池の上を通して後ろへ、約 4cm。ユーザーの決定)。
# 前 = 壁センサ(受光のアンプ・定電流)、ブザー・BLE・電源スイッチ。左右の対になるもの(U2・U3、U6・U7、U74・U75、U70〜U73、J1・J4、SW2・J7)は目当てを左右対称に
FIXED = {
    # モーターの線のパッド(裏の SMD)。モーターの端子 (-12, ±1.5) から線を前へ出し、モーターとファンの囲いの間(裏 x -6.9〜-3.3)ではんだ付けする
    'J2': (-5.1, 12.0, [90], 'B', 0, False), 'J3': (-5.1, -12.0, [90], 'B', 0, False),
    # 電池の線(高さのある穴のパッド)は後ろの左。ファンの線のパッド J4 と左右対称
    'J1': (-20.0, 12.0, [90], 'T', 3, False),
    # 電源スイッチ SW1(つまみ +Y = 機体の -y が 0°)は**上の面の後ろの真ん中**、V 字の切り欠きの先の縁に、つまみを後ろ(−x、270°)へ出す(2026-11-24、ユーザー: 電源スイッチは後ろに置きたい)。
    # そのために V 字の先のモードの LED 3個を 3.5mm 前へ動かした(mechanical/vehicle/pcb_t24.py)。LED の抵抗はここに置かない(place_caps.py t24)
    'SW1': (-24.1, 0.0, [270], 'T', 2, 'SW1'),
    # デバッグの端子 J7 は後ろの右(2026-11-24)。足が裏へ突き抜けるので、裏がファンの囲い(半径 17.5)・モーターの所には置けない(前の案の電池の前の右は、真下がファンの囲いだった)
    'J7': (-27.0, -8.0, [0, 90], 'T', 6, False),
    # BOOT0 のテストパッド TP4(2026-11-23)は J7 のそば。電池から電源を入れたまま 3.3V(J7 の1番)とつなぐので、電池の下に置かない
    'TP4': (-24.0, -8.0, None, 'T', 8, False),
    # 電池の 100µF(T521D、高さ 3.1mm。2026-11-23 に 47µF から)と電源スイッチの MOSFET(1.75mm)は裏の後ろ(モーターの後ろ、x < -17.2)。Q1 は電池の線 J1 のそば
    'Q1': (-23.0, 5.0, [0, 90, 180, 270], 'B', 6, False),
    'C4': (-26.5, 16.5, [0, 90, 180, 270], 'B', 6, False),
    # MCU のグループ(約 25 × 25mm)は電池の下の真ん中。探す半径は 1mm(2026-11-23: C65・CM の終端の R24・R25・R34・R35 でグループが大きくなり、半径 12mm だと左へずれて U6 か U2 のグループが入らなくなった)
    'U4': (-4.5, 0.0, None, 'T', 1, False),
    # モータードライバは線のパッドの近く(電池の下)。モーターの電流の INA241A3(U6・U7、5mΩ のシャントを含む)は
    # ドライバの OUT1 とモーターの線の間。INA241A3IDDFR(SOT-23-THIN)は高さ 1.1mm 以下なので電池の下にも置ける(2026-11-23。それまで 1.45mm としていた)。
    # 目当てを電池の下((-7.5, ±15)・(-8, ±16)・(-6, ±16)・(-9.5, ±17.5)・(-11, ±17)・(-12, ±15))にも変えて試したが、
    # ドライバの OUT1 → シャント → モーターの線の長さ(2つの合計)は今の目当ての 22.5mm がいちばん短い(ほかは 26〜35mm か、グループがばらける)ので、目当ては電池の縁のまま
    'U2': (-9.0, 12.5, [270], 'T', 1, False), 'U3': (-9.0, -12.5, [270], 'T', 1, False),
    'U6': (-11.75, 19.0, None, 'T', 2, False), 'U7': (-11.75, -19.0, None, 'T', 2, False),
    # IMU は回転の中心(車軸の真ん中)の近く
    'U76': (0.0, 0.0, None, 'T', 12, False),
    # 3.3V の DC-DC(スイッチングのノイズ)は、壁センサから一番遠い後ろの左(電池の入口 J1 のそば)。グループは入りきらないので、ばらして近くに置く
    'U1': (-22.0, 8.0, None, 'T', 6, False),
    # ファン(Q40 のグループ)は後ろの右。ファンの電流の輪(VBAT → J4 → ファン → Q40 → R43 → PGND)を後ろで閉じ、壁センサの近くを通さない
    'Q40': (-17.0, -10.0, None, 'T', 4, False),
    # 壁センサの受光のアンプ: U74 は FL と R(左の前)、U75 は FR と L(右の前)
    'U74': (30.0, 17.5, None, 'T', 2, False), 'U75': (30.0, -17.5, None, 'T', 2, False),
    # BLE モジュール HY0020(U5)は**前の真ん中**(2026-11-24、ユーザー)。電池の下に置かない(アンテナがシールドの上の面)。縁の近くで、モーター・ファンの線から離す
    'U5': (31.0, 0.0, [90, 270], 'T', 4, False),
    # ブザーは BLE の後ろ(音の穴は前)。グループは入りきらないので、ばらして置く
    'BZ1': (25.0, 0.0, [0], 'T', 5, False),
    # 決定のスイッチ SW2 は電池の後ろ(SW1 のそば、少し右)。後ろの真ん中は SW1 とモードの LED になったので
    'SW2': (-19.5, -6.0, None, 'T', 5, False),
    # ファンの線のパッドと、ファンの電流の輪の部品(グループから外して、J4 のまわりに置く)
    'J4': (-20.0, -12.0, [90], 'T', 3, False),
    'R43': (-17.0, -20.5, None, 'T', 4, False),
    'D40': (-23.5, -12.0, None, 'T', 8, False),
    'C41': (-22.0, -17.0, None, 'T', 5, False),
    # 定電流の NJU6080 は、それぞれが動かす発光の LED(OPV332)の足の近く: U70 → D70(FL、前の左)、U73 → D73(FR、前の右)、U72 → D72(左の横)、U71 → D71(右の横)
    'U70': (19.0, 25.5, None, 'T', 3, False),
    'U73': (19.0, -25.5, None, 'T', 3, False),
    'U72': (34.0, 24.5, None, 'T', 3, False),
    'U71': (34.0, -24.5, None, 'T', 3, False),
    'R98': (-19.5, -10.0, None, 'T', 5, False),
    'C90': (-21.5, -10.0, None, 'T', 5, False),
}
EDGE_PARTS = {'SW1'}
BOTTOM_OK = {'C4', 'Q1', 'J2', 'J3'}     # 裏の面に置いてよい部品(手ではんだ付け)。ほかは上の面だけ
WHEELS = unary_union([box(-12.5, 22.0, 12.5, 40.0), box(-12.5, -40.0, 12.5, -22.0)])     # タイヤ・71T(つまみを向けない)
ORDER = ['J2', 'J3', 'J1', 'J4', 'SW1', 'SW2', 'R98', 'J7', 'TP4', 'U5', 'BZ1', 'Q1', 'C4', 'U2', 'U3', 'U6', 'U7', 'U1', 'R43', 'D40', 'C41', 'Q40', 'U4', 'U76', 'U74', 'U75', 'U70', 'U73', 'U72', 'U71']
BATTERY = box(-16.25, -16.0, 6.25, 16.0)
H_MAX_BAT = 1.2
# 部品の高さ(最大、mm)。フットプリントの名前の一部で引く
# 線をはんだ付けするパッド(SolderWire)は、線とはんだで 1.2mm を超えるので 2.0 とする(電池の下に置かない)
HEIGHT = [('C_0603', 0.9), ('R_0603', 0.55), ('C_0402', 0.7), ('R_0402', 0.4), ('L_0603', 0.95), ('C_0805', 1.25), ('C_1206', 1.8), ('R_1206', 0.6), ('CP_EIA-7343', 3.1),
          ('SOIC-8', 1.75), ('SOT-23-8', 1.1), ('SOT-23-6', 1.45), ('SOT-23', 1.2), ('VSSOP-8', 1.1), ('LGA-14', 0.86), ('QFN-68', 1.0), ('MPS_QFN', 1.0),
          ('LXDC55', 1.0), ('DFE201610', 1.0), ('CSTNE', 1.0), ('D_SMF', 1.08), ('SOD-123F', 1.08), ('SOD-323', 1.1), ('LED_0402', 0.5),
          ('LED_0603', 0.8), ('TestPoint', 0.1), ('SolderWire', 2.0), ('PinHeader', 6.0), ('SSSS8', 1.4), ('TVAF06', 2.0),
          ('SMT-0540', 2.0), ('NetTie', 0.05)]
THIN = {'C22': 0.95, 'C32': 0.95, 'U5': 9.9}      # U5(BLE、高さ 1.05mm)はアンテナの上に電池が来ないよう、電池の下に置かない(高さの決まりで止める)。モータードライバの VBAT の 10µF 25V(0805)は厚さ 0.85mm の品(村田 GRM219 系など)にして、ドライバのすぐ横(電池の下)に置く
def height(fp, ref=None):
    if ref in THIN:
        return THIN[ref]
    for k, h in HEIGHT:
        if k in fp:
            return h
    return 9.9
# 裏の面に置けない所(機構)
UNDER = unary_union([box(-17.2, -22.1, -6.9, 22.1),                                   # モーター(x -17.2〜-6.9。基板の下面まで 0.25mm)
                     box(-23.6, 15.3, 10.6, 22.6), box(-23.6, -22.6, 10.6, -15.3),     # マウント
                     Point(ps.FAN).buffer(17.8, 64)]                                    # ファンの囲い(半径 17.5)
                    + [ps.holder(k).buffer(0.3, join_style=2) for k in ps.SENS])
# 両方の面でよける所
BOTH = unary_union([Point(ps.FAN).buffer(ps.HUB_HOLE + 0.3, 64)] + [Point(p).buffer(2.6) for p in ps.SCREWS])
TOP_ONLY = unary_union([box(x0 - 0.3, y0 - 0.3, x1 + 0.3, y1 + 0.3) for (x0, x1, y0, y1) in ps.ENC])
SIGNAL_W, GND_W, BOTTOM_COST = 1.0, 0.12, 2.5
POWER = {'+3V3', '+3V3A', 'VBAT', '/電源/BAT+', 'PGND'}
GNDS = {'GND', 'PGND'}
ACTIVE = ('U', 'Q', 'J', 'Y', 'D7', 'SW', 'BZ', 'FB')      # 電源のネットで相手にする部品(IC・コネクタ・発振子・壁センサなど)

DUMP = r'''
import pcbnew, json, sys
b = pcbnew.LoadBoard(sys.argv[1])
out = {}
for fp in b.GetFootprints():
    ref = fp.GetReference()
    pos = fp.GetPosition()
    d = dict(fp=fp.GetFPIDAsString(), sheet=fp.GetSheetname(), x=pos.x / 1e6 - 150, y=100 - pos.y / 1e6, rot=fp.GetOrientationDegrees(), flip=fp.IsFlipped(), var={})
    def geo(ox=0.0, oy=0.0):
        cy = []
        for L in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
            poly = fp.GetCourtyard(L)
            for i in range(poly.OutlineCount()):
                o = poly.Outline(i); cy.append([(o.CPoint(j).x / 1e6 - ox, oy - o.CPoint(j).y / 1e6) for j in range(o.PointCount())])
        pads = []
        for p in fp.Pads():
            bb = p.GetBoundingBox()
            pads.append(dict(n=p.GetNumber(), x=p.GetPosition().x / 1e6 - ox, y=oy - p.GetPosition().y / 1e6, net=p.GetNetname(),
                             th=p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH),
                             bb=(bb.GetLeft() / 1e6 - ox, oy - bb.GetBottom() / 1e6, bb.GetRight() / 1e6 - ox, oy - bb.GetTop() / 1e6)))
        return cy, pads
    d['cy'], d['pads'] = geo(150.0, 100.0)          # 今の位置で(機体の座標に)
    fp.SetPosition(pcbnew.VECTOR2I(0, 0))
    for side in ('T', 'B'):
        if fp.IsFlipped() != (side == 'B'):
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        for r in (0, 90, 180, 270):
            fp.SetOrientationDegrees(r)
            d['var'][f'{side}{r}'] = geo()
    out[ref] = d
groups = [(g.GetName(), [it.Cast().GetReference() for it in g.GetItems() if hasattr(it.Cast(), 'GetReference')]) for g in b.Groups()]
json.dump(dict(fps=out, groups=groups), open(sys.argv[2], 'w'))
'''

APPLY = r'''
import pcbnew, json, sys
b = pcbnew.LoadBoard(sys.argv[1])
P = json.load(open(sys.argv[2]))
for fp in b.GetFootprints():
    q = P.get(fp.GetReference())
    if q is None:
        continue
    if fp.IsFlipped() != (q['side'] == 'B'):
        fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(150 + q['x']), pcbnew.FromMM(100 - q['y'])))
    fp.SetOrientationDegrees(q['rot'])
b.Save(sys.argv[1])
'''

def dump():
    path = os.path.join(DST, 'fps.json')
    subprocess.run([PY, '-c', DUMP, PCB, path], check=True, capture_output=True)
    d = json.load(open(path)); os.remove(path)
    return d['fps'], d['groups']

def polys(cy):
    out = [Polygon(c).buffer(0) for c in cy if len(c) >= 3]
    return unary_union(out) if out else None

def pad_poly(pads):
    """コートヤードのない部品(ネットタイ NT1 など)は、パッドの箱 + 0.25mm"""
    if not pads:
        return None
    return unary_union([box(*p['bb']) for p in pads]).envelope.buffer(0.25, join_style=2)

def rot_pt(x, y, a):
    c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
    return x * c - y * s, x * s + y * c

class Unit:
    """部品1つか、グループ(塊のまま動かす)。geo(side, rot) は基準点からの相対の [(ref, コートヤード, パッドの list)]"""
    def __init__(self, name, refs, F, anchor):
        self.name, self.refs, self.F, self.anchor = name, refs, F, anchor
        self.group = len(refs) > 1
        if self.group:     # 基準点 = IC のコートヤードの真ん中
            self.px, self.py = polys(F[anchor]['cy']).envelope.centroid.coords[0]
        self._cache = {}
        self.hmap = {r: height(F[r]['fp'], r) for r in refs}
    def sides(self):
        # 裏の面に置いてよいのは、手ではんだ付けする大きい部品・線のパッド・テストパッドだけ(JLC は上の面だけで組み立てる。2026-11-24)
        if self.group:
            return ('T',)
        if self.anchor in BOTTOM_OK or self.anchor.startswith('TP'):
            return ('T', 'B')
        return ('T',)
    def geo(self, side, rot):
        k = (side, rot)
        if k in self._cache:
            return self._cache[k]
        if not self.group:
            cy, pads = self.F[self.anchor]['var'][f'{side}{rot}']
            items = [(self.anchor, polys(cy) or pad_poly(pads), [dict(p, ref=self.anchor) for p in pads])]
        else:
            items = []
            for r in self.refs:
                d = self.F[r]
                pg = polys(d['cy']) or pad_poly(d['pads'])
                pg = None if pg is None else affinity.rotate(affinity.translate(pg, -self.px, -self.py), rot, origin=(0, 0))
                pads = []
                for p in d['pads']:
                    x, y = rot_pt(p['x'] - self.px, p['y'] - self.py, rot)
                    bb = affinity.rotate(affinity.translate(box(*p['bb']), -self.px, -self.py), rot, origin=(0, 0))
                    pads.append(dict(p, x=x, y=y, bb=bb.bounds, ref=r))
                items.append((r, pg, pads))
        self._cache[k] = items
        return items
    def center_offset(self, side, rot):
        """(x, y) の決まり(ひとつならコートヤードの外の四角の真ん中、グループなら IC の真ん中 = 基準点)に合わせるずれ"""
        if self.group:
            return 0.0, 0.0
        pg = unary_union([g for _, g, _ in self.geo(side, rot) if g is not None])
        return pg.envelope.centroid.coords[0]
    def final(self, side, rot, X, Y):
        """各部品の最後の位置と向き(KiCad の向き)"""
        out = {}
        for r in self.refs:
            if not self.group:
                out[r] = dict(x=round(X, 4), y=round(Y, 4), rot=float(rot), side=side)
            else:
                d = self.F[r]
                x, y = rot_pt(d['x'] - self.px, d['y'] - self.py, rot)
                out[r] = dict(x=round(X + x, 4), y=round(Y + y, 4), rot=float((d['rot'] + rot + 180) % 360 - 180), side='T')
        return out

def plan():
    F, G = dump()
    board = ps.outline()
    board = unary_union([Polygon(g.exterior, g.interiors) for g in getattr(board, 'geoms', [board])])
    board = board.difference(unary_union([ps.slot(k) for k in ps.SENS]))       # ほぞの穴
    onboard = {r for r, d in F.items() if -40 < d['x'] < 50 and abs(d['y']) < 40}   # 機構で決まる部品・LED とその抵抗・C86・C87(make_main_t24・place_caps が置いた)
    units, unit_of = [], {}
    for name, refs in G:
        if any(r in onboard for r in refs):
            continue
        u = Unit(name, refs, F, name.split()[0]); units.append(u)
        for r in refs:
            unit_of[r] = u
    for r in F:
        if r not in onboard and r not in unit_of:
            u = Unit(r, [r], F, r); units.append(u); unit_of[r] = u
    for ref in FIXED:       # グループの中の部品を手で置くなら、グループから外す。裏に置くグループ(Q1)はばらす(グループは上の面だけ)
        u = unit_of.get(ref)
        if u is not None and u.group and u.anchor == ref and FIXED[ref][3] == 'B':
            units.remove(u)
            for r in u.refs:
                v = Unit(r, [r], F, r); units.append(v); unit_of[r] = v
            print('ばらしたグループ(裏に置くため):', u.name)
            continue
        if u is not None and u.group and u.anchor != ref:
            units.remove(u)
            g2 = Unit(u.name, [r for r in u.refs if r != ref], F, u.anchor); units.append(g2)
            for r in g2.refs:
                unit_of[r] = g2
            v = Unit(ref, [ref], F, ref); units.append(v); unit_of[ref] = v
    by_anchor = {u.anchor: u for u in units}
    placed = {}     # ref → dict(side, poly, pads, mech)
    for r in onboard:
        d = F[r]
        placed[r] = dict(side='B' if d['flip'] else 'T', poly=polys(d['cy']), pads=[dict(p, ref=r) for p in d['pads']], mech=True)
    result = {}
    def obstacles(side):
        obs = [BOTH] + ([TOP_ONLY] if side == 'T' else [UNDER])
        for r, q in placed.items():
            if q['poly'] is not None and q['side'] == side:
                obs.append(q['poly'])
            for p in q['pads']:
                if p['th']:
                    obs.append(box(*p['bb']).buffer(0.25, join_style=2))
        return unary_union(obs)
    def targets(net, u):
        pts = []
        sheets = {F[x]['sheet'] for x in u.refs}
        for r, q in placed.items():
            if r in u.refs:
                continue
            if net in POWER and (not r.startswith(ACTIVE) or F[r]['sheet'] not in sheets):    # 電源のネット: 同じシートの IC・コネクタだけ
                continue
            pts += [(p['x'], p['y']) for p in q['pads'] if p['net'] == net]
        return np.array(pts) if pts else None
    def weight(net):
        return GND_W if net in GNDS else SIGNAL_W
    def ext_pads(u, side, rot):
        return [p for _, _, pads in u.geo(side, rot) for p in pads if p['net'] and not p['net'].startswith('unconnected')]
    def cost_grid(u, side, rot, X, Y):
        c = np.zeros_like(X, dtype=float)
        tcache = {}
        for p in ext_pads(u, side, rot):
            n = p['net']
            if n not in tcache:
                tcache[n] = targets(n, u)
            t = tcache[n]
            if t is None:
                continue
            px, py = X + p['x'], Y + p['y']
            c += weight(n) * np.min(np.hypot(px[..., None] - t[:, 0], py[..., None] - t[:, 1]), axis=-1)
        return c
    def put(u, side, rot, X, Y):
        for r, g, pads in u.geo(side, rot):
            placed[r] = dict(side=side, poly=None if g is None else affinity.translate(g, X, Y),
                             pads=[dict(p, x=p['x'] + X, y=p['y'] + Y, bb=(p['bb'][0] + X, p['bb'][1] + Y, p['bb'][2] + X, p['bb'][3] + Y)) for p in pads], mech=False)
        result.update(u.final(side, rot, X, Y))
    def fits(u, side, rot, X, Y, pf, pb):
        for r, g, pads in u.geo(side, rot):
            if g is None:
                continue
            if r in EDGE_PARTS:      # つまみ(コートヤードの +Y の 1.4mm より先)は外形の外に出てよい
                # 裏の面では左右が裏返るので、回転の向きが逆になる(2026-11-24。SW1 を裏に置けるようにした)
                if side == 'B':
                    g = g.difference(affinity.rotate(box(-10, -10, 10, -1.4), -rot, origin=(0, 0)))
                else:
                    g = g.difference(affinity.rotate(box(-10, -10, 10, -1.4), rot, origin=(0, 0)))
            gg = affinity.translate(g, X, Y)
            if not pf[side].contains(gg.buffer(0.01, join_style=2)):
                return False
            other = 'T' if side == 'B' else 'B'      # 穴(足を通す穴・位置決めの穴)は反対の面にも出るので、反対の面も空いているか見る(2026-11-24)
            for p in pads:
                if p['th']:
                    hole = box(p['bb'][0] + X, p['bb'][1] + Y, p['bb'][2] + X, p['bb'][3] + Y).buffer(0.25, join_style=2)
                    if not pf[other].contains(hole):
                        return False
            if side == 'T' and u.hmap[r] > H_MAX_BAT and pb.intersects(gg):
                return False
        return True
    xs = np.arange(-30.0, 46.0, 0.25); ys = np.arange(-34.0, 34.25, 0.25)
    X, Y = np.meshgrid(xs, ys)
    free = {s_: board.buffer(-0.05, join_style=2).difference(obstacles(s_)) for s_ in ('T', 'B')}     # 縁から 0.05mm 内側(1005 のコートヤードはパッドから 0.18mm しかなく、銅と縁 0.2mm に足りないため)
    edge = board.boundary
    def place(u, cands, need_edge=False):
        """cands = [(値の格子, 面, 回転)]。値の小さい順に、置ける所を探す"""
        allc = np.concatenate([c.ravel() for c, _, _ in cands])
        idx = np.argsort(allc, kind='stable'); idx = idx[np.isfinite(allc[idx])]
        n = X.size
        pf = {s_: prep(free[s_]) for s_ in ('T', 'B')}; pb = prep(BATTERY)
        for k in idx:
            ci, j_ = divmod(int(k), n)
            _, side, rot = cands[ci]
            x, y = float(X.flat[j_]), float(Y.flat[j_])
            if not fits(u, side, rot, x, y, pf, pb):
                continue
            if need_edge:      # 本体の前の面(原点から 1.3mm)が縁から 1.3mm 以内で、つまみ(4.4mm まで)は外へ
                dx, dy = math.sin(math.radians(rot)), -math.cos(math.radians(rot))      # つまみの向き(機体の座標)
                if side == 'B':      # 裏の面では左右が裏返るので、つまみの向きの x が逆になる
                    dx = -dx
                if board.contains(Point(x + dx * 2.6, y + dy * 2.6)) or not board.contains(Point(x + dx * 1.0, y + dy * 1.0)):
                    continue
                if WHEELS.contains(Point(x + dx * 4.4, y + dy * 4.4)):
                    continue
            put(u, side, rot, x, y)
            for r in u.refs:
                q = placed[r]
                if q['poly'] is not None:
                    free[side] = free[side].difference(q['poly'])
                for p in q['pads']:
                    if p['th']:
                        o = box(*p['bb']).buffer(0.25, join_style=2)
                        free['T'] = free['T'].difference(o); free['B'] = free['B'].difference(o)
            return True
        return False
    dissolved = []
    def dissolve(u):
        """置けないグループは、ばらして部品ごとに(裏の面も使って)置く。IC を先に"""
        if not u.group:
            print('置けない:', u.name)
            return
        dissolved.append(u.name)
        if u in units:
            units.remove(u)
        for r in u.refs:
            v = Unit(r, [r], F, r); units.append(v); unit_of[r] = v
    # 1. 手で置くもの(目当ての近くで)
    for ref in ORDER:
        x, y, rots, side, R, need_edge = FIXED[ref]
        u = by_anchor[ref]
        cands = []
        for rot in (rots or (0, 90, 180, 270)):
            rot = int(rot) % 360
            cx, cy_ = u.center_offset(side, rot)
            d = np.hypot(X - (x - cx), Y - (y - cy_))
            if R == 0:
                c = np.where(d < 0.13, 0.0, np.inf)
            else:
                c = np.where(d <= R, 4.0 * d + 0.25 * cost_grid(u, side, rot, X, Y), np.inf)
            cands.append((c, side, rot))
        if R == 0:      # ちょうどその位置に(格子からずれないよう、格子の点を目当てに置き換える)
            cands = []
            for rot in (rots or (0, 90, 180, 270)):
                rot = int(rot) % 360
                cx, cy_ = u.center_offset(side, rot)
                put(u, side, rot, round(x - cx, 3), round(y - cy_, 3))
                break
            for r in u.refs:
                q = placed[r]
                if q['poly'] is not None:
                    free[side] = free[side].difference(q['poly'])
        else:
            if not place(u, cands, need_edge):
                dissolve(u)
        if u in units:
            units.remove(u)
    # 2. ほかのグループと部品
    def attach(u):
        return sum(weight(p['net']) for p in ext_pads(u, 'T', 0) if targets(p['net'], u) is not None) + (100 if u.group else 0) + (50 if u.anchor[0] in 'UQ' or u.anchor.startswith('C4') else 0)
    while units:
        units.sort(key=lambda u: (-attach(u), u.name))
        u = units.pop(0)
        cands = []
        for side in u.sides():
            inside = shapely.contains_xy(free[side], X, Y) if not u.group else np.ones_like(X, dtype=bool)
            for rot in (0, 90, 180, 270):
                c = cost_grid(u, side, rot, X, Y) + (BOTTOM_COST if side == 'B' else 0.0)
                cands.append((np.where(inside, c, np.inf), side, rot))
        if not place(u, cands):
            dissolve(u)
    print('ばらしたグループ:', dissolved if dissolved else 'なし')
    # 3. 確かめ: 重なり・外形・電池の下の高さ・裏の機構・よける所
    bad = []
    items = [(r, q) for r, q in placed.items() if q['poly'] is not None and not r.startswith('H')]
    for i, (r1, q1) in enumerate(items):
        for r2, q2 in items[i + 1:]:
            if q1['side'] == q2['side'] and q1['poly'].intersection(q2['poly']).area > 1e-4:
                bad.append(f'{r1}-{r2}')
    for r, q in items:
        if q['mech']:
            continue
        if r not in EDGE_PARTS and not board.contains(q['poly']):
            bad.append(f'{r} が外形の外')
        if q['side'] == 'T' and height(F[r]['fp'], r) > H_MAX_BAT and BATTERY.intersection(q['poly']).area > 1e-4:
            bad.append(f'{r} が電池の下(高さ {height(F[r]["fp"], r)}mm)')
        if q['side'] == 'B' and UNDER.intersection(q['poly']).area > 1e-4:
            bad.append(f'{r} が裏の機構に当たる')
        if BOTH.intersection(q['poly']).area > 1e-4 or (q['side'] == 'T' and TOP_ONLY.intersection(q['poly']).area > 1e-4):
            bad.append(f'{r} がよける所に当たる')
    print('重なり・はみ出し:', bad if bad else 'なし')
    return F, G, board, placed, result

def mst(pts):
    """点の最小全域木の長さ(ネットの線の長さの目安)"""
    if len(pts) < 2:
        return 0.0
    pts = np.array(pts); n = len(pts); used = np.zeros(n, bool); used[0] = True
    d = np.hypot(*(pts - pts[0]).T); L = 0.0
    for _ in range(n - 1):
        d2 = np.where(used, np.inf, d); j = int(np.argmin(d2)); L += d2[j]; used[j] = True
        d = np.minimum(d, np.hypot(*(pts - pts[j]).T))
    return L

def draw(F, G, board, placed, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import logging; logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)
    plt.rcParams['font.family'] = 'WenQuanYi Zen Hei'; plt.rcParams['axes.unicode_minus'] = False
    frame = ps.dz.outline(0)
    fig, axs = plt.subplots(1, 2, figsize=(20, 9.6))
    colors = {'/MCU/': '#4e79a7', '/センサ/': '#59a14f', '/モーター/': '#e15759', '/電源/': '#f28e2b', '/表示・通信/': '#b07aa1'}
    for ax, side, title in ((axs[0], 'T', '上の面'), (axs[1], 'B', '裏の面(上から透かして見た図。裏から見ると左右が逆)')):
        ax.fill(*frame.exterior.xy, color='#f0f0f0', ec='#aaa', lw=0.6)
        for g in getattr(board, 'geoms', [board]):
            ax.fill(*g.exterior.xy, color='#dfeee2', ec='k', lw=1.0)
            for r_ in g.interiors:
                ax.fill(*r_.xy, color='#f0f0f0', ec='k', lw=0.6)
        if side == 'T':
            ax.fill(*BATTERY.exterior.xy, fill=False, hatch='//', ec='#b8860b', lw=0.8)
            ax.text(-5, -15.3, '電池の下: 高さ 1.2mm まで', fontsize=8, color='#8b6508', ha='center')
        else:
            for g in getattr(UNDER, 'geoms', [UNDER]):
                ax.fill(*g.exterior.xy, fill=False, hatch='\\\\', ec='#8a5cc7', lw=0.6)
            ax.text(-12, 0, 'モーター', fontsize=8, color='#5b3a8c', ha='center', rotation=90)
            ax.text(14.2, -12, 'ファンの囲い', fontsize=8, color='#5b3a8c', ha='center')
        for name, refs in G:      # グループの枠
            pg = [placed[r]['poly'] for r in refs if r in placed and placed[r]['poly'] is not None and placed[r]['side'] == side]
            if len(pg) > 2 and not name.endswith('LED'):
                env = unary_union(pg).buffer(0.4, join_style=2).envelope
                ax.plot(*env.exterior.xy, color='#555', lw=0.6, ls=':')
        for r, q in placed.items():
            if r.startswith('H'):
                continue
            col = colors.get(F[r].get('sheet'), '#888')
            if q['side'] == side and q['poly'] is not None:
                for g in getattr(q['poly'], 'geoms', [q['poly']]):
                    ax.fill(*g.exterior.xy, color=col, alpha=0.35 if q['mech'] else 0.55, ec=col, lw=0.6)
                c = q['poly'].centroid
                ax.text(c.x, c.y, r, fontsize=6.5 if q['poly'].area > 12 else 4.4, ha='center', va='center')
            for p in q['pads']:
                if p['th'] or q['side'] == side:
                    x0, y0, x1, y1 = p['bb']
                    ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, color='#c08a00' if not p['th'] else '#7a5500', lw=0))
        ax.set_aspect('equal'); ax.set_xlim(-33, 48); ax.set_ylim(-37, 37); ax.set_title(title, fontsize=12)
        ax.set_xlabel('x [mm](前 →)'); ax.set_ylabel('y [mm](左 ↑)'); ax.grid(alpha=0.15)
    hs = [plt.Rectangle((0, 0), 1, 1, color=c, alpha=0.6) for c in colors.values()]
    fig.legend(hs + [plt.Line2D([], [], color='#555', ls=':')], [s.strip('/') for s in colors] + ['IC ごとのグループ'], loc='upper center', ncol=6, fontsize=10, bbox_to_anchor=(0.5, 0.96))
    fig.suptitle('KOGUMA-Mk4_t24 メイン基板の仮の配置(hardware/kicad/place_main_t24.py)', fontsize=13)
    fig.subplots_adjust(left=0.04, right=0.99, bottom=0.07, top=0.9, wspace=0.08)
    fig.savefig(path, dpi=90)

if __name__ == '__main__':
    F, G, board, placed, result = plan()
    pj = os.path.join(DST, 'place.json')
    json.dump(result, open(pj, 'w'), indent=0, ensure_ascii=False, sort_keys=True)
    subprocess.run([PY, '-c', APPLY, PCB, pj], check=True, capture_output=True)
    nets = {}
    for r, q in placed.items():
        for p in q['pads']:
            if p['net'] and not p['net'].startswith('unconnected'):
                nets.setdefault(p['net'], []).append((p['x'], p['y']))
    L = {n: mst(v) for n, v in nets.items()}
    sig = sum(v for n, v in L.items() if n not in POWER and n not in GNDS)
    nT = sum(1 for q in result.values() if q['side'] == 'T'); nB = len(result) - nT
    bat = sum(1 for r, q in placed.items() if not q['mech'] and q['side'] == 'T' and q['poly'] is not None and BATTERY.contains(q['poly'].centroid))
    print(f'置いた部品 {len(result)}(上 {nT}・裏 {nB}、電池の下 {bat})、信号のネットの長さの目安 合計 {sig:.0f}mm')
    for n, v in sorted(L.items(), key=lambda kv: -kv[1])[:12]:
        print(f'  {n:24s} {v:6.1f}mm')
    print('裏の面:', sorted(r for r, q in result.items() if q['side'] == 'B'))
    draw(F, G, board, placed, os.path.join(DST, 'floorplan.png'))

"""タイヤ24mm 用のメイン基板(KOGUMA-Mk4_t24)の部品の仮の配置(2026-11-23、ブランチ claude/trusting-dirac-1tdt54)
使い方(リポジトリの一番上で):
  1. /usr/bin/python3.12 hardware/kicad/make_main_t24.py   … 基板の土台(機構で決まる部品だけ置く)
  2. python3 hardware/kicad/place_main_t24.py              … 部品の置き場所を決めて KOGUMA-Mk4_t24/place.json と floorplan.png に書く
  3. /usr/bin/python3.12 hardware/kicad/make_main_t24.py   … place.json のとおりに置き直す
決め方:
  - 回路の要の部品(MCU・IMU・モータードライバ・電源・アンプ・線のパッド)は FIXED に手で置く(下の説明)
  - ほかの部品(抵抗・コンデンサなど)は、つながる先の近くへ1個ずつ置く(つながりの多いものから)。
    置く所の値 = 各パッドから同じネットの置いた部品のパッドまでの距離の和(GND は小さい重み。電源のネットは IC・コネクタのパッドだけを相手にする)。裏の面は少し損にする
  - 置いてよい所: 外形の中(コートヤードが外形の中)。上の面の電池の下(x -16.25〜6.25、y ±16)は高さ 1.2mm 以下の部品だけ。
    裏の面はモーター・マウント・ファンの囲い・壁センサのホルダの所に置かない。ファンのモーターの穴・柱・エンコーダのパッド・壁センサの足の穴をよける
座標は機体の座標(x 前、y 左)。KiCad の X = 150 + x、Y = 100 − y"""
import os, sys, json, math, subprocess
import numpy as np
from shapely.geometry import Polygon, Point, box, MultiPolygon
from shapely.ops import unary_union
from shapely.prepared import prep
from shapely import affinity

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(ROOT, '../..')
DST = os.path.join(ROOT, 'KOGUMA-Mk4_t24')
PCB = os.path.join(DST, 'KOGUMA-Mk4_t24.kicad_pcb')
sys.path.insert(0, os.path.join(REPO, 'mechanical/vehicle')); sys.path.insert(0, os.path.join(REPO, 'docs/calc/frame'))
cwd = os.getcwd(); os.chdir(REPO)
import pcb_t24, pcb_shape as ps
os.chdir(cwd)

# ---- 手で置く部品: ref → (x, y, 回転[°], 面 'T'/'B')。(x, y) はコートヤードの外の四角の真ん中 ----
FIXED = {
    # MCU は電池の下の後ろ寄り(真下はモーター。パスコンは上の面に)。回転はつなぐ先までの長さで決める(None)
    'U4': (-11.1, 0.0, None, 'T'),
    # IMU は回転の中心(車軸の真ん中)の近く
    'U76': (1.0, 0.0, None, 'T'),
    # モーターの線のパッド: モーターの端子 (-12, ±1.5) から線を前へ出し、モーターとファンの囲いの間(裏の面 x -6.9〜-3.3)で下から通す
    'J2': (-4.85, 4.7, 90.0, 'T'), 'J3': (-4.85, -4.7, 90.0, 'T'),
    # モータードライバは線のパッドのすぐ前
    'U2': (-1.0, 7.4, None, 'T'), 'U3': (-1.0, -7.4, None, 'T'),
    # 電源: 電池の線(J1)・電源スイッチの MOSFET(Q1)・大きいコンデンサ(C4)は高いので、電池の後ろ(x -22〜-16.25)
    'J1': (-19.3, 10.2, 90.0, 'T'), 'C4': (-19.2, 0.0, 90.0, 'T'), 'Q1': (-19.25, -9.6, 90.0, 'T'),
    # 3.3V の SMPS(高さ 1.0mm)は電池の下の前寄り
    'U1': (2.8, 12.8, None, 'T'),
    # 壁センサの受光のアンプ: U74 は FL と R(左の前)、U75 は FR と L(右の前)
    'U74': (31.0, 18.0, None, 'T'), 'U75': (31.0, -18.0, None, 'T'),
    # ファンの線のパッドはファンのモーターの穴の横
    'J4': (14.2, 10.2, 0.0, 'T'),
    # デバッグの端子(高い)は後ろの右の羽
    'J7': (-24.6, -9.0, 0.0, 'T'),
    # 電源の LED は後ろの左の羽(UI の LED のそば)
    'D2': (-25.6, 10.6, 90.0, 'T'),
}
# フットプリントがまだない部品の場所(仮に取っておく): ref → (x0, y0, x1, y1, 面)
RESERVE = {
    'SW1': (-29.0, 17.6, -23.8, 22.2, 'T'),      # 電源スイッチ(SSSS810701)。左の後ろの縁、つまみを外へ
    'SW2': (-29.0, -22.2, -23.8, -17.6, 'T'),    # スイッチ(TVAF06-A020B-R)。右の後ろの縁
    'BZ1': (28.6, -2.8, 34.2, 2.8, 'T'),         # ブザー(SMT-0540-S-R、5 × 5mm)。前の真ん中(前の縁は y 0 で x 37)
}
BATTERY = box(-16.25, -16.0, 6.25, 16.0)
H_MAX_BAT = 1.2
# 部品の高さ(最大、mm)。フットプリントの名前の一部で引く
HEIGHT = [('C_0603', 0.9), ('R_0603', 0.55), ('L_0603', 0.95), ('C_0805', 1.25), ('C_1206', 1.8), ('R_1206', 0.6), ('CP_EIA-7343', 2.0),
          ('SOIC-8', 1.75), ('SOT-23-6', 1.45), ('SOT-23', 1.2), ('VSSOP-8', 1.1), ('LGA-14', 0.86), ('QFN-68', 1.0), ('MPS_QFN', 1.0),
          ('LXDC55', 1.0), ('DFE201610', 1.0), ('CSTNE', 1.0), ('D_SMF', 1.08), ('SOD-123F', 1.08), ('SOD-323', 1.1), ('LED_0402', 0.5),
          ('LED_0603', 0.8), ('TestPoint', 0.1), ('SolderWire', 1.0), ('PinHeader', 6.0)]
THIN = {'C22': 0.95, 'C32': 0.95}      # モータードライバの VBAT の 10µF 25V(0805)は厚さ 0.85mm の品(村田 GRM219 系など)にして、ドライバのすぐ横(電池の下)に置く
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
TOP_ONLY = unary_union([box(x0 - 0.3, y0 - 0.3, x1 + 0.3, y1 + 0.3) for (x0, x1, y0, y1) in ps.ENC]
                       + [box(a, b_, c, d) for (a, b_, c, d, s) in RESERVE.values() if s == 'T'])
SIGNAL_W, GND_W, BOTTOM_COST = 1.0, 0.12, 2.5
POWER = {'+3V3', 'VBAT', '/電源/BAT+'}
ACTIVE = ('U', 'Q', 'J', 'Y', 'D7')      # 電源のネットで相手にする部品(IC・コネクタ・発振子・壁センサ)

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
    keep = (fp.GetPosition(), fp.GetOrientationDegrees(), fp.IsFlipped())
    fp.SetPosition(pcbnew.VECTOR2I(0, 0))
    for side in ('T', 'B'):
        if fp.IsFlipped() != (side == 'B'):
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        for r in (0, 90, 180, 270):
            fp.SetOrientationDegrees(r)
            d['var'][f'{side}{r}'] = geo()
    out[ref] = d
json.dump(out, open(sys.argv[2], 'w'))
'''

def dump():
    path = os.path.join(DST, 'fps.json')
    subprocess.run(['/usr/bin/python3.12', '-c', DUMP, PCB, path], check=True, capture_output=True)
    d = json.load(open(path)); os.remove(path)
    return d

def poly_of(cy, dx=0.0, dy=0.0):
    ps_ = [Polygon([(x + dx, y + dy) for x, y in c]).buffer(0) for c in cy if len(c) >= 3]
    return unary_union(ps_) if ps_ else None

def pads_of(pads, dx=0.0, dy=0.0):
    return [dict(p, x=p['x'] + dx, y=p['y'] + dy, bb=(p['bb'][0] + dx, p['bb'][1] + dy, p['bb'][2] + dx, p['bb'][3] + dy)) for p in pads]

def plan():
    F = dump()
    board = ps.outline()
    board = unary_union([Polygon(g.exterior, g.interiors) for g in getattr(board, 'geoms', [board])])
    board = board.difference(unary_union([ps.slot(k) for k in ps.SENS]))       # ほぞの穴
    placed = {}     # ref → dict(side, rot, x, y, poly, pads)
    fixed_mech = [r for r in F if r[0] == 'H' or r in ('J5', 'J6') or r.startswith('D7') or r in ('D90', 'D91', 'D92', 'D93', 'D94', 'D95', 'D96')]
    for r in fixed_mech:
        d = F[r]
        placed[r] = dict(side='B' if d['flip'] else 'T', rot=d['rot'], x=d['x'], y=d['y'], poly=poly_of(d['cy']), pads=d['pads'], mech=True)
    th_all = []
    def obstacles(side):
        obs = [BOTH] + ([TOP_ONLY] if side == 'T' else [UNDER])
        for r, q in placed.items():
            if q['poly'] is not None and (q['side'] == side):
                obs.append(q['poly'])
            for p in q['pads']:
                if p['th']:
                    obs.append(box(*p['bb']).buffer(0.25, join_style=2))
        return unary_union(obs)
    def put(ref, x, y, rot, side):
        v = F[ref]['var'][f'{side}{int(rot) % 360}']
        placed[ref] = dict(side=side, rot=rot, x=x, y=y, poly=poly_of(v[0], x, y), pads=pads_of(v[1], x, y), mech=False)
    def targets(net, ref):
        """ネット net の、置いた部品のパッドの位置(電源のネットは IC・コネクタだけ)"""
        pts = []
        for r, q in placed.items():
            if r == ref:
                continue
            if net in POWER and (not r.startswith(ACTIVE) or F[r]['sheet'] != F[ref]['sheet']):
                continue
            pts += [(p['x'], p['y']) for p in q['pads'] if p['net'] == net]
        return np.array(pts) if pts else None
    def weight(net):
        return GND_W if net == 'GND' else SIGNAL_W
    def cost_grid(ref, side, rot, X, Y):
        v = F[ref]['var'][f'{side}{rot}']
        c = np.zeros_like(X)
        for p in v[1]:
            if not p['net'] or p['net'].startswith('unconnected'):
                continue
            t = targets(p['net'], ref)
            if t is None:
                continue
            px, py = X + p['x'], Y + p['y']
            dd = np.min(np.hypot(px[..., None] - t[:, 0], py[..., None] - t[:, 1]), axis=-1)
            c += weight(p['net']) * dd
        return c
    # 1. 手で置く部品(回転が None なら、つなぐ先まで一番短い回転)
    order = ['J2', 'J3', 'J1', 'C4', 'Q1', 'J4', 'J7', 'D2', 'U76', 'U74', 'U75', 'U2', 'U3', 'U4', 'U1']
    for ref in order:
        x, y, rot, side = FIXED[ref]
        if rot is None:
            best = min((float(cost_grid(ref, side, r, np.array([[x]]), np.array([[y]]))[0, 0]), r) for r in (0, 90, 180, 270))
            rot = best[1]
        cx, cy_ = poly_of(F[ref]['var'][f'{side}{int(rot) % 360}'][0]).envelope.centroid.coords[0]   # (x, y) はコートヤードの真ん中(原点が1番ピンの部品があるため)
        put(ref, round(x - cx, 3), round(y - cy_, 3), rot, side)
    # 2. ほかの部品
    rest = [r for r in F if r not in placed]
    def attach(ref):
        s = 0.0
        for p in F[ref]['var']['T0'][1]:
            if p['net'] and targets(p['net'], ref) is not None:
                s += weight(p['net'])
        return s
    xs = np.arange(-30.0, 46.0, 0.25); ys = np.arange(-34.0, 34.25, 0.25)
    X, Y = np.meshgrid(xs, ys)
    free = {}
    def free_area(side):
        a = board.difference(obstacles(side))
        return a
    free = {s: free_area(s) for s in ('T', 'B')}
    bat_free_T = None
    log = []
    while rest:
        rest.sort(key=lambda r: (-attach(r), r))
        ref = rest.pop(0)
        h = height(F[ref]['fp'], ref)
        cands = []
        for side in ('T', 'B'):
            for rot in (0, 90, 180, 270):
                c = cost_grid(ref, side, rot, X, Y) + (BOTTOM_COST if side == 'B' else 0.0)
                cands.append((c, side, rot))
        import shapely
        for i, (c, side, rot) in enumerate(cands):
            inside = shapely.contains_xy(free[side], X, Y)
            cands[i] = (np.where(inside, c, np.inf), side, rot)
        allc = np.concatenate([c.ravel() for c, _, _ in cands])
        idx = np.argsort(allc, kind='stable')
        idx = idx[np.isfinite(allc[idx])]
        n = X.size
        ok = False
        pf = {s: prep(free[s]) for s in ('T', 'B')}
        pbat = prep(BATTERY)
        for k in idx:
            ci, j = divmod(int(k), n)
            _, side, rot = cands[ci]
            x, y = X.flat[j], Y.flat[j]
            v = F[ref]['var'][f'{side}{rot}']
            poly = poly_of(v[0], x, y)
            if poly is None:
                continue
            if not pf[side].contains(poly.buffer(0.01, join_style=2)):
                continue
            if side == 'T' and h > H_MAX_BAT and pbat.intersects(poly):
                continue
            put(ref, x, y, rot, side)
            free[side] = free[side].difference(poly)
            for p in placed[ref]['pads']:
                if p['th']:
                    o = box(*p['bb']).buffer(0.25, join_style=2)
                    free['T'] = free['T'].difference(o); free['B'] = free['B'].difference(o)
            log.append((ref, side, rot, round(float(allc[k]), 2)))
            ok = True
            break
        if not ok:
            print('置けない:', ref)
    bad = []
    items = [(r, q) for r, q in placed.items() if q['poly'] is not None and not r.startswith('H')]
    for i, (r1, q1) in enumerate(items):
        for r2, q2 in items[i + 1:]:
            if q1['side'] == q2['side'] and q1['poly'].intersection(q2['poly']).area > 1e-4:
                bad.append(f'{r1}-{r2}')
    for r, q in items:
        if not q['mech'] and not board.contains(q['poly']):
            bad.append(f'{r} が外形の外')
        if not q['mech'] and q['side'] == 'T' and height(F[r]['fp'], r) > H_MAX_BAT and BATTERY.intersection(q['poly']).area > 1e-4:
            bad.append(f'{r} が電池の下(高さ {height(F[r]["fp"], r)}mm)')
        if not q['mech'] and q['side'] == 'B' and UNDER.intersection(q['poly']).area > 1e-4:
            bad.append(f'{r} が裏の機構に当たる')
    print('重なり・はみ出し:', bad if bad else 'なし')
    return F, board, placed, log

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

def draw(F, board, placed, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams['font.family'] = 'WenQuanYi Zen Hei'; plt.rcParams['axes.unicode_minus'] = False
    frame = ps.dz.outline(0)
    fig, axs = plt.subplots(1, 2, figsize=(20, 9.6))
    colors = {'/MCU/': '#4e79a7', '/センサ/': '#59a14f', '/モーター/': '#e15759', '/電源/': '#f28e2b', '/表示・通信/': '#b07aa1'}
    for ax, side, title in ((axs[0], 'T', '上の面'), (axs[1], 'B', '裏の面(上から見た図。裏から見ると左右が逆)')):
        ax.fill(*frame.exterior.xy, color='#f0f0f0', ec='#aaa', lw=0.6)
        for g in getattr(board, 'geoms', [board]):
            ax.fill(*g.exterior.xy, color='#dfeee2', ec='k', lw=1.0)
            for r_ in g.interiors:
                ax.fill(*r_.xy, color='#f0f0f0', ec='k', lw=0.6)
        if side == 'T':
            ax.fill(*BATTERY.exterior.xy, fill=False, hatch='//', ec='#b8860b', lw=0.8)
            ax.text(-5, -15.2, '電池の下: 高さ 1.2mm まで', fontsize=8, color='#8b6508', ha='center')
            for k, (a, b_, c, d, s) in RESERVE.items():
                ax.add_patch(plt.Rectangle((a, b_), c - a, d - b_, fill=False, ec='#333', ls='--', lw=0.8))
                ax.text((a + c) / 2, (b_ + d) / 2, k + '\n(仮)', fontsize=7, ha='center', va='center')
        else:
            for g in getattr(UNDER, 'geoms', [UNDER]):
                ax.fill(*g.exterior.xy, fill=False, hatch='\\\\', ec='#8a5cc7', lw=0.6)
            ax.text(-12, 0, 'モーター', fontsize=8, color='#5b3a8c', ha='center', rotation=90)
            ax.text(14.2, -12, 'ファンの囲い', fontsize=8, color='#5b3a8c', ha='center')
        for (x, y) in ps.SCREWS:
            ax.add_patch(plt.Circle((x, y), 1.1, color='w', ec='k', lw=0.6))
        for r, q in placed.items():
            if r.startswith('H'):
                continue
            col = colors.get(F[r].get('sheet'), '#888')
            if q['side'] == side and q['poly'] is not None:
                for g in getattr(q['poly'], 'geoms', [q['poly']]):
                    ax.fill(*g.exterior.xy, color=col, alpha=0.35 if q['mech'] else 0.55, ec=col, lw=0.6)
                c = q['poly'].centroid
                big = q['poly'].area > 12
                ax.text(c.x, c.y, r, fontsize=6.5 if big else 4.6, ha='center', va='center')
            for p in q['pads']:
                if p['th'] or q['side'] == side:
                    x0, y0, x1, y1 = p['bb']
                    ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, color='#c08a00' if not p['th'] else '#7a5500', lw=0))
        ax.set_aspect('equal'); ax.set_xlim(-33, 48); ax.set_ylim(-37, 37); ax.set_title(title, fontsize=12)
        ax.set_xlabel('x [mm](前 →)'); ax.set_ylabel('y [mm](左 ↑)'); ax.grid(alpha=0.15)
    hs = [plt.Rectangle((0, 0), 1, 1, color=c, alpha=0.6) for c in colors.values()]
    fig.legend(hs, [s.strip('/') for s in colors], loc='upper center', ncol=5, fontsize=10, bbox_to_anchor=(0.5, 0.96))
    fig.suptitle('KOGUMA-Mk4_t24 メイン基板の仮の配置(hardware/kicad/place_main_t24.py)', fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(path, dpi=90)

if __name__ == '__main__':
    F, board, placed, log = plan()
    out = {r: dict(x=round(q['x'], 3), y=round(q['y'], 3), rot=q['rot'], side=q['side']) for r, q in placed.items() if not q['mech']}
    json.dump(out, open(os.path.join(DST, 'place.json'), 'w'), indent=0, ensure_ascii=False, sort_keys=True)
    # ネットごとの線の長さの目安(最小全域木)
    nets = {}
    for r, q in placed.items():
        for p in q['pads']:
            if p['net'] and not p['net'].startswith('unconnected'):
                nets.setdefault(p['net'], []).append((p['x'], p['y']))
    L = {n: mst(v) for n, v in nets.items()}
    sig = sum(v for n, v in L.items() if n not in POWER and n != 'GND')
    print(f'置いた部品 {len(out)}、信号のネットの長さの目安 合計 {sig:.0f}mm')
    for n, v in sorted(L.items(), key=lambda kv: -kv[1])[:15]:
        print(f'  {n:24s} {v:6.1f}mm')
    draw(F, board, placed, os.path.join(DST, 'floorplan.png'))
    nB = sum(1 for q in out.values() if q['side'] == 'B')
    print('裏の面に置いた部品:', nB, sorted(r for r, q in out.items() if q['side'] == 'B'))

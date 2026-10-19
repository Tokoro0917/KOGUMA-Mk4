"""フレームの形を、寸法のパラメータから作る。x: 前(+)、y: 左(+)、原点は車軸の中心 [mm]"""
import numpy as np
from shapely.geometry import Polygon, box, Point, LineString
from shapely.ops import unary_union
from shapely import affinity

XE, YE = 50.0, 25.3          # 前後の端、端の辺の半幅(2026-10-19 に 50.5 から。前後 100mm)
XB, YB = 16.7, 35.0          # 真ん中の帯の半幅、最大の半幅(2026-10-19 に 35.3 から。左右 70mm)
SX, SY = 30.25, 15.25        # 吸引する面の半分
FAN_X, FAN_R = 14.2, 7.5     # ファンの穴
SLOT_L, SLOT_Y0, SLOT_Y1 = 14.0, 25.8, 32.3   # タイヤ・ホイール・41T の穴: 前後14mm(2026-10-19 に13mmから。角でタイヤとのすき間0.26mmだった)、y 25.8〜32.3
MOUNT_SCREWS = [(-17.0, 22.0), (8.0, 22.0)]    # モーターマウントのねじ。左右に写す(2026-10-19 に (−17.15, 22.1)、(7.85, 22.1) から。穴の間を 1mm 単位に)
BOSS_R = 3.7                                    # ねじのまわりの肉(直径7.4mm。M3 のときに決めた大きさのまま)
SCREW, HOLE_D = 'M2', 2.3                       # ねじは M2、穴 φ2.3(2026-10-19 に M3 から変更)
FAN_SCREWS = [(22.0, 18.0), (22.0, -18.0), (33.0, 0.0)]   # 吸引ファンのケースを留めるねじ(2026-10-19 に (21.5, ±17.6)、(32.6, 0) から。穴の間を 1mm 単位に)
FAN_BOSS_R = 3.3                                # ファンのねじのまわりに必ず残す肉(穴の縁から2.15mm。窓がここにかからない)

def holes():
    """フレームのねじの穴の中心: モーターマウント(左右) + 吸引ファンのケース"""
    return [(x, sy * y) for (x, y) in MOUNT_SCREWS for sy in (1, -1)] + list(FAN_SCREWS)
G_FRONT = (12.0, 19.0)                          # 骨Gの始まり(モーターマウントの前の耳のすぐ前)
G_REAR = (-21.5, 19.0)                          # 骨Gの始まり(モーターマウントの後ろの耳のすぐ後ろ)
MOUNT_PAD = (-22.0, 12.5, SY, SLOT_Y0 + 0.5)    # マウントが載る所は窓を開けない: x0, x1, |y|0, |y|1

DEFAULT = dict(rim=2.5, end_edge=2.5, spine_root=4.0, spine_tip=4.0, inner_spine=4.0,
               land=3.0, fan_ring=3.5, braces=(), brace_w=2.5, fillet=1.5, corner_r=3.0,
               end_window_min=20.0, rect_ribs=(), rib_w=3.0, root_fill=XB,
               v_ribs=(), v_rib_h=4.0, mount_windows=(), brace_w_each={},
               rim_rear=None, end_edge_rear=None, spine_root_rear=None, spine_tip_rear=None, brace_w_rear=None,
               pad_full=False)   # *_rear: 後ろ半分だけ変えるとき(None なら前と同じ)。pad_full: マウントの所の窓を前後にまっすぐ切る

def outline(r):
    pts = [(-XE, -YE), (-XB, -YB), (XB, -YB), (XE, -YE), (XE, YE), (XB, YB), (-XB, YB), (-XE, YE)]
    return Polygon(pts).buffer(-r).buffer(r)

def rounded(p, r):
    if r <= 0:
        return p
    return p.buffer(-r).buffer(r)

def taper(x0, x1, w0, w1):
    return Polygon([(x0, -w0 / 2), (x1, -w1 / 2), (x1, w1 / 2), (x0, w0 / 2)])

def rear(P, k):
    """後ろ半分の値(*_rear が None なら前と同じ)"""
    v = P.get(k + '_rear')
    return P[k] if v is None else v

def brace_lines(P):
    """筋交いの線(前の右上の四分の一で定義し、上下・前後に写す。後ろは後ろの枠・辺の幅で角を決める)"""
    def side_lines(r, ee):
        fc = (XE - ee, YE - r)                     # 角
        bc = (XB, YB - r)                          # 帯の角
        rc = (SX, SY)                              # 吸引する面の角
        return fc, {'A': (fc, (SX, 0.0)),          # 角 → 背骨の根元
                    'B': (bc, (XE - ee, 0.0)),     # 帯の角 → 背骨の先
                    'C': (fc, rc),                 # 角 → 吸引する面の角
                    'D': (bc, rc),                 # 帯の角 → 吸引する面の角
                    'E': (rc, (XE - ee, YE * 0.45)),   # 吸引する面の角 → 辺の途中
                    'H': (rc, (XE - ee, 0.0))}         # 吸引する面の角 → 背骨の先
    fcf, lf = side_lines(P['rim'], P['end_edge'])
    fcr, lr = side_lines(rear(P, 'rim'), rear(P, 'end_edge'))
    out = []
    for k in P['braces']:
        if k == 'G':   # モーターマウントの前後の端 → 前後の角(ファンを避けて、ほぼ前後方向にまっすぐ)
            for sy in (1, -1):
                out.append(LineString([(G_FRONT[0], sy * G_FRONT[1]), (fcf[0], sy * fcf[1])]))
                out.append(LineString([(G_REAR[0], sy * G_REAR[1]), (-fcr[0], sy * fcr[1])]))
            continue
        for sx, lines in ((1, lf), (-1, lr)):
            a, b = lines[k]
            for sy in (1, -1):
                out.append(LineString([(sx * a[0], sy * a[1]), (sx * b[0], sy * b[1])]))
    return out

ENC_BOARD = (-3.0, 3.0, 20.46, 21.06)   # エンコーダ基板が立つ所(x0, x1, |y|0, |y|1)。ここはフレームを残す

def mount_windows(carbon, suction, kinds):
    """働いていない所の窓(2026-10-18、pocket.py で調べた)。左右に写す
      'pad' : モーターマウントの下(後ろのねじとエンコーダ基板の間)
      'side': タイヤの穴の後ろの横の帯(横からの衝突の守り。開けると横の安全率が下がる)"""
    keep = carbon.boundary.buffer(1.5)                                     # 縁・窓・穴から1.5mm
    keep = keep.union(suction.boundary.buffer(3.0))                        # スカートを貼る縁
    for (x, y) in MOUNT_SCREWS:
        for sy in (1, -1):
            keep = keep.union(Point(x, sy * y).buffer(BOSS_R + 0.8, 32))   # ねじの頭・マウントの耳
    x0, x1, y0, y1 = ENC_BOARD
    keep = keep.union(box(x0 - 1.5, y0 - 1.5, x1 + 1.5, y1 + 1.5)).union(box(x0 - 1.5, -y1 - 1.5, x1 + 1.5, -y0 + 1.5))
    raw, clean = [], []
    # すっきりした四角い窓(2026-10-19)。マウントの耳(半径3.1)から0.5mm、エンコーダ基板の足から1.5mm、タイヤの穴から1.5mm
    if 'pad2' in kinds:      # マウントの下(後ろのねじとエンコーダ基板の間)
        clean.append(box(MOUNT_SCREWS[0][0] + 3.6, SY + 3.0, ENC_BOARD[0] - 1.5, SLOT_Y0 - 2.0))
    if 'side2' in kinds or 'side2r' in kinds:     # タイヤの穴の後ろの横の帯(外周の枠は残す)
        clean.append(box(MOUNT_PAD[0] + 2.5, SLOT_Y0 + 0.8, -SLOT_L / 2 - 2.0, YB - 2.0))
    if 'side2' in kinds:     # タイヤの穴の前の横の帯
        clean.append(box(SLOT_L / 2 + 2.0, SLOT_Y0 + 0.8, XB - 2.0, YB - 3.0))
    if clean:
        clean += [affinity.scale(r, 1, -1, origin=(0, 0)) for r in clean]
        cw = unary_union(clean).intersection(carbon.buffer(-2.0))         # ほかの切り口から 2mm 以上
        return cw.buffer(-1.5).buffer(1.5)                             # 角は R1.5
    if 'pad' in kinds:
        raw.append(box(-13.0, SY + 2.0, ENC_BOARD[0] - 1.5, SLOT_Y0))
    if 'side' in kinds:
        raw.append(box(-16.5, SLOT_Y0 - 0.5, -7.5, YB - 2.5))
    raw += [affinity.scale(r, 1, -1, origin=(0, 0)) for r in raw]
    w = unary_union(raw).intersection(carbon).difference(keep)
    return w.buffer(-1.0).buffer(1.0)                                      # 角は R1(刃物の半径)

def no_boss(wins, boss, r):
    """窓がねじのまわりの肉にかかるときだけ、そこを除いてから角を丸め直す(かからない窓はそのまま)"""
    out = []
    for w in wins:
        if w.intersects(boss):
            w = rounded(w.difference(boss), r)
        out += [g for g in getattr(w, 'geoms', [w]) if not g.is_empty and g.area > 1.0]
    return out

def build(**kw):
    P = dict(DEFAULT, **kw)
    o = outline(P['corner_r'])
    inner = unary_union([o.buffer(-P['rim'], join_style=2).intersection(box(0, -50, 60, 50)),
                         o.buffer(-rear(P, 'rim'), join_style=2).intersection(box(-60, -50, 0, 50))])
    inner = inner.difference(box(XE - P['end_edge'], -50, 60, 50)).difference(box(-60, -50, -XE + rear(P, 'end_edge'), 50))
    suction = box(-SX, -SY, SX, SY)
    band = box(-XB, -50, XB, 50)
    members = [taper(SX, XE, P['spine_root'], P['spine_tip']), taper(-SX, -XE, rear(P, 'spine_root'), rear(P, 'spine_tip'))]
    for k in P['braces']:      # 骨ごとの幅は brace_w_each で変えられる(ないものは brace_w)。後ろの骨Gは brace_w_rear
        w = P['brace_w_each'].get(k, P['brace_w'])
        for l in brace_lines(dict(P, braces=(k,))):
            wl = rear(P, 'brace_w') if (k == 'G' and l.coords[0][0] < 0) else w
            members.append(l.buffer(wl / 2, cap_style=2, join_style=2))
    root = box(-P['root_fill'], -50, P['root_fill'], 50)      # ここより内側は窓を開けない(付け根を太くする)
    x0, x1, y0, y1 = MOUNT_PAD
    if P['pad_full']:
        y1 = 50.0
    pad = unary_union([box(x0, y0, x1, y1), box(x0, -y1, x1, -y0)]
                      + [Point(x, sy * y).buffer(BOSS_R + 0.8, 32) for (x, y) in MOUNT_SCREWS for sy in (1, -1)])
    fan_boss = unary_union([Point(x, y).buffer(FAN_BOSS_R, 32) for (x, y) in FAN_SCREWS])
    ends = inner.difference(band).difference(root).difference(suction).difference(unary_union(members)).difference(pad)
    holes = [rounded(g, P['fillet']) for g in getattr(ends, 'geoms', [ends]) if g.area > P['end_window_min']]
    holes = [h for g in holes for h in getattr(g, 'geoms', [g]) if not h.is_empty]
    holes = no_boss(holes, fan_boss, P['fillet'])
    # 吸引する面の中の窓(ポリカーボネートでふさぐ)
    win = box(-SX + P['land'], -SY + P['land'], SX - P['land'], SY - P['land'])
    if P['inner_spine'] > 0:
        win = win.difference(box(-60, -P['inner_spine'] / 2, 60, P['inner_spine'] / 2))
    ribs = []
    hl = P['land'] / 2
    (xr, _), (xf, _) = MOUNT_SCREWS
    for k in P['rect_ribs']:
        if k == 'T':      # ねじの位置を通る横の骨
            ribs += [LineString([(x, -SY), (x, SY)]) for x in (xr, xf)]
        if k == 'X':      # 背骨の根元から、ねじの位置へ斜めの骨
            for sy in (1, -1):
                ribs += [LineString([(SX - hl, 0), (xf, sy * (SY - hl))]),
                         LineString([(-SX + hl, 0), (xr, sy * (SY - hl))])]
        if k == 'L':      # 吸引する面の前後の角から、ねじの位置へ
            for sy in (1, -1):
                ribs += [LineString([(SX - hl, sy * (SY - hl)), (xf, sy * (SY - hl) * 0.0)]),
                         LineString([(-SX + hl, sy * (SY - hl)), (xr, 0.0)])]
    if ribs:
        win = win.difference(unary_union([r.buffer(P['rib_w'] / 2, cap_style=2) for r in ribs]))
    fan = Point(FAN_X, 0).buffer(FAN_R, 64)
    win = win.difference(Point(FAN_X, 0).buffer(FAN_R + P['fan_ring'], 64))
    pcw = [rounded(g, 1.5) for g in getattr(win, 'geoms', [win]) if g.area > 20]
    pcw = [h for g in pcw for h in getattr(g, 'geoms', [g]) if not h.is_empty]
    pcw = no_boss(pcw, fan_boss, 1.5)
    slots = [rounded(box(-SLOT_L / 2, s0, SLOT_L / 2, s1), 1.0) for s0, s1 in ((SLOT_Y0, SLOT_Y1), (-SLOT_Y1, -SLOT_Y0))]
    domain = o.difference(unary_union(holes + slots + [fan]))
    carbon = domain.difference(unary_union(pcw))
    if P['mount_windows']:
        mw = mount_windows(carbon, suction, P['mount_windows'])
        domain, carbon = domain.difference(mw), carbon.difference(mw)
    clamps = [Point(x, sy * y).buffer(BOSS_R, 32) for (x, y) in MOUNT_SCREWS for sy in (1, -1)]
    # 縦に立てるリブ(1mm のカーボンを溝に差して接着)。(線, 高さ, 足元の板の幅)
    vr = []
    h = P['v_rib_h']
    for k in P['v_ribs']:
        if k == 'S':      # 背骨の上(前: ファンの穴のまわりの外から前の端まで、後ろ: 吸引する面の中から後ろの端まで)
            vr += [(LineString([(FAN_X + FAN_R + P['fan_ring'] + 0.5, 0), (XE - 1.0, 0)]), h, P['spine_root']),
                   (LineString([(-20.0, 0), (-XE + 1.0, 0)]), h, P['spine_root'])]
        if k == 'F':      # 前後の端の辺に沿って(壁センサを付ける壁にもなる)
            for sx in (1, -1):
                vr.append((LineString([(sx * (XE - P['end_edge'] / 2), -(YE - 4)), (sx * (XE - P['end_edge'] / 2), YE - 4)]), h, P['end_edge']))
        if k == 'R':      # 外周の斜めの枠の中心線に沿って(帯の角の近くから前の角の近くまで)
            p0, p1 = np.array([XB, YB]), np.array([XE, YE])
            u = (p1 - p0) / np.linalg.norm(p1 - p0)
            nin = np.array([u[1], -u[0]])
            L = np.linalg.norm(p1 - p0)
            a = p0 + nin * P['rim'] / 2 + u * 3.0
            b = p0 + nin * P['rim'] / 2 + u * (L - 5.0)
            for sx in (1, -1):
                for sy in (1, -1):
                    vr.append((LineString([(sx * a[0], sy * a[1]), (sx * b[0], sy * b[1])]), h, P['rim']))
        if k == 'M':      # 吸引する面の横のすぐ外を、モーターマウントの前後から付け根まで(付け根を埋めた形で使う)
            (xr, yr), (xf, yf) = MOUNT_SCREWS
            yy = SY + 1.25
            for sy in (1, -1):
                vr += [(LineString([(xf + 2.0, sy * yy), (P['root_fill'] - 0.5, sy * yy)]), h, 2.5),
                       (LineString([(xr - 2.0, sy * yy), (-P['root_fill'] + 0.5, sy * yy)]), h, 2.5)]
        if k == 'G':      # 骨Gの上(モーターマウントの端 → 前後の角)
            fc = (XE - P['end_edge'], YE - P['rim'])
            for sy in (1, -1):
                for (x0, y0), sx in ((G_FRONT, 1), (G_REAR, -1)):
                    a = np.array([x0, sy * y0]); b = np.array([sx * fc[0], sy * fc[1]])
                    u = (b - a) / np.linalg.norm(b - a)
                    vr.append((LineString([a + u * 0.5, b - u * 2.0]), h, P['brace_w']))
        if k == 'H':      # 筋交いH(吸引する面の角 → 背骨の先)の上
            for sx in (1, -1):
                for sy in (1, -1):
                    a = np.array([sx * SX, sy * SY]); b = np.array([sx * (XE - P['end_edge']), 0.0])
                    u = (b - a) / np.linalg.norm(b - a)
                    vr.append((LineString([a + u * 1.5, b - u * 2.5]), h, P['brace_w']))
        if k == 'C':      # 筋交いC(吸引する面の角 → 前の角)の上
            fc = (XE - P['end_edge'], YE - P['rim'])
            for sx in (1, -1):
                for sy in (1, -1):
                    vr.append((LineString([(sx * (SX + 1.0), sy * (SY + 0.3)), (sx * (fc[0] - 1.5), sy * (fc[1] - 0.6))]), h, P['brace_w']))
    return dict(P=P, domain=domain, carbon=carbon, pc=pcw, clamps=clamps, suction=suction, vribs=vr)

def mass_iz(g):
    """カーボンとポリカーボネートの質量 [g] と、原点まわりの慣性モーメント [g·cm²]"""
    from shapely import contains_xy
    xs = np.arange(-55, 55, 0.1); ys = np.arange(-40, 40, 0.1)
    X, Y = np.meshgrid(xs, ys)
    mc = contains_xy(g['carbon'], X, Y)
    mp = contains_xy(unary_union(g['pc']), X, Y) if g['pc'] else np.zeros_like(mc)
    sheet = contains_xy(g['suction'].difference(Point(FAN_X, 0).buffer(FAN_R, 64)), X, Y)
    r2 = X**2 + Y**2
    dc = 1.55e-3 * 0.01      # g / (0.1mm)² セル(1mm厚)
    dp = 0.2 * 1.2e-3 * 0.01
    m_c = mc.sum() * dc
    m_p = sheet.sum() * dp
    iz = (r2[mc].sum() * dc + r2[sheet].sum() * dp) / 100
    for (line, h, wb) in g.get('vribs', []):          # リブの質量(1mm 厚 × 高さ × 長さ)
        n = max(2, int(line.length / 0.5))
        pts = [line.interpolate(i / (n - 1), normalized=True) for i in range(n)]
        dm = 1.55e-3 * 1.0 * h * line.length / n
        m_c += dm * n
        iz += sum(dm * (p.x**2 + p.y**2) for p in pts) / 100
    return m_c, m_p, iz

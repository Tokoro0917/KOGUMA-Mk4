"""メイン基板(KOGUMA-Mk4.kicad_pcb)を回路図から起こす(2026-10-31)
- 回路図のネットリスト(kicad-cli で書き出す)から部品とネットを読む
- 外形は mechanical/vehicle/pcb_shape.py の outline()(今は v16)。円弧はできるだけ円弧にする
- 位置が決まっている部品だけ置く: 壁センサ(裏、pcb_shape.SENS)、エンコーダの基板の穴(J5・J6)、UI の LED 8個、マウントの柱の穴 H1〜H4
- ほかの部品は基板の右(前)の外に、シートごとに並べておく(あとで配置する)
- 2層、0.6mm。設計ルールはエンコーダの基板・ToraNeko.Mk3 と同じ(KOGUMA-Mk4.kicad_pro)
座標: 機体の座標(原点は車軸の中心、+x 前、+y 左)を KiCad の (OX + x, OY − y) に置く。上から見て前が右、左が上
使い方(このフォルダで): python3 gen_pcb.py   → KOGUMA-Mk4.kicad_pcb(ある場合は上書きするので、配置を始めたら使わない)"""
import os, sys, re, math, subprocess, json
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '../../../mechanical/vehicle'))
sys.path.insert(0, os.path.join(HERE, '../../../docs/calc/frame'))
import pcb_shape as ps
import dxf_arcs as dxa

OX, OY = 150.0, 100.0
mm = pcbnew.FromMM
def P(x, y):
    return pcbnew.VECTOR2I(mm(OX + x), mm(OY - y))
def back(v):
    return (pcbnew.ToMM(v.x) - OX, OY - pcbnew.ToMM(v.y))

STD = '/usr/share/kicad/footprints'
def lib_path(nick):
    return os.path.join(HERE, 'KOGUMA-Mk4.pretty') if nick == 'KOGUMA-Mk4' else os.path.join(STD, nick + '.pretty')

# ---- ネットリスト ----
NET = '/tmp/koguma_mk4_netlist.net'
subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '-o', NET, os.path.join(HERE, 'KOGUMA-Mk4.kicad_sch')], check=True, capture_output=True)
s = open(NET).read()
comps = []
for blk in s.split('\n    (comp (ref "')[1:]:
    blk = blk.split('\n  (libparts')[0]
    ref, body = blk.split('"', 1)
    m = [None, ref]
    g = lambda k: (re.search(r'\n      \(%s "([^"]*)"\)' % k, body) or [None, ''])[1]
    sheet = re.search(r'\(sheetpath \(names "([^"]*)"\) \(tstamps "([^"]*)"\)\)', body)
    comps.append(dict(ref=m[1], value=g('value'), fp=g('footprint'), sheet=sheet.group(1), path=sheet.group(2) + g('tstamps')))
nets = {}
for blk in s.split('\n    (net (code "')[1:]:
    name = re.search(r'\(name "([^"]*)"\)', blk).group(1)
    for ref, pin in re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', blk):
        nets[(ref, pin)] = name

board = pcbnew.BOARD()
board.SetCopperLayerCount(2)
ds = board.GetDesignSettings()
ds.SetBoardThickness(mm(0.6))
netinfo = {}
for name in sorted(set(nets.values())):
    n = pcbnew.NETINFO_ITEM(board, name); board.Add(n); netinfo[name] = n

def add(ref, value, fpid, path=''):
    nick, name = fpid.split(':')
    fp = pcbnew.FootprintLoad(lib_path(nick), name)
    assert fp is not None, fpid
    fp.SetFPID(pcbnew.LIB_ID(nick, name))
    fp.SetReference(ref); fp.SetValue(value)
    if path:                                                # 回路図の部品: 部品表から外すかどうかは記号に合わせる(線のパッド・テストパッドも外さない)
        fp.SetPath(pcbnew.KIID_PATH(path)); fp.SetExcludedFromBOM(False)
    for pad in fp.Pads():
        k = (ref, pad.GetNumber())
        if k in nets:
            pad.SetNet(netinfo[nets[k]])
    board.Add(fp)
    return fp

FPS = {c['ref']: add(c['ref'], c['value'], c['fp'], c['path']) for c in comps}

# ---- 外形 ----
def seg(a, b):
    sh = pcbnew.PCB_SHAPE(board); sh.SetShape(pcbnew.SHAPE_T_SEGMENT); sh.SetLayer(pcbnew.Edge_Cuts)
    sh.SetStart(P(*a)); sh.SetEnd(P(*b)); sh.SetWidth(mm(0.05)); board.Add(sh)
def arc(a, b, bulge):
    th = 4 * math.atan(bulge)                               # 中心角(反時計回りが正)
    ch = math.hypot(b[0] - a[0], b[1] - a[1]); r = ch / 2 / math.sin(abs(th) / 2)
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    nx, ny = -(b[1] - a[1]) / ch, (b[0] - a[0]) / ch       # 弦の左の向き
    sag = r - math.sqrt(max(r * r - ch * ch / 4, 0)) if abs(th) <= math.pi else r + math.sqrt(max(r * r - ch * ch / 4, 0))
    sgn = -1 if th > 0 else 1                               # 反時計回りの弧の真ん中は弦の右
    mid = (mx + sgn * nx * sag, my + sgn * ny * sag)
    sh = pcbnew.PCB_SHAPE(board); sh.SetShape(pcbnew.SHAPE_T_ARC); sh.SetLayer(pcbnew.Edge_Cuts)
    sh.SetArcGeometry(P(*a), P(*mid), P(*b)); sh.SetWidth(mm(0.05)); board.Add(sh)
def ring(coords):
    kind = dxa.ring_entities(coords)
    if kind[0] == 'circle':
        (cx, cy), r = kind[1], kind[2]
        sh = pcbnew.PCB_SHAPE(board); sh.SetShape(pcbnew.SHAPE_T_CIRCLE); sh.SetLayer(pcbnew.Edge_Cuts)
        sh.SetCenter(P(cx, cy)); sh.SetEnd(P(cx + r, cy)); sh.SetWidth(mm(0.05)); board.Add(sh)
        return
    pts = kind[1]
    for i, (x, y, bu) in enumerate(pts):
        nx_, ny_ = pts[(i + 1) % len(pts)][:2]
        if math.hypot(nx_ - x, ny_ - y) < 1e-6:
            continue
        (arc if abs(bu) > 1e-9 else lambda a, b, _: seg(a, b))((x, y), (nx_, ny_), bu)
o = ps.outline()
ring(list(o.exterior.coords))
for r in o.interiors:
    ring(list(r.coords))

# ---- 位置が決まっている部品 ----
def place_check(fp, x, y, cands, ok):
    fp.SetPosition(P(x, y))
    for a in cands:
        fp.SetOrientationDegrees(a % 360)
        if ok(fp):
            return a % 360
    raise RuntimeError(fp.GetReference())

# 壁センサ: ホルダは基板の裏。発光(ほぞの穴つき)と受光を同じ位置・向きに
EMIT = {'FL': 'D70', 'L': 'D71', 'R': 'D72', 'FR': 'D73'}
RECV = {re.search(r'\((\w+)\)', c['value']).group(1): c['ref'] for c in comps if c['value'].startswith('SFH 229 FA')}
for nm, ((x, y), ang) in ps.SENS.items():
    for ref, part in ((EMIT[nm], 'emit'), (RECV[nm], 'recv')):
        fp = FPS[ref]
        fp.SetPosition(P(x, y))
        fp.Flip(P(x, y), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        want = sorted((round(px, 2), round(py, 2)) for px, py in ps.pads(nm, part))
        def ok(f, want=want):
            got = sorted((round(a, 2), round(b, 2)) for a, b in (back(p.GetPosition()) for p in f.Pads()))
            return all(abs(g[0] - w[0]) < 0.02 and abs(g[1] - w[1]) < 0.02 for g, w in zip(got, want))
        cands = [ang, -ang, 180 - ang, 180 + ang]
        a = place_check(fp, x, y, cands, ok)
        if part == 'emit':                      # ほぞの穴がホルダの後ろにあるか(光の向きが逆でないか)
            sl = [d for d in fp.GraphicalItems() if d.GetLayer() == pcbnew.Edge_Cuts]
            pts = [back(v) for d in sl for v in (d.GetStart(), d.GetEnd())]
            cx = (min(p[0] for p in pts) + max(p[0] for p in pts)) / 2; cy = (min(p[1] for p in pts) + max(p[1] for p in pts)) / 2
            c = ps.slot(nm).centroid
            assert math.hypot(cx - c.x, cy - c.y) < 0.6, (nm, cx, cy, c.x, c.y)
# エンコーダの基板の穴: 左 J5 は 0°、右 J6 は 180°(穴の真ん中が原点)
for ref, (x0, x1, y0, y1), a in (('J5', ps.ENC[1], 0), ('J6', ps.ENC[0], 180)):
    FPS[ref].SetPosition(P((x0 + x1) / 2, (y0 + y1) / 2)); FPS[ref].SetOrientationDegrees(a)
# UI の LED: 後ろの角の4個がナンバー(左から NUM3〜NUM0)、V 字の先の3個がモード(左から MODE2〜MODE0)。
# 1608 なので長い方を x(前後)に向ける(ToraNeko の 1005 は長い方が y。1608 で y に向けると 1.9mm おきでは重なる)
LEDREF = ['D96', 'D95', 'D92', 'D91', 'D90', 'D94', 'D93']   # ps.LEDS の順(LED1 = 左の外 … LED7 = 右の外)
for ref, (x, y) in zip(LEDREF, ps.LEDS):
    FPS[ref].SetPosition(P(x, y)); FPS[ref].SetOrientationDegrees(0)
FPS['D98'].SetPosition(P(*ps.LED_FRONT)); FPS['D98'].SetOrientationDegrees(0)
FIXED_REFS = list(EMIT.values()) + list(RECV.values()) + ['J5', 'J6', 'D98'] + LEDREF
# マウントの柱の穴(M2、穴 φ2.2、回路図にはないので基板だけの部品)
for i, (x, y) in enumerate(ps.SCREWS):
    h = add(f'H{i + 1}', 'M2', 'MountingHole:MountingHole_2.2mm_M2')
    h.SetBoardOnly(True); h.SetExcludedFromBOM(True); h.SetExcludedFromPosFiles(True)
    h.SetPosition(P(x, y))

# 位置が決まっている部品の部品番号は Fab に(シルクは小さい部品が混むので、配置のときに足す)
for r in FIXED_REFS + [f'H{i + 1}' for i in range(len(ps.SCREWS))]:
    fp = FPS[r] if r in FPS else board.FindFootprintByReference(r)
    t = fp.Reference(); t.SetLayer(pcbnew.B_Fab if fp.IsFlipped() else pcbnew.F_Fab)

# ---- まだ置かない部品: 基板の右の外に、シートごとに並べる ----
FIXED = set(EMIT.values()) | set(RECV.values()) | {'J5', 'J6', 'D98'} | set(LEDREF)
groups = {}
for c in comps:
    if c['ref'] not in FIXED:
        groups.setdefault(c['sheet'], []).append(c['ref'])
x0 = 60.0
for sheet in sorted(groups):
    refs = sorted(groups[sheet], key=lambda r: (re.sub(r'\d', '', r), int(re.sub(r'\D', '', r) or 0)))
    col, y = x0, 40.0
    wmax = 0
    for r in refs:
        fp = FPS[r]
        bb = fp.GetBoundingBox(False)
        w, hgt = pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())
        if y - hgt < -40:
            col += wmax + 2; y = 40.0; wmax = 0
        fp.SetPosition(P(col + w / 2, y - hgt / 2))
        y -= hgt + 1.5; wmax = max(wmax, w)
    x0 = col + wmax + 6

out = os.path.join(HERE, 'KOGUMA-Mk4.kicad_pcb')
board.Save(out)
# ---- 設計ルール(プロジェクトに書く。board.Save がプロジェクトを既定の値で書き直すので、そのあとで)----
# 細かいピッチの IC のパッドの間は KOGUMA-Mk4.kicad_dru
pro = os.path.join(HERE, 'KOGUMA-Mk4.kicad_pro')
d = json.load(open(pro))
enc = json.load(open(os.path.join(HERE, '../KOGUMA-Mk4_Encoder/KOGUMA-Mk4_Encoder.kicad_pro')))
d['board'] = enc['board']; d['net_settings'] = enc['net_settings']
json.dump(d, open(pro, 'w'), indent=2)
print('部品', len(FPS) + 4, 'ネット', len(netinfo), '→', out)

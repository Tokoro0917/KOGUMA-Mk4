"""メイン基板の配線(2026-10-31、自動配線の最初の案)
1. ネットクラスを決める(KOGUMA-Mk4.kicad_pro): 電池・VBAT は太く、モーター・ファンの出力、3.3V・GND は少し太く
2. Specctra DSN を書き出し、Freerouting(https://github.com/freerouting/freerouting)で自動配線する。
   GND は線で引かず両面のベタにするので、DSN から GND のネットを抜く
   2.1.0 はこの基板でほとんどつながらなかった(LED の線 16本だけでも、何周しても 11本残る)。1.9.0 を使う(画面が要るので xvfb-run)
3. 結果(SES)を読み込み、両面に GND のベタを敷く
   自動配線は線とクリアランスを 0.15mm で引くので、基板の縁(0.2mm)とエンコーダの穴(0.25mm)の決まりに合うよう、
   DSN の穴・ポケット・ホルダのほぞの穴のまわりの禁止の範囲を 0.05mm(エンコーダの穴は 0.1mm)広げる。
   (配線できる範囲を縁から 0.05mm 内側にする boundary も足してみたが、Freerouting 1.9.0 が 2時間たっても終わらなかった)
   Freerouting 1.9.0 は名前に日本語があると読み違えることがあるので、DSN では英字にして、SES で戻す
使い方(このフォルダで。基板は部品を置いただけの状態から):
  python3 route_pcb.py dsn     → /tmp/koguma_mk4_s1.dsn(GND を抜く)
  xvfb-run -a java -jar freerouting-1.9.0.jar -de /tmp/koguma_mk4_s1.dsn -do /tmp/koguma_mk4_s1.ses -mp 30
  python3 route_pcb.py ses1    → 1回目の配線を読み込む
  python3 route_pcb.py dsn2    → /tmp/koguma_mk4_s2.dsn(GND も入れ、1回目の配線はそのまま)
  xvfb-run -a java -jar freerouting-1.9.0.jar -de /tmp/koguma_mk4_s2.dsn -do /tmp/koguma_mk4_s2.ses -mp 30
  python3 route_pcb.py ses2    → 2回目の配線を読み込み、両面に GND のベタを敷いて保存"""
import os, sys, json, re
import pcbnew
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../mechanical/vehicle'))
import pcb_shape as ps
from shapely.geometry import LineString, Polygon
HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, 'KOGUMA-Mk4.kicad_pcb')
PRO = os.path.join(HERE, 'KOGUMA-Mk4.kicad_pro')
DSN = '/tmp/koguma_mk4.dsn'
OX, OY = 150.0, 100.0          # gen_pcb.py と同じ: 機体の (x, y) を KiCad の (OX + x, OY − y) に
ASCII = (('/電源/', '/PWR/'), ('/センサ/', '/SENS/'), ('/モーター/', '/MOT/'), ('/表示・通信/', '/UI/'), ('(仮)', '(TBD)'), ('(要選定)', '(TBD)'))
mm = pcbnew.FromMM

# 線の太さ [mm]: ふつうの線は 0.15mm(2026-10-31: MCU の QFN-68 は 0.4mm おきでパッドの幅 0.25mm。0.2mm の線ではピンから
# まっすぐ出しても隣のパッドまで 0.175mm でクリアランス 0.2mm を守れず、自動配線が MCU から出られなかった。0.15mm なら 0.2mm)。
# 3.3V も MCU のピンにつなぐのでふつうの線にし、太くしたい所はあとでベタで太くする
DEFAULT_W = 0.15
CLEARANCE = 0.15   # 2026-10-31: 0.15mm の線でも MCU のピンまでちょうど 0.2mm で、自動配線が入れなかった。0.15mm に(JLC の2層は 0.127mm まで作れる)
CLASSES = {
    'Battery': (0.5, ['/電源/BAT+', 'VBAT']),                                         # 電池から最大 8A(瞬間)
    'Motor':   (0.4, ['Net-(J2-Pin_1)', 'Net-(J2-Pin_2)', 'Net-(J3-Pin_1)', 'Net-(J3-Pin_2)', 'Net-(D40-A)', 'Net-(Q40-S)']),   # モーター 3A、ファン 1A
}

def set_classes():
    d = json.load(open(PRO))
    ns = d['net_settings']
    base = next(c for c in ns['classes'] if c['name'] == 'Default')
    base['track_width'] = DEFAULT_W; base['clearance'] = CLEARANCE
    ns['classes'] = [base] + [dict(base, name=n, track_width=w, priority=i) for i, (n, (w, _)) in enumerate(CLASSES.items())]
    ns['netclass_patterns'] = [dict(netclass=n, pattern=net) for n, (_, nets) in CLASSES.items() for net in nets]
    d['board']['design_settings']['rules']['min_clearance'] = CLEARANCE
    json.dump(d, open(PRO, 'w'), indent=2)


def dsn_path(geom, kind):
    """機体の座標の shapely の形 → DSN の path(um、y は KiCad の上下を逆に)"""
    pts = list(geom.exterior.coords)
    xy = '  '.join(f'{(OX + x) * 1000:.1f} {(y - OY) * 1000:.1f}' for x, y in pts)
    return f'(path {kind} 0  {xy})'

def fix_dsn(s, drop_gnd):
    """DSN を Freerouting 向けに直す: 配線できる範囲、禁止の範囲、英字の名前。drop_gnd なら GND のネットを抜く"""
    if drop_gnd:
        i = s.index('(net GND'); j = s.index('\n    )', i) + 6
        s = s[:i] + s[j:]
        s = s.replace(' GND ', ' ').replace(' GND\n', '\n')
    a, b = s.index('(structure'), s.index('(placement')
    st = re.sub(r'\n    \(keepout "" \(polygon signal 0 [^)]*\)\s*\)', '', s[a:b])
    o = ps.outline()
    bd = Polygon(o.exterior).buffer(-0.05, join_style=2)
    holes = [Polygon(r).buffer(0.05, join_style=2) for r in o.interiors] + [ps.slot(k).buffer(0.05) for k in ps.SENS]
    holes += [LineString([(-2.45, (y0 + y1) / 2), (2.45, (y0 + y1) / 2)]).buffer(0.5 + 0.1) for _, _, y0, y1 in ps.ENC]   # エンコーダの穴(NPTH 5.9 × 1.0)
    # 配線できる範囲(signal の boundary)を足すと Freerouting 1.9.0 が 2時間たっても終わらなかったので、禁止の範囲だけにする
    add = ''.join(f'\n    (keepout "" (polygon signal 0  {dsn_path(h, "x")[10:-1]}))' for h in holes)
    k = st.index('\n    )', st.index('(boundary')) + 6                    # 基板の外形の boundary のあと
    st = st[:k] + add + st[k:]
    s = s[:a] + st + s[b:]
    for x, y in ASCII:
        s = s.replace(x, y)
    return s

def import_ses(board, path):
    s = open(path).read()
    for x, y in ASCII:
        if x.startswith('/'):
            s = s.replace(y, x)
    open('/tmp/koguma_mk4_import.ses', 'w').write(s)
    for t in list(board.GetTracks()):
        board.Remove(t)
    assert pcbnew.ImportSpecctraSES(board, '/tmp/koguma_mk4_import.ses')

def gnd_zones(board):
    """両面に GND のベタ(電池の下・ファンのまわりも)。線とのすき間 0.25mm、パッドへはサーマル"""
    gnd = board.FindNet('GND')
    for z in list(board.Zones()):
        board.Remove(z)
    bb = board.GetBoardEdgesBoundingBox()
    for lay in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board); z.SetLayer(lay); z.SetNet(gnd)
        o = z.Outline(); o.NewOutline()
        for x, y in ((bb.GetLeft(), bb.GetTop()), (bb.GetRight(), bb.GetTop()), (bb.GetRight(), bb.GetBottom()), (bb.GetLeft(), bb.GetBottom())):
            o.Append(x, y)
        z.SetLocalClearance(mm(0.25)); z.SetMinThickness(mm(0.2))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL); z.SetThermalReliefGap(mm(0.25)); z.SetThermalReliefSpokeWidth(mm(0.3))
        z.SetIsFilled(False)
        board.Add(z)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())

cmd = sys.argv[1]
if cmd in ('dsn', 'dsn2'):
    set_classes()
    board = pcbnew.LoadBoard(PCB)
    if cmd == 'dsn':
        for t in list(board.GetTracks()):
            board.Remove(t)
    for z in list(board.Zones()):
        board.Remove(z)
    assert pcbnew.ExportSpecctraDSN(board, DSN)
    out = '/tmp/koguma_mk4_s1.dsn' if cmd == 'dsn' else '/tmp/koguma_mk4_s2.dsn'
    open(out, 'w').write(fix_dsn(open(DSN).read(), drop_gnd=(cmd == 'dsn')))
    print('→', out)
elif cmd in ('ses1', 'ses2'):
    board = pcbnew.LoadBoard(PCB)
    import_ses(board, f'/tmp/koguma_mk4_{"s1" if cmd == "ses1" else "s2"}.ses')
    if cmd == 'ses2':
        gnd_zones(board)
    board.Save(PCB)
    print('配線', len(board.GetTracks()), 'ゾーン', len(board.Zones()))

"""メイン基板の配線(2026-10-31、自動配線の最初の案)
1. ネットクラスを決める(KOGUMA-Mk4.kicad_pro): 電池・VBAT は太く、モーター・ファンの出力、3.3V・GND は少し太く
2. Specctra DSN を書き出し、Freerouting(https://github.com/freerouting/freerouting)で自動配線する。
   GND は線で引かず両面のベタにするので、DSN から GND のネットを抜く
   2.1.0 はこの基板でほとんどつながらなかった(LED の線 16本だけでも、何周しても 11本残る)。1.9.0 を使う(画面が要るので xvfb-run)
3. 結果(SES)を読み込み、両面に GND のベタを敷く
使い方(このフォルダで):
  python3 route_pcb.py dsn                        → /tmp/koguma_mk4.dsn と GND を抜いた /tmp/koguma_mk4_nognd.dsn(ネットクラスも書く)
  xvfb-run -a java -jar freerouting-1.9.0.jar -de /tmp/koguma_mk4_nognd.dsn -do /tmp/koguma_mk4_nognd.ses -mp 40
  python3 route_pcb.py ses                        → 配線を読み込み、GND のベタを敷いて保存"""
import os, sys, json
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, 'KOGUMA-Mk4.kicad_pcb')
PRO = os.path.join(HERE, 'KOGUMA-Mk4.kicad_pro')
DSN, SES = '/tmp/koguma_mk4.dsn', '/tmp/koguma_mk4_nognd.ses'
DSN_NOGND = '/tmp/koguma_mk4_nognd.dsn'
mm = pcbnew.FromMM

# 線の太さ [mm]: ふつうの線は 0.15mm(2026-10-31: MCU の QFN-68 は 0.4mm おきでパッドの幅 0.25mm。0.2mm の線ではピンから
# まっすぐ出しても隣のパッドまで 0.175mm でクリアランス 0.2mm を守れず、自動配線が MCU から出られなかった。0.15mm なら 0.2mm)。
# 3.3V も MCU のピンにつなぐのでふつうの線にし、太くしたい所はあとでベタで太くする
DEFAULT_W = 0.15
CLASSES = {
    'Battery': (0.5, ['/電源/BAT+', 'VBAT']),                                         # 電池から最大 8A(瞬間)
    'Motor':   (0.4, ['Net-(J2-Pin_1)', 'Net-(J2-Pin_2)', 'Net-(J3-Pin_1)', 'Net-(J3-Pin_2)', 'Net-(D40-A)', 'Net-(Q40-S)']),   # モーター 3A、ファン 1A
}

def set_classes():
    d = json.load(open(PRO))
    ns = d['net_settings']
    base = next(c for c in ns['classes'] if c['name'] == 'Default')
    base['track_width'] = DEFAULT_W
    ns['classes'] = [base] + [dict(base, name=n, track_width=w, priority=i) for i, (n, (w, _)) in enumerate(CLASSES.items())]
    ns['netclass_patterns'] = [dict(netclass=n, pattern=net) for n, (_, nets) in CLASSES.items() for net in nets]
    json.dump(d, open(PRO, 'w'), indent=2)

if sys.argv[1] == 'dsn':
    set_classes()
    board = pcbnew.LoadBoard(PCB)
    assert pcbnew.ExportSpecctraDSN(board, DSN)
    s = open(DSN).read()                                       # GND のネットを抜く(ベタにする)
    i = s.index('(net GND'); j = s.index('\n    )', i) + 6
    s = s[:i] + s[j:]
    s = s.replace(' GND ', ' ').replace(' GND\n', '\n')
    open(DSN_NOGND, 'w').write(s)
    print('→', DSN, DSN_NOGND)
elif sys.argv[1] == 'ses':
    board = pcbnew.LoadBoard(PCB)
    for t in list(board.GetTracks()):
        board.Remove(t)
    assert pcbnew.ImportSpecctraSES(board, SES)
    # 両面に GND のベタ(電池の下・ファンのまわりも)。線とのすき間 0.25mm、パッドへはサーマル
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
    board.Save(PCB)
    print('配線', len(board.GetTracks()), 'ゾーン', len(board.Zones()))

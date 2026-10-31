"""メイン基板の配線(2026-10-31、自動配線の最初の案)
1. ネットクラスを決める(KOGUMA-Mk4.kicad_pro): 電池・VBAT は太く、モーター・ファンの出力、3.3V・GND は少し太く
2. Specctra DSN を書き出し、Freerouting(https://github.com/freerouting/freerouting、2.1.0)で自動配線する
3. 結果(SES)を読み込み、両面に GND のベタを敷く
使い方(このフォルダで):
  python3 route_pcb.py dsn                        → /tmp/koguma_mk4.dsn(ネットクラスも書く)
  java -jar freerouting-2.1.0.jar -de /tmp/koguma_mk4.dsn -do /tmp/koguma_mk4.ses -mp 100
  python3 route_pcb.py ses                        → 配線を読み込み、GND のベタを敷いて保存"""
import os, sys, json
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, 'KOGUMA-Mk4.kicad_pcb')
PRO = os.path.join(HERE, 'KOGUMA-Mk4.kicad_pro')
DSN, SES = '/tmp/koguma_mk4.dsn', '/tmp/koguma_mk4.ses'
mm = pcbnew.FromMM

# 線の太さ [mm]: QFN のパッド(幅 0.25mm 前後)につなげる太さにしておき、太い電流はあとでベタ(塗りつぶし)で太くする
CLASSES = {
    'Battery': (0.5, ['/電源/BAT+', 'VBAT']),                                         # 電池から最大 8A(瞬間)
    'Motor':   (0.4, ['Net-(J2-Pin_1)', 'Net-(J2-Pin_2)', 'Net-(J3-Pin_1)', 'Net-(J3-Pin_2)', 'Net-(D40-A)', 'Net-(Q40-S)']),   # モーター 3A、ファン 1A
    'Supply':  (0.3, ['+3V3', 'GND', '/MCU/VCORE', 'Net-(U4-VLXSMPS)']),
}

def set_classes():
    d = json.load(open(PRO))
    ns = d['net_settings']
    base = next(c for c in ns['classes'] if c['name'] == 'Default')
    ns['classes'] = [base] + [dict(base, name=n, track_width=w, priority=i) for i, (n, (w, _)) in enumerate(CLASSES.items())]
    ns['netclass_patterns'] = [dict(netclass=n, pattern=net) for n, (_, nets) in CLASSES.items() for net in nets]
    json.dump(d, open(PRO, 'w'), indent=2)

if sys.argv[1] == 'dsn':
    set_classes()
    board = pcbnew.LoadBoard(PCB)
    assert pcbnew.ExportSpecctraDSN(board, DSN)
    print('→', DSN)
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

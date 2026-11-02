"""エンコーダの基板 v2(2026-11-02): メイン基板の裏に突き当ててはんだ付けする形に作り直す
マウント v11・基板 v18 に合わせる: 6.0 × 10.3 × 0.6mm(x −3.0〜3.0、z 3.3〜13.6)。上の辺をメイン基板の裏に当てる。
- チップの面(F)は外を向き、上の 2.3mm(z 11.3〜13.6)はマウントの面に当たる(ここにはんだのフィレットは作れない)。
  なので **パッド7つはすべて裏の面(B、内側)** に並べる(0.8mm おき、幅 0.5mm、上の辺から 0.2〜1.2mm。ToraNeko の TN_ENC_Edge と同じ高さ)
- MT6835 の中心は x 0、z 7.5(上の辺から 6.1mm)。ピン 1〜8(SPI・CAL_EN)を上に向け、5本はチップの面から上のビアで裏のパッドへ
- C1(0.1µF)は裏の面。VDD・VSS はチップの下のビアで裏に移り、C1 を通って上のパッドへ
メイン基板の側のフットプリント `ENC_Base_Butt`(../KOGUMA-Mk4/KOGUMA-Mk4.pretty)もここで作る(メイン基板の裏のパッド、内側に 0.3〜1.3mm)
使い方(このフォルダで): python3 gen_encoder.py
"""
import os, uuid
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, 'KOGUMA-Mk4_Encoder.kicad_pcb')
LIB = os.path.join(HERE, 'KOGUMA-Mk4_Encoder.pretty')
BASE_LIB = os.path.join(HERE, '../KOGUMA-Mk4/KOGUMA-Mk4.pretty')
mm = pcbnew.FromMM
U = lambda: str(uuid.uuid4())

W, H, T = 6.0, 10.3, 0.6           # 幅、高さ、厚さ
CHIP = 6.1                          # 上の辺から MT6835 の中心
PITCH, PW, PH, P0 = 0.8, 0.5, 1.0, 0.2   # パッドのピッチ、幅、高さ、上の辺からの始まり
# パッドの x(チップの面から見て。番号は回路図の J1): 信号はチップのピンの真上に近い順に並べ、電源は右の端
PADS = {6: -2.4, 5: -1.6, 4: -0.8, 3: 0.0, 2: 0.8, 1: 1.6, 7: 2.4}
NAMES = {1: '+3V3', 2: 'ENC_CAL', 3: 'ENC_MISO', 4: 'ENC_MOSI', 5: 'ENC_SCK', 6: 'ENC_CS', 7: 'GND'}
POCKET = (2.3, 9.8)                 # マウントのくぼみ(上の辺から。z 11.3〜3.8)

def line(x0, y0, x1, y1, layer, w=0.05):
    return f'''	(fp_line (start {x0:g} {y0:g}) (end {x1:g} {y1:g}) (stroke (width {w}) (type solid)) (layer "{layer}") (uuid "{U()}"))\n'''

def text(s, x, y, layer, size=0.3, kind='user'):
    return f'''	(fp_text {kind} "{s}" (at {x:g} {y:g} 0) (layer "{layer}") (uuid "{U()}") (effects (font (size {size} {size}) (thickness {size * 0.15:g}))))\n'''

def pad(num, x, y, w, h, side):
    return f'''	(pad "{num}" smd roundrect (at {x:g} {y:g}) (size {w:g} {h:g}) (layers "{side}.Cu" "{side}.Mask" "{side}.Paste") (roundrect_rratio 0.1) (uuid "{U()}"))\n'''

def prop(name, val, x, y, layer, hide=False, size=0.5):
    return f'''	(property "{name}" "{val}" (at {x:g} {y:g} 0) (layer "{layer}"){" (hide yes)" if hide else ""} (uuid "{U()}") (effects (font (size {size:g} {size:g}) (thickness {size * 0.15:g}))))\n'''

def edge_fp():          # 参照の名前は基板が小さいのでシルクに出さない(F.Fab)
    yc = P0 + PH / 2
    s = f'''(footprint "ENC_Edge"
	(version 20241229)
	(generator "gen_encoder.py")
	(layer "F.Cu")
	(descr "KOGUMA MK4 encoder board v2 ({W}x{H}x{T}, motor mount v11): pads at the edge that butts against the underside of the main board. All 7 pads on the back (B, inner side), {P0}-{P0 + PH}mm from the edge, pitch {PITCH}mm, because the chip side touches the mount face from the edge down to {POCKET[0]}mm. Magnet axis at {CHIP}mm")
	(tags "encoder edge KOGUMA")
''' + prop('Reference', 'REF**', 0, -0.9, 'F.Fab') + prop('Value', 'ENC_Edge', 0, H + 0.6, 'F.Fab') + \
        prop('Datasheet', '', 0, 0, 'F.Fab', True) + prop('Description', '', 0, 0, 'F.Fab', True) + '	(attr smd)\n'
    for n, x in PADS.items():
        s += pad(n, x, yc, PW, PH, 'B')
    s += line(-W / 2 - 0.15, 0, W / 2 + 0.15, 0, 'Dwgs.User') + text('MAIN BOARD UNDERSIDE (z 13.6)', 0, -0.35, 'Dwgs.User')
    s += line(-W / 2 - 0.15, POCKET[0], W / 2 + 0.15, POCKET[0], 'Dwgs.User') + text('MOUNT FACE ABOVE / POCKET BELOW (z 11.3)', 0, POCKET[0] - 0.3, 'Dwgs.User', 0.25)
    s += line(-W / 2 - 0.15, POCKET[1], W / 2 + 0.15, POCKET[1], 'Dwgs.User') + text('POCKET BOTTOM (z 3.8)', 0, POCKET[1] + 0.35, 'Dwgs.User', 0.25)
    s += line(-1, CHIP, 1, CHIP, 'Dwgs.User') + line(0, CHIP - 1, 0, CHIP + 1, 'Dwgs.User') + text('MAGNET AXIS', 1.9, CHIP, 'Dwgs.User', 0.25)
    s += line(-W / 2 - 0.15, H, W / 2 + 0.15, H, 'Dwgs.User') + text('BOTTOM EDGE z 3.3 (FRAME TOP z 3.0)', 0, H + 0.3, 'Dwgs.User', 0.25)
    s += text('PADS ON BACK (B)', 0, P0 + PH + 0.35, 'Dwgs.User', 0.25)
    return s + ')\n'

def base_fp():
    """メイン基板の裏のパッド。エンコーダ基板の真ん中が原点、チップの面が −Y(回転 0 で左のエンコーダ。右は 180°)。
    x はエンコーダ基板と逆向き(チップの面から見た右が、機体の後ろ = 画面の左)"""
    s = f'''(footprint "ENC_Base_Butt"
	(version 20241229)
	(generator "gen_encoder.py")
	(layer "F.Cu")
	(descr "KOGUMA MK4 main board: pads on the underside (B.Cu) for the encoder board v2 ({W}x{T}mm) butted against the bottom face. Encoder board between Y -0.3 and +0.3; chip side = -Y (outer, touches the motor mount), pads on the inner side +0.3 to +1.3mm. Rotation 0 = left encoder of the robot; rotate 180deg for the right encoder. No hole")
	(tags "encoder KOGUMA butt")
''' + prop('Reference', 'REF**', 0, -1.2, 'F.SilkS', size=0.8) + prop('Value', 'ENC_Base_Butt', 0, 2.0, 'F.Fab') + \
        prop('Datasheet', '', 0, 0, 'F.Fab', True) + prop('Description', '', 0, 0, 'F.Fab', True) + '	(attr smd)\n'
    for n, x in PADS.items():
        s += pad(n, -x, T / 2 + PH / 2, PW, PH, 'B')
    for (x0, y0, x1, y1) in ((-W / 2, -T / 2, W / 2, -T / 2), (W / 2, -T / 2, W / 2, T / 2), (W / 2, T / 2, -W / 2, T / 2), (-W / 2, T / 2, -W / 2, -T / 2)):
        s += line(x0, y0, x1, y1, 'B.Fab', 0.1) + line(x0, y0, x1, y1, 'Dwgs.User', 0.05)
    s += text('ENC (CHIP SIDE -Y)', 0, -0.75, 'Dwgs.User', 0.3)
    return s + ')\n'

open(os.path.join(LIB, 'ENC_Edge.kicad_mod'), 'w').write(edge_fp())
open(os.path.join(BASE_LIB, 'ENC_Base_Butt.kicad_mod'), 'w').write(base_fp())

# ---------------- 基板 ----------------
OX, OY = 100.0, 100.0           # 上の辺の真ん中
P = lambda x, y: pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))
b = pcbnew.LoadBoard(PCB)
edges = [d for d in b.Drawings() if d.GetLayerName() == 'Edge.Cuts']   # 線を消すより前に集める(あとだと SWIG が壊れる)
tracks = list(b.GetTracks())
for d in edges + tracks:
    b.Remove(d)
for (x0, y0, x1, y1) in ((-W / 2, 0, W / 2, 0), (W / 2, 0, W / 2, H), (W / 2, H, -W / 2, H), (-W / 2, H, -W / 2, 0)):
    s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.05))
    s.SetStart(P(x0, y0)); s.SetEnd(P(x1, y1)); b.Add(s)

fps = {fp.GetReference(): fp for fp in b.GetFootprints()}
# J1 を新しいフットプリントに置きかえる(ネットはパッドの番号で引きつぐ)
old = fps['J1']; nets = {p.GetNumber(): p.GetNet() for p in old.Pads()}
new = pcbnew.FootprintLoad(LIB, 'ENC_Edge')
new.SetReference('J1'); new.SetValue(old.GetValue()); new.SetFPIDAsString('KOGUMA-Mk4_Encoder:ENC_Edge')
new.SetPath(old.GetPath()); new.SetPosition(P(0, 0))
for p in new.Pads():
    p.SetNet(nets[p.GetNumber()])
b.Remove(old); b.Add(new); fps['J1'] = new
fps['U1'].SetPosition(P(0, CHIP)); fps['U1'].SetOrientationDegrees(-90)
fps['C1'].SetPosition(P(1.92, 4.5))
pads = {(r, p.GetNumber()): p for r, fp in fps.items() for p in fp.Pads()}
if pcbnew.ToMM(pads[('C1', '1')].GetPosition().x) > pcbnew.ToMM(pads[('C1', '2')].GetPosition().x):
    fps['C1'].SetOrientationDegrees(fps['C1'].GetOrientationDegrees() + 180)
xy = lambda r, n: (pcbnew.ToMM(pads[(r, n)].GetPosition().x) - OX, pcbnew.ToMM(pads[(r, n)].GetPosition().y) - OY)
net = lambda r, n: pads[(r, n)].GetNet()

def track(pts, layer, w, nt):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b); t.SetStart(P(x0, y0)); t.SetEnd(P(x1, y1)); t.SetLayer(layer); t.SetWidth(mm(w)); t.SetNet(nt); b.Add(t)

def via(x, y, nt):
    v = pcbnew.PCB_VIA(b); v.SetPosition(P(x, y)); v.SetWidth(mm(0.6)); v.SetDrill(mm(0.3)); v.SetNet(nt); b.Add(v)

F, B = pcbnew.F_Cu, pcbnew.B_Cu
VIA_Y = 1.85                         # 信号のビア(J1 のパッドの下の端 1.2mm とチップのパッドの上の端 2.5mm の間)
for pin, jn in (('4', 2), ('5', 3), ('6', 4), ('7', 5), ('8', 6)):        # CAL・MISO・MOSI・SCK・CS
    px, py = xy('U1', pin); jx, jy = xy('J1', str(jn)); nt = net('U1', pin)
    assert nt.GetNetCode() == net('J1', str(jn)).GetNetCode(), (pin, jn)
    track([(px, py), (px, 2.4), (jx, VIA_Y)], F, 0.2, nt)
    via(jx, VIA_Y, nt)
    track([(jx, VIA_Y), (jx, jy)], B, 0.2, nt)
# 電源: VDD(9)は左下のビアで裏へ、GND(11〜13)はつないで 13 の上のビアで裏へ。裏で C1 を通って J1 の 1・7 へ
VIA_P = 7.6                          # 下の列のパッドの上の端(上の辺から 8.22mm)の 0.62mm 上
x9, y9 = xy('U1', '9'); x11, y11 = xy('U1', '11'); x13, y13 = xy('U1', '13')
v3, gnd = net('U1', '9'), net('U1', '11')
track([(x9, y9), (x9, VIA_P)], F, 0.3, v3); via(x9, VIA_P, v3)
track([(x11, y11 + 0.39), (x13, y13 + 0.39)], F, 0.3, gnd); track([(x13, y13), (x13, VIA_P)], F, 0.3, gnd); via(x13, VIA_P, gnd)
c1, c2 = xy('C1', '1'), xy('C1', '2'); j1, j7 = xy('J1', '1'), xy('J1', '7')
track([j1, (j1[0], c1[1] - 0.6), c1, (c1[0] - 0.44, c1[1] + 0.7), (x9, c1[1] + 0.7), (x9, VIA_P)], B, 0.3, v3)
track([j7, c2, (c2[0], VIA_P), (x13, VIA_P)], B, 0.3, gnd)
b.Save(PCB)
print('ok', {k: tuple(round(v, 3) for v in xy(*k)) for k in (('J1', '1'), ('J1', '7'), ('C1', '1'), ('C1', '2'), ('U1', '1'), ('U1', '9'))})

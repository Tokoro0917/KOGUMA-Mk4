"""タイヤ24mm 用のエンコーダ基板(KOGUMA-Mk4_Encoder_t24、2026-11-21、ブランチ claude/trusting-dirac-1tdt54)を作る。
KiCad 9 の pcbnew で動かす(Ubuntu 24.04 の KiCad は Python 3.12 向けなので /usr/bin/python3.12。3.13 では落ちる)。使い方(リポジトリの一番上で): /usr/bin/python3.12 hardware/kicad/make_encoder_t24.py
main のエンコーダ基板(KOGUMA-Mk4_Encoder、回路は同じ: MT6835・C1・J1 のパッド7つ)をもとに、新しいディレクトリへ作る:
  - 基板 6.0 × 8.75 × 0.6mm。機体では z 8.15〜16.9(MT6835 の中心 = 車軸 z 12.0)。メイン基板(z 13.6〜14.2)の切り欠きの縁に沿って立て、上へ出す
  - J1 のパッド7つは**裏の面(B、内側。メイン基板の側)**に、ピッチ 0.8mm、0.5 × 3.6mm、z 12.4〜16.0。
    2026-11-25(ユーザー: 表裏どちらでもはんだで固定できるように、同じ基板で): メイン基板の上の面の上(z 14.2〜16.0)と、裏の面の下(z 12.4〜13.6)の
    両方にかかる長いパッドにした。メイン基板の上の面のパッド・裏の面のパッドのどちらとも(両方とも)直角にはんだ付けできる。左右とも同じ基板
    並び(チップの面から見て左から): CS・SCK・MOSI・MISO・CAL・GND・3V3。信号はチップの面(F)のピンから斜めに上へ出し、パッドの真上のビアで裏へ
  - 3V3・GND は、チップの下の段のピン(9・11〜13)からビアで裏へ移り、C1(0402、裏)を通って、3V3 は右の縁に沿って、GND はパッドの下の端の下を横に通ってパッドへ
  - メイン基板の側のフットプリント ENC_Base_Edge_T24(KOGUMA-Mk4.pretty)も作る
座標は KiCad の基板の座標(y は下向き)。チップの面(F)から見て、+x が右、上の辺が y 100.0"""
import os, shutil, math
import pcbnew

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'KOGUMA-Mk4_Encoder')
DST = os.path.join(ROOT, 'KOGUMA-Mk4_Encoder_t24')
NAME = 'KOGUMA-Mk4_Encoder_t24'
MM = pcbnew.FromMM

# ---- 寸法(チップの中心からの y、下が +)----
X0, X1 = 97.0, 103.0           # 基板の左右(6.0mm)
CY = 104.9                     # MT6835 の中心
TOP, BOT = CY - 4.9, CY + 3.85  # 上の辺 100.0、下の辺 108.75(z 16.9、8.15)
PAD_Y0, PAD_Y1 = CY - 4.0, CY - 0.4     # 裏のパッド(z 16.0〜12.4)。メイン基板(z 13.6〜14.2)の上と下の両方にかかる(2026-11-25)
GND_Y = PAD_Y1 + 0.5           # GND の線がパッドの下の端の下を横に通る所(パッドと 0.35mm あける)
VIA_Y = TOP + 0.55             # 信号のビア(縁から 0.25)
PITCH = 0.8                    # 0.85 では外のビア(φ0.6)が基板の縁から 0.15mm になる
ORDER = ['6', '5', '4', '3', '2', '7', '1']   # 左から: CS, SCK, MOSI, MISO, CAL, GND, 3V3(J1 のピン番号)
PAD_X = {n: round(100.0 + PITCH * (i - 3), 4) for i, n in enumerate(ORDER)}
SIG = {'2': 4, '3': 5, '4': 6, '5': 7, '6': 8}  # J1 のピン → MT6835 のピン(CAL, MISO, MOSI, SCK, CS)

def ensure_project():
    os.makedirs(DST, exist_ok=True)      # README.md・絵など、ここで作らないファイルは消さない
    for fn in os.listdir(SRC):
        s = os.path.join(SRC, fn)
        if fn == 'README.md':
            continue
        proj = fn.startswith('KOGUMA-Mk4_Encoder.kicad_') and fn.split('.')[-1] in ('kicad_pro', 'kicad_sch', 'kicad_pcb')   # 記号ライブラリ(.kicad_sym)は名前を変えない
        d = os.path.join(DST, fn.replace('KOGUMA-Mk4_Encoder.', NAME + '.') if proj else fn)
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            shutil.copy(s, d)
    sch = os.path.join(DST, NAME + '.kicad_sch')     # 回路図の J1 のフットプリントを新しいものに
    t = open(sch).read()
    assert t.count('"KOGUMA-Mk4_Encoder:ENC_Edge"') == 1
    open(sch, 'w').write(t.replace('"KOGUMA-Mk4_Encoder:ENC_Edge"', '"KOGUMA-Mk4_Encoder:ENC_Edge_T24"'))

def edge_pad_fp():
    """エンコーダ基板の J1(裏のパッド7つ)"""
    fp = pcbnew.FOOTPRINT(None)
    fp.SetFPID(pcbnew.LIB_ID('KOGUMA-Mk4_Encoder', 'ENC_Edge_T24'))
    fp.SetLibDescription('KOGUMA MK4 encoder board for tire 24mm (6.0x8.75x0.6): 7 pads on the BACK (B, toward the main board), '
                         'pitch 0.8, 0.5x3.6mm, 0.9-4.5mm from the top edge (main board top face at 2.7mm, bottom face at 3.3mm): '
                         'can be soldered to the main board on its top face, its bottom face, or both. '
                         'Order seen from the chip side, left to right: 6 CS, 5 SCK, 4 MOSI, 3 MISO, 2 CAL, 7 GND, 1 3V3. Magnet axis at 4.9mm from the top edge')
    fp.SetAttributes(pcbnew.FP_SMD)
    for n in ORDER:
        p = pcbnew.PAD(fp)
        p.SetNumber(n); p.SetShape(pcbnew.PAD_SHAPE_ROUNDRECT); p.SetRoundRectRadiusRatio(0.1)
        p.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        ls = pcbnew.LSET(); ls.AddLayer(pcbnew.B_Cu); ls.AddLayer(pcbnew.B_Mask); ls.AddLayer(pcbnew.B_Paste)
        p.SetLayerSet(ls)
        p.SetSize(pcbnew.VECTOR2I(MM(0.5), MM(PAD_Y1 - PAD_Y0)))
        p.SetPosition(pcbnew.VECTOR2I(MM(round(PAD_X[n] - 100.0, 4)), MM((PAD_Y0 + PAD_Y1) / 2 - TOP)))
        fp.Add(p)
    return fp

def base_fp():
    """メイン基板の側: 切り欠きの縁(local Y = 0)の内側、**上の面と裏の面の両方**にパッド7つずつ(2026-11-25、ユーザー: 表裏どちらでもはんだで固定できるように)。
    上と裏の同じ番号のパッドは同じピン(KiCad では同じ番号のパッドは同じネットになる)。上と裏をつなぐビアは配線のときに置く。
    回転 0 = チップの面(縁の外)が画面の上 = 左のエンコーダ(J5)。右(J6)は 180°。
    原点は縁の上の、エンコーダ基板の真ん中(機体の x 0)。エンコーダ基板の裏の面は縁にぴったり(local Y 0。2026-11-24 にすき間 0.2mm をやめた。ユーザー)"""
    fp = pcbnew.FOOTPRINT(None)
    fp.SetFPID(pcbnew.LIB_ID('KOGUMA-Mk4', 'ENC_Base_Edge_T24'))
    fp.SetLibDescription('KOGUMA MK4 main board for tire 24mm: solder pads on BOTH the top and the bottom side along the cutout edge (local Y=0) for the encoder board '
                         'standing right at the edge (back face at Y=0, chip face at Y=-0.6). Pads 0.5x0.8 from Y=0.2 to 1.0, pitch 0.8. '
                         'Rotation 0 = chip side toward the top of the screen (left encoder J5, edge at robot y +16.9); rotate 180deg for the right encoder J6 (y -16.9)')
    fp.SetAttributes(pcbnew.FP_SMD)
    # 上の面(F)のパッド7つ、続けて裏の面(B)のパッド7つ。裏は上の真下(上から見て同じ位置)
    for layers in ((pcbnew.F_Cu, pcbnew.F_Mask, pcbnew.F_Paste), (pcbnew.B_Cu, pcbnew.B_Mask, pcbnew.B_Paste)):
        for n in ORDER:
            p = pcbnew.PAD(fp)
            p.SetNumber(n); p.SetShape(pcbnew.PAD_SHAPE_ROUNDRECT); p.SetRoundRectRadiusRatio(0.1)
            p.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
            ls = pcbnew.LSET()
            for layer in layers:
                ls.AddLayer(layer)
            p.SetLayerSet(ls)
            p.SetSize(pcbnew.VECTOR2I(MM(0.5), MM(0.8)))
            p.SetPosition(pcbnew.VECTOR2I(MM(round(-(PAD_X[n] - 100.0), 4)), MM(0.6)))   # 左のエンコーダ: チップの面から見た左右が、上から見ると逆
            fp.Add(p)
    # F.Fab: エンコーダ基板(0.6mm)と縁
    for (a, b) in (((-3.0, 0.0), (3.0, 0.0)), ((-3.0, -0.6), (3.0, -0.6)), ((-3.0, 0.0), (-3.0, -0.6)), ((3.0, 0.0), (3.0, -0.6)), ((-4.5, 0.0), (4.5, 0.0))):
        s = pcbnew.PCB_SHAPE(fp); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(pcbnew.F_Fab); s.SetWidth(MM(0.05))
        s.SetStart(pcbnew.VECTOR2I(MM(a[0]), MM(a[1]))); s.SetEnd(pcbnew.VECTOR2I(MM(b[0]), MM(b[1]))); fp.Add(s)
    return fp

def save_fp(fp, libdir, name):
    fp.SetFPID(pcbnew.LIB_ID('', name))
    pcbnew.FootprintSave(libdir, fp)

def track(b, net, layer, pts, w):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b); t.SetStart(pcbnew.VECTOR2I(MM(x0), MM(y0))); t.SetEnd(pcbnew.VECTOR2I(MM(x1), MM(y1)))
        t.SetWidth(MM(w)); t.SetLayer(layer); t.SetNet(net); b.Add(t)

def via(b, net, x, y):
    v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y))); v.SetWidth(MM(0.6)); v.SetDrill(MM(0.3)); v.SetNet(net); b.Add(v)

def build():
    ensure_project()
    lib = os.path.join(DST, 'KOGUMA-Mk4_Encoder.pretty')
    save_fp(edge_pad_fp(), lib, 'ENC_Edge_T24')
    save_fp(base_fp(), os.path.join(ROOT, 'KOGUMA-Mk4', 'KOGUMA-Mk4.pretty'), 'ENC_Base_Edge_T24')
    path = os.path.join(DST, NAME + '.kicad_pcb')
    # 古い配線(segment・via)・外形・文字(gr_*)は、読み込む前にファイルの文字の上で消す
    # (KiCad 9.0.9 の Python では、GetDrawings() が使えず、Remove() でトラックを消すと GetFootprints() が壊れるため)
    text = open(path).read()
    for blk in top_blocks(text):
        if blk.lstrip().startswith(('(segment', '(via', '(gr_')):
            text = text.replace('\t' + blk + '\n', '', 1)
    open(path, 'w').write(text)
    b = pcbnew.LoadBoard(path)
    nets = {n.GetNetname(): n for n in b.GetNetsByName().values()}
    fps = {f.GetReference(): f for f in b.GetFootprints()}   # 一覧は最初に1回だけ取る
    # 外形
    for (a, c) in (((X0, TOP), (X1, TOP)), ((X1, TOP), (X1, BOT)), ((X1, BOT), (X0, BOT)), ((X0, BOT), (X0, TOP))):
        s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(MM(0.05))
        s.SetStart(pcbnew.VECTOR2I(MM(a[0]), MM(a[1]))); s.SetEnd(pcbnew.VECTOR2I(MM(c[0]), MM(c[1]))); b.Add(s)
    for txt, y in (('KOGUMA MK4 ENC t24 (MT6835)  6.0 x 8.75 x 0.6mm, 2 layers, tire 24mm / mount t24v2', TOP - 2.0),
                   ('chip side = F (faces the magnet). J1 pads on B (toward the main board), soldered on the main board top and/or bottom face. C1 on B', TOP - 1.4),
                   ('robot z: top edge 16.9, J1 pads 16.0-12.4, main board 14.2-13.6, chip center 12.0, bottom edge 8.15', TOP - 0.8)):
        t = pcbnew.PCB_TEXT(b); t.SetText(txt); t.SetLayer(pcbnew.Cmts_User); t.SetTextSize(pcbnew.VECTOR2I(MM(0.4), MM(0.4)))
        t.SetPosition(pcbnew.VECTOR2I(MM(100.0), MM(y))); b.Add(t)
    # J1 を新しいフットプリントに(ネットは古い J1 のパッドから写す)
    old = fps['J1']; padnet = {p.GetNumber(): p.GetNet() for p in old.Pads()}
    new = edge_pad_fp(); new.SetReference('J1'); new.SetValue(old.GetValue())
    new.SetPosition(pcbnew.VECTOR2I(MM(100.0), MM(TOP)))
    for p in new.Pads():
        p.SetNet(padnet[p.GetNumber()])
    new.Reference().SetVisible(False); new.Value().SetVisible(False)
    new.SetPath(old.GetPath()); new.SetSheetname(old.GetSheetname()); new.SetSheetfile(old.GetSheetfile())
    b.Remove(old); b.Add(new)
    # MT6835 と C1
    u1 = fps['U1']; u1.SetPosition(pcbnew.VECTOR2I(MM(100.0), MM(CY)))
    c1 = fps['C1']; c1.SetPosition(pcbnew.VECTOR2I(MM(98.725), MM(CY + 0.6)))
    for f in (u1, c1):
        f.Reference().SetVisible(False)
    upad = {p.GetNumber(): p for p in u1.Pads()}
    # ---- 信号: チップのピンの上の端から斜めにパッドの真上のビアへ(F)、ビアからパッドへ(B)----
    for jn, un in SIG.items():
        p = upad[str(un)]; net = p.GetNet()
        px = p.GetPosition().x / 1e6; py_end = (p.GetPosition().y - p.GetSize().x / 2) / 1e6   # 回転 -90 なので長い方が y。上の段のピンの上の端
        tx = PAD_X[jn]; dx = tx - px
        y_bend = py_end - 0.15
        track(b, net, pcbnew.F_Cu, [(px, py_end + 0.1), (px, y_bend), (tx, y_bend - abs(dx)), (tx, VIA_Y)], 0.2)
        via(b, net, tx, VIA_Y)
        track(b, net, pcbnew.B_Cu, [(tx, VIA_Y), (tx, PAD_Y0 + 0.3)], 0.3)
    # ---- 電源: 下の段のピン → ビア → C1(B)→ 右の縁に沿ってパッドへ ----
    n3, ng = nets['+3V3'], nets['GND']
    p9, p12 = upad['9'], upad['12']
    x9, y9 = p9.GetPosition().x / 1e6, (p9.GetPosition().y - p9.GetSize().x / 2) / 1e6
    x12, y12 = p12.GetPosition().x / 1e6, (p12.GetPosition().y - p12.GetSize().x / 2) / 1e6
    v3 = (x9 + 0.375, CY + 1.4); vg = (x12 - 0.325, CY + 1.4)
    track(b, n3, pcbnew.F_Cu, [(x9, y9 + 0.1), (x9, y9 - 0.3), v3], 0.3); via(b, n3, *v3)
    track(b, ng, pcbnew.F_Cu, [(x12, y12 + 0.1), (x12, y12 - 0.3), vg], 0.3); via(b, ng, *vg)
    yg = upad['11'].GetPosition().y / 1e6 + 0.037
    track(b, ng, pcbnew.F_Cu, [(upad['11'].GetPosition().x / 1e6, yg), (upad['13'].GetPosition().x / 1e6, yg)], 0.2)
    c1p = {p.GetNumber(): p for p in c1.Pads()}
    c3 = (c1p['1'].GetPosition().x / 1e6, c1p['1'].GetPosition().y / 1e6); cg = (c1p['2'].GetPosition().x / 1e6, c1p['2'].GetPosition().y / 1e6)
    x3, xg = PAD_X['1'], PAD_X['7']
    y_low = BOT - 0.55
    track(b, n3, pcbnew.B_Cu, [v3, c3, (c3[0], y_low), (x3, y_low), (x3, PAD_Y1 - 0.3)], 0.3)
    track(b, ng, pcbnew.B_Cu, [vg, cg], 0.3)
    # GND: ビアから 45° で右上へ、パッドの下の端より下(GND_Y)まで来たら横へ、x = GND のパッドに来たら真上へ。
    # パッドを長くした(2026-11-25)ので、ほかのパッドの下の端をよけて横に通る
    d = vg[1] - GND_Y
    track(b, ng, pcbnew.B_Cu, [vg, (vg[0] + d, GND_Y), (xg, GND_Y), (xg, PAD_Y1 - 0.3)], 0.3)
    b.Save(path)
    return path

def top_blocks(text):
    """(kicad_pcb ...) のすぐ下の S 式を、文字列のまま順に返す"""
    out, depth, start, i, n, instr = [], 0, None, 0, len(text), False
    while i < n:
        c = text[i]
        if instr:
            if c == '\\': i += 1
            elif c == '"': instr = False
        elif c == '"': instr = True
        elif c == '(':
            depth += 1
            if depth == 2: start = i
        elif c == ')':
            if depth == 2: out.append(text[start:i + 1])
            depth -= 1
        i += 1
    return out

def blk_uuid(blk):
    import re
    m = re.search(r'\n\t\t\(uuid "([0-9a-f-]+)"\)', blk)
    return m.group(1) if m else None

if __name__ == '__main__':
    print(build())

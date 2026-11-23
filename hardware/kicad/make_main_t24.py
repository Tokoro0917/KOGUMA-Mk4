"""タイヤ24mm 用のメイン基板の土台(KOGUMA-Mk4_t24、2026-11-21、ブランチ claude/trusting-dirac-1tdt54)を作る。
KiCad 9 の pcbnew で動かす(Ubuntu 24.04 の KiCad は Python 3.12 向け): /usr/bin/python3.12 hardware/kicad/make_main_t24.py
標準のフットプリント(/usr/share/kicad/footprints、パッケージ kicad-footprints)を使う。

  1. main の回路図(KOGUMA-Mk4)を KOGUMA-Mk4_t24 に写す。J5・J6 のフットプリントを ENC_Base_Edge_T24 に替える(回路は同じ)
  2. 回路図からネットリストを出し(kicad-cli)、部品とネットをすべて基板に読み込む(回路図とのつながり = KIID のパスも付ける)
  3. 外形: mechanical/vehicle/pcb_t24.py の外形(t24v3、案1)を Edge.Cuts に。壁センサのホルダのほぞの穴はフットプリントに入っている
  4. 機構で位置が決まる部品を置く: エンコーダのパッド J5・J6、壁センサのホルダ D70〜D77(裏)、UI の LED D90〜D96、ねじの穴 4つ(基板だけの部品)。
     ほかの部品は、基板の右に、回路図のシートごとに並べておく(配置と配線はこれから)
  5. 置いた壁センサの足の穴が pcb_shape.pads() と合っているか確かめる
座標: KiCad の X = 150 + x、Y = 100 − y(x は機体の前、y は左。画面の上が機体の左)
"""
import os, re, shutil, subprocess, sys, math
import pcbnew

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(ROOT, '../..')
SRC = os.path.join(ROOT, 'KOGUMA-Mk4')
NAME = 'KOGUMA-Mk4_t24'
DST = os.path.join(ROOT, NAME)
STD = '/usr/share/kicad/footprints'
OX, OY = 150.0, 100.0
MM = pcbnew.FromMM
def P(x, y):
    return pcbnew.VECTOR2I(MM(OX + x), MM(OY - y))

# 機構の値(機体の座標)。shapely が要るので、ふつうの python3 で計算して JSON でもらう(KiCad の Python 3.12 には入っていない)
GEOM = r'''
import json, sys, os
sys.path.insert(0, 'mechanical/vehicle'); sys.path.insert(0, 'docs/calc/frame')
import pcb_t24, pcb_shape as ps
o = ps.outline()
rings = [list(r.coords) for g in getattr(o, 'geoms', [o]) for r in [g.exterior] + list(g.interiors)]
print(json.dumps(dict(rings=rings, SENS=ps.SENS, LEDS=ps.LEDS, LED_FRONT=ps.LED_FRONT, SCREWS=ps.SCREWS,
                      pads={k: dict(emit=ps.pads(k, 'emit'), recv=ps.pads(k, 'recv')) for k in ps.SENS})))
'''
import json
_g = json.loads(subprocess.run(['python3', '-c', GEOM], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip().splitlines()[-1])
class ps:
    SENS = {k: (tuple(v[0]), v[1]) for k, v in _g['SENS'].items()}
    LEDS = [tuple(p) for p in _g['LEDS']]
    LED_FRONT = tuple(_g['LED_FRONT'])
    SCREWS = [tuple(p) for p in _g['SCREWS']]
    @staticmethod
    def pads(nm, part):
        return [tuple(p) for p in _g['pads'][nm][part]]
UI_LEDS = ['D90', 'D91', 'D92', 'D93', 'D94', 'D95', 'D96']   # ps.LEDS の順(左の角2つ、V 字の先3つ、右の角2つ)に置く。仮
SENSORS = {'FL': ('D70', 'D74'), 'L': ('D71', 'D77'), 'R': ('D72', 'D75'), 'FR': ('D73', 'D76')}   # (発光, 受光)。回路図の値の (FL) などから

# ---- 1. プロジェクト ----
def ensure_project():
    os.makedirs(DST, exist_ok=True)
    for fn in os.listdir(SRC):
        if not fn.endswith('.kicad_sch') and fn != 'KOGUMA-Mk4.kicad_pro':
            continue
        d = os.path.join(DST, fn.replace('KOGUMA-Mk4.', NAME + '.') if fn.startswith('KOGUMA-Mk4.') else fn)
        t = open(os.path.join(SRC, fn)).read()
        t = t.replace('(project "KOGUMA-Mk4"', f'(project "{NAME}"')          # 記号の番号はプロジェクトの名前ごとに持っている
        # UI の LED は回路図のまま 1608(2026-11-23、ユーザーの決定)。1.9mm おきの並び(pcb_shape.LEDS)に、長い方を x(前後)に向けて置く
        if fn == 'sensor.kicad_sch':
            assert t.count('"KOGUMA-Mk4:ENC_Base_Butt"') == 2      # main(タイヤ15mm)はエンコーダ基板 v2 を裏に突き当てる形(2026-11-02)
            t = t.replace('"KOGUMA-Mk4:ENC_Base_Butt"', '"KOGUMA-Mk4:ENC_Base_Edge_T24"')
            t = t.replace('を小さな基板(6.0 × 10.3mm、左右で同じ、hardware/kicad/KOGUMA-Mk4_Encoder)に載せる。\\nエンコーダの基板はメイン基板の裏に突き当て(2026-11-02、穴はなし)、裏のパッド(ENC_Base_Butt、エンコーダ基板の両側に7つずつ)と両面ではんだ付けする(線は使わない)。',
                          'を小さな基板(6.0 × 8.75mm、左右で同じ、hardware/kicad/KOGUMA-Mk4_Encoder_t24)に載せる。\\nエンコーダの基板はメイン基板の切り欠きの縁に沿って立て、上の面のパッド7つ(ENC_Base_Edge_T24)にはんだ付けする(線は使わない)。')
        open(d, 'w').write(t)
    # モーターの線のパッド J2・J3: 穴のパッド → 裏の面の SMD のパッド2つ(MotorWire_SMD_1x02_P3.2mm、2026-11-23)。
    # モーターの端子 (-12, ±1.5) から線を前へ出し、モーターとファンの囲いの間(裏 x -6.9〜-3.3)ではんだ付けする。上の面が空くので、MCU のグループを電池の下の真ん中に置ける
    write_motor_wire_fp()
    t = open(os.path.join(DST, 'motor.kicad_sch')).read()
    for ref in ('J2', 'J3'):
        i = t.index(f'(property "Reference" "{ref}"')
        j = t.index('"Connector_Wire:SolderWire-0.25sqmm_1x02_P4.2mm_D0.65mm_OD1.7mm"', i)
        t = t[:j] + '"KOGUMA-Mk4:MotorWire_SMD_1x02_P3.2mm"' + t[j + len('"Connector_Wire:SolderWire-0.25sqmm_1x02_P4.2mm_D0.65mm_OD1.7mm"'):]
    open(os.path.join(DST, 'motor.kicad_sch'), 'w').write(t)
    # 細かいピッチの IC(U4・U74・U75・U76)のパッドの間だけ 0.14mm まで許す設計ルール(main と同じ)
    shutil.copy(os.path.join(SRC, 'KOGUMA-Mk4.kicad_dru'), os.path.join(DST, NAME + '.kicad_dru'))
    open(os.path.join(DST, 'fp-lib-table'), 'w').write(
        '(fp_lib_table\n\t(version 7)\n\t(lib (name "KOGUMA-Mk4")(type "KiCad")(uri "${KIPRJMOD}/../KOGUMA-Mk4/KOGUMA-Mk4.pretty")(options "")(descr "MK4 project footprints"))\n)\n')
    open(os.path.join(DST, 'sym-lib-table'), 'w').write(
        '(sym_lib_table\n\t(version 7)\n\t(lib (name "KOGUMA-Mk4")(type "KiCad")(uri "${KIPRJMOD}/../KOGUMA-Mk4/KOGUMA-Mk4.kicad_sym")(options "")(descr "MK4 project symbols"))\n)\n')

def write_motor_wire_fp():
    """モーターの線をはんだ付けする SMD のパッド2つ(1.6 × 2.6mm、間 3.2mm)。裏の面に置く"""
    pads = ''.join(f"""
	(pad "{n}" smd roundrect (at {x} 0) (size 1.6 2.6) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.15))""" for n, x in (('1', -1.6), ('2', 1.6)))
    txt = f"""(footprint "MotorWire_SMD_1x02_P3.2mm"
	(version 20241229)
	(generator "make_main_t24.py")
	(layer "F.Cu")
	(descr "Two SMD pads 1.6x2.6mm, pitch 3.2mm, to solder motor wires (0.25sqmm) on the bottom of the KOGUMA-Mk4 t24 main board")
	(tags "wire pad SMD motor")
	(property "Reference" "REF**" (at 0 -2.2 0) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))
	(property "Value" "MotorWire_SMD_1x02_P3.2mm" (at 0 2.2 0) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))
	(attr smd exclude_from_pos_files exclude_from_bom)
	(fp_rect (start -2.65 -1.55) (end 2.65 1.55) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))
	(fp_rect (start -2.4 -1.3) (end 2.4 1.3) (stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab")){pads}
)
"""
    open(os.path.join(SRC, 'KOGUMA-Mk4.pretty', 'MotorWire_SMD_1x02_P3.2mm.kicad_mod'), 'w').write(txt)

# ---- 2. ネットリスト ----
def sexp(text):
    toks = re.findall(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()]+', text)
    stack = [[]]
    for t in toks:
        if t == '(':
            stack.append([])
        elif t == ')':
            x = stack.pop(); stack[-1].append(x)
        else:
            stack[-1].append(t[1:-1].replace('\\"', '"') if t.startswith('"') else t)
    return stack[0][0]

def find(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]

def netlist():
    out = os.path.join(DST, NAME + '.net')
    subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '-o', out, os.path.join(DST, NAME + '.kicad_sch')], check=True, capture_output=True)
    n = sexp(open(out).read()); os.remove(out)
    comps = []
    for c in find(find(n, 'components')[0], 'comp'):
        g = lambda k: find(c, k)[0][1] if find(c, k) else ''
        sp = find(c, 'sheetpath')[0]
        comps.append(dict(ref=g('ref'), value=g('value'), fp=g('footprint'), sheet=find(sp, 'names')[0][1],
                          path=find(sp, 'tstamps')[0][1] + find(c, 'tstamps')[0][1]))
    nets = {}
    for net in find(find(n, 'nets')[0], 'net'):
        name = find(net, 'name')[0][1]
        for node in find(net, 'node'):
            nets[(find(node, 'ref')[0][1], find(node, 'pin')[0][1])] = name
    return comps, nets

def load_fp(fpid):
    lib, name = fpid.split(':')
    path = os.path.join(ROOT, 'KOGUMA-Mk4', 'KOGUMA-Mk4.pretty') if lib == 'KOGUMA-Mk4' else os.path.join(STD, lib + '.pretty')
    fp = pcbnew.FootprintLoad(path, name)
    assert fp is not None, fpid
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp

# ---- 3. 外形 ----
def add_outline(b):
    for ring in _g['rings']:
            pts = [ring[0]]
            for q in ring[1:]:          # 0.01mm より近い点はまとめる(長さほぼ 0 の線があると、KiCad が外形を正しくないとする)
                if math.hypot(q[0] - pts[-1][0], q[1] - pts[-1][1]) >= 0.01:
                    pts.append(q)
            if math.hypot(pts[-1][0] - ring[0][0], pts[-1][1] - ring[0][1]) > 1e-9:
                pts[-1] = ring[0]
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(MM(0.05))
                s.SetStart(P(x0, y0)); s.SetEnd(P(x1, y1)); b.Add(s)

def note(b, txt, x, y, size=1.0):
    t = pcbnew.PCB_TEXT(b); t.SetText(txt); t.SetLayer(pcbnew.Cmts_User); t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size)))
    t.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y))); b.Add(t)

def build():
    ensure_project()
    comps, nets = netlist()
    b = pcbnew.CreateEmptyBoard()
    ds = b.GetDesignSettings()
    ds.m_MinClearance = MM(0.2); ds.m_TrackMinWidth = MM(0.15); ds.m_ViasMinSize = MM(0.6); ds.m_MinThroughDrill = MM(0.3)
    ds.m_CopperEdgeClearance = MM(0.2)      # エンコーダ基板と同じ(縁まで 0.2mm)。エンコーダのパッドは切り欠きの縁から 0.2mm
    ds.SetBoardThickness(MM(0.6))
    netinfo = {}
    for name in sorted(set(nets.values())):
        ni = pcbnew.NETINFO_ITEM(b, name); b.Add(ni); netinfo[name] = ni
    fps = {}
    no_fp = [c['ref'] + '(' + c['value'] + ')' for c in comps if ':' not in c['fp']]
    comps = [c for c in comps if ':' in c['fp']]      # フットプリントが決まっていない部品(main と同じ)は入れない
    for c in comps:
        fp = load_fp(c['fp'])
        fp.SetReference(c['ref']); fp.SetValue(c['value'])
        fp.SetAttributes(fp.GetAttributes() & ~pcbnew.FP_EXCLUDE_FROM_BOM)   # 回路図ではどれも部品表に入れる(ライブラリの設定を消す)
        fp.SetPath(pcbnew.KIID_PATH(c['path'])); fp.SetSheetname(c['sheet']); fp.SetSheetfile(c['sheet'].strip('/') + '.kicad_sch' if c['sheet'] != '/' else NAME + '.kicad_sch')
        b.Add(fp)
        for pad in fp.Pads():
            k = (c['ref'], pad.GetNumber())
            if k in nets:
                pad.SetNet(netinfo[nets[k]])
        fps[c['ref']] = fp
    add_outline(b)
    placed = set()
    # エンコーダのパッド: 左 J5 は縁 (0, +16.7) で回転 0、右 J6 は (0, -16.7) で 180°
    for ref, y, rot in (('J5', 16.7, 0.0), ('J6', -16.7, 180.0)):
        fps[ref].SetPosition(P(0.0, y)); fps[ref].SetOrientationDegrees(rot); placed.add(ref)
    # 壁センサのホルダ(裏)。ps.pads() と合う向きを探す
    for nm, (em, rc) in SENSORS.items():
        (sx, sy), ang = ps.SENS[nm]
        want = {'emit': sorted(ps.pads(nm, 'emit')), 'recv': sorted(ps.pads(nm, 'recv'))}
        for ref, part in ((em, 'emit'), (rc, 'recv')):
            fp = fps[ref]
            if not fp.IsFlipped():
                fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
            fp.SetPosition(P(sx, sy))
            best = None
            for cand in (ang, 180 - ang, -ang, ang + 180, 180 + ang, -180 - ang):
                fp.SetOrientationDegrees(cand)
                got = sorted((p.GetPosition().x / 1e6 - OX, OY - p.GetPosition().y / 1e6) for p in fp.Pads() if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH)
                if len(got) != len(want[part]):
                    continue
                err = max(math.hypot(a[0] - b_[0], a[1] - b_[1]) for a, b_ in zip(got, want[part]))
                if best is None or err < best[0]:
                    best = (err, cand)
            fp.SetOrientationDegrees(best[1]); placed.add(ref)
            print(f'  {ref} {nm} {part}: 向き {best[1]:.1f}°、足の穴のずれ {best[0]:.3f}mm')
            assert best[0] < 0.01, f'{ref} の足の穴が pcb_shape.pads() と合わない'
    # 電池の下(上の面): 高さ 1.2mm までの部品だけ置いてよい(2026-11-23)。電池は厚さ 1.5mm のスペーサーで浮かせる
    for (a, c_) in (((-16.25, -16.0), (6.25, -16.0)), ((6.25, -16.0), (6.25, 16.0)), ((6.25, 16.0), (-16.25, 16.0)), ((-16.25, 16.0), (-16.25, -16.0))):
        sh = pcbnew.PCB_SHAPE(b); sh.SetShape(pcbnew.SHAPE_T_SEGMENT); sh.SetLayer(pcbnew.Cmts_User); sh.SetWidth(MM(0.15))
        sh.SetStart(P(*a)); sh.SetEnd(P(*c_)); b.Add(sh)
    note(b, 'BATTERY (top): parts <= 1.2mm high only (battery on 1.5mm spacer)', OX - 15.5, OY - 13.5, 0.8)
    # UI の LED(1608。1.9mm おきなので長い方を x(前後)に向ける)と前の LED(D98、PB3)
    for ref, (x, y) in zip(UI_LEDS, ps.LEDS):
        fps[ref].SetPosition(P(x, y)); fps[ref].SetOrientationDegrees(0.0); placed.add(ref)
    fps['D98'].SetPosition(P(*ps.LED_FRONT)); fps['D98'].SetOrientationDegrees(0.0); placed.add('D98')
    # ねじの穴(基板だけの部品)
    for i, (x, y) in enumerate(ps.SCREWS):
        h = load_fp('MountingHole:MountingHole_2.2mm_M2'); h.SetReference(f'H{i + 1}'); h.SetValue('M2')
        h.SetAttributes(h.GetAttributes() | pcbnew.FP_BOARD_ONLY | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
        h.SetPosition(P(x, y)); b.Add(h)
    # ほかの部品: 基板の右に、シートごとに並べる
    x0 = OX + 60
    sheets = {}
    for c in comps:
        if c['ref'] not in placed:
            sheets.setdefault(c['sheet'], []).append(c['ref'])
    y = OY - 40
    for sh, refs in sorted(sheets.items()):
        note(b, f'{sh}(未配置)', x0, y - 3, 1.2)
        x = x0
        for ref in sorted(refs, key=lambda r: (re.sub(r'\d', '', r), int(re.sub(r'\D', '', r) or 0))):
            fp = fps[ref]
            fp.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
            bb = fp.GetBoundingBox(False)
            x += max(bb.GetWidth() / 1e6, 1.5) + 1.5
            if x > x0 + 70:
                x = x0; y += 6
        y += 10
    note(b, 'KOGUMA MK4 main board for tire 24mm (t24): outline t24v3 (mechanical/pcb/pcb_outline_t24v3.dxf), 0.6mm. '
            'Fixed by mechanics: J5/J6 encoder pads, D70-D77 wall sensor holders (bottom), D90-D96 UI LEDs (1608, order tentative), D98 front LED, H1-H4 M2 posts. Others: not placed yet', OX - 50, OY - 42, 1.0)
    note(b, 'No footprint in the schematic yet (not on this board): ' + ', '.join(no_fp), OX - 50, OY - 39, 1.0)
    path = os.path.join(DST, NAME + '.kicad_pcb')
    b.Save(path)
    print('フットプリントが決まっていない部品(入れていない):', ', '.join(no_fp))
    return path, len(comps)

if __name__ == '__main__':
    print(build())

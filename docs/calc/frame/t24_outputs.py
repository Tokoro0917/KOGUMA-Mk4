"""タイヤ24mm 用のフレーム(frame t24v10、2026-11-23)の製作用ファイルと図を、main のスクリプトで作る。
t24v10: t24v9 の形(吸引する面 80 × 42.6mm、骨 1.6mm、吸引する面の中に斜めの骨、窓の角の丸み 1.5mm、前の辺 2.5mm、
マウントのねじ (6.8, ±18.4)・(-21, ±18.4))で、**吸引する面の窓をカーボンで埋め、板を 0.8mm に**した(塩ビのシートはなくす。ユーザー)。
下の面は z 2.0 のまま、上の面が z 2.8(t24v9 までは 1mm、z 2.0〜3.0)。案は t24.py の w2lXf15se8。
t24v9 は 1mm + 塩ビ 0.2mm(w2lXf15se)、t24v8 は後ろのねじ (-21, ±17.7)、t24v7 はねじ (6.8, ±18.9)・(-21, ±18.9)、t24v6 は前の辺 1.6mm。
main のスクリプト(make_dxf.py・make_order.py・report.py・mechanical/frame_3d.py)を、t24.py を読み込んでから動かし、
塩ビのシートの所を外し、厚さを 0.8mm にする。
使い方(このディレクトリで): python3 t24_outputs.py
  → mechanical/frame/frame_t24v10.dxf・MK4FRAMET24V10_T08.dxf・frame_t24v10_3d.step、docs/img/frame/t24v10_drawing.png・t24v10_fields.png"""
import os, sys, json, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '../../..')
FRAME_DIR = os.path.join(ROOT, 'mechanical/frame')
IMG = os.path.join(ROOT, 'docs/img/frame')
sys.path.insert(0, HERE)
os.chdir(HERE)
import t24, design as dz
P = {k: v for k, v in json.load(open(os.path.join(HERE, 'results/t24_w2lXf15se8_params.json'))).items() if k != '_suction'}
t24.set_suction('w2')
TAG = 't24v10'


def run(path, argv, replace=(), cut=()):
    """path のスクリプトを、文字の置き換え(replace)と、start から end の手前までの削除(cut)をしてから動かす"""
    src = open(path).read()
    for a, b in replace:
        assert a in src, (path, a)
        src = src.replace(a, b)
    for start, end in cut:
        i = src.index(start)
        j = src.index(end, i)
        src = src[:i] + src[j:]
    sys.argv = argv
    exec(compile(src, path, 'exec'), {'__name__': '__main__', '__file__': path})


# 1. レイヤー別の DXF と寸法の図(塩ビのシートの層は書かない)
json.dump(P, open(f'results/{TAG}_params.json', 'w'))
run('make_dxf.py', ['make_dxf.py', f'results/{TAG}_params.json', f'frame_{TAG}', FRAME_DIR],
    [("add_poly(sheet, 'PC_SHEET', dy=-85)\n", ""),
     ("msp.add_text('PVC sheet 0.2mm (glue on TOP of carbon over suction area)', dxfattribs={'layer': 'TEXT', 'height': 2.0}).set_placement((-30, -105))\n", ""),
     ("carbon 1mm (gray){rib_s} + PVC 0.2mm sheet windows (blue)", "carbon 0.8mm (gray){rib_s}, suction area filled (no PVC sheet)")])
shutil.move(f'frame_{TAG}_drawing.png', os.path.join(IMG, f'{TAG}_drawing.png'))
if os.path.exists(f'frame_{TAG}_ribs.json'):
    os.remove(f'frame_{TAG}_ribs.json')
# 2. 注文用(カーボン 0.8mm だけ。塩ビのシートと型紙は作らない)
run('make_order.py', ['make_order.py', FRAME_DIR],
    [("VER = '69'", "VER = 'T24V10'"), ("json.load(open(os.path.join(HERE, 'results/final_params.json')))", f"json.load(open(os.path.join(HERE, 'results/{TAG}_params.json')))"),
     ("f'MK4FRAME{VER}_T1.dxf'", "f'MK4FRAME{VER}_T08.dxf'"),
     ("* 1.55e-3:.2f} g(1mm)", "* 1.55e-3 * 0.8:.2f} g(0.8mm)")],
    cut=[("# ポリカーボネート", "print('書き出し:'")])
# 3. 3D(板は z 2.0〜2.8、塩ビなし)
run(os.path.join(ROOT, 'mechanical/frame_3d.py'), ['frame_3d.py', FRAME_DIR],
    [("TAG = 'frame_v6_9'", f"TAG = 'frame_{TAG}'"), ("json.load(open(os.path.join(HERE, '../docs/calc/frame/results/final_params.json')))", f"json.load(open(os.path.join(HERE, '../docs/calc/frame/results/{TAG}_params.json')))"),
     ("parts['carbon'] = poly_solid(plate, 2.0, 3.0)", "parts['carbon'] = poly_solid(plate, 2.0, 2.8)"),
     ("parts['pc_sheet'] = poly_solid(sheet, 3.0, 3.2)     # 塩ビ 0.2mm\n", ""),
     ("print(f'カーボン {v * 1.55e-3:.2f} g、塩ビ {parts[\"pc_sheet\"].Volume() * 1.4e-3:.2f} g')", "print(f'カーボン {v * 1.55e-3:.2f} g')")])
for fn in os.listdir(FRAME_DIR):      # frame_3d.py の確認用の絵は使わない
    if fn.startswith(f'frame_{TAG}') and fn.endswith('.png'):
        os.remove(os.path.join(FRAME_DIR, fn))
# 4. FEM の図(たわみ・応力・振動・座屈)
import report as rp
_src = open('report.py').read()
_old = """    msp.add_lwpolyline(list(sheet.exterior.coords), close=True, dxfattribs={'layer': 'PC_SHEET'})
    for i in sheet.interiors:
        msp.add_lwpolyline(list(i.coords), close=True, dxfattribs={'layer': 'PC_SHEET'})
"""
assert _old in _src
_ns = {'__name__': 'report_t24'}
exec(compile(_src.replace(_old, ''), 'report.py', 'exec'), _ns)
_ns['report'](P, TAG)
shutil.move(f'{TAG}_fields.png', os.path.join(IMG, f'{TAG}_fields.png'))
for fn in (f'{TAG}_shape.png', f'{TAG}.dxf', f'{TAG}_result.json'):
    if os.path.exists(fn):
        os.remove(fn)
print('ok')

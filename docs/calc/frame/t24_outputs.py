"""タイヤ24mm 用のフレーム(frame t24v5、吸引する面 80 × 42.6mm、骨 1.6mm、吸引する面の中に斜めの骨、窓の角の丸み 1.5mm(案 w2lXf15)。t24v4 は丸み 2mm(w2lX)、t24v3 は 68 × 34mm で案 w16l)の製作用ファイルと図を、main のスクリプトで作る。
main のスクリプト(make_dxf.py・make_order.py・report.py・mechanical/frame_3d.py)を、t24.py を読み込んでから動かし、
シートは t24 の形(マウントが載る所を切ったもの、g['sheet'])に差し替える。
使い方(このディレクトリで): python3 t24_outputs.py
  → mechanical/frame/frame_t24v5.dxf・MK4FRAMET24V5_T1.dxf・MK4PCT24V5_T02.dxf・MK4PCT24V5_template_A4_1to1.pdf・frame_t24v5_3d.step、
    docs/img/frame/t24v5_drawing.png・t24v5_fields.png"""
import os, sys, json, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '../../..')
FRAME_DIR = os.path.join(ROOT, 'mechanical/frame')
IMG = os.path.join(ROOT, 'docs/img/frame')
sys.path.insert(0, HERE)
os.chdir(HERE)
import t24, design as dz
P = {k: v for k, v in json.load(open(os.path.join(HERE, 'results/t24_w2lXf15_params.json'))).items() if k != '_suction'}
t24.set_suction('w2')
SHEET = "g['sheet']"

def run(path, argv, replace=()):
    src = open(path).read()
    for a, b in replace:
        assert a in src, (path, a)
        src = src.replace(a, b)
    sys.argv = argv
    exec(compile(src, path, 'exec'), {'__name__': '__main__', '__file__': path})

# 1. レイヤー別の DXF と寸法の図
json.dump(P, open('results/t24v5_params.json', 'w'))
run('make_dxf.py', ['make_dxf.py', 'results/t24v5_params.json', 'frame_t24v5', FRAME_DIR],
    [("sheet = g['suction'].difference(Point(dz.FAN_X, 0).buffer(dz.FAN_R, 64))", f"sheet = {SHEET}")])
shutil.move('frame_t24v5_drawing.png', os.path.join(IMG, 't24v5_drawing.png'))
if os.path.exists('frame_t24v5_ribs.json'):
    os.remove('frame_t24v5_ribs.json')
# 2. 注文用(カーボンと塩ビのシート、型紙)
run('make_order.py', ['make_order.py', FRAME_DIR],
    [("VER = '69'", "VER = 'T24V5'"), ("json.load(open(os.path.join(HERE, 'results/final_params.json')))", "json.load(open(os.path.join(HERE, 'results/t24v5_params.json')))"),
     ("sheet = g['suction'].difference(Point(dz.FAN_X, 0).buffer(dz.FAN_R, 128))", f"sheet = {SHEET}"),
     ("(frame v{VER[0]}.{VER[1:]}, ", "(frame t24v5, ")])
# 3. 3D
run(os.path.join(ROOT, 'mechanical/frame_3d.py'), ['frame_3d.py', FRAME_DIR],
    [("TAG = 'frame_v6_9'", "TAG = 'frame_t24v5'"), ("json.load(open(os.path.join(HERE, '../docs/calc/frame/results/final_params.json')))", "json.load(open(os.path.join(HERE, '../docs/calc/frame/results/t24v5_params.json')))"),
     ("sheet = g['suction'].difference(Point(dz.FAN_X, 0).buffer(dz.FAN_R, 64))", f"sheet = {SHEET}")])
for fn in os.listdir(FRAME_DIR):      # frame_3d.py の確認用の絵は使わない
    if fn.startswith('frame_t24v5') and fn.endswith('.png'):
        os.remove(os.path.join(FRAME_DIR, fn))
# 4. FEM の図(たわみ・応力・振動・座屈)
import report as rp
rp.report(P, 't24v5')
shutil.move('t24v5_fields.png', os.path.join(IMG, 't24v5_fields.png'))
for fn in ('t24v5_shape.png', 't24v5.dxf', 't24v5_result.json'):
    if os.path.exists(fn):
        os.remove(fn)
print('ok')

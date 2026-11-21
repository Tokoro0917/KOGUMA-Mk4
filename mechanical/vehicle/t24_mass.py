"""タイヤ24mm の機体(t24、2026-11-21、ブランチ claude/trusting-dirac-1tdt54)の質量・重心・慣性モーメント。
先に docs/calc/frame/t24.py(フレーム・ねじ・ファンの台の継ぎ目)と pcb_t24.py(基板の外形)を読み込んでから、
main の機体(vehicle.py v4、56.06g)の作り方で機体を作り(FAST=1)、足回り・モーターマウント・電池のホルダをタイヤ24mm のものに入れ替えて計算する。
入れ替えた部品とほかのすべての部品のすき間も調べる。
  入れ替えるもの: マウント(t24v2)、電池のホルダ(t24v1)、ホイール(t24v1)、タイヤ(24 × 8.5mm、ゴム)、71T(POM、厚さ2mm、穴φ8)、
                  走行用モーター・軸・ピニオン(新しい位置)、平行ピン・軸受・磁石(main から (0, ±3.5, +4.5))、エンコーダ基板(6.0 × 9.2mm)・MT6835
  vehicle.py が t24 の値で作るもの: フレーム(frame t24v1)、基板(t24v1)、ねじ(新しい位置)、ファンの台(継ぎ目 (14, ±20.3))
  そのまま: 電池、ファン、壁センサ、配線、滑り板・スカート・シート
使い方(リポジトリの一番上で): python3 mechanical/vehicle/t24_mass.py → mechanical/vehicle/vehicle_t24_mass.json、mk4_vehicle_t24.step"""
import os, sys, json
import numpy as np
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
SCRATCH = os.environ.get('T24_TMP', '/tmp')

# ---- 先にタイヤ24mm の設定を読む: design.py(フレームの切り欠き・ねじ・ファンの台の継ぎ目)と pcb_shape.py(基板の外形)----
sys.path.insert(0, os.path.join(HERE, '../motor_mount')); sys.path.insert(0, os.path.join(HERE, '../wheel'))
sys.path.insert(0, os.path.join(HERE, '../battery_holder')); sys.path.insert(0, os.path.join(HERE, '../../docs/calc/frame'))
sys.path.insert(0, HERE)
import t24 as ft            # design.py の定数と build を t24 に
import pcb_t24              # pcb_shape.outline を t24v1 に
dz = ft.dz
# ---- 機体(vehicle.py v4 の作り方)を作る。FAST=1 だと質量を出したところで sys.exit するので、exec して変数を取り出す ----
os.environ['FAST'] = '1'
sys.argv = [os.path.join(HERE, 'vehicle.py'), SCRATCH, 'v4']
cwd = os.getcwd(); os.chdir(HERE); sys.path.insert(0, HERE)
V = {'__name__': '__main__', '__file__': os.path.join(HERE, 'vehicle.py')}
try:
    exec(compile(open(os.path.join(HERE, 'vehicle.py')).read(), V['__file__'], 'exec'), V)
except SystemExit:
    pass
os.chdir(cwd)
rows_v, M_v, CG_v, Iz_v = V['rows'], V['M'], V['CG'], V['Izz']
M_main, CG_main, Iz_main = 56.06, np.array([0.68, 0.0, 12.71]), 265.0     # main(vehicle.py v4、2026-11-01)の値
props, RHO, FIXED, ycyl, mirror = V['props'], V['RHO'], V['FIXED'], V['ycyl'], V['mirror']
poly_solid, Z_FB, Z_FT = V['poly_solid'], V['Z_FB'], V['Z_FT']
assert V['dz'] is dz and V['dz'].MOUNT_SCREWS == [(-21.0, 19.5), (8.0, 19.5)]

# ---- 入れ替えるタイヤ24mm の部品(vehicle.py は main の足回り・マウント・電池のホルダを作るので、それを入れ替える)----
import mount as mm, mount_t24 as mt, wheel_t24 as wt, battery_holder as bh, battery_holder_t24 as bht

P = mt.P
ax, az = P['axle']; mx, mz = mm.motor_center(P)
right = {}
right['mount'] = (mm.build(P).val(), 'resin')
right['wheel'] = (wt.build().val(), 'resin')
right['tire'] = (ycyl(12.0, -33.3, -24.8, ax, az).cut(ycyl(10.0, -33.4, -24.7, ax, az)).val(), 'rubber')
right['spur71'] = (ycyl(10.65, -24.8, -22.8, ax, az).cut(ycyl(4.0, -24.9, -22.7, ax, az)).val(), 'pom')   # 歯の分を平均して半径 10.65(ピッチ円 10.65)
right['motor'] = (ycyl(4.3, P['motor_face'], P['motor_face'] + 20.0, mx, mz).union(ycyl(1.2, P['motor_face'] - 0.3, P['motor_face'], mx, mz)).val(), 'motor')
right['shaft'] = (ycyl(0.6, P['motor_face'] - 0.3, -24.4, mx, mz).val(), 'steel')
right['pinion'] = (ycyl(2.25, -22.4, -24.4, mx, mz).cut(ycyl(0.6, -22.3, -24.5, mx, mz)).val(), 'brass')
right['enc_board'] = (cq.Solid.makeBox(6.0, 0.6, 9.2, cq.Vector(-3.0, -17.5, 8.3)), 'fr4')
right['mt6835'] = (cq.Solid.makeBox(4.4, 1.2, 5.0, cq.Vector(-2.2, -18.7, 9.5)), 'resin')
for r in rows_v:      # 平行ピン・軸受・磁石は main のものを動かす
    for k in ('pin', 'brg_out', 'brg_in', 'magnet'):
        if r['name'] == k + '_R':
            right[k] = (V['parts'][r['name']][0].translate(cq.Vector(0, 3.5, 4.5)), V['parts'][r['name']][1])
assert json.load(open(os.path.join(HERE, '../../docs/calc/frame/results/final_params.json'))) == json.load(open(os.path.join(HERE, '../../docs/calc/frame/results/t24_a_params.json'))), 'フレームのパラメータが t24 a と違う'
new_parts = {}
for k, (s, m) in right.items():
    new_parts[k + '_R'] = (s, m); new_parts[k + '_L'] = (mirror(s), m)
for sy, nm in ((1, 'L'), (-1, 'R')):
    new_parts[f'battery_holder_{nm}'] = (bh.holder(sy, bht.P, z0=V['Z_PCBT']).val(), 'resin')

DROP = ('mount_', 'wheel_', 'tire_', 'spur41_', 'motor_', 'shaft_', 'pinion_', 'enc_board_', 'as5047p_', 'pin_', 'brg_', 'magnet_', 'battery_holder_')
rows = [dict(r) for r in rows_v if not any(r['name'].startswith(k) for k in DROP)]
for name, (shape, mat) in new_parts.items():
    v, c, I = props(shape)
    if mat in FIXED:
        m = FIXED[mat]; rho = m / v
    else:
        rho = RHO[mat]; m = v * rho
    rows.append(dict(name=name, mat=mat, vol=v, m=m, c=c, I=I * rho, new=True))
M = sum(r['m'] for r in rows)
CG = sum(r['m'] * r['c'] for r in rows) / M
Izz = sum(r['I'][2, 2] + r['m'] * ((r['c'][0] - CG[0])**2 + (r['c'][1] - CG[1])**2) for r in rows) / 100
GROUP = [('フレーム・シート・スカート・滑り板', ('frame', 'pc_sheet', 'skirt', 'skid')),
         ('モーターマウント × 2', ('mount_',)), ('走行用モーター × 2', ('motor_',)),
         ('車輪・タイヤ・71T・ピニオン・軸・軸受・磁石・エンコーダ', ('wheel', 'tire', 'spur71', 'pinion', 'pin_', 'shaft_', 'brg_', 'magnet', 'enc_board', 'mt6835')),
         ('吸引ファン', ('fan_', 'impeller')), ('基板 + 部品', ('pcb',)), ('電池 + ホルダ', ('battery',)),
         ('壁センサ × 4', ('sensor_',)), ('ねじ・ナット', ('screw_', 'nut_')), ('配線', ('wiring',))]
def group(rows, CG, name_map=None):
    out = []
    for gname, keys in GROUP:
        keys2 = tuple(k.replace('spur71', 'spur41').replace('mt6835', 'as5047p') for k in keys) if name_map else keys
        sel = [r for r in rows if any(r['name'].startswith(k) for k in keys2)]
        out.append(dict(group=gname, m=round(sum(r['m'] for r in sel), 2),
                        iz=round(sum(r['I'][2, 2] + r['m'] * ((r['c'][0] - CG[0])**2 + (r['c'][1] - CG[1])**2) for r in sel) / 100, 1)))
    return out
gt = group(rows, CG)
print(f'main(v4): {M_main:.2f} g、重心 ({CG_main[0]:.2f}, {CG_main[1]:.2f}, {CG_main[2]:.2f}) mm、慣性モーメント {Iz_main:.0f} g·cm²')
print(f't24     : {M:.2f} g、重心 ({CG[0]:.2f}, {CG[1]:.2f}, {CG[2]:.2f}) mm、慣性モーメント {Izz:.0f} g·cm²')
for b in gt:
    print(f"  {b['group']:28s} {b['m']:6.2f} g   {b['iz']:6.1f} g·cm²")
parts_new = {r['name']: round(r['m'], 3) for r in rows if r.get('new')}
print('入れ替えた部品', parts_new)

# ---- ぶつかり: 入れ替えた部品と、ほかのすべての部品のすき間 ----
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
shapes = {k: v[0] for k, v in V['parts'].items() if not any(k.startswith(d) for d in DROP)}
shapes.update({k: v[0] for k, v in new_parts.items()})
IGN = {frozenset(p) for p in [('pinion_R', 'spur71_R'), ('pinion_L', 'spur71_L')]}
for sd in 'RL':     # 組み合わせて使う所(圧入・はめ合い・接着・載せる)
    for a, b in (('pin', 'wheel'), ('pin', 'brg_out'), ('pin', 'brg_in'), ('magnet', 'brg_in'), ('magnet', 'pin'), ('brg_out', 'spur71'), ('spur71', 'wheel'),
                 ('tire', 'wheel'), ('shaft', 'pinion'), ('motor', 'shaft'), ('enc_board', 'mt6835'), ('brg_in', 'brg_out'), ('pin', 'spur71'), ('wheel', 'brg_out')):
        IGN.add(frozenset((f'{a}_{sd}', f'{b}_{sd}')))
def dist(a, b):
    d = BRepExtrema_DistShapeShape(a.wrapped, b.wrapped); d.Perform(); return d.Value()
rows_c = []
names = list(shapes)
for i, a in enumerate(names):
    for b in names[i + 1:]:
        if not (a in new_parts or b in new_parts) or frozenset((a, b)) in IGN:
            continue
        ba, bb_ = shapes[a].BoundingBox(), shapes[b].BoundingBox()
        if ba.xmin > bb_.xmax + 1 or bb_.xmin > ba.xmax + 1 or ba.ymin > bb_.ymax + 1 or bb_.ymin > ba.ymax + 1 or ba.zmin > bb_.zmax + 1 or bb_.zmin > ba.zmax + 1:
            continue
        d = dist(shapes[a], shapes[b])
        if d < 0.5:
            ov = shapes[a].intersect(shapes[b]).Volume() if d < 1e-6 else 0.0
            rows_c.append((a, b, round(d, 3), round(ov, 3)))
rows_c.sort(key=lambda r: (r[2], -r[3]))
print('すき間 0.5mm 未満(入れ替えた部品とほか):')
for a, b, d, ov in rows_c:
    pair = {a.rsplit('_', 1)[0], b.rsplit('_', 1)[0]}
    if ov > 1e-3 and 'mount' in pair and any(x.startswith('screw') for x in pair):
        kind = '  ねじ山(下穴 φ1.6 に M2 をねじ込む分)'
    elif ov > 1e-3 and pair in ({'mount', 'motor'}, {'mount', 'brg_out'}, {'mount', 'brg_in'}):
        kind = '  しまりばめ(当たり面)'
    else:
        kind = '  ぶつかる' if ov > 1e-3 else ('  接している' if d < 1e-6 else '')
    print(f'  {a:18s} - {b:18s} すき間 {d:6.3f} mm  重なり {ov:7.3f} mm³' + kind)
json.dump(dict(main=dict(mass=M_main, cg=list(CG_main), iz=Iz_main),
               t24=dict(mass=round(M, 2), cg=[round(c, 2) for c in CG], iz=round(Izz, 1), groups=gt, new_parts=parts_new),
               clearances=[dict(a=a, b=b, gap=d, overlap=ov) for a, b, d, ov in rows_c]),
          open(os.path.join(HERE, 'vehicle_t24_mass.json'), 'w'), ensure_ascii=False, indent=1, default=float)
cq.exporters.export(cq.Compound.makeCompound(list(shapes.values())), os.path.join(HERE, 'mk4_vehicle_t24.step'))

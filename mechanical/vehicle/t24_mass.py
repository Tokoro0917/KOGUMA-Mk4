"""タイヤ24mm の機体(t24、2026-11-21、ブランチ claude/trusting-dirac-1tdt54)の質量・重心・慣性モーメント。
main の機体(vehicle.py v4、56.06g)を FAST=1 で作って部品ごとの質量と重心を取り出し、
足回り・モーターマウント・フレームをタイヤ24mm のものに入れ替え、マウントのねじを新しい位置へ動かして計算する。
  入れ替えるもの: フレーム(frame t24v1)、マウント(t24v2)、ホイール(t24v1)、タイヤ(24 × 8.5mm、ゴム)、71T(POM、厚さ2mm、穴φ8)、
                  走行用モーター・軸・ピニオン(新しい位置)、平行ピン・軸受・磁石(main から (0, ±3.5, +4.5))、エンコーダ基板(6.0 × 9.2mm)・MT6835
  ねじ・ナット: マウントのねじの所にあるものは、新しい位置 (8, ±19.5)・(-21, ±19.5) へ平行に動かす(形と材料はそのまま)
  そのまま: 基板(t24 の切り欠きは入れていない)、電池とホルダ、ファン、壁センサ、配線、滑り板・スカート・シート
使い方(リポジトリの一番上で): python3 mechanical/vehicle/t24_mass.py → mechanical/vehicle/vehicle_t24_mass.json"""
import os, sys, json
import numpy as np
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
SCRATCH = os.environ.get('T24_TMP', '/tmp')

# ---- main の機体(v4)を作る。FAST=1 だと質量を出したところで sys.exit するので、exec して変数を取り出す ----
os.environ['FAST'] = '1'
sys.argv = [os.path.join(HERE, 'vehicle.py'), SCRATCH, 'v4']
cwd = os.getcwd(); os.chdir(HERE); sys.path.insert(0, HERE)
V = {'__name__': '__main__', '__file__': os.path.join(HERE, 'vehicle.py')}
try:
    exec(compile(open(os.path.join(HERE, 'vehicle.py')).read(), V['__file__'], 'exec'), V)
except SystemExit:
    pass
os.chdir(cwd)
rows_main, M_main, CG_main, Iz_main = V['rows'], V['M'], V['CG'], V['Izz']
props, RHO, FIXED, ycyl, mirror = V['props'], V['RHO'], V['FIXED'], V['ycyl'], V['mirror']
poly_solid, Z_FB, Z_FT = V['poly_solid'], V['Z_FB'], V['Z_FT']
OLD_SCREWS = [(x, sy * y) for (x, y) in V['dz'].MOUNT_SCREWS for sy in (1, -1)]

# ---- タイヤ24mm の部品 ----
sys.path.insert(0, os.path.join(HERE, '../motor_mount')); sys.path.insert(0, os.path.join(HERE, '../wheel'))
sys.path.insert(0, os.path.join(HERE, '../../docs/calc/frame'))
import mount as mm, mount_t24 as mt, wheel_t24 as wt
import t24 as ft          # design.py の定数をタイヤ24mm に変える(V['dz'] と同じモジュールなので、ここから先の dz は t24)
dz = ft.dz
NEW_SCREWS = [(x, sy * y) for (x, y) in dz.MOUNT_SCREWS for sy in (1, -1)]

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
for r in rows_main:      # 平行ピン・軸受・磁石は main のものを動かす
    for k in ('pin', 'brg_out', 'brg_in', 'magnet'):
        if r['name'] == k + '_R':
            right[k] = (V['parts'][r['name']][0].translate(cq.Vector(0, 3.5, 4.5)), V['parts'][r['name']][1])
g = dz.build(**json.load(open(os.path.join(HERE, '../../docs/calc/frame/results/t24_a_params.json'))))
from shapely.geometry import Point
from shapely.ops import unary_union
plate = g['carbon'].difference(unary_union([Point(c).buffer(dz.HOLE_D / 2, 32) for c in dz.holes()]))
new_parts = {'frame': (poly_solid(plate, Z_FB, Z_FT), 'carbon')}
for k, (s, m) in right.items():
    new_parts[k + '_R'] = (s, m); new_parts[k + '_L'] = (mirror(s), m)

DROP = ('frame', 'mount_', 'wheel_', 'tire_', 'spur41_', 'motor_', 'shaft_', 'pinion_', 'enc_board_', 'as5047p_', 'pin_', 'brg_', 'magnet_')
rows = []
for r in rows_main:
    if r['name'] == 'frame' or any(r['name'].startswith(k) for k in DROP[1:]):
        continue
    r = dict(r)
    if r['name'].startswith(('screw_', 'nut_')):      # マウントのねじの所にあるものを動かす
        for (ox, oy), (nx, ny) in zip(OLD_SCREWS, NEW_SCREWS):
            if abs(r['c'][0] - ox) < 0.5 and abs(r['c'][1] - oy) < 0.5:
                r['c'] = r['c'] + np.array([nx - ox, ny - oy, 0.0]); r['moved'] = True
    rows.append(r)
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
gm, gt = group(rows_main, CG_main, True), group(rows, CG)
print(f'main(v4): {M_main:.2f} g、重心 ({CG_main[0]:.2f}, {CG_main[1]:.2f}, {CG_main[2]:.2f}) mm、慣性モーメント {Iz_main:.0f} g·cm²')
print(f't24     : {M:.2f} g、重心 ({CG[0]:.2f}, {CG[1]:.2f}, {CG[2]:.2f}) mm、慣性モーメント {Izz:.0f} g·cm²')
for a, b in zip(gm, gt):
    print(f"  {b['group']:28s} {a['m']:6.2f} → {b['m']:6.2f} g   {a['iz']:6.1f} → {b['iz']:6.1f} g·cm²")
parts_new = {r['name']: round(r['m'], 3) for r in rows if r.get('new')}
print('入れ替えた部品', parts_new)
print('動かしたねじ・ナット', [r['name'] for r in rows if r.get('moved')])
json.dump(dict(main=dict(mass=round(M_main, 2), cg=[round(c, 2) for c in CG_main], iz=round(Iz_main, 1), groups=gm),
               t24=dict(mass=round(M, 2), cg=[round(c, 2) for c in CG], iz=round(Izz, 1), groups=gt, new_parts=parts_new)),
          open(os.path.join(HERE, 'vehicle_t24_mass.json'), 'w'), ensure_ascii=False, indent=1, default=float)

"""タイヤ24mm のマウント(mount_t24.py)のまわりの部品を並べ、ぶつかり(重なる体積)とすき間を確かめる。右側だけ。
軸受・平行ピン・磁石は tn_drive_mk4_right.step(ToraNeko.Mk3)のものを main の位置から (0, +3.5, +4.5) 動かして使う。
ホイール・タイヤ・71T・MT6835・エンコーダ基板・メイン基板・フレーム・シート・ファンの囲いは、寸法から作った簡単な形。
フレームとメイン基板は、タイヤ24mm の形がまだないので、外形を四角にして切り欠きと穴だけ開けた仮の形。
使い方: python3 check_t24.py → 一覧を表示し、check_t24_result.txt と mk4_drive_R_t24_check.step を書き出す"""
import math, sys
import cadquery as cq
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
import mount as mm
import mount_t24 as mt
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../wheel'))
import wheel_t24 as wt

P = mt.P
ax, az = P['axle']
mx, mz = mm.motor_center(P)
ycyl, box = mm.ycyl, mm.box
def zcyl(r, z0, z1, x, y): return cq.Workplane().center(x, y).circle(r).extrude(z1 - z0).translate((0, 0, z0))

parts = {}
parts['mount'] = mm.build(P).val()
DY, DZ = 3.5, 4.5
for s in cq.importers.importStep('tn_drive_mk4_right.step').val().Solids():
    bb = s.BoundingBox()
    if abs(bb.ymax + 23.7) < 0.05 and abs(bb.ymin + 29.7) < 0.05: nm = 'pin'
    elif abs(bb.ymin + 23.7) < 0.05 and abs(bb.ymax + 22.7) < 0.05: nm = 'magnet'
    elif abs((bb.xmax - bb.xmin) - 7.2) < 0.05: nm = 'brg_out' if bb.ymin < -26 else 'brg_in'
    else: continue
    parts[nm] = s.translate(cq.Vector(0, DY, DZ))
parts['tire'] = ycyl(12.0, -33.3, -24.8, ax, az).cut(ycyl(10.0, -33.4, -24.7, ax, az)).val()
parts['wheel'] = wt.build().val()                                 # mechanical/wheel/wheel_t24.py
parts['spur71'] = ycyl(10.95, -24.8, -22.8, ax, az).cut(ycyl(4.0, -24.9, -22.7, ax, az)).val()   # 中の穴 φ8(外の軸受のつばが入る)
parts['MT6835'] = box(-2.5, 2.5, -18.7, -17.5, 8.8, 15.2).val()      # TSSOP-16、足まで
parts['enc_board'] = box(-3.0, 3.0, -17.5, -16.9, 8.15, 16.9).val()   # hardware/kicad/KOGUMA-Mk4_Encoder_t24(6.0 × 8.75mm)
parts['motor'] = ycyl(4.3, P['motor_face'], P['motor_face'] + 20.0, mx, mz).val()
parts['motor_boss'] = ycyl(1.2, P['motor_face'] - 0.3, P['motor_face'], mx, mz).val()
parts['shaft'] = ycyl(0.6, P['motor_face'] - 0.3, -24.4, mx, mz).val()
parts['pinion13'] = ycyl(2.25, -22.4, -24.4, mx, mz).cut(ycyl(0.6, -22.3, -24.5, mx, mz)).val()
screws = [P['screw_front'], P['screw_rear']]
pcb = box(-30, 45, -34.6, 0, 13.6, 14.2).cut(box(-4.5, 4.5, -40, -16.7, 13, 15)).cut(box(-12.5, 12.5, -40, -22.3, 13, 15))
frame = box(-50, 50, -35, 0, 2.0, 3.0).cut(box(-9.5, 9.5, -40, -22.3, 1, 4))
for sx, sy in screws:
    pcb = pcb.cut(zcyl(1.1, 13, 15, sx, sy)); frame = frame.cut(zcyl(1.1, 1, 4, sx, sy))
parts['pcb'] = pcb.val()
parts['frame'] = frame.val()
parts['sheet'] = box(-30, 30, -15, 0, 3.0, 3.2).val()
parts['fan_ring'] = zcyl(17.5, 3.2, 10.0, 14.2, 0).cut(zcyl(16.5, 3.1, 10.1, 14.2, 0)).val()
parts['battery'] = box(-16.25, 6.25, -16.0, 0, 14.2, 20.0).val()
for nm, (sx, sy) in (('front', P['screw_front']), ('rear', P['screw_rear'])):
    parts[f'screw_{nm}'] = cq.Compound.makeCompound([zcyl(1.9, 0.9, 2.0, sx, sy).val(), zcyl(P['hole_d'] / 2, 2.0, 7.0, sx, sy).val()])

if __name__ == '__main__':
    def dist(a, b):
        d = BRepExtrema_DistShapeShape(a.wrapped, b.wrapped); d.Perform(); return d.Value()
    def overlap(a, b):
        try: return a.intersect(b).Volume()
        except Exception: return -1
    ignore = {('pinion13', 'spur71'), ('pin', 'wheel'), ('pin', 'brg_out'), ('pin', 'brg_in'), ('magnet', 'brg_in'), ('magnet', 'pin'),
              ('brg_out', 'spur71'), ('spur71', 'wheel'), ('tire', 'wheel'), ('shaft', 'pinion13'), ('motor', 'motor_boss'),
              ('motor_boss', 'shaft'), ('enc_board', 'MT6835'), ('brg_in', 'brg_out'), ('screw_front', 'frame'), ('screw_rear', 'frame'),
              ('frame', 'sheet'), ('battery', 'pcb'), ('pin', 'spur71')}
    focus = ('wheel', 'mount', 'motor', 'shaft', 'pinion13', 'motor_boss', 'enc_board', 'MT6835', 'screw_front', 'screw_rear', 'pcb')
    names = list(parts); rows = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if (a, b) in ignore or (b, a) in ignore or not (a in focus or b in focus):
                continue
            d = dist(parts[a], parts[b])
            if d < 1.5:
                rows.append((a, b, d, overlap(parts[a], parts[b]) if d < 1e-6 else 0.0))
    out = [f'マウント {mt.VER}: 体積 {parts["mount"].Volume():.0f} mm³({parts["mount"].Volume()*1.2e-3:.2f} g)、モーターの中心 ({mx:.2f}, {mz:.2f})']
    for a, b, d, ov in sorted(rows, key=lambda r: r[2]):
        flag = 'ぶつかる' if ov > 1e-3 else ('接している' if d < 1e-6 else '')
        out.append(f'{a:12s} - {b:12s} すき間 {d:6.3f} mm  重なり {ov:7.3f} mm³ {flag}')
    print('\n'.join(out))
    open('check_t24_result.txt', 'w').write('\n'.join(out) + '\n')
    cq.exporters.export(cq.Compound.makeCompound(list(parts.values())), 'mk4_drive_R_t24_check.step')

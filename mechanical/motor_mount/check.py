"""マウント v1 のまわりの部品を並べ、ぶつかり(重なる体積)とすき間を確かめる。右側だけ
使い方: python3 check.py [モーターの軸を切る位置 y(既定 -27.9)]
足回りの部品は tn_drive_mk4_right.step(ToraNeko.Mk3 の STEP から tn_parts.py で取り出したもの)"""
import math, json, sys
import cadquery as cq
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../docs/calc/frame'))
import mount as mm
import design as fd      # フレームの形(docs/calc/frame/design.py)

P = mm.P
assert [(P['screw_rear'][0], -P['screw_rear'][1]), (P['screw_front'][0], -P['screw_front'][1])] == fd.MOUNT_SCREWS, 'マウントとフレームのねじの位置が違う'
mx, mz = mm.motor_center(P)
def ycyl(r, y0, y1, x, z): return mm.ycyl(r, y0, y1, x, z)

parts = {}
parts['mount'] = mm.build(P).val()
tn = cq.importers.importStep('tn_drive_mk4_right.step').val().Solids()
for s in tn:
    bb = s.BoundingBox()
    if abs(bb.zmax - 14.5) < 0.05:          # ToraNeko のタイヤ(φ14)は使わない
        continue
    if bb.ymin > -21.1 and bb.ymax < -20.4:   # エンコーダ基板(フレームの上面 3.0 に合わせて 0.11 上げる)
        s = s.translate(cq.Vector(0, 0, 0.11)); parts['enc_board'] = s; continue
    if bb.ymin > -22.3 and bb.ymax < -20.9:
        s = s.translate(cq.Vector(0, 0, 0.11)); parts['AS5047P'] = s; continue
    if abs(bb.zmax - 13.25) < 0.05: parts['wheel'] = s; continue
    if abs(bb.zmax - 13.95) < 0.05: parts['spur41'] = s; continue
    if abs(bb.ymax + 23.7) < 0.05 and abs(bb.ymin + 29.7) < 0.05: parts['pin'] = s; continue
    if abs(bb.ymin + 23.7) < 0.05: parts['magnet'] = s; continue
    if abs((bb.xmax - bb.xmin) - 7.2) < 0.05:
        parts['brg_out' if bb.ymin < -26 else 'brg_in'] = s; continue
parts['tire15'] = ycyl(7.5, -31.8, -28.3, 0, 7.5).cut(ycyl(5.75, -31.9, -28.2, 0, 7.5)).val()
parts['motor'] = ycyl(4.3, P['motor_face'], P['motor_face'] + 20.0, mx, mz).val()
parts['motor_boss'] = ycyl(1.2, P['motor_face'] - 0.3, P['motor_face'], mx, mz).val()
cut_to = float(sys.argv[1]) if len(sys.argv) > 1 else -27.9
parts['shaft'] = ycyl(0.6, P['motor_face'] - 0.3, cut_to, mx, mz).val()
parts['pinion13'] = ycyl(2.25, -25.9, -27.9, mx, mz).cut(ycyl(0.6, -25.8, -28.0, mx, mz)).val()
# フレーム(タイヤの穴を y 25.8〜32.3、x ±6.5 にした形)
FP = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../docs/calc/frame/results/final_params.json')))
g = fd.build(**FP)
from shapely.geometry import box as sbox
car = g['carbon'].intersection(sbox(-60, -40, 60, -10))      # 右側だけ
def poly_solid(poly, z0, z1):
    wp = cq.Workplane().polyline(list(poly.exterior.coords)[:-1]).close().extrude(z1 - z0)
    for r in poly.interiors:
        wp = wp.cut(cq.Workplane().polyline(list(r.coords)[:-1]).close().extrude(z1 - z0))
    return wp.translate((0, 0, z0)).val()
geoms = getattr(car, 'geoms', [car])
parts['frame'] = cq.Compound.makeCompound([poly_solid(p, 2.0, 3.0) for p in geoms if p.area > 1])
sheet = g['suction'].difference(__import__('shapely').geometry.Point(fd.FAN_X, 0).buffer(fd.FAN_R, 48)).intersection(sbox(-60, -40, 60, 0))
parts['pc_sheet'] = poly_solid(sheet, 3.0, 3.2)
parts['fan_ring(φ35 h6.8)'] = cq.Workplane().center(fd.FAN_X, 0).circle(17.5).extrude(6.8).translate((0, 0, 3.2)).val()   # ファンを囲う輪の外側(羽根 φ32、囲いの内径 φ33、壁1.0。2026-10-20)
for (l, h, w) in g['vribs']:
    (x0, y0), (x1, y1) = l.coords[0], l.coords[-1]
    if y0 > 0: continue
    L = l.length; ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
    rib = cq.Workplane().box(L, 1.0, h, centered=(False, True, False)).rotate((0, 0, 0), (0, 0, 1), ang).translate((x0, y0, 3.0)).val()
    parts[f'rib_{"front" if x0 > 0 else "rear"}'] = rib
for nm, (sx, sy) in (('front', P['screw_front']), ('rear', P['screw_rear'])):
    # M2 の低頭 L5(頭 φ3.8 × 1.1)とナット(二面幅4.0 × 1.6)
    head = cq.Workplane().center(sx, sy).circle(1.9).extrude(1.1).translate((0, 0, 0.9)).val()
    shank = cq.Workplane().center(sx, sy).circle(P['hole_d'] / 2 if P.get('tap') else 1.0).extrude(5.0).translate((0, 0, 2.0)).val()   # タップのときは下穴の径(ねじ山がかみ合う分は重なりにしない)
    nut = (cq.Workplane().center(sx, sy).polygon(6, 4.0 / math.cos(math.pi / 6)).extrude(1.6)
           .cut(cq.Workplane().center(sx, sy).circle(1.0).extrude(1.6)).translate((0, 0, P['ear_top'] - P['nut_depth'] + 0.05)).val())
    parts[f'screw_{nm}'] = cq.Compound.makeCompound([head, shank])
    if not P.get('tap'):
        parts[f'nut_{nm}'] = nut

def dist(a, b):
    d = BRepExtrema_DistShapeShape(a.wrapped, b.wrapped); d.Perform()
    return d.Value()
def overlap(a, b):
    try:
        return a.intersect(b).Volume()
    except Exception:
        return -1
ignore = {('pinion13', 'spur41'), ('pin', 'wheel'), ('pin', 'brg_out'), ('pin', 'brg_in'), ('magnet', 'brg_in'),
          ('brg_out', 'spur41'), ('spur41', 'wheel'), ('tire15', 'wheel'), ('shaft', 'pinion13'), ('motor', 'motor_boss'),
          ('motor_boss', 'shaft'), ('enc_board', 'AS5047P'), ('nut_front', 'screw_front'), ('nut_rear', 'screw_rear'),
          ('magnet', 'pin'), ('brg_in', 'brg_out')}
names = list(parts)
rows = []
for i, a in enumerate(names):
    for b in names[i + 1:]:
        if (a, b) in ignore or (b, a) in ignore:
            continue
        if 'screw' in a + b and 'frame' in (a, b):
            continue   # フレームの M3 の穴はこの確認の模型には開けていない
        if not ('mount' in (a, b) or 'motor' in (a, b) or 'shaft' in (a, b) or 'pinion13' in (a, b) or 'motor_boss' in (a, b)
                or 'enc_board' in (a, b) or 'AS5047P' in (a, b) or 'screw' in a + b or 'nut' in a + b):
            continue
        d = dist(parts[a], parts[b])
        if d < 1.5:
            ov = overlap(parts[a], parts[b]) if d < 1e-6 else 0.0
            rows.append((a, b, d, ov))
for a, b, d, ov in sorted(rows, key=lambda r: r[2]):
    flag = 'ぶつかる' if ov > 1e-3 else ('接している' if d < 1e-6 else '')
    print(f'{a:16s} - {b:16s} すき間 {d:6.3f} mm  重なり {ov:7.3f} mm³ {flag}')
import os
os.makedirs('parts', exist_ok=True)
for k, s in parts.items():
    cq.exporters.export(cq.Workplane().add(s), f'parts/{k}.step')
cq.exporters.export(cq.Compound.makeCompound(list(parts.values())), 'mk4_drive_R_check.step')
json.dump({k: [round(v, 2) for v in (s.BoundingBox().xmin, s.BoundingBox().xmax, s.BoundingBox().ymin, s.BoundingBox().ymax, s.BoundingBox().zmin, s.BoundingBox().zmax)] for k, s in parts.items()}, open('parts_bb.json', 'w'), ensure_ascii=False, indent=1)

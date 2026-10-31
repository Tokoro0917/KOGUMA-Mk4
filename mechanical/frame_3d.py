"""フレームの3Dモデル(カーボン板・ポリカーボネート・M3の穴。リブがあるときはリブとリブの溝も)と、マウント・モーター・タイヤを並べた確認用の STEP と絵を作る。
座標 [mm]: x 前(+)、y 左(+)、z 上(床 = 0)。フレームの下面 z = 2.0"""
import os, sys, json, math
import numpy as np
import cadquery as cq
from shapely.geometry import Point
from shapely.ops import unary_union
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '../docs/calc/frame'))
sys.path.insert(0, os.path.join(HERE, 'motor_mount'))
import design as dz, ribparts as rp
import mount as mm

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'frame')   # 製作用のファイルは mechanical/frame に置く
TAG = 'frame_v6_7'   # ファンの真下を半径16.5mmまでカーボンで埋めた(2026-10-20)
P = json.load(open(os.path.join(HERE, '../docs/calc/frame/results/final_params.json')))
g = dz.build(**P)
slots = [s for (l, h, w) in g['vribs'] for s in rp.slots_for(l)]
holes = [Point(c).buffer(dz.HOLE_D / 2, 32) for c in dz.holes()]
plate = g['carbon'].difference(unary_union(slots + holes))

def poly_solid(poly, z0, z1):
    out = []
    for p in getattr(poly, 'geoms', [poly]):
        wp = cq.Workplane().polyline(list(p.exterior.coords)[:-1]).close().extrude(z1 - z0)
        for r in p.interiors:
            wp = wp.cut(cq.Workplane().polyline(list(r.coords)[:-1]).close().extrude(z1 - z0))
        out.append(wp.translate((0, 0, z0)).val())
    return cq.Compound.makeCompound(out)

parts = {}
parts['carbon'] = poly_solid(plate, 2.0, 3.0)
sheet = g['suction'].difference(Point(dz.FAN_X, 0).buffer(dz.FAN_R, 64))
parts['pc_sheet'] = poly_solid(sheet, 3.0, 3.2)     # 塩ビ 0.2mm
ribs = []
for (l, h, w) in g['vribs']:
    (x0, y0), (x1, y1) = l.coords[0], l.coords[-1]
    ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
    part = rp.rib_part(l.length, h)   # (u, v): v=0 が板の上面、つめは v<0
    s = cq.Workplane('XZ').polyline(list(part.exterior.coords)[:-1]).close().extrude(-0.5, both=True)
    s = s.rotate((0, 0, 0), (0, 0, 1), ang).translate((x0, y0, 3.0))
    ribs.append(s.val())
if ribs:
    parts['ribs'] = cq.Compound.makeCompound(ribs)
cq.exporters.export(cq.Compound.makeCompound(list(parts.values())), os.path.join(OUT, f'{TAG}_3d.step'))

# 確認用: マウント・モーター・タイヤ・ファン(左右)
m_r = mm.build().val()
mx, mz = mm.motor_center(mm.P)
extra = {'mount': cq.Compound.makeCompound([m_r, m_r.mirror('XZ')])}
mot = mm.ycyl(4.3, mm.P['motor_face'], mm.P['motor_face'] + 20, mx, mz).val()
extra['motor'] = cq.Compound.makeCompound([mot, mot.mirror('XZ')])
tire = mm.ycyl(7.5, -31.8, -28.3, 0, 7.5).cut(mm.ycyl(5.75, -31.9, -28.2, 0, 7.5)).val()
extra['tire'] = cq.Compound.makeCompound([tire, tire.mirror('XZ')])
extra['fan'] = cq.Workplane().center(dz.FAN_X, 0).circle(16).extrude(6).translate((0, 0, 3.2)).val()
# マウントなどを並べた STEP が要るときは、次の行を有効にする
# cq.exporters.export(cq.Compound.makeCompound(list(parts.values()) + list(extra.values())), os.path.join(OUT, f'{TAG}_with_mounts.step'))

# 絵
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
COL = {'carbon': '#4a463f', 'pc_sheet': '#9ecae1', 'ribs': '#e6550d', 'mount': '#f28e2b', 'motor': '#a0a0a0', 'tire': '#222', 'fan': '#c7e9c0'}
def tris(shape, tol=0.08):
    v, t = shape.tessellate(tol, 0.4)
    v = np.array([(p.x, p.y, p.z) for p in v])
    return v[np.array(t)] if len(t) else np.zeros((0, 3, 3))
fig = plt.figure(figsize=(16, 7.5))
for k, (items, elev, azim, title) in enumerate((
        (tuple(parts), 38, -62, f'{TAG} from front-left (carbon 1mm' + (' + ribs h3 orange' if ribs else ', no ribs') + ' + PVC 0.2mm blue)'),
        (tuple(parts), 38, -118, 'from rear-left'))):
    ax = fig.add_subplot(1, 2, k + 1, projection='3d')
    allp = {**parts, **extra}
    for name in items:
        T = tris(allp[name])
        a = 0.45 if name in ('pc_sheet', 'fan') else 1.0
        ax.add_collection3d(Poly3DCollection(T, facecolors=COL[name], linewidths=0, alpha=a, shade=True))
    ax.set_xlim(-52, 52); ax.set_ylim(-37, 37); ax.set_zlim(0, 12)
    ax.set_box_aspect((104, 74, 12), zoom=1.12); ax.view_init(elev, azim); ax.set_axis_off()
    ax.set_title(title, fontsize=10)
    ax.text(52, 0, 4, 'FRONT', fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(OUT, f'{TAG}_3d.png'), dpi=110)
v = sum(parts[k].Volume() for k in ('carbon', 'ribs') if k in parts)
print(f'カーボン {v * 1.55e-3:.2f} g、塩ビ {parts["pc_sheet"].Volume() * 1.4e-3:.2f} g')

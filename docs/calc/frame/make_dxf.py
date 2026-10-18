"""最終案の製作用 DXF(単位 mm、原点は車軸の中心、+x が前)
  CARBON      : カーボン板の外形と窓
  M3          : M3 の穴(φ3.2)。モーターマウントのねじの位置は仮
  RIB_SLOT    : リブを差す溝(リブがあるときだけ)
  RIB_PARTS   : リブの部品(同じ1mmのカーボン板から切る)。板の下に並べて置く(リブがあるときだけ)
  PC_SHEET    : ポリカーボネート 0.2mm の板(吸引する面)。板の下に置く
"""
import json, sys, numpy as np, ezdxf, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import Point
from shapely.ops import unary_union
from shapely import affinity
import design as dz, ribparts as rp

P = json.load(open(sys.argv[1]))
tag = sys.argv[2]
g = dz.build(**P)
ribs = g['vribs']
slots = [s for (l, h, w) in ribs for s in rp.slots_for(l)]
plate = g['carbon'].difference(unary_union(slots))
holes = [Point(x, sy * y) for (x, y) in dz.MOUNT_SCREWS for sy in (1, -1)]
sheet = g['suction'].difference(Point(dz.FAN_X, 0).buffer(dz.FAN_R, 64))

doc = ezdxf.new(units=4)   # mm
for name, col in (('CARBON', 7), ('M3', 1), ('RIB_SLOT', 3), ('RIB_PARTS', 5), ('PC_SHEET', 4), ('TEXT', 2)):
    doc.layers.add(name, color=col)
msp = doc.modelspace()
def add_poly(p, layer, dx=0, dy=0):
    for q in getattr(p, 'geoms', [p]):
        for ring in [q.exterior] + list(q.interiors):
            msp.add_lwpolyline([(x + dx, y + dy) for x, y in list(ring.coords)[:-1]], close=True, dxfattribs={'layer': layer})
add_poly(g['carbon'], 'CARBON')
for s in slots:
    add_poly(s, 'RIB_SLOT')
for h in holes:
    msp.add_circle(h.coords[0], 1.6, dxfattribs={'layer': 'M3'})
add_poly(sheet, 'PC_SHEET', dy=-85)
msp.add_text('PC 0.2mm (glue on TOP of carbon over suction area)', dxfattribs={'layer': 'TEXT', 'height': 2.0}).set_placement((-30, -105))
# リブの部品
y0 = -125
parts = []
for i, (l, h, w) in enumerate(ribs):
    part = rp.rib_part(l.length, h)
    add_poly(part, 'RIB_PARTS', dx=-50, dy=y0 - i * (h + 4))
    msp.add_text(f'RIB{i+1} L={l.length:.1f} h={h:.0f}', dxfattribs={'layer': 'TEXT', 'height': 1.5}).set_placement((-50 + l.length + 3, y0 - i * (h + 4)))
    parts.append(dict(no=i + 1, start=[round(c, 2) for c in l.coords[0]], end=[round(c, 2) for c in l.coords[-1]],
                      length=round(l.length, 2), height=h, tabs=[round(float(t), 2) for t in rp.tab_positions(l.length)]))
doc.saveas(f'{tag}.dxf')
json.dump(parts, open(f'{tag}_ribs.json', 'w'), indent=1)

# 寸法を書いた図
fig, ax = plt.subplots(figsize=(12, 8.4))
for q in getattr(plate, 'geoms', [plate]):
    ax.fill(*q.exterior.xy, color='#5f5a50', ec='k', lw=.5)
    for r in q.interiors:
        ax.fill(*r.xy, color='white', ec='k', lw=.5)
for p in g['pc']:
    ax.fill(*p.exterior.xy, color='#9ecae1', ec='#3182bd', lw=.6)
for (l, h, w) in ribs:
    ax.plot(*l.xy, color='#e6550d', lw=3, solid_capstyle='butt')
for hh in holes:
    ax.plot(*hh.buffer(1.6).exterior.xy, color='r', lw=1)
ax.plot(*Point(dz.FAN_X, 0).buffer(16).exterior.xy, 'g:', lw=1)
ax.plot(*g['suction'].exterior.xy, 'r--', lw=.8)
def note(x, y, s, dx=0, dy=0):
    ax.annotate(s, (x, y), (x + dx, y + dy), fontsize=7.5, color='#003', arrowprops=dict(arrowstyle='-', lw=.5, color='#003'))
(fx, fy), (rx, ry) = dz.G_FRONT, dz.G_REAR
fc = (dz.XE - P['end_edge'], dz.YE - P['rim'])
note(fx, fy, f'G start ({fx}, {fy})', 2, -7)
note(rx, ry, f'G start ({rx}, {ry})', -14, -7)
note(fc[0], fc[1], f'G end ({fc[0]}, {fc[1]})', -16, 9)
note(40, 0, f"spine {P['spine_root']}mm", -2, -6)
note(30, 28.3, f"rim {P['rim']}mm", 3, 6)
note(dz.XE - 1.5, -12, f"front edge {P['end_edge']}mm", -12, -14)
note(25, 20.4, f"G brace {P['brace_w']}mm" + (f" + rib h{P['v_rib_h']:.0f}" if ribs else ''), -8, 9)
for x, y in dz.MOUNT_SCREWS:
    note(x, -y, f'M3 ({x}, {-y})', -6, -9)
if 'A' in P['braces']:
    note(38.9, 11.4, f"brace A {P.get('brace_w_each', {}).get('A', P['brace_w'])}mm", 4, -3)
note(dz.FAN_X + 11, -11, 'fan dia.32 (dotted)', 4, -8)
ax.set_aspect('equal'); ax.grid(alpha=.25); ax.set_xlim(-55, 55); ax.set_ylim(-40, 40)
rib_s = f' + ribs 1mm x h{P["v_rib_h"]:.0f} (orange)' if ribs else ' (no ribs)'
ax.set_title(f'{tag}: carbon 1mm (gray){rib_s} + PC 0.2mm windows (blue). origin = axle, +x = front')
fig.tight_layout(); fig.savefig(f'{tag}_drawing.png', dpi=120)
print(json.dumps(parts, indent=1))

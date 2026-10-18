"""M3 の穴の中心を、板を広げなくても置ける所の図(穴のまわりに2mm以上の肉、吸引する面の外、
エンコーダの磁石から8mm以上、マウントのねじと重ならない)
使い方: python3 m3_map.py 出力.png"""
import sys, json, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import Point
from shapely.ops import unary_union
import design as dz

P = json.load(open('results/final_params.json'))
g = dz.build(**P)
screws = [(x, sy * y) for (x, y) in dz.MOUNT_SCREWS for sy in (1, -1)]
plate = g['carbon'].difference(unary_union([Point(c).buffer(1.6) for c in screws]))
ok = plate.buffer(-3.7).difference(g['suction'])
ok = ok.difference(unary_union([Point(c).buffer(7.4) for c in screws]))
ok = ok.difference(unary_union([Point(0, s * 22.0).buffer(8.0) for s in (1, -1)]))
fig, ax = plt.subplots(figsize=(10, 7))
for p in getattr(plate, 'geoms', [plate]):
    ax.fill(*p.exterior.xy, color='#5f5a50')
    for r in p.interiors:
        ax.fill(*r.xy, color='w')
for p in g['pc']:
    ax.fill(*p.exterior.xy, color='#9ecae1')
ax.plot(*g['suction'].exterior.xy, 'r--', lw=.8)
for p in getattr(ok, 'geoms', [ok]):
    if p.area > 0.01:
        ax.fill(*p.exterior.xy, color='#31a354', alpha=.9)
for c in screws:
    ax.plot(*Point(c).buffer(1.6).exterior.xy, 'r')
ax.set_aspect('equal'); ax.grid(alpha=.3); ax.set_xlim(-53, 53); ax.set_ylim(-38, 38)
ax.set_title('M3 hole centers OK without extra boss (green)\n(2 mm material around, outside suction area, >8 mm from encoder magnet, clear of mount screws)', fontsize=10)
fig.tight_layout(); fig.savefig(sys.argv[1], dpi=100)

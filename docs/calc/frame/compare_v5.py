"""v4.7 と v5 のカーボンの違いの図(赤 = 削った所、緑 = 足した所)。docs/calc/frame で python3 compare_v5.py"""
import json, sys
sys.path.insert(0, '.')
import design as dz
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import MultiPolygon, Polygon
def polys(g):
    return list(g.geoms) if hasattr(g, 'geoms') else [g]
def fill(ax, g, **kw):
    for p in polys(g):
        if p.is_empty or not isinstance(p, Polygon): continue
        ax.fill(*p.exterior.xy, **kw)
        for h in p.interiors:
            ax.fill(*h.xy, color='white', lw=0)
old = dz.build(**json.load(open('results/v4_7_params.json')))['carbon']
new = dz.build(**json.load(open('results/final_params.json')))['carbon']
cut = old.difference(new).buffer(-0.01).buffer(0.01)
add = new.difference(old).buffer(-0.01).buffer(0.01)
fig, ax = plt.subplots(figsize=(14, 9.5))
fill(ax, new, color='#5f5a50', lw=0)
fill(ax, cut, color='#e15759', lw=0)
fill(ax, add, color='#59a14f', lw=0)
for x, y in dz.holes():
    ax.add_patch(plt.Circle((x, y), dz.HOLE_D / 2, color='white'))
ax.text(-30, 0, 'REAR', ha='center', fontsize=12, color='w'); ax.text(38, 0, 'FRONT  →', ha='center', fontsize=11, color='w')
ax.fill([], [], color='#e15759', label=f'removed vs v4.7 ({cut.area * 1.55e-3:.2f} g)')
ax.fill([], [], color='#59a14f', label=f'added vs v4.7 ({add.area * 1.55e-3:.2f} g)')
ax.fill([], [], color='#5f5a50', label='frame v5 carbon')
ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.06), ncol=3, fontsize=11, frameon=False)
ax.set_aspect('equal'); ax.set_xlim(-53, 53); ax.set_ylim(-38, 38); ax.grid(alpha=.3)
ax.set_title('frame v5 vs v4.7: red = cut away, green = added (origin = axle, +x = front)')
fig.tight_layout(); fig.savefig('../../img/frame/v5_vs_v4_7.png', dpi=100)
print(round(old.area * 1.55e-3, 3), round(new.area * 1.55e-3, 3))

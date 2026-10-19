"""安全率5まで下げたときの形(results/sf5_cands.json)を並べて描く。docs/calc/frame で python3 sf5_view.py"""
import json
import design as dz
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import Polygon

P0 = json.load(open('results/final_params.json'))
cands = json.load(open('results/sf5_cands.json'))
res = {r['name']: r for r in json.load(open('results/sf5_try.json'))}
show = [('base', 'v5 (now)'), ('T3 作れる一番細い', 'T3: thinnest buildable'), ('T4 = T3 から筋交いAなし', 'T4: T3 without brace A')]
fig, axs = plt.subplots(1, 3, figsize=(21, 6.2))
for ax, (k, title) in zip(axs, show):
    g = dz.build(**dict(P0, **cands.get(k, {})))
    for p in (g['carbon'].geoms if hasattr(g['carbon'], 'geoms') else [g['carbon']]):
        ax.fill(*p.exterior.xy, color='#5f5a50', lw=0)
        for h in p.interiors:
            ax.fill(*h.xy, color='white', lw=0)
    for x, y in dz.holes():
        ax.add_patch(plt.Circle((x, y), dz.HOLE_D / 2, color='white'))
    r = res[k]
    sf = min(v for kk, v in r.items() if kk.startswith('SF_'))
    ax.set_title(f"{title}\ncarbon {r['m_carbon']:.2f} g, front skid {r['dA']:.2f} mm, corner {r['dB']:.2f} mm, {r['f1']:.0f} Hz\n"
                 f"buckling front {r['BK_D'] * 50:.0f} N / corner {r['BK_E'] * 30:.0f} N, material SF {sf:.1f}", fontsize=10)
    ax.set_aspect('equal'); ax.set_xlim(-53, 53); ax.set_ylim(-38, 38); ax.set_xticks([]); ax.set_yticks([])
fig.tight_layout(); fig.savefig('../../img/frame/sf5_shapes.png', dpi=90)

"""壁センサの光が迷路の壁のどこに当たるかの図(機体の中心がマスの真ん中、前向き)。
迷路: 1マス 180mm、壁の厚さ 12mm(壁の面は中心から 84mm)。使い方: python3 sensor_view.py 出力.png"""
import sys, os, json, math
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import LineString, box, Point
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '../../docs/calc/frame'))
import design as dz
sys.path.insert(0, HERE)
import pcb_shape
SENS = pcb_shape.SENS   # ホルダの前の面の真ん中と光の向き(基板 v7、2026-10-30。v6 までは (12, ±30)・(41, ±24))
P = json.load(open(os.path.join(HERE, '../../docs/calc/frame/results/final_params.json')))
g = dz.build(**P)
walls = {'left wall': box(-96, 84, 96, 96), 'right wall': box(-96, -96, 96, -84), 'front wall': box(84, -96, 96, 96)}
posts = [box(84, 84, 96, 96), box(84, -96, 96, -84), box(-96, 84, -84, 96), box(-96, -96, -84, -84)]
fig, ax = plt.subplots(figsize=(8, 8))
for w in walls.values():
    ax.fill(*w.exterior.xy, color='#d9c9a3')
for p in posts:
    ax.fill(*p.exterior.xy, color='#8c7b55')
c = g['carbon']
for q in getattr(c, 'geoms', [c]):
    ax.fill(*q.exterior.xy, color='#5f5a50')
    for h in q.interiors:
        ax.fill(*h.xy, color='w')
def hit(x, y, u, ws):
    ray = LineString([(x, y), (x + 400 * u[0], y + 400 * u[1])])
    best = None
    for wn, w in ws.items():
        i = ray.intersection(w)
        if not i.is_empty:
            d = Point(x, y).distance(i)
            if best is None or d < best[0]:
                best = (d, wn)
    if best is None:
        return None
    d = best[0]
    hx, hy = x + d * u[0], y + d * u[1]
    if min(Point(hx, hy).distance(p) for p in posts) < 1.0:     # 柱(の角)に当たる(2026-10-30)
        best = (d, 'post')
    return d, best[1], hx, hy
# 前の壁がないとき: 柱は残す(2026-10-30、横のセンサで柱を見るため)
no_front = {k: v for k, v in walls.items() if k != 'front wall'}
no_front.update({'post': posts[0], 'post ': posts[1]})
for nm, ((x, y), a) in SENS.items():
    u = (math.cos(math.radians(a)), math.sin(math.radians(a)))
    d, wn, hx, hy = hit(x, y, u, walls)
    ax.plot([x, hx], [y, hy], color='r', lw=1.2)
    ax.plot(x, y, 'o', color='r', ms=4)
    txt = f'{nm}: {wn} {d:.0f} mm\nhit at ({hx:.0f}, {hy:.0f})'
    h2 = hit(x, y, u, no_front)
    if h2 and (round(h2[2]), round(h2[3])) != (round(hx), round(hy)):
        d2, wn2, hx2, hy2 = h2
        ax.plot([hx, hx2], [hy, hy2], color='r', lw=1.0, ls='--')
        txt += f'\nno front wall: {wn2.strip()} at ({hx2:.0f}, {hy2:.0f})'
    ax.annotate(txt, (hx, hy), (hx - 60 if hx > 0 else hx + 5, hy + (8 if hy > 0 else -24)), fontsize=8)
ax.set_aspect('equal'); ax.set_xlim(-100, 100); ax.set_ylim(-100, 100); ax.grid(alpha=.3)
ax.set_title('wall sensors (mouse at cell center, heading +x). wall faces at 84 mm. dashed: without the front wall', fontsize=9)
fig.tight_layout(); fig.savefig(sys.argv[1], dpi=100)

# ---- 斜めの直線(2026-10-30): 前センサが柱にかかるか。使い方: python3 sensor_view.py 出力.png 斜めの出力.png ----
# 柱(12mm 角)の中心は進む線から 90/√2 = 63.6mm、同じ側の柱は 254.6mm おき、左右交互に 127.3mm おき。
# MK3 の斜めの制御(Wallsensor.c の calWallConrol_NANAME)は、前センサ(FL・FR)が柱に近づいて値が上がったら押し返す
if len(sys.argv) > 2:
    from shapely import affinity
    fig, axs = plt.subplots(1, 2, figsize=(14, 7))
    s2 = math.sqrt(2)
    posts_d = [box(i - 6, j - 6, i + 6, j + 6) for i in range(-360, 721, 180) for j in range(-360, 721, 180)]
    for ax, phase in zip(axs, (0.0, 63.6)):
        # 機体: 進む線 y = x - 90 の上、(90, 0) から phase だけ進んだ所、向き 45°
        cx, cy = 90 + phase / s2, phase / s2
        for p in posts_d:
            ax.fill(*p.exterior.xy, color='#8c7b55')
        g_ = affinity.translate(affinity.rotate(g['carbon'], 45, origin=(0, 0)), cx, cy)
        for q in getattr(g_, 'geoms', [g_]):
            ax.fill(*q.exterior.xy, color='#5f5a50')
        for nm, ((x, y), a) in SENS.items():
            if nm not in ('FL', 'FR'):
                continue
            th = math.radians(45)
            px, py = cx + x * math.cos(th) - y * math.sin(th), cy + x * math.sin(th) + y * math.cos(th)
            u = (math.cos(th + math.radians(a)), math.sin(th + math.radians(a)))
            ray = LineString([(px, py), (px + 400 * u[0], py + 400 * u[1])])
            best = None
            for p in posts_d:
                i = ray.intersection(p)
                if not i.is_empty:
                    d = Point(px, py).distance(i)
                    if best is None or d < best:
                        best = d
            L = best if best else 400
            ax.plot([px, px + L * u[0]], [py, py + L * u[1]], color='r', lw=1.2)
            ax.annotate(f'{nm}: ' + (f'post {best:.0f} mm' if best else 'no post within 400 mm'),
                        (px + L * u[0], py + L * u[1]), fontsize=8)
        xs = [cx - 120, cx + 330]; ax.plot(xs, [x - 90 for x in xs], color='#999', lw=0.6, ls='--')
        ax.set_aspect('equal'); ax.set_xlim(cx - 120, cx + 320); ax.set_ylim(cy - 120, cy + 320); ax.grid(alpha=.3)
        ax.set_title(f'diagonal run, {phase:.1f} mm after a wall midpoint', fontsize=9)
    fig.suptitle('front sensors on a diagonal straight (posts only; beams stop at the first post)', fontsize=10)
    fig.tight_layout(); fig.savefig(sys.argv[2], dpi=90)

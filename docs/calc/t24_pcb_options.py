"""タイヤ24mm のメイン基板の外形を広げる案の図(2026-11-22、ブランチ claude/trusting-dirac-1tdt54)
使い方(リポジトリの一番上で): python3 docs/calc/t24_pcb_options.py → docs/img/tire24/pcb_options.png"""
import sys, os
sys.path.insert(0, 'mechanical/vehicle'); sys.path.insert(0, 'docs/calc/frame')
import pcb_t24, pcb_shape as ps, design as dz
from shapely.geometry import box, Point
from shapely.ops import unary_union
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'WenQuanYi Zen Hei'; plt.rcParams['axes.unicode_minus'] = False

def cuts(o):
    x, y = 12.2, 22.3
    o = o.difference(box(-x, y, x, 60)).difference(box(-x, -60, x, -y))
    o = o.difference(unary_union([box(-4.5, 16.7, 4.5, 60), box(-4.5, -60, 4.5, -16.7)]).buffer(-1).buffer(1))
    o = o.difference(Point(ps.FAN).buffer(ps.HUB_HOLE, 64))
    return o.difference(unary_union([ps.slot(k) for k in ps.SENS]))
cur = ps.board()
from shapely.geometry import Polygon
A = unary_union([Polygon(p.exterior) for p in getattr(cur, 'geoms', [cur])])   # 中の穴(ポケット)を埋め、ハブの穴とほぞの穴だけ開け直す
A = A.difference(Point(ps.FAN).buffer(ps.HUB_HOLE, 64)).difference(unary_union([ps.slot(k) for k in ps.SENS]))
B = cuts(ps.outline_v11())
C = cuts(dz.outline(0).buffer(-1.5, join_style=2)).difference(Point(55, 0).buffer(18, 64))
bat = box(-16.25, -16, 6.25, 16)
under = unary_union([box(-17.2, -22.1, -6.9, 22.1), box(-23.6, 15.3, 10.6, 22.6), box(-23.6, -22.6, 10.6, -15.3)])
frame = dz.outline(0)
cases = [('今(t24v1)', cur, ''), ('A. 前と横のセンサの間のポケットを埋める', A, '+0.36g'),
         ('B. 後ろを削る前の形(main の v11)に戻す', B, '+0.74g'), ('C. フレームの 1.5mm 内側まで', C, '+2.2g')]
fig, axs = plt.subplots(2, 2, figsize=(15, 11))
for ax, (title, g, w) in zip(axs.flat, cases):
    ax.fill(*frame.exterior.xy, color='#eeeeee', ec='#888', lw=0.8)
    for p in getattr(cur, 'geoms', [cur]):
        ax.fill(*p.exterior.xy, color='#2e8b57', alpha=0.85)
        for r in p.interiors: ax.fill(*r.xy, color='#eeeeee')
    if g is not cur:     # 増える所は緑の上に描く(ポケットを埋めた所も見えるように)
        for p in getattr(g.difference(cur), 'geoms', [g.difference(cur)]):
            if p.area > 0.5:
                ax.fill(*p.exterior.xy, color='#f2b134', alpha=0.95)
    for p in getattr(g, 'geoms', [g]):
        ax.plot(*p.exterior.xy, color='k', lw=1.2)
        for r in p.interiors: ax.plot(*r.xy, color='k', lw=0.8)
    ax.fill(*bat.exterior.xy, fill=False, hatch='//', ec='#b8860b', lw=1.0)
    for p in getattr(under, 'geoms', [under]):
        ax.fill(*p.exterior.xy, fill=False, hatch='\\\\', ec='#8a5cc7', lw=0.8)
    for k in ps.SENS:
        ax.fill(*ps.holder(k).exterior.xy, color='#5aa0ff', alpha=0.8)
    for (x, y) in ps.SCREWS:
        ax.add_patch(plt.Circle((x, y), 1.1, color='w', ec='k', lw=0.6))
    for sy in (1, -1):
        ax.add_patch(plt.Rectangle((-12, 24.8 if sy > 0 else -33.3), 24, 8.5, fill=False, ec='#333', lw=0.8, ls='--'))
    ax.set_aspect('equal'); ax.set_xlim(-53, 53); ax.set_ylim(-38, 38); ax.grid(alpha=0.2)
    ax.set_title(f'{title}: {g.area:,.0f}mm²(今から {g.area - cur.area:+,.0f}、+{(g.area - cur.area) / cur.area:.0%}) {w}', fontsize=11)
fig.suptitle('メイン基板の外形の案(緑 = 今、黄 = 増える所、黒の線 = 案の外形)。黄の斜線 = 電池(上の面に置けない)、紫の斜線 = モーター・マウント(裏の面に置けない)、\n'
             '青 = 壁センサのホルダ(裏)、白丸 = 柱、点線 = タイヤ。灰色はフレーム。main(v17)は 3,110mm²', fontsize=11)
fig.tight_layout()
os.makedirs('docs/img/tire24', exist_ok=True)
fig.savefig('docs/img/tire24/pcb_options.png', dpi=85)
print({t: round(g.area) for t, g, _ in cases})

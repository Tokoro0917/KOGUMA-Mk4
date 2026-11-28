"""タイヤ24mm のメイン基板の外形: B 案の広さのまま、形を整える案(2026-11-22、ブランチ claude/trusting-dirac-1tdt54)
使い方(リポジトリの一番上で): python3 docs/calc/t24_pcb_design.py → docs/img/tire24/pcb_design.png
作り方: v11 の形(切り欠く前)に後ろの形を足し・引きし、へこんだ角と出っ張った角を丸めてから、タイヤ・車軸の切り欠き、ファンのハブの穴、
ほぞの穴を開ける(切り欠きは丸めない。タイヤとのすき間を減らさないため)。切り欠きの角は R1
確かめること: UI の LED(縁から 0.3mm)・柱(半径2.6 が基板の中)・壁センサの足の穴(1.6mm の四角、縁から 0.2mm)"""
import sys, os, math
sys.path.insert(0, 'mechanical/vehicle'); sys.path.insert(0, 'docs/calc/frame')
import pcb_t24, pcb_shape as ps, design as dz
from shapely.geometry import box, Point, Polygon
from shapely.ops import unary_union
from shapely import affinity
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'WenQuanYi Zen Hei'; plt.rcParams['axes.unicode_minus'] = False

FRAME = dz.outline(0)
LIM = FRAME.buffer(-ps.FRAME_MARGIN, join_style=2)

def base_v11():
    """v11 の形を、切り欠きとハブの穴を開ける前で"""
    keep = ps.WHEEL_CUT
    ps.WHEEL_CUT = (0.0, 0.0, 99.0)
    o = ps.outline_v11()
    ps.WHEEL_CUT = keep
    return unary_union([Polygon(p.exterior) for p in getattr(o, 'geoms', [o])])

def cuts(o):
    x0, x1, y0 = ps.WHEEL_CUT
    xa, ya = pcb_t24.AXLE_CUT
    c = unary_union([box(x0, y0, x1 - 0.3, 60), box(x0, -60, x1 - 0.3, -y0), box(-xa, ya, xa, 60), box(-xa, -60, xa, -ya)]).buffer(-1.0).buffer(1.0)
    o = o.difference(c).difference(Point(ps.FAN).buffer(ps.HUB_HOLE, 64))
    keep = unary_union([Point(p).buffer(3.1) for p in ps.SCREWS] + [box(-3.6, 15.4, 3.6, 16.7), box(-3.6, -16.7, 3.6, -15.4)]
                       + [ps.footprint(k, 1.0) for k in ps.SENS]).intersection(o)
    o = o.buffer(-R_CUT, join_style=1).buffer(R_CUT, join_style=1).union(keep)   # 切り欠きでできた出っ張った角を R_CUT で丸める(柱・パッド・センサの所は残す)
    o = o.buffer(-0.01).buffer(0.01)
    return o.difference(unary_union([ps.slot(k) for k in ps.SENS]))
R_CUT = 3.0

def smooth(o, r_in, r_out):
    o = o.buffer(r_in, join_style=1).buffer(-r_in, join_style=1)
    return o.buffer(-r_out, join_style=1).buffer(r_out, join_style=1)

def pods(o):
    """壁センサの所は、丸めたあとも必ず残す(フレームの 0.3mm 内側まで)"""
    return unary_union([o] + [ps.footprint(k, 1.0).intersection(FRAME.buffer(-0.3, join_style=2)) for k in ps.SENS])

R = ps.REAR
yi, yo = ps.LED_WING
def design(kind):
    o = base_v11()
    if kind == 'V':          # 後ろを ToraNeko.Mk3 と同じ V 字に切り欠き、左右の角(羽)に LED(main v15・v16 と同じ考え方)
        o = o.difference(Polygon([(R - 1, yi), (R, yi), (ps.LED_APEX, 0.0), (R, -yi), (R - 1, -yi)]))
        o = o.difference(box(R - 5, 23.0, -16, 40)).difference(box(R - 5, -40, -16, -23.0))  # 羽の外は |y| 23 まで(main は 18.5。後ろの柱 (-21, ±19.5) のため)
    elif kind == 'arc':      # 後ろも前と同じ円弧で切り欠く(前後で同じ形)
        o = o.difference(Point(R - 13.0, 0).buffer(15.0, 128))
    elif kind == 'wing':     # 後ろは広く残し、羽の先を大きく丸める
        o = o.difference(Point(R - 9.0, 0).buffer(11.0, 128))
    o = smooth(o.intersection(LIM), 10.0, 3.0)
    return cuts(pods(o))

def check(o):
    o = o.union(unary_union([ps.slot(k) for k in ps.SENS]))      # ほぞの穴と受光の足のパッドの問題は main からあるので、ここでは見ない
    bad = []
    for i, p in enumerate(ps.LEDS):
        if not o.buffer(-0.3).contains(Point(p).buffer(0.55)):
            bad.append(f'LED{i + 1}')
    for p in ps.SCREWS:
        if not o.contains(Point(p).buffer(2.6)):      # 柱(マウントの柱の上の面)が基板の中にあること
            bad.append(f'柱{p}')
    for k in ps.SENS:
        (_, ang) = ps.SENS[k]
        for (px, py) in ps.pads(k):
            sq = affinity.rotate(box(px - 0.8, py - 0.8, px + 0.8, py + 0.8), ang, origin=(px, py))
            if not o.buffer(-0.2).contains(sq):
                bad.append(f'{k}の足')
    return sorted(set(bad))

if __name__ == '__main__':
    cur = ps.outline()      # ねじの穴・ほぞの穴を除く前の形で比べる
    cases = [('今(B 案、t24v2)', cur)] + [(n, design(k)) for n, k in (('案1: 後ろを V 字に(ToraNeko・main v16 と同じ)', 'V'),
                                                                       ('案2: 後ろも前と同じ円弧に', 'arc'),
                                                                       ('案3: 後ろを広く、羽の先を大きく丸める', 'wing'))]
    fig, axs = plt.subplots(2, 2, figsize=(15, 11))
    for ax, (title, g) in zip(axs.flat, cases):
        ax.fill(*FRAME.exterior.xy, color='#eeeeee', ec='#888', lw=0.8)
        for p in getattr(g, 'geoms', [g]):
            ax.fill(*p.exterior.xy, color='#2e8b57')
            for r in p.interiors: ax.fill(*r.xy, color='#eeeeee')
            ax.plot(*p.exterior.xy, color='k', lw=1.0)
        for k in ps.SENS:
            ax.fill(*ps.holder(k).exterior.xy, color='#5aa0ff', alpha=0.8)
            for (px, py) in ps.pads(k): ax.add_patch(plt.Circle((px, py), 0.8, fill=False, ec='orange', lw=0.8))
        for (x, y) in ps.SCREWS: ax.add_patch(plt.Circle((x, y), 1.1, color='w', ec='k', lw=0.6))
        for (x, y) in ps.LEDS: ax.add_patch(plt.Rectangle((x - 0.25, y - 0.5), 0.5, 1.0, color='#ffd27f'))
        for sy in (1, -1):
            ax.add_patch(plt.Rectangle((-12, 24.8 if sy > 0 else -33.3), 24, 8.5, fill=False, ec='#333', lw=0.8, ls='--'))
        ax.add_patch(plt.Rectangle((-16.25, -16), 22.5, 32, fill=False, ec='#b8860b', lw=0.8, ls=':'))
        bad = check(g)
        ax.set_aspect('equal'); ax.set_xlim(-50, 50); ax.set_ylim(-37, 37); ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(f'{title}\n{g.area:,.0f}mm²(今から {g.area - cur.area:+,.0f}、{(g.area - cur.area) * 0.6 * 1.85e-3:+.2f}g)' + ('' if not bad else f'  ×: {", ".join(bad)}'), fontsize=11)
    fig.suptitle('メイン基板の外形の形(どれも、へこんだ角 R10・出っ張った角 R3。タイヤ・車軸の切り欠きは、端の出っ張った角だけ R3 で丸める)。灰色 = フレーム、点線 = タイヤ・電池', fontsize=12)
    fig.tight_layout()
    fig.savefig('docs/img/tire24/pcb_design.png', dpi=85)
    for t, g in cases:
        print(t, round(g.area), check(g))

"""MK4 電池のホルダ(左右2個)。CadQuery で作る。
基板を留める上のねじ(マウントの前後の柱、(-17, ±22)・(8, ±22)。鉄の低頭 M2 L5)を共用して、電池の位置だけを決める(ねじは増やさない)。
左右それぞれ、電池の横の面に沿う壁と、前後の角を回り込む短い壁(コの字)、ねじの頭の下にはさむ耳2つ。
電池の上下(z)は両面テープで基板に貼る。前後・左右は壁で止める。
v1(2026-10-31): 壁 1.0mm、高さ 4.0mm(基板の上面から)、電池とのすき間 0.3mm、角の回り込み 4.0mm、耳の厚さ 1.0mm
座標は機体と同じ [mm]: 原点は車軸の中心で床、+x が前、+y が左。z は基板の上面(z 14.2)から上
使い方(リポジトリの一番上で): python3 mechanical/battery_holder/battery_holder.py → battery_holder_L_v1.* / _R_v1.*
"""
import os, sys
import cadquery as cq
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '../vehicle'))
import pcb_shape as ps

P = dict(gap=0.3, wall=1.0, h=4.0, ret=4.0, ear_t=1.0, ear_r=2.6, hole_d=2.2, r=0.5)
VER = 'v1'

def holder(sy, P=P, z0=0.0):
    """sy = +1 が左(y > 0)、-1 が右。z0 は基板の上面の高さ"""
    bx0, bx1, by = ps.BAT
    g, w, h = P['gap'], P['wall'], P['h']
    xi0, xi1, yi = bx0 - g, bx1 + g, by + g            # 電池のまわりの内側の線
    side = cq.Workplane().box(xi1 - xi0 + 2 * w, w, h, centered=False).translate((xi0 - w, yi, 0))
    rets = [cq.Workplane().box(w, P['ret'], h, centered=False).translate((x, yi - P['ret'], 0)) for x in (xi0 - w, xi1)]
    body = side
    for r_ in rets:
        body = body.union(r_)
    holes = [(x, y) for (x, y) in ps.SCREWS if y > 0]
    for hx, hy in holes:
        er = P['ear_r']
        ear = (cq.Workplane().center(hx, hy).circle(er).extrude(P['ear_t'])
               .union(cq.Workplane().box(2 * er, hy - yi, P['ear_t'], centered=False).translate((hx - er, yi, 0))))
        body = body.union(ear)
    try:
        body = body.edges('|Z').fillet(P['r'] * 0.99)
    except Exception:
        pass
    for hx, hy in holes:
        body = body.cut(cq.Workplane().center(hx, hy).circle(P['hole_d'] / 2).extrude(20).translate((0, 0, -5)))
    if sy < 0:
        body = body.mirror('XZ')
    return body.translate((0, 0, z0))

if __name__ == '__main__':
    import numpy as np
    for sy, nm in ((1, 'L'), (-1, 'R')):
        s = holder(sy)
        for ext in ('step', 'stl'):
            kw = dict(tolerance=0.01, angularTolerance=0.1) if ext == 'stl' else {}
            cq.exporters.export(s, os.path.join(HERE, f'battery_holder_{nm}_{VER}.{ext}'), **kw)
        v = s.val().Volume(); bb = s.val().BoundingBox()
        print(f'{nm}: 体積 {v:.1f} mm³、光造形の樹脂(1.15 g/cm³)で {v * 1.15e-3:.3f} g、大きさ {bb.xlen:.1f} × {bb.ylen:.1f} × {bb.zlen:.1f}')
    # 図: 上から(電池と基板の外形とねじ)と斜め
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig = plt.figure(figsize=(13, 5.5))
    ax = fig.add_subplot(1, 2, 1)
    o = ps.outline(); ax.plot(*o.exterior.xy, color='#2a7', lw=0.8)
    for i in o.interiors: ax.plot(*i.xy, color='#2a7', lw=0.5)
    bx0, bx1, by = ps.BAT
    ax.add_patch(plt.Rectangle((bx0, -by), bx1 - bx0, 2 * by, fc='#cde', ec='#36a', lw=0.8)); ax.text(bx0 + 1, -1, 'battery', color='#36a')
    from shapely.geometry import Polygon
    for sy in (1, -1):
        sec = holder(sy).section(0.5)
        for f in sec.faces().vals():
            pts = [(v.X, v.Y) for v in f.outerWire().Vertices()]
            ax.fill(*zip(*pts), color='#333', alpha=0.85)
        sec = holder(sy).section(2.5)
        for f in sec.faces().vals():
            pts = [(v.X, v.Y) for v in f.outerWire().Vertices()]
            ax.fill(*zip(*pts), color='#000')
    for (x, y) in ps.SCREWS: ax.add_patch(plt.Circle((x, y), 1.1, fc='w', ec='k', lw=0.6))
    ax.set_aspect('equal'); ax.set_xlim(-32, 48); ax.set_ylim(-36, 36); ax.set_title('top view (grey: ears t1.0, black: walls h4.0)', fontsize=9); ax.grid(alpha=0.3)
    ax = fig.add_subplot(1, 2, 2, projection='3d')
    for sy in (1, -1):
        vs, ts = holder(sy).val().tessellate(0.02, 0.2)
        V_ = np.array([[p.x, p.y, p.z] for p in vs]); T = V_[np.array(ts)]
        nrm = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); nrm /= np.linalg.norm(nrm, axis=1)[:, None] + 1e-12
        sh = 0.35 + 0.65 * np.clip(nrm @ np.array([0.4, -0.6, 0.7]), 0, 1)
        ax.add_collection3d(Poly3DCollection(T, facecolor=np.c_[0.3 * sh, 0.3 * sh, 0.33 * sh, np.ones_like(sh)], edgecolor='none'))
    ax.set_xlim(-22, 12); ax.set_ylim(-25, 25); ax.set_zlim(-2, 8); ax.set_box_aspect((34, 50, 10)); ax.view_init(30, -60)
    fig.suptitle(f'MK4 battery holder {VER} (L/R, black resin): walls {P["wall"]} x h{P["h"]} mm, gap {P["gap"]} mm, '
                 f'ears t{P["ear_t"]} under the M2 L5 PCB screws', fontsize=10)
    fig.tight_layout(); fig.savefig(os.path.join(HERE, f'battery_holder_{VER}.png'), dpi=90)

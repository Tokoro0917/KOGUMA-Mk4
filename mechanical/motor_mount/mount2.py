"""MK4 モーターマウント v20(2026-11-01 に作り直し)。CadQuery。右側(y が負)。左は y を反転して作る。
v1〜v16(mount.py)は形を少しずつ足し引きしてきたので、考え方をそろえて一つの箱から作り直した。

座標 [mm]: x 前(+)、y 左(+)、z 上(床 = 0)。車軸 (0, y, 7.5)。フレームの上面 z 3.0、メイン基板の下面 z 13.6。
部品の並び(外側 → 内側、y):
  41T -28.3〜-26.3 | LF-630(外、つばが外)-26.7〜-24.7(つば -26.7〜-26.1) | MR63(内、つばなし)-24.7〜-22.7(2つを突き当てる)
  磁石 -23.7〜-22.7 | チップ -22.2〜-21.1 | エンコーダ基板 -21.0〜-20.4(マウントの面 y -21.0 に当てる)
  モーター NFP-D8620 φ8.6 × 20: 前の面 y -25.0、車軸の後ろ 8.1mm(41T:13T)で水平から 5° 上。ピニオン 13T -25.9〜-27.9

形(すべて一つの箱から削る):
  箱      x(モーターの筒の後ろ)〜 x 4.0、y -25.6(外の面)〜 -21.0(エンコーダ基板を当てる面)、z 3.0(フレーム)〜 13.4
  筒      箱より内側へ、モーターの筒(壁 0.9mm)を y -15.6 まで
  輪      外の面の外に、外の軸受のつばを全周で受ける輪(半径 4.0、y -26.1〜-25.6)
  耳と柱  前 (8, -22)・後ろ (-17, -22):フレームの上から基板の下面 z 13.6 まで。上下から M2 のねじ山(下穴 φ1.6)
  腕      前の耳から、吸引ファンの台の継ぎ目 (14, -22) へ(z 4.0〜8.8、継ぎ目の柱は半径 2.5、上から M2 のねじ山)
穴:
  モーター  前の面 y -25.0 から内側へ。当たり面3つ(φ8.5、しまりばめ)、その間は逃がし(φ8.8)、
            軸受の穴の側(±30°)は寸法どおり(φ8.6。間の壁 0.8mm を押さない)、内側の入口 1.0mm は寸法どおりの丸い穴、面取り 0.3
  軸受      外の面 y -26.1 から y -22.7 まで(2.0 + 2.0 - 0.6 = 3.4mm)。モーターと同じ考え方で当たり面3つ(φ5.9)。外から MR63、LF-630 の順に入れる
  エンコーダの部屋  x ±2.75、z 4.0〜11.0、y -22.7〜-21.0。MT6835 は TSSOP-16(本体 x ±2.5、脚の列が上下で z 4.3〜10.7)。
            左右の壁(x ±2.75)が MR63 の外輪(半径 2.75〜3.0)に当たって、内側への止めになる(内輪には当たらない)。
            2つの軸受の位置は LF-630 のつばで決まる(外から MR63、LF-630 の順に押し込む)ので、この止めは後で内へずれないためのもの
  基板の溝    エンコーダ基板(x ±3.0)が筒の横を通る所を x ±3.1 で逃がす
  はんだの逃げ  基板の上の端(メイン基板とのはんだのフィレット)の所: 面から 0.6mm、z 12.3 から上
使い方(このフォルダで): python3 mount2.py → motor_mount_R_v20.step/.stl、motor_mount_L_v20.step/.stl、motor_mount_v20.png
"""
import math
import cadquery as cq

P = dict(
    frame_top=3.0, box_top=13.4, pcb_post=13.6,
    axle=(0.0, 7.5), cd=0.15 * (41 + 13), motor_angle=5.0,
    motor_d=8.6, motor_face=-25.0, motor_end=-15.6, lip_hole=3.2, outer_face=-25.6, wall=0.9,
    brg_od=6.0, brg_face=-26.1, brg_end=-22.7, flange_ring_r=4.0,
    press=0.1, relief=0.1, pad_w=2.6, wall_free=30.0, mouth=1.0, chamfer=0.3, brg_chamfer=0.1,
    box_front=4.0, board_face=-21.0, board_half=3.0, board_t=0.6, slot_clr=0.1,
    chamber=(-2.75, 2.75, 4.0, 11.0),   # MT6835(TSSOP-16、本体 5.0 × 4.4、脚の先まで 6.4mm)。脚の列は上下(z 4.3〜10.7)
    solder=(0.6, 12.3, 3.2),
    screw_rear=(-17.0, -22.0), screw_front=(8.0, -22.0), boss_r=2.6, post_r=2.6, ear_top=7.0, link_w=3.4,
    fan_joint=(14.0, -22.0), joint_r=2.5, joint_z=(4.0, 8.8), arm_w=3.4, hole_d=1.6, hole_chamfer=0.3,
    # mount.py と同じ名前で vehicle.py などが読む値
    motor_len=20.0, cradle_end=-15.6, brg_seat_out=-26.1, brg_seat_in=-22.7, inner_bearing='MR63',
)
VER = 'v20'

def motor_center(P=P):
    a = math.radians(P['motor_angle'])
    return (P['axle'][0] - P['cd'] * math.cos(a), P['axle'][1] + P['cd'] * math.sin(a))

def ycyl(r, y0, y1, x, z):
    lo, hi = min(y0, y1), max(y0, y1)
    return cq.Workplane('XZ', origin=(x, 0, z)).circle(r).extrude(-(hi - lo)).translate((0, lo, 0))

def zcyl(r, z0, z1, x, y):
    return cq.Workplane().center(x, y).circle(r).extrude(z1 - z0).translate((0, 0, z0))

def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane().box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))

def wedge(R, y0, y1, x, z, a, hw):
    lo, hi = min(y0, y1), max(y0, y1)
    pts = [(0, 0)] + [(R * math.cos(a + t), R * math.sin(a + t)) for t in (-hw, -hw / 2, 0, hw / 2, hw)]
    return cq.Workplane('XZ', origin=(x, 0, z)).polyline(pts).close().extrude(-(hi - lo)).translate((0, lo, 0))

def press_bore(d, y0, y1, x, z, a_pad, a_wall, P):
    """しまりばめの穴(削る形): 当たり面3つ(直径 d - press、角度 a_pad + k·120°)、その間は逃がし(d + 2·relief)、
    a_wall ± wall_free は寸法どおり(d)"""
    rp, rn, rr = (d - P['press']) / 2, d / 2, d / 2 + P['relief']
    hw = math.radians(P['wall_free'])
    cut = ycyl(rp, y0, y1, x, z)
    rel = ycyl(rr, y0, y1, x, z).cut(wedge(rr + 2, y0, y1, x, z, a_wall, hw))
    lo, hi = min(y0, y1), max(y0, y1)
    for k in range(3):
        b = a_pad + k * 2 * math.pi / 3
        rel = rel.cut(cq.Workplane().box(rr + 1, hi - lo, P['pad_w'], centered=(False, False, True))
                      .rotate((0, 0, 0), (0, 1, 0), -math.degrees(b)).translate((x, lo, z)))
    cut = cut.union(rel).union(ycyl(rn, y0, y1, x, z).intersect(wedge(rn + 2, y0, y1, x, z, a_wall, hw)))
    return cut

def cone_y(r, c, y, sgn, x, z):
    return cq.Workplane().add(cq.Solid.makeCone(r + c, r, c, cq.Vector(x, y, z), cq.Vector(0, sgn, 0)))

def cone_z(r, c, z, sgn, x, y):
    return cq.Workplane().add(cq.Solid.makeCone(r + c, r, c, cq.Vector(x, y, z), cq.Vector(0, 0, sgn)))

def build(P=P):
    """形を作る(足し引きのたびの面の整理は最後に1回だけ)"""
    _cut, _union = cq.Workplane.cut, cq.Workplane.union
    cq.Workplane.cut = lambda self, o, clean=False, tol=None: _cut(self, o, clean=False)
    cq.Workplane.union = lambda self, o=None, clean=False, glue=False, tol=None: _union(self, o, clean=False)
    try:
        return _build(P)
    finally:
        cq.Workplane.cut, cq.Workplane.union = _cut, _union

def _build(P):
    ax, az = P['axle']
    mx, mz = motor_center(P)
    ft, top = P['frame_top'], P['box_top']
    rm = P['motor_d'] / 2 + P['wall']
    yo, yb = P['outer_face'], P['board_face']
    # ---- 肉 ----
    body = box(mx - rm, ax + P['box_front'], yo, yb, ft, top)                                   # 箱
    body = body.union(ycyl(rm, yb, P['motor_end'], mx, mz)).union(box(mx - rm, mx + rm, yb, P['motor_end'], ft, mz))   # 内側へ伸ばすモーターの筒
    body = body.union(ycyl(P['flange_ring_r'], P['brg_face'], yo, ax, az))                     # 外のつばを受ける輪
    body = body.cut(box(-50, 50, -50, 50, top, 30))                                              # 上は z box_top まで
    (rx, ry), (fx, fy) = P['screw_rear'], P['screw_front']
    lw = P['link_w'] / 2
    body = body.union(box(rx, mx - rm + 0.01, ry - lw, ry + lw, ft, P['ear_top']))              # 後ろの耳へ
    body = body.union(box(ax + P['box_front'] - 0.01, fx, fy - lw, fy + lw, ft, P['ear_top']))  # 前の耳へ
    for (sx, sy) in (P['screw_rear'], P['screw_front']):
        body = body.union(zcyl(P['post_r'], ft, P['pcb_post'], sx, sy))                         # 耳と柱(基板の下面まで)
    jx, jy = P['fan_joint']; j0, j1 = P['joint_z']
    body = body.union(box(fx, jx, jy - P['arm_w'] / 2, jy + P['arm_w'] / 2, j0, j1)).union(zcyl(P['joint_r'], j0, j1, jx, jy))   # ファンの台への腕
    # ---- 穴 ----
    a_m = math.atan2(az - mz, ax - mx)          # モーターから車軸への向き(xz 面)
    body = body.cut(press_bore(P['motor_d'], P['motor_face'], P['motor_end'] - P['mouth'], mx, mz, a_m + math.pi / 3, a_m, P))
    body = body.cut(ycyl(P['motor_d'] / 2, P['motor_end'] - P['mouth'] - 0.01, P['motor_end'] + 1, mx, mz), clean=False)   # 入口はまっすぐな丸い穴
    body = body.cut(cone_y(P['motor_d'] / 2, P['chamfer'], P['motor_end'], -1, mx, mz))
    body = body.cut(ycyl(P['lip_hole'] / 2, yo - 1, P['motor_face'] + 0.01, mx, mz))            # モーターの軸受けの出っ張りの逃げ
    body = body.cut(press_bore(P['brg_od'], P['brg_face'] - 1, P['brg_end'], ax, az, a_m + math.pi + math.pi / 3, a_m + math.pi, P))
    body = body.cut(cone_y(P['brg_od'] / 2, P['brg_chamfer'], P['brg_face'], 1, ax, az))
    cx0, cx1, cz0, cz1 = P['chamber']
    body = body.cut(box(ax + cx0, ax + cx1, P['brg_end'] - 0.01, yb + 0.01, cz0, cz1))           # エンコーダの部屋
    h = P['board_half'] + P['slot_clr']
    body = body.cut(box(ax - h, ax + h, yb, yb + P['board_t'] + 0.05, ft - 0.01, 30))           # エンコーダ基板の溝
    sd, sz0, sh = P['solder']
    body = body.cut(box(ax - sh, ax + sh, yb - sd, yb + 0.01, sz0, 30))                          # はんだのフィレットの逃げ
    for (sx, sy) in (P['screw_rear'], P['screw_front']):                                         # 耳と柱: 上下からねじ山
        body = body.cut(zcyl(P['hole_d'] / 2, ft - 1, P['pcb_post'] + 1, sx, sy))
        body = body.cut(cone_z(P['hole_d'] / 2, P['hole_chamfer'], ft, 1, sx, sy)).cut(cone_z(P['hole_d'] / 2, P['hole_chamfer'], P['pcb_post'], -1, sx, sy))
    body = body.cut(zcyl(P['hole_d'] / 2, j0 - 1, j1 + 1, jx, jy)).cut(cone_z(P['hole_d'] / 2, P['hole_chamfer'], j1, -1, jx, jy))
    return body

if __name__ == '__main__':
    import os
    import numpy as np
    here = os.path.dirname(os.path.abspath(__file__))
    m = build()
    v = m.val().Volume(); bb = m.val().BoundingBox()
    print(f'{VER}: 体積 {v:.0f} mm³、樹脂(1.2 g/cm³)で {v * 1.2e-3:.2f} g、外形 x {bb.xmin:.2f}〜{bb.xmax:.2f}、y {bb.ymin:.2f}〜{bb.ymax:.2f}、z {bb.zmin:.2f}〜{bb.zmax:.2f}、正しい形 {m.val().isValid()}')
    L = m.mirror('XZ')
    for nm, s in (('R', m), ('L', L)):
        cq.exporters.export(s, os.path.join(here, f'motor_mount_{nm}_{VER}.step'))
        cq.exporters.export(s, os.path.join(here, f'motor_mount_{nm}_{VER}.stl'), tolerance=0.01, angularTolerance=0.1)
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    vs, ts = m.val().tessellate(0.02, 0.2)
    V = np.array([[p.x, p.y, p.z] for p in vs]); T = V[np.array(ts)]
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); n /= np.linalg.norm(n, axis=1)[:, None] + 1e-12
    fig = plt.figure(figsize=(18, 9.5))
    for i, (el, az_, t) in enumerate(((20, -60, 'outside, front'), (20, -125, 'outside, rear'), (20, 60, 'inside, front (encoder face)'),
                                      (20, 125, 'inside, rear (motor goes in)'), (75, -90, 'top'), (-60, -90, 'bottom'))):
        a3 = fig.add_subplot(2, 3, i + 1, projection='3d')
        Lv = np.array([math.cos(math.radians(az_)) * math.cos(math.radians(el)), math.sin(math.radians(az_)) * math.cos(math.radians(el)), math.sin(math.radians(el))])
        sh = 0.3 + 0.7 * np.clip(n @ Lv, 0, 1)
        a3.add_collection3d(Poly3DCollection(T, facecolor=np.c_[0.95 * sh, 0.6 * sh, 0.25 * sh, np.ones_like(sh)], edgecolor='none'))
        a3.set_xlim(-20, 17); a3.set_ylim(-27, -14); a3.set_zlim(2, 15); a3.set_box_aspect((37, 13, 13)); a3.view_init(el, az_)
        a3.set_title(t, fontsize=10); a3.set_xticks([]); a3.set_yticks([]); a3.set_zticks([])
    fig.suptitle(f'MK4 motor mount {VER} (right, rebuilt from one box): LF-630 (outer) + MR63 (inner) butted, 3-pad press fits, encoder board on the face y -21.0, {v * 1.2e-3:.2f} g', fontsize=11)
    fig.tight_layout(); fig.savefig(os.path.join(here, f'motor_mount_{VER}.png'), dpi=80)

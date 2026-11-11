"""MK4 壁センサのホルダ。CadQuery で作る。
ToraNeko.Mk3 のセンサホルダ v4(`mechanical/exported/TORANEKO.Mk3_v36.step` の「センサホルダ v4」を測った)と同じ形:
発光(OPV332、φ3 の T-1)を基板から遠い穴、受光(SFH 229 FA、φ3 の T-1)を基板に近い穴に入れ、足は後ろから出して基板の側へ曲げ、基板の穴に通す。
ホルダのほぞを基板の穴に差して、位置と向きを決める。
v1(2026-10-30): ToraNeko と同じ寸法で、基板の上に立てる(高さ 10.5mm、穴 3.5・8.1mm)
v2(2026-10-30): **基板の裏(下)にさかさまに付ける**。下はフレーム(上面 z 3.0)なので、高さを 9.9mm、穴を 3.2・7.6mm にした
               (基板の下面 z 13.6 から下の端 z 3.7、フレームまで 0.7mm)
v3(2026-10-31): **下の端をフレームに当てる**(フレームとの間 0.3mm に両面テープ(スポンジ)をはさんで貼る)。高さ 9.9 → 10.3mm
               (下の端 z 3.3)。穴の位置(光の高さ)は同じ。下の端から後ろへ**足**(長さ 3.5mm、厚さ 1.0mm)を出し、フレームの骨に当たる面積を増やす
               (横の2本は、ホルダの真下がほとんど窓なので、足がないとカーボンに当たるのが 6mm² だけ。足で 18mm²)。
               フレームがたわんでもぶつからず、基板の前の板をフレームで支えて揺れを減らす
v4(2026-11-01): **足をやめ、ホルダの形のままそのまま下まで伸ばす**(6.0 × 4.04mm の四角い柱、高さ 10.3mm)。
               **丸めていた角をすべて角にし**、下の端の面(6.0 × 4.04mm = 24mm²)を全部平らにして、そこに緩衝材(両面テープ)を貼ってフレームに当てる。
               フレームはこの下の端の真下 + 1mm を窓なしにする
v5(2026-11-01): **ほぞをかっちりはめる**。ほぞの4つの面の真ん中に、つぶし用のリブ(幅 0.3mm、高さ 0.6mm、先 0.2mm を面取り)を付けた。
               リブの先どうしの幅 3.25mm(基板の穴 3.2mm より 0.05mm きつい)。差し込むとリブの先だけがつぶれて止まる。形はほかは v4 と同じ。
               合わせ用の試し片(リブの幅 3.15〜3.35mm の5本)は fit_test.py
v6(2026-11-01): **カチッとはめる爪**。ほぞを真ん中のすき間(1.2mm)で左右2本の腕(厚さ 0.8mm)に分け、腕の先の爪を基板の上の面に引っかける。
               爪は基板の穴の縁から 0.10mm 出る(長さ 2.0mm、先は斜め 0.6mm)。腕の外側にすき間(0.5mm)をホルダの中へ 1.2mm 切り込み、腕を長くしてしならせる。
               差し込むと腕が内へしなり、基板の上へ抜けたところで爪が開いて止まる。外すときは基板の上から2本の爪をつまむ。爪は基板の上へ 0.6mm 出る
v7(2026-11-01): **爪・リブをやめ、v4 と同じまっすぐなほぞ 3.0 × 3.0mm に戻した**。基板の穴も 3.0 × 3.0mm(すき間なし、基板 v19)にしたので、
               差すときつめに入る。基板の穴の角は削る刃で R0.5 になるので、ほぞの縦の角を R0.4 → R0.6 にして角で当たらないようにした
座標 [mm]: 原点は前の面(光が出る面)の真ん中で、基板に付ける面。+y が光の向き、x は幅、+z は基板から離れる向き
(基板の裏に付けるので、機体では下向き)。ほぞは −z 側(基板の穴に入る)。
使い方(このフォルダで): python3 sensor_holder.py  → sensor_holder_v2.step / .stl / .png
"""
import os, math
import cadquery as cq

P = dict(
    w=6.0, d=4.04, h=10.5,          # v8(2026-11-11): カーボン 0.8mm でフレームの上の面が z 2.8 に下がったので 10.3 → 10.5(下の端 z 3.1、フレームとのすき間 0.3mm は同じ)。 幅、奥行き(前の面から後ろの面まで)、基板の面からの高さ(v3。v2 は 9.9、v1・ToraNeko は 10.5)
    hole_d=3.2,                     # 発光・受光を入れる穴(ToraNeko と同じ。φ3 の T-1 が入る)
    z_emit=7.6, z_recv=3.2,         # 穴の中心の基板の面からの距離。遠い方が発光、近い方が受光(ToraNeko と同じ並び。v1・ToraNeko は 8.1・3.5)
    r_front=0.0, r_top_front=0.0, r_top_side=0.0,   # 角の丸み: 前の縦の辺、前の端(基板から遠い所)の辺、端の横の辺。v4 はすべて角(v3 までは 1.6・1.6・1.0)
    peg_w=3.0, peg_d=3.0, peg_back=0.0, peg_t=0.6, peg_r=0.6,   # ほぞ: 幅、奥行き、後ろの面からのずれ、長さ(基板の厚さ)、縦の角の丸み
    rib_span=None, rib_w=0.3, rib_lead=0.2,     # v5 のつぶし用リブ(v7 は使わない)
    snap=None, snap_v6=dict(gap=1.2, arm_t=0.8, relief_w=0.5, relief_h=1.2, pcb_t=0.6, catch_clr=0.03, lip=0.6, hook=0.10, hook_len=2.0, slot_half=1.6),
    # v6: 爪のほぞ。真ん中のすき間、腕の厚さ、腕の外側の切り込みの幅と深さ(ホルダの中へ)、基板の厚さ、爪と基板のすき間、爪の斜めの長さ、
    #     爪が基板の穴の縁(半径 slot_half)から出る長さ、爪の長さ(y。基板の穴の角 R0.5 をよける)   # v5: ほぞの4つの面のつぶし用リブ。リブの先どうしの幅(基板の穴 3.2 より 0.05 きつい)、リブの幅、先の面取りの長さ
    foot_l=0.0, foot_t=1.0, foot_r=1.0,    # v3: 下の端から後ろへ出す足の長さ、厚さ、後ろの角の丸み(v4 はなし)
    base_d=0.0, base_z=5.0, base_r=0.5,    # (使わない。2026-11-01 の最初の v4 案: 基板から base_z より下を、後ろへ base_d 厚くする)
)
VER = 'v8'
MOUNT = 'bottom'     # 基板の裏に付ける(2026-10-30)

def holder(P=P):
    w, d, h = P['w'], P['d'], P['h']
    body = cq.Workplane('XY').box(w, d, h, centered=(True, False, False)).translate((0, -d, 0))
    if P['r_front']:
        body = body.edges('|Z and >Y').fillet(P['r_front'])                  # 前の縦の辺
    if P['r_top_front']:
        body = body.edges('>Z and >Y').fillet(P['r_top_front'] - 0.01)       # 前の上の辺
    if P['r_top_side']:
        try:
            body = body.edges('>Z and |Y').fillet(P['r_top_side'])           # 上の横の辺(後ろ側)
        except Exception:
            pass
    if P.get('base_d'):     # v4: 下の方を後ろへ太くして、そのまま下まで伸ばす
        bd = P['base_d']
        base = (cq.Workplane('XY').box(w, bd + 0.5, h - P['base_z'], centered=(True, False, False))
                .translate((0, -d - bd, P['base_z'])).edges('|Z and <Y').fillet(P['base_r']))
        body = body.union(base)
        d = d + bd          # 穴を後ろまで通す
    for z in (P['z_emit'], P['z_recv']):
        body = body.cut(cq.Workplane('XZ').circle(P['hole_d'] / 2).extrude(d + 2, both=True).translate((0, -d / 2, z)))
    if P.get('foot_l'):     # 下の端(基板から遠い所)から後ろへ足を出す。フレームに当てる面を広げる
        foot = (cq.Workplane('XY').box(w, P['foot_l'] + 0.5, P['foot_t'], centered=(True, False, False))
                .translate((0, -d - P['foot_l'], h - P['foot_t'])).edges('|Z and <Y').fillet(P['foot_r']))
        body = body.union(foot)
    y1 = -d + P['peg_back']
    if P.get('snap'):
        return snap_peg(body, y1, P)
    peg = peg_shape(P).translate((0, y1, 0))
    return body.union(peg)

def snap_peg(body, y1, P=P):
    """v6: ほぞを真ん中で2本の腕に分け、腕の先の爪で基板の上の面に引っかける(カチッとはめる)。
    腕は左右(x)。後ろには発光・受光の足のパッドがあるので爪は付けない。
    腕を長くしてしなりやすくするため、腕の外側のすき間をホルダの中まで切り込む(z relief_h まで)"""
    S = P['snap']
    g, t, rw, rh = S['gap'] / 2, S['arm_t'], S['relief_w'], S['relief_h']
    pcb, clr, lip, hook, hl = S['pcb_t'], S['catch_clr'], S['lip'], S['hook'], S['hook_len']
    d = P['peg_d']
    z_tip = -(pcb + clr + lip)
    for sx in (1, -1):
        x0, x1 = sorted((sx * g, sx * (g + t)))
        body = body.union(cq.Workplane('XY').box(x1 - x0, d, -z_tip, centered=False).translate((x0, y1, z_tip)))     # 腕
        # 爪: 引っかかる面は基板の上の面(z -pcb)の clr 外、そこから先へ斜め(差し込むときに腕が内へしなる)
        xo = sx * (g + t)
        prof = [(xo, -(pcb + clr)), (xo + sx * (S['slot_half'] + hook - (g + t)), -(pcb + clr)), (xo, z_tip)]
        claw = cq.Workplane('XZ').polyline(prof).close().extrude(-hl).translate((0, y1 + (d - hl) / 2, 0))
        body = body.union(claw)
        rx0, rx1 = sorted((sx * (g + t), sx * (g + t + rw)))
        body = body.cut(cq.Workplane('XY').box(rx1 - rx0, d + 0.02, rh, centered=False).translate((rx0, y1 - 0.01, 0)))   # 腕の外側の切り込み
    body = body.cut(cq.Workplane('XY').box(2 * g, d + 0.02, rh - z_tip + 0.01, centered=False).translate((-g, y1 - 0.01, z_tip - 0.01)))   # 真ん中のすき間
    return body

def peg_shape(P=P, span=None):
    """ほぞ(後ろの端 y 0、z 0 から -peg_t)。v5 から4つの面の真ん中に、つぶし用のリブ(先に面取り)"""
    w, d, t = P['peg_w'], P['peg_d'], P['peg_t']
    peg = cq.Workplane('XY').box(w, d, t, centered=(True, False, False)).translate((0, 0, -t)).edges('|Z').fillet(P['peg_r'])
    span = P.get('rib_span') if span is None else span
    if not span:
        return peg
    for (cx, cy, ang, half) in ((w / 2, d / 2, 0, w / 2), (-w / 2, d / 2, 180, w / 2), (0, d, 90, d / 2), (0, 0, 270, d / 2)):
        h = span / 2 - half               # 面から出る高さ
        lead = P['rib_lead']
        prof = [(0, 0), (h, 0), (h, -(t - lead)), (0, -t)]     # (外向き, z)。先(z -t)に向かって面取り
        rib = (cq.Workplane('XZ').polyline([(-0.01, 0)] + prof[1:] + [(-0.01, -t)]).close()
               .extrude(P['rib_w'] / 2, both=True).rotate((0, 0, 0), (0, 0, 1), ang).translate((cx, cy, 0)))
        peg = peg.union(rib)
    return peg

def footprint_info(P=P):
    """基板の側に要るもの(ホルダの座標): ほぞの穴の中心と大きさ"""
    return dict(peg_center=(0.0, -P['d'] + P['peg_back'] + P['peg_d'] / 2), peg_size=(P['peg_w'], P['peg_d']))

if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    s = holder()
    cq.exporters.export(s, os.path.join(here, f'sensor_holder_{VER}.step'))
    cq.exporters.export(s, os.path.join(here, f'sensor_holder_{VER}.stl'), tolerance=0.01, angularTolerance=0.1)
    v = s.val().Volume()
    print(f'体積 {v:.1f} mm³、光造形の樹脂(1.15 g/cm³)で {v * 1.15e-3:.3f} g')
    # 図: 斜め・前・横・上
    import numpy as np
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    vs, ts = s.val().tessellate(0.01, 0.15)
    V_ = np.array([[p.x, p.y, p.z] for p in vs]); T = V_[np.array(ts)]
    nrm = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); nrm /= np.linalg.norm(nrm, axis=1)[:, None] + 1e-12
    fig = plt.figure(figsize=(14, 4.2))
    for i, (el, az, tt) in enumerate([(25, -60, 'front (light goes +y)'), (25, 120, 'back (leads come out here)'), (0, -90, 'side'), (90, -90, 'top')]):
        ax = fig.add_subplot(1, 4, i + 1, projection='3d')
        sh = 0.35 + 0.65 * np.clip(nrm @ np.array([0.4, -0.6, 0.7]), 0, 1)
        ax.add_collection3d(Poly3DCollection(T, facecolor=np.c_[0.6 * sh, 0.6 * sh, 0.65 * sh, np.ones_like(sh)], edgecolor='none'))
        ax.set_xlim(-4, 4); ax.set_ylim(-9, 2); ax.set_zlim(-1, 11); ax.set_box_aspect((8, 11, 12)); ax.view_init(el, az); ax.set_title(tt, fontsize=9)
        ax.set_xticks([-3, 0, 3]); ax.set_yticks([-4, 0]); ax.set_zticks([0, P['z_recv'], P['z_emit'], P['h']])
    fig.suptitle(f'MK4 wall sensor holder {VER}: {P["w"]} x {P["d"]} x {P["h"]} mm, holes phi{P["hole_d"]} at {P["z_recv"]} (receiver) / {P["z_emit"]} (emitter) from the board. '
                 'Mounted upside down under the board (z here = distance below the board)', fontsize=9)
    fig.tight_layout(); fig.savefig(os.path.join(here, f'sensor_holder_{VER}.png'), dpi=90)

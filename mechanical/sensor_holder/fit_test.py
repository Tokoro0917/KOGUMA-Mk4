"""壁センサのホルダの爪のほぞ(v6)の合わせ用の試し片(2026-11-01)。
板(30 × 8 × 2.0mm)の上に、ホルダ v6 と同じ爪のほぞを5本並べる。爪が基板の穴の縁から出る長さを 0.06・0.08・0.10・0.12・0.14mm にし、
手前の縁の切り欠きの数(1〜5)で見分ける。基板が届いたら穴(3.2 × 3.2mm)に下から差し、
「カチッと止まり、割れず、軽くつまむと外せる」ものを選び、sensor_holder.py の snap の hook をその値にする。
使い方(このフォルダで): python3 fit_test.py → sensor_holder_fit_test.step / .stl
"""
import os
import cadquery as cq
import sensor_holder as sh
HOOKS = [0.06, 0.08, 0.10, 0.12, 0.14]
PITCH, T = 6.0, 2.0
if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    W = PITCH * len(HOOKS)
    plate = cq.Workplane().box(W, 8.0, T, centered=(False, False, False))     # z 0〜T(T は腕の切り込み 1.2mm より厚く)
    body = plate.rotate((0, 0, 0), (1, 0, 0), 180).translate((0, 8.0, T))       # 板の下の面を z 0 に(ほぞは -z へ)
    body = cq.Workplane().box(W, 8.0, T, centered=(False, False, False))
    for i, h in enumerate(HOOKS):
        cx = PITCH * (i + 0.5)
        P = dict(sh.P, snap=dict(sh.P['snap'], hook=h))
        blk = cq.Workplane('XY').box(4.4, 4.0, T, centered=(True, False, False))      # ほぞのまわりの台(ホルダの代わり)
        blk = sh.snap_peg(blk, 0.0, dict(P, peg_d=3.0))                               # 台の下の面 z 0 から下へ爪のほぞ
        blk = blk.rotate((0, 0, 0), (1, 0, 0), 180).translate((cx, 2.0 + 3.0, T))     # 上向きにして板の上へ
        body = body.union(blk)
        for k in range(i + 1):
            body = body.cut(cq.Workplane().box(0.5, 0.8, T + 0.2, centered=(True, False, False)).translate((cx - (i * 0.45) + k * 0.9, -0.01, -0.1)))
    v = body.val().Volume()
    print(f'試し片: {W:.0f} × 8 × {T}mm + 爪のほぞ5本(爪 {HOOKS} mm)、体積 {v:.0f} mm³(約 {v * 1.15e-3:.2f} g)、正しい形 {body.val().isValid()}')
    cq.exporters.export(body, os.path.join(here, 'sensor_holder_fit_test.step'))
    cq.exporters.export(body, os.path.join(here, 'sensor_holder_fit_test.stl'), tolerance=0.01, angularTolerance=0.1)

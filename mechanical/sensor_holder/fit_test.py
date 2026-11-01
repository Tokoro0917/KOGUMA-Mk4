"""壁センサのホルダのほぞの合わせ用の試し片(2026-11-01)。
板(30 × 7 × 1.0mm)の上に、ホルダ v5 と同じほぞ(3.0 × 3.0 × 0.6mm、4つの面につぶし用のリブ)を5本並べる。
リブの先どうしの幅を 3.15・3.20・3.25・3.30・3.35mm にし、手前の縁の切り欠きの数(1〜5)で見分ける。
基板が届いたら、ほぞの穴(3.2 × 3.2mm)に差して、手で押して入り、逆さにしても落ちないものを選び、sensor_holder.py の rib_span をその値にする。
使い方(このフォルダで): python3 fit_test.py → sensor_holder_fit_test.step / .stl
"""
import os
import cadquery as cq
import sensor_holder as sh
SPANS = [3.15, 3.20, 3.25, 3.30, 3.35]
PITCH, T = 6.0, 1.0
if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    n = len(SPANS); W = PITCH * n
    body = cq.Workplane().box(W, 7.0, T, centered=(False, False, False))
    for i, s in enumerate(SPANS):
        cx = PITCH * (i + 0.5)
        peg = sh.peg_shape(span=s).rotate((0, 0, 0), (1, 0, 0), 180).translate((cx, 2.0 + sh.P['peg_d'], T))   # 上向き(先が +z)
        body = body.union(peg)
        for k in range(i + 1):        # 見分け用の切り欠き(手前の縁、1〜5個)
            body = body.cut(cq.Workplane().box(0.5, 0.8, T + 0.2, centered=(True, False, False)).translate((cx - (i * 0.45) + k * 0.9, -0.01, -0.1)))
    v = body.val().Volume()
    print(f'試し片: {W:.0f} × 7 × {T}mm + ほぞ5本(リブの先 {SPANS})、体積 {v:.0f} mm³(約 {v * 1.15e-3:.2f} g)')
    cq.exporters.export(body, os.path.join(here, 'sensor_holder_fit_test.step'))
    cq.exporters.export(body, os.path.join(here, 'sensor_holder_fit_test.stl'), tolerance=0.01, angularTolerance=0.1)

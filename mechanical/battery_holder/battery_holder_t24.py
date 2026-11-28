"""タイヤ24mm 用の電池のホルダ(t24v1、2026-11-21、ブランチ claude/trusting-dirac-1tdt54)。battery_holder.py の holder() を使う。
  - ねじ(基板の柱)が (8, ±19.5)・(-21, ±19.5) に移ったので、横の壁を耳の中心まで伸ばしてつなぐ(後ろの耳は電池の後ろの端から離れた)
  - 車軸の所(|x| ≤ 4.6)の横の壁を、基板の上面から 3.6mm(z 17.8)まで切る: エンコーダ基板(x ±3.0、|y| 16.9〜17.5、z 17.5 まで)と、
    基板の上へ出るマウントの軸受の受け(x ±4.3、|y| ≥ 16.9、z 16.0 まで)を避ける。その上(z 17.8〜19.2、1.4mm)は橋として残し、前後の壁を1つにつなぐ
  - 壁の高さは 4.0 → 5.0mm(橋の厚さを取るため。電池は 14mm)
使い方(リポジトリの一番上で): python3 mechanical/battery_holder/battery_holder_t24.py → battery_holder_L_t24v1.* / _R_t24v1.*"""
import os, sys
import cadquery as cq
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '../vehicle'))
import pcb_t24            # design.py・pcb_shape.py をタイヤ24mm に(SCREWS が新しい位置になる)
import battery_holder as bh

P = dict(bh.P, reach_ears=True, wall_gap=4.6, bridge_z=3.6, h=5.0)
VER = 't24v1'
if __name__ == '__main__':
    for sy, nm in ((1, 'L'), (-1, 'R')):
        s = bh.holder(sy, P)
        cq.exporters.export(s, os.path.join(HERE, f'battery_holder_{nm}_{VER}.step'))
        cq.exporters.export(s, os.path.join(HERE, f'battery_holder_{nm}_{VER}.stl'), tolerance=0.01, angularTolerance=0.1)
        v = s.val().Volume(); bb = s.val().BoundingBox()
        print(f'{nm}: 体積 {v:.1f} mm³、{v * 1.15e-3:.3f} g、x {bb.xmin:.2f}〜{bb.xmax:.2f}、y {bb.ymin:.2f}〜{bb.ymax:.2f}、{len(s.val().Solids())} 個の塊')

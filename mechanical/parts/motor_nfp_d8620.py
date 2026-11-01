"""NFP-D8620(φ8.6 × 20mm コアレス)の簡単な形。販売ページの外形図の値(docs/spec.md「モーター」):
本体 φ8.6 × 20.0、前の面に軸受けの出っ張り φ2.4 × 0.3、軸 φ1.2 × 5.1(前の面から)。後ろの端子・リード線は入れていない。
出力: NFP-D8620_v1.step(部品の座標: 前の面が z 0、本体は z −20〜0、軸は +z)、
      NFP-D8620_R_v1.step / _L_v1.step(機体の位置: 右は中心 (−8.07, y, 8.21)、前の面 y −25.0 で軸は外(−y)向き)
"""
import os, sys
import cadquery as cq
HERE = os.path.dirname(os.path.abspath(__file__))
D, L, BOSS_D, BOSS_L, SHAFT_D, SHAFT_L = 8.6, 20.0, 2.4, 0.3, 1.2, 5.1

def motor():
    body = cq.Workplane().circle(D / 2).extrude(-L)
    body = body.union(cq.Workplane().circle(BOSS_D / 2).extrude(BOSS_L))
    return body.union(cq.Workplane().circle(SHAFT_D / 2).extrude(SHAFT_L))

if __name__ == '__main__':
    sys.path.insert(0, os.path.join(HERE, '../motor_mount'))
    import mount2 as mm
    m = motor()
    cq.exporters.export(m, os.path.join(HERE, 'NFP-D8620_v1.step'))
    mx, mz = mm.motor_center()
    R = m.rotate((0, 0, 0), (1, 0, 0), 90).translate((mx, mm.P['motor_face'], mz))     # +z → −y(外向き)
    b = R.val().BoundingBox()
    print(f'右: x {b.xmin:.2f}〜{b.xmax:.2f}、y {b.ymin:.2f}〜{b.ymax:.2f}、z {b.zmin:.2f}〜{b.zmax:.2f}')
    cq.exporters.export(R, os.path.join(HERE, 'NFP-D8620_R_v1.step'))
    cq.exporters.export(R.mirror('XZ'), os.path.join(HERE, 'NFP-D8620_L_v1.step'))

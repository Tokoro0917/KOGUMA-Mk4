"""MK4 のタイヤ(ミニッツのタイヤ φ15 の仮の形)。CadQuery。
ToraNeko.Mk3 のタイヤ(φ14、内径 φ11.5、幅 3.5mm、外の角 R0.5)と同じ形で、外径だけ φ15 にした。
座標は機体と同じ(右: 車軸 (0, y, 7.5)、y −31.8〜−28.3)。左は y を反転。
実物が届いたら内径・外径・幅を測り、P を直す(ホイールの外径 φ11.5 も合わせて確かめる)。
使い方(このフォルダで): python3 tire.py → tire_R_v1.step/.stl、tire_L_v1.step/.stl
"""
import os
import cadquery as cq
P = dict(od=15.0, id=11.5, w=3.5, y_out=-31.8, axle_z=7.5, r_edge=0.5)
VER = 'v1'

def tire(P=P):
    t = (cq.Workplane('XZ').circle(P['od'] / 2).circle(P['id'] / 2).extrude(-P['w'])
         .faces('<Y or >Y').edges('%CIRCLE').edges(cq.selectors.RadiusNthSelector(1)).fillet(P['r_edge']))
    return t.translate((0, P['y_out'], P['axle_z']))

if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    R = tire(); L = R.mirror('XZ')
    b = R.val().BoundingBox()
    print(f'タイヤ {VER}: 外径 {b.xlen:.2f}、幅 {b.ylen:.2f}、y {b.ymin:.2f}〜{b.ymax:.2f}、体積 {R.val().Volume():.0f} mm³(ゴム 1.2 g/cm³ で {R.val().Volume() * 1.2e-3:.2f} g)')
    for nm, s in (('R', R), ('L', L)):
        cq.exporters.export(s, os.path.join(here, f'tire_{nm}_{VER}.step'))
        cq.exporters.export(s, os.path.join(here, f'tire_{nm}_{VER}.stl'), tolerance=0.01, angularTolerance=0.1)

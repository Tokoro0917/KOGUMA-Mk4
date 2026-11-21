"""タイヤ24mm 用のメイン基板の外形(t24v1、2026-11-21、ブランチ claude/trusting-dirac-1tdt54)。
main の外形(pcb_shape.py v17)を、タイヤ24mm の並びに合わせて変える:
  - マウントの柱(ねじの穴)を (8, ±19.5)・(-21, ±19.5) に(docs/calc/frame/t24.py が design.py の MOUNT_SCREWS を変え、pcb_shape.SCREWS がそれを読む)
  - 車輪(タイヤ・71T)の所を x ±12.2、|y| > 22.3 で切り欠く(main は x -8〜8.5、|y| > 25)。タイヤは z 24 まで、71T は z 22.95 まで来る(基板の高さ z 13.6〜14.2 では x ±11.89 まで)
  - 前の壁センサ FL・FR は (20.8, ±30.35)(docs/calc/frame/t24.py が pcb_shape.SENS を書き換える)
  - 車軸のまわり(軸受の受け・MT6835・エンコーダ基板が基板の上へ出る所)を x ±4.5、|y| > 16.7 で切り欠く。切り欠きの角は R1
  - エンコーダ基板は切り欠きの縁(|y| 16.9〜17.5)に沿って立て、基板の上の面ではんだ付けする。そのパッドの所(x ±3.0、|y| 16.1〜16.7)のまわりに縁を残す
使い方(リポジトリの一番上で): python3 mechanical/vehicle/pcb_t24.py → mechanical/pcb/pcb_outline_t24v1.dxf・.png"""
import os, sys, runpy
from shapely.geometry import box
from shapely.ops import unary_union
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '../../docs/calc/frame'))
import t24                     # design.py の定数をタイヤ24mm に(先に読む)
sys.path.insert(0, HERE)
import pcb_shape as ps

ps.VER = 't24v1'
ps.WHEEL_CUT = (-12.2, 12.5, 22.3)           # x0, x1(実際は x1 - 0.3 まで), |y| y0。タイヤは基板の高さで x ±11.89 まで(2026-11-21 に ±12.5 から。前の壁センサの足の穴のため)
ps.ENC = [(-3.0, 3.0, -16.7, -16.1), (-3.0, 3.0, 16.1, 16.7)]   # エンコーダ基板をはんだ付けするパッドの所(基板の上の面)
AXLE_CUT = (4.5, 16.7)                       # 車軸のまわり: |x| ≤ 4.5 で |y| > 16.7
CUT_R = 1.0
_outline_main = ps.outline

def outline():
    o = _outline_main()
    xa, ya = AXLE_CUT
    cuts = unary_union([box(-xa, ya, xa, 60), box(-xa, -60, xa, -ya)]).buffer(-CUT_R).buffer(CUT_R)
    return o.difference(cuts)
ps.outline = outline

if __name__ == '__main__':
    os.chdir(os.path.join(HERE, '../..'))
    sys.argv = ['pcb_dxf.py']
    runpy.run_path(os.path.join(HERE, 'pcb_dxf.py'), run_name='__main__')
    b = ps.board()
    print('ねじの穴', ps.SCREWS)
    print(f'面積 {b.area:.0f} mm²(main v17 は約 3,110mm²)')

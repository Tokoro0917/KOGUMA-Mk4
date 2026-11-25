"""タイヤ24mm 用のメイン基板の外形(t24v3、2026-11-22、ブランチ claude/trusting-dirac-1tdt54)。形は outline() の説明(案1)。
実装する面積を取るため、main の v11 の形(後ろの長方形、前と横のセンサの間のポケットなし)をもとにし(2026-11-22、B 案。t24v1 は v16 の形で 2,784mm²)、タイヤ24mm の並びに合わせて変える:
  - マウントの柱(ねじの穴)を (8, ±19.5)・(-21, ±19.5) に(docs/calc/frame/t24.py が design.py の MOUNT_SCREWS を変え、pcb_shape.SCREWS がそれを読む)
  - 車輪(タイヤ・71T)の所を x ±12.2、|y| > 22.3 で切り欠く(main は x -8〜8.5、|y| > 25)。タイヤは z 24 まで、71T は z 22.95 まで来る(基板の高さ z 13.6〜14.2 では x ±11.89 まで)
  - 前の壁センサ FL・FR は (20.8, ±30.35)(docs/calc/frame/t24.py が pcb_shape.SENS を書き換える)
  - 車軸のまわり(軸受の受け・MT6835・エンコーダ基板が基板の上へ出る所)を x ±4.5、|y| > 16.7 で切り欠く。切り欠きの角は R1
  - エンコーダ基板は切り欠きの縁(|y| 16.9〜17.5)に沿って立て、基板の上の面ではんだ付けする。そのパッドの所(x ±3.0、|y| 16.1〜16.7)のまわりに縁を残す
使い方(リポジトリの一番上で): python3 mechanical/vehicle/pcb_t24.py → mechanical/pcb/pcb_outline_t24v3.dxf・.png"""
import os, sys, runpy
from shapely.geometry import box
from shapely.ops import unary_union
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '../../docs/calc/frame'))
import t24                     # design.py の定数をタイヤ24mm に(先に読む)
sys.path.insert(0, HERE)
import pcb_shape as ps

ps.VER = 't24v10'    # 2026-11-24(t24v10): ファンの上の穴を φ14 → φ20(下の HUB_HOLE)。t24v9 2026-11-24: エンコーダ基板の左右をはめ込む切り込み(幅 6.0mm)。t24v8: 車軸のまわりの切り欠きの縁をエンコーダ基板にぴったり(|y| 16.7 → 16.9)。t24v7: ホルダのほぞの穴を 3.0 × 3.0mm の角のままに(ToraNeko.Mk3 と同じ)。t24v6(2026-11-23): マウントのねじを (6.8, ±18.4)・(-21, ±18.4) にそろえた(マウント t24v5)。t24v5: (-21, ±17.7)。t24v4: (6.8, ±18.9)・(-21, ±18.9)(frame t24v4、吸引する面 80 × 42.6mm)。t24v3(2026-11-22): 案1。B 案(v11 の広さ)に、後ろの V 字の切り欠き・羽と、角の丸み(v16 と同じ考え方)。t24v2 は B 案のまま(3,432mm²)、t24v1 は v16 の形(2,784mm²)
ps.WHEEL_CUT = (-12.2, 12.5, 22.3)           # x0, x1(実際は x1 - 0.3 まで), |y| y0。タイヤは基板の高さで x ±11.89 まで(2026-11-21 に ±12.5 から。前の壁センサの足の穴のため)
ps.ENC = [(-3.0, 3.0, -16.9, -16.3), (-3.0, 3.0, 16.3, 16.9)]   # エンコーダ基板をはんだ付けするパッドの所(基板の上の面と裏の面。2026-11-25 から両方)。t24v8(2026-11-24): 0.2mm 外へ(エンコーダ基板とのすき間 0)
ps.SLOT_CLR, ps.SLOT_R = 0.0, 0.0          # t24v7(2026-11-24): ホルダのほぞの穴を 3.0 × 3.0mm の角のまま・すき間なしに(ToraNeko.Mk3 と同じ。t24v6 までは 3.2 × 3.2mm・角 R0.5)
# 2026-11-24(t24v10、ユーザー: ファンの上も肉抜きの対象): ファンの空気は羽の先と輪のすき間から上へ出て、基板の穴へ抜ける(docs/calc/fan_cfd は φ26 で計算)。
# 基板はふたではないので、ハブの穴を半径 7 → 10(φ20)に広げる。φ22 以上はマイコンのパスコン(C62)・IMU などにかかる
ps.HUB_HOLE = 10.0
# 2026-11-24(ユーザー: 電源スイッチを後ろに置きたい): 後ろの V 字の先のモードの LED 3個を 3.5mm 前へ。あいた後ろの真ん中(V 字の切り欠きの先の縁)に
# 電源スイッチ SW1 を置き、つまみを後ろへ出す。基板の外形(LED_APEX)は変えない。左右の角の LED 4個はそのまま
ps.LEDS = [ps.LEDS[0], ps.LEDS[1], (ps.LEDS[2][0] + 3.5, ps.LEDS[2][1]), (ps.LEDS[3][0] + 3.5, ps.LEDS[3][1]), (ps.LEDS[4][0] + 3.5, ps.LEDS[4][1]), ps.LEDS[5], ps.LEDS[6]]
# 2026-11-25(ユーザー: 決定のスイッチ SW2 を後ろへ。後ろの右の角に置く): 左右の角の LED 2個ずつを、縁に沿って1つ分(約 1.9mm)内側へ。
# 右は No.1(D93)が No.2(D94)のあった所、No.2 がその内側。あいた右の角に SW2 を置く。左(No.8・No.4)も左右でそろえて同じだけ内側へ。
# 並び(左から No.8・No.4・モード・No.2・No.1)は変えない。内側の2個(No.4・No.2)は縁が V 字へ入りはじめるので、0.3mm 前(x −27.85)
_CORNER = ps.LEDS
ps.LEDS = [_CORNER[1], (-27.85, 12.37), _CORNER[2], _CORNER[3], _CORNER[4], (-27.85, -12.46), _CORNER[5]]
AXLE_CUT = (4.5, 17.5)                       # 車軸のまわり: |x| ≤ 4.5 で |y| > 17.5(t24v9: エンコーダ基板の外の面から外。t24v8 は 16.9、t24v7 までは 16.7)
ENC_NOTCH = (3.0, 16.9, 17.5)                # t24v9(2026-11-24): エンコーダ基板をはめ込む切り込み: |x| ≤ 3.0(基板の幅 6.0mm と同じ)、|y| 16.9〜17.5(基板の厚さ)。
                                             # 左右(|x| 3.0〜4.5)に残した基板が、エンコーダ基板の端を挟む(ユーザー)。作る誤差は見込まない
CUT_R = 1.0
_outline_main = ps.outline_v11      # t24v2(B 案): v11 の形(後ろの長方形・ポケットなし)。t24v1 は ps.outline(v16)

def outline_t24v2():
    """B 案: v11 の形 + 車軸のまわりの切り欠き"""
    o = _outline_main()
    xa, ya = AXLE_CUT
    cuts = unary_union([box(-xa, ya, xa, 60), box(-xa, -60, xa, -ya)]).buffer(-CUT_R).buffer(CUT_R)
    return o.difference(cuts)

R_IN, R_OUT, R_CUT = 10.0, 3.0, 3.0      # へこんだ角、出っ張った角、切り欠きの端の出っ張った角
WING_Y = 23.0                             # 後ろの羽の外(main v15・v16 は 18.5。後ろの柱 (-21, ±19.5) のため)
def outline():
    """t24v3(案1、2026-11-22、docs/calc/t24_pcb_design.py の 'V'): v11 の形(切り欠く前)の後ろを ToraNeko.Mk3 と同じ V 字に切り欠き、
    羽の外を |y| WING_Y で切り、へこんだ角 R_IN・出っ張った角 R_OUT で丸め、壁センサの所はフレームの 0.3mm 内側まで残してから、
    タイヤ・車軸の切り欠き(角 R1)とハブの穴を開け、切り欠きでできた出っ張った角を R_CUT で丸める(柱・エンコーダのパッド・センサの所は残す)"""
    from shapely.geometry import Polygon, Point
    keep_wc = ps.WHEEL_CUT
    ps.WHEEL_CUT = (0.0, 0.0, 99.0)
    o = ps.outline_v11()
    ps.WHEEL_CUT = keep_wc
    o = unary_union([Polygon(p.exterior) for p in getattr(o, 'geoms', [o])])
    R, (yi, yo) = ps.REAR, ps.LED_WING
    o = o.difference(Polygon([(R - 1, yi), (R, yi), (ps.LED_APEX, 0.0), (R, -yi), (R - 1, -yi)]))
    o = o.difference(box(R - 5, WING_Y, -16, 40)).difference(box(R - 5, -40, -16, -WING_Y))
    frame = ps.dz.outline(0)
    o = o.intersection(frame.buffer(-ps.FRAME_MARGIN, join_style=2))
    o = o.buffer(R_IN, join_style=1).buffer(-R_IN, join_style=1).buffer(-R_OUT, join_style=1).buffer(R_OUT, join_style=1)
    o = unary_union([o] + [ps.footprint(k, 1.0).intersection(frame.buffer(-0.3, join_style=2)) for k in ps.SENS])
    x0, x1, y0 = ps.WHEEL_CUT
    xa, ya = AXLE_CUT
    c = unary_union([box(x0, y0, x1 - 0.3, 60), box(x0, -60, x1 - 0.3, -y0), box(-xa, ya, xa, 60), box(-xa, -60, xa, -ya)]).buffer(-CUT_R).buffer(CUT_R)
    o = o.difference(c).difference(Point(ps.FAN).buffer(ps.HUB_HOLE, 64))
    xn, yn0, yn1 = ENC_NOTCH
    notch = unary_union([box(-xn, yn0, xn, yn1 + 0.01), box(-xn, -yn1 - 0.01, xn, -yn0)])     # 角は丸めない(はめ込むため)
    fingers = unary_union([box(xn, yn0, xa, yn1), box(-xa, yn0, -xn, yn1), box(xn, -yn1, xa, -yn0), box(-xa, -yn1, -xn, -yn0)])   # 切り込みの左右の基板
    keep = unary_union([Point(p).buffer(3.1) for p in ps.SCREWS] + [box(-3.6, 15.6, 3.6, 16.9), box(-3.6, -16.9, 3.6, -15.6)]
                       + [ps.footprint(k, 1.0) for k in ps.SENS]).intersection(o)
    keep = keep.difference(box(-xa, ya, xa, 60)).difference(box(-xa, -60, xa, -ya))     # 柱のまわりを残しても、車軸の切り欠きには入れない(t24v4、前の柱が x 6.8 で切り欠きに近い)
    o = o.buffer(-R_CUT, join_style=1).buffer(R_CUT, join_style=1).union(keep).union(fingers).difference(notch)
    return o.buffer(-0.01).buffer(0.01).simplify(0.002)      # 近すぎる点をまとめる(DXF の円弧にするときに止まるため)
ps.outline = outline

if __name__ == '__main__':
    os.chdir(os.path.join(HERE, '../..'))
    sys.argv = ['pcb_dxf.py']
    runpy.run_path(os.path.join(HERE, 'pcb_dxf.py'), run_name='__main__')
    b = ps.board()
    print('ねじの穴', ps.SCREWS)
    print(f'面積 {b.area:.0f} mm²(main v17 は約 3,110mm²)')

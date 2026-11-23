"""タイヤ24mm の機体(mk4_vehicle_t24.step)から、注文する部品を1つずつ STEP に書き出す(2026-11-23、Fusion で確かめるため)
使い方(このフォルダで): python3 export_t24_parts.py → ../order_t24/NN_名前.step(印刷する部品は .stl も)
座標は機体と同じ(原点は車軸の中心、+x 前、+y 左、z 床から上、mm)。Fusion で全部を原点に挿入すると、組み上がった位置に並ぶ。
機体の STEP の部品の名前は番号なので、番号と部品の対応は下の PARTS(外形の位置で確かめた)。機体を作り直したら番号が変わることがあるので、外形で確かめる"""
import os, sys
import cadquery as cq
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '../order_t24')
src = open(os.path.join(HERE, 'export_part.py')).read()
sys.argv = ['x', os.path.join(HERE, 'mk4_vehicle_t24.step')]
exec(src[:src.index('\n', src.index('walk(l, TopLoc_Location(), name(l))'))])     # parts = {番号: 形}
# (番号, ファイルの名前, 印刷する部品か, 確かめる外形 (xmin, xmax, ymin, ymax))
PARTS = [
    ('1', '01_frame_t24v6', False, (-50.0, 50.0, -35.0, 35.0)),             # フレーム(カーボン 1mm)。注文は MK4FRAMET24V6_T1.dxf
    ('33', '02_pc_sheet_t24v6', False, (-40.0, 40.0, -21.3, 21.3)),         # 塩ビのシート 0.2mm。注文は MK4PCT24V6_T02.dxf
    ('34', '03_motor_mount_R_t24v3', True, (-23.4, 16.5, -22.6, -15.3)),    # モーターマウント 右(Temp Resin)
    ('35', '04_motor_mount_L_t24v3', True, (-23.4, 16.5, 15.3, 22.6)),      # モーターマウント 左
    ('5', '05_fan_mount_t24v2', True, (-3.3, 31.7, -22.8, 22.8)),           # ファンの台(Temp Resin)。継ぎ目 (14, ±20.3)。t24v2: 吸引する面が広がり、輪の下はシートの上(z 3.2)
    ('36', '06_wheel_R_t24v1', True, (-10.0, 10.0, -33.3, -23.2)),          # ホイール 右(Black Resin)
    ('37', '07_wheel_L_t24v1', True, (-10.0, 10.0, 23.2, 33.3)),            # ホイール 左
    ('11', '08_sensor_holder_v5', True, (16.4, 21.2, 26.9, 33.3)),          # 壁センサのホルダ(Black Resin、4個。これは FL の位置)
    ('9', '09_main_pcb_t24v4', False, (-30.0, 45.7, -34.1, 34.1)),          # メイン基板(外形だけ。配線のあとで JLCPCB)
    ('48', '10_encoder_board_R_t24', False, (-3.0, 3.0, -17.5, -16.9)),     # エンコーダ基板 右
]
REF = ['2', '3', '4', '6', '7', '8', '10'] + [str(i) for i in range(12, 33) if i not in (14, 17, 20)] + ['14', '17', '20', '49'] + [str(i) for i in range(38, 48)] + [str(i) for i in range(50, 60)]

def check(s, bb0):
    bb = s.BoundingBox()
    got = (bb.xmin, bb.xmax, bb.ymin, bb.ymax)
    assert all(abs(a - b) < 0.15 for a, b in zip(got, bb0)), (got, bb0)

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for k, fn, printed, bb0 in PARTS:
        s = parts[k]
        check(s, bb0)
        cq.exporters.export(s, os.path.join(OUT, fn + '.step'))
        if printed:
            cq.exporters.export(s, os.path.join(OUT, fn + '.stl'), tolerance=0.01, angularTolerance=0.1)
        bb = s.BoundingBox()
        print(f'{fn}: 体積 {s.Volume():.0f} mm³、x {bb.xmin:.2f}〜{bb.xmax:.2f}、y {bb.ymin:.2f}〜{bb.ymax:.2f}、z {bb.zmin:.2f}〜{bb.zmax:.2f}')
    # 買う部品・ほかの部品(モーター・タイヤ・71T・ピニオン・軸受・ピン・磁石・ねじ・電池・ファンのモーター・羽根・センサ・滑り板・スカート)を1つに
    ref = cq.Compound.makeCompound([parts[k] for k in REF if k in parts])
    cq.exporters.export(ref, os.path.join(OUT, '11_purchased_and_other_parts.step'))
    print('11_purchased_and_other_parts: 部品', len([k for k in REF if k in parts]))

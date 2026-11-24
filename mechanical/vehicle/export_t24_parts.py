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
    # 2026-11-23(frame t24v10): 塩ビのシートがなくなったので、番号を詰めた(t24v9 までは 02 が塩ビのシート)
    ('1', '01_frame_t24v10', False, (-50.0, 50.0, -35.0, 35.0)),            # フレーム(カーボン 0.8mm、吸引する面を埋めた、z 2.0〜2.8)。注文は MK4FRAMET24V10_T08.dxf
    ('33', '02_motor_mount_R_t24v12', True, (-23.0, 16.5, -22.6, -15.3)),    # モーターマウント 右(Temp Resin)。t24v12: 穴の入口の面取りなし(t24v11 はモーターの穴だけ)。t24v10: 辺だけでつながっていた所を直した。t24v9: 角に半径 0.4mm のフィレット。t24v8: モーターの前の面の壁 0.8mm。t24v7: 薄い所を直した(t24v6: 下の端を 0.2mm 伸ばした、z 2.8 から)
    ('34', '03_motor_mount_L_t24v12', True, (-23.0, 16.5, 15.3, 22.6)),      # モーターマウント 左
    ('5', '04_fan_mount_t24v4', True, (-3.3, 31.7, -22.8, 22.8)),           # ファンの台(Temp Resin)。継ぎ目 (14, ±20.3)。t24v4: ハブの底を 0.8mm に。t24v3: 輪の下をフレームの上(z 2.8)まで伸ばした(t24v2 はシートの上 z 3.2)
    ('35', '05_wheel_t24v7', True, (-10.0, 10.0, -33.3, -23.2)),          # ホイール(Black Resin、左右で同じ形。左は 180° 回して付ける。2026-11-24 に確かめた)。t24v7: ピンの穴を 0.2mm 浅く(磁石の面を軸受の面に)。t24v6: 71T の芯出しの段 φ8.05(少しきつめ)。t24v5: φ8.1。t24v4: φ8.0。t24v3: 窓なし・円板 1.2mm・面取りなし。t24v2: 平行ピン 3×8 を 5mm 圧入
    ('11', '06_sensor_holder_v6', True, (16.4, 21.2, 26.9, 33.3)),          # 壁センサのホルダ(Black Resin、4個。これは FL の位置)。下の端 z 3.3 とフレーム(z 2.8)の間 0.5mm に緩衝材
    ('9', '07_main_pcb_t24v9', False, (-30.0, 45.7, -34.1, 34.1)),          # メイン基板(外形だけ。配線のあとで JLCPCB)
    ('47', '08_encoder_board_R_t24', False, (-3.0, 3.0, -17.5, -16.9)),     # エンコーダ基板 右
]
REF = ['2', '3', '4', '6', '7', '8', '10', '36'] + [str(i) for i in range(12, 33) if i not in (14, 17, 20)] + ['14', '17', '20', '48'] + [str(i) for i in range(37, 47)] + [str(i) for i in range(49, 59)]

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
    # 2026-11-24: 走行用モーター 右(NFP-D8620、φ8.6 × 20mm の円柱 + 軸受の出っ張り + 軸 φ1.2)とピニオン 13T。買う部品の確かめる用(形は簡単にした円柱)
    motor = [parts[k] for k in ('41', '43')]
    check(motor[0], (-16.31, -7.71, -21.6, -1.3))
    cq.exporters.export(cq.Compound.makeCompound(motor), os.path.join(OUT, '10_motor_R_NFP-D8620.step'))
    check(parts['45'], (-14.26, -9.76, -24.4, -22.4))
    cq.exporters.export(parts['45'], os.path.join(OUT, '11_pinion_13T_R.step'))
    print('10_motor_R_NFP-D8620・11_pinion_13T_R')
    # 2026-11-24: エンコーダ基板 右に部品を付ける(ユーザー「IC もつけて」)。KiCad の 3D モデルが入っていないので、寸法から作る
    #   MT6835(TSSOP-16、MT6835 Rev1.3 の 13 章): 本体 D 5.0 × E1 4.4 × 厚さ 1.1mm(浮き 0.1mm、全体 A 1.2mm まで)、足 16 本(ピッチ 0.65、幅 0.25、
    #   足の先から先 E 6.4mm、足の厚さ 0.15、先の平らな所 L 0.6)。ピンの列を上下(z)に向け、中心は (x 0, z 12.0)、チップの面(F、y -17.5 から外)
    #   C1(0402、1.0 × 0.5 × 0.5mm): 裏の面(B、y -16.9 から内)、KiCad の (98.725, 105.5) = 機体の (x -1.275, z 11.4)
    enc = [parts['47']]
    check(parts['47'], (-3.0, 3.0, -17.5, -16.9))
    YF, ZC = -17.5, 12.0
    enc.append(cq.Solid.makeBox(5.0, 1.1, 4.4, cq.Vector(-2.5, YF - 1.2, ZC - 2.2)))                 # 本体(y -18.7〜-17.6)
    for k in range(8):
        x = -2.275 + 0.65 * k - 0.125
        for sz in (1, -1):
            z_body = ZC + sz * 2.2
            z_tip = ZC + sz * 3.2
            z0, z1 = sorted((z_body, z_body + sz * 0.4))
            enc.append(cq.Solid.makeBox(0.25, 0.15, z1 - z0, cq.Vector(x, YF - 0.65, z0)))          # 本体から出る所
            z0, z1 = sorted((z_body + sz * 0.4, z_tip))
            enc.append(cq.Solid.makeBox(0.25, 0.15, z1 - z0, cq.Vector(x, YF - 0.15, z0)))          # 基板に付く所
            z0, z1 = sorted((z_body + sz * 0.35, z_body + sz * 0.45))
            enc.append(cq.Solid.makeBox(0.25, 0.5, z1 - z0, cq.Vector(x, YF - 0.65, z0)))           # 曲がる所
    enc.append(cq.Solid.makeBox(1.0, 0.5, 0.5, cq.Vector(-1.775, -16.9, 11.15)))                      # C1(裏)
    cq.exporters.export(cq.Compound.makeCompound(enc), os.path.join(OUT, '08_encoder_board_R_t24.step'))
    print('08_encoder_board_R_t24(MT6835・C1 付き)')
    # 2026-11-24: タイヤ 右(MK3 と同じミニッツのタイヤ。外径 24mm・内径 20mm・幅 8.5mm の輪で簡単に描いた形)
    check(parts['37'], (-12.0, 12.0, -33.3, -24.8))
    cq.exporters.export(parts['37'], os.path.join(OUT, '12_tire_R.step'))
    print('12_tire_R')
    # 買う部品・ほかの部品(モーター・タイヤ・71T・ピニオン・軸受・ピン・磁石・ねじ・電池・ファンのモーター・羽根・センサ・滑り板・スカート)を1つに
    ref = cq.Compound.makeCompound([parts[k] for k in REF if k in parts])
    cq.exporters.export(ref, os.path.join(OUT, '09_purchased_and_other_parts.step'))
    print('09_purchased_and_other_parts: 部品', len([k for k in REF if k in parts]))

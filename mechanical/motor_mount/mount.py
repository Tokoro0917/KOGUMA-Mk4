"""MK4 モーターマウント v1(右側。左側は y を反転)。CadQuery で作る。
座標 [mm]: x 前(+)、y 左(+)、z 上(床 = 0)。車軸 (0, y, 7.5)。右側なので外側が -y。
フレームの上面 z = 3.0。部品の並び(外側から): タイヤ -31.8〜-28.3、41T -28.3〜-26.3、
LF-630 外 -26.7〜-24.7(つばが外)、LF-630 内 -24.5〜-22.5(つばが内)、磁石 -23.7〜-22.7、
AS5047P -22.2〜-21.0、エンコーダ基板 -21.06〜-20.46(ToraNeko.Mk3 と同じ並び)。"""
import math
import cadquery as cq

P = dict(
    frame_top=3.0,
    axle=(0.0, 7.5),                  # (x, z)
    cd=0.15 * (41 + 13),              # 軸間 8.1mm(41T:13T)
    motor_angle=5.0,                  # 車軸の後ろで、水平から上に 5°
    motor_d=8.6, motor_len=20.0, bore_clear=0.1,   # 穴は 8.7mm(接着か軽い圧入)
    motor_face=-25.0,                 # モーターの前の面(軸の側)の y
    lip=0.6,                          # モーターの前の面を受ける壁の厚さ(-25.0〜-25.6)
    lip_hole=3.2,                     # 軸受けの出っ張り(φ2.4)の逃げ
    outer_face=-25.6,                 # マウントの外側の面(ピニオン -25.9 とのすき間 0.3、41T とは 0.7)
    brg_seat_out=-26.1, brg_seat_in=-23.1,   # 軸受の壁(つばが両側に当たる)。外のつばは r3.7 の輪で受ける
    seat_r=3.7,
    brg_od=6.0,
    wall=0.8,                         # モーターの穴のまわりの壁
    axle_wall=1.0,                    # 軸受の穴のまわりの壁
    inner_face=-20.0,                 # マウントの内側の面(エンコーダ基板の溝の内側)
    cradle_end=-15.6,                 # モーターを受ける筒の内側の端(吸引する面に入らない)
    enc_slot=(-21.1, -20.4, 3.05),    # エンコーダ基板の溝: y0, y1, x 方向の半幅
    pocket=(3.8, 3.7, 14.0),          # AS5047P と内側の軸受のつばの逃げ: x 半幅、z0、z1(上は開ける。基板を上から差す)
    screw_front=(7.85, -22.1), screw_rear=(-17.15, -22.1),
    boss_r=3.7, ear_top=7.0, nut_af=5.7, nut_depth=2.5, hole_d=3.2,
)

def motor_center(P):
    a = math.radians(P['motor_angle'])
    return (P['axle'][0] - P['cd'] * math.cos(a), P['axle'][1] + P['cd'] * math.sin(a))

def ycyl(r, y0, y1, x, z):
    """y 方向の円柱(y0 から y1 まで)"""
    lo, hi = min(y0, y1), max(y0, y1)
    return cq.Workplane('XZ', origin=(x, 0, z)).circle(r).extrude(-(hi - lo)).translate((0, lo, 0))

def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane().box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))

def build(P=P):
    mx, mz = motor_center(P)
    ax, az = P['axle']
    ft = P['frame_top']
    rm = P['motor_d'] / 2 + P['bore_clear'] / 2 + P['wall']
    ra = P['brg_od'] / 2 + P['axle_wall']
    y_in, y_out = P['inner_face'], P['outer_face']
    body = (ycyl(ra, P['brg_seat_out'], y_in, ax, az)                       # 軸受のまわり
            .union(box(ax - ra, ax + ra, P['brg_seat_out'], y_in, ft, az))   # その下(フレームまで)
            .union(ycyl(rm, y_out, P['cradle_end'], mx, mz))                 # モーターのまわりの筒
            .union(box(mx - rm, mx + rm, y_out, P['cradle_end'], ft, mz))    # 筒の下(フレームまで)
            .union(box(mx, ax, y_out, y_in, ft, min(mz + rm, az + ra))))     # 2つの穴の間
    # ねじの耳(M3 + ナット)
    for (sx, sy) in (P['screw_front'], P['screw_rear']):
        ear = (cq.Workplane().center(sx, sy).circle(P['boss_r']).extrude(P['ear_top'] - ft).translate((0, 0, ft)))
        body = body.union(ear)
        # 耳とマウントをつなぐ
        x_link0, x_link1 = sorted((sx, ax if sx > 0 else mx))
        body = body.union(box(x_link0, x_link1, sy - P['boss_r'], min(sy + P['boss_r'], y_in), ft, P['ear_top']))
    # ---- 穴 ----
    body = body.cut(ycyl(P['motor_d'] / 2 + P['bore_clear'] / 2, P['motor_face'], P['cradle_end'] + 1, mx, mz))
    body = body.cut(ycyl(P['lip_hole'] / 2, y_out - 1, P['motor_face'] + 0.01, mx, mz))
    body = body.cut(ycyl(P['brg_od'] / 2, P['brg_seat_out'] - 1, P['brg_seat_in'], ax, az))
    px, pz0, pz1 = P['pocket']
    # ポケットは基板の溝の手前まで(基板の裏は壁で受ける)。前側は開ける(薄い壁を残さない)
    body = body.cut(box(ax - px, ax + px + 1.0, P['brg_seat_in'], P['enc_slot'][0], pz0, pz1))
    sy0, sy1, sx = P['enc_slot']
    body = body.cut(box(ax - sx, ax + sx, sy0, sy1, ft - 0.01, 14.0))
    # 外側の面より外に出た所を削る(41T・ピニオンとのすき間)
    body = body.cut(box(-40, 40, -40, y_out, 0, 30).cut(ycyl(P['seat_r'], P['brg_seat_out'], y_out, ax, az)))
    for (sx_, sy_) in (P['screw_front'], P['screw_rear']):
        body = body.cut(cq.Workplane().center(sx_, sy_).circle(P['hole_d'] / 2).extrude(20).translate((0, 0, ft - 1)))
        body = body.cut(cq.Workplane().center(sx_, sy_).polygon(6, P['nut_af'] / math.cos(math.pi / 6))
                        .extrude(P['nut_depth'] + 1).translate((0, 0, P['ear_top'] - P['nut_depth'])))
    return body

if __name__ == '__main__':
    m = build()
    v = m.val().Volume()
    print(f'体積 {v:.0f} mm³、樹脂(1.2 g/cm³)で {v * 1.2e-3:.2f} g、ナイロン PA12(1.01)で {v * 1.01e-3:.2f} g')
    print('外形', m.val().BoundingBox().__dict__ if False else [round(x, 2) for x in (m.val().BoundingBox().xmin, m.val().BoundingBox().xmax, m.val().BoundingBox().ymin, m.val().BoundingBox().ymax, m.val().BoundingBox().zmin, m.val().BoundingBox().zmax)])
    print('モーターの中心', [round(c, 3) for c in motor_center(P)])
    cq.exporters.export(m, 'motor_mount_R_v1.step'); cq.exporters.export(m, 'motor_mount_R_v1.stl')
    cq.exporters.export(m.mirror('XZ'), 'motor_mount_L_v1.step'); cq.exporters.export(m.mirror('XZ'), 'motor_mount_L_v1.stl')

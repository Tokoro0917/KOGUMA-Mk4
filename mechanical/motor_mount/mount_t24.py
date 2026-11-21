"""タイヤ24mm・71T:13T のモーターマウント(t24 v1、2026-11-21。右側、左側は y を反転)。
`mount.py` の build() を、タイヤ24mm の並び(`docs/spec.md` の「方針の変更(2026-11-21)」)のパラメータで使う。
座標 [mm]: x 前(+)、y 左(+)、z 上(床 = 0)。車軸 (0, y, 12.0)。右側なので外側が -y。
部品の並び(外側から、main より 3.5mm 内): タイヤ -33.3〜-24.8、71T -24.8〜-22.8、LF-630 外 -23.2〜-21.2、内 -21.0〜-19.0、
磁石 -20.2〜-19.2、MT6835 -18.7〜-17.5、エンコーダ基板 -17.5〜-16.9。メイン基板の下面 z 13.6。
使い方: python3 mount_t24.py → motor_mount_R_t24v1.step/.stl、motor_mount_L_t24v1.step/.stl"""
import math
import cadquery as cq
import mount as mm

FRAME_TOP = 3.0
PCB_BOTTOM = 13.6
AXLE_Z = 12.0
CD = 0.15 * (71 + 13)          # 軸間 12.6mm
WALL = 0.9                     # モーターの筒の壁(main v8 と同じ)
# モーターの中心の高さ: 筒の下の壁がフレームの上面(3.0)に載り、筒の上がメイン基板の下面から 0.25mm 下になる所
MOTOR_Z = 8.2                  # 筒 z 3.05〜13.35、モーター z 3.9〜12.5
MOTOR_ANGLE = -math.degrees(math.asin((AXLE_Z - MOTOR_Z) / CD))   # 水平から 17.55° 下

P = dict(mm.P)
P.update(
    axle=(0.0, AXLE_Z), cd=CD, motor_angle=MOTOR_ANGLE,
    motor_face=-21.5, outer_face=-22.1, brg_seat_out=-22.6, brg_seat_in=-19.6,   # main + 3.5
    inner_face=-16.5,
    cradle_end=-15.3,          # 筒は吸引する面(|y| ≤ 15.2)に入れない。モーターを 6.2mm くわえる(main は 9.4mm)
    enc_slot=(-17.5, -16.9, 3.05),
    # エンコーダ基板(6.0 × 9.2mm、x -3.0〜3.0、z 8.3〜17.5)の面と、MT6835(z 8.8〜15.2)・内の軸受のつばのくぼみ(上は開ける)
    enc_face=dict(x0=-3.1, bx0=-4.2, x1=6.0, wx1=3.1, ztop=16.0, px1=4.0, pz1=16.5),
    pocket=(4.0, 7.8, 16.5),
    # ねじ: 71T(|y| 22.8〜24.8、半径 10.95)とモーターの筒(x -17.2〜-6.9)を避ける
    screw_front=(8.0, -19.5), screw_rear=(-21.0, -19.5),
    fan_joint=(14.0, -20.3),   # ファンの囲い(中心 x 14.2、半径 17.5)から 0.3mm
    pcb_post=PCB_BOTTOM,
    top_cut=dict(z=PCB_BOTTOM, x=4.3, y=-16.9),   # メイン基板の切り欠き(x ±4.5、y < -16.7)の中だけ、上へ出してよい
)
VER = 't24v1'

if __name__ == '__main__':
    m = mm.build(P)
    v = m.val().Volume()
    bb = m.val().BoundingBox()
    print(f'体積 {v:.0f} mm³、樹脂(1.2 g/cm³)で {v * 1.2e-3:.2f} g')
    print('外形', [round(x, 2) for x in (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)])
    print('モーターの中心', [round(c, 3) for c in mm.motor_center(P)], f'角度 {MOTOR_ANGLE:.2f}°')
    cq.exporters.export(m, f'motor_mount_R_{VER}.step'); cq.exporters.export(m, f'motor_mount_R_{VER}.stl')
    cq.exporters.export(m.mirror('XZ'), f'motor_mount_L_{VER}.step'); cq.exporters.export(m.mirror('XZ'), f'motor_mount_L_{VER}.stl')

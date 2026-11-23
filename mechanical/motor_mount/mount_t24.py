"""タイヤ24mm・71T:13T のモーターマウント(t24 v1、2026-11-21。右側、左側は y を反転)。
`mount.py` の build() を、タイヤ24mm の並び(`docs/spec.md` の「方針の変更(2026-11-21)」)のパラメータで使う。
座標 [mm]: x 前(+)、y 左(+)、z 上(床 = 0)。車軸 (0, y, 12.0)。右側なので外側が -y。
部品の並び(外側から、main より 3.5mm 内): タイヤ -33.3〜-24.8、71T -24.8〜-22.8、LF-630 外 -23.2〜-21.2、内 -21.0〜-19.0、
磁石 -20.2〜-19.2、MT6835 -18.7〜-17.5、エンコーダ基板 -17.5〜-16.9。メイン基板の下面 z 13.6。
使い方: python3 mount_t24.py → motor_mount_R_t24v6.step/.stl、motor_mount_L_t24v6.step/.stl(v1 は P_V1)"""
import math
import cadquery as cq
import mount as mm

FRAME_TOP = 2.8              # フレームの上面。2026-11-23(t24v6): フレームを 0.8mm(下の面 z 2.0 のまま)にしたので 3.0 → 2.8。マウントの下の端を 0.2mm 伸ばす(車軸・モーター・基板の高さは同じ)
PCB_BOTTOM = 13.6
AXLE_Z = 12.0
CD = 0.15 * (71 + 13)          # 軸間 12.6mm
WALL = 0.9                     # モーターの筒の壁(main v8 と同じ)
# モーターの中心の高さ: 筒の下の壁がフレームの上面(t24v5 までの 3.0)に載り、筒の上がメイン基板の下面から 0.25mm 下になる所
MOTOR_Z = 8.2                  # 筒 z 3.05〜13.35、モーター z 3.9〜12.5
MOTOR_ANGLE = -math.degrees(math.asin((AXLE_Z - MOTOR_Z) / CD))   # 水平から 17.55° 下

P = dict(mm.P)
P.update(
    frame_top=FRAME_TOP,
    axle=(0.0, AXLE_Z), cd=CD, motor_angle=MOTOR_ANGLE,
    motor_face=-21.5, outer_face=-22.1, brg_seat_out=-22.6, brg_seat_in=-19.6,   # main + 3.5
    inner_face=-16.5,
    cradle_end=-15.3,          # 筒は吸引する面(|y| ≤ 15.2)に入れない。モーターを 6.2mm くわえる(main は 9.4mm)
    enc_slot=(-17.5, -16.9, 3.05),
    # エンコーダ基板(6.0 × 9.2mm、x -3.0〜3.0、z 8.3〜17.5)の面と、MT6835(z 8.8〜15.2)・内の軸受のつばのくぼみ(上は開ける)
    enc_face=dict(x0=-3.1, bx0=-4.2, x1=6.0, wx1=3.1, ztop=16.0, px1=4.0, pz1=16.5),
    pocket=(4.0, 7.8, 16.5),
    # ねじ: 71T(|y| 22.8〜24.8、半径 10.95)とモーターの筒(x -17.2〜-6.9)を避ける
    # t24v3(2026-11-23): (8, -19.5)・(-21, -19.5) から内へ。吸引する面を横 ±21.3 に広げ、ねじの頭をその中に入れるため(frame t24v4)。
    #   前の柱(半径 2.4)はファンの囲い(半径 17.5)から 0.4mm、ねじの頭(φ3.8)は基板の車軸の切り欠き(x 4.5)から 0.4mm
    # t24v4(2026-11-23): さらに内へ (6.8, -18.4)・(-21, -17.7)。ねじの頭とスカートの線(|y| 21.3)の間に余裕(前 1.0mm、後ろ 1.7mm)。柱は半径 2.0
    # t24v5(2026-11-23): 後ろも |y| 18.4 にして前後をそろえる(ユーザー)
    screw_front=(6.8, -18.4), screw_rear=(-21.0, -18.4),
    boss_r=2.0, post_r=2.0,    # t24v4: 2.4 → 2.0(前の柱をファンの囲いから 0.33mm 離すため。M2 の下穴 φ1.6 のまわりに 1.2mm)
    fan_joint=(14.0, -20.3),   # ファンの囲い(中心 x 14.2、半径 17.5)から 0.3mm
    pcb_post=PCB_BOTTOM,
    top_cut=dict(z=PCB_BOTTOM, x=4.3, y=-16.9),   # メイン基板の切り欠き(x ±4.5、y < -16.7)の中だけ、上へ出してよい
)

def windows(P, wall=0.8, strut=0.9, r_round=0.4, min_area=2.0):
    """モーターの穴と軸受の穴の間・車軸の下の肉抜きの窓(xz 面)。穴のまわり・床・メイン基板の下面・エンコーダのくぼみの床から wall 以上離す"""
    from shapely.geometry import Point, LineString, box as sbox
    ax_, az_ = P['axle']; mx_, mz_ = mm.motor_center(P)
    ft = P['frame_top']
    region = sbox(mx_, ft + wall, ax_ + 3.2, P['top_cut']['z'] - wall)
    region = region.difference(Point(mx_, mz_).buffer(P['motor_d'] / 2 + P.get('pad_relief', 0) + wall, 64))
    region = region.difference(Point(ax_, az_).buffer(P['brg_od'] / 2 + P.get('pad_relief', 0) + P['axle_wall'] + 0.0, 64))
    px, pz0, _ = P['pocket']
    region = region.difference(sbox(ax_ + P['enc_face']['bx0'] - wall, pz0 - wall, 99, 99))   # エンコーダのくぼみの床(z 7.8)の下 wall まで
    # 軸受の受けを支える柱を残す: モーターの穴へ(2つの中心を結ぶ線)と、真下のフレームへ。幅 2 × strut
    region = region.difference(LineString([(mx_, mz_), (ax_, az_)]).buffer(strut))
    region = region.difference(LineString([(ax_, az_), (ax_, ft)]).buffer(strut))
    region = region.buffer(-r_round).buffer(r_round)
    geoms = getattr(region, 'geoms', [region])
    y0, y1 = P['outer_face'] - 0.1, P['inner_face'] + 0.1
    return [([(round(x, 3), round(z, 3)) for x, z in list(g.exterior.coords)[:-1]], y0, y1) for g in geoms if g.area >= min_area]

VER = 't24v6'      # 2026-11-23(t24v6): フレームが 0.8mm になり上面が z 2.8 に下がったので、下の端を 0.2mm 伸ばした。t24v5: 後ろのねじも (-21, ±18.4) にそろえた。t24v4: ねじを (6.8, ±18.4)・(-21, ±17.7) へ、柱を半径 2.0 に。t24v3: ねじを (6.8, ±18.9)・(-21, ±18.9) へ、柱を半径 2.4 に(t24v2 は (8, ±19.5)・(-21, ±19.5)、半径 2.6)
P_V1 = dict(P)
# v2(2026-11-21): モーターの穴と軸受の穴の間・車軸の下を、y 方向に抜ける窓で肉抜きする(壁 0.8mm 以上)。
#   軸受の受けからモーターの穴へ・フレームへの柱(幅 1.8mm)は残す
P['windows'] = windows(P)

if __name__ == '__main__':
    m = mm.build(P)
    v = m.val().Volume()
    bb = m.val().BoundingBox()
    print(f'体積 {v:.0f} mm³、樹脂(1.2 g/cm³)で {v * 1.2e-3:.2f} g')
    print('外形', [round(x, 2) for x in (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)])
    print('モーターの中心', [round(c, 3) for c in mm.motor_center(P)], f'角度 {MOTOR_ANGLE:.2f}°')
    cq.exporters.export(m, f'motor_mount_R_{VER}.step'); cq.exporters.export(m, f'motor_mount_R_{VER}.stl')
    cq.exporters.export(m.mirror('XZ'), f'motor_mount_L_{VER}.step'); cq.exporters.export(m.mirror('XZ'), f'motor_mount_L_{VER}.stl')

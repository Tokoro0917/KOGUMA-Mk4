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
    pcb_post=None,                    # 後ろの耳を基板の下面まで伸ばす柱の上の z(機体の仮の案、2026-10-18)。None なら作らない
    post_r=3.0,
    post_nut=False,                   # True: 柱の上に基板のねじのナット、耳にフレームのねじのナット(どちらも後ろから横に入れる)。
                                      # False: 下から長いねじ1本で、ナットは基板の上
)

# v1(2026-10-17): M3、柱なし。P_V1 で作り直せる
P_V1 = dict(P)
# v2(2026-10-19): ねじを M2 にし(穴 φ2.3、ナット二面幅4.0 → 穴4.2)、後ろの耳の上に基板を受ける柱(z 13.6 まで)を足した
P.update(boss_r=3.1, nut_af=4.2, nut_depth=1.7, hole_d=2.3, pcb_post=13.6, post_r=3.1, post_nut=True)
P_V2 = dict(P)
# v3(2026-10-19): フレーム v6.1 に合わせて、ねじの位置を 1mm 単位に((7.85, -22.1)、(-17.15, -22.1) から)
P.update(screw_front=(8.0, -22.0), screw_rear=(-17.0, -22.0))
P_V3 = dict(P)
# v4(2026-10-20): ナットをやめて、ねじの穴に M2 のねじ山を切る(タップ)。下穴 φ1.6、ナットの穴はなくす
P.update(hole_d=1.6, tap=True)
P_V4 = dict(P)
# v5(2026-10-20): 前の耳から腕を伸ばしてファンの台を持つ(継ぎ目 (10, -16)、上から M2 でねじ山に留める)。
#                 前の耳の上にも基板を受ける柱を立てる(ファンの台の左右の柱をやめたため)
P.update(fan_joint=(10.0, -16.0), joint_r=3.0, joint_z=(4.0, 8.8), arm_w=3.4, pcb_post_front=True)
P_V5 = dict(P)
# v6(2026-10-20): 羽根 φ32・囲い φ33(外径 φ34.2)にしたので、継ぎ目を (20, -22) へ(前の耳からまっすぐ前へ12mm)
P.update(fan_joint=(20.0, -22.0))
P_V6 = dict(P)
# v7(2026-10-21): 継ぎ目を (14, -22) へ。継ぎ目の台を半径2.5にし、フレームの窓にかからない(下から見えない)ようにする
P.update(fan_joint=(14.0, -22.0), joint_r=2.5)
P_V7 = dict(P)
# v8(2026-10-29): 薄い壁・軽さ・印刷の誤差・組み立てを見直す
#   - モーターの穴を φ8.6(寸法どおり)にし、モーターの穴と軸受の穴の間の壁を 0.75 → 0.80mm(JLC のすすめる最小)
#   - モーターの穴と軸受の穴は「3点で受ける」形: 穴のまわりを 0.1mm 逃がし(筒の壁は 0.8 → 0.9mm にして、逃がした所でも 0.8mm)、幅 PAD_W の当たり面を 120° おきに3つ残す。
#     当たり面の1つは相手の穴の側に置く(間の壁は寸法どおり 0.80mm のまま)。印刷の誤差で穴が小さめでも押し込め、ゆるければ接着できる
#   - 穴の入口に面取り 0.3mm(軸受・モーターを入れやすく、タップを立てやすく)
#   - 耳と柱の半径 3.1 → 2.6、耳とマウントをつなぐ板の幅を 3.4mm にして軽くする
P.update(bore_clear=0.0, wall=0.9, pads=True, pad_relief=0.1, pad_w=2.6, chamfer=0.3, boss_r=2.6, post_r=2.6, link_w=3.4)
P_V8 = dict(P)
# v9(2026-10-29): エンコーダ基板を溝に差して裏の壁で支えるのをやめ、マウントの面(y -21.1、磁石の側)に当てて接着する(ねじなし)。
#   基板は x -2.8〜5.2、z 3.0〜13.2(8.0 × 10.2mm、0.6mm)。下はフレームの上面、前は x 5.4 の当たり面(z 3〜7)で受ける。
#   2026-10-29(同じ日): エンコーダ基板はメイン基板の裏にはんだ付けして立てる(x -2.6〜5.2、y -21.0〜-20.4、z 3.3〜13.6。面とのすき間0.1、モーターの筒とは0.27)ことにした。マウントの形はこのまま。面と当たり面は、基板を下ろすときの案内(貼らない)
#   面の縁(貼る所): 上 z 11.3〜13.6、前 x 4.0〜5.2、下 z 3.0〜3.8。くぼみ(AS5047P・部品・つば)は x -4.0〜4.0、z 3.8〜11.3
#   くぼみの後ろの端を x -3.8 → -4.0 にし、モーターの穴とつなげる(内の軸受のつばとモーターの間は 0.2mm しかなく、間に 0.2mm の薄い壁が残っていたため。v8 まで)
#   くぼみの底を z 3.7 → 3.8(床の厚さ 0.8mm)、上の縁の肉を後ろ x -4.2 まで伸ばしてモーターの筒とつなげる
P.update(enc_face=dict(x0=-2.8, bx0=-4.2, x1=6.0, wx1=5.4, ztop=13.6, px1=4.0, pz1=11.3), pocket=(4.0, 3.8, 14.0))
VER = 'v9'

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
        lw = P.get('link_w', 2 * P['boss_r']) / 2
        body = body.union(box(x_link0, x_link1, sy - lw, min(sy + lw, y_in), ft, P['ear_top']))
    if P.get('fan_joint'):    # 前の耳からファンの台の継ぎ目へ伸ばす腕と、継ぎ目のねじの柱
        (sx, sy), (jx, jy) = P['screw_front'], P['fan_joint']
        z0, z1 = P['joint_z']
        L = math.hypot(jx - sx, jy - sy); ang = math.degrees(math.atan2(jy - sy, jx - sx))
        arm = cq.Workplane().box(L, P['arm_w'], z1 - z0, centered=(False, True, False)).rotate((0, 0, 0), (0, 0, 1), ang).translate((sx, sy, z0))
        body = body.union(arm).union(cq.Workplane().center(jx, jy).circle(P['joint_r']).extrude(z1 - z0).translate((0, 0, z0)))
        body = body.union(cq.Workplane().center(sx, sy).circle(P['boss_r']).extrude(z1 - ft).translate((0, 0, ft)))
    if P.get('pcb_post_front'):   # 前の耳の上にも基板を受ける柱
        sx, sy = P['screw_front']
        body = body.union(cq.Workplane().center(sx, sy).circle(P['post_r']).extrude(P['pcb_post'] - ft).translate((0, 0, ft)))
    if P.get('pcb_post'):     # 後ろの耳の上に柱を立て、基板を受ける(下から長いねじで、フレーム・柱・基板をまとめて留める)
        sx, sy = P['screw_rear']
        body = body.union(cq.Workplane().center(sx, sy).circle(P['post_r']).extrude(P['pcb_post'] - P['ear_top']).translate((0, 0, P['ear_top'])))
    # ---- 穴 ----
    body = body.cut(ycyl(P['motor_d'] / 2 + P['bore_clear'] / 2, P['motor_face'], P['cradle_end'] + 1, mx, mz))
    if P.get('pads'):     # 3点で受ける: 当たり面の1つを相手の穴の側に向ける
        a_m = math.atan2(az - mz, ax - mx)
        body = body.cut(relief(P['motor_d'] / 2 + P['pad_relief'], P['motor_face'], P['cradle_end'] + 1, mx, mz, a_m, P['pad_w']))
        body = body.cut(relief(P['brg_od'] / 2 + P['pad_relief'], P['brg_seat_out'] - 1, P['brg_seat_in'], ax, az, a_m + math.pi, P['pad_w']))
    body = body.cut(ycyl(P['lip_hole'] / 2, y_out - 1, P['motor_face'] + 0.01, mx, mz))
    body = body.cut(ycyl(P['brg_od'] / 2, P['brg_seat_out'] - 1, P['brg_seat_in'], ax, az))
    px, pz0, pz1 = P['pocket']
    ef = P.get('enc_face')
    if ef:   # v9: エンコーダ基板をマウントの面に当てて接着する(裏から支えない)
        # 面の縁を作る肉(くぼみの上・前): 内の軸受の壁から基板の面まで
        body = body.union(box(ax + ef.get('bx0', ef['x0']), ax + ef['x1'], P['brg_seat_in'] - 0.01, P['enc_slot'][0], ft, ef['ztop']))
        body = body.cut(ycyl(P['motor_d'] / 2 + P.get('pad_relief', 0.0), P['brg_seat_in'] - 0.02, P['enc_slot'][0] + 0.02, mx, mz))   # 足した肉がモーターの穴を埋めないように
        # くぼみ(AS5047P・部品・内の軸受のつば): 上は z ef['pz1'] で閉じ、前は ef['px1'] まで
        body = body.cut(box(ax - px, ax + ef['px1'], P['brg_seat_in'], P['enc_slot'][0], pz0, ef['pz1']))
        # 基板の面より内側は、基板の外形の所をすべて開ける(裏の壁をなくす)
        body = body.cut(box(ax + ef['x0'], ax + ef['wx1'], P['enc_slot'][0], P['inner_face'] + 1.0, ft - 0.01, 20.0))   # 前は x wx1 で止め、基板の前の端を受ける
    else:
        # ポケットは基板の溝の手前まで(基板の裏は壁で受ける)。前側は開ける(薄い壁を残さない)
        body = body.cut(box(ax - px, ax + px + 1.0, P['brg_seat_in'], P['enc_slot'][0], pz0, pz1))
        sy0, sy1, sx = P['enc_slot']
        body = body.cut(box(ax - sx, ax + sx, sy0, sy1, ft - 0.01, 14.0))
    # 外側の面より外に出た所を削る(41T・ピニオンとのすき間)
    body = body.cut(box(-40, 40, -40, y_out, 0, 30).cut(ycyl(P['seat_r'], P['brg_seat_out'], y_out, ax, az)))
    for (sx_, sy_) in (P['screw_front'], P['screw_rear']):
        body = body.cut(cq.Workplane().center(sx_, sy_).circle(P['hole_d'] / 2).extrude(20).translate((0, 0, ft - 1)))
        if P.get('tap'):
            continue          # ねじ山を切るので、ナットの穴は作らない(耳は下からフレームのねじ、柱の上は基板のねじ)
        if P.get('pcb_post') and (sx_, sy_) == P['screw_rear']:
            if not P.get('post_nut'):
                continue      # 柱のある耳はナットを基板の上に置く
            hexr = P['nut_af'] / math.cos(math.pi / 6)
            for z0 in (P['ear_top'] - P['nut_depth'], P['pcb_post'] - P['nut_depth']):   # 耳のナットと、柱の上のナット
                body = body.cut(cq.Workplane().center(sx_, sy_).polygon(6, hexr).extrude(P['nut_depth']).translate((0, 0, z0)))
                body = body.cut(box(sx_ - 6.0, sx_, sy_ - P['nut_af'] / 2, sy_ + P['nut_af'] / 2, z0, z0 + P['nut_depth']))
            continue
        body = body.cut(cq.Workplane().center(sx_, sy_).polygon(6, P['nut_af'] / math.cos(math.pi / 6))
                        .extrude(P['nut_depth'] + 1).translate((0, 0, P['ear_top'] - P['nut_depth'])))
    if P.get('fan_joint'):
        jx, jy = P['fan_joint']
        body = body.cut(cq.Workplane().center(jx, jy).circle(P['hole_d'] / 2).extrude(20).translate((0, 0, ft - 1)))   # 継ぎ目の下穴(ねじ山)
    if P.get('chamfer'):  # 穴の入口の面取り
        c = P['chamfer']
        def cone_y(r, y, sgn, x, z):     # y の面から sgn の向きへ、半径 r + c から r まで
            return cq.Workplane().add(cq.Solid.makeCone(r + c, r, c, cq.Vector(x, y, z), cq.Vector(0, sgn, 0)))
        def cone_z(r, z, sgn, x, y):
            return cq.Workplane().add(cq.Solid.makeCone(r + c, r, c, cq.Vector(x, y, z), cq.Vector(0, 0, sgn)))
        body = body.cut(cone_y(P['brg_od'] / 2, P['brg_seat_out'], 1, ax, az))          # 外の軸受(外から入れる)
        body = body.cut(cone_y(P['brg_od'] / 2, P['brg_seat_in'], -1, ax, az))          # 内の軸受(内から入れる)
        body = body.cut(cone_y(P['motor_d'] / 2, P['cradle_end'], -1, mx, mz))          # モーター(内から入れる)
        holes = [(P['screw_front'], ft, P['pcb_post'] if P.get('pcb_post_front') else P['ear_top']),
                 (P['screw_rear'], ft, P['pcb_post'] if P.get('pcb_post') else P['ear_top'])]
        if P.get('fan_joint'):
            holes.append((P['fan_joint'], P['joint_z'][0], P['joint_z'][1]))
        for (hx, hy), z0, z1 in holes:   # タップの下穴の上下
            body = body.cut(cone_z(P['hole_d'] / 2, z0, 1, hx, hy)).cut(cone_z(P['hole_d'] / 2, z1, -1, hx, hy))
    return body

def relief(r, y0, y1, x, z, a, w):
    """穴のまわりを半径 r まで逃がし、幅 w の当たり面を角度 a(xz 面、x から z へ)と a ± 120° に残す形(これを削る)"""
    rel = ycyl(r, y0, y1, x, z)
    lo, hi = min(y0, y1), max(y0, y1)
    for k in range(3):
        b = a + k * 2 * math.pi / 3
        pad = (cq.Workplane().box(r + 1, hi - lo, w, centered=(False, False, True))
               .rotate((0, 0, 0), (0, 1, 0), -math.degrees(b)).translate((x, lo, z)))
        rel = rel.cut(pad)
    return rel

if __name__ == '__main__':
    m = build()
    v = m.val().Volume()
    print(f'体積 {v:.0f} mm³、樹脂(1.2 g/cm³)で {v * 1.2e-3:.2f} g、ナイロン PA12(1.01)で {v * 1.01e-3:.2f} g')
    print('外形', m.val().BoundingBox().__dict__ if False else [round(x, 2) for x in (m.val().BoundingBox().xmin, m.val().BoundingBox().xmax, m.val().BoundingBox().ymin, m.val().BoundingBox().ymax, m.val().BoundingBox().zmin, m.val().BoundingBox().zmax)])
    print('モーターの中心', [round(c, 3) for c in motor_center(P)])
    cq.exporters.export(m, f'motor_mount_R_{VER}.step'); cq.exporters.export(m, f'motor_mount_R_{VER}.stl')
    cq.exporters.export(m.mirror('XZ'), f'motor_mount_L_{VER}.step'); cq.exporters.export(m.mirror('XZ'), f'motor_mount_L_{VER}.stl')

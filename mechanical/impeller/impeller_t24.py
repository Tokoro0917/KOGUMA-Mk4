"""タイヤ24mm の機体の吸引ファンの羽根(C 案、φ30・9 枚・まっすぐ、2026-11-26、ユーザー「ファンはどうする」→「軸は 1.18 くらいにしておいて」)。
t24v4(2026-11-26、ユーザー「割れにくいようにして」): 角に丸みを足し、ハブを太くした(下の「割れにくくするための形」)。
t24v3(2026-11-26、ユーザー「トラ猫みたいにモータの軸根元にファンが当たるようにしたい」): ハブを上の板の上へ z 8.9 まで伸ばした(下の「軸の根元まで伸ばしたハブ」)。
t24v2(2026-11-26、ユーザー「ファンの軸を通したところにくぼみを作り接着剤が入れられるようにして」): ハブの下に接着剤を入れるくぼみ。
t24v1: 軸の穴 φ1.18 だけ。
CadQuery で作る。座標は機体と同じ(原点は車軸の真ん中の床、+x 前、+y 左、z 上、mm)。ファンの中心は (14.2, 0)。
使い方(リポジトリの一番上で): python3 mechanical/impeller/impeller_t24.py
  → mechanical/impeller/impeller_t24v3.step・.stl(羽根の中心が原点。DMM などに出す用)
     mechanical/order_t24/13_impeller_t24v3.step(機体の座標。Fusion で組み上がりを見る用)

形は流体の計算(docs/calc/fan_cfd/)で決めた:
  - C 案: 羽根と一緒に回る外の壁 + ファンの台の止まった輪(半径 16.5〜17.5、ファンの台 t24v4 のまま)
  - φ30(羽の先 半径 15.0)、外の壁 0.6mm(半径 15.0〜15.6。輪とのすき間 0.9mm)
  - 9 枚・まっすぐ(曲げ 0°)。スカートのすき間 0.05mm の計算で 5 枚・60° より 8% 少ない電力(粗いメッシュ)。
    まっすぐの羽は、遠心力で付け根が曲げられない(docs/calc/fan_cfd/impeller_stress.py)
  - 羽の厚さ 0.6mm、内の端 半径 5mm、高さ 3.9mm(z 3.3〜7.2)、上の板 0.8mm(z 7.2〜8.0)
高さの決まり(機体のモデル mechanical/vehicle/vehicle.py と t24_mass.py):
  - フレームの上の面 z 2.8 → 羽根の下の端 z 3.3(すき間 0.5mm)
  - ファンの台のハブの底 z 8.6 → 羽根の上の面 z 8.0(すき間 0.6mm)
  - モーターの前の面 z 9.4、軸 φ1.2 は前の面から 5.1mm(先は z 4.3)
軸の穴: φ1.18(軸 φ1.2 を圧入、ユーザー)。下まで抜いておく(印刷のあと中の樹脂を洗い流せるように。軸を押し出すときにも使える)。
接着剤のくぼみ(t24v2): ハブの下の面(z 3.3)から、φ2.4 で z 4.6 まで(深さ 1.3mm)。
  組み立ての順は「モーターをファンの台に上から圧入 → 羽根を下から軸に押し込む」なので、羽根を付けたあと手が届くのは下の面だけ。
  軸の先(z 4.3)がくぼみの中に 0.3mm 出るので、下から瞬間接着剤を入れると、軸の先のまわりにたまり、軸と穴のすき間にもしみ込む。
  上の面(モーターの側)には付けない(接着剤がモーターの軸受にしみ込まないように)。
  くぼみのまわりのハブの壁は 0.8mm(ハブ 半径 2.0 − くぼみ 半径 1.2)。
軸の根元まで伸ばしたハブ(t24v3、ToraNeko.Mk3 と同じ作り):
  ToraNeko.Mk3 の機体の STEP(mechanical/exported/TORANEKO.Mk3_v36.step)では、羽根のハブが MK06-45 の軸の根元
  (軸受の出っ張り)の 0.19mm 手前まで伸びている。同じように、ハブを 半径 1.2mm で上の板の上(z 8.0)から z 8.9 まで伸ばす。
  - モーターの軸受の出っ張り(半径 1.2、z 9.1〜9.4、止まっている)との間は 0.2mm。回る羽根が止まった所にこすれないように、当てきらない
  - 組むときは、羽根と軸受の出っ張りの間に 0.2mm の紙(名刺など)をはさみ、当たるまで押し込んでから紙を抜く。高さがいつも同じになる
  - ファンの台のハブの穴(半径 1.5、z 8.6〜9.4)との横のすき間は 0.3mm
  - 軸の穴のまわりの肉は 0.61mm(半径 1.2 − 穴の半径 0.59)
軸がかかる長さ(圧入): z 4.6〜8.9 の 4.3mm(t24v2 は 3.4mm)
割れにくくするための形(t24v4):
  - 角に丸み R0.3 を足した: 外の壁と上の板の内の角、ハブと上の板の下の角、伸ばしたハブと上の板の上の角(力が角に集まって割れが始まらないように)。
    羽の付け根(上の板・外の壁)の丸み R0.3 は t24v1 から
  - ハブを 半径 2.0 → 2.5mm に太くした。接着剤のくぼみのまわりの壁 0.8 → 1.3mm、軸の穴のまわりの肉 1.41 → 1.91mm
    (羽の内の端は 半径 5mm なので、空気の通り道は変わらない)
  - 伸ばしたハブ(半径 1.2)は、ファンの台の穴(半径 1.5)とのすき間を 0.3mm 残したいので太くしない
  - 圧入で割れるかは、穴の太さ(φ1.18)と材料の伸びで決まる(形をいくら太くしても、穴のふちの伸びは「しめしろ ÷ 穴の直径」でほぼ決まる)。
    docs/order.md の羽根の所を見る"""
import os
import cadquery as cq

VER = 't24v4'
FAN_X = 14.2           # ファンの中心(機体の座標)
R_TIP = 15.0           # 羽の先(φ30)
RIM_T = 0.6            # 回る外の壁の厚さ
R_INNER = 5.0          # 羽の内の端
N_BLADES = 9           # 羽の枚数
BLADE_T = 0.6          # 羽の厚さ
Z_BOTTOM = 3.3         # 羽・外の壁の下の端
Z_DISC0 = 7.2          # 上の板の下の面
Z_DISC1 = 8.0          # 上の板の上の面
HUB_R = 2.5            # 軸を通すハブの半径(t24v4 で 2.0 から太くした。流体の計算は 2.0)
BORE_D = 1.18          # 軸の穴(軸 φ1.2 を圧入)
TOP_HUB_R = 1.2        # 上の板の上へ伸ばしたハブの半径(モーターの軸受の出っ張りと同じ)
TOP_HUB_Z = 8.9        # 伸ばしたハブの上の端(軸受の出っ張り z 9.1 の 0.2mm 手前。ToraNeko は 0.19mm)
GLUE_D = 2.4           # 接着剤のくぼみの直径
GLUE_Z = 4.6           # くぼみの上の端(軸の先 z 4.3 より 0.3mm 上)
FILLET_R = 0.3         # 羽の付け根の丸み(docs/spec.md の「ファンの羽根の強さ」の決まり: R0.3 以上)

HERE = os.path.dirname(os.path.abspath(__file__))
ORDER = os.path.join(HERE, '..', 'order_t24')


def cyl(r, z0, z1):
    """羽根の中心を原点にした、z0〜z1 の円柱"""
    return cq.Workplane('XY').workplane(offset=z0).circle(r).extrude(z1 - z0)


def blade(angle_deg):
    """まっすぐな羽 1 枚(内の端から外の壁まで)。外の壁と上の板に少し食い込ませて、1 つの形につなげる"""
    length = R_TIP + 0.3 - R_INNER
    height = Z_DISC0 + 0.1 - Z_BOTTOM
    b = cq.Workplane('XY').box(length, BLADE_T, height, centered=(False, True, False))
    b = b.translate((R_INNER, 0, Z_BOTTOM))
    return b.rotate((0, 0, 0), (0, 0, 1), angle_deg)


def is_blade_root(edge):
    """羽の付け根の辺か(羽と上の板の角: z が Z_DISC0 の横の線。羽と外の壁の角: 半径 R_TIP の縦の線)"""
    p0 = edge.startPoint()
    p1 = edge.endPoint()
    # 上の板との角(羽の両側の 2 本)
    if abs(p0.z - Z_DISC0) < 1e-3 and abs(p1.z - Z_DISC0) < 1e-3:
        r0 = (p0.x ** 2 + p0.y ** 2) ** 0.5
        r1 = (p1.x ** 2 + p1.y ** 2) ** 0.5
        if min(r0, r1) > R_INNER - 0.1 and max(r0, r1) < R_TIP + 0.01 and abs(r1 - r0) > 1.0:
            return True
    # 外の壁との角(羽の両側の 2 本)
    if abs(p0.x - p1.x) < 1e-6 and abs(p0.y - p1.y) < 1e-6:
        r = (p0.x ** 2 + p0.y ** 2) ** 0.5
        if abs(r - R_TIP) < 0.05:
            return True
    return False


def fillet_circle(body, radius, z, name):
    """半径 radius・高さ z にある丸い辺(羽で切れて弧になっていてもよい)に、丸み FILLET_R を付ける"""
    edges = []
    for e in body.edges().vals():
        if e.geomType() != 'CIRCLE':
            continue
        center = e.arcCenter()   # 円・弧の中心(羽根の軸の上にあるものだけ選ぶ)
        p = e.startPoint()
        r = (p.x ** 2 + p.y ** 2) ** 0.5
        if abs(center.x) < 1e-3 and abs(center.y) < 1e-3 and abs(p.z - z) < 1e-3 and abs(r - radius) < 1e-3:
            edges.append(e)
    print(f'丸み R{FILLET_R}: {name}({len(edges)} 本の辺)')
    return body.newObject(edges).fillet(FILLET_R)


def impeller():
    """羽根 1 つ(上の板 + 外の壁 + 羽 9 枚 + ハブ、軸の穴あき)"""
    body = cyl(R_TIP + RIM_T, Z_DISC0, Z_DISC1)                                   # 上の板
    body = body.union(cyl(R_TIP + RIM_T, Z_BOTTOM, Z_DISC1).cut(cyl(R_TIP, Z_BOTTOM - 1, Z_DISC1)))   # 外の壁
    body = body.union(cyl(HUB_R, Z_BOTTOM, Z_DISC0 + 0.1))                         # ハブ
    body = body.union(cyl(TOP_HUB_R, Z_DISC1 - 0.1, TOP_HUB_Z))                    # 上の板の上へ伸ばしたハブ(軸の根元の近くまで)
    # 丸い角に丸みを付ける(t24v4)。羽を付ける前に付ける(羽を付けたあとでは、羽の付け根の丸みとぶつかって作れない)
    body = fillet_circle(body, R_TIP, Z_DISC0, '外の壁と上の板の内の角')
    body = fillet_circle(body, HUB_R, Z_DISC0, 'ハブと上の板の下の角')
    body = fillet_circle(body, TOP_HUB_R, Z_DISC1, '伸ばしたハブと上の板の上の角')
    for i in range(N_BLADES):
        body = body.union(blade(360.0 / N_BLADES * i))
    # 羽の付け根に丸みを付ける(角に力が集まって割れないように)
    roots = []
    for e in body.edges().vals():
        if is_blade_root(e):
            roots.append(e)
    print(f'丸みを付ける辺: {len(roots)} 本(羽 {N_BLADES} 枚 × 4 本 = {N_BLADES * 4} 本のはず)')
    body = body.newObject(roots).fillet(FILLET_R)
    body = body.cut(cyl(BORE_D / 2, Z_BOTTOM - 1, Z_DISC1 + 1))                   # 軸の穴(下まで抜く)
    body = body.cut(cyl(GLUE_D / 2, Z_BOTTOM - 1, GLUE_Z))                       # 接着剤のくぼみ(ハブの下から)
    return body


imp = impeller()
solid = imp.val()
assert solid.isValid(), '羽根の形が壊れた'
volume = solid.Volume()
print(f'羽根 {VER}: 体積 {volume:.1f} mm³、重さ {volume * 1.16 / 1000:.3f} g(樹脂 1.16 g/cm³)')
bb = solid.BoundingBox()
print(f'大きさ: x {bb.xmin:.2f}〜{bb.xmax:.2f}、y {bb.ymin:.2f}〜{bb.ymax:.2f}、z {bb.zmin:.2f}〜{bb.zmax:.2f}')

# 羽根の中心が原点のもの(注文に出す用)
cq.exporters.export(imp, os.path.join(HERE, f'impeller_{VER}.step'))
cq.exporters.export(imp, os.path.join(HERE, f'impeller_{VER}.stl'), tolerance=0.005, angularTolerance=0.1)
# 機体の座標に置いたもの(Fusion で組み上がりを見る用)
cq.exporters.export(imp.translate((FAN_X, 0, 0)), os.path.join(ORDER, f'13_impeller_{VER}.step'))
print('書き出した')

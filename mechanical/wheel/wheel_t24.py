"""タイヤ24mm 用のホイール(t24v2、2026-11-24。t24v1 は 2026-11-21)。右側、左は y を反転。CadQuery で作る。
座標は機体と同じ(原点は車軸の真下の床、+x 前、+y 左、z 上、mm)。車軸 (0, y, 12.0)。
タイヤ(MK3 と同じ 24mm、内径・幅はミニッツのナローから推定 φ20 × 8.5mm)を y -33.3〜-24.8 に受ける。
71T(厚さ 2mm、y -24.8〜-22.8)はホイールの内側の面に接着する。車軸は **3×8 の平行ピン(y -28.2〜-20.2)** を内側から 5mm 圧入する。
t24v2(2026-11-24、ユーザー): ピンを 3×6 → 3×8 にし、ホイールの穴を 3 → 5mm に深くした(穴の縁の面圧 31 → 11MPa、docs/calc/t24_wheel_strength.py)。
ピンの内の端(y -20.2)と磁石・エンコーダの位置は t24v1 と同じ。
使い方(リポジトリの一番上で): python3 mechanical/wheel/wheel_t24.py"""
import math
import cadquery as cq
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import cq_arcs     # 丸い所を本当の円弧にする(2026-11-24)

VER = 't24v2'
PIN_Y = (-28.2, -20.2)      # 平行ピン 3×8 の両端(機体のモデル・確かめるスクリプトが使う)
AX = (0.0, 12.0)            # 車軸 (x, z)
W = dict(
    od=20.0,                # ホイールの外径 = タイヤの内径(推定。実物で測る)
    y_out=-33.3, y_in=-24.8,   # タイヤを受ける幅 8.5mm(推定)
    rim=0.8,                # 外の輪の厚さ(JLC のすすめる最小)
    web=1.0, web_y=-24.8,   # 円板(内側の面、71T を貼る面)の厚さ
    hub_r=2.5,              # ピンを囲むハブ
    hub_y0=-29.2,           # ハブの外の端(ピンの穴の底 1.0mm)。t24v1 は -27.2
    boss_r=3.8, boss_y1=-23.4,   # 71T の穴(φ8 として)の中に入る段: 71T の芯を出す。外の軸受(-23.2)から 0.2mm
    spacer_r=1.9, spacer_y1=-23.2,   # 外の軸受の内輪に当たる段(内輪だけに当たり、外輪とつばには触れない)
    pin_r=1.5, pin_y0=-28.2, pin_clear=-0.05,   # 平行ピンの穴(圧入。φ2.95、深さ 5mm)。t24v1 は -26.2(深さ 3mm)
    holes=6, hole_r0=3.6, hole_r1=8.6, spoke_w=1.4,   # 円板の肉抜き(扇形の窓 6つ、スポーク 1.4mm)
    chamfer=0.3,
)

def ycyl(r, y0, y1, x=AX[0], z=AX[1]):
    lo, hi = min(y0, y1), max(y0, y1)
    return cq.Workplane('XZ', origin=(x, 0, z)).circle(r).extrude(-(hi - lo)).translate((0, lo, 0))

def window(r0, r1, a0, a1, y0, y1):
    """xz 面の扇形の窓(半径 r0〜r1、角度 a0〜a1)を y 方向に伸ばした形"""
    n = 16
    pts = [(r1 * math.cos(a0 + (a1 - a0) * k / n), r1 * math.sin(a0 + (a1 - a0) * k / n)) for k in range(n + 1)]
    pts += [(r0 * math.cos(a1 - (a1 - a0) * k / n), r0 * math.sin(a1 - (a1 - a0) * k / n)) for k in range(n + 1)]
    # 2026-11-24: 円弧の所を本当の円弧にして作る(STEP がギザギザにならないように、cq_arcs.py)
    return cq_arcs.prism_xz([(AX[0] + u, AX[1] + v) for u, v in pts], y0, y1)

def build(W=W):
    R = W['od'] / 2
    body = ycyl(R, W['y_out'], W['y_in']).cut(ycyl(R - W['rim'], W['y_out'] - 1, W['y_in'] + 1))   # 外の輪
    body = body.union(ycyl(R - W['rim'] + 0.01, W['web_y'] - W['web'], W['web_y']))                  # 円板
    body = body.union(ycyl(W['hub_r'], W['hub_y0'], W['web_y']))                                      # ハブ
    body = body.union(ycyl(W['boss_r'], W['web_y'], W['boss_y1']))                                   # 71T の芯出しの段
    body = body.union(ycyl(W['spacer_r'], W['boss_y1'], W['spacer_y1']))                             # 軸受の内輪に当たる段
    # 円板の窓: スポークの幅が一定になるよう、内と外で角度を変えた扇形の近似(内の半径でスポーク幅を確保)
    n = W['holes']
    for k in range(n):
        c = 2 * math.pi * k / n + math.pi / n
        half = math.pi / n - (W['spoke_w'] / 2) / W['hole_r0']
        body = body.cut(window(W['hole_r0'], W['hole_r1'], c - half, c + half, W['web_y'] - W['web'] - 0.1, W['web_y'] + 0.1))
    pr = W['pin_r'] + W['pin_clear'] / 2
    body = body.cut(ycyl(pr, W['pin_y0'], W['spacer_y1'] + 0.1))                                     # ピンの穴(内側から、止まり穴)
    c = W['chamfer']
    body = body.cut(cq.Workplane().add(cq.Solid.makeCone(pr + c, pr, c, cq.Vector(AX[0], W['spacer_y1'], AX[1]), cq.Vector(0, -1, 0))))
    return body

if __name__ == '__main__':
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    m = build()
    v = m.val().Volume(); bb = m.val().BoundingBox()
    print(f'体積 {v:.0f} mm³、樹脂(1.2 g/cm³)で {v * 1.2e-3:.2f} g')
    print('外形', [round(x, 2) for x in (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)])
    for side, part in (('R', m), ('L', m.mirror('XZ'))):
        cq.exporters.export(part, os.path.join(here, f'wheel_{side}_{VER}.step'))
        cq.exporters.export(part, os.path.join(here, f'wheel_{side}_{VER}.stl'), tolerance=0.005, angularTolerance=0.05)

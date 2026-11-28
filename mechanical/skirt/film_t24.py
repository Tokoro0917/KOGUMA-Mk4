"""二次スカート(フィルム)の型紙(2026-11-27、ユーザー「ここにデジキーのあおい袋を切って貼る」「外向きに垂らすよ」)。
t24v3(2026-11-27、ユーザー「ギアに被っても大丈夫」): 横を ±22 → ±24.5mm に広げた(71T の下まで。タイヤの 0.3mm 手前)。
t24v2(2026-11-27、ユーザーが前の機体の裏の写真で「こんな感じにつける」): 袋を機体の裏のほぼ全体を覆う大きな 1 枚にした。
  角の丸い長方形(横 ±22mm、前後 ±48mm、角 R8)で、真ん中を一次スカートの枠の内側(75 × 27.4mm)と同じ形に抜き、滑り板(φ5、x ±45)に穴をあける。
  一次スカートの枠の下の面に貼り、枠から外の袋は、やわらかいので床の方へたれて、吸うと床に押し付けられる。
t24v1: 枠と同じ輪 + 外へ 1.0mm の垂らす分(下の説明)。
一次スカート(skirt_t24.py、枠 t24v3)の下の面に、Digi-Key の青い袋を切って両面テープで貼り、外のふちから外へはみ出した分を下へ折って垂らす。
使い方(リポジトリの一番上で): python3 mechanical/skirt/film_t24.py
  → mechanical/skirt/film_t24v1_template_A4_1to1.pdf(A4、「実際のサイズ」で印刷して型紙にする)
     mechanical/skirt/film_t24v1.dxf(切る線。レーザーやカッティングマシンで切るとき用)
形:
  - 枠と同じ四角い輪(外のふち x ±40・y ±16.2、幅 2.5mm)に、外へ HANG だけはみ出す「垂らす分」を足す
  - 垂らす分は、枠の外のふちの線(点線)で下へ折る。枠の下の端は床から 1.0mm なので、テープとフィルムの厚さを引くと、1.0mm 垂らせば床に軽く届く
  - 四隅は、垂らす分の角(HANG × HANG)を切り落とす(4 辺を別々に折れるように)
  - 横の垂らす分は、マウントのねじの頭(|y| 16.5 から)の 0.3mm 手前で下へ折れる。外へ広がらないように、折り目をしっかり付ける"""
import os
import ezdxf
from shapely.geometry import box, Point
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

VER = 't24v3'
HERE = os.path.dirname(os.path.abspath(__file__))
X_OUT = 40.0      # 枠の外のふち(skirt_t24.py の t24v3 と同じ)
Y_OUT = 16.2
W = 2.5           # 枠の幅
HANG = 1.0        # t24v1: 外へはみ出させて下へ折る長さ
FILM_X = 48.0     # t24v2: 袋の前後の端(フレームの端 x ±50 の少し手前)
FILM_Y = 24.5     # t24v3(ユーザー「ギアに被っても大丈夫」): 袋の横のふち。71T(|y| 22.8〜24.8、下の端は床から 1.35mm)の下まで広げ、
                  # タイヤ(|y| 24.8 から)の 0.3mm 手前まで。t24v2 は 22.0(71T に当たらない幅)
CORNER_R = 8.0    # t24v2: 角の丸み(両端を半円にすると、枠の四隅の外に 0.6mm しか残らないので、角の丸い長方形にした)
SKIDS = [(45.0, 0.0), (-45.0, 0.0)]
SKID_HOLE_R = 3.0 # 滑り板(φ5)を通す穴


def film_outline():
    """t24v2 の袋の形(切る線): 角の丸い長方形から、真ん中の四角(枠の内側)と滑り板の穴を抜く"""
    # 角の丸い長方形 = 小さい長方形を CORNER_R だけ丸く太らせる
    outer = box(-FILM_X + CORNER_R, -FILM_Y + CORNER_R, FILM_X - CORNER_R, FILM_Y - CORNER_R).buffer(CORNER_R, 64)
    inner = box(-X_OUT + W, -Y_OUT + W, X_OUT - W, Y_OUT - W)
    film = outer.difference(inner)
    for x, y in SKIDS:
        film = film.difference(Point(x, y).buffer(SKID_HOLE_R, 64))
    return film


def film_outline_t24v1():
    """t24v1 のフィルムの形(切る線)。外の四角から四隅の角を切り落とし、内の四角を抜く"""
    outer = box(-X_OUT - HANG, -Y_OUT - HANG, X_OUT + HANG, Y_OUT + HANG)
    for sx in (1, -1):
        for sy in (1, -1):
            corner = box(min(sx * X_OUT, sx * (X_OUT + HANG)), min(sy * Y_OUT, sy * (Y_OUT + HANG)),
                         max(sx * X_OUT, sx * (X_OUT + HANG)), max(sy * Y_OUT, sy * (Y_OUT + HANG)))
            outer = outer.difference(corner)
    inner = box(-X_OUT + W, -Y_OUT + W, X_OUT - W, Y_OUT - W)
    return outer.difference(inner)


film = film_outline()
fold = box(-X_OUT, -Y_OUT, X_OUT, Y_OUT)     # 折る線(枠の外のふち)

# DXF(切る線だけ)
doc = ezdxf.new(units=4)
msp = doc.modelspace()
msp.add_lwpolyline(list(film.exterior.coords), close=True)
for hole in film.interiors:
    msp.add_lwpolyline(list(hole.coords), close=True)
doc.saveas(os.path.join(HERE, f'film_{VER}.dxf'))

# 1:1 の型紙(A4、印刷は「実際のサイズ」で)。横長の機体を縦に置く(前が上)
plt.rcParams['font.family'] = 'IPAPGothic'
W_MM, H_MM = 210, 297
fig = plt.figure(figsize=(W_MM / 25.4, H_MM / 25.4))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W_MM)
ax.set_ylim(0, H_MM)
ax.axis('off')
OX, OY = 105, 170          # 型紙の真ん中の位置


def draw(geom_line, style, lw):
    xs, ys = geom_line.xy
    # 機体の x(前)を紙の上へ、y(左)を紙の左へ
    ax.plot([OX - y for y in ys], [OY + x for x in xs], style, lw=lw)


draw(film.exterior, 'k-', 0.6)
for hole in film.interiors:
    draw(hole, 'k-', 0.6)
draw(fold.exterior, 'b--', 0.4)     # 一次スカートの枠の外のふち(ここに枠が来る)
ax.text(OX, OY + FILM_X + 4, 'FRONT(前)', ha='center', fontsize=9)
ax.text(20, 285, f'MK4 t24 二次スカート(Digi-Key の青い袋)型紙 {VER}  1:1', fontsize=11)
ax.text(20, 278, '「実際のサイズ」(100%)で印刷。下の 50mm の線をものさしで測って確かめる', fontsize=8)
ax.text(20, 272, '実線: 切る線(外のふち・真ん中の四角・滑り板の丸い穴) / 青い点線: 一次スカートの枠の外のふち(貼る位置の目安)', fontsize=8)
ax.text(20, 266, f'袋の外 {2 * FILM_X:g} × {2 * FILM_Y:g}mm(角 R{CORNER_R:g})、真ん中の穴 {2 * (X_OUT - W):g} × {2 * (Y_OUT - W):g}mm(枠 t24v3 の内側)、滑り板の穴 φ{2 * SKID_HOLE_R:g}', fontsize=8)
ax.plot([20, 70], [30, 30], 'k-', lw=0.8)
ax.plot([20, 20], [30, 80], 'k-', lw=0.8)
ax.text(22, 33, '50 mm', fontsize=8)
ax.text(22, 75, '50 mm', fontsize=8)
fig.savefig(os.path.join(HERE, f'film_{VER}_template_A4_1to1.pdf'))
fig.savefig(os.path.join(HERE, f'film_{VER}_template.png'), dpi=110)
print(f'袋 {VER}: 外 {2 * FILM_X:g} × {2 * FILM_Y:g}mm、真ん中の穴 {2 * (X_OUT - W):g} × {2 * (Y_OUT - W):g}mm、面積 {film.area:.0f} mm²')

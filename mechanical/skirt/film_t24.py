"""二次スカート(フィルム)の型紙(2026-11-27、ユーザー「ここにデジキーのあおい袋を切って貼る」「外向きに垂らすよ」)。
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
from shapely.geometry import box
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

VER = 't24v1'
HERE = os.path.dirname(os.path.abspath(__file__))
X_OUT = 40.0      # 枠の外のふち(skirt_t24.py の t24v3 と同じ)
Y_OUT = 16.2
W = 2.5           # 枠の幅
HANG = 1.0        # 外へはみ出させて下へ折る長さ


def film_outline():
    """フィルムの形(切る線)。外の四角から四隅の角を切り落とし、内の四角を抜く"""
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
draw(fold.exterior, 'b--', 0.4)
ax.text(OX, OY + X_OUT + HANG + 4, 'FRONT(前)', ha='center', fontsize=9)
ax.text(20, 285, f'MK4 t24 二次スカート(Digi-Key の青い袋)型紙 {VER}  1:1', fontsize=11)
ax.text(20, 278, '「実際のサイズ」(100%)で印刷。下の 50mm の線をものさしで測って確かめる', fontsize=8)
ax.text(20, 272, '実線: 切る線 / 青い点線: 折る線(枠の外のふち)。点線の外 1.0mm を下へ折って垂らす', fontsize=8)
ax.text(20, 266, f'枠(一次スカート t24v3)の外 {2 * X_OUT:g} × {2 * Y_OUT:g}mm・幅 {W}mm。四隅の {HANG} × {HANG}mm は切り落とす', fontsize=8)
ax.plot([20, 70], [30, 30], 'k-', lw=0.8)
ax.plot([20, 20], [30, 80], 'k-', lw=0.8)
ax.text(22, 33, '50 mm', fontsize=8)
ax.text(22, 75, '50 mm', fontsize=8)
fig.savefig(os.path.join(HERE, f'film_{VER}_template_A4_1to1.pdf'))
fig.savefig(os.path.join(HERE, f'film_{VER}_template.png'), dpi=110)
print(f'フィルム {VER}: 外 {2 * (X_OUT + HANG):g} × {2 * (Y_OUT + HANG):g}mm、内 {2 * (X_OUT - W):g} × {2 * (Y_OUT - W):g}mm、面積 {film.area:.0f} mm²')

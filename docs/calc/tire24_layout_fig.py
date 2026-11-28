"""タイヤ24mm・71T:13T・フレーム70mm の配置の略図(2026-11-21)
使い方(リポジトリの一番上で): python3 docs/calc/tire24_layout_fig.py → docs/img/tire24/layout_v3.png
座標は機体と同じ(原点は車軸の中心の真下の床、+x が前、+y が左、z は床から上、mm)。
灰色の点線は main(タイヤ15mm、41T:13T)。フレームの外形・基板は略図。高さ方向(モーター・基板)はまだ決めていない"""
import math, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon, Wedge

plt.rcParams['font.family'] = 'WenQuanYi Zen Hei'
plt.rcParams['axes.unicode_minus'] = False   # このフォントには U+2212 がない
OUT = 'docs/img/tire24/layout_v3.png'

# 新しい並び(右側、y の範囲)
AX = 12.0                      # 車軸の高さ
TIRE = (-33.3, -24.8, 10.0, 12.0)   # y0, y1, ホイールの外径の半径, タイヤの半径
SPUR = (-24.8, -22.8, 10.95)
BRG_O = (-23.2, -21.2); BRG_I = (-21.0, -19.0)
MAG = (-20.2, -19.2); CHIP = (-18.7, -17.5); ENC = (-17.5, -16.9)
ENC_Z = (8.15, 16.9); CHIP_Z = (8.8, 15.2)   # チップは TSSOP-16、足まで入れて縦6.4mm、中心 z 12.0
PCB_Z = (13.6, 14.2); PCB_EDGE = -16.7   # メイン基板(0.6mm)。車軸のまわり(x ±4.5)は |y| > 16.7 を切り欠く(軸受・マウント・チップが通る)
PIN = (-25.6 + 3.5 - 3.5, None)
MOTOR_Z = 8.2                          # マウント t24v2: 筒(壁0.9mm)の下の壁がフレームの上面に載り、上がメイン基板の 0.25mm 下(v2 の図までは 8.4)
MOTOR_DEG = -math.degrees(math.asin((AX - MOTOR_Z) / 12.6))   # -16.6°
MOTOR_X = -12.6 * math.cos(math.radians(MOTOR_DEG))
FRAME_Y = 35.0; FRAME_X = (-50, 50); FRAME_Z = (2.0, 3.0)
# main
M_AX = 7.5; M_TIRE = (-31.8, -28.3, 5.75, 7.5); M_SPUR = (-28.3, -26.3, 6.45)

C = dict(tire='#3b3b3b', wheel='#9aa5b1', spur='#d9822b', brg='#4a7ab5', mag='#c23b3b',
         enc='#2e8b57', frame='#555555', motor='#7d5ba6', main='#aaaaaa', suck='#cfe3f5')

fig = plt.figure(figsize=(15, 10.5), dpi=110)
gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.05], width_ratios=[1, 1.15])
ax1 = fig.add_subplot(gs[0, 0]); ax2 = fig.add_subplot(gs[0, 1]); ax3 = fig.add_subplot(gs[1, :])


def rect(ax, y0, y1, z0, z1, **kw):
    ax.add_patch(Rectangle((min(y0, y1), z0), abs(y1 - y0), z1 - z0, **kw))


# ---- 1. 正面(車軸を通る断面、右側) ----
ax = ax1
ax.axhline(0, color='k', lw=1)
# main(点線)
y0, y1, rw, rt = M_TIRE
rect(ax, y0, y1, M_AX - rt, M_AX + rt, fill=False, ec=C['main'], ls='--', lw=1.2)
rect(ax, M_SPUR[0], M_SPUR[1], M_AX - M_SPUR[2], M_AX + M_SPUR[2], fill=False, ec=C['main'], ls=':', lw=1.2)
# フレーム
rect(ax, -FRAME_Y, -22.3, *FRAME_Z, fc='none', ec=C['frame'], hatch='////', lw=0.8)
rect(ax, -22.3, 0, *FRAME_Z, fc='#bbbbbb', ec=C['frame'], lw=0.8)
ax.annotate('フレームはここで切り欠き\n(|y| > 22.3)', (-30, 2.5), (-37.5, -5.5), fontsize=8,
            arrowprops=dict(arrowstyle='->', lw=0.7))
# タイヤとホイール
y0, y1, rw, rt = TIRE
for s in (1, -1):
    rect(ax, y0, y1, AX + s * rw, AX + s * rt, fc=C['tire'], ec='k', lw=0.6)
rect(ax, y0, y1, AX - rw, AX + rw, fc=C['wheel'], ec='k', lw=0.6, alpha=0.6)
rect(ax, *SPUR[:2], AX - SPUR[2], AX + SPUR[2], fc=C['spur'], ec='k', lw=0.6)
rect(ax, -29.7 + 3.5, -23.7 + 3.5, AX - 1.5, AX + 1.5, fc='#e0e0e0', ec='k', lw=0.6)   # 平行ピン
for b in (BRG_O, BRG_I):
    rect(ax, *b, AX - 3.0, AX + 3.0, fc=C['brg'], ec='k', lw=0.6, alpha=0.8)
rect(ax, *MAG, AX - 1.5, AX + 1.5, fc=C['mag'], ec='k', lw=0.6)
rect(ax, *CHIP, *CHIP_Z, fc='#222', ec='k', lw=0.6)
rect(ax, *ENC, *ENC_Z, fc=C['enc'], ec='k', lw=0.6)
rect(ax, PCB_EDGE, 0, *PCB_Z, fc='#6aa56a', ec='k', lw=0.6)
rect(ax, -23.4, -18.8, AX - 3.6, AX + 3.6, fill=False, ec='#555', ls=':', lw=0.9)
A = dict(arrowstyle='->', lw=0.6)
def lab(txt, xy, xyt, color='k', **kw):
    ax.annotate(txt, xy, xyt, fontsize=7.5, color=color, arrowprops=dict(A, color=color), **kw)
lab('マウント(軸受の受け、上 z 約15.6)', (-21, AX + 3.6), (-14, 26.5), '#555')
lab('エンコーダ基板 z 8.15〜16.9\n(メイン基板の縁に沿って立て、\n 上ではんだ付け)', (-17.2, 16.5), (-12.5, 21.0), C['enc'])
lab('MT6835(中心 z 12.0、z 8.8〜15.2)', (-18.1, 9.5), (-14.0, -3.5), '#222')
lab('磁石', (-19.7, AX - 1.5), (-17.5, 0.8), C['mag'])
lab('軸受×2', (-22.2, AX - 3.0), (-23.5, -2.5), C['brg'])
lab('メイン基板 z 13.6〜14.2(main と同じ)\n車軸のまわり x ±4.5 は\ny < -16.7 を切り欠く', (-8, 13.6), (-14.8, 6.0), '#2e6b2e')
ax.plot([-16.0, -16.0], [PCB_Z[1], 20.0], color='#b8860b', lw=0.8, ls='--')
lab('電池・ホルダ(|y| ≤ 17.3)', (-16.0, 19.0), (-7.5, 16.0), '#b8860b')
ax.axvline(-FRAME_Y, color=C['frame'], lw=0.8, ls='-.')
ax.text(-35.6, 14, 'フレームの端 y -35.0', fontsize=8, rotation=90, ha='right', va='center')
ax.text(-29.05, 24.6, 'タイヤ 24mm × 8.5mm\n(y -33.3〜-24.8)', fontsize=8, ha='center')
ax.text(-23.8, 23.6, '71T', fontsize=8, ha='center')
ax.text(-37.5, -9.5, '灰色の点線: main(タイヤ15mm・41T、車軸 7.5mm)', fontsize=8, color='#777')
ax.plot([-33.3, -24.8], [AX, AX], color='w', lw=0.5)
ax.axhline(AX, color='#c00', lw=0.6, ls=':')
ax.text(-1, AX + 0.4, '車軸 z 12.0', fontsize=8, color='#c00', ha='right')
ax.set_xlim(-38, 0); ax.set_ylim(-11, 28); ax.set_aspect('equal')
ax.set_xlabel('y [mm](右が内側)'); ax.set_ylabel('z [mm]')
ax.set_title('1. 正面(車軸を通る断面、右側)')
ax.grid(alpha=0.2)

# ---- 2. 横(右から見る) ----
ax = ax2
ax.axhline(0, color='k', lw=1)
ax.add_patch(Circle((0, M_AX), 7.5, fill=False, ec=C['main'], ls='--', lw=1.2))
ax.add_patch(Circle((0, M_AX), 6.45, fill=False, ec=C['main'], ls=':', lw=1.2))
ma = math.radians(5); ax.add_patch(Circle((-8.1 * math.cos(ma), M_AX + 8.1 * math.sin(ma)), 4.3, fill=False, ec=C['main'], ls='--', lw=1.2))
ax.add_patch(Circle((0, AX), 12.0, fc=C['tire'], ec='k', lw=0.6))
ax.add_patch(Circle((0, AX), 10.0, fc=C['wheel'], ec='k', lw=0.6))
ax.add_patch(Circle((0, AX), 10.95, fill=False, ec=C['spur'], lw=1.5))
rect(ax, -50, -8.5, *FRAME_Z, fc='#bbbbbb', ec=C['frame'], lw=0.8)
rect(ax, 8.5, 50, *FRAME_Z, fc='#bbbbbb', ec=C['frame'], lw=0.8)
# モーターの中心が通れる円(軸間12.6)
ax.add_patch(Circle((0, AX), 12.6, fill=False, ec=C['motor'], ls='--', lw=0.8))
ax.add_patch(Circle((MOTOR_X, MOTOR_Z), 4.3, fc=C['motor'], alpha=0.45, ec=C['motor']))
ax.add_patch(Circle((MOTOR_X, MOTOR_Z), 5.15, fill=False, ec=C['motor'], ls=':', lw=0.8))
ax.text(-49, 33.5, f'モーター(φ8.6)は下に(2026-11-21決定)\n  中心 x {MOTOR_X:.2f}、z {MOTOR_Z:.1f}(車軸から{MOTOR_DEG:.1f}°、軸間 12.6mm)\n'
        f'  モーターの下 z {MOTOR_Z-4.3:.1f}、上 z {MOTOR_Z+4.3:.1f}\n  点線はマウントの筒(壁0.9mm): z {MOTOR_Z-5.15:.2f}〜{MOTOR_Z+5.15:.2f}(フレームの上面に載る。吸引する面には入れない)', fontsize=8, va='top', color=C['motor'])
ax.axhspan(13.6, 14.2, color='#6aa56a', alpha=0.5); ax.text(49, 14.6, 'メイン基板 z 13.6〜14.2(main と同じ。車輪の所は x ±12.5 を切り欠く)', fontsize=8, color='#2e6b2e', ha='right')
ax.text(13, -1.5, '71T の一番下 z 1.05', fontsize=8, color=C['spur'])
ax.text(49, 31, '横から見るとモーターがタイヤに重なって見えるが、\nモーターはタイヤより内側(y が違う)なので当たらない', fontsize=8, ha='right', va='top')
ax.set_xlim(-50, 50); ax.set_ylim(-3, 34); ax.set_aspect('equal')
ax.set_xlabel('x [mm](右が前)'); ax.set_ylabel('z [mm]')
ax.set_title('2. 横(右から見る)')
ax.grid(alpha=0.2)

# ---- 3. 上から ----
ax = ax3
# フレーム(略図: 前後100 × 左右70、角を落とした八角形)
ch = 10
frame = [(-50 + ch, -35), (50 - ch, -35), (50, -35 + ch), (50, 35 - ch), (50 - ch, 35), (-50 + ch, 35), (-50, 35 - ch), (-50, -35 + ch)]
ax.add_patch(Polygon(frame, closed=True, fc='#ececec', ec=C['frame'], lw=1))
ax.add_patch(Rectangle((-30, -15), 60, 30, fc=C['suck'], ec='#7aa7d6', lw=0.8))
ax.text(0, 0, '吸引する面 60 × 30(main)', fontsize=9, ha='center', va='center', color='#3b6fa8')
for s in (1, -1):
    # 切り欠き
    ax.add_patch(Rectangle((-12.8, 22.3 if s > 0 else -35.5), 25.6, 13.2, fc='white', ec=C['frame'], lw=0.8, ls='--'))
    yy = (24.8, 33.3) if s > 0 else (-33.3, -24.8)
    ax.add_patch(Rectangle((-12, yy[0]), 24, 8.5, fc=C['tire'], ec='k', lw=0.6, alpha=0.85))
    sy = (22.8, 24.8) if s > 0 else (-24.8, -22.8)
    ax.add_patch(Rectangle((-10.95, sy[0]), 21.9, 2, fc=C['spur'], ec='k', lw=0.6))
    ey = (16.9, 17.5) if s > 0 else (-17.5, -16.9)
    ax.add_patch(Rectangle((-3, ey[0]), 6, 0.6, fc=C['enc'], ec='k', lw=0.6))
    # main のタイヤ
    my = (28.3, 31.8) if s > 0 else (-31.8, -28.3)
    ax.add_patch(Rectangle((-7.5, my[0]), 15, 3.5, fill=False, ec=C['main'], ls='--', lw=1.2))
    # モーター(車軸と平行。前の面 |y| 21.5、長さ20)
    my0 = 1.5 if s > 0 else -21.5
    ax.add_patch(Rectangle((MOTOR_X - 4.3, my0), 8.6, 20, fc=C['motor'], alpha=0.3, ec=C['motor'], lw=0.8))
ax.text(-17.5, 3.5, 'モーター\n左右の間 3mm', fontsize=8, color=C['motor'], ha='right', va='center')
ax.text(0, 36.5, 'タイヤ 24 × 8.5mm(y ±24.8〜±33.3)、71T(±22.8〜±24.8)、エンコーダ基板(±16.9〜±17.5)', fontsize=9, ha='center')
ax.text(0, -38.5, 'フレームの端 y ±35.0(タイヤより1.7mm外、MK3と同じ)。白い点線の四角が切り欠き。トレッド 58.1mm', fontsize=9, ha='center')
ax.annotate('main のタイヤ(灰色の点線)', (7.5, -30), (20, -28), fontsize=8, color='#777', arrowprops=dict(arrowstyle='->', lw=0.7, color='#777'))
ax.annotate('モーターは吸引する面の上を通る\n(モーターの下はシートの0.7mm上。筒は入れない)', (-12.6, -10), (-53, -24), fontsize=8, color=C['motor'], arrowprops=dict(arrowstyle='->', lw=0.7, color=C['motor']))
ax.text(46, 0, '前 →', fontsize=10, ha='right', va='center')
ax.set_xlim(-55, 55); ax.set_ylim(-41, 39); ax.set_aspect('equal')
ax.set_xlabel('x [mm](右が前)'); ax.set_ylabel('y [mm](上が左)')
ax.set_title('3. 上から(フレームの外形は略図)')
ax.grid(alpha=0.2)

fig.suptitle('タイヤ24mm・71T:13T・フレーム70mm の配置(2026-11-21、v3 略図: マウント t24v2・エンコーダ基板 t24 の値)', fontsize=13)
fig.tight_layout()
os.makedirs(os.path.dirname(OUT), exist_ok=True)
fig.savefig(OUT)
print(OUT)

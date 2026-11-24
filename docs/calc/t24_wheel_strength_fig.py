"""車輪の軸の強さの図(2026-11-24)。使い方: python3 docs/calc/t24_wheel_strength_fig.py → docs/img/tire24/wheel_strength.png
左: 右の車輪の軸のまわりの断面(車軸を通る縦の面、x = 0)。部品の位置は機体のモデル(mechanical/vehicle/t24_mass.py)と同じ。
    タイヤが床から受ける力(縦 N、横 F)と、それを2つの軸受が受ける力を矢印で描く。
右上: 軸受の荷重と静定格荷重 C0r。右下: ホイールのピンの穴の縁の面圧(3×6 を 3mm、3×8 を 5mm)
数字は t24_wheel_strength.py と同じ計算"""
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
import t24_wheel_strength as ws

plt.rcParams['font.family'] = 'IPAGothic'
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '../img/tire24/wheel_strength.png')
AZ = 12.0          # 車軸の高さ


def ring(ax, y0, y1, r0, r1, color, label=None, alpha=1.0, hatch=None):
    """車軸のまわりの輪(断面では上と下に2つの四角)"""
    for sign in (1, -1):
        z0 = AZ + sign * r0
        z1 = AZ + sign * r1
        ax.add_patch(Rectangle((y0, min(z0, z1)), y1 - y0, abs(z1 - z0), facecolor=color, edgecolor='k', lw=0.5,
                               alpha=alpha, hatch=hatch, label=label if sign == 1 else None))


def section(ax, pin_y0, title):
    """断面の図。pin_y0: 平行ピンの外の端の y(3×6 は -26.2、3×8 は -28.2)"""
    ring(ax, -33.3, -24.8, 10.0, 12.0, '#333333', 'タイヤ(φ24)')
    ring(ax, -33.3, -24.8, 9.2, 10.0, '#e8b04a', 'ホイール(樹脂)')
    ring(ax, -25.8, -24.8, 2.5, 9.2, '#e8b04a')
    hub_y0 = pin_y0 - 1.0
    ring(ax, hub_y0, -24.8, 1.5, 2.5, '#e8b04a')
    ring(ax, -24.8, -23.4, 1.5, 3.8, '#e8b04a')
    ring(ax, -23.4, -23.2, 1.5, 1.9, '#e8b04a')
    ring(ax, -24.8, -22.8, 4.0, 10.65, '#8fbf8f', '71T')
    ring(ax, -23.2, -21.2, 1.5, 3.0, '#4a7ab5', '軸受 LF-630')
    ring(ax, -21.0, -19.0, 1.5, 3.0, '#4a7ab5')
    ring(ax, -22.1, -16.5, 3.0, 5.0, '#f2c49b', 'モーターマウント', alpha=0.6)
    # 平行ピン(ハッチ)と磁石
    ax.add_patch(Rectangle((pin_y0, AZ - 1.5), -20.2 - pin_y0, 3.0, facecolor='#b0b0b0', edgecolor='k', lw=0.8, hatch='///', label='平行ピン φ3'))
    ax.add_patch(Rectangle((-20.2, AZ - 1.5), 1.0, 3.0, facecolor='#c0392b', edgecolor='k', lw=0.5, label='磁石'))
    ax.add_patch(Rectangle((-18.7, 9.5), 1.2, 5.0, facecolor='#111111', edgecolor='k', lw=0.5, label='MT6835'))
    ax.add_patch(Rectangle((-17.5, 8.15), 0.6, 8.75, facecolor='#2e8b57', edgecolor='k', lw=0.5, label='エンコーダ基板'))
    ax.plot([-40, -14], [0, 0], color='#7a5c3a', lw=2)
    ax.text(-15.2, -0.9, '床', fontsize=9, color='#7a5c3a')
    # 床からタイヤへの力(タイヤの真ん中 y -29.05)
    n, f = ws.wheel_loads(600)
    yt = ws.Y_TIRE
    ax.add_patch(FancyArrowPatch((yt, -4.0), (yt, -0.2), arrowstyle='-|>', mutation_scale=14, color='#d62728', lw=2))
    ax.text(yt + 0.3, -3.6, f'縦 N {n:.1f}N', color='#d62728', fontsize=9)
    ax.add_patch(FancyArrowPatch((yt - 6.5, 0.6), (yt - 0.3, 0.6), arrowstyle='-|>', mutation_scale=14, color='#1f77b4', lw=2))
    ax.text(yt - 10.5, 0.2, f'横 F {f:.1f}N\n(内向き)', color='#1f77b4', fontsize=9)
    # 腕の長さ
    ax.annotate('', (yt - 1.0, AZ), (yt - 1.0, 0), arrowprops=dict(arrowstyle='<->', color='#1f77b4'))
    ax.text(yt - 4.6, 6.0, '半径\n12mm', color='#1f77b4', fontsize=9)
    ax.annotate('', (yt, 25.2), (ws.Y_BRG_OUT, 25.2), arrowprops=dict(arrowstyle='<->', color='#d62728'))
    ax.text(yt + 1.0, 25.6, '6.85mm', color='#d62728', fontsize=8)
    # 軸受の受ける力(悪い場合の足し合わせ)
    m = ws.moment(n, f, False)
    span = 1.6
    r_in = m / span
    r_out = r_in + n
    for y, r, txt in ((-22.2, -r_out, f'外の軸受\n{r_out:.0f}N'), (-20.6, r_in, f'内の軸受\n{r_in:.0f}N')):
        z0 = AZ + 3.2 if r < 0 else AZ - 3.2
        z1 = z0 + (-1 if r < 0 else 1) * 0
        ax.add_patch(FancyArrowPatch((y, AZ + (7.5 if r < 0 else -7.5)), (y, AZ + (3.2 if r < 0 else -3.2)),
                                     arrowstyle='-|>', mutation_scale=14, color='#9467bd', lw=2))
        ax.text(y + 0.2, AZ + (6.0 if r < 0 else -8.5), txt, color='#9467bd', fontsize=8)
    # ピンのかかり
    ax.annotate('内の軸受にかかる\nピンは 0.8mm だけ\n(残りは磁石)', (-20.6, AZ + 1.6), (-19.6, 20.5), fontsize=8,
                arrowprops=dict(arrowstyle='->', color='k'))
    depth = -23.2 - pin_y0
    ax.annotate(f'ホイールに圧入 {depth:.0f}mm', ((pin_y0 - 23.2) / 2, AZ - 1.6), ((pin_y0 - 23.2) / 2 - 4, 5.5), fontsize=9,
                arrowprops=dict(arrowstyle='->', color='k'))
    ax.set_xlim(-40, -14.5)
    ax.set_ylim(-4.5, 27)
    ax.set_aspect('equal')
    ax.set_xlabel('y [mm](左が外)')
    ax.set_ylabel('z [mm](床から)')
    ax.set_title(title, fontsize=10)


fig = plt.figure(figsize=(15, 13))
gs = fig.add_gridspec(2, 2, height_ratios=[1.35, 1.0])
ax1 = fig.add_subplot(gs[0, 0])
section(ax1, -26.2, 't24v1: 平行ピン 3×6 をホイールに 3mm(吸引 600g、横と縦を足し合わせた悪い場合)')
fig.legend(*ax1.get_legend_handles_labels(), loc='upper center', bbox_to_anchor=(0.5, 0.955), ncol=9, fontsize=9)
ax2 = fig.add_subplot(gs[0, 1])
section(ax2, -28.2, 't24v2: 平行ピン 3×8 をホイールに 5mm(ピンの内の端・磁石・エンコーダは同じ)')

# 軸受の荷重
ax3 = fig.add_subplot(gs[1, 0])
labels, now, through = [], [], []
for suction in (600, 1000):
    n, f = ws.wheel_loads(suction)
    for cancel, tag in ((True, 'ターン'), (False, '足し合わせ')):
        m = ws.moment(n, f, cancel)
        labels.append(f'{suction}g\n{tag}')
        now.append(m / 1.6 + n)
        through.append(m / 2.2 + n)
xs = range(len(labels))
ax3.bar([x - 0.2 for x in xs], now, 0.4, color='#9467bd', label='今(軸受の間 1.6mm)')
ax3.bar([x + 0.2 for x in xs], through, 0.4, color='#c5b0d5', label='ピンが内の軸受を通る(2.2mm)')
ax3.axhline(ws.C0R, color='r', ls='--')
ax3.text(-0.45, ws.C0R + 3, f'静定格荷重 C0r {ws.C0R:.0f}N(玉に跡が付き始める)', color='r', fontsize=8)
ax3.set_xticks(list(xs))
ax3.set_xticklabels(labels, fontsize=8)
ax3.set_ylabel('外の軸受の荷重 [N]')
ax3.set_title('軸受 LF-630ZZ の荷重(タイヤが滑る限界)', fontsize=10)
ax3.legend(fontsize=8, loc='upper left')

# ホイールの穴の面圧
ax4 = fig.add_subplot(gs[1, 1])
labels, p3, p5 = [], [], []
for suction in (600, 1000):
    n, f = ws.wheel_loads(suction)
    m = ws.moment(n, f, False)
    labels.append(f'吸引 {suction}g')
    p3.append(6 * m / (3.0 * 3.0**2))
    p5.append(6 * m / (3.0 * 5.0**2))
xs = range(len(labels))
ax4.bar([x - 0.2 for x in xs], p3, 0.4, color='#e8b04a', label='3×6 を 3mm(t24v1)')
ax4.bar([x + 0.2 for x in xs], p5, 0.4, color='#a0522d', label='3×8 を 5mm(t24v2)')
ax4.axhspan(60, 71, color='r', alpha=0.15)
ax4.text(-0.45, 62, '樹脂の引っ張り強さ(Temp Resin 60〜71MPa)', color='r', fontsize=8)
ax4.set_xticks(list(xs))
ax4.set_xticklabels(labels)
ax4.set_ylim(0, 80)
ax4.set_ylabel('ピンの穴の縁の面圧 [MPa]')
ax4.set_title('ホイール(樹脂)のピンの穴(悪い場合)', fontsize=10)
ax4.legend(fontsize=8, loc='upper left')
fig.suptitle('車輪の軸の強さ(右の車輪、外のタイヤが滑る限界の力。平行ピンの曲げは 53〜85MPa で十分)', fontsize=12)
fig.tight_layout(rect=(0, 0, 1, 0.94))
fig.savefig(OUT, dpi=110)
print(OUT)

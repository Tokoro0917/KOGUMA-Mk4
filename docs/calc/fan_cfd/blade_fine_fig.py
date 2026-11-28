"""羽根の形の比べのうち、細かいメッシュで確かめた 3 つ(C 案 φ30、35,000rpm)を、上から見た羽根の形と棒グラフで見せる(2026-11-25)。
使い方(リポジトリの一番上から): python3 docs/calc/fan_cfd/blade_fine_fig.py
  → docs/img/tire24/fan_blade_fine.png
数値は post.py の出力(細かいメッシュ、くり返し 1,500 回)を書き写したもの。
羽の形は make_case.py の blade() と同じ式(内の端から外へ、回る向きと逆へ log で曲がる)で描く"""
import math
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', '..', 'img', 'tire24', 'fan_blade_fine.png')

R_TIP = 15.0          # 羽の先(φ30)
R_INNER = 5.0         # 羽の内の端
R_RIM = 15.6          # 回る外の壁の外(厚さ 0.6)
RING_IN = 16.5        # 止まった輪(ファンの台)
RING_OUT = 17.5
R_HOLE = 7.5          # フレームの吸い込みの穴(φ15)

# (名前, 羽の枚数, 曲げ [°], 吸引 [g], 羽根を回す電力 [W])
CASES = [
    ('基準(今)\n5枚・曲げ 60°', 5, 60, 254, 3.90),
    ('7枚・曲げ 75°', 7, 75, 254, 3.54),
    ('9枚・曲げ 60°', 9, 60, 273, 3.98),
]
COLORS = ['#3d3d3d', '#e07b00', '#e07b00']


def equal_suction_power(suction_g, power_w):
    """吸引を基準(254g)にそろえたときの電力 [W]。吸引は回転数の2乗、電力は3乗に比例するとして換算"""
    base_suction = CASES[0][3]
    return power_w * (base_suction / suction_g) ** 1.5


def draw_impeller(ax, n_blades, sweep_deg):
    """上から見た羽根(羽・回る外の壁・止まった輪・吸い込みの穴)を描く"""
    # 止まった輪(灰色の太い輪)
    ax.add_patch(plt.Circle((0, 0), RING_OUT, color='#d0d0d0'))
    ax.add_patch(plt.Circle((0, 0), RING_IN, color='white'))
    # 回る外の壁
    ax.add_patch(plt.Circle((0, 0), R_RIM, color='#7a9cc6'))
    ax.add_patch(plt.Circle((0, 0), R_TIP, color='#eef3fa'))
    # 吸い込みの穴(点線)
    ax.add_patch(plt.Circle((0, 0), R_HOLE, fill=False, ls='--', color='#888888', lw=1))
    # 羽
    for k in range(n_blades):
        xs = []
        ys = []
        for i in range(41):
            r = R_INNER + (R_TIP - R_INNER) * i / 40
            th = math.radians(360.0 / n_blades * k) - math.radians(sweep_deg) * math.log(r / R_INNER) / math.log(R_TIP / R_INNER)
            xs.append(r * math.cos(th))
            ys.append(r * math.sin(th))
        ax.plot(xs, ys, color='#1f3b66', lw=2.2, solid_capstyle='butt')
    # 回る向き(反時計回り)の矢印
    ax.annotate('', xy=(-12.5, 12.5), xytext=(-2, 17.0),
                arrowprops=dict(arrowstyle='->', color='#c0392b', lw=1.5, connectionstyle='arc3,rad=0.3'))
    ax.set_xlim(-19, 19)
    ax.set_ylim(-19, 19)
    ax.set_aspect('equal')
    ax.axis('off')


plt.rcParams['font.family'] = 'IPAPGothic'
fig = plt.figure(figsize=(11, 8))

# 上の段: 3 つの羽根の形
for i in range(len(CASES)):
    name, n_blades, sweep_deg, suction_g, power_w = CASES[i]
    ax = fig.add_axes([0.04 + i * 0.32, 0.47, 0.28, 0.40])
    draw_impeller(ax, n_blades, sweep_deg)
    ax.set_title(name, fontsize=13, color=COLORS[i])

# 下の段の左: 同じ吸引にしたときの電力
names = []
powers = []
suctions = []
for name, n_blades, sweep_deg, suction_g, power_w in CASES:
    names.append(name.replace('\n', ' '))
    powers.append(equal_suction_power(suction_g, power_w))
    suctions.append(suction_g)
y = [0, 1, 2]

ax1 = fig.add_axes([0.22, 0.08, 0.32, 0.28])
ax1.barh(y, powers, color=COLORS, height=0.6)
for i in range(3):
    diff = (powers[i] / powers[0] - 1) * 100
    text = f'{powers[i]:.2f}W'
    if i > 0:
        text = text + f'({diff:+.0f}%)'
    ax1.text(powers[i] + 0.05, i, text, va='center', fontsize=11)
ax1.set_xlim(0, 5.2)
ax1.set_yticks(y)
ax1.set_yticklabels(names, fontsize=11)
ax1.invert_yaxis()
ax1.set_title('吸引を 254g にそろえたときの電力(短いほどよい)', fontsize=12)

# 下の段の右: 同じ回転数での吸引
ax2 = fig.add_axes([0.62, 0.08, 0.30, 0.28], sharey=ax1)
ax2.barh(y, suctions, color=COLORS, height=0.6)
for i in range(3):
    ax2.text(suctions[i] + 4, i, f'{suctions[i]}g', va='center', fontsize=11)
ax2.set_xlim(0, 330)
ax2.set_title('同じ 35,000rpm での吸引(長いほどよい)', fontsize=12)
plt.setp(ax2.get_yticklabels(), visible=False)

for ax in (ax1, ax2):
    ax.set_xticks([])
    for side in ('top', 'right', 'bottom', 'left'):
        ax.spines[side].set_visible(False)
    ax.tick_params(axis='y', length=0)

fig.suptitle('羽根の枚数と曲げ(C 案 φ30、流体の計算、細かいメッシュ)', fontsize=15)
fig.text(0.02, 0.015,
         '濃い青 = 羽、薄い青 = 回る外の壁、灰色 = 止まった輪(ファンの台)、点線 = フレームの吸い込みの穴(φ15)、赤い矢印 = 回る向き。'
         'スカートと床のすき間 0.15mm での計算',
         fontsize=9, color='#444444')
fig.savefig(OUT, dpi=150)
print(OUT)

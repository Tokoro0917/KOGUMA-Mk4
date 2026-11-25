"""羽根の形の比べ(C 案 φ30、粗いメッシュ、35,000rpm)の結果を棒グラフにする(2026-11-25)。
使い方(リポジトリの一番上から): python3 docs/calc/fan_cfd/blade_screen_fig.py
  → docs/img/tire24/fan_blade_screen.png
数値は post.py の出力(くり返し 1,200 回)を書き写したもの。
「同じ吸引に要る電力」は、吸引が回転数の2乗、電力が3乗に比例するとして、電力 ÷ 吸引^1.5 を基準と比べた値"""
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', '..', 'img', 'tire24', 'fan_blade_screen.png')

# (名前, 吸引 [g], 羽根を回す電力 [W])。書いていない所は基準と同じ(5枚・曲げ 60°・高さ 3.9mm・内の端 半径 5mm)
CASES = [
    ('基準 5枚・60°', 233, 3.65),
    ('3枚', 208, 3.41),
    ('4枚', 235, 3.78),
    ('7枚・60°', 248, 3.67),
    ('9枚・60°', 260, 3.93),
    ('曲げ 0°', 242, 4.02),
    ('曲げ 30°', 236, 3.89),
    ('曲げ 90°', 226, 3.11),
    ('3枚・0°', 200, 3.54),
    ('4枚・0°', 228, 3.92),
    ('7枚・75°', 248, 3.62),
    ('7枚・90°', 242, 3.46),
    ('9枚・90°', 249, 3.78),
    ('高さ 2.9mm', 211, 3.16),
    ('高さ 4.9mm', 247, 4.02),
    ('内の端 3.5mm', 235, 3.81),
    ('内の端 7mm', 218, 3.02),
]
CANDIDATES = ['7枚・75°', '9枚・60°']     # 細かいメッシュで確かめたもの
BASE = '基準 5枚・60°'

COLOR_CANDIDATE = '#e07b00'
COLOR_BASE = '#3d3d3d'
COLOR_OTHER = '#b0b0b0'


def power_ratio_percent(suction_g, power_w):
    """同じ吸引にしたときの電力を、基準と比べた差 [%]"""
    base_suction = CASES[0][1]
    base_power = CASES[0][2]
    ratio = (power_w / suction_g ** 1.5) / (base_power / base_suction ** 1.5)
    return (ratio - 1) * 100


def bar_color(name):
    if name in CANDIDATES:
        return COLOR_CANDIDATE
    if name == BASE:
        return COLOR_BASE
    return COLOR_OTHER


# 電力の少ない順(よい順)に並べる
rows = []
for name, suction_g, power_w in CASES:
    rows.append((power_ratio_percent(suction_g, power_w), name, suction_g))
rows.sort()
names = []
powers = []
suctions = []
colors = []
for power, name, suction_g in rows:
    names.append(name)
    powers.append(power)
    suctions.append(suction_g)
    colors.append(bar_color(name))

plt.rcParams['font.family'] = 'IPAPGothic'
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 7.5), sharey=True)
y = list(range(len(names)))

# 左: 同じ吸引に要る電力(小さいほどよい)
ax1.barh(y, powers, color=colors, height=0.7)
ax1.axvline(0, color='#3d3d3d', lw=1)
for i in range(len(names)):
    text = f'{powers[i]:+.0f}%'
    if powers[i] < 0:
        ax1.text(powers[i] - 0.5, i, text, va='center', ha='right', fontsize=10)
    else:
        ax1.text(powers[i] + 0.5, i, text, va='center', ha='left', fontsize=10)
ax1.set_xlim(-16, 27)
ax1.set_title('同じ吸引に要る電力(基準との差)\n左ほどよい', fontsize=12)
ax1.set_yticks(y)
ax1.set_yticklabels(names, fontsize=11)
ax1.invert_yaxis()

# 右: 同じ回転数での吸引(大きいほどよい)
ax2.barh(y, suctions, color=colors, height=0.7)
ax2.axvline(CASES[0][1], color='#3d3d3d', lw=1, ls='--', zorder=0)
for i in range(len(names)):
    ax2.text(suctions[i] + 2, i, f'{suctions[i]}g', va='center', ha='left', fontsize=10,
             bbox=dict(fc='white', ec='none', pad=1))       # 点線の上に字を重ねて読めるように
ax2.set_xlim(150, 285)
ax2.set_title('同じ 35,000rpm での吸引\n右ほどよい(点線は基準)', fontsize=12)

for ax in (ax1, ax2):
    ax.set_xticks([])
    for side in ('top', 'right', 'bottom', 'left'):
        ax.spines[side].set_visible(False)
    ax.tick_params(axis='y', length=0)

fig.suptitle('吸引ファンの羽根の形の比べ(C 案 φ30、流体の計算、粗いメッシュ)', fontsize=14)
fig.text(0.02, 0.025,
         'オレンジ = 細かいメッシュで確かめたもの(7枚・75°、9枚・60°。結果は fan_blade_fine.png)。黒 = 今の形。'
         '書いていない所は基準と同じ(5枚・曲げ 60°・高さ 3.9mm・内の端 半径 5mm)。\n'
         '粗いメッシュの値なので、細かいメッシュでは数 % 動くかもしれない。',
         fontsize=9.5, color='#444444')
fig.subplots_adjust(left=0.15, right=0.97, top=0.86, bottom=0.1, wspace=0.08)
fig.savefig(OUT, dpi=150)
print(OUT)

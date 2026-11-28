"""羽根の形の比べを、密閉に近い条件(スカートと床のすき間 0.05mm)でやり直した結果を、すき間 0.15mm の結果と並べて図にする
(2026-11-26、ユーザー「C案の羽根の形を密閉に近い条件で比べて」)。
使い方(リポジトリの一番上から): python3 docs/calc/fan_cfd/blade_seal_fig.py
  → docs/img/tire24/fan_blade_seal.png
数値は watch_steady.py の出力(C 案 φ30、35,000rpm、粗いメッシュ)を書き写したもの。落ち着いたところ(止めた回の前 3 回)の平均。
すき間 0.15mm の値は blade_screen_fig.py と同じ。
「同じ吸引に要る電力」は、吸引が回転数の2乗、電力が3乗に比例するとして、電力 ÷ 吸引^1.5 を基準と比べた値"""
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', '..', 'img', 'tire24', 'fan_blade_seal.png')

# (名前, すき間 0.05mm の吸引 [g], 電力 [W], すき間 0.15mm の吸引 [g], 電力 [W])
# 0.15mm で計算していない形は None。書いていない所は基準と同じ(5枚・曲げ 60°・高さ 3.9mm・内の端 半径 5mm)
CASES = [
    ('基準 5枚・60°', 341.7, 1.845, 233, 3.65),
    ('3枚', 305.4, 1.725, 208, 3.41),
    ('4枚', 322.9, 1.832, 235, 3.78),
    ('7枚・60°', 356.9, 1.853, 248, 3.67),
    ('9枚・60°', 361.9, 1.846, 260, 3.93),
    ('曲げ 0°', 336.8, 1.815, 242, 4.02),
    ('曲げ 30°', 342.0, 1.840, 236, 3.89),
    ('曲げ 90°', 336.7, 1.787, 226, 3.11),
    ('7枚・75°', 356.1, 1.852, 248, 3.62),
    ('7枚・0°', 354.3, 1.845, None, None),
    ('9枚・0°', 361.6, 1.849, None, None),
    ('高さ 2.9mm', 324.6, 1.736, 211, 3.16),
    ('高さ 4.9mm', 349.3, 1.894, 247, 4.02),
    ('内の端 3.5mm', 352.4, 1.887, 235, 3.81),
    ('内の端 7mm', 314.5, 1.744, 218, 3.02),
]

COLOR_SEAL = '#257de0'      # すき間 0.05mm(今回)
COLOR_LEAK = '#b8b8b8'      # すき間 0.15mm(前の比べ)
TEXT = '#333333'


def percent_vs_base(suction_g, power_w, base_suction_g, base_power_w):
    """同じ吸引にしたときの電力を、基準と比べた差 [%]"""
    ratio = (power_w / suction_g ** 1.5) / (base_power_w / base_suction_g ** 1.5)
    return (ratio - 1) * 100


# 基準の値
base_seal_g = CASES[0][1]
base_seal_w = CASES[0][2]
base_leak_g = CASES[0][3]
base_leak_w = CASES[0][4]

# すき間 0.05mm の電力の少ない順(よい順)に並べる
rows = []
for name, seal_g, seal_w, leak_g, leak_w in CASES:
    seal = percent_vs_base(seal_g, seal_w, base_seal_g, base_seal_w)
    leak = None
    if leak_g is not None:
        leak = percent_vs_base(leak_g, leak_w, base_leak_g, base_leak_w)
    seal = round(seal) + 0.0          # 整数の % にそろえる(-0.4 が「-0%」と出ないように。-0 に 0.0 を足すと 0.0 になる)
    rows.append((seal, name, leak, seal_g))
rows.sort()

plt.rcParams['font.family'] = 'IPAPGothic'
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 8), sharey=True, gridspec_kw={'width_ratios': [1.6, 1]})
BAR = 0.38

# 左: 同じ吸引に要る電力(基準との差)。青 = 0.05mm、灰色 = 0.15mm
for i in range(len(rows)):
    seal, name, leak, seal_g = rows[i]
    ax1.barh(i - BAR / 2, seal, color=COLOR_SEAL, height=BAR)
    if seal < 0:
        ax1.text(seal - 0.4, i - BAR / 2, f'{seal:+.0f}%', va='center', ha='right', fontsize=10, color=TEXT)
    else:
        ax1.text(seal + 0.4, i - BAR / 2, f'{seal:+.0f}%', va='center', ha='left', fontsize=10, color=TEXT)
    if leak is None:
        ax1.text(0.4, i + BAR / 2, '(0.15mm は計算なし)', va='center', ha='left', fontsize=8.5, color='#888888')
    else:
        ax1.barh(i + BAR / 2, leak, color=COLOR_LEAK, height=BAR)
        if leak < 0:
            ax1.text(leak - 0.4, i + BAR / 2, f'{leak:+.0f}%', va='center', ha='right', fontsize=8.5, color='#777777')
        else:
            ax1.text(leak + 0.4, i + BAR / 2, f'{leak:+.0f}%', va='center', ha='left', fontsize=8.5, color='#777777')
ax1.axvline(0, color='#3d3d3d', lw=1)
ax1.set_xlim(-15, 15)
ax1.set_title('同じ吸引に要る電力(基準との差)\n左ほどよい', fontsize=12, color=TEXT)
# 凡例(色の見本の四角を作って渡す)
legend_seal = Patch(color=COLOR_SEAL, label='すき間 0.05mm(密閉に近い)')
legend_leak = Patch(color=COLOR_LEAK, label='すき間 0.15mm(前の比べ)')
ax1.legend(handles=[legend_seal, legend_leak], loc='lower left', frameon=False, fontsize=10)

# 右: 同じ 35,000rpm での吸引(すき間 0.05mm)
names = []
for i in range(len(rows)):
    seal, name, leak, seal_g = rows[i]
    names.append(name)
    ax2.barh(i, seal_g, color=COLOR_SEAL, height=0.6)
    ax2.text(seal_g + 2, i, f'{seal_g:.0f}g', va='center', ha='left', fontsize=10, color=TEXT,
             bbox=dict(fc='white', ec='none', pad=1))       # 点線の上に字を重ねて読めるように
ax2.axvline(base_seal_g, color='#3d3d3d', lw=1, ls='--', zorder=0)
ax2.set_xlim(250, 390)
ax2.set_title('すき間 0.05mm・35,000rpm での吸引\n右ほどよい(点線は基準)', fontsize=12, color=TEXT)

ax1.set_yticks(list(range(len(names))))
ax1.set_yticklabels(names, fontsize=11)
ax1.invert_yaxis()
for ax in (ax1, ax2):
    ax.set_xticks([])
    for side in ('top', 'right', 'bottom', 'left'):
        ax.spines[side].set_visible(False)
    ax.tick_params(axis='y', length=0, colors=TEXT)

fig.suptitle('羽根の形の比べ・密閉に近いとき(C 案 φ30、流体の計算、粗いメッシュ)', fontsize=14, color=TEXT)
fig.text(0.02, 0.02,
         '書いていない所は基準と同じ(5枚・曲げ 60°・高さ 3.9mm・内の端 半径 5mm)。'
         '電力は、吸引が回転数の2乗、電力が3乗に比例するとして換算。\n'
         '密閉に近いと、効くのは羽根の枚数だけ。曲げはほとんど効かなくなり、内の端 7mm は逆に悪くなる。',
         fontsize=9.5, color='#555555')
fig.subplots_adjust(left=0.13, right=0.97, top=0.88, bottom=0.09, wspace=0.08)
fig.savefig(OUT, dpi=150)
print(OUT)

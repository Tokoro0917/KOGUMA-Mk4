"""スカートと床のすき間を変えたときの、C(回る外の壁 + 輪)と D(壁なし)の比べを図にする(2026-11-26、ユーザー
「吸引し始めるとスカートの中はほぼ密閉状態になる」)。
使い方(リポジトリの一番上から): python3 docs/calc/fan_cfd/leak_fig.py
  → docs/img/tire24/fan_cfd_leak.png
数値は post.py・watch_steady.py の出力(φ30、35,000rpm、粗いメッシュ)を書き写したもの。
D は羽根の先が開いていて値が ±3% ほど揺れ続けるので、最後の 600 回(1,000〜1,500 回)の平均。
C は落ち着いたところ(止めた回の前 3 回)の平均。
「同じ吸引にそろえた電力」は、吸引が回転数の2乗、電力が3乗に比例するとして、吸引 300g にそろえた値"""
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', '..', 'img', 'tire24', 'fan_cfd_leak.png')

GAP_MM = [0.0, 0.05, 0.10, 0.15]           # スカートと床のすき間
C_SUCTION_G = [383.7, 341.7, 301.8, 233.7]  # 35,000rpm での吸引
C_POWER_W = [0.715, 1.845, 2.987, 3.646]    # 35,000rpm での羽根を回す仕事
D_SUCTION_G = [339.7, 327.2, 332.3, 331.2]
D_POWER_W = [2.213, 2.696, 3.377, 3.743]
TARGET_G = 300.0                            # そろえる吸引

COLOR_C = '#257de0'
COLOR_D = '#f47230'
TEXT = '#333333'
GRID = '#e5e5e5'


def power_at_target(suction_g, power_w):
    """吸引を TARGET_G にそろえたときの電力 [W](回転数を変えたとして換算)"""
    return power_w * (TARGET_G / suction_g) ** 1.5


c_target = []
d_target = []
for i in range(len(GAP_MM)):
    c_target.append(power_at_target(C_SUCTION_G[i], C_POWER_W[i]))
    d_target.append(power_at_target(D_SUCTION_G[i], D_POWER_W[i]))

plt.rcParams['font.family'] = 'IPAPGothic'
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5.2))

# 左: 同じ 35,000rpm での吸引
ax1.plot(GAP_MM, C_SUCTION_G, color=COLOR_C, lw=2, marker='o', ms=8, label='C 回る外の壁 + 輪')
ax1.plot(GAP_MM, D_SUCTION_G, color=COLOR_D, lw=2, marker='s', ms=8, label='D 壁なし')
ax1.text(0.156, C_SUCTION_G[3], 'C', color=TEXT, va='center', fontsize=12)
ax1.text(0.156, D_SUCTION_G[3], 'D', color=TEXT, va='center', fontsize=12)
ax1.set_ylim(0, 420)
ax1.set_ylabel('吸引 [g](68 × 34mm の面)', color=TEXT)
ax1.set_title('同じ 35,000rpm での吸引(高いほどよい)', fontsize=12, color=TEXT)

# 右: 吸引 300g にそろえたときの電力
ax2.plot(GAP_MM, c_target, color=COLOR_C, lw=2, marker='o', ms=8, label='C 回る外の壁 + 輪')
ax2.plot(GAP_MM, d_target, color=COLOR_D, lw=2, marker='s', ms=8, label='D 壁なし')
ax2.text(0.156, c_target[3], 'C', color=TEXT, va='center', fontsize=12)
ax2.text(0.156, d_target[3], 'D', color=TEXT, va='center', fontsize=12)
ax2.axvline(0.10, color='#999999', lw=1, ls='--', zorder=0)
ax2.text(0.097, 5.5, '入れ替わる所(約 0.10mm)', ha='right', va='top', fontsize=10, color=TEXT)
ax2.text(0.097, 0.25, '← C がよい', fontsize=11, color=TEXT, ha='right')
ax2.text(0.103, 0.25, 'D がよい →', fontsize=11, color=TEXT, ha='left')
ax2.set_ylim(0, 5.6)
ax2.set_ylabel('羽根を回す電力 [W]', color=TEXT)
ax2.set_title('吸引 300g にそろえたときの電力(低いほどよい)', fontsize=12, color=TEXT)
ax2.legend(loc='upper left', bbox_to_anchor=(0.0, 0.85), frameon=False, fontsize=10)

for ax in (ax1, ax2):
    ax.set_xlim(-0.005, 0.175)
    ax.set_xticks(GAP_MM)
    ax.set_xticklabels(['0\n(密閉)', '0.05', '0.10', '0.15'])
    ax.set_xlabel('スカートと床のすき間 [mm]', color=TEXT)
    ax.grid(axis='y', color=GRID)
    ax.set_axisbelow(True)
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    for side in ('left', 'bottom'):
        ax.spines[side].set_color('#999999')
    ax.tick_params(colors=TEXT)

fig.suptitle('スカートのすき間と、ファンの形(φ30、流体の計算、粗いメッシュ)', fontsize=14, color=TEXT)
fig.text(0.02, 0.02,
         'すき間が小さいほど、空気は流れず、羽根は圧力だけを作る。C は囲った空気が一緒に回るので無駄が少ない。'
         'D は羽根の先で空気が出入りし続ける。\n'
         '電力は、吸引が回転数の2乗、電力が3乗に比例するとして換算。D の値は ±3% ほど揺れるので平均。',
         fontsize=9, color='#555555')
fig.subplots_adjust(left=0.07, right=0.96, top=0.86, bottom=0.2, wspace=0.25)
fig.savefig(OUT, dpi=150)
print(OUT)

"""吸引ファンの4つの形(A・B・C・D)のうち、どれが良かったかを1枚の PDF にする(日本語版と英語版、2026-11-25)。
D(壁のない普通のファン)は 2026-11-25 にユーザー「壁がない普通のファンの場合も同じ条件で」で足した。
2026-11-26: スカートと床のすき間を変えた C と D の比べ(leak_fig.py と同じ数値)を足し、答えを「すき間しだい」に直した(ユーザー「A~Dの報告PDF作って」)。
使い方(リポジトリの一番上から): python3 docs/calc/fan_cfd/report_pdf.py
  → docs/calc/fan_cfd/fan_cfd_report_ja.pdf、fan_cfd_report_en.pdf
A4 の大きさの matplotlib の図を、そのまま PDF で保存している。
数値は post.py の出力(2026-11-24、細かいメッシュ、くり返し 1,500 回)を書き写したもの。くわしくは README.md。"""
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- 計算の結果(35,000rpm、細かいメッシュ)----
D_SUCTION = 394      # D の吸引 [g](2026-11-25、細かいメッシュ、くり返し 1,500 回)
D_POWER = 5.64       # D の羽根を回す電力 [W]
CASES = ['A', 'B', 'C', 'D']
SUCTION_G = {'A': 277, 'B': 299, 'C': 323, 'D': D_SUCTION}     # 吸引 [g]
POWER_W = {'A': 4.28, 'B': 5.21, 'C': 5.11, 'D': D_POWER}      # 羽根を回す電力 [W]
BEST = 'D'                                                     # すき間 0.15mm で一番よかった形(2026-11-25 に C → D)
CHOICES = ['C', 'D']                                           # すき間しだいで選ぶ 2 つ(2026-11-26)

# ---- すき間を変えた比べ(φ30、粗いメッシュ。leak_fig.py と同じ数値)----
GAP_MM = [0.0, 0.05, 0.10, 0.15]
GAP_C_SUCTION_G = [383.7, 341.7, 301.8, 233.7]
GAP_C_POWER_W = [0.715, 1.845, 2.987, 3.646]
GAP_D_SUCTION_G = [339.7, 327.2, 332.3, 331.2]
GAP_D_POWER_W = [2.213, 2.696, 3.377, 3.743]
GAP_TARGET_G = 300.0          # そろえる吸引 [g]


def power_same_suction(case):
    """A と同じ吸引(277g)にそろえたときの電力。吸引は回転数の2乗、電力は3乗に比例するとして換算する"""
    speed_ratio = (SUCTION_G['A'] / SUCTION_G[case]) ** 0.5
    return POWER_W[case] * speed_ratio ** 3


# ---- 色 ----
COLOR_ROTOR = '#d9534f'     # 回る羽根
COLOR_RING = '#f0c040'      # 止まった輪
COLOR_FRAME = '#6b6b6b'     # フレーム
COLOR_PCB = '#3a9a5b'       # 基板
COLOR_MOTOR = '#b5b5b5'     # モーター
COLOR_AIR = '#2f6fd6'       # 空気の流れ
COLOR_BEST = '#e07b00'      # 一番よかったもの
COLOR_LINE_C = '#257de0'    # すき間の図の C
COLOR_LINE_D = '#f47230'    # すき間の図の D
COLOR_OTHER = '#9a9a9a'

# ---- 文章 ----
TEXT = {
    'ja': {
        'font': 'IPAPGothic',
        'dot': '・ ',
        'title': '吸引ファン 4つの形の比べ(流体の計算、35,000rpm)',
        'answer': '密閉に近いなら C、漏れが多いなら D',
        'reason': 'スカートと床のすき間 約 0.10mm で入れ替わる。実機のすき間を測って決める',
        'names': {'A': 'A  今の MK4', 'B': 'B  xfa273 さんの形', 'C': 'C  組み合わせ', 'D': 'D  壁なし'},
        'desc': {'A': '羽根だけ回る + 止まった輪', 'B': '外の壁も一緒に回る', 'C': '外の壁も回る + 止まった輪',
                 'D': '羽根だけ。輪も外の壁もない'},
        'legend': ['回る羽根', '止まった輪', 'フレーム', '基板', '空気'],
        'bar2': '① すき間 0.15mm: 同じ吸引(277g)に要る電力',
        'bar2_unit': 'W',
        'better2': '4つの形、φ32。小さいほどよい',
        'line': '② すき間を変えると: 同じ吸引(300g)に要る電力',
        'line_sub': 'C と D、φ30。小さいほどよい',
        'line_x': 'スカートと床のすき間 [mm]',
        'line_x0': '0\n(密閉)',
        'line_swap': '入れ替わる',
        'notes': [
            '① 漏れが多い(すき間 0.15mm)と D が一番よい。同じ吸引なら A より 22%、C より 18% 少ない電力。\n   輪や回る外の壁が、羽根から出た空気の出口を狭くしていた。',
            '② 密閉に近いほど C がよい。密閉では C は D の約 1/4 の電力。\n   C は囲った空気が一緒に回るので無駄が少ない。D は羽根の先で空気が出入りし続ける。',
            'A・B はすき間 0.15mm だけで計算した。まわりの部品(マウント・タイヤなど)を入れても、\n   ①の結果はほぼ変わらなかった。',
            '吸引の力とファンの電流を実機で測ってすき間を見積もり、印刷した羽根で決める。',
        ],
        'foot': 'くわしくは docs/calc/fan_cfd/README.md',
    },
    'en': {
        'font': 'DejaVu Sans',
        'dot': '• ',
        'title': 'Suction fan: four geometries compared (CFD, 35,000 rpm)',
        'answer': 'Nearly sealed: C.  Leaky skirt: D.',
        'reason': 'They swap at a skirt-to-floor gap of about 0.10 mm. Measure the real gap to decide.',
        'names': {'A': 'A  current MK4', 'B': 'B  xfa273 type', 'C': 'C  combined', 'D': 'D  no walls'},
        'desc': {'A': 'Impeller + fixed ring', 'B': 'Rotating shroud', 'C': 'Rotating shroud + fixed ring',
                 'D': 'Impeller only, no ring'},
        'legend': ['impeller (rotating)', 'fixed ring', 'frame', 'PCB', 'air'],
        'bar2': '(1) Gap 0.15 mm: power for 277 g suction',
        'bar2_unit': 'W',
        'better2': 'four shapes, dia. 32 mm; lower is better',
        'line': '(2) Varying the gap: power for 300 g suction',
        'line_sub': 'C and D, dia. 30 mm; lower is better',
        'line_x': 'Skirt-to-floor gap [mm]',
        'line_x0': '0\n(sealed)',
        'line_swap': 'swap',
        'notes': [
            '(1) With a leaky skirt (0.15 mm gap) D is best: for the same suction it needs\n    22 % less power than A and 18 % less than C. The ring and shroud narrow the outlet.',
            '(2) The tighter the skirt, the better C gets. Sealed, C needs about 1/4 of the power of D:\n    the enclosed air turns with C, while D keeps pumping air in and out at the blade tips.',
            'A and B were computed at 0.15 mm only. Adding the surrounding parts (mounts, tires)\n    hardly changed (1).',
            'Estimate the real gap from measured suction and fan current,\n    then decide with printed impellers.',
        ],
        'foot': 'Details: docs/calc/fan_cfd/README.md',
    },
}


def rect(ax, r0, r1, z0, z1, color):
    """軸をはさんで左右に同じ四角を描く(r0〜r1 は軸からの距離 [mm]、z は床からの高さ [mm])"""
    ax.add_patch(Rectangle((r0, z0), r1 - r0, z1 - z0, fc=color, ec='none'))
    ax.add_patch(Rectangle((-r1, z0), r1 - r0, z1 - z0, fc=color, ec='none'))


def arrow(ax, points):
    """空気の流れの矢印を、左右に描く(points は右側の折れ線の点)"""
    for side in (1, -1):
        xs = []
        zs = []
        for x, z in points:
            xs.append(x * side)
            zs.append(z)
        ax.plot(xs[:-1], zs[:-1], color=COLOR_AIR, lw=2)
        ax.annotate('', xy=(xs[-1], zs[-1]), xytext=(xs[-2], zs[-2]),
                    arrowprops=dict(arrowstyle='-|>', color=COLOR_AIR, lw=2, mutation_scale=14))


def draw_shape(ax, case):
    """ファンの縦の断面を簡単な四角で描く(寸法は make_case.py と同じ)"""
    rect(ax, 7.5, 24, 0, 2.8, COLOR_FRAME)               # フレーム(真ん中に吸い込みの穴 φ15)
    rect(ax, 13, 24, 13.6, 14.2, COLOR_PCB)              # メイン基板
    ax.add_patch(Rectangle((-5.35, 8.6), 10.7, 9.4, fc=COLOR_MOTOR, ec='none'))   # モーター
    rect(ax, 5, 16, 3.3, 7.2, '#f2b8b5')                 # 羽根のある所(羽根は5枚、薄い色で)
    if case == 'A':
        rect(ax, 0, 16, 7.2, 8.0, COLOR_ROTOR)          # 上の板
        rect(ax, 16.5, 17.5, 2.8, 10, COLOR_RING)       # 止まった輪
        arrow(ax, [(0, -3), (0, 2.5), (10, 5), (16.25, 6), (16.25, 11), (23, 11.5)])
    if case == 'B':
        rect(ax, 0, 16.6, 7.2, 8.0, COLOR_ROTOR)        # 上の板
        rect(ax, 16, 16.6, 3.3, 8.0, COLOR_ROTOR)       # 回る外の壁
        arrow(ax, [(0, -3), (0, 2.5), (10, 4.5), (15.5, 3.4), (23.5, 3.4)])
    if case == 'C':
        rect(ax, 0, 16.6, 7.2, 8.0, COLOR_ROTOR)        # 上の板
        rect(ax, 16, 16.6, 3.3, 8.0, COLOR_ROTOR)       # 回る外の壁
        rect(ax, 17.6, 18.6, 2.8, 10, COLOR_RING)       # 止まった輪
        arrow(ax, [(0, -3), (0, 2.5), (10, 4.5), (17.1, 4.5), (17.1, 11), (23, 11.5)])
    if case == 'D':
        rect(ax, 0, 16, 7.2, 8.0, COLOR_ROTOR)          # 上の板(外の壁も輪もない)
        arrow(ax, [(0, -3), (0, 2.5), (10, 5), (23.5, 5.5)])
    ax.set_xlim(-24, 24)
    ax.set_ylim(-4, 19)
    ax.set_aspect('equal')
    ax.axis('off')


def bar_chart(ax, values, title, unit, better, best_case, digits):
    """3つの形の棒グラフ。一番よいものだけ色を付ける"""
    names = CASES
    colors = []
    for case in names:
        if case == best_case:
            colors.append(COLOR_BEST)
        else:
            colors.append(COLOR_OTHER)
    heights = []
    for case in names:
        heights.append(values[case])
    ax.bar(names, heights, color=colors, width=0.6)
    top = max(heights) * 1.25
    for i in range(len(names)):
        ax.text(i, heights[i] + top * 0.02, f'{heights[i]:.{digits}f}', ha='center', fontsize=11)
    ax.set_ylabel(unit, fontsize=10, rotation=0, labelpad=12)
    ax.set_ylim(0, top)
    ax.set_title(title, fontsize=11, pad=18)
    ax.text(0.5, 1.01, f'({better})', transform=ax.transAxes, ha='center', fontsize=9, color='#555555')
    ax.tick_params(axis='x', labelsize=13)
    ax.set_yticks([])
    for side in ('top', 'right', 'left'):
        ax.spines[side].set_visible(False)


def gap_power(suction_g, power_w):
    """吸引を GAP_TARGET_G にそろえたときの電力 [W](回転数を変えたとして換算)"""
    return power_w * (GAP_TARGET_G / suction_g) ** 1.5


def gap_chart(ax, t):
    """すき間と、同じ吸引に要る電力の線グラフ(C と D)"""
    power_c = []
    power_d = []
    for i in range(len(GAP_MM)):
        power_c.append(gap_power(GAP_C_SUCTION_G[i], GAP_C_POWER_W[i]))
        power_d.append(gap_power(GAP_D_SUCTION_G[i], GAP_D_POWER_W[i]))
    ax.plot(GAP_MM, power_c, color=COLOR_LINE_C, lw=2, marker='o', ms=7)
    ax.plot(GAP_MM, power_d, color=COLOR_LINE_D, lw=2, marker='s', ms=7)
    ax.text(0.157, power_c[3], 'C', va='center', fontsize=12)
    ax.text(0.157, power_d[3], 'D', va='center', fontsize=12)
    ax.text(-0.004, power_c[0] - 0.45, f'{power_c[0]:.2f}', ha='left', fontsize=9.5)
    ax.text(-0.004, power_d[0] + 0.25, f'{power_d[0]:.2f}', ha='left', fontsize=9.5)
    ax.axvline(0.10, color='#999999', lw=1, ls='--', zorder=0)
    ax.text(0.097, 5.6, t['line_swap'], ha='right', va='top', fontsize=9.5, color='#444444')
    ax.set_xlim(-0.008, 0.172)
    ax.set_ylim(0, 5.8)
    ax.set_xticks(GAP_MM)
    ax.set_xticklabels([t['line_x0'], '0.05', '0.10', '0.15'], fontsize=9.5)
    ax.set_xlabel(t['line_x'], fontsize=9.5)
    ax.set_ylabel('W', fontsize=10, rotation=0, labelpad=12)
    ax.set_title(t['line'], fontsize=11, pad=18)
    ax.text(0.5, 1.01, f"({t['line_sub']})", transform=ax.transAxes, ha='center', fontsize=9, color='#555555')
    ax.grid(axis='y', color='#e5e5e5')
    ax.set_axisbelow(True)
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)


def build(lang):
    t = TEXT[lang]
    plt.rcParams['font.family'] = t['font']
    plt.rcParams['pdf.fonttype'] = 42             # 字を PDF に埋め込む(文字として選べるように)
    fig = plt.figure(figsize=(8.27, 11.69))       # A4 の縦 [インチ]

    # 1. 題と答え
    fig.text(0.5, 0.955, t['title'], ha='center', fontsize=15)
    box = FancyBboxPatch((0.08, 0.84), 0.84, 0.085, boxstyle='round,pad=0.005,rounding_size=0.015',
                         transform=fig.transFigure, fc='#fff1df', ec=COLOR_BEST, lw=2)
    fig.patches.append(box)
    fig.text(0.5, 0.893, t['answer'], ha='center', va='center', fontsize=24, color=COLOR_BEST)
    fig.text(0.5, 0.857, t['reason'], ha='center', va='center', fontsize=11)

    # 2. 4つの形の断面(横に 4 つ並べる)
    width = 0.235
    for k in range(len(CASES)):
        case = CASES[k]
        left = 0.02 + k * 0.243
        ax = fig.add_axes([left, 0.62, width, 0.14])
        draw_shape(ax, case)
        color = 'black'
        if case in CHOICES:
            color = COLOR_BEST
            # すき間しだいで選ぶ 2 つの形を枠で囲む
            frame = FancyBboxPatch((left - 0.003, 0.595), width + 0.006, 0.225,
                                   boxstyle='round,pad=0.003,rounding_size=0.01',
                                   transform=fig.transFigure, fc='none', ec=COLOR_BEST, lw=2)
            fig.patches.append(frame)
        fig.text(left + width / 2, 0.80, t['names'][case], ha='center', fontsize=11.5, color=color)
        fig.text(left + width / 2, 0.782, t['desc'][case], ha='center', fontsize=8.5, color='#444444')
    # 色の説明
    legend_colors = [COLOR_ROTOR, COLOR_RING, COLOR_FRAME, COLOR_PCB, COLOR_AIR]
    legend_x = [0.08, 0.28, 0.46, 0.62, 0.78]      # 色の四角を置く横の位置(英語の長い言葉が重ならないように)
    for i in range(5):
        x = legend_x[i]
        fig.patches.append(Rectangle((x, 0.567), 0.022, 0.009, transform=fig.transFigure, fc=legend_colors[i], ec='none'))
        fig.text(x + 0.028, 0.5715, t['legend'][i], va='center', fontsize=9.5)

    # 3. 棒グラフ
    power_same = {}
    for case in CASES:
        power_same[case] = power_same_suction(case)
    ax1 = fig.add_axes([0.08, 0.29, 0.36, 0.21])
    bar_chart(ax1, power_same, t['bar2'], t['bar2_unit'], t['better2'], BEST, 2)
    ax2 = fig.add_axes([0.57, 0.29, 0.36, 0.21])
    gap_chart(ax2, t)

    # 4. ひとこと
    y = 0.225
    for note in t['notes']:
        fig.text(0.07, y, t['dot'] + note, fontsize=9.5, va='top', linespacing=1.5)
        lines = note.count('\n') + 1
        y = y - 0.017 * lines - 0.01          # 行の数だけ下げて、次のひとこととの間を少しあける
    fig.text(0.07, 0.03, t['foot'], fontsize=9, color='#666666')

    out = os.path.join(HERE, f'fan_cfd_report_{lang}.pdf')
    fig.savefig(out)
    plt.close(fig)
    print(out)


build('ja')
build('en')

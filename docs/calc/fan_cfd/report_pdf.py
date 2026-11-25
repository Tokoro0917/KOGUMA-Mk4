"""吸引ファンの形の比べ(流体の計算)の報告を PDF にする。日本語版と英語版の2つを作る(2026-11-25)。
使い方(リポジトリの一番上から): python3 docs/calc/fan_cfd/report_pdf.py
  → docs/calc/fan_cfd/fan_cfd_report_ja.pdf、fan_cfd_report_en.pdf
先に図を作っておく:
  python3 docs/calc/fan_cfd/section_fig.py(と --en)
  python3 docs/calc/fan_cfd/flow_fig.py docs/img/tire24/fan_cfd_flow.png <A> <B> <C>(と fan_cfd_flow_en.png)
数値は post.py の出力(2026-11-24、細かいメッシュはくり返し 1,500 回、粗いメッシュは 1,500 回)を書き写したもの。
棒グラフ(fan_cfd_bar.png・fan_cfd_bar_en.png)はこのスクリプトが作る。"""
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, '../../img/tire24')

# 日本語は IPA P ゴシック、英語は DejaVu Sans(どちらも「−」「·」「φ」の字がある)
pdfmetrics.registerFont(TTFont('JA', '/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf'))
pdfmetrics.registerFont(TTFont('EN', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('EN-B', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))

# ---- 計算の結果(post.py の出力)----
# 細かいメッシュ、35,000rpm
SUCTION_G = {'A': 277, 'B': 299, 'C': 323}           # 吸引(68 × 34mm の面)[g]
PRESSURE_PA = {'A': -1177, 'B': -1271, 'C': -1371}   # 機体の下の部屋の圧力 [Pa]
LEAK_L_MIN = {'A': 63.3, 'B': 65.7, 'C': 68.2}       # 漏れる空気 [L/min]
TORQUE_P = {'A': 1.035, 'B': 1.228, 'C': 1.255}      # トルクのうち圧力の分 [mN·m]
TORQUE_F = {'A': 0.133, 'B': 0.194, 'C': 0.140}      # トルクのうち摩擦の分 [mN·m]
POWER_W = {'A': 4.28, 'B': 5.21, 'C': 5.11}          # 羽根を回す仕事 [W]
CELLS = {'A': 1555111, 'B': 1432826, 'C': 1804825}   # セルの数
# 粗いメッシュ、35,000rpm
COARSE_SUCTION_G = {'A': 269, 'B': 295, 'C': 291}
COARSE_POWER_W = {'A': 3.93, 'B': 4.83, 'C': 4.70}
# くり返し 1,000 回の吸引(収束の確かめ)
SUCTION_1000_G = {'A': 278, 'B': 295, 'C': 320}
RPM = 35000


def same_suction(case):
    """吸引を A と同じにそろえたときの回転数と仕事。負圧は回転数の2乗、仕事は3乗に比例するとして換算する"""
    ratio = (SUCTION_G['A'] / SUCTION_G[case]) ** 0.5     # 回転数の比
    rpm = RPM * ratio
    power = POWER_W[case] * ratio ** 3
    return rpm, power


def air_efficiency(case):
    """空気にした仕事(負圧 × 流量)÷ 羽根を回す仕事"""
    air_w = -PRESSURE_PA[case] * LEAK_L_MIN[case] / 60000
    return air_w / POWER_W[case]


def percent(case, table):
    """A に対して何 % 違うか"""
    return (table[case] / table['A'] - 1) * 100


# ---- 文章(日本語と英語)----
TEXT = {
    'ja': {
        'title': '吸引ファンの形の比べ(流体の計算)',
        'sub': 'KOGUMA MK4(タイヤ 24mm)/ 2026-11-24 計算、2026-11-25 まとめ',
        'summary_h': '要点',
        'summary': [
            '今の MK4 のファン(A)、xfa273 さんの X の投稿のファンの形(B)、その組み合わせ(C)の3つを、35,000rpm で流体の計算(OpenFOAM)で比べた。',
            '<b>C(回る外の壁 + 止まった輪)が一番よい</b>: 吸引 323g(A の +17%)、羽根を回す仕事 5.11W(+19%)。同じ吸引 277g にそろえると 4.06W で、<b>A より 5% 少ない仕事</b>で済む(32,400rpm)。',
            'B は同じ回転数なら A より吸引が 8% 強いが、回す仕事が 22% 増える。同じ吸引にそろえると A より 9% 多くかかり、得にならない。',
            '値はメッシュの細かさで 1 割ほど動く(特に C)。順位(C &gt; B &gt; A)は細かいメッシュの結果を信じるが、最後は印刷した羽根で吸引の力と電流を実測して決める。',
        ],
        'shape_h': '1. 比べた3つの形',
        'shape_cols': ['形', '中身', '空気の出口'],
        'shapes': [
            ['A 今', '羽根 φ32(5枚)+ 上の板。羽根の外に止まった輪(ファンの台、半径 16.5〜17.5mm)', '羽根と輪のすき間 0.5mm から上へ'],
            ['B xfa273 さん', '羽根の外に回る外の壁(半径 16〜16.6mm、羽根・上の板と一体)。止まった輪はない', '外の壁の下の端とフレームのすき間 0.5mm から横へ'],
            ['C 組み合わせ', 'B の羽根 + 止まった輪(半径 17.6〜18.6mm)', '回る壁と輪のすき間 1mm から上へ'],
        ],
        'shape_note': '羽根の形はどれも同じ: 厚さ 0.6mm、内の端 半径 5mm、後ろへ 60° 曲げた5枚、高さ z 3.3〜7.2mm(フレームの上面 z 2.8)、上の板 z 7.2〜8.0mm。B の形は投稿の写真から読んだ推定。',
        'method_h': '2. 計算のしかた',
        'method': [
            'OpenFOAM v1912 の simpleFoam(定常、非圧縮)。乱流は k-ω SST、壁は壁関数。羽根のまわりの円柱の範囲を回る座標で解く(MRF)。',
            'メッシュは snappyHexMesh で STL から作る。細かいメッシュは羽根・輪のまわりを 0.125mm、全体で 143〜180 万セル。粗いメッシュは羽根のまわり 0.25mm。',
            'スカートと床のすき間の漏れは、すき間 0.15mm × スカートの縁 204mm と同じ面積(30.6mm²)の穴にした。穴の下は大気(圧力 0)。',
            '吸引の力 = 機体の下の部屋の平均の圧力 × 68 × 34mm。トルクは羽根の面の圧力と壁の摩擦から求め、仕事 = トルク × 角速度(モーターの損失は入れない)。',
            'くり返し 1,500 回(4並列で1つ約1時間)。このパッケージは forces などの関数オブジェクトが動かないので、書き出した場を Python(post.py)で読んで計算した。',
        ],
        'result_h': '3. 結果(細かいメッシュ、35,000rpm)',
        'result_rows': ['機体の下の圧力', '吸引(68 × 34mm)', '漏れる空気', 'トルク(圧力 + 摩擦)', '羽根を回す仕事', '空気にした仕事 ÷ 回す仕事', '吸引 277g にそろえた回転数', '吸引 277g にそろえた仕事'],
        'names': {'A': 'A 今', 'B': 'B xfa273 さん', 'C': 'C 組み合わせ'},
        'result_note': '吸引 277g にそろえる換算は、負圧が回転数の2乗、仕事が3乗に比例するとした。',
        'bar_title1': '35,000rpm での吸引と仕事',
        'bar_title2': '同じ吸引 277g にそろえたときの仕事',
        'bar_suction': '吸引 [g]',
        'bar_power': '仕事 [W]',
        'flow_h': '4. 流れ',
        'flow': [
            'A と C は、空気が上へ出て基板の下を横へ抜ける。B は空気がフレームの上を這って横へ吹き出す(フレームの上の部品に当たる)。',
            'C は回る外の壁と輪の間の空気が一緒に回るので、外の壁の摩擦が A と同じくらい(B 0.19 → C 0.14 mN·m)に収まり、すき間でも圧力を少し上げていると考えられる(計算から読んだ推測)。B は外の壁の外側の面が開いた空気をこするので摩擦が大きい。',
        ],
        'check_h': '5. 確かめと気をつけること',
        'check_cols': ['', 'A 今', 'B xfa273 さん', 'C 組み合わせ'],
        'check_rows': ['吸引: 粗い → 細かいメッシュ', '仕事: 粗い → 細かいメッシュ', '吸引: くり返し 1,000 → 1,500 回', 'セルの数(細かいメッシュ)'],
        'caveats': [
            '<b>メッシュで値が動く</b>: C は粗いメッシュから細かいメッシュで吸引が +11% 変わった。幅 1mm のすき間の流れが粗いメッシュでは足りていなかった。C の値はもう1段細かくすると、また数 % 動くかもしれない。',
            '粗いメッシュでは B と C はほぼ同じ(295g・291g)だったが、細かいメッシュでは C が B より 8% 強い。',
            'ファンの台の腕、モーターの支え、壁センサのホルダなどは入れていない。実物は印刷の精度(羽根の厚さ、すき間)でも変わる。',
            '吸引する面は 68 × 34mm で計算した(今の設計は 80 × 42.6mm に広げている)。3つの比べ(差の割合)には関係しない。',
        ],
        'next_h': '6. まとめと次にやること',
        'next': [
            '羽根を作るときは <b>C(回る外の壁 + 止まった輪)を第一候補</b>にする。',
            'A と C を印刷して、同じ回転数(または同じ電流)で吸引の力とファンの電流を測り、計算の順位を確かめる。',
            '計算のファイル: docs/calc/fan_cfd/(make_case.py・run_case.sh・post.py・flow_fig.py・section_fig.py・README.md)',
        ],
        'fig_shapes': '図2 3つの形の縦の断面(y = 0)',
        'fig_bar': '図1 吸引と仕事の比べ',
        'fig_flow': '図3 流れの縦の断面(上: 圧力、下: 速さ)',
    },
    'en': {
        'title': 'Suction Fan Geometry Comparison (CFD)',
        'sub': 'KOGUMA MK4 (24 mm tyre version) / computed 2026-11-24, report 2026-11-25',
        'summary_h': 'Summary',
        'summary': [
            'Three suction fan geometries were compared by CFD (OpenFOAM) at 35,000 rpm: the current MK4 fan (A), the fan shape shown in a post on X by xfa273 (B), and a combination of the two (C).',
            '<b>C (rotating shroud + fixed ring) performs best</b>: 323 g of suction (+17 % vs A) for 5.11 W of shaft power (+19 %). Scaled to the same suction of 277 g it needs 4.06 W, <b>5 % less power than A</b> (at 32,400 rpm).',
            'B gives 8 % more suction than A at the same speed, but needs 22 % more power. Scaled to the same suction it needs 9 % more power than A, so it brings no net benefit.',
            'The results change by about 10 % with mesh resolution (most for C). The ranking (C &gt; B &gt; A) is taken from the fine mesh; the final choice should be confirmed by measuring suction force and fan current on printed impellers.',
        ],
        'shape_h': '1. Geometries compared',
        'shape_cols': ['Case', 'Description', 'Air outlet'],
        'shapes': [
            ['A current', '5-blade impeller (dia. 32 mm) with a top disc. A fixed ring (part of the fan mount, r = 16.5-17.5 mm) surrounds the blades', 'Upward through the 0.5 mm gap between blade tips and ring'],
            ['B xfa273 type', 'A rotating shroud (r = 16-16.6 mm) is part of the impeller together with the blades and top disc. No fixed ring', 'Sideways through the 0.5 mm gap between the shroud bottom and the frame'],
            ['C combined', 'Impeller B + fixed ring (r = 17.6-18.6 mm)', 'Upward through the 1 mm gap between shroud and ring'],
        ],
        'shape_note': 'The blades are identical in all cases: 0.6 mm thick, inner radius 5 mm, five blades swept back by 60°, z = 3.3-7.2 mm (frame top at z = 2.8), top disc z = 7.2-8.0 mm. Geometry B is estimated from the photos in the post.',
        'method_h': '2. Method',
        'method': [
            'OpenFOAM v1912, simpleFoam (steady, incompressible), k-ω SST turbulence model with wall functions. A cylindrical zone around the impeller is solved in the rotating frame (MRF).',
            'Meshes were generated from STL with snappyHexMesh. Fine mesh: 0.125 mm cells around the impeller and ring, 1.43-1.80 million cells in total. Coarse mesh: 0.25 mm around the impeller.',
            'The leak between skirt and floor is modelled as an orifice with the same area as a 0.15 mm gap along the 204 mm skirt edge (30.6 mm²), opening to the atmosphere (p = 0).',
            'Suction force = mean pressure in the chamber under the robot × 68 × 34 mm. Torque is computed from the pressure and wall friction on the impeller surfaces; power = torque × angular speed (motor losses not included).',
            '1,500 iterations (about 1 hour per case on 4 cores). Function objects (forces etc.) do not work in this OpenFOAM package, so the written fields were evaluated in Python (post.py).',
        ],
        'result_h': '3. Results (fine mesh, 35,000 rpm)',
        'result_rows': ['Pressure under the robot', 'Suction (68 × 34 mm)', 'Leak flow', 'Torque (pressure + friction)', 'Shaft power', 'Air power / shaft power', 'Speed for 277 g suction', 'Power for 277 g suction'],
        'names': {'A': 'A current', 'B': 'B xfa273 type', 'C': 'C combined'},
        'result_note': 'Scaling to the same suction of 277 g assumes pressure ∝ speed² and power ∝ speed³.',
        'bar_title1': 'Suction and power at 35,000 rpm',
        'bar_title2': 'Power at the same suction (277 g)',
        'bar_suction': 'Suction [g]',
        'bar_power': 'Power [W]',
        'flow_h': '4. Flow field',
        'flow': [
            'In A and C the air leaves upward and then flows outward under the PCB. In B the air is blown sideways along the top of the frame (towards the parts mounted on the frame).',
            'In C the air between the rotating shroud and the fixed ring rotates with the shroud, which keeps the shroud friction at the level of A (B 0.19 → C 0.14 mN·m) and appears to add some pressure rise in the gap (an interpretation of the results). In B the outer face of the shroud rubs against open air, which increases friction.',
        ],
        'check_h': '5. Checks and limitations',
        'check_cols': ['', 'A current', 'B xfa273 type', 'C combined'],
        'check_rows': ['Suction: coarse → fine mesh', 'Power: coarse → fine mesh', 'Suction: 1,000 → 1,500 iterations', 'Cells (fine mesh)'],
        'caveats': [
            '<b>Mesh sensitivity</b>: the suction of C changed by +11 % from the coarse to the fine mesh, because the flow in the 1 mm gap was under-resolved on the coarse mesh. The value for C may move by a few percent again with further refinement.',
            'On the coarse mesh B and C were almost equal (295 g, 291 g); on the fine mesh C is 8 % stronger than B.',
            'The fan mount arms, motor support, wall sensor holders etc. are not modelled. Real parts will also differ due to print accuracy (blade thickness, gaps).',
            'The suction area was taken as 68 × 34 mm (the current design uses 80 × 42.6 mm). This does not affect the relative comparison.',
        ],
        'next_h': '6. Conclusion and next steps',
        'next': [
            '<b>C (rotating shroud + fixed ring) is the first choice</b> for the impeller design.',
            'Print A and C and measure suction force and fan current at the same speed (or the same current) to confirm the ranking.',
            'Files: docs/calc/fan_cfd/ (make_case.py, run_case.sh, post.py, flow_fig.py, section_fig.py, README.md)',
        ],
        'fig_shapes': 'Fig. 2 Vertical sections of the three geometries (y = 0)',
        'fig_bar': 'Fig. 1 Comparison of suction and power',
        'fig_flow': 'Fig. 3 Flow field in the vertical section (top: pressure, bottom: speed)',
    },
}


def make_bar_chart(lang, path):
    """吸引と仕事の棒グラフ(左: 35,000rpm、右: 同じ吸引にそろえたとき)"""
    t = TEXT[lang]
    if lang == 'ja':
        plt.rcParams['font.family'] = 'IPAGothic'
    else:
        plt.rcParams['font.family'] = 'DejaVu Sans'
    names = [t['names']['A'], t['names']['B'], t['names']['C']]
    suction = [SUCTION_G['A'], SUCTION_G['B'], SUCTION_G['C']]
    power = [POWER_W['A'], POWER_W['B'], POWER_W['C']]
    power_same = [POWER_W['A'], same_suction('B')[1], same_suction('C')[1]]
    color_case = ['#8c8c8c', '#4a7fc1', '#d9822b']

    fig, axes = plt.subplots(1, 3, figsize=(11, 3.4))
    axes[0].bar(names, suction, color=color_case)
    axes[0].set_title(t['bar_suction'] + '  (35,000rpm)', fontsize=10)
    axes[0].set_ylim(0, 360)
    for i in range(3):
        axes[0].text(i, suction[i] + 5, f'{suction[i]}', ha='center', fontsize=9)
    axes[1].bar(names, power, color=color_case)
    axes[1].set_title(t['bar_power'] + '  (35,000rpm)', fontsize=10)
    axes[1].set_ylim(0, 6)
    for i in range(3):
        axes[1].text(i, power[i] + 0.08, f'{power[i]:.2f}', ha='center', fontsize=9)
    axes[2].bar(names, power_same, color=color_case)
    axes[2].set_title(t['bar_title2'], fontsize=10)
    axes[2].set_ylim(0, 6)
    for i in range(3):
        axes[2].text(i, power_same[i] + 0.08, f'{power_same[i]:.2f}', ha='center', fontsize=9)
    for ax in axes:
        ax.tick_params(axis='x', labelsize=9)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def styles(lang):
    """段落の書式。日本語は行を折り返しやすくする(wordWrap='CJK')"""
    font = 'JA'
    bold = 'JA'
    wrap = 'CJK'
    if lang == 'en':
        font = 'EN'
        bold = 'EN-B'
        wrap = None
    st = {}
    st['title'] = ParagraphStyle('title', fontName=bold, fontSize=17, leading=23, spaceAfter=3, wordWrap=wrap)
    st['sub'] = ParagraphStyle('sub', fontName=font, fontSize=9, leading=13, textColor=colors.HexColor('#555555'), spaceAfter=10, wordWrap=wrap)
    st['h'] = ParagraphStyle('h', fontName=bold, fontSize=12.5, leading=17, spaceBefore=10, spaceAfter=5, textColor=colors.HexColor('#1f4e79'), keepWithNext=1, wordWrap=wrap)   # 見出しだけがページの下に残らないように
    st['body'] = ParagraphStyle('body', fontName=font, fontSize=9.5, leading=15, spaceAfter=3, wordWrap=wrap)
    st['bullet'] = ParagraphStyle('bullet', parent=st['body'], leftIndent=12, bulletIndent=2)
    st['cell'] = ParagraphStyle('cell', fontName=font, fontSize=8.5, leading=12, wordWrap=wrap)
    st['cellb'] = ParagraphStyle('cellb', fontName=bold, fontSize=8.5, leading=12, wordWrap=wrap)
    st['cap'] = ParagraphStyle('cap', fontName=font, fontSize=8.5, leading=12, alignment=1, textColor=colors.HexColor('#444444'), spaceAfter=8, wordWrap=wrap)
    st['note'] = ParagraphStyle('note', fontName=font, fontSize=8.5, leading=12, textColor=colors.HexColor('#444444'), spaceAfter=4, wordWrap=wrap)
    if lang == 'ja':
        # IPA P ゴシックには太字がないので、見出しは色と大きさで分ける。<b> は同じ字で出る
        pdfmetrics.registerFontFamily('JA', normal='JA', bold='JA', italic='JA', boldItalic='JA')
    else:
        pdfmetrics.registerFontFamily('EN', normal='EN', bold='EN-B', italic='EN', boldItalic='EN-B')
    return st


def table_style(header_rows=1):
    return TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#999999')),
        ('BACKGROUND', (0, 0), (-1, header_rows - 1), colors.HexColor('#dfe8f3')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ])


def figure(path, width_mm):
    """図を、幅を決めて縦横比のまま置く"""
    img = Image(path)
    scale = width_mm * mm / img.imageWidth
    img.drawWidth = width_mm * mm
    img.drawHeight = img.imageHeight * scale
    return img


def result_table(lang, st):
    """3つの形の結果の表"""
    t = TEXT[lang]
    rows = t['result_rows']
    head = [Paragraph('', st['cellb'])]
    for case in 'ABC':
        head.append(Paragraph(t['names'][case], st['cellb']))
    data = [head]
    lines = {}
    for case in 'ABC':
        rpm, power_same = same_suction(case)
        s_pct = percent(case, SUCTION_G)
        p_pct = percent(case, POWER_W)
        ps_pct = (power_same / POWER_W['A'] - 1) * 100
        suction = f'{SUCTION_G[case]} g'
        power = f'{POWER_W[case]:.2f} W'
        power_same_text = f'{power_same:.2f} W'
        if case != 'A':
            suction = suction + f' ({s_pct:+.0f}%)'
            power = power + f' ({p_pct:+.0f}%)'
            power_same_text = power_same_text + f' ({ps_pct:+.0f}%)'
        torque = TORQUE_P[case] + TORQUE_F[case]
        lines[case] = [
            f'{PRESSURE_PA[case]:,} Pa'.replace('-', '−'),
            suction,
            f'{LEAK_L_MIN[case]:.1f} L/min',
            f'{torque:.3f} mN·m ({TORQUE_P[case]:.3f} + {TORQUE_F[case]:.3f})',
            power,
            f'{air_efficiency(case) * 100:.0f}%',
            f'{rpm:,.0f} rpm',
            power_same_text,
        ]
    for k in range(len(rows)):
        row = [Paragraph(rows[k], st['cell'])]
        for case in 'ABC':
            text = lines[case][k]
            style = st['cell']
            # C の吸引・同じ吸引の仕事は、一番よい値なので太字にする
            if case == 'C' and k in (1, 7):
                style = st['cellb']
            row.append(Paragraph(text, style))
        data.append(row)
    tbl = Table(data, colWidths=[44 * mm, 41 * mm, 41 * mm, 44 * mm])
    style = table_style()
    style.add('BACKGROUND', (3, 1), (3, -1), colors.HexColor('#fdf1e3'))   # C の列に色
    tbl.setStyle(style)
    return tbl


def check_table(lang, st):
    """メッシュと収束の確かめの表"""
    t = TEXT[lang]
    data = [[Paragraph(c, st['cellb']) for c in t['check_cols']]]
    row_s = [Paragraph(t['check_rows'][0], st['cell'])]
    row_p = [Paragraph(t['check_rows'][1], st['cell'])]
    row_i = [Paragraph(t['check_rows'][2], st['cell'])]
    row_c = [Paragraph(t['check_rows'][3], st['cell'])]
    for case in 'ABC':
        ds = (SUCTION_G[case] / COARSE_SUCTION_G[case] - 1) * 100
        dp = (POWER_W[case] / COARSE_POWER_W[case] - 1) * 100
        di = (SUCTION_G[case] / SUCTION_1000_G[case] - 1) * 100
        row_s.append(Paragraph(f'{COARSE_SUCTION_G[case]} → {SUCTION_G[case]} g ({ds:+.0f}%)', st['cell']))
        row_p.append(Paragraph(f'{COARSE_POWER_W[case]:.2f} → {POWER_W[case]:.2f} W ({dp:+.0f}%)', st['cell']))
        row_i.append(Paragraph(f'{SUCTION_1000_G[case]} → {SUCTION_G[case]} g ({di:+.1f}%)', st['cell']))
        row_c.append(Paragraph(f'{CELLS[case]:,}', st['cell']))
    data.append(row_s)
    data.append(row_p)
    data.append(row_i)
    data.append(row_c)
    tbl = Table(data, colWidths=[50 * mm, 40 * mm, 40 * mm, 40 * mm])
    tbl.setStyle(table_style())
    return tbl


def shape_table(lang, st):
    """3つの形の説明の表"""
    t = TEXT[lang]
    data = [[Paragraph(c, st['cellb']) for c in t['shape_cols']]]
    for row in t['shapes']:
        data.append([Paragraph(row[0], st['cellb']), Paragraph(row[1], st['cell']), Paragraph(row[2], st['cell'])])
    tbl = Table(data, colWidths=[28 * mm, 88 * mm, 54 * mm])
    tbl.setStyle(table_style())
    return tbl


def bullets(items, st):
    out = []
    for text in items:
        out.append(Paragraph(text, st['bullet'], bulletText='•'))
    return out


def page_number(canvas, doc):
    """ページの下に番号を書く"""
    canvas.saveState()
    canvas.setFont('EN', 8)
    canvas.drawCentredString(A4[0] / 2, 10 * mm, f'{doc.page}')
    canvas.restoreState()


def build(lang):
    t = TEXT[lang]
    st = styles(lang)
    suffix = ''
    if lang == 'en':
        suffix = '_en'
    bar_png = os.path.join(IMG, f'fan_cfd_bar{suffix}.png')
    make_bar_chart(lang, bar_png)
    out = os.path.join(HERE, f'fan_cfd_report_{lang}.pdf')
    doc = SimpleDocTemplate(out, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=18 * mm,
                            title=t['title'], author='KOGUMA MK4')
    story = []
    story.append(Paragraph(t['title'], st['title']))
    story.append(Paragraph(t['sub'], st['sub']))
    story.append(Paragraph(t['summary_h'], st['h']))
    story += bullets(t['summary'], st)
    story.append(Spacer(1, 4))
    story.append(KeepTogether([figure(bar_png, 140), Paragraph(t['fig_bar'], st['cap'])]))

    story.append(Paragraph(t['shape_h'], st['h']))
    story.append(shape_table(lang, st))
    story.append(Spacer(1, 4))
    story.append(Paragraph(t['shape_note'], st['note']))
    story.append(KeepTogether([figure(os.path.join(IMG, f'fan_cfd_shapes{suffix}.png'), 165), Paragraph(t['fig_shapes'], st['cap'])]))

    story.append(PageBreak())
    story.append(Paragraph(t['method_h'], st['h']))
    story += bullets(t['method'], st)

    story.append(Paragraph(t['result_h'], st['h']))
    story.append(result_table(lang, st))
    story.append(Spacer(1, 4))
    story.append(Paragraph(t['result_note'], st['note']))

    story.append(Paragraph(t['flow_h'], st['h']))
    story += bullets(t['flow'], st)
    story.append(Spacer(1, 4))
    story.append(KeepTogether([figure(os.path.join(IMG, f'fan_cfd_flow{suffix}.png'), 170), Paragraph(t['fig_flow'], st['cap'])]))

    story.append(Paragraph(t['check_h'], st['h']))
    story.append(check_table(lang, st))
    story.append(Spacer(1, 4))
    story += bullets(t['caveats'], st)

    story.append(Paragraph(t['next_h'], st['h']))
    story += bullets(t['next'], st)
    doc.build(story, onFirstPage=page_number, onLaterPages=page_number)
    print(out)


build('ja')
build('en')

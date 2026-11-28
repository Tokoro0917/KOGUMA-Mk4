"""BLE モジュール(HY0020)・有線(STLINK-V3MODS)とマイコン(STM32H562)のつながりの図(2026-11-27、ユーザー「図示して」)
使い方(リポジトリの一番上で): /usr/bin/python3.12 docs/img/ble_uart.py → docs/img/ble_uart.png
中身は docs/ble.md の 1 章・9 章と、回路図(hardware/kicad/KOGUMA-Mk4/ui.kicad_sch)の U5・D99〜D101・R101・J7・TP1"""
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon

plt.rcParams['font.family'] = 'WenQuanYi Zen Hei'
plt.rcParams['axes.unicode_minus'] = False
HERE = os.path.dirname(os.path.abspath(__file__))

C_TX = '#1f6fd1'     # マイコンから出る線
C_RX = '#d1401f'     # マイコンに入る線
C_RST = '#7a3fb0'    # リセット
C_PWR = '#888888'

fig, ax = plt.subplots(figsize=(13, 8.2))
ax.set_xlim(0, 130); ax.set_ylim(-4, 82); ax.axis('off')


def block(x, y, w, h, title, sub, color):
    """部品の箱"""
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.4', fc=color, ec='#333333', lw=1.2))
    ax.text(x + w / 2, y + h - 2.5, title, ha='center', va='top', fontsize=13, fontweight='bold')
    ax.text(x + w / 2, y + h - 7.0, sub, ha='center', va='top', fontsize=9, color='#333333')


def line(pts, color, lw=2.0):
    """折れ線"""
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    ax.plot(xs, ys, color=color, lw=lw, solid_capstyle='round')


def arrow(x0, y0, x1, y1, color):
    """向きの矢印(線の途中に置く)"""
    ax.annotate('', xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle='-|>', color=color, lw=2.0, mutation_scale=16))


def diode(x, y, color, name):
    """ダイオード(横向き。左がアノード、右がカソード = 右の送り手が L のときだけ電流が右へ流れ、線を L に引く)"""
    ax.add_patch(Polygon([(x - 1.6, y + 1.6), (x - 1.6, y - 1.6), (x + 1.2, y)], closed=True, fc='white', ec=color, lw=1.8, zorder=5))
    ax.plot([x + 1.2, x + 1.2], [y - 1.6, y + 1.6], color=color, lw=1.8, zorder=5)
    ax.text(x, y + 2.4, name, ha='center', va='bottom', fontsize=9, color=color)


def dot(x, y, color):
    ax.plot([x], [y], 'o', color=color, ms=6, zorder=6)


# ---- 箱 ----
block(4, 18, 30, 52, 'マイコン', 'STM32H562(U4)', '#dbe7f5')
block(92, 46, 34, 26, 'BLE モジュール', 'HY0020(U5、nRF52832)', '#f1e1f5')
block(92, 2, 34, 40, '有線(USB シリアル)', 'STLINK-V3MODS\n(J7 と TP1 にはんだ付け)', '#e6f0dc')
ax.text(109, 74.5, '↑ 電波(BLE)で PC へ', ha='center', fontsize=10, color='#7a3fb0')
ax.text(109, -2.5, '↓ USB で PC へ', ha='center', fontsize=10, color='#4a7a2a')

# マイコンのピン
pins = [(60, 'PB6\nUSART1_TX', C_TX), (44, 'PB7\nUSART1_RX', C_RX), (24, 'NRST', C_RST)]
for y, t, c in pins:
    ax.text(32.5, y, t, ha='right', va='center', fontsize=10, color=c, fontweight='bold')

# ---- マイコン → BLE・有線(送信)----
line([(34.4, 60), (92, 60)], C_TX)
arrow(60, 60, 66, 60, C_TX)
ax.text(93, 60, 'P0.08\n(受信)', ha='left', va='center', fontsize=9, color=C_TX)
dot(82, 60, C_TX)
line([(82, 60), (82, 28), (92, 28)], C_TX)
arrow(84, 28, 88, 28, C_TX)
ax.text(93, 28, 'J7 の 2番\n(UART_TX → 仮想 COM の受信)', ha='left', va='center', fontsize=8.5, color=C_TX)
ax.text(62, 61.2, 'UART_TX(両方に届く)', ha='center', va='bottom', fontsize=9, color=C_TX)

# ---- BLE・有線 → マイコン(受信。ワイヤード AND)----
line([(34.4, 44), (70, 44)], C_RX)
arrow(56, 44, 44, 44, C_RX)
ax.text(52, 45.2, 'UART_RX', ha='center', va='bottom', fontsize=9, color=C_RX)
dot(70, 44, C_RX)
# 引き上げ R101
line([(58, 44), (58, 49)], C_RX)
dot(58, 44, C_RX)
ax.add_patch(plt.Rectangle((56.8, 49), 2.4, 5, fc='white', ec=C_RX, lw=1.6))
ax.text(55.5, 51.5, 'R101 4.7kΩ', ha='right', va='center', fontsize=9, color=C_RX)
line([(58, 54), (58, 56.2)], C_PWR); ax.text(58, 56.6, '+3.3V', ha='center', va='bottom', fontsize=8.5, color=C_PWR)
# BLE の送信 → D99
line([(70, 44), (70, 52), (92, 52)], C_RX)
diode(76, 52, C_RX, 'D99')
ax.text(93, 52, 'P0.06\n(送信)', ha='left', va='center', fontsize=9, color=C_RX)
# 有線の送信 → TP1 → D100
line([(70, 44), (70, 16), (92, 16)], C_RX)
diode(76, 16, C_RX, 'D100')
ax.text(93, 16, 'TP1\n(仮想 COM の送信)', ha='left', va='center', fontsize=8.5, color=C_RX)
# BLE が UART_RX を見る(P0.04)
line([(70, 47.5), (88, 47.5), (92, 47.5)], C_RX, lw=1.0)
dot(70, 47.5, C_RX)
ax.text(93, 47.0, 'P0.04(UART_RX を見るだけ)', ha='left', va='center', fontsize=8, color=C_RX)

# ---- リセット ----
line([(34.4, 24), (86, 24)], C_RST)
dot(86, 24, C_RST)
line([(86, 24), (86, 56), (92, 56)], C_RST)
diode(89, 56, C_RST, '')
ax.text(89.2, 57.8, 'D101', ha='center', va='bottom', fontsize=9, color=C_RST)
ax.text(93, 56, 'P0.07(リセット)', ha='left', va='center', fontsize=9, color=C_RST)
line([(86, 24), (92, 24)], C_RST)
ax.text(93, 23.5, 'J7 の 3番(NRST)', ha='left', va='center', fontsize=8.5, color=C_RST)

# ---- 説明 ----
notes = [
    '・送信(青): マイコンの PB6 から BLE と有線の両方へ。どちらがつながっていても同じ文字が届く',
    '・受信(赤): BLE と有線の 2 つが 1 本の UART_RX に入る。R101 で H に引き上げ、送り手はダイオードを通して L に引くだけ',
    '  (ワイヤード AND)。H と L がぶつからないので、両方つないだままでよい。BLE は P0.04 で有線が送っているかを見て、待つ',
    '・リセット(紫): STLINK と BLE のどちらからもマイコンをリセットできる(BLE からはプログラムの書き込みのとき)。D101 で L に引くだけ',
    '・中身は改行で区切ったテキスト(1Mbaud。最初は 115200)。@ で始まる行(@link up・@link down・@quiet on)だけ BLE が自分で使う',
]
for i, t in enumerate(notes):
    ax.text(4, 12.5 - i * 2.9, t, ha='left', va='center', fontsize=9.2)
ax.set_title('BLE・有線とマイコンのつながり(UART、docs/ble.md の 1・9 章)', fontsize=14)
plt.savefig(os.path.join(HERE, 'ble_uart.png'), dpi=110, bbox_inches='tight')
print('ok')

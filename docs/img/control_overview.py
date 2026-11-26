"""MK4 の制御の全体の図(docs/control.md の1章・docs/software.md の4章をもとに、2026-11-26)。使い方: python3 docs/img/control_overview.py docs/img/control_overview.png"""
import sys
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
matplotlib.rcParams['font.family'] = 'WenQuanYi Zen Hei'; matplotlib.rcParams['axes.unicode_minus'] = False
import logging; logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)
fig = plt.figure(figsize=(16, 15.5))
ax = fig.add_axes([0.02, 0.36, 0.96, 0.62]); ax.set_xlim(0, 160); ax.set_ylim(0, 100); ax.axis('off')
C_CTRL, C_SENS, C_HW, C_EST = '#dbe9f6', '#e2f0d9', '#eeeeee', '#fff2cc'
def box(x, y, w, h, title, body='', c=C_CTRL, fs=11):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.5', fc=c, ec='k', lw=1.1))
    ax.text(x + w / 2, y + h - 1.6, title, ha='center', va='top', fontsize=fs, weight='bold')
    if body: ax.text(x + w / 2, y + h - 5.2, body, ha='center', va='top', fontsize=8.8, linespacing=1.4)
def arrow(x0, y0, x1, y1, txt='', c='k', side='r', ls='-'):
    ax.annotate('', (x1, y1), (x0, y0), arrowprops=dict(arrowstyle='->', lw=1.6, color=c, linestyle=ls))
    if txt:
        ax.text((x0 + x1) / 2 + (1.0 if side == 'r' else -1.0), (y0 + y1) / 2, txt, fontsize=8.6, color=c, ha='left' if side == 'r' else 'right', va='center')
ax.text(80, 99, 'KOGUMA MK4 の制御の全体(案。docs/control.md・docs/software.md)', ha='center', fontsize=15, weight='bold')
# 制御の段(中央の縦の列)
X = 52; W = 44
box(X, 85, W, 10, '軌道の生成', '直線・ターンの目標: 位置・向き・速度 v・角速度 ω\n加速度 a・角加速度 α', C_CTRL)
box(X, 67, W, 12, '位置・向きの制御  1kHz', '軌道との位置・向きのずれ → v・ω の補正\n壁センサで横のずれ・向きを直す(壁制御)', C_CTRL)
box(X, 49, W, 12, '速度・角速度の制御  1kHz(あとで 2〜5kHz)', 'v・ω のずれ → 加速度・角加速度の補正\n+ 軌道の a・α(フィードフォワード)', C_CTRL)
box(X, 34, W, 9, '左右の電流の目標に直す  1kHz', 'モデル(力・慣性)で a・α → 左右の電流。±3A で頭打ち', C_CTRL)
box(X, 16, W, 12, '電流の制御  20kHz(PWM に同期)', 'duty = (R×目標 + Ke×角速度) / 電池の電圧 + PI\n電池の電流 7.5A 以下に。5A が 1ms で止める', C_CTRL)
box(X, 1, W, 9, 'PWM(TIM1、40kHz、センターアラインド)', 'MP6551 × 2 → 左右のモーター NFP-D8620', C_HW)
arrow(X + W / 2, 85, X + W / 2, 79.6, '目標')
arrow(X + W / 2, 67, X + W / 2, 61.6, 'v・ω の目標')
arrow(X + W / 2, 49, X + W / 2, 43.6, 'a・α の目標')
arrow(X + W / 2, 34, X + W / 2, 28.6, '電流の目標')
arrow(X + W / 2, 16, X + W / 2, 10.6, 'duty')
ax.annotate('', (X - 1.5, 38.5), (X - 1.5, 89), arrowprops=dict(arrowstyle='->', lw=1.3, color='#7f7f7f', linestyle='--', connectionstyle='arc3,rad=0.3'))
ax.text(35, 52, '軌道の a・α は\n電流の目標へ直接\n(フィードフォワード)', fontsize=8.8, color='#555', ha='center')
# センサ(左: 壁・電流、右: IMU・エンコーダ)と推定(右)
box(2, 66, 30, 14, '壁センサ  4kHz', 'OPV332 + NJW4615A × 4\nSFH 229 FA + OPA2354\nADC1(20kHz の5つの順番で1巡)', C_SENS, 10.5)
box(2, 13, 30, 13, '電流・電池  20kHz', 'INA241A3(5mΩ)× 2、電池の電圧\nADC2(PWM の真ん中で読む)', C_SENS, 10.5)
box(103, 84, 25, 11, 'IMU LSM6DSR', 'ジャイロ 6.66kHz\n(INT1 → SPI3 の DMA)・加速度', C_SENS, 10)
box(131, 84, 27, 11, 'エンコーダ MT6835 × 2', '10kHz(SPI2 の DMA)\n21ビットの角度 → 差で速度', C_SENS, 10)
box(110, 50, 44, 22, '状態の推定', '速度 v: 相補フィルタ(エンコーダ + 前後の加速度)\n角速度 ω: ジャイロ\n向き θ: ジャイロの積分\n位置: v・θ の積分', C_EST, 10.5)
arrow(115.5, 84, 125, 72.6, '', '#2a7'); arrow(144.5, 84, 138, 72.6, '', '#2a7')
ax.text(73 + 2, 75.6, '', fontsize=8)
arrow(32.5, 73, X - 0.5, 73)
ax.text(42, 74.6, '横・前の壁との距離', fontsize=8.6, ha='center')
arrow(109.5, 66, X + W + 0.5, 72)
ax.text(103, 72.5, '位置・向き', fontsize=8.6, ha='center')
arrow(109.5, 56, X + W + 0.5, 55)
ax.text(103, 57.6, 'v・ω', fontsize=8.6, ha='center')
arrow(32.5, 19.5, X - 0.5, 21)
ax.text(42, 23, '測った電流・電池の電圧', fontsize=8.6, ha='center')
box(110, 14, 44, 13, '吸引ファン', 'TIM16(TIM1 と同じ周期で同時に動かす)\n電流は ADC1 で測る。電圧の上限 7.4V(最短は 8.5V の案)', C_HW, 10.5)
ax.text(132, 8.5, '車輪とファンの PWM の同じ位置で壁センサを読む\n(点灯と消灯の引き算で PWM のノイズを消す)', fontsize=8.6, ha='center', color='#555')
# 下: 20kHz の処理の時間の流れ
ax2 = fig.add_axes([0.06, 0.04, 0.9, 0.28]); ax2.set_xlim(-5, 265); ax2.set_ylim(0, 10)
ax2.set_yticks([]); ax2.set_xlabel('時間 [µs]')
ax2.set_title('20kHz の処理の流れ(TIM1 の PWM 40kHz の2周期 = 50µs ごと。壁センサは5つの順番で 250µs = 4kHz で1巡)', fontsize=12)
for k in range(0, 11):                       # PWM 40kHz(25µs)
    ax2.plot([k * 25, k * 25], [8.6, 9.4], color='#999', lw=0.8)
ax2.text(-4, 9.0, 'PWM 40kHz', fontsize=8.5, va='center', ha='right')
reads = ['消灯', 'FL・R', 'L・FR', '空き', '空き']
spans = [(0, 5, '消灯', '#dddddd'), (5, 55, 'FL・R が点いている', '#f4b183'), (55, 105, 'L・FR が点いている', '#9dc3e6'), (105, 255, '消灯(3・4 は空き)', '#eeeeee'), (255, 262, '', '#f4b183')]
for a, b, s, c in spans:
    ax2.add_patch(plt.Rectangle((a, 5.8), b - a, 1.6, fc=c, ec='k', lw=0.6))
    if s: ax2.text((a + b) / 2, 6.6, s, ha='center', va='center', fontsize=9)
ax2.text(-4, 6.6, '発光', fontsize=8.5, va='center', ha='right')
for n in range(5):
    t0 = n * 50
    ax2.annotate('', (t0, 5.6), (t0, 8.4), arrowprops=dict(arrowstyle='->', color='#c00', lw=1.4))
    ax2.text(t0 + 1, 5.15, f'ADC1・ADC2 を起動\n読む: {reads[n]}', fontsize=7.6, color='#c00', va='top')
    ax2.add_patch(plt.Rectangle((t0 + 1, 2.0), 4, 1.2, fc='#c00', ec='none'))
    ax2.text(t0 + 6, 2.6, '20kHz の処理 3〜5µs: 電流の制御 → duty\n→ 壁センサの値を受け取り、次の組に切り替える', fontsize=7.0, va='center')
    if n % 2 == 0:
        ax2.text(t0 + 6, 0.9, 'エンコーダの読み取りを始める(10kHz)', fontsize=7.2, va='center', color='#2a7')
ax2.annotate('', (50, 7.9), (5, 7.9), arrowprops=dict(arrowstyle='<->', color='#444'))
ax2.text(27.5, 8.15, '点けてから読むまで 約 45µs(落ち着くのに要るのは 約 5µs)', ha='center', fontsize=8.2)
ax2.text(132, 0.25, '1kHz の処理は 20 回に1回(1ms):軌道 → 位置・向き → 速度・角速度 → 電流の目標、壁制御、ログ(20〜50µs、優先度は下)', fontsize=8.2, ha='center', color='#1f4e79')
fig.savefig(sys.argv[1], dpi=110)

"""エンコーダの磁石を軸受の外へ出す前と後の、車軸の真上を通る縦の断面(x = 0、右の車輪)の図(2026-11-24)。
使い方: python3 docs/calc/t24_encoder_layout_fig.py → docs/img/tire24/encoder_layout.png
寸法は機体のモデル(mechanical/vehicle/mk4_vehicle_t24.step)の値。右の車輪なので、左が外(y が小さい)"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

plt.rcParams['font.family'] = 'IPAGothic'
AZ = 12.0


def rect(ax, y0, y1, z0, z1, color, label=None, hatch=None, alpha=1.0, lw=0.6):
    ax.add_patch(Rectangle((y0, z0), y1 - y0, z1 - z0, facecolor=color, edgecolor='k', lw=lw, hatch=hatch, alpha=alpha, label=label))


def ring(ax, y0, y1, r0, r1, color, label=None, hatch=None):
    rect(ax, y0, y1, AZ + r0, AZ + r1, color, label, hatch)
    rect(ax, y0, y1, AZ - r1, AZ - r0, color, None, hatch)


def draw(ax, new):
    d = 2.0 if new else 0.0                              # 内へ動かす量
    pin_end = -18.2 if new else -20.2
    rect(ax, -36, -8, 2.0, 2.8, '#5f5a50', 'フレーム')
    pcb_edge = -14.7 if new else -16.7                   # メイン基板の車軸のまわりの切り欠き
    rect(ax, pcb_edge, -8, 13.6, 14.2, '#2e8b57', 'メイン基板(切り欠きの縁から内)')
    rect(ax, -16.0, -8, 17.8, 31.8, '#4a6fb5', '電池(|y| 16 まで、z 17.8〜)', alpha=0.85)
    ring(ax, -33.3, -24.8, 10.0, 12.0, '#333333', 'タイヤ')
    ring(ax, -33.3, -24.8, 9.2, 10.0, '#e8b04a', 'ホイール')
    rect(ax, -26.0, -24.8, AZ - 9.2, AZ + 9.2, '#e8b04a')
    ring(ax, -24.8, -22.8, 4.0, 10.65, '#8fbf8f', '71T')
    ring(ax, -23.2, -21.2, 1.5, 3.0, '#9aa7b8', '軸受 LF-630(鋼)')
    ring(ax, -21.0, -19.0, 1.5, 3.0, '#9aa7b8')
    ring(ax, -23.2, -19.0, 1.5, 1.9, '#5a6578', '軸受の内輪(鋼)')
    pin_color = '#d9d9d9' if new else '#7f7f7f'
    pin_label = '平行ピン 3×10(ステンレス SUS304、磁石にくっつかない)' if new else '平行ピン 3×8(鋼)'
    rect(ax, -28.2, pin_end, AZ - 1.5, AZ + 1.5, pin_color, pin_label, hatch='///')
    rect(ax, pin_end, pin_end + 1.0, AZ - 1.5, AZ + 1.5, '#c0392b', '磁石 φ3 × 1')
    rect(ax, -18.7 + d, -17.5 + d, 9.5, 14.5, '#111111', 'MT6835')
    rect(ax, -17.5 + d, -16.9 + d, 8.15, 16.9, '#1b7f3b', 'エンコーダ基板(z 8.15〜16.9)')
    # 寸法の書き込み
    ax.annotate('', (-16.9 + d, 17.8), (-16.9 + d, 16.9), arrowprops=dict(arrowstyle='<->', color='m'))
    ax.text(-16.8 + d, 17.15, '0.9mm', color='m', fontsize=9)
    if new:
        ax.annotate('磁石は軸受の外(0.8mm 離れる)\nうしろはステンレスのピン', (pin_end + 0.5, AZ + 1.6), (-35.5, 27.0), fontsize=9,
                    arrowprops=dict(arrowstyle='->'))
        ax.annotate('ピンが内の軸受を通り切る\n(軸受の間 1.6 → 2.2mm)', (-20.0, AZ - 1.0), (-31.5, 5.0), fontsize=9, arrowprops=dict(arrowstyle='->'))
    else:
        ax.annotate('磁石が軸受の内輪(鋼)の中、\nうしろも鋼のピン\n→ 磁束が鋼を通って外へ出にくい', (pin_end + 0.5, AZ + 1.6), (-35.5, 27.0), fontsize=9,
                    arrowprops=dict(arrowstyle='->'))
    ax.set_xlim(-36, -8)
    ax.set_ylim(0, 33)
    ax.set_aspect('equal')
    ax.grid(alpha=.25)
    ax.set_xlabel('y [mm](左が外)')
    ax.set_ylabel('z [mm](床から)')


fig, axes = plt.subplots(1, 2, figsize=(17, 8.5))
draw(axes[0], False)
axes[0].set_title('今: 磁石は軸受の中、エンコーダ基板 |y| 16.9〜17.5', fontsize=11)
draw(axes[1], True)
axes[1].set_title('新: 磁石を軸受の外へ、エンコーダ基板を 2mm 内(|y| 14.9〜15.5)', fontsize=11)
h, l = axes[1].get_legend_handles_labels()
fig.legend(h, l, loc='lower center', ncol=5, fontsize=9)
fig.suptitle('車軸の真上を通る縦の断面(x = 0、右の車輪)。電池の下の面は z 17.8 なので、エンコーダ基板(上の端 z 16.9)が電池の下に入っても 0.9mm あく', fontsize=12)
fig.tight_layout(rect=(0, 0.07, 1, 0.95))
fig.savefig('docs/img/tire24/encoder_layout.png', dpi=100)
print('docs/img/tire24/encoder_layout.png')

"""t24 のメイン基板の配置図に、IC などの名前(何の部品か)を書き込む(2026-11-24)
使い方(リポジトリの一番上で): /usr/bin/python3.12 hardware/kicad/draw_labeled_t24.py
  → hardware/kicad/KOGUMA-Mk4_t24/floorplan_labeled.png(place_main_t24.py で置き直したら、もう一度走らせる)"""
import sys, pcbnew
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon as MPoly
plt.rcParams['font.family'] = 'WenQuanYi Zen Hei'; plt.rcParams['axes.unicode_minus'] = False
import logging; logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)
import os
HERE = os.path.dirname(os.path.abspath(__file__))
b = pcbnew.LoadBoard(os.path.join(HERE, 'KOGUMA-Mk4_t24/KOGUMA-Mk4_t24.kicad_pcb'))
out = os.path.join(HERE, 'KOGUMA-Mk4_t24/floorplan_labeled.png')
X = lambda v: pcbnew.ToMM(v) - 150; Y = lambda v: 100 - pcbnew.ToMM(v)
# 名前: ref → (名前, 色)
C_MCU, C_MOT, C_PWR, C_SEN, C_UI, C_FAN = '#4c78a8', '#e45756', '#f58518', '#54a24b', '#b279a2', '#9d755d'
NAMES = {
 'U4': ('マイコン\nSTM32H725', C_MCU), 'U76': ('IMU\n(ジャイロ・加速度)', C_MCU), 'Y1': ('発振子', C_MCU),
 'U2': ('左モーターの\nドライバ MP6551', C_MOT), 'U3': ('右モーターの\nドライバ MP6551', C_MOT),
 'U6': ('左モーターの電流\nINA241A3', C_MOT), 'U7': ('右モーターの電流\nINA241A3', C_MOT),
 'R22': ('左のシャント 5mΩ', C_MOT), 'R32': ('右のシャント 5mΩ', C_MOT),
 'U1': ('3.3V の DC-DC\nLXDC55', C_PWR), 'J1': ('電池の線', C_PWR), 'D1': ('TVS', C_PWR), 'NT1': ('PGND と GND\nをつなぐ所', C_PWR),
 'C2': ('VBAT 22µF', C_PWR), 'C3': ('VBAT 22µF', C_PWR),
 'Q40': ('ファンの\nMOSFET', C_FAN), 'R43': ('ファンの\nシャント 0.1Ω', C_FAN), 'J4': ('ファンの線', C_FAN), 'D40': ('ファンの\nダイオード', C_FAN),
 'U74': ('受光のアンプ\n(FL・R)', C_SEN), 'U75': ('受光のアンプ\n(FR・L)', C_SEN),
 'U70': ('発光の定電流\n(FL)', C_SEN), 'U73': ('発光の定電流\n(FR)', C_SEN), 'U72': ('発光の定電流\n(R)', C_SEN), 'U71': ('発光の定電流\n(L)', C_SEN),
 'U5': ('BLE モジュール\nHY0020', C_UI), 'BZ1': ('ブザー', C_UI), 'SW1': ('電源スイッチ', C_UI), 'SW2': ('スイッチ\n(決定)', C_UI),
 'J7': ('デバッグの端子\n(STLINK)', C_UI), 'TP4': ('BOOT0', C_UI), 'D98': ('前の LED', C_UI), 'TP1': ('UART_RX', C_UI),
 'J5': ('左エンコーダ', C_MCU), 'J6': ('右エンコーダ', C_MCU),
 # 裏
 'Q1': ('電源スイッチの\nMOSFET', C_PWR), 'C4': ('VBAT 100µF', C_PWR), 'J2': ('左モーターの線', C_MOT), 'J3': ('右モーターの線', C_MOT),
 'D70': ('壁センサ FL\n(発光 D70・受光 D74)', C_SEN), 'D71': ('壁センサ L\n(発光 D71・受光 D77)', C_SEN), 'D72': ('壁センサ R\n(発光 D72・受光 D75)', C_SEN), 'D73': ('壁センサ FR\n(発光 D73・受光 D76)', C_SEN),
}
LED_UI = {'D96': 'No.8', 'D95': 'No.4', 'D92': 'モード4', 'D91': 'モード2', 'D90': 'モード1', 'D94': 'No.2', 'D93': 'No.1'}
# 外形
edges = []
for d in b.GetDrawings():
    if d.GetLayer() == pcbnew.Edge_Cuts:
        edges.append(d)
fig, axs = plt.subplots(1, 2, figsize=(22, 10.5))
for ax, side, title in ((axs[0], 'T', '上の面(上から見た図。右が前、上が左)'), (axs[1], 'B', '裏の面(上から透かして見た図)')):
    for d in edges:
        try:
            sh = d.GetShape()
            if sh == pcbnew.SHAPE_T_SEGMENT:
                ax.plot([X(d.GetStart().x), X(d.GetEnd().x)], [Y(d.GetStart().y), Y(d.GetEnd().y)], 'k-', lw=1)
            else:
                pts = d.GetCorners() if sh == pcbnew.SHAPE_T_RECT else None
                poly = d.GetPolyShape() if sh == pcbnew.SHAPE_T_POLY else None
                if sh in (pcbnew.SHAPE_T_ARC, pcbnew.SHAPE_T_CIRCLE, pcbnew.SHAPE_T_BEZIER) or poly is not None:
                    ps = d.GetPolyShape() if poly is not None else None
                    if ps is None:
                        d.RebuildBezierToSegmentsPointsList(pcbnew.FromMM(0.05)) if sh == pcbnew.SHAPE_T_BEZIER else None
                        pl = d.GetCorners() if False else None
                    if sh == pcbnew.SHAPE_T_CIRCLE:
                        c = d.GetCenter(); r = pcbnew.ToMM(d.GetRadius())
                        ax.add_patch(plt.Circle((X(c.x), Y(c.y)), r, fill=False, color='k', lw=1))
                    elif sh == pcbnew.SHAPE_T_ARC:
                        import numpy as np
                        c = d.GetCenter(); r = pcbnew.ToMM(d.GetRadius())
                        a0 = np.radians(-d.GetArcAngleStart().AsDegrees()) if False else None
                        st, en, mid = d.GetStart(), d.GetEnd(), d.GetArcMid()
                        import math
                        cx, cy = X(c.x), Y(c.y)
                        ang = lambda p: math.atan2(Y(p.y) - cy, X(p.x) - cx)
                        A0, A1, Am = ang(st), ang(en), ang(mid)
                        def between(a, s, e):
                            return (a - s) % (2 * math.pi) <= (e - s) % (2 * math.pi)
                        if between(Am, A0, A1):
                            t = np.linspace(A0, A0 + (A1 - A0) % (2 * math.pi), 40)
                        else:
                            t = np.linspace(A1, A1 + (A0 - A1) % (2 * math.pi), 40)
                        ax.plot(cx + r * np.cos(t), cy + r * np.sin(t), 'k-', lw=1)
                    elif poly is not None:
                        o = poly.Outline(0)
                        xs = [X(o.CPoint(i).x) for i in range(o.PointCount())]; ys = [Y(o.CPoint(i).y) for i in range(o.PointCount())]
                        ax.plot(xs + xs[:1], ys + ys[:1], 'k-', lw=1)
        except Exception as e:
            pass
    for fp in b.GetFootprints():
        ref = fp.GetReference()
        onB = fp.GetLayer() == pcbnew.B_Cu
        if (side == 'T') == onB and ref not in ('D70', 'D71', 'D72', 'D73', 'D74', 'D75', 'D76', 'D77', 'J5', 'J6'):
            continue
        if ref in ('D70', 'D71', 'D72', 'D73', 'D74', 'D75', 'D76', 'D77') and side == 'T':
            continue
        if ref in ('J5', 'J6') and side == 'T':
            continue
        cy = fp.GetCourtyard(pcbnew.B_CrtYd if onB else pcbnew.F_CrtYd)
        if cy.OutlineCount() > 0:
            bb = cy.BBox()
        else:
            bb = fp.GetBoundingBox(False)
        x0, x1, y0, y1 = X(bb.GetLeft()), X(bb.GetRight()), Y(bb.GetBottom()), Y(bb.GetTop())
        name = NAMES.get(ref); led = LED_UI.get(ref)
        if name:
            txt, col = name
            ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=col, ec=col, alpha=0.55, lw=1.2))
            big = (x1 - x0) * (y1 - y0) > 30
            lab = txt if ref.startswith('D7') else f'{ref}\n{txt}'
            ax.text((x0 + x1) / 2, (y0 + y1) / 2, lab, fontsize=8.5 if big else 6.8, ha='center', va='center', color='black', fontweight='bold' if ref in ('U4', 'U1', 'U2', 'U3', 'U5') else 'normal')
        elif led:
            ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc='#ffbf00', ec='#ffbf00', alpha=0.8))
            ax.text(x0 - 0.4, (y0 + y1) / 2, led, fontsize=6.5, ha='right', va='center')
        else:
            ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc='#dddddd', ec='#999999', alpha=0.6, lw=0.4))
    # 電池の範囲
    if side == 'T':
        ax.add_patch(Rectangle((-16.25, -16), 22.5, 32, fill=False, ec='#8b6508', lw=1.2, ls='--'))
        ax.text(-5, -15.2, '電池の下(高さ 1.2mm まで)', fontsize=8, color='#8b6508', ha='center')
        ax.annotate('前 →', (44, 33), fontsize=11)
    ax.set_aspect('equal'); ax.set_xlim(-33, 48); ax.set_ylim(-36, 36); ax.set_title(title, fontsize=13)
    ax.grid(alpha=0.2); ax.set_xlabel('x [mm](前 →)'); ax.set_ylabel('y [mm](左 ↑)')
from matplotlib.patches import Patch
fig.legend([Patch(color=c, alpha=0.6) for c in (C_MCU, C_MOT, C_PWR, C_FAN, C_SEN, C_UI, '#ffbf00')], ['マイコン・センサの入力', 'モーター', '電源', 'ファン(吸引)', '壁センサ', '表示・通信', 'UI の LED'], loc='upper center', ncol=7, fontsize=11, bbox_to_anchor=(0.5, 0.97))
fig.suptitle('KOGUMA-Mk4 t24 メイン基板の配置(部品の名前つき、2026-11-24)', fontsize=14)
fig.tight_layout(rect=(0, 0, 1, 0.93))
fig.savefig(out, dpi=110)
print('ok')

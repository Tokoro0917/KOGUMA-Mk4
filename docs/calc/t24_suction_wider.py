"""吸引する面をもっと広げられるか(2026-11-23、ブランチ claude/trusting-dirac-1tdt54)
使い方(リポジトリの一番上で): python3 docs/calc/t24_suction_wider.py → docs/img/tire24/suction_wider.png
フレームの下(スカートを貼る面)でぶつかるもの: タイヤ・71T の切り欠き(|x| < 9 で |y| > 22.3)、前後の滑り板(x ±45、φ5)、フレームの外形。
マウントのねじの頭(φ3.8、フレームの下)は、スカートの線にかからなければ吸引する面の中でも外でもよい。壁センサのホルダはフレームの上なのでぶつからない"""
import sys, math
sys.path.insert(0, 'docs/calc/frame'); sys.path.insert(0, 'mechanical/vehicle')
import t24, design as dz
from shapely.geometry import box, Point
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'WenQuanYi Zen Hei'; plt.rcParams['axes.unicode_minus'] = False
import logging; logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)
frame = dz.outline(0)
slots = [box(-dz.SLOT_L / 2, dz.SLOT_Y0, dz.SLOT_L / 2, 60), box(-dz.SLOT_L / 2, -60, dz.SLOT_L / 2, -dz.SLOT_Y0)]
skids = [Point(45, 0).buffer(2.5), Point(-45, 0).buffer(2.5)]
screws = [Point(p).buffer(1.9) for p in dz.MOUNT_SCREWS] + [Point(x, -y).buffer(1.9) for x, y in dz.MOUNT_SCREWS]
RIM = 1.5          # スカートを貼る縁(切り欠き・外形・滑り板から)
CASES = [('今(t24v2・v3)', 34.0, 17.0), ('A: 前後だけ ±40', 40.0, 17.0), ('B: 前後 ±40・横 ±20.8(ねじを動かす)', 40.0, 20.8)]
DP0 = 600 * 9.81e-3     # 吸引 600g [N]
def check(sx, sy):
    r = box(-sx, -sy, sx, sy)
    bad = []
    if not frame.buffer(-RIM).contains(r): bad.append('外形')
    if any(r.distance(s) < RIM - 1e-6 for s in slots): bad.append('切り欠き')
    if any(r.distance(s) < RIM - 1e-6 for s in skids): bad.append('滑り板')
    if any(r.exterior.distance(s) < 0.5 for s in screws): bad.append('ねじの頭')      # スカートの線がねじの頭(+0.5mm)にかかる
    return bad
fig, axs = plt.subplots(1, 3, figsize=(18, 6))
rows = []
for ax, (t, sx, sy) in zip(axs, CASES):
    A = 4 * sx * sy; per = 4 * (sx + sy); dp = DP0 / (A * 1e-6)
    leak = per * dp ** 1.5      # すき間から漏れる空気 × 負圧(ファンの仕事)の目安 ∝ 縁の長さ × 負圧^1.5
    rows.append((t, A, per, dp, leak))
    ax.fill(*frame.exterior.xy, color='#ddd', ec='#666')
    for s in slots: ax.fill(*s.intersection(box(-60, -40, 60, 40)).exterior.xy, color='#c9a227', alpha=0.6)
    for s in skids + screws: ax.fill(*s.exterior.xy, color='#555')
    ax.add_patch(plt.Rectangle((-sx, -sy), 2 * sx, 2 * sy, fill=True, color='#4e79a7', alpha=0.35, ec='#1f4e79', lw=1.5))
    ax.add_patch(plt.Rectangle((-34, -17), 68, 34, fill=False, ec='r', ls='--', lw=1))
    for p in [(0, 0)]: ax.plot(*p, 'k+')
    bad = check(sx, sy)
    ax.set_title(f'{t}\n{2*sx:.0f} × {2*sy:.1f}mm = {A:,.0f}mm²、600g の負圧 {dp:,.0f}Pa' + (f'  × {bad}' if bad else ''), fontsize=10)
    ax.set_aspect('equal'); ax.set_xlim(-55, 55); ax.set_ylim(-40, 40); ax.grid(alpha=0.2)
fig.suptitle('吸引する面(青)。赤の点線 = 今。黄 = タイヤ・71T の切り欠き、黒 = 滑り板とマウントのねじの頭(フレームの下)', fontsize=12)
fig.tight_layout(); fig.savefig('docs/img/tire24/suction_wider.png', dpi=80)
base = rows[0]
for t, A, per, dp, leak in rows:
    print(f'{t:22s} 面積 {A:6.0f}mm²({A / base[1] - 1:+.0%})、縁 {per:.0f}mm({per / base[2] - 1:+.0%})、600g の負圧 {dp:5.0f}Pa、ファンの仕事の目安 {leak / base[4]:.2f} 倍')
print('切り欠きの縁', dz.SLOT_Y0, '滑り板 x ±45 φ5')

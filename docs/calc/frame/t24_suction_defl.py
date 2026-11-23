"""frame t24v9 の吸引によるたわみ(スカートの線がどれだけ床に近づくか)と、ターンでのねじれの見積もり(2026-11-23)。
使い方(このディレクトリで): python3 t24_suction_defl.py → 数字と docs/img/frame/t24v9_suction_defl.png
- 今: フレームはマウントのねじ(4か所 × 左右)だけで持つ
- ファンの輪を貼る: ファンの台の輪(中心 (14.2, 0)、半径 16.5〜17.5)の下をフレームに貼り、台が動かないとみる
吸引の力はフレームの吸引する面に均一の圧力。たわみは吸引の力に比例する"""
import json, sys, numpy as np
sys.path.insert(0, '.')
import t24, design as dz, fem
from shapely.geometry import Point
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'IPAGothic'

SUCTION_N = 5.9                 # 吸引 600g
SKIRT_X, SKIRT_Y = 40.0, 21.3   # スカートの線(吸引する面の半分)

t24.set_suction('w2')
P = dict(json.load(open('results/t24v9_params.json')))
P.pop('base', None)
g = dz.build(**P)
ring = Point(14.2, 0).buffer(17.5, 64).difference(Point(14.2, 0).buffer(16.5, 64))


def solve(extra_clamps):
    """吸引 600g のときの、各点の下がる量(mm)を返す"""
    mesh = fem.make_mesh(g['domain'], g['pc'], 0.45, 0.15)
    M = fem.Model(mesh, g['pc'], g['clamps'] + extra_clamps, ribs=g['vribs'])
    K = M.K_bend()
    D = M.clamp_dofs_bend()
    FC, area = M.load_pressure(g['suction'], 1.0)
    w = fem.solve_multi(K, [FC * (SUCTION_N / area)], D)[0][0][M.bb.nodal_dofs[0]]
    return mesh, w


def report(name, mesh, drop):
    """スカートの前・後ろ・横の辺で、一番下がる量"""
    vx, vy = mesh.p
    front = (np.abs(vx - SKIRT_X) < 0.6) & (np.abs(vy) <= SKIRT_Y)
    rear = (np.abs(vx + SKIRT_X) < 0.6) & (np.abs(vy) <= SKIRT_Y)
    side = (np.abs(np.abs(vy) - SKIRT_Y) < 0.6) & (np.abs(vx) <= SKIRT_X)
    print(f'{name}: スカートの前の辺 {np.abs(drop[front]).max():.3f}mm、後ろの辺 {np.abs(drop[rear]).max():.3f}mm、横の辺 {np.abs(drop[side]).max():.3f}mm(吸引 600g。1,000g なら 1.7 倍)')


fig, axes = plt.subplots(1, 2, figsize=(14, 5))
for ax, (name, extra) in zip(axes, (('今(マウントのねじだけ)', []), ('ファンの輪をフレームに貼る', [ring]))):
    mesh, drop = solve(extra)
    report(name, mesh, drop)
    vx, vy = mesh.p
    tc = ax.tricontourf(vx, vy, mesh.t.T, drop * 1000, np.linspace(-5, 100, 22), cmap='viridis_r', extend='both')
    ax.plot([SKIRT_X, SKIRT_X, -SKIRT_X, -SKIRT_X, SKIRT_X], [SKIRT_Y, -SKIRT_Y, -SKIRT_Y, SKIRT_Y, SKIRT_Y], 'w--', lw=1)
    for c in g['clamps'] + extra:
        ax.fill(*c.exterior.xy, color='r')
        for hole in c.interiors:        # 輪の内側は塗らない(穴の形で白く塗り直す)
            ax.fill(*hole.xy, color='w')
    ax.set_aspect('equal')
    ax.set_title(f'{name}')
fig.colorbar(tc, ax=axes, label='下がる量 [1/1000 mm](吸引 600g)')
fig.suptitle('frame t24v9 吸引によるたわみ(赤: 固定する所、白の点線: スカートの線)')
fig.savefig('../../img/frame/t24v9_suction_defl.png', dpi=100, bbox_inches='tight')

# ターン: 横の加速度で外側のタイヤに荷重が移る(機体全体が傾く。フレームはねじれない)
m_kg, h_mm, track_mm = 0.05992, 13.78, 58.1     # 機体の重さ、重心の高さ、左右のタイヤの接地点の間
for a in (100.0, 166.0):                          # 166 m/s² は吸引 600g の滑る限界
    dN = m_kg * a * h_mm / track_mm
    N0 = (m_kg * 9.81 + SUCTION_N) / 2
    print(f'横 {a:.0f} m/s²: 外のタイヤ {N0 + dN:.1f}N・内 {N0 - dN:.1f}N(差 ±{dN:.2f}N)。'
          f'タイヤの硬さ k N/mm なら、スカートの横の辺は外側で {dN / 1 * SKIRT_Y / (track_mm / 2):.2f}/k mm 下がる')

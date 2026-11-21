"""タイヤ24mm のマウント(mount_t24.py)の絵(右側): 斜めから見た図と断面。部品は check_t24.py と同じ
使い方: python3 render_t24.py → mount_t24v1_3d.png、mount_t24v1_sections.png"""
import numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import cadquery as cq
import mount_t24 as mt
import check_t24 as ck

plt.rcParams['font.family'] = 'WenQuanYi Zen Hei'; plt.rcParams['axes.unicode_minus'] = False
COL = {'mount': '#f28e2b', 'motor': '#9e9e9e', 'motor_boss': '#9e9e9e', 'shaft': '#555', 'pinion13': '#d4af37',
       'spur71': '#d9822b', 'wheel': '#9aa5b1', 'tire': '#333', 'pin': '#777', 'magnet': '#e15759',
       'brg_out': '#4a7ab5', 'brg_in': '#4a7ab5', 'enc_board': '#2e8b57', 'MT6835': '#111', 'frame': '#5f5a50',
       'sheet': '#9ecae1', 'screw_front': '#333', 'screw_rear': '#333', 'pcb': '#6aa56a', 'fan_ring': '#bbb', 'battery': '#e0c060'}
parts = ck.parts

def tris(shape, tol=0.05):
    v, t = shape.tessellate(tol, 0.3)
    v = np.array([(p.x, p.y, p.z) for p in v])
    return v[np.array(t)] if len(t) else np.zeros((0, 3, 3))

fig = plt.figure(figsize=(14, 6.5))
for k, (elev, azim, title, skip) in enumerate((
        (22, -125, '外側の前から(タイヤ・ホイール・71T を外す)', ('tire', 'wheel', 'spur71', 'pcb', 'battery', 'frame', 'sheet', 'fan_ring')),
        (28, -50, '内側の後ろから(メイン基板・電池を外す)', ('pcb', 'battery', 'frame', 'sheet', 'fan_ring')))):
    ax = fig.add_subplot(1, 2, k + 1, projection='3d')
    for name, s in parts.items():
        if name in skip:
            continue
        T = tris(s)
        if len(T):
            ax.add_collection3d(Poly3DCollection(T, facecolor=COL.get(name, '#ccc'), edgecolor='none', alpha=0.95))
    sec = parts['frame'].intersect(cq.Solid.makeBox(48, 36, 2, pnt=cq.Vector(-30, -36, 1.5)))
    ax.add_collection3d(Poly3DCollection(tris(sec, 0.2), facecolor='#5f5a50', edgecolor='none', alpha=0.3))
    ax.set_xlim(-30, 18); ax.set_ylim(-36, 0); ax.set_zlim(0, 24)
    ax.set_box_aspect((48, 36, 24)); ax.view_init(elev, azim)
    ax.set_xlabel('x(前 +)'); ax.set_ylabel('y'); ax.set_zlabel('z'); ax.set_title(title, fontsize=10)
fig.suptitle(f'タイヤ24mm のモーターマウント {mt.VER}(オレンジ)、NFP-D8620、71T:13T、LF-630 × 2、磁石 + MT6835(緑の基板)', fontsize=12)
fig.tight_layout(); fig.savefig(f'mount_{mt.VER}_3d.png', dpi=110)

fig, axs = plt.subplots(1, 3, figsize=(17, 5.6))
for ax, (plane, val, title) in zip(axs, (('y', -22.0, '断面 y = -22.0(外の軸受・モーターの前の壁)'),
                                          ('y', -18.0, '断面 y = -18.0(MT6835 のくぼみ)'),
                                          ('z', 5.0, '断面 z = 5.0(上から)'))):
    for name, s in parts.items():
        if name == 'battery':
            continue
        cut = cq.Solid.makeBox(80, 0.02, 40, pnt=cq.Vector(-40, val, -5)) if plane == 'y' else cq.Solid.makeBox(80, 80, 0.02, pnt=cq.Vector(-40, -60, val))
        try:
            c = s.intersect(cut)
        except Exception:
            continue
        if c.Volume() < 1e-7:
            continue
        for f in c.Faces():
            n = f.normalAt()
            if (plane == 'y' and abs(n.y) > 0.9) or (plane == 'z' and abs(n.z) > 0.9):
                for j, w in enumerate([f.outerWire()] + f.innerWires()):
                    pts = np.array([(p.x, p.y, p.z) for p in w.positions(list(np.linspace(0, 1, 200)))])
                    a, b = (pts[:, 0], pts[:, 2]) if plane == 'y' else (pts[:, 0], pts[:, 1])
                    ax.fill(a, b, color=COL.get(name, '#ccc') if j == 0 else 'white', ec='k', lw=0.3, alpha=0.9 if j == 0 else 1)
    ax.set_aspect('equal'); ax.grid(alpha=.3); ax.set_title(title, fontsize=10)
    if plane == 'y':
        ax.set_xlim(-26, 18); ax.set_ylim(0, 20); ax.set_xlabel('x(前 +)'); ax.set_ylabel('z(床 = 0)'); ax.axhline(0, color='k', lw=1)
    else:
        ax.set_xlim(-26, 18); ax.set_ylim(-36, -8); ax.set_xlabel('x(前 +)'); ax.set_ylabel('y(左 +)')
fig.tight_layout(); fig.savefig(f'mount_{mt.VER}_sections.png', dpi=110)
print('ok')

"""組み立ての絵(右側): 斜めから見た図と、横から見た断面"""
import glob, os, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import cadquery as cq

COL = {'mount': '#f28e2b', 'motor': '#9e9e9e', 'motor_boss': '#9e9e9e', 'shaft': '#555', 'pinion13': '#d4af37',
       'spur41': '#eeeeee', 'wheel': '#4e79a7', 'tire15': '#222', 'pin': '#777', 'magnet': '#e15759',
       'brg_out': '#bbbbbb', 'brg_in': '#bbbbbb', 'enc_board': '#59a14f', 'AS5047P': '#111', 'frame': '#5f5a50',
       'pc_sheet': '#9ecae1', 'rib_front': '#e6550d', 'rib_rear': '#e6550d', 'screw_front': '#333', 'screw_rear': '#333',
       'nut_front': '#888', 'nut_rear': '#888'}
parts = {os.path.basename(f)[:-5]: cq.importers.importStep(f).val() for f in glob.glob('parts/*.step')}

def tris(shape, tol=0.05):
    v, t = shape.tessellate(tol, 0.3)
    v = np.array([(p.x, p.y, p.z) for p in v])
    return v[np.array(t)] if len(t) else np.zeros((0, 3, 3))

fig = plt.figure(figsize=(13, 6))
for k, (elev, azim, title) in enumerate(((22, -125, 'right side, from front-outside'), (25, -55, 'from rear-inside'))):
    ax = fig.add_subplot(1, 2, k + 1, projection='3d')
    for name, s in parts.items():
        if name.startswith('fan') or name in ('frame', 'pc_sheet') or name.startswith('rib'):
            continue
        T = tris(s)
        if len(T) == 0:
            continue
        pc = Poly3DCollection(T, facecolor=COL.get(name, '#ccc'), edgecolor='none', alpha=0.95 if name != 'pc_sheet' else 0.4)
        ax.add_collection3d(pc)
    fr = parts['frame']
    sec = fr.intersect(cq.Solid.makeBox(42, 30, 2, pnt=cq.Vector(-26, -36, 1.5)))
    T = tris(sec, 0.2)
    ax.add_collection3d(Poly3DCollection(T, facecolor='#5f5a50', edgecolor='none', alpha=0.35))
    ax.set_xlim(-26, 16); ax.set_ylim(-36, -6); ax.set_zlim(0, 20)
    ax.set_box_aspect((42, 30, 20)); ax.view_init(elev, azim)
    ax.set_xlabel('x (front +)'); ax.set_ylabel('y'); ax.set_zlabel('z'); ax.set_title(title, fontsize=9)
fig.suptitle('MK4 motor mount v2 (orange, M2 screws, PCB post) with NFP-D8620, 41T:13T, LF-630 x2, magnet + AS5047P board (green)')
fig.tight_layout(); fig.savefig('mount_v2_3d.png', dpi=110)

# 断面(y 一定の面で切る): 軸受の所 y=-25.0 と、エンコーダの所 y=-21.5
fig, axs = plt.subplots(1, 3, figsize=(15, 5))
for ax, (plane, val, title) in zip(axs, (('y', -25.4, 'section y = -25.4 (outer bearing)'),
                                          ('y', -21.8, 'section y = -21.8 (encoder pocket)'),
                                          ('z', 5.0, 'section z = 5.0 (top view)'))):
    for name, s in parts.items():
        if name.startswith('fan'):
            continue
        if plane == 'y':
            cut = cq.Solid.makeBox(80, 0.02, 40, pnt=cq.Vector(-40, val, -5))
        else:
            cut = cq.Solid.makeBox(80, 80, 0.02, pnt=cq.Vector(-40, -60, val))
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
    ax.set_aspect('equal'); ax.grid(alpha=.3); ax.set_title(title, fontsize=9)
    if plane == 'y':
        ax.set_xlim(-24, 15); ax.set_ylim(0, 16); ax.set_xlabel('x (front +)'); ax.set_ylabel('z (floor = 0)')
        ax.axhline(0, color='k', lw=1)
    else:
        ax.set_xlim(-24, 15); ax.set_ylim(-34, -10); ax.set_xlabel('x (front +)'); ax.set_ylabel('y (left +)')
fig.tight_layout(); fig.savefig('mount_v2_sections.png', dpi=110)
print('ok')

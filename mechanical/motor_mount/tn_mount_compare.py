"""ToraNeko.Mk3 のモーターマウント(v26)と MK4 のマウント(t24)を、同じ向き・同じ大きさで並べて描く(2026-11-24)。
使い方: python3 tn_mount_compare.py → tn_mount_compare.png
ToraNeko のマウントは tn_mount_extract.py が書いた tn_motor_mount_v26.step を、tn_parts.py と同じ変換(z 軸まわりに 90°)で
MK4 の向き(x 前、y 左、z 上、右側は外が -y)にそろえる。位置は車軸の中心を原点にする"""
import numpy as np
import cadquery as cq
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import mount as mm
import mount_t24 as mt

plt.rcParams['font.family'] = 'IPAGothic'


def load_tn():
    """ToraNeko のマウントを MK4 の向きにし、車軸の中心(ToraNeko の (x, -5.32, 5.21))を原点に"""
    s = cq.importers.importStep('tn_motor_mount_v26.step').val()
    s = s.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), 90)        # (x, y) → (-y, x)
    return s.translate(cq.Vector(-5.32, 0, -5.21))


def load_mk4():
    s = mm.build(mt.P).val()
    ax, az = mt.P['axle']
    return s.translate(cq.Vector(-ax, 0, -az))


def draw(ax, shape, elev, azim, title, color):
    verts, tris = shape.tessellate(0.02, 0.2)
    V = np.array([(v.x, v.y, v.z) for v in verts])
    polys = V[np.array(tris)]
    n = np.cross(polys[:, 1] - polys[:, 0], polys[:, 2] - polys[:, 0])
    n /= np.linalg.norm(n, axis=1)[:, None] + 1e-12
    light = np.array([0.4, -0.6, 0.7])
    light /= np.linalg.norm(light)
    shade = 0.35 + 0.65 * np.clip(np.abs(n @ light), 0, 1)
    base = np.array(matplotlib.colors.to_rgb(color))
    pc = Poly3DCollection(polys, facecolors=np.clip(base[None, :] * shade[:, None], 0, 1), edgecolors='none')
    ax.add_collection3d(pc)
    bb = shape.BoundingBox()
    c = np.array([(bb.xmin + bb.xmax) / 2, (bb.ymin + bb.ymax) / 2, (bb.zmin + bb.zmax) / 2])
    r = 12.5
    ax.set_xlim(c[0] - r, c[0] + r)
    ax.set_ylim(c[1] - r, c[1] + r)
    ax.set_zlim(c[2] - r, c[2] + r)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev, azim)
    ax.set_axis_off()
    ax.set_title(title, fontsize=10)


if __name__ == '__main__':
    tn = load_tn()
    mk = load_mk4()
    fig = plt.figure(figsize=(18, 11))
    views = ((25, -60, '外側の前から'), (25, 120, '内側の後ろから'), (20, 60, '内側の前から'))
    for i, (elev, azim, t) in enumerate(views):
        ax = fig.add_subplot(2, 3, i + 1, projection='3d')
        draw(ax, tn, elev, azim, f'ToraNeko.Mk3 v26(0.45g): {t}', '#7fa7d9')
        ax = fig.add_subplot(2, 3, i + 4, projection='3d')
        draw(ax, mk, elev, azim, f'MK4 {mt.VER}(1.20g): {t}', '#f2a65a')
    fig.suptitle('モーターマウントの比べ(同じ縮尺、車軸の中心をそろえた。上: ToraNeko.Mk3、下: MK4 タイヤ24mm)', fontsize=13)
    fig.tight_layout()
    fig.savefig('tn_mount_compare.png', dpi=100)
    print('tn_mount_compare.png')

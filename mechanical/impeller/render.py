"""羽根(impeller_t24.py が書き出した STL)を、斜め下と斜め上から見た図にする(2026-11-26)。
使い方(リポジトリの一番上で): python3 mechanical/impeller/render.py  → mechanical/impeller/impeller_t24v1.png"""
import os
import struct
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

HERE = os.path.dirname(os.path.abspath(__file__))
VER = 't24v1'


def load_stl(path):
    """STL(バイナリ)の三角形を (n, 3, 3) の配列で読む"""
    data = open(path, 'rb').read()
    n = struct.unpack('<I', data[80:84])[0]
    rows = np.frombuffer(data[84:84 + n * 50], dtype=np.dtype([('n', '<3f4'), ('v', '<9f4'), ('a', '<u2')]))
    return rows['v'].reshape(-1, 3, 3).astype(float)


tri = load_stl(os.path.join(HERE, f'impeller_{VER}.stl'))
# 面の向きで明るさを変える(光は斜め上から)
normal = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
normal = normal / (np.linalg.norm(normal, axis=1, keepdims=True) + 1e-12)

plt.rcParams['font.family'] = 'IPAPGothic'
fig = plt.figure(figsize=(11, 5.5))
views = [('下から(羽と外の壁)', -55, 30, np.array([0.3, 0.3, -1.0])),
         ('上から(上の板と軸の穴)', 50, 30, np.array([0.3, 0.3, 1.0]))]
for i in range(2):
    title, elev, azim, light = views[i]
    light = light / np.linalg.norm(light)
    shade = np.clip(np.abs(normal @ light), 0.15, 1.0)
    colors = np.zeros((len(tri), 4))
    colors[:, 0] = 0.25 + 0.6 * shade
    colors[:, 1] = 0.45 + 0.5 * shade
    colors[:, 2] = 0.75 + 0.25 * shade
    colors[:, 3] = 1.0
    ax = fig.add_subplot(1, 2, i + 1, projection='3d')
    ax.add_collection3d(Poly3DCollection(tri, facecolors=colors, edgecolor='none'))
    ax.set_xlim(-16, 16)
    ax.set_ylim(-16, 16)
    ax.set_zlim(-10, 22)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    ax.set_title(title, fontsize=13)
fig.suptitle(f'吸引ファンの羽根 {VER}(C 案 φ30・外の壁 φ31.2・9 枚・まっすぐ・軸の穴 φ1.18)', fontsize=14)
fig.subplots_adjust(left=0, right=1, top=0.9, bottom=0.02, wspace=0)
out = os.path.join(HERE, f'impeller_{VER}.png')
fig.savefig(out, dpi=130)
print(out)

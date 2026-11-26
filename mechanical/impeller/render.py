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
VER = 't24v3'


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
fig.suptitle(f'吸引ファンの羽根 {VER}(C 案 φ30・外の壁 φ31.2・9 枚・まっすぐ・軸の穴 φ1.18・下に接着剤のくぼみ・ハブを軸の根元の 0.2mm 手前まで)', fontsize=14)
fig.subplots_adjust(left=0, right=1, top=0.9, bottom=0.02, wspace=0)
out = os.path.join(HERE, f'impeller_{VER}.png')
fig.savefig(out, dpi=130)
print(out)


# ハブのまわりの断面(羽根の中心を通る縦の面で切った図)。寸法は impeller_t24.py の値を書き写したもの
HUB_R = 2.0
BORE_R = 1.18 / 2
GLUE_R = 2.4 / 2
GLUE_Z = 4.6
Z_BOTTOM = 3.3
Z_DISC0 = 7.2
Z_DISC1 = 8.0
SHAFT_R = 0.6
SHAFT_TIP_Z = 4.3       # 軸の先(モーターの前の面 z 9.4 から 5.1mm)
MOTOR_FACE_Z = 9.4
HUB_BOTTOM_Z = 8.6      # ファンの台のハブの底
TOP_HUB_R = 1.2         # 上へ伸ばしたハブ(t24v3)
TOP_HUB_Z = 8.9

fig2, ax = plt.subplots(figsize=(7, 6))
resin = '#9cc3ee'
for side in (1, -1):
    # 上の板(半径 4 まで描く)
    ax.add_patch(plt.Rectangle((side * BORE_R, Z_DISC0), side * (4.0 - BORE_R), Z_DISC1 - Z_DISC0, color=resin))
    # ハブ(軸の穴より上: 穴のまわり。くぼみの所: くぼみのまわり)
    ax.add_patch(plt.Rectangle((side * BORE_R, GLUE_Z), side * (HUB_R - BORE_R), Z_DISC0 - GLUE_Z, color=resin))
    ax.add_patch(plt.Rectangle((side * BORE_R, Z_DISC1), side * (TOP_HUB_R - BORE_R), TOP_HUB_Z - Z_DISC1, color=resin))
    ax.add_patch(plt.Rectangle((side * GLUE_R, Z_BOTTOM), side * (HUB_R - GLUE_R), GLUE_Z - Z_BOTTOM, color=resin))
# 軸(灰色)と、接着剤がたまる所(黄色)
ax.add_patch(plt.Rectangle((-GLUE_R, Z_BOTTOM + 0.2), 2 * GLUE_R, GLUE_Z - Z_BOTTOM - 0.2, color='#f5d76e', alpha=0.8))
ax.add_patch(plt.Rectangle((-SHAFT_R, SHAFT_TIP_Z), 2 * SHAFT_R, MOTOR_FACE_Z - SHAFT_TIP_Z, color='#888888'))
# モーター(前の面から上)と、ファンの台のハブの底
ax.add_patch(plt.Rectangle((-4.3, MOTOR_FACE_Z), 8.6, 1.2, color='#555555'))
ax.add_patch(plt.Rectangle((-1.2, MOTOR_FACE_Z - 0.3), 2.4, 0.3, color='#555555'))
ax.add_patch(plt.Rectangle((1.5, HUB_BOTTOM_Z), 3.0, MOTOR_FACE_Z - HUB_BOTTOM_Z, color='#d0d0d0'))
ax.add_patch(plt.Rectangle((-1.5, HUB_BOTTOM_Z), -3.0, MOTOR_FACE_Z - HUB_BOTTOM_Z, color='#d0d0d0'))
ax.text(2.3, 7.6, '上の板', fontsize=10, va='center')
ax.text(2.3, 5.6, 'ハブ(半径 2.0)', fontsize=10, va='center')
ax.text(1.0, 10.2, 'モーター', fontsize=10, color='white', va='center')
ax.text(2.0, 9.0, 'ファンの台の\nハブの底', fontsize=9, va='center')
ax.annotate('軸 φ1.2(φ1.18 の穴に圧入\nかかる長さ 4.3mm)', xy=(0.3, 6.5), xytext=(-6.8, 6.3), fontsize=10,
            arrowprops=dict(arrowstyle='->', color='#333333'))
ax.annotate('接着剤のくぼみ φ2.4\n(下から瞬間接着剤を入れる)', xy=(0.0, 3.9), xytext=(-6.8, 2.2), fontsize=10,
            arrowprops=dict(arrowstyle='->', color='#333333'))
ax.annotate('伸ばしたハブ(軸受の出っ張りとの間 0.2mm)', xy=(-1.0, 8.6), xytext=(-6.8, 11.3), fontsize=10,
            arrowprops=dict(arrowstyle='->', color='#333333'))
ax.annotate('軸の先 z 4.3', xy=(0.6, 4.3), xytext=(2.3, 4.0), fontsize=10,
            arrowprops=dict(arrowstyle='->', color='#333333'))
ax.set_xlim(-7, 5)
ax.set_ylim(1.5, 11.8)
ax.set_aspect('equal')
ax.set_xlabel('中心からの距離 [mm]')
ax.set_ylabel('z(床から)[mm]')
ax.set_title(f'羽根 {VER} のハブの断面(下から羽根を押し込み、下から接着する)', fontsize=12)
for side in ('top', 'right'):
    ax.spines[side].set_visible(False)
fig2.tight_layout()
out2 = os.path.join(HERE, f'impeller_{VER}_hub.png')
fig2.savefig(out2, dpi=130)
print(out2)

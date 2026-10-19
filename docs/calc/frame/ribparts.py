"""縦リブの部品(差し込み用のつめ付き)と、フレームに開ける溝を作る"""
import numpy as np
from shapely.geometry import Polygon, box, LineString, Point
from shapely import affinity

TAB_L, TAB_D = 3.0, 1.0        # つめの長さ、深さ(板の厚さ)
# 溝: 加工業者の最小の溝幅 1.5mm(カーボンラボ.jp、厚さ5mm以下)に合わせて 1.6mm。
# 長さは、つめの根元に残る刃物の丸み(R0.75)が入るよう、つめの両側に 0.9mm ずつ余らせる。すき間はエポキシで埋める
SLOT_W, SLOT_EXTRA = 1.6, 3.4
TAB_PITCH = 12.0               # つめの間隔の目安(溝と溝の間を広く取る)

def tab_positions(L):
    """つめの位置(リブの始まりからの距離)。両端から3mm、間は TAB_PITCH 前後"""
    n = max(2, int(round((L - 6.0 - TAB_L) / TAB_PITCH)) + 1)
    return np.linspace(3.0, L - 3.0 - TAB_L, n)

def rib_part(L, h):
    """リブ1本の外形(リブの面内の座標: u 長さ方向、v 高さ方向。v=0 が板の上面)"""
    p = box(0, 0, L, h)
    for s in tab_positions(L):
        p = p.union(box(s, -TAB_D, s + TAB_L, 0))
    return p

def slots_for(line):
    """フレームに開ける溝(リブの線に沿った長丸)"""
    (x0, y0), (x1, y1) = line.coords[0], line.coords[-1]
    L = line.length
    u = np.array([x1 - x0, y1 - y0]) / L
    out = []
    for s in tab_positions(L):
        a = np.array([x0, y0]) + u * (s - SLOT_EXTRA / 2 + SLOT_W / 2)
        b = np.array([x0, y0]) + u * (s + TAB_L + SLOT_EXTRA / 2 - SLOT_W / 2)
        out.append(LineString([a, b]).buffer(SLOT_W / 2, 16))
    return out

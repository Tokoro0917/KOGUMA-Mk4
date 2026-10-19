"""shapely の輪(細かい折れ線)を、DXF の直線 + 本当の円弧(LWPOLYLINE の bulge)にする。
丸ごと円の輪は CIRCLE にする。CAD・加工機で線ががたがたにならないようにするため(2026-10-19)"""
import math
import numpy as np

TOL = 0.003     # 円弧に乗っているとみなす距離 [mm]
R_MAX = 60.0    # これより大きい半径の「円弧」は直線として扱う


def _circle(a, b, c):
    """3点を通る円の中心と半径(一直線なら None)"""
    ax, ay = a; bx, by = b; cx, cy = c
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-12:
        return None
    ux = ((ax**2 + ay**2) * (by - cy) + (bx**2 + by**2) * (cy - ay) + (cx**2 + cy**2) * (ay - by)) / d
    uy = ((ax**2 + ay**2) * (cx - bx) + (bx**2 + by**2) * (ax - cx) + (cx**2 + cy**2) * (bx - ax)) / d
    return (ux, uy), math.hypot(ax - ux, ay - uy)


def _cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _drop_collinear(P):
    """一直線に並んだ途中の点を消す"""
    out = []
    n = len(P)
    for i in range(n):
        a, b, c = P[i - 1], P[i], P[(i + 1) % n]
        L = math.hypot(c[0] - a[0], c[1] - a[1])
        if L > 0 and abs(_cross(a, b, c)) / L < 1e-6:
            continue
        out.append(b)
    return out


def _fits(P, i, j, cen, r):
    """P[i..j] がすべて円の上にあり、同じ向きに曲がっているか"""
    for k in range(i, j + 1):
        if abs(math.hypot(P[k][0] - cen[0], P[k][1] - cen[1]) - r) > TOL:
            return False
    for k in range(i, j):      # 1辺が 35° より長い所は円弧ではない(長方形の角が1つの円に乗るときなど)
        if math.hypot(P[k + 1][0] - P[k][0], P[k + 1][1] - P[k][1]) > 0.6 * r:
            return False
    s = None
    for k in range(i + 1, j):
        c = _cross(P[k - 1], P[k], P[k + 1])
        if abs(c) < 1e-12:
            return False
        if s is None:
            s = c > 0
        elif (c > 0) != s:
            return False
    return True


def ring_entities(coords):
    """閉じた輪の点 → ('circle', (cx, cy), r) か ('poly', [(x, y, bulge), ...])"""
    P = [tuple(p) for p in coords]
    if P[0] == P[-1]:
        P = P[:-1]
    P = _drop_collinear(P)
    n = len(P)
    # 丸ごと円か
    c = _circle(P[0], P[n // 3], P[2 * n // 3]) if n >= 8 else None
    if c and all(abs(math.hypot(p[0] - c[0][0], p[1] - c[0][1]) - c[1]) < TOL for p in P):
        return ('circle', c[0], c[1])
    # 円弧の途中から始まらないよう、一番長い辺の始点から回す
    k0 = max(range(n), key=lambda k: math.hypot(P[(k + 1) % n][0] - P[k][0], P[(k + 1) % n][1] - P[k][1]))
    P = P[k0:] + P[:k0] + [P[k0]]          # 閉じる(最後 = 最初)
    out = []
    i = 0
    while i < len(P) - 1:
        best = None
        j = i + 2
        while j < len(P):
            c = _circle(P[i], P[(i + j) // 2], P[j])
            if c is None or c[1] > R_MAX or not _fits(P, i, j, *c):
                break
            best = (j, c)
            j += 1
        if best and best[0] - i >= 3:      # 4点以上(3辺以上)乗っていれば円弧
            j, (cen, r) = best
            a0 = math.atan2(P[i][1] - cen[1], P[i][0] - cen[0])
            a1 = math.atan2(P[j][1] - cen[1], P[j][0] - cen[0])
            ccw = _cross(P[i], P[i + 1], P[i + 2]) > 0
            d = (a1 - a0) % (2 * math.pi) if ccw else -((a0 - a1) % (2 * math.pi))
            out.append((P[i][0], P[i][1], math.tan(d / 4)))
            i = j
        else:
            out.append((P[i][0], P[i][1], 0.0))
            i += 1
    return ('poly', out)


def add_ring(msp, coords, dxfattribs=None, dx=0.0, dy=0.0):
    kind = ring_entities([(x + dx, y + dy) for x, y in coords])
    at = dict(dxfattribs or {})
    if kind[0] == 'circle':
        msp.add_circle(kind[1], kind[2], dxfattribs=at)
    else:
        msp.add_lwpolyline(kind[1], format='xyb', close=True, dxfattribs=at)


def add_polygon(msp, poly, dxfattribs=None, dx=0.0, dy=0.0):
    for q in getattr(poly, 'geoms', [poly]):
        for ring in [q.exterior] + list(q.interiors):
            add_ring(msp, list(ring.coords), dxfattribs, dx, dy)

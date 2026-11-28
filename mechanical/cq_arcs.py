"""shapely などの細かい折れ線を、直線と本当の円弧でできた CadQuery の形にする(2026-11-24)。
STEP の丸い所(窓の角・穴・外形の丸み)がギザギザ(細かい折れ線)にならないようにするため。
折れ線のどこが円弧かは docs/calc/frame/dxf_arcs.py(DXF を書くときと同じ)で見つける。
  - poly_solid(poly, z0, z1): shapely の多角形(穴あり)を、z0〜z1 の板にする
  - prism_xz(pts, y0, y1): xz 面の多角形(点の列)を、y0〜y1 に伸ばした柱にする(マウント・ホイールの肉抜きの窓)"""
import math
import os
import sys
import cadquery as cq

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../docs/calc/frame'))
import dxf_arcs


def _arc_mid(p0, p1, bulge):
    """bulge(DXF の書き方: tan(中心角 / 4)、正なら反時計回り)の円弧の、真ん中の点"""
    dx = p1[0] - p0[0]
    dy = p1[1] - p0[1]
    chord = math.hypot(dx, dy)
    sagitta = bulge * chord / 2          # 弦の真ん中から円弧の真ん中までの距離
    mx = (p0[0] + p1[0]) / 2
    my = (p0[1] + p1[1]) / 2
    return (mx + sagitta * dy / chord, my - sagitta * dx / chord)


def _drop_close(coords, min_len=0.02):
    """前の点から min_len [mm] より近い点を消す。
    shapely の buffer や丸めのあとには、0.005mm くらいの短い辺が円弧の途中に残り、円弧として見つからなくなるため"""
    pts = [tuple(p) for p in coords]
    if pts[0] == pts[-1]:
        pts = pts[:-1]
    out = [pts[0]]
    for p in pts[1:]:
        if math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) >= min_len:
            out.append(p)
    if len(out) > 3 and math.hypot(out[-1][0] - out[0][0], out[-1][1] - out[0][1]) < min_len:
        out = out[:-1]
    return out + [out[0]]


def ring_wire(coords, to3d, normal):
    """閉じた輪の点 → CadQuery の線(Wire)。to3d(u, v) は平面の点を 3D の点にする関数、normal は平面の向き"""
    kind = dxf_arcs.ring_entities(_drop_close(coords))
    if kind[0] == 'circle':
        (cu, cv), r = kind[1], kind[2]
        return cq.Wire.makeCircle(r, to3d(cu, cv), normal)
    pts = kind[1]
    edges = []
    for k in range(len(pts)):
        u0, v0, b = pts[k]
        u1, v1, _ = pts[(k + 1) % len(pts)]
        if abs(b) < 1e-9:
            edges.append(cq.Edge.makeLine(to3d(u0, v0), to3d(u1, v1)))
        else:
            um, vm = _arc_mid((u0, v0), (u1, v1), b)
            edges.append(cq.Edge.makeThreePointArc(to3d(u0, v0), to3d(um, vm), to3d(u1, v1)))
    return cq.Wire.assembleEdges(edges)


def poly_solid(poly, z0, z1, min_area=0.0):
    """shapely の多角形(MultiPolygon も可)を z0〜z1 の板にする。円弧は本当の円弧"""
    to3d = lambda u, v: cq.Vector(u, v, z0)
    normal = cq.Vector(0, 0, 1)
    out = []
    for p in getattr(poly, 'geoms', [poly]):
        if p.area < min_area:
            continue
        outer = ring_wire(list(p.exterior.coords), to3d, normal)
        inners = [ring_wire(list(r.coords), to3d, normal) for r in p.interiors]
        face = cq.Face.makeFromWires(outer, inners)
        out.append(cq.Solid.extrudeLinear(face, cq.Vector(0, 0, z1 - z0)))
    if len(out) == 1:
        return out[0]
    return cq.Compound.makeCompound(out)


def prism_xz(pts, y0, y1):
    """xz 面の多角形(点 (x, z) の列)を、y0〜y1 に伸ばした柱(cq.Workplane)にする。円弧は本当の円弧"""
    lo = min(y0, y1)
    hi = max(y0, y1)
    to3d = lambda u, v: cq.Vector(u, lo, v)
    coords = list(pts)
    if coords[0] != coords[-1]:
        coords = coords + [coords[0]]
    wire = ring_wire(coords, to3d, cq.Vector(0, 1, 0))
    face = cq.Face.makeFromWires(wire)
    return cq.Workplane().add(cq.Solid.extrudeLinear(face, cq.Vector(0, hi - lo, 0)))

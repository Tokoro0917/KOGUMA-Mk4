"""MK4 フレーム(1mm カーボン + 0.2mm ポリカーボネート)の有限要素解析。

単位: 長さ mm、力 N、応力 MPa(N/mm²)、質量 t(トン、= 1e6 g)、時間 s。
  曲げ(面外): Morley 要素(Kirchhoff の薄板)
  面内: 2次の三角形要素(平面応力)
  座屈: 面内の応力から幾何剛性を作り、曲げの剛性との固有値問題を解く
材料: 平織りのカーボン(0/90)。繊維の向きは機体の前後(x)と左右(y)に合わせる。
"""
import numpy as np
import triangle as tr
from shapely.geometry import Polygon, Point
from skfem import (MeshTri, Basis, FacetBasis, BilinearForm, LinearForm, asm, condense,
                   ElementTriMorley, ElementTriP2, ElementVector, ElementTriP0)
from skfem.helpers import dd, sym_grad, grad
from scipy.sparse.linalg import splu, eigsh

# ---- 材料 ----
CF = dict(E1=55000.0, E2=55000.0, nu12=0.05, G12=4000.0, t=1.0, rho=1.55e-9,
          Xt=600.0, Xc=500.0, Yt=600.0, Yc=500.0, S=90.0)          # 平織りカーボン(代表値)
PC = dict(E=3000.0, nu=0.38, t=0.2, rho=1.40e-9)                     # 吸引する面のシート: 硬質塩ビ 0.2mm(2026-10-19。前はポリカーボネート 0.2mm: E=2400, t=0.2, rho=1.20e-9)

def q_ortho(E1, E2, nu12, G12):
    nu21 = nu12 * E2 / E1
    den = 1 - nu12 * nu21
    return E1 / den, nu12 * E2 / den, E2 / den, G12          # Q11, Q12, Q22, Q66

def q_iso(E, nu):
    return E / (1 - nu**2), nu * E / (1 - nu**2), E / (1 - nu**2), E / (2 * (1 + nu))

Q_CF = q_ortho(CF['E1'], CF['E2'], CF['nu12'], CF['G12'])
Q_PC = q_iso(PC['E'], PC['nu'])

# ---- メッシュ ----
def _ring(coords, h, verts, segs):
    c = np.array(coords)[:-1]
    pts = []
    for i in range(len(c)):
        a, b = c[i], c[(i + 1) % len(c)]
        k = max(1, int(np.ceil(np.linalg.norm(b - a) / h)))
        for j in range(k):
            pts.append(a + (b - a) * j / k)
    i0 = len(verts)
    verts.extend(pts)
    m = len(pts)
    segs.extend([[i0 + j, i0 + (j + 1) % m] for j in range(m)])

def make_mesh(domain, inner_lines, h, max_area):
    """domain: 解析する領域(穴あり)。inner_lines: 材料の境目(ポリカーボネートの窓の輪郭)"""
    verts, segs, holes = [], [], []
    _ring(domain.exterior.coords, h, verts, segs)
    for r in domain.interiors:
        _ring(r.coords, h, verts, segs)
        holes.append(Polygon(r).representative_point().coords[0])
    for poly in inner_lines:
        _ring(poly.exterior.coords, h, verts, segs)
    A = dict(vertices=np.array(verts), segments=np.array(segs))
    if holes:
        A['holes'] = np.array(holes)
    T = tr.triangulate(A, f'pq30a{max_area}')
    return MeshTri(T['vertices'].T.copy(), T['triangles'].T.copy())

# ---- 要素ごとの材料 ----
class Model:
    def __init__(self, mesh, pc_regions, clamp_regions, intorder=4, ribs=()):
        self.m = mesh
        self.ribs = ribs
        cent = mesh.p[:, mesh.t].mean(axis=1)
        self.cent = cent
        ispc = np.zeros(mesh.t.shape[1], bool)
        for r in pc_regions:
            ispc |= np.array([r.contains(Point(x, y)) for x, y in cent.T])
        self.ispc = ispc
        clamp = np.zeros(mesh.t.shape[1], bool)
        for r in clamp_regions:
            clamp |= np.array([r.contains(Point(x, y)) for x, y in cent.T])
        self.clamp = clamp
        t = np.where(ispc, PC['t'], CF['t'])
        Q = [np.where(ispc, qp, qc) for qp, qc in zip(Q_PC, Q_CF)]
        self.t = t
        self.Q = Q
        self.D = [q * t**3 / 12 for q in Q]
        self.rhot = np.where(ispc, PC['rho'] * PC['t'], CF['rho'] * CF['t'])
        # リブ: (線, 高さ h, 足元の板の幅 w)。リブの方向の曲げ剛性 ΔEI を足元の要素に広げる
        self.rib_d = np.zeros(mesh.t.shape[1]); self.rib_nx = np.ones(mesh.t.shape[1]); self.rib_ny = np.zeros(mesh.t.shape[1])
        self.rib_rhot = np.zeros(mesh.t.shape[1]); self.rib_info = []
        area = self.elem_area()
        for (line, h, wbase) in ribs:
            d = np.array([line.distance(Point(x, y)) for x, y in cent.T])
            sel = (d <= max(0.6, wbase / 2 - 0.05)) & ~ispc
            if not sel.any():
                continue
            E = CF['E1']; tt = CF['t']
            A1, A2 = wbase * tt, tt * h
            z2 = tt / 2 + h / 2
            zb = A2 * z2 / (A1 + A2)
            Itot = wbase * tt**3 / 12 + A1 * zb**2 + tt * h**3 / 12 + A2 * (z2 - zb)**2
            dEI = E * (Itot - wbase * tt**3 / 12)
            L = line.length
            self.rib_d[sel] += dEI * L / area[sel].sum()
            (x0, y0), (x1, y1) = line.coords[0], line.coords[-1]
            n = np.array([x1 - x0, y1 - y0]); n /= np.linalg.norm(n)
            self.rib_nx[sel], self.rib_ny[sel] = n
            self.rib_rhot[sel] += CF['rho'] * tt * h * L / area[sel].sum()
            self.rib_info.append(dict(sel=sel, E=E, ztop=tt / 2 + h - zb, zbot=-(tt / 2) - zb, dEI=dEI, h=h, L=L))
        self.bb = Basis(mesh, ElementTriMorley(), intorder=intorder)          # 曲げ
        self.bi = Basis(mesh, ElementVector(ElementTriP2()), intorder=intorder)  # 面内
        self.nqp = self.bb.X.shape[1]

    def ef(self, arr):
        """要素ごとの値を、積分点ごとの配列にする"""
        return np.repeat(np.asarray(arr, float)[:, None], self.nqp, axis=1)

    # 曲げ剛性
    def K_bend(self):
        @BilinearForm
        def k(u, v, w):
            U, V = dd(u), dd(v)
            kn_u = w.nx**2 * U[0, 0] + 2 * w.nx * w.ny * U[0, 1] + w.ny**2 * U[1, 1]
            kn_v = w.nx**2 * V[0, 0] + 2 * w.nx * w.ny * V[0, 1] + w.ny**2 * V[1, 1]
            return (w.d11 * U[0, 0] * V[0, 0] + w.d12 * (U[0, 0] * V[1, 1] + U[1, 1] * V[0, 0])
                    + w.d22 * U[1, 1] * V[1, 1] + 4 * w.d66 * U[0, 1] * V[0, 1] + w.rd * kn_u * kn_v)
        d11, d12, d22, d66 = (self.ef(d) for d in self.D)
        return asm(k, self.bb, d11=d11, d12=d12, d22=d22, d66=d66, rd=self.ef(self.rib_d),
                   nx=self.ef(self.rib_nx), ny=self.ef(self.rib_ny))

    def rib_stress(self, w):
        """リブの上端・下端(板の下面)の、リブ方向の応力 [MPa] の最大"""
        H = self.bb.interpolate(w).hess.mean(axis=-1)
        out = 0.0
        for r in self.rib_info:
            s = r['sel']
            kn = self.rib_nx[s]**2 * H[0, 0][s] + 2 * self.rib_nx[s] * self.rib_ny[s] * H[0, 1][s] + self.rib_ny[s]**2 * H[1, 1][s]
            out = max(out, np.abs(r['E'] * kn * r['ztop']).max(), np.abs(r['E'] * kn * r['zbot']).max())
        return out

    def M_bend(self, extra=None):
        """質量行列。extra: (中心x, 中心y, 半径, 質量[g]) の点の質量(小さな円に広げる)"""
        rt = self.rhot.copy() + self.rib_rhot
        for (x0, y0, r, mg) in (extra or []):
            inside = (self.cent[0] - x0)**2 + (self.cent[1] - y0)**2 <= r**2
            a = self.elem_area()[inside].sum()
            assert a > 0, ('質量の位置に板がない', x0, y0)
            rt[inside] += mg * 1e-6 / a
        @BilinearForm
        def mm(u, v, w):
            return w.rt * u * v
        return asm(mm, self.bb, rt=self.ef(rt))

    def elem_area(self):
        p, t = self.m.p, self.m.t
        a = p[:, t[1]] - p[:, t[0]]
        b = p[:, t[2]] - p[:, t[0]]
        return np.abs(a[0] * b[1] - a[1] * b[0]) / 2

    def load_patch(self, x0, y0, r, F):
        """面外の力 F[N] を、半径 r の円に均一に広げる(下向きを正)"""
        inside = (self.cent[0] - x0)**2 + (self.cent[1] - y0)**2 <= r**2
        a = self.elem_area()[inside].sum()
        assert a > 0, ('荷重の位置に板がない', x0, y0)
        q = np.where(inside, F / a, 0.0)
        @LinearForm
        def f(v, w):
            return w.q * v
        return asm(f, self.bb, q=self.ef(q))

    def load_pressure(self, region, p):
        inside = np.array([region.contains(Point(x, y)) for x, y in self.cent.T])
        q = np.where(inside, p, 0.0)
        @LinearForm
        def f(v, w):
            return w.q * v
        return asm(f, self.bb, q=self.ef(q)), self.elem_area()[inside].sum()

    def clamp_dofs_bend(self):
        return np.unique(self.bb.element_dofs[:, self.clamp])

    def clamp_dofs_inplane(self):
        return np.unique(self.bi.element_dofs[:, self.clamp])

    # 曲げの応力(表面)と破壊の指数
    def bend_stress(self, w):
        H = self.bb.interpolate(w).hess.mean(axis=-1)       # (2,2,nel) 要素ごとに一定
        kx, ky, kxy = H[0, 0], H[1, 1], H[0, 1]
        d11, d12, d22, d66 = self.D
        Mx = -(d11 * kx + d12 * ky)
        My = -(d12 * kx + d22 * ky)
        Mxy = -2 * d66 * kxy
        t = self.t
        return 6 * Mx / t**2, 6 * My / t**2, 6 * Mxy / t**2

    # 面内
    def K_in(self):
        @BilinearForm
        def k(u, v, w):
            eu, ev = sym_grad(u), sym_grad(v)
            sx = w.a11 * eu[0, 0] + w.a12 * eu[1, 1]
            sy = w.a12 * eu[0, 0] + w.a22 * eu[1, 1]
            sxy = w.a66 * 2 * eu[0, 1]
            return sx * ev[0, 0] + sy * ev[1, 1] + sxy * 2 * ev[0, 1]
        a = [self.ef(q * self.t) for q in self.Q]
        return asm(k, self.bi, a11=a[0], a12=a[1], a22=a[2], a66=a[3])

    def load_edge(self, sel, F):
        """面内の力 F=(Fx,Fy)[N] を、sel(x,y) を満たす外周の辺に均一に広げる"""
        facets = self.m.facets_satisfying(lambda x: sel(x[0], x[1]), boundaries_only=True)
        fb = FacetBasis(self.m, self.bi.elem, facets=facets)
        @LinearForm
        def one(v, w):
            return v[0] * 0 + 1.0
        L = asm(LinearForm(lambda v, w: 1.0 + 0 * w.x[0]), FacetBasis(self.m, ElementTriP0(), facets=facets)).sum()
        qx, qy = F[0] / L, F[1] / L
        @LinearForm
        def f(v, w):
            return qx * v[0] + qy * v[1]
        return asm(f, fb), L

    def inplane_stress_qp(self, u):
        G = self.bi.interpolate(u).grad                     # (2,2,nel,nqp)
        exx, eyy, gxy = G[0, 0], G[1, 1], G[0, 1] + G[1, 0]
        Q = [self.ef(q) for q in self.Q]
        sx = Q[0] * exx + Q[1] * eyy
        sy = Q[1] * exx + Q[2] * eyy
        sxy = Q[3] * gxy
        return sx, sy, sxy

    def K_geo(self, sx, sy, sxy):
        """幾何剛性(面内の応力 [MPa] × 厚さ)。引っ張りが正"""
        t = self.ef(self.t)
        @BilinearForm
        def kg(u, v, w):
            gu, gv = grad(u), grad(v)
            return w.t * (w.sx * gu[0] * gv[0] + w.sy * gu[1] * gv[1]
                          + w.sxy * (gu[0] * gv[1] + gu[1] * gv[0]))
        return asm(kg, self.bb, t=t, sx=sx, sy=sy, sxy=sxy)

def tsai_hill(sx, sy, sxy, ispc=None):
    X = np.where(sx >= 0, CF['Xt'], CF['Xc'])
    Y = np.where(sy >= 0, CF['Yt'], CF['Yc'])
    fi = (sx / X)**2 - sx * sy / X**2 + (sy / Y)**2 + (sxy / CF['S'])**2
    if ispc is not None:
        fi = np.where(ispc, 0.0, fi)
    return fi

def solve_multi(K, Fs, D):
    """同じ剛性で複数の荷重を解く"""
    n = K.shape[0]
    I = np.setdiff1d(np.arange(n), D)
    lu = splu(K[I][:, I].tocsc())
    out = []
    for F in Fs:
        x = np.zeros(n)
        x[I] = lu.solve(F[I])
        out.append(x)
    return out, I

def buckling(K, KG, D, k=3):
    n = K.shape[0]
    I = np.setdiff1d(np.arange(n), D)
    A = K[I][:, I].tocsc()
    B = (-KG[I][:, I]).tocsc()
    vals = eigsh(A, k=k, M=B, sigma=1e-2, which='LM', mode='buckling', return_eigenvectors=False)
    pos = vals[vals > 0]
    return pos.min() if len(pos) else np.inf

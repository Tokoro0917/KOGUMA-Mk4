"""手計算(はりの公式)と比べて、有限要素の計算が正しいか確かめる"""
import numpy as np
from shapely.geometry import box
import fem
from scipy.sparse.linalg import eigsh

E = fem.CF['E1']; b = 2.5; t = 1.0; L = 35.0; I = b * t**3 / 12
strip = box(-3, -b/2, L, b/2)
for ma in (0.2, 0.1):
    mesh = fem.make_mesh(strip, [], 0.4, ma)
    M = fem.Model(mesh, [], [box(-3, -5, 0, 5)])
    D = M.clamp_dofs_bend()
    K = M.K_bend()
    xl = L - 0.6
    F = M.load_patch(xl, 0, 0.6, 1.0)
    (w,), _ = fem.solve_multi(K, [F], D)
    tip = np.abs(w[M.bb.nodal_dofs[0]]).max()
    print(f'[曲げ] 要素{mesh.t.shape[1]}: 先端のたわみ {tip:.4f} mm、はりの式 {xl**2*(3*L-xl)/(6*E*I):.4f} mm')
    # 固有振動数
    Mm = M.M_bend()
    I_ = np.setdiff1d(np.arange(K.shape[0]), D)
    lam = eigsh(K[I_][:, I_], k=1, M=Mm[I_][:, I_], sigma=0, which='LM', return_eigenvectors=False)
    f1 = np.sqrt(lam.min()) / 2 / np.pi
    fb = 1.875**2 / (2 * np.pi) * np.sqrt(E * I / (fem.CF['rho'] * b * t * L**4))
    print(f'[振動] 1次 {f1:.0f} Hz、はりの式 {fb:.0f} Hz')
    # 座屈(先端に軸方向の圧縮 1N)
    Ki = M.K_in()
    Fi, Lc = M.load_edge(lambda x, y: x > L - 1e-6, (-1.0, 0.0))
    (u,), _ = fem.solve_multi(Ki, [Fi], M.clamp_dofs_inplane())
    sx, sy, sxy = M.inplane_stress_qp(u)
    print(f'   圧縮応力(平均) {sx.mean():.3f} MPa (1/A = {-1/(b*t):.3f})')
    KG = M.K_geo(sx, sy, sxy)
    lam = fem.buckling(K, KG, D)
    print(f'[座屈] 限界の力 {lam:.1f} N、オイラーの式(片持ち) {np.pi**2*E*I/(4*L**2):.1f} N')
    # 面内の曲げ(横向きの力 1N)
    Fi2, _ = M.load_edge(lambda x, y: x > L - 1e-6, (0.0, 1.0))
    (u2,), _ = fem.solve_multi(Ki, [Fi2], M.clamp_dofs_inplane())
    uy = u2[M.bi.nodal_dofs[1]].max()
    Iin = t * b**3 / 12
    print(f'[面内] 先端のたわみ {uy:.5f} mm、はりの式 {L**3/(3*E*Iin):.5f} mm(せん断の分は含まない)')

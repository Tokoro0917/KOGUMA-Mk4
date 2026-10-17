"""リブの模型の確認: 平らな帯(幅4)にリブ(高さ4)を足した片持ちを、はりの式と比べる"""
import numpy as np
from shapely.geometry import box, LineString
import fem
E = fem.CF['E1']; w = 4.0; t = 1.0; h = 4.0; L = 30.0
strip = box(-3, -w/2, L, w/2)
mesh = fem.make_mesh(strip, [], 0.5, 0.2)
M = fem.Model(mesh, [], [box(-3, -5, 0, 5)], ribs=[(LineString([(0, 0), (L, 0)]), h, w)])
K = M.K_bend(); D = M.clamp_dofs_bend()
xl = L - 0.6
(wv,), _ = fem.solve_multi(K, [M.load_patch(xl, 0, 0.6, 1.0)], D)
A1, A2 = w*t, t*h; z2 = t/2 + h/2; zb = A2*z2/(A1+A2)
I = w*t**3/12 + A1*zb**2 + t*h**3/12 + A2*(z2-zb)**2
print(f'リブあり: FEM {np.abs(wv[M.bb.nodal_dofs[0]]).max():.4f} mm、はりの式 {xl**2*(3*L-xl)/(6*E*I):.4f} mm(I={I:.2f}、平らな帯だけ {w/12:.2f})')
print(f'根元のリブ上端の応力 FEM {M.rib_stress(wv):.1f} MPa、はりの式 {xl*(t/2+h-zb)/I:.1f} MPa')

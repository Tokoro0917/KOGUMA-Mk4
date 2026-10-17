"""選んだ形を細かいメッシュで計算し、図(たわみ・応力・振動・座屈)と DXF を出す"""
import json, sys, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from scipy.sparse.linalg import eigsh
import ezdxf
import fem, design as dz, analyze as an

def field_plot(ax, mesh, val, title, cmap='viridis', g=None, vmax=None):
    vx, vy = mesh.p
    if val.shape[0] == mesh.t.shape[1]:
        tp = ax.tripcolor(vx, vy, mesh.t.T, facecolors=val, cmap=cmap, vmax=vmax)
    else:
        tp = ax.tripcolor(vx, vy, mesh.t.T, val, shading='gouraud', cmap=cmap, vmax=vmax)
    plt.colorbar(tp, ax=ax, fraction=0.03)
    if g is not None:
        for p in g['pc']:
            ax.plot(*p.exterior.xy, color='w', lw=0.5, alpha=0.6)
        for c in g['clamps']:
            ax.plot(*c.exterior.xy, color='r', lw=0.8)
    ax.set_aspect('equal'); ax.set_title(title, fontsize=9); ax.set_xlim(-53, 53); ax.set_ylim(-38, 38)

def report(params, tag, max_area=0.15, h=0.45):
    g = dz.build(**params)
    mesh = fem.make_mesh(g['domain'], g['pc'], h, max_area)
    M = fem.Model(mesh, g['pc'], g['clamps'], ribs=g['vribs'])
    K = M.K_bend(); D = M.clamp_dofs_bend()
    FA = M.load_patch(45, 0, 1.0, an.LOADS['A_front'])
    FB = M.load_patch(49.2, 22.0, 1.0, an.LOADS['B_corner'])
    FC, area = M.load_pressure(g['suction'], 1.0)
    (wA, wB, wC), _ = fem.solve_multi(K, [FA, FB, FC * an.LOADS['C_suction'] / area], D)
    nd = M.bb.nodal_dofs[0]
    fig, axs = plt.subplots(3, 2, figsize=(13, 13))
    field_plot(axs[0, 0], mesh, np.abs(wA[nd]), f"LC-A front skid {an.LOADS['A_front']}N: |w| [mm]", g=g)
    field_plot(axs[0, 1], mesh, np.abs(wB[nd]), f"LC-B front corner {an.LOADS['B_corner']}N: |w| [mm]", g=g)
    sx, sy, sxy = M.bend_stress(wA)
    fiA = np.maximum(fem.tsai_hill(sx, sy, sxy, M.ispc), fem.tsai_hill(-sx, -sy, -sxy, M.ispc))
    field_plot(axs[1, 0], mesh, np.sqrt(fiA), 'LC-A failure index sqrt(Tsai-Hill) (1 = break)', cmap='inferno', g=g)
    # 振動
    Mm = M.M_bend(an.MASSES)
    I = np.setdiff1d(np.arange(K.shape[0]), D)
    lam, vec = eigsh(K[I][:, I], k=3, M=Mm[I][:, I], sigma=0, which='LM')
    o = np.argsort(lam); phi = np.zeros(K.shape[0]); phi[I] = vec[:, o[0]]
    f = np.sqrt(np.sort(lam)) / 2 / np.pi
    field_plot(axs[1, 1], mesh, np.abs(phi[nd]) / np.abs(phi[nd]).max(), f'1st mode {f[0]:.0f} Hz (2nd {f[1]:.0f}, 3rd {f[2]:.0f})', cmap='magma', g=g)
    # 面内(正面衝突)と座屈
    Ki = M.K_in(); Di = M.clamp_dofs_inplane()
    FD, _ = M.load_edge(lambda x, y: (x > dz.XE - 0.05) & (np.abs(y) < 15), (-an.LOADS['D_front'], 0))
    c = np.sqrt(0.5)
    FE, _ = M.load_edge(lambda x, y: (x > dz.XE - 6) & (y > dz.YE - 6), (-an.LOADS['E_corner'] * c, -an.LOADS['E_corner'] * c))
    (uD, uE), _ = fem.solve_multi(Ki, [FD, FE], Di)
    sx, sy, sxy = M.inplane_stress_qp(uE)
    fiE = fem.tsai_hill(sx, sy, sxy, M.ef(M.ispc).astype(bool)).max(axis=1)
    field_plot(axs[2, 0], mesh, np.sqrt(fiE), f"LC-E corner crash {an.LOADS['E_corner']}N (45deg): sqrt(Tsai-Hill)", cmap='inferno', g=g)
    sx, sy, sxy = M.inplane_stress_qp(uD)
    KG = M.K_geo(sx, sy, sxy)
    vals, vecs = eigsh(K[I][:, I].tocsc(), k=1, M=(-KG[I][:, I]).tocsc(), sigma=1e-2, which='LM', mode='buckling')
    phi = np.zeros(K.shape[0]); phi[I] = vecs[:, 0]
    field_plot(axs[2, 1], mesh, np.abs(phi[nd]) / np.abs(phi[nd]).max(),
               f"LC-D front crash buckling mode: buckles at {vals[0]*an.LOADS['D_front']:.0f} N", cmap='magma', g=g)
    fig.suptitle(f'{tag}  (carbon 1mm 0/90 woven + PC 0.2mm, mount screws = red circles = fixed)', fontsize=11)
    fig.tight_layout(); fig.savefig(f'{tag}_fields.png', dpi=100)
    # 形の図
    fig, ax = plt.subplots(figsize=(10, 7))
    for p in getattr(g['carbon'], 'geoms', [g['carbon']]):
        ax.fill(*p.exterior.xy, color='#5f5a50', ec='k', lw=.5)
        for i in p.interiors:
            ax.fill(*i.xy, color='white', ec='k', lw=.5)
    for p in g['pc']:
        ax.fill(*p.exterior.xy, color='#9ecae1', ec='#3182bd', lw=.6)
    ax.plot(*g['suction'].exterior.xy, 'r--', lw=.8)
    for c in g['clamps']:
        ax.plot(*c.exterior.xy, color='orange', lw=1)
        ax.plot(*c.centroid.xy, '+', color='orange')
    ax.set_aspect('equal'); ax.grid(alpha=.3); ax.set_xlim(-55, 55); ax.set_ylim(-40, 40)
    ax.set_title(f'{tag}: carbon (gray), PC windows (blue), suction area (red), mount M3 (orange)')
    ax.annotate('FRONT ->', (36, 37)); fig.tight_layout(); fig.savefig(f'{tag}_shape.png', dpi=120)
    # DXF
    doc = ezdxf.new(); msp = doc.modelspace()
    doc.layers.add('CARBON_OUTLINE'); doc.layers.add('M3_HOLES'); doc.layers.add('PC_SHEET')
    for p in getattr(g['carbon'], 'geoms', [g['carbon']]):
        msp.add_lwpolyline(list(p.exterior.coords), close=True, dxfattribs={'layer': 'CARBON_OUTLINE'})
        for i in p.interiors:
            msp.add_lwpolyline(list(i.coords), close=True, dxfattribs={'layer': 'CARBON_OUTLINE'})
    for c in g['clamps']:
        msp.add_circle(c.centroid.coords[0], 1.7, dxfattribs={'layer': 'M3_HOLES'})
    sheet = g['suction'].difference(__import__('shapely').geometry.Point(dz.FAN_X, 0).buffer(dz.FAN_R, 64))
    msp.add_lwpolyline(list(sheet.exterior.coords), close=True, dxfattribs={'layer': 'PC_SHEET'})
    for i in sheet.interiors:
        msp.add_lwpolyline(list(i.coords), close=True, dxfattribs={'layer': 'PC_SHEET'})
    doc.saveas(f'{tag}.dxf')
    r = an.run(params, max_area=max_area, h=h)
    json.dump(dict(params=params, result=r), open(f'{tag}_result.json', 'w'), ensure_ascii=False, indent=1, default=float)
    return r

if __name__ == '__main__':
    params = json.loads(sys.argv[2])
    print(json.dumps(report(params, sys.argv[1]), indent=1, default=float))

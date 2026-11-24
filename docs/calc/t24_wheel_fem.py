"""タイヤ24mm のホイール(t24v2)の強さとたわみを、立体の FEM で調べる(2026-11-24、ユーザー「ホイールの強度は本当に大丈夫? 吸引によるたわみもある」)。
使い方(gmsh と scikit-fem のある Python で。リポジトリの一番上から):
    python docs/calc/t24_wheel_fem.py [STEP] [名前]  → 数字と docs/img/tire24/wheel_fem_<名前>.png
やり方:
  - 形は mechanical/order_t24/05_wheel_t24v2.step(機体の座標。車軸は (0, y, 12.0)、右の車輪、外が -y)
  - gmsh で四面体に分け、scikit-fem の 2 次の要素で線形の弾性を解く
  - 材料: JLC Black Resin(引っ張りの弾性率 2,649〜2,731MPa → 2,650MPa、引っ張り強さ 41〜58MPa → 41MPa で見る、ポアソン比 0.38 と仮定)
  - 固定: 平行ピンを圧入する穴の面と穴の底(ピンは硬いとみる)
  - 力: タイヤが床から受ける力を、外の輪の外の面の下 ±30° に均一に広げる(タイヤのゴムが力を広げるとみる)。
    縦(上向き)、横(内向き = +y)、前後(+x)の 1N ずつで解き、足し合わせる
  - 前後の力(加速・減速)は 71T がギアで受けるので、71T を貼る面を固定して解く。縦・横の力はピンで受ける。
    71T は円板に貼るので実際は円板がもっと硬い(縦・横では入れない = 厳しめ)"""
import os
import sys
import numpy as np
import gmsh
from skfem import MeshTet, Basis, ElementTetP2, ElementVector, FacetBasis, asm, solve, condense
from skfem.models.elasticity import linear_elasticity, lame_parameters
from skfem.helpers import dot
from skfem import LinearForm
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.family'] = 'IPAGothic'
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..')
STEP = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'mechanical/order_t24/05_wheel_t24v2.step')
TAG = sys.argv[2] if len(sys.argv) > 2 else 't24v2'
E_MPA, NU = 2650.0, 0.38
STRENGTH_MPA = 41.0
AZ = 12.0                      # 車軸の高さ
R_OUT = 10.0                   # 外の輪の外の面(タイヤの内径)
R_PIN = 1.475                  # ピンの穴の半径(φ2.95)
Y_OUT, Y_IN = -33.3, -24.8     # 外の輪の幅
HALF_ANGLE = np.radians(30.0)  # 力を広げる範囲(真下から ±30°)


def make_mesh(size=0.45):
    """STEP を読み、四面体に分ける"""
    gmsh.initialize()
    gmsh.option.setNumber('General.Terminal', 0)
    gmsh.model.occ.importShapes(STEP)
    gmsh.model.occ.synchronize()
    gmsh.option.setNumber('Mesh.MeshSizeMax', size)
    gmsh.option.setNumber('Mesh.MeshSizeMin', 0.15)
    gmsh.option.setNumber('Mesh.MeshSizeFromCurvature', 16)
    gmsh.model.mesh.generate(3)
    tags, coords, _ = gmsh.model.mesh.getNodes()
    p = coords.reshape(-1, 3)
    index = {t: i for i, t in enumerate(tags)}
    etypes, _, enodes = gmsh.model.mesh.getElements(3)
    tets = None
    for et, en in zip(etypes, enodes):
        if et == 4:                                 # 4 点の四面体
            tets = np.array([index[n] for n in en]).reshape(-1, 4)
    gmsh.finalize()
    used = np.unique(tets)
    remap = -np.ones(len(p), int)
    remap[used] = np.arange(len(used))
    return MeshTet(p[used].T.copy(), remap[tets].T.copy())


def main():
    m = make_mesh()
    print(f'節点 {m.p.shape[1]}、四面体 {m.t.shape[1]}')
    e = ElementVector(ElementTetP2())
    basis = Basis(m, e)
    lam, mu = lame_parameters(E_MPA, NU)
    K = asm(linear_elasticity(lam, mu), basis)

    # 固定する面: ピンの穴の面と底
    def on_pin(x):
        r = np.sqrt(x[0]**2 + (x[2] - AZ)**2)
        side = (np.abs(r - R_PIN) < 0.03) & (x[1] > -28.25) & (x[1] < -23.15)
        bottom = (np.abs(x[1] + 28.2) < 0.03) & (r < R_PIN + 0.03)
        return side | bottom
    fixed_facets = m.facets_satisfying(on_pin, boundaries_only=True)
    D = basis.get_dofs(fixed_facets).all()
    print('固定する面の数', len(fixed_facets))

    # 力をかける面: 外の輪の外の面の下 ±30°
    def on_load(x):
        r = np.sqrt(x[0]**2 + (x[2] - AZ)**2)
        ang = np.arctan2(x[0], -(x[2] - AZ))        # 真下から測った角度
        return (np.abs(r - R_OUT) < 0.05) & (np.abs(ang) <= HALF_ANGLE + 1e-6) & (x[1] > Y_OUT - 0.01) & (x[1] < Y_IN + 0.01)
    load_facets = m.facets_satisfying(on_load, boundaries_only=True)
    fb = FacetBasis(m, e, facets=load_facets)
    # 前後の力(加速・減速)は、ホイールに貼った 71T がギアで受けるので、71T を貼る面(y = -24.8、半径 4.0〜9.2)を固定して解く
    def on_glue(x):
        r = np.sqrt(x[0]**2 + (x[2] - AZ)**2)
        return (np.abs(x[1] + 24.8) < 0.03) & (r > 4.0) & (r < 9.25)
    D_glue = basis.get_dofs(m.facets_satisfying(on_glue, boundaries_only=True)).all()
    from scipy.sparse.linalg import splu
    lus = {}
    for key, DD in (('pin', D), ('glue', D_glue)):
        I = np.setdiff1d(np.arange(K.shape[0]), DD)
        lus[key] = (I, splu(K[I][:, I].tocsc()))
    unit = {}
    for name, d in (('縦', (0, 0, 1.0)), ('横', (0, 1.0, 0)), ('前後', (1.0, 0, 0))):
        @LinearForm
        def f(v, w, d=d):
            return d[0] * v[0] + d[1] * v[1] + d[2] * v[2]
        F = asm(f, fb)
        total = F[basis.nodal_dofs[{(0, 0, 1.0): 2, (0, 1.0, 0): 1, (1.0, 0, 0): 0}[d]]].sum() + \
            F[basis.edge_dofs[{(0, 0, 1.0): 2, (0, 1.0, 0): 1, (1.0, 0, 0): 0}[d]]].sum()
        F = F / total                                # 合計 1N にする
        I, lu = lus['glue' if name == '前後' else 'pin']
        x = np.zeros(K.shape[0])
        x[I] = lu.solve(F[I])
        unit[name] = x
    return m, basis, unit


def stresses(m, basis, u):
    """要素ごとのミーゼス応力と最大主応力 [MPa](2 次の要素の応力を積分点で出し、要素ごとに最大をとる)"""
    lam, mu = lame_parameters(E_MPA, NU)
    w = basis.interpolate(u)
    g = w.grad                                       # (3, 3, nel, nqp)
    eps = 0.5 * (g + np.transpose(g, (1, 0, 2, 3)))
    tr = eps[0, 0] + eps[1, 1] + eps[2, 2]
    sig = 2 * mu * eps
    for i in range(3):
        sig[i, i] = sig[i, i] + lam * tr
    s = np.moveaxis(sig, (0, 1), (-2, -1))           # (nel, nqp, 3, 3)
    ev = np.linalg.eigvalsh(s)
    vm = np.sqrt(0.5 * ((ev[..., 0] - ev[..., 1])**2 + (ev[..., 1] - ev[..., 2])**2 + (ev[..., 2] - ev[..., 0])**2))
    return vm.max(axis=1), ev[..., 2].max(axis=1)


if __name__ == '__main__':
    import t24_wheel_strength as ws
    m, basis, unit = main()
    cases = []
    for suction in (600, 1000):
        n_static = (ws.M_KG + suction / 1000) * 9.81 / 2
        n_turn, f_turn = ws.wheel_loads(suction)
        cases.append((f'吸引 {suction}g 止まっている', n_static, 0.0, 0.0))
        cases.append((f'吸引 {suction}g 直線の加減速の限界', n_static, 0.0, ws.MU * n_static))
        cases.append((f'吸引 {suction}g ターンの外の車輪(滑る限界)', n_turn, f_turn, 0.0))
    cent = m.p[:, m.t].mean(axis=1)
    # 外の輪のいちばん下(接地の真上)の点のたわみ
    bottom = np.argmin((m.p[0])**2 + (m.p[2] - (AZ - R_OUT))**2 + (m.p[1] - (Y_OUT + Y_IN) / 2)**2)
    rows = []
    for name, n, f, t in cases:
        u = n * unit['縦'] + f * unit['横'] + t * unit['前後']
        vm, s1 = stresses(m, basis, u)
        k = int(np.argmax(vm))
        uz = u[basis.nodal_dofs[2]][bottom]
        uy_rim = u[basis.nodal_dofs[1]][np.argmin(m.p[0]**2 + (m.p[2] - (AZ - R_OUT))**2 + (m.p[1] - Y_OUT)**2)]
        rows.append((name, n, f, t, vm.max(), s1.max(), uz, uy_rim, cent[:, k]))
        print(f'{name}: 縦 {n:.1f}N 横 {f:.1f}N 前後 {t:.1f}N → ミーゼス 最大 {vm.max():.1f}MPa(({cent[0, k]:.1f}, {cent[1, k]:.1f}, {cent[2, k]:.1f}))、'
              f'最大主応力 {s1.max():.1f}MPa、安全率 {STRENGTH_MPA / s1.max():.1f}、接地の所が上へ {uz * 1000:.1f}µm、外の輪の端が横へ {uy_rim * 1000:.1f}µm')
    # 図: 一番厳しい場合のミーゼス応力(要素の真ん中の点)
    name, n, f, t = cases[-1][:4]
    u = n * unit['縦'] + f * unit['横'] + t * unit['前後']
    vm, s1 = stresses(m, basis, u)
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    for ax, (i, j, lab) in zip(axes, ((0, 2, 'x-z(横から)'), (1, 2, 'y-z(前から)'))):
        sc = ax.scatter(cent[i], cent[j], c=vm, s=2, cmap='inferno', vmin=0, vmax=max(5.0, np.percentile(vm, 99.9)))
        ax.set_aspect('equal')
        ax.set_title(f'{lab}')
        ax.set_xlabel(['x', 'y', 'z'][i] + ' [mm]')
        ax.set_ylabel('z [mm]')
    fig.colorbar(sc, ax=axes, label='ミーゼス応力 [MPa]')
    fig.suptitle(f'ホイール {TAG} の応力({name}: 縦 {n:.1f}N・横 {f:.1f}N。Black Resin の引っ張り強さ 41〜58MPa)')
    fig.savefig(os.path.join(ROOT, f'docs/img/tire24/wheel_fem_{TAG}.png'), dpi=100, bbox_inches='tight')

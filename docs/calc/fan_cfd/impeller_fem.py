"""吸引ファンの羽根(t24v6、C 案 φ30・9 枚・まっすぐ。t24v4 も同じやり方)が、遠心力でもげないかを立体の FEM で調べる
(2026-11-26、ユーザー「はねはもげないですか?」)。
使い方(gmsh と scikit-fem のある Python で。リポジトリの一番上から):
    python docs/calc/fan_cfd/impeller_fem.py  → 数字と docs/img/tire24/impeller_fem_t24v6.png
    python docs/calc/fan_cfd/impeller_fem.py mechanical/impeller/impeller_t24v4.step t24v4 7.2  → 前の形
結果(64,000rpm、高精細プラスチック): t24v4 は上の板の羽の内の端の角で 67MPa(安全率 0.9)。t24v5(上の板 1.2mm・羽をハブまで)は外の壁の下の端で 28MPa(2.1)。
  t24v6(上の板 0.8mm・羽をハブまで)は外の壁の下の端で 33MPa(1.8)。上の板 1.2mm だけ(羽は半径 5 から)は 67MPa(0.9)のまま
やり方(docs/calc/t24_wheel_fem.py と同じ道具):
  - 形は mechanical/impeller/impeller_t24v6.step(羽根の中心が原点、z は床から上)
  - gmsh で四面体に分け、scikit-fem の 2 次の要素で線形の弾性を解く
  - 自由度が約 86 万あり、直接法(splu)ではメモリ(15GB)が足りないので、AMG(pyamg)で前処理した共役勾配法で解く
  - 力: 遠心力(体積あたり ρ ω² r、外向き)。空気が羽を押す力は、トルク 1.7mN·m(64,000rpm)を 9 枚で分けても
    1 枚 0.02N で、遠心力(1 枚 約 12N)よりずっと小さいので入れない
  - 固定: 軸の穴の面(軸が入る所、z 4.6〜8.9)を動かない。圧入の締め付けの力は入れない
  - 遠心力だけで、形を決めた固定なら、応力は弾性率によらない(ポアソン比と密度と回転数だけで決まる)。
    なので 1 回解き、回転数の 2 乗・密度で換算する
  - 材料: DMM 高精細プラスチック(ProJet 2500、密度 1.16、引っ張り強さ 60MPa)と、高精細アクリル(1.19、22MPa)。
    ポアソン比 0.38 と仮定。弾性率は 2,700MPa(高精細プラスチック)で解き、たわみはアクリル(1,300MPa)にも換算する"""
import os
import sys
import numpy as np
import gmsh
from skfem import MeshTet, Basis, ElementTetP2, ElementVector, asm, LinearForm
from skfem.models.elasticity import linear_elasticity, lame_parameters
from scipy.sparse.linalg import cg
import pyamg
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.family'] = 'IPAGothic'
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../..')
STEP = os.path.join(ROOT, 'mechanical/impeller/impeller_t24v6.step')
TAG = 't24v6'
if len(sys.argv) > 2:          # 別の形を調べるとき: python impeller_fem.py <STEP> <名前>
    STEP = sys.argv[1]
    TAG = sys.argv[2]
E_MPA = 2700.0                 # 高精細プラスチックの引っ張りの弾性率
NU = 0.38
RHO_SOLVE = 1.16e-6            # 解くときの密度 [kg/mm³]
RPM_SOLVE = 64000.0            # 解くときの回転数(満充電で duty 100% の暴走)
R_BORE = 0.59                  # 軸の穴の半径(φ1.18)
Z_FIX = (4.6, 8.9)             # 軸が入っている高さ

# (名前, 密度 [g/cm³], 引っ張り強さ [MPa], 弾性率 [MPa])
MATERIALS = [('高精細プラスチック', 1.16, 60.0, 2700.0), ('高精細アクリル', 1.19, 22.0, 1300.0)]
# (名前, 回転数 [rpm])
SPEEDS = [('ふだん', 35000.0), ('最短走行の上限 8.5V', 45000.0), ('付ける前に回して確かめる', 56000.0), ('満充電で duty 100% の暴走', 64000.0)]


def make_mesh(size_max=0.6):
    """STEP を読み、四面体に分ける(薄い羽 0.6mm に 2 つ以上の要素が入るように、細かさは曲がり具合でも決める)"""
    gmsh.initialize()
    gmsh.option.setNumber('General.Terminal', 0)
    gmsh.model.occ.importShapes(STEP)
    gmsh.model.occ.synchronize()
    gmsh.option.setNumber('Mesh.MeshSizeMax', size_max)
    gmsh.option.setNumber('Mesh.MeshSizeMin', 0.2)
    gmsh.option.setNumber('Mesh.MeshSizeFromCurvature', 8)
    gmsh.model.mesh.generate(3)
    tags, coords, _ = gmsh.model.mesh.getNodes()
    p = coords.reshape(-1, 3)
    index = {t: i for i, t in enumerate(tags)}
    etypes, _, enodes = gmsh.model.mesh.getElements(3)
    tets = None
    for et, en in zip(etypes, enodes):
        if et == 4:
            tets = np.array([index[n] for n in en]).reshape(-1, 4)
    gmsh.finalize()
    used = np.unique(tets)
    remap = -np.ones(len(p), int)
    remap[used] = np.arange(len(used))
    return MeshTet(p[used].T.copy(), remap[tets].T.copy())


def solve_centrifugal(m):
    """RPM_SOLVE・RHO_SOLVE の遠心力で解いた変位 [mm]"""
    e = ElementVector(ElementTetP2())
    basis = Basis(m, e)
    lam, mu = lame_parameters(E_MPA, NU)
    K = asm(linear_elasticity(lam, mu), basis)
    omega = RPM_SOLVE * 2 * np.pi / 60

    @LinearForm
    def body(v, w):
        # 遠心力 [N/mm³] = 密度 [kg/mm³] × ω² × 半径 [mm] × 1e-3(kg·mm/s² → N)
        k = RHO_SOLVE * omega ** 2 * 1e-3
        return k * (w.x[0] * v[0] + w.x[1] * v[1])
    F = asm(body, basis)

    def on_bore(x):
        r = np.sqrt(x[0] ** 2 + x[1] ** 2)
        return (np.abs(r - R_BORE) < 0.02) & (x[2] > Z_FIX[0] - 0.01) & (x[2] < Z_FIX[1] + 0.01)
    fixed = m.facets_satisfying(on_bore, boundaries_only=True)
    D = basis.get_dofs(fixed).all()
    print(f'固定する面の数 {len(fixed)}、自由度 {K.shape[0]}')
    I = np.setdiff1d(np.arange(K.shape[0]), D)
    u = np.zeros(K.shape[0])
    A = K[I][:, I].tocsr()
    # AMG の前処理: 剛体の動き(3 つの平行移動と 3 つの回転)を、粗い所でも表せるように渡す
    xyz = basis.doflocs[:, I]
    comp = np.zeros(K.shape[0], int)
    comp[basis.nodal_dofs[1]] = 1
    comp[basis.nodal_dofs[2]] = 2
    comp[basis.edge_dofs[1]] = 1
    comp[basis.edge_dofs[2]] = 2
    comp = comp[I]
    B = np.zeros((len(I), 6))
    for c in range(3):
        B[comp == c, c] = 1.0
    B[comp == 0, 3] = -xyz[1, comp == 0]
    B[comp == 1, 3] = xyz[0, comp == 1]
    B[comp == 1, 4] = -xyz[2, comp == 1]
    B[comp == 2, 4] = xyz[1, comp == 2]
    B[comp == 2, 5] = -xyz[0, comp == 2]
    B[comp == 0, 5] = xyz[2, comp == 0]
    ml = pyamg.smoothed_aggregation_solver(A, B=B, max_coarse=2000)
    residuals = []
    x, info = cg(A, F[I], rtol=1e-8, maxiter=2000, M=ml.aspreconditioner(),
                 callback=lambda xk: residuals.append(0))
    print(f'共役勾配法: {len(residuals)} 回のくり返し(info {info}。0 なら収束)')
    u[I] = x
    return basis, u


def stresses(basis, u):
    """要素ごとのミーゼス応力と最大主応力 [MPa](積分点の最大)"""
    lam, mu = lame_parameters(E_MPA, NU)
    g = basis.interpolate(u).grad
    eps = 0.5 * (g + np.transpose(g, (1, 0, 2, 3)))
    tr = eps[0, 0] + eps[1, 1] + eps[2, 2]
    sig = 2 * mu * eps
    for i in range(3):
        sig[i, i] = sig[i, i] + lam * tr
    s = np.moveaxis(sig, (0, 1), (-2, -1))
    ev = np.linalg.eigvalsh(s)
    vm = np.sqrt(0.5 * ((ev[..., 0] - ev[..., 1]) ** 2 + (ev[..., 1] - ev[..., 2]) ** 2 + (ev[..., 2] - ev[..., 0]) ** 2))
    return vm.max(axis=1), ev[..., 2].max(axis=1)


Z_PLATE_BOTTOM = 7.2          # 上の板の下の面(t24v6・t24v4。t24v5 は 6.8: 3 番目の引数で変える)


def where(c):
    """要素の真ん中の位置から、羽根のどこかを言葉にする"""
    r = np.hypot(c[0], c[1])
    if r > 14.9:
        return '外の壁'
    if c[2] > Z_PLATE_BOTTOM - 0.05 and r > 2.6:
        return '上の板'
    if r < 2.6:
        return 'ハブ'
    return '羽'


if __name__ == '__main__':
    if len(sys.argv) > 3:
        Z_PLATE_BOTTOM = float(sys.argv[3])
    m = make_mesh()
    print(f'節点 {m.p.shape[1]}、四面体 {m.t.shape[1]}')
    basis, u = solve_centrifugal(m)
    vm, s1 = stresses(basis, u)
    cent = m.p[:, m.t].mean(axis=1)
    r_cent = np.hypot(cent[0], cent[1])
    k = int(np.argmax(s1))
    print(f'{RPM_SOLVE:.0f}rpm・密度 {RHO_SOLVE * 1e6:.2f}: 最大主応力 {s1.max():.2f}MPa({where(cent[:, k])}、'
          f'({cent[0, k]:.1f}, {cent[1, k]:.1f}, {cent[2, k]:.1f}))、ミーゼス 最大 {vm.max():.2f}MPa')
    # 場所ごとの最大(羽・上の板・外の壁・ハブ)
    for part in ('羽', '上の板', '外の壁', 'ハブ'):
        mask = np.array([where(cent[:, i]) == part for i in range(cent.shape[1])])
        j = np.where(mask)[0][np.argmax(s1[mask])]
        print(f'  {part}: 最大主応力 {s1[mask].max():.2f}MPa(半径 {r_cent[j]:.1f}、z {cent[2, j]:.1f})、上から 0.5% の値 {np.percentile(s1[mask], 99.5):.2f}MPa')
    # 羽の先(外の壁の上)が外へ広がる量
    rim = np.hypot(m.p[0], m.p[1]) > 15.55
    ux = u[basis.nodal_dofs[0]]
    uy = u[basis.nodal_dofs[1]]
    grow = ((ux * m.p[0] + uy * m.p[1]) / np.hypot(m.p[0], m.p[1]))[rim].max()
    print(f'  外の壁が外へ広がる量 {grow * 1000:.1f}µm(弾性率 {E_MPA:.0f}MPa)')
    print()
    for name, rho, strength, e_mat in MATERIALS:
        for speed_name, rpm in SPEEDS:
            scale = (rho * 1e-6 / RHO_SOLVE) * (rpm / RPM_SOLVE) ** 2
            peak = s1.max() * scale
            print(f'{name} {rpm:,.0f}rpm({speed_name}): 最大主応力 {peak:.1f}MPa、安全率 {strength / peak:.1f}、'
                  f'外の壁が広がる {grow * scale * E_MPA / e_mat * 1000:.0f}µm')
    # 図: 64,000rpm・高精細プラスチックの最大主応力(要素の真ん中の点)。羽の付け根が見えるよう、下から見た図と横から見た図
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.5))
    vmax = np.percentile(s1, 99.9)
    order = np.argsort(s1)
    sc = axes[0].scatter(cent[0, order], cent[1, order], c=s1[order], s=1.5, cmap='inferno', vmin=0, vmax=vmax)
    axes[0].set_aspect('equal')
    axes[0].set_title('上から見た図(重なった所は、応力の大きい点を上に描く)')
    axes[0].set_xlabel('x [mm]')
    axes[0].set_ylabel('y [mm]')
    axes[1].scatter(r_cent[order], cent[2, order], c=s1[order], s=1.5, cmap='inferno', vmin=0, vmax=vmax)
    axes[1].set_title('中心からの距離と高さ(9 枚を重ねて見る)')
    axes[1].set_xlabel('中心からの距離 [mm]')
    axes[1].set_ylabel('z [mm]')
    fig.colorbar(sc, ax=axes, label='最大主応力 [MPa]')
    fig.suptitle(f'羽根 {TAG} の遠心力による応力({RPM_SOLVE:,.0f}rpm、高精細プラスチック 密度 1.16。引っ張り強さ 60MPa)')
    out = os.path.join(ROOT, f'docs/img/tire24/impeller_fem_{TAG}.png')
    fig.savefig(out, dpi=100, bbox_inches='tight')
    print(out)

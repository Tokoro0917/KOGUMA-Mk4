"""タイヤ24mm 用のフレーム(t24、2026-11-21、ブランチ claude/trusting-dirac-1tdt54)。
frame v6.9 のパラメータ(results/v6_9_params.json)のまま、design.py の定数だけをタイヤ24mm の並びに変えて作り、FEM で計算する。
  - タイヤ・71T の所は外へ開いた切り欠き(|y| > 22.3、前後 SLOT_L)。フレームの外側の帯はなくす(spec「車輪の並びとフレームの幅」)
  - モーターマウント t24v2 のねじ (8, ±19.5)・(-21, ±19.5)、ファンの台の継ぎ目 (14, ±20.3)
  - 横からの衝突(F)は、切り欠きの前後のフレームの横の辺(|y| = 35、9 < |x| < 16.7)で受ける(v6.9 はタイヤの外の帯 |x| < 8)
  - frame t24v2(案 w): 吸引する面を 68 × 34mm に広げた(v1 は 60 × 30mm)。シートはマウントが載る所を切る(g['sheet'])
使い方(このディレクトリで): python3 t24.py [max_area(既定 0.15)] [案の名前 ...]
  → results/t24_<案>_result.json、params.json。案は下の VARIANTS"""
import json, os, sys, time
import numpy as np
from scipy.sparse.linalg import eigsh
import design as dz

# ---- タイヤ24mm の並び(右側の値を正の y で) ----
dz.SLOT_L, dz.SLOT_Y0, dz.SLOT_Y1 = 18.0, 22.3, 40.0   # 切り欠き: 前後18mm(z 3.0 でタイヤの前後 ±7.94、すき間約1mm)、71T の内の面 22.8 から 0.5mm
dz.MOUNT_SCREWS = [(-21.0, 18.9), (6.8, 18.9)]    # 2026-11-23(t24v4): (-21, ±19.5)・(8, ±19.5) から内へ。吸引する面を横 ±21.3 に広げ、ねじの頭(φ3.8)を面の中に入れるため。
                                                  # 前は柱(半径 2.4)がファンの囲い(半径 17.5)から 0.4mm、ねじの頭が基板の車軸の切り欠き(x 4.5)から 0.4mm になる所
dz.FAN_JOINTS = [(14.0, 20.3), (14.0, -20.3)]
dz.G_REAR = (-25.5, 19.0)                               # 骨G の始まり(後ろの耳のすぐ後ろ)
dz.MOUNT_PAD = (-25.0, 12.5, 15.0, dz.SLOT_Y0 + 0.5)    # マウントが載る所(窓を開けない)。マウントは |y| 15.3 から
MOUNT_PAD_DEFAULT = dz.MOUNT_PAD
# 2026-11-23(t24v6): ねじのまわりの肉(半径 BOSS_R + 0.8 = 4.5)が上の四角から 0.5〜0.6mm はみ出して、窓の辺に段やへこみができていたので、
# 四角をねじのまわりの肉を含む大きさにする(窓の辺がまっすぐになる)
MOUNT_PAD_SMOOTH = (-21.0 - 4.5, 12.5, 18.9 - 4.5, 18.9 + 4.5)

SUCTION = {'v1': (30.0, 15.0),     # 吸引する面の半分(x, y)。v1 は main と同じ 60 × 30mm
           'w': (34.0, 17.0),      # 68 × 34mm(2026-11-21): 横はマウントのねじの頭(|y| 17.6 から)、前は横の壁センサのホルダ(x 36.5 から)まで
           'w2': (40.0, 21.3)}     # 80 × 42.6mm(2026-11-23、t24v4): 前後は滑り板(x ±45、φ5)の手前、横はタイヤ・71T の切り欠き(|y| 22.3)まで 1.0mm。
                                   # マウントのねじの頭(|y| 17.0〜20.8)は面の中。壁センサのホルダはフレームの上なのでぶつからない(docs/calc/t24_suction_wider.py)
def set_suction(name):
    dz.SX, dz.SY = SUCTION[name]
SHEET_CUT = (-24.0, 11.0, 15.2)   # 吸引する面のシート(塩ビ)を切る所: マウントがカーボンに直に載る所(x0, x1, |y| から外)
dz.ENC_BOARD = (-3.0, 3.0, 16.9, 17.5)                  # エンコーダ基板はフレームまで来ないが、窓の計算の都合で残す所

MOUTH_R = 1.5                                           # 切り欠きの口の角(フレームの外側の角)を丸める半径
SMALL_WINDOW = 25.0                                     # これより小さい窓(吸引する面の外)は開けない [mm²]
_build = dz.build
def build_t24(**kw):
    """design.build の形から、切り欠きの口の角 (±SLOT_L/2, ±YB) を半径 MOUTH_R で丸める(壁に引っかからないように)。
    _pad_m: 壁センサのホルダの当たる所のまわりの余白(既定 1.0)、_small: 吸引する面の外の窓をこれより小さければ開けない(既定 SMALL_WINDOW)"""
    from shapely.geometry import box, Point
    from shapely.ops import unary_union
    global SMALL_WINDOW
    kw = dict(kw)
    dz.SENSOR_PAD_M = kw.pop('_pad_m', 1.0)
    dz.MOUNT_PAD = kw.pop('_mount_pad', MOUNT_PAD_DEFAULT)      # マウントが載る所(窓を開けない四角)
    small_window = kw.pop('_small', 25.0)
    g = _build(**kw)
    x0, y0, r = dz.SLOT_L / 2, dz.YB, MOUTH_R
    cuts = []
    for sx in (1, -1):
        for sy in (1, -1):
            sq = box(min(sx * x0, sx * (x0 + r)), min(sy * y0, sy * (y0 - r)), max(sx * x0, sx * (x0 + r)), max(sy * y0, sy * (y0 - r)))
            cuts.append(sq.difference(Point(sx * (x0 + r), sy * (y0 - r)).buffer(r, 64)))
    c = unary_union(cuts)
    g['domain'], g['carbon'] = g['domain'].difference(c), g['carbon'].difference(c)
    # 吸引する面の外の小さな窓(SMALL_WINDOW mm² 未満)は開けない(骨を細くすると、吸引する面の角のそばに小さな窓ができ、隣の窓との間が加工できる幅より細くなるため)
    from shapely.geometry import Polygon
    small = [Polygon(r) for poly in getattr(g['carbon'], 'geoms', [g['carbon']]) for r in poly.interiors
             if Polygon(r).area < small_window and not g['suction'].buffer(1.0).contains(Polygon(r).centroid)]
    if small:
        fill = unary_union(small).buffer(0.01)
        g['domain'], g['carbon'] = g['domain'].union(fill.intersection(g['domain'].convex_hull)), g['carbon'].union(fill)
    # シート: 吸引する面からファンの穴と、マウントが載る所(吸引する面が |y| 15.2 より広いとき)を除く。そこはカーボンなので空気は漏れない
    x0, x1, yc = SHEET_CUT
    g['sheet'] = (g['suction'].difference(Point(dz.FAN_X, 0).buffer(dz.FAN_R, 64))
                  .difference(box(x0, yc, x1, 60)).difference(box(x0, -60, x1, -yc)))
    return g
dz.build = build_t24

# 前の壁センサ FL・FR を前へ(2026-11-21、(17, ±30.75) → (20.8, ±30.35)): (17, ±30.75) のままだと、ホルダの後ろから出る足の穴(x 9.9〜12.3)がタイヤ(基板の高さで x 11.9 まで、
# |y| 24.8〜33.3)の上に来て、基板の車輪の所の切り欠きにも入る。足の穴の後ろの端が切り欠き(x 12.2)から 0.2mm 以上、
# ホルダの外の角がフレームの外形から 0.5mm 以上内側になる一番後ろの位置。向き(外へ 7°)は同じ。pcb_shape.SENS を書き換える(フレームのホルダの当たる所・基板の外形・機体が使う)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../mechanical/vehicle'))
import pcb_shape as _ps
SENS_FRONT = ((20.8, 30.35), 7.0)   # 足のパッド(1.6mm の四角)が基板の外形(切り欠きの角の丸みを含む)から 0.3mm、ホルダがフレームから 0.56mm
_ps.SENS['FL'] = SENS_FRONT
_ps.SENS['FR'] = ((SENS_FRONT[0][0], -SENS_FRONT[0][1]), -SENS_FRONT[1])

import fem, analyze as an
set_suction('w2')    # 2026-11-23 から frame t24v4(吸引する面 80 × 42.6mm。t24v2・v3 は 'w' の 68 × 34mm)。t24.py を読み込むほかのスクリプト(機体・基板・注文)はこの値で作る

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = json.load(open(os.path.join(HERE, 'results/v6_9_params.json')))
VARIANTS = {
    'a': dict(BASE),                                             # v6.9 そのまま(マウントの下・切り欠きの前後の横の帯に窓)
    'b': dict(BASE, mount_windows=['pad2']),                     # 切り欠きの前後の横の帯には窓を開けない
    'c': dict(BASE, mount_windows=[]),                           # マウントの下にも窓を開けない
    'w': dict(BASE, _suction='w'),                               # a の形で、吸引する面を 68 × 34mm に
    # w を軽くする案(2026-11-21): 前の骨・枠・背骨も後ろと同じ 1.6mm に(加工できる一番細い幅 1.5mm に公差を見た値)
    'w16': dict(BASE, _suction='w', rim=1.6, end_edge=1.6, spine_root=1.6, spine_tip=1.6, brace_w=1.6, brace_w_each={'A': 1.6}, land=2.0),
    'w16l': dict(BASE, _suction='w', rim=1.6, end_edge=1.6, spine_root=1.6, spine_tip=1.6, brace_w=1.6, brace_w_each={'A': 1.6}, land=1.6, inner_spine=1.6),
    # 2026-11-23(frame t24v4): w16l の形で、吸引する面を 80 × 42.6mm に
    'w2': dict(BASE, _suction='w2'),                             # 骨は v6.9 のまま(前 2.0mm・後ろ 1.6mm)
    'w2f': dict(BASE, _suction='w2', rim=1.6, end_edge=1.6, inner_spine=1.6, land=1.6),      # 前の骨・背骨・筋交いは 2.0mm のまま、枠・辺だけ 1.6mm
    'w2lT': dict(BASE, _suction='w2', rim=1.6, end_edge=1.6, spine_root=1.6, spine_tip=1.6, brace_w=1.6, brace_w_each={'A': 1.6}, land=1.6, inner_spine=1.6, rect_ribs=['T'], rib_w=1.6),
    # 2026-11-23(frame t24v5 の案): w2lX から、ホルダの当たる所のまわりを 1.0 → 0.3mm、窓の角の丸み 2 → 1mm、小さな窓も開ける(10mm² から)
    'w2lXc': dict(BASE, _suction='w2', rim=1.6, end_edge=1.6, spine_root=1.6, spine_tip=1.6, brace_w=1.6, brace_w_each={'A': 1.6}, land=1.6, inner_spine=1.6, rect_ribs=['X'], rib_w=1.6,
                  fillet=1.0, end_window_min=10.0, _pad_m=0.3, _small=10.0),
    'w2lXp': dict(BASE, _suction='w2', rim=1.6, end_edge=1.6, spine_root=1.6, spine_tip=1.6, brace_w=1.6, brace_w_each={'A': 1.6}, land=1.6, inner_spine=1.6, rect_ribs=['X'], rib_w=1.6, _pad_m=0.3),                                    # ホルダのまわりだけ 0.3mm
    'w2lXs': dict(BASE, _suction='w2', rim=1.6, end_edge=1.6, spine_root=1.6, spine_tip=1.6, brace_w=1.6, brace_w_each={'A': 1.6}, land=1.6, inner_spine=1.6, rect_ribs=['X'], rib_w=1.6, end_window_min=10.0, _small=10.0),               # 小さな窓だけ
    'w2lXf': dict(BASE, _suction='w2', rim=1.6, end_edge=1.6, spine_root=1.6, spine_tip=1.6, brace_w=1.6, brace_w_each={'A': 1.6}, land=1.6, inner_spine=1.6, rect_ribs=['X'], rib_w=1.6, fillet=1.0),                                     # 角の丸みだけ 1mm
    'w2lXps': dict(BASE, _suction='w2', rim=1.6, end_edge=1.6, spine_root=1.6, spine_tip=1.6, brace_w=1.6, brace_w_each={'A': 1.6}, land=1.6, inner_spine=1.6, rect_ribs=['X'], rib_w=1.6, end_window_min=10.0, _pad_m=0.3, _small=10.0),  # ホルダのまわり + 小さな窓
    'w2lXf15': dict(BASE, _suction='w2', rim=1.6, end_edge=1.6, spine_root=1.6, spine_tip=1.6, brace_w=1.6, brace_w_each={'A': 1.6}, land=1.6, inner_spine=1.6, rect_ribs=['X'], rib_w=1.6, fillet=1.5, end_window_min=10.0, _pad_m=0.3, _small=10.0),
    'w2lXf17': dict(BASE, _suction='w2', rim=1.6, end_edge=1.6, spine_root=1.6, spine_tip=1.6, brace_w=1.6, brace_w_each={'A': 1.6}, land=1.6, inner_spine=1.6, rect_ribs=['X'], rib_w=1.6, fillet=1.75, end_window_min=10.0, _pad_m=0.3, _small=10.0),
    'w2lXf15s': dict(BASE, _suction='w2', rim=1.6, end_edge=1.6, spine_root=1.6, spine_tip=1.6, brace_w=1.6, brace_w_each={'A': 1.6}, land=1.6, inner_spine=1.6, rect_ribs=['X'], rib_w=1.6, fillet=1.5, end_window_min=10.0, _pad_m=0.3, _small=10.0, _mount_pad=MOUNT_PAD_SMOOTH),   # frame t24v6: 窓の辺をまっすぐに
    'w2lXf15se': dict(BASE, _suction='w2', rim=1.6, end_edge=2.5, spine_root=1.6, spine_tip=1.6, brace_w=1.6, brace_w_each={'A': 1.6}, land=1.6, inner_spine=1.6, rect_ribs=['X'], rib_w=1.6, fillet=1.5, end_window_min=10.0, _pad_m=0.3, _small=10.0, _mount_pad=MOUNT_PAD_SMOOTH),   # frame t24v7: 前の辺 2.5mm(後ろは end_edge_rear 1.6 のまま)
    'w2lX': dict(BASE, _suction='w2', rim=1.6, end_edge=1.6, spine_root=1.6, spine_tip=1.6, brace_w=1.6, brace_w_each={'A': 1.6}, land=1.6, inner_spine=1.6, rect_ribs=['X'], rib_w=1.6),
    'w2lTX': dict(BASE, _suction='w2', rim=1.6, end_edge=1.6, spine_root=1.6, spine_tip=1.6, brace_w=1.6, brace_w_each={'A': 1.6}, land=1.6, inner_spine=1.6, rect_ribs=['T', 'X'], rib_w=1.6),
    'w2l': dict(BASE, _suction='w2', rim=1.6, end_edge=1.6, spine_root=1.6, spine_tip=1.6, brace_w=1.6, brace_w_each={'A': 1.6}, land=1.6, inner_spine=1.6),
    # w16・w16l は、筋交い A と窓の間(35.3, ±16.7)に加工できる幅(1.5mm)より細い所ができる。筋交い A だけ 2.0mm に戻す
    'w16a': dict(BASE, _suction='w', rim=1.6, end_edge=1.6, spine_root=1.6, spine_tip=1.6, brace_w=1.6, brace_w_each={'A': 2.0}, land=2.0),
    'w16al': dict(BASE, _suction='w', rim=1.6, end_edge=1.6, spine_root=1.6, spine_tip=1.6, brace_w=1.6, brace_w_each={'A': 2.0}, land=1.6, inner_spine=1.6),
}

def run(params, max_area=0.15, h=0.45):
    """analyze.run と同じ。ただし横からの衝突 F は切り欠きの前後の横の辺で受ける"""
    params = dict(params); params.pop('base', None)
    set_suction(params.pop('_suction', 'v1'))
    t0 = time.time()
    g = dz.build(**params)
    mc, mp, iz = dz.mass_iz(g)
    mesh = fem.make_mesh(g['domain'], g['pc'], h, max_area)
    M = fem.Model(mesh, g['pc'], g['clamps'], ribs=g['vribs'])
    res = dict(m_carbon=mc, m_pc=mp, iz=iz, nel=mesh.t.shape[1])
    L = an.LOADS
    K = M.K_bend(); D = M.clamp_dofs_bend()
    FA = M.load_patch(45, 0, 1.0, L['A_front']); FR = M.load_patch(-45, 0, 1.0, L['A_rear'])
    FB = M.load_patch(49.2, 22.0, 1.0, L['B_corner'])
    FC, area = M.load_pressure(g['suction'], 1.0)
    ws, _ = fem.solve_multi(K, [FA, FR, FB, FC * (L['C_suction'] / area)], D)
    vx, vy = mesh.p
    wv = [w[M.bb.nodal_dofs[0]] for w in ws]
    near = lambda x0, y0, r: (vx - x0)**2 + (vy - y0)**2 <= r**2
    res['dA'] = np.abs(wv[0][near(45, 0, 1.0)]).max()
    res['dA_rear'] = np.abs(wv[1][near(-45, 0, 1.0)]).max()
    res['dB'] = np.abs(wv[2][near(49.2, 22, 1.0)]).max()
    for name, w in zip(('A', 'A_rear', 'B', 'C'), ws):
        sx, sy, sxy = M.bend_stress(w)
        fi = max(fem.tsai_hill(sx, sy, sxy, M.ispc).max(), fem.tsai_hill(-sx, -sy, -sxy, M.ispc).max())
        res[f'SF_{name}'] = 1 / np.sqrt(fi)
    Mm = M.M_bend(an.MASSES)
    I = np.setdiff1d(np.arange(K.shape[0]), D)
    lam = eigsh(K[I][:, I], k=3, M=Mm[I][:, I], sigma=0, which='LM', return_eigenvectors=False)
    res['f1'] = np.sqrt(np.sort(lam)[0]) / 2 / np.pi
    Ki = M.K_in(); Di = M.clamp_dofs_inplane()
    FD, _ = M.load_edge(lambda x, y: (x > dz.XE - 0.05) & (np.abs(y) < 15), (-L['D_front'], 0))
    c = np.sqrt(0.5)
    FE, _ = M.load_edge(lambda x, y: (x > dz.XE - 6) & (y > dz.YE - 6), (-L['E_corner'] * c, -L['E_corner'] * c))
    FF, nF = M.load_edge(lambda x, y: (y > dz.YB - 0.05) & (np.abs(x) > dz.SLOT_L / 2) & (np.abs(x) < dz.XB), (0, -L['F_side']))
    us, _ = fem.solve_multi(Ki, [FD, FE, FF], Di)
    for name, u in zip(('D', 'E', 'F'), us):
        sx, sy, sxy = M.inplane_stress_qp(u)
        res[f'SF_{name}'] = 1 / np.sqrt(fem.tsai_hill(sx, sy, sxy, M.ef(M.ispc).astype(bool)).max())
        ux, uy = u[M.bi.nodal_dofs[0]], u[M.bi.nodal_dofs[1]]
        res[f'd{name}'] = np.sqrt(ux**2 + uy**2).max()
        res[f'BK_{name}'] = fem.buckling(K, M.K_geo(sx, sy, sxy), D)
    res['time'] = time.time() - t0
    return res, g

if __name__ == '__main__':
    ma = float(sys.argv[1]) if len(sys.argv) > 1 else 0.15
    names = sys.argv[2:] or list(VARIANTS)
    for nm in names:
        r, g = run(VARIANTS[nm], max_area=ma)
        r = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}
        json.dump(r, open(f'results/t24_{nm}_result.json', 'w'), indent=1)
        json.dump(VARIANTS[nm], open(f'results/t24_{nm}_params.json', 'w'), ensure_ascii=False)
        print(nm, f"カーボン {r['m_carbon']:.2f}g、前 {r['dA']:.2f}mm、後ろ {r['dA_rear']:.2f}mm、角 {r['dB']:.2f}mm、{r['f1']:.0f}Hz、"
              f"座屈 正面 {r['BK_D'] * an.LOADS['D_front']:.0f} / 角 {r['BK_E'] * an.LOADS['E_corner']:.0f} / 横 {r['BK_F'] * an.LOADS['F_side']:.0f}N、安全率 "
              + ' '.join(f"{k[3:]}{r[k]:.1f}" for k in r if k.startswith('SF_')) + f"、{r['time']:.0f}s", flush=True)

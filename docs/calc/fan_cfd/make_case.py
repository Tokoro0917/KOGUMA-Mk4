"""吸引ファンの 3 つの形を、流体の計算(OpenFOAM v1912、simpleFoam + MRF)で比べるための計算の用意(2026-11-24、ユーザー
「xfa273 さんのファンと今のと、組み合わせた形の 3 つを流体で比べて」)。
使い方(リポジトリの一番上から): python3 docs/calc/fan_cfd/make_case.py <A|B|C|D> <計算のフォルダ> [coarse] [名前=値 ...]
  → 計算のフォルダに OpenFOAM の計算一式(形の STL と設定)を作る。走らせるのは run_case.sh
  parts を付けると、まわりの部品を入れる(2026-11-25、ユーザー「逆流してくる空気があると思う」→ D の横へ吹き出す空気が部品に当たる影響を見る):
    mechanical/order_t24/ の STEP(機体の座標)から、フレームの上と基板の下の間にある部品を取り、ファンの中心(14.2, 0)が原点になるようにずらす。
    入れるもの: モーターマウント・モーター・タイヤ・ホイール・71T・壁センサのホルダ・ねじ・エンコーダ基板・ファンの台(輪を除いた腕・ハブ・継ぎ目)。
    ファンの台の輪は、C では計算の輪(ring)と同じ所なので除き、D ではもともとない
  「名前=値」で羽根の形を変えられる(2026-11-25、ユーザー「C 案は採用。羽の形も検証したい」):
    tip=16     羽の先の半径 [mm](C 案を今の輪(外 半径 17.5)に収めるときは 15 = φ30)
    gap=1.0    C の回る壁と止まった輪のすき間 [mm](φ30 のときは 0.9 で、輪が今と同じ半径 16.5〜17.5 になる)
    blades=5   羽の枚数
    sweep=60   羽の曲がり [°](内の端から外の端まで、回る向きと逆へ回る角度。0 はまっすぐ)
    height=3.9 羽の高さ [mm](下の端は z 3.3 のまま。上の板・モーターもその分上がる)
    inner=5    羽の内の端の半径 [mm]

3 つの形(どれも羽根 φ32、曲がった羽 5 枚、羽の高さ z 3.3〜7.2、上の板 z 7.2〜8.0。違いは外の壁と出口だけ):
  A 今の MK4: 羽根に外の壁なし。止まった輪(ファンの台、内径 φ33 = 羽の先とのすき間 0.5mm)の中で回る。
    空気は羽の先と輪のすき間から上へ出て、メイン基板の穴(φ26)の方へ抜ける
  B xfa273 さんの形: 羽根と一体の外の壁(φ32〜φ33.2、z 3.3〜8.0)が一緒に回る。上の板でふさがり、
    空気は外の壁の下の縁とフレームのすき間(0.5mm)から横へ出る。止まった輪はない
  C 組み合わせ: B の羽根の外に、止まった輪(内径 φ35.2 = 回る壁とのすき間 1.0mm)を残す。
    下の縁から出た空気を、回る壁と止まった輪の間を通して上へ導く
  D 壁のない普通のファン(2026-11-25、ユーザー「壁がない普通のファンの場合も同じ条件で」): A から止まった輪を除いた形。
    羽根に外の壁もなく、空気は羽の先からそのまま横へ出る

計算の範囲(ファンの中心が原点、z は床から上。STL は m で書く):
  - 機体の下(スカートで囲った所)は、フレームの穴(φ15)の下の部屋で表す。部屋の下に漏れの穴を 1 つ置き、
    その外を大気(圧力 0)にする。漏れの穴の面積 = スカートの縁の長さ 204mm(68 × 34mm のまわり)× 床とのすき間 0.15mm
    = 30.6mm²(半径 3.12mm)。とがった穴の流量係数は約 0.6 で、docs/spec.md の漏れの見積もり(流量係数 0.6)と同じ扱い
  - フレームの上面 z 2.8、メイン基板 z 13.6〜14.2(ファンの上に穴 φ26)、モーターとハブ(φ10.7、z 8.6 から上)は止まっている壁
  - 横(x, y = ±30mm)と上(z 20mm)は大気(圧力 0)。フレームと基板の間の空気は横へ抜ける
  - ファンの台の腕(4 本)は入れていない(3 つとも同じなので比べには効かない)
羽根は MRF(羽根のまわりの範囲だけを回る座標で解く、定常)で回す。35,000rpm、+z まわり(上から見て反時計回り)。羽は後ろ向きに曲げる"""
import math
import os
import sys
import cadquery as cq
from shapely.geometry import LineString

CASE = sys.argv[1]
OUT = sys.argv[2]
COARSE = 'coarse' in sys.argv[3:]
PARTS = 'parts' in sys.argv[3:]      # まわりの部品(マウント・タイヤ・ホルダなど)を入れる(2026-11-25)
# 羽根の形の指定(書かなければ、3 つの形を比べたときの値)
SHAPE = {'tip': 16.0, 'gap': 1.0, 'blades': 5, 'sweep': 60.0, 'height': 3.9, 'inner': 5.0}
for arg in sys.argv[3:]:
    if '=' in arg:
        name, value = arg.split('=')
        if name not in SHAPE:
            raise SystemExit(f'{name} という指定はない({list(SHAPE)} のどれか)')
        SHAPE[name] = float(value)
N_BLADES = int(SHAPE['blades'])
RPM = 35000.0
OMEGA = RPM * 2 * math.pi / 60

# 寸法 [mm]
R_TIP = SHAPE['tip']  # 羽の先(φ32)
Z_FRAME = 2.8         # フレームの上面
Z_BLADE0 = 3.3        # 羽の下の端(フレームとのすき間 0.5mm)
Z_DISC0 = Z_BLADE0 + SHAPE['height']   # 上の板の下の面(羽の高さ 3.9 なら 7.2)
Z_DISC1 = Z_DISC0 + 0.8               # 上の板の上の面(ファンの台の「羽根の上面 z 8.0」)
R_HOLE = 7.5          # フレームの吸い込みの穴(φ15)
R_LEAK = math.sqrt(204.0 * 0.15 / math.pi)    # 漏れの穴(半径 3.12mm)
RIM_T = 0.6           # B・C の回る外の壁の厚さ
BLADE_T = 0.6         # 羽の厚さ
R_BLADE0 = SHAPE['inner']   # 羽の内の端
SWEEP_DEG = SHAPE['sweep']  # 羽の曲がり(内の端から外の端まで回る角度)
R_MOTOR = 5.35        # モーターのハブ(φ10.7)
Z_MOTOR0 = Z_DISC1 + 0.6    # 上の板の上 0.6mm から(羽の高さ 3.9 なら 8.6)
HALF = 30.0           # 計算の範囲 x, y = ±30
Z_TOP = 20.0
Z_BOTTOM = -6.0       # 部屋の下(この面が大気からの入口)

if CASE == 'A':
    RIM = False
    RING = (R_TIP + 0.5, R_TIP + 1.5)          # 止まった輪(ファンの台)
    R_ZONE = R_TIP + 0.25                       # 回る範囲の半径(すき間の真ん中)
elif CASE == 'B':
    RIM = True
    RING = None
    R_ZONE = R_TIP + RIM_T + 0.5
elif CASE == 'C':
    RIM = True
    RING = (R_TIP + RIM_T + SHAPE['gap'], R_TIP + RIM_T + SHAPE['gap'] + 1.0)
    R_ZONE = R_TIP + RIM_T + SHAPE['gap'] / 2           # 回る範囲の半径(すき間の真ん中)
elif CASE == 'D':
    RIM = False
    RING = None
    R_ZONE = R_TIP + 0.5                        # 回る範囲の半径(羽の先から 0.5mm 外まで)
else:
    raise SystemExit('A・B・C・D のどれか')
Z_ZONE0 = Z_FRAME + 0.25
Z_ZONE1 = Z_DISC1 + 0.3
Z_RING1 = 10.0        # 止まった輪の上の端
if Z_DISC1 + 2.0 > Z_RING1:
    Z_RING1 = Z_DISC1 + 2.0   # 羽を高くしたときは、輪も上の板より 2mm 上まで


def cyl(r, z0, z1):
    """z0〜z1 の円柱(真ん中が原点)"""
    return cq.Workplane('XY').workplane(offset=z0).circle(r).extrude(z1 - z0)


def ring_solid(r0, r1, z0, z1):
    return cyl(r1, z0, z1).cut(cyl(r0, z0 - 1, z1 + 1))


def blade(k):
    """k 番目の羽(上から見た形を shapely で作り、z 方向に伸ばす)。中心線は内の端から羽の先までで、外ほど回る向きと逆へ曲がる"""
    pts = []
    n = 40
    for i in range(n + 1):
        r = R_BLADE0 + (R_TIP + 0.3 - R_BLADE0) * i / n
        th = math.radians(360.0 / N_BLADES * k) - math.radians(SWEEP_DEG) * math.log(r / R_BLADE0) / math.log(R_TIP / R_BLADE0)
        pts.append((r * math.cos(th), r * math.sin(th)))
    poly = LineString(pts).buffer(BLADE_T / 2, cap_style=2)
    wp = cq.Workplane('XY').workplane(offset=Z_BLADE0).polyline(list(poly.exterior.coords)[:-1]).close()
    return wp.extrude(Z_DISC0 + 0.1 - Z_BLADE0)


def impeller():
    """回る羽根(羽 5 枚 + 上の板 + 軸のボス。B・C は外の壁も)"""
    r_disc = R_TIP
    if RIM:
        r_disc = R_TIP + RIM_T
    body = cyl(r_disc, Z_DISC0, Z_DISC1).union(cyl(2.0, Z_BLADE0, Z_DISC0 + 0.1))
    for k in range(N_BLADES):
        body = body.union(blade(k))
    if RIM:
        body = body.union(ring_solid(R_TIP, R_TIP + RIM_T, Z_BLADE0, Z_DISC1))
    else:
        body = body.intersect(cyl(R_TIP, Z_BLADE0 - 1, Z_DISC1 + 1))      # 羽の先を φ32 で切りそろえる
    return body


def base():
    """フレームから下: 部屋(フレームの穴の下)と漏れの穴と入口の部屋を除いた、詰まった塊"""
    b = cq.Workplane('XY').box(2 * HALF + 2, 2 * HALF + 2, Z_FRAME - (Z_BOTTOM - 1), centered=(True, True, False)).translate((0, 0, Z_BOTTOM - 1))
    b = b.cut(cyl(R_HOLE, -4.0, Z_FRAME + 1))          # 部屋とフレームの穴
    b = b.cut(cyl(R_LEAK, -4.6, -3.9))                   # 漏れの穴(厚さ 0.5mm の板の穴)
    b = b.cut(cyl(R_HOLE, Z_BOTTOM - 2, -4.5))           # 入口の部屋(大気)
    return b


def pcb():
    p = cq.Workplane('XY').box(2 * HALF + 2, 2 * HALF + 2, 0.6, centered=(True, True, False)).translate((0, 0, 13.6))
    return p.cut(cyl(13.0, 13, 15))


def motor():
    return cyl(R_MOTOR, Z_MOTOR0, Z_TOP + 2)


FAN_X = 14.2          # 機体の座標でのファンの中心(mechanical/vehicle/pcb_shape.py の FAN)
PARTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../mechanical/order_t24')


def parts():
    """まわりの部品を1つの塊にする(機体の座標の STEP を読み、ファンの中心が原点になるようにずらして、計算の範囲で切り取る)"""
    files = ['02_motor_mount_R_t24v12', '03_motor_mount_L_t24v12', '05_wheel_t24v7', '06_sensor_holder_v6',
             '08_encoder_board_R_t24', '09_purchased_and_other_parts']
    solids = []
    for f in files:
        for v in cq.importers.importStep(os.path.join(PARTS_DIR, f + '.step')).solids().vals():
            bb = v.BoundingBox()
            # 09 の中の、羽根・ファンのモーター・軸(ファンの軸の上にある物)は計算の側で持っているので除く
            if abs((bb.xmin + bb.xmax) / 2 - FAN_X) < 1.0 and abs((bb.ymin + bb.ymax) / 2) < 1.0:
                continue
            solids.append(v)
    # ファンの台: 輪(半径 16.3〜17.7、腕の上の端 z 10.8 まで)を除いて、腕・ハブ・継ぎ目だけ残す
    mount = cq.importers.importStep(os.path.join(PARTS_DIR, '04_fan_mount_t24v4.step'))
    ring_cut = cq.Workplane('XY').workplane(offset=0).center(FAN_X, 0).circle(17.7).circle(16.3).extrude(10.9)
    mount = mount.cut(ring_cut)
    solids = solids + mount.solids().vals()
    # 計算の範囲(横 ±HALF、フレームの上の面の少し下 〜 基板の下の面の少し上)で切り取る。少し重ねて、すき間の細い所を作らない
    clip = cq.Workplane('XY').box(2 * HALF - 0.2, 2 * HALF - 0.2, 13.75 - 2.7, centered=(True, True, False)).translate((FAN_X, 0, 2.7)).val()
    pieces = []
    for v in solids:
        for piece in v.intersect(clip).Solids():
            pieces.append(piece)
    # 重なった部品を1つにまとめる(1つずつ union すると部品が消えることがあったので、まとめて fuse する)
    body = pieces[0].fuse(*pieces[1:]).clean().fix()
    body = cq.Workplane('XY').add(body)
    return body.translate((-FAN_X, 0, 0))


def write_stl(wp, name, tolerance_mm=0.002):
    """STL に書き出す(tolerance_mm は面を三角に分ける細かさ。まわりの部品は 0.02mm で粗くして、ファイルを小さくする)"""
    shape = wp.val().scale(0.001)
    os.makedirs(os.path.join(OUT, 'constant/triSurface'), exist_ok=True)
    cq.exporters.export(cq.Workplane().add(shape), os.path.join(OUT, 'constant/triSurface', name + '.stl'), tolerance=tolerance_mm * 0.001, angularTolerance=0.1)


def write(path, text):
    full = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w') as f:
        f.write(text)


HEADER = 'FoamFile {{ version 2.0; format ascii; class {cls}; object {obj}; }}\n'


def m(v):
    """mm → m の文字列"""
    return f'{v / 1000:.6g}'


def dicts():
    lv_fine = 3
    lv_mid = 2
    if COARSE:
        lv_fine = 2
        lv_mid = 1
    surfaces = ['impeller', 'base', 'pcb', 'motor']
    if RING:
        surfaces.append('ring')
    if PARTS:
        surfaces.append('parts')
    write('system/blockMeshDict', HEADER.format(cls='dictionary', obj='blockMeshDict') + f'''
convertToMeters 0.001;
vertices ( (-{HALF} -{HALF} {Z_BOTTOM}) ({HALF} -{HALF} {Z_BOTTOM}) ({HALF} {HALF} {Z_BOTTOM}) (-{HALF} {HALF} {Z_BOTTOM})
           (-{HALF} -{HALF} {Z_TOP}) ({HALF} -{HALF} {Z_TOP}) ({HALF} {HALF} {Z_TOP}) (-{HALF} {HALF} {Z_TOP}) );
blocks ( hex (0 1 2 3 4 5 6 7) (60 60 26) simpleGrading (1 1 1) );
boundary (
  inlet {{ type patch; faces ((0 3 2 1)); }}
  outlet {{ type patch; faces ((4 5 6 7) (0 1 5 4) (1 2 6 5) (2 3 7 6) (3 0 4 7)); }}
);
''')
    geo = ''.join(f'  {s}.stl {{ type triSurfaceMesh; name {s}; }}\n' for s in surfaces)
    levels = {'impeller': lv_fine, 'ring': lv_fine, 'base': lv_mid, 'motor': lv_mid, 'pcb': 1, 'parts': lv_mid}
    ref = ''.join(f'    {s} {{ level ({levels[s]} {levels[s]}); patchInfo {{ type wall; }} }}\n' for s in surfaces)
    feats = ''.join(f'    {{ file "{s}.eMesh"; level {levels[s]}; }}\n' for s in surfaces)
    write('system/snappyHexMeshDict', HEADER.format(cls='dictionary', obj='snappyHexMeshDict') + f'''
castellatedMesh true; snap true; addLayers false;
geometry {{
{geo}  refineZone {{ type searchableCylinder; point1 (0 0 {m(Z_FRAME - 0.5)}); point2 (0 0 {m(Z_DISC1 + 1.0)}); radius {m(R_ZONE + 2.5)}; }}
}}
castellatedMeshControls {{
  maxLocalCells 3000000; maxGlobalCells 10000000; minRefinementCells 10; maxLoadUnbalance 0.10; nCellsBetweenLevels 3;
  features (
{feats}  );
  refinementSurfaces {{
{ref}  }}
  resolveFeatureAngle 30;
  refinementRegions {{ refineZone {{ mode inside; levels ((1e15 {lv_mid})); }} }}
  locationInMesh (0.0101 0.0013 0.01213);
  allowFreeStandingZoneFaces true;
}}
snapControls {{ nSmoothPatch 3; tolerance 2.0; nSolveIter 50; nRelaxIter 5; nFeatureSnapIter 10; implicitFeatureSnap false; explicitFeatureSnap true; multiRegionFeatureSnap false; }}
addLayersControls {{ relativeSizes true; layers {{ }} expansionRatio 1.0; finalLayerThickness 0.3; minThickness 0.1; nGrow 0; featureAngle 60;
  nRelaxIter 3; nSmoothSurfaceNormals 1; nSmoothNormals 3; nSmoothThickness 10; maxFaceThicknessRatio 0.5; maxThicknessToMedialRatio 0.3;
  minMedianAxisAngle 90; nBufferCellsNoExtrude 0; nLayerIter 50; }}
meshQualityControls {{ maxNonOrtho 65; maxBoundarySkewness 20; maxInternalSkewness 4; maxConcave 80; minVol 1e-20; minTetQuality 1e-15;
  minArea -1; minTwist 0.02; minDeterminant 0.001; minFaceWeight 0.05; minVolRatio 0.01; minTriangleTwist -1; nSmoothScale 4; errorReduction 0.75;
  relaxed {{ maxNonOrtho 75; }} }}
mergeTolerance 1e-6;
''')
    feat_entries = ''.join(f'{s}.stl {{ extractionMethod extractFromSurface; extractFromSurfaceCoeffs {{ includedAngle 150; }} writeObj no; }}\n' for s in surfaces)
    write('system/surfaceFeatureExtractDict', HEADER.format(cls='dictionary', obj='surfaceFeatureExtractDict') + feat_entries)
    write('system/topoSetDict', HEADER.format(cls='dictionary', obj='topoSetDict') + f'''
actions (
  {{ name rotorCells; type cellSet; action new; source cylinderToCell; sourceInfo {{ p1 (0 0 {m(Z_ZONE0)}); p2 (0 0 {m(Z_ZONE1)}); radius {m(R_ZONE)}; }} }}
  {{ name rotor; type cellZoneSet; action new; source setToCellZone; sourceInfo {{ set rotorCells; }} }}
  {{ name chamberCells; type cellSet; action new; source cylinderToCell; sourceInfo {{ p1 (0 0 {m(-3.5)}); p2 (0 0 {m(1.5)}); radius {m(R_HOLE)}; }} }}
  {{ name chamber; type cellZoneSet; action new; source setToCellZone; sourceInfo {{ set chamberCells; }} }}
);
''')
    write('system/decomposeParDict', HEADER.format(cls='dictionary', obj='decomposeParDict') + 'numberOfSubdomains 4; method simple; coeffs { n (2 2 1); }\n')
    write('system/controlDict', HEADER.format(cls='dictionary', obj='controlDict') + f'''
application simpleFoam; startFrom latestTime; startTime 0; stopAt endTime; endTime 1500; deltaT 1;
writeControl timeStep; writeInterval 500; purgeWrite 2; writeFormat ascii; writePrecision 8; timeFormat general; runTimeModifiable true;
''')
    write('system/fvSchemes', HEADER.format(cls='dictionary', obj='fvSchemes') + '''
ddtSchemes { default steadyState; }
gradSchemes { default Gauss linear; grad(U) cellLimited Gauss linear 1; }
divSchemes { default none; div(phi,U) bounded Gauss linearUpwind grad(U); div(phi,k) bounded Gauss upwind; div(phi,omega) bounded Gauss upwind;
  div((nuEff*dev2(T(grad(U))))) Gauss linear; }
laplacianSchemes { default Gauss linear limited corrected 0.5; }
interpolationSchemes { default linear; }
snGradSchemes { default limited corrected 0.5; }
wallDist { method meshWave; }
''')
    write('system/fvSolution', HEADER.format(cls='dictionary', obj='fvSolution') + '''
solvers {
  p { solver GAMG; smoother GaussSeidel; tolerance 1e-7; relTol 0.05; }
  "(U|k|omega)" { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-8; relTol 0.1; }
}
SIMPLE { nNonOrthogonalCorrectors 1; consistent no; residualControl { p 1e-5; U 1e-6; "(k|omega)" 1e-6; } }
relaxationFactors { fields { p 0.2; } equations { U 0.5; k 0.5; omega 0.5; } }
''')
    write('constant/transportProperties', HEADER.format(cls='dictionary', obj='transportProperties') + 'transportModel Newtonian; nu 1.5e-05;\n')
    write('constant/turbulenceProperties', HEADER.format(cls='dictionary', obj='turbulenceProperties') +
          'simulationType RAS; RAS { RASModel kOmegaSST; turbulence on; printCoeffs on; }\n')
    write('constant/MRFProperties', HEADER.format(cls='dictionary', obj='MRFProperties') +
          f'MRF1 {{ cellZone rotor; active yes; nonRotatingPatches (); origin (0 0 0); axis (0 0 1); omega {OMEGA:.4f}; }}\n')
    walls = ' '.join(s for s in surfaces if s != 'impeller')
    wall_re = '"(' + '|'.join(s for s in surfaces if s != 'impeller') + ')"'
    write('0.orig/U', HEADER.format(cls='volVectorField', obj='U') + f'''dimensions [0 1 -1 0 0 0 0]; internalField uniform (0 0 0);
boundaryField {{
  "(inlet|outlet)" {{ type pressureInletOutletVelocity; value uniform (0 0 0); }}
  impeller {{ type fixedValue; value uniform (0 0 0); }}
  {wall_re} {{ type noSlip; }}
}}
''')
    write('0.orig/p', HEADER.format(cls='volScalarField', obj='p') + f'''dimensions [0 2 -2 0 0 0 0]; internalField uniform 0;
boundaryField {{
  ".*" {{ type zeroGradient; }}
  "(inlet|outlet)" {{ type totalPressure; p0 uniform 0; value uniform 0; }}
}}
''')
    for name, dim, val, wf in (('k', '[0 2 -2 0 0 0 0]', 1.0, 'kqRWallFunction'), ('omega', '[0 0 -1 0 0 0 0]', 1000.0, 'omegaWallFunction')):
        write(f'0.orig/{name}', HEADER.format(cls='volScalarField', obj=name) + f'''dimensions {dim}; internalField uniform {val};
boundaryField {{
  ".*" {{ type {wf}; value uniform {val}; }}
  "(inlet|outlet)" {{ type inletOutlet; inletValue uniform {val}; value uniform {val}; }}
}}
''')
    write('0.orig/nut', HEADER.format(cls='volScalarField', obj='nut') + '''dimensions [0 2 -1 0 0 0 0]; internalField uniform 0;
boundaryField {
  ".*" { type nutkWallFunction; value uniform 0; }
  "(inlet|outlet)" { type calculated; value uniform 0; }
}
''')
    return walls


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    write_stl(impeller(), 'impeller')
    write_stl(base(), 'base')
    write_stl(pcb(), 'pcb')
    write_stl(motor(), 'motor')
    if RING:
        write_stl(ring_solid(RING[0], RING[1], Z_FRAME - 0.1, Z_RING1), 'ring')
    if PARTS:
        write_stl(parts(), 'parts', 0.02)
    dicts()
    print(f'形 {CASE}: {OUT}(回る範囲 r ≤ {R_ZONE:.2f}mm、z {Z_ZONE0:.2f}〜{Z_ZONE1:.2f}mm、漏れの穴 半径 {R_LEAK:.2f}mm、{RPM:.0f}rpm = {OMEGA:.1f} rad/s)')

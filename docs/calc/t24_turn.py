"""タイヤ24mm の機体(t24、59.4g)のターンの速さを上げるには(2026-11-21、ブランチ claude/trusting-dirac-1tdt54)。
使い方(リポジトリの一番上で): python3 docs/calc/t24_turn.py

ターンの速さは次の2つの小さい方で決まる:
  1. グリップ: 横の加速度 ≤ μ g (m + 吸引) / m。V90(G_Turn2000 を速度で換算した形)は、角速度が一番大きい所の半径が
     速さによらず 2 m/s / 2000 deg/s = 57.3mm なので、横の加速度 = v² / 0.0573
  2. 入りの電流: 外側のモーターの電流 = 有効慣性モーメント × 角加速度 / トレッド × 半径 / (Kt × ギア比)。角加速度は速さの2乗に比例
     (drive_calc.py の v90_peak_current。G_Turn2000 の 130,000 deg/s² を (v/2)² 倍)。入りをゆるくする(角加速度を下げる)と電流は比例して減る
吸引の力に要るファンの電力は、docs/spec.md の「吸引400gに必要な圧力と電力」と同じ式(流量係数0.6、ファンの効率30%)で、吸引する面 68 × 34mm(縁 204mm)
"""
import math, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t24_performance as tp    # 機体の値と式(引数なしで動かす)

V = 11.1
p = tp.model('t24(24mm、71T:13T)', V)
m = p['m']
AREA, PERIM = 0.068 * 0.034, 2 * (0.068 + 0.034)
R_V90 = 2.0 / (2000 * math.pi / 180)
I22 = tp.v90_current(p, 2.2)          # 2.2 m/s の入りの外側の電流

def a_lat(S):
    return tp.MU * tp.d.G_ACC * (m + S / 1000) / m

def fan(S, gap):
    dp = S / 1000 * tp.d.G_ACC / AREA
    q = 0.6 * PERIM * gap * math.sqrt(2 * dp / 1.2)
    w = q * dp / 0.3
    return dp, w, w / V

def v_grip(S, R):
    return math.sqrt(a_lat(S) * R)

def v_current(I, soft=1.0):
    """外側の電流が I になる V90 の入りの速さ。soft は角加速度の倍率(0.7 なら入りを3割ゆるく)"""
    return 2.2 * math.sqrt(I / (I22 * soft))

out = []
P = out.append
P(f'機体 {m * 1000:.1f}g、有効慣性モーメント {p["Iz_eff"] * 1e7:.0f} g·cm²(機体 {p["Iz"] * 1e7:.0f}、車輪 {2 * p["Jw"] * (p["T"] / 2 / p["r"]) ** 2 * 1e7:.0f}、'
  f'ロータ {2 * tp.J_ROT * p["G"] ** 2 * (p["T"] / 2 / p["r"]) ** 2 * 1e7:.0f})、μ {tp.MU:.2f}、V90 の角速度が一番大きい所の半径 {R_V90 * 1000:.1f}mm')
P('')
P('■ 1. 吸引の力とグリップ(吸引する面 68 × 34mm)')
P('  吸引  負圧    ファン(すき間0.1 / 0.2mm)        横の上限   V90(グリップ)  半径45 / 90mm のターン')
for S in (400, 500, 600, 700, 800):
    dp, w1, i1 = fan(S, 1e-4); _, w2, i2 = fan(S, 2e-4)
    P(f'  {S:4d}g {dp / 1000:4.1f}kPa  {w1:4.1f}W {i1:4.2f}A / {w2:4.1f}W {i2:4.2f}A   {a_lat(S):5.0f} m/s²  {v_grip(S, R_V90):4.2f} m/s      '
      f'{v_grip(S, 0.045):4.2f} / {v_grip(S, 0.09):4.2f} m/s')
P('')
P(f'■ 2. 入りの電流(外側のモーター。2.2 m/s で {I22:.1f}A、速さの2乗に比例)')
P('  外側の電流の上限   G_Turn2000 の形   入りを2割ゆるく   入りを3割ゆるく')
for I in (3.5, 4.0, 5.0):
    P(f'  {I:.1f}A{"(MP6551 の上限)" if I == 5.0 else "             "}   {v_current(I):4.2f} m/s         {v_current(I, 0.8):4.2f} m/s        {v_current(I, 0.7):4.2f} m/s')
P('  (ターンの入りで電流が大きいのは外側だけ。内側は減速するので、電池から出る電流は 外側 + ファン。電池の上限 8.1A)')
P('')
P('■ 3. 組み合わせ(V90 の速さ = グリップと電流の小さい方)')
for S in (400, 500, 600, 700):
    row = []
    for I, soft in ((3.5, 1.0), (5.0, 1.0), (5.0, 0.7)):
        v = min(v_grip(S, R_V90), v_current(I, soft))
        _, _, fi = fan(S, 1.5e-4)
        row.append(f'{v:4.2f}({"グリップ" if v_grip(S, R_V90) < v_current(I, soft) else "電流"}、電池 {I + fi:3.1f}A)')
    P(f'  吸引 {S}g: 3.5A {row[0]}  5A {row[1]}  5A・入り3割ゆるく {row[2]}')
print('\n'.join(out))

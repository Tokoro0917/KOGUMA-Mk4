"""MK3のタイヤ(23.1mm)にしたときのギアの比べ(2026-11-21)
今の機体(56g、265 g·cm²、トレッド60mm、3S 11.1V)のまま、タイヤだけ23.1mmにして、スパーとピニオン(m0.3)の組み合わせを比べる。
床とのすき間はスパーの歯先とタイヤの半径から出す(タイヤが潰れない、床が平らとして)。
使い方(リポジトリの一番上で): python3 docs/calc/tire23_study.py [--tire 23.1] [--mass 0.060]"""
import sys, math, argparse; sys.path.insert(0, 'docs/calc')
import drive_calc as d

ap = argparse.ArgumentParser()
ap.add_argument('--tire', type=float, default=23.1, help='タイヤ径[mm]')
ap.add_argument('--mass', type=float, default=0.056, help='質量[kg]')
ap.add_argument('--iz', type=float, default=265, help='慣性モーメント[g·cm²]')
a = ap.parse_args()
tire = a.tire / 1000; m = a.mass; Iz = a.iz * 1e-7; T = 0.0601; V = 11.1
MOD = 0.3
# (スパー, ピニオン)。41:13 は今、71:20 は MK3
COMBOS = [(41, 13), (71, 20), (50, 13), (60, 13), (60, 15), (66, 14), (68, 13), (71, 15)]

mu = 91.5 * 0.078 / ((0.078 + 0.4) * d.G_ACC)   # gear_study.py と同じ


def run(G, I, suction, L, v0=3.0):
    """直線 L[m] を v0 で入って v0 で出る時間(gear_study.py の run と同じ)"""
    p = d.mk4(G, m=m, T=T, V=V, tire=tire)
    grip = d.grip_limit(m, suction, mu)
    acc = lambda v: min(d.accel_voltage_limit(p, v), d.accel_current_limit(p, I), grip)
    dec = lambda v: min(d.accel_current_limit(p, I), grip)
    dt = 1e-4; x = 0; v = v0; t = 0
    while True:
        sd = (v * v - v0 * v0) / (2 * dec(v))
        if x + sd >= L: break
        acv = acc(v)
        if acv <= 1e-6: break
        v += acv * dt; x += v * dt; t += dt
        if v > 40: break
    t += (v - v0) / dec(v) + max(0, L - x - (v * v - v0 * v0) / (2 * dec(v))) / v
    return t, v


print(f'タイヤ {a.tire}mm、{m*1000:.0f}g、{a.iz:.0f} g·cm²、3S {V}V、m{MOD}')
print('スパー:ピニオン ギア比 軸間  歯先  床まで  3Aの加速  無負荷最高速  14m/sの回転数  V90 3000外側A  15区画(3A・吸引400g)')
for Z, z in COMBOS:
    G = Z / z
    p = d.mk4(G, m=m, T=T, V=V, tire=tire)
    tip = MOD * (Z + 2)
    floor = (a.tire - tip) / 2
    vmax = p['V'] / p['Ke'] * p['r'] / G
    rpm14 = 14 / p['r'] * G * 60 / (2 * math.pi)
    t, _ = run(G, 3.0, 400, 15 * 0.18)
    print(f'  {Z:3d}T:{z:2d}T     {G:4.2f}  {MOD*(Z+z)/2:5.2f} {tip:5.1f}  {floor:5.2f}   {d.accel_current_limit(p,3):5.0f}      {vmax:5.1f}        {rpm14/1000:5.1f}k        {d.v90_peak_current(p,Iz,3.0):4.1f}         {t*1000:4.0f}ms')

"""最短走行の初手のターン(スタートの区画を出てすぐのターン)をどのくらいの速さで回れるか(2026-11-25、ユーザー
「最短時の初手ターンはどのくらい出せそう」)。
使い方(リポジトリの一番上で): python3 docs/calc/t24_first_turn.py

1. 走り出し: 止まった所から、片側 5A(電池の見張りつき)とグリップの小さい方で加速する(t24_performance.py の acc_guard)。
   機体の後ろをスタートの壁に付けると、車軸は壁から 50mm(フレームの前後の端 ±50mm)。
   区画の内のり 168mm なので、区画の真ん中まで 34mm、区画の出口(次の区画との境)まで 124mm 走れる
2. ターン: 角速度を「1 − cos」の形で上げ、一定で回り、同じ形で下げる(V90 の G_Turn2000 と同じ形)。
   上げ下げで回る角度は、G_Turn2000 と同じ 24.2°(= π W² / (4 A)、W 2000 deg/s・A 130,000 deg/s²)とする。
   入りと出の位置は決まっている(大回り 90° は区画の出口から入って出口へ: 前へ 90mm・横へ 90mm、
   大回り 180° は横へ 180mm)ので、この形で回ると一番小さい半径は 90mm より小さくなる。その半径で
     グリップで決まる速さ v = √(横の加速度の上限 × 一番小さい半径)
     入りの外側のモーターの電流 = 有効慣性モーメント × 角加速度 / トレッド × タイヤの半径 / (Kt × ギア比)
       角加速度の最大 A = π W² / (4 × 上げ下げの角度)、W = v / 一番小さい半径
   V90 は docs/spec.md と同じ(一番小さい半径 57.3mm、入りを 3 割ゆるく = 角加速度 0.7 倍)
機体は今の 60.71g・298 g·cm²(mechanical/vehicle/vehicle_t24_mass.json)。μ 1.52(MK3 のタイヤの下限)"""
import math
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t24_performance as tp

# 今の機体(2026-11-24 の vehicle_t24_mass.json)。ほかは t24_performance.py の t24 と同じ
tp.M['t24 今'] = dict(m=0.06071, Iz=298.3e-7, r=0.012, G=71 / 13, T=0.0581, Jw=282e-9)
P = tp.model('t24 今', 11.1)

RUNUP_CENTER_M = 0.034     # スタートの位置から区画の真ん中まで
RUNUP_EXIT_M = 0.124       # スタートの位置から区画の出口まで
RAMP_DEG = math.pi * 2000 ** 2 / (4 * 130000)   # 上げ下げで回る角度 [°](W [deg/s]、A [deg/s²] で計算するので、そのまま度。24.2°)
CURRENT_MAX_A = 5.0        # 片側の電流の上限(MP6551)


def speed_after(distance_m, suction_g):
    """止まった所から distance_m 走ったときの速さ(加速の上限いっぱいで)"""
    dt = 1e-5
    x = 0.0
    v = 0.0
    while x < distance_m:
        v = v + tp.acc_guard(P, v, suction_g) * dt
        x = x + v * dt
    return v


def runup_needed(v_target, suction_g):
    """止まった所から v_target まで加速するのに要る距離"""
    dt = 1e-5
    x = 0.0
    v = 0.0
    while v < v_target:
        v = v + tp.acc_guard(P, v, suction_g) * dt
        x = x + v * dt
    return x


def turn_shape(total_deg):
    """一番小さい半径を 1 としたときの、ターンの入りから出までの動き(前へ, 横へ)。
    速さ 1 で、角速度を 1 − cos の形で 0 → 1 に上げ、1 で回り、同じ形で 0 に下げる"""
    ramp = math.radians(RAMP_DEG)
    hold = math.radians(total_deg) - 2 * ramp
    t_ramp = 2 * ramp                  # 1 − cos の形で 0 → 1 に上げると、回る角度は t_ramp / 2
    t_total = 2 * t_ramp + hold
    n = 200000
    dt = t_total / n
    angle = 0.0
    forward = 0.0
    side = 0.0
    for i in range(n):
        t = (i + 0.5) * dt
        if t < t_ramp:
            w = 0.5 * (1 - math.cos(math.pi * t / t_ramp))
        elif t < t_ramp + hold:
            w = 1.0
        else:
            w = 0.5 * (1 - math.cos(math.pi * (t_total - t) / t_ramp))
        forward = forward + math.cos(angle) * dt
        side = side + math.sin(angle) * dt
        angle = angle + w * dt
    return forward, side


def turn_current(v, r_min, soft=1.0):
    """入りの外側のモーターの電流のピーク [A]。soft は角加速度の倍率"""
    w = v / r_min
    a = math.pi * w * w / (4 * math.radians(RAMP_DEG)) * soft
    dc = P['dc']
    return P['Iz_eff'] * a / dc['T'] * dc['r'] / (dc['n'] * dc['Kt'] * dc['G'])


def turn_limit(r_min, suction_g, soft=1.0):
    """グリップと電流(5A)の小さい方で決まる速さと、そのときの電流"""
    v_grip = math.sqrt(tp.grip(P, suction_g) * r_min)
    v_current = v_grip * math.sqrt(CURRENT_MAX_A / turn_current(v_grip, r_min, soft))
    v = min(v_grip, v_current)
    limit = 'グリップ'
    if v_current < v_grip:
        limit = '電流 5A'
    return v, turn_current(v, r_min, soft), limit


if __name__ == '__main__':
    f90, s90 = turn_shape(90)
    r_big90 = 0.090 / s90
    f180, s180 = turn_shape(180)
    r_big180 = 0.180 / s180
    print(f'機体 {P["m"] * 1000:.1f}g、有効慣性モーメント {P["Iz_eff"] * 1e7:.0f} g·cm²、上げ下げの角度 {RAMP_DEG:.1f}°')
    print(f'大回り 90°: 一番小さい半径 {r_big90 * 1000:.1f}mm(入りから出まで 前へ {f90 * r_big90 * 1000:.1f}mm・横へ 90mm)')
    print(f'大回り 180°: 一番小さい半径 {r_big180 * 1000:.1f}mm(横へ 180mm)')
    turns = [
        ('大回り 90°(区画の出口から)', r_big90, 1.0, RUNUP_EXIT_M),
        ('大回り 180°(区画の出口から)', r_big180, 1.0, RUNUP_EXIT_M),
        ('V90 の形(入り 3 割ゆるく)', 0.0573, 0.7, RUNUP_EXIT_M),
        ('小回り 半径 45mm(区画の真ん中から)', 0.045, 1.0, RUNUP_CENTER_M),
    ]
    for suction_g, fan in ((600, '最短でファン 8.5V'), (500, 'ファン 7.4V')):
        print()
        print(f'■ 吸引 {suction_g}g({fan})、グリップの限界 {tp.grip(P, suction_g):.0f} m/s²、'
              f'走り出しの加速 {tp.acc_guard(P, 0, suction_g):.0f} m/s²')
        for name, r_min, soft, runup in turns:
            v_turn, current, limit = turn_limit(r_min, suction_g, soft)
            v_runup = speed_after(runup, suction_g)
            need = runup_needed(v_turn, suction_g)
            v = min(v_turn, v_runup)
            by = f'ターンの上限({limit})'
            if v_runup < v_turn:
                by = '助走が足りない'
            print(f'  {name}: 上限 {v_turn:.2f} m/s(入りの電流 {current:.1f}A)、要る助走 {need * 1000:.0f}mm / ある助走 {runup * 1000:.0f}mm'
                  f' → 初手 {v:.2f} m/s({by})')

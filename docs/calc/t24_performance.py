"""タイヤ24mm の機体(t24)の出せる性能の見積もり(2026-11-21、ブランチ claude/trusting-dirac-1tdt54)。main(タイヤ15mm)と比べる。
使い方(リポジトリの一番上で): python3 docs/calc/t24_performance.py [--suction 400] [--volt 11.1]

入れたもの:
  - 機体の質量・慣性モーメント: mechanical/vehicle/t24_mass.py(t24)、vehicle.py v4(main)
  - 回る部品の慣性(車輪 = タイヤ・ホイール・スパー・車軸、モーターのロータ 0.15 g·cm²)を、直線では質量に、旋回では慣性モーメントに足す
      有効質量 = 質量 + 2 × (J_車輪 + J_ロータ × ギア比²) / 半径²
      有効慣性モーメント = 慣性モーメント + 2 × (J_車輪 + J_ロータ × ギア比²) × (トレッド/2 / 半径)²
  - モーター NFP-D8620(7.4V版)を 3S で。電流は片側の上限で切る(ソフトで制限)。電池の電圧降下・摩擦・ドライバの損失は入れない
  - グリップ: μ = 1.52(MK3 が V90 2200 で滑らなかったことからの下限。MK3 と同じタイヤの t24 にはそのまま使える。
    main の 15mm のタイヤでは確かめていない)。吸引の力はすべてタイヤにかかるとする(加速・減速・旋回で同じ限界)
  - 直線: 区画 180mm。3 m/s で入って 3 m/s で出る。減速は電流とグリップで決まる(逆起電力は減速を助けるので電圧では決まらない)
  - 最高速: モーターの回転数を 44,000rpm(軸受とブラシの寿命の目安、docs/spec.md)で切る場合と、切らない場合
  - ターン: 旋回の横の加速度の上限(グリップ)から、半径ごとの速さの上限。V90 の入りの電流は drive_calc.py と同じ形(G_Turn2000 を速度で換算)
"""
import argparse, math, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import drive_calc as d

J_ROT = 15e-9                                   # 0.15 g·cm² → kg·m²
MU = 91.5 * 0.078 / ((0.078 + 0.4) * d.G_ACC)   # 1.52
CELL = 0.18
RPM_CAP = 44000
M = {
    'main(15mm、41T:13T)': dict(m=0.05606, Iz=265e-7, r=0.0075, G=41 / 13, T=0.0601, Jw=26e-9),
    't24(24mm、71T:13T)': dict(m=0.05941, Iz=288e-7, r=0.012, G=71 / 13, T=0.0581, Jw=282e-9),
    # 2026-11-24: 京商 MZT302-30(LM ワイド、外径 27mm・幅 11mm・内径 20mm と表から読んだ値)にしたら。タイヤの重さは
    # ゴムの体積の比で 24mm のタイヤ(1.41g)から 3.4g と見積もり(+2.0g × 2)、ホイールの幅 +2.5mm で +0.25g × 2。
    # 機体は 60.66g(t24、ホイール t24v3)+ 4.5g。トレッドは外へ広げる案(タイヤの真ん中 |y| 30.3)。
    # 車輪の慣性: タイヤ 3.4g の輪(半径 10〜13.5mm)4.8e-7 + ほか 1.1e-7 + ホイール 0.1e-7
    't27(27mm、71T:13T)': dict(m=0.0652, Iz=335e-7, r=0.0135, G=71 / 13, T=0.0606, Jw=600e-9),
    't27(27mm、71T:12T)': dict(m=0.0652, Iz=335e-7, r=0.0135, G=71 / 12, T=0.0606, Jw=600e-9),
    # スパーを大きく・ピニオンを小さく(ユーザー、2026-11-24)。車軸 z 13.5 で、スパーの歯先と床のすき間を 1mm 以上残すには 80T まで(歯先の半径 12.3mm)。
    # スパーは重く(80T の POM、+0.25g × 2)、慣性も増える(+0.6e-7)
    't27(27mm、76T:12T)': dict(m=0.0655, Iz=337e-7, r=0.0135, G=76 / 12, T=0.0606, Jw=640e-9),
    't27(27mm、80T:12T)': dict(m=0.0657, Iz=338e-7, r=0.0135, G=80 / 12, T=0.0606, Jw=670e-9),
    't27(27mm、80T:11T)': dict(m=0.0657, Iz=338e-7, r=0.0135, G=80 / 11, T=0.0606, Jw=670e-9),
}

def model(k, V):
    p = dict(M[k])
    rot = p['Jw'] + J_ROT * p['G'] ** 2
    p['m_eff'] = p['m'] + 2 * rot / p['r'] ** 2
    p['Iz_eff'] = p['Iz'] + 2 * rot * (p['T'] / 2 / p['r']) ** 2
    p['dc'] = d.mk4(p['G'], m=p['m_eff'], T=p['T'], V=V, tire=2 * p['r'])   # drive_calc の式に有効質量を入れる
    return p

def grip(p, S):
    return d.grip_limit(p['m'], S, MU)

def acc(p, v, I, S, cap=True):
    a_ = min(d.accel_voltage_limit(p['dc'], v), d.accel_current_limit(p['dc'], I), grip(p, S))
    if cap and v >= vcap(p):
        return 0.0
    return max(a_, 0.0)

def i_battery_guard(p, v, I_max=5.0, I_bat=7.5, I_fan=0.9):
    """電池の電流を見張って決める片側の電流の上限(2026-11-21)。
    電池から出る電流 = 2 × 電流 × (R × 電流 + Ke × ω) / 電圧 + ファン ≤ I_bat、かつ 電流 ≤ I_max(MP6551 の上限)"""
    dc = p['dc']; w = v / p['r'] * p['G']
    a_, b_, c_ = 2 * dc['R'] / dc['V'], 2 * dc['Ke'] * w / dc['V'], -(I_bat - I_fan)
    i = (-b_ + math.sqrt(b_ * b_ - 4 * a_ * c_)) / (2 * a_)
    return min(I_max, i)

def acc_guard(p, v, S, cap=True):
    return acc(p, v, i_battery_guard(p, v), S, cap)

def straight_guard(p, L, S, v0=3.0, cap=True):
    """直線(電流の上限を電池の見張りで決める)。減速も 5A まで(逆起電力で電池へは戻る向き。回生は別に制限する)"""
    dt = 1e-4; x = 0; v = v0; t = 0
    dmax = dec(p, 5.0, S)
    while True:
        sd = (v * v - v0 * v0) / (2 * dmax)
        if x + sd >= L:
            break
        ac = acc_guard(p, v, S, cap)
        if ac <= 1e-6:
            rest = L - x - sd; t += rest / v; x += rest
            break
        v += ac * dt; x += v * dt; t += dt
    t += (v - v0) / dmax
    return t, v

def dec(p, I, S):
    return min(d.accel_current_limit(p['dc'], I), grip(p, S))

def vcap(p):
    return RPM_CAP / 60 * 2 * math.pi * p['r'] / p['G']

def vmax_free(p):
    return p['dc']['V'] / p['dc']['Ke'] * p['r'] / p['G']

def straight(p, L, I, S, v0=3.0, cap=True):
    dt = 1e-4; x = 0; v = v0; t = 0
    while True:
        sd = (v * v - v0 * v0) / (2 * dec(p, I, S))
        if x + sd >= L:
            break
        ac = acc(p, v, I, S, cap)
        if ac <= 1e-6:     # これ以上速くならない: 一定の速さで進み、減速の所まで
            rest = L - x - sd
            t += rest / v; x += rest
            break
        v += ac * dt; x += v * dt; t += dt
    t += (v - v0) / dec(p, I, S)
    return t, v

def v90_current(p, v):
    return d.v90_peak_current(p['dc'], p['Iz_eff'], v)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--suction', type=float, nargs='*', default=[400.0, 510.0], help='吸引の力 [g](t24 で同じ負圧なら約510g)')
    ap.add_argument('--volt', type=float, default=11.1)
    a = ap.parse_args()

    out = []
    P = lambda s='': out.append(s)
    P(f'電源 {a.volt}V、μ {MU:.2f}、区画 {CELL * 1000:.0f}mm、回転数の上限 {RPM_CAP}rpm(ロータ {J_ROT * 1e7:.2f} g·cm²)')
    P()
    P('■ 質量と回る部品')
    for k in M:
        p = model(k, a.volt)
        P(f'  {k}: 質量 {p["m"] * 1000:.1f}g → 有効質量 {p["m_eff"] * 1000:.1f}g、慣性モーメント {p["Iz"] * 1e7:.0f} → 有効 {p["Iz_eff"] * 1e7:.0f} g·cm²')
    for S in a.suction:
        P()
        P(f'■ 吸引 {S:.0f}g')
        for k in M:
            p = model(k, a.volt)
            P(f'  {k}')
            P(f'    グリップの限界(加速・減速・横): {grip(p, S):.0f} m/s²(この加速に要る電流 片側 {grip(p, S) / d.accel_current_limit(p["dc"], 1):.1f}A)')
            P(f'    加速(0 m/s): 片側3A {acc(p, 0, 3, S):.0f}、3.5A {acc(p, 0, 3.5, S):.0f}、4A {acc(p, 0, 4, S):.0f}、5A {acc(p, 0, 5, S):.0f} m/s²'
              f' / 6 m/s で 3.5A {acc(p, 6, 3.5, S, False):.0f}、10 m/s で {acc(p, 10, 3.5, S, False):.0f} m/s²(電圧で決まる所は電流によらない)')
            P(f'    最高速: 回転数の上限で {vcap(p):.1f} m/s、上限なし(無負荷){vmax_free(p):.1f} m/s')
            for I in (3.0, 3.5):
                row = []
                for n in (2, 4, 8, 15):
                    t1, v1 = straight(p, n * CELL, I, S)
                    t2, v2 = straight(p, n * CELL, I, S, cap=False)
                    row.append(f'{n}区画 {t1 * 1000:.0f}ms({v1:.1f})' + ('' if abs(t1 - t2) < 1e-3 else f' [上限なし {t2 * 1000:.0f}ms({v2:.1f})]'))
                P(f'    直線(片側{I}A、3 m/s で入って出る): ' + '、'.join(row))
            row = []
            for n in (2, 4, 8, 15):
                tg, vg = straight_guard(p, n * CELL, S)
                row.append(f'{n}区画 {tg * 1000:.0f}ms({vg:.1f})')
            P(f'    直線(片側 5A・電池の電流 7.5A で見張る、2026-11-21 決定): ' + '、'.join(row)
              + f'。走り出し {acc_guard(p, 0, S):.0f}、4 m/s {acc_guard(p, 4, S):.0f}、10 m/s {acc_guard(p, 10, S, False):.0f} m/s²')
            lat = grip(p, S)
            P('    ターンの速さの上限(横の加速度 = グリップ): ' + '、'.join(f'半径{R * 1000:.0f}mm {math.sqrt(lat * R):.2f} m/s' for R in (0.045, 0.07, 0.09, 0.135)))
            P('    V90 の入りの外側の電流: ' + '、'.join(f'{v:.1f} m/s {v90_current(p, v):.1f}A' for v in (2.2, 2.6, 3.0, 3.4)))
    print('\n'.join(out))

"""MK4の駆動系の見積もり(docs/spec.md の表を出すスクリプト)

python3 docs/calc/drive_calc.py
python3 docs/calc/drive_calc.py --gear 4.2   # ギア比を指定(スパーの歯数 / ピニオンの歯数)

摩擦・ドライバの損失・電池の電圧降下は入れていない。
V90のdutyは、MK3がV90 2200でちょうど張り付く(100%)ように慣性モーメントを逆算して求める。
"""
import argparse
import math

G_ACC = 9.80665
D2R = math.pi / 180

# MK3(KOGUMA MkIIl の Define.h)
MK3 = dict(V=16.0, Kt=2.63e-3, Ke=2.09e-3, R=5.4, G=70 / 41, n=1, r=0.0231 / 2, T=0.055, m=0.078)

# NFP-D8620-3665-3-7.4(販売ページの表)
NFP_KT = 15 * G_ACC / 100 / 1000          # 15 g·cm/A → N·m/A
NFP_R = 1.0
NFP_KE = (7.4 - 0.14 * NFP_R) / (46000 * 2 * math.pi / 60)   # 無負荷回転数から


def mk4(G, n=1, m=0.090, T=0.055, V=7.4):
    return dict(V=V, Kt=NFP_KT, Ke=NFP_KE, R=NFP_R, G=G, n=n, r=0.023 / 2, T=T, m=m)


def accel_voltage_limit(p, v):
    """速度v[m/s]で電圧いっぱいに出せる加速度[m/s²]"""
    i = (p['V'] - p['Ke'] * p['G'] * v / p['r']) / p['R']
    return 2 * p['n'] * p['Kt'] * p['G'] * i / (p['r'] * p['m'])


def accel_current_limit(p, i):
    """1個あたりの電流i[A]で出せる加速度[m/s²]"""
    return 2 * p['n'] * p['Kt'] * p['G'] * i / (p['r'] * p['m'])


def grip_limit(m, suction_g, mu):
    """2輪で吸引の力がすべて駆動輪にかかるときのグリップの限界[m/s²]"""
    return mu * (m + suction_g / 1000) * G_ACC / m


def v90_duty(p, Iz, v):
    """V90(G_Turn2000の2000deg/s・130000deg/s²を速度で換算)の外側の車輪に必要な電圧 / 電源電圧[%]"""
    k = v / 2.0
    W = 2000 * k * D2R
    A = 130000 * k * k * D2R
    t1 = math.pi * W / (2 * A)
    worst = 0
    for j in range(201):
        t = t1 * j / 200
        w = W / 2 * (1 - math.cos(2 * A / W * t))
        a = A * math.sin(2 * A / W * t)
        i = Iz * a / p['T'] * p['r'] / (p['n'] * p['Kt'] * p['G'])
        worst = max(worst, (i * p['R'] + p['Ke'] * p['G'] * (v + w * p['T'] / 2) / p['r']) / p['V'])
    return worst * 100


def calibrate_iz():
    lo, hi = 1e-7, 1e-3
    for _ in range(60):
        mid = (lo + hi) / 2
        if v90_duty(MK3, mid, 2.2) > 100:
            hi = mid
        else:
            lo = mid
    return lo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--gear', type=float, nargs='*', default=[3, 4, 5, 6])
    args = ap.parse_args()

    print(f'NFP-D8620 7.4V: Kt={NFP_KT * 1e3:.3f} mNm/A, Ke={NFP_KE * 1e3:.3f} mV/(rad/s), '
          f'Km={NFP_KT / math.sqrt(NFP_R) * 1e3:.2f} (MK3 {MK3["Kt"] / math.sqrt(MK3["R"]) * 1e3:.2f})')

    print('\n直線の加速(片側1個、90g、7.4V)')
    for G in args.gear:
        p = mk4(G)
        rpm6 = 6 / p['r'] * G * 60 / (2 * math.pi)
        print(f'  ギア比{G:.2f}: 電圧の上限 {accel_voltage_limit(p, 0):.0f} / {accel_voltage_limit(p, 3):.0f} / '
              f'{accel_voltage_limit(p, 6):.0f} m/s² (0/3/6 m/s), 片側3A {accel_current_limit(p, 3):.0f} m/s², '
              f'6m/sで{rpm6:.0f}rpm, 無負荷の最高速 {p["V"] / p["Ke"] * p["r"] / G:.1f} m/s')
    print(f'  MK3: 電圧の上限 {accel_voltage_limit(MK3, 0):.0f} m/s² (0 m/s)')

    mu = 91.5 * MK3['m'] / ((MK3['m'] + 0.4) * G_ACC)
    print(f'\nグリップ(μ ≥ {mu:.2f}: MK3はV90 2200(横91.5m/s²)で滑らず、dutyが先に張り付いたため下限)')
    for n, m in [(1, 0.090), (2, 0.102)]:
        for s in [400, 600]:
            print(f'  片側{n}個 {m * 1000:.0f}g 吸引{s}g: {grip_limit(m, s, mu):.0f} m/s² 以上')

    Iz = calibrate_iz()
    print(f'\nV90の外側の車輪に必要な電圧(MK3から逆算した慣性モーメント {Iz * 1e7:.0f} g·cm²)')
    for v in [2.2, 2.4, 2.7, 3.0, 3.3]:
        cols = ' | '.join(f'ギア比{G:.2f} {v90_duty(mk4(G), Iz * 1.15, v):.0f}%' for G in args.gear)
        print(f'  V90 {v * 1000:.0f}: MK3 {v90_duty(MK3, Iz, v):.0f}% | {cols}')


if __name__ == '__main__':
    main()

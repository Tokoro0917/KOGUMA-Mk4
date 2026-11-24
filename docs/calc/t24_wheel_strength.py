"""タイヤ24mm のホイール・平行ピン・軸受の強さの見積もり(2026-11-24、ユーザー「強度は担保できるのですか? 無理なら平行ピンを長くする」)。
使い方: python3 docs/calc/t24_wheel_strength.py
右の車輪で考える(y は外がマイナス)。並び(mechanical/vehicle の機体): タイヤ y -33.3〜-24.8(真ん中 -29.05、半径 12)、
外の軸受 LF-630 -23.2〜-21.2、内の軸受 -21.0〜-19.0、平行ピン 3×6 は -26.2〜-20.2(ホイールに 3mm 圧入)、磁石 -20.2〜-19.2。
内の軸受は、ピンに 0.8mm(-21.0〜-20.2)しかかかっていない(残りは磁石)。
荷重: ターンで外のタイヤが滑る限界(タイヤの μ 1.52、機体 59.9g、重心の高さ 13.8mm、左右のタイヤの間 58.1mm)。
LF-630ZZ: 基本動定格荷重 Cr 206N、基本静定格荷重 C0r 73N(NMB の仕様書)"""
import math

M_KG, H_MM, TRACK_MM, MU, R_TIRE = 0.0599, 13.8, 58.1, 1.52, 12.0
Y_TIRE, Y_BRG_OUT = -29.05, -22.2          # タイヤの真ん中、外の軸受の真ん中
C0R, CR = 73.0, 206.0


def wheel_loads(suction_g):
    """外のタイヤの縦の力 N と横の力 F [N](滑る限界)"""
    total_n = (M_KG + suction_g / 1000) * 9.81
    a = MU * total_n / M_KG
    dn = M_KG * a * H_MM / TRACK_MM
    n_out = total_n / 2 + dn
    return n_out, MU * n_out


def moment(n, f, cancel):
    """軸受のまわりの曲げモーメント [N·mm]。外のタイヤの横の力(内向き)と縦の力の向きは逆に効く(cancel)。足し合わせる場合も見る"""
    a = Y_BRG_OUT - Y_TIRE
    if cancel:
        return abs(f * R_TIRE - n * a)
    return f * R_TIRE + n * a


print('LF-630ZZ: C0r', C0R, 'N、Cr', CR, 'N')
for suction in (600, 1000):
    n, f = wheel_loads(suction)
    print(f'\n吸引 {suction}g: 外のタイヤ 縦 {n:.1f}N、横 {f:.1f}N(滑る限界)')
    for cancel in (True, False):
        m = moment(n, f, cancel)
        tag = '縦と横が打ち消し合う(ターン)' if cancel else '足し合わせ(悪い場合)'
        for name, span in (('今(内の軸受にピン 0.8mm、間 1.6mm)', 1.6), ('ピンが内の軸受を通る(間 2.2mm)', 2.2)):
            r_in = m / span
            r_out = r_in + n
            print(f'  {tag}、{name}: モーメント {m:.0f} N·mm → 外の軸受 {r_out:.0f}N、内 {r_in:.0f}N(C0r の {r_out / C0R:.2f} 倍)')
    m = moment(n, f, False)
    for depth in (3.0, 5.0):
        p_edge = 6 * m / (3.0 * depth**2)       # ピンの穴の縁の面圧(長さ方向に直線で分布するとして)
        print(f'  ホイールのピンの穴 深さ {depth:.0f}mm: 縁の面圧 {p_edge:.0f} MPa(足し合わせのモーメントで)')
    sigma_pin = 32 * m / (math.pi * 3.0**3)
    print(f'  平行ピン φ3 の曲げの応力 {sigma_pin:.0f} MPa(鋼の焼入れピンは 1,000MPa 以上)')

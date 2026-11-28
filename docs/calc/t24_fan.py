"""タイヤ24mm の機体(t24)の吸引ファンの動く所の見積もり(2026-11-21、ブランチ claude/trusting-dirac-1tdt54)。
吸引の力 600g(目標)を、吸引する面 68 × 34mm(t24v3)・80 × 42.6mm(t24v5、2026-11-23)・羽根 φ32・モーター NFP-D8620(7.4V版)を 3S で出せるか。
使い方(リポジトリの一番上で): python3 docs/calc/t24_fan.py

  負圧 = 吸引の力 / 面積。漏れる空気 = 流量係数 0.6 × 縁の長さ × すき間 × √(2 × 負圧 / 空気の密度)(docs/spec.md の見積もりと同じ)
  羽根の先端の速さ: 負圧 = 空気の密度 × 先端の速さ² × 係数(0.6〜1.0。docs/spec.md の「羽根の回転数」)
  羽根の効率(空気の仕事 / 軸の仕事)を 40% として、軸のトルク = 軸の仕事 / 角速度
  モーター: 電流 = トルク / Kt + 無負荷の電流、電圧 = R × 電流 + Ke × 角速度、duty = 電圧 / 電池の電圧、電池の電流 = duty × 電流
"""
import math, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import drive_calc as d

RHO = 1.2
AREAS = {'t24v3(68 × 34mm)': (0.068, 0.034), 't24v5(80 × 42.6mm、2026-11-23)': (0.080, 0.0426)}
D_IMP = 0.032
ETA_IMP = 0.40
I0 = 0.14                     # 無負荷の電流(7.4V、販売ページの表)
V_BAT = 11.1
V_MOT_MAX = 7.4               # モーターの定格の電圧(7.4V 版)。duty でこれまでに抑える
Kt, Ke, R = d.NFP_KT, d.NFP_KE, d.NFP_R

def point(S, gap, c, area, perim):
    """吸引の力 S [g]、すき間 gap [m]、羽根の係数 c → (負圧, 風量, 空気の仕事, 回転数 rpm, モーターの電流, 電圧, 電池の電流)"""
    dp = S / 1000 * d.G_ACC / area
    q = 0.6 * perim * gap * math.sqrt(2 * dp / RHO)
    pa = q * dp
    u = math.sqrt(dp / (RHO * c))
    w = u / (D_IMP / 2)
    T = pa / ETA_IMP / w
    I = T / Kt + I0
    U = R * I + Ke * w
    return dp, q, pa, w * 60 / (2 * math.pi), I, U, U / V_BAT * I

def max_force(gap, c, area, perim, vmax=V_MOT_MAX):
    """モーターの電圧が vmax になる吸引の力 [g]"""
    lo, hi = 0.0, 5000.0
    for _ in range(60):
        m = (lo + hi) / 2
        if point(m, gap, c, area, perim)[5] > vmax:
            hi = m
        else:
            lo = m
    return lo

for name, (lx, ly) in AREAS.items():
    AREA, PERIM = lx * ly, 2 * (lx + ly)
    print(f'\n== {name}: 吸引する面 {AREA * 1e6:.0f}mm²(縁 {PERIM * 1000:.0f}mm)、羽根 φ{D_IMP * 1000:.0f}、羽根の効率 {ETA_IMP:.0%}、電池 {V_BAT}V')
    print('吸引  すき間  負圧    風量      空気の仕事  回転数(係数1.0 / 0.6)    モーターの電流  電圧(7.4V以下か)  電池の電流')
    for S in (400, 600, 700):
        for gap in (0.1e-3, 0.15e-3, 0.2e-3):
            (dp, q, pa, r1, i1, u1, b1), (_, _, _, r2, i2, u2, b2) = point(S, gap, 1.0, AREA, PERIM), point(S, gap, 0.6, AREA, PERIM)
            print(f'{S:4d}g  {gap * 1000:.2f}mm  {dp / 1000:.2f}kPa  {q * 1000:.2f} L/s   {pa:.2f}W      {r1 / 1000:4.1f}k / {r2 / 1000:4.1f}k rpm        '
                  f'{i1:.2f} / {i2:.2f}A    {u1:.1f} / {u2:.1f}V        {b1:.2f} / {b2:.2f}A')
    print('モーター 7.4V(定格)で出せる吸引の力(羽根の係数 1.0 / 0.6): ' + '、'.join(
        f'すき間 {g * 1000:.2f}mm {max_force(g, 1.0, AREA, PERIM):.0f} / {max_force(g, 0.6, AREA, PERIM):.0f}g' for g in (0.1e-3, 0.15e-3, 0.2e-3)))

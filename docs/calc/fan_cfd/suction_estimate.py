"""組み上がった形(羽根 t24v6、一次スカート t24v3、二次スカートの袋 t24v3)で、ファンの電圧ごとの回転数・電流・吸引の力を見積もる
(2026-11-27、ユーザー「これで揃った。どれだけ吸引するか計算できますか?」)。
使い方: python3 docs/calc/fan_cfd/suction_estimate.py
やり方:
  1. 35,000rpm の負圧は流体の計算(post.py。吸引 [g] は負圧 × 68 × 34mm で出している)から逆算する
     - すき間 0.05mm: 9 枚・羽をハブまで(n9s0hub、粗いメッシュ)の 365g・1.87W
     - 密閉: 5 枚の密閉(CS0c、粗いメッシュ)の 384g・0.72W に、9 枚にした分(すき間 0.05mm で吸引 +6%)を掛けた見込み
  2. 負圧は回転数の 2 乗、羽根を回す仕事は 3 乗(トルクは 2 乗)に比例するとして、モーターの式
     電圧 = 逆起電力定数 × 角速度 + 巻線抵抗 × 電流、電流 = 無負荷の電流 + トルク ÷ トルク定数 を解く
     (NFP-D8620: 逆起電力定数 1.51 mV/(rad/s)、トルク定数 1.47 mN·m/A、巻線抵抗 1Ω。docs/spec.md。無負荷の電流 0.05A は仮の値)
  3. 吸引の力 = 負圧 × 低い圧力がかかる面積。袋が床のどこで閉じるかで面積が変わるので、3 つで見る:
     枠の中(75 × 27.4mm)、枠の外のふち(80 × 32.4mm)、袋の外のふち(96 × 49mm、角 R8)"""
import math

KE = 1.51e-3          # 逆起電力定数 [V/(rad/s)]
KT = 1.47e-3          # トルク定数 [N·m/A]
R_OHM = 1.0           # 巻線抵抗
I0_A = 0.05           # 無負荷の電流(仮)
AREA_CFD_MM2 = 68 * 34
AREAS = [('枠の中 75×27.4', 75 * 27.4), ('枠の外のふち 80×32.4', 80 * 32.4), ('袋の外 96×49', 96 * 49 - (4 - math.pi) * 8 ** 2)]
W35 = 35000 * 2 * math.pi / 60
CASES = [('すき間 0.05mm', 364.5, 1.868), ('密閉(見込み)', 383.7 * 1.06, 0.715 * 1.06 ** 1.5)]


def speed_at(voltage, torque35):
    """電圧をかけたときの角速度 [rad/s](二分法で解く)"""
    lo = 0.0
    hi = voltage / KE
    for i in range(100):
        w = (lo + hi) / 2
        torque = torque35 * (w / W35) ** 2
        if KE * w + R_OHM * (I0_A + torque / KT) > voltage:
            hi = w
        else:
            lo = w
    return w


for name, grams35, power35 in CASES:
    p35 = grams35 / 1000 * 9.81 / (AREA_CFD_MM2 * 1e-6)
    torque35 = power35 / W35
    print(f'{name}: 35,000rpm で負圧 {p35:.0f}Pa')
    for voltage in (5.0, 6.0, 7.4, 8.5):
        w = speed_at(voltage, torque35)
        scale = (w / W35) ** 2
        current = I0_A + torque35 * scale / KT
        text = f'  {voltage:.1f}V: {w * 60 / 2 / math.pi:,.0f}rpm、{current:.2f}A、負圧 {p35 * scale:.0f}Pa →'
        for area_name, area in AREAS:
            text += f' {area_name}: {p35 * scale * area * 1e-6 / 9.81 * 1000:.0f}g'
        print(text)

"""ファンの羽根(C 案、φ30)が回る力(遠心力)でどれくらい引っぱられ、曲げられるかの見積もり(2026-11-25、ユーザー
「回転数を上げるとファン自体が自壊するらしいので、壊れにくい設計にしなきゃ」)。
使い方(リポジトリの一番上から): python3 docs/calc/fan_cfd/impeller_stress.py

手で計算できる3つを出す(FEM ではない。形が決まったら FEM で確かめる):
  1. 回る外の壁(薄い輪): 輪の向きに引っぱられる力 σ = ρ v²(v は輪の速さ)
  2. 上の板(真ん中に軸の穴のある円板): 穴のふちが一番引っぱられる。σ = (3 + ν) / 4 × ρ ω² R²
  3. 羽: 曲がった羽は、遠心力のうち羽の面に直角な分で横へ曲げられる。羽は上の板から下へぶら下がった
     片持ちの板として、付け根の曲げの力 σ = 3 ρ ω² r sinβ L² / t
       r: 軸からの距離、β: 羽の面と半径の向きのなす角、L: 羽の高さ、t: 羽の厚さ
     まっすぐ(0°)の羽は遠心力が羽の面に沿うので、曲げはほぼ 0
     羽の外の端は回る外の壁につながっているので、外の端の近くは計算より小さい。内の方(r 10mm)を目安にする
  羽の曲がりは make_case.py と同じ対数らせん: 内の端から外の端までで sweep 回る → tanβ = sweep / ln(R_TIP / R_IN)
材料は光造形の樹脂として 密度 1.2 g/cm³、ν 0.35。付け根の角が丸められていないと、角で力が 2〜3 倍に集まる
あわせて、ファンのモーター(NFP-D8620、7.4V 版)にかける電圧と回転数の関係も出す(2026-11-25、ユーザー「吸引ファンのモーターは
最短のときだけ定格を超えるのを許す」)。羽根のトルクは回転数の2乗に比例するとし、35,000rpm で 1.07 mN·m
(C 案 φ30 の粗いメッシュ 0.995 mN·m を、φ32 での粗い → 細かいの差 +8% で直した仮の値。細かいメッシュの結果で置きかえる)"""
import math

RHO = 1200.0          # 樹脂の密度 [kg/m³]
NU = 0.35             # ポアソン比
R_TIP = 15.0e-3       # 羽の先(φ30)
R_IN = 5.0e-3         # 羽の内の端
R_RIM = 15.3e-3       # 回る外の壁の厚さの真ん中
R_DISC = 15.6e-3      # 上の板の外の半径
R_BLADE = 10.0e-3     # 羽の曲げを見る位置
HEIGHT = 3.9e-3       # 羽の高さ
THICK = 0.6e-3        # 羽の厚さ
# ファンのモーター NFP-D8620(docs/spec.md「モーター」)
R_MOTOR_OHM = 1.0     # 巻線抵抗
KT = 1.47e-3          # トルク定数 [N·m/A]
KE = 1.51e-3          # 逆起電力定数 [V/(rad/s)]
I_NOLOAD_A = 0.14     # 無負荷電流
TORQUE_35K = 1.07e-3  # 羽根を 35,000rpm で回すトルク [N·m](仮)


def omega(rpm):
    return rpm * 2 * math.pi / 60


def rim_stress_mpa(rpm):
    """回る外の壁が輪の向きに引っぱられる力 [MPa]"""
    v = omega(rpm) * R_RIM
    return RHO * v ** 2 / 1e6


def disc_stress_mpa(rpm):
    """上の板の、軸の穴のふちの力 [MPa](穴が小さいときの式)"""
    return (3 + NU) / 4 * RHO * omega(rpm) ** 2 * R_DISC ** 2 / 1e6


def blade_angle_deg(sweep_deg):
    """羽の面と半径の向きのなす角 β [°]"""
    return math.degrees(math.atan(math.radians(sweep_deg) / math.log(R_TIP / R_IN)))


def blade_stress_mpa(rpm, sweep_deg, height=HEIGHT, thick=THICK):
    """羽の付け根(上の板とのつなぎ目)の曲げの力 [MPa]"""
    beta = math.radians(blade_angle_deg(sweep_deg))
    return 3 * RHO * omega(rpm) ** 2 * R_BLADE * math.sin(beta) * height ** 2 / thick / 1e6


def fan_rpm(volt):
    """モーターに volt をかけたときの回転数。volt = R × 電流 + Ke × ω、電流 = 羽根のトルク / Kt + 無負荷電流 を ω について解く"""
    a = TORQUE_35K / omega(35000) ** 2 / KT * R_MOTOR_OHM     # ω² の係数
    b = KE                                                     # ω の係数
    c = I_NOLOAD_A * R_MOTOR_OHM - volt
    w = (-b + math.sqrt(b * b - 4 * a * c)) / (2 * a)          # 2次方程式の正の解
    return w * 60 / (2 * math.pi)


def fan_current_a(rpm):
    """その回転数でモーターに流れる電流"""
    torque = TORQUE_35K * (rpm / 35000) ** 2
    return torque / KT + I_NOLOAD_A


if __name__ == '__main__':
    print('回転数        外の壁   上の板の穴   羽(0° / 30° / 60° / 90°)の付け根の曲げ')
    for rpm in (35000, 40000, 45000, 56000, 64000):
        blades = []
        for sweep in (0, 30, 60, 90):
            blades.append(f'{blade_stress_mpa(rpm, sweep):5.1f}')
        print(f'{rpm:6d}rpm   {rim_stress_mpa(rpm):5.1f}MPa   {disc_stress_mpa(rpm):5.1f}MPa     {" / ".join(blades)} MPa')
    print()
    for sweep in (0, 30, 60, 90):
        print(f'曲がり {sweep:2d}°: 羽の面と半径の向きのなす角 β = {blade_angle_deg(sweep):4.1f}°')
    print()
    print(f'60° の羽、35,000rpm: 高さ 4.9mm → {blade_stress_mpa(35000, 60, height=4.9e-3):.1f}MPa、'
          f'厚さ 0.8mm → {blade_stress_mpa(35000, 60, thick=0.8e-3):.1f}MPa(基準 {blade_stress_mpa(35000, 60):.1f}MPa)')
    print()
    print('ファンのモーターの電圧と回転数(羽根 φ30 の C 案、トルクは仮の値)')
    for volt in (7.4, 8.0, 8.5, 9.0, 12.6):
        rpm = fan_rpm(volt)
        print(f'  {volt:4.1f}V → {rpm:6.0f}rpm、モーターの電流 {fan_current_a(rpm):.2f}A、60° の羽の付け根 {blade_stress_mpa(rpm, 60):.1f}MPa')

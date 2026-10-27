"""ギア比の見直し(2026-10-27): 今の機体(52.76g、251 g·cm²、タイヤ15mm、トレッド60mm、3S 11.1V)で、ピニオン11〜15Tを比べる
使い方(リポジトリの一番上で): python3 docs/calc/gear_study.py"""
import sys, math; sys.path.insert(0,'docs/calc')
import drive_calc as d
m=0.05276; Iz=250.9e-7; T=0.0601; tire=0.015; V=11.1
mu=91.5*0.078/((0.078+0.4)*d.G_ACC)
def run(G, I, suction, L, v0=3.0):
    p=d.mk4(G, m=m, T=T, V=V, tire=tire)
    grip=d.grip_limit(m, suction, mu)
    acc=lambda v: min(d.accel_voltage_limit(p,v), d.accel_current_limit(p,I), grip)
    dec=lambda v: min(d.accel_current_limit(p,I), grip)   # 減速は電流とグリップ
    # 加速で v を上げ、残りで v0 まで落とせる所まで。時間を積分
    dt=1e-4; x=0; v=v0; t=0; xs=[];
    best=None
    while True:
        # 今から減速して v0 に落とすのに要る距離
        sd=(v*v-v0*v0)/(2*dec(v))
        if x+sd>=L: break
        a=acc(v)
        if a<=1e-6: break
        v+=a*dt; x+=v*dt; t+=dt
        if v>40: break
    vmax=v
    t+= (v-v0)/dec(v) + max(0,L-x-(v*v-v0*v0)/(2*dec(v)))/v
    return t, vmax
print('ギア比  ピニオン 軸間  1Aの加速 3A/3.5Aの加速  無負荷最高速 電圧上限(3/6/10m/s)  6m/sと14m/sの回転数  V90 3000外側A/電圧%')
for z in (11,12,13,14,15):
    G=41/z; p=d.mk4(G,m=m,T=T,V=V,tire=tire)
    vmax=p['V']/p['Ke']*p['r']/G
    rpm=lambda v: v/p['r']*G*60/(2*math.pi)
    print(f'{G:5.2f} {z:3d}T  {0.15*(41+z):.2f}  {d.accel_current_limit(p,1):5.1f}   {d.accel_current_limit(p,3):5.0f}/{d.accel_current_limit(p,3.5):4.0f}     {vmax:5.1f}      {d.accel_voltage_limit(p,3):4.0f}/{d.accel_voltage_limit(p,6):4.0f}/{d.accel_voltage_limit(p,10):4.0f}        {rpm(6)/1000:4.1f}k/{rpm(14)/1000:4.1f}k      {d.v90_peak_current(p,Iz,3.0):.1f}/{d.v90_duty(p,Iz,3.0):.0f}')
print()
for I in (3.0, 3.5):
  for s in (400,550):
    print(f'片側{I}A・吸引{s}g: 直線を 3m/s で入って 3m/s で出る時間 [ms](最高速 m/s)')
    for z in (11,12,13,14,15):
        G=41/z
        row=[]
        for n in (2,4,8,15):
            t,vm=run(G,I,s,n*0.18); row.append(f'{n}区画 {t*1000:5.0f}({vm:4.1f})')
        print(f'  {z}T(G{G:.2f}): '+'  '.join(row))

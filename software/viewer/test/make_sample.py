"""ビューアの試験用: MK4 の見本のログ(run・current・sensor・explore)と、書き込みの見本の .bin を作る"""
import math
import os
import random

OUT = os.environ.get("OUT_DIR", "/tmp")   # 見本のファイルを置く所

L = []
n = 1500
dt = 0.001
cols = "t,x,v,v_target,a,a_target,v_L,v_R,w,w_target,angle,i_L_target,i_R_target,i_L,i_R,duty_L,duty_R,batt,s_FL,s_L,s_R,s_FR,dist_L,dist_R,dist_F,wall_err,wall_out,fan_i,wall,phase,flags"
L.append(f"#BEGIN LOG kind=run dt={dt} n={n} div=1")
L.append(cols)
x = 0
for i in range(n):
    t = i * dt
    vt = min(1500, t * 6000)
    v = vt + 20 * math.sin(t * 50)
    x += v * dt
    ph = 1 if i < 800 else (4 if i < 1100 else 5)
    w = 0 if ph != 4 else 600 * math.sin((i - 800) / 300 * math.pi)
    acc = 6000 if t < 0.25 else 0
    ang = 0 if ph != 4 else (i - 800) * 0.3
    row = [t, x, v, vt, acc, acc, v - 5, v + 5, w, w, ang, 800, 820, 790, 815, 30, 31, 11.8, 300, 900, 880, 320, 42, 41, 120, 0.3, 1.2, 1500, 3, ph, 0]
    L.append(",".join(str(round(z, 2)) for z in row))
L.append("#END LOG crc=0 len=0")

n = 4000
dt = 0.00005
L.append(f"#BEGIN LOG kind=current dt={dt} n={n}")
L.append("t,i_L_target,i_L,i_R_target,i_R,duty_L,duty_R,batt,v_L,v_R")
for i in range(n):
    t = i * dt
    it = 1000 if t > 0.02 else 0
    il = it * (1 - math.exp(-(t - 0.02) / 0.0004)) if t > 0.02 else 0
    L.append(",".join(str(round(z, 3)) for z in [t, it, il + random.gauss(0, 8), it, il, 20, 20, 11.9, 0, 0]))
L.append("#END LOG")

n = 2000
dt = 0.00025
L.append(f"#BEGIN LOG kind=sensor dt={dt} n={n}")
L.append("t,off_FL,off_L,off_R,off_FR,on_FL,on_R,on_L,on_FR,x3_FL,x3_L,x3_R,x3_FR,x,angle")
for i in range(n):
    t = i * dt
    L.append(",".join(str(round(z, 2)) for z in [t, 200, 210, 205, 198, 1200 + 300 * math.sin(t * 10), 950, 900, 1150, 202, 211, 206, 199, t * 100, 0]))
L.append("#END LOG")

L.append("#BEGIN EXPLORE n=60")
L.append("t_ms,cell_x,cell_y,dir,wall_F,wall_L,wall_R,s_FL,s_L,s_R,s_FR,action,calc_us,v")
for i in range(60):
    row = [i * 180, i % 16, i // 16, 0, random.randint(0, 1), random.randint(0, 1), random.randint(0, 1), 300, 900, 880, 320, random.randint(0, 3), random.randint(40, 300), 600]
    L.append(",".join(str(z) for z in row))
L.append("#END EXPLORE")

open(OUT + "/sample_mk4.txt", "w").write("\n".join(L) + "\n")
open(OUT + "/app.bin", "wb").write(os.urandom(30000))
print("ok")

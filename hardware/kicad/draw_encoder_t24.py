"""タイヤ24mm 用のエンコーダ基板(KOGUMA-Mk4_Encoder_t24)の絵: チップの面(F)と裏の面(B)。
パッド・配線・ビアは /usr/bin/python3.12 の pcbnew で読み(KiCad 9 の Python は 3.12 向け)、matplotlib で描く。
使い方(リポジトリの一番上で): python3 hardware/kicad/draw_encoder_t24.py → hardware/kicad/KOGUMA-Mk4_Encoder_t24/encoder_t24.png"""
import json, os, subprocess
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, 'KOGUMA-Mk4_Encoder_t24', 'KOGUMA-Mk4_Encoder_t24.kicad_pcb')
DUMP = r'''
import json, sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
out = dict(pads=[], tracks=[], vias=[])
for fp in b.GetFootprints():
    for p in fp.Pads():
        q = p.GetPosition(); s = p.GetSize()
        lay = 'B' if p.IsOnLayer(pcbnew.B_Cu) and not p.IsOnLayer(pcbnew.F_Cu) else 'F'
        out['pads'].append(dict(ref=fp.GetReference(), net=p.GetNetname(), x=q.x / 1e6, y=q.y / 1e6, w=s.x / 1e6, h=s.y / 1e6, ang=p.GetOrientationDegrees(), layer=lay))
for t in b.GetTracks():
    if t.GetClass() == 'PCB_VIA':
        out['vias'].append(dict(x=t.GetPosition().x / 1e6, y=t.GetPosition().y / 1e6))
    else:
        out['tracks'].append(dict(x0=t.GetStart().x / 1e6, y0=t.GetStart().y / 1e6, x1=t.GetEnd().x / 1e6, y1=t.GetEnd().y / 1e6, w=t.GetWidth() / 1e6, layer=pcbnew.LayerName(t.GetLayer())))
print('JSON' + json.dumps(out))
'''
res = subprocess.run(['/usr/bin/python3.12', '-c', DUMP, PCB], capture_output=True, text=True, check=True)
d = json.loads([l for l in res.stdout.splitlines() if l.startswith('JSON')][0][4:])

plt.rcParams['font.family'] = 'WenQuanYi Zen Hei'; plt.rcParams['axes.unicode_minus'] = False
X0, X1, TOP, BOT, CY = 97.0, 103.0, 100.0, 108.75, 104.9
col = {'F': '#c83232', 'B': '#3c78c8'}
short = {'/ENC_CS': 'CS', '/ENC_SCK': 'SCK', '/ENC_MOSI': 'MOSI', '/ENC_MISO': 'MISO', '/ENC_CAL': 'CAL', 'GND': 'GND', '+3V3': '3V3'}
fig, axs = plt.subplots(1, 2, figsize=(11, 7.6))
for ax, side, title, mir in ((axs[0], 'F', 'チップの面(F、外側・磁石の側)から見る', False), (axs[1], 'B', '裏の面(B、内側・メイン基板の側)から見る', True)):
    ax.add_patch(Rectangle((X0, TOP), X1 - X0, BOT - TOP, fc='#0b2a14', ec='#ddd', lw=1))
    for t in d['tracks']:
        L = t['layer'][0]
        ax.plot([t['x0'], t['x1']], [t['y0'], t['y1']], color=col[L], lw=t['w'] * 28, alpha=1 if L == side else 0.18, solid_capstyle='round')
    for p in d['pads']:
        if p['layer'] != side and p['ref'] != 'U1':
            continue
        w, h = (p['h'], p['w']) if abs(p['ang']) % 180 == 90 else (p['w'], p['h'])
        ax.add_patch(Rectangle((p['x'] - w / 2, p['y'] - h / 2), w, h, fc=col[p['layer']], alpha=1 if p['layer'] == side else 0.18, ec='none'))
        if p['ref'] == 'J1' and p['layer'] == side:
            ax.text(p['x'], p['y'] + 1.25, short.get(p['net'], p['net']), ha='center', fontsize=7, color='w', rotation=90)
    for v in d['vias']:
        ax.add_patch(Circle((v['x'], v['y']), 0.3, fc='#c8a832')); ax.add_patch(Circle((v['x'], v['y']), 0.15, fc='#0b2a14'))
    ax.add_patch(Rectangle((97.8, CY - 2.5), 4.4, 5.0, fill=False, ec='#bbb', lw=0.8, ls='--'))
    ax.text(100, CY, 'MT6835', ha='center', va='center', color='#bbb', fontsize=8, alpha=0.8)
    for y, s, c in ((CY - 2.2, 'メイン基板の上面 z 14.2', '#ffd27f'), (CY - 1.6, '下面 z 13.6', '#ffd27f'), (CY, '磁石の軸 z 12.0', '#ff7070')):
        ax.axhline(y, color=c, lw=0.8, ls=':'); ax.text(103.15 if not mir else 96.85, y, s, fontsize=7, color=c, va='center', ha='left' if not mir else 'right')
    ax.set_ylim(109.2, 99.5); ax.set_aspect('equal')
    ax.set_xlim(*((103.5, 94.4) if mir else (96.5, 105.6)))
    ax.set_title(title, fontsize=10); ax.set_facecolor('#1d2530'); ax.set_xticks([]); ax.set_yticks([])
fig.suptitle('タイヤ24mm 用のエンコーダ基板 t24(6.0 × 8.75 × 0.6mm)。赤 = F、青 = B、黄 = ビア。薄い色は反対の面', fontsize=11)
fig.tight_layout()
out = os.path.join(HERE, 'KOGUMA-Mk4_Encoder_t24', 'encoder_t24.png')
fig.savefig(out, dpi=110); print(out)

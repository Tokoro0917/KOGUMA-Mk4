"""frame t24v6 の前を太くしたらどうなるか(2026-11-23)。使い方(このディレクトリで): python3 t24_thicker.py
前の辺(end_edge)・外周の枠(rim)・筋交い A・骨 G・背骨を太くした案の、重さと衝突(正面・角・横)で座屈する力・割れる力。後ろは 1.6mm のまま"""
import json
import t24, analyze as an
BASE = dict(json.load(open('results/t24v6_params.json')), _suction='w2')
CASES = [('t24v6(今)', {}),
         ('前の辺 2.0', dict(end_edge=2.0)),
         ('前の辺 2.5', dict(end_edge=2.5)),
         ('筋交いA 2.0', dict(brace_w_each={'A': 2.0})),
         ('外周の枠 2.0', dict(rim=2.0)),
         ('骨G 2.0', dict(brace_w=2.0, brace_w_each={'A': 1.6})),
         ('前の辺 2.5 + 筋交いA 2.0', dict(end_edge=2.5, brace_w_each={'A': 2.0})),
         ('前の辺・枠・筋交い・骨G・背骨 2.0', dict(end_edge=2.0, rim=2.0, brace_w=2.0, brace_w_each={'A': 2.0}, spine_root=2.0, spine_tip=2.0)),
         ('前の辺・枠・筋交い・骨G・背骨 2.5', dict(end_edge=2.5, rim=2.5, brace_w=2.5, brace_w_each={'A': 2.5}, spine_root=2.5, spine_tip=2.5))]
L = an.LOADS
rows = []
for name, d in CASES:
    r, g = t24.run(dict(BASE, **d))
    rows.append((name, r))
    print(f"{name:28s} カーボン {r['m_carbon']:.2f}g  座屈 正面 {r['BK_D'] * L['D_front']:.0f} / 角 {r['BK_E'] * L['E_corner']:.0f} / 横 {r['BK_F'] * L['F_side']:.0f}N  "
          f"割れる 正面 {r['SF_D'] * L['D_front']:.0f} / 角 {r['SF_E'] * L['E_corner']:.0f} / 横 {r['SF_F'] * L['F_side']:.0f}N  前の滑り板 {r['dA']:.2f}mm  {r['f1']:.0f}Hz", flush=True)
json.dump({n: r for n, r in rows}, open('results/t24_thicker.json', 'w'), indent=1, ensure_ascii=False, default=float)

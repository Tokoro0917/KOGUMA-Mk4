#!/usr/bin/env python3
"""debug_region.py — 1 つの区間の、命令の種類・メモリの読み書きの内わけを出す(モデルの確かめ用)
  python3 analysis/debug_region.py m7 O2 41"""
import os, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cycle_model as cm

core, cfg, rid = sys.argv[1], sys.argv[2], int(sys.argv[3])
elf = os.path.join(cm.HERE, "build", "%s_%s" % (core, cfg), "bench.elf")
table = cm.decode(core, elf)
regions, seqs = cm.parse_trace(os.path.join(cm.HERE, "traces", "%s_%s.txt" % (core, cfg)), table, core)
key = max(regions[rid], key=lambda k: len(k[0]))
seq = cm.build_seq(key, table)
kinds = Counter(i.kind for i, t, m in seq)
mems = Counter((c, s) for i, t, m in seq for c, s in m)
taken = sum(1 for i, t, m in seq if i.kind == "branch" and t)
print("insns", len(seq), dict(kinds))
print("mem", dict(mems))
print("taken branches", taken)
for lv in range(3):
    for dc in (False, True):
        p = cm.mem_params(core, lv, dc)
        f = cm.cost_m7 if core == "m7" else cm.cost_m33
        print("level", lv, "dcache", dc, "cycles", f(seq, lv, p))
# 依存の遅れを 0 にしたとき(素の 2 つ出し)
funcs = Counter(i.func for i, t, m in seq)
print(funcs.most_common(25))
zero = {k: (0, 0) for k in cm.MEM[core]}
for lv in range(3):
    f = cm.cost_m7 if core == "m7" else cm.cost_m33
    print("level", lv, "no-memory-wait cycles", f(seq, lv, zero), "CPI", round(f(seq, lv, zero) / len(seq), 2))

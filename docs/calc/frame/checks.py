"""最終案の確認: メッシュの細かさ、材料の値のばらつき、軽い案・強い案"""
import json, sys
import fem, analyze as an

F = json.load(open('final_params.json'))
what = sys.argv[1]
out = {}
keys = ('m_carbon', 'iz', 'dA', 'dA_rear', 'dB', 'f1', 'BK_D', 'BK_E', 'SF_A', 'SF_E', 'nel')
if what == 'mesh':
    for ma, h in ((0.3, 0.6), (0.15, 0.45), (0.08, 0.32)):
        r = an.run(F, max_area=ma, h=h)
        out[f'{ma}'] = {k: r[k] for k in keys}
elif what == 'mat':
    base = dict(fem.CF)
    for name, ch in (('E45', dict(E1=45000.0, E2=45000.0)), ('E65', dict(E1=65000.0, E2=65000.0)),
                     ('G3', dict(G12=3000.0)), ('G5', dict(G12=5000.0))):
        fem.CF.update(base); fem.CF.update(ch)
        fem.Q_CF = fem.q_ortho(fem.CF['E1'], fem.CF['E2'], fem.CF['nu12'], fem.CF['G12'])
        r = an.run(F, max_area=0.3, h=0.6)
        out[name] = {k: r[k] for k in keys}
elif what == 'variants':
    light = dict(F, rim=2.0, brace_w=3.0)
    strong = dict(F, v_ribs=['G', 'S'], v_rib_h=4.0)
    for name, p in (('light', light), ('strong', strong)):
        r = an.run(p, max_area=0.15, h=0.45)
        out[name] = dict(params=p, **{k: r[k] for k in keys}, SFmin=min(v for k, v in r.items() if k.startswith('SF_') and 'rib' not in k),
                         SFrib=min([v for k, v in r.items() if k.startswith('SF_rib')] or [99]))
json.dump(out, open(f'check_{what}.json', 'w'), indent=1, default=float)
print(json.dumps(out, indent=1, default=float))

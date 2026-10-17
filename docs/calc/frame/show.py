import json, sys
R = json.load(open(sys.argv[1]))
keys = sys.argv[2].split(',') if len(sys.argv) > 2 else ['rect_ribs', 'land', 'inner_spine']
print(' '.join(f'{k[:8]:>8}' for k in keys), '   mC    Iz    dA   dAr    dB   f1  SFmin  BK_D  BK_E  BK_F  dCsk')
for r in sorted(R, key=lambda r: r.get('m_carbon', 99)):
    if 'error' in r:
        print('ERR', r['params'], r['error'][:100]); continue
    p = r['params']
    sfmin = min(r[k] for k in r if k.startswith('SF_'))
    vals = ' '.join(f"{(''.join(p[k]) if isinstance(p[k], (list, tuple)) else p[k]) or '-'!s:>8}" for k in keys)
    print(vals, f"{r['m_carbon']:5.2f} {r['iz']:5.1f} {r['dA']:5.3f} {r['dA_rear']:5.3f} {r['dB']:5.3f} {r['f1']:4.0f} {sfmin:5.1f} {r['BK_D']:5.2f} {r['BK_E']:5.2f} {r['BK_F']:5.1f} {r['dC_skirt']:5.3f}")

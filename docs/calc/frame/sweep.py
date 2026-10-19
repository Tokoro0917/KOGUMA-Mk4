import json, sys, itertools
from multiprocessing import Pool
import analyze

def job(p):
    try:
        r = analyze.run(p, max_area=0.3, h=0.6)
    except Exception as e:
        r = dict(error=str(e))
    r['params'] = p
    return r

if __name__ == '__main__':
    stage = sys.argv[1]
    cands = []
    if stage == '1':
        for br in [(), ('A',), ('B',), ('C',), ('A', 'D'), ('C', 'D'), ('A', 'B')]:
            for bw in (2.5, 3.5):
                if not br and bw == 3.5:
                    continue
                for sp in ((4, 4), (8, 5)):
                    cands.append(dict(rim=2.5, end_edge=3.0, spine_root=sp[0], spine_tip=sp[1], braces=br, brace_w=bw))
    elif stage == '2a':
        base = dict(rim=2.5, end_edge=3.0, spine_root=8, spine_tip=5, braces=('C',), brace_w=2.5)
        for rr in [(), ('T',), ('X',), ('T', 'X'), ('L',)]:
            for land in (3.0, 4.5):
                for isp in (4.0, 6.0):
                    cands.append(dict(base, rect_ribs=rr, land=land, inner_spine=isp))
    elif stage == '2b':
        for rf, land, rr, br, sp in itertools.product((16.7, 23.0, 30.25), (3.0, 4.5), ((), ('L',)),
                                                     (('C',), ('C', 'D'), ('B',)), ((8, 5), (12, 5))):
            if rf >= 30 and 'D' in br:
                continue
            cands.append(dict(rim=2.5, end_edge=3.0, spine_root=sp[0], spine_tip=sp[1], braces=br, brace_w=2.5,
                              rect_ribs=rr, land=land, inner_spine=4.0, root_fill=rf))
    elif stage == '3':
        bases = [dict(root_fill=16.7, land=3.0, braces=('C',), spine_root=8, spine_tip=5),
                 dict(root_fill=23.0, land=3.0, braces=('C', 'D'), spine_root=8, spine_tip=5),
                 dict(root_fill=16.7, land=4.5, braces=(), spine_root=8, spine_tip=5)]
        for bi, b in enumerate(bases):
            for vr in [(), ('S',), ('S', 'F'), ('S', 'R'), ('S', 'F', 'R'), ('F',), ('R',)]:
                for hh in ((3.0, 4.0, 5.0) if vr else (4.0,)):
                    cands.append(dict(b, rim=2.5, end_edge=3.0, brace_w=2.5, inner_spine=4.0,
                                      v_ribs=vr, v_rib_h=hh, base=bi))
    elif stage == '4':
        b30 = dict(root_fill=30.25, land=3.0, braces=('C',), spine_root=8, spine_tip=5)
        b23 = dict(root_fill=23.0, land=3.0, braces=('C', 'D'), spine_root=8, spine_tip=5)
        for b, vrs in ((b30, [(), ('S', 'R'), ('S', 'R', 'M'), ('S', 'M', 'C'), ('S', 'R', 'M', 'C')]),
                       (b23, [('S', 'R', 'C'), ('S', 'R', 'M'), ('S', 'R', 'M', 'C')])):
            for vr in vrs:
                cands.append(dict(b, rim=2.5, end_edge=3.0, brace_w=2.5, inner_spine=4.0, v_ribs=vr, v_rib_h=3.0))
    elif stage == '5':
        for br, sp, vr, bw in itertools.product((('G',), ('G', 'H')), ((6, 4), (8, 5)),
                                                (('G',), ('G', 'S'), ('G', 'S', 'H'), ('G', 'S', 'R')), (2.5, 3.5)):
            if 'H' in vr and 'H' not in br:
                continue
            cands.append(dict(root_fill=16.7, land=3.0, braces=br, spine_root=sp[0], spine_tip=sp[1], rim=2.5,
                              end_edge=3.0, brace_w=bw, inner_spine=4.0, v_ribs=vr, v_rib_h=3.0))
    elif stage == '6':
        for rim, sp, bw, vr, hh in itertools.product((2.0, 2.5), ((4, 4), (6, 4)), (3.0, 3.5, 4.5),
                                                     (('G',), ('G', 'S')), (3.0, 4.0)):
            cands.append(dict(root_fill=16.7, land=3.0, braces=('G',), spine_root=sp[0], spine_tip=sp[1], rim=rim,
                              end_edge=3.0, brace_w=bw, inner_spine=4.0, v_ribs=vr, v_rib_h=hh))
    elif stage == '7':   # リブなし(2026-10-18 に決定)で、骨の組み合わせと幅を選び直す
        for br, sp, bw, rim, ee in itertools.product((('G',), ('G', 'H')), ((4, 4), (6, 4)), (3.0, 4.6),
                                                     (2.5, 3.5), (3.0, 4.0)):
            cands.append(dict(root_fill=16.7, land=3.0, braces=br, spine_root=sp[0], spine_tip=sp[1], rim=rim,
                              end_edge=ee, brace_w=bw, inner_spine=4.0, v_ribs=(), end_window_min=40.0, fillet=2.0))
    else:
        tops = json.loads(sys.argv[2])
        for br, rim, ee, sp, bw in itertools.product(tops, (2.5, 3.0, 3.5), (2.5, 3.5, 5.0),
                                                     ((6, 4), (8, 5), (12, 6), (16, 8)), (2.5, 3.5)):
            if not br and bw == 3.5:
                continue
            cands.append(dict(rim=rim, end_edge=ee, spine_root=sp[0], spine_tip=sp[1], braces=tuple(br), brace_w=bw))
    print(len(cands), 'candidates', flush=True)
    with Pool(4) as pool:
        out = pool.map(job, cands, chunksize=1)
    json.dump(out, open(f'stage{stage}.json', 'w'), ensure_ascii=False, indent=0)

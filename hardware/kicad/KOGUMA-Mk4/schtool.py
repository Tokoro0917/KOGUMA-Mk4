"""回路図(.kicad_sch)を読む小さな道具(2026-11-01): 記号のピンの位置と、線でつながったまとまり(シートの中だけ)
電源の記号(GND など)がどの部品のピンにつながっているかを調べ、PGND などに差し替えるのに使う"""
import re, math

def tokens(s):
    return re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+', s)

def parse(s):
    """S式 → 入れ子のリスト(文字列はそのまま、引用符つき)。位置(文字の範囲)も返す"""
    stack = [[]]; spans = [[0]]
    for m in re.finditer(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+', s):
        t = m.group(0)
        if t == '(':
            stack.append([]); spans.append([m.start()])
        elif t == ')':
            node = stack.pop(); st = spans.pop()[0]
            node = Node(node, st, m.end())
            stack[-1].append(node)
        else:
            stack[-1].append(t)
    return stack[0][0]

class Node(list):
    def __init__(self, items, start, end):
        super().__init__(items); self.start, self.end = start, end
    @property
    def tag(self):
        return self[0] if self else None
    def find(self, tag):
        return [c for c in self if isinstance(c, Node) and c.tag == tag]
    def one(self, tag):
        f = self.find(tag)
        return f[0] if f else None
    def prop(self, name):
        for p in self.find('property'):
            if p[1].strip('"') == name:
                return p[2].strip('"')

def lib_pins(root):
    """lib_symbols の中の記号ごとのピン: {lib_id: [(番号, x, y, unit)]}(ライブラリの座標、y は上が +)"""
    out = {}
    ls = root.one('lib_symbols')
    for sym in ls.find('symbol'):
        name = sym[1].strip('"'); pins = []
        for sub in [sym] + sym.find('symbol'):
            m = re.search(r'_(\d+)_(\d+)$', sub[1].strip('"')) if sub is not sym else None
            unit = int(m.group(1)) if m else 0
            for p in sub.find('pin'):
                at = p.one('at'); num = p.one('number')[1].strip('"')
                pins.append((num, float(at[1]), float(at[2]), unit))
        out[name] = pins
    return out

def place(x, y, sx, sy, rot, mirror):
    """ライブラリの座標 (x, y) → 回路図の座標(KiCad: y を反転、ミラー、回転の順)"""
    X, Y = x, -y
    if mirror == 'x':
        Y = -Y
    elif mirror == 'y':
        X = -X
    a = math.radians(rot)
    c, s = round(math.cos(a)), round(math.sin(a))
    return (round(sx + X * c + Y * s, 2), round(sy - X * s + Y * c, 2))

class Sheet:
    def __init__(self, path):
        self.path = path
        self.text = open(path).read()
        self.root = parse(self.text)
        self.lib = lib_pins(self.root)
        self.syms = []                                         # (ref, lib_id, value, node, {pin: (x, y)})
        for sym in self.root.find('symbol'):
            if not sym.one('lib_id'):
                continue
            lid = sym.one('lib_id')[1].strip('"'); at = sym.one('at')
            sx, sy, rot = float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0
            mir = sym.one('mirror'); mir = mir[1] if mir else None
            unit = int(sym.one('unit')[1]) if sym.one('unit') else 1
            pins = {}
            for num, x, y, u in self.lib.get(lid, []):
                if u in (0, unit):
                    pins[num] = place(x, y, sx, sy, rot, mir)
            self.syms.append((sym.prop('Reference'), lid, sym.prop('Value'), sym, pins))
        # 線でつながった点をまとめる
        self.parent = {}
        def find(p):
            while self.parent.setdefault(p, p) != p:
                self.parent[p] = self.parent[self.parent[p]]; p = self.parent[p]
            return p
        self._find = find
        def union(a, b):
            self.parent[find(a)] = find(b)
        segs = []
        for w in self.root.find('wire'):
            pts = [(round(float(q[1]), 2), round(float(q[2]), 2)) for q in w.one('pts').find('xy')]
            union(pts[0], pts[1]); segs.append(pts)
        # 線の途中に、ほかの線の端・ピン・ジャンクションが載っていたらつなぐ
        pts_all = set(p for s_ in segs for p in s_) | set(p for *_, pins in self.syms for p in pins.values())
        pts_all |= set((round(float(j.one('at')[1]), 2), round(float(j.one('at')[2]), 2)) for j in self.root.find('junction'))
        for (a, b) in segs:
            for p in pts_all:
                if p in (a, b):
                    continue
                if min(a[0], b[0]) - 1e-6 <= p[0] <= max(a[0], b[0]) + 1e-6 and min(a[1], b[1]) - 1e-6 <= p[1] <= max(a[1], b[1]) + 1e-6 \
                        and abs((b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])) < 1e-6:
                    union(p, a)
        # ラベル(シートの中は同じ名前でつながる)
        self.labels = []
        for kind in ('label', 'global_label', 'hierarchical_label'):
            for l in self.root.find(kind):
                at = l.one('at'); p = (round(float(at[1]), 2), round(float(at[2]), 2))
                self.labels.append((l[1].strip('"'), p)); find(p)
        by = {}
        for n, p in self.labels:
            by.setdefault(n, []).append(p)
        for ps_ in by.values():
            for p in ps_[1:]:
                union(ps_[0], p)

    def group(self, p):
        return self._find(p)

    def pin_point(self, ref, num):
        for r, lid, val, node, pins in self.syms:
            if r == ref and num in pins:
                return pins[num]

    def members(self):
        """まとまりごとに、つながっているピン [(ref, 番号, lib_id, value)]"""
        g = {}
        for r, lid, val, node, pins in self.syms:
            for num, p in pins.items():
                g.setdefault(self.group(p), []).append((r, num, lid, val))
        return g

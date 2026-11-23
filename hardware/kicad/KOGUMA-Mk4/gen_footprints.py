"""KOGUMA-Mk4.pretty の手で寸法を入れるフットプリントを作る(2026-10-31)
寸法はメーカーの図面の推奨ランド(下のそれぞれの descr)。原点は部品の真ん中。
使い方(このフォルダで): python3 gen_footprints.py"""
import os, uuid

U = lambda: str(uuid.uuid4())
f = lambda v: f'{v:.4f}'.rstrip('0').rstrip('.')

def text(kind, val, x, y, layer, hide=False):
    return f'''	(property "{kind}" "{val}"
		(at {f(x)} {f(y)} 0)
		(layer "{layer}")
{'		(hide yes)' + chr(10) if hide else ''}		(uuid "{U()}")
		(effects
			(font
				(size 1 1)
				(thickness 0.15)
			)
		)
	)
'''

def line(x0, y0, x1, y1, layer, w):
    return f'''	(fp_line
		(start {f(x0)} {f(y0)})
		(end {f(x1)} {f(y1)})
		(stroke
			(width {w})
			(type solid)
		)
		(layer "{layer}")
		(uuid "{U()}")
	)
'''

def poly(pts, layer, w):
    return ''.join(line(*pts[i], *pts[(i + 1) % len(pts)], layer, w) for i in range(len(pts)))

def rect(x0, y0, x1, y1, layer, w):
    return poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], layer, w)

def smd(num, x, y, w, h):
    return f'''	(pad "{num}" smd roundrect
		(at {f(x)} {f(y)})
		(size {f(w)} {f(h)})
		(layers "F.Cu" "F.Mask" "F.Paste")
		(roundrect_rratio 0.1)
		(uuid "{U()}")
	)
'''

def npth(x, y, d):
    return f'''	(pad "" np_thru_hole circle
		(at {f(x)} {f(y)})
		(size {f(d)} {f(d)})
		(drill {f(d)})
		(layers "*.Cu" "*.Mask")
		(uuid "{U()}")
	)
'''

def footprint(name, descr, tags, ref_y, val_y, body, attr='smd'):
    return f'''(footprint "{name}"
	(version 20241229)
	(generator "pcbnew")
	(generator_version "9.0")
	(layer "F.Cu")
	(descr "{descr}")
	(tags "{tags}")
{text('Reference', 'REF**', 0, ref_y, 'F.SilkS')}{text('Value', name, 0, val_y, 'F.Fab')}{text('Datasheet', '', 0, 0, 'F.Fab', True)}{text('Description', '', 0, 0, 'F.Fab', True)}	(attr {attr})
{body}	(embedded_fonts no)
)
'''

FP = {}

# ---- SW1 電源スイッチ: Alps Alpine SSSS810701(SSSS8、横に動かすスライド、1回路2接点)----
# 製品ページの Dimensions・Land Dimensions(tech.alpsalpine.com、SSSS810701)。
# 原点は位置決めの穴2つの真ん中。端子(1・2・3、2 が共通)は -y 側、つまみは +y 側に出る(基板の縁に向ける)。
# 端子: 1 は x −2.25、2 は +0.75、3 は +2.25(1 と 2 の間 3、2 と 3 の間 1.5、2 は真ん中から 0.75)。
# パッド 0.7 × 1.5、穴の線から 1〜2.5mm。穴 φ0.9 × 2(間 3)。本体 6.7 × 2.6(穴の線が本体の真ん中)、つまみ 1.3 幅・1.5 出る、動き 1.5
b = ''.join(smd(n, x, -1.75, 0.7, 1.5) for n, x in (('1', -2.25), ('2', 0.75), ('3', 2.25)))
b += npth(-1.5, 0, 0.9) + npth(1.5, 0, 0.9)
b += rect(-3.35, -1.3, 3.35, 1.3, 'F.Fab', 0.1) + rect(-0.65 - 0.75, 1.3, 0.65 - 0.75, 2.8, 'F.Fab', 0.1)   # つまみ(1 側に寄せた位置で描く)
b += line(-3.47, -0.6, -3.47, 1.42, 'F.SilkS', 0.12) + line(3.47, -0.6, 3.47, 1.42, 'F.SilkS', 0.12)
b += line(-3.47, 1.42, -1.5, 1.42, 'F.SilkS', 0.12) + line(-0.0, 1.42, 3.47, 1.42, 'F.SilkS', 0.12)
b += rect(-3.6, -2.75, 3.6, 4.4, 'F.CrtYd', 0.05)
FP['SW_Slide_SPDT_Alps_SSSS8'] = footprint(
    'SW_Slide_SPDT_Alps_SSSS8',
    'Alps Alpine SSSS8 (SSSS810701) SMD slide switch SPDT, 6.7x2.6x1.4mm, land pattern from the product page (Land Dimensions). '
    'Pads 1-2-3 (2 = common) on -y, actuator on +y (toward the board edge), 2 locating holes 0.9mm',
    'switch slide SPDT Alps SSSS8', -3.6, 3.6 + 1.5, b)

# ---- SW2 スイッチ: Zhejiang Jianfu TVAF06-A020B-R(2.9 × 3.9mm、上から押す)----
# 仕様書 2011101401 の P.C.B LAND DIMENSION: パッド 1.6 × 1.05(外 5.5、内 3.4)、穴 φ0.75 × 2(間 1.8)
b = smd('1', 0, -2.225, 1.6, 1.05) + smd('2', 0, 2.225, 1.6, 1.05)
b += npth(-0.9, 0, 0.75) + npth(0.9, 0, 0.75)
b += rect(-1.45, -1.95, 1.45, 1.95, 'F.Fab', 0.1)
b += line(-1.57, -1.4, -1.57, 1.4, 'F.SilkS', 0.12) + line(1.57, -1.4, 1.57, 1.4, 'F.SilkS', 0.12)
b += rect(-1.85, -3.0, 1.85, 3.0, 'F.CrtYd', 0.05)
FP['SW_Push_Jianfu_TVAF06'] = footprint(
    'SW_Push_Jianfu_TVAF06',
    'Zhejiang Jianfu TVAF06-A020B-R SMD tact switch 2.9x3.9mm, H2.0mm, land pattern from spec 2011101401 (P.C.B LAND DIMENSION): pads 1.6x1.05 at +-2.225, 2 holes 0.75mm',
    'switch tact push Jianfu TVAF06', -3.8, 3.8, b)

# ---- BZ1 ブザー: PUI Audio SMT-0540-S-R(5 × 5 × 2mm、横に音が出る)----
# データシートの Suggested Land Pattern: パッド 1.30 × 1.50、左の列は x −2.25〜−0.95、右は 1.25〜2.55、上の行は y −3.0〜−1.5、下は 1.5〜3.0。
# 上から見て、左上が +、左下が −、右上は電気的につながらない足(DUMMY LEAD)。音の出る穴は +x の面
b = smd('1', -1.6, -2.25, 1.3, 1.5) + smd('2', -1.6, 2.25, 1.3, 1.5) + smd('', 1.9, -2.25, 1.3, 1.5)
b += poly([(-2.5, -2.5), (2.5, -2.5), (2.5, 1.5), (1.5, 2.5), (-2.5, 2.5)], 'F.Fab', 0.1)
b += line(-0.7, -2.62, 1.0, -2.62, 'F.SilkS', 0.12) + line(-0.7, 2.62, 1.6, 2.62, 'F.SilkS', 0.12)
b += line(2.62, -1.25, 2.62, 1.55, 'F.SilkS', 0.12) + line(-2.62, -1.35, -2.62, 1.35, 'F.SilkS', 0.12)
b += line(-3.3, -2.25, -3.3, -1.6, 'F.SilkS', 0.12) + line(-3.6, -1.95, -3.0, -1.95, 'F.SilkS', 0.12)   # + の印
b += rect(-3.75, -3.25, 3.05, 3.25, 'F.CrtYd', 0.05)
FP['Buzzer_PUI_SMT-0540'] = footprint(
    'Buzzer_PUI_SMT-0540',
    'PUI Audio SMT-0540-S-R magnetic buzzer 5x5x2mm, side sound hole (+x), suggested land pattern from the datasheet: pads 1.30x1.50, 1 = +, 2 = -, unnumbered pad = dummy lead',
    'buzzer magnetic transducer PUI SMT-0540', -4.1, 4.1, b)

if __name__ == '__main__':
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'KOGUMA-Mk4.pretty')
    for n, s in FP.items():
        open(os.path.join(here, n + '.kicad_mod'), 'w').write(s)
        print(n)

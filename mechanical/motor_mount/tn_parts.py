"""ToraNeko.Mk3 の STEP から足回りの部品(片側)を取り出し、MK4 の座標(右側、y が負)に移して STEP にする。
MK4: x 前、y 左、z 上(床 = 0)。車軸 (0, y, 7.5)。
ToraNeko → MK4: x' = -(y + 5.32)、y' = x + 1.3、z' = z + 2.285(z 軸まわりに 90° 回す + 平行移動)"""
import sys, json
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.TDF import TDF_Label, TDF_ChildIterator
from OCP.TDataStd import TDataStd_Name
from OCP.TopLoc import TopLoc_Location
from OCP.gp import gp_Trsf, gp_Ax1, gp_Pnt, gp_Dir, gp_Vec
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
import cadquery as cq

doc = TDocStd_Document(TCollection_ExtendedString("doc"))
r = STEPCAFControl_Reader(); r.SetNameMode(True)
assert r.ReadFile(sys.argv[1]) == 1
r.Transfer(doc)
st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())

def name(lab):
    n = TDataStd_Name()
    return n.Get().ToExtString() if lab.FindAttribute(TDataStd_Name.GetID_s(), n) else '?'

T = gp_Trsf(); T.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), 3.141592653589793 / 2)
T2 = gp_Trsf(); T2.SetTranslation(gp_Vec(-5.32, 1.3, 2.285))
TT = T2.Multiplied(T)   # 先に回して、そのあと平行移動
# 回転 90°: (x, y) → (-y, x)。平行移動で x' = -y - 5.32、y' = x + 1.3
keep = ('ホイール', 'ミニッツタイヤ', 'Spur Gear (41', '3*6平行ピン', 'LF-630', '3mm磁石', 'エンコーダ基板', 'TSSOP')
out = {}
def walk(lab, loc, path):
    if st.IsAssembly_s(lab):
        it = TDF_ChildIterator(lab, False)
        while it.More():
            c = it.Value(); it.Next()
            if not st.IsComponent_s(c):
                continue
            ref = TDF_Label(); st.GetReferredShape_s(c, ref)
            walk(ref, loc.Multiplied(st.GetLocation_s(c)), path + [name(c)])
    else:
        p = '/'.join(path)
        if '足回り v20' not in p or 'ミラー' in p:
            return
        if not any(k in p for k in keep):
            return
        shp = st.GetShape_s(lab).Moved(loc)
        shp = BRepBuilderAPI_Transform(shp, TT, True).Shape()
        key = path[-1] if path else name(lab)
        out[p] = cq.Shape.cast(shp)

it = TDF_ChildIterator(st.Label(), False)
while it.More():
    l = it.Value(); it.Next()
    if st.IsFree_s(l) and st.IsShape_s(l):
        walk(l, TopLoc_Location(), [name(l)])
asm = cq.Assembly()
info = {}
for i, (p, s) in enumerate(out.items()):
    bb = s.BoundingBox()
    short = p.split('/')[2] if len(p.split('/')) > 2 else p
    info[f'{i:02d} {short}'] = [round(v, 2) for v in (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)]
    asm.add(s, name=f'p{i:02d}')
cq.exporters.export(cq.Compound.makeCompound(list(out.values())), 'tn_drive_mk4_right.step')
json.dump(info, open('tn_drive_mk4_right.json', 'w'), ensure_ascii=False, indent=1)
for k, v in info.items():
    print(k.ljust(40), v)

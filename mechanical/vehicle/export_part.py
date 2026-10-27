"""機体の STEP から部品を1つ取り出して、STEP と STL に書き出す(2026-10-27)
使い方: python3 export_part.py 機体.step 部品の名前 出力(拡張子なし)
例: python3 export_part.py mk4_vehicle_v4.step fan_case ../fan_mount/fan_mount_v1"""
import sys
import cadquery as cq
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.TDF import TDF_Label, TDF_ChildIterator
from OCP.TDataStd import TDataStd_Name
from OCP.TopLoc import TopLoc_Location

doc = TDocStd_Document(TCollection_ExtendedString('doc'))
r = STEPCAFControl_Reader(); r.SetNameMode(True)
assert r.ReadFile(sys.argv[1]) == 1
r.Transfer(doc)
st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())

def name(lab):
    n = TDataStd_Name()
    return n.Get().ToExtString() if lab.FindAttribute(TDataStd_Name.GetID_s(), n) else '?'

parts = {}
def walk(lab, loc, nm):
    if st.IsAssembly_s(lab):
        it = TDF_ChildIterator(lab, False)
        while it.More():
            c = it.Value(); it.Next()
            if not st.IsComponent_s(c):
                continue
            ref = TDF_Label(); st.GetReferredShape_s(c, ref)
            walk(ref, loc.Multiplied(st.GetLocation_s(c)), name(c))
    else:
        parts[nm] = cq.Shape.cast(st.GetShape_s(lab).Moved(loc))
it = TDF_ChildIterator(st.Label(), False)
while it.More():
    l = it.Value(); it.Next()
    if st.IsFree_s(l) and st.IsShape_s(l):
        walk(l, TopLoc_Location(), name(l))

s = parts[sys.argv[2]]
assert s.isValid()
cq.exporters.export(s, sys.argv[3] + '.step')
cq.exporters.export(s, sys.argv[3] + '.stl', tolerance=0.01, angularTolerance=0.1)
bb = s.BoundingBox()
print(f'{sys.argv[2]}: 体積 {s.Volume():.0f} mm³(樹脂 1.2 g/cm³ で {s.Volume() * 1.2e-3:.2f} g)、'
      f'外形 x {bb.xmin:.2f}〜{bb.xmax:.2f}、y {bb.ymin:.2f}〜{bb.ymax:.2f}、z {bb.zmin:.2f}〜{bb.zmax:.2f}')

"""ToraNeko.Mk3 のモーターマウント(モータマウント v26)を STEP から取り出し、形を調べる(2026-11-24、ユーザー「きちんと Mk3 のモーターマウントを確認しましたか?」)。
使い方: python3 tn_mount_extract.py <TORANEKO.Mk3_v36.step>  → tn_motor_mount_v26.step(ToraNeko の座標のまま)と、面の種類・肉の厚さの一覧
ToraNeko の座標: x が左右(外がマイナス、タイヤ -33)、y が前後、z が上。リポジトリは Tokoro0917/toraneko.mk3 の mechanical/exported/"""
import sys
from collections import Counter
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.TDF import TDF_Label, TDF_ChildIterator
from OCP.TDataStd import TDataStd_Name
from OCP.TopLoc import TopLoc_Location
import cadquery as cq

doc = TDocStd_Document(TCollection_ExtendedString("doc"))
reader = STEPCAFControl_Reader()
reader.SetNameMode(True)
assert reader.ReadFile(sys.argv[1]) == 1
reader.Transfer(doc)
tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())


def name(lab):
    n = TDataStd_Name()
    if lab.FindAttribute(TDataStd_Name.GetID_s(), n):
        return n.Get().ToExtString()
    return '?'


found = {}


def walk(lab, loc, path):
    """組み立ての木をたどり、足回りのモーターマウント(ミラーでない方)を探す"""
    if tool.IsAssembly_s(lab):
        it = TDF_ChildIterator(lab, False)
        while it.More():
            c = it.Value()
            it.Next()
            if not tool.IsComponent_s(c):
                continue
            ref = TDF_Label()
            tool.GetReferredShape_s(c, ref)
            walk(ref, loc.Multiplied(tool.GetLocation_s(c)), path + [name(c)])
    else:
        p = '/'.join(path)
        if '足回り' in p and 'モータマウント' in p and 'ミラー' not in p:
            found[p] = cq.Shape.cast(tool.GetShape_s(lab).Moved(loc))


it = TDF_ChildIterator(tool.Label(), False)
while it.More():
    lab = it.Value()
    it.Next()
    if tool.IsFree_s(lab) and tool.IsShape_s(lab):
        walk(lab, TopLoc_Location(), [name(lab)])
for p, s in found.items():
    bb = s.BoundingBox()
    print(p, f'体積 {s.Volume():.1f} mm³(樹脂 1.2 g/cm³ で {s.Volume() * 1.2e-3:.2f} g)')
    print('  外形', [round(v, 2) for v in (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)])
    print('  面の種類', dict(Counter(f.geomType() for f in s.Faces())))
    print('  辺の種類', dict(Counter(e.geomType() for e in s.Edges())))
    cq.exporters.export(s, 'tn_motor_mount_v26.step')
    cq.exporters.export(s, 'tn_motor_mount_v26.stl')

"""機体の STEP から吸引ファンのまわりの部品を取り出して、基板と電池を外した図を作る
使い方: python3 fan_view.py mk4_vehicle_v3.step 出力.png"""
import sys
import numpy as np
import cadquery as cq
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.TDF import TDF_Label, TDF_ChildIterator
from OCP.TDataStd import TDataStd_Name
from OCP.TopLoc import TopLoc_Location
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

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

KEEP = ('frame', 'pc_sheet', 'fan_case', 'impeller', 'fan_motor', 'fan_shaft', 'screw_fanframe', 'nut_fanframe',
        'screw_fanclamp', 'nut_fanclamp', 'motor_', 'mount_', 'skirt')
COL = {'frame': (0.25, 0.24, 0.22), 'pc_sheet': (0.62, 0.79, 0.88), 'fan_case': (0.95, 0.56, 0.17), 'impeller': (0.95, 0.85, 0.3),
       'fan_motor': (0.65, 0.65, 0.68), 'fan_shaft': (0.3, 0.3, 0.32), 'screw_fanframe': (0.3, 0.3, 0.32),
       'nut_fanframe': (0.95, 0.95, 0.9), 'screw_fanclamp': (0.95, 0.95, 0.9), 'nut_fanclamp': (0.95, 0.95, 0.9),
       'motor_': (0.65, 0.65, 0.68), 'mount_': (0.95, 0.56, 0.17), 'skirt': (0.9, 0.9, 0.6)}
box = cq.Solid.makeBox(48, 50, 40, pnt=cq.Vector(-8, -25, -1))
T, C = [], []
for nm, s in parts.items():
    key = next((k for k in KEEP if nm.startswith(k)), None)
    if key is None:
        continue
    if nm in ('frame', 'pc_sheet', 'skirt'):
        s = s.intersect(box)
    v, t = s.tessellate(0.05, 0.3)
    if not len(t):
        continue
    v = np.array([(p.x, p.y, p.z) for p in v])
    T.append(v[np.array(t)])
    a = 0.4 if nm in ('pc_sheet', 'skirt') else 1.0
    C.append(np.tile(list(COL[key]) + [a], (len(t), 1)))
T = np.concatenate(T); C = np.concatenate(C)
fig = plt.figure(figsize=(16, 7.5))
for k, (elev, azim, title) in enumerate(((35, -60, 'fan unit (PCB and battery removed), from front-left'),
                                        (35, 120, 'from rear-left'))):
    ax = fig.add_subplot(1, 2, k + 1, projection='3d')
    ax.add_collection3d(Poly3DCollection(T, facecolors=C, linewidths=0, shade=True))
    ax.set_xlim(-8, 40); ax.set_ylim(-25, 25); ax.set_zlim(0, 30)
    ax.set_box_aspect((48, 50, 30), zoom=1.1); ax.view_init(elev, azim); ax.set_axis_off(); ax.set_title(title, fontsize=10)
fig.tight_layout(); fig.savefig(sys.argv[2], dpi=110)

# 上から見た断面(z = 6、渦巻きの中が見える)
fig, ax = plt.subplots(figsize=(8, 8))
cut = cq.Solid.makeBox(60, 60, 0.3, pnt=cq.Vector(-10, -30, 5.85))
for nm, col in (('frame', '#5f5a50'), ('fan_case', '#f28e2b'), ('impeller', '#e8c84a')):
    s = parts[nm].intersect(cut) if nm != 'frame' else parts[nm].intersect(cq.Solid.makeBox(60, 60, 0.3, pnt=cq.Vector(-10, -30, 2.35)))
    v, t = s.tessellate(0.03, 0.2)
    if not len(t):
        continue
    v = np.array([(p.x, p.y) for p in v])
    for tri in np.array(t):
        ax.fill(*v[tri].T, color=col, lw=0)
for nm in ('screw_fanframe_0', 'screw_fanframe_1', 'screw_fanframe_2', 'fan_motor'):
    bb = parts[nm].BoundingBox()
    ax.add_patch(plt.Circle(((bb.xmin + bb.xmax) / 2, (bb.ymin + bb.ymax) / 2), (bb.xmax - bb.xmin) / 2, fill=False, ec='k', lw=1, ls='--'))
ax.annotate('outlet', (26.3, 15.5), (30, 22), arrowprops=dict(arrowstyle='->'))
ax.set_aspect('equal'); ax.set_xlim(-5, 38); ax.set_ylim(-22, 24); ax.grid(alpha=.3)
ax.set_title('section at z = 6 mm: volute (orange), impeller (yellow), frame (gray); dashed = screws, fan motor')
fig.tight_layout(); fig.savefig(sys.argv[2].replace('.png', '_section.png'), dpi=100)

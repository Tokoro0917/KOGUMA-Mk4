"""ToraNeko.Mk3 のホイールを MK4 の位置(右側、車軸 (0, y, 7.5))のまま取り出し、右・左の STEP・STL にする(2026-10-30)
使い方(リポジトリの一番上で): python3 mechanical/wheel/export_wheel.py
元は mechanical/motor_mount/tn_drive_mk4_right.step(tn_parts.py で ToraNeko.Mk3 の STEP から作ったもの)の 0 番目の部品"""
import cadquery as cq

s = cq.importers.importStep('mechanical/motor_mount/tn_drive_mk4_right.step').val().Solids()[0]
bb = s.BoundingBox()
assert abs(bb.xmax - 5.75) < 0.01 and abs(bb.ymin + 31.8) < 0.01, 'ホイールでない部品を取った'
for side, part in (('R', s), ('L', s.mirror('XZ'))):
    cq.exporters.export(part, f'mechanical/wheel/wheel_{side}_v1.step')
    cq.exporters.export(part, f'mechanical/wheel/wheel_{side}_v1.stl', tolerance=0.005, angularTolerance=0.05)
print(f'体積 {s.Volume():.0f} mm³(樹脂 1.2 g/cm³ で {s.Volume() * 1.2e-3:.2f} g)、外径 φ{bb.xmax - bb.xmin:.2f}、幅 {bb.ymax - bb.ymin:.2f}mm')

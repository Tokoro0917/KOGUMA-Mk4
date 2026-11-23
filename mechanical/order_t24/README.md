# タイヤ24mm の機体の注文する部品(Fusion で確かめる用、2026-11-23)

ブランチ `claude/trusting-dirac-1tdt54`。`../vehicle/export_t24_parts.py` が機体のモデル `../vehicle/mk4_vehicle_t24.step`(59.97g、ぶつかりなし。2026-11-23 に吸引する面を広げ、フレームを削って作り直した)から1つずつ書き出す。

**座標は機体と同じ**(原点は車軸の真ん中、+x が前、+y が左、z は床から上、単位 mm)。Fusion で全部を原点に挿入すると、組み上がった位置に並ぶ。印刷する部品は STL も(JLC3DP に出す用。向きは JLC3DP の画面で決める)。

| ファイル | 部品 | 注文先・材料 | 数 | 注文に出すファイル |
|---|---|---|---|---|
| `01_frame_t24v8.step` | フレーム **t24v8**(1mm、**吸引する面 80 × 42.6mm**、骨 1.6mm・前の辺 2.5mm、吸引する面の中に斜めの骨、窓の角の丸み 1.5mm、ねじ (6.8, ±18.4)・(−21, ±17.7)、5.02g。2026-11-23) | カーボンラボ.jp、カーボン 1mm | 2(予備1) | `../frame/MK4FRAMET24V8_T1.dxf` |
| `02_pc_sheet_t24v8.step` | 塩ビのシート(0.2mm、フレームの上、0.79g) | 自分で切る(型紙) | 1 | `../frame/MK4PCT24V8_T02.dxf`、型紙 `MK4PCT24V8_template_A4_1to1.pdf` |
| `03_motor_mount_R_t24v4.step` | モーターマウント 右 **t24v4**(1.14g。ねじ (6.8, −18.4)・(−21, −17.7)、柱 半径 2.0) | JLC3DP、Temp Resin | 3 | `03_motor_mount_R_t24v4.stl`(= `../motor_mount/motor_mount_R_t24v4.stl`) |
| `04_motor_mount_L_t24v4.step` | モーターマウント 左 | JLC3DP、Temp Resin | 3 | `04_motor_mount_L_t24v4.stl` |
| `05_fan_mount_t24v2.step` | **ファンの台 t24v2**(1.60g、継ぎ目 (14, ±20.3)。main の v1 は (14, ±22) なので使えない。t24v2 は吸引する面が広がり、輪の下をシートの上 z 3.2 に) | JLC3DP、Temp Resin | 3 | `05_fan_mount_t24v2.stl` |
| `06_wheel_R_t24v1.step` | ホイール 右(φ20 × 8.5mm、0.75g) | JLC3DP、Black Resin | 3 | `06_wheel_R_t24v1.stl`。**タイヤの内径・幅と 71T の穴を測ってから** |
| `07_wheel_L_t24v1.step` | ホイール 左 | JLC3DP、Black Resin | 3 | `07_wheel_L_t24v1.stl` |
| `08_sensor_holder_v5.step` | 壁センサのホルダ v5(FL の位置) | JLC3DP、Black Resin | 6(4 + 予備2) | `08_sensor_holder_v5.stl`(= `../sensor_holder/sensor_holder_v5.stl`) |
| `09_main_pcb_t24v5.step` | メイン基板 t24v5(外形と厚さ 0.6mm だけ。ねじの穴が新しい位置) | JLCPCB(配線のあと) | — | 確かめる用 |
| `10_encoder_board_R_t24.step` | エンコーダ基板 右(6.0 × 8.75 × 0.6mm、左は y を反転) | JLCPCB(配線のあと) | — | 確かめる用 |
| `11_purchased_and_other_parts.step` | 買う部品・ほか(モーター・タイヤ・71T・ピニオン・軸受・平行ピン・磁石・ねじ・電池・ファンのモーターと羽根・壁センサとほかの3つのホルダ・MT6835・滑り板・スカート) | — | — | ぶつかりを見る用 |

- ねじは M2 低頭 L5 × 10 本(マウント (6.8, ±18.4)・(−21, ±17.7) に、フレームの下から4本・基板の上から4本、ファンの台の継ぎ目 (14, ±20.3) に2本)
- JLC3DP は M6 未満のねじ山を作らないので、M2 は届いてから自分でタップを立てる(下穴 φ1.6)
- 電池のホルダは使わない(電池の底を両面テープで基板に貼る)

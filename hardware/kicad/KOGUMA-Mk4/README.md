# KOGUMA-Mk4 の KiCad プロジェクト

KiCad 9.0 で開く(`KOGUMA-Mk4.kicad_pro`)。

| ファイル | 中身 |
|---|---|
| `KOGUMA-Mk4.kicad_sch` | 一番上のシート。下のシートを並べる |
| `power.kicad_sch` | 電源(電池 → 電源スイッチ → VBAT → 3.3V、電池の電圧の分圧) |
| `motor.kicad_sch` | モーター(MP6551 × 2、CM の分圧とコンデンサ)と吸引ファン(IRLML6344、0.1Ω のシャント) |
| `sensor.kicad_sch` | センサ(A3): 壁センサの発光 4ch(OPV332 + NJU6080)、受光 4ch(SFH 229 FA + OPA2354、820kΩ ∥ 0.5pF)、PD_BIAS、IMU(LSM6DSR)、エンコーダの基板(MT6835)とのつなぎ(J5・J6、メイン基板の穴とパッド7つ) |
| `ui.kicad_sch` | 表示・入力・通信: LED 7個と前の LED(D98、PB3)、ブザー、スイッチ、デバッグの端子(J7、ToraNeko.Mk3 の J6 と同じ並び)、UART_RX のテストパッド |
| `mcu.kicad_sch` | MCU(STM32H725RGVx)、SMPS(Direct SMPS)、発振子(10MHz、CSTNE10M0G52Z000R0)、パスコン、BOOT0・NRST。ピンは `docs/pinmap.md` のネット名のグローバルラベルでほかのシートとつなぐ |
| `KOGUMA-Mk4.kicad_sym` | このプロジェクト用の記号: AO4407A、LXDC55FAAA-203、MP6551GQB、IRLML6344、NJU6080、OPA2354、LSM6DSR(標準の LSM6DS3 を写し、SDX を passive に)、STM32H725RGVx(標準の記号を写し、VLXSMPS を power_out、VCAP の49・66番を passive に直した)、片方向のTVS(D_TVS_Uni)、電源記号 VBAT |
| `KOGUMA-Mk4.pretty/` | このプロジェクト用のフットプリント: LXDC55FAAA-203(村田のデータシートの「Reference Land Pattern」)、MPS_QFN-14_2.5x3mm(MP6551 のデータシートの「Recommended Land Pattern」)、Resonator_Murata_CSTNE-3Pin_3.2x1.3mm(村田の仕様書 JGC42-8974A の推奨ランド)、ENC_Base_Slot(エンコーダの基板を通す穴 NPTH 1.0 × 5.9mm と、上の面のパッド7つ。左の J5 は回転 0°、右の J6 は 180°)、WallSensor_Holder_Emitter・WallSensor_Holder_Receiver(壁センサのホルダの発光・受光の足の穴。Emitter にホルダのほぞの穴(Edge.Cuts)を含む。原点はホルダの前の面の真ん中、光は +X。ホルダは基板の裏に付けるので、同じセンサの2つを**裏の面に**、同じ位置・同じ向きに置く。位置は `mechanical/vehicle/pcb_shape.py` の `SENS`) |
| `sym-lib-table`・`fp-lib-table` | 上の2つをプロジェクトのライブラリとして登録する |

## ネットの名前

| ネット | 中身 |
|---|---|
| `BAT+` | 電池の+(電源スイッチの前。電源のシートの中だけ) |
| `VBAT` | 電源スイッチのあと。MP6551・LXDC55 の入力 |
| `+3V3` | LXDC55 の出力 |
| `BATT` | 電池の電圧の分圧(MCU の PB1、ADC2_INP5 へ)。グローバルラベル |
| `MOT_L_IN1`・`MOT_L_IN2`・`MOT_R_IN1`・`MOT_R_IN2` | MP6551 の IN(TIM1 の CH1〜CH4) |
| `MOT_EN` | 2個の MP6551 の EN1・EN2(共通) |
| `MOT_nFAULT` | 2個の nFAULT(オープンドレインを共通に、10kΩ で 3.3V へ) |
| `MOT_L_CM1`・`MOT_L_CM2`・`MOT_R_CM1`・`MOT_R_CM2` | CM の電圧(ADC2) |
| `FAN_PWM`・`FAN_ISENSE` | ファンの PWM(TIM16)と電流(ADC1) |
| `WALL_FL`・`WALL_L`・`WALL_R`・`WALL_FR` | 壁センサの受光のアンプの出力(ADC1) |
| `WALL_LED_FL_R`・`WALL_LED_L_FR` | 壁センサの発光(対角の2個ずつ。MK3 の WallLED_12 / WallLED_34) |
| `IMU_*`・`ENC_*` | IMU(SPI3)とエンコーダ(SPI2) |
| `ENC_CAL` | 2個の MT6835 の CAL_EN(左右共通、PC15)。校正のときだけ H |

## まだ決めていないこと

- SW1(SSSS810701)と J1(BT2.0 のケーブルをはんだ付けするパッド)のフットプリント。J1 は仮に `Connector_Wire:SolderWire-0.5sqmm_1x02_P4.8mm_D0.9mm_OD2.3mm`
- C4(ポリマー 47µF 25V)の品番と大きさ。仮に 7343
- LXDC55 のフットプリントは、データシートのランドパターンの寸法から作った。基板を注文する前に、実物か村田の最新の資料で確かめる
- **MP6551 のフットプリント(MPS_QFN-14_2.5x3mm)は寸法の読み取りに自信がない**。データシートの図の「2.80」を上下の小さいパッドの中心の間、「1.20」を長いパッドの長さ、「1.30」を中心から長いパッドの外の端までと読んだ(パッケージの足の位置とつじつまが合う読み方)。長いパッドの幅は 0.25mm と仮定。基板を注文する前に、印刷した図に実物を重ねるなどして確かめる
- モーター・ファンの線のパッド(J2〜J4)、ファンの還流ダイオード(D40)の品番、R41(ゲートの直列抵抗)の値
- SW2(TVAF06-A020B-R)・BZ1(SMT-0540-S-R)のフットプリントと、LED の品番
- MCU のフットプリントは標準の `Package_DFN_QFN:QFN-68-1EP_8x8mm_P0.4mm_EP6.4x6.4mm`(KiCad の記号の既定)。ST のデータシートの図75と見比べる

## 確かめたこと(2026-10-29、kicad-cli 9.0.9)

- ERC: エラー 0。警告は、確かめた環境に KiCad の標準ライブラリ(Device など)が登録されていないことによるものだけ
- ネットリストで、全部のピンが意図したネットにつながっていることを確かめた(つないでいないのは SW1 の3番、LXDC55 の NC と PG だけ)
- 全シート(電源・モーター・MCU・センサ・表示と通信、同日): ERC のエラー 0、ラベルの相手がいない警告も 0(残る警告は確かめた環境に標準ライブラリがないことによるものだけ)。MCU のピン43本(発振子の2本を含む。2026-10-29 に ENC_CAL を足して44本)が `docs/pinmap.md` のネット名と一致することをネットリストで確かめた
- IMU の割り込み(2026-10-31): LSM6DSR の INT1 を MCU の PD2 へ(グローバルラベル `IMU_INT`)。全シートの ERC エラー 0・警告 0(標準ライブラリがないことによるものを除く)、ネットリストで U4 の 57番(PD2)と U76 の 4番(INT1)がつながることを確かめた。`docs/calc/check_pins.py` で OK(使う45本、残り1本 PB3)
- エンコーダの基板(2026-10-29): `../KOGUMA-Mk4_Encoder/` の ERC エラー 0、DRC エラー 0、回路図と基板の食い違い 0。メイン基板の ENC_CAL を PC15 に足し、`docs/calc/check_pins.py` で OK(使う44本、残り2本)

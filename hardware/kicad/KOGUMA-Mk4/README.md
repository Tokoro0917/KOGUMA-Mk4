# KOGUMA-Mk4 の KiCad プロジェクト

KiCad 9.0 で開く(`KOGUMA-Mk4.kicad_pro`)。

| ファイル | 中身 |
|---|---|
| `KOGUMA-Mk4.kicad_sch` | 一番上のシート。下のシートを並べる |
| `power.kicad_sch` | 電源(電池 → 電源スイッチ → VBAT → 3.3V、電池の電圧の分圧) |
| `motor.kicad_sch` | モーター(MP6551 × 2、CM の分圧とコンデンサ)と吸引ファン(IRLML6344、0.1Ω のシャント) |
| `mcu.kicad_sch` | MCU(STM32H725RGVx)、SMPS(Direct SMPS)、発振子(10MHz、CSTNE10M0G52Z000R0)、パスコン、BOOT0・NRST。ピンは `docs/pinmap.md` のネット名のグローバルラベルでほかのシートとつなぐ |
| `KOGUMA-Mk4.kicad_sym` | このプロジェクト用の記号: AO4407A、LXDC55FAAA-203、MP6551GQB、IRLML6344、STM32H725RGVx(標準の記号を写し、VLXSMPS を power_out、VCAP の49・66番を passive に直した)、片方向のTVS(D_TVS_Uni)、電源記号 VBAT |
| `KOGUMA-Mk4.pretty/` | このプロジェクト用のフットプリント: LXDC55FAAA-203(村田のデータシートの「Reference Land Pattern」)、MPS_QFN-14_2.5x3mm(MP6551 のデータシートの「Recommended Land Pattern」)、Resonator_Murata_CSTNE-3Pin_3.2x1.3mm(村田の仕様書 JGC42-8974A の推奨ランド) |
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

## まだ決めていないこと

- SW1(SSSS810701)と J1(BT2.0 のケーブルをはんだ付けするパッド)のフットプリント。J1 は仮に `Connector_Wire:SolderWire-0.5sqmm_1x02_P4.8mm_D0.9mm_OD2.3mm`
- C4(ポリマー 47µF 25V)の品番と大きさ。仮に 7343
- LXDC55 のフットプリントは、データシートのランドパターンの寸法から作った。基板を注文する前に、実物か村田の最新の資料で確かめる
- **MP6551 のフットプリント(MPS_QFN-14_2.5x3mm)は寸法の読み取りに自信がない**。データシートの図の「2.80」を上下の小さいパッドの中心の間、「1.20」を長いパッドの長さ、「1.30」を中心から長いパッドの外の端までと読んだ(パッケージの足の位置とつじつまが合う読み方)。長いパッドの幅は 0.25mm と仮定。基板を注文する前に、印刷した図に実物を重ねるなどして確かめる
- モーター・ファンの線のパッド(J2〜J4)、ファンの還流ダイオード(D40)の品番、R41(ゲートの直列抵抗)の値
- センサ・表示・通信のシートがまだないので、ERC に壁センサ・エンコーダ・IMU・LED・スイッチ・ブザー・UART・SWD のラベルの相手がいない警告が出る
- MCU のフットプリントは標準の `Package_DFN_QFN:QFN-68-1EP_8x8mm_P0.4mm_EP6.4x6.4mm`(KiCad の記号の既定)。ST のデータシートの図75と見比べる

## 確かめたこと(2026-10-29、kicad-cli 9.0.9)

- ERC: エラー 0。警告は、確かめた環境に KiCad の標準ライブラリ(Device など)が登録されていないことによるものだけ
- ネットリストで、全部のピンが意図したネットにつながっていることを確かめた(つないでいないのは SW1 の3番、LXDC55 の NC と PG だけ)
- モーター・MCU のシート(同日): ERC のエラーは 0。MCU のピン43本(発振子の2本を含む)が `docs/pinmap.md` のネット名と一致することをネットリストで確かめた

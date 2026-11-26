# 参考資料

| ファイル | 中身 |
|---|---|
| `KOGUMA-CHAN.MkII_v2.pdf` | MK3(KOGUMA MkIIl)の回路図(KiCad、A3、1枚)。MK4 の資料で「MK3 と同じ」と書いた回路(壁センサ、電源スイッチ、ファン、LED、ブザー、スイッチ、発振子など)の元 |

## `datasheets/`(2026-11-23)

部品のデータシート。メーカーのサイトは自動の取得を受け付けないことが多いので、取れたものをここに残す。

| ファイル | 部品 |
|---|---|
| `MP6551_MPS.pdf` | MPS MP6551(モータードライバ、Rev.1.0) |
| `STM32H725_DS13311.pdf` | ST STM32H725xE/G(MCU、DS13311) |
| `LXDC55FAAA_Murata.pdf` | 村田 LXDC55FAAA-203(3.3V の DC-DC) |
| `CSTNE10M0G52Z000R0_Murata.pdf` | 村田 CSTNE10M0G52Z000R0(発振子、JGC42-8974A。推奨ランドはこれを見る) |
| `CSTNE10M0G52A000R0_Murata.pdf` | 村田 CSTNE10M0G52A000R0(発振子、LCSC C907976 の資料。車載用、仕様は Z と同じ: 10.000MHz、±0.50%、−40〜125°C、温度で ±0.20%、経年 ±0.10%、40Ω 以下、10pF、3.2 × 1.3mm)。2026-11-26 に Y1 をこれに替えた |
| `RLM12_TA-I.pdf` | TA-I RLM12 シリーズ(TRLM-120S032E。モーターの電流のシャント R22・R32 の RLM12FTCMR005、LCSC C316225)。金属板、1W、±50ppm/°C、−55〜170°C、AEC-Q200、3.2 × 1.6 × 0.6±0.2mm。2026-11-26 に PMR18EZPFU5L00 から替えた |
| `TS-1088-AR_XUNPU.pdf` | XUNPU TS-1088-AR シリーズ(タクトスイッチ SW2 の TS-1088-AR02016、LCSC C720477)。3.0 × 3.9mm(つめを入れて 5.0)、高さ 2.0mm、160gf、DC 12V 50mA、位置決めの足なし。推奨ランド 2.00 × 1.05mm を外 5.50・内 3.40mm。2026-11-26 に TVAF06-A020B-R から替えた |
| `MT6835_Rev1.3.pdf` | MagnTek MT6835(エンコーダ) |
| `NJU6080.pdf` | 日清紡 NJU6080(壁センサの発光の定電流ドライバ。在庫がないので 2026-11-26 に NJW4615A へ替えた) |
| `NJW4615A_Nisshinbo.pdf` | 日清紡 NJW4615A(壁センサの発光の定電流ドライバ。NJU6080 と同じピン、VDD 2.5〜35V、±1.2%、PWM で点くまで 3µs。2026-11-26) |
| `HY0020_FDK_Ver3.0.pdf` | FDK HY0020(BLE モジュール) |
| `INA241A_TI_SBOSA30D.pdf` | TI INA241A(モーターの電流センスアンプ) |
| `DFE201610E_Murata_JETE243A.pdf` | 村田 DFE201610E(SMPS のインダクタ L1、2.2µH)。ユーザーから(2026-11-23) |
| `SMF_Littelfuse.pdf` | Littelfuse SMF シリーズ(VBAT の TVS D1、SMF13A)。ユーザーから(2026-11-23) |
| `IRLML6344_Infineon.pdf` | Infineon IRLML6344(ファンの MOSFET Q40)。ユーザーから(2026-11-23) |
| `LSM6DSR_ST.pdf` | ST LSM6DSR(IMU)。ユーザーから(2026-11-23) |
| `OPA2354_TI_ja.pdf` | TI OPAx354(受光アンプ、日本語版 Rev.H)。ユーザーから(2026-11-23) |
| `AN5419_STM32H72x_hardware.pdf` | ST AN5419(STM32H72x/73x のハードウェアの始め方。電源のコンデンサ)。ユーザーから(2026-11-23) |
| `AN2606_STM32_bootloader.pdf` | ST AN2606(STM32 の書き込み用のプログラム。H72x は USART1 が PA9・PA10 だけ)。ユーザーから(2026-11-23) |

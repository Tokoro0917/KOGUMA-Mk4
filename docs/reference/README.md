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
| `CSTNE10M0G52Z000R0_Murata.pdf` | 村田 CSTNE10M0G52Z000R0(発振子、JGC42-8974A) |
| `MT6835_Rev1.3.pdf` | MagnTek MT6835(エンコーダ) |
| `NJU6080.pdf` | 日清紡 NJU6080(壁センサの発光の定電流ドライバ) |
| `HY0020_FDK_Ver3.0.pdf` | FDK HY0020(BLE モジュール) |
| `INA241A_TI_SBOSA30D.pdf` | TI INA241A(モーターの電流センスアンプ) |
| `DFE201610E_Murata_JETE243A.pdf` | 村田 DFE201610E(SMPS のインダクタ L1、2.2µH)。ユーザーから(2026-11-23) |
| `SMF_Littelfuse.pdf` | Littelfuse SMF シリーズ(VBAT の TVS D1、SMF13A)。ユーザーから(2026-11-23) |
| `IRLML6344_Infineon.pdf` | Infineon IRLML6344(ファンの MOSFET Q40)。ユーザーから(2026-11-23) |
| `LSM6DSR_ST.pdf` | ST LSM6DSR(IMU)。ユーザーから(2026-11-23) |
| `OPA2354_TI_ja.pdf` | TI OPAx354(受光アンプ、日本語版 Rev.H)。ユーザーから(2026-11-23) |
| `AN5419_STM32H72x_hardware.pdf` | ST AN5419(STM32H72x/73x のハードウェアの始め方。電源のコンデンサ)。ユーザーから(2026-11-23) |
| `AN2606_STM32_bootloader.pdf` | ST AN2606(STM32 の書き込み用のプログラム。H72x は USART1 が PA9・PA10 だけ)。ユーザーから(2026-11-23) |
| `OPV332_TT.pdf` | TT Electronics OPV332(壁センサの発光、VCSEL、Rev D)。足の間隔 約 1.0〜1.5mm、連続 12mA まで。ユーザーから(2026-11-23、ブランチ `claude/trusting-dirac-1tdt54`、`docs/bom_t24.md`) |
| `SFH229FA_ams-OSRAM.pdf` | ams OSRAM SFH 229 FA(壁センサの受光、Version 1.6)。**2025-11-28 に生産終了**。ユーザーから(2026-11-23) |
| `APTD1608LSECK-J4-PF_Kingbright.pdf` | Kingbright APTD1608LSECK/J4-PF(LED、1608、高さ 0.95mm、1番がカソード)。ユーザーから(2026-11-23) |
| `SMT-0540-S-R_PUI.pdf` | PUI Audio SMT-0540-S-R(ブザー、推奨ランド)。ユーザーから(2026-11-23) |
| `TVAF06-A020B-R_Jianfu.pdf` | Jianfu TVAF06-A020B-R(タクトスイッチ、仕様書 2011101401)。ユーザーから(2026-11-23) |
| `SSSS8_Alps.pdf` | Alps Alpine SSSS8 シリーズ(電源スイッチ SSSS810701 は図番 3。定格 0.3A 5V DC)。ユーザーから(2026-11-23) |
| `GRM219R61E106KA12_Murata.pdf` | 村田 GRM219R61E106KA12(10µF 25V 0805、厚さ 0.85±0.1mm)。ユーザーから(2026-11-23) |
| `AO4407A_AOS.pdf` | AOS AO4407A(電源スイッチの MOSFET Q1、Rev 11.1。SOA で電源を入れた瞬間を確かめた)。ユーザーから(2026-11-23) |
| `T52x_KEMET_T2076.pdf` | KEMET T52x(ポリマータンタル、T521V476M025ATE040 は V ケース 1.9±0.1mm、ESR 40mΩ)。ユーザーから(2026-11-23) |
| `PMR18_ROHM_ja.pdf` | ROHM PMR18EZP(モーターの電流のシャント 5mΩ、1W は端子 80°C まで、厚さ 0.42±0.15mm)。ユーザーから(2026-11-23) |
| `MBR230LSFT1_onsemi.pdf` | onsemi MBR230LSFT1G(ファンの還流ダイオード D40、推奨パッド)。ユーザーから(2026-11-23) |
| `BLM18PG_Murata_ENFA0003.pdf` | 村田 BLM18 シリーズ(フェライトビーズ FB1・FB2、BLM18PG221SN1D)。ユーザーから(2026-11-23) |

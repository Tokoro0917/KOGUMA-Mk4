# メイン基板 t24 の部品表(タイヤ24mm、2026-11-23)

ブランチ `claude/trusting-dirac-1tdt54` のメイン基板 `hardware/kicad/KOGUMA-Mk4_t24` の部品。回路と、決めた理由は `docs/bom.md`(main と同じ回路)。ここは t24 で**大きさを変えたもの**と、**受動部品の品番**(JLCPCB・LCSC で買える品)を決めたもの。

- 作り方: `/usr/bin/python3.12 hardware/kicad/bom_t24.py` → この下の「部品の一覧」と、JLCPCB に出す BOM `hardware/kicad/KOGUMA-Mk4_t24/bom_t24.csv`(Comment, Designator, Footprint, LCSC Part #。線のパッド・壁センサ・テストパッドは入れない)
- 品番は (値, フットプリント) で引く。**LCSC の番号・定格・パッケージは LCSC の製品ページ、コンデンサの厚さは Samsung の製品ページで確かめた**(2026-11-23)。在庫は注文のときに JLCPCB の BOM ツールで確かめる。IC など品番が前から決まっている部品の LCSC の番号はまだ入れていない
- **高さ**: 電池の下(上の面、x −16.25〜6.25、y ±16)は 1.2mm まで。電池の下に入る IC はデータシートで確かめた: STM32H725(VFQFPN68)最大 1.00、MP6551 最大 1.00、CSTNE 0.90±0.10、LSM6DSR 最大 0.86、DFE201610E 1.0
- 層: **2層・0.6mm**(JLCPCB は 4層を 0.6mm で作らない。2026-11-23)。配線はユーザーがする

## t24 で替えたもの

- **0603 のコンデンサ・抵抗は 1005 に**(2026-11-23、ユーザーの決定)。**3.3V にかかる 10µF・4.7µF(C50・C51・C62・C78・C79・C80・C85・C91)は 1608 のまま**(1005 は 6.3V・10V の品しかなく、3.3V で容量が大きく減る)。1005 の 10µF は VCORE(約1.2V)の C54・C65 だけ
- **10µF 25V(0805)は厚さ 0.85mm の Samsung CL21A106KACLRNC(C318687)**: 電池の下のモータードライバの横の C22・C32 のため(ふつうの 1.25mm の品は入らない)。C5・C41 も同じ品にそろえる。村田 GRM219R61E106KA12 も 0.85±0.1mm・25V(データシート `docs/reference/datasheets/GRM219R61E106KA12_Murata.pdf`)だが、LCSC での扱いと今も作っているかが確かめられなかった
- 22µF 10V(0805、DC-DC の出力)も厚さ 0.85mm の Samsung CL21A226MPCLRNC(C307529)
- J2・J3(モーターの線)は裏の SMD のパッド(`MotorWire_SMD_1x02_P3.2mm`)

## データシートで確かめたこと(2026-11-23、ユーザーにもらった PDF を `docs/reference/datasheets/` に保存)

| 部品 | 確かめたこと |
|---|---|
| SW1 Alps SSSS810701(`SSSS8_Alps.pdf`) | 図番 3(1極2位置、グラウンド端子なし)。ランド: 0.7 × 1.5mm のパッド3つ(中心 x −2.25・0.75・2.25、y は中心から 1.0〜2.5)、φ0.9 の穴2つ(x ±1.5)→ フットプリント `SW_Slide_SPDT_Alps_SSSS8` と一致。高さ 1.4mm。**定格は 0.3A 5V DC(最大)** — 下の「気をつけること」 |
| SW2 Jianfu TVAF06-A020B-R(`TVAF06-A020B-R_Jianfu.pdf`、仕様書 2011101401) | ランド: 1.6 × 1.05mm のパッド2つ(外 5.5、内 3.4)、φ0.75 の穴2つ(間 1.8)→ `SW_Push_Jianfu_TVAF06` と一致。高さ 2.0mm、定格 DC 12V 50mA |
| BZ1 PUI SMT-0540-S-R(`SMT-0540-S-R_PUI.pdf`) | 推奨ランド 1.30 × 1.50mm(左の列 x −2.25〜−0.95、右 1.25〜2.55、y ±1.5〜3.0)、上から見て左上が +、左下が −、右上がつながらない足、音の穴は +x → `Buzzer_PUI_SMT-0540` と一致。定格 3V(2〜4V)、12Ω、100mA |
| LED Kingbright APTD1608LSECK/J4-PF(`APTD1608LSECK-J4-PF_Kingbright.pdf`) | 1.6 × 0.8 × **0.95mm**。推奨ランドは 0.8 × 0.8mm を 0.85mm あけて並べる(中心の間 1.65mm)。今の `LED_0603_1608Metric`(0.8 × 0.95mm、中心の間 1.575mm)とほぼ同じなのでこのまま。**1番がカソード**(フットプリントの1番 = K と合う)。2mA で 250〜450mcd |
| OPV332(`OPV332_TT.pdf`、Rev D 2026-11) | T-1(本体 φ2.92〜3.18、つば φ3.81〜4.06)。連続 12mA まで(回路は 10mA)、VF 1.0〜2.2V(7mA)、パルス 48mA(1µs、10%)。**足は 0.38〜0.64mm の角、間隔は約 1.0〜1.5mm**(基板の穴は 2.54mm 間隔なので、ホルダの後ろで足を広げて曲げる。穴は φ1.0 にした)。**足1がアノード、足2がカソード**(フットプリントの1番(四角)はカソードのネット) |
| SFH 229 FA(`SFH229FA_ams-OSRAM.pdf`、Version 1.6) | 足の間隔 2.54mm、本体 φ2.9〜3.1、つば最大 4.0。**2025-11-28 に生産終了**(Discontinued) — 下の「気をつけること」 |
| C22・C32 の候補 GRM219R61E106KA12 | 2.0 × 1.25 × **0.85±0.1mm**、25V、X5R |

## 気をつけること・決めたこと(2026-11-23)

1. **SFH 229 FA は生産終了**(2025-11-28)→ **予備を含めて在庫を確保する**(ユーザーの決定)。今の回路・ホルダのまま
2. **電源スイッチ SSSS810701 の定格は 5V DC**。OFF のときに電池の電圧(最大 12.6V)がかかる(流れるのは約 0.1mA、R1 100kΩ と R2 10kΩ)→ **このまま使う**(MK3 と同じ使い方。ユーザーの決定)
3. **壁センサの足の穴を φ0.9 → φ1.0 に**(`WallSensor_Holder_Emitter`・`_Receiver`、main と共通。OPV332 の足は最大 0.64mm 角で対角 約0.9mm。パッドは φ1.6 のまま)
4. J7(デバッグの 1.27mm 2 × 3 のヘッダ)は**手持ち**を使う。JLC の BOM には入れない
5. R43(ファンの電流 0.1Ω、2512)は厚膜で温度係数 ±800ppm/°C。電流の精度が要るなら金属板の品に
6. 受光の帰還 0.5pF は ±0.1pF の品(±0.05pF なら GJM1555C1HR50WB01D、C76912)

## 部品の一覧

| 部品 | 数 | 面 | 値 | 品番 | LCSC | 高さ[mm] | メモ |
|---|---|---|---|---|---|---|---|
| BZ1 | 1 | 上 | SMT-0540-S-R | PUI Audio SMT-0540-S-R |  |  |  |
| C1 | 1 | 上 | 220n 25V | Samsung CL05A224KA5NNNC (25V X5R) | C47129 | 0.55 | BAT+ とゲートの間 |
| C2 C3 | 2 | 上 | 22u 25V | Samsung CL31A226KAHNNNE (25V X5R) | C12891 | 1.8 | 厚さ 1.60±0.20。電池の外に置く。JLC Basic |
| C4 | 1 | 裏 | T521V476M025ATE040 | KEMET T521V476M025ATE040 |  |  |  |
| C5 C22 C32 C41 | 4 | 上 | 10u 25V | Samsung CL21A106KACLRNC (25V X5R) | C318687 | 0.95 | **厚さ 0.85±0.10**(電池の下の C22・C32 のため。ほかも同じ品にそろえる) |
| C6 C21 C31 C42 | 4 | 上 | 100n 25V | Samsung CL05A104KA5NNNC (25V X5R) | C100072 | 0.55 | VBAT(12.6V) |
| C7 C8 | 2 | 上 | 22u 10V | Samsung CL21A226MPCLRNC (10V X5R) | C307529 | 0.95 | 厚さ 0.85±0.10 |
| C9 | 1 | 上 | 10n | Samsung CL05B103KB5NNNC (50V X7R) | C15195 | 0.55 | JLC Basic |
| C10 | 1 | 上 | 22n 50V | FH 0402B223K500NT (50V X7R) | C1532 | 0.55 | JLC Basic |
| C23 C33 | 2 | 上 | 1n C0G | FH 0402CG102J500NT (50V C0G ±5%) | C53547 | 0.55 |  |
| C24 C34 C52 C55 C56 C57 C58 C59 C60 C61 C63 C64 C70 C71 C72 C73 C81 C82 C83 C84 C90 C92 | 22 | 上 | 100n | Samsung CL05B104KO5NNNC (16V X7R) | C1525 | 0.55 | JLC Basic |
| C40 | 1 | 上 | 1u | Samsung CL05A105KA5NQNC (25V X5R) | C52923 | 0.55 | JLC Basic |
| C50 C91 C78 C79 C80 C85 | 6 | 上 | 10u 10V | Samsung CL10A106KP8NNNC (10V X5R) | C19702 | 0.9 | 厚さ 0.80±0.10。JLC Basic |
| C51 C62 | 2 | 上 | 4.7u 10V | Samsung CL10A475KP8NNNC (10V X5R) | C1705 | 0.9 | 厚さ 0.80±0.10 |
| C53 | 1 | 上 | 220p | FH 0402CG221J500NT (50V C0G ±5%) | C39122 | 0.55 |  |
| C54 C65 | 2 | 上 | 10u | Samsung CL05A106MQ5NUNC (6.3V X5R) | C15525 | 0.7 | VCORE(約1.2V)だけ。厚さ 0.50±0.20。JLC Basic |
| C74 C75 C76 C77 | 4 | 上 | 0.5p C0G | Murata GJM1555C1HR50BB01D (50V C0G ±0.1pF) | C76911 | 0.55 | 受光アンプの帰還。±0.05pF なら GJM1555C1HR50WB01D(C76912) |
| C86 C87 | 2 | 上 | 2.2u 10V | Samsung CL05A225MP5NNNC (10V X5R) | C107370 | 0.55 |  |
| D1 | 1 | 上 | SMF13A | Littelfuse SMF13A |  |  |  |
| D2 D90 D91 D92 D93 D94 D95 D96 D98 | 9 | 上 | APTD1608LSECK/J4-PF | Kingbright APTD1608LSECK/J4-PF |  | 0.95 | 1番がカソード |
| D40 | 1 | 上 | MBR230LSFT1G | onsemi MBR230LSFT1G |  |  |  |
| D70 D71 D72 D73 | 4 | 裏 | OPV332 | TT Electronics (Optek) OPV332 |  |  |  |
| D74 D75 D76 D77 | 4 | 裏 | SFH 229 FA | ams OSRAM SFH 229 FA(2025-11-28 生産終了。**予備を含めて在庫を確保**) |  |  |  |
| D97 D99 D100 D101 | 4 | 上 | BAT54WS | Jingdao BAT54WS (30V 200mA) | C438012 | 1.1 | JSCJ(C2991936)・LGE(C402232)の BAT54WS は 100mA なので使わない |
| FB1 FB2 | 2 | 上 | BLM18PG221SN1D | Murata BLM18PG221SN1D |  |  |  |
| J1 | 1 | 上 | BATT | (基板のパッド。部品なし) |  |  | 電池の線 BT2.0 のケーブルをはんだ付け |
| J2 J3 | 2 | 裏 | MOTOR_L | (基板のパッド。部品なし) |  |  | モーターの線(裏) |
| J4 | 1 | 上 | FAN | (基板のパッド。部品なし) |  |  | ファンの線 |
| J5 J6 | 2 | 上 | ENC_L | (基板のパッド。部品なし) |  |  | エンコーダ基板をはんだ付け |
| J7 | 1 | 上 | DEBUG | 1.27mm 2 × 3 のピンヘッダ(縦、穴)。**手持ち**(2026-11-23) |  | 6.0 | 高さ約 5mm。電池の外。JLC の BOM には入れない |
| L1 | 1 | 上 | 2.2u DFE201610E-2R2M | Murata DFE201610E-2R2M=P2 |  |  |  |
| NT1 | 1 | 上 | NetTie_2 | (基板のパッド。部品なし) |  |  | PGND と GND の1点 |
| Q1 | 1 | 裏 | AO4407A | AOS AO4407A |  |  |  |
| Q40 | 1 | 上 | IRLML6344 | Infineon IRLML6344TRPBF |  |  |  |
| Q90 | 1 | 上 | 2N7002 | CJ 2N7002 | C8545 | 1.2 | JLC Basic |
| R1 | 1 | 上 | 100k | UNI-ROYAL 0402WGF1003TCE | C25741 | 0.4 | JLC Basic |
| R2 R40 R42 R50 R83 R84 R97 R98 R5 | 9 | 上 | 10k | UNI-ROYAL 0402WGF1002TCE | C25744 | 0.4 | JLC Basic |
| R3 | 1 | 上 | 1.30k 1% | UNI-ROYAL 0402WGF1301TCE | C25866 | 0.4 | DC-DC の出力の設定 |
| R4 R82 | 2 | 上 | 47k 1% | UNI-ROYAL 0402WGF4702TCE | C25792 | 0.4 | JLC Basic |
| R6 R81 R101 R24 R25 R34 R35 | 7 | 上 | 4.7k | UNI-ROYAL 0402WGF4701TCE | C25900 | 0.4 | JLC Basic |
| R21 R31 | 2 | 上 | 0 | UNI-ROYAL 0402WGF0000TCE | C17168 | 0.4 | JLC Basic |
| R22 R32 | 2 | 上 | PMR18EZPFU5L00 | ROHM PMR18EZPFU5L00 |  |  |  |
| R23 R33 R41 | 3 | 上 | 100 | UNI-ROYAL 0402WGF1000TCE | C25076 | 0.4 | JLC Basic |
| R43 | 1 | 上 | 0.1 1W | UNI-ROYAL 25121WF100LT4E (1W ±1%、厚膜) | C25466 | 0.65 | ファンの電流。温度係数 ±800ppm/°C(精度が要るなら金属板の品に) |
| R44 R78 R90 R91 R92 R93 R94 R95 R96 R99 | 10 | 上 | 1k | UNI-ROYAL 0402WGF1001TCE | C11702 | 0.4 | JLC Basic |
| R51 R80 | 2 | 上 | 2.2 | TA-I RMS04FT2R20 | C208851 | 0.4 |  |
| R70 R71 R72 R73 | 4 | 上 | 20 1% | UNI-ROYAL 0402WGF200JTCE | C25089 | 0.4 |  |
| R74 R75 R76 R77 | 4 | 上 | 820k | UNI-ROYAL 0402WGF8203TCE | C67558 | 0.4 |  |
| R79 | 1 | 上 | 47 | UNI-ROYAL 0402WGF470JTCE | C25118 | 0.4 |  |
| SW1 | 1 | 上 | SSSS810701 | Alps Alpine SSSS810701 |  |  |  |
| SW2 | 1 | 上 | TVAF06-A020B-R | Jianfu TVAF06-A020B-R |  |  |  |
| TP1 TP2 | 2 | 上 | UART_RX | (基板のパッド。部品なし) |  |  |  |
| TP3 | 1 | 裏 | BLE_SWDCLK | (基板のパッド。部品なし) |  |  |  |
| U1 | 1 | 上 | LXDC55FAAA-203 | Murata LXDC55FAAA-203 |  |  |  |
| U2 U3 | 2 | 上 | MP6551GQB | MPS MP6551GQB |  |  |  |
| U4 | 1 | 上 | STM32H725RGVx | STM32H725RGV6(または RGV3) |  |  |  |
| U5 | 1 | 上 | HY0020 | FDK HY0020 |  |  |  |
| U6 U7 | 2 | 上 | INA241A3 | TI INA241A3IDDFR(SOT-23-8) |  |  |  |
| U70 U71 U72 U73 | 4 | 上 | NJU6080 | NJR NJU6080 |  |  |  |
| U74 U75 | 2 | 上 | OPA2354 | TI OPA2354(VSSOP-8) |  |  |  |
| U76 | 1 | 上 | LSM6DSR | ST LSM6DSR |  |  |  |
| Y1 | 1 | 上 | CSTNE10M0G52Z000R0 | Murata CSTNE10M0G52Z000R0 |  |  |  |

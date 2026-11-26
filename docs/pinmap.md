# STM32H562RG ピンの割り当て(MK4)

2026-10-12作成、同日モータードライバをMP6551に変え、ファンの電流を追加、水晶をなくして更新。2026-10-17にエンコーダを磁気式(AS5047P、SPI2)に変えて更新。2026-10-29に発振子(HSE、10MHz、MK3 と同じ CSTNE10M0G52Z000R0)を付けることにして PH0・PH1 を使う。同日にエンコーダを MT6835 に変え、校正の CAL_EN を PC15 から出す。2026-10-31 に PD2 を IMU の INT1(データ準備完了の割り込み)に、PB3 を前の LED にする。これで46本すべて使う。パッケージはVFQFPN68(8×8mm)、使えるIOは46本。**2026-11-26 に MCU を STM32H725RG から STM32H562RG(同じ VFQFPN68、IO 53本)に替えた**(H725 はどこにも在庫がないため。`docs/spec.md` の「MCU」)。ピンの機能の名前は同じなので割り当てはそのまま移し、ピンの番号を H562 に直した。H562 には PD2 がないので、IMU の INT1 を PB3 へ、前の LED を PB3 から PE0 へ移した。

## 確かめ方

STが公開しているピン定義(STM32CubeMXと同じデータ、[STM32_open_pin_data](https://github.com/STMicroelectronics/STM32_open_pin_data))で、`docs/calc/check_pins.py`が次を確かめる。割り当てを変えたら走らせ直す。

```sh
git clone --depth 1 https://github.com/STMicroelectronics/STM32_open_pin_data
python3 docs/calc/check_pins.py STM32_open_pin_data/mcu/STM32H562RGVx.xml
```

- ピンがVFQFPN68にあるか
- そのピンに、割り当てた機能(タイマのチャンネル、ADCの入力、SPI、USARTなど)があるか
- 同じピン、同じタイマのチャンネル、同じADCの入力を2回使っていないか

**結果: OK**。使う46本、残り7本(2026-11-27、STM32H562RGVx。IMU を SPI1 へ移したあと)。

確かめていないこと(CubeMXで.iocを作るときに確かめる): クロックの設定、DMAの割り当て、ADCを2つ同時に動かす設定、タイマの周波数。

## 割り当て表

| ピン番号 | ピン | 機能 | ネット名 | 用途 |
|---|---|---|---|---|
| 3 | PC14-OSC32_IN | GPIO_Input | SW | スイッチ |
| 4 | PC15-OSC32_OUT | GPIO_Output | ENC_CAL | エンコーダの校正(MT6835 の CAL_EN、左右共通) |
| 5 | PH0-OSC_IN | RCC_OSC_IN | OSC_IN | 発振子(HSE、10MHz) |
| 6 | PH1-OSC_OUT | RCC_OSC_OUT | OSC_OUT | 発振子(HSE、10MHz) |
| 8 | PC0 | ADC1_INP10 | WALL_FL | 壁センサ 左前 |
| 9 | PC1 | ADC1_INP11 | WALL_L | 壁センサ 左 |
| 10 | PC2 | ADC1_INP12 | WALL_R | 壁センサ 右。2026-11-27 に PA6 から(前を向いた辺) |
| 11 | PC3 | ADC1_INP13 | WALL_FR | 壁センサ 右前。2026-11-27 に PA7 から(前を向いた辺) |
| 14 | PA0 | GPIO_Output | LED_MODE0 | モード ビット0 |
| 15 | PA1 | GPIO_Output | LED_MODE1 | モード ビット1 |
| 16 | PA2 | GPIO_Output | LED_MODE2 | モード ビット2 |
| 17 | PA3 | ADC2_INP15 | MOT_R_CMS | 右の MP6551 の CM1 + CM2(下の FET の電流の和 ≒ 電池から出る電流、2026-11-23)。2026-11-27 に PA5 から |
| 20 | PA4 | ADC2_INP18 | MOT_R_I | 右モーターの電流(INA241A3 の出力、2026-11-23。それまでは MP6551 の CM1) |
| 21 | PA5 | SPI1_SCK | IMU_SCK | IMU SPIクロック。2026-11-27 に SPI3(PC10)から SPI1 へ(IMU のほうを向いた辺) |
| 22 | PA6 | SPI1_MISO | IMU_MISO | IMU MISO。2026-11-27 に PC11 から |
| 23 | PA7 | SPI1_MOSI | IMU_MOSI | IMU MOSI。2026-11-27 に PC12 から |
| 24 | PC4 | ADC2_INP4 | MOT_L_I | 左モーターの電流(INA241A3 の出力、2026-11-23。それまでは MP6551 の CM1) |
| 25 | PC5 | ADC2_INP8 | MOT_L_CMS | 左の MP6551 の CM1 + CM2(下の FET の電流の和 ≒ 電池から出る電流、2026-11-23) |
| 26 | PB0 | ADC1_INP9 | FAN_ISENSE | 吸引ファンの電流(シャント抵抗の電圧をRCで平均) |
| 27 | PB1 | ADC2_INP5 | BATT | 電池の電圧(分圧) |
| 28 | PB2 | GPIO_Output | MOT_EN | ドライバ2個のEN1・EN2(共通。Lでスリープ) |
| 29 | PB10 | GPIO_Output | IMU_CS | IMU チップセレクト。2026-11-27 に PA15 から |
| 30 | PB11 | GPIO_EXTI11 | IMU_INT | IMU の INT1(データ準備完了の割り込み。2026-11-26 に PD2 から。H562 には PD2 がない)。2026-11-27 に PB3 から(EXTI11) |
| 34 | PB12 | GPIO_Output | LED_NUM2 | ナンバー ビット2 |
| 35 | PB13 | GPIO_Output | LED_NUM3 | ナンバー ビット3 |
| 36 | PB14 | SPI2_MISO | ENC_MISO | エンコーダ MISO |
| 37 | PB15 | SPI2_MOSI | ENC_MOSI | エンコーダ MOSI |
| 38 | PD11 | GPIO_Output | LED_NUM1 | ナンバー ビット1。2026-11-27 に PB10 から |
| 39 | PD12 | GPIO_Output | LED_NUM0 | ナンバー ビット0。2026-11-27 に PA3 から(LED のある後ろを向いた辺) |
| 40 | PC6 | GPIO_Output | ENC_L_CS | 左エンコーダ チップセレクト |
| 41 | PC7 | GPIO_Output | ENC_R_CS | 右エンコーダ チップセレクト |
| 43 | PC9 | GPIO_Input | MOT_nFAULT | ドライバ2個のnFAULT(オープンドレインを共通に) |
| 44 | PA8 | TIM1_CH1 | MOT_L_IN1 | 左モーター IN1(PWM) |
| 45 | PA9 | TIM1_CH2 | MOT_L_IN2 | 左モーター IN2(PWM) |
| 46 | PA10 | TIM1_CH3 | MOT_R_IN1 | 右モーター IN1(PWM) |
| 47 | PA11 | TIM1_CH4 | MOT_R_IN2 | 右モーター IN2(PWM) |
| 48 | PA12 | SPI2_SCK | ENC_SCK | エンコーダ SPIクロック |
| 49 | PA13(JTMS/SWDIO) | DEBUG_JTMS-SWDIO | SWDIO | 書き込み・デバッグ |
| 52 | PA14(JTCK/SWCLK) | DEBUG_JTCK-SWCLK | SWCLK | 書き込み・デバッグ |
| 58 | PB4(NJTRST) | GPIO_Output | WALL_LED_FL_R | 壁センサの発光 FL と R(NJU6080 2個のPWM端子。MK3 の WallLED_12) |
| 59 | PB5 | GPIO_Output | WALL_LED_L_FR | 壁センサの発光 L と FR(NJU6080 2個のPWM端子。MK3 の WallLED_34) |
| 60 | PB6 | USART1_TX | UART_TX | PCへ(USBシリアル変換)と BLE モジュール HY0020 の受信(P0.08、2026-11-23) |
| 61 | PB7 | USART1_RX | UART_RX | PCから(TP1、D100)と HY0020 の送信(P0.06、D99)。R101 4.7kΩ で引き上げ、ダイオードで L に引くだけ(ワイヤード AND、両方つないだままでよい。`docs/ble.md` の9章)。HY0020 の P0.04 も見る |
| 63 | PB8 | TIM16_CH1 | FAN_PWM | 吸引ファン(PWM) |
| 64 | PB9 | TIM17_CH1 | BUZZER | ブザー(PWM) |
| 65 | PE0 | GPIO_Output | LED_FRONT | 前の LED(D98。前の円弧の切り欠きの真ん中。2026-10-31)。2026-11-26 に PB3 から |

## 残りのピン

**7本**(2026-11-27): PC13(2番)、PC8(42番)、PA15(53番)、PC10・PC11・PC12(54〜56番)、PB3(57番)。2026-11-26 に H562 にして増えた分(PC2・PC3・PB11・PD11・PD12)は、2026-11-27 に IMU を SPI1 へ移したときに使った。回路図では × にしてある。ソフトで出力の L にしておく(浮かせない)。H725 のとき(2026-10-31〜11-26)は46本すべて使っていた。**SWO は使わない**: ログは今までどおり UART(J7 の STLINK-V3MODS の仮想COMポート)で出す。MK3 のビューア(`tools/viewer.html`)が USB シリアルで読むため。ピンが足りなくなったら、LED 8個をシフトレジスタ(3本)にすれば5本空く

## 割り当ての考え方

- **モーター(MP6551 × 2)**: TIM1のCH1〜CH4(PA8〜PA11)で、左右それぞれIN1・IN2の両方をPWMにする。前進はIN1にPWM・IN2を0、後退はIN1を0・IN2にPWM。止めている間(PWMのオフ)はどちらの向きも両側の出力がLになり、下側のFETで減衰する。こうすると、電流の出力(CM)をどちらの向きでも同じように読める(下記)。4本とも同じタイマなので、周期がそろう
- **モーターの電流**(2026-11-23 から): OUT1 とモーターの間の 5mΩ を INA241A3 で測り、ADC2 で読む(MOT_L_I PC4・MOT_R_I PA4)。MP6551 の CM1・CM2 はつないで 4.7k × 2 で終端し、ADC2 で読む(MOT_L_CMS PC5・MOT_R_CMS PA3(2026-11-27 に PA5 から)、電池の電流の目安)。ADC2 は TIM1 で起動し、PWM の真ん中で読む(`docs/software.md` の4章)。それまでの CM の読み方は `docs/spec.md` の「駆動のしかたと電流の測り方」に記録
- **ADC**: 壁センサの4本とファンの電流はADC1(INP10・11・12・13・9)、モーターの電流4本と電池はADC2(INP4・8・18・15・5)(2026-11-27: 壁センサ R・FR を PC2・PC3、MOT_R_CMS を PA3 へ。前は INP3・7 と INP19)。ADC1とADC2を同時に動かせる
- **エンコーダ**: MT6835 × 2をSPI2(SCK PA12、MISO PB14、MOSI PB15)で読み、CSは左PC6・右PC7(GPIO)。バスはIMU(SPI3)と分けたまま(2026-10-17にAS5047P(モード1)で分けた。MT6835はIMUと同じモード3だが、配線の都合で分けておく)
- **エンコーダの校正**: PC15(ENC_CAL)で左右の CAL_EN を一緒に H にする(2026-10-29)。PC15 は電流を流せない(3mAまで、2MHzまで)ピンだが、CAL_EN は入力(中に 250kΩ のプルダウン)なので問題ない。リセット中はハイインピーダンスになり、プルダウンで L に保たれる
- **吸引ファン・ブザー**: TIM16・TIM17
- **IMU**: **SPI1(PA5 SCK・PA6 MISO・PA7 MOSI)、CS は PB10(GPIO)、INT1 は PB11(EXTI11)**(2026-11-27。前は SPI3(PC10〜12)・CS PA15・INT1 PB3 で、IMU(回転の中心のそば)と反対の辺から出ていたので、5本が MCU を回り込んでいた。ユーザー: 部品配置の見直し。INT1 は 2026-10-31 に PD2 で決め、H562 で PB3 になっていた): 新しい値ができたら割り込みで知らせる(データ準備完了)。同じ値を2回読んだり、古い値を使ったりしないため。使わないときはソフトで無視すればよい。EXTI の2番を使う入力はほかにない(スイッチ PC14 は14番、nFAULT PC9 は9番)。INT2 はつながない
- **UART**: USART1(PB6・PB7)。PA9・PA10はモーターのPWMに、PB14・PB15はエンコーダのSPI2に使うので、USART1の3つ目の組にした
- **LED**: モード3ビットはPA0〜PA2、ナンバー4ビットはPD12・PD11・PB12・PB13(2026-11-27 に PA3・PB10 から。LED のある後ろを向いた辺へ)、前の LED は PE0(2026-10-31 に PB3、2026-11-26 に PE0 へ)
- **スイッチ**: PC14(OSC32_IN)。入力なので、流せる電流が小さくても問題ない
- **発振子(HSE)**: 10MHz のセラミック発振子(CSTNE10M0G52A000R0。MK3 の CSTNE10M0G52Z000R0 と同じ仕様で、2026-11-26 に在庫のある品に替えた)を PH0・PH1 に付ける(2026-10-29)。PLL で 240MHz にする(例: 10MHz ÷ 1 × 48 ÷ 2。2026-11-26: H562 の上限は 250MHz だが、TIM1 の 80kHz・20kHz がちょうど割り切れる 240MHz にする。H725 のときは 550MHz の予定だった)。2026-10-12 には付けず HSI にしていた

## 気をつけること

- **PA15(JTDI)とPB4(NJTRST)とPB3(JTDO)**は、リセット直後はJTAGの機能になっている(H562 も同じ)。CubeMXでデバッグを「Serial Wire」にすれば、GPIOとして使える
- **BOOT0**(62番。H725 では 63番)は専用ピン。10kΩ程度でGNDに落とす。**テストパッド TP4 を付ける**(2026-11-23。電源の設定ミスなどで応答しなくなったとき、TP4 を 3.3V につないだまま電源を入れると、自分のプログラムが動かず STLINK でつないで消せる)。HY0020 にはつながない(2026-11-23。AN2606: H72x の書き込み用のプログラムの USART1 は PA9・PA10 だけで、この機体の UART(PB6・PB7)では使えない。**H562 も同じ**: USART1 は PA9・PA10、USART2 は PA2・PA3、USART3 は PD8・PD9 だけ(AN2606 Rev 71 の表137)。どれもこの機体では別の用途に使っている)
- **NRST**(7番。H725 では 12番)は専用ピン。SWDの端子にも出す。HY0020 の P0.07 からも動かせる(2026-11-23)
- **電源のピン**: H562 の VFQFPN68 は **LDO だけ**(SMPS はない。VCAP × 2 に 2.2µF ずつ、VDD × 4、VDDA・VSSA、VBAT、VSS は裏の大きいパッドにもつながる)。2026-11-26 までの H725 は SMPS 専用(VSSSMPS・VLXSMPS・VDDSMPS・VFBSMPS、VCAP × 3)だった。部品は仕様書の「MCUの電源」

# STM32H725RG ピンの割り当て(MK4)

2026-10-12作成、同日モータードライバをMP6551に変え、ファンの電流を追加、水晶をなくして更新。2026-10-17にエンコーダを磁気式(AS5047P、SPI2)に変えて更新。2026-10-29に発振子(HSE、10MHz、MK3 と同じ CSTNE10M0G52Z000R0)を付けることにして PH0・PH1 を使う。同日にエンコーダを MT6835 に変え、校正の CAL_EN を PC15 から出す。2026-10-31 に PD2 を IMU の INT1(データ準備完了の割り込み)にする。パッケージはVFQFPN68(8×8mm)、使えるIOは46本。

## 確かめ方

STが公開しているピン定義(STM32CubeMXと同じデータ、[STM32_open_pin_data](https://github.com/STMicroelectronics/STM32_open_pin_data))で、`docs/calc/check_pins.py`が次を確かめる。割り当てを変えたら走らせ直す。

```sh
git clone --depth 1 https://github.com/STMicroelectronics/STM32_open_pin_data
python3 docs/calc/check_pins.py STM32_open_pin_data/mcu/STM32H725RGVx.xml
```

- ピンがVFQFPN68にあるか
- そのピンに、割り当てた機能(タイマのチャンネル、ADCの入力、SPI、USARTなど)があるか
- 同じピン、同じタイマのチャンネル、同じADCの入力を2回使っていないか

**結果: OK**。使う45本、残り1本(2026-10-31)。

確かめていないこと(CubeMXで.iocを作るときに確かめる): クロックの設定、DMAの割り当て、ADCを2つ同時に動かす設定、タイマの周波数。

## 割り当て表

| ピン番号 | ピン | 機能 | ネット名 | 用途 |
|---|---|---|---|---|
| 2 | PC14-OSC32_IN | GPIO_Input | SW | スイッチ |
| 3 | PC15-OSC32_OUT | GPIO_Output | ENC_CAL | エンコーダの校正(MT6835 の CAL_EN、左右共通) |
| 10 | PH0-OSC_IN | RCC_OSC_IN | OSC_IN | 発振子(HSE、10MHz) |
| 11 | PH1-OSC_OUT | RCC_OSC_OUT | OSC_OUT | 発振子(HSE、10MHz) |
| 13 | PC0 | ADC1_INP10 | WALL_FL | 壁センサ 左前 |
| 14 | PC1 | ADC1_INP11 | WALL_L | 壁センサ 左 |
| 17 | PA0 | GPIO_Output | LED_MODE0 | モード ビット0 |
| 18 | PA1 | GPIO_Output | LED_MODE1 | モード ビット1 |
| 19 | PA2 | GPIO_Output | LED_MODE2 | モード ビット2 |
| 20 | PA3 | GPIO_Output | LED_NUM0 | ナンバー ビット0 |
| 23 | PA4 | ADC2_INP18 | MOT_R_CM1 | 右モーターの電流(OUT1側の下側FET) |
| 24 | PA5 | ADC2_INP19 | MOT_R_CM2 | 右モーターの電流(OUT2側の下側FET) |
| 25 | PA6 | ADC1_INP3 | WALL_R | 壁センサ 右 |
| 26 | PA7 | ADC1_INP7 | WALL_FR | 壁センサ 右前 |
| 27 | PC4 | ADC2_INP4 | MOT_L_CM1 | 左モーターの電流(OUT1側の下側FET) |
| 28 | PC5 | ADC2_INP8 | MOT_L_CM2 | 左モーターの電流(OUT2側の下側FET) |
| 29 | PB0 | ADC1_INP9 | FAN_ISENSE | 吸引ファンの電流(シャント抵抗の電圧をRCで平均) |
| 30 | PB1 | ADC2_INP5 | BATT | 電池の電圧(分圧) |
| 31 | PB2 | GPIO_Output | MOT_EN | ドライバ2個のEN1・EN2(共通。Lでスリープ) |
| 32 | PB10 | GPIO_Output | LED_NUM1 | ナンバー ビット1 |
| 36 | PB12 | GPIO_Output | LED_NUM2 | ナンバー ビット2 |
| 37 | PB13 | GPIO_Output | LED_NUM3 | ナンバー ビット3 |
| 38 | PB14 | SPI2_MISO | ENC_MISO | エンコーダ MISO |
| 39 | PB15 | SPI2_MOSI | ENC_MOSI | エンコーダ MOSI |
| 40 | PC6 | GPIO_Output | ENC_L_CS | 左エンコーダ チップセレクト |
| 41 | PC7 | GPIO_Output | ENC_R_CS | 右エンコーダ チップセレクト |
| 42 | PC9 | GPIO_Input | MOT_nFAULT | ドライバ2個のnFAULT(オープンドレインを共通に) |
| 43 | PA8 | TIM1_CH1 | MOT_L_IN1 | 左モーター IN1(PWM) |
| 44 | PA9 | TIM1_CH2 | MOT_L_IN2 | 左モーター IN2(PWM) |
| 45 | PA10 | TIM1_CH3 | MOT_R_IN1 | 右モーター IN1(PWM) |
| 46 | PA11 | TIM1_CH4 | MOT_R_IN2 | 右モーター IN2(PWM) |
| 47 | PA12 | SPI2_SCK | ENC_SCK | エンコーダ SPIクロック |
| 48 | PA13(JTMS/SWDIO) | DEBUG_JTMS-SWDIO | SWDIO | 書き込み・デバッグ |
| 52 | PA14(JTCK/SWCLK) | DEBUG_JTCK-SWCLK | SWCLK | 書き込み・デバッグ |
| 53 | PA15(JTDI) | GPIO_Output | IMU_CS | IMU チップセレクト |
| 54 | PC10 | SPI3_SCK | IMU_SCK | IMU SPIクロック |
| 55 | PC11 | SPI3_MISO | IMU_MISO | IMU MISO |
| 56 | PC12 | SPI3_MOSI | IMU_MOSI | IMU MOSI |
| 57 | PD2 | GPIO_EXTI2 | IMU_INT | IMU の INT1(データ準備完了の割り込み。2026-10-31) |
| 59 | PB4(NJTRST) | GPIO_Output | WALL_LED_FL_R | 壁センサの発光 FL と R(NJU6080 2個のPWM端子。MK3 の WallLED_12) |
| 60 | PB5 | GPIO_Output | WALL_LED_L_FR | 壁センサの発光 L と FR(NJU6080 2個のPWM端子。MK3 の WallLED_34) |
| 61 | PB6 | USART1_TX | UART_TX | PCへ(USBシリアル変換) |
| 62 | PB7 | USART1_RX | UART_RX | PCから |
| 64 | PB8 | TIM16_CH1 | FAN_PWM | 吸引ファン(PWM) |
| 65 | PB9 | TIM17_CH1 | BUZZER | ブザー(PWM) |

## 残りのピン(1本)

| ピン | 使える機能 | 使い道の案 |
|---|---|---|
| PB3 | SWO(デバッグのトレース出力)、TIM2_CH2、SPI1/3/6_SCK、UART7_RX | 予備。制御の時間を測るテストパッド(GPIO)か SWO の案(2026-10-31 に検討、未決定)。ADC にはならない |

## 割り当ての考え方

- **モーター(MP6551 × 2)**: TIM1のCH1〜CH4(PA8〜PA11)で、左右それぞれIN1・IN2の両方をPWMにする。前進はIN1にPWM・IN2を0、後退はIN1を0・IN2にPWM。止めている間(PWMのオフ)はどちらの向きも両側の出力がLになり、下側のFETで減衰する。こうすると、電流の出力(CM)をどちらの向きでも同じように読める(下記)。4本とも同じタイマなので、周期がそろう
- **モーターの電流**: MP6551のCM1・CM2を別々にADC2で読む(4本)。電流は下側のFETで測られるので、0に固定している側(前進ならOUT2側 = CM2)を読むと、PWMのオンでもオフでもモーターの電流そのものが読める。CM1とCM2をつないで1本にすると、オフの間に打ち消し合って「duty × モーターの電流」(電池から出る電流)になってしまう
- **ADC**: 壁センサの4本とファンの電流はADC1(INP10・11・3・7・9)、モーターの電流4本と電池はADC2(INP4・8・18・19・5)。ADC1とADC2を同時に動かせる
- **エンコーダ**: MT6835 × 2をSPI2(SCK PA12、MISO PB14、MOSI PB15)で読み、CSは左PC6・右PC7(GPIO)。バスはIMU(SPI3)と分けたまま(2026-10-17にAS5047P(モード1)で分けた。MT6835はIMUと同じモード3だが、配線の都合で分けておく)
- **エンコーダの校正**: PC15(ENC_CAL)で左右の CAL_EN を一緒に H にする(2026-10-29)。PC15 は電流を流せない(3mAまで、2MHzまで)ピンだが、CAL_EN は入力(中に 250kΩ のプルダウン)なので問題ない。リセット中はハイインピーダンスになり、プルダウンで L に保たれる
- **吸引ファン・ブザー**: TIM16・TIM17
- **IMU**: SPI3(PC10・PC11・PC12)、CSはPA15(GPIO)。**INT1 は PD2(EXTI2)**(2026-10-31): 新しい値ができたら割り込みで知らせる(データ準備完了)。同じ値を2回読んだり、古い値を使ったりしないため。使わないときはソフトで無視すればよい。EXTI の2番を使う入力はほかにない(スイッチ PC14 は14番、nFAULT PC9 は9番)。INT2 はつながない
- **UART**: USART1(PB6・PB7)。PA9・PA10はモーターのPWMに、PB14・PB15はエンコーダのSPI2に使うので、USART1の3つ目の組にした
- **LED**: モード3ビットはPA0〜PA2、ナンバー4ビットはPA3・PB10・PB12・PB13
- **スイッチ**: PC14(OSC32_IN)。入力なので、流せる電流が小さくても問題ない
- **発振子(HSE)**: 10MHz のセラミック発振子(CSTNE10M0G52Z000R0、MK3 と同じ)を PH0・PH1 に付ける(2026-10-29)。PLL で 550MHz にする(例: 10MHz ÷ 5 × 275 ÷ 1)。2026-10-12 には付けず HSI にしていた

## 気をつけること

- **PA15(JTDI)とPB4(NJTRST)**は、リセット直後はJTAGの機能になっている。CubeMXでデバッグを「Serial Wire」にすれば、GPIOとして使える
- **BOOT0**(63番)は専用ピン。10kΩ程度でGNDに落とす
- **NRST**(12番)は専用ピン。SWDの端子にも出す
- **電源のピン**: VFQFPN68はSMPS専用(VSSSMPS・VLXSMPS・VDDSMPS・VFBSMPS、VCAP × 3、VDDA・VSSA、VBAT)。部品は仕様書の「MCUの電源」

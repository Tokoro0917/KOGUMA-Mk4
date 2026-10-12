# STM32H725RG ピンの割り当て(MK4)

2026-10-12作成、同日モータードライバをMP6551に変え、ファンの電流を追加して更新。パッケージはVFQFPN68(8×8mm)、使えるIOは46本。

## 確かめ方

STが公開しているピン定義(STM32CubeMXと同じデータ、[STM32_open_pin_data](https://github.com/STMicroelectronics/STM32_open_pin_data))で、`docs/calc/check_pins.py`が次を確かめる。割り当てを変えたら走らせ直す。

```sh
git clone --depth 1 https://github.com/STMicroelectronics/STM32_open_pin_data
python3 docs/calc/check_pins.py STM32_open_pin_data/mcu/STM32H725RGVx.xml
```

- ピンがVFQFPN68にあるか
- そのピンに、割り当てた機能(タイマのチャンネル、ADCの入力、SPI、USARTなど)があるか
- 同じピン、同じタイマのチャンネル、同じADCの入力を2回使っていないか
- エンコーダのA/B相が、同じタイマのCH1/CH2になっているか

**結果: OK**。使う42本、残り4本。

確かめていないこと(CubeMXで.iocを作るときに確かめる): クロックの設定、DMAの割り当て、ADCを2つ同時に動かす設定、タイマの周波数。

## 割り当て表

| ピン番号 | ピン | 機能 | ネット名 | 用途 |
|---|---|---|---|---|
| 2 | PC14-OSC32_IN | GPIO_Input | SW | スイッチ |
| 10 | PH0-OSC_IN | RCC_OSC_IN | HSE_IN | 水晶(HSE) |
| 11 | PH1-OSC_OUT | RCC_OSC_OUT | HSE_OUT | 水晶(HSE) |
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
| 38 | PB14 | USART1_TX | UART_TX | PCへ(USBシリアル変換) |
| 39 | PB15 | USART1_RX | UART_RX | PCから |
| 40 | PC6 | TIM3_CH1 | ENC_R_A | 右エンコーダ A相 |
| 41 | PC7 | TIM3_CH2 | ENC_R_B | 右エンコーダ B相 |
| 42 | PC9 | GPIO_Input | MOT_nFAULT | ドライバ2個のnFAULT(オープンドレインを共通に) |
| 43 | PA8 | TIM1_CH1 | MOT_L_IN1 | 左モーター IN1(PWM) |
| 44 | PA9 | TIM1_CH2 | MOT_L_IN2 | 左モーター IN2(PWM) |
| 45 | PA10 | TIM1_CH3 | MOT_R_IN1 | 右モーター IN1(PWM) |
| 46 | PA11 | TIM1_CH4 | MOT_R_IN2 | 右モーター IN2(PWM) |
| 48 | PA13(JTMS/SWDIO) | DEBUG_JTMS-SWDIO | SWDIO | 書き込み・デバッグ |
| 52 | PA14(JTCK/SWCLK) | DEBUG_JTCK-SWCLK | SWCLK | 書き込み・デバッグ |
| 53 | PA15(JTDI) | GPIO_Output | IMU_CS | IMU チップセレクト |
| 54 | PC10 | SPI3_SCK | IMU_SCK | IMU SPIクロック |
| 55 | PC11 | SPI3_MISO | IMU_MISO | IMU MISO |
| 56 | PC12 | SPI3_MOSI | IMU_MOSI | IMU MOSI |
| 59 | PB4(NJTRST) | GPIO_Output | WALL_LED_L | 壁センサの発光 左(NJU6080のPWM端子) |
| 60 | PB5 | GPIO_Output | WALL_LED_R | 壁センサの発光 右(NJU6080のPWM端子) |
| 61 | PB6 | TIM4_CH1 | ENC_L_A | 左エンコーダ A相 |
| 62 | PB7 | TIM4_CH2 | ENC_L_B | 左エンコーダ B相 |
| 64 | PB8 | TIM16_CH1 | FAN_PWM | 吸引ファン(PWM) |
| 65 | PB9 | TIM17_CH1 | BUZZER | ブザー(PWM) |

## 残りのピン(4本)

| ピン | 使える機能 | 使い道の案 |
|---|---|---|
| PD2 | TIM3_ETR | IMUの割り込み(INT) |
| PA12 | TIM1_ETR | 予備 |
| PB3 | SWO(デバッグのトレース出力)、TIM2_CH2 | 予備(SWOを使うならここ) |
| PC15 | (OSC32_OUT) | 予備(電流を多く流せないピン) |

## 割り当ての考え方

- **モーター(MP6551 × 2)**: TIM1のCH1〜CH4(PA8〜PA11)で、左右それぞれIN1・IN2の両方をPWMにする。前進はIN1にPWM・IN2を0、後退はIN1を0・IN2にPWM。止めている間(PWMのオフ)はどちらの向きも両側の出力がLになり、下側のFETで減衰する。こうすると、電流の出力(CM)をどちらの向きでも同じように読める(下記)。4本とも同じタイマなので、周期がそろう
- **モーターの電流**: MP6551のCM1・CM2を別々にADC2で読む(4本)。電流は下側のFETで測られるので、0に固定している側(前進ならOUT2側 = CM2)を読むと、PWMのオンでもオフでもモーターの電流そのものが読める。CM1とCM2をつないで1本にすると、オフの間に打ち消し合って「duty × モーターの電流」(電池から出る電流)になってしまう
- **ADC**: 壁センサの4本とファンの電流はADC1(INP10・11・3・7・9)、モーターの電流4本と電池はADC2(INP4・8・18・19・5)。ADC1とADC2を同時に動かせる
- **エンコーダ**: 左はTIM4(PB6・PB7)、右はTIM3(PC6・PC7)。どちらもCH1/CH2の組
- **吸引ファン・ブザー**: TIM16・TIM17
- **IMU**: SPI3(PC10・PC11・PC12)、CSはPA15(GPIO)
- **UART**: USART1(PB14・PB15)。PA9・PA10はモーターのPWMに使うので、USART1のもう一組のピンにした
- **LED**: モード3ビットはPA0〜PA2、ナンバー4ビットはPA3・PB10・PB12・PB13
- **スイッチ**: PC14(OSC32_IN)。入力なので、流せる電流が小さくても問題ない
- **水晶(HSE)**: PH0・PH1。付けないならこの2本も予備になる

## 気をつけること

- **PA15(JTDI)とPB4(NJTRST)**は、リセット直後はJTAGの機能になっている。CubeMXでデバッグを「Serial Wire」にすれば、GPIOとして使える
- **BOOT0**(63番)は専用ピン。10kΩ程度でGNDに落とす
- **NRST**(12番)は専用ピン。SWDの端子にも出す
- **電源のピン**: VFQFPN68はSMPS専用(VSSSMPS・VLXSMPS・VDDSMPS・VFBSMPS、VCAP × 3、VDDA・VSSA、VBAT)。部品は仕様書の「MCUの電源」

# CubeMX 設定(ステップ0)

STM32CubeMX で `KOGUMA-Mk4` プロジェクトを新しく作るときの `.ioc` の設定値です。ToraNeko.Mk3 の `CUBEMX_SETUP.md` と同じ形にしてあります。コードは CMake 形式で作り、VS Code(STM32Cube for Visual Studio Code 拡張)でビルド・書き込み・デバッグします。

- ピンは [../../docs/pinmap.md](../../docs/pinmap.md) の割り当て表のとおり
- 時刻の作り方(TIM1 を元に 20kHz・1kHz)は [../../docs/software.md](../../docs/software.md) の4章
- RAM・DMA の決まりは [../../docs/firmware_memory.md](../../docs/firmware_memory.md)
- 「ToraNeko」列は参考用に ToraNeko.Mk3(F411、100MHz)の設定を載せています

## 0. Core/ は手で書いた(2026-11-28)

CubeMX を使える環境がなかったので、**`KOGUMA-Mk4/Core/` は Claude が、CubeMX が作るのと同じ形で手で書いた**(ユーザーの決定)。
ファイルの名前・関数の名前(`MX_xxx_Init`、`HAL_xxx_MspInit`)・`USER CODE` 欄の形は CubeMX と同じなので、
あとで CubeMX で `.ioc` を作って生成し直しても、`USER CODE` 欄と `App/` はそのまま残る。中身の設定は、この文書の値のとおり。

作ったときに、次の所をこの文書の前の案から変えた(**DMA を使わない**。H5 の GPDMA の回し続ける設定(linked-list)は難しく、確かめる手段もないため):

| 所 | 前の案 | 今(`Core/`) |
|---|---|---|
| ADC1・ADC2 | 5 本の regular + DMA(GPDMA の linked-list) | **4 本の injected**(結果が JDR1〜4 に別々に入るので DMA が要らない)を TIM1 の TRGO で起動。5 本目(ファンの電流・電池)は regular で、20kHz の処理の中でソフトで起動して次の回に読む。割り込みは ADC2 の JEOS(4 本の終わり) |
| SPI1・SPI2 | DMA、10kHz | DMA なし。4kHz の処理の中で `HAL_SPI_TransmitReceive`(ToraNeko と同じ読み方) |
| USART1 | DMA | 送る・受けるとも割り込み(`HAL_UART_Transmit_IT`・`HAL_UART_Receive_IT`) |
| NVIC | GPDMA1 Ch1 が 20kHz の処理 | **ADC2 の割り込み(優先度 0)が 20kHz の処理**、TIM6(2)が 4kHz の処理、USART1(5) |
| IMU_INT(PB11) | EXTI11 の割り込み | ふつうの入力(今は使わない。4kHz の処理で読む) |
| リンカの設定 | `.dma_buf`(SRAM2) | **`.sram3`**(SRAM3 にログ 256KB。`App/config/memory_place.h` の `SRAM3_DATA`)。`.dma_buf` は DMA を使うまで作らない |
| プログラムの番地 | 先頭(0x08000000)から | **0x08010000 から**(ブートローダのあと。`CMakeLists.txt` の `VECT_TAB_OFFSET`) |

## 0.1 MCU を替えた(2026-11-26)

**STM32H725RGVx から STM32H562RGVx に替えた**(H725 はどこにも在庫がない。`docs/spec.md` の「MCU」)。この文書は H562 の設定に書き直した。数値はデータシート DS14258 Rev 6 で確かめたもの。**H5 の CubeMX は作者も Claude もまだ使ったことがない**ので、「確かめる」と書いた所は、CubeMX の画面を見て決め、決めたらこの文書を直す。

## 1. プロジェクトを作る

| 項目 | 設定 |
|---|---|
| MCU | **STM32H562RGVx**(VFQFPN68) |
| TrustZone | **使わない**(プロジェクトを作るときに「without TrustZone activated」を選ぶ) |
| Project Name | `KOGUMA-Mk4` |
| 作る場所 | `software/main-controller/KOGUMA-Mk4/` |
| Project Manager → Project → **Toolchain / IDE** | **CMake**(STM32CubeIDE は使わない) |
| Project Manager → Project → Do not generate the main() | OFF |
| Project Manager → Code Generator → STM32Cube MCU packages and embedded software packs | **Copy only the necessary library files**(`Drivers/` をプロジェクトの中に置き、コミットする) |
| Project Manager → Code Generator → Generate peripheral initialization as a pair of '.c/.h' files per peripheral | **ON** |
| Project Manager → Code Generator → Keep User Code when re-generating | ON |
| Project Manager → Code Generator → Delete previously generated files when not re-generated | ON |

## 2. System Core

### SYS・DEBUG

| 項目 | 設定 | 備考 |
|---|---|---|
| Debug | **Serial Wire** | これを設定しないと PA15・PB4(JTAG と兼用のピン)が LED_MODE1・WALL_LED_FL_R に使えない |
| Timebase Source | SysTick | |

### RCC・PWR

| 項目 | 設定 | 備考 |
|---|---|---|
| High Speed Clock (HSE) | **Crystal/Ceramic Resonator** | Y1 CSTNE10M0G52A000R0(ToraNeko の CSTNE10M0G52Z000R0 と同じ仕様。負荷容量は中にある) |
| Low Speed Clock (LSE) | Disable | |
| 電源(Supply Source) | **LDO**(初めの値のまま) | H562 の VFQFPN68 は LDO だけ(SMPS はない)。H725 のときの「Direct SMPS にしないと応答しなくなる」は、もう気にしなくてよい |
| Power Regulator Voltage Scale | **Scale 0**(VOS0) | 200MHz を超えるので VOS0(DS14258 の表48: PLL の出力は VOS0 で 250MHz まで、VOS1 で 200MHz まで) |

### ICACHE・MPU

| 項目 | 設定 | 備考 |
|---|---|---|
| ICACHE | **Enabled**(2-way) | Flash の待ち(240MHz で 5 回)を隠す |
| MPU | 使わない | 内蔵の RAM にデータのキャッシュがないので、キャッシュしない所を決める必要がない(`docs/firmware_memory.md`) |

### GPIO(出力・入力)

| ピン | モード | 初めの出力 | プル | 速さ | User Label | 備考 |
|---|---|---|---|---|---|---|
| PC8 | GPIO_Output | Low | なし | Low | `LED_MODE0` | モードの 1(2026-11-27 に PA0 から) |
| PA15 | GPIO_Output | Low | なし | Low | `LED_MODE1` | モードの 2(2026-11-27 に PA1 から) |
| PC10 | GPIO_Output | Low | なし | Low | `LED_MODE2` | モードの 4(2026-11-27 に PA2 から) |
| PA0 | GPIO_Output | Low | なし | Low | `LED_WALL_FL` | 壁の表示 FL(2026-11-27) |
| PA1 | GPIO_Output | Low | なし | Low | `LED_WALL_L` | 壁の表示 L |
| PA2 | GPIO_Output | Low | なし | Low | `LED_WALL_R` | 壁の表示 R |
| PC13 | GPIO_Output | Low | なし | **Low**(PC13〜15 は 2MHz 以下) | `LED_WALL_FR` | 壁の表示 FR |
| PC11 | GPIO_Output | Low | なし | Low | `LED_STATUS0` | 状態の LED 0(前の LED の左) |
| PC12 | GPIO_Output | Low | なし | Low | `LED_STATUS1` | 状態の LED 1(前の LED の右) |
| PD12 | GPIO_Output | Low | なし | Low | `LED_NUM0` | No. の 1(2026-11-27 に PA3 から) |
| PD11 | GPIO_Output | Low | なし | Low | `LED_NUM1` | No. の 2(2026-11-27 に PB10 から) |
| PB12 | GPIO_Output | Low | なし | Low | `LED_NUM2` | No. の 4 |
| PB13 | GPIO_Output | Low | なし | Low | `LED_NUM3` | No. の 8 |
| PE0 | GPIO_Output | Low | なし | Low | `LED_FRONT` | 前の LED(2026-11-26 に PB3 から) |
| PB4 | GPIO_Output | Low | なし | **High** | `WALL_LED_FL_R` | 壁センサの発光 FL と R(消灯で始める) |
| PB5 | GPIO_Output | Low | なし | **High** | `WALL_LED_L_FR` | 壁センサの発光 L と FR |
| PB2 | GPIO_Output | **Low** | なし | Low | `MOT_EN` | モータードライバのスリープ。L で始める(モーターは止まったまま) |
| PC6 | GPIO_Output | **High** | なし | High | `ENC_L_CS` | エンコーダの CS は High(選ばない)で始める |
| PC7 | GPIO_Output | **High** | なし | High | `ENC_R_CS` | 同上 |
| PB10 | GPIO_Output | **High** | なし | High | `IMU_CS` | 同上(2026-11-27 に PA15 から) |
| PC15 | GPIO_Output | Low | なし | **Low**(PC13〜15 は 2MHz 以下) | `ENC_CAL` | エンコーダの校正(ふだんは L) |
| PC14 | GPIO_Input | - | なし(外付けの 10k で引き上げ。押すと L) | - | `SW` | スイッチ SW2 |
| PC9 | GPIO_Input | - | なし(外付けの R40 10k で引き上げ) | - | `MOT_nFAULT` | L で異常 |
| PB11 | GPIO_EXTI11 | - | なし | - | `IMU_INT` | **External Interrupt Mode with Rising edge**。LSM6DSR の INT1(データの準備ができた)。2026-11-26 に PD2 から PB3、2026-11-27 に PB11 へ(IMU のほうを向いた辺) |
| PB3 | GPIO_Output | Low | なし | Low | - | 使わないピン(回路図では ×)。浮かせないように出力の L にする |

- CS は High で始める。Low で始めると、電源を入れた直後に IMU・エンコーダが選ばれた状態になる(ToraNeko と同じ)
- 壁センサの発光と MOT_EN は Low で始める(消灯・モーターは止まったまま)

## 3. クロック(Clock Configuration)

**240MHz** で動かす(H562 の上限は 250MHz。TIM1 の 80kHz・20kHz がちょうど割り切れる 240MHz にした)。数値は DS14258 の表48(PLL の入力 2〜16MHz、VCO 128〜560MHz、VOS0 で出力 250MHz まで)と ADC の特性の表(ADC のクロック 75MHz まで)で確かめた。CubeMX は上限を超えると赤で知らせるので、赤くないことを確かめる。

| 項目 | 値 | ToraNeko |
|---|---|---|
| Input frequency(HSE) | **10 MHz** | 10 MHz |
| PLL1 Source Mux | HSE | HSE |
| PLL1M | **/2**(PLL の入力 5MHz) | /5 |
| PLL1N | **×96**(VCO 480MHz) | ×200 |
| PLL1P | **/2 → 240MHz** | /4 |
| PLL1Q | **/4 → 120MHz**(SPI の元) | - |
| System Clock Mux | PLLCLK | PLLCLK |
| **SYSCLK・HCLK・CPU** | **240 MHz** | 100 MHz |
| APB1・APB2・APB3 Prescaler | **/1 → 240MHz**(タイマーも 240MHz) | APB1 /2・APB2 /1 |
| ADC・DAC Clock Mux | **HCLK(240MHz)** | - |
| ADC の Clock Prescaler(ADC の画面) | **/4 → 60MHz**(上限 75MHz) | - |
| SPI1,2,3 Clock Mux | **PLL1Q(120MHz)**(SPI1 は IMU、SPI2 はエンコーダ) | - |
| USART1 Clock Mux | PCLK2(240MHz) | - |

**タイマーのクロックは全部 240MHz にそろう**ので、分周の計算が簡単になる(ToraNeko は 100MHz)。Flash の待ちの回数(LATENCY)は CubeMX が決める(240MHz で 5 回)。

## 4. タイマー

| 用途 | タイマー | モード | PSC | ARR(Period) | 周波数 | 備考 |
|---|---|---|---|---|---|---|
| モーターの PWM | **TIM1** CH1〜CH4 | PWM Generation CH1〜CH4、Counter Mode **Center Aligned mode 1** | 0 | **1500** | **80 kHz** | センターアラインドは 0 → 1500 → 0 で 1 周期(2 × 1500 / 240MHz = 12.5µs)。**Repetition Counter = 7**(山と谷で 1 つずつ数えるので、8 つで PWM 4 周期 = 20kHz に 1 回)。**Trigger Event Selection(TRGO)= Update Event**(ADC1・ADC2 を起動)。CH の Pulse は 0 で始める |
| 吸引ファンの PWM | **TIM16** CH1(PB8) | PWM Generation CH1 | 0 | **3000-1** | **80 kHz** | TIM1 と同じ周期(12.5µs)。TIM16 はほかのタイマーに合わせる仕組みがないので、TIM1 と同時にスタートさせる(同じクロックなのでずれない) |
| ブザー | **TIM17** CH1(PB9) | PWM Generation CH1 | 240-1(1MHz) | 音の高さで変える(例: 2kHz なら 500-1) | | KOGUMA と同じく PWM で鳴らす |
| 4kHz の処理を起こす | **TIM6**(割り込みの番号だけ使う) | Activated | - | - | - | TIM6 自体は動かさない。20kHz の処理から 5 回に 1 回 `NVIC_SetPendingIRQ(TIM6_IRQn)` で 4kHz の処理を起こす(`docs/software.md` の4章)。NVIC で `TIM6_IRQn` を有効にする(H5 の名前は CubeMX で確かめる) |
| 処理時間を測る・µs の待ち | **TIM5** | Activated(内部クロック) | 240-1 | 0xFFFFFFFF | 1 MHz で数える | 32 ビットのフリーラン(ToraNeko と同じ) |

## 5. ADC

> **2026-11-28: 今の `Core/` は DMA を使わない形**(0 章の表)。下の DMA の行は前の案として残す。

どちらの ADC も **TIM1 の TRGO(20kHz)で同時に起動**し、DMA で `DMA_BUF` の配列に入れる。壁センサの発光は、20kHz の処理の中で「次に読む組」に切り替えておく(点けてから読むまで約 50µs あるので、受光のアンプは十分に落ち着く。`docs/software.md` の 4.3)。**H562 の ADC は 12 ビット**(H725 は 16 ビット)。細かさが要る値は、20kHz の処理の中で足し合わせて平均する(ファンの電流など。`docs/spec.md` の「ファンの電流の計測」)。

| 項目 | ADC1(壁センサ・ファンの電流) | ADC2(モーターの電流・電池) |
|---|---|---|
| Clock Prescaler | 非同期 /4(60MHz) | 同じ |
| Resolution | 12 bit | 12 bit |
| Scan Conversion Mode | Enable | Enable |
| Continuous Conversion Mode | Disable | Disable |
| DMA Continuous Requests | Enable | Enable |
| External Trigger Conversion Source | **Timer 1 Trigger Out event** | **Timer 1 Trigger Out event** |
| External Trigger Conversion Edge | Rising edge | Rising edge |
| Overrun behaviour | Overrun data overwritten | Overrun data overwritten |
| Oversampling | Disable(最初) | Disable(最初) |
| Number Of Conversion | 5 | 5 |
| DMA | GPDMA1 Channel 0(ADC1 → メモリ、Half Word) | GPDMA1 Channel 1(ADC2 → メモリ、Half Word) |

| ADC | Rank | チャンネル | ピン | 信号 | Sampling Time |
|---|---|---|---|---|---|
| ADC1 | 1 | IN10 | PC0 | WALL_FL | 12.5 cycles |
| ADC1 | 2 | IN11 | PC1 | WALL_L | 12.5 cycles |
| ADC1 | 3 | IN12 | PC2 | WALL_R | 12.5 cycles |
| ADC1 | 4 | IN13 | PC3 | WALL_FR | 12.5 cycles |
| ADC1 | 5 | IN9 | PB0 | FAN_ISENSE | 12.5 cycles |
| ADC2 | 1 | IN4 | PC4 | MOT_L_I | 12.5 cycles |
| ADC2 | 2 | IN18 | PA4 | MOT_R_I | 12.5 cycles |
| ADC2 | 3 | IN8 | PC5 | MOT_L_CMS | 12.5 cycles |
| ADC2 | 4 | IN15 | PA3 | MOT_R_CMS | 12.5 cycles |
| ADC2 | 5 | IN5 | PB1 | BATT | **47.5 cycles**(分圧の 47k・10k を C9 10nF で受けているので長めに) |

- 1 本の変換は 12.5 + 12.5 = 25 クロック(60MHz で約 0.4µs)。5 本で約 2〜3µs
- **DMA を回し続ける**: H5 の GPDMA には H7 の「Circular」の設定がなく、**linked-list の 1 つのノードを自分に戻す**形で回し続ける(CubeMX の GPDMA1 の画面で Channel 0・1 を Linked-List にする。**作るときに確かめる**)。または、20kHz の処理の最後に次の DMA を自分で始める
- ADC2 の DMA の終わり(GPDMA1 Channel 1 の割り込み)が **20kHz の処理**になる。この割り込みは HAL を通さず、レジスタを直接読んで書く(`docs/calc/cpu_est/README.md`)
- 起動したら、使う前に一度だけ校正する(`HAL_ADCEx_Calibration_Start(&hadc1, ADC_SINGLE_ENDED)`、ADC2 も。H5 にはリニアリティの校正はない(DS14258 の表5))

## 6. SPI

> **2026-11-28: 今の `Core/` は DMA を使わない形**(0 章の表)。下の DMA の行は前の案として残す。

| 項目 | SPI2(エンコーダ MT6835 × 2) | **SPI1**(IMU LSM6DSR。2026-11-27 に SPI3 から) | ToraNeko |
|---|---|---|---|
| ピン | PA12 SCK / PB14 MISO / PB15 MOSI(CubeMX の初めのピンから付け替える) | PA5 SCK / PA6 MISO / PA7 MOSI | |
| Mode | Full-Duplex Master | Full-Duplex Master | 同じ |
| Hardware NSS | Disable(CS は GPIO) | Disable | 同じ |
| Data Size | 8 bit | 8 bit | 同じ |
| First Bit | MSB | MSB | 同じ |
| CPOL / CPHA | **High / 2 Edge(モード3)**(MT6835 のデータシート 7.6) | High / 2 Edge(モード3) | IMU は同じ。エンコーダは AS5047P でモード1 だった |
| Prescaler | **/8 → 15 MHz**(MT6835 は 16.6MHz まで) | **/16 → 7.5 MHz**(LSM6DSR は 10MHz まで) | 6.25MHz |
| DMA | RX GPDMA1 Channel 2、TX Channel 3(Byte) | RX GPDMA1 Channel 4、TX Channel 5(Byte)(SPI1 の要求) | なし |

- MT6835 は CS を下げてから最初のクロックまで 100ns 以上あける(データシートの TL)。角度は「バースト読み出し」(命令 1010、番地 0x003 から 0x006 まで続けて読む)で、CS を下げた瞬間の角度が読める
- エンコーダ・IMU の DMA の割り込みも、HAL を通さずレジスタを直接書く(CPU を軽くするため)

## 7. USART1(PC・BLE との通信)

> **2026-11-28: 今の `Core/` は DMA を使わない形**(0 章の表)。下の DMA の行は前の案として残す。

| 項目 | 設定 | ToraNeko |
|---|---|---|
| Mode | **Asynchronous** | Single Wire(送るだけ) |
| Baud Rate | 115200 bps(まず動かす)→ あとで 1Mbps | 115200 bps |
| Word Length / Parity / Stop | 8 bit / None / 1 | 同じ |
| Data Direction | **Receive and Transmit** | Transmit Only |
| ピン | PB6 TX / PB7 RX(CubeMX の初めのピンから付け替える) | PA9 |
| DMA | USART1_RX → GPDMA2 Channel 0(回し続ける。ADC と同じく linked-list)、USART1_TX → GPDMA2 Channel 1(Byte) | TX だけ |
| 割り込み | USART1 global interrupt を有効(受けの途切れ(IDLE)を知るため) | |

- PB7(UART_RX)は基板の R101 4.7kΩ で引き上げてあるので、中のプルアップは要らない
- 有線(TP1)と BLE(HY0020)はどちらもこの 1 本に入る(ダイオードのワイヤード AND、`docs/ble.md` の9章)

## 8. NVIC(割り込みの優先度)

> **2026-11-28: 今の `Core/` は DMA を使わない形**(0 章の表)。下の DMA の行は前の案として残す。

| 割り込み | 優先度 | 用途 |
|---|---|---|
| GPDMA1 Channel 1(ADC2) | **0** | 20kHz の処理(電流の制御、壁センサの組の切り替え) |
| GPDMA1 Channel 2(SPI2 RX)、Channel 4(SPI1 RX)、EXTI11(IMU_INT) | 1 | エンコーダ・IMU の読み取り |
| TIM6 | 2 | 4kHz の処理 |
| GPDMA2 Channel 0・1(USART1)、USART1 | 5 | 通信 |
| SysTick | CubeMX の初めの値 | `HAL_Delay` 用。割り込みの中では `HAL_Delay` を使わない |
| GPDMA1 Channel 0(ADC1)、Channel 3・5(SPI の TX) | 割り込みは使わない(無効) | ADC1 は ADC2 と同時に終わるので、20kHz の処理で読む |

## 9. 作ったあとにやること

1. `Core/Src/main.c` の USER CODE 欄に `app_init();` と `app_loop();` の呼び出しだけを書く
2. リンカの設定(CubeMX が作る `*_FLASH.ld`)に、`DMA_BUF` の置き場所(`.dma_buf`)を足す(`docs/firmware_memory.md` の 4.1)
3. `App/` をビルドに加える(下の「CMake のビルド設定」)
4. `cmake --preset Debug && cmake --build --preset Debug` でビルドが通ること、STLINK-V3MODS で書き込めることを確かめる
5. `software/main-controller/KOGUMA-Mk4/` を `Drivers/` も含めてコミットする(`build/` は `.gitignore` で除外)

- ブートローダ(ステップ13)を入れるまでは、プログラムは Flash の先頭(0x08000000)から。入れるときに 0x08010000(ブートローダ 64KB のあと)に変える(`docs/spec.md` の「内蔵Flashの使い方」)

## 10. CMake のビルド設定

ToraNeko の `CUBEMX_SETUP.md` の10と同じです。プロジェクトの一番上の `CMakeLists.txt` に `App/` を足します。

```cmake
# User sources (App/). Add one file per line as each step is implemented
set(APP_SOURCES
    App/app.c
    # App/drv/*.c などはステップごとに足す
)

target_sources(${CMAKE_PROJECT_NAME} PRIVATE
    ${APP_SOURCES}
)

target_include_directories(${CMAKE_PROJECT_NAME} PRIVATE
    App
)

# Warnings for user code only (App/); generated HAL code is left as is
set_source_files_properties(${APP_SOURCES} PROPERTIES COMPILE_OPTIONS "-Wall;-Wextra;-Wdouble-promotion")
# 制御・電流・エンコーダは Debug でも -O2(CPU を軽くするため。docs/calc/cpu_est/README.md)。ToraNeko の APP_FAST_SOURCES と同じ考え
```

- ソースは `file(GLOB ...)` を使わず 1 ファイルずつ書く
- インクルードは `App/` を起点に書く(例: `#include "drv/encoder.h"`)
- 警告は `APP_SOURCES` のファイルだけに付ける。MK4 は `-Wdouble-promotion` も付ける(float の計算が double にならないように)

## 11. VS Code の設定

ToraNeko の `CUBEMX_SETUP.md` の11と同じです(STM32Cube for Visual Studio Code、arm-none-eabi-gcc 11 以降、CMake、Ninja、STM32CubeProgrammer、Serial Monitor)。

- プロジェクトを開く: `software/main-controller/KOGUMA-Mk4/` を VS Code で開き、CMake のプリセット `Debug` を選ぶ
- ST-LINK は機体に電気を送らないので、書き込むときも機体の電源を入れる

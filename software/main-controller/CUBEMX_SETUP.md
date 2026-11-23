# CubeMX 設定(ステップ0)

STM32CubeMX で `KOGUMA-Mk4` プロジェクトを新しく作るときの `.ioc` の設定値です。ToraNeko.Mk3 の `CUBEMX_SETUP.md` と同じ形にしてあります。コードは CMake 形式で作り、VS Code(STM32Cube for Visual Studio Code 拡張)でビルド・書き込み・デバッグします。

- ピンは [../../docs/pinmap.md](../../docs/pinmap.md) の割り当て表のとおり
- 時刻の作り方(TIM1 を元に 20kHz・1kHz)は [../../docs/software.md](../../docs/software.md) の4章
- RAM・キャッシュ・DMA の決まりは [../../docs/firmware_memory.md](../../docs/firmware_memory.md)
- 「ToraNeko」列は参考用に ToraNeko.Mk3(F411、100MHz)の設定を載せています

## 1. プロジェクトを作る

| 項目 | 設定 |
|---|---|
| MCU | **STM32H725RGVx**(VFQFPN68) |
| Project Name | `KOGUMA-Mk4` |
| 作る場所 | `software/main-controller/KOGUMA-Mk4/` |
| Project Manager → Project → **Toolchain / IDE** | **CMake**(STM32CubeIDE は使わない) |
| Project Manager → Project → Do not generate the main() | OFF |
| Project Manager → Code Generator → STM32Cube MCU packages and embedded software packs | **Copy only the necessary library files**(`Drivers/` をプロジェクトの中に置き、コミットする) |
| Project Manager → Code Generator → Generate peripheral initialization as a pair of '.c/.h' files per peripheral | **ON** |
| Project Manager → Code Generator → Keep User Code when re-generating | ON |
| Project Manager → Code Generator → Delete previously generated files when not re-generated | ON |

## 2. System Core

### SYS

| 項目 | 設定 | 備考 |
|---|---|---|
| Debug | **Serial Wire** | これを設定しないと PA15・PB3・PB4(JTAG と兼用のピン)が IMU_CS・LED_FRONT・WALL_LED_FL_R に使えない |
| Timebase Source | SysTick | |

### RCC

| 項目 | 設定 | 備考 |
|---|---|---|
| High Speed Clock (HSE) | **Crystal/Ceramic Resonator** | Y1 CSTNE10M0G52Z000R0(ToraNeko と同じ。負荷容量は中にある) |
| Low Speed Clock (LSE) | Disable | |
| **Power Parameters → Supply Source** | **PWR_DIRECT_SMPS_SUPPLY** | **いちばん大事**。VFQFPN68 は SMPS だけ。初めの値の LDO のまま書き込むと MCU が応答しなくなる(復旧のしかたは `docs/firmware_memory.md` の6章、TP4) |
| Power Parameters → Power Regulator Voltage Scale | **Scale 1**(VOS1) | 400MHz まで。520MHz に上げるときに Scale 0 にする |

### CORTEX_M7

| 項目 | 設定 | 備考 |
|---|---|---|
| CPU ICache | **Enabled** | 命令のキャッシュはいつでも安全 |
| CPU DCache | **Disabled**(最初) | 動いてから Enabled にする(`docs/firmware_memory.md` の5章) |
| MPU Control Mode | Background Region Privileged accesses only + MPU Enabled during hard fault, NMI and FAULTMASK handlers | |
| MPU Region 0 | CubeMX が最初から入れている設定(Base 0x0、Size 4GB、SubRegion Disable 0x87、Access Permission ALL ACCESS NOT PERMITTED)があれば**そのまま残す** | ST が勧める、使っていない番地を読みにいかないための設定 |
| **MPU Region 1** | Enable、Base Address **0x30000000**、Size **32KB**、SubRegion Disable 0x0、TEX field **level 1**、Access Permission ALL ACCESS PERMITTED、Instruction Access DISABLE、Shareable **NOT**、Cacheable **NOT**、Bufferable **NOT** | SRAM1・SRAM2 を「キャッシュしない」にする。DMA の配列はすべてここ(`DMA_BUF`)。番号の大きいほうが勝つので、Region 0 より大きい番号にする |

### GPIO(出力・入力)

| ピン | モード | 初めの出力 | プル | 速さ | User Label | 備考 |
|---|---|---|---|---|---|---|
| PA0 | GPIO_Output | Low | なし | Low | `LED_MODE0` | モードの 1 |
| PA1 | GPIO_Output | Low | なし | Low | `LED_MODE1` | モードの 2 |
| PA2 | GPIO_Output | Low | なし | Low | `LED_MODE2` | モードの 4 |
| PA3 | GPIO_Output | Low | なし | Low | `LED_NUM0` | No. の 1 |
| PB10 | GPIO_Output | Low | なし | Low | `LED_NUM1` | No. の 2 |
| PB12 | GPIO_Output | Low | なし | Low | `LED_NUM2` | No. の 4 |
| PB13 | GPIO_Output | Low | なし | Low | `LED_NUM3` | No. の 8 |
| PB3 | GPIO_Output | Low | なし | Low | `LED_FRONT` | 前の LED |
| PB4 | GPIO_Output | Low | なし | **High** | `WALL_LED_FL_R` | 壁センサの発光 FL と R(消灯で始める) |
| PB5 | GPIO_Output | Low | なし | **High** | `WALL_LED_L_FR` | 壁センサの発光 L と FR |
| PB2 | GPIO_Output | **Low** | なし | Low | `MOT_EN` | モータードライバのスリープ。L で始める(モーターは止まったまま) |
| PC6 | GPIO_Output | **High** | なし | High | `ENC_L_CS` | エンコーダの CS は High(選ばない)で始める |
| PC7 | GPIO_Output | **High** | なし | High | `ENC_R_CS` | 同上 |
| PA15 | GPIO_Output | **High** | なし | High | `IMU_CS` | 同上 |
| PC15 | GPIO_Output | Low | なし | **Low**(PC13〜15 は 2MHz 以下) | `ENC_CAL` | エンコーダの校正(ふだんは L) |
| PC14 | GPIO_Input | - | なし(外付けの 10k で引き上げ。押すと L) | - | `SW` | スイッチ SW2 |
| PC9 | GPIO_Input | - | なし(外付けの R40 10k で引き上げ) | - | `MOT_nFAULT` | L で異常 |
| PD2 | GPIO_EXTI2 | - | なし | - | `IMU_INT` | **External Interrupt Mode with Rising edge**。LSM6DSR の INT1(データの準備ができた) |

- CS は High で始める。Low で始めると、電源を入れた直後に IMU・エンコーダが選ばれた状態になる(ToraNeko と同じ)
- 壁センサの発光と MOT_EN は Low で始める(消灯・モーターは止まったまま)

## 3. クロック(Clock Configuration)

最初は **400MHz(VOS1)** で動かします。数値は DS13311 の表(PLL の出力は VOS1 で 400MHz まで、VCO は 192〜836MHz、ADC は 16 ビットで 36MHz まで)で確かめてあります。CubeMX は上限を超えると赤で知らせるので、赤くないことを確かめます。

| 項目 | 値 | ToraNeko |
|---|---|---|
| Input frequency(HSE) | **10 MHz** | 10 MHz |
| PLL Source Mux | HSE | HSE |
| DIVM1 | **/5**(PLL の入力 2MHz) | /5 |
| DIVN1 | **×400**(VCO 800MHz) | ×200 |
| DIVP1 | **/2 → 400MHz** | /4 |
| DIVQ1 | **/4 → 200MHz**(SPI の元) | - |
| System Clock Mux | PLLCLK | PLLCLK |
| **SYSCLK・CPU** | **400 MHz** | 100 MHz |
| D1CPRE | /1 | - |
| HPRE(AXI・AHB) | **/2 → 200MHz** | /1 |
| D1PPRE・D2PPRE1・D2PPRE2・D3PPRE(APB1〜4) | **/2 → 100MHz**(タイマーは 200MHz) | APB1 /2・APB2 /1 |
| DIVM2 | /5(2MHz) | - |
| DIVN2 | ×180(VCO 360MHz) | - |
| DIVP2 | **/10 → 36MHz**(ADC の元) | - |
| ADC Clock Mux | **PLL2P(36MHz)** | - |
| SPI1,2,3 Clock Mux | **PLL1Q(200MHz)** | - |
| USART1 Clock Mux | PCLK2(100MHz) | - |

**タイマーのクロックは全部 200MHz にそろう**ので、分周の計算が簡単になります(ToraNeko は 100MHz)。520MHz に上げるとき(VOS0)は、この表を作り直します。

## 4. タイマー

| 用途 | タイマー | モード | PSC | ARR(Period) | 周波数 | 備考 |
|---|---|---|---|---|---|---|
| モーターの PWM | **TIM1** CH1〜CH4 | PWM Generation CH1〜CH4、Counter Mode **Center Aligned mode 1** | 0 | **2500** | **40 kHz** | センターアラインドは 0 → 2500 → 0 で 1 周期(2 × 2500 / 200MHz = 25µs)。**Repetition Counter = 3**(山と谷で 1 つずつ数えるので、4 つで PWM 2 周期 = 20kHz に 1 回)。**Trigger Event Selection(TRGO)= Update Event**(ADC1・ADC2 を起動)。CH の Pulse は 0 で始める |
| 吸引ファンの PWM | **TIM16** CH1(PB8) | PWM Generation CH1 | 0 | **5000-1** | **40 kHz** | TIM1 と同じ周期(25µs)。TIM16 はほかのタイマーに合わせる仕組みがないので、TIM1 と同時にスタートさせる(同じクロックなのでずれない) |
| ブザー | **TIM17** CH1(PB9) | PWM Generation CH1 | 200-1(1MHz) | 音の高さで変える(例: 2kHz なら 500-1) | | KOGUMA と同じく PWM で鳴らす |
| 1kHz の処理を起こす | **TIM6**(割り込みの番号だけ使う) | Activated | - | - | - | TIM6 自体は動かさない。20kHz の処理から `NVIC_SetPendingIRQ(TIM6_DAC_IRQn)` で 1kHz の処理を起こす(`docs/software.md` の4章)。NVIC で `TIM6_DAC_IRQn` を有効にする |
| 処理時間を測る・µs の待ち | **TIM5** | Activated(内部クロック) | 200-1 | 0xFFFFFFFF | 1 MHz で数える | 32 ビットのフリーラン(ToraNeko と同じ) |

## 5. ADC

どちらの ADC も **TIM1 の TRGO(20kHz)で同時に起動**し、DMA で `DMA_BUF` の配列に入れます。壁センサの発光は、20kHz の処理の中で「次に読む組」に切り替えておきます(点けてから読むまで約 50µs あるので、受光のアンプは十分に落ち着く。`docs/software.md` の 4.3)。

| 項目 | ADC1(壁センサ・ファンの電流) | ADC2(モーターの電流・電池) |
|---|---|---|
| Resolution | 16 bit | 16 bit |
| Scan Conversion Mode | Enable | Enable |
| Continuous Conversion Mode | Disable | Disable |
| Conversion Data Management Mode | **DMA Circular Mode** | **DMA Circular Mode** |
| External Trigger Conversion Source | **Timer 1 Trigger Out event** | **Timer 1 Trigger Out event** |
| External Trigger Conversion Edge | Rising edge | Rising edge |
| Overrun behaviour | Overrun data overwritten | Overrun data overwritten |
| Number Of Conversion | 5 | 5 |
| DMA | DMA1 Stream0、Peripheral to Memory、**Circular**、Half Word | DMA1 Stream1、Peripheral to Memory、**Circular**、Half Word |

| ADC | Rank | チャンネル | ピン | 信号 | Sampling Time |
|---|---|---|---|---|---|
| ADC1 | 1 | INP10 | PC0 | WALL_FL | 8.5 cycles |
| ADC1 | 2 | INP11 | PC1 | WALL_L | 8.5 cycles |
| ADC1 | 3 | INP3 | PA6 | WALL_R | 8.5 cycles |
| ADC1 | 4 | INP7 | PA7 | WALL_FR | 8.5 cycles |
| ADC1 | 5 | INP9 | PB0 | FAN_ISENSE | 8.5 cycles |
| ADC2 | 1 | INP4 | PC4 | MOT_L_I | 8.5 cycles |
| ADC2 | 2 | INP18 | PA4 | MOT_R_I | 8.5 cycles |
| ADC2 | 3 | INP8 | PC5 | MOT_L_CMS | 8.5 cycles |
| ADC2 | 4 | INP19 | PA5 | MOT_R_CMS | 8.5 cycles |
| ADC2 | 5 | INP5 | PB1 | BATT | **32.5 cycles**(分圧の 47k・10k を C9 10nF で受けているので長めに) |

- 5 本の変換は合わせて約 3µs(36MHz、16 ビット)
- ADC2 の DMA の終わり(`DMA1_Stream1_IRQn`)が **20kHz の処理**になる
- 起動したら、使う前に一度だけ校正する(`HAL_ADCEx_Calibration_Start(&hadc1, ADC_CALIB_OFFSET_LINEARITY, ADC_SINGLE_ENDED)`、ADC2 も)

## 6. SPI

| 項目 | SPI2(エンコーダ MT6835 × 2) | SPI3(IMU LSM6DSR) | ToraNeko |
|---|---|---|---|
| ピン | PA12 SCK / PB14 MISO / PB15 MOSI(CubeMX の初めのピンから付け替える) | PC10 SCK / PC11 MISO / PC12 MOSI | |
| Mode | Full-Duplex Master | Full-Duplex Master | 同じ |
| Hardware NSS | Disable(CS は GPIO) | Disable | 同じ |
| Data Size | 8 bit | 8 bit | 同じ |
| First Bit | MSB | MSB | 同じ |
| CPOL / CPHA | **High / 2 Edge(モード3)**(MT6835 のデータシート 7.6) | High / 2 Edge(モード3) | IMU は同じ。エンコーダは AS5047P でモード1 だった |
| Prescaler | **/16 → 12.5 MHz**(MT6835 は 16.6MHz まで) | **/32 → 6.25 MHz**(LSM6DSR は 10MHz まで) | 6.25MHz |
| DMA | RX DMA1 Stream2、TX DMA1 Stream3(Normal、Byte) | RX DMA1 Stream4、TX DMA1 Stream5(Normal、Byte) | なし |

- MT6835 は CS を下げてから最初のクロックまで 100ns 以上あける(データシートの TL)。角度は「バースト読み出し」(命令 1010、番地 0x003 から 0x006 まで続けて読む)で、CS を下げた瞬間の角度が読める

## 7. USART1(PC・BLE との通信)

| 項目 | 設定 | ToraNeko |
|---|---|---|
| Mode | **Asynchronous** | Single Wire(送るだけ) |
| Baud Rate | 115200 bps(まず動かす)→ あとで 1Mbps | 115200 bps |
| Word Length / Parity / Stop | 8 bit / None / 1 | 同じ |
| Data Direction | **Receive and Transmit** | Transmit Only |
| ピン | PB6 TX / PB7 RX(CubeMX の初めのピンから付け替える) | PA9 |
| DMA | USART1_RX → DMA2 Stream0(**Circular**、Byte)、USART1_TX → DMA2 Stream1(Normal、Byte) | TX だけ |
| 割り込み | USART1 global interrupt を有効(受けの途切れ(IDLE)を知るため) | |

- PB7(UART_RX)は基板の R101 4.7kΩ で引き上げてあるので、中のプルアップは要らない
- 有線(TP1)と BLE(HY0020)はどちらもこの 1 本に入る(ダイオードのワイヤード AND、`docs/ble.md` の9章)

## 8. NVIC(割り込みの優先度)

| 割り込み | 優先度 | 用途 |
|---|---|---|
| DMA1 Stream1(ADC2) | **0** | 20kHz の処理(電流の制御、壁センサの組の切り替え) |
| DMA1 Stream2(SPI2 RX)、DMA1 Stream4(SPI3 RX)、EXTI2(IMU_INT) | 1 | エンコーダ・IMU の読み取り |
| TIM6_DAC | 2 | 1kHz の処理 |
| DMA2 Stream0・1(USART1)、USART1 | 5 | 通信 |
| SysTick | CubeMX の初めの値 | `HAL_Delay` 用。割り込みの中では `HAL_Delay` を使わない |
| DMA1 Stream0(ADC1)、Stream3・5(SPI の TX) | 割り込みは使わない(無効) | ADC1 は ADC2 と同時に終わるので、20kHz の処理で読む |

## 9. 作ったあとにやること

1. `Core/Src/main.c` の USER CODE 欄に `app_init();` と `app_loop();` の呼び出しだけを書く
2. リンカの設定(`STM32H725RGVX_FLASH.ld`)に、`DMA_BUF` の置き場所(RAM_D2 と `.dma_buf`)を足す(`docs/firmware_memory.md` の 4.1)
3. `App/` をビルドに加える(下の「CMake のビルド設定」)
4. `cmake --preset Debug && cmake --build --preset Debug` でビルドが通ること、STLINK-V3MODS で書き込めることを確かめる
5. **Direct SMPS になっているか**を確かめる: `Core/Src/main.c` の `SystemClock_Config()` に `HAL_PWREx_ConfigSupply(PWR_DIRECT_SMPS_SUPPLY);` があること(`PWR_LDO_SUPPLY` なら書き込まない)
6. `software/main-controller/KOGUMA-Mk4/` を `Drivers/` も含めてコミットする(`build/` は `.gitignore` で除外)

- ブートローダ(ステップ13)を入れるまでは、プログラムは Flash の先頭(0x08000000)から。入れるときに 0x08020000 に変える

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
```

- ソースは `file(GLOB ...)` を使わず 1 ファイルずつ書く
- インクルードは `App/` を起点に書く(例: `#include "drv/encoder.h"`)
- 警告は `APP_SOURCES` のファイルだけに付ける。MK4 は `-Wdouble-promotion` も付ける(float の計算が double にならないように)

## 11. VS Code の設定

ToraNeko の `CUBEMX_SETUP.md` の11と同じです(STM32Cube for Visual Studio Code、arm-none-eabi-gcc 11 以降、CMake、Ninja、STM32CubeProgrammer、Serial Monitor)。

- プロジェクトを開く: `software/main-controller/KOGUMA-Mk4/` を VS Code で開き、CMake のプリセット `Debug` を選ぶ
- ST-LINK は機体に電気を送らないので、書き込むときも機体の電源を入れる

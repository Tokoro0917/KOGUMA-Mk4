# KOGUMA MK4 ソフトの設計

2026-11-23 作成。同じ日に **ToraNeko.Mk3 のファームウェア(`toraneko.mk3/software/main-controller/`)と同じ作りにする**と決めた(ユーザー)。

回路は `hardware/kicad/KOGUMA-Mk4/`、ピンは `docs/pinmap.md`、制御の考え方は `docs/control.md`、無線とブートローダは `docs/ble.md`、RAM・キャッシュ・DMA の決まりは `docs/firmware_memory.md`。

## 0. 方針

- ソフトのフォルダは `software/main-controller/`(README・CubeMX の設定・操作とモード)
- **ToraNeko.Mk3 の main-controller と同じ作りにする**: 開発環境(CubeMX + CMake + VS Code)、フォルダと層(`App/` の config・drv・ctrl・maze・sys)、名前の付け方、書き方の決まり(素直に書く)、操作とモード、LED の合図、PC のテスト、作る順(ステップ)、ビューア。**ToraNeko の `App/` のコードを元にして**、MK4 で違う所を直す
- ToraNeko は KOGUMA(MK3、`KOGUMA.MkIIl`)のコードを機能ごとに確かめながら移したもの。MK4 は ToraNeko を元にし、KOGUMA は参照だけにする(KOGUMA にしかない機能(吸引の探索など)が要るときは、ToraNeko と同じやり方で確かめてから移す)
- MK3 の反省(`KOGUMA.MkIIl/docs/next_robot.md`)を最初から入れる: 電流・左右の車輪の速度・電池をいつもログに残す、モーターの定数を実測で決める、ADC を読む時刻をタイマーで決める、会場ごとの値を Flash に保存する
- **ToraNeko と違う所**(下の表)だけ、MK4 で新しく作る

| | ToraNeko.Mk3 | MK4 |
|---|---|---|
| MCU | STM32F411(100MHz) | STM32H725(400MHz から。`docs/firmware_memory.md` の決まりが要る) |
| モーターの制御 | 速度・角度の制御 → モーターの**電圧** | 速度・角度の制御 → **電流の目標 → 電流の制御(20kHz、INA241A3)** → duty |
| 制御の周期 | 2kHz(TIM11) | 電流 20kHz・エンコーダ 10kHz・制御 4kHz(壁センサの1巡と同じ。TIM1 を元にする。4章) |
| 壁センサの順番 | TIM3 で ADC を起動し、DMA の終わりで次の LED へ(1 周期で 4 回) | TIM1 で ADC1 を起動し、20kHz の割り込みで順番を進める(車輪・ファンの PWM と同じ位置で読む) |
| エンコーダ | AS5047P(14 ビット) | MT6835(21 ビット、CRC あり) |
| ブザー | なし(合図は LED だけ) | **あり**(LED と一緒に音も出す) |
| 前の LED | なし | D98(BLE のつながりを出す。案) |
| UART | 送るだけ | 送る・受ける(有線の TP1 と BLE。コマンドで値を変える、`docs/ble.md`) |
| 吸引 | 探索は吸引なし | 吸引ありの探索も作る(KOGUMA の吸引探索を確かめてから移す) |
| Flash | 後ろの 2 セクタに迷路とゴール | ブートローダ・プログラム・パラメータと迷路・ログ(8章) |
| 書き込み | STLINK だけ | STLINK と無線(ブートローダ、`docs/ble.md` の6章) |

## 1. 開発環境とビルド(ToraNeko と同じ)

| 項目 | 決定 |
|---|---|
| 開発環境 | **STM32CubeMX(コード生成、Toolchain = CMake)+ VS Code(STM32Cube for Visual Studio Code 拡張)**。CubeIDE は使わない |
| ビルド | `cmake --preset Debug && cmake --build --preset Debug`(CubeMX が作る `CMakePresets.json`)。成果物は `build/Debug/KOGUMA-Mk4.elf` |
| ライブラリ | STM32 HAL。20kHz の割り込みの中で重い所は、必要になったら LL・レジスタに置き換える |
| 書き込み・デバッグ | STLINK-V3MODS(J7、ToraNeko の J6 と同じ並び)。printf とログは UART → STLINK の仮想 COM ポート |
| CI | ToraNeko と同じ 2 つ: **firmware-build**(ARM のビルド、警告が 1 つでもあれば失敗、プログラムの大きさが Flash のセクタ 1〜3(384KB)に収まるか)と **maze-test**(PC のテスト、12章) |
| push の前 | 必ずビルドを通す(`App/` は `-Wall -Wextra` で警告なし) |

## 2. フォルダ(ToraNeko と同じ形)

```
software/
  main-controller/
    README.md               決定事項・ファイル構成・実装のステップ・モード一覧
    PIN_REQUIREMENTS.md     ピン(docs/pinmap.md から)と ToraNeko との違い
    CUBEMX_SETUP.md         .ioc の設定値
    TORANEKO_PORTING.md     ToraNeko のコードの棚卸しと、MK4 で変える所
    MODES.md                操作・LED・ブザー・モードの割り当て・保存
    tools/viewer.html       ビューア(ToraNeko のものを写して直す。BLE でつなぐを足す)
    tools/fw.py・tune.py    無線の書き込み・ターンの自動調整(docs/ble.md)
    logs/                   実機の出力
    test/                   PC で動かすテスト(CI で実行)
    KOGUMA-Mk4/             CubeMX(CMake)のプロジェクト
      KOGUMA-Mk4.ioc
      CMakeLists.txt        App/ の追加はここ
      Core/  Drivers/  cmake/   CubeMX が作る(USER CODE 欄以外は編集しない)
      App/                  自作のコードはすべてここ
        app.c/.h            app_init()・app_loop()
        config/             機体の定数(robot_params.h・ctrl_gains.h・run_params.h・turn_params.h …)
        drv/                ハードに直接触れる層(HAL を呼ぶのはここと sys/scheduler.c だけ)
        ctrl/               制御
        maze/               迷路(HAL に依存しない。ToraNeko からほぼそのまま)
        sys/                全体の管理
  bootloader/               自分のブートローダ(docs/ble.md の6章)
  ble-bridge/               HY0020(nRF52832)の橋渡し
```

### 2.1 ファイル(ToraNeko から変える・足すもの)

| 層 | ファイル | 中身 | ToraNeko との違い |
|---|---|---|---|
| drv | `motor.c` | TIM1 の duty、MOT_EN、nFAULT | TIM1(センターアラインド、80kHz) |
| drv | `current.c`(新) | ADC2(INA241A3 の電流 2 本・CMS 2 本・電池)を TIM1 で起動し、DMA で受ける | 新しい |
| drv | `wall.c` | 壁センサの発光と ADC1 | 順番を 20kHz の割り込みで進める(4章) |
| drv | `encoder.c` | MT6835 × 2(SPI2 + DMA、CRC) | AS5047P から変える |
| drv | `imu.c` | LSM6DSR(SPI3、INT1 の割り込みで読む) | ほぼ同じ |
| drv | `fan.c` | 吸引ファン(TIM16。TIM1 と同じ周期) | タイマー |
| drv | `buzzer.c`(新) | ブザー(TIM17) | 新しい(KOGUMA にはある) |
| drv | `uart.c` | 送る(DMA)と受ける(DMA のリングバッファ)、XON・XOFF | 受けるのを足す |
| drv | `flash_memory.c` | 内蔵 Flash の消す・書く・読む | H725 の書き方(32 バイト単位) |
| drv | `dma_buf.h`(新) | DMA の配列の置き場所と確かめ(`docs/firmware_memory.md`) | 新しい |
| ctrl | `current_ctrl.c`(新) | 電流の制御(20kHz)、電流の守り | 新しい |
| ctrl | `odometry.c` | 車輪の速さ、走った距離、加速度と合わせた速度の推定 | 加速度との相補フィルタを足す |
| ctrl | `control.c` | 速度・角度の制御 → **左右の電流の目標** | 出口を電圧から電流に |
| ctrl | `trajectory.c`・`run.c`・`wall_ctrl.c`・`wall_dist.c` | ToraNeko と同じ | 速さ・寸法の値 |
| maze | `maze_map.c`・`search.c`・`dijkstra.c`・`path.c` | ToraNeko と同じ | なし |
| sys | `scheduler.c` | 20kHz・10kHz・4kHz の処理を呼び、処理時間と間隔を記録 | 周期の作り方(4章) |
| sys | `mode.c`・`ui.c`・`goal.c`・`explore.c`・`shortest.c`・`adjust.c`・`turn_test.c`・`log.c`・`output.c`・`failsafe.c`・`flash.c` | ToraNeko と同じ | ブザー、吸引の探索、保存の場所 |
| sys | `cmd.c`(新) | コマンド(`status`・`get`・`set`・`save`・`run`・`stop`、`docs/ble.md` の4章) | 新しい |
| sys | `params.c`(新) | コマンドで変えられる値の表と、Flash への保存(8.3) | 新しい |

### 2.2 層の決まり(ToraNeko と同じ)

```
sys(explore / mode / cmd / ...)
 ├→ ctrl  →  drv  →  HAL(Core/, Drivers/)
 └→ maze
```

- 呼び出しは上の層から下の層への一方向だけ。`ctrl` と `maze` はお互いを知らない(つなぐのは `sys/explore.c` と `sys/shortest.c`)
- HAL を直接呼ぶのは `drv/` と `sys/scheduler.c` だけ
- `maze/` は `drv` も HAL も使わない(PC でそのままテストできる)
- `Core/` の生成コードには、USER CODE 欄に `App/` の関数呼び出しを 1 行書くだけ

## 3. MCU の設定

| 項目 | 設定 | 理由 |
|---|---|---|
| 電源 | **Direct SMPS**(CubeMX の初めの値の LDO にしない) | VFQFPN68 は SMPS だけ。LDO のまま書くと応答しなくなる(復旧は TP4、`docs/firmware_memory.md`) |
| クロック | HSE 10MHz(Y1、ToraNeko と同じ発振子)→ PLL。**最初は 400MHz(VOS1)**、動いてから 520MHz(VOS0)に上げる | ほかの問題と切り分けるため、余裕のある設定から |
| キャッシュ | 命令のキャッシュは最初から ON。データのキャッシュは最初 OFF、動いてから ON | `docs/firmware_memory.md` の決まりを守れば、ON にしても壊れない |
| RAM | ふつうの変数・スタックは DTCM、DMA の配列は SRAM1・2(`DMA_BUF`)、ログは AXI SRAM | |
| 時間を測る | TIM5(32 ビット)を 1MHz でフリーラン(ToraNeko と同じ)。細かく測るときは DWT のカウンタ | 割り込みの処理時間を常に見る |
| ms の待ち | SysTick(`HAL_GetTick()`、ToraNeko と同じ) | |
| ウォッチドッグ | IWDG 約 50ms。4kHz の処理で、20kHz・10kHz の処理が動いているのを確かめてからクリア | 割り込みが止まったらリセットして止まる |
| 数 | `float`(単精度)。定数は `0.5f`。`-Wdouble-promotion` を付ける | |

## 4. 時刻の作り方(MK4 で新しく作る所)

ToraNeko は 2kHz の割り込み 1 つで制御を回す。MK4 は電流の制御を 20kHz で回すので、**モーターの PWM のタイマー TIM1 をすべての時刻の元にする**。

### 4.1 TIM1

- モーターの PWM(CH1〜CH4 = 左右の IN1・IN2)。**センターアラインド**。PWM の周波数は **80kHz**(2026-11-26 決定。コアレスモーターの電流の上下を小さくするため。`docs/spec.md` の「モーターの PWM の周波数」。前は 40kHz から始めて 40〜80kHz で決める予定だった、`docs/control.md`)。400MHz のときタイマーのクロックは 200MHz で、ARR 2500(設定は `software/main-controller/CUBEMX_SETUP.md`)
- 繰り返しのカウンタで **4 周期に 1 回(20kHz)** ADC2 を起動する(400MHz のときタイマーのクロックは 200MHz で ARR 1250、Repetition Counter 7)
- 吸引ファンの TIM16 は、TIM1 と**同じ周期にして同時にスタート**する(同じクロックなのでずれない)。壁センサを読む位置が、車輪とファンの PWM のいつも同じ所になる

### 4.2 ADC2(モーターの電流と電池、20kHz)

- TIM1 の PWM の真ん中で起動し、MOT_L_I・MOT_R_I・MOT_L_CMS・MOT_R_CMS・BATT の 5 本を読む
- INA241A3 はシャントの電圧をいつも測るので、PWM の真ん中で読むと 1 周期の平均の電流に近い
- 読み終わり(DMA の終わり)で 20kHz の割り込み(4.4)

### 4.3 ADC1(壁センサとファンの電流)

- **ADC2 と同じく TIM1 の TRGO で、同時に起動する**(20kHz)。発光は、20kHz の処理の中で「次に読む組」に切り替えておく。点けてから読むまで約 50µs あるので、受光のアンプ(約 7µs で落ち着く)は十分に間に合い、読む位置はいつも PWM の同じ所になる
- 20kHz の処理を 5 つの順番に分け、**4kHz で 1 巡**する。点灯の値 − 消灯の値を使う(ToraNeko・KOGUMA と同じ考え。対角の 2 個ずつ点ける)。1 つの組が点いているのは 5 回に 1 回(50µs)なので、OPV332 の平均の電流は 10mA × 1/5 = 2mA

| 順番 | 発光 | ADC1 で読むもの |
|---|---|---|
| 0 | なし | FL・L・R・FR の消灯の値、ファンの電流 |
| 1 | FL と R | FL・R |
| 2 | L と FR | L・FR |
| 3・4 | なし | 空き(2 回読んで平均するなど、あとで使う) |

### 4.4 20kHz の処理(いちばん優先度が高い)

1. 電流を mA に直す
2. 電流の守り(目標を ±3A で頭打ち。5A を 1ms 超えたら止める)
3. 電流の制御: duty = (R × 目標 + Ke × モーターの角速度) / 電池の電圧 + PI(目標 − 測った電流)。duty の上限・回生の制限もここ(`docs/control.md` の4章)
4. duty を TIM1 に書く
5. 壁センサ: ADC1 の値(いま点いている組)を受け取り、順番を進めて、次の組の発光を点ける・消す
6. 偶数回目に、エンコーダの読み取り(SPI2 の DMA)を始める(10kHz)
7. 5 回に 1 回、壁センサの順番 2(L・FR)を読んだあとに **4kHz の処理**を起こす(2026-11-26 に 1kHz から。`docs/control.md` の4章。TIM6 の割り込みの番号を借りて `NVIC_SetPendingIRQ(TIM6_DAC_IRQn)`。TIM6 自体は動かさない)
8. 処理時間を記録する(ToraNeko の scheduler と同じく、いちばん長かった値と間隔)

### 4.5 そのほか

| 優先度 | 処理 | 周期 | 目安の時間 |
|---|---|---|---|
| 0(高) | 20kHz の処理(ADC2 の DMA の終わり) | 50µs | 3〜5µs |
| 1 | エンコーダ(SPI2 の DMA の終わり → 速度の推定)、IMU(INT1 → SPI3 の DMA) | 100µs・150µs | 1〜2µs |
| 2 | 4kHz の処理: 軌道 → 位置・向き → 速度・角度 → 電流の目標、壁制御、フェイルセーフ、ログ(ふだんは 4 回に 1 回 = 1kHz に間引いて残す。ターンの調整などのときだけ 4kHz で残す) | 250µs | 20〜50µs |
| 3 | UART の DMA、SysTick | | 短い |
| なし | メインのループ(`app_loop()`): モード、走る手順、迷路の計算、コマンド、保存、出力 | | |

合わせて CPU の 2〜3 割(4kHz の処理が 8〜20%、20kHz の処理が 6〜10%)。割り込みを使う所は、ToraNeko の決まりどおり、処理の流れをコメントで順に説明する。

## 5. 制御

中身は `docs/control.md`。ToraNeko の `control.c` との違い:

- 出口を「モーターの電圧」から**「左右の電流の目標」**にする。電圧への直し(逆起電力・巻線の抵抗・電池の電圧)は `current_ctrl.c` が 20kHz で行う
- 速度・角度は並進と回転に分け、軌道の加速度・角加速度はフィードフォワードとして電流に直接入れる
- 速度の推定(`odometry.c`)に IMU の加速度との相補フィルタを足す(`docs/control.md` の2章)
- 周期は `config/robot_params.h` の定数で持ち、ゲインは周期から換算する(ToraNeko と同じ)

## 6. 操作とモード(ToraNeko と同じ)

`toraneko.mk3/software/main-controller/MODES.md` と同じにする。MK4 の `MODES.md` は、それを写して下の違いだけ直す。

### 6.1 操作の流れ

1. 電源を入れる。「ロード中」(LED を 1 個ずつ順に点けて消す、約 1 秒)のあと、モード0 No.0
2. **左タイヤを回してモード(0〜7)、右タイヤを回して No.(0〜15)**を選ぶ
3. **スイッチ(SW2)で決定**。LED が全部 1 回点滅し、スタート待ち(選んだモードと No. を点滅)。もう一度押すと選び直し
4. 機体を置き、**前センサに手をかざす**(LED 全部点く)→ **手を離す**(全部消える)→ **1 秒後に走り出す**(この 1 秒でジャイロの 0 点を測る)
5. 走り終わると「うまくいった」(全部を 1 秒)→「ロード中」→ **同じモード・No. のまま** 2 に戻る
- No.0 と表にない番号は何もしない(スイッチを押しても決定しない)

### 6.2 LED

- 並びは ToraNeko と同じ形(t24 の基板: 左の角 2 個・V 字の先 3 個・右の角 2 個、`hardware/kicad/KOGUMA-Mk4_t24/README.md`)。**割り当ても ToraNeko と同じにする**: 真ん中の 3 個がモード(LED_MODE0〜2 = 4・2・1)、外側の 4 個が No.(LED_NUM0〜3 = 8・4・2・1)。t24 の基板はこの割り当てで置いた(2026-11-23。左の角 = No. の 8・4、V 字の先 = モードの 4・2・1、右の角 = No. の 2・1)
- 合図(ロード中・決定・スタート待ち・うまくいった・できなかった・保存中・電池が少ない・フェイルセーフ・走っている間の壁)も ToraNeko の `MODES.md` の表と同じ

### 6.3 MK4 で足すもの

| もの | 使い方 |
|---|---|
| ブザー | LED の合図と一緒に短い音を出す(決定・スタート・うまくいった・できなかった・フェイルセーフ)。KOGUMA と同じく、音で分かると機体を見なくてよい。音を消すパラメータも持つ |
| 前の LED(D98) | BLE がつながっている間は点ける(案) |
| コマンド | BLE・UART の `run <種類>` でも、同じ流れ(手をかざして離す)で走る(`docs/ble.md` の5章) |

### 6.4 モードの割り当て(ToraNeko と同じ)

| モード | 中身 | MK4 で足すもの |
|---|---|---|
| 0 | 探索 | 吸引ありの探索(KOGUMA の吸引探索を確かめてから) |
| 1 | 最短走行(No. は遅い順) | |
| 2 | 探索のターン調整 | |
| 3 | 最短走行のターン調整 | `turn_test`(PC から値を送って走り、ログを返す、`docs/ble.md` の5章) |
| 4 | 実験用 | **電流の制御の確かめとモーターの同定**(巻線抵抗・インダクタンス・Kt、`docs/control.md` の5章)、電流のステップ応答 |
| 5 | センサ(値の表示と調整) | |
| 6 | 基本調整 | エンコーダの校正(MT6835 の CAL_EN) |
| 7 | 出力と設定 | 出力は、つながっていれば走り終わりに自動でも送る(`docs/ble.md` の3章) |

## 7. 止める条件(フェイルセーフ)

止まったときの動き(モーターと吸引を止め、LED を全部点滅、スイッチで「ロード中」→ 選び直し、探索中なら最後の 5 区画を戻して迷路を保存)は ToraNeko と同じ。止める条件に MK4 の分を足す:

| 条件 | 見る所 | すること |
|---|---|---|
| ぶつかった・滑った(目標と推定のずれが大きい) | 4kHz | 止める(ToraNeko・KOGUMA と同じ) |
| モーターの電流が 5A を 1ms 超えた | 20kHz | すぐ duty 0・EN を L |
| nFAULT が L(MP6551 の過電流・過熱) | 4kHz | 止める |
| 電池が少ない | 電源を入れたとき(ToraNeko と同じ)と、4kHz(止まっているときの値か時間の平均) | 電源を入れたときなら何もできない(外側の LED の点滅)。走っていれば止める |
| 20kHz・10kHz の処理が止まった | 4kHz | 止める。4kHz の処理も止まれば IWDG がリセット |
| エンコーダ・IMU の読み取りの失敗が続いた | 4kHz | 止める |
| 回生で電池の電圧が上がった(13.5V 超) | 20kHz | 回生の電流の制限を強める |

止まった理由はログと `#STATUS` に残す。

## 8. 保存(内蔵 Flash)

### 8.1 Flash の分け方

| セクタ | 大きさ | 中身 |
|---|---|---|
| 0 | 128KB | ブートローダ(無線の書き込みでは消さない) |
| 1〜3 | 384KB | プログラム(先頭に見出し: 印・長さ・CRC32)。超えたら CI が失敗にする |
| 4・5 | 256KB | パラメータ・迷路・ゴール(2 つを交互に使う) |
| 6・7 | 256KB | ログ |

### 8.2 書き方

- 保存する場面と、迷路の呼び出し(モード7 No.15)は ToraNeko の `MODES.md` の5章と同じ(電源を入れたときは迷路は空、探索でスタートに戻ったとき・片道でゴールに着いたとき・フェイルセーフのときに保存)
- 確かめの数で、途中で電源が切れていないかを調べる(ToraNeko と同じ)。MK4 は 1 つのセクタにレコードを後ろへ足していき、読むときは確かめの合う一番新しいものを使う。いっぱいになったら、もう片方に最新を書いてから古いほうを消す
- **書くのは止まっているときだけ**。書いたあとに読み直すときは、その範囲のキャッシュを捨てる(`docs/firmware_memory.md` の5章)

### 8.3 コマンドで変える値(`sys/params.c`)

- ToraNeko は値を `config/*.h` の定数で持ち、変えるときは書き込み直す。MK4 も初めの値は `config/*.h` に置くが、**会場で変えたい値**(壁センサの感度、ターンの値など)は表にして、BLE・UART の `set` → `save` で変え、Flash に残せるようにする
- 表の 1 行 = 名前、値の場所、下限、上限、説明。新しい値は 1 行足すだけでコマンドからも変えられる

## 9. ログと出力(ToraNeko と同じ形)

- `sys/log.c`(記録)と `sys/output.c`(出力)。形は ToraNeko・KOGUMA と同じ(`#BEGIN 種類 …` と `#END 種類`、走行ログは 1 行目が列の名前の CSV)なので、**ビューアで読める**
- MK4 で足す列: **左右の電流の目標と測った値、左右の duty、電池の電圧、左右の車輪の速度、推定の速度と加速度**、CMS(電池の電流の目安)、エンコーダ・IMU のエラーの数、割り込みのいちばん長い時間
- 置き場所は AXI SRAM の 256KB(ToraNeko より大きい)。電流の制御を合わせるときだけ、20kHz で電流と duty を短く取るモードも持つ
- 走り終わったら Flash に書き、つながっていれば送る(`docs/ble.md` の3章)

## 10. 通信

`docs/ble.md` のとおり。UART は 1Mbaud。受けた行は割り込みの中では処理せず、メインのループで `sys/cmd.c` が読む。大きなログは 4KB ずつ `DMA_BUF` の送り口に写して送る。有線と無線はどちらも同じ UART に見えるので、区別しない。

## 11. ブートローダと書き込み

`docs/ble.md` の6章のとおり。ブートローダは `software/bootloader/`(別の CMake のプロジェクト)。プログラムは 0x08020000 から。STLINK で書くときのために、プログラムの ELF にブートローダも入れる。

## 12. テスト(ToraNeko と同じ形)

`software/main-controller/test/`。ホストの gcc でビルドする(`make`)。ToraNeko のテストを持ってきて、MK4 の分を足す。

| テスト | 確かめること | |
|---|---|---|
| `test_maze.c` | 迷路探索・最短経路・探索走行(仮の機体) | ToraNeko から |
| `test_mode.c` | モード選択と操作(時刻ごとの入力を与えて、LED・ブザーと結果を調べる) | ToraNeko から。ブザーを足す |
| `test_output.c` | 出力と走行ログ | ToraNeko から。列を足す |
| `test_flash.c` | 保存(Flash の代わりに配列。壊れた保存を読まないか) | ToraNeko から。レコードの形に合わせる |
| `test_trajectory.c`・`test_turn.c` | 軌道、ターンの終わりの位置・向き | ToraNeko から |
| `test_wall_dist.c` | 壁センサの値を距離に直す | ToraNeko から |
| `test_current.c`(新) | 電流の制御(モーターのモデル R・L・Ke と電池の内部抵抗を PC で動かす。追いつくか、3A で頭打ちか、回生で電圧が上がりすぎないか) | 新しい |
| `test_odometry.c`(新) | 速度の推定(作った加速度とエンコーダの値から、速度が正しく出るか) | 新しい |
| `test_cmd.c`(新) | コマンドの読み取り、`set` の範囲、CRC32 | 新しい |

## 13. 作る順(ToraNeko のステップに合わせる)

各ステップで「ToraNeko の該当するコードを読む → MK4 で変える点を決める → 作る → 実機・PC で確かめる」(ToraNeko と同じ進め方)。

| # | 中身 | 作るファイル | 確かめること |
|---|---|---|---|
| 0 | 空のプロジェクト(CubeMX → CMake、電源 Direct SMPS、クロック 400MHz、MPU) | `.ioc`、`Core/`、`App/app.c`、`CMakeLists.txt` | CI でビルドが通る。**TP4 の復旧を一度試す** |
| 1 | LED・ブザーとシリアル(printf) | `drv/led.c`、`drv/buzzer.c`、`drv/uart.c`、`drv/timebase.c` | LED の順送り、1 秒ごとの出力 |
| 2 | 時刻の元(TIM1)と 20kHz・4kHz の処理 | `sys/scheduler.c`、`drv/motor.c`(duty 0 のまま) | 周期と処理時間(ToraNeko の tick・period・busy と同じ出力) |
| 3 | エンコーダ(MT6835) | `drv/encoder.c` | 手で回した角度、CRC のエラーがない |
| 4 | IMU(LSM6DSR) | `drv/imu.c` | 静止のノイズ、回したときの符号 |
| 5 | モーターの PWM と電流の読み取り(車輪を浮かせる) | `drv/motor.c`、`drv/current.c` | 回る向き、0A の値、電流の向きと大きさ |
| 5a | **電流の制御とモーターの同定**(MK4 だけ) | `ctrl/current_ctrl.c`、モード4 | ステップの応答、3A の頭打ち。R・L・Kt を測り、PWM の周波数を決める |
| 6 | 壁センサ(発光の順番と ADC1) | `drv/wall.c`、`ctrl/wall_ctrl.c` | オシロで発光と PWM の位置。値 → mm の表 |
| 7 | 速度・角度の制御 | `ctrl/odometry.c`、`ctrl/trajectory.c`、`ctrl/control.c`、`ctrl/run.c` | 直進・その場旋回をログで |
| 8 | 迷路探索と最短経路 | `maze/*`、`test/` | PC のテスト(ToraNeko から持ってくるので、ほぼそのまま通る) |
| 9 | 探索走行、モード、ログ、フェイルセーフ、保存 | `sys/*`、`drv/flash_memory.c`、`drv/switch.c` | 16 × 16 の迷路で通す。電源を切っても迷路が残る |
| 10 | コマンドと値の保存(MK4 だけ) | `sys/cmd.c`、`sys/params.c` | 有線の UART で `set` → `save` → 電源を入れ直しても残る |
| 11 | BLE(MK4 だけ) | `software/ble-bridge/`、ビューア | 有線と同じことが無線でできる |
| 12 | ターンの自動調整(MK4 だけ) | `tools/tune.py`、モード3 | PC から値を送って走り、ログが戻る |
| 13 | ブートローダと無線の書き込み(MK4 だけ) | `software/bootloader/`、`tools/fw.py` | 途中で切っても戻せる |

## 14. 書き方の決まり(ToraNeko の `CLAUDE.md` と同じ)

コードを読むのは作者本人。**作者が自分で読んで理解し、直せること**をいちばんに考える。短さ・賢さ・汎用性より、素直で読みやすい書き方を選ぶ。

- **素直に書く**。同じ処理が数行並ぶくらいなら、ループや表にまとめるより並べて書く
- **避ける書き方**(使わずに書けるなら使わない。どうしても要るときは、何をしているかをコメントで説明する): ビット演算、三項演算子、`%` による巻き戻し、ポインタ演算・関数ポインタ・関数のようなマクロ・共用体、1 行に複数の処理を詰め込む書き方
  - MK4 で避けられない所(DMA の置き場所の確かめ、レジスタを直接書く 20kHz の処理、Flash のレコード)は、処理の流れをコメントで順に説明する
- **名前で意味が分かるようにする**。物理量には単位を付ける(`speed_mm_s`、`current_mA`、`wait_ms`、`angle_deg`)
- **関数は短く、1 つの仕事だけ**。関数の前に「何をする関数か」を 1〜2 行で書く。ファイルの先頭にファイルの役割を書く
- **コメントは日本語**で、「何をしているか」と「なぜそうするか」
- 割り込み・DMA・`volatile`・割り込み禁止を使う所は、処理の流れをコメントで順に説明する
- 名前の付け方(ToraNeko と同じ):

| 対象 | 決まり | 例 |
|---|---|---|
| ファイル名 | 小文字 + アンダースコア。層はフォルダで表す | `drv/encoder.c` |
| 関数名 | `モジュール名_動詞_目的語` | `current_ctrl_update()`、`motor_set_duty()` |
| 型名 | 小文字 + アンダースコア + `_t` | `odometry_state_t` |
| ファイルをまたぐ変数 | `g_` を付ける(なるべく使わず、関数で受け渡す) | `g_maze_map` |
| ファイルの中だけ | `static` | `static float s_prev_error;` |
| 定数・マクロ | 大文字 + アンダースコア | `CTRL_FREQ_HZ` |

- モードを足したり変えたりしたら、`software/main-controller/README.md` の「モード一覧」と `MODES.md` を同じコミットで直す(ToraNeko と同じ)

## 15. まだ決めていないこと

- ブザーの音の割り当て
- 吸引ありの探索の No.(KOGUMA のモード0 の吸引探索から何を持ってくるか)
- ログの列の最終形と、1 回の走行で取る長さ
- 電池の電圧で止める値の細かい決め方
- UART の速さ(1Mbaud が STLINK-V3 で使えるか)
- `turn_test` のコースと、ずれの測り方(`docs/ble.md` の8章)

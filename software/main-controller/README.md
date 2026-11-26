# main-controller

KOGUMA MK4 メイン基板(STM32H562RGV6。2026-11-26 に STM32H725RGV6 から替えた)のファームウェアです。**ToraNeko.Mk3 のファームウェア(`Tokoro0917/toraneko.mk3` の `software/main-controller/`)と同じ作り**にします(2026-11-23 決定)。ToraNeko の `App/` のコードを元にし、MK4 で違う所を直します。

- [../../docs/software.md](../../docs/software.md): ソフトの設計(ToraNeko との違い、時刻の作り方、制御、保存、ログ、テスト、作る順)
- [CUBEMX_SETUP.md](CUBEMX_SETUP.md): CubeMX(`.ioc`)の設定値(ステップ0)
- [MODES.md](MODES.md): 機体の操作、LED・ブザーの表し方、モードの割り当て
- ピン: [../../docs/pinmap.md](../../docs/pinmap.md)
- RAM・キャッシュ・DMA の決まり: [../../docs/firmware_memory.md](../../docs/firmware_memory.md)
- 無線(BLE)とブートローダ: [../../docs/ble.md](../../docs/ble.md)
- コードの書き方: リポジトリの一番上の [CLAUDE.md](../../CLAUDE.md)(ToraNeko と同じ)

## 決定事項

| 項目 | 決定 | 理由・補足 |
|---|---|---|
| 作り | ToraNeko.Mk3 と同じ(フォルダ・層・名前・書き方・操作・テスト・ステップ) | 2026-11-23 ユーザーの決定 |
| 開発環境 | STM32CubeMX(Toolchain = CMake)+ VS Code(STM32Cube for Visual Studio Code 拡張) | ToraNeko と同じ。CubeIDE は使わない |
| ビルド | `KOGUMA-Mk4/` で `cmake --preset Debug && cmake --build --preset Debug` | 成果物は `build/Debug/KOGUMA-Mk4.elf` |
| 書き込み・デバッグ | STLINK-V3MODS(J7) | 無線の書き込みはステップ13 |
| 電源 | **LDO**(CubeMX の初めの値のまま)、VOS0 | H562 の VFQFPN68 は LDO だけ |
| クロック | HSE 10MHz → 240MHz | 上限は 250MHz。TIM1 の 80kHz・20kHz が割り切れる |
| 時刻の元 | TIM1(モーターの PWM 80kHz、センターアラインド) | 20kHz で ADC1・ADC2 を起動 → 電流の制御、4kHz で制御(`docs/software.md` の4章) |
| UART | USART1(PB6・PB7)、送る・受ける | 有線(TP1)と BLE を同じ 1 本で |

## 実装の進め方

各ステップで「ToraNeko の該当するコードを読む → MK4 で変える点を決める → 作る → 実機・PC で確かめる」。中身は [../../docs/software.md](../../docs/software.md) の13章。

| # | 内容 | 状態 |
|---|---|---|
| 0 | 空のプロジェクト(CubeMX → CMake、STM32H562、LDO・VOS0、240MHz) | **CubeMX の設定値を書いた**(`CUBEMX_SETUP.md`)。CubeMX での作成はまだ(作者の PC で行う) |
| 1 | LED・ブザーとシリアル | |
| 2 | 時刻の元(TIM1)と 20kHz・1kHz の処理 | |
| 3 | エンコーダ(MT6835) | |
| 4 | IMU(LSM6DSR) | |
| 5 | モーターの PWM と電流の読み取り | |
| 5a | 電流の制御とモーターの同定 | |
| 6 | 壁センサ | |
| 7 | 速度・角度の制御 | |
| 8 | 迷路探索と最短経路(ToraNeko から) | |
| 9 | 探索走行、モード、ログ、フェイルセーフ、保存 | |
| 10 | コマンドと値の保存 | |
| 11 | BLE | |
| 12 | ターンの自動調整 | |
| 13 | ブートローダと無線の書き込み | |

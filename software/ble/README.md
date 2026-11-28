# ble — BLE モジュール HY0020(nRF52832)のプログラム

STM32 の UART と、PC の BLE(Nordic UART Service = NUS)の橋渡しをするプログラムです(2026-11-28)。
中身は見ずにそのまま渡し、`@` で始まる行だけを自分で処理します。決まりは [../../docs/ble.md](../../docs/ble.md)。

- 回路: `hardware/kicad/KOGUMA-Mk4/ui.kicad_sch` の U5(図は `docs/img/ble_uart.png`)
- 最初の書き込みの手順: `docs/ble.md` の 6.6

## ファイル

| ファイル | 中身 |
|---|---|
| `src/main.c` | 起動の順番だけ |
| `src/stm32_uart.c` | STM32 との UART。行に区切る、PC からの行を送る(有線が送っている間は待つ)、XON・XOFF、@reset・@flash のときの NRST・UART_RX の操作 |
| `src/ble_link.c` | BLE。アドバタイズ(1 秒に 1 回)、つながる・切れる(`@link up`・`@link down` を STM32 へ)、PC へ送る、名前 |
| `src/at_lines.c` | `@` で始まる行の処理 |
| `src/koguma_ble.h` | ファイルどうしで使う関数の一覧 |
| `prj.conf` | 設定(Kconfig)。BLE、UART、名前を Flash に残す、DFU |
| `boards/nrf52dk_nrf52832.overlay` | ピン(デバイスツリー)。uart0 は P0.06 送る・P0.08 受ける(流れ制御の線は外す)、115200、NRST は P0.07、UART_RX を見るのは P0.04 |
| `sysbuild.conf`・`sysbuild/mcuboot.conf` | ブートローダ MCUboot を入れる(2 回目からは BLE で書き換える)。MCUboot も UART に文字を出さない |

HY0020 の中は nRF52832 で、UART のピン(送る P0.06・受ける P0.08)が Nordic の評価ボード nRF52 DK と同じなので、**ボードは `nrf52dk/nrf52832` の設定をそのまま使い**、違う所だけを overlay で上書きしています。

## `@` の行

| 行 | 向き | 意味 |
|---|---|---|
| `@link up`・`@link down` | nRF → STM32 | PC とつながった・切れた(起動したときも `@link down` を送る) |
| `@link?` | STM32 → nRF | 今つながっているかを聞く(STM32 が再起動したあと用。2026-11-28 に足した) |
| `@quiet on`・`@quiet off` | STM32 → nRF | 電波を止める・戻す |
| `@reset` | PC → nRF | STM32 の NRST を 10ms L |
| `@flash` | PC → nRF | STM32 をブートローダの書き込みの待ちに入れる |
| `@name <名前>` | PC → nRF | アドバタイズの名前を変えて Flash に残す(29 文字まで) |

PC からの `@` の行には `#OK @…` か `#ERR unknown @ command` を返します。

## ビルド

**nRF Connect SDK v3.4.2** を使います(2026-11-28 に確かめた版)。

1. VS Code に「nRF Connect for VS Code」の拡張を入れる → 拡張の画面で **Toolchain と SDK の v3.4.2** を入れる
2. 「Open an existing application」で、このフォルダ(`software/ble`)を開く
3. 「Add build configuration」→ Board target に **`nrf52dk/nrf52832`**、System build(sysbuild)は **Build system default**(有効)→ 「Build Configuration」
4. ビルドが終わればよい。できるファイル(`build/` の中):
   - `mcuboot/zephyr/zephyr.hex` … ブートローダ(最初の 1 回だけ書く)
   - `ble/zephyr/zephyr.signed.hex` … このプログラム(署名つき)
   - `dfu_application.zip` … BLE で書き換えるときに使う

コマンドで作るときは(SDK を入れたフォルダで): `west build -b nrf52dk/nrf52832 --sysbuild -d build <このフォルダ>`

大きさ(2026-11-28): Flash 160KB / 212KB(MCUboot の 2 つの領域の片方)、RAM 63.8KB / 64KB(97%)。
**RAM に余りが少ない**ので、バッファを大きくするときは、ほかを小さくする(PC へ送る列 8KB、STM32 へ送る列 6KB)。

## 書き込み

- **最初の 1 回**: TP2・TP3(SWD)から、`mcuboot/zephyr/zephyr.hex` と `ble/zephyr/zephyr.signed.hex` の 2 つを書く(`docs/ble.md` の 6.6)
- **2 回目から**: スマホの「nRF Connect Device Manager」アプリで KOGUMA-MK4 につなぎ、`dfu_application.zip` を選んで書き換える(BLE の DFU。MCUboot と MCUmgr)

## ログ

uart0 は STM32 につながっているので、ログは UART には出さず、SWD の **RTT** で見る(pyOCD なら `pyocd rtt -t nrf52832`)。

## まだ確かめていないこと(実機で)

- 1Mbaud にしたときに、STM32 から受ける文字を取りこぼさないか(今は 115200。速さは overlay の `current-speed` と STM32 の USART1 の両方を変える)
- `@flash` で STM32 がブートローダに入るか(STM32 のブートローダはまだ作っていない)
- XOFF が間に合うか(PC へ送る列 8KB の 3/4 で XOFF)

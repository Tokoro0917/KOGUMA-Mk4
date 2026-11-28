# bootloader — STM32H562 のブートローダ(Flash の先頭 64KB)

走るプログラムを、UART(有線の TP1 でも、BLE の HY0020 でも)から書き込むための小さいプログラムです(2026-11-28)。
決まりは [../../docs/ble.md](../../docs/ble.md) の 6 章、PC の道具は [../main-controller/tools/fw.py](../main-controller/tools/fw.py)。

## Flash の分け方

| 番地 | 大きさ | 中身 |
|---|---|---|
| 0x08000000〜0x0800FFFF | 64KB(バンク 1 のセクタ 0〜7) | このブートローダ。自分では消さない |
| 0x08010000〜0x0807FFFF | 448KB(セクタ 8〜63) | 走るプログラム(先頭はベクタテーブル) |

## 起動したとき(約 1ms。待たない)

1. TAMP のバックアップレジスタ 0 に「書き込みへ」の印(`0x464C5348`)がある(走るプログラムが PC の `fw begin` を受けて書き、リセットした)
2. UART_RX(PB7)が 1ms の間ずっと L(BLE の HY0020 が `@flash` で引いている)
3. 走るプログラムが正しくない(スタックの初めの値が RAM の中、リセットの番地が走るプログラムの中、でなければ)

どれかなら **書き込みの待ち**、どれでもなければ **すぐ走るプログラムへ移る**(電源を入れてすぐ走れる。デバッガもそのまま使える)。

書き込みの待ち:
- `#BOOT ready` を送り、状態の LED 0(D114、PC11)を速く点滅させる
- 10 秒なにも来なければ、走るプログラムが正しければそちらへ移る(正しくなければ `#BOOT ready` を送り直して待ち続ける)
- モーター・ファンのピンは触らない。時計は起動のままの HSI(32MHz)

## 受ける行

| 行 | 返事 | 中身 |
|---|---|---|
| `fw begin <長さ> <crc>` | `#OK fw begin` | 走るプログラムの領域を、長さの分だけ消す(CRC32 は 16 進) |
| `fw <位置> <base64>` | 4KB ごとに `#OK fw <位置>` | 位置から書く(PC は 192 バイトずつ)。前の行が届いていないと書かずに `#ERR fw gap <位置>`(PC はそこから送り直す) |
| `fw end` | `#OK fw end` | 全体の CRC32 を確かめ、合えば先頭の 1KB を書いて、走るプログラムへ |
| `status` | `#BOOT ready` | ブートローダにいることを知らせる |

**書いている途中で切れても、こわれたプログラムに飛ばない工夫**: `fw begin` で先に全部消し、先頭の 1KB(ベクタテーブル)は RAM にためておいて、
`fw end` で CRC が合ったときだけ最後に書く。途中で切れると先頭が消えたままなので、次の起動で「正しくない」になり、書き込みを待つ。
同じ行が送り直されても、Flash に同じ中身があれば書かずに進む(H562 の Flash は、一度書いた 16 バイトを消さずに書き直せないため)。

## ファイル

| ファイル | 中身 |
|---|---|
| `App/boot_main.c` | 起動したときの判断、書き込みの待ち、LED |
| `App/boot_lines.c` | 受けた行の処理(fw begin・fw・fw end・status) |
| `App/boot_flash.c` | Flash を消す・書く・CRC、走るプログラムが正しいか、走るプログラムへ移る |
| `App/boot_uart.c` | USART1(PB6・PB7、115200)。1 文字ごとの割り込みでリングバッファに |
| `App/base64.c`・`App/crc32.c` | base64 を戻す、CRC32(zlib と同じ) |
| `App/boot_config.h` | 番地・大きさ・時間 |
| `Core/` | 割り込み(SysTick・USART1)、ST の起動のコード(`startup_stm32h562xx.s`、`system_stm32h5xx.c`)、HAL の設定 |
| `Drivers/` | ST の HAL・CMSIS のうち使う分だけ(STMicroelectronics/stm32h5xx-hal-driver・cmsis-device-h5・cmsis-core の GitHub から、2026-11-28) |
| `STM32H562RGVX_BOOT.ld` | リンカの設定(ST の `STM32H562xx_FLASH.ld` の Flash を 64KB にした) |

CubeMX は使っていない(小さいので、HAL を直接呼ぶ)。

## ビルド

`software/bootloader/` で:

```bash
cmake --preset Release && cmake --build --preset Release
```

できるもの: `build/Release/KOGUMA-Mk4-bootloader.elf`・`.hex`・`.bin`。大きさ(2026-11-28)は Release で 19KB、Debug で 36KB(64KB の中)。
いるもの: arm-none-eabi-gcc、CMake、Ninja(VS Code の STM32Cube の拡張で入るもの)。

PC の道具とブートローダの行の処理は、PC の上で試した(`boot_lines.c`・`base64.c`・`crc32.c` を PC でコンパイルし、Flash を配列にして、
`tools/fw.py --port socket://localhost:5000` で 50KB を送る。行を落とさないとき・途中の行を落としたとき・最後の行を落としたときに、書けた中身が元と同じ)。**実機では未確認。**

## 書き込み(最初の 1 回)

STLINK-V3MODS(J7)で、`build/Release/KOGUMA-Mk4-bootloader.hex` を書く(STM32CubeProgrammer の「Erase & programming」、または VS Code)。
**走るプログラムを書くとき、Flash を全部消すとブートローダも消える**。そのときは、もう一度これを書く。

## 走るプログラムがやること(STM32 のメインのプログラムを作るとき)

1. リンカの設定(CubeMX が作る `*_FLASH.ld`)の Flash を **`ORIGIN = 0x08010000, LENGTH = 448K`** にする
2. 起動したらすぐ **`SCB->VTOR = 0x08010000`**(`system_stm32h5xx.c` の `USER_VECT_TAB_ADDRESS` と `VECT_TAB_OFFSET 0x00010000U` でもよい)
3. PC から `fw begin …` を受けたら(止まっているとき): TAMP の `BKP0R` に `0x464C5348` を書き、`NVIC_SystemReset()`。走っているときは `#ERR busy` を返す
4. 起動したら `#STATUS …` を 1 行送る(PC の道具が「書けた」を確かめる)

コードの例(バックアップレジスタは、PWR の DBP を許してから。`boot_main.c` の `backup_register_enable` と同じ):

```c
HAL_PWR_EnableBkUpAccess();
__HAL_RCC_RTCAPB_CLK_ENABLE();
TAMP->BKP0R = 0x464C5348U;   /* 「書き込みへ」の印。リセットしても消えない */
NVIC_SystemReset();
```

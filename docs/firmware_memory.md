# STM32H562 の RAM・DMA の決まり(2026-11-26。前は STM32H725)

**2026-11-26: MCU を STM32H725 から STM32H562 に替えた**(`docs/spec.md` の「MCU」)。H725 で怖かった2つ(DMA が届かない RAM、データのキャッシュに古い値が残る)は、**H562 では起きない**。それでも、DMA の配列の置き場所を1か所に決めて、外れたら止まる仕組みは残す(CLAUDE.md の決まり: DMA の配列は `DMA_BUF`、DMA を動かす前に `dma_check()`)。H725 のときの文書は下の「付録」に残す。

## 1. H562 の RAM

データシート DS14258 の 3.5 章、ST のヘッダ `stm32h562xx.h`。

| RAM | 番地 | 大きさ | CPU | GPDMA1・GPDMA2 |
|---|---|---|---|---|
| SRAM1 | 0x2000 0000 | 256KB | 待ちなし | 届く |
| SRAM2 | 0x2004 0000 | 64KB(ECC を付けられる) | 待ちなし | 届く |
| SRAM3 | 0x2005 0000 | 320KB(ECC を付けると 64KB 減る) | 待ちなし | 届く |
| BKPSRAM | 0x4003 6400 | 4KB | | (使わない) |

- 内蔵の RAM には**データのキャッシュがない**(H562 の 4KB のデータキャッシュは、外付けのメモリ(FMC・OCTOSPI)だけに使う。この機体では使わない)。だから、キャッシュの掃除(clean・invalidate)は要らず、MPU でキャッシュしない所を決める必要もない
- DMA は GPDMA1・GPDMA2(8 チャンネルずつ)。バスのマトリクスで、**どの SRAM にも届く**(DS14258 の 3.15 章)
- 命令のキャッシュ(ICACHE、8KB)は ON にする(Flash の待ち 5 回を隠す)
- TrustZone は使わない(CubeMX で「without TrustZone」。オプションバイトの TZEN は出荷のまま 0)

## 2. 決まり(3つ。H725 と同じ書き方を残す)

1. **DMA が触る配列は、すべて `DMA_BUF` を付けて `.dma_buf` のセクションに置く**。ほかの所に置かない(DMA の配列が1か所にまとまり、大きさ・そろえ方を1か所で決められる)
2. **`DMA_BUF` は 32 バイトにそろえる**(GPDMA はデータの幅にそろった番地が要る。16 ビットの ADC の値なら 2 バイト。32 にしておけばどれにも合う)
3. **DMA を動かす関数は、必ず `dma_check()` を通す**。`.dma_buf` から外れた配列を渡したら、その場で止まって LED で知らせる

## 3. 置き場所

| もの | 置き場所 | DMA |
|---|---|---|
| ふつうの変数、スタック、制御の計算 | SRAM1(CubeMX のまま) | 使わない |
| 速くしたい割り込みの関数 | Flash(ICACHE)。足りなければ SRAM に置く(`docs/calc/cpu_est/README.md`) | 使わない |
| ADC1・ADC2 の受け口(壁センサ・電流・電池) | **`.dma_buf`(`DMA_BUF`)** | GPDMA |
| SPI2(エンコーダ)・SPI3(IMU)の送り口・受け口 | **`.dma_buf`(`DMA_BUF`)** | GPDMA |
| UART の受け口(リングバッファ)・送り口(4KB × 2) | **`.dma_buf`(`DMA_BUF`)** | GPDMA |
| ログ(256KB)、迷路、パラメータ | SRAM3 | 使わない(送るときは 4KB ずつ写す) |

- `.dma_buf` は SRAM2 の先頭に 32KB とる(ADC 2 × 64B、SPI 4 × 64B、UART 4KB + 4KB × 2 → 約 13KB)
- **大きなログを DMA に直接渡さない**。ログから 4KB ずつ `DMA_BUF` の送り口に写して、DMA で送る(2つを交互に使う)。H562 では直接渡しても壊れないが、置き場所の決まりを1つにするため
- ADC を DMA で回し続けるときは、GPDMA の linked-list の循環にする(H7 の「circular」の設定の代わり。CubeMX の GPDMA の画面)

## 4. 入れるもの(最初の1回だけ)

### 4.1 リンカの設定(CubeMX が作る `STM32H562RGVX_FLASH.ld` に足す)

```ld
MEMORY
{
  /* CubeMX が作った行はそのまま。RAM の長さを SRAM2 の前までに縮めるかは、作られた中身を見て決める */
  DMA_RAM (xrw) : ORIGIN = 0x20040000, LENGTH = 32K
}

SECTIONS
{
  /* ほかのセクションのあとに */
  .dma_buf (NOLOAD) :
  {
    . = ALIGN(32);
    __dma_buf_start = .;
    *(.dma_buf)
    *(.dma_buf*)
    . = ALIGN(32);
    __dma_buf_end = .;
  } >DMA_RAM
}
```

- `NOLOAD` なので、起動したときの中身は決まっていない(0 にならない)。使う前に DMA が書く・自分で 0 にする
- CubeMX のリンカの設定で、ふつうの RAM が 0x2004 0000〜 にかかっていないかを確かめる(かかっていれば RAM の長さを縮める)

### 4.2 置き場所の印と、外れたら止まる関数(`dma_buf.h`)

H725 のときと同じ(下の付録の 4.2)。HAL の DMA の関数を直接呼ばず、`dma_check()` を入れた自分の関数から呼ぶ。20kHz の ADC、エンコーダ・IMU の SPI はレジスタを直接書く形にする(`docs/calc/cpu_est/README.md`)が、そこでも最初に `dma_check()` を通す。

### 4.3 MPU

**入れない**(内蔵の RAM にデータのキャッシュがないので要らない)。

```c
int main(void)
{
    HAL_Init();
    /* 電源は LDO(H562 の VFQFPN68 は LDO だけ。CubeMX の初めの値のまま) */
    SystemClock_Config();  /* HSE 10MHz → PLL 240MHz、Flash の待ちは RM0481 の表どおり(CubeMX が決める) */
    HAL_ICACHE_Enable();   /* 命令のキャッシュ(CubeMX の ICACHE の画面で ON にしてもよい。どちらか1か所だけ) */
    ...
}
```

## 5. ほかに気をつけること

- **自分で内蔵 Flash に書いたあと、同じ所を読み直すとき**(パラメータの保存、ブートローダの CRC の確認): ICACHE に古い中身が残っていることがあるので、書いたあとに `HAL_ICACHE_Invalidate()` してから読む(RM0481 の ICACHE の章で確かめる)
- **書き込みは 16 バイト(128 ビット)単位**、消去は 8KB 単位(H725 は 32 バイト・128KB)。Flash のレコードの大きさを 16 バイトの倍数にする
- **起動したときの確かめ**: 起動のたびに、ADC の受け口の値が 1ms 以内に 0 以外に変わるかを見る。変わらなければ LED で知らせる(DMA が動いていない)

## 6. 困ったとき

| 起きたこと | まず疑う所 |
|---|---|
| DMA の値が 0 のまま | GPDMA のチャンネルの要求(ADC・SPI の番号)、linked-list の設定。`dma_check()` を通していれば、置き場所の間違いならその場で止まっている |
| 書き込んだ直後、MCU が応答しない | クロック・電源の設定、ピンの設定の間違い。STLINK の「リセットしたままつなぐ」で消す。それでもつながらなければ、**TP4(BOOT0)を 3.3V(J7 の1番など)につないだまま電源を入れ**、STLINK でつないで全部消す(自分のプログラムが動かないので、必ずつながる)。消したら TP4 を外す |

---

# 付録: STM32H725 のときの決まり(2026-11-23〜11-26。今は使わない)

H7 で多い失敗は2つ。どちらも **最初に置き場所を決めて、外れたら止まる仕組み** にすれば起きない。
この文書の決まりを、ソフトを書き始める前に入れる(CubeMX で作ったあと、最初の1回だけ)。

## 1. 何が怖いのか

### 落とし穴1: DMA が届かない RAM がある

H725 の RAM は1つではなく、つながっている所が違う(データシート DS13311 の 3.3.2、表2)。

| RAM | 番地 | 大きさ | CPU | DMA1・DMA2 |
|---|---|---|---|---|
| ITCM | 0x0000 0000 | 64KB | 速い(待ちなし) | **届かない** |
| DTCM | 0x2000 0000 | 128KB | 速い(待ちなし)。キャッシュは使わない | **届かない** |
| AXI SRAM | 0x2400 0000 | 128KB(+ ITCM と分け合う 192KB) | ふつう。キャッシュを使う | 届く |
| SRAM1・SRAM2(D2) | 0x3000 0000 | 16KB + 16KB | ふつう。キャッシュを使う | 届く |
| SRAM4(D3) | 0x3800 0000 | 16KB | ふつう | BDMA だけ(この機体では使わない) |

- CubeMX が作るリンカの設定は、**ふつうの変数・スタックを DTCM に置く**。速いので CPU にはよい
- ところが `static uint16_t adc_buf[8];` と書いただけの DMA の受け口も DTCM に入る → **DMA が届かず、値が 0 のまま変わらない**(エラーにもならないことがある)

### 落とし穴2: キャッシュに古い値が残る

- D キャッシュは、CPU が RAM を読んだ値を手元に覚えておく仕組み
- DMA は CPU を通らずに RAM に書く。CPU のキャッシュには **前に読んだ古い値** が残っていて、CPU はそれを読んでしまう(壁センサの値が更新されない、ときどき古い値、など。再現しにくい)
- 逆向き(CPU が書いて DMA が送る)では、CPU の書いた値がキャッシュにだけあって RAM にまだない → **古いデータを送る**

## 2. 決まり(3つ)

1. **DMA が触る配列は、すべて `DMA_BUF` を付けて SRAM1・SRAM2(0x3000 0000〜、32KB)に置く**。ほかの所に置かない
2. **その 32KB は MPU で「キャッシュしない」にする**。だから、キャッシュの掃除(clean・invalidate)は一度も書かなくてよい
3. **DMA を動かす関数は、必ず `dma_check()` を通す**。決まり1から外れた配列を渡したら、その場で止まって LED で知らせる(気づかずに走ることがない)

これで、D キャッシュを ON にしても OFF にしても、同じように正しく動く。

## 3. 置き場所

| もの | 置き場所 | DMA |
|---|---|---|
| ふつうの変数、スタック、制御の計算 | DTCM(CubeMX のまま) | 使わない |
| 速くしたい割り込みの関数 | ITCM(あとで必要なら) | 使わない |
| ADC1・ADC2 の受け口(壁センサ・電流・電池) | **SRAM1・2(`DMA_BUF`)** | DMA1・DMA2 |
| SPI2(エンコーダ)・SPI3(IMU)の送り口・受け口 | **SRAM1・2(`DMA_BUF`)** | DMA1・DMA2 |
| UART の受け口(リングバッファ)・送り口(4KB × 2) | **SRAM1・2(`DMA_BUF`)** | DMA1・DMA2 |
| ログ(256KB)、迷路、パラメータ | AXI SRAM | **使わない**(下) |

- 32KB の内訳の目安: ADC 2 × 64B、SPI 4 × 64B、UART の受け口 4KB、送り口 4KB × 2 → 約 13KB。余裕がある
- **大きなログを DMA に直接渡さない**。送るときは、ログから 4KB ずつ `DMA_BUF` の送り口に写して(memcpy は数 µs)、それを DMA で送る。2つの送り口を交互に使う
- ADC は ADC1・ADC2 だけを使う(`docs/pinmap.md`)。どちらも DMA1・DMA2 で届くので、SRAM4・BDMA は使わない

## 4. 入れるもの(最初の1回だけ)

### 4.1 リンカの設定(CubeMX が作る `STM32H725RGVX_FLASH.ld` に足す)

```ld
MEMORY
{
  /* CubeMX が作った行(DTCMRAM・RAM_D1 など)はそのまま */
  RAM_D2 (xrw) : ORIGIN = 0x30000000, LENGTH = 32K
}

SECTIONS
{
  /* ほかのセクションのあとに */
  .dma_buf (NOLOAD) :
  {
    . = ALIGN(32);
    __dma_buf_start = .;
    *(.dma_buf)
    *(.dma_buf*)
    . = ALIGN(32);
    __dma_buf_end = .;
  } >RAM_D2
}
```

- `NOLOAD` なので、起動したときの中身は決まっていない(0 にならない)。使う前に DMA が書く・自分で 0 にする
- 32 バイトそろえ(ALIGN(32))は、キャッシュの1行の大きさ。キャッシュしない設定なので本当は要らないが、あとで設定を変えても壊れないように

### 4.2 置き場所の印と、外れたら止まる関数(`dma_buf.h`)

```c
#include <stdint.h>
#include <stddef.h>

#define DMA_BUF __attribute__((section(".dma_buf"), aligned(32)))

extern uint8_t __dma_buf_start[], __dma_buf_end[];
void dma_fatal(const void *p);              /* LED を決まった形で光らせて止まる */

static inline void dma_check(const void *p, size_t n)
{
    uintptr_t a = (uintptr_t)p;
    if (a < (uintptr_t)__dma_buf_start || a + n > (uintptr_t)__dma_buf_end)
        dma_fatal(p);
}
```

使い方:

```c
DMA_BUF static uint16_t adc1_buf[8];

void adc_start(void)
{
    dma_check(adc1_buf, sizeof adc1_buf);
    HAL_ADC_Start_DMA(&hadc1, (uint32_t *)adc1_buf, 8);
}
```

- HAL の DMA の関数(`HAL_ADC_Start_DMA`・`HAL_SPI_TransmitReceive_DMA`・`HAL_UART_Transmit_DMA`・`HAL_UART_Receive_DMA` など)を **直接呼ばず、`dma_check()` を入れた自分の関数から呼ぶ**

### 4.3 MPU(キャッシュしない所を決める。D キャッシュを ON にする前に)

```c
static void mpu_config(void)
{
    MPU_Region_InitTypeDef r = {0};

    HAL_MPU_Disable();
    r.Enable           = MPU_REGION_ENABLE;
    r.Number           = MPU_REGION_NUMBER1;     /* Region 0 は CubeMX が入れる 4GB の「読まない」設定に残す(番号の大きいほうが勝つ) */
    r.BaseAddress      = 0x30000000;             /* SRAM1・SRAM2 */
    r.Size             = MPU_REGION_SIZE_32KB;
    r.SubRegionDisable = 0x00;
    r.TypeExtField     = MPU_TEX_LEVEL1;         /* TEX=1・C=0・B=0 = キャッシュしないふつうのメモリ */
    r.IsCacheable      = MPU_ACCESS_NOT_CACHEABLE;
    r.IsBufferable     = MPU_ACCESS_NOT_BUFFERABLE;
    r.IsShareable      = MPU_ACCESS_NOT_SHAREABLE;
    r.AccessPermission = MPU_REGION_FULL_ACCESS;
    r.DisableExec      = MPU_INSTRUCTION_ACCESS_DISABLE;
    HAL_MPU_ConfigRegion(&r);
    HAL_MPU_Enable(MPU_PRIVILEGED_DEFAULT);
}

int main(void)
{
    mpu_config();          /* 1. MPU */
    SCB_EnableICache();    /* 2. 命令のキャッシュ(いつでも安全) */
    SCB_EnableDCache();    /* 3. データのキャッシュ(MPU のあと) */
    HAL_Init();
    /* 電源は Direct SMPS(docs/spec.md の「MCUの電源」)。CubeMX の初期値の LDO のままにしない */
    ...
}
```

- CubeMX の「CORTEX_M7」の画面でも同じ設定ができる(MPU Region 1: 0x30000000、32KB、TEX level 1、Cacheable・Bufferable・Shareable を NOT。`software/main-controller/CUBEMX_SETUP.md` の2章)。**MK4 は CubeMX で入れる**(上のコードは中身の説明)。どちらか**1か所だけ** にする

## 5. ほかに気をつけること

- **自分で内蔵 Flash に書いたあと、同じ所を読み直すとき**(パラメータの保存、ブートローダの CRC の確認): Flash もキャッシュされるので、書いたあとに `SCB_InvalidateDCache_by_Addr()` でその範囲を捨ててから読む。ブートローダは D キャッシュを OFF のまま動かす(速さは要らない)
- **D キャッシュは、最初は OFF で始めてもよい**。制御の変数は DTCM(キャッシュを使わない、待ちなし)にあるので、OFF でも制御の速さはほとんど変わらない。全部動いてから ON にし、ログで割り込みの時間を比べる。決まり1〜3を守っていれば、ON にしても壊れない
- **起動したときの確かめ**: 起動のたびに、ADC の受け口の値が 1ms 以内に 0 以外に変わるかを見る。変わらなければ LED で知らせる(DMA が動いていない)

## 6. 困ったとき

| 起きたこと | まず疑う所 |
|---|---|
| DMA の値が 0 のまま | 受け口が DTCM にある(`DMA_BUF` の付け忘れ)。`dma_check()` を通していれば、その場で止まっているはず |
| 値がときどき古い・更新されない | 受け口がキャッシュされる所にある(MPU の設定の順番・大きさ) |
| 送ったデータが一部古い | 大きな配列を DMA に直接渡している(4KB ずつ写して送る) |
| 書き込んだ直後、MCU が応答しない | 電源の設定が LDO のまま(Direct SMPS にする)。STLINK の「リセットしたままつなぐ」で消す。それでもつながらなければ、**TP4(BOOT0)を 3.3V(J7 の1番など)につないだまま電源を入れ**、STLINK でつないで全部消す(自分のプログラムが動かないので、必ずつながる)。消したら TP4 を外す |

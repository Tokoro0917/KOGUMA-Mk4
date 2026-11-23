# STM32H725 の RAM・キャッシュ・DMA の決まり(2026-11-23)

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

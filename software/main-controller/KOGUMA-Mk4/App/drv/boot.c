/*
 * boot.c
 * ブートローダ(software/bootloader/)へ移って、プログラムの書き込みを待ってもらう。MK4 で足したもの(2026-11-28)
 *
 * ■ しくみ(software/bootloader/README.md の「走るプログラムがやること」、docs/ble.md の 6 章)
 *   1. TAMP のバックアップレジスタ 0(BKP0R)に「書き込みへ」の印 0x464C5348 を書く。
 *      バックアップレジスタは、リセットしても消えない(電源を切ると消える)
 *   2. マイコンをリセットする(NVIC_SystemReset)
 *   3. 起動したブートローダが印を見つけて消し、書き込みの待ちになる(#BOOT ready を送る)
 * バックアップレジスタは書き込みが守られているので、PWR の DBP を許してから書く(ブートローダの backup_register_enable と同じ)。
 */
#include "drv/boot.h"

#include "drv/timebase.h"
#include "main.h"

#define BOOT_REQUEST_MAGIC 0x464C5348U  /* 「書き込みへ」の印(software/bootloader/App/boot_config.h と同じ) */
#define UART_FLUSH_MS 20                /* リセットの前に、送りかけの文字を送り終える時間 [ms] */

/* ブートローダへ移る(戻らない)。送りかけの文字を送り終えてからリセットする */
void boot_enter_bootloader(void)
{
  timebase_wait_ms(UART_FLUSH_MS);
  HAL_PWR_EnableBkUpAccess();
  __HAL_RCC_RTCAPB_CLK_ENABLE();  /* TAMP のレジスタの時計 */
  TAMP->BKP0R = BOOT_REQUEST_MAGIC;
  NVIC_SystemReset();
}

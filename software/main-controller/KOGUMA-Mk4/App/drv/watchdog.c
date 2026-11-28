/*
 * watchdog.c
 * ウォッチドッグ(IWDG)。MK4 で足したもの(docs/software.md の 3 章)
 *
 * IWDG は、決めた時間のうちに「まだ動いている」の合図(watchdog_refresh())が来ないと、マイコンをリセットする。
 * 割り込みが止まった(プログラムがどこかで固まった)ときに、モーターを回したままにしないため。
 *   - 時計は中の LSI(32kHz)。÷32 で 1kHz、50 数えたら(約 50ms)リセット
 *   - 合図は 4kHz の処理から、20kHz の処理も動いているのを確かめてから送る(sys/scheduler.c)
 *   - デバッガで止めているあいだは IWDG も止める(止めないと、ブレークポイントで止めるたびにリセットされる)
 * 一度動かすと、リセットするまで止められない。
 */
#include "drv/watchdog.h"

#include "main.h"

static IWDG_HandleTypeDef s_iwdg;

/* IWDG を動かし始める(約 50ms) */
void watchdog_start(void)
{
  __HAL_DBGMCU_FREEZE_IWDG();
  s_iwdg.Instance = IWDG;
  s_iwdg.Init.Prescaler = IWDG_PRESCALER_32;
  s_iwdg.Init.Reload = 50;
  s_iwdg.Init.Window = IWDG_WINDOW_DISABLE;
  s_iwdg.Init.EWI = 0;
  HAL_IWDG_Init(&s_iwdg);
}

/* 「まだ動いている」の合図(IWDG の数を初めに戻す) */
void watchdog_refresh(void)
{
  HAL_IWDG_Refresh(&s_iwdg);
}

/* 前の起動が IWDG のリセットだったら true(起動したときに 1 回だけ呼ぶ。印は消す) */
bool watchdog_was_reset(void)
{
  bool was_reset = false;
  if (__HAL_RCC_GET_FLAG(RCC_FLAG_IWDGRST)) {
    was_reset = true;
  }
  __HAL_RCC_CLEAR_RESET_FLAGS();
  return was_reset;
}

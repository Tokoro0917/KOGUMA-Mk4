/*
 * app.c
 * App 全体の入口。main.c から app_init() と app_loop() が呼ばれる
 * ToraNeko.Mk3 の App/app.c から(2026-11-28。MK4 のドライバ・ブザー・コマンド・値の保存を足した)
 *
 * 起動したら、センサやモーターを使えるようにしてから、モードを選んで走らせる(sys/mode.c)。
 * 操作の仕方は MODES.md。
 */
#include "app.h"

#include <stdio.h>

#include "config/robot_params.h"
#include "ctrl/current_ctrl.h"
#include "ctrl/odometry.h"
#include "drv/buzzer.h"
#include "drv/current.h"
#include "drv/encoder.h"
#include "drv/imu.h"
#include "drv/led.h"
#include "drv/timebase.h"
#include "drv/uart.h"
#include "drv/watchdog.h"
#include "sys/cmd.h"
#include "sys/mode.h"
#include "sys/params.h"
#include "sys/scheduler.h"
#include "sys/ui.h"

#define ZERO_MEASURE_TIMEOUT_MS 300  /* 電流の 0A の値を測り終えるのを待つ上限 [ms](ふつうは 0.1 秒) */

/* シリアルに出す文字は英数字だけにする(日本語は、表示するソフトによって文字化けするため。ToraNeko と同じ) */

/* 電流の 0A の値を測る(モーターを止めているとき。drv/current.c) */
static void measure_current_zero(void)
{
  current_start_zero_measure();
  uint32_t start_ms = timebase_get_ms();
  while (!current_is_zero_ready() && timebase_get_ms() - start_ms < ZERO_MEASURE_TIMEOUT_MS) {
  }
  printf("Current zero L %u R %u (2048 = 1.65V)\r\n", current_get_left_raw(), current_get_right_raw());
}

/* 電池の電圧を調べ、下限より低ければ、知らせて止まる(戻らない)。電池を調べるのは電源を入れたときだけ(KOGUMA・ToraNeko と同じ) */
static void check_battery(void)
{
  float battery_v = current_get_battery_v();
  printf("Battery %.2f V\r\n", battery_v);
  if (battery_v < BATTERY_LOW_V) {
    printf("Battery low (below %.1f V). Replace the battery\r\n", BATTERY_LOW_V);
    current_ctrl_stop();
    ui_stop_for_low_battery();
  }
}

/* 起動時に 1 回だけ呼ばれる。周辺機能を使えるようにして、20kHz・4kHz の処理を始める */
void app_init(void)
{
  led_init();
  uart_init();
  timebase_init();
  buzzer_init();
  printf("\r\nKOGUMA-Mk4 boot (SYSCLK %lu Hz)\r\n", timebase_get_sysclk_hz());
  if (watchdog_was_reset()) {
    printf("Watchdog reset happened before this boot\r\n");
  }
  encoder_init();
  odometry_init();
  if (imu_init()) {
    printf("IMU OK (LSM6DSR)\r\n");
  } else {
    printf("IMU NG: WHO_AM_I=0x%02X (expected 0x6B)\r\n", imu_get_who_am_i());
  }
  params_init();
  if (params_load()) {
    printf("Params loaded from Flash\r\n");
  }
  params_apply();
  scheduler_start();  /* ここから、20kHz・4kHz の処理が動く。ジャイロのゼロ点は最初の 0.5 秒で測る */
  measure_current_zero();
  timebase_wait_ms(10);  /* 電池の電圧のゆれを減らす処理が落ち着くのを待つ */
  check_battery();
  mode_init();
  cmd_init();
  cmd_print_status();  /* 起動した印(PC の書き込みの道具 tools/fw.py は、これで「書けた」を確かめる) */
  ui_show_loading();   /* 電源を入れたときの「ロード中」(MODES.md の 2)。このあいだに、ジャイロのゼロ点も測り終わる */
}

/* main() の while(1) から繰り返し呼ばれる。モードを選んで走らせ、終わったら戻る */
void app_loop(void)
{
  mode_run_once();
}

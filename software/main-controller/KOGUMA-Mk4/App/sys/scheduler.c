/*
 * scheduler.c
 * 20kHz の処理と 4kHz の処理を呼ぶ。ToraNeko.Mk3 の App/sys/scheduler.c から(2026-11-28。docs/software.md の 4 章)
 *
 * ■ 仕組み
 * ToraNeko は TIM11 の 2kHz の割り込み 1 つで制御を回していた。MK4 は電流の制御を 20kHz で回すので、
 * モーターの PWM のタイマー TIM1 を、すべての時刻の元にする。
 *   1. TIM1 は PWM 4 周期ごと(20kHz)に TRGO を出し、ADC1(壁センサ)・ADC2(電流)の変換を同時に始める
 *   2. ADC2 の変換が終わると割り込みが来る(優先度 0、いちばん高い)
 *        ADC2_IRQHandler()(Core/Src/stm32h5xx_it.c)→ scheduler_on_adc_done()(このファイル)
 *      ここが「20kHz の処理」: 電流・電池・ファンの電流・壁センサを読み、電流の制御で duty を決める
 *   3. 壁センサの順番が 1 巡(5 回に 1 回)したら、NVIC_SetPendingIRQ(TIM6_IRQn) で TIM6 の割り込みを「起こす」。
 *      TIM6 自体は動かしていない。割り込みの番号を借りて、優先度 2 の「4kHz の処理」を走らせる
 *        TIM6_IRQHandler() → scheduler_on_control_tick()(このファイル)
 *      ここが「4kHz の処理」: エンコーダ・IMU を読み、速度・角度の制御で電流の目標を決める
 *   4. 20kHz の処理のほうが優先度が高いので、4kHz の処理の途中でも 20kHz の処理は割り込んで動く
 *      (4kHz の処理が長引いても、電流の制御は遅れない)
 *
 * ■ 処理時間の記録(ToraNeko と同じ)
 * 毎回、TIM5(µs)で「始まった時刻」と「終わった時刻」を読み、かかった時間と、前の回からの間隔を記録する。
 * app.c が 1 秒ごとに scheduler_take_stats() で取り出して、シリアルに出す。
 *
 * ■ 割り込みの中で気をつけること(ToraNeko と同じ)
 * - 割り込みの中では printf や待ち(timebase_wait_ms)を使わない。SysTick(ms を数える割り込み)は
 *   どちらの処理より優先度が低いので、この中では ms が進まない
 * - 割り込みの中で書き換える変数には volatile を付ける。volatile がないと、コンパイラが
 *   「この変数は変わらない」と考えて、メインの処理で古い値を使い続けることがある
 */
#include "sys/scheduler.h"

#include "ctrl/control.h"
#include "ctrl/current_ctrl.h"
#include "ctrl/odometry.h"
#include "drv/buzzer.h"
#include "drv/current.h"
#include "drv/encoder.h"
#include "drv/fan.h"
#include "drv/imu.h"
#include "drv/motor.h"
#include "drv/timebase.h"
#include "drv/uart.h"
#include "drv/wall.h"
#include "drv/watchdog.h"
#include "sys/failsafe.h"
#include "main.h"
#include "sys/log.h"

#define CONTROL_TICK_PRIORITY 2  /* 4kHz の処理(TIM6 の割り込み)の優先度 */

/* 割り込みの中で書き換える記録(volatile の理由は先頭のコメント) */
static volatile uint32_t s_tick_count = 0;
static volatile uint32_t s_busy_max_us = 0;
static volatile uint32_t s_period_min_us = 0xFFFFFFFF;  /* まだ測っていないときは、いちばん大きい数にしておく */
static volatile uint32_t s_period_max_us = 0;
static volatile uint32_t s_last_start_us = 0;          /* 前の回が始まった時刻 [µs] */
static volatile bool s_has_last_start = false;         /* 前の回の時刻があるか(最初の 1 回は間隔を測れない) */
static volatile uint32_t s_fast_count = 0;
static volatile uint32_t s_fast_busy_max_us = 0;
static volatile bool s_fast_alive = false;   /* 前に scheduler_check_alive() を呼んでから、20kHz の処理が来たか */
static volatile bool s_tick_alive = false;   /* 同じく 4kHz の処理 */
static volatile bool s_fast_since_tick = false;  /* 前の 4kHz の処理から、20kHz の処理が来たか(ウォッチドッグ用) */

/* 20kHz の処理が、前の 4kHz の処理から 1 回でも来ていれば、ウォッチドッグに「まだ動いている」を送る。
 * 20kHz の処理が止まると合図が来なくなり、約 50ms でリセットされる(drv/watchdog.c) */
static void refresh_watchdog(void)
{
  if (s_fast_since_tick) {
    watchdog_refresh();
  }
  s_fast_since_tick = false;
}

/* PC・BLE から stop が来ていて、モーターを回していれば止める(drv/uart.c が受けた行を割り込みの中で見ている) */
static void check_stop_command(void)
{
  if (uart_take_stop_request() && current_ctrl_get_mode() != CURRENT_CTRL_OFF) {
    failsafe_stop_with_reason(FAILSAFE_REASON_STOP_COMMAND);
  }
}

/* 4kHz の処理の中身(制御の処理)。ToraNeko の run_control() と同じ順 */
static void run_control(void)
{
  encoder_update();
  imu_update();
  odometry_update();     /* エンコーダから、速さと距離を求める */
  current_ctrl_set_wheel_speed(odometry_get_left_speed_mm_s(), odometry_get_right_speed_mm_s());
  control_update();      /* 走っているときだけ、目標の速さ・向きになるように左右の電流の目標を決める */
  fan_update();          /* 吸引ファンの PWM の割合を、今の電池の電圧で計算し直す(回していなければ 0 のまま) */
  log_record_fast();     /* 壁センサの生の値のログ(取っているときだけ。sys/log.c) */
  failsafe_check_hardware();  /* 電流の守り・MP6551 の異常・エンコーダのエラーを見る */
  check_stop_command();
  buzzer_update();       /* ブザーを止める時刻なら止める */
  refresh_watchdog();
}

/* 割り込みの間隔を記録する */
static void record_period(uint32_t start_us)
{
  if (s_has_last_start) {
    uint32_t period_us = start_us - s_last_start_us;
    if (period_us < s_period_min_us) {
      s_period_min_us = period_us;
    }
    if (period_us > s_period_max_us) {
      s_period_max_us = period_us;
    }
  }
  s_last_start_us = start_us;
  s_has_last_start = true;
}

/* 4kHz の処理(TIM6 の割り込み)。制御の処理を呼び、かかった時間を記録する */
void scheduler_on_control_tick(void)
{
  uint32_t start_us = timebase_get_us();
  record_period(start_us);

  run_control();

  uint32_t busy_us = timebase_get_us() - start_us;
  if (busy_us > s_busy_max_us) {
    s_busy_max_us = busy_us;
  }
  s_tick_count = s_tick_count + 1;
  s_tick_alive = true;
}

/* 20kHz の処理(ADC2 の割り込み)。
 *   1. ADC2 の「4 本終わった」の印(JEOS)を消す(消さないと、割り込みがすぐまた来る)
 *   2. 電流・電池・ファンの電流を読む
 *   3. 電流の制御で duty を決めて書く(読んでから書くまでを短くするため、壁センサより先)
 *   4. 壁センサを読み、発光の順番を進める。1 巡したら 4kHz の処理を起こす */
void scheduler_on_adc_done(void)
{
  uint32_t start_us = timebase_get_us();
  LL_ADC_ClearFlag_JEOS(ADC2);

  current_read_adc();
  fan_read_adc();
  current_ctrl_update();
  log_record_current();  /* 20kHz の電流のログ(取っているときだけ) */
  bool cycle_done = wall_read_adc();
  if (cycle_done) {
    NVIC_SetPendingIRQ(TIM6_IRQn);
  }

  uint32_t busy_us = timebase_get_us() - start_us;
  if (busy_us > s_fast_busy_max_us) {
    s_fast_busy_max_us = busy_us;
  }
  s_fast_count = s_fast_count + 1;
  s_fast_alive = true;
  s_fast_since_tick = true;
}

/* 20kHz・4kHz の処理を始める。timebase_init() のあとに 1 回だけ呼ぶ。
 * ADC を待ちの状態にしてから TIM1・TIM16 を動かす(TIM1 が動くと、すぐ TRGO が来て変換が始まるため) */
void scheduler_start(void)
{
  HAL_NVIC_SetPriority(TIM6_IRQn, CONTROL_TICK_PRIORITY, 0);
  HAL_NVIC_EnableIRQ(TIM6_IRQn);
  wall_init();
  current_init();
  motor_init();
  fan_init();
  watchdog_start();
}

/* 前に取り出してからの記録を stats に入れて、記録を 0 から取り直す。メインの処理(app.c)から呼ぶ */
void scheduler_take_stats(scheduler_stats_t *stats)
{
  /* 写しているあいだに割り込みが入ると、半分だけ新しい記録になるので、割り込みを少しのあいだ止める。
   * 止めるのは数行(1µs 未満)なので、止めているあいだに来た割り込みは、再開したときにすぐ処理される */
  __disable_irq();
  stats->tick_count = s_tick_count;
  stats->busy_max_us = s_busy_max_us;
  stats->period_min_us = s_period_min_us;
  stats->period_max_us = s_period_max_us;
  stats->fast_count = s_fast_count;
  stats->fast_busy_max_us = s_fast_busy_max_us;
  s_tick_count = 0;
  s_busy_max_us = 0;
  s_period_min_us = 0xFFFFFFFF;
  s_period_max_us = 0;
  s_fast_count = 0;
  s_fast_busy_max_us = 0;
  __enable_irq();
}

/* 20kHz・4kHz の処理が、前に呼んでから 1 回でも来ていれば true。印は消して、次に備える */
bool scheduler_check_alive(void)
{
  bool alive = s_fast_alive && s_tick_alive;
  s_fast_alive = false;
  s_tick_alive = false;
  return alive;
}

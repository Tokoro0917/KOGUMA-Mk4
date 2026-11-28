/*
 * motor_test.c
 * 電流の制御の確かめと、モーターの同定(モード4 No.14・15。MODES.md、docs/control.md の 5 章)。MK4 で足したもの(2026-11-28)
 *
 * どちらも **タイヤを浮かせて** から始める(機体は動かない)。
 *
 * ■ No.14 電流のステップの応答
 * 左右に STEP_CURRENT_MA の電流の目標を STEP_MS だけ入れて、0 に戻す。20kHz の電流のログ(kind=current)を取るので、
 * 終わったらモード7 No.1(またはコマンドの get log)で、目標と測った電流の立ち上がりを見る(CURRENT_KP・KI を決める)。
 *
 * ■ No.15 モーターの同定(空転)
 * 決めた電圧を段ごとにかけ、落ち着いたところで電流とタイヤの速さを平均してシリアルに出す:
 *   MOTOR_ID,電圧[V],左の電流[mA],右の電流[mA],左の速さ[mm/s],右の速さ[mm/s]
 * 空転では、電圧 ≒ R × 電流 + Ke × モーターの角速度 なので、2 つ以上の段から R と Ke(= Kt)を求められる
 * (PC で計算する)。巻線の抵抗だけを測るときは、タイヤを手で押さえて止めた状態で、同じ No.15 を使う(速さが 0 になる)。
 */
#include "sys/motor_test.h"

#include <stdio.h>

#include "ctrl/current_ctrl.h"
#include "ctrl/odometry.h"
#include "drv/current.h"
#include "drv/timebase.h"
#include "sys/log.h"
#include "sys/ui.h"

#define STEP_CURRENT_MA 500.0f   /* ステップの電流 [mA] */
#define STEP_BEFORE_MS 20        /* ステップの前に 0 にしておく時間 [ms] */
#define STEP_MS 200              /* ステップを入れている時間 [ms] */
#define STEP_AFTER_MS 100        /* ステップのあと 0 にしておく時間 [ms] */

#define ID_STEP_COUNT 4          /* 同定の段の数 */
#define ID_SETTLE_MS 600         /* 1 段で、落ち着くまで待つ時間 [ms] */
#define ID_AVERAGE_COUNT 100     /* 平均する回数(2ms ごと) */
#define ID_AVERAGE_STEP_MS 2

/* 電流のステップの応答(No.14)。電流のログを取る */
void motor_test_current_step(void)
{
  log_kind_t kind_before = log_get_kind();
  log_set_kind(LOG_KIND_CURRENT);
  log_start(1);
  current_ctrl_set_target_mA(0.0f, 0.0f);
  ui_wait_ms(STEP_BEFORE_MS);
  current_ctrl_set_target_mA(STEP_CURRENT_MA, STEP_CURRENT_MA);
  ui_wait_ms(STEP_MS);
  current_ctrl_set_target_mA(0.0f, 0.0f);
  ui_wait_ms(STEP_AFTER_MS);
  current_ctrl_stop();
  log_stop();
  log_set_kind(kind_before);
  printf("CURRENT_STEP done (%.0f mA, %d ms). Send 'get log' to see it\r\n", STEP_CURRENT_MA, STEP_MS);
  ui_signal_ok();
}

/* 同定の 1 段: voltage_v をかけて、落ち着いたら平均を出す */
static void identify_one_step(float voltage_v)
{
  current_ctrl_set_voltage(voltage_v, voltage_v);
  ui_wait_ms(ID_SETTLE_MS);
  float left_mA = 0.0f;
  float right_mA = 0.0f;
  float left_mm_s = 0.0f;
  float right_mm_s = 0.0f;
  for (int i = 0; i < ID_AVERAGE_COUNT; i++) {
    left_mA = left_mA + current_get_left_mA();
    right_mA = right_mA + current_get_right_mA();
    left_mm_s = left_mm_s + odometry_get_left_speed_mm_s();
    right_mm_s = right_mm_s + odometry_get_right_speed_mm_s();
    timebase_wait_ms(ID_AVERAGE_STEP_MS);
  }
  printf("MOTOR_ID,%.2f,%.1f,%.1f,%.1f,%.1f\r\n", voltage_v,
         left_mA / ID_AVERAGE_COUNT, right_mA / ID_AVERAGE_COUNT,
         left_mm_s / ID_AVERAGE_COUNT, right_mm_s / ID_AVERAGE_COUNT);
}

/* モーターの同定(No.15)。電圧を 0.5V ずつ上げる */
void motor_test_identify(void)
{
  printf("MOTOR_ID,voltage_V,i_L_mA,i_R_mA,v_L_mm_s,v_R_mm_s (battery %.2f V)\r\n", current_get_battery_v());
  for (int step = 1; step <= ID_STEP_COUNT; step++) {
    identify_one_step(0.5f * step);
  }
  current_ctrl_stop();
  ui_signal_ok();
}

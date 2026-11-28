/*
 * test_current.c
 * 電流の制御(App/ctrl/current_ctrl.c)の PC のテスト。MK4 で足したもの(2026-11-28。docs/software.md の 12 章)
 *
 * モーターを PC の上の式で動かす(巻線の抵抗 R・インダクタンス L・逆起電力 Ke。タイヤは止めたまま、または決めた速さ):
 *   L × 電流の変わる速さ = かけた電圧(duty × 電池の電圧)− R × 電流 − Ke × モーターの角速度
 * 20kHz の 1 周期(50µs)を 50 に分けて、少しずつ電流を進める。
 * 確かめること:
 *   [1] 1A の目標に追いつく(5ms で 2% 以内)
 *   [2] 目標を大きくしても、上限(3A)で頭打ちになる
 *   [3] タイヤが回っていても(逆起電力があっても)目標に追いつく
 *   [4] 電流が大きすぎる状態が 1ms 続いたら止める。止めたら duty は 0
 *   [5] 電圧で回すときは duty = 電圧 ÷ 電池の電圧
 *   [6] 電池の電圧が読めていない(0V)ときは回さない
 */
#include <math.h>
#include <stdbool.h>
#include <stdio.h>

#include "config/robot_params.h"
#include "ctrl/current_ctrl.h"
#include "drv/current.h"
#include "drv/motor.h"

#define MODEL_INDUCTANCE_H 0.0001f   /* 仮のモーターのインダクタンス(100µH。まだ測っていない) */
#define SUB_STEPS 50                 /* 1 周期を何回に分けて進めるか */

static int s_fail_count = 0;

/* ok が false なら失敗として数え、message を表示する */
static void check(bool ok, const char *message)
{
  if (!ok) {
    s_fail_count = s_fail_count + 1;
    printf("  失敗: %s\n", message);
  }
}

/* ---- 仮のモーターと電池(current_ctrl.c が使う関数) ---- */
static float s_current_left_mA = 0.0f;
static float s_current_right_mA = 0.0f;
static float s_duty_left = 0.0f;
static float s_duty_right = 0.0f;
static float s_battery_v = 12.0f;
static float s_forced_current_mA = 0.0f;  /* 0 でなければ、測った電流をこの値にする(守りのテスト) */
static bool s_enabled = false;

float current_get_left_mA(void)
{
  if (s_forced_current_mA != 0.0f) {
    return s_forced_current_mA;
  }
  return s_current_left_mA;
}

float current_get_right_mA(void)
{
  return s_current_right_mA;
}

float current_get_battery_v(void)
{
  return s_battery_v;
}

void motor_set_duty(float left_duty, float right_duty)
{
  s_duty_left = left_duty;
  s_duty_right = right_duty;
}

void motor_stop(void)
{
  s_duty_left = 0.0f;
  s_duty_right = 0.0f;
}

void motor_enable(bool on)
{
  s_enabled = on;
}

/* 1 つのモーターの電流を 1 周期(50µs)進める。wheel_mm_s はタイヤの速さ */
static float step_motor(float current_mA, float duty, float wheel_mm_s)
{
  float dt_s = CURRENT_CTRL_PERIOD_S / SUB_STEPS;
  float motor_rad_s = wheel_mm_s * GEAR_RATIO / (TIRE_DIAMETER_MM / 2.0f);
  float current_a = current_mA / 1000.0f;
  for (int i = 0; i < SUB_STEPS; i++) {
    float voltage_v = duty * s_battery_v - MOTOR_RESISTANCE_OHM * current_a - MOTOR_KE_V_PER_RAD_S * motor_rad_s;
    current_a = current_a + voltage_v / MODEL_INDUCTANCE_H * dt_s;
  }
  return current_a * 1000.0f;
}

/* 20kHz の処理を count 回進める(電流の制御 → モーター) */
static void run_ticks(int count, float wheel_mm_s)
{
  for (int i = 0; i < count; i++) {
    current_ctrl_update();
    s_current_left_mA = step_motor(s_current_left_mA, s_duty_left, wheel_mm_s);
    s_current_right_mA = step_motor(s_current_right_mA, s_duty_right, wheel_mm_s);
  }
}

/* はじめの状態にする */
static void reset(void)
{
  current_ctrl_stop();
  s_current_left_mA = 0.0f;
  s_current_right_mA = 0.0f;
  s_battery_v = 12.0f;
  s_forced_current_mA = 0.0f;
  current_ctrl_set_wheel_speed(0.0f, 0.0f);
  current_ctrl_set_limit_mA(CURRENT_LIMIT_MA);
}

static void test_step(void)
{
  printf("[1] 1A の目標に追いつく(タイヤは止めたまま)\n");
  reset();
  current_ctrl_set_target_mA(1000.0f, -1000.0f);
  run_ticks(100, 0.0f);  /* 5ms */
  printf("  5ms 後: 左 %.1f mA、右 %.1f mA(duty 左 %.3f)\n", s_current_left_mA, s_current_right_mA, s_duty_left);
  check(fabsf(s_current_left_mA - 1000.0f) < 20.0f, "左は 5ms で 1000mA の 2% 以内");
  check(fabsf(s_current_right_mA + 1000.0f) < 20.0f, "右(− の向き)も 5ms で −1000mA の 2% 以内");
  check(s_enabled, "電流で回すと MP6551 を動かす(MOT_EN が H)");
}

static void test_limit(void)
{
  printf("[2] 目標を大きくしても、上限で頭打ち\n");
  reset();
  current_ctrl_set_target_mA(10000.0f, 10000.0f);
  run_ticks(200, 0.0f);
  printf("  10ms 後: %.1f mA(上限 %.0f mA)\n", s_current_left_mA, CURRENT_LIMIT_MA);
  check(fabsf(s_current_left_mA - CURRENT_LIMIT_MA) < 60.0f, "上限(3A)で頭打ち");
  current_ctrl_set_limit_mA(100000.0f);
  current_ctrl_set_target_mA(10000.0f, 10000.0f);
  run_ticks(200, 0.0f);
  printf("  上限を大きく頼んだとき: %.1f mA(いちばん大きい上限 %.0f mA)\n", s_current_left_mA, CURRENT_LIMIT_MAX_MA);
  check(fabsf(s_current_left_mA - CURRENT_LIMIT_MAX_MA) < 100.0f, "上限は CURRENT_LIMIT_MAX_MA(5A)より大きくならない");
  check(!current_ctrl_is_tripped(), "5A では守りは働かない(6A を 1ms で止める)");
}

static void test_back_emf(void)
{
  printf("[3] タイヤが 2000mm/s で回っていても、目標に追いつく(逆起電力の分を足す)\n");
  reset();
  current_ctrl_set_wheel_speed(2000.0f, 2000.0f);
  current_ctrl_set_target_mA(500.0f, 500.0f);
  run_ticks(100, 2000.0f);
  printf("  5ms 後: %.1f mA、duty %.3f\n", s_current_left_mA, s_duty_left);
  check(fabsf(s_current_left_mA - 500.0f) < 20.0f, "5ms で 500mA の 4% 以内");
}

static void test_trip(void)
{
  printf("[4] 電流が大きすぎる状態が 1ms 続いたら止める\n");
  reset();
  current_ctrl_set_target_mA(500.0f, 500.0f);
  run_ticks(10, 0.0f);
  s_forced_current_mA = 7000.0f;  /* 測った電流が 7A(ショートなど) */
  run_ticks(CURRENT_TRIP_TICKS - 1, 0.0f);
  check(!current_ctrl_is_tripped(), "19 回(0.95ms)では止めない");
  run_ticks(1, 0.0f);
  check(current_ctrl_is_tripped(), "20 回(1ms)続いたら止める");
  check(s_duty_left == 0.0f && s_duty_right == 0.0f && !s_enabled, "止めたら duty は 0、MP6551 はスリープ");
  current_ctrl_set_target_mA(500.0f, 500.0f);
  run_ticks(5, 0.0f);
  check(s_duty_left == 0.0f, "止めたあとは、目標を入れても回さない(current_ctrl_stop() まで)");
  s_forced_current_mA = 0.0f;
  current_ctrl_stop();
  check(!current_ctrl_is_tripped(), "current_ctrl_stop() で守りの印が消える");
}

static void test_voltage_mode(void)
{
  printf("[5] 電圧で回す\n");
  reset();
  current_ctrl_set_voltage(3.0f, -1.2f);
  run_ticks(1, 0.0f);
  printf("  duty 左 %.4f、右 %.4f(電池 12V)\n", s_duty_left, s_duty_right);
  check(fabsf(s_duty_left - 0.25f) < 0.0001f && fabsf(s_duty_right + 0.1f) < 0.0001f, "duty = 電圧 ÷ 電池の電圧");
  current_ctrl_set_voltage(100.0f, 0.0f);
  run_ticks(1, 0.0f);
  check(fabsf(s_duty_left - 0.95f) < 0.0001f, "duty は 0.95 まで");
}

static void test_no_battery(void)
{
  printf("[6] 電池の電圧が読めていないときは回さない\n");
  reset();
  s_battery_v = 0.0f;
  current_ctrl_set_target_mA(1000.0f, 1000.0f);
  run_ticks(10, 0.0f);
  check(s_duty_left == 0.0f, "電池 0V なら duty 0");
}

int main(void)
{
  test_step();
  test_limit();
  test_back_emf();
  test_trip();
  test_voltage_mode();
  test_no_battery();
  if (s_fail_count == 0) {
    printf("すべて成功\n");
    return 0;
  }
  printf("失敗 %d 件\n", s_fail_count);
  return 1;
}
